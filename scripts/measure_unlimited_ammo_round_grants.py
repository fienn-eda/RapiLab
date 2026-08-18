"""How much does [Unlimited Ammunition] freezing "for N round(s)" buffs move damage?

Why: the status is a correctness fix (a round-count buff counts ammunition
spent, and a unit under [Unlimited Ammunition] spends none - Fienn, in-game
2026-08-18), but "correct" says nothing about size. Only two encoded units grant
a round buff ACROSS units - Miranda (top-1 ATK ally) and Zwei (squad) - and only
four can receive it under the status - Grave, Nayuta, Moran, Modernia. This
scores exactly those pairings with the status on and off, so the change has a
number instead of an argument.

The A/B toggles the ENGINE INPUT (`unlimited_ammo_durations`), not the effects
it produces, so both runs go through the same code path the product uses.

Reading the zeros - most of the table is +0.00%, and each zero has its own
reason. They are the point of running this rather than assuming:

- base `miranda` grants no round buff at all; only her Favorite Item build does.
- `modernia` is played burst-ABSTAINING, so she opens no window to freeze in.
- `zwei` grants Pierce DAMAGE, which pays nothing to a recipient with no Pierce.
  Grave is the one receiver who gains Pierce (her own burst, same window), which
  is why hers is the only Zwei row that moves.
- Miranda + Grave is zero for the opposite reason: Grave's own burst already
  puts her at the 100% crit-rate cap for exactly the 10 sec her window lasts, so
  a longer-lived Critical Rate buff on her buys nothing there.

The shell gives every unit the same base ATK, so Miranda's "highest final ATK"
target is decided by buffs and deck order rather than by a real roster's stat
spread. Read a row as the size of the effect WHEN the grant lands on that
receiver, not as a forecast for any particular player's deck.

Usage (any cwd):
    python3 scripts/measure_unlimited_ammo_round_grants.py
    python3 scripts/measure_unlimited_ammo_round_grants.py --fight-duration 180
"""
import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import roster as roster_module  # noqa: E402
from app.deck_search import (  # noqa: E402
    BossProfile,
    deck_is_valid,
    evaluate_deck,
    feasible_orderings,
    never_full_bursts,
)
from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

# Every encoded unit that grants a "for N round(s)" buff to somebody OTHER than
# itself. A self-scoped round buff cannot meet this bug: none of the four
# unlimited-ammo units has one.
GRANTERS = ["miranda", "miranda-signature", "zwei", "zwei-signature"]
# Every encoded unit who can be under [Unlimited Ammunition] when one lands.
RECEIVERS = ["grave", "nayuta", "moran", "modernia"]
# Filler pool - units that grant no round buff and have no unlimited ammo of
# their own, spanning all three burst tiers. Three of them are picked per
# pairing, because which three make a LEGAL SHAPE depends on the two units
# under test (a Burst-1 granter beside Burst-1 Moran needs a different pair
# than one beside Burst-3 Modernia). A fixed trio silently reported "no
# feasible deck" for half the table.
FILLER_POOL = ["liter", "volume", "crown", "blanc", "helm", "snow-white"]


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _best_total(slugs, boss, status_on):
    """Best total damage over this composition's feasible seat orders, with the
    unlimited-ammo status either wired as the product wires it or withheld."""
    original = roster_module.get_unlimited_ammo_duration
    if not status_on:
        roster_module.get_unlimited_ammo_duration = lambda slug, values: None
    try:
        specs, excluded = load_roster([_nikke(s) for s in slugs])
        if excluded:
            return None
        best = None
        for ordering in feasible_orderings(specs):
            if {u.slug for u in ordering} != set(slugs) or not deck_is_valid(ordering):
                continue
            result = evaluate_deck(ordering, boss)
            if never_full_bursts(result):
                continue
            if best is None or result["total_damage"] > best:
                best = result["total_damage"]
        return best
    finally:
        roster_module.get_unlimited_ammo_duration = original


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fight-duration", type=float, default=180.0)
    parser.add_argument("--element", default="Water")
    args = parser.parse_args()
    boss = BossProfile(element=args.element, fight_duration=args.fight_duration)

    print(f"{'deck':<58} {'status off':>16} {'status on':>16} {'delta':>9}")
    rows = 0
    for granter, receiver in itertools.product(GRANTERS, RECEIVERS):
        off = on = slugs = None
        for fillers in itertools.combinations(FILLER_POOL, 3):
            candidate = [granter, receiver, *fillers]
            if len(set(candidate)) != 5:
                continue
            candidate_off = _best_total(candidate, boss, status_on=False)
            if not candidate_off:
                continue
            # Several filler trios are legal; the one that scores highest is the
            # deck a player would actually field, so it is the one that decides
            # the pairing's number.
            if off is None or candidate_off > off:
                off = candidate_off
                on = _best_total(candidate, boss, status_on=True)
                slugs = candidate
        if off is None:
            print(f"{granter + ' + ' + receiver:<58} {'no feasible deck':>16}")
            continue
        rows += 1
        label = f"{granter} + {receiver}  ({', '.join(s for s in slugs[2:])})"
        print(f"{label:<58} {off:>16,.0f} {on:>16,.0f} "
              f"{(on / off - 1) * 100:>+8.2f}%")
    if not rows:
        print("no pairing produced a feasible deck - check FILLERS against the shape rules")


if __name__ == "__main__":
    main()
