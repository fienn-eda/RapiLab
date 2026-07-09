from app.effects import EffectRegistry
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule
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


def test_cdr_pulse_rule_emits_a_drainable_pulse():
    rule = cdr_pulse_rule("full_burst_enter", 3.17)
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"src": [rule]}, ctx(), registry, time=0.0)

    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 3.17
    assert pulses[0].scope == "squad"
