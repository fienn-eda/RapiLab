"""Print an encoded Nikke's max-level skill text the way an encoding review reads it.

WHY: auditing an encoding means putting each `SkillRule` next to the skill's own
words - the trigger phrase ("Activates when using Annihilation"), the arrow, the
scope line, the duration. The collected JSON is per-level and site-shaped
(dotgg keeps ONE template with `{description_value_NN}` placeholders plus a
value dict per level; lootandwaifus renders the numbers into the prose once per
level), so reading it raw costs more attention than the audit itself. This
prints, per skill: the cooldown, the max-level text, and - for dotgg - the slot
table beside the template, so a slot number in the module can be checked without
counting tokens by hand.

Engine-only build variants (`<slug>-signature`, `rapi-red-hood-b1`, the MODE_
VARIANTS candidates) read another character's file; the slug is resolved through
its registry manifest, so pass the ENCODED slug and the right file is opened.

WHEN TO RUN: reviewing or re-reviewing an encoding, and after collecting new
character data.

    python scripts/dump_skill_text.py liter crown
    python scripts/dump_skill_text.py --all --list      # every encoded slug, names only
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.skill_rules import registry as skill_registry
from app.skill_values import (DATA_DIR, assemble_skill_values,
                              extract_lootandwaifus_slots, load_character_data)


def _source_for(slug):
    """(source, data_slug) the encoding actually reads.

    ShiftyPad's normalized files are value slots with no prose, so a
    shiftypad-sourced unit falls back to its lootandwaifus file - the same place
    the encoding workflow gets its effect text from.
    """
    manifest = skill_registry.get_skill_value_manifest(slug)
    source, data_slug = manifest["source"], manifest.get("data_slug", slug)
    if source == "shiftypad":
        if (Path(DATA_DIR) / "lootandwaifus" / f"char_{data_slug}.json").exists():
            return "lootandwaifus", data_slug
        if (Path(DATA_DIR) / "dotgg" / f"char_{data_slug}.json").exists():
            return "dotgg", data_slug
    return source, data_slug


def dump(slug, show_slots=True):
    source, data_slug = _source_for(slug)
    try:
        data = load_character_data(source, data_slug)
    except FileNotFoundError as error:
        print(f"### {slug}: NO TEXT ({source}/{data_slug}): {error}\n")
        return False

    header = f"### {slug}  [{source}: {data_slug}]"
    meta = " ".join(
        f"{key}={data[key]}" for key in ("class", "weapon", "element", "burst")
        if data.get(key)
    )
    print(header + (f"  {meta}" if meta else ""))
    for array in ("skills", "dollskills"):
        for index, skill in enumerate(data.get(array) or []):
            name = skill.get("name", "?")
            cooldown = skill.get("cooldown")
            label = f"-- {array}[{index}] {name}"
            if cooldown:
                label += f"   (cooldown {cooldown})"
            print(label)
            levels = skill.get("levels") or []
            if source == "dotgg":
                print(skill.get("description") or "(no description)")
                if show_slots and levels and isinstance(levels[-1], dict):
                    slots = {k: v for k, v in levels[-1].items() if v not in ("", None)}
                    print("   slots: " + ", ".join(
                        f"{k.replace('description_value_', '_')}={v}" for k, v in slots.items()))
            else:
                text = levels[-1] if levels and isinstance(levels[-1], str) else "(no text)"
                print(text)
                if show_slots and isinstance(text, str) and text != "(no text)":
                    # The numbering the encoder must use. Counting by eye gets it
                    # wrong - the extractor skips numbers that are not value
                    # slots ("Activates once per battle"), so read it from here.
                    slots = extract_lootandwaifus_slots(text)
                    if slots:
                        print("   slots: " + ", ".join(
                            f"{k.replace('description_value_', '_')}={v}"
                            for k, v in slots.items()))
            print()
    if show_slots:
        _print_assembled(slug)
    print()
    return True


def _print_assembled(slug):
    """The values the BUILDER actually receives - manifest keys, drop_tokens and
    all - so a slot read in the module can be checked against a number instead of
    against a hand count of the prose."""
    manifest = skill_registry.get_skill_value_manifest(slug)
    keys = manifest.get("keys") or {}
    if not keys:
        return
    try:
        values = assemble_skill_values(
            slug, manifest, {"skill1": 10, "skill2": 10, "burst": 10})
    except Exception as error:                       # noqa: BLE001 - report, don't crash
        print(f"   (assembled values unavailable: {type(error).__name__}: {error})")
        return
    print("-- assembled (what the builder reads, skill level 10)")
    for key in keys:
        slots = values.get(key)
        if isinstance(slots, dict):
            print(f"   {key}: " + ", ".join(
                f"{k.replace('description_value_', '_')}={v}"
                for k, v in sorted(slots.items())))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slugs", nargs="*", help="encoded slug(s)")
    parser.add_argument("--all", action="store_true", help="every encoded slug")
    parser.add_argument("--list", action="store_true",
                        help="print slug -> character-file mapping only")
    parser.add_argument("--no-slots", action="store_true",
                        help="omit the dotgg slot table")
    args = parser.parse_args()

    encoded = sorted(skill_registry._BUILDERS)
    slugs = encoded if args.all else args.slugs
    if not slugs:
        parser.error("pass at least one slug, or --all")
    unknown = [s for s in slugs if s not in encoded]
    if unknown:
        parser.error(f"not encoded slug(s): {', '.join(unknown)}")

    if args.list:
        for slug in slugs:
            source, data_slug = _source_for(slug)
            print(f"{slug}\t{source}\t{data_slug}")
        return 0

    missing = 0
    for slug in slugs:
        if not dump(slug, show_slots=not args.no_slots):
            missing += 1
    if missing:
        print(f"{missing} slug(s) had no collected text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
