"""실측 덱의 채움율이 무기만으로 도달 가능한가 - 천장과 개전으로 가른다.

`check_gauge_convergence.py`가 「고정점이 멈추는가」를 묻는다면 이쪽은 **「엔진이
낼 수 있는 최대가 실측에 닿기는 하는가」**를 묻는다. 둘은 다른 실패를 잡는다.

**왜 필요한가.** 채움이 실측보다 느릴 때 원인 후보는 늘 셋이다 - 재장전 위상이
나빴거나, 케이던스가 느리거나, **세는 것이 빠졌거나**. 앞의 둘은 크기가 유한하다:
재장전도 스핀업도 위상도 전부 0인 이상적 발사가 그 덱의 **천장**이고, 실측이
그것마저 넘으면 남은 설명은 「무기 밖 채움원이 있다」 하나뿐이다. 크기 일치가
아니라 **부등식**이라 어떤 위상 이야기로도 빠져나갈 수 없다.

2026-08-22에 이 논증이 덱1의 갭을 갈랐다: 무기 천장 183,879/초에 실측 요구는
244,141/초라 33% 모자랐고, 그 차이가 아니스 별똥별의 착탄율(59,360/초)과 1.5%
안에서 같았다. 상세는 `docs/measurements/burst-gauge-fill.md`의 「후속 분석」.

**개전 대조가 같이 붙어 있는 이유.** 사이클 채움은 재장전 위상·버프·창 경계가
섞여 있어 「엔진이 왜 느린가」를 못 가른다. 개전은 전원이 탄창 만재로 t=0에
시작하고 버스트 버프가 없고 위상이 확정적이라, 발사 모델 자체가 맞는지를 **혼자**
답한다. 개전이 맞고 사이클만 틀리면 원인은 「버스트가 끝난 뒤에만 존재하는 것」
으로 좁혀진다.

**언제 쓰나:** 채움이 실측과 어긋날 때 **가장 먼저**. 무엇을 고칠지 정하기 전에
「고칠 수 있는 것인가」를 먼저 답해야 한다 - 천장을 넘는 갭은 케이던스·재장전을
아무리 만져도 안 닫힌다. 그리고 게이지가 세는 것을 바꾼 뒤 회귀 확인용으로.

**어떻게 읽나.**

- `실측/천장 <= 1`: 무기만으로 설명된다. 갭이 있다면 위상이나 재장전이다.
- `실측/천장 > 1`: **무기 밖 채움원이 반드시 있다.** 아래에 그 크기를 찍는다.
- 개전 `엔진/실측`이 1 근처면 발사 모델은 무죄다.

Usage (any cwd):
    python3 scripts/check_gauge_ceiling.py
    python3 scripts/check_gauge_ceiling.py --deck 1

천장을 넘는 덱이 하나라도 있으면 종료 코드 1.
"""
import argparse
import statistics
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app import burst_gauge  # noqa: E402
from app.deck_search import BossProfile, feasible_orderings  # noqa: E402
from app.raid_simulator import simulate_raid  # noqa: E402
from app.roster import assemble_simulation_inputs  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import RECORD_BOSS, RECORD_CUBES  # noqa: E402
from roster_fixture import real_roster  # noqa: E402

FB_LEN = 10.133

# `docs/measurements/burst-gauge-fill.md`의 「원본 - 덱 단위」와 「원본 - 덱1 버스트
# 사이클」. 덱1만 14사이클 전부의 시각이 있어 평균이 정밀하고, 나머지는 1분 눈대중
# 이라 판독을 그대로 싣고 평균을 쓴다. 덱4·5는 판독이 시간이 아니라 「쿨타임에 거의
# 맞음」·「좋음」이라 이 대조에 못 들어온다.
MEASURED_DECKS = {
    1: {
        "slugs": ["anis-star", "brid-silent-track", "crown", "rapi-red-hood",
                  "diesel-winter-sweets-highlight"],
        "fills": [2.048],
        "opening": 3.117,        # 전투 시작 21.000 -> 첫 충전완료 24.117
    },
    2: {
        "slugs": ["little-mermaid", "mast-romantic-maid", "mint",
                  "mihara-bonding-chain", "privaty-signature"],
        "fills": [3.7, 3.8],
    },
    3: {
        "slugs": ["liter", "nayuta", "cinderella-crystal-wave-mg", "cinderella",
                  "modernia"],
        "fills": [3.5, 3.1, 2.85, 2.7, 2.55],
    },
}


def _owner(states, slug):
    """애장품/시그니처 변형은 기본 슬러그의 투자 상태를 물려받는다."""
    if slug in states:
        return states[slug]
    for base in sorted(states, key=len, reverse=True):
        if slug.startswith(base + "-"):
            return states[base]
    raise KeyError(slug)


