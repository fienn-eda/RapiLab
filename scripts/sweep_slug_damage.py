"""Per-slug damage sweep: every encoded Nikke measured in one fixed deck shell.

Why: engine changes (a new buff kind, a fix to how effects stack) move damage
for reasons that unit tests don't quantify. This prints one comparable number
per encoded slug so a change can be A/B'd end-to-end instead of argued about.

Each slug is evaluated as the lone variable member of a fixed support shell, so
the only thing differing between rows is the unit under test. Slugs that can't
form a feasible deck in the shell (burst-tier clashes) are reported as skipped.

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
from app.skill_rules.registry import ENCODED_SLUGS  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402

# Fixed support shell: four units already covering burst tiers 1/2/3, so the
# fifth seat accepts a unit of ANY tier and every encoded slug is measurable.
# The shell's own output is constant across rows.
SHELL_SLUGS = ["liter", "volume", "crown", "helm"]
BOSS = BossProfile(element="Water", fight_duration=180.0)


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def measure(slug):
    """Best total damage over the feasible orderings of shell + slug, or None
    if the slug can't form a deck here."""
    states = [_nikke(s) for s in SHELL_SLUGS + [slug] if s != slug or s not in SHELL_SLUGS]
    if slug in SHELL_SLUGS:
        return None  # shell members aren't measurable against their own shell
    specs, excluded = load_roster(states)
    if excluded:
        return None
    best = None
    for ordering in feasible_orderings(specs):
        total = evaluate_deck(ordering, BOSS)["total_damage"]
        if best is None or total > best:
            best = total
    return best


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

    rows, skipped = run_sweep()
    for slug, value in sorted(rows.items()):
        print(f"  {value:>16,.0f}  {slug}")
    print(f"\nmeasured {len(rows)} slugs, skipped {len(skipped)}")
    for note in skipped:
        print(f"  SKIP {note}")
    if args.out:
        Path(args.out).write_text(
            json.dumps({"shell": SHELL_SLUGS, "damage": rows, "skipped": skipped}, indent=2),
            encoding="utf-8",
        )
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
