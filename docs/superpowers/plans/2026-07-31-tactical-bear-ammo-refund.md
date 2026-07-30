# 택티컬 베어 탄환 환급 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 택티컬 베어 큐브의 「10발 사격 시 탄환 3발 충전」을 발사 타임라인 안의 실제 카운터로 모델링하고, 실기록 채점이 유닛별 실제 큐브를 쓰게 한다.

**Architecture:** 환급은 스탯이 아니라 탄창 상태 기계다. `attack_rate.py`에 순수 헬퍼 `magazine_shot_count(capacity, shots_before, refund)`를 두고, 기존 탄창 루프들의 `magazine_size = ...` 한 줄만 그 호출로 바꾼다. 큐브 식별자는 `NikkeSpec.cube`로 들어와 `weapon_stats[slug]["ammo_refund"]`에 실려 나간다 — `charge_motion_delay`가 이미 다니는 길이다. 실제 큐브 명단은 `scripts/raid_record.py`에만 두고 추천기·프론트는 건드리지 않는다.

**Tech Stack:** Python 3.14 · pytest · 기존 백엔드(`backend/app`), 측정 스크립트(`scripts/`)

## Global Constraints

- 설계 원본: `docs/superpowers/specs/2026-07-31-tactical-bear-ammo-refund-design.md`
- **환급 카운터는 재장전을 넘어 누적된다** (Fienn 룰링 2026-07-31).
- **환급은 최대 탄창에서 캡된다** — `min(capacity, rounds + refund.rounds)` (Fienn 룰링 2026-07-31).
- **이 탄창을 소모하는 발만 카운트한다** — 진짜 변신 세그먼트는 세지 않고, `shares_magazine` 세그먼트는 센다.
- **환급 없는 경로는 비트 단위로 기존과 동일해야 한다.** `refund=None`이 기본이고, 그 경로의 산술은 바뀌지 않는다.
- 추천기·프론트엔드·동기화 경로는 **무변경**(전원 렐릭 베어 유지).
- 테스트 실행: 저장소 루트에서 `cd backend; python -m pytest`. 기준선은 **1645 passed / 3 skipped**.
- 커밋 메시지는 무엇을 하는지 현재형으로 쓴다(변경 이력·"예전엔 이랬다" 금지 — `.claude/CLAUDE.md`).

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/app/attack_rate.py` (수정) | `AmmoRefund`, `magazine_shot_count`, 그리고 탄창을 걷는 모든 생성기에 환급을 배선 |
| `backend/app/cube_effects.py` (수정) | 큐브 두 종류를 이름으로 로드하고, 스탯 효과와 탄환 환급을 각각 내보냄 |
| `backend/app/roster.py` (수정) | `NikkeSpec.cube` → 큐브 효과 + `weapon_stats["ammo_refund"]` |
| `backend/app/closed_form.py` (수정) | 대리 발수 계산에 환급 전달 |
| `scripts/raid_record.py` (수정) | `RECORD_CUBES` — 기록된 런의 유닛별 큐브 |
| `scripts/measure_record_calibration.py` (수정) | 채점 전 스펙에 기록 큐브를 얹음 |
| `backend/tests/test_ammo_refund.py` (신규) | 카운터 헬퍼와 생성기 배선 |
| `backend/tests/test_assumed_cube.py` (수정) | 큐브 두 종류 |
| `backend/tests/test_roster_cube_wiring.py` (수정) | 큐브가 시뮬레이션 입력까지 도달 |

---

### Task 1: 탄창 카운터 헬퍼

**Files:**
- Modify: `backend/app/attack_rate.py` (파일 상단, `RATE_OF_FIRE_60FPS` 정의 아래)
- Test: `backend/tests/test_ammo_refund.py` (신규)

**Interfaces:**
- Produces: `AmmoRefund(every_shots: int, rounds: int)` (frozen dataclass), `magazine_shot_count(capacity: int, shots_before: int, refund: AmmoRefund | None) -> tuple[int, int]` — `(이 탄창이 실제로 쏘는 발수, 그 뒤의 누적 카운터)`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_ammo_refund.py`:

