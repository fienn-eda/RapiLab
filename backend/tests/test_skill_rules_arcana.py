from app.effects import EffectRegistry
from app.skill_rules.arcana import arcana_burst_percent, build_arcana_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
AWAKENED_DESTINY = {
    "description_value_01": "3",    # Burst 3 (deferred bullet's tier filter)
    "description_value_02": "75",   # deferred: Cooldown of Skill 2 down %
    "description_value_03": "15",   # deferred: duration
    "description_value_04": "180",  # deferred: Attack damage %
    "description_value_05": "15",   # deferred: duration
    "description_value_06": "5",    # squad ATK % of caster's ATK
    "description_value_07": "10",   # duration
}
CYCLE_OF_DESTINY = {
    "description_value_01": "3",    # deferred: Burst 3 tier filter
    "description_value_02": "180",  # deferred: Strength ATK % of caster's ATK
    "description_value_03": "15",   # deferred: duration
    "description_value_04": "6",    # Death: Cooldown of Burst Skill down sec
    "description_value_05": "50",   # Death: ATK % of caster's ATK
    "description_value_06": "5",    # Death: duration
    "description_value_07": "7.5",  # squad Attack damage %
    "description_value_08": "10",   # duration
}
SHACKLES_OF_DESTINY = {
    "description_value_01": "10",   # Wheel of Fortune: Attack damage %
    "description_value_02": "10",   # duration
    "description_value_03": "300",  # burst nuke % of final ATK
    "description_value_04": "10",   # Judgement: Damage taken %
    "description_value_05": "10",   # duration
}


def make_context():
    return SquadContext([
        SquadMember("arcana", burst_tier=2, element="Electric"),
        SquadMember("electric-ally", burst_tier=3, element="Electric"),
        SquadMember("fire-ally", burst_tier=1, element="Fire"),
    ])


def build(caster_atk=10000):
    return build_arcana_rules({
        "awakened_destiny": AWAKENED_DESTINY,
        "cycle_of_destiny": CYCLE_OF_DESTINY,
        "shackles_of_destiny": SHACKLES_OF_DESTINY,
        "caster_atk": caster_atk,
    })


ELECTRIC_ALLY = {"slug": "electric-ally", "element": "Electric"}
FIRE_ALLY = {"slug": "fire-ally", "element": "Fire"}


def test_burst_percent_is_300():
    assert arcana_burst_percent({"shackles_of_destiny": SHACKLES_OF_DESTINY}) == 300.0


def test_shackles_grants_electric_attack_damage_and_enemy_damage_taken():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"arcana": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", ELECTRIC_ALLY, now=5.0), 4) == 0.10
    assert registry.total_for("attack_damage_up", FIRE_ALLY, now=5.0) == 0.0  # element-gated
    assert round(registry.total_for("damage_taken_up", FIRE_ALLY, now=5.0), 4) == 0.10  # squad-wide


def test_awakened_destiny_squad_atk_applies_unconditionally():
    ctx = make_context()
    registry = EffectRegistry()
    # arcana's own burst has NOT fired this cycle
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=15.0)

    assert registry.total_for("flat_atk", FIRE_ALLY, now=15.0) == 500.0  # 5% of 10000


def test_cycle_of_destiny_death_bullet_requires_arcana_burst_this_cycle():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=15.0)
    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []
    # only Awakened Destiny's unconditioned 5% applies, not Death's 50%
    assert registry.total_for("flat_atk", FIRE_ALLY, now=15.0) == 500.0

    ctx.burst_used_this_cycle.add("arcana")
    registry2 = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry2, time=15.0)
    pulses = registry2.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 6.0
    assert pulses[0].scope == "squad"
    # Awakened's 5% (500) + Death's 50% (5000) = 5500
    assert registry2.total_for("flat_atk", FIRE_ALLY, now=15.0) == 5500.0


def test_cycle_of_destiny_attack_damage_bullet_applies_unconditionally():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=15.0)
    assert round(registry.total_for("attack_damage_up", FIRE_ALLY, now=15.0), 4) == 0.075
