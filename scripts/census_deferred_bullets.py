"""Re-count what the encodings say they had to leave out.

`docs/engine-gaps.md` ranks engine gaps by "how many units does this block".
Its original counts came from phrase-scanning 44 collected characters, which
stopped being the best ledger once most of the roster was encoded: the encoding
modules themselves record, in their own docstrings, exactly what each unit had
to defer and why. This walks those docstrings instead.

Run it when re-ranking the gap inventory, after a batch of encodings, or to
check whether a gap you just closed still has consumers claiming it is open.

WHY IT PRINTS BOTH BUCKETS. A deferral is only interesting if the engine CANNOT
do the thing; bullets that skip healing, shields or burst-gauge fill are scope
decisions and would drown the signal. So bullets are split by the vocabulary of
those scope decisions - but that vocabulary OVERLAPS real gaps ("when cover is
attacked" is a trigger gap that says `cover`; "MG heating up speed" is a firing-
timeline gap that says `heating`). Reading only the gap bucket silently loses
them. Both buckets are printed for that reason; read both, and treat the split
as a sort order rather than an answer.

Usage (any cwd):
    python3 scripts/census_deferred_bullets.py            # both buckets
    python3 scripts/census_deferred_bullets.py --only gap
    python3 scripts/census_deferred_bullets.py --width 0  # do not truncate
"""
import argparse
import re
import sys
from pathlib import Path

MODULES = Path(__file__).resolve().parent.parent / "backend/app/skill_rules"

# Headings an encoding uses to open its "what I left out" section.
_SECTION = re.compile(r"^(Not modeled|Not encoded|Deferred)", re.M)

# The vocabulary of a deliberate scope decision. Overlaps real gaps - see the
# module docstring; that is why the scope bucket is printed too.
_SCOPE = re.compile(
    r"survivab|not DPS|healing|heal\b|shield|taunt|cover\b|HP recover|"
    r"damage taken|damage reduc|revive|invincib|burst gauge|gauge fill|utility",
    re.I,
)


def deferred_bullets(module_path):
    """Yield each bullet of a module's deferral section as one flat string."""
    src = module_path.read_text(encoding="utf-8")
    doc = re.match(r'\s*"""(.*?)"""', src, re.S)
    if not doc:
        return
    found = _SECTION.search(doc.group(1))
    if not found:
        return
    bullet = None
    for line in doc.group(1)[found.start():].splitlines():
        if line.startswith("- "):
            if bullet:
                yield re.sub(r"\s+", " ", bullet)
            bullet = line[2:].strip()
        elif bullet is not None and line.strip():
            bullet += " " + line.strip()
    if bullet:
        yield re.sub(r"\s+", " ", bullet)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=("gap", "scope"),
                    help="print one bucket only (default: both)")
    ap.add_argument("--width", type=int, default=220,
                    help="truncate each bullet to N chars (0 = no truncation)")
    args = ap.parse_args()

    if not MODULES.is_dir():
        sys.exit(f"skill_rules not found at {MODULES}")

    buckets = {"gap": [], "scope": []}
    modules = sorted(MODULES.glob("*.py"))
    for module_path in modules:
        for bullet in deferred_bullets(module_path):
            key = "scope" if _SCOPE.search(bullet) else "gap"
            buckets[key].append((module_path.stem, bullet))

    total = len(buckets["gap"]) + len(buckets["scope"])
    print(f"{len(modules)} modules, {total} deferred bullets "
          f"({len(buckets['gap'])} engine-gap, {len(buckets['scope'])} scope)")

    for key in ("gap", "scope"):
        if args.only and args.only != key:
            continue
        label = ("ENGINE CANNOT REPRESENT" if key == "gap"
                 else "SCOPE DECISION - read anyway, the filter overlaps real gaps")
        print(f"\n=== {label} ({len(buckets[key])}) ===")
        for stem, bullet in buckets[key]:
            text = bullet if args.width <= 0 else bullet[:args.width]
            print(f"{stem}\t{text}")


if __name__ == "__main__":
    main()
