from app.effects import EffectRegistry
from app.skill_rules.rosanna_chic_ocean import (
    SPINA_COOLDOWN,
    build_rosanna_rules,
    build_spina_periodic_rules,
    build_spina_scheduled_nukes,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Rosanna: Chic Ocean).
FERITA = {
    "description_value_01": "24.26",  # Damage to Parts %
    "description_value_02": "15",     # duration
}
SPINA_DI_ROSA = {
    "description_value_01": "24.26",  # Damage to Parts % (squad)
    "description_value_02": "15",     # duration
    "description_value_03": "70.4",   # sustained damage % of final ATK per tick
    "description_value_04": "1",      # tick interval
    "description_value_05": "15",     # DoT duration
}
ONDA_GRANDE = {
    "description_value_01": "20.32",  # Sustained Damage % (squad)
    "description_value_02": "10",     # duration
    "description_value_03": "32.23",  # Damage Taken % (enemy)
    "description_value_04": "10",     # duration
}


def make_context():
    return SquadContext([
        SquadMember("rosanna-chic-ocean", burst_tier=2, element="Wind"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build():
    return build_rosanna_rules({"ferita": FERITA, "onda_grande": ONDA_GRANDE})


ROSANNA = {"slug": "rosanna-chic-ocean", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_ferita_grants_squad_damage_to_parts_at_battle_start():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"rosanna-chic-ocean": build()}, ctx, registry, time=0.0)

    assert round(registry.total_for("damage_to_parts_up", ALLY, now=0.0), 4) == 0.2426
    assert registry.total_for("damage_to_parts_up", ALLY, now=15.1) == 0.0


def test_burst_grants_squad_sustained_damage_and_enemy_damage_taken():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"rosanna-chic-ocean": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("sustained_damage_up", ALLY, now=5.0), 4) == 0.2032
    assert round(registry.total_for("damage_taken_up", ALLY, now=5.0), 4) == 0.3223
    assert registry.total_for("sustained_damage_up", ALLY, now=15.1) == 0.0
    assert registry.total_for("damage_taken_up", ALLY, now=15.1) == 0.0


def test_spina_periodic_buff_matches_ferita_and_fires_on_its_own_cooldown():
    (cooldown, rules), = build_spina_periodic_rules({"spina_di_rosa": SPINA_DI_ROSA})
    assert cooldown == SPINA_COOLDOWN == 30.0

    ctx = make_context()
    registry = EffectRegistry()
    rules[0].action(ctx, "rosanna-chic-ocean", 30.0, registry)  # first cast, t=cooldown

    assert round(registry.total_for("damage_to_parts_up", ALLY, now=30.0), 4) == 0.2426
    assert round(registry.total_for("damage_to_parts_up", ALLY, now=44.9), 4) == 0.2426
    assert registry.total_for("damage_to_parts_up", ALLY, now=45.0) == 0.0  # 15s window


def test_spina_dot_ticks_every_second_for_15s_per_cast_starting_at_cooldown():
    spec, = build_spina_scheduled_nukes({"spina_di_rosa": SPINA_DI_ROSA})
    assert spec["percent"] == 70.4
    assert spec["damage_type"] == "sustained"

    ticks = sorted(spec["schedule"](make_context(), 180.0))

    # Casts at t=30/60/90/120/150 - Spina has no battle-start force-fire, so the
    # first cast is at its own cooldown (docs/decisions.md, periodic skill trigger).
    assert ticks[:15] == [31.0 + n for n in range(15)]
    assert len(ticks) == 5 * 15
    assert max(ticks) == 165.0  # last cast t=150, last tick t=165


def test_spina_dot_never_ticks_past_the_end_of_the_fight():
    spec, = build_spina_scheduled_nukes({"spina_di_rosa": SPINA_DI_ROSA})
    ticks = list(spec["schedule"](make_context(), 40.0))

    assert ticks == [31.0 + n for n in range(9)]  # cast at 30, cut at t=40
