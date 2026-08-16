"""Put each skill's own "■ Activates ..." phrase next to the triggers its module wires.

WHY: the trigger is where an encoding goes wrong invisibly. Asuka: WILLE's
Emergency Repair reads "Activates when using Annihilation" - and Annihilation is
"After Annihilation State ends", i.e. burst + 9 sec - but three of its effects
were wired to her burst instant, dumping her magazine at the very moment her
Anti A.T. Field stacks were supposed to build (Fienn, 2026-08-16). Every value,
scope and arrow in that encoding was correct; only WHEN was wrong, so no test
and no other audit could see it.

`audit_burst_stage_triggers.py` covers exactly one phrase ("Burst Stage N").
This one is the general form: it prints every bullet's activation phrase beside
the set of triggers the module actually registers, so a human reads the pairing
once per unit. It cannot judge - a supporter whose text says "when entering Full
Burst" may legitimately be wired to `own_burst_activate` (the two coincide for a
Burst 3), and an always-on approximation legitimately reads `battle_start`
against a per-shot phrase. What it does is make the pairing visible.

It also flags DELAYED phrases - "when using <a named state/skill>" where that
name is defined elsewhere in the unit's own text as happening after something
ends - since that is the exact shape of the Asuka bug.

WHEN TO RUN: after encoding a Nikke, when reviewing an encoding, and after
collecting new character data.

Exit code is 0 - this is a checklist, not a gate.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.skill_rules import registry as skill_registry
from app.skill_values import DATA_DIR, load_character_data

MODULE_DIR = ROOT / "backend" / "app" / "skill_rules"

# Triggers a module can register, as they appear in source. Read off the
# catalog's trigger table (references/engine-capabilities.md) plus the two
# pseudo-triggers the per-shot / periodic machinery uses.
TRIGGER_NAMES = (
    "battle_start", "own_burst_activate", "ally_burst_activate",
    "full_burst_enter", "full_burst_end", "per_shot",
)

# Phrases that describe a moment LATER than the cast that starts it. A bullet
# carrying one of these must not be wired to the plain burst instant unless the
# module says why.
DELAY_MARKERS = (
    "after", "ends", "when using", "takes effect",
)


def _bullets(source, data_slug):
    """(array, index, skill name, activation phrase) for every ■ bullet."""
    data = load_character_data(source, data_slug)
    for array in ("skills", "dollskills"):
        for index, skill in enumerate(data.get(array) or []):
            name = skill.get("name", "?")
            if source == "dotgg":
                text = skill.get("description") or ""
            else:
                levels = skill.get("levels") or []
                text = levels[-1] if levels and isinstance(levels[-1], str) else ""
            for line in text.split("\n"):
                line = line.strip()
                if not line.startswith("■"):
                    continue
                phrase = re.sub(r"<[^>]+>", "", line[1:]).strip()
                yield array, index, name, phrase


def _read(source, data_slug):
    if source == "shiftypad":
        for fallback in ("lootandwaifus", "dotgg"):
            if (Path(DATA_DIR) / fallback / f"char_{data_slug}.json").exists():
                return list(_bullets(fallback, data_slug)), fallback
        return [], None
    try:
        return list(_bullets(source, data_slug)), source
    except FileNotFoundError:
        return [], None


def _module_triggers(slug):
    """Triggers registered anywhere in the slug's module, with their line numbers.

    Source-level rather than by building rules: a builder needs assembled skill
    values, and what the review wants to see is which triggers the module names
    at all - the same thing a reader would grep for.
    """
    module = MODULE_DIR / (slug.replace("-", "_") + ".py")
    if not module.exists():
        return None
    found = {}
    for number, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for name in TRIGGER_NAMES:
            if f'"{name}"' in line or f"'{name}'" in line:
                found.setdefault(name, []).append(number)
    return found


def _delayed(phrase):
    lowered = phrase.lower()
    return [marker for marker in DELAY_MARKERS if marker in lowered]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", help="one encoded slug instead of all")
    parser.add_argument("--delayed-only", action="store_true",
                        help="only bullets whose phrase names a later moment")
    args = parser.parse_args()

    slugs = sorted(skill_registry._BUILDERS)
    if args.slug:
        if args.slug not in slugs:
            parser.error(f"{args.slug} is not an encoded slug")
        slugs = [args.slug]

    unreadable = []
    for slug in slugs:
        manifest = skill_registry.get_skill_value_manifest(slug)
        bullets, source = _read(manifest["source"], manifest.get("data_slug", slug))
        if source is None:
            unreadable.append(slug)
            continue
        triggers = _module_triggers(slug)
        rows = [b for b in bullets if not args.delayed_only or _delayed(b[3])]
        if not rows:
            continue
        wired = "(module file not found - built elsewhere)" if triggers is None else (
            ", ".join(f"{name} x{len(lines)}" for name, lines in sorted(triggers.items()))
            or "(no trigger literal in module)")
        print(f"{slug}  [{source}]")
        print(f"    wired: {wired}")
        for array, index, name, phrase in rows:
            mark = "  <-- names a later moment" if _delayed(phrase) else ""
            print(f"    {array}[{index}] {name}: {phrase}{mark}")
        print()

    print(f"{len(slugs)} encoded slug(s) scanned")
    if unreadable:
        print("NOT SCANNED (no collected text): " + ", ".join(unreadable))
    return 0


if __name__ == "__main__":
    sys.exit(main())
