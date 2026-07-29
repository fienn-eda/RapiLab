# 차지 창 계산기 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 흑련·리버렐리오·네온이 FB 10초 창 안에 몇 발 쏘는지, 그리고 다음 타수를 사려면 차지속도 오버로드를 얼마나 붙여야 하는지 보여주는 화면을 만든다.

**Architecture:** 계산 코어는 `attack_rate`의 기존 간격 공식과 `registry`의 모션 딜레이를 재사용하는 순수 모듈이다. 그 위에 로스터 상태를 코어 입력으로 바꾸는 조립층, `POST /api/charge-window` 엔드포인트, React 새 탭이 얹힌다. 새 상수를 하나도 정의하지 않는 것이 설계의 핵심이다 — 엔진이 실측을 반영해 값을 고치면 계산기가 자동으로 따라온다.

**Tech Stack:** Python 3 · FastAPI · pytest (백엔드) / React + Vite + TypeScript · vitest + Testing Library (프론트)

## Global Constraints

- 설계 근거는 `docs/superpowers/specs/2026-07-29-charge-window-calculator-design.md`. 이 계획과 어긋나면 스펙이 우선이다.
- **새 게임 상수를 정의하지 않는다.** 차지시간·모션딜레이·탄창·재장전·큐브·오버로드는 전부 기존 로더에서 읽는다. 스킬 텍스트에서 오는 두 값(흑련 아수라 최대장탄, 리버렐리오 Calm Depths 감소초)은 해당 유닛 모듈에 이름 붙인 함수를 만들고 **스킬 규칙 빌더와 계산기가 그 함수를 공유**한다.
- FB 창 길이는 `WindowInputs.window_seconds` 기본값 **10.0초**.
- 리버렐리오의 시전자 기준 감소는 `charge_time_reduction_sec` (절대 초), 오버로드 차지속도는 `charge_speed_percent` (비율, 0.0286 = 2.86%). 두 스탯을 섞지 않는다.
- 백엔드 주석·docstring은 영어. 예외는 `api.py` 의 **라우트 docstring**과 사용자에게 그대로 보이는 문자열로, 기존 코드가 한국어를 쓴다(`engine_version_route` 참고). 프론트 사용자 문구는 한국어.
- 작업 디렉터리는 `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\charge-frame-snap`. 백엔드 명령은 `backend/`에서, 프론트 명령은 `frontend/`에서 실행한다.
- 기준선: 백엔드 `1561 passed, 3 skipped`. 어떤 작업도 이 수를 줄이면 안 된다. 각 작업이 적은 절대 개수는 그 작업까지의 누적치이며, **줄어들지 않는 것**이 실제 게이트다.
- **이 워크트리에는 `frontend/node_modules`가 없다.** Task 6을 시작하기 전에 `cd frontend && npm install`을 한 번 실행한다. 하지 않으면 모든 vitest 명령이 `ERR_MODULE_NOT_FOUND`로 죽는다.

**스펙에서 의도적으로 벗어나는 것 하나:** 스펙의 "자동 채움 값 옆에 **동기화 시각**을 적는다"는 구현하지 않는다. `frontend/src/types/profile.ts`의 `Profile`에 타임스탬프 필드가 없고, 추가하려면 프로필 저장 포맷과 `upsertProfile` 마이그레이션까지 건드려야 해서 이 기능의 범위를 넘는다. 대신 입력 필드가 "비우면 동기화된 로스터 값"임을 명시하고 언제든 덮어쓸 수 있게 둔다 — 스펙이 실제로 요구한 것(값이 낡을 수 있음을 알리고 수정 가능하게)은 그것으로 충족된다.

---

### Task 1: 계산 코어 — 샷 시각과 타수 분포

**Files:**
- Create: `backend/app/charge_window.py`
- Test: `backend/tests/test_charge_window.py`

**Interfaces:**
- Consumes: `app.attack_rate.shot_interval_with_speed(charge_time, charge_speed_percent, flat_reduction_sec=0.0, motion_delay=0.0) -> float`, `app.attack_rate.reload_time_with_speed(reload_time, reload_speed_percent) -> float`
- Produces:
  - `WindowInputs` (frozen dataclass) — 필드: `charge_time: float`, `motion_delay: float`, `max_ammo: int`, `reload_time: float`, `charge_speed_percent: float`, `charge_time_reduction_sec: float`, `reload_speed_percent: float`, `window_seconds: float = 10.0`
  - `shot_interval(inputs: WindowInputs) -> float`
  - `shot_times(inputs: WindowInputs, start_charged: bool) -> list[float]`
  - `reload_intervenes(inputs: WindowInputs) -> bool`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_charge_window.py` 를 새로 만들고 아래를 넣는다.

```python
"""FB 창 안의 샷 타임라인 (docs/superpowers/specs/2026-07-29-charge-window-calculator-design.md)."""
import pytest

from app.charge_window import WindowInputs, reload_intervenes, shot_interval, shot_times

# Scarlet: Black Shadow as Fienn actually measured her (2026-07-29): a 0.30 sec
# charge, a 0.43 sec motion delay, and a 2.86% charge-speed overload too small
# to buy a frame of an 18-frame charge. Magazine is large enough that no reload
# lands inside the window, so these cases isolate the cadence.
SCARLET = WindowInputs(
    charge_time=0.30,
    motion_delay=0.43,
    max_ammo=22,
    reload_time=2.0,
    charge_speed_percent=0.0286,
    charge_time_reduction_sec=0.0,
    reload_speed_percent=0.2969,
)
LIBERALIO_CUT = 0.1274 * 1.5  # 0.1911 sec, her caster-based grant


def test_interval_reproduces_the_solo_measurement():
    # 14 shots 0.72998 sec apart. A third of a frame is the tolerance.
    assert shot_interval(SCARLET) == pytest.approx(0.72998, abs=1 / 180)


def test_interval_reproduces_the_liberalio_measurement():
    # Two runs, 0.52923 and 0.52709 sec. Carrying the unfloored 0.1089 charge
    # would give 0.5389 and fail both.
    buffed = dataclasses_replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    for measured in (0.52923, 0.52709):
        assert shot_interval(buffed) == pytest.approx(measured, abs=1 / 180)


def test_start_charged_lands_a_shot_at_zero():
    times = shot_times(SCARLET, start_charged=True)
    assert times[0] == pytest.approx(0.0)


def test_starting_empty_delays_the_first_shot_by_one_interval():
    times = shot_times(SCARLET, start_charged=False)
    assert times[0] == pytest.approx(shot_interval(SCARLET))


def test_every_shot_lands_strictly_inside_the_window():
    for start_charged in (True, False):
        times = shot_times(SCARLET, start_charged=start_charged)
        assert times, "the window must fit at least one shot"
        assert max(times) < SCARLET.window_seconds


def test_starting_charged_is_worth_exactly_one_shot_when_no_reload_lands():
    charged = len(shot_times(SCARLET, start_charged=True))
    empty = len(shot_times(SCARLET, start_charged=False))
    assert charged - empty == 1


def test_a_small_magazine_forces_a_reload_inside_the_window():
    small = dataclasses_replace(SCARLET, max_ammo=5)
    assert reload_intervenes(small) is True
    assert reload_intervenes(SCARLET) is False


def test_the_reload_gap_is_the_cube_buffed_one():
    # 5 rounds at 0.73 sec empty the magazine at 3.65 sec; the sixth shot comes
    # one buffed reload plus one charge later. reload_time_with_speed is the
    # engine's, so this test pins that the calculator does not restate it.
    from app.attack_rate import reload_time_with_speed

    small = dataclasses_replace(SCARLET, max_ammo=5)
    times = shot_times(small, start_charged=False)
    gap = times[5] - times[4]
    expected = reload_time_with_speed(2.0, 0.2969) + shot_interval(small)
    assert gap == pytest.approx(expected)


