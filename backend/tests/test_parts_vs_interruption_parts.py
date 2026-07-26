"""Two different game concepts wear near-identical English names.

- "Damage to Parts" (파츠 대미지) raises damage dealt to a boss's DESTRUCTIBLE
  PARTS.
- "Damage to Interruption Parts" (저지 부위 공격 대미지) raises damage dealt to
  the zone you must hit to clear an interruption GIMMICK - a different target
  entirely, not a destructible part (Fienn, 2026-07-26).

Both were being written into `damage_to_parts_up`, which is exactly the
misreading the wording invites. They are separate stats now. Neither reaches
body damage, so this is about keeping the encodings honest rather than about
moving a number today.
"""
from app.effects import EffectRegistry
from app.skill_rules.anis_sparkling_summer import build_sparkling_missile_per_shot_rules
from app.skill_rules.helm import build_fire_away_rules
from app.skill_rules.noir import build_noir_rules
from app.squad_engine import SquadContext, SquadMember

INTERRUPTION = "damage_to_interruption_parts_up"
DESTRUCTIBLE = "damage_to_parts_up"


def _ctx(slug):
    return SquadContext([
        SquadMember(slug, burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def _fire(rules, slug, registry, time=0.0):
    ctx = _ctx(slug)
    for rule in rules:
        rule.action(ctx, slug, time, registry)


def test_helms_fire_away_grants_interruption_parts_not_destructible_parts():
    # "아군 전체에게 저지 부위 공격 대미지 N% 증가, 지속" - Fienn's own reading
    # of the Korean text that started this.
    values = {"description_value_01": "3.08", "description_value_02": "20.0",
              "description_value_03": "10.0"}
    registry = EffectRegistry()
    _fire(build_fire_away_rules(values), "helm", registry)
    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for(INTERRUPTION, ally, now=99999), 4) == 0.0308
    assert registry.total_for(DESTRUCTIBLE, ally, now=99999) == 0.0


def test_noirs_finale_grants_interruption_parts():
    values = {
        "caster_atk": 100000,
        "lucky_charm": {"description_value_01": "14.08"},
        "finale": {
            "description_value_01": "351.64", "description_value_02": "13.93",
            "description_value_03": "10", "description_value_04": "23.23",
            "description_value_05": "10", "description_value_06": "11.61",
            "description_value_07": "30", "description_value_08": "19.36",
            "description_value_09": "30",
        },
    }
    registry = EffectRegistry()
    _fire(build_noir_rules(values), "noir", registry)
    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for(INTERRUPTION, ally, 0.0), 4) == round(0.2323 + 0.1936, 4)
    assert registry.total_for(DESTRUCTIBLE, ally, 0.0) == 0.0


def test_sparkling_summers_self_buff_is_interruption_parts():
    values = {"description_value_01": "382.42", "description_value_02": "6.91",
              "description_value_03": "10"}
    registry = EffectRegistry()
    rules = build_sparkling_missile_per_shot_rules(values)
    _, _, shot_rules = rules[0]
    _fire(shot_rules, "anis-sparkling-summer", registry, time=3.0)
    anis = {"slug": "anis-sparkling-summer", "element": "Water"}
    assert round(registry.total_for(INTERRUPTION, anis, now=3.0), 4) == 0.0691
    assert registry.total_for(DESTRUCTIBLE, anis, now=3.0) == 0.0
