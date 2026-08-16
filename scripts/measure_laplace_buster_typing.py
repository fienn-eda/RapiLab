"""What Laplace: Signature's Buster typing is worth, measured against a boss
that can actually show it.

Why this is not a `sweep_slug_damage.py` row: that sweep's boss is
`BossProfile(element="Water", fight_duration=180.0)`, i.e. `enemy_def=0` and no
core. True damage's whole effect is ignoring DEF, so at DEF 0 it is worth
exactly nothing, and the type-gated buckets are worth nothing unless a deckmate
supplies them. The sweep reports "0 of 101 slugs changed" for this change and
that reading is correct-but-blind - see docs/insights.md, the same trap that
nearly closed the hit-rate work as "no effect".

So: a DEF-carrying boss, and a deck holding a Projectile Explosion buffer.

Two independent engine facts are being measured, and the script separates them
by neutralising each in turn:

  A (old engine)  gate forced open  + delivery bucket suppressed
  B               gate live         + delivery bucket suppressed
  C (current)     gate live         + delivery bucket live

  B - A  = the Hero Vision gate on the segment's true typing
  C - B  = the weapon's delivery bucket surviving the true typing

Usage (any cwd):
    python scripts/measure_laplace_buster_typing.py
    python scripts/measure_laplace_buster_typing.py --enemy-def 8000
    python scripts/measure_laplace_buster_typing.py --deck mint liter crown helm
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import raid_simulator  # noqa: E402
from app.deck_search import (  # noqa: E402
    BossProfile,
    deck_is_valid,
    evaluate_deck,
    feasible_orderings,
)
from app.models import UserNikkeState  # noqa: E402
from app.skill_rules import laplace_signature  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

SLUG = "laplace-signature"
# Mint is the Projectile Explosion buffer here on purpose: her own docstring
# says the buff is "consumed by every RL ally's normal attacks", which is
# exactly the claim under test.
DEFAULT_SHELL = ["mint", "liter", "crown", "helm"]


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _best(shell, boss):
    """Best total over the feasible orderings, plus that ordering's damage log."""
    specs, excluded = load_roster([_nikke(s) for s in shell + [SLUG]])
    if excluded:
        raise SystemExit(f"roster rejected: {excluded}")
    best = None
    for ordering in feasible_orderings(specs):
        if not deck_is_valid(ordering) or SLUG not in {u.slug for u in ordering}:
            continue
        result = evaluate_deck(ordering, boss)
        if best is None or result["total_damage"] > best["total_damage"]:
            best = result
    if best is None:
        raise SystemExit(f"no feasible deck for {shell + [SLUG]}")
    return best


def _her_damage(result):
    return sum(e["damage"] for e in result["damage_log"] if e["slug"] == SLUG)


def _tick_types(result):
    counts = {}
    for e in result["damage_log"]:
        if e["slug"] == SLUG and e["source"] == "normal_attack":
            counts[e["damage_type"]] = counts.get(e["damage_type"], 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--enemy-def", type=float, default=8000.0,
                        help="boss DEF; true damage is worth 0 at 0 (default: 8000)")
    parser.add_argument("--deck", nargs="+", default=DEFAULT_SHELL,
                        help=f"the four shell members (default: {' '.join(DEFAULT_SHELL)})")
    args = parser.parse_args()

    boss = BossProfile(element="Water", fight_duration=180.0, enemy_def=args.enemy_def)

    real_gate = laplace_signature.hero_vision_max_stack_gate
    real_delivery = raid_simulator.weapon_delivery_type

    def gate_forced_open(values):
        name, cap, lifetime, _fn = real_gate(values)
        return (name, cap, lifetime, lambda count: 1.0)

    runs = {}
    try:
        # A - the engine before this change.
        laplace_signature.hero_vision_max_stack_gate = gate_forced_open
        raid_simulator.weapon_delivery_type = lambda weapon_type: "attack"
        runs["A old engine        "] = _best(args.deck, boss)

        # B - the gate alone.
        laplace_signature.hero_vision_max_stack_gate = real_gate
        runs["B + Hero Vision gate"] = _best(args.deck, boss)

        # C - plus the delivery bucket.
        raid_simulator.weapon_delivery_type = real_delivery
        runs["C + delivery bucket "] = _best(args.deck, boss)
    finally:
        laplace_signature.hero_vision_max_stack_gate = real_gate
        raid_simulator.weapon_delivery_type = real_delivery

    print(f"deck: {' + '.join(args.deck)} + {SLUG}")
    print(f"boss: DEF {args.enemy_def:,.0f}, 180s, no core\n")

    base_her = _her_damage(runs["A old engine        "])
    base_total = runs["A old engine        "]["total_damage"]
    print(f"{'':22} {'her damage':>16} {'vs A':>9} {'deck total':>16} {'vs A':>9}")
    for label, result in runs.items():
        her = _her_damage(result)
        total = result["total_damage"]
        print(f"{label:22} {her:16,.0f} {her / base_her - 1:+8.2%} "
              f"{total:16,.0f} {total / base_total - 1:+8.2%}")

    print(f"\nher normal-attack ticks by type (current engine): "
          f"{_tick_types(runs['C + delivery bucket '])}")


if __name__ == "__main__":
    main()