def dataclasses_replace(inputs, **changes):
    import dataclasses

    return dataclasses.replace(inputs, **changes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_charge_window.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.charge_window'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/charge_window.py`:

```python
"""How many normal attacks a charge weapon lands inside one Full Burst window.

The cadence itself is NOT computed here - `attack_rate.shot_interval_with_speed`
owns it, including the motion delay and the frame grid the charge snaps to. This
module only walks that interval across a 10-second window, spending magazine and
reloading when it runs out, so a re-measured charge time or delay moves the
calculator without anyone editing it.

The magazine is assumed FULL at window start. For Scarlet: Black Shadow that is
a fact - Fleetly Fading: Asura reloads her instantly on Full Burst entry - and
for Liberalio and Neon it is an assumption the UI states, since nothing records
how much they fired just before the window opened.
"""
from dataclasses import dataclass

from app.attack_rate import reload_time_with_speed, shot_interval_with_speed


@dataclass(frozen=True)
class WindowInputs:
    charge_time: float
    motion_delay: float
    max_ammo: int                      # overload and self-buffs already folded in
    reload_time: float
    charge_speed_percent: float
    charge_time_reduction_sec: float   # Liberalio's caster-based grant, in seconds
    reload_speed_percent: float
    window_seconds: float = 10.0


def shot_interval(inputs: WindowInputs) -> float:
    return shot_interval_with_speed(
        inputs.charge_time,
        inputs.charge_speed_percent,
        inputs.charge_time_reduction_sec,
        motion_delay=inputs.motion_delay,
    )


def shot_times(inputs: WindowInputs, start_charged: bool) -> list[float]:
    """Shot timestamps strictly inside [0, window_seconds).

    `start_charged` is the phase the window opens at: a charge that completed
    exactly as the window opened fires at t=0, an empty one fires a full
    interval later. Fienn's three measured runs opened at 0.05, 0.29 and 0.39
    sec, so neither end is the normal case - the caller reports both.
    """
    interval = shot_interval(inputs)
    reload_gap = reload_time_with_speed(inputs.reload_time, inputs.reload_speed_percent)
    times = []
    time = 0.0 if start_charged else interval
    fired = 0
    while time < inputs.window_seconds:
        times.append(time)
        fired += 1
        if fired >= inputs.max_ammo:
            time += reload_gap
            fired = 0
        time += interval
    return times


def reload_intervenes(inputs: WindowInputs) -> bool:
    """Whether the magazine empties before the window closes. When it does, the
    last shot depends on the reload formula, which is a known open question -
    see docs/engine-gaps.md. The UI warns instead of quietly answering."""
    return inputs.max_ammo * shot_interval(inputs) < inputs.window_seconds
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_charge_window.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/charge_window.py backend/tests/test_charge_window.py
git commit -m "Walk a charge weapon's shots across one Full Burst window"
```

---

### Task 2: 계산 코어 — 차지속도 계단과 타수 분포

**Files:**
- Modify: `backend/app/charge_window.py`
- Test: `backend/tests/test_charge_window.py`

**Interfaces:**
- Consumes: Task 1의 `WindowInputs`, `shot_interval`, `shot_times`
- Produces:
  - `aggregate_charge_speed(lines: list[float], charge_time: float) -> float` — 줄 목록(퍼센트 단위, 2.86 = 2.86%)을 엔진 규칙(생합계)으로 비율(0.0286)로 바꾼다
  - `near_frame_boundary(lines: list[float], charge_time: float) -> bool`
  - `charge_speed_steps(charge_time: float) -> list[float]` — 프레임 한 칸씩 오르는 최소 비율들
  - `Outcome` (frozen dataclass) — `low_shots: int`, `low_probability: float`, `high_shots: int`, `high_probability: float`
  - `outcome(inputs: WindowInputs) -> Outcome`
  - `Threshold` (frozen dataclass) — `charge_speed_percent: float`, `interval: float`, `outcome: Outcome`
  - `thresholds(inputs: WindowInputs) -> list[Threshold]`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_charge_window.py` 끝에 이어 붙인다.

```python
from app.charge_window import (aggregate_charge_speed, charge_speed_steps,
                               near_frame_boundary, outcome, thresholds)


def test_charge_speed_steps_are_one_frame_apart():
    # Scarlet charges in 0.30 sec = 18 frames, so a frame costs 1/18 = 5.56%.
    steps = charge_speed_steps(0.30)
    assert steps[0] == pytest.approx(0.0)
    assert steps[1] == pytest.approx(1 / 18)
    assert steps[2] == pytest.approx(2 / 18)
    assert len(steps) == 19  # 0 frames through 18 (a charge of zero)


def test_a_step_below_the_next_frame_changes_nothing():
    # 2.86% and 5.0% both floor to zero frames of an 18-frame charge.
    quiet = dataclasses_replace(SCARLET, charge_speed_percent=0.05)
    assert shot_interval(quiet) == pytest.approx(shot_interval(SCARLET))


def test_aggregate_sums_the_lines_and_returns_a_ratio():
    assert aggregate_charge_speed([2.86], 0.30) == pytest.approx(0.0286)
    assert aggregate_charge_speed([4.33, 4.33], 0.30) == pytest.approx(0.0866)
    assert aggregate_charge_speed([], 0.30) == pytest.approx(0.0)


def test_a_total_near_a_frame_boundary_is_flagged():
    # The engine sums raw; the community reports per-line rounding. The two
    # disagree on 6.7% of combinations and every one sits within 1.10 points of
    # a frame boundary, so the total alone is enough to warn. 5.51% is one such
    # case: raw gives 0 frames, rounding to 6% would give 1.
    assert near_frame_boundary([5.51], 0.30) is True
    # 8.66% is 1.56 frames - far enough from both 5.56 and 11.11 to be safe.
    assert near_frame_boundary([4.33, 4.33], 0.30) is False


def test_outcome_splits_the_window_between_two_shot_counts():
    # At 0.53 sec a 10-second window holds 18.87 intervals, so the phase decides
    # between 19 and 18, and 19 comes up 87% of the time.
    buffed = dataclasses_replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    got = outcome(buffed)
    assert got.high_shots == 19
    assert got.low_shots == 18
    assert got.high_probability == pytest.approx(0.868, abs=0.005)
    assert got.low_probability == pytest.approx(1 - got.high_probability)


def test_thresholds_only_list_charge_speeds_that_change_the_interval():
    buffed = dataclasses_replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    got = thresholds(buffed)
    assert [round(t.charge_speed_percent * 100, 2) for t in got][:5] == [
        0.0, 5.56, 11.11, 16.67, 22.22]
    intervals = [t.interval for t in got]
    assert intervals == sorted(intervals, reverse=True), "each step must be faster"


def test_thresholds_carry_the_shot_counts_fienn_asked_about():
    buffed = dataclasses_replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    by_percent = {round(t.charge_speed_percent * 100, 2): t.outcome for t in thresholds(buffed)}
    assert by_percent[0.0].high_shots == 19
    assert by_percent[5.56].high_shots == 20
    assert by_percent[11.11].high_shots == 21
    assert by_percent[22.22].high_shots == 22


def test_a_small_magazine_caps_the_shots_no_matter_the_charge_speed():
    """Charge speed is wasted money once the magazine, not the cadence, is the
    binding constraint - the reload eats whatever the faster charge bought."""
    small = dataclasses_replace(SCARLET, max_ammo=6,
                                charge_time_reduction_sec=LIBERALIO_CUT)
    counts = {t.outcome.high_shots for t in thresholds(small)}
    roomy = dataclasses_replace(SCARLET, max_ammo=22,
                                charge_time_reduction_sec=LIBERALIO_CUT)
    assert max(counts) < max(t.outcome.high_shots for t in thresholds(roomy))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_charge_window.py -v`
Expected: FAIL — `ImportError: cannot import name 'aggregate_charge_speed'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/charge_window.py` 의 import 줄을 바꾸고 파일 끝에 추가한다.

import 줄을 이렇게 바꾼다:

```python
from dataclasses import dataclass

from app.attack_rate import (FRAME_SECONDS, reload_time_with_speed,
                             shot_interval_with_speed)
```

파일 끝에 추가:

```python
# How far from a frame boundary a charge-speed total has to be before the
# engine's aggregation rule and the community's can no longer disagree. The
# engine sums the raw lines and floors once; community sources report each line
# rounding to a whole percent, with equal values summed before rounding
# (arca.live/b/nikketgv/169159561). Across every 1-to-4 line combination the two
# differ on 6.7%, and all of those sit within this many percentage points of a
# boundary - so a total alone is enough to flag the doubt. Which rule is right
# is unresolved: every measurement we hold fails to separate them, and overload
# options roll at random so a player cannot compose a decisive one on demand.
BOUNDARY_TOLERANCE_POINTS = 1.10


def aggregate_charge_speed(lines: list[float], charge_time: float) -> float:
    """Overload charge-speed lines (in percent) as the ratio the engine wants.

    `charge_time` is unused today - the engine's rule needs only the sum - and
    is in the signature because the alternative rule quantises against it. If
    the per-line rounding is ever confirmed, this function is the only thing
    that changes.
    """
    return sum(lines) / 100


def near_frame_boundary(lines: list[float], charge_time: float) -> bool:
    """Whether this total sits close enough to a frame boundary that the two
    aggregation rules could disagree - see BOUNDARY_TOLERANCE_POINTS."""
    total_points = sum(lines)
    frames = charge_time / FRAME_SECONDS
    if frames <= 0:
        return False
    points_per_frame = 100 / frames
    return any(
        abs(total_points - points_per_frame * step) <= BOUNDARY_TOLERANCE_POINTS
        for step in range(int(frames) + 1)
    )


def charge_speed_steps(charge_time: float) -> list[float]:
    """Every charge-speed ratio that buys one more frame, and nothing between.

    Charge speed lands in whole frames, so the useful values are enumerable
    rather than searchable: a 0.30 sec charge is 18 frames and moves only every
    1/18 = 5.56%. Anything in between is money that changes no number.
    """
    frames = int(round(charge_time / FRAME_SECONDS))
    return [step / frames for step in range(frames + 1)]


@dataclass(frozen=True)
class Outcome:
    low_shots: int
    low_probability: float
    high_shots: int
    high_probability: float


@dataclass(frozen=True)
class Threshold:
    charge_speed_percent: float
    interval: float
    outcome: Outcome


def outcome(inputs: WindowInputs) -> Outcome:
    """The two shot counts this cadence can produce, and how often each.

    The phase the window opens at is not the player's to choose - Fienn's three
    runs opened at 0.05, 0.29 and 0.39 sec - so a single number would be either
    an over- or under-statement. Reporting the guaranteed count alone hides that
    Scarlet reads 19 shots 87% of the time at zero charge speed.

    The split is exact only while the magazine outlasts the window. Once a
    reload lands inside it the shots are no longer evenly spaced and the
    fraction is an approximation - which is what `reload_intervenes` exists to
    warn about, since the reload formula is itself unsettled.
    """
    low = len(shot_times(inputs, start_charged=False))
    high = len(shot_times(inputs, start_charged=True))
    if high == low:
        return Outcome(low, 1.0, high, 0.0)
    high_probability = inputs.window_seconds / shot_interval(inputs) - low
    high_probability = min(1.0, max(0.0, high_probability))
    return Outcome(low, 1.0 - high_probability, high, high_probability)


def thresholds(inputs: WindowInputs) -> list[Threshold]:
    """One row per charge-speed step that actually changes the cadence."""
    import dataclasses

    rows, previous = [], None
    for step in charge_speed_steps(inputs.charge_time):
        stepped = dataclasses.replace(inputs, charge_speed_percent=step)
        interval = shot_interval(stepped)
        if previous is not None and interval == previous:
            continue
        previous = interval
        rows.append(Threshold(step, interval, outcome(stepped)))
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_charge_window.py -v`
Expected: PASS (16 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/charge_window.py backend/tests/test_charge_window.py
git commit -m "Enumerate the charge-speed steps that actually buy a shot"
```

---

### Task 3: 스킬값 두 개를 유닛 모듈에서 공유 가능하게 꺼낸다

**Files:**
- Modify: `backend/app/skill_rules/scarlet_black_shadow.py`
- Modify: `backend/app/skill_rules/liberalio.py:122-154`
- Test: `backend/tests/test_charge_window_inputs.py`

**Interfaces:**
- Produces:
  - `app.skill_rules.scarlet_black_shadow.full_burst_max_ammo_percent(values: dict) -> float` — 아수라의 최대장탄 증가를 비율로 (0.60 = +60%)
  - `app.skill_rules.liberalio.calm_depths_charge_cut_seconds(values: dict, caster_weapon_stats: dict) -> float` — 시전자 기준 감소를 초로 (0.1911)
- 두 함수는 기존 규칙 빌더가 **호출**해야 한다. 값을 두 곳에 적으면 이 작업의 목적이 사라진다.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_charge_window_inputs.py` 를 새로 만든다.

```python
"""The two skill-text values the calculator needs, shared with the rule builders.

These live in the unit modules rather than in the calculator so there is exactly
one place each value is read. A copy in the calculator would drift silently the
day a skill level or a weapon stat changes.
"""
from app.skill_rules.liberalio import calm_depths_charge_cut_seconds
from app.skill_rules.scarlet_black_shadow import full_burst_max_ammo_percent


def test_asura_max_ammo_is_read_as_a_ratio():
    values = {"fleetly_fading_asura": {"description_value_01": "60",
                                       "description_value_02": "10",
                                       "description_value_03": "100"}}
    assert full_burst_max_ammo_percent(values) == 0.60


def test_calm_depths_cut_is_the_percent_times_the_casters_own_charge():
    # "Charge Speed +12.74% of the skill user's" on a 1.5 sec Sniper Rifle is
    # 0.1911 sec for the recipient - an absolute figure that does NOT scale with
    # whoever receives it.
    values = {"calm_depths": {"description_value_07": "12.74",
                              "description_value_08": "10"}}
    assert calm_depths_charge_cut_seconds(values, {"charge_time": 1.5}) == 0.1274 * 1.5


def test_the_rule_hands_out_exactly_what_the_shared_function_returns():
    """Pin that the builder did not keep its own copy of the arithmetic. Fires
    the real rule through a real registry - the same way
    test_skill_rules_burst3_eb1 exercises Calm Depths - and compares the effect
    it granted against the shared function's answer."""
    from app.effects import EffectRegistry
    from app.skill_rules.liberalio import build_calm_depths_charge_rules
    from app.squad_engine import SquadContext, SquadMember, fire_trigger

    values = {"calm_depths": {"description_value_07": "12.74",
                              "description_value_08": "10"}}
    weapon = {"charge_time": 1.5}
    rules = {"liberalio": build_calm_depths_charge_rules(values, weapon)}
    ctx = SquadContext(
        [
            SquadMember("liberalio", burst_tier=3, element="Wind"),
            SquadMember("scarlet-black-shadow", burst_tier=3, element="Wind"),
        ],
        base_atk={"liberalio": 400_000, "scarlet-black-shadow": 300_000},
    )
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    granted = registry.total_for(
        "charge_time_reduction_sec",
        {"slug": "scarlet-black-shadow", "element": "Wind"}, now=5.0)
    assert granted == calm_depths_charge_cut_seconds(values, weapon)
```

`EffectRegistry` 의 import 경로가 `app.effects` 가 아니면 `backend/tests/test_skill_rules_burst3_eb1.py` 상단이 무엇을 import하는지 보고 그것을 그대로 쓴다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_charge_window_inputs.py -v`
Expected: FAIL — `ImportError: cannot import name 'full_burst_max_ammo_percent'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/skill_rules/scarlet_black_shadow.py` 에서 `build_scarlet_black_shadow_rules` **바로 위**에 함수를 추가한다:

```python
def full_burst_max_ammo_percent(values):
    """Fleetly Fading: Asura's Max Ammunition Capacity grant, as a ratio.

    Shared with charge_window_inputs: her magazine size decides whether a reload
    lands inside the Full Burst window, so the calculator needs the same number
    the rule below applies."""
    return float(values["fleetly_fading_asura"]["description_value_01"]) / 100
```

그리고 같은 파일의 `build_scarlet_black_shadow_rules` 안에서 `max_ammo` 를 그 함수로 바꾼다. 기존 두 줄

```python
    asura = values["fleetly_fading_asura"]
    max_ammo = float(asura["description_value_01"]) / 100
    max_ammo_duration = float(asura["description_value_02"])
```

를 이렇게 바꾼다:

```python
    asura = values["fleetly_fading_asura"]
    max_ammo = full_burst_max_ammo_percent(values)
    max_ammo_duration = float(asura["description_value_02"])
```

`backend/app/skill_rules/liberalio.py` 에서 `build_calm_depths_charge_rules` **바로 위**에 함수를 추가한다:

```python
def calm_depths_charge_cut_seconds(values: dict, caster_weapon_stats: dict) -> float:
    """Calm Depths' caster-based grant, in absolute seconds.

    Shared with charge_window_inputs so the calculator and the rule below cannot
    disagree about what she hands an ally."""
    percent = float(values["calm_depths"]["description_value_07"]) / 100
    return percent * float(caster_weapon_stats["charge_time"])
```

같은 파일 `build_calm_depths_charge_rules` 안의 네 줄

```python
    calm = values["calm_depths"]
    percent = float(calm["description_value_07"]) / 100
    duration = float(calm["description_value_08"])
    seconds = percent * float(caster_weapon_stats["charge_time"])
```

를 이렇게 바꾼다:

```python
    calm = values["calm_depths"]
    duration = float(calm["description_value_08"])
    seconds = calm_depths_charge_cut_seconds(values, caster_weapon_stats)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_charge_window_inputs.py tests/test_skill_rules_scarlet_black_shadow.py tests/test_skill_rules_burst3_eb1.py -v`
Expected: PASS — 새 테스트 3개 + 기존 흑련·리버렐리오 테스트 전부

- [ ] **Step 5: Run the full suite to prove nothing moved**

Run: `cd backend && python -m pytest -q`
Expected: `1580 passed, 3 skipped` (기준선 1561 + Task 1·2의 16 + 이 작업의 3). 정확한 수보다 **줄지 않았는지**가 게이트다 — 줄었다면 기존 흑련·리버렐리오 테스트를 깨뜨린 것이므로 되돌린다.

- [ ] **Step 6: Commit**

```bash
git add backend/app/skill_rules/scarlet_black_shadow.py backend/app/skill_rules/liberalio.py backend/tests/test_charge_window_inputs.py
git commit -m "Name the two skill values the calculator has to share with the rules"
```

---

### Task 4: 로스터 상태 → WindowInputs 조립

**Files:**
- Create: `backend/app/charge_window_inputs.py`
- Test: `backend/tests/test_charge_window_inputs.py` (Task 3에서 만든 파일에 이어 붙임)

**Interfaces:**
- Consumes: `app.charge_window.WindowInputs`, `app.user_roster.load_nikke_spec(state, data_dir, slug_override=None) -> NikkeSpec | None`, `app.skill_rules.registry.get_charge_motion_delay(slug) -> float`, `app.cube_effects.assumed_cube_effects(source_slug)`, Task 3의 두 함수
- Produces:
  - `CALCULATOR_SLUGS: tuple[str, ...]` — `("scarlet-black-shadow", "liberalio", "neon-vision-eye")`
  - `LIBERALIO_SLUG: str`
  - `Overrides` (frozen dataclass) — `charge_speed_lines: list[float] | None`, `max_ammo_percent: float | None`, `reload_speed_percent: float | None` (전부 None이면 로스터 값 사용)
  - `build_inputs(state, with_liberalio: bool, overrides: Overrides, liberalio_state=None, data_dir=DATA_DIR) -> WindowInputs`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_charge_window_inputs.py` 끝에 이어 붙인다.

```python
import pytest

from app.charge_window_inputs import (CALCULATOR_SLUGS, LIBERALIO_SLUG, Overrides,
                                      build_inputs)
from app.models import OverloadOption, SkillLevels, UserNikkeState

MAXED = SkillLevels(skill1=10, skill2=10, burst=10)


def a_state(slug, overloads=()):
    return UserNikkeState(
        character_slug=slug, level=200, hp=1_000_000, atk=100_000, def_=10_000,
        skill_levels=MAXED,
        overload_options=[OverloadOption(name=n, value=v) for n, v in overloads],
    )


def test_the_three_units_the_calculator_covers():
    assert CALCULATOR_SLUGS == ("scarlet-black-shadow", "liberalio", "neon-vision-eye")
    assert LIBERALIO_SLUG == "liberalio"


def test_scarlet_carries_her_measured_charge_and_delay():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.charge_time == pytest.approx(0.30)
    assert got.motion_delay == pytest.approx(0.43)


def test_asuras_magazine_grant_is_folded_into_max_ammo():
    # Base 9 rounds, Asura +60%, no overload: round(9 * 1.60) = 14.
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.max_ammo == 14


def test_an_overload_max_ammo_line_stacks_on_top_of_asura():
    # round(9 * (1 + 0.6 + 0.8537)) = 22.
    state = a_state("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])
    got = build_inputs(state, with_liberalio=False, overrides=Overrides(None, None, None))
    assert got.max_ammo == 22


def test_the_charge_speed_overload_line_reaches_the_inputs():
    state = a_state("scarlet-black-shadow", [("차지 속도 증가", 2.86)])
    got = build_inputs(state, with_liberalio=False, overrides=Overrides(None, None, None))
    assert got.charge_speed_percent == pytest.approx(0.0286)


def test_the_assumed_cube_supplies_reload_speed():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.reload_speed_percent == pytest.approx(0.2969, abs=1e-4)


def test_liberalio_hands_over_her_absolute_seconds():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=True,
                       overrides=Overrides(None, None, None),
                       liberalio_state=a_state(LIBERALIO_SLUG))
    assert got.charge_time_reduction_sec == pytest.approx(0.1274 * 1.5, abs=1e-4)


def test_without_the_companion_there_is_no_cut():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.charge_time_reduction_sec == 0.0


def test_liberalio_refuses_the_cut_even_when_asked():
    # Strange Currents makes her immune to external charge-speed effects, so the
    # companion toggle cannot apply to her own row.
    got = build_inputs(a_state(LIBERALIO_SLUG), with_liberalio=True,
                       overrides=Overrides(None, None, None),
                       liberalio_state=a_state(LIBERALIO_SLUG))
    assert got.charge_time_reduction_sec == 0.0


def test_overrides_replace_the_roster_values():
    state = a_state("scarlet-black-shadow", [("차지 속도 증가", 2.86)])
    got = build_inputs(state, with_liberalio=False,
                       overrides=Overrides(charge_speed_lines=[6.09, 6.09],
                                           max_ammo_percent=0.8537,
                                           reload_speed_percent=0.0))
    assert got.charge_speed_percent == pytest.approx(0.1218)
    assert got.max_ammo == 22
    assert got.reload_speed_percent == 0.0


def test_an_unknown_slug_is_refused():
    with pytest.raises(ValueError, match="charge-window calculator"):
        build_inputs(a_state("liter"), with_liberalio=False,
                     overrides=Overrides(None, None, None))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_charge_window_inputs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.charge_window_inputs'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/charge_window_inputs.py`:

```python
"""Turns a roster entry into the calculator's WindowInputs.

Everything except two skill-text values is read from the loaders the recommender
already uses, so a re-measured charge time, a re-timed motion delay or a
re-synced overload roll moves the calculator with no edit here. The two
exceptions - Asura's magazine grant and Calm Depths' caster-based cut - are read
through the functions their own unit modules expose, which the rule builders
call too.
"""
from dataclasses import dataclass

from app.charge_window import WindowInputs, aggregate_charge_speed
from app.cube_effects import assumed_cube_effects
from app.overload_effects import NAME_TO_STAT
from app.skill_rules.liberalio import calm_depths_charge_cut_seconds
from app.skill_rules.registry import get_charge_motion_delay
from app.skill_rules.scarlet_black_shadow import full_burst_max_ammo_percent
from app.skill_values import DATA_DIR
from app.user_roster import load_nikke_spec

SCARLET_SLUG = "scarlet-black-shadow"
LIBERALIO_SLUG = "liberalio"
NEON_SLUG = "neon-vision-eye"

# The units this calculator answers for: every one is a charge weapon whose kit
# fires something on each Full Charge, which is what makes "how many shots"
# equal "how much damage" for them.
CALCULATOR_SLUGS = (SCARLET_SLUG, LIBERALIO_SLUG, NEON_SLUG)


@dataclass(frozen=True)
class Overrides:
    """What the user typed over the synced roster. None means "use the roster".

    The roster snapshot goes stale the moment gear changes, and for this screen
    that is the normal state rather than an error - Fienn's own measured runs
    already used a bigger magazine than his last sync recorded.
    """
    charge_speed_lines: list[float] | None
    max_ammo_percent: float | None
    reload_speed_percent: float | None


def _overload_total(spec, stat):
    return sum(option.value for option in spec.overload_options
               if NAME_TO_STAT.get(option.name) == stat) / 100


def _cube_reload_speed(slug):
    for effect in assumed_cube_effects(slug):
        if effect.stat == "reload_speed_percent":
            return effect.value
    return 0.0


def _self_max_ammo_percent(spec):
    """Magazine grants the unit gives ITSELF inside the window. Only Scarlet has
    one; Liberalio and Neon fight the window on their base magazine."""
    if spec.slug == SCARLET_SLUG:
        return full_burst_max_ammo_percent(spec.skill_values)
    return 0.0


def build_inputs(state, with_liberalio, overrides, liberalio_state=None,
                 data_dir=DATA_DIR):
    if state.character_slug not in CALCULATOR_SLUGS:
        raise ValueError(
            f"{state.character_slug} is not covered by the charge-window calculator")
    spec = load_nikke_spec(state, data_dir)
    if spec is None:
        raise ValueError(f"{state.character_slug} could not be loaded from local data")
    weapon = spec.weapon_stats

    if overrides.charge_speed_lines is None:
        charge_speed = _overload_total(spec, "charge_speed_percent")
    else:
        charge_speed = aggregate_charge_speed(
            overrides.charge_speed_lines, weapon["charge_time"])

    ammo_percent = (_overload_total(spec, "max_ammo_percent")
                    if overrides.max_ammo_percent is None else overrides.max_ammo_percent)
    reload_speed = (_cube_reload_speed(spec.slug)
                    if overrides.reload_speed_percent is None
                    else overrides.reload_speed_percent)

    # Strange Currents grants Liberalio immunity to external charge-speed
    # effects, so she can never receive her own grant - the toggle is refused
    # rather than hidden, because the API is callable without the UI.
    cut = 0.0
    if with_liberalio and spec.slug != LIBERALIO_SLUG:
        companion = load_nikke_spec(liberalio_state or state, data_dir,
                                    slug_override=LIBERALIO_SLUG)
        if companion is not None:
            cut = calm_depths_charge_cut_seconds(
                companion.skill_values, companion.weapon_stats)

    total_ammo_percent = ammo_percent + _self_max_ammo_percent(spec)
    return WindowInputs(
        charge_time=weapon["charge_time"],
        motion_delay=get_charge_motion_delay(spec.slug),
        max_ammo=max(1, round(weapon["max_ammo"] * (1 + total_ammo_percent))),
        reload_time=weapon["reload_time"],
        charge_speed_percent=charge_speed,
        charge_time_reduction_sec=cut,
        reload_speed_percent=reload_speed,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_charge_window_inputs.py -v`
Expected: PASS (14 tests — Task 3의 3개 + 이 작업의 11개)

`assumed_cube_effects(source_slug) -> list[Effect]` 이고 각 `Effect` 는 `.stat` 과 `.value`(이미 비율)를 갖는다 — `_cube_reload_speed` 는 그 모양을 그대로 읽는다. 29.69 같은 숫자를 코드에 적어 넣지 않는다.

- [ ] **Step 5: Commit**

```bash
git add backend/app/charge_window_inputs.py backend/tests/test_charge_window_inputs.py
git commit -m "Assemble calculator inputs from the roster the recommender already loads"
```

---

### Task 5: `POST /api/charge-window` 엔드포인트

**Files:**
- Modify: `backend/app/api.py` (모델은 `SupportedUnit` 정의 근처, 라우트는 `/api/supported-units` 위)
- Test: `backend/tests/test_api_charge_window.py`

**Interfaces:**
- Consumes: Task 2·4의 전부
- Produces: `POST /api/charge-window`
  - 요청: `{ "slug": str, "roster": [UserNikkeState], "with_liberalio": bool, "overrides": {"charge_speed_lines": [float]|null, "max_ammo_percent": float|null, "reload_speed_percent": float|null} }`
  - 응답: `{ "interval": float, "magazine": int, "charge_speed_percent": float, "current": Outcome, "thresholds": [{"charge_speed_percent","interval","outcome"}], "notes": [str] }`
  - `Outcome` 와이어 형태: `{"low_shots": int, "low_probability": float, "high_shots": int, "high_probability": float}`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_charge_window.py`:

```python
"""POST /api/charge-window - the FB shot-count calculator's surface."""
import pytest
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)

