"""What Centi's and Rosanna: Signature's stacks are worth if the timer refreshes.

WHY THESE TWO SEPARATELY: both hold a "stacks up to N ... lasts for D sec" buff
as OVERLAPPING `buff_rule` instances rather than a `ResourceSpec`, so
`audit_stack_lifetime_refresh.py`'s engine half - which reads resource counts -
cannot see them. They are also the two largest, and both were written off with
the same sentence:

  Centi:    "Neither stack cap binds: the cycle is ~5.7 sec against 8- and
             10-sec buffs, so at most 2 of the 10 stacks are ever live."
  Rosanna:  "about 2-3 instances overlap at steady state ... the skill text's
             10-stack cap is NOT reachable from this source alone."

That is per-stack-expiry arithmetic. Under the refreshing rule (the Raven
ruling, Fienn 2026-07-17) a proc arriving inside D restarts D for the WHOLE
stack, so a cadence FASTER than D never lets the stack lapse and the count
climbs to the cap. Centi procs every ~5.7 sec against 8 sec; Rosanna every ~15
sec against 30. Neither chain can break.

HOW IT IS EMULATED: each proc grants a PERMANENT instance (nothing expires
while the chain holds, which at these cadences is the whole fight), and only
the first `cap` procs grant anything. That is the refreshing rule's answer
wherever the chain does not break - which is the case under test. It is NOT a
general-purpose model: a unit whose cadence is slower than its duration needs
the real thing, not this.

WHEN TO RUN: before deciding whether to re-encode either bullet, and again
after, to check the re-encoding lands on the number measured here.

    python scripts/measure_buffrule_stack_refresh.py
    python scripts/measure_buffrule_stack_refresh.py --slug centi-signature
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import roster as roster_module  # noqa: E402
from app.deck_search import (  # noqa: E402
    BossProfile,
    deck_is_valid,
    evaluate_deck,
    feasible_orderings,
)
from app.effects import Effect  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.skill_rules._helpers import _rule  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

# Deckmates that carry no timed stack of their own, picked so the candidate is
# the only holder of HER burst tier - Rosanna is Burst 1 and Centi Burst 2, and
# a shellmate taking that seat changes how often she fires at all.
SHELL_BY_TIER = {
    1: ["crown", "red-hood", "helm", "mint"],
    2: ["liter", "red-hood", "helm", "mint"],
    3: ["liter", "crown", "helm", "mint"],
}
# Centi's second bullet only pays against an Electric boss (she buffs Iron
# allies' elemental advantage), so her case is scored against one.
CASES = {
    "centi-signature": {"cap": 10, "element": "Electric", "shape": "periodic"},
    "rosanna-signature": {"cap": 10, "element": "Water", "shape": "per_shot"},
}


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _deck(slug, boss):
    solo, excluded = load_roster([_nikke(slug)])
    if excluded or not solo:
        raise SystemExit(f"roster rejected {slug}: {excluded}")
    shell = [s for s in SHELL_BY_TIER[solo[0].burst_tier] if s != slug]
    specs, excluded = load_roster([_nikke(s) for s in shell + [slug]])
    if excluded:
        raise SystemExit(f"roster rejected: {excluded}")
    for ordering in feasible_orderings(specs):
        if deck_is_valid(ordering) and slug in {u.slug for u in ordering}:
            return ordering
    raise SystemExit(f"no feasible deck seating {slug}")


def _capped_permanent_rule(trigger, buffs, cap):
    """One permanent instance per proc, for the first `cap` procs."""
    seen = set()

    def action(context, caster_slug, time, registry):
        seen.add(time)
        if sorted(seen).index(time) + 1 > cap:
            return
        for stat, value, scope in buffs:
            registry.add(Effect(stat, value, scope, None, caster_slug), applied_at=time)

    return _rule(trigger, action, None)


def _centi_patch(cap):
    original = roster_module.get_periodic_rules

    def patched(slug, skill_values):
        spec = original(slug, skill_values)
        if slug != "centi-signature" or not spec:
            return spec
        discussion = skill_values["field_discussion"]
        fortification = skill_values["maintain_fortification"]
        buffs = [
            ("flat_atk",
             float(discussion["description_value_03"]) / 100 * skill_values["caster_atk"],
             "squad"),
            ("other_elemental_bonus",
             float(fortification["description_value_04"]) / 100, "element:Iron"),
        ]
        return [(interval, [_capped_permanent_rule("periodic", buffs, cap)])
                for interval, _rules in spec]

    roster_module.get_periodic_rules = patched
    return lambda: setattr(roster_module, "get_periodic_rules", original)


def _rosanna_patch(cap):
    original = roster_module.get_per_shot_rules

    def patched(slug, skill_values):
        rules = original(slug, skill_values)
        if slug != "rosanna-signature" or not rules:
            return rules
        capo = skill_values["capo_dei_capi"]
        buffs = [("atk_percent", float(capo["description_value_09"]) / 100, "self")]
        shots = int(float(capo["description_value_08"]))
        return [(n, mode,
                 [_capped_permanent_rule("per_shot", buffs, cap)] if n == shots else rs)
                for n, mode, rs in rules]

    roster_module.get_per_shot_rules = patched
    return lambda: setattr(roster_module, "get_per_shot_rules", original)


PATCHES = {"periodic": _centi_patch, "per_shot": _rosanna_patch}


def _score(slug, boss, case, refreshing):
    restore = PATCHES[case["shape"]](case["cap"]) if refreshing else None
    try:
        result = evaluate_deck(_deck(slug, boss), boss)
    finally:
        if restore:
            restore()
    her = sum(e["damage"] for e in result["damage_log"] if e["slug"] == slug)
    return her, result["total_damage"]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", choices=sorted(CASES), help="measure only this one")
    parser.add_argument("--enemy-def", type=float, default=8000.0)
    parser.add_argument("--duration", type=float, default=180.0)
    args = parser.parse_args()

    for slug in ([args.slug] if args.slug else sorted(CASES)):
        case = CASES[slug]
        boss = BossProfile(element=case["element"], core_hittable=True,
                           core_diameter_px=48.89, enemy_def=args.enemy_def,
                           fight_duration=args.duration)
        her_a, deck_a = _score(slug, boss, case, refreshing=False)
        her_b, deck_b = _score(slug, boss, case, refreshing=True)
        print(f"{slug}  (boss {case['element']}, DEF {args.enemy_def:g})")
        print(f"  current, instances overlap      her {her_a:>15,.0f}  deck {deck_a:>15,.0f}")
        print(f"  refreshing, capped at {case['cap']:<2}       her {her_b:>15,.0f}  "
              f"deck {deck_b:>15,.0f}")
        print(f"  -> her {(her_b/her_a-1)*100:+.2f}%   deck {(deck_b/deck_a-1)*100:+.2f}%\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
