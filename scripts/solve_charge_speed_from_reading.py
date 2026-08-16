"""프레임 판독이 요구하는 차지속도를 역산한다 — 엔진이 쓰는 값과 대조용.

**왜 이 방향인가.** 차지속도의 양자화는 이미 정해져 있다: 굴림은 정수 퍼센트로
반올림되고(같은 값끼리 먼저 합산), 그 퍼센트가 사는 프레임은 내림된다. 브래디
실측이 프레임 격자를 **13.5σ로 확정**했고 커뮤니티의 「0.01초 반올림」을 같은
자리에서 기각했다(`docs/measurements/bready-charge.md`). **격자를 다시 의심하지 말 것.**

그래서 남은 질문은 격자가 아니라 **입력**이다: 실측 발 간격이 정수 프레임 하나를
가리키면, 그 프레임 수를 사는 차속 퍼센트 범위는 유일하게 결정된다. 엔진이 그
유닛에게 주는 퍼센트가 그 범위 밖이면, 어긋난 것은 공식이 아니라 **차속 총량**이다.

**쓸 때:** 차지 무기 프레임 판독을 새로 받았을 때. 「엔진이 왜 이 유닛에서만
틀리나」를 물을 때. 엔진 함수를 직접 부르므로 규칙이 바뀌어도 이 스크립트는
드리프트하지 않는다.

사용법 (아무 cwd):
    python scripts/solve_charge_speed_from_reading.py
    python scripts/solve_charge_speed_from_reading.py --charge 1.5 --measured 83.174 --se 0.224
"""
import argparse
import math
import sys
from itertools import combinations_with_replacement
from pathlib import Path

# 이 환경의 콘솔은 cp949라 한글과 em-dash에서 UnicodeEncodeError로 죽는다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.attack_rate import charge_frames_bought  # noqa: E402
from app.overload_decode import charge_speed_percent_from_lines  # noqa: E402

# Fienn 인게임 프레임 판독. 원본과 조건은 docs/measurements/ 아래 각 파일.
# `se`는 그 파일의 간격들에서 직접 계산한 평균의 표준오차.
# `note`는 그 판독의 큐브 등 조건 — 대조에 필요한 만큼만.
READINGS = (
    # (슬러그, 차지초, 오버로드 굴림, 실측 발간격f, SE, 비고)
    #
    # 갈리는 축은 편성이 아니라 `input_type`이다 — UP 둘은 엔진과 0.0σ, 차속을 타는
    # DOWN_Charge 둘은 엔진에서 5.5~12.6σ 벗어난다. 편성은 무관하다(리베랄리오는
    # 단독 83.000f · 5인 83.174f로 사실상 같다).
    ("bready [UP]", 1.0, (6.09,), 57.000, 0.0319,
     "단독, 재장전 큐브 Lv15 명시, 딜레이 22f를 뺀 확정 차지 (bready-charge.md)"),
    ("prika [UP]", 1.0, (4.92,), 57.000, 0.1606,
     "단독, 차속을 건드리는 자기 스킬 없음, n=31 (prika-charge.md)"),
    ("liberalio [DOWN_Charge]", 1.5, (6.09,), 83.000, 0.159,
     "**단독** 재측정 n=35, 분포 81x2 82x9 83x11 84x13 (85f는 0회)"),
    ("neon-vision-eye [DOWN_Charge]", 1.0, (6.09, 1.98, 4.63, 4.33), 49.115, 0.160,
     "5인, 멈춤 0 — 간격이 곧 차지, n=26"),
)


def percent_window(charge_frames, bought):
    """`bought` 프레임을 정확히 사는 차속 비율의 반열린 구간 [낮, 높).

    `charge_frames_bought`가 `int(프레임 x 비율)`이므로 역상은 구간이다.
    """
    return bought / charge_frames, (bought + 1) / charge_frames


def integer_percents_in(low, high):
    """그 구간 안에 드는 정수 퍼센트 — 엔진이 실제로 만들어낼 수 있는 값들."""
    return [p for p in range(0, 201) if low <= p / 100 < high]


# 오버로드 차속 한 줄이 굴릴 수 있는 15개 값 (1~15레벨).
LINE_VALUES = (1.98, 2.28, 2.57, 2.86, 3.16, 3.45, 3.75, 4.04,
               4.33, 4.63, 4.92, 5.21, 5.51, 5.80, 6.09)


def roll_totals_reaching(percents, max_lines=6):
    """그 정수 퍼센트들에 도달하는 굴림 **합계**의 범위와 조합 수.

    왜 합계인가: 로스터가 굴림을 잃어버려도 화면의 차속 표기(합계)는 남는다. 그래서
    「이 판독이 성립하려면 표기가 몇 %여야 하나」가 실제로 대조 가능한 질문이고,
    그 답이 표기값과 어긋나면 **분해를 어떻게 고르든 판독이 설명되지 않는다** —
    굴림 오독 가설이 거기서 죽는다.
    """
    wanted = set(percents)
    totals = []
    for n in range(1, max_lines + 1):
        for combo in combinations_with_replacement(LINE_VALUES, n):
            if charge_speed_percent_from_lines(combo) in wanted:
                totals.append(round(sum(combo), 2))
    return (min(totals), max(totals), len(totals)) if totals else None