MAXED = {"skill1": 10, "skill2": 10, "burst": 10}


def a_unit(slug, overloads=()):
    return {
        "character_slug": slug, "level": 200, "hp": 1_000_000, "atk": 100_000,
        "def_": 10_000, "skill_levels": MAXED,
        "overload_options": [{"name": n, "value": v} for n, v in overloads],
    }


def post(slug, roster, with_liberalio=False, overrides=None):
    return client.post("/api/charge-window", json={
        "slug": slug, "roster": roster, "with_liberalio": with_liberalio,
        "overrides": overrides or {},
    })


def test_scarlet_with_liberalio_reports_the_measured_cadence():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    response = post("scarlet-black-shadow", roster, with_liberalio=True)
    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == pytest.approx(0.53, abs=1 / 180)
    assert body["magazine"] == 22
    assert body["current"]["high_shots"] == 19


def test_the_threshold_ladder_comes_back_ordered_and_deduplicated():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    percents = [round(t["charge_speed_percent"] * 100, 2) for t in body["thresholds"]]
    assert percents[:4] == [0.0, 5.56, 11.11, 16.67]
    assert percents == sorted(percents)


def test_a_reload_inside_the_window_is_reported_as_a_note():
    # Base magazine plus Asura only: 14 rounds empty at 7.42 sec.
    roster = [a_unit("scarlet-black-shadow"), a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert any("재장전" in note for note in body["notes"])


def test_a_roomy_magazine_produces_no_reload_note():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert not any("재장전" in note for note in body["notes"])


def test_liberalio_taking_her_own_buff_is_reported():
    # The grant goes to the lowest-ATK Burst 3 ally and does NOT exclude her, so
    # a Scarlet with more ATK means Liberalio keeps it.
    scarlet = a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])
    liberalio = a_unit("liberalio")
    liberalio["atk"] = 50_000  # lower than Scarlet's 100,000
    body = post("scarlet-black-shadow", [scarlet, liberalio], with_liberalio=True).json()
    assert any("리버렐리오" in note for note in body["notes"])


