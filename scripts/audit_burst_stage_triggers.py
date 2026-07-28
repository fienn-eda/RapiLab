"""Cross-check every encoded Nikke's "entering Burst Stage N" bullets against
the trigger its module actually wires.

WHY: "Activates when entering Burst Stage N" describes the STAGE, not the
caster - it fires in every cycle where ANY ally of that tier takes the slot.
Encoding it as `own_burst_activate` silently drops the cycles a different unit
of the same tier bursts, which in a two-B3 deck is roughly half of them. The
correct wiring is `ally_burst_activate` + `squad_engine.burst_stage_entered(N)`.
A 2026-07-27 sweep corrected five units this way but was done with a file-level
grep for one exact phrase; this script reads the skill text instead, so wording
variants ("Burst SKILL Stage 3") and units whose text was never checked are
covered.

WHEN TO USE: after encoding a Nikke, and whenever the burst-stage/full-burst
timing model changes. Also re-run after collecting fresh skill data - a
rephrased bullet upstream would otherwise sit unnoticed.

The script produces a CANDIDATE LIST, not a verdict. The 2026-07-27 sweep
already had one false positive (Maiden: Ice Rose, where the grep matched a
helper function name), so every SUSPECT row still needs a bullet-level read of
the module before anything is changed.

Usage:  python3 scripts/audit_burst_stage_triggers.py [--all]
        --all  also list the units whose text and wiring already agree
"""

import argparse
import glob
import json
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.skill_rules import registry  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")
SKILL_RULES = os.path.join(REPO, "backend", "app", "skill_rules")
LOOTANDWAIFUS = os.path.join(REPO, "data", "lootandwaifus")

BULLET = "■"
# The two phrasings seen in collected text. Ein's skill 1 reads "Burst SKILL
# Stage 3" where Mint's reads "Burst Stage 3" - a grep for either alone misses
# the other.
STAGE_PHRASE = re.compile(r"entering Burst(?: Skill)? Stage (\d)", re.IGNORECASE)
# Anything else mentioning a stage, so a third wording surfaces as a question
# rather than as silence.
LOOSE_PHRASE = re.compile(r"Burst(?: Skill)? Stage \d", re.IGNORECASE)

# Slugs whose skill text lives under a different file name than the slug.
DATA_ALIASES = {"privaty": "privaty-nikke"}

# Units whose stage bullet is genuinely not a SkillRule, checked by hand. They
# match the phrase and always will, so listing the reason here keeps a re-run
# from re-opening a settled question. Drop a unit from this list the moment its
# encoding changes - the reason is what is being trusted, not the slug.
CLEARED = {
    "maiden-ice-rose":
        "MP accrual runs through _resolve_squad_burst_cycle_resource, which "
        "already fills on ANY member's Burst Stage 1 (squad scope). The "
        "module's own_burst_activate rule is a different bullet - Blessings "
        "Upon You's 'when MP is used'.",
    "velvet":
        "Bullet Snatch only refills the 6000-round ammo pouch, listed under "
        "'Not modeled' - the pouch never binds, so the trigger has no "
        "damage consequence.",
    "soda-twinkling-bunny":
        "Beginner's Rewards is deferred whole: it extends Full Burst "
        "duration, which the engine holds as a single global constant.",
}


def base_slug(slug):
    """The unit `slug` is a variant of. Mode variants and favorite-item
    variants share their base unit's module and skill text."""
    for base, variants in registry.MODE_VARIANTS.items():
        if slug in variants:
            return base
    if slug.endswith("-signature"):
        return slug[: -len("-signature")]
    return slug


def data_slug(slug):
    """The file name under which `slug`'s collected text is stored."""
    return DATA_ALIASES.get(base_slug(slug), base_slug(slug))


