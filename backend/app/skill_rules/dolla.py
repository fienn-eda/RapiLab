"""Dolla (slug "dolla"), a Burst-2 Wind SR supporter.
Values from ShiftyPad; effect text cross-read from lootandwaifus.

Modeled (DPS-relevant):
- Entrepreneurship (skills[0], cd 10): squad ATK +16.16% for 5 sec. No trigger
  phrase and a cooldown, which is the signature of a `periodic_rules` skill -
  it first fires at t=10 and repeats, never at battle start. A 5-sec buff on a
  10-sec cooldown is a 50% duty cycle, and the engine models exactly that
  rather than steady-stating it.
- Risk Sharing (skills[1]), both halves escalating "Once/Twice/Three times,
  each subsequent effect triggers all effects before it":
  - on Full Burst enter, squad burst-cooldown reduction 1.82 / 2.2 / 2.6 sec,
    summing to 6.62 by the third cycle. Written out directly rather than via
    `escalating_buff_rule` because a Pulse is not an Effect - the same shape as
    Helm: Aquamarine's tiers.
  - on her own burst, squad ATK +7.72%, then Critical Rate +4.21%, then
    Critical Damage +13.22%, each 5 sec. Every tier is a DIFFERENT stat, so the
    ramp is which stats are live, not how large one of them is.
- R&D Shot (skills[2], her burst, cd 20): 734.69% of final ATK as burst damage.
  "Affects 1 enemy unit with the highest final DEF" - the solo raid has one
  boss, so the targeting is a no-op here.

The Full Burst tier count uses `activation_count(caster, "full_burst_enter")`,
which tracks the raid's cycle number rather than her own burst count: entering
Full Burst is a squad-wide event and the text says "the number of times
entered", not "the number of times you burst".

Not modeled / deferred: nothing. Every bullet in her kit is a damage stat the
engine consumes.
"""
from app.effects import Pulse
from app.skill_rules._helpers import buff_rule, escalating_buff_rule
from app.squad_engine import SkillRule


SKILL_VALUE_MANIFESTS = {
    "dolla": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_dolla",
        "keys": {
            "entrepreneurship": ("skills", 0),
            "risk_sharing": ("skills", 1),
            "rnd_shot": ("skills", 2),
        },
    },
}


# lootandwaifus prints it in the skill title ("Entrepreneurship (cd 10)"); it is
# fixed skill text, not a data slot.
ENTREPRENEURSHIP_COOLDOWN = 10.0


def rnd_shot_burst_percent(values):
    return float(values["rnd_shot"]["description_value_02"])


def build_entrepreneurship_periodic_rules(entrepreneurship):
    """Skill 1 on its own 10-sec cooldown - see raid_simulator's
    `periodic_rules`. Stateless, as that mechanism requires."""
    atk = float(entrepreneurship["description_value_01"]) / 100
    duration = float(entrepreneurship["description_value_02"])
    return [buff_rule("periodic", [("atk_percent", atk, "squad", duration)])]


def build_dolla_rules(values):
    risk = values["risk_sharing"]

    cdr_tiers = [
        float(risk["description_value_01"]),  # Once
        float(risk["description_value_02"]),  # Twice
        float(risk["description_value_03"]),  # Three times
    ]
    atk = float(risk["description_value_04"]) / 100
    atk_duration = float(risk["description_value_05"])
    crit_rate = float(risk["description_value_06"]) / 100
    crit_rate_duration = float(risk["description_value_07"])
    crit_damage = float(risk["description_value_08"]) / 100
    crit_damage_duration = float(risk["description_value_09"])

    def apply_cdr(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, "full_burst_enter")
        total = sum(cdr_tiers[: min(n, len(cdr_tiers))])
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", total, "squad", caster_slug))

    return [
        SkillRule(trigger="full_burst_enter", action=apply_cdr),
        escalating_buff_rule("own_burst_activate", [
            [("atk_percent", atk, "squad", atk_duration)],
            [("crit_rate", crit_rate, "squad", crit_rate_duration)],
            [("other_critical_damage_sources", crit_damage, "squad", crit_damage_duration)],
        ]),
    ]