```python
"""The Tactical Bear cube's bullet refund, as a magazine-walking counter.

The refund is not a stat: a magazine that refills mid-burst shifts every
later reload, and reload phase against the 10-second Full Burst window is
what decides whether the extra rounds are worth anything. Scoring deck 1
with the refund faked as a flat max-ammo percentage reads 0.9804x at +11%,
0.9736x at +22% and 0.9930x at +43% - non-monotonic, so no percentage
stands in for it.
"""
import pytest

from app.attack_rate import AmmoRefund, magazine_shot_count


BASTION = AmmoRefund(every_shots=10, rounds=3)


def test_no_refund_fires_exactly_the_magazine():
    assert magazine_shot_count(9, 0, None) == (9, 9)


def test_a_fresh_nine_round_magazine_never_reaches_the_trigger():
    # Scarlet: Black Shadow holds 9 - the 10th shot of the fight lands in her
    # SECOND magazine, which is why the counter has to survive the reload.
    assert magazine_shot_count(9, 0, BASTION) == (9, 9)


def test_the_counter_carries_across_the_reload_and_buys_one_round():
    # Second magazine: shot 10 refunds 3 onto 8 remaining, capped back to 9.
    assert magazine_shot_count(9, 9, BASTION) == (10, 19)


def test_the_steady_state_is_ten_shots_per_magazine():
    shots_before = 0
    sizes = []
    for _ in range(4):
        size, shots_before = magazine_shot_count(9, shots_before, BASTION)
        sizes.append(size)
    assert sizes == [9, 10, 10, 10]


def test_a_magazine_larger_than_the_trigger_refunds_inside_itself():
    # Her Full Burst magazine is 9 x 1.6 = 14. Shot 10 of the fight lands
    # with 4 left, so the refund is NOT capped away: 4 + 3 = 7 more rounds.
    assert magazine_shot_count(14, 0, BASTION) == (17, 17)


def test_a_refund_that_outpaces_the_trigger_is_rejected():
    # 10 rounds back every 10 shots would never empty the magazine.
    with pytest.raises(ValueError, match="never empties"):
        AmmoRefund(every_shots=10, rounds=10)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py -v`
Expected: FAIL — `ImportError: cannot import name 'AmmoRefund' from 'app.attack_rate'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/attack_rate.py` — `CHARGE_WEAPONS = {"RL", "SR"}` 바로 아래에 추가하고, 파일 상단 `import math` 옆에 `from dataclasses import dataclass`를 올린다(파일 끝에 이미 있는 `from dataclasses import dataclass`는 그대로 두면 중복이므로 **끝의 것을 지우고 상단으로 옮긴다**):

```python
@dataclass(frozen=True)
class AmmoRefund:
    """Rounds handed back into the magazine every N shots fired.

    The Tactical Bear (택티컬 베어) harmony cube is the consumer: "10발 사격 시
    탄환 충전 3발". Two rulings shape it (Fienn, 2026-07-31, in game):

    - The shot counter is CUMULATIVE over the fight, not per magazine. Scarlet:
      Black Shadow holds 9 rounds, so a per-magazine counter would never reach
      10 and the cube would do nothing for her; it does.
    - The refund is CAPPED at the magazine's capacity. Landing on a magazine
      with 8 of 9 left hands back 1, not 3.

    Those two together are why this cannot be a max-ammo percentage: how much
    a refund is worth depends on where in the magazine it lands.
    """
    every_shots: int
    rounds: int

    def __post_init__(self):
        if self.rounds >= self.every_shots:
            raise ValueError(
                f"a refund of {self.rounds} every {self.every_shots} shots never "
                "empties the magazine")


def magazine_shot_count(capacity, shots_before, refund):
    """Rounds this magazine actually fires, and the shot counter afterwards.

    Walks the magazine one round at a time because the refund's value depends
    on the rounds remaining when it lands (it is capped at capacity), and the
    counter it triggers on runs across magazines. `refund=None` returns the
    capacity untouched, so every non-Bastion timeline keeps its exact
    arithmetic.
    """
    if refund is None:
        return capacity, shots_before + capacity
    rounds = capacity
    shots = 0
    counter = shots_before
    while rounds > 0:
        rounds -= 1
        shots += 1
        counter += 1
        if counter % refund.every_shots == 0:
            rounds = min(capacity, rounds + refund.rounds)
    return shots, counter
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/attack_rate.py backend/tests/test_ammo_refund.py
git commit -m "Count a magazine that refills while it fires"
```

---

### Task 2: 발사 시각 생성기에 환급을 배선

**Files:**
- Modify: `backend/app/attack_rate.py` — `generate_magazine_shot_times`, `generate_charge_shot_times`, `generate_shot_times`, `magazine_last_bullet_times`, `charge_last_bullet_times`, `magazine_first_bullet_times`, `charge_first_bullet_times`, `_base_shot_records`, `generate_segmented_shots`
- Test: `backend/tests/test_ammo_refund.py`

