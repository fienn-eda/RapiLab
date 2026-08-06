"""List every NARROW targeting line in the collected skill text, per encoded Nikke.

WHY: an `Effect`'s scope is the one thing no value check can catch. "Affects all
allies with a Sniper Rifle" and "Affects all allies" reach the encoder as the
same buff with the same number, and a squad-scoped encoding of the first passes
every slot-mapping test, every fixture and the whole suite - it just quietly
pays units the skill excludes. D: Killer Wife's Calm Sniping shipped that way
for months behind the reason "the scope model has no weapon-conditional
targeting", which stopped being true when gap #3 landed `member_subset_buff_rule`
(2026-07-16). Brid's Full Throttle shipped "Affects all allies (except self)" as
squad and handed Brid her own flat ATK.

The engine can express, EXACTLY, all of these:
  - weapon class    -> member_subset_buff_rule(m.weapon == "SR")
  - element code    -> "element:<Name>" scope, or a member filter
  - except self     -> a member filter on m.slug != caster_slug
  - N highest ATK   -> highest_atk_buff_rule / round_buff_rule(("top_atk", n))
  - bursted allies  -> a member filter reading context.burst_used_this_cycle
Only POSITIONAL targeting ("both adjacent allies", "2 allies on both sides") has
no scope, and is the one that may honestly be approximated as squad - say so in
the docstring when you do.

The audit cannot judge: it cannot tell WHICH Effect a text line became, and a
narrow line whose payload is an inert stat (Hit Rate, Damage to Parts) is
harmless as squad. What it does is put every narrow targeting line in front of
you next to the scopes the module actually emits, so each one gets read against
its encoding once. A unit with narrow lines and NO narrow scope anywhere is the
shape both real bugs had - those are listed first.

WHEN TO RUN: after encoding a Nikke, after collecting new character data, and
after any engine change that adds a scope or a targeting helper.

Exit code is 0 - this is a checklist, not a gate.
"""
import argparse
import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.skill_rules import registry as skill_registry
from app.skill_values import DATA_DIR, load_character_data

SKILL_DIR = ROOT / "backend" / "app" / "skill_rules"

# A targeting line the engine can express EXACTLY, by the kind of narrowing.
NARROW_TARGETS = {
    "weapon": re.compile(
        r"allies with (?:a |an |)(?:sniper rifle|shotgun|assault rifle|machine gun|"
        r"submachine gun|rocket launcher|shotguns|snipers)|[a-z]+-wielding allies",
        re.I),
    "element": re.compile(r"all (?:\w+ )?(?:fire|water|wind|iron|electric) code allies", re.I),
    "except self": re.compile(r"except (?:for )?self|except the skill user|excluding self", re.I),
    "top ATK": re.compile(r"all(?:y|ies) unit\(s\) with the highest", re.I),
    "bursted allies": re.compile(r"allies who (?:previously cast|have used) their burst", re.I),
}

# Positional targeting has NO engine scope - squad is the documented fallback.
POSITIONAL = re.compile(
    r"adjacent all(?:y|ies)|allies on both sides|back row|front row", re.I)

# What a module emitting an exact subset looks like.
NARROW_SCOPE = re.compile(
    r'"element:|"slugs:|member_subset_buff_rule|highest_atk_buff_rule|'
    r'"top_atk"|\.weapon ==|\.element ==|!= caster_slug|burst_used_this_cycle')


def _texts(source, data_slug):
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
    is read from its lootandwaifus file when one was collected.
    """
    if source == "shiftypad":
        if (Path(DATA_DIR) / "lootandwaifus" / f"char_{data_slug}.json").exists():
            return list(_texts("lootandwaifus", data_slug)), None
        return [], "shiftypad's normalized file carries no prose, and no lootandwaifus text was collected"
    try:
        return list(_texts(source, data_slug)), None
    except FileNotFoundError as error:
        return [], f"{type(error).__name__}: {error}"


def _module_emits_a_narrow_scope(slugs):
    """Whether ANY module that could encode these slugs emits a narrow scope.

    Matched by module file rather than by slug because one module encodes a
    whole dual-slug family, and the scope may live in either half.
    """
    for slug in slugs:
        stem = slug.replace("-", "_")
        for path in SKILL_DIR.glob("*.py"):
            if not stem.startswith(path.stem) and not path.stem.startswith(stem.split("_signature")[0]):
                continue
            if NARROW_SCOPE.search(path.read_text(encoding="utf-8")):
                return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", choices=sorted(NARROW_TARGETS) + ["positional"],
                        help="show only one kind of narrowing")
    args = parser.parse_args()

    # Group by the file actually READ, not by the manifest source: a dual-slug
    # pair can name two sources and still fall back to one lootandwaifus page,
    # which would otherwise print the same skill text twice.
    readers = collections.defaultdict(list)
    for slug in sorted(skill_registry.ENCODED_SLUGS):
        manifest = skill_registry.get_skill_value_manifest(slug)
        source, data_slug = manifest["source"], manifest.get("data_slug", slug)
        if source == "shiftypad" and (
                Path(DATA_DIR) / "lootandwaifus" / f"char_{data_slug}.json").exists():
            source = "lootandwaifus"
        readers[(source, data_slug)].append(slug)

    wanted = {args.kind: NARROW_TARGETS[args.kind]} if args.kind in NARROW_TARGETS else NARROW_TARGETS
    show_positional = args.kind in (None, "positional")

    suspect, reviewed, unreadable = [], [], []
    for (source, data_slug), slugs in sorted(readers.items(), key=lambda kv: kv[0][1]):
        skills, why_not = _read(source, data_slug)
        if why_not:
            unreadable.append((", ".join(slugs), why_not))
            continue
        narrow, positional = [], []
        for array, index, name, text in skills:
            for line in re.split(r"[\r\n]+", text):
                line = line.strip()
                if not line:
                    continue
                if args.kind != "positional":
                    for kind, pattern in wanted.items():
                        if pattern.search(line):
                            narrow.append((kind, array, index, name, line))
                if show_positional and POSITIONAL.search(line):
                    positional.append((array, index, name, line))
        if not narrow and not positional:
            continue
        entry = (data_slug, slugs, narrow, positional)
        if narrow and not _module_emits_a_narrow_scope(slugs):
            suspect.append(entry)
        else:
            reviewed.append(entry)

    def show(entries):
        for data_slug, slugs, narrow, positional in entries:
            print(f"{data_slug}  (encoded: {', '.join(slugs)})")
            for kind, array, index, name, line in narrow:
                print(f"    [{kind}] {array}[{index}] {name}: {line}")
            for array, index, name, line in positional:
                print(f"    [positional - no engine scope] {array}[{index}] {name}: {line}")
            print()

    print(f"{len(readers)} character file(s) for {len(skill_registry.ENCODED_SLUGS)} encoded slug(s)\n")
    print(f"== SUSPECT: narrow targeting, but the module emits NO narrow scope "
          f"({len(suspect)}) ==\n")
    show(suspect) if suspect else print("  (none)\n")
    print(f"== narrow targeting alongside at least one narrow scope - read each "
          f"line against its own Effect ({len(reviewed)}) ==\n")
    show(reviewed)
    if unreadable:
        print("NOT SCANNED - unanswered, not clean:")
        for reading, why in unreadable:
            print(f"  {reading}: {why}")


if __name__ == "__main__":
    main()
