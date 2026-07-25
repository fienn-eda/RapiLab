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

USAGE
    python scripts/solve_core_flat.py --class Supporter --grade 3 \
        --core 2 --atk 91234 --hp 2612345 \
        --core-baseline 0 --atk-baseline 90000 --hp-baseline 2600000

    Repeat for a second unit of the same class/corporation; the two answers must
    agree. Put the result in CORE_FLAT_ATK_PILGRIM / CORE_FLAT_HP_OVERSPEC and
    the parity suite becomes the regression test.
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


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--class", dest="character_class", required=True,
                   choices=("Attacker", "Supporter", "Defender"))
    p.add_argument("--grade", type=int, required=True, help="돌파 (0-3), same in both readings")
    p.add_argument("--core", type=int, required=True, help="core of the FIRST reading")
    p.add_argument("--atk", type=float, required=True, help="level-400 ATK at --core")
    p.add_argument("--hp", type=float, help="level-400 HP at --core")
    p.add_argument("--core-baseline", type=int, required=True,
                   help="core of the SECOND reading (anything different, 0 is easiest)")
    p.add_argument("--atk-baseline", type=float, required=True)
    p.add_argument("--hp-baseline", type=float)
    p.add_argument("--label", default="unit")
    args = p.parse_args()

    tables = load_stat_tables()
    print(f"{args.label}: class={args.character_class} grade={args.grade} "
          f"core {args.core_baseline} -> {args.core}")

    flat, base, scaled = solve(tables, args.character_class, args.grade,
                               sa.base_atk, "atk",
                               args.core, args.atk,
                               args.core_baseline, args.atk_baseline)
    print(f"  ATK: base={base:,.0f} scaled_delta={scaled:,.2f} "
          f"-> core_flat_atk = {flat:.4f}")
    print(f"       compare CORE_FLAT_ATK={sa.CORE_FLAT_ATK[args.character_class]}, "
          f"PILGRIM={sa.CORE_FLAT_ATK_PILGRIM}, OVERSPEC={sa.CORE_FLAT_ATK_OVERSPEC}")

    if args.hp is not None and args.hp_baseline is not None:
        flat, base, scaled = solve(tables, args.character_class, args.grade,
                                   sa.base_hp, "hp",
                                   args.core, args.hp,
                                   args.core_baseline, args.hp_baseline)
        print(f"  HP:  base={base:,.0f} scaled_delta={scaled:,.2f} "
              f"-> core_flat_hp = {flat:.4f}")
        print(f"       compare CORE_FLAT_HP={sa.CORE_FLAT_HP[args.character_class]}, "
              f"OVERSPEC={sa.CORE_FLAT_HP_OVERSPEC}")
    else:
        print("  HP:  skipped (pass --hp and --hp-baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