**Interfaces:**
- Consumes: `AmmoRefund`, `magazine_shot_count` (Task 1)
- Produces: 위 함수들이 `ammo_refund=None` 키워드를 받는다. `_base_shot_records`/`generate_segmented_shots`는 인자가 아니라 **`base["ammo_refund"]`**(weapon_stats 딕셔너리)에서 읽는다 — `charge_motion_delay`와 같은 규약.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_ammo_refund.py`에 추가:

```python
from app.attack_rate import (
    generate_segmented_shots, generate_shot_times, last_bullet_shot_times)


RL = dict(weapon="RL", max_ammo=9, reload_time=2.0, charge_time=0.3,
          damage_percent=57.29, charge_damage_percent=164.205,
          charge_motion_delay=0.43)


def test_the_refund_adds_shots_to_a_charge_weapons_timeline():
    without = generate_shot_times("RL", 9, 2.0, 0.3, 180.0)
    with_refund = generate_shot_times("RL", 9, 2.0, 0.3, 180.0,
                                      ammo_refund=BASTION)
    assert len(with_refund) > len(without)


def test_a_timeline_without_a_refund_is_unchanged():
    assert generate_shot_times("RL", 9, 2.0, 0.3, 180.0) == \
        generate_shot_times("RL", 9, 2.0, 0.3, 180.0, ammo_refund=None)


def test_last_bullet_marks_the_refunded_final_round():
    # With the refund the second magazine runs to 10 rounds, so the round that
    # empties it is the 10th, not the 9th.
    times = generate_shot_times("RL", 9, 2.0, 0.3, 180.0, ammo_refund=BASTION)
    lasts = last_bullet_shot_times("RL", 9, 2.0, 0.3, 180.0,
                                   ammo_refund=BASTION)
    assert times[8] in lasts        # first magazine still ends at round 9
    assert times[18] in lasts       # second ends at round 10 (index 9..18)
    assert times[17] not in lasts


def test_the_weapon_stats_dict_carries_the_refund_into_segmented_shots():
    plain = generate_segmented_shots(RL, [], 180.0)
    bastion = generate_segmented_shots({**RL, "ammo_refund": BASTION}, [], 180.0)
    assert len(bastion) > len(plain)
    assert [r.time for r in plain] == [r.time for r in
                                       generate_segmented_shots(RL, [], 180.0)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py -v`
Expected: FAIL — `TypeError: generate_shot_times() got an unexpected keyword argument 'ammo_refund'`

- [ ] **Step 3: Write minimal implementation**

각 탄창 루프에서 **`magazine_size = max(1, round(...))` 한 줄**을 아래 두 줄로 바꾸고, `while` 루프 앞에 `shots_fired = 0`을 둔다. 예 — `generate_magazine_shot_times`:

```python
def generate_magazine_shot_times(
    rate_of_fire,
    max_ammo,
    reload_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    ammo_refund=None,
):
    shots = []
    magazine_start = 0.0
    shots_fired = 0

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, ammo_refund)
        for i in range(magazine_size):
            ...
```

같은 치환을 `generate_charge_shot_times`, `magazine_last_bullet_times`, `charge_last_bullet_times`, `magazine_first_bullet_times`, `charge_first_bullet_times`, `_base_shot_records`에 적용한다. 각 함수는 `ammo_refund=None` 키워드를 새로 받고, 디스패처 `generate_shot_times` / `last_bullet_shot_times` / `first_bullet_shot_times`는 그 값을 그대로 넘긴다.

`_base_shot_records`는 인자가 아니라 `base`에서 읽는다(호출자가 weapon_stats 딕셔너리를 그대로 넘기므로):

```python
    refund = base.get("ammo_refund")
```
그리고 두 분기(charge / magazine) 모두에서 `magazine_shot_count(capacity, shots_fired, refund)`를 쓴다. `generate_segmented_shots`는 시그니처가 바뀌지 않는다.

주의 — `_base_shot_records`는 `window_start`마다 새 탄창으로 재시작하지만(변신 후 재개 규약), **누적 카운터는 함수 호출 단위로 0에서 시작**한다. 진짜 변신은 다른 무기이므로 세그먼트 발은 카운트에 들어가지 않는다는 설계 규칙과 일치한다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py tests/test_attack_rate.py -v`
Expected: PASS — 새 테스트 통과, `test_attack_rate.py` 전부 불변

- [ ] **Step 5: 전체 회귀 확인**

Run: `cd backend; python -m pytest`
Expected: 1645 passed / 3 skipped (기준선과 동일 — 아직 아무 유닛도 환급을 받지 않는다)

- [ ] **Step 6: Commit**

```bash
git add backend/app/attack_rate.py backend/tests/test_ammo_refund.py
git commit -m "Thread the ammo refund through every shot timeline"
```

---

### Task 3: 탄창을 공유하는 변신 경로