def solve(charge_time, measured, se, lines=None):
    charge_frames = charge_time * 60
    # 실측이 가리키는 정수 프레임: 95% 구간 안의 정수들.
    lo, hi = measured - 1.96 * se, measured + 1.96 * se
    candidates = [f for f in range(math.floor(lo), math.ceil(hi) + 1) if lo <= f <= hi]
    if not candidates:
        candidates = [round(measured)]

    print(f"  차지 {charge_time:.2f}초 = {charge_frames:.0f}프레임")
    print(f"  실측 {measured:.3f}f ± {se:.3f}  ->  95% 구간 [{lo:.3f}, {hi:.3f}]")
    if lines:
        percent = charge_speed_percent_from_lines(lines)
        bought = charge_frames_bought(charge_time, percent / 100)
        print(f"  엔진: 굴림 {list(lines)} 합계 {sum(lines):.2f}% -> 정수 {percent:.0f}% "
              f"-> {bought}프레임 삼 -> **{charge_frames - bought:.0f}f**")
    print(f"  실측이 가리키는 정수 프레임: {candidates}")
    for frames in candidates:
        bought = charge_frames - frames
        low, high = percent_window(charge_frames, bought)
        allowed = integer_percents_in(low, high)
        print(f"    {frames}f  <- {bought:.0f}프레임 삼  <- 차속 "
              f"[{low * 100:.3f}%, {high * 100:.3f}%)  정수 후보 {allowed}")
        if lines:
            need = [p - percent for p in allowed]
            print(f"       엔진의 {percent:.0f}%에서 모자란 양: "
                  f"{['%+d%%p' % d for d in need]}")
        reach = roll_totals_reaching(allowed)
        if reach:
            lo_t, hi_t, count = reach
            verdict = ""
            if lines:
                total = round(sum(lines), 2)
                verdict = ("  <- 표기 합계가 이 안" if lo_t <= total <= hi_t
                           else f"  <- ★ 표기 합계 {total:.2f}%는 이 **밖**이다")
            print(f"       이 프레임을 내는 굴림 **합계** 범위: "
                  f"[{lo_t:.2f}%, {hi_t:.2f}%]  ({count}개 조합){verdict}")


# 양자화 지점 후보들. 엔진과 Fienn 가설은 **반올림 방향이 반대**라는 것이 요점이다:
# 「차속이 사는 프레임을 내림」은 차지를 길게, 「차지 시간을 내림」은 짧게 만든다.
# 판독이 어느 쪽을 고르는지가 곧 판정이다 (docs/measurements/charge-speed-scaling.md).
def quantisation_models(base_frames, percent):
    s = percent / 100
    cont = base_frames * (1 - s)
    engine = base_frames - math.floor(base_frames * s)
    return {
        "엔진  base-floor(base*s)": engine,
        "Fienn floor(base*(1-s))": math.floor(cont),
        "      ceil(base*(1-s))": math.ceil(cont),
        "      연속값": cont,
        "      비례 -2.06%": engine * 0.9794,
    }


def compare_models(charge_time, measured, se, lines):
    """양자화 후보들을 이 판독에 대조한다. 새 프레임 판독을 받으면 이것부터."""
    base = charge_time * 60
    percent = charge_speed_percent_from_lines(lines)
    print(f"  차지 {charge_time:.2f}초 = {base:.0f}f · 굴림 {list(lines)} -> 정수 {percent:.0f}%")
    print(f"  실측 {measured:.3f}f ± {se:.3f}")
    for label, value in quantisation_models(base, percent).items():
        sigma = abs(value - measured) / se if se else float("nan")
        print(f"    {label:<26}{value:8.3f}f   {sigma:6.1f}σ")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--models", action="store_true",
                   help="역산 대신 양자화 모델 후보들을 판독에 대조한다")
    p.add_argument("--charge", type=float, help="차지 시간(초)")
    p.add_argument("--measured", type=float, help="실측 발 간격(프레임)")
    p.add_argument("--se", type=float, default=0.0, help="실측 평균의 표준오차")
    p.add_argument("--lines", nargs="*", type=float, default=None,
                   help="오버로드 차속 굴림 (예: --lines 6.09)")
    args = p.parse_args()

    if args.charge and args.measured:
        lines = tuple(args.lines or ()) or None
        if args.models:
            if not lines:
                p.error("--models 는 --lines 가 있어야 한다")
            compare_models(args.charge, args.measured, args.se, lines)
        else:
            solve(args.charge, args.measured, args.se, lines)
        return

    for slug, charge, lines, measured, se, note in READINGS:
        print(f"\n=== {slug} ===")
        print(f"  {note}")
        if args.models:
            compare_models(charge, measured, se, lines)
        else:
            solve(charge, measured, se, lines)


if __name__ == "__main__":
    main()
