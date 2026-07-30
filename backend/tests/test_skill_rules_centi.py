"""Base Centi - a shield Defender whose only damage contribution is her burst:
a 145.46% nuke plus a squad-wide enemy DEF debuff."""
from app.effects import EffectRegistry
from app.skill_rules.centi import build_centi_rules, start_construction_burst_percent
from app.squad_engine import SquadContext, SquadMember, fire_trigger

START_CONSTRUCTION = {
    "description_value_01": "5", "description_value_02": "145.46",
    "description_value_03": "14.54", "description_value_04": "10",
}
CENTI = {"start_construction": START_CONSTRUCTION}

SELF = {"slug": "centi", "element": "Iron"}
ALLY = {"slug": "ally", "element": "Fire"}


def _fire(time=0.0):
    ctx = SquadContext([
        SquadMember("centi", burst_tier=2, element="Iron", weapon="RL"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ])
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"centi": build_centi_rules(CENTI)}, ctx, reg, time)
    return reg


def test_burst_strips_enemy_def_for_every_attacker():
    reg = _fire()
    assert round(reg.total_for("enemy_def_percent", SELF, 0.0), 4) == -0.1454
    assert round(reg.total_for("enemy_def_percent", ALLY, 0.0), 4) == -0.1454
    assert round(reg.total_for("enemy_def_percent", ALLY, 9.9), 4) == -0.1454
    assert reg.total_for("enemy_def_percent", ALLY, 10.1) == 0.0


def test_the_burst_debuff_starts_where_the_burst_fires():
    reg = _fire(time=20.0)
    assert reg.total_for("enemy_def_percent", ALLY, 19.9) == 0.0
    assert round(reg.total_for("enemy_def_percent", ALLY, 20.0), 4) == -0.1454


def test_burst_percent_is_the_nuke_coefficient():
    assert start_construction_burst_percent(CENTI) == 145.46


def test_the_shield_and_the_cooldown_cut_add_no_effects():
    """Her Skill 1 and Skill 2 are a cooldown cut and a shield; neither has a
    damage consumer in this build, so the burst rule is the whole encoding."""
    assert len(build_centi_rules(CENTI)) == 1