**Files:**
- Modify: `backend/app/attack_rate.py` — `_shared_magazine_shots`
- Test: `backend/tests/test_ammo_refund.py`

**Interfaces:**
- Consumes: `AmmoRefund`, `magazine_shot_count` (Task 1)
- Produces: 없음(내부 경로)

**왜 별도 태스크인가:** 이 루프는 `magazine_size`를 미리 뽑지 않고 `rounds`를 직접 깎으므로 헬퍼를 그대로 쓸 수 없고, `is_first_bullet=(rounds == capacity - 1)`이 **환급 뒤에 두 번 참이 되는** 버그를 만든다(9발이 8로 줄었다가 환급으로 9가 되고 다음 발에서 다시 8).

- [ ] **Step 1: Write the failing test**

`backend/tests/test_ammo_refund.py`에 추가:

```python
def test_a_shared_magazine_segment_spends_refunded_rounds_too():
    # Snow White: Heavy Arms' Fully Active window draws from her own magazine,
    # so its shots count toward the refund trigger like any other.
    base = dict(weapon="SR", max_ammo=6, reload_time=2.0, charge_time=1.2,
                damage_percent=100.0, charge_damage_percent=200.0)
    segment = [dict(start=5.0, until_shots=3, shares_magazine=True,
                    profile=dict(weapon="SR", charge_time=3.2,
                                 damage_percent=100.0,
                                 charge_damage_percent=200.0))]
    plain = generate_segmented_shots(base, segment, 60.0)
    bastion = generate_segmented_shots({**base, "ammo_refund": BASTION},
                                       segment, 60.0)
    assert len(bastion) > len(plain)


def test_a_refund_does_not_re_open_the_magazine():
    # Refunding onto a partly-spent magazine must not mark another shot as the
    # magazine's first - only a reload starts a magazine.
    base = dict(weapon="SR", max_ammo=6, reload_time=2.0, charge_time=1.2,
                damage_percent=100.0, charge_damage_percent=200.0,
                ammo_refund=BASTION)
    segment = [dict(start=5.0, until_shots=3, shares_magazine=True,
                    profile=dict(weapon="SR", charge_time=3.2,
                                 damage_percent=100.0,
                                 charge_damage_percent=200.0))]
    records = generate_segmented_shots(base, segment, 60.0)
    firsts = [r for r in records if r.is_first_bullet]
    lasts = [r for r in records if r.is_last_bullet]
    # Every magazine opens once and closes once (the fight may cut the last
    # one short, so firsts can lead lasts by at most one).
    assert 0 <= len(firsts) - len(lasts) <= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py -k shared_magazine -v` 그리고 `-k re_open -v`
Expected: 첫 번째는 FAIL(발수가 같음), 두 번째는 FAIL(firsts가 lasts보다 여러 개 많음)

- [ ] **Step 3: Write minimal implementation**

`_shared_magazine_shots`에서:

```python
    refund = base.get("ammo_refund")
    ...
    capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(0.0))))
    rounds = capacity
    shots_fired = 0
    opening = True            # 이 발이 탄창의 첫 발인가
```

발을 기록하는 자리에서 `is_first_bullet`을 `rounds` 비교가 아니라 `opening`으로 판정하고, 발사 직후 환급을 적용한다:

```python
        rounds -= 1
        shots_fired += 1
        records.append(ShotRecord(
            shot_time, profile["weapon"], profile["damage_percent"], bonus,
            is_first_bullet=opening, is_last_bullet=False,
            damage_type=profile.get("damage_type") if in_segment else None,
            in_segment=in_segment))
        opening = False
        if refund is not None and shots_fired % refund.every_shots == 0:
            rounds = min(capacity, rounds + refund.rounds)
```

`is_last_bullet`은 발사 시점에 알 수 없게 되므로(환급이 탄창을 다시 채울 수 있다) 환급을 적용한 **뒤에** 판정한다 — `rounds == 0`이면 방금 넣은 레코드를 `dataclasses.replace(records[-1], is_last_bullet=True)`로 교체하고 재장전한다:

```python
        if rounds == 0:
            records[-1] = replace(records[-1], is_last_bullet=True)
            cursor = shot_time + reload_time_with_speed(
                base["reload_time"], reload_speed_percent_at(shot_time))
            capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(cursor))))
            rounds = capacity
            opening = True
```

