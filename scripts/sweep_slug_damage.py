"""Per-slug damage sweep: every encoded Nikke measured in a fixed deck shell.

Why: engine changes (a new buff kind, a fix to how effects stack) move damage
for reasons that unit tests don't quantify. This prints one comparable number
per encoded slug so a change can be A/B'd end-to-end instead of argued about.

Each slug is evaluated as the lone variable member of a fixed support shell, so
the only thing differing between rows is the unit under test. The shell is
chosen by the unit's own burst tier and holds as few units of that tier as the
deck rules allow - see SHELLS. Slugs that can't form a feasible deck are
reported as skipped.

**Tier-3 numbers taken before 2026-08-07 are not comparable to ones taken
after.** The tier-3 shell was `(2,2,1)` until then, a shape ALLOWED_SHAPES
rejects, so those rows measured decks the product cannot build. Fixing it moved
every tier-3 row (+20.6% to +94.9%, median +39.8%) and tiers 1 and 2 not at all.
A `--compare` spanning that date reads those tier-3 deltas as an engine change;
they are not one. Re-take the baseline.

Usage (any cwd):
    python3 scripts/sweep_slug_damage.py --out before.json
    # ...apply the engine change...
    python3 scripts/sweep_slug_damage.py --out after.json
    python3 scripts/sweep_slug_damage.py --compare before.json after.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models import UserNikkeState  # noqa: E402
from app.skill_rules.registry import ENCODED_SLUGS, character_map  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.deck_search import (  # noqa: E402
    BossProfile,
    deck_is_valid,
    evaluate_deck,
    feasible_orderings,
    never_full_bursts,
)

# One fixed shell per burst tier. A shell holds as few members of the tier it
# measures as the rules allow: only one unit per tier bursts each cycle, so a
# same-tier shell member can crowd the unit under test out of the rotation and
# its burst-triggered damage then measures as zero (Zwei, against a liter+volume
# shell, never bursted at all).
#
# For tiers 1 and 2 "as few as the rules allow" is none. For tier 3 it is ONE:
# every ALLOWED_SHAPES formation carries at least two Burst 3s, so a tier-3
# shell without one describes a deck the product cannot build. It did until
# 2026-08-07, and the cost was not theoretical - Diesel: Winter Sweets in
# Highlight skips the opening cycle by design, and with nobody to cover it the
# fight opened NO Full Burst at all and she measured at 163M against a real
# ~691M. `never_full_bursts` now catches that shape of failure; this shell stops
# producing it.
#
# The tier-3 partner is Helm because a shell should add as little of its own
# damage as possible: she is the lowest-output Burst 3 that is also a supporter,
# so she fills the seat and buffs the unit under test instead of drowning it.
# `measure` takes the best of every seat order, so the ordering that lets the
# unit under test take the seat whenever it is ready is the one that scores.
SHELLS = {
    1: ["crown", "blanc", "helm", "modernia"],       # 2x B2 + 2x B3 -> (1,2,2)
    2: ["liter", "volume", "helm", "modernia"],      # 2x B1 + 2x B3 -> (2,1,2)
    3: ["liter", "crown", "blanc", "helm"],          # B1 + 2x B2 + B3 -> (1,2,2)
}

# The Burst 3 the tier-3 shell seats, and the stand-ins that measure the
# partner itself (a deck holding a unit and its own other build is a character
# clash, so Helm's row cannot be measured against Helm).
#
# The overrides form a CYCLE rather than a pair pointing at each other: two
# units that stood in for one another would put both rows on the identical five
# units, and two rows that cannot differ cannot tell you which of them an engine
# change moved. Modernia needs an entry for the same reason one step further
# out - she also sits in the tier-1 and tier-2 shells, so measuring her against
# the default partner would rebuild Liter's tier-1 deck exactly. Rows measured
# against a stand-in still are not strictly comparable to the rest: whoever
# stood in dealt their own damage into the total.
#
# `check_shells_are_distinct` proves the table has no such pair rather than
# leaving it to whoever edits it next.
TIER3_PARTNER = "helm"
TIER3_PARTNER_OVERRIDES = {
    "helm": "maxwell",
    "maxwell": "modernia",
    "modernia": "snow-white",
}

BOSS = BossProfile(element="Water", fight_duration=180.0)


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _tier_of(slug):
    specs, excluded = load_roster([_nikke(slug)])
    return None if excluded or not specs else specs[0].burst_tier


def _shell_for(slug, tier):
    """This slug's shell.

    Tier 3 is the one that needs a Burst-3 partner (see SHELLS), so it is also
    the one where the shell can collide with the unit under test. The collision
    is by CHARACTER, not slug: measuring `helm-signature` against a shell
    holding base Helm is a deck the search rejects outright, and the row would
    come back as "no feasible deck" rather than as a number."""
    shell = SHELLS.get(tier)
    if shell is None:
        return None
    if tier != 3:
        return None if slug in shell else shell
    character = character_map().get(slug, slug)
    partner = TIER3_PARTNER_OVERRIDES.get(character, TIER3_PARTNER)
    return [partner if member == TIER3_PARTNER else member for member in shell]


def measure(slug):
    """Best total damage over the feasible orderings of (tier-matched shell +
    slug), or None if the slug can't be measured here.

    Two things make it unmeasurable beyond a missing tier. The deck must be one
    the product would actually build (`deck_is_valid`) - a shell that forms an
    illegal shape measures something no player can field, which is how the
    tier-3 shell went two months describing a one-Burst-3 deck. And the fight
    must open a Full Burst at all: a deck that never does still totals its
    normal attacks, so it comes back as a number rather than as a complaint
    (Diesel: Winter Sweets in Highlight read 163M against a real ~691M)."""
    tier = _tier_of(slug)
    shell = _shell_for(slug, tier)
    if shell is None:
        return None  # unknown tier, or the slug is itself a shell member
    specs, excluded = load_roster([_nikke(s) for s in shell + [slug]])
    if excluded:
        return None
    best = None
    for ordering in feasible_orderings(specs):
        # Both checks are per ORDERING, not per roster. `load_roster` hands back
        # a candidate POOL, which can hold more than five specs - Rapi: Red Hood
        # expands into her Burst-3 build and her Burst-1 one, and `feasible_
        # orderings` then picks five. That also means an ordering can drop the
        # very unit this row is about, and its total would still compete for the
        # max, so the row would silently be measuring a deck without its own
        # subject.
        if slug not in {unit.slug for unit in ordering} or not deck_is_valid(ordering):
            continue
        result = evaluate_deck(ordering, BOSS)
        if never_full_bursts(result):
            return None
        if best is None or result["total_damage"] > best:
            best = result["total_damage"]
    return best


def check_shells_are_distinct():
    """[(slug, slug, deck)] for every pair of slugs this sweep would measure on
    the SAME five units - which makes their two rows move together forever, so
    neither can ever say which unit an engine change touched.

    It is easy to build one by accident: the shells share a small vocabulary
    across tiers, so a tier-3 shell that gains a Burst-1 rebuilds that Burst-1's
    own tier-1 deck exactly (liter and modernia, first time round). Checked
    rather than reasoned about, and printed by the sweep."""
    decks = {}
    for slug in ENCODED_SLUGS:
        try:
            shell = _shell_for(slug, _tier_of(slug))
        except Exception:
            continue
        if shell is None:
            continue
        decks[slug] = frozenset(shell + [slug])
    by_deck = {}
    clashes = []
    for slug, deck in sorted(decks.items()):
        if deck in by_deck:
            clashes.append((by_deck[deck], slug, sorted(deck)))
        else:
            by_deck[deck] = slug
    return clashes


def run_sweep():
    rows, skipped = {}, []
    for slug in ENCODED_SLUGS:
        try:
            value = measure(slug)
        except Exception as exc:  # a broken encoding must not abort the sweep
            skipped.append(f"{slug}: {type(exc).__name__}: {exc}")
            continue
        if value is None:
            skipped.append(f"{slug}: no feasible deck in the shell")
        else:
            rows[slug] = value
    return rows, skipped


def compare(before_path, after_path):
    before = json.loads(Path(before_path).read_text(encoding="utf-8"))["damage"]
    after = json.loads(Path(after_path).read_text(encoding="utf-8"))["damage"]
    deltas = []
    for slug, new in after.items():
        old = before.get(slug)
        if old is None:
            print(f"  NEW    {slug}: {new:,.0f}")
            continue
        if old == new:
            continue
        deltas.append((100.0 * (new - old) / old, slug, old, new))
    deltas.sort(reverse=True)
    unchanged = len(after) - len(deltas)
    print(f"{len(deltas)} of {len(after)} slugs changed ({unchanged} unchanged)")
    for pct, slug, old, new in deltas:
        print(f"  {pct:+7.2f}%  {slug}: {old:,.0f} -> {new:,.0f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", help="write sweep results to this JSON file")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"),
                        help="diff two sweep files instead of running a sweep")
    args = parser.parse_args()

    if args.compare:
        compare(*args.compare)
        return

    clashes = check_shells_are_distinct()
    for first, second, deck in clashes:
        print(f"  SHELL CLASH  {first} and {second} are the same deck: {deck}")
    if clashes:
        print()

    rows, skipped = run_sweep()
    for slug, value in sorted(rows.items()):
        print(f"  {value:>16,.0f}  {slug}")
    print(f"\nmeasured {len(rows)} slugs, skipped {len(skipped)}")
    for note in skipped:
        print(f"  SKIP {note}")
    if clashes:
        print(f"  {len(clashes)} pair(s) share a deck - those rows can never differ")
    if args.out:
        Path(args.out).write_text(
            json.dumps({"shells": SHELLS, "damage": rows, "skipped": skipped}, indent=2),
            encoding="utf-8",
        )
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
