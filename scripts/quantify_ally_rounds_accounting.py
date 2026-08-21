"""아군 누적 소모탄 카운터를 창마다 리셋하는 것과 전투 내내 누적하는 것이,
실제 덱의 최종 수렴된 게이지 충전 시간을 다르게 만드는가 - 이름 붙인 덱으로 잰다.

`burst_gauge.fill_times`의 `bonus_fills`(인어공주 Bubble Order, 신데렐라: 크리스탈
웨이브 Beauty-Full)는 아군이 쏜 누적 라운드 수가 문턱을 넘을 때마다 게이지를
채운다. 그 카운터를 창마다 0에서 다시 세는 것(창-상대 근사)과, 게임 원문
"total ammo expended by allies"대로 전투 시작부터 절대 안 비는 것(누적) 중
어느 쪽이 맞는지는 `docs/insights.md`의 논의를 참고 - 이 스크립트는 그 판단에
쓰인 **정량 증거**를 재현 가능하게 남긴다.

두 회계 규칙을 이 스크립트 안에 그대로 구현해(`fill_times_window_reset`이
2026-08-22 이전 버전, `fill_times_cumulative`가 그 이후 - 둘 다 실제
`app.burst_gauge.fill_times`와 별개의 순수 함수라 프로덕션 코드를 건드리지
않는다) `burst_gauge.fill_times`를 몽키패치해서 각 규칙으로 **따로 고정점까지**
수렴시킨다(반쪽짜리 비교가 아니라 회계 규칙 교체가 사이클 타이밍 자체를 바꾸는
이차 효과까지 잡기 위해서다). 사이클별 게이지·문턱 크로싱 횟수를 나란히 찍는다.

**언제 쓰나:** `fill_times`의 아군 소모탄 회계 방식(리셋 vs 누적, 문턱값,
`GAUGE_QUANTUM_SEC`)을 건드릴 때. 2026-08-22 측정: 덱2(인어공주, 문턱 400,
초당 ~118발이라 3.4초 창)에서 정상상태 채움 시간이 창-리셋 ~5.5초 -> 누적
~2.4~2.7초로 거의 반토막났다 - 문턱이 창 길이에 육박할수록 리셋 근사의 오차가
커진다. 덱3(신데렐라: CW, 문턱 200)은 창 대비 문턱이 작아 차이가 더 작지만
여전히 여러 사이클에서 갈린다.

**어떻게 읽나:** 「<-- 다르다」가 붙은 사이클이 두 회계가 갈리는 지점이다. 크로싱
횟수 차이가 원인이면(예: 2 vs 3) 창 시작 시점의 누적 위상이 정말 바뀐 것이고,
크로싱은 같은데 초 값만 다르면 그 사이클의 이전 사이클들이 갈려서 온 이차 효과다.

Usage (any cwd):
    python3 scripts/quantify_ally_rounds_accounting.py
"""
import bisect
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import burst_gauge  # noqa: E402
from app.burst_gauge import GAUGE_FULL, energy_per_hit, quantize  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402
from app.raid_simulator import MAX_FULL_BURST_PASSES, _simulate_raid_once  # noqa: E402
from app.roster import assemble_simulation_inputs  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import RECORD_BOSS, RECORD_CUBES  # noqa: E402
from roster_fixture import real_roster  # noqa: E402

# gauge_cost_named_decks.py(Task 4 fix round)와 같은 이름 붙은 덱 - 이 둘이
# `_GAUGE_FILL_BUILDERS`의 두 소비자(인어공주, 신데렐라: CW)를 각각 낀다.
DECKS = {
    2: ["little-mermaid", "mast-romantic-maid", "mint", "mihara-bonding-chain",
        "privaty-signature"],
    3: ["liter", "nayuta", "cinderella-crystal-wave-mg", "cinderella", "modernia"],
}


def _per_hit(weapon_stats):
    return {
        slug: (energy_per_hit(stats, full_charge=False), energy_per_hit(stats, full_charge=True))
        for slug, stats in weapon_stats.items() if stats.get("burst_energy_pershot")
    }


def _merged(shots_by_slug, ammo_rounds_by_slug):
    ammo_rounds_by_slug = ammo_rounds_by_slug or {}
    return sorted(
        (time, slug, is_tap, rounds)
        for slug, shots in shots_by_slug.items()
        for (time, is_tap), rounds in zip(shots, ammo_rounds_by_slug.get(slug) or [1.0] * len(shots))
    )


