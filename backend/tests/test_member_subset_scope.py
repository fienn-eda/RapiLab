"""member_subset_buff_rule (gap #3): timed buffs on the squad members selected
by a live filter at trigger time - subsets Effect.scope can't express, like
"all Wind Code allies with assault rifles" (needs SquadMember.weapon)."""
from app.effects import EffectRegistry
from app.skill_rules._helpers import member_subset_buff_rule
from app.squad_engine import SquadContext, SquadMember, fire_trigger


def _context():
    return SquadContext([
        SquadMember("caster", burst_tier=1, element="Wind", weapon="AR"),
        SquadMember("wind-ar", burst_tier=3, element="Wind", weapon="AR"),
        SquadMember("wind-sg", burst_tier=3, element="Wind", weapon="SG"),
        SquadMember("iron-ar", burst_tier=3, element="Iron", weapon="AR"),
    ])


def _rules():
    return member_subset_buff_rule(
        "full_burst_enter",
        lambda m, context: m.element == "Wind" and m.weapon == "AR",
        [("sustained_damage_up", 0.775, 10.0)],
    )


def test_buff_lands_only_on_matching_members():
    context, registry = _context(), EffectRegistry()
    fire_trigger("full_burst_enter", {"caster": [_rules()]}, context, registry, time=5.0)
    def total(slug, element, weapon):
        return registry.total_for("sustained_damage_up", {"slug": slug, "element": element, "weapon": weapon}, 6.0)
    assert total("wind-ar", "Wind", "AR") == 0.775
    assert total("caster", "Wind", "AR") == 0.775   # caster matches the filter too
    assert total("wind-sg", "Wind", "SG") == 0.0
    assert total("iron-ar", "Iron", "AR") == 0.0


def test_empty_selection_applies_nothing():
    context, registry = _context(), EffectRegistry()
    rule = member_subset_buff_rule(
        "full_burst_enter", lambda m, c: m.weapon == "MG", [("atk_percent", 1.0, 10.0)]
    )
    fire_trigger("full_burst_enter", {"caster": [rule]}, context, registry, time=5.0)
    assert registry.total_for("atk_percent", {"slug": "wind-ar", "element": "Wind"}, 6.0) == 0.0


def test_weapon_defaults_to_none_for_existing_constructions():
    member = SquadMember("x", burst_tier=1, element="Wind")
    assert member.weapon is None