`from dataclasses import dataclass, replace`로 임포트를 넓힌다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py -v`
Expected: PASS (전부)

- [ ] **Step 5: 스노우화이트 회귀 확인**

Run: `cd backend; python -m pytest tests/ -k "snow_white or shared_magazine or weapon_mode" -v`
Expected: PASS — 환급이 없는 그녀의 타임라인은 불변

- [ ] **Step 6: Commit**

```bash
git add backend/app/attack_rate.py backend/tests/test_ammo_refund.py
git commit -m "Refund rounds into a shared magazine without re-opening it"
```

---

### Task 4: 대리 발수 계산에도 같은 답을 내게 한다

**Files:**
- Modify: `backend/app/closed_form.py:168-186` (`_shot_count`)
- Test: `backend/tests/test_ammo_refund.py`

**Interfaces:**
- Consumes: `generate_shot_times(..., ammo_refund=...)` (Task 2)
- Produces: 없음

- [ ] **Step 1: Write the failing test**

```python
def test_the_surrogate_shot_count_sees_the_refund():
    from app.closed_form import _shot_count
    plain = _shot_count(dict(weapon="RL", max_ammo=9, reload_time=2.0,
                             charge_time=0.3), 180.0)
    bastion = _shot_count(dict(weapon="RL", max_ammo=9, reload_time=2.0,
                               charge_time=0.3, ammo_refund=BASTION), 180.0)
    assert bastion > plain
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py -k surrogate -v`
Expected: FAIL — 두 값이 같다

- [ ] **Step 3: Write minimal implementation**

`_shot_count`의 캐시 키와 호출에 환급을 넣는다. `AmmoRefund`가 frozen dataclass라 그대로 키에 쓸 수 있다:

```python
    refund = weapon_stats.get("ammo_refund")
    key = (
        weapon_stats["weapon"], weapon_stats["max_ammo"], weapon_stats["reload_time"],
        weapon_stats["charge_time"], fight_duration, refund,
    )
    cached = _shot_count_cache.get(key)
    if cached is None:
        cached = len(generate_shot_times(
            weapon_stats["weapon"], weapon_stats["max_ammo"], weapon_stats["reload_time"],
            weapon_stats["charge_time"], fight_duration, ammo_refund=refund,
        ))
        _shot_count_cache[key] = cached
    return cached
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; python -m pytest tests/test_ammo_refund.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/closed_form.py backend/tests/test_ammo_refund.py
git commit -m "Let the surrogate shot count see the refund too"
```

---

### Task 5: 큐브 두 종류

**Files:**
- Modify: `backend/app/cube_effects.py`
- Modify: `backend/tests/test_assumed_cube.py`
- Test: `backend/tests/test_assumed_cube.py`

**Interfaces:**
- Consumes: `AmmoRefund` (Task 1)
- Produces:
  - `CUBE_NAMES = ("resilience", "tactical_bear")`, `DEFAULT_CUBE = "resilience"`
  - `load_cube(name: str) -> dict` — 큐브 레코드
  - `cube_skill_percents(cube: dict, cube_level: int) -> dict[str, float]` — **첫 인자가 tables에서 큐브 레코드로 바뀐다**
  - `cube_ammo_refund(cube: dict, cube_level: int) -> AmmoRefund | None`
  - `assumed_cube_effects(source_slug: str, cube_name: str = DEFAULT_CUBE) -> list[Effect]`
  - `cube_refund_for(cube_name: str) -> AmmoRefund | None`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_assumed_cube.py`의 기존 테스트 4개는 `cube_skill_percents(tables, N)`을 호출한다. 첫 인자를 `load_cube("resilience")`로 바꾸고(모듈 fixture `tables`를 `resilience`로 교체), 아래를 추가한다:

```python
from app.attack_rate import AmmoRefund
from app.cube_effects import (
    cube_ammo_refund, cube_refund_for, load_cube)


@pytest.fixture(scope="module")
def resilience():
    return load_cube("resilience")


@pytest.fixture(scope="module")
def tactical_bear():
    return load_cube("tactical_bear")


def test_the_two_cubes_differ_only_in_their_first_slot(tactical_bear, resilience):
    # Both give superior code damage 19.09% at Lv.15; only slot 1 differs.
    assert cube_skill_percents(tactical_bear, ASSUMED_CUBE_LEVEL) == {
        "other_elemental_bonus": 19.09,
    }
    assert resilience["atk"] == tactical_bear["atk"]
    assert resilience["hp"] == tactical_bear["hp"]


def test_the_tactical_bear_refunds_three_rounds_every_ten_shots(tactical_bear):
    assert cube_ammo_refund(tactical_bear, ASSUMED_CUBE_LEVEL) == AmmoRefund(10, 3)


def test_the_resilience_cube_refunds_nothing(resilience):
    assert cube_ammo_refund(resilience, ASSUMED_CUBE_LEVEL) is None


def test_the_refund_lookup_is_keyed_by_cube_name():
    assert cube_refund_for("tactical_bear") == AmmoRefund(10, 3)
    assert cube_refund_for("resilience") is None


def test_a_tactical_bear_wearer_gets_no_reload_speed():
    stats = {e.stat for e in assumed_cube_effects("scarlet-black-shadow",
                                                  "tactical_bear")}
    assert stats == {"other_elemental_bonus"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; python -m pytest tests/test_assumed_cube.py -v`