def fill_times_window_reset(shots_by_slug, full_burst_ends, *, weapon_stats, fight_duration,
                            ammo_rounds_by_slug=None, bonus_fills=()):
    """2026-08-22 이전 커밋의 회계 - `ally_rounds`가 창마다 0에서 다시 센다."""
    per_hit = _per_hit(weapon_stats)
    merged = _merged(shots_by_slug, ammo_rounds_by_slug)
    out, crossings = {}, {}
    for cycle_index, end in enumerate(full_burst_ends):
        gauge, ally_rounds, n = 0.0, 0.0, 0
        for time, slug, is_tap, rounds in merged:
            if time < end:
                continue
            if time >= fight_duration:
                break
            base, charged = per_hit.get(slug, (0.0, 0.0))
            gauge += base if is_tap else charged
            if bonus_fills:
                before = ally_rounds
                ally_rounds += rounds
                for fill in bonus_fills:
                    threshold = fill["every_ally_rounds"]
                    c = int(ally_rounds // threshold) - int(before // threshold)
                    if c:
                        n += c
                        gauge += c * fill["fraction"] * GAUGE_FULL
            if gauge >= GAUGE_FULL:
                out[cycle_index + 1] = quantize(time - end)
                crossings[cycle_index + 1] = n
                break
    return out, crossings


def fill_times_cumulative(shots_by_slug, full_burst_ends, *, weapon_stats, fight_duration,
                          ammo_rounds_by_slug=None, bonus_fills=()):
    """오늘 `app.burst_gauge.fill_times`가 실제로 쓰는 회계 - `ally_rounds`는
    전투 시작부터 절대 안 비고, 창은 그 시점의 누적값을 위상으로 이어받는다."""
    per_hit = _per_hit(weapon_stats)
    merged = _merged(shots_by_slug, ammo_rounds_by_slug)
    times_only = [m[0] for m in merged]
    prefix = [0.0]
    for m in merged:
        prefix.append(prefix[-1] + m[3])
    out, crossings = {}, {}
    for cycle_index, end in enumerate(full_burst_ends):
        gauge, n = 0.0, 0
        ally_rounds = prefix[bisect.bisect_left(times_only, end)] if bonus_fills else 0.0
        for time, slug, is_tap, rounds in merged:
            if time < end:
                continue
            if time >= fight_duration:
                break
            base, charged = per_hit.get(slug, (0.0, 0.0))
            gauge += base if is_tap else charged
            if bonus_fills:
                before = ally_rounds
                ally_rounds += rounds
                for fill in bonus_fills:
                    threshold = fill["every_ally_rounds"]
                    c = int(ally_rounds // threshold) - int(before // threshold)
                    if c:
                        n += c
                        gauge += c * fill["fraction"] * GAUGE_FULL
            if gauge >= GAUGE_FULL:
                out[cycle_index + 1] = quantize(time - end)
                crossings[cycle_index + 1] = n
                break
    return out, crossings


def _specs(slugs, states):
    def owner(slug):
        if slug in states:
            return states[slug]
        for base in sorted(states, key=len, reverse=True):
            if slug.startswith(base + "-"):
                return states[base]
    specs, excluded = load_roster(
        [owner(s).model_copy(update={"character_slug": s}) for s in slugs])
    assert not excluded, excluded
    for spec in specs:
        spec.cube = RECORD_CUBES.get(spec.slug, spec.cube)
    return specs


def _converge(order, boss, rule):
    """진짜 고정점까지 - `simulate_raid`와 같은 루프를 직접 돌린다(그래야 회계
    교체가 사이클 타이밍 자체를 바꾸는 이차 효과까지 반영된다)."""
    last_crossings = {}

    def wrapper(shots_by_slug, full_burst_ends, **kw):
        nonlocal last_crossings
        gauge, crossings = rule(shots_by_slug, full_burst_ends, **kw)
        last_crossings = crossings
        return gauge

    burst_gauge.fill_times = wrapper
    inputs = assemble_simulation_inputs(order)
    overrides, late_max_hp, gauge = {}, (), {}
    result = None
    for attempt in range(MAX_FULL_BURST_PASSES):
        result, resolved, resolved_max_hp, resolved_gauge = _simulate_raid_once(
            **inputs, enemy_def=boss.enemy_def,
            gauge_charge_time=boss.gauge_charge_time,
            fight_duration=boss.fight_duration, mode=boss.mode,
            core_hittable=boss.core_hittable, boss_element=boss.element,
            part_destructible=boss.part_destructible,
            part_destruction_times=boss.part_destruction_times,
            effective_range_band=boss.effective_range_band,
            pierce_hits_body_behind_core=boss.pierce_hits_body_behind_core,
            core_diameter_px=boss.core_diameter_px,
            full_burst_stage_overrides=overrides, late_flat_max_hp=late_max_hp,
            gauge_charge_overrides=gauge)
        if (resolved == overrides and resolved_max_hp == late_max_hp
                and resolved_gauge == gauge):
            return result["gauge_charge_times"], last_crossings, attempt + 1
        overrides, late_max_hp, gauge = resolved, resolved_max_hp, resolved_gauge
    return result["gauge_charge_times"], last_crossings, MAX_FULL_BURST_PASSES


def main():
    warnings.simplefilter("ignore")
    real_fill_times = burst_gauge.fill_times
    states = {s.character_slug: s for s in real_roster()}
    if not states:
        raise SystemExit("no synced roster - see roster_fixture.py")
    boss = BossProfile(**{**RECORD_BOSS, "element": "Wind", "enemy_def": 31784.0})

    for name, slugs in DECKS.items():
        specs = _specs(slugs, states)
        burst_gauge.fill_times = real_fill_times  # 좌석 선택은 오늘 코드로 - 어느 회계를 재든 같은 좌석
        order = list(max(feasible_orderings(specs),
                         key=lambda d: evaluate_deck(list(d), boss)["total_damage"]))

        old_gauge, old_crossings, old_passes = _converge(order, boss, fill_times_window_reset)
        new_gauge, new_crossings, new_passes = _converge(order, boss, fill_times_cumulative)
        burst_gauge.fill_times = real_fill_times

        print(f"\n=== 덱{name}: {[u.slug for u in order]} ===")
        print(f"  window-reset: {old_passes}패스, gauge_charge_times={old_gauge}")
        print(f"  cumulative:   {new_passes}패스, gauge_charge_times={new_gauge}")
        for c in sorted(set(old_gauge) | set(new_gauge)):
            o, n = old_gauge.get(c), new_gauge.get(c)
            oc, nc = old_crossings.get(c, 0), new_crossings.get(c, 0)
            same = "" if o == n else "  <-- 다르다"
            print(f"    사이클 {c}: window-reset {o}(크로싱 {oc}) vs cumulative {n}(크로싱 {nc}){same}")

    burst_gauge.fill_times = real_fill_times


if __name__ == "__main__":
    main()
