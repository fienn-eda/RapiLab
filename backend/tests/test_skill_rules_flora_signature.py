"""Flora's Favorite Item build - the Max-HP bump at Burst Stage 2 entry drives a
self-contained shield combo that turns her into a real ATK buffer."""
from app.effects import EffectRegistry
from app.skill_rules.flora_signature import build_flora_signature_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# lootandwaifus dollskills, level 10, slots numbered left-to-right over EVERY
# number in the text - including the literal "Burst Stage 2" (petunia slot 06)
# and Iris's "90%" HP threshold (iris slot 01), which are trigger wording rather
# than buff values. Numbering them keeps the doll's Iris slots aligned with base
# Flora's ShiftyPad slots (01=90, 04=30.97).
PETUNIA = {
    "description_value_01": "1", "description_value_02": "4",
    "description_value_03": "5", "description_value_04": "100",
    "description_value_05": "1", "description_value_06": "2",
    "description_value_07": "15.01", "description_value_08": "2",
}
IRIS = {
    "description_value_01": "90", "description_value_02": "10.22",
    "description_value_03": "10", "description_value_04": "30.97",
    "description_value_05": "10", "description_value_06": "45.12",
    "description_value_07": "10",
}
SECRET_GARDEN = {
    "description_value_01": "10.45", "description_value_02": "42.39",
    "description_value_03": "10", "description_value_04": "85.86",
    "description_value_05": "10",
}
CASTER_ATK = 60_000.0
CASTER_MAX_HP = 1_000_000.0
FLORA_SIG = {
    "petunia": PETUNIA, "iris": IRIS, "secret_garden": SECRET_GARDEN,
    "caster_atk": CASTER_ATK, "caster_max_hp": CASTER_MAX_HP,
}

SELF = {"slug": "flora-signature", "element": "Electric"}
ALLY = {"slug": "ally-b3", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("flora-signature", burst_tier=2, element="Electric", weapon="MG"),
        SquadMember("other-b2", burst_tier=2, element="Water", weapon="SMG"),
        SquadMember("ally-b3", burst_tier=3, element="Fire", weapon="AR"),
    ])


def _fire(trigger, burster=None, time=0.0, ctx=None):
    reg = EffectRegistry()
    ctx = ctx or _ctx()
    if burster is not None:
        ctx.last_burst_slug = burster
    fire_trigger(trigger, {"flora-signature": build_flora_signature_rules(FLORA_SIG)},
                 ctx, reg, time)
    return reg


def test_iris_true_damage_is_permanent_like_the_base_build():
    reg = _fire("battle_start")
    assert round(reg.total_for("true_damage_up", ALLY, 0.0), 4) == 0.3097
    assert round(reg.total_for("true_damage_up", ALLY, 179.0), 4) == 0.3097


def test_stage_two_entry_grants_max_hp_for_two_seconds():
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0)
    expected = CASTER_MAX_HP * 0.1501
    assert round(reg.total_for("flat_max_hp", ALLY, 20.0), 2) == round(expected, 2)
    assert reg.total_for("flat_max_hp", ALLY, 22.1) == 0.0  # 2 sec


def test_stage_two_entry_also_grants_the_shield_combo_atk_for_ten_seconds():
    # Max HP up WITHOUT healing drops every ally below 90% HP, which fires
    # Iris's shield, which fires the Favorite Item's ATK bullet (Fienn, 2026-07-24).
    reg = _fire("ally_burst_activate", burster="flora-signature", time=20.0)
    expected = CASTER_ATK * 0.4512
    assert round(reg.total_for("flat_atk", ALLY, 20.0), 2) == round(expected, 2)
    assert round(reg.total_for("flat_atk", ALLY, 29.9), 2) == round(expected, 2)
    assert reg.total_for("flat_atk", ALLY, 30.1) == 0.0  # 10 sec


def test_stage_two_bullets_fire_even_when_another_burst2_ally_takes_the_slot():
    reg = _fire("ally_burst_activate", burster="other-b2", time=20.0)
    assert round(reg.total_for("flat_max_hp", ALLY, 20.0), 2) == round(CASTER_MAX_HP * 0.1501, 2)
    assert round(reg.total_for("flat_atk", ALLY, 20.0), 2) == round(CASTER_ATK * 0.4512, 2)


def test_stage_two_bullets_do_not_fire_on_another_tier_burst():
    reg = _fire("ally_burst_activate", burster="ally-b3", time=20.0)
    assert reg.total_for("flat_max_hp", ALLY, 20.0) == 0.0
    assert reg.total_for("flat_atk", ALLY, 20.0) == 0.0


def test_burst_adds_squad_atk_on_top_of_its_true_damage():
    reg = _fire("own_burst_activate", time=20.0)
    assert round(reg.total_for("true_damage_up", ALLY, 20.0), 4) == 0.4239
    assert round(reg.total_for("flat_atk", ALLY, 20.0), 2) == round(CASTER_ATK * 0.8586, 2)
    assert reg.total_for("flat_atk", ALLY, 30.1) == 0.0