def test_a_total_near_a_frame_boundary_is_reported():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    body = post("scarlet-black-shadow", roster,
                overrides={"charge_speed_lines": [5.51]}).json()
    assert any("부위" in note for note in body["notes"])


def test_an_unsupported_slug_is_a_422():
    assert post("liter", [a_unit("liter")]).status_code == 422


def test_a_slug_missing_from_the_roster_is_a_422():
    assert post("neon-vision-eye", [a_unit("liberalio")]).status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_api_charge_window.py -v`
Expected: FAIL — 전부 404 (라우트 없음)

- [ ] **Step 3: Write minimal implementation**

`backend/app/api.py` 의 import 블록에 추가한다:

```python
from app.charge_window import (near_frame_boundary, outcome, reload_intervenes,
                               shot_interval, thresholds)
from app.charge_window_inputs import (CALCULATOR_SLUGS, LIBERALIO_SLUG, Overrides,
                                      build_inputs)
```

`Field` · `HTTPException` · `UserNikkeState` 는 `api.py` 가 이미 import하고 있으므로 더 넣지 않는다.

`class SupportedUnit(BaseModel):` **바로 위**에 모델을 추가한다:

```python
class ChargeWindowOverrides(BaseModel):
    """What the user typed over the synced roster; omitted fields keep it."""
    charge_speed_lines: list[float] | None = None
    max_ammo_percent: float | None = None
    reload_speed_percent: float | None = None


