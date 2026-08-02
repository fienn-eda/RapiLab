"""Report which encoded Nikkes heal and which place shields, from skill text.

Why: two bullets key off events the engine does not model - Crown's Royal Attire
arms "when recovery takes effect" (ANY ally's healing, Fienn 2026-07-20) and
Flora's Favorite Item Iris bullet arms "when a shield is placed in front of this
unit". Neither can ask more than "is there someone in this deck who does that",
and that roster belongs in data rather than in someone's memory of 90 kits.

The classification itself lives in `app.skill_rules.provider_scan`, so
`tests/test_provider_lists_match_data.py` checks the committed constants against
the SAME logic this prints - a script that re-implements the rule produces wrong
numbers with no error, which has happened twice in this repo.

When to use: after encoding a new Nikke, or after refreshing collected data. The
test fails on its own when a constant needs a new entry; this is what shows WHY,
with the matching line per slug so a classification can be eyeballed.

Usage:
    python scripts/find_heal_providers.py            # both lists, with evidence
    python scripts/find_heal_providers.py --quiet    # just the slug sets
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.skill_rules._helpers import (  # noqa: E402
    ELEMENT_GATED_SHIELD_SLUGS,
    HEAL_PROVIDER_SLUGS,
    SHIELD_PROVIDER_SLUGS,
)
from app.skill_rules.provider_scan import (  # noqa: E402
    COVER_ONLY,
    HEAL_PATTERNS,
    SHIELD_PATTERNS,
    matching_lines,
    unreadable_slugs,
)
from app.skill_rules.registry import ENCODED_SLUGS  # noqa: E402


def _collect(patterns, exclude=None):
    rows = []
    for slug in sorted(ENCODED_SLUGS):
        found = matching_lines(slug, patterns, exclude=exclude)
        if found:
            rows.append((slug, found))
    return rows


def _report(title, rows, committed, quiet):
    if not quiet:
        print(f"\n===== {title} =====")
        for slug, found in rows:
            print(slug)
            for array, name, line in found:
                print(f"    [{array}] {name}: {line[:90]}")

    derived = {slug for slug, _ in rows}
    print(f"\n# {title}: {len(derived)} of {len(ENCODED_SLUGS)} encoded slugs")
    print("{")
    for slug in sorted(derived):
        print(f'    "{slug}",')
    print("}")

    missing = sorted(derived - committed)
    extra = sorted(committed - derived - unreadable_slugs())
    if missing:
        print(f"MISSING from the committed constant: {', '.join(missing)}", file=sys.stderr)
    if extra:
        print(f"COMMITTED but not found in data: {', '.join(extra)}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiet", action="store_true", help="print only the slug sets")
    args = parser.parse_args()

    _report("heal providers", _collect(HEAL_PATTERNS, exclude=COVER_ONLY),
            HEAL_PROVIDER_SLUGS, args.quiet)
    _report("shield providers", _collect(SHIELD_PATTERNS),
            SHIELD_PROVIDER_SLUGS | ELEMENT_GATED_SHIELD_SLUGS, args.quiet)

    unreadable = sorted(unreadable_slugs())
    if unreadable:
        print(f"\nNO MANIFEST / DATA ({len(unreadable)}): {', '.join(unreadable)}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
