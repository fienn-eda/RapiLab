"""What Centi's and Rosanna: Signature's stacks cost when read as separate timers.

WHY THESE TWO: both held a "stacks up to N ... lasts for D sec" buff as
OVERLAPPING `buff_rule` instances rather than a capped counter, so
`audit_stack_lifetime_refresh.py`'s engine half - which reads resource counts -
could not see them at all. They were also the two largest, and both were
written off with the same sentence:

  Centi:    "Neither stack cap binds: the cycle is ~5.7 sec against 8- and
             10-sec buffs, so at most 2 of the 10 stacks are ever live."
  Rosanna:  "about 2-3 instances overlap at steady state ... the skill text's
             10-stack cap is NOT reachable from this source alone."

That is per-stack-expiry arithmetic. The duration is ONE timer the whole stack
shares, restarted by every new stack (the Raven ruling, Fienn 2026-07-17), so a
cadence FASTER than D never lets the stack lapse and the count climbs to the
cap. Centi procs every 5.96 sec against 8; Rosanna every ~15 against 30.
Neither chain can break, and Fienn confirmed in game (2026-08-17) that both
reach their caps. Both are now `ResourceSpec` counters.

So this script scores what the OLD reading was worth, by putting the
overlapping instances back and taking the counter away:

  current       the capped counter both units now carry
  per-stack     the same bullets as independent D-second instances

WHEN TO RUN: as a guard - if either encoding drifts back toward independent
instances, this is the number that moves. Re-run it after touching either
unit's stacks.

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
from app.models import UserNikkeState  # noqa: E402
from app.skill_rules._helpers import buff_rule  # noqa: E402
from app.skill_rules.centi import field_discussion_effective_cooldown  # noqa: E402
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
    "centi-signature": {"element": "Electric"},
    "rosanna-signature": {"element": "Water"},
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


def _without_resource(slug):
    """Take the counter away, so only the restored instances remain."""
    original = roster_module.get_resource_specs

    def patched(spec_slug, skill_values):
        if spec_slug == slug:
            return None
        return original(spec_slug, skill_values)

    roster_module.get_resource_specs = patched
    return lambda: setattr(roster_module, "get_resource_specs", original)


def _centi_old_model():
    """Her two Skill-2 buffs as independent 8- and 10-second instances."""
    original = roster_module.get_periodic_rules

    def patched(slug, skill_values):
        if slug != "centi-signature":
            return original(slug, skill_values)
        discussion = skill_values["field_discussion"]
        fortification = skill_values["maintain_fortification"]
        return [(
            field_discussion_effective_cooldown(skill_values),
            [buff_rule("periodic", [
                ("flat_atk",
                 float(discussion["description_value_03"]) / 100 * skill_values["caster_atk"],
                 "squad", float(discussion["description_value_05"])),
                ("other_elemental_bonus",
                 float(fortification["description_value_04"]) / 100, "element:Iron",
                 float(fortification["description_value_06"])),
            ])],
        )]

    roster_module.get_periodic_rules = patched
    return lambda: setattr(roster_module, "get_periodic_rules", original)


def _rosanna_old_model():
    """Frenzy as independent 30-second instances, every 500 shots."""
    original = roster_module.get_per_shot_rules

    def patched(slug, skill_values):
        rules = original(slug, skill_values)
        if slug != "rosanna-signature":
            return rules
        capo = skill_values["capo_dei_capi"]
        return list(rules or []) + [(
            int(float(capo["description_value_08"])), "every",
            [buff_rule("per_shot", [(
                "atk_percent", float(capo["description_value_09"]) / 100, "self",
                float(capo["description_value_11"]),
            )])],
        )]

    roster_module.get_per_shot_rules = patched
    return lambda: setattr(roster_module, "get_per_shot_rules", original)


OLD_MODELS = {"centi-signature": _centi_old_model, "rosanna-signature": _rosanna_old_model}


def _score(slug, boss, per_stack_expiry):
    restores = []
    if per_stack_expiry:
        restores = [_without_resource(slug), OLD_MODELS[slug]()]
    try:
        result = evaluate_deck(_deck(slug, boss), boss)
    finally:
        for restore in reversed(restores):
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
        her_now, deck_now = _score(slug, boss, per_stack_expiry=False)
        her_old, deck_old = _score(slug, boss, per_stack_expiry=True)
        print(f"{slug}  (boss {case['element']}, DEF {args.enemy_def:g})")
        print(f"  current, one capped counter     her {her_now:>15,.0f}  deck {deck_now:>15,.0f}")
        print(f"  per-stack expiry (old reading)  her {her_old:>15,.0f}  deck {deck_old:>15,.0f}")
        print(f"  -> the correction is worth her {(her_now/her_old-1)*100:+.2f}%   "
              f"deck {(deck_now/deck_old-1)*100:+.2f}%\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
