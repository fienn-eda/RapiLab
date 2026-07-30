"""Which owned charge unit can settle a charge-speed aggregation rule, and how.

Why this exists: twice now a community rule about charge speed has come down to
"whose charge time, measured how". Scarlet could not settle the 0.01-sec rule
because her two charge-speed values sit on different accounts; Bready could,
because her 1.00-sec charge widens the gap and her charge gauge can be read
inside one account (docs/measurements/bready-charge.md). Picking that unit by
hand each time is how the wrong one gets picked, so this script reads the synced
roster and reports, per charge unit, whether the rules actually disagree on her
and by how many frames.

The engine floors the RAW SUM of charge-speed lines onto the frame grid. The
surviving community claim (arca.live/b/nikketgv/169159561) rounds each line to a
whole percent first, summing same-valued lines before rounding. Where those buy
a different number of frames, one measurement decides.

The roster stores overload options AGGREGATED - a total per option kind, not the
individual lines - so the script enumerates every multiset of canonical overload
values that sums to the observed total. A unit is only listed as decisive when
EVERY decomposition disagrees with the engine, because then the reading settles
the rule without anyone knowing which lines are actually equipped.

Usage (any cwd):
    python3 scripts/find_charge_rule_discriminators.py
    python3 scripts/find_charge_rule_discriminators.py --all
    python3 scripts/find_charge_rule_discriminators.py --lines 4.92 4.92 --charge 1.0
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

from app.skill_rules.registry import (  # noqa: E402
    ENCODED_SLUGS, NO_CHARGE_MOTION_DELAY, get_charge_motion_delay,
    get_skill_value_manifest)
from app.skill_values import DATA_DIR, load_weapon_data  # noqa: E402

# The 15 levels a charge-speed overload line can roll, in hundredths of a
# percent so the decomposition search is exact integer arithmetic.
LINE_CENTS = (198, 228, 257, 286, 316, 345, 375, 404, 433, 463, 492, 521, 551,
              580, 609)
CHARGE_SPEED_OPTION = "차지 속도 증가"
ROSTER_JSON = (Path(__file__).resolve().parent.parent
               / "tools" / "collect-blablalink" / "roster-drafts.json")
FRAMES_PER_SEC = 60


def engine_frames(charge_frames, total_cents):
    """The engine's rule: floor the raw sum onto the frame grid."""
    return int(charge_frames * total_cents / 10000)


def whole_percent_frames(charge_frames, line_cents):
    """The community rule: same-valued lines sum, each group rounds to a whole
    percent, and the frame grid is applied to that total."""
    grouped = {}
    for line in line_cents:
        grouped[line] = grouped.get(line, 0) + line
    percent = sum(round(group / 100) for group in grouped.values())
    return int(charge_frames * percent / 100)


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


def _self_charge_speed(slug):
    """Whether this unit buffs or debuffs her OWN charge speed, which would
    contaminate a reading unless the measurement avoids the trigger. Bready's
    Taste is the reason this column exists."""
    module = (Path(__file__).resolve().parent.parent / "backend" / "app"
              / "skill_rules" / (slug.replace("-", "_") + ".py"))
    if not module.exists():
        return False
    return any("charge_speed_percent" in line
               for line in module.read_text(encoding="utf-8").splitlines())


def _charge_units_from_roster():
    if not ROSTER_JSON.exists():
        sys.exit(f"no synced roster at {ROSTER_JSON} - see scripts/roster_fixture.py")
    for draft in json.loads(ROSTER_JSON.read_text(encoding="utf-8")):
        slug = draft["character_slug"]
        total = sum(float(option["value"])
                    for option in (draft.get("overload_options") or [])
                    if option["name"] == CHARGE_SPEED_OPTION)
        if total <= 0:
            continue
        manifest = get_skill_value_manifest(slug)
        if manifest is None:
            continue
        try:
            weapon = load_weapon_data(manifest, slug, DATA_DIR)
        except Exception:
            continue
        if not weapon or weapon.get("weapon") not in ("RL", "SR"):
            continue
        yield slug, weapon, total


def _report(rows, show_all):
    header = (f"{'유닛':<24}{'무기':>4}{'차지':>6}{'차속합':>8}"
              f"{'엔진':>6}{'정수%':>9}{'분해':>5}{'장탄':>5}  판정")
    print(header)
    print("-" * len(header))
    for row in rows:
        if not show_all and row["verdict"] != "DECISIVE":
            continue
        note = {"DECISIVE": f"★ {row['gap']}프레임 갈림 — 전 분해 일치",
                "PARTIAL": "일부 분해만 갈림 — 줄 구성을 알아야 판정",
                "SAME": "동일 — 판정 불가"}[row["verdict"]]
        if row["self_charge_speed"]:
            note += " ⚠자기 차속 버프 있음"
        print(f"{row['slug']:<24}{row['weapon']:>4}{row['charge_time']:6.2f}"
              f"{row['total']:8.2f}{row['engine']:6d}{str(row['community']):>9}"
              f"{row['decompositions']:5d}{row['max_ammo']:5d}  {note}")