Expected: FAIL — `ImportError: cannot import name 'load_cube'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/cube_effects.py`:

```python
import json
from functools import lru_cache

from app.attack_rate import AmmoRefund
from app.effects import Effect
from app.stat_assembly import STAT_TABLES, load_stat_tables

# Cube skill name (as it appears in the table) -> the engine stat it feeds.
# 리로드 업 HC is deliberately absent: it hands back ROUNDS, which is a
# magazine mechanic rather than a stat, and cube_ammo_refund reads it.
CUBE_SKILL_STATS = {
    "퀵 리로드 HC": "reload_speed_percent",
    "안티 코드 HC": "other_elemental_bonus",
}

CUBE_REFUND_SKILL = "리로드 업 HC"

DEFAULT_CUBE = "resilience"
CUBE_NAMES = ("resilience", "tactical_bear")

ASSUMED_CUBE_LEVEL = 15


@lru_cache(maxsize=None)
def load_cube(name: str) -> dict:
    """One harmony cube's committed stat-table record.

    The Resilience cube rides in tables.json (it was the only one collected
    when the global assumption landed); the Tactical Bear was pulled later
    into its own file next to it. Both are the game's own record shape.
    """
    if name == "resilience":
        return load_stat_tables()["resilience_cube"]
    if name == "tactical_bear":
        path = STAT_TABLES.parent / "tactical-bear-cube.json"
        return json.loads(path.read_text(encoding="utf-8"))
    raise KeyError(f"unknown harmony cube {name!r}; have {CUBE_NAMES}")
```

`cube_skill_percents`는 첫 인자만 바꾼다(`cube = tables["resilience_cube"]` 줄을 지우고 인자를 그대로 쓴다). `CUBE_REFUND_SKILL`은 경고 없이 건너뛰도록 이름 조회 전에 `if name == CUBE_REFUND_SKILL: continue`를 넣는다.

환급 추출:

```python
def cube_ammo_refund(cube: dict, cube_level: int) -> AmmoRefund | None:
    """The rounds this cube hands back, or None if it hands back none.

    The skill's two description values are the trigger ("10발 사격 시") and the
    rounds ("탄환 충전 3발"), each a ladder indexed by the slot's skill level.
    """
    for slot, group in enumerate(cube["harmonycube_skill_group"], start=1):
        if group is None or group["name_localkey"] != CUBE_REFUND_SKILL:
            continue
        skill_level = cube[f"level{slot}"][cube_level - 1]
        if skill_level <= 0:
            return None
        values = group["description_value_list"]
        every = float(values[0]["description_value"][skill_level - 1])
        rounds = float(values[1]["description_value"][skill_level - 1])
        if every != int(every) or rounds != int(rounds):
            raise ValueError(
                f"fractional ammo refund {rounds} every {every} shots at skill "
                f"level {skill_level} - the magazine walker counts whole rounds")
        return AmmoRefund(int(every), int(rounds))
    return None


@lru_cache(maxsize=None)
def cube_refund_for(cube_name: str) -> AmmoRefund | None:
    """The assumed-level refund for a cube named on a NikkeSpec."""
    return cube_ammo_refund(load_cube(cube_name), ASSUMED_CUBE_LEVEL)
```

`_assumed_percents`는 큐브 이름을 받게 하고 `assumed_cube_effects(source_slug, cube_name=DEFAULT_CUBE)`가 그것을 넘긴다:

```python
@lru_cache(maxsize=None)
def _assumed_percents(cube_name: str) -> tuple[tuple[str, float], ...]:
    """One cube's percentages, read once. Tuple so lru_cache is safe."""
    return tuple(cube_skill_percents(load_cube(cube_name), ASSUMED_CUBE_LEVEL).items())


def assumed_cube_effects(source_slug: str, cube_name: str = DEFAULT_CUBE) -> list[Effect]:
    """The wearer's cube as always-on self buffs."""
    return [
        Effect(stat, percent / 100, "self", None, source_slug)
        for stat, percent in _assumed_percents(cube_name)
    ]
```

