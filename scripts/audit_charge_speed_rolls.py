"""Which owned charge units need their overload ROLLS, not just the total.

Charge speed rounds per roll: lines of the same value sum first and each group
rounds to a whole percent (`app.overload_decode.charge_speed_percent_from_lines`
carries the rule and the Prika measurement behind it). A roster that stores only
the displayed TOTAL therefore cannot always say how many frames a unit's charge
actually takes - the engine falls back to treating that total as one roll.

Sometimes the fallback is exactly right: a total only one multiset of canonical
line values can reach, or one every multiset agrees on, is unambiguous no matter
what was rolled. This script separates those from the totals where knowing the
rolls would move the frame count, so "re-sync the roster" is a decision with a
number attached rather than a habit.

It calls the engine's own rule rather than restating it. An earlier version of
this script reimplemented the aggregation locally, and when the rule changed the
copy did not - it went on reporting the superseded behaviour as "the engine".

Usage (any cwd):
    python3 scripts/audit_charge_speed_rolls.py
    python3 scripts/audit_charge_speed_rolls.py --all
    python3 scripts/audit_charge_speed_rolls.py --lines 4.63 4.63 4.33 --charge 1.0
"""
import argparse
import json
import sys
from itertools import combinations_with_replacement
from pathlib import Path

# Windows consoles here default to cp949, which cannot encode the Korean labels
# or the em-dash below and kills the run with UnicodeEncodeError. Ask for UTF-8
# rather than writing around it.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.attack_rate import charge_frames_bought  # noqa: E402
from app.overload_decode import charge_speed_percent_from_lines  # noqa: E402
from app.skill_rules.registry import get_skill_value_manifest  # noqa: E402
from app.skill_values import DATA_DIR, load_weapon_data  # noqa: E402
from roster_fixture import add_roster_argument  # noqa: E402

# The 15 levels a charge-speed overload line can roll, in hundredths of a
# percent so the decomposition search is exact integer arithmetic.
LINE_CENTS = (198, 228, 257, 286, 316, 345, 375, 404, 433, 463, 492, 521, 551,
              580, 609)
CHARGE_SPEED_OPTION = "차지 속도 증가"


def frames_bought(charge_time, line_cents):
    """Frames these rolls take off this charge, by the engine's own arithmetic."""
    percent = charge_speed_percent_from_lines([cents / 100 for cents in line_cents])
    return charge_frames_bought(charge_time, percent / 100)


def decompositions(total_cents, max_lines=6):
    """Every multiset of canonical line values summing to this total. Overload
    rolls at random, so the roster's aggregate is all anyone knows - the caller
    needs all the ways it could have been reached."""
    found = []
    for count in range(1, max_lines + 1):
        for combo in combinations_with_replacement(LINE_CENTS, count):
            if sum(combo) == total_cents:
                found.append(combo)
    return found


def roll_outcomes(charge_time, total_cents):
    """(fallback frames, {frames each decomposition would buy}, decompositions).

    The fallback is what the engine does today with a rolls-free roster: the
    displayed total, rounded as if it were a single roll.
    """
    fallback = frames_bought(charge_time, (total_cents,))
    combos = decompositions(total_cents)
    return fallback, {frames_bought(charge_time, combo) for combo in combos}, combos


def _charge_units_from_roster(roster_json):
    if not roster_json.exists():
        sys.exit(f"no synced roster at {roster_json} - see scripts/roster_fixture.py")
    for draft in json.loads(roster_json.read_text(encoding="utf-8")):
        slug = draft["character_slug"]
        options = draft.get("overload_options") or []
        charge_options = [option for option in options
                          if option["name"] == CHARGE_SPEED_OPTION]
        total = sum(float(option["value"]) for option in charge_options)
        if total <= 0:
            continue
        # A roster that already carries the rolls needs no inference at all -
        # the answer is read rather than bracketed.
        rolls = [round(float(line["value"]) * 100)
                 for option in charge_options for line in (option.get("lines") or [])]
        manifest = get_skill_value_manifest(slug)
        if manifest is None:
            continue
        try:
            weapon = load_weapon_data(manifest, slug, DATA_DIR)
        except Exception:
            continue
        if not weapon or weapon.get("weapon") not in ("RL", "SR"):
            continue
        yield slug, weapon, total, rolls


def _rows(roster_json):
    for slug, weapon, total, rolls in _charge_units_from_roster(roster_json):
        charge_time = float(weapon["chargeTime"])
        total_cents = round(total * 100)
        fallback, outcomes, combos = roll_outcomes(charge_time, total_cents)
        yield {
            "slug": slug, "weapon": weapon["weapon"], "charge_time": charge_time,
            "total": total, "rolls": rolls, "fallback": fallback,
            "actual": frames_bought(charge_time, rolls) if rolls else None,
            "outcomes": sorted(outcomes), "decompositions": len(combos),
            "ambiguous": outcomes != {fallback},
        }


def _report(rows, show_all):
    print(f"{'유닛':<26}{'무기':>4}{'차지':>6}{'차속합':>8}"
          f"{'폴백':>6}{'실제':>6}{'분해별':>10}  판정")
    print("-" * 82)
    shown = 0
    for row in sorted(rows, key=lambda r: (not r["ambiguous"], r["slug"])):
        if not show_all and not row["ambiguous"]:
            continue
        shown += 1
        if row["actual"] is not None:
            verdict = ("굴림으로 확정 — 폴백은 틀렸다"
                       if row["actual"] != row["fallback"] else "굴림으로 확정")
        elif row["ambiguous"]:
            verdict = "★ 굴림을 알아야 한다"
        else:
            verdict = "총합만으로 확정"
        actual = "—" if row["actual"] is None else str(row["actual"])
        print(f"{row['slug']:<26}{row['weapon']:>4}{row['charge_time']:>6.2f}"
              f"{row['total']:>8.2f}{row['fallback']:>6}{actual:>6}"
              f"{str(row['outcomes']):>10}  {verdict}")
    if not shown:
        print("(모든 유닛이 총합만으로 확정된다)")


def _what_if(lines, charge_time):
    cents = [round(line * 100) for line in lines]
    unknown = tuple([sum(cents)])
    print(f"굴림 {lines} · 차지 {charge_time:.2f}초 "
          f"({round(charge_time * 60)}프레임)")
    print(f"  굴림을 알 때   {frames_bought(charge_time, cents)}프레임")
    print(f"  총합만 알 때   {frames_bought(charge_time, unknown)}프레임 "
          f"(표시 합계 {sum(cents) / 100:.2f}%)")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    p.add_argument("--all", action="store_true",
                   help="총합만으로 확정되는 유닛까지 전부 출력")
    p.add_argument("--lines", nargs="+", type=float,
                   help="로스터 대신 이 굴림 조합을 계산한다 (예: --lines 4.63 4.63 4.33)")
    p.add_argument("--charge", type=float, default=1.0,
                   help="--lines와 함께 쓸 차지 시간(초), 기본 1.0")
    args = p.parse_args()

    if args.lines:
        _what_if(args.lines, args.charge)
        return

    rows = list(_rows(args.roster))
    print(f"로스터: {args.roster.name}\n")
    _report(rows, args.all)
    ambiguous = sum(1 for row in rows if row["ambiguous"] and row["actual"] is None)
    print(f"\n굴림을 알아야 프레임이 정해지는 유닛: {ambiguous} / {len(rows)}")
    if ambiguous:
        print("이 export는 굴림을 안 싣고 있다 — 다시 동기화하거나(RECIPE.md) "
              "굴림이 실린 export를 --roster로 지목할 것.")


if __name__ == "__main__":
    main()