def _recipe(row):
    engine_frames_left = round(row["charge_time"] * FRAMES_PER_SEC) - row["engine"]
    community_left = round(row["charge_time"] * FRAMES_PER_SEC) - row["community"][0]
    reading = ("대미지 숫자 = 발사 (SR은 즉시 명중)" if row["weapon"] == "SR"
               else "총구 섬광 = 발사 (RL 유탄은 비행시간이 있어 대미지 숫자를 쓰면 안 된다)")
    unique = ("줄 구성이 유일하다 — 판독이 예상 밖이면 규칙이 틀린 것이다"
              if row["decompositions"] == 1
              else f"줄 구성이 {row['decompositions']}가지 — 전부 같은 답을 내지만 "
                   "예상 밖 판독은 규칙 탓인지 구성 탓인지 못 가린다")
    print(f"\n=== 추천 측정: {row['slug']} ===")
    print(f"  차속 {row['total']:.2f}% · 차지 {row['charge_time']:.2f}초 "
          f"({round(row['charge_time'] * FRAMES_PER_SEC)}프레임) · 장탄 {row['max_ammo']}발")
    print(f"  {unique}")
    print(f"  현행 엔진 예측   차지 {engine_frames_left}프레임 "
          f"({engine_frames_left / FRAMES_PER_SEC:.5f}초)")
    print(f"  정수 % 예측      차지 {community_left}프레임 "
          f"({community_left / FRAMES_PER_SEC:.5f}초)")
    print(f"  → 갭 {abs(engine_frames_left - community_left)}프레임")
    print("  기록 형식: [발사, 차지시작, 발사, 차지시작, ...] 영상 프레임 번호")
    print(f"  판독: {reading} · 차지시작 = 차지 게이지가 최초로 양수가 된 프레임")
    print("  조건: 단독 편성(버스트 없음) · FB 밖 · 재장전으로 끊긴 시퀀스는 제외")
    print("  분량: 20판독이면 5.8σ, 30이면 7σ (브래디 판독 산포 0.76프레임 기준)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true",
                        help="판정 불가한 유닛까지 전부 보여준다")
    parser.add_argument("--lines", nargs="+", type=float, metavar="PCT",
                        help="로스터 대신 가정한 줄 목록으로 계산 (--charge 필요)")
    parser.add_argument("--charge", type=float, metavar="SEC",
                        help="--lines와 함께 쓰는 차지시간(초)")
    args = parser.parse_args()

    if args.lines:
        if not args.charge:
            sys.exit("--lines 는 --charge 가 필요하다")
        frames = round(args.charge * FRAMES_PER_SEC)
        cents = [round(line * 100) for line in args.lines]
        engine = engine_frames(frames, sum(cents))
        community = whole_percent_frames(frames, cents)
        print(f"차지 {args.charge}초 = {frames}프레임 · 줄 {args.lines}")
        print(f"  엔진(생합계)  {engine}프레임 사고 차지 {(frames - engine) / 60:.5f}초")
        print(f"  정수 %        {community}프레임 사고 차지 {(frames - community) / 60:.5f}초")
        print(f"  → {'갈린다' if engine != community else '동일하다'}"
              f" (갭 {abs(engine - community)}프레임)")
        return

    rows = []
    for slug, weapon, total in _charge_units_from_roster():
        frames = round(float(weapon["chargeTime"]) * FRAMES_PER_SEC)
        cents = round(total * 100)
        found = decompositions(cents)
        engine = engine_frames(frames, cents)
        community = sorted({whole_percent_frames(frames, combo) for combo in found})
        if community and all(value != engine for value in community):
            verdict = "DECISIVE"
        elif any(value != engine for value in community):
            verdict = "PARTIAL"
        else:
            verdict = "SAME"
        rows.append({
            "slug": slug, "weapon": weapon["weapon"], "max_ammo": int(weapon["maxAmmo"]),
            "charge_time": float(weapon["chargeTime"]), "total": total,
            "engine": engine, "community": community, "decompositions": len(found),
            "verdict": verdict, "gap": abs(community[0] - engine) if community else 0,
            "self_charge_speed": _self_charge_speed(slug),
            "encoded": slug in ENCODED_SLUGS,
            "delay_known": slug in NO_CHARGE_MOTION_DELAY or get_charge_motion_delay(slug) > 0,
        })

    rows.sort(key=lambda row: (row["verdict"] != "DECISIVE", -row["gap"], row["slug"]))
    _report(rows, args.all)

    decisive = [row for row in rows if row["verdict"] == "DECISIVE"]
    if not decisive:
        print("\n판정 가능한 유닛이 로스터에 없다 — 오버로드가 더 굴러가야 한다.")
        return
    # A UNIQUE decomposition comes first: with one, an unexpected reading can
    # only mean the rule is wrong, while with several it could also mean the
    # equipped lines are an exotic combination, and then the measurement decides
    # nothing. After that prefer an SR, whose shot frame is the damage number
    # rather than a muzzle flash; then a unit whose pause is already timed, so
    # `interval = charge + delay` can check the reading against itself; then the
    # widest gap and the biggest magazine.
    best = sorted(decisive, key=lambda row: (row["decompositions"] > 1,
                                             row["weapon"] != "SR",
                                             not row["delay_known"], -row["gap"],
                                             -row["max_ammo"], row["slug"]))[0]
    _recipe(best)
    print(f"\n판정 가능 {len(decisive)}기 / 차속 보유 차지무기 {len(rows)}기")


if __name__ == "__main__":
    main()