class ChargeWindowRequest(BaseModel):
    slug: str
    roster: list[UserNikkeState]
    with_liberalio: bool = False
    overrides: ChargeWindowOverrides = Field(default_factory=ChargeWindowOverrides)


class ShotOutcome(BaseModel):
    low_shots: int
    low_probability: float
    high_shots: int
    high_probability: float


class ChargeWindowThreshold(BaseModel):
    charge_speed_percent: float
    interval: float
    outcome: ShotOutcome


class ChargeWindowResponse(BaseModel):
    interval: float
    magazine: int
    charge_speed_percent: float
    current: ShotOutcome
    thresholds: list[ChargeWindowThreshold]
    notes: list[str]
```

`@app.get("/api/supported-units"...)` **바로 위**에 라우트를 추가한다:

```python
def _shot_outcome(value) -> ShotOutcome:
    """charge_window.Outcome -> the wire model. Written out field by field so a
    rename on either side is a type error rather than a silently missing key."""
    return ShotOutcome(
        low_shots=value.low_shots,
        low_probability=value.low_probability,
        high_shots=value.high_shots,
        high_probability=value.high_probability,
    )


def _charge_window_notes(request, inputs, spec_atk, liberalio_atk):
    """The judgements worth surfacing next to the ladder. Each is a fact the
    calculator can check rather than a caveat the reader has to remember."""
    notes = []
    if reload_intervenes(inputs):
        notes.append(
            "탄창이 창 안에서 비어 재장전이 걸립니다 — 엔진의 재장전 모델이 실측과 "
            "어긋나 있어(docs/engine-gaps.md) 마지막 한 발이 불확실합니다.")
    if (request.with_liberalio and request.slug != LIBERALIO_SLUG
            and liberalio_atk is not None and liberalio_atk <= spec_atk):
        notes.append(
            "리버렐리오의 공격력이 더 낮아 차지속도 버프가 그녀 자신에게 갑니다 — "
            "대상은 '최저 공격력 버스트 3 아군'이고 시전자를 제외하지 않습니다.")
    lines = (request.overrides.charge_speed_lines
             if request.overrides.charge_speed_lines is not None
             else [inputs.charge_speed_percent * 100])
    if near_frame_boundary(lines, inputs.charge_time):
        notes.append(
            "차지속도 합계가 프레임 경계에 가까워, 부위별 옵션 구성에 따라 한 칸 "
            "갈릴 수 있습니다 — 오버로드 집계 규칙이 미결입니다.")
    return notes