def _run(slugs):
    """이 덱을 한 번 돌리고 `fill_times`가 받은 입력을 통째로 잡아 온다."""
    captured = {}
    real = burst_gauge.fill_times

    def spy(shots_by_slug, full_burst_ends, **kw):
        captured.update(shots=shots_by_slug, ends=full_burst_ends, kw=kw)
        return real(shots_by_slug, full_burst_ends, **kw)

    states = {s.character_slug: s for s in real_roster()}
    specs, _ = load_roster(
        [_owner(states, s).model_copy(update={"character_slug": s}) for s in slugs])
    for spec in specs:
        spec.cube = RECORD_CUBES.get(spec.slug, spec.cube)
    boss = BossProfile(**{**RECORD_BOSS, "element": "Wind", "enemy_def": 31784.0})
    order = list(feasible_orderings(specs))[0]
    burst_gauge.fill_times = spy
    try:
        simulate_raid(
            **assemble_simulation_inputs(order), enemy_def=boss.enemy_def,
            gauge_charge_time=boss.gauge_charge_time,
            fight_duration=boss.fight_duration, mode=boss.mode,
            core_hittable=boss.core_hittable, boss_element=boss.element,
            part_destructible=boss.part_destructible,
            part_destruction_times=boss.part_destruction_times,
            effective_range_band=boss.effective_range_band,
            pierce_hits_body_behind_core=boss.pierce_hits_body_behind_core,
            core_diameter_px=boss.core_diameter_px)
    finally:
        burst_gauge.fill_times = real
    return captured, boss


def _energy_events(captured, boss):
    """(시각, 슬러그, 에너지) - 무기 샷과 스킬 타격을 게이지가 세는 대로 합친다."""
    kw = captured["kw"]
    stats = kw["weapon_stats"]
    speed_at = kw.get("speed_multiplier_at") or (lambda slug, time: 1.0)
    out = []
    for slug, rec in captured["shots"].items():
        st = stats.get(slug) or {}
        if not st.get("burst_energy_pershot"):
            continue
        base = burst_gauge.energy_per_hit(st, full_charge=False)
        charged = burst_gauge.energy_per_hit(st, full_charge=True)
        out += [(t, slug, (base if tap else charged) * speed_at(slug, t))
                for t, tap in rec if t < boss.fight_duration]
    for slug, hits in (kw.get("skill_hits_by_slug") or {}).items():
        st = stats.get(slug) or {}
        if not st.get("burst_energy_pershot"):
            continue
        base = burst_gauge.energy_per_hit(st, full_charge=False)
        out += [(t, slug, base * n * speed_at(slug, t))
                for t, n in hits if t < boss.fight_duration]
    out.sort()
    return out


def _opening_fill(captured, boss):
    """개전 게이지가 가득 차는 시각. 못 채우면 None."""
    total = 0.0
    for time, _, energy in _energy_events(captured, boss):
        total += energy
        if total >= burst_gauge.GAUGE_FULL:
            return time
    return None


def _bonus_ceiling(captured, cadences):
    """`bonus_fills`가 이상적 발사에서 내는 초당 에너지.

    무기 타격과 달리 이쪽은 **트리거 종류마다 세는 것이 다르다** - 아군 누적
    소모탄은 스쿼드 전체의 라운드 소모율에 걸리고, 자기 풀차지는 그 좌석의
    케이던스에 걸린다. 천장이므로 재장전·위상은 없다고 본다.
    """
    kw = captured["kw"]
    fills = kw.get("bonus_fills") or ()
    if not fills:
        return 0.0
    rounds_by_slug = kw.get("ammo_rounds_by_slug") or {}
    # 이상적 발사에서의 스쿼드 라운드 소모율. 한 샷이 회계하는 라운드 수는
    # 좌석마다 다르다(탄약 주머니를 쓰는 아군은 한 발이 수백 라운드다).
    ally_rounds_per_sec = 0.0
    for slug, cadence in cadences.items():
        rounds = rounds_by_slug.get(slug) or []
        per_shot = statistics.mean(rounds) if rounds else 1.0
        if cadence:
            ally_rounds_per_sec += per_shot / cadence
    total = 0.0
    for fill in fills:
        if "every_ally_rounds" in fill:
            crossings = ally_rounds_per_sec / fill["every_ally_rounds"]
            total += crossings * fill["fraction"] * burst_gauge.GAUGE_FULL
        elif "every_own_full_charge" in fill:
            cadence = cadences.get(fill["every_own_full_charge"])
            if cadence:
                total += fill["fraction"] * burst_gauge.GAUGE_FULL / cadence
    return total


