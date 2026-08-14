"""명중률 인코딩이 실제로 딜에 닿는지, 유닛별로 얼마나 닿는지 잰다.

`hit_rate`는 `accuracy.core_hit_rate`를 통해서만 딜에 닿고, 그 경로는
`BossProfile.core_diameter_px`가 있는 인카운터에서만 열린다(기본값 `None`).
그래서 스위트가 전부 초록이어도 「명중을 인코딩했다」와 「그 명중이 딜을
움직인다」는 여전히 다른 진술이다 — 15슬러그가 5주 동안 전자 없이 후자를 적어
두고 있었던 것과 같은 종류의 틈이다.

이 스크립트가 그 틈을 닫는다. 코어 지름을 켠 같은 덱을 두 번 돌리는데, 두 번째는
`accuracy.core_hit_rate`를 **명중률 0으로 고정해** 호출하도록 감싼다. 두 값의 차가
곧 그 유닛의 인코딩된 명중이 사 준 딜이다.

**코어 지름의 기본값은 애니힐리오 실측 `raid_record.CORE_DIAMETER_PX`(48.89)다.**
실측이 있는 유일한 보스라 기본값으로 쓸 뿐, 이 셸의 보스가 애니힐리오라는 뜻은
아니다 — 코어는 보스마다 다르다(사격장 표적은 같은 mid에서 33.40으로 1.46배 차이).
여기서 읽을 것은 절대 수치가 아니라 「인코딩이 배선됐는가」와 「유닛 사이 크기
순서」다. 2026-08-14 이전 판은 실측이 없어 50px을 가정했다.

**셸은 `sweep_slug_damage.py`와 같아서 같은 한계를 갖는다.** 티어 3 셸에는 다른
Burst 3이 없는데, 디젤: 윈터 스위츠(Highlight)는 `burst_delay`로 첫 사이클을
거르므로 그 셸에서는 **풀 버스트가 한 번도 안 열린다**(180초 동안 0회). 그래서
버스트 횟수를 같이 출력한다 - 0이면 그 행의 0.00%는 「인코딩이 안 됐다」가 아니라
「그 불릿이 발동할 기회가 없었다」는 뜻이다.

사용법 (cwd 무관):
    python3 scripts/measure_hit_rate_core_gain.py
    python3 scripts/measure_hit_rate_core_gain.py --core-diameter 67 --slug jill-valentine
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.accuracy as accuracy  # noqa: E402
import app.raid_simulator as raid_simulator  # noqa: E402
from app.deck_search import (  # noqa: E402
    BossProfile,
    evaluate_deck,
    feasible_orderings,
    never_full_bursts,
)
from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import CORE_DIAMETER_PX  # noqa: E402

# sweep_slug_damage.py와 같은 셸: 재는 유닛의 티어를 셸이 갖지 않아야 그 유닛이
# 로테이션에서 밀려나지 않는다.
SHELLS = {
    1: ["crown", "blanc", "helm", "modernia"],
    2: ["liter", "volume", "helm", "modernia"],
    3: ["liter", "volume", "crown", "blanc"],
}

# 이번에 명중을 인코딩한 슬러그 전량. 모더니아·앵커·마스트·디젤은 자기 무기가
# MG/RL이라 자기 딜은 안 변하고, 셸 안의 아군에게만 값이 간다.
HIT_RATE_SLUGS = [
    "jill-valentine", "quency-escape-queen", "nayuta", "chisato-nishikigi",
    "phantom", "phantom-signature", "dorothy-serendipity", "soda-twinkling-bunny",
    "sugar", "sugar-signature", "noir", "drake", "drake-signature",
    "miranda", "miranda-signature", "modernia", "anchor-innocent-maid",
    "mast-romantic-maid", "diesel-winter-sweets-intro",
    "diesel-winter-sweets-highlight",
]


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _tier_of(slug):
    specs, excluded = load_roster([_nikke(slug)])
    return None if excluded or not specs else specs[0].burst_tier


def _best(slug, boss):
    """(총딜, 이 유닛의 버스트 횟수) · "NO_FULL_BURST" · None.

    버스트 횟수를 같이 돌려주는 이유: 버스트에 달린 명중 불릿은 그 유닛이 그
    셸에서 버스트를 안 하면 아예 안 걸리고, 그러면 차이가 0.00%로 나와
    「배선이 안 됐다」와 구별되지 않는다.

    `"NO_FULL_BURST"`는 그보다 더한 경우다 - 이 셸로는 풀 버스트가 한 번도 안
    열려서 총딜 자체가 다른 행과 비교 불가다. 디젤: 윈터 스위츠(Highlight)가
    그렇다: `burst_delay`가 그녀를 첫 사이클에서 빼는데 이 셸에는 대신 쏠
    Burst 3이 없다. 그 조합은 `ALLOWED_SHAPES`가 못 만들게 하므로 추천 결과가
    아니라 **이 셸의 한계**다."""
    tier = _tier_of(slug)
    shell = SHELLS.get(tier)
    if shell is None or slug in shell:
        return None
    specs, excluded = load_roster([_nikke(s) for s in shell + [slug]])
    if excluded:
        return None
    best = None
    for ordering in feasible_orderings(specs):
        result = evaluate_deck(ordering, boss)
        if never_full_bursts(result):
            return "NO_FULL_BURST"
        if best is None or result["total_damage"] > best[0]:
            # `events`, not the damage log: a buffs-only burst (Jill, Sugar,
            # Chisato) records no "burst" damage entry at all, so counting the
            # log would report every one of them as never bursting.
            bursts = sum(1 for e in result["events"]
                         if e.get("type") == "burst" and e.get("slug") == slug)
            best = (result["total_damage"], bursts)
    return best


class _blind:
    """`accuracy.core_hit_rate`를 명중률 0으로 고정해 부르는 컨텍스트.

    raid_simulator가 임포트 시점에 이름을 바인딩하므로 두 모듈 다 갈아끼운다 -
    한쪽만 바꾸면 조용히 아무 일도 안 일어나고 차이가 0으로 나온다.
    """

    def __enter__(self):
        self._real = accuracy.core_hit_rate

        def blind(weapon, hit_rate, core_diameter, _real=self._real):
            return _real(weapon, 0.0, core_diameter)

        accuracy.core_hit_rate = blind
        raid_simulator.core_hit_rate = blind
        return self

    def __exit__(self, *exc):
        accuracy.core_hit_rate = self._real
        raid_simulator.core_hit_rate = self._real


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # 콘솔이 cp949라 help 문구에 em dash를 쓰면 --help가 UnicodeEncodeError로 죽는다.
    parser.add_argument("--core-diameter", type=float, default=CORE_DIAMETER_PX,
                        help=f"보스 코어 지름 px "
                             f"(기본 {CORE_DIAMETER_PX:.2f}, 애니힐리오 실측)")
    parser.add_argument("--slug", action="append",
                        help="이 슬러그만 잰다 (반복 가능)")
    args = parser.parse_args()

    boss = BossProfile(element="Water", fight_duration=180.0, core_hittable=True,
                       core_diameter_px=args.core_diameter)
    slugs = args.slug or HIT_RATE_SLUGS

    print(f"코어 지름 {args.core_diameter:g}px · 고정 셸 · 180초\n")
    print(f"{'슬러그':30} {'명중 있음':>16} {'명중 0 고정':>16} {'차이':>9}  버스트")
    rows = []
    for slug in slugs:
        measured = _best(slug, boss)
        if measured is None:
            print(f"{slug:30} {'덱을 못 만든다':>16}")
            continue
        if measured == "NO_FULL_BURST":
            print(f"{slug:30} {'이 셸로는 풀 버스트가 안 열린다 — 측정 불가':>16}")
            continue
        with_hit, bursts = measured
        with _blind():
            without, _ = _best(slug, boss)
        gain = 100.0 * (with_hit - without) / without if without else 0.0
        rows.append((gain, slug, with_hit, without, bursts))
        note = "" if bursts else "  <- 이 셸에서는 버스트를 안 한다"
        print(f"{slug:30} {with_hit:16,.0f} {without:16,.0f} {gain:+8.2f}%  {bursts:>5}{note}")

    moved = [r for r in rows if abs(r[0]) > 1e-9]
    print(f"\n{len(moved)}/{len(rows)} 슬러그의 딜이 움직였다.")
    if moved:
        top = max(moved)
        print(f"최대: {top[1]} {top[0]:+.2f}%")
    flat = [r for r in rows if abs(r[0]) <= 1e-9]
    if flat:
        print("안 움직인 슬러그 - 사유를 하나씩 확인할 것:")
        for _gain, slug, _a, _b, bursts in flat:
            why = "버스트를 안 해서 버스트 불릿이 안 걸린다" if not bursts else \
                  "자기 무기가 MG/RL이거나 셸에 받을 아군이 없다"
            print(f"  {slug}: {why}")


if __name__ == "__main__":
    main()