@app.post("/api/charge-window", response_model=ChargeWindowResponse)
def charge_window_route(request: ChargeWindowRequest) -> ChargeWindowResponse:
    """FB 창 안 타수와, 다음 타수를 사는 차지속도 임계값."""
    if request.slug not in CALCULATOR_SLUGS:
        raise HTTPException(422, f"charge-window calculator does not cover {request.slug}")
    by_slug = {state.character_slug: state for state in request.roster}
    if request.slug not in by_slug:
        raise HTTPException(422, f"{request.slug} is not in the submitted roster")
    try:
        inputs = build_inputs(
            by_slug[request.slug], request.with_liberalio,
            Overrides(request.overrides.charge_speed_lines,
                      request.overrides.max_ammo_percent,
                      request.overrides.reload_speed_percent),
            liberalio_state=by_slug.get(LIBERALIO_SLUG),
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

    liberalio_state = by_slug.get(LIBERALIO_SLUG)
    notes = _charge_window_notes(
        request, inputs, by_slug[request.slug].atk,
        liberalio_state.atk if liberalio_state else None)
    return ChargeWindowResponse(
        interval=shot_interval(inputs),
        magazine=inputs.max_ammo,
        charge_speed_percent=inputs.charge_speed_percent,
        current=_shot_outcome(outcome(inputs)),
        thresholds=[
            ChargeWindowThreshold(
                charge_speed_percent=row.charge_speed_percent,
                interval=row.interval,
                outcome=_shot_outcome(row.outcome),
            )
            for row in thresholds(inputs)
        ],
        notes=notes,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_api_charge_window.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: `1599 passed, 3 skipped` (1580 + Task 4의 11 + 이 작업의 8). 실패가 하나라도 있으면 다음 작업으로 넘어가지 않는다.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api.py backend/tests/test_api_charge_window.py
git commit -m "Serve the Full Burst shot-count ladder over the API"
```

---

### Task 6: 프론트 API 클라이언트와 타입

**Files:**
- Create: `frontend/src/types/chargeWindow.ts`
- Create: `frontend/src/api/chargeWindow.ts`
- Test: `frontend/src/api/chargeWindow.test.ts`

**Interfaces:**
- Consumes: Task 5의 `POST /api/charge-window`, 기존 `RecommendApiError`
- Produces:
  - `ShotOutcome` = `{ lowShots: number; lowProbability: number; highShots: number; highProbability: number }`
  - `ChargeWindowThreshold` = `{ chargeSpeedPercent: number; interval: number; outcome: ShotOutcome }`
  - `ChargeWindowResult` = `{ interval: number; magazine: number; chargeSpeedPercent: number; current: ShotOutcome; thresholds: ChargeWindowThreshold[]; notes: string[] }`
  - `postChargeWindow(request: ChargeWindowRequest): Promise<ChargeWindowResult>`
  - `ChargeWindowRequest` = `{ slug: string; roster: unknown[]; withLiberalio: boolean; overrides: { chargeSpeedLines: number[] | null; maxAmmoPercent: number | null; reloadSpeedPercent: number | null } }`

- [ ] **Step 0: Install the frontend dependencies (once)**

Run: `cd frontend && npm install`
Expected: 완료. 이 워크트리에는 `node_modules`가 없어서, 건너뛰면 이후 모든 vitest·tsc 명령이 `ERR_MODULE_NOT_FOUND`로 죽는다.

- [ ] **Step 1: Write the failing test**

`frontend/src/api/chargeWindow.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { postChargeWindow } from './chargeWindow'

const WIRE = {
  interval: 0.53,
  magazine: 22,
  charge_speed_percent: 0,
  current: { low_shots: 18, low_probability: 0.132, high_shots: 19, high_probability: 0.868 },
  thresholds: [
    {
      charge_speed_percent: 0,
      interval: 0.53,
      outcome: { low_shots: 18, low_probability: 0.132, high_shots: 19, high_probability: 0.868 },
    },
  ],
  notes: ['탄창이 창 안에서 비어 재장전이 걸립니다'],
}

afterEach(() => vi.unstubAllGlobals())

describe('postChargeWindow', () => {
  it('maps the snake_case wire shape to camelCase', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: true, json: () => Promise.resolve(WIRE) }))
    const result = await postChargeWindow({
      slug: 'scarlet-black-shadow', roster: [], withLiberalio: true,
      overrides: { chargeSpeedLines: null, maxAmmoPercent: null, reloadSpeedPercent: null },
    })
    expect(result.current.highShots).toBe(19)
    expect(result.current.highProbability).toBeCloseTo(0.868)
    expect(result.thresholds[0].chargeSpeedPercent).toBe(0)
    expect(result.thresholds[0].outcome.lowShots).toBe(18)
    expect(result.notes).toHaveLength(1)
  })

  it('sends snake_case field names to the backend', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(WIRE) })
    vi.stubGlobal('fetch', fetchMock)
    await postChargeWindow({
      slug: 'neon-vision-eye', roster: [], withLiberalio: false,
      overrides: { chargeSpeedLines: [4.33, 4.33], maxAmmoPercent: null, reloadSpeedPercent: null },
    })
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.with_liberalio).toBe(false)
    expect(body.overrides.charge_speed_lines).toEqual([4.33, 4.33])
  })

  it('throws RecommendApiError on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: false, status: 422, json: () => Promise.resolve({ detail: 'nope' }) }))
    await expect(postChargeWindow({
      slug: 'liter', roster: [], withLiberalio: false,
      overrides: { chargeSpeedLines: null, maxAmmoPercent: null, reloadSpeedPercent: null },
    })).rejects.toMatchObject({ status: 422 })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/chargeWindow.test.ts`
Expected: FAIL — `Failed to resolve import "./chargeWindow"`

- [ ] **Step 3: Write minimal implementation**

`frontend/src/types/chargeWindow.ts`:

```ts
// Wire and view shapes for POST /api/charge-window. The backend speaks
// snake_case; everything past the api client speaks camelCase.

export interface ShotOutcomeWire {
  low_shots: number
  low_probability: number
  high_shots: number
  high_probability: number
}

export interface ChargeWindowThresholdWire {
  charge_speed_percent: number
  interval: number
  outcome: ShotOutcomeWire
}

export interface ChargeWindowResultWire {
  interval: number
  magazine: number
  charge_speed_percent: number
  current: ShotOutcomeWire
  thresholds: ChargeWindowThresholdWire[]
  notes: string[]
}

export interface ShotOutcome {
  lowShots: number
  lowProbability: number
  highShots: number
  highProbability: number
}

export interface ChargeWindowThreshold {
  chargeSpeedPercent: number
  interval: number
  outcome: ShotOutcome
}

export interface ChargeWindowResult {
  interval: number
  magazine: number
  chargeSpeedPercent: number
  current: ShotOutcome
  thresholds: ChargeWindowThreshold[]
  notes: string[]
}

export interface ChargeWindowRequest {
  slug: string
  roster: unknown[]
  withLiberalio: boolean
  overrides: {
    chargeSpeedLines: number[] | null
    maxAmmoPercent: number | null
    reloadSpeedPercent: number | null
  }
}

export const mapShotOutcome = (wire: ShotOutcomeWire): ShotOutcome => ({
  lowShots: wire.low_shots,
  lowProbability: wire.low_probability,
  highShots: wire.high_shots,
  highProbability: wire.high_probability,
})

export const mapChargeWindowResult = (wire: ChargeWindowResultWire): ChargeWindowResult => ({
  interval: wire.interval,
  magazine: wire.magazine,
  chargeSpeedPercent: wire.charge_speed_percent,
  current: mapShotOutcome(wire.current),
  thresholds: wire.thresholds.map((row) => ({
    chargeSpeedPercent: row.charge_speed_percent,
    interval: row.interval,
    outcome: mapShotOutcome(row.outcome),
  })),
  notes: wire.notes,
})
```

`frontend/src/api/chargeWindow.ts`:

```ts
// Typed client for POST /api/charge-window - the Full Burst shot-count ladder.

import type { ChargeWindowRequest, ChargeWindowResult, ChargeWindowResultWire } from '../types/chargeWindow'
import { mapChargeWindowResult } from '../types/chargeWindow'
import { RecommendApiError } from './recommendApiError'

export const postChargeWindow = async (
  request: ChargeWindowRequest,
): Promise<ChargeWindowResult> => {
  const response = await fetch('/api/charge-window', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      slug: request.slug,
      roster: request.roster,
      with_liberalio: request.withLiberalio,
      overrides: {
        charge_speed_lines: request.overrides.chargeSpeedLines,
        max_ammo_percent: request.overrides.maxAmmoPercent,
        reload_speed_percent: request.overrides.reloadSpeedPercent,
      },
    }),
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return mapChargeWindowResult((await response.json()) as ChargeWindowResultWire)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/chargeWindow.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/chargeWindow.ts frontend/src/api/chargeWindow.ts frontend/src/api/chargeWindow.test.ts
git commit -m "Type the charge-window endpoint for the frontend"
```

---

### Task 7: 사다리 표 컴포넌트

**Files:**
- Create: `frontend/src/components/ChargeWindowLadder.tsx`
- Test: `frontend/src/components/ChargeWindowLadder.test.tsx`

**Interfaces:**
- Consumes: Task 6의 `ChargeWindowResult`
- Produces: `ChargeWindowLadder({ result }: { result: ChargeWindowResult })`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/ChargeWindowLadder.test.tsx`:

```tsx
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ChargeWindowLadder } from './ChargeWindowLadder'
import type { ChargeWindowResult } from '../types/chargeWindow'

const outcome = (low: number, high: number, highProbability: number) => ({
  lowShots: low, lowProbability: 1 - highProbability,
  highShots: high, highProbability,
})

const RESULT: ChargeWindowResult = {
  interval: 0.53,
  magazine: 22,
  chargeSpeedPercent: 0,
  current: outcome(18, 19, 0.868),
  thresholds: [
    { chargeSpeedPercent: 0, interval: 0.53, outcome: outcome(18, 19, 0.868) },
    { chargeSpeedPercent: 0.0556, interval: 0.5133, outcome: outcome(19, 20, 0.481) },
    { chargeSpeedPercent: 0.1111, interval: 0.4967, outcome: outcome(20, 21, 0.134) },
  ],
  notes: ['탄창이 창 안에서 비어 재장전이 걸립니다'],
}

describe('ChargeWindowLadder', () => {
  it('renders one row per threshold', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    expect(screen.getAllByRole('row')).toHaveLength(RESULT.thresholds.length + 1)
  })

  it('marks the row the current charge speed sits on', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    const current = screen.getByTestId('ladder-row-current')
    expect(within(current).getByText(/0\.00%/)).toBeInTheDocument()
  })

  it('marks the highest step at or below the current charge speed', () => {
    render(<ChargeWindowLadder result={{ ...RESULT, chargeSpeedPercent: 0.09 }} />)
    // 9% buys the 5.56% step but not the 11.11% one.
    const current = screen.getByTestId('ladder-row-current')
    expect(within(current).getByText(/5\.56%/)).toBeInTheDocument()
  })

  it('shows both shot counts with their probabilities', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    const current = screen.getByTestId('ladder-row-current')
    expect(within(current).getByText(/19타 87%/)).toBeInTheDocument()
    expect(within(current).getByText(/18타 13%/)).toBeInTheDocument()
  })

  it('reports how much more charge speed the next step costs', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    expect(screen.getByText(/5\.56%p/)).toBeInTheDocument()
  })

  it('lists every note', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    expect(screen.getByText(/재장전이 걸립니다/)).toBeInTheDocument()
  })

  it('says so when the ladder has no further step to buy', () => {
    const topped = {
      ...RESULT,
      chargeSpeedPercent: 0.1111,
      thresholds: RESULT.thresholds.slice(0, 3),
    }
    render(<ChargeWindowLadder result={topped} />)
    expect(screen.getByText(/더 올릴 구간이 없습니다/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/ChargeWindowLadder.test.tsx`
Expected: FAIL — `Failed to resolve import "./ChargeWindowLadder"`

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/ChargeWindowLadder.tsx`:

```tsx
// The charge-speed ladder: one row per step that actually changes the cadence,
// with the row the player currently sits on marked.
//
// Both shot counts are shown with their probabilities rather than a single
// number, because the phase the Full Burst window opens at is not the player's
// to choose and it decides the last shot.

import type { ChargeWindowResult, ShotOutcome } from '../types/chargeWindow'

const percent = (ratio: number) => `${(ratio * 100).toFixed(2)}%`
const odds = (ratio: number) => `${Math.round(ratio * 100)}%`

const describeOutcome = (outcome: ShotOutcome) => {
  if (outcome.highProbability <= 0) return `${outcome.lowShots}타`
  return `${outcome.highShots}타 ${odds(outcome.highProbability)} / ${outcome.lowShots}타 ${odds(outcome.lowProbability)}`
}

export function ChargeWindowLadder({ result }: { result: ChargeWindowResult }) {
  // The highest step the current total already pays for. Steps are sorted
  // ascending, so the last one at or below the total is the live row.
  let currentIndex = 0
  result.thresholds.forEach((row, index) => {
    if (row.chargeSpeedPercent <= result.chargeSpeedPercent + 1e-9) currentIndex = index
  })
  const next = result.thresholds[currentIndex + 1]
  const gap = next ? next.chargeSpeedPercent - result.chargeSpeedPercent : null

  return (
    <div className="charge-ladder">
      <p className="charge-ladder__summary">
        탄창 {result.magazine}발 · 발당 {result.interval.toFixed(4)}초 · 현재 차지속도{' '}
        {percent(result.chargeSpeedPercent)}
      </p>
      <table className="charge-ladder__table">
        <thead>
          <tr>
            <th scope="col">차지속도</th>
            <th scope="col">간격</th>
            <th scope="col">타수</th>
          </tr>
        </thead>
        <tbody>
          {result.thresholds.map((row, index) => (
            <tr
              key={row.chargeSpeedPercent}
              data-testid={index === currentIndex ? 'ladder-row-current' : undefined}
              className={index === currentIndex ? 'charge-ladder__row--current' : undefined}
            >
              <td>{percent(row.chargeSpeedPercent)}</td>
              <td>{row.interval.toFixed(4)}초</td>
              <td>{describeOutcome(row.outcome)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="charge-ladder__next">
        {gap === null
          ? '더 올릴 구간이 없습니다 — 차지가 이미 사라졌습니다.'
          : `다음 구간까지 ${(gap * 100).toFixed(2)}%p 남았습니다.`}
      </p>
      {result.notes.length > 0 && (
        <ul className="charge-ladder__notes">
          {result.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/ChargeWindowLadder.test.tsx`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChargeWindowLadder.tsx frontend/src/components/ChargeWindowLadder.test.tsx
git commit -m "Render the charge-speed ladder with both shot counts"
```

---

### Task 8: 차지 탭 패널

**Files:**
- Create: `frontend/src/components/ChargeWindowPanel.tsx`
- Test: `frontend/src/components/ChargeWindowPanel.test.tsx`

**Interfaces:**
- Consumes: Task 6의 `postChargeWindow`, Task 7의 `ChargeWindowLadder`, 기존 `NumberField`
- Produces: `ChargeWindowPanel({ roster }: { roster: unknown[] })` — `roster` 는 `App` 의 `validRoster` (`UserNikkeState[]`)

- [ ] **Step 1: Write the failing test**

`frontend/src/components/ChargeWindowPanel.test.tsx`:

```tsx
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ChargeWindowPanel } from './ChargeWindowPanel'

const outcome = (low: number, high: number, highProbability: number) => ({
  low_shots: low, low_probability: 1 - highProbability,
  high_shots: high, high_probability: highProbability,
})

const WIRE = {
  interval: 0.53,
  magazine: 22,
  charge_speed_percent: 0,
  current: outcome(18, 19, 0.868),
  thresholds: [{ charge_speed_percent: 0, interval: 0.53, outcome: outcome(18, 19, 0.868) }],
  notes: [],
}

const ROSTER = [
  { character_slug: 'scarlet-black-shadow', atk: 100000 },
  { character_slug: 'liberalio', atk: 90000 },
]

const stubFetch = () => {
  const mock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(WIRE) })
  vi.stubGlobal('fetch', mock)
  return mock
}

afterEach(() => vi.unstubAllGlobals())

describe('ChargeWindowPanel', () => {
  it('offers only the three units the calculator covers', () => {
    stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    const select = screen.getByLabelText('유닛')
    expect(within(select).getAllByRole('option')).toHaveLength(3)
  })

  it('requests the ladder and renders it', async () => {
    const fetchMock = stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(await screen.findByText(/19타 87%/)).toBeInTheDocument()
  })

  it('hides the Liberalio toggle when Liberalio is the subject', async () => {
    stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    expect(screen.getByLabelText('리버렐리오 동반')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('유닛'), 'liberalio')
    expect(screen.queryByLabelText('리버렐리오 동반')).not.toBeInTheDocument()
  })

  it('sends the typed overrides instead of the roster values', async () => {
    const fetchMock = stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    await userEvent.clear(screen.getByLabelText(/차지속도 합계/))
    await userEvent.type(screen.getByLabelText(/차지속도 합계/), '12.18')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.overrides.charge_speed_lines).toEqual([12.18])
  })

  it('reports an error instead of a ladder when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      { ok: false, status: 422, json: () => Promise.resolve({ detail: 'nope' }) }))
    render(<ChargeWindowPanel roster={ROSTER} />)
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('says the magazine is assumed full at window start', () => {
    stubFetch()
    render(<ChargeWindowPanel roster={ROSTER} />)
    expect(screen.getByText(/탄창은 가득/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/ChargeWindowPanel.test.tsx`
Expected: FAIL — `Failed to resolve import "./ChargeWindowPanel"`

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/ChargeWindowPanel.tsx`:

```tsx
// The 차지 tab: how many shots a charge unit lands inside its Full Burst
// window, and what charge-speed total buys the next one.
//
// The numeric fields start empty, which means "use the synced roster". A typed
// value overrides it - the roster snapshot goes stale the moment gear changes,
// and for this screen that is the normal state rather than an error.

import { useState } from 'react'
import { postChargeWindow } from '../api/chargeWindow'
import type { ChargeWindowResult } from '../types/chargeWindow'
import { ChargeWindowLadder } from './ChargeWindowLadder'
import { NumberField } from './fields/NumberField'

const UNITS = [
  { slug: 'scarlet-black-shadow', label: '홍련: 흑영' },
  { slug: 'liberalio', label: '리버렐리오' },
  { slug: 'neon-vision-eye', label: '네온: 비전 아이' },
]

const LIBERALIO_SLUG = 'liberalio'

const optional = (raw: string): number | null => {
  const trimmed = raw.trim()
  if (trimmed === '') return null
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}

export function ChargeWindowPanel({ roster }: { roster: unknown[] }) {
  const [slug, setSlug] = useState(UNITS[0].slug)
  const [withLiberalio, setWithLiberalio] = useState(true)
  const [chargeSpeed, setChargeSpeed] = useState('')
  const [maxAmmo, setMaxAmmo] = useState('')
  const [result, setResult] = useState<ChargeWindowResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      const chargeSpeedValue = optional(chargeSpeed)
      const maxAmmoValue = optional(maxAmmo)
      setResult(await postChargeWindow({
        slug,
        roster,
        withLiberalio: slug === LIBERALIO_SLUG ? false : withLiberalio,
        overrides: {
          chargeSpeedLines: chargeSpeedValue === null ? null : [chargeSpeedValue],
          maxAmmoPercent: maxAmmoValue === null ? null : maxAmmoValue / 100,
          reloadSpeedPercent: null,
        },
      }))
    } catch {
      setResult(null)
      setError('계산에 실패했습니다. 해당 유닛이 로스터에 있는지 확인해 주세요.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="charge-panel">
      <label className="field__label" htmlFor="charge-unit">유닛</label>
      <select
        id="charge-unit"
        className="field__input"
        value={slug}
        onChange={(event) => setSlug(event.target.value)}
      >
        {UNITS.map((unit) => (
          <option key={unit.slug} value={unit.slug}>{unit.label}</option>
        ))}
      </select>

      {/* Strange Currents makes Liberalio immune to external charge-speed
          effects, so pairing her with herself is not a choice that exists. */}
      {slug !== LIBERALIO_SLUG && (
        <label className="field__checkbox">
          <input
            type="checkbox"
            checked={withLiberalio}
            onChange={(event) => setWithLiberalio(event.target.checked)}
          />
          리버렐리오 동반
        </label>
      )}

      <NumberField
        label="차지속도 합계"
        hint="(%, 비우면 동기화된 로스터 값)"
        value={chargeSpeed}
        onChange={setChargeSpeed}
        step={0.01}
      />
      <NumberField
        label="최대장탄 오버로드"
        hint="(%, 비우면 동기화된 로스터 값)"
        value={maxAmmo}
        onChange={setMaxAmmo}
        step={0.01}
      />

      <p className="charge-panel__assumption">
        풀버스트 진입 시 탄창은 가득으로 가정합니다. 흑련은 아수라가 즉시 재장전하므로
        사실이고, 리버렐리오와 네온은 가정입니다.
      </p>

      <button type="button" className="button" onClick={run} disabled={busy}>
        계산
      </button>

      {error && <p className="field__error" role="alert">{error}</p>}
      {result && <ChargeWindowLadder result={result} />}
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/ChargeWindowPanel.test.tsx`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChargeWindowPanel.tsx frontend/src/components/ChargeWindowPanel.test.tsx
git commit -m "Add the charge-window panel with roster defaults and overrides"
```

---

### Task 9: 앱에 「차지」 탭 배선

**Files:**
- Modify: `frontend/src/App.tsx:25-30` (`Tab` 타입과 `TABS` 배열), 그리고 탭 패널 블록
- Modify: `frontend/src/App.css` (사다리 표 스타일)
- Test: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Task 8의 `ChargeWindowPanel`

- [ ] **Step 1: Write the failing test**

`frontend/src/App.test.tsx` 끝에 이어 붙인다. 이 파일은 `render(<App />)` 를 직접 부르고 프로필은 `seedProfiles` 로 심는다 — 그 방식을 그대로 쓰고 새 헬퍼를 만들지 않는다. `render`·`screen`·`within`·`userEvent`·`seedProfiles`·`validDraft` 는 파일 상단에 이미 있다.

탭 버튼과 패널이 `aria-labelledby`로 묶여 있으므로 패널의 접근성 이름은 탭 라벨(`차지`)과 같다.

```tsx
describe('차지 탭', () => {
  it('is one of the tabs', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: '차지' })).toBeInTheDocument()
  })

  it('shows the calculator when selected', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('tab', { name: '차지' }))
    const panel = screen.getByRole('tabpanel', { name: '차지' })
    expect(within(panel).getByLabelText('유닛')).toBeInTheDocument()
  })

  it('keeps the other panels mounted so a running request survives', async () => {
    render(<App />)
    await userEvent.click(screen.getByRole('tab', { name: '차지' }))
    // hidden, not unmounted - the same rule the recommend panel follows.
    expect(screen.getByRole('tabpanel', { name: '솔로 레이드', hidden: true }))
      .toHaveAttribute('hidden')
  })
})
```

앱이 프로필 없이 온보딩 화면부터 뜨는 구조라면(파일 상단의 기존 테스트가 `seedProfiles` 를 먼저 부르는지 보면 알 수 있다) 세 테스트 모두 `render(<App />)` 앞에 기존 테스트와 **같은 방식으로** `seedProfiles` 를 부른다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: FAIL — `Unable to find role="tab" and name "차지"`

- [ ] **Step 3: Write minimal implementation**

`frontend/src/App.tsx` 에서 import 추가:

```tsx
import { ChargeWindowPanel } from './components/ChargeWindowPanel'
```

`Tab` 타입과 `TABS` 를 바꾼다:

```tsx
type Tab = 'roster' | 'recommend' | 'union' | 'charge'

const TABS: { id: Tab; label: string }[] = [
  { id: 'roster', label: '니케 풀' },
  { id: 'recommend', label: '솔로 레이드' },
  { id: 'union', label: '유니온 레이드' },
  { id: 'charge', label: '차지' },
]
```

`panel-union` 블록 **바로 아래**에 새 패널을 추가한다 (다른 패널과 같이 `hidden` 으로만 감춘다):

```tsx
            <div
              role="tabpanel"
              id="panel-charge"
              aria-labelledby="tab-charge"
              hidden={tab !== 'charge'}
              className="panel"
            >
              <ChargeWindowPanel roster={validRoster} />
            </div>
```

`frontend/src/App.css` 끝에 스타일을 추가한다:

```css
/* 차지 창 계산기 — 사다리 표. 좁은 화면에서 표가 페이지를 밀지 않도록
   자기 컨테이너 안에서만 가로 스크롤한다. */
.charge-ladder__table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0;
}

.charge-ladder__table th,
.charge-ladder__table td {
  padding: 0.35rem 0.6rem;
  text-align: left;
  border-bottom: 1px solid var(--border, #3a3a3a);
  white-space: nowrap;
}

.charge-ladder__row--current {
  font-weight: 700;
  background: var(--accent-soft, rgba(120, 170, 255, 0.14));
}

.charge-ladder__notes {
  margin: 0.5rem 0 0;
  padding-left: 1.1rem;
  font-size: 0.9em;
  opacity: 0.85;
}

.charge-panel__assumption {
  font-size: 0.9em;
  opacity: 0.8;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run`
Expected: 기준선(397 passed)에 이 계획이 더한 테스트가 얹힌 수가 전부 PASS

- [ ] **Step 5: Type-check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: 오류 없음

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.css frontend/src/App.test.tsx
git commit -m "Wire the charge tab into the app"
```

---

### Task 10: 지식 베이스 갱신

**Files:**
- Modify: `docs/roadmap.md` (To-Do / 단계 상태)
- Modify: `frontend/README.md` (엔드포인트 목록)

- [ ] **Step 1: Read what is already there**

Run: `grep -n "api/" frontend/README.md | head -20`
Run: `grep -n "To-Do" docs/roadmap.md | head`

- [ ] **Step 2: Add the endpoint to the frontend contract**

`frontend/README.md` 는 엔드포인트마다 `### \`POST /api/...\`` 섹션을 둔다(`### \`GET /api/supported-units\`` 가 마지막). 그 뒤에 같은 형식으로 섹션을 추가한다:

````markdown
### `POST /api/charge-window`

FB 10초 창 안 타수와, 다음 타수를 사는 차지속도 임계값. `차지` 탭 전용.

요청:

```json
{
  "slug": "scarlet-black-shadow",
  "roster": [ /* UserNikkeState[] — /api/recommend 와 같은 모양 */ ],
  "with_liberalio": true,
  "overrides": {
    "charge_speed_lines": [12.18],
    "max_ammo_percent": 0.8537,
    "reload_speed_percent": null
  }
}
```

응답:

```json
{
  "interval": 0.53,
  "magazine": 22,
  "charge_speed_percent": 0.0,
  "current": {"low_shots": 18, "low_probability": 0.132,
              "high_shots": 19, "high_probability": 0.868},
  "thresholds": [{"charge_speed_percent": 0.0, "interval": 0.53,
                  "outcome": {"low_shots": 18, "low_probability": 0.132,
                              "high_shots": 19, "high_probability": 0.868}}],
  "notes": ["탄창이 창 안에서 비어 재장전이 걸립니다 — ..."]
}
```

- `slug` 는 `scarlet-black-shadow` · `liberalio` · `neon-vision-eye` 셋뿐이고, 나머지는 **422**. 로스터에 그 슬러그가 없어도 422.
- `overrides` 의 각 필드는 `null` 이면 동기화된 로스터 값을 쓴다. `charge_speed_lines` 는 퍼센트 단위 줄 목록이고(집계 규칙이 미결이라 목록으로 받는다), `max_ammo_percent` · `reload_speed_percent` 는 비율이다.
- `thresholds` 는 케이던스를 **실제로 바꾸는** 차지속도만 오름차순으로 담는다. 두 타수와 각 확률을 함께 주는 이유는 FB 진입 위상이 플레이어의 선택이 아니기 때문이다.
- `notes` 는 사용자에게 그대로 보여줄 한국어 문장이다.
````

- [ ] **Step 3: Record the feature in the roadmap**

`docs/roadmap.md` 의 To-Do 체크리스트에서 이웃 항목의 형식(체크박스·굵은 글씨 사용법)을 그대로 따라 완료 항목을 하나 더한다. 담겨야 할 내용:

> 차지 창 계산기(`차지` 탭 · `POST /api/charge-window`) — 흑련·리버렐리오·네온의 FB 10초 창 타수와 차지속도 임계값을 확률 분포로 낸다. 오버로드 집계 규칙 미결(생합계 유지 + 프레임 경계 1.10%p 경고)과 재장전 모델 미착륙은 `docs/engine-gaps.md` 참조.

- [ ] **Step 4: Commit**

```bash
git add docs/roadmap.md frontend/README.md
git commit -m "Document the charge-window calculator and its endpoint"
```

---

### Task 11: 최종 검증

- [ ] **Step 1: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: `1599 passed, 3 skipped` — skipped 는 3에서 늘면 안 되고, passed 는 기준선 1561 밑으로 내려가면 안 된다.

- [ ] **Step 2: Run the whole frontend suite**

Run: `cd frontend && npx vitest run`
Expected: 전부 PASS

- [ ] **Step 3: Drive the real app once**

`/verify` 스킬 또는 `/run` 스킬로 백엔드(:8000)와 프론트(:5173)를 함께 띄우고, 실제 프로필로 `차지` 탭에서 흑련을 계산한다. 확인할 것:
- 사다리 표가 그려지고 "지금 여기" 행이 표시된다
- 리버렐리오 동반을 껐다 켜면 간격이 바뀐다
- 유닛을 리버렐리오로 바꾸면 동반 토글이 사라진다

로컬 개발은 **서버 두 개**가 필요하다 — Vite(:5173)가 `/api/*` 를 FastAPI(:8000)로 프록시하므로, 백엔드를 안 띄우면 `ECONNREFUSED` 가 난다.

- [ ] **Step 4: Commit any fixes, then report**

수정이 있었으면 커밋하고, 없으면 이 단계는 넘어간다. 마지막으로 브랜치 상태를 보고한다:

```bash
git log --oneline wip/scaffolding..HEAD
git status --short
```