모듈 docstring도 두 큐브를 다룬다는 사실에 맞춘다(무엇을/왜만 쓰고 변경 이력은 쓰지 않는다).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; python -m pytest tests/test_assumed_cube.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/cube_effects.py backend/tests/test_assumed_cube.py
git commit -m "Read either harmony cube, and its bullet refund"
```

---

### Task 6: 큐브가 시뮬레이션 입력까지 간다

**Files:**
- Modify: `backend/app/roster.py` — `NikkeSpec`, `_passive_effects`, `assemble_simulation_inputs`
- Modify: `backend/tests/test_roster_cube_wiring.py`

**Interfaces:**
- Consumes: `cube_refund_for`, `assumed_cube_effects(slug, cube_name)` (Task 5); `weapon_stats["ammo_refund"]` 규약 (Task 2)
- Produces: `NikkeSpec.cube: str = "resilience"`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_roster_cube_wiring.py`에 추가:

```python
from app.attack_rate import AmmoRefund


def test_a_tactical_bear_wearer_carries_the_refund_on_its_weapon_stats():
    spec = _spec("attacker", cube="tactical_bear")
    inputs = assemble_simulation_inputs([spec])
    assert inputs["weapon_stats"]["attacker"]["ammo_refund"] == AmmoRefund(10, 3)


def test_a_default_wearer_carries_no_refund_key():
    spec = _spec("attacker")
    inputs = assemble_simulation_inputs([spec])
    assert "ammo_refund" not in inputs["weapon_stats"]["attacker"]
```

`_spec(...)`은 이 파일이 이미 쓰고 있는 NikkeSpec 조립 방식을 그대로 따르되 `cube` 키워드를 받도록 한다(파일에 헬퍼가 없으면 기존 테스트가 스펙을 만드는 코드를 헬퍼로 뽑아 쓴다 — 중복을 늘리지 않는다).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; python -m pytest tests/test_roster_cube_wiring.py -v`
Expected: FAIL — `TypeError: NikkeSpec.__init__() got an unexpected keyword argument 'cube'`

- [ ] **Step 3: Write minimal implementation**

`NikkeSpec`에 필드를 하나 더한다(기본값이 있으므로 위치 인자 호출은 안 깨진다):

```python
    collectible_level: int = 0
    # Which harmony cube this unit wears. Everyone is assumed to wear a
    # Resilience cube; the recorded raid is scored with the cubes actually
    # worn (scripts/raid_record.RECORD_CUBES), which is the only caller that
    # sets this today.
    cube: str = DEFAULT_CUBE
```

`_passive_effects`는 `assumed_cube_effects(spec.slug, spec.cube)`를 부르고, `assemble_simulation_inputs`의 weapon_stats 조립을 환급까지 얹도록 넓힌다:

```python
        motion_delay = get_charge_motion_delay(spec.slug)
        refund = cube_refund_for(spec.cube)
        extra = {}
        if motion_delay:
            extra["charge_motion_delay"] = motion_delay
        if refund is not None:
            extra["ammo_refund"] = refund
        weapon_stats[spec.slug] = {**spec.weapon_stats, **extra} if extra else spec.weapon_stats
```

임포트에 `from app.cube_effects import DEFAULT_CUBE, assumed_cube_effects, cube_refund_for`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; python -m pytest tests/test_roster_cube_wiring.py -v`
Expected: PASS

- [ ] **Step 5: 전체 회귀 확인**

Run: `cd backend; python -m pytest`
Expected: 1645 + 새 테스트 passed / 3 skipped

- [ ] **Step 6: Commit**

```bash
git add backend/app/roster.py backend/tests/test_roster_cube_wiring.py
git commit -m "Carry each unit's cube into its simulation inputs"
```

---

### Task 7: 실기록은 실제로 낀 큐브로 채점한다

**Files:**
- Modify: `scripts/raid_record.py`
- Modify: `scripts/measure_record_calibration.py`
- Modify: `scripts/measure_deck_breakdown.py` (같은 조립 경로를 쓰면 동일 적용)

**Interfaces:**
- Consumes: `NikkeSpec.cube` (Task 6)
- Produces: `RECORD_CUBES: dict[str, str]`

- [ ] **Step 1: 기록에 큐브를 적는다**

`scripts/raid_record.py`의 `RECORD_ROTATIONS` 근처에 추가:

```python
# The harmony cube each unit actually wore in the recorded run. Everyone not
# named here wore the Resilience cube the engine assumes. This is a fact about
# the RECORD, not about the roster - cubes are re-equipped between fights, so a
# synced snapshot cannot supply it (Fienn).
#
# Scarlet: Black Shadow's Tactical Bear is confirmed (Fienn, 2026-07-29).
RECORD_CUBES = {
    "scarlet-black-shadow": "tactical_bear",
}
```

- [ ] **Step 2: 채점 경로에 얹는다**

