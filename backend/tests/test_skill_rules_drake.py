from app.effects import EffectRegistry
from app.skill_rules.drake import (
    build_drake_rules,
    build_drake_signature_rules,
    build_thunderbolt_per_shot_rules,
    build_thunderbolt_signature_per_shot_rules,
    drake_signature_burst_percent,
    drake_special_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg (base `skills` and signature `dollskills`).
OVERCHARGE = {
    "description_value_01": "11.85",  # deferred: Hit Rate %
    "description_value_02": "10",
    "description_value_03": "11.85",  # squad ATK %
    "description_value_04": "10",
}
THUNDERBOLT = {
    "description_value_01": "10",     # normal-attack threshold
    "description_value_02": "3",      # enemies (collapses to the single boss)
    "description_value_03": "98.55",  # nuke % of final ATK
}
DRAKE_SPECIAL = {
    "description_value_01": "1254",   # burst nuke % of final ATK
    "description_value_02": "72.18",  # self Max Ammo %
    "description_value_03": "10",
}
OVERCHARGE_SIG = {
    "description_value_01": "20.09",  # deferred: Hit Rate %
    "description_value_02": "10",
    "description_value_03": "11.85",  # all-allies ATK %
    "description_value_04": "10",
    "description_value_05": "63.88",  # SG-allies (squad approx) ATK %
    "description_value_06": "10",
    "description_value_07": "50.14",  # SG-allies (squad approx) Max Ammo %
    "description_value_08": "10",
}
THUNDERBOLT_SIG = {
    "description_value_01": "10",     # threshold clause 1
    "description_value_02": "3",
    "description_value_03": "98.55",  # nuke % clause 1
    "description_value_04": "5",      # threshold clause 2
    "description_value_05": "1",
    "description_value_06": "201.6",  # nuke % clause 2
}
DRAKE_SPECIAL_SIG = {
    "description_value_01": "3009.6",  # burst nuke % of final ATK
    "description_value_02": "72.18",   # self Max Ammo %
    "description_value_03": "10",
    "description_value_04": "31.68",   # self Attack Damage %
    "description_value_05": "10",
}


def make_context():
    return SquadContext([
        SquadMember("drake", burst_tier=3, element="Fire", weapon="SG"),
        SquadMember("ally", burst_tier=1, element="Wind", weapon="AR"),
        SquadMember("sg-ally", burst_tier=2, element="Iron", weapon="SG"),
    ])


DRAKE = {"slug": "drake", "element": "Fire"}
ALLY = {"slug": "ally", "element": "Wind"}
SG_ALLY = {"slug": "sg-ally", "element": "Iron"}


def base():
    return build_drake_rules({"overcharge": OVERCHARGE, "drake_special": DRAKE_SPECIAL})


def sig():
    return build_drake_signature_rules({"overcharge": OVERCHARGE_SIG, "drake_special": DRAKE_SPECIAL_SIG})


def test_burst_percents():
    assert drake_special_burst_percent({"drake_special": DRAKE_SPECIAL}) == 1254.0
    assert drake_signature_burst_percent({"drake_special": DRAKE_SPECIAL_SIG}) == 3009.6


def test_base_overcharge_squad_atk_and_burst_max_ammo():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"drake": base()}, ctx, registry, time=5.0)
    assert round(registry.total_for("atk_percent", ALLY, now=5.0), 4) == 0.1185
    assert registry.total_for("atk_percent", ALLY, now=15.1) == 0.0

    registry2 = EffectRegistry()
    fire_trigger("own_burst_activate", {"drake": base()}, ctx, registry2, time=5.0)
    assert round(registry2.total_for("max_ammo_percent", DRAKE, now=5.0), 4) == 0.7218
    assert registry2.total_for("max_ammo_percent", ALLY, now=5.0) == 0.0  # self-only


def test_base_thunderbolt_nukes_every_10_normals():
    rules = build_thunderbolt_per_shot_rules({"thunderbolt": THUNDERBOLT})
    assert len(rules) == 1
    assert (rules[0][0], rules[0][1]) == (10, "every")
    registry = EffectRegistry()
    rules[0][2][0].action(make_context(), "drake", 5.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 98.55


def test_signature_overcharge_adds_sg_atk_and_max_ammo_to_sg_allies_only():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"drake": sig()}, ctx, registry, time=5.0)
    # SG allies (drake included): all-allies 11.85% + SG-allies 63.88% = 75.73%
    assert round(registry.total_for("atk_percent", SG_ALLY, now=5.0), 4) == 0.7573
    assert round(registry.total_for("max_ammo_percent", SG_ALLY, now=5.0), 4) == 0.5014
    assert round(registry.total_for("atk_percent", DRAKE, now=5.0), 4) == 0.7573
    # the AR ally gets only the all-allies portion
    assert round(registry.total_for("atk_percent", ALLY, now=5.0), 4) == 0.1185
    assert registry.total_for("max_ammo_percent", ALLY, now=5.0) == 0.0


def test_signature_burst_adds_self_attack_damage():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"drake": sig()}, ctx, registry, time=5.0)
    assert round(registry.total_for("max_ammo_percent", DRAKE, now=5.0), 4) == 0.7218
    assert round(registry.total_for("attack_damage_up", DRAKE, now=5.0), 4) == 0.3168
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0  # self-only


def test_signature_thunderbolt_has_two_nuke_triggers():
    rules = build_thunderbolt_signature_per_shot_rules({"thunderbolt": THUNDERBOLT_SIG})
    assert len(rules) == 2
    assert (rules[0][0], rules[0][1]) == (10, "every")
    assert (rules[1][0], rules[1][1]) == (5, "every")
    registry = EffectRegistry()
    rules[0][2][0].action(make_context(), "drake", 5.0, registry)
    rules[1][2][0].action(make_context(), "drake", 5.0, registry)
    values = sorted(p.value for p in registry.drain_pulses("instant_damage_percent"))
    assert values == [98.55, 201.6]
