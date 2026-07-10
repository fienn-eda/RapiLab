from app.effects import EffectRegistry
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule, escalating_buff_rule, instant_nuke_pulse_rule
from app.squad_engine import SquadContext, SquadMember, fire_trigger


def ctx():
    return SquadContext([
        SquadMember("src", burst_tier=1, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def test_buff_rule_adds_all_listed_effects_scoped_and_timed():
    rule = buff_rule("full_burst_enter", [
        ("atk_percent", 0.66, "squad", 5.0),
        ("crit_rate", 0.30, "self", 5.0),
    ])
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"src": [rule]}, ctx(), registry, time=2.0)

    ally = {"slug": "ally", "element": "Fire"}
    src = {"slug": "src", "element": "Iron"}
    assert registry.total_for("atk_percent", ally, now=2.0) == 0.66  # squad
    assert registry.total_for("crit_rate", ally, now=2.0) == 0.0     # self-only
    assert registry.total_for("crit_rate", src, now=2.0) == 0.30
    assert registry.total_for("atk_percent", ally, now=7.1) == 0.0   # expired


def test_escalating_buff_rule_applies_tiers_cumulatively_by_activation():
    # "Once/Twice/Three times, previous effects trigger repeatedly": each tier
    # unlocks on its activation and is re-applied every activation after. Tier 1
    # here is empty (e.g. a non-DPS hit-rate step).
    rule = escalating_buff_rule("full_burst_end", [
        [],
        [("flat_atk", 100.0, "squad", 10.0)],
        [("reload_speed_percent", 0.4, "squad", 15.0)],
    ])
    registry = EffectRegistry()
    context = ctx()
    ally = {"slug": "ally", "element": "Fire"}

    fire_trigger("full_burst_end", {"src": [rule]}, context, registry, time=10.0)
    assert registry.total_for("flat_atk", ally, now=10.0) == 0.0  # cycle 1: nothing

    fire_trigger("full_burst_end", {"src": [rule]}, context, registry, time=30.0)
    assert registry.total_for("flat_atk", ally, now=30.0) == 100.0  # cycle 2 unlock
    assert registry.total_for("reload_speed_percent", ally, now=30.0) == 0.0

    fire_trigger("full_burst_end", {"src": [rule]}, context, registry, time=50.0)
    # cycle 3: reload unlocks; flat_atk re-applied fresh (its cycle-2 window expired)
    assert registry.total_for("flat_atk", ally, now=50.0) == 100.0
    assert registry.total_for("reload_speed_percent", ally, now=50.0) == 0.4


def test_instant_nuke_pulse_rule_emits_a_drainable_instant_damage_pulse():
    rule = instant_nuke_pulse_rule("full_burst_enter", 636.0)
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"src": [rule]}, ctx(), registry, time=5.0)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 636.0
    assert pulses[0].scope == "self"
    assert pulses[0].source_slug == "src"


def test_cdr_pulse_rule_emits_a_drainable_pulse():
    rule = cdr_pulse_rule("full_burst_enter", 3.17)
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"src": [rule]}, ctx(), registry, time=0.0)

    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 3.17
    assert pulses[0].scope == "squad"
