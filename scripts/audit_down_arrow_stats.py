"""List every `▼` bullet in the collected skill text, per encoded Nikke.

WHY: a skill's value slot carries only the NUMBER. "Max Ammunition Capacity ▲
73.92%" and "▼ 73.92%" reach the encoder as the same `73.92`, so the direction
lives in the arrow and nowhere else - and an encoding that adds where the text
subtracts passes every slot-mapping check, including its own tests. Anis:
Sparkling Summer read +73.92% Max Ammo (magazine 5 -> 9) where the text cuts her
to 1 round, inverting the mechanic her whole kit is built on; Modernia read
+5.04% per stack the same way. Privaty's EX Magazine, same stat and same arrow,
was encoded as a negative all along - so the data supports getting it right.

The audit cannot judge. `Cooldown of Burst Skill ▼` is a reduction the engine
models as a POSITIVE `burst_cooldown_reduction_sec`, and an enemy `DEF ▼` is a
negative `enemy_def_percent`. What it does is put every arrow in front of you
with its unit, so each one gets read against the encoding once.

WHEN TO RUN: after encoding a Nikke, and after collecting new character data.
Use `--stat` to re-check one stat across the roster when a misread turns up.

Exit code is 0 - this is a checklist, not a gate.
"""
import argparse
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.skill_rules import registry as skill_registry
from app.skill_values import DATA_DIR, load_character_data

DOWN = "▼"


def _texts(source, data_slug):
    """(skill array, index, name, text) for each skill's max-level description.

    dotgg keeps ONE `description` template per skill with `{description_value_NN}`
    placeholders, which is better than a rendered number: the arrow arrives
    already paired with the slot name the encoding reads. lootandwaifus renders
    per level, so the last level is the max-level text. shiftypad's normalized
    files are value slots with no prose at all - see `_read`.
    """
    data = load_character_data(source, data_slug)
    for array in ("skills", "dollskills"):
        for index, skill in enumerate(data.get(array) or []):
            name = skill.get("name", "?")
            if source == "dotgg":
                text = skill.get("description") or ""
            else:
                levels = skill.get("levels") or []
                text = levels[-1] if levels and isinstance(levels[-1], str) else ""
            if text:
                yield array, index, name, text


def _read(source, data_slug):
    """Max-level text for a unit, plus why it is missing when it is.

    shiftypad's normalized output carries no prose, so a shiftypad-sourced unit
    is read from its lootandwaifus file when one was collected - the same place
    the encoding workflow gets its effect text.
    """
    if source == "shiftypad":
        if (Path(DATA_DIR) / "lootandwaifus" / f"char_{data_slug}.json").exists():
            return list(_texts("lootandwaifus", data_slug)), None
        return [], "shiftypad's normalized file carries no prose, and no lootandwaifus text was collected"
    try:
        return list(_texts(source, data_slug)), None
    except FileNotFoundError as error:
        return [], f"{type(error).__name__}: {error}"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--slug", help="audit one encoded slug instead of all of them")
    parser.add_argument("--stat", help="only bullets whose stat name contains this "
                                       "(case-insensitive), e.g. 'Ammunition'")
    args = parser.parse_args()

    slugs = sorted(skill_registry._BUILDERS)
    if args.slug:
        if args.slug not in slugs:
            parser.error(f"{args.slug} is not an encoded slug")
        slugs = [args.slug]

    # Engine-only build variants read another character's file, so group by the
    # source they actually read and remember every slug reading it.
    readers = collections.defaultdict(list)
    for slug in slugs:
        manifest = skill_registry.get_skill_value_manifest(slug)
        readers[(manifest["source"], manifest.get("data_slug", slug))].append(slug)

    needle = args.stat.lower() if args.stat else None
    rows, unreadable = 0, []
    for (source, data_slug), reading in sorted(readers.items(), key=lambda kv: kv[0][1]):
        skills, why_not = _read(source, data_slug)
        if why_not:
            unreadable.append((", ".join(reading), why_not))
            continue
        found = []
        for array, index, name, text in skills:
            for line in text.split("\n"):
                if DOWN not in line:
                    continue
                if needle and needle not in line.split(DOWN)[0].lower():
                    continue
                found.append((array, index, name, line.strip()))
        if not found:
            continue
        print(f"{data_slug}  [{source}]  (encoded as: {', '.join(reading)})")
        for array, index, name, line in found:
            print(f"    {array}[{index}] {name}: {line}")
            rows += 1
        print()

    print(f"{rows} `{DOWN}` bullet(s) over {len(readers)} character file(s) "
          f"for {len(slugs)} encoded slug(s)")
    if unreadable:
        print("\nNOT SCANNED - unanswered, not clean:")
        for who, why in unreadable:
            print(f"  {who}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
