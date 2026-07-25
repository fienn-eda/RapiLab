"""Solve a unit's per-core flat ATK/HP from two ShiftyPad readings.

WHY THIS EXISTS
    stat_assembly's CORE_FLAT_* tables are measured, not derived, and a
    combination nobody owns cored stays unmeasured - today a PILGRIM/OVERSPEC
    Supporter (Chime, Dorothy, Grave, Little Mermaid, Nayuta, Rapunzel). An
    account that owns one cored loses that unit from recommendations
    (`UnmeasuredStat`, reported as `unmeasured` by /api/assemble-roster).

THE TRICK
    The model is

        stat400 = base(class,400) * mult(grade, core)
                  + grade*grade_flat + core*core_flat + extra_flat

    Read the SAME unit twice, changing ONLY the core. `extra_flat` (affinity,
    research, equipment, cube, favorite item) and the grade term are identical in
    both readings, so they cancel and one unknown is left:

        core_flat = (d_stat - base*(mult(g,c2) - mult(g,c1))) / (c2 - c1)

    That is why this needs no equipment or research transcription at all - only
    grade, the two core values, and the two level-400 numbers ShiftyPad shows.

    Give THREE OR MORE readings when the unit's core allows it. Every span
    against the lowest core must imply the same value; a value that drifts with
    the span means the core term is not linear the way the model assumes, which
    matters more than the number itself. With only two readings there is nothing
    to check that against.

USAGE
    python scripts/solve_core_flat.py --class Supporter --grade 3 --label Grave \
        --reading 0,110022,3398025 \
        --reading 1,111740,3452200 \
        --reading 3,115175,3560351

    A reading is `core,atk,hp` (hp optional: `core,atk`). Repeat for a second
    unit of the same class/corporation; the two answers must agree, or the value
    is unit-specific and belongs in CORE_FLAT_*_BY_RESOURCE_ID rather than in the
    class/corporation table. Either way the parity suite is the regression test.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app.stat_assembly as sa            # noqa: E402
from app.stat_assembly import load_stat_tables  # noqa: E402


def solve(tables, character_class, grade, base_fn, flat_key,
          core_a, stat_a, core_b, stat_b):
    """Per-core flat implied by two readings that differ only in core."""
    if core_a == core_b:
        raise ValueError("the two readings must use different core values")
    base = base_fn(tables, character_class, 400)
    scaled_delta = base * (sa.breakthrough_multiplier(grade, core_a)
                           - sa.breakthrough_multiplier(grade, core_b))
    return (stat_a - stat_b - scaled_delta) / (core_a - core_b), base, scaled_delta


def _reading(text):
    """`core,atk[,hp]` -> (core, atk, hp|None)."""
    parts = text.split(",")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError(f"expected core,atk[,hp] - got {text!r}")
    core, atk, *rest = parts
    return int(core), float(atk), float(rest[0]) if rest else None


def _report(tables, label, character_class, grade, readings, stat, base_fn,
            class_table, corp_tables):
    values = [(c, v) for c, v, in readings if v is not None]
    if len(values) < 2:
        print(f"  {stat}: need two readings")
        return
    lo_core, lo_stat = min(values)
    print(f"  {stat}:")
    for core, value in sorted(values):
        if core == lo_core:
            continue
        flat, base, scaled = solve(tables, character_class, grade, base_fn, stat,
                                   core, value, lo_core, lo_stat)
        print(f"    core {lo_core}->{core} (span {core - lo_core}): "
              f"d={value - lo_stat:>12,.0f}  scaled={scaled:>12,.2f}  "
              f"-> {flat:.4f}")
    print(f"    measured elsewhere: class={class_table[character_class]}, "
          + ", ".join(f"{n}={t.get(character_class, '-')}"
                      for n, t in corp_tables.items()))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--class", dest="character_class", required=True,
                   choices=("Attacker", "Supporter", "Defender"))
    p.add_argument("--grade", type=int, required=True,
                   help="돌파 (0-3), the SAME in every reading")
    p.add_argument("--reading", type=_reading, action="append", required=True,
                   metavar="CORE,ATK[,HP]",
                   help="one level-400 reading; repeat (2 minimum, 3+ to check linearity)")
    p.add_argument("--label", default="unit")
    args = p.parse_args()

    tables = load_stat_tables()
    cores = [r[0] for r in args.reading]
    if len(set(cores)) != len(cores):
        p.error(f"two readings share a core value: {cores}")
    print(f"{args.label}: class={args.character_class} grade={args.grade} "
          f"cores {sorted(cores)}")

    _report(tables, args.label, args.character_class, args.grade,
            [(c, a) for c, a, _ in args.reading], "ATK", sa.base_atk,
            sa.CORE_FLAT_ATK,
            {"PILGRIM": sa.CORE_FLAT_ATK_PILGRIM, "OVERSPEC": sa.CORE_FLAT_ATK_OVERSPEC})
    _report(tables, args.label, args.character_class, args.grade,
            [(c, h) for c, _, h in args.reading], "HP", sa.base_hp,
            sa.CORE_FLAT_HP, {"OVERSPEC": sa.CORE_FLAT_HP_OVERSPEC})
    return 0


if __name__ == "__main__":
    sys.exit(main())