`scripts/measure_record_calibration.py` — `from raid_record import (...)`에 `RECORD_CUBES`를 넣고, `_states_for` 아래에 헬퍼를 둔다:

```python
def _record_roster(states):
    """load_roster, plus the cube each unit actually wore in the record."""
    specs, excluded = load_roster(states)
    for spec in specs:
        spec.cube = RECORD_CUBES.get(spec.slug, spec.cube)
    return specs, excluded
```

`measure()`와 `_print_orderings()`의 `specs, excluded = load_roster(states)`를 `_record_roster(states)`로 바꾼다.

- [ ] **Step 3: 환급 전/후를 둘 다 잰다**

```bash
git stash list   # 스택은 워크트리 간 공유다. 쓰지 말 것.
python scripts/measure_record_calibration.py --deck deck1
```

`RECORD_CUBES`를 빈 딕셔너리로 잠시 두고 한 번, 원래대로 두고 한 번 돌려 **흑련 비율 두 개를 기록**한다. 두 숫자는 다음 태스크의 문서에 그대로 들어간다.

- [ ] **Step 4: 전체 캘리브레이션**

Run: `python scripts/measure_record_calibration.py`
Expected: 합계·21/25·유닛별 비율이 출력된다. 흑련 외 24명의 비율은 **변하지 않아야 한다**(그들의 큐브는 그대로다) — 변했다면 배선이 샌 것이다.

- [ ] **Step 5: Commit**

```bash
git add scripts/raid_record.py scripts/measure_record_calibration.py
git commit -m "Score the recorded raid with the cubes it was fought with"
```

---

### Task 8: 문서와 마무리

**Files:**
- Modify: `docs/engine-gaps.md` (마지막 갱신 줄 + 큐브 항목)
- Modify: `docs/roadmap.md` (To-Do)
- Modify: `docs/superpowers/specs/2026-07-31-tactical-bear-ammo-refund-design.md` (Status)

- [ ] **Step 1: 측정 결과를 문서에 적는다**

`docs/engine-gaps.md`의 큐브 항목(#12)에 택티컬 베어가 이제 표현된다는 사실과 Task 7에서 잰 **흑련 비율 전/후**를 적는다. 추측이 아니라 측정된 숫자만 적는다.

- [ ] **Step 2: 남은 열린 질문을 적는다**

설계 문서의 「열린 질문」 두 개(변신 세그먼트가 카운터를 올리는지 / 재장전 중 환급)를 `docs/roadmap.md`의 To-Do로 옮긴다. 인게임 확인이 필요한 항목이라 Fienn만 닫을 수 있다.

- [ ] **Step 3: 결정·통찰 기록**

`/document`로 docs-keeper에 넘긴다 — 기록할 것: (a) 유닛별 큐브를 실기록 전용으로 둔 결정과 그 대안 셋, (b) **탄환 환급은 스탯으로 근사할 수 없다**는 통찰(비단조 측정표), (c) 잘못 주던 재장전속도가 0.0004x였다는 사실.

- [ ] **Step 4: 최종 검증**

```bash
cd backend; python -m pytest
```
Expected: 전부 통과, skip 3

- [ ] **Step 5: Commit**

```bash
git add docs/
git commit -m "Record what the Tactical Bear cube changed"
```

## Self-Review

**1. Spec coverage**

| 설계 절 | 태스크 |
|---|---|
| 1. 메커니즘 (`AmmoRefund`, `magazine_shot_count`) | 1 |
| 1. 적용처 — 시뮬레이터/closed_form/트리거 헬퍼 | 2, 3, 4 |
| 1. 카운트 규칙(변신 세그먼트 제외, shares_magazine 포함) | 2 Step 3 주석, 3 |
| 2. 큐브 두 종류 | 5 |
| 3. `weapon_stats["ammo_refund"]` 배선 | 2, 6 |
| 4. 실기록 전용 `RECORD_CUBES` | 7 |
| 테스트 절 전부 | 1·2·3·5·6의 테스트 + 7 Step 4 |
| 열린 질문 | 8 Step 2 |

**2. Placeholder scan** — 없음. 모든 코드 스텝에 실제 코드가 들어 있다.

**3. Type consistency** — `AmmoRefund(every_shots, rounds)`은 Task 1에서 정의되어 2·3·4·5·6에서 같은 이름으로 쓰인다. `magazine_shot_count`의 반환은 어디서나 `(shots, counter)` 튜플이다. `cube_refund_for(name) -> AmmoRefund | None`은 Task 5가 만들고 6이 쓴다. `weapon_stats` 키는 어디서나 `"ammo_refund"`다.
