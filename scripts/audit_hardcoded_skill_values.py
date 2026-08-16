"""Find skill VALUES hardcoded in a module instead of read from a value slot.

WHY: an encoding is supposed to read every number from `skill_values`, which the
roster layer assembles at the player's OWN skill levels. A number written into
the module instead is frozen at whatever level the encoder was reading - so a
player whose skill sits at 7 is simulated at 10. Quency: Escape Queen's Explore
Route was encoded this way (`STEADY_STATE_ATK = 2.45 * 10 + 4.9 * 10 + 7.36 * 5`,
all three level-10 numbers), and the skill is absent from her manifest entirely,
so no assembly test could see it either.

Not every literal is a defect. A cap ("stacks up to 5"), an interval written in
prose ("Attack Interval: 0.25 sec") and a measured constant (Ein's 0.3 sec
throttle) are all legitimately module-level, because they do NOT move with skill
level. That is exactly the test this script applies: a literal is only reported
when the unit's own collected text carries that number at max level AND a
different number at level 1. A value that is identical across all ten levels is
skill-level-independent and is not reported.

WHEN TO RUN: after encoding a Nikke, and when auditing existing encodings.

Exit code is 0 - this is a checklist, not a gate; read each hit against the
module.
"""
import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.skill_rules import registry as skill_registry
from app.skill_values import DATA_DIR, load_character_data

MODULE_DIR = ROOT / "backend" / "app" / "skill_rules"

# A literal has to look like a skill value to be worth reporting: skill numbers
# are decimals (14.08, 2.45). Bare integers are overwhelmingly caps, indexes and
# tick counts, and reporting them buries the real hits.
LITERAL = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\w.])")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _levels(source, data_slug):
    """[(level_index, {numbers in that level's text})] for every collected skill.

    dotgg keeps a value dict per level, lootandwaifus a rendered string; both
    reduce to the set of numbers that level's text carries.
    """
    data = load_character_data(source, data_slug)
    per_level = {}
    for array in ("skills", "dollskills"):
        for skill in data.get(array) or []:
            for index, level in enumerate(skill.get("levels") or []):
                if isinstance(level, dict):
                    values = {v for v in level.values() if v not in ("", None)}
                elif isinstance(level, str):
                    values = set(NUMBER.findall(level))
                else:
                    continue
                per_level.setdefault(index, set()).update(
                    str(v).rstrip("0").rstrip(".") if "." in str(v) else str(v)
                    for v in values
                )
    return per_level


def _source_for(slug):
    manifest = skill_registry.get_skill_value_manifest(slug)
    source, data_slug = manifest["source"], manifest.get("data_slug", slug)
    if source == "shiftypad":
        for fallback in ("lootandwaifus", "dotgg"):
            if (Path(DATA_DIR) / fallback / f"char_{data_slug}.json").exists():
                return fallback, data_slug
    return source, data_slug


def _normalize(text):
    return text.rstrip("0").rstrip(".") if "." in text else text


def audit(slug):
    """[(line number, literal, line text)] - literals that look like level-scaled
    skill values."""
    module = MODULE_DIR / (slug.replace("-", "_") + ".py")
    if not module.exists():
        return None
    source, data_slug = _source_for(slug)
    try:
        per_level = _levels(source, data_slug)
    except FileNotFoundError:
        return None
    if not per_level:
        return None
    top = max(per_level)
    max_level, first_level = per_level[top], per_level[0]
    # Scaling numbers are the ones the max level has and level 1 does not.
    scaling = max_level - first_level

    # AST, not a line scan: docstrings and comments quote these numbers
    # constantly ("self ATK +30.5% for 3 sec"), and only a real numeric literal
    # in executable code is the defect.
    text = module.read_text(encoding="utf-8")
    lines = text.splitlines()
    hits = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, float):
            continue
        literal = _normalize(f"{node.value:g}")
        if literal in scaling:
            source_line = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
            hits.append((node.lineno, literal, source_line))
    return sorted(set(hits))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", help="one encoded slug instead of all")
    args = parser.parse_args()

    slugs = sorted(skill_registry._BUILDERS)
    if args.slug:
        if args.slug not in slugs:
            parser.error(f"{args.slug} is not an encoded slug")
        slugs = [args.slug]

    flagged = 0
    for slug in slugs:
        hits = audit(slug)
        if not hits:
            continue
        flagged += 1
        print(f"{slug}  ({(MODULE_DIR / (slug.replace('-', '_') + '.py')).name})")
        for number, literal, text in hits:
            print(f"    line {number}: {literal}   |  {text[:110]}")
        print()

    print(f"{flagged} module(s) carry a level-scaled skill number as a literal, "
          f"of {len(slugs)} encoded slug(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
