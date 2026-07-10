from app.effects import EffectRegistry
from app.skill_rules.nayuta import asceticism_burst_percent, build_nayuta_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
HYPOCRISY = {
    "description_value_01": "9",       # self Indomitability sec (not modeled)
    "description_value_02": "1",       # activation count (not modeled)
    "description_value_03": "25.15",   # squad core-damage %
    "description_value_04": "5",       # duration
    "description_value_05": "30.16",   # squad ATK % of caster's ATK
    "description_value_06": "5",       # duration
    "description_value_07": "150",     # deferred: Full Charge nuke %
    "description_value_08": "25",      # self HP recovery % (not modeled)
    "description_value_09": "0",       # unused slot
    "description_value_10": "380.46",  # deferred: stage-target additional %
    "description_value_11": "5",       # unused slot
}
IMPERMANENCE = {
    "description_value_01": "3",       # stack interval sec
    "description_value_02": "30",      # max stacks
    "description_value_03": "30",      # Stage 3 threshold (== cap)
    "description_value_04": "21.05",   # Stage 3 self core-damage %
    "description_value_05": "2",       # Stage 1 threshold
    "description_value_06": "15.2",    # Stage 1 self ATK %
    "description_value_07": "10",      # Stage 2 threshold
    "description_value_08": "20.27",   # Stage 2 self Attack Damage %
    "description_value_09": "1.4",     # Hit Rate % (not modeled)
}
ASCETICISM = {
    "description_value_01": "35.45",   # squad Attack Damage %
    "description_value_02": "15",      # duration
    "description_value_03": "275.18",  # deferred: Memory Incineration damage %
    "description_value_04": "10",      # deferred: Memory Incineration duration
    "description_value_05": "645.33",  # burst nuke % of final ATK
    "description_value_06": "10",      # deferred: unlimited ammo duration
}


def make_context():
    return SquadContext([
        SquadMember("nayuta", burst_tier=2, element="Wind"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build(caster_atk=10000):
    return build_nayuta_rules({
        "hypocrisy": HYPOCRISY,
        "impermanence": IMPERMANENCE,
        "asceticism": ASCETICISM,
        "caster_atk": caster_atk,
    })


NAYUTA = {"slug": "nayuta", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_burst_percent_is_64533():
    assert asceticism_burst_percent({"asceticism": ASCETICISM}) == 645.33


def test_hypocrisy_squad_buffs_are_active_from_the_first_trigger_at_3_sec():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"nayuta": build()}, ctx, registry, time=0.0)

    assert registry.total_for("other_core_damage_sources", ALLY, now=2.9) == 0.0
    assert round(registry.total_for("other_core_damage_sources", ALLY, now=3.0), 4) == 0.2515
    assert registry.total_for("flat_atk", ALLY, now=3.0) == 3016.0  # 30.16% of 10000
    # stays active for the rest of the fight (overlapping re-triggers)
    assert round(registry.total_for("other_core_damage_sources", ALLY, now=179.0), 4) == 0.2515


def test_impermanence_stage_buffs_activate_at_their_fixed_stack_threshold_times():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"nayuta": build()}, ctx, registry, time=0.0)

    # Stage 1 (reaches 2 stacks) at t=6s, self-scoped ATK.
    assert registry.total_for("atk_percent", NAYUTA, now=5.9) == 0.0
    assert round(registry.total_for("atk_percent", NAYUTA, now=6.0), 4) == 0.152
    assert registry.total_for("atk_percent", ALLY, now=6.0) == 0.0  # self-only, not squad

    # Stage 2 (reaches 10 stacks) at t=30s, self-scoped Attack Damage.
    assert registry.total_for("attack_damage_up", NAYUTA, now=29.9) == 0.0
    assert round(registry.total_for("attack_damage_up", NAYUTA, now=30.0), 4) == 0.2027

    # Stage 3 (reaches the 30-stack cap) at t=90s, self-scoped core damage,
    # stacking on top of Hypocrisy's squad-wide core-damage share.
    assert round(registry.total_for("other_core_damage_sources", NAYUTA, now=89.9), 4) == 0.2515
    assert round(registry.total_for("other_core_damage_sources", NAYUTA, now=90.0), 4) == 0.462


def test_asceticism_grants_squad_attack_damage_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"nayuta": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.3545
    assert registry.total_for("attack_damage_up", ALLY, now=20.1) == 0.0