def load_bullets(slug):
    """Bullets of every non-burst skill at max level, or None if this unit's
    text was never collected. Returns [(skill_index, skill_name, bullet)]."""
    path = os.path.join(LOOTANDWAIFUS, f"char_{data_slug(slug)}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        char = json.load(handle)
    out = []
    for index, skill in enumerate(char.get("skills") or []):
        levels = skill.get("levels") or []
        if not levels:
            continue
        for chunk in levels[-1].split(BULLET):
            chunk = chunk.strip()
            if chunk:
                out.append((index, skill.get("name") or f"skill[{index}]", chunk))
    return out


def module_slugs():
    """module path -> the slugs it encodes, from the `slug "..."` docstring
    convention with a filename fallback for the mode-variant modules."""
    found = {}
    for path in sorted(glob.glob(os.path.join(SKILL_RULES, "*.py"))):
        name = os.path.basename(path)
        if name in ("__init__.py", "registry.py", "_helpers.py"):
            continue
        with open(path, encoding="utf-8") as handle:
            head = handle.read(1500)
        slugs = set(re.findall(r'slug "([a-z0-9-]+)"', head))
        slugs.add(name[: -len(".py")].replace("_", "-"))
        found[path] = slugs
    return found


def owning_module(slug, modules):
    for path, slugs in modules.items():
        if slug in slugs:
            return path
    base = base_slug(slug)
    for path, slugs in modules.items():
        if base in slugs:
            return path
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Find 'entering Burst Stage N' bullets wired to own_burst_activate."
    )
    parser.add_argument(
        "--all", action="store_true",
        help="also list units whose text and wiring already agree",
    )
    args = parser.parse_args()

    modules = module_slugs()
    suspects, agreed, untextted, loose, cleared = [], [], [], [], []

    for slug in sorted(registry.ENCODED_SLUGS):
        bullets = load_bullets(slug)
        path = owning_module(slug, modules)
        if path is None:
            print(f"!! no module found for {slug} - the resolver needs a case")
            continue
        source = open(path, encoding="utf-8").read()
        wired = "burst_stage_entered" in source
        rel = os.path.relpath(path, REPO).replace("\\", "/")

        if bullets is None:
            untextted.append((slug, rel, wired))
            continue

        staged = [(i, n, b) for i, n, b in bullets if STAGE_PHRASE.search(b)]
        if not staged:
            odd = [(i, n, b) for i, n, b in bullets if LOOSE_PHRASE.search(b)]
            if odd:
                loose.append((slug, rel, odd))
            continue
        if wired:
            agreed.append((slug, rel, staged))
        elif slug in CLEARED:
            cleared.append((slug, rel))
        else:
            suspects.append((slug, rel, staged))

    print(f"{len(registry.ENCODED_SLUGS)} encoded slugs checked\n")

    print(f"== SUSPECT: stage text, but the module never calls burst_stage_entered ({len(suspects)}) ==")
    for slug, rel, staged in suspects:
        print(f"\n  {slug}   ({rel})")
        for index, name, bullet in staged:
            print(f"    skill[{index}] {name}")
            for line in bullet.splitlines():
                print(f"      | {line}")
    if not suspects:
        print("  (none)")

    print(f"\n== cleared by hand: stage text, but no SkillRule to fix ({len(cleared)}) ==")
    for slug, rel in cleared:
        print(f"\n  {slug}   ({rel})")
        for line in textwrap.wrap(CLEARED[slug], 74):
            print(f"    {line}")

    print(f"\n== UNVERIFIABLE: no collected skill text, read the module by hand ({len(untextted)}) ==")
    for slug, rel, wired in untextted:
        print(f"  {slug:<38} {rel}  burst_stage_entered={'yes' if wired else 'NO'}")

    if loose:
        print(f"\n== OTHER 'Burst Stage' wording, not the known phrase ({len(loose)}) ==")
        for slug, rel, odd in loose:
            print(f"\n  {slug}   ({rel})")
            for index, name, bullet in odd:
                print(f"    skill[{index}] {name}")
                for line in bullet.splitlines():
                    print(f"      | {line}")

    print(f"\n== text and wiring agree ({len(agreed)}) ==")
    if args.all:
        for slug, rel, staged in agreed:
            print(f"  {slug:<38} {rel}  ({len(staged)} stage bullet(s))")
    else:
        print("  " + ", ".join(slug for slug, _, _ in agreed) or "  (none)")

    return 1 if suspects else 0


if __name__ == "__main__":
    sys.exit(main())
