"""Derive which encoded Nikkes provide healing, from their own skill text.

Why: Crown's Royal Attire grants the squad Attack Damage "when recovery takes
effect" - triggered by ANY ally's healing, not just her own (Fienn,
2026-07-20). The engine has no heal event, so the deck-level question is only
"is there a healer here at all", which this answers from data rather than from
someone's memory of 77 kits.

When to use: after encoding a new Nikke, or when refreshing the collected
data, to regenerate `_HEAL_PROVIDER_SLUGS` in backend/app/skill_rules/registry.py.
Prints the slug list plus the matching line for each, so the classification can
be eyeballed rather than trusted blindly.

Usage:
    python scripts/find_heal_providers.py            # report all encoded slugs
    python scripts/find_heal_providers.py --quiet    # just the slug list
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest  # noqa: E402
from app.skill_values import load_character_data  # noqa: E402

# Phrases NIKKE uses for restoring HP. "Incoming healing up" is deliberately
# NOT here: buffing someone else's healing does not itself heal anyone.
HEAL_PATTERNS = [
    re.compile(r"Recovers?\b[^.]*\bHP\b", re.I),
    re.compile(r"\bRestores?\b[^.]*\bHP\b", re.I),
    re.compile(r"\bHeals?\b[^.]*\bHP\b", re.I),
]

# Cover HP is the crouching cover's own health, not a unit's - restoring it is
# not a unit "receiving recovery", so it does not arm Crown's Royal Attire.
COVER_ONLY = re.compile(r"\bCover(?:'s)?\s+HP\b", re.I)


def heal_lines(slug):
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        return None
    data_slug = manifest.get("data_slug", slug)
    for source in ("lootandwaifus", "dotgg"):
        try:
            data = load_character_data(source, data_slug)
        except (FileNotFoundError, KeyError):
            continue
        arrays = [key for key in ("skills", "dollskills") if data.get(key)]
        found = []
        for key in arrays:
            for skill in data[key]:
                levels = skill.get("levels") or []
                if not levels:
                    continue
                last = levels[-1]
                text = last if isinstance(last, str) else " ".join(
                    str(v) for v in last.values())
                if source == "dotgg" and not isinstance(last, str):
                    text = skill.get("description", "")
                for pattern in HEAL_PATTERNS:
                    match = pattern.search(text)
                    if match and not COVER_ONLY.search(match.group(0)):
                        found.append((key, skill.get("name"), match.group(0).strip()))
                        break
        if found:
            return found
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiet", action="store_true", help="print only the slug list")
    args = parser.parse_args()

    healers, unreadable = [], []
    for slug in sorted(ENCODED_SLUGS):
        found = heal_lines(slug)
        if found is None:
            unreadable.append(slug)
            continue
        if found:
            healers.append((slug, found))

    if not args.quiet:
        for slug, found in healers:
            print(f"{slug}")
            for array, name, line in found:
                print(f"    [{array}] {name}: {line[:90]}")
        if unreadable:
            print(f"\nNO MANIFEST / DATA ({len(unreadable)}): {', '.join(unreadable)}",
                  file=sys.stderr)
        print()

    print("_HEAL_PROVIDER_SLUGS = {")
    for slug, _ in healers:
        print(f'    "{slug}",')
    print("}")
    print(f"\n# {len(healers)} of {len(ENCODED_SLUGS)} encoded slugs", file=sys.stderr)


if __name__ == "__main__":
    main()
