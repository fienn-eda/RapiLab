"""Flora (base build) - a healer whose DPS contribution is True Damage buffs."""
from app.effects import EffectRegistry
from app.skill_rules.flora import build_flora_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/flora.json, level 10).
IRIS = {
    "description_value_01": "90", "description_value_02": "10.22",
    "description_value_03": "10", "description_value_04": "30.97",
    "description_value_05": "5",
}
SECRET_GARDEN = {
    "description_value_01": "10.45", "description_value_02": "42.39",
    "description_value_03": "10",
}
FLORA = {"iris": IRIS, "secret_garden": SECRET_GARDEN}

SELF = {"slug": "flora", "element": "Electric"}
ALLY = {"slug": "ally", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("flora", burst_tier=2, element="Electric", weapon="MG"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ])


def _fire(trigger, time=0.0):
    reg = EffectRegistry()
    fire_trigger(trigger, {"flora": build_flora_rules(FLORA)}, _ctx(), reg, time)
    return reg


def test_iris_true_damage_is_permanent_and_squad_wide():
    # "when either adjacent ally reaches max HP" - allies never lose HP in the
    # sim, so Fienn ruled this always-on (2026-07-24). Adjacency has no scope
    # 트리거일 뿐이고, 효과 줄은 "Affects all allies"라 squad가 이 불릿의 제
    # 스코프다 - 좌석과 무관하다.
    reg = _fire("battle_start")
    assert round(reg.total_for("true_damage_up", SELF, 0.0), 4) == 0.3097
    assert round(reg.total_for("true_damage_up", ALLY, 0.0), 4) == 0.3097
    assert round(reg.total_for("true_damage_up", ALLY, 179.0), 4) == 0.3097


def test_burst_stacks_its_true_damage_on_top_for_ten_seconds():
    reg = EffectRegistry()
    rules = {"flora": build_flora_rules(FLORA)}
    ctx = _ctx()
    fire_trigger("battle_start", rules, ctx, reg, 0.0)
    fire_trigger("own_burst_activate", rules, ctx, reg, 20.0)
    # Secret Garden is a separate source, so it sums with the permanent bullet.
    assert round(reg.total_for("true_damage_up", ALLY, 20.0), 4) == round(0.3097 + 0.4239, 4)
    assert round(reg.total_for("true_damage_up", ALLY, 30.1), 4) == 0.3097


def test_heals_shields_and_the_stack_count_buff_are_not_emitted():
    """Heals/shields/Incoming Healing are not damage, and "increase the stack
    count of stackable buffs" has no engine concept at all."""
    for trigger in ("battle_start", "own_burst_activate", "full_burst_enter"):
        reg = _fire(trigger)
        for stat in ("shield_amount", "flat_max_hp", "atk_percent", "flat_atk"):
            assert reg.total_for(stat, SELF, 0.0) == 0.0