def check(number, spec):
    captured, boss = _run(spec["slugs"])
    kw = captured["kw"]
    stats = kw["weapon_stats"]
    speed_at = kw.get("speed_multiplier_at") or (lambda slug, time: 1.0)
    ends = [e for e in captured["ends"] if e < boss.fight_duration]
    table = burst_gauge.fill_times(captured["shots"], captured["ends"], **kw)
    engine = [v for v in table.values() if v != float("inf")]
    measured = statistics.mean(spec["fills"])
    energy = burst_gauge.GAUGE_FULL

    print(f"\n=== 덱 {number}: {', '.join(spec['slugs'])}")
    print(f"  실측 채움 {measured:.3f}초 = {energy / measured:,.0f}/초"
          f"   엔진 {statistics.mean(engine):.3f}초 = "
          f"{energy / statistics.mean(engine):,.0f}/초")

    if spec.get("opening"):
        got = _opening_fill(captured, boss)
        if got:
            print(f"  개전 채움  엔진 {got:.3f}초  실측 {spec['opening']:.3f}초"
                  f"  → 엔진/실측 {got / spec['opening']:.2f}"
                  f"   ({'발사 모델 무죄' if abs(got / spec['opening'] - 1) < 0.15 else '발사 모델도 어긋난다'})")

    print(f"  {'좌석':34s} {'케이던스':>9s} {'발당':>10s} {'천장/초':>11s}")
    ceiling = 0.0
    cadences = {}
    for slug in spec["slugs"]:
        rec = captured["shots"].get(slug)
        st = stats.get(slug) or {}
        if not rec or not st.get("burst_energy_pershot"):
            print(f"  {slug:34s} {'(게이지값 없음)':>9s}")
            continue
        times = sorted(t for t, _ in rec)
        gaps = [b - a for a, b in zip(times, times[1:])]
        # 중앙값은 재장전·스핀업이 아니라 **그 무기가 연속 발사할 때의** 간격이다.
        cadence = statistics.median(gaps) if gaps else float("inf")
        cadences[slug] = cadence
        per = (burst_gauge.energy_per_hit(st, full_charge=True)
               * speed_at(slug, (ends[0] + 1.0) if ends else 1.0))
        rate = per / cadence if cadence else 0.0
        ceiling += rate
        print(f"  {slug:34s} {cadence:9.3f} {per:10,.0f} {rate:11,.0f}")

    # 스킬 타격은 **창 밖에 남는 몫만** 천장에 얹는다 - 창 안 타격은 게이지가 안 센다.
    windows = [(e - FB_LEN, e) for e in ends]
    outside = boss.fight_duration - sum(
        min(b, boss.fight_duration) - a for a, b in windows
        if a < boss.fight_duration)
    skill_rate = 0.0
    for slug, hits in (kw.get("skill_hits_by_slug") or {}).items():
        st = stats.get(slug) or {}
        if not st.get("burst_energy_pershot"):
            continue
        base = burst_gauge.energy_per_hit(st, full_charge=False)
        count = sum(n for t, n in hits
                    if t < boss.fight_duration
                    and not any(a <= t <= b for a, b in windows))
        skill_rate += base * count * speed_at(slug, 1.0) / outside
    if skill_rate:
        print(f"  {'(창 밖 스킬 타격)':34s} {'':9s} {'':10s} {skill_rate:11,.0f}")

    bonus_rate = _bonus_ceiling(captured, cadences)
    if bonus_rate:
        print(f"  {'(스킬이 선언한 플랫 충전)':34s} {'':9s} {'':10s} {bonus_rate:11,.0f}")

    total = ceiling + skill_rate + bonus_rate
    need = energy / measured
    over = need > total
    print(f"  천장 합계 {total:,.0f}/초   실측 요구 {need:,.0f}/초"
          f"   → 실측/천장 = {need / total:.2f}")

    # **천장은 엔진이 실제로 낸 값보다 낮을 수 없다.** 낮다면 이 스크립트가 채움원을
    # 하나 안 세고 있다는 뜻이고, 그러면 「천장을 넘는다」는 결론이 통째로 무효다 -
    # 이 가드가 없던 첫 판에서 덱3이 `bonus_fills` 누락으로 그 자리에 앉았다.
    engine_rate = energy / statistics.mean(engine)
    if total < engine_rate:
        print(f"  ⚠ 천장({total:,.0f})이 엔진 실효율({engine_rate:,.0f})보다 낮다 —"
              " 이 스크립트가 채움원을 빠뜨렸다. 위 판정을 믿지 말 것")
        return "broken"

    if over:
        missing = (need - total) * measured
        print(f"  ★ 천장을 {need / total - 1:.0%} 넘는다 — 무기 밖 채움원이 사이클마다"
              f" {missing:,.0f} (게이지의 {missing / energy:.1%}) 있어야 한다")
    else:
        print(f"  천장 안 ({need / total:.0%}) — 무기만으로 설명된다")
    return over


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--deck", type=int, choices=sorted(MEASURED_DECKS),
                        help="이 덱 하나만 본다 (기본: 판독이 있는 덱 전부)")
    args = parser.parse_args()
    warnings.simplefilter("ignore")

    numbers = [args.deck] if args.deck else sorted(MEASURED_DECKS)
    results = {n: check(n, MEASURED_DECKS[n]) for n in numbers}
    broken = [n for n, r in results.items() if r == "broken"]
    over = [n for n, r in results.items() if r is True]
    if broken:
        print(f"\n천장이 엔진보다 낮게 나온 덱: {broken} — 판정 이전에 이 스크립트를"
              " 고쳐야 한다")
        return 2
    if over:
        print(f"\n천장을 넘는 덱: {over} — 이 덱들의 갭은 케이던스·재장전을 만져서"
              " 못 닫는다")
        return 1
    print("\n판독이 있는 덱이 전부 천장 안에 있다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
