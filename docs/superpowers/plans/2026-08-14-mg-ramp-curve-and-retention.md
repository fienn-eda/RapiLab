# MG 램프 곡선 + 부분 잔존 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MG 예열을 실측된 앞쪽 몰림 곡선으로 바꾸고, 짧은 재장전 뒤에 예열이 부분적으로 남는 것을 배선한다.

**Architecture:** `Spinup`이 「총합 하나」에서 「누적 곡선」이 된다. `magazine_shot_offset`이 그 곡선 위 임의의 위치에서 시작할 수 있게 `ramp_start` 인자를 받고, 탄창 워크 넷이 직전 탄창의 발사 공백에서 그 위치를 유도한다. 발사 공백에는 실측된 재장전 후 지연 12.5프레임이 포함된다.

**Tech Stack:** Python 3.14, pytest. 순수 함수 변경이고 새 의존성은 없다.

**Spec:** `docs/superpowers/specs/2026-08-14-mg-ramp-curve-and-retention-design.md`

## Global Constraints

- **줄 번호는 `b1e6e300` 기준이고 태스크가 착륙할 때마다 밀린다.** 앞 태스크가 `Spinup`을 길게 만들면 뒤 번호가 전부 이동하므로, **심볼 이름으로 찾고 줄 번호는 참고로만** 쓴다.
- **백엔드 테스트는 반드시 `backend/`에서 돌린다.** 루트에서는 `No module named 'app'`으로 수집이 깨진다.
- **감쇠 D = 66프레임** (`HEATING_DECAY_SECONDS = 66 / 60`). Fienn 판정 2026-08-14.
- **재장전 후 지연 = 12.5프레임**, **MG 한정**. 다른 무기군은 미측정이므로 일반화 금지.
- **램프 곡선 = `((0, 0.0), (2, 56/60), (24, 111/60), (48, 137/60))`.** 원본 프레임 수치이며 바꾸지 않는다.
- **주석은 WHAT과 WHY만.** 「예전엔 이랬다」/「이 커밋에서 바뀌었다」를 코드 주석에 쓰지 않는다.
- **각 태스크 끝에서 전체 스위트가 초록이어야 한다** — `cd backend && python -m pytest -q`. 기준선은 이 워크트리(`8aac1da6`)에서 실측한 **2367 passed / 3 skipped**(125초). 3 skipped는 워크트리에 `frontend/node_modules`가 없어서이며 회귀가 아니다.
- **가드 테스트는 구현 뒤에 직접 떼어서** 빨개지는 것을 확인한다. 가드가 생기기 전에도 초록인 테스트는 아무것도 재지 않는다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/app/attack_rate.py` (수정) | 곡선 자료구조, 시작 위치 유도, 탄창 워크 넷 |
| `backend/tests/test_mg_spinup.py` (수정) | 예열의 모든 성질에 대한 단위 테스트 |
| `docs/engine-gaps.md` (수정) | 갭 닫힘 |
| `docs/measurements/mg-spinup.md` (수정) | 해석 절만 |
| `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md` (수정) | `mg_heating_speed_percent` 항목 |
| `docs/roadmap.md` (수정) | 상태·캘리 수치 |

---

### Task 1: `Spinup`을 누적 곡선으로 (동작 불변)

자료구조만 바꾸고 **관측 가능한 동작은 한 자리도 안 움직인다**. 그래서 기존 테스트를 하나도 수정하지 않는다 — 이 태스크가 초록인 것이 「곡선이 기존 총합을 정확히 재현한다」의 증거다.

**Files:**
- Modify: `backend/app/attack_rate.py:58-73` (`Spinup`), `:113` (`MG_SPINUP`), `:132-156` (`spinup_with_speed`)
- Test: `backend/tests/test_mg_spinup.py`

**Interfaces:**
- Consumes: 없음
- Produces: `Spinup(points=tuple)` — `.points`, `.intervals`, `.seconds`, `.cost`, `.elapsed(position) -> float`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_mg_spinup.py`의 `test_the_spin_up_costs_a_fixed_time_at_the_head_of_each_magazine` 바로 아래에 추가:

```python
def test_the_ramp_is_a_curve_with_the_cost_at_the_front():
    """Three readings with ammo counts attached put three points on the ramp,
    and they are not a straight line: 56 of a cold magazine's 137 frames go to
    the first TWO rounds. `docs/measurements/mg-spinup.md`."""
    assert MG_SPINUP.elapsed(0) == pytest.approx(0.0)
    assert MG_SPINUP.elapsed(2) == pytest.approx(56 * F)
    assert MG_SPINUP.elapsed(24) == pytest.approx(111 * F)
    assert MG_SPINUP.elapsed(48) == pytest.approx(137 * F)
    assert MG_SPINUP.elapsed(60) == pytest.approx(137 * F)   # past the ramp
    # 41% of the ramp on the first 2 of its 48 rounds.
    assert MG_SPINUP.elapsed(2) / MG_SPINUP.seconds == pytest.approx(56 / 137)
    # Linear inside a segment: position 1 is half of the first segment.
    assert MG_SPINUP.elapsed(1) == pytest.approx(28 * F)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py::test_the_ramp_is_a_curve_with_the_cost_at_the_front -v`
Expected: FAIL — `AttributeError: 'Spinup' object has no attribute 'elapsed'`

- [ ] **Step 3: `Spinup`을 곡선으로 바꾼다**

`backend/app/attack_rate.py:58-73`을 통째로 교체:

```python
@dataclass(frozen=True)
class Spinup:
    """A weapon that reaches its nominal rate of fire only after warming up.

    `points` is the warm-up as a CUMULATIVE CURVE: each entry is `(position on
    the ramp, seconds from the magazine's first round to that position)`,
    starting at `(0, 0.0)` and ending where the weapon reaches full speed.
    The rate is constant between two entries, so `elapsed` interpolates
    linearly inside a segment.

    A curve rather than one total because the measurement pins the SHAPE, and
    the shape is what lets a magazine open PART WAY UP the ramp - which is what
    a reload shorter than the heating decay leaves behind.
    """
    points: tuple

    @property
    def intervals(self):
        """Shot gaps the warm-up covers before the weapon is at full speed."""
        return self.points[-1][0]

    @property
    def seconds(self):
        """Seconds a COLD magazine spends warming up."""
        return self.points[-1][1]

    @property
    def cost(self):
        """Seconds a cold magazine loses to warming up, at 60 rounds/sec."""
        return self.seconds - self.intervals / RATE_OF_FIRE_60FPS["MG"]

    def elapsed(self, position):
        """Seconds from the magazine's first round to ramp `position`."""
        if position <= 0:
            return 0.0
        start, started_at = self.points[0]
        for end, ends_at in self.points[1:]:
            if position <= end:
                return started_at + ((ends_at - started_at)
                                     * (position - start) / (end - start))
            start, started_at = end, ends_at
        return self.seconds
```

- [ ] **Step 4: `MG_SPINUP`을 점열로 바꾼다**

`backend/app/attack_rate.py:113`을 교체:

```python
MG_SPINUP = Spinup(points=((0, 0.0), (2, 56 / 60), (24, 111 / 60), (48, 137 / 60)))
```

그리고 그 위 주석 블록에서 **모양이 미측정이라고 말하는 두 문단**(현재 `:83-88`의 "The SHAPE of the ramp is NOT measured..." 문단과 `:103-109`의 "The ramp's own SHAPE is measured too..." 문단)을 아래 한 문단으로 대체한다. 나머지 문단(최대 연사, 탄창당, 감쇠 70프레임 관측)은 그대로 둔다:

```python
# The ramp's SHAPE is measured, not assumed. Three readings that carry ammo
# counts alongside frame numbers put three points on the curve, and the cost
# sits at the front: rounds 0-2 of a cold magazine take 56 frames, 2-24 another
# 55, 24-48 only 26. A rate rising linearly in TIME is ruled out separately (it
# would need a negative starting rate to fit 48 rounds into 137 frames). What is
# still unmeasured is the shape INSIDE 2-24, which is carried as a straight line.
```

- [ ] **Step 5: `spinup_with_speed`가 점열을 스케일하게 한다 (총합 클램프 유지)**

`backend/app/attack_rate.py:149-156`의 본문만 교체한다. 독스트링은 이 태스크에서 건드리지 않는다:

```python
    if spinup is None or not heating_speed_percent:
        return spinup
    if heating_speed_percent > 0:
        factor = 1.0 / (1 + heating_speed_percent)
    else:
        factor = 1.0 - heating_speed_percent
    floor = spinup.intervals / rate_of_fire
    if spinup.seconds * factor < floor:
        factor = floor / spinup.seconds
    return Spinup(points=tuple((p, t * factor) for p, t in spinup.points))
```

- [ ] **Step 6: 새 테스트와 전체 스위트를 돌린다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -v`
Expected: 전부 PASS. **기존 테스트는 한 줄도 고치지 않았어야 한다.**

Run: `cd backend && python -m pytest -q`
Expected: 기준선과 같은 passed 수.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_mg_spinup.py
git commit -m "MG 예열을 누적 곡선으로 표현한다 - 실측된 세 점이 자료구조가 된다"
```

---

### Task 2: `magazine_shot_offset`이 곡선을 쓴다

여기서 **콜드 탄창의 48발이 재배치된다**. 탄창의 총 길이와 램프 끝(48구간)의 시각은 바뀌지 않으므로 캘리는 흔들리지 않고, 그 사이 발의 위치만 실측을 따라간다.

**Files:**
- Modify: `backend/app/attack_rate.py:159-172` (`magazine_shot_offset`)
- Test: `backend/tests/test_mg_spinup.py`

**Interfaces:**
- Consumes: `Spinup.elapsed`, `Spinup.intervals`, `Spinup.seconds` (Task 1)
- Produces: `magazine_shot_offset(index, shot_interval, spinup, ramp_start=0.0) -> float`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_a_cold_magazine_follows_the_measured_curve():
    """The ramp's total is unchanged - what moves is where its rounds sit."""
    shots = _one_magazine()
    assert shots[2] == pytest.approx(56 * F)
    assert shots[24] == pytest.approx(111 * F)
    assert shots[MG_SPINUP.intervals] == pytest.approx(137 * F)
    assert shots[MAGAZINE - 1] == pytest.approx((EMPTY - FIRST_SHOT) * F)


def test_a_magazine_can_open_part_way_up_the_ramp():
    """The two short-reload readings, read straight off the curve: a magazine
    that keeps 24 of the 48 ramp rounds pays 26 frames, not the 68.5 a flat
    ramp would charge for the same 24 gaps."""
    interval = 1 / RATE_OF_FIRE_60FPS["MG"]
    assert magazine_shot_offset(24, interval, MG_SPINUP, 24) == pytest.approx(26 * F)
    assert magazine_shot_offset(46, interval, MG_SPINUP, 2) == pytest.approx(81 * F)
    # ramp_start defaults to a cold magazine
    assert magazine_shot_offset(48, interval, MG_SPINUP) == pytest.approx(137 * F)
    # past the ramp the nominal gap resumes
    assert magazine_shot_offset(25, interval, MG_SPINUP, 24) == pytest.approx(27 * F)
```

`magazine_shot_offset`을 import 목록에 추가한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -k "measured_curve or part_way" -v`
Expected: FAIL — `shots[2]`가 5.7프레임(평탄값), `magazine_shot_offset`이 인자 4개를 안 받음.

- [ ] **Step 3: 구현한다**

`backend/app/attack_rate.py:159-172`를 교체:

```python
def magazine_shot_offset(index, shot_interval, spinup, ramp_start=0.0):
    """Seconds from a magazine's first round to its `index`-th one.

    `ramp_start` is the ramp position this magazine OPENS at - 0.0 for a cold
    magazine, higher when a reload was short enough that some heating survived.
    It defaults to a cold start, so a caller that does not track heating gets
    the same timeline it always did.

    The single place the spin-up is applied, because four call sites generate
    magazine timelines - `generate_magazine_shot_times`, `_base_shot_records`
    and the two bullet-marker walks - and they are contractually bit-identical
    when there are no segments.
    """
    if spinup is None or index <= 0:
        return index * shot_interval
    position = ramp_start + index
    spent = spinup.elapsed(ramp_start)
    if position <= spinup.intervals:
        return spinup.elapsed(position) - spent
    return ((spinup.seconds - spent)
            + (position - spinup.intervals) * shot_interval)
```

- [ ] **Step 4: 클램프 바닥 테스트를 곡선에 맞게 고친다**

`test_the_clamp_floor_ignores_attack_speed`(현재 `:195-211`)는 램프의 **첫 간격**이 공칭과 같다고 주장하는데, 곡선에서는 첫 간격이 가장 느리므로 그 주장이 곡선의 존재와 모순된다. 이 테스트가 실제로 지키려는 것은 「바닥이 공칭 연사에서 오지 연사 버프가 부풀린 값에서 오지 않는다」이므로, **램프 총합**으로 다시 쓴다. `:207-208`의 두 줄을 교체:

```python
    ramp_total = slowed[MG_SPINUP.intervals].time - slowed[0].time
    assert ramp_total == pytest.approx(MG_SPINUP.intervals / RATE_OF_FIRE_60FPS["MG"])
```

- [ ] **Step 5: 테스트를 돌린다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -v`
Expected: 전부 PASS.

Run: `cd backend && python -m pytest -q`
Expected: 기준선. **여기서 다른 파일이 빨개지면 그 유닛은 램프 중간의 발 시각에 의존하고 있었다는 뜻이므로, 고치기 전에 무엇에 의존하는지 읽고 기록한다.**

- [ ] **Step 6: 가드를 직접 떼어서 확인한다**

`magazine_shot_offset`에서 `spinup.elapsed(position)`을 옛 평탄식 `index * (spinup.seconds / spinup.intervals)`로 잠시 바꿔 `test_a_cold_magazine_follows_the_measured_curve`가 빨개지는지 본다. 확인 뒤 되돌린다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_mg_spinup.py
git commit -m "램프의 발을 실측 곡선 위에 놓는다 - 콜드 137프레임의 41%가 첫 2발이다"
```

---

### Task 3: 부분 잔존 + 재장전 후 지연을 워크 넷에 배선

**둘을 한 태스크로 하는 이유:** 잔존을 결정하는 것이 발사 공백인데, 지연이 그 공백의 일부다. 잔존만 먼저 넣으면 아스카의 강제 재장전 공백이 65.8프레임이 되어 D=66 **바로 아래**로 떨어지고, 그녀의 기존 테스트(`test_skill_rules_asuka_shikinami_langley_wille.py:280`)가 빨개졌다가 지연을 넣는 순간 다시 초록이 된다. 지연을 포함하면 78.3프레임으로 콜드가 되어 처음부터 초록이다.

**Files:**
- Modify: `backend/app/attack_rate.py` — 상수·헬퍼 추가, `:692-717`, `:825-849`, `:920-939`, `:1127-1152`
- Test: `backend/tests/test_mg_spinup.py`

**Interfaces:**
- Consumes: `magazine_shot_offset(..., ramp_start)` (Task 2)
- Produces: `HEATING_DECAY_SECONDS`, `ramp_start_after_gap(spinup, gap_seconds) -> float`, `post_reload_delay_for_weapon(weapon) -> float`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_a_short_reload_keeps_part_of_the_heating():
    """Stacked reload speed collapses the reload, and the game does not charge
    a cold ramp to a magazine that never cooled. Crown plus Privaty reached a
    31-frame gap and a 26-frame ramp where a cold one is 137."""
    assert reload_time_with_speed(RELOAD_FILE, 1.5) == 0.0
    stacked = _one_magazine(reload_speed_percent_at=lambda _t: 1.5)
    gap = stacked[MAGAZINE] - stacked[MAGAZINE - 1]
    start = ramp_start_after_gap(MG_SPINUP, gap)
    assert start == pytest.approx(
        MG_SPINUP.intervals * (1 - gap / HEATING_DECAY_SECONDS))
    assert start > 30                     # most of the ramp survived the gap
    # What this magazine still owes is the curve from `start` to the end. Its
    # 48th round is already PAST the ramp, so it also pays `start` nominal gaps
    # - that sum is what the timeline has to show.
    left = MG_SPINUP.seconds - MG_SPINUP.elapsed(start)
    assert left < 12 * F                  # against a cold ramp's 137 frames
    assert (stacked[MAGAZINE + MG_SPINUP.intervals] - stacked[MAGAZINE]
            == pytest.approx(left + start / RATE_OF_FIRE_60FPS["MG"]))


def test_a_natural_reload_still_opens_cold():
    """The gap has to CLEAR the decay for the ramp to reset, and every natural
    reload does - Rosanna 1.67 sec, Asuka: WILLE 2.478, and 1.080 even on her
    forced one. This is the guard against silently handing retention to units
    the measurement says get none."""
    shots = _one_magazine()
    gap = shots[MAGAZINE] - shots[MAGAZINE - 1]
    assert gap > HEATING_DECAY_SECONDS
    assert ramp_start_after_gap(MG_SPINUP, gap) == 0.0
    assert (shots[MAGAZINE + MG_SPINUP.intervals] - shots[MAGAZINE]
            == pytest.approx(MG_SPINUP.seconds))
    for forced in (1.080, 1.67, 2.478):
        assert ramp_start_after_gap(MG_SPINUP, forced + 12.5 * F + F) == 0.0


def test_the_reload_is_followed_by_a_measured_pause():
    """All three readings show 12-13 frames between the reload completing and
    the next round leaving the barrel (13, 12, 12). With it the engine lands on
    the frame the next magazine's first round was actually read at."""
    assert post_reload_delay_for_weapon("MG") == pytest.approx(12.5 * F)
    for weapon in ("AR", "SMG", "SG", "RL", "SR"):
        assert post_reload_delay_for_weapon(weapon) == 0.0
    shots = _one_magazine()
    assert shots[MAGAZINE] - shots[MAGAZINE - 1] == pytest.approx(
        (NEXT_FIRST_SHOT - EMPTY) * F, abs=2 * F)


def test_the_markers_agree_with_the_shots_when_heating_is_retained():
    """All four magazine walks derive the ramp position themselves, so one left
    behind would fire a trigger at an instant no shot occupies."""
    stacked = dict(reload_speed_percent_at=lambda _t: 1.5)
    shot_list = _one_magazine(**stacked)
    shots = set(shot_list)
    walk = dict(rate_of_fire=RATE_OF_FIRE_60FPS["MG"], max_ammo=MAGAZINE,
                reload_time=RELOAD_FILE, fight_duration=60.0, weapon="MG", **stacked)
    firsts = magazine_first_bullet_times(**walk)
    lasts = magazine_last_bullet_times(**walk)
    assert firsts <= shots and lasts <= shots
    # the retained magazine's own boundaries, which is where a walk left behind
    # would land off by the ramp it still thinks it owes
    assert shot_list[0] in firsts and shot_list[MAGAZINE] in firsts
    assert shot_list[MAGAZINE - 1] in lasts
    segmented = [r.time for r in generate_segmented_shots(
        _mg_base(), [], fight_duration=60.0, **stacked)]
    assert segmented == pytest.approx(shot_list)
```

파일 상단 상수 옆에 추가한다:

```python
NEXT_FIRST_SHOT = 1380      # the second magazine's first round, same reading
```

import에 `HEATING_DECAY_SECONDS`, `ramp_start_after_gap`, `post_reload_delay_for_weapon`을 추가한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -k "short_reload or natural_reload or measured_pause or markers_agree" -v`
Expected: FAIL — `ImportError: cannot import name 'ramp_start_after_gap'`

- [ ] **Step 3: 상수와 헬퍼를 넣는다**

`backend/app/attack_rate.py`의 `spinup_for_weapon` 바로 뒤에 추가:

```python
# Heating does not vanish when firing stops - it bleeds off, and a magazine that
# opens before it is gone starts PART WAY UP the ramp. Fienn read the release
# three ways (2026-08-14) and they land 6-11% apart: 62 frames from the 31-frame
# gap that kept 24 rounds, 65.8 from the 63-frame gap that kept 2, and 70 read
# directly as "fully released". 66 is where the line through the two RETENTION
# readings crosses zero, and retention is what this constant has to reproduce.
# docs/measurements/mg-spinup.md.
HEATING_DECAY_SECONDS = 66 / 60


def ramp_start_after_gap(spinup, gap_seconds):
    """The ramp position a magazine opens at, `gap_seconds` after the previous
    magazine's last round left the barrel.

    Linear from the last round: a gap that clears `HEATING_DECAY_SECONDS`
    opens a cold magazine, half that gap keeps half the ramp. The front-loaded
    curve then does the rest of the work - a magazine that keeps only 3 of the
    48 ramp rounds still skips 56 of the ramp's 89 wasted frames, because that
    is where they were.
    """
    if spinup is None:
        return 0.0
    retained = 1.0 - gap_seconds / HEATING_DECAY_SECONDS
    return max(0.0, min(float(spinup.intervals), spinup.intervals * retained))


# A machine gun does not fire the instant its reload completes: Fienn read
# 13, 12 and 12 frames of pause across the three readings that carry ammo
# counts (docs/measurements/mg-spinup.md). It is part of the firing gap that
# decides how much heating survives, so the two are modeled together. MG only -
# all three readings are machine guns and no other class has been timed.
_POST_RELOAD_DELAY_BY_WEAPON = {"MG": 12.5 / 60}


def post_reload_delay_for_weapon(weapon):
    """Seconds between this weapon's reload completing and its next round."""
    return _POST_RELOAD_DELAY_BY_WEAPON.get(weapon, 0.0)
```

- [ ] **Step 4: `generate_magazine_shot_times`를 배선한다**

`backend/app/attack_rate.py:692-717`의 본문을 교체:

```python
    shots = []
    magazine_start = 0.0
    shots_fired = 0
    base_spinup = spinup_for_weapon(weapon)
    post_reload_delay = post_reload_delay_for_weapon(weapon)
    ramp_start = 0.0

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        spinup = spinup_with_speed(
            base_spinup, heating_speed_percent_at(magazine_start), rate_of_fire)
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, iv=shot_interval, sp=spinup, rs=ramp_start: (
                s + magazine_shot_offset(i, iv, sp, rs)),
            refills=ammo_refills, stop_time=fight_duration)
        for i in range(magazine_size):
            shot_time = magazine_start + magazine_shot_offset(i, shot_interval, spinup, ramp_start)
            if shot_time >= fight_duration:
                return shots
            shots.append(shot_time)
        last_round_at = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup, ramp_start)
        magazine_empty_at = last_round_at + shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time + post_reload_delay
        ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_at)

    return shots
```

- [ ] **Step 5: 마커 워크 둘을 같은 모양으로 배선한다**

`magazine_last_bullet_times`(`:825-849`)의 루프에 `post_reload_delay`/`ramp_start`를 같은 방식으로 넣는다. 이 워크는 이미 `last_round_time`을 계산하고 있으므로 그것을 그대로 쓴다:

```python
    last_bullets = set()
    magazine_start = 0.0
    shots_fired = 0
    base_spinup = spinup_for_weapon(weapon)
    post_reload_delay = post_reload_delay_for_weapon(weapon)
    ramp_start = 0.0

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        spinup = spinup_with_speed(
            base_spinup, heating_speed_percent_at(magazine_start), rate_of_fire)
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, iv=shot_interval, sp=spinup, rs=ramp_start: (
                s + magazine_shot_offset(i, iv, sp, rs)),
            refills=ammo_refills, stop_time=fight_duration)
        last_round_time = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup, ramp_start)
        if last_round_time >= fight_duration:
            return last_bullets
        last_bullets.add(last_round_time)
        magazine_empty_at = last_round_time + shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time + post_reload_delay
        ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_time)

    return last_bullets
```

`magazine_first_bullet_times`(`:920-939`)도 같다. 그 워크는 `last_round_at`을 따로 안 갖고 있으므로 `magazine_empty_at` 계산을 두 줄로 쪼갠다:

```python
        last_round_at = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup, ramp_start)
        magazine_empty_at = last_round_at + shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time + post_reload_delay
        ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_at)
```

- [ ] **Step 6: `_base_shot_records`의 MG 갈래를 배선한다**

`:1127-1152`의 `else:` 갈래. 이 함수는 매 호출이 `window_start`에서 **새 탄창으로 시작**하므로(변신 후 재개 의미론) `ramp_start`는 0.0으로 초기화한다:

```python
    else:
        rate = rate_of_fire_for_weapon(weapon)
        base_spinup = spinup_for_weapon(weapon)
        post_reload_delay = post_reload_delay_for_weapon(weapon)
        ramp_start = 0.0
        magazine_start = window_start
        while magazine_start < window_end:
            interval = 1.0 / (rate * (1 + attack_speed_percent_at(magazine_start)))
            spinup = spinup_with_speed(
                base_spinup, heating_speed_percent_at(magazine_start), rate)
            capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            magazine_size, shots_fired = _walk_magazine(
                capacity, shots_fired, refund,
                time_of_round=lambda i, s=magazine_start, iv=interval, sp=spinup, rs=ramp_start: (
                    s + magazine_shot_offset(i, iv, sp, rs)),
                refills=refills, stop_time=window_end)
            for i in range(magazine_size):
                shot_time = magazine_start + magazine_shot_offset(i, interval, spinup, ramp_start)
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], 0.0,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1)))
            last_round_at = magazine_start + magazine_shot_offset(
                magazine_size - 1, interval, spinup, ramp_start)
            magazine_empty_at = last_round_at + interval
            actual_reload = reload_time_with_speed(base["reload_time"], reload_speed_percent_at(magazine_empty_at))
            magazine_start = magazine_empty_at + actual_reload + post_reload_delay
            ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_at)
    return records
```

- [ ] **Step 7: 기존 프레임 테스트를 새 값으로 고친다**

`test_a_magazine_reproduces_the_measured_frame_numbers`의 `:72-75`를 교체한다. 재장전 뒤 지연이 들어가면서 이 단언은 **판독된 프레임 번호를 하나 더 재현**하게 된다 — 다음 탄창 첫 발이 1380프레임에 읽혔고, 엔진은 이제 1378.6에 놓는다:

```python
    # The engine's own convention is that the last round occupies its interval
    # too, so the next magazine opens one gap, a reload and the measured
    # post-reload pause after the last shot. Against the reading that is 122.6
    # frames where 124 were read, inside the same one-frame precision.
    assert shots[MAGAZINE] == pytest.approx(
        shots[MAGAZINE - 1] + F + reload_time_with_speed(RELOAD_FILE, 0.0)
        + post_reload_delay_for_weapon("MG"))
    assert (shots[MAGAZINE] - shots[MAGAZINE - 1]) == pytest.approx(
        (NEXT_FIRST_SHOT - EMPTY) * F, abs=2 * F)
```

- [ ] **Step 8: 테스트를 돌린다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -v`
Expected: 전부 PASS.

Run: `cd backend && python -m pytest -q`
Expected: 기준선. **아스카 테스트(`test_skill_rules_asuka_shikinami_langley_wille.py`)가 초록인지 특히 확인한다** — 그녀의 강제 재장전 공백 78.3프레임이 감쇠 66을 넘어 콜드로 남아야 한다.

- [ ] **Step 9: 가드를 직접 떼어서 확인한다**

`ramp_start_after_gap`의 `max(0.0, ...)`를 잠시 없애 `test_a_natural_reload_still_opens_cold`가 빨개지는지 본다(공백이 감쇠를 넘으면 음수 위치가 나와 램프가 137프레임보다 길어진다). 확인 뒤 되돌린다.

- [ ] **Step 10: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_mg_spinup.py
git commit -m "짧은 재장전이 남긴 예열을 다음 탄창이 물려받는다"
```

---

### Task 4: 클램프를 구간별로

heating ▲ 버프가 램프를 공칭 연사보다 빠르게 만들 수 없다는 규칙을, 총합이 아니라 **발당**으로 건다. 꼬리 구간이 1.083프레임/발이라 +8.3%부터 물린다.

**Files:**
- Modify: `backend/app/attack_rate.py:132-156` (`spinup_with_speed`)
- Test: `backend/tests/test_mg_spinup.py`

**Interfaces:**
- Consumes: `Spinup.points` (Task 1)
- Produces: 변경 없음 — 같은 시그니처, 다른 클램프

- [ ] **Step 1: 실패하는 테스트를 쓴다**

기존 `test_heating_speed_up_100_percent_halves_the_ramp`(`:121-124`)와 `test_the_ramp_can_never_beat_the_nominal_rate`(`:127-135`)를 아래 셋으로 교체한다:

```python
def test_heating_speed_up_100_percent_halves_what_it_can():
    """The arrow scales the DURATION, but a warm-up is a slow start and not an
    accelerator, so no segment may go tighter than the weapon's nominal gap.
    Halving 56/55/26 gives 28/27.5/13, and the last one is floored at its own
    24 frames - so a cold 137 becomes 79.5, not 68.5."""
    scaled = spinup_with_speed(MG_SPINUP, 1.0, RATE_OF_FIRE_60FPS["MG"])
    assert scaled.seconds == pytest.approx(79.5 * F)
    assert scaled.intervals == MG_SPINUP.intervals
    assert scaled.elapsed(2) == pytest.approx(28 * F)
    assert scaled.elapsed(24) == pytest.approx(55.5 * F)


def test_heating_speed_down_is_untouched_by_the_clamp():
    """Slowing the ramp never approaches the floor, so the doubling is exact."""
    scaled = spinup_with_speed(MG_SPINUP, -1.0, RATE_OF_FIRE_60FPS["MG"])
    assert scaled.seconds == pytest.approx(MG_SPINUP.seconds * 2)
    assert scaled.elapsed(2) == pytest.approx(112 * F)


def test_no_segment_of_the_ramp_beats_the_nominal_gap():
    """Where the clamp actually binds: the ramp's tail is only 1.083 frames a
    round, so it hits the nominal 1.0 at +8.3% while the head has far to go."""
    nominal = 1 / RATE_OF_FIRE_60FPS["MG"]
    for heating in (0.5, 1.0, 5.0, 20.0):
        scaled = spinup_with_speed(MG_SPINUP, heating, RATE_OF_FIRE_60FPS["MG"])
        assert scaled.intervals == MG_SPINUP.intervals
        start, started_at = scaled.points[0]
        for end, ends_at in scaled.points[1:]:
            assert (ends_at - started_at) / (end - start) >= nominal - 1e-12
            start, started_at = end, ends_at
    # Past the point where every segment is floored, the ramp is a flat nominal
    # run and cannot shrink further.
    assert spinup_with_speed(MG_SPINUP, 100.0, RATE_OF_FIRE_60FPS["MG"]).seconds \
        == pytest.approx(MG_SPINUP.intervals * nominal)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -k "halves_what_it_can or no_segment" -v`
Expected: FAIL — 총합 클램프가 68.5프레임을 준다.

- [ ] **Step 3: 구현한다**

`spinup_with_speed`의 본문을 교체하고, 독스트링의 클램프 문단을 아래로 바꾼다:

```python
def spinup_with_speed(spinup, heating_speed_percent, rate_of_fire):
    """This warm-up under a live "MG heating up speed" buff or debuff.

    Fienn's ruling (2026-08-14): the arrow scales the DURATION, so up 100%
    halves the ramp and down 100% doubles it - the same shape as his ruling
    that Ada's charge speed down 300% means charge time x4. The number of gaps
    the ramp covers (`intervals`) does NOT move; those 48 rounds just take
    longer or less long.

    The positive direction deliberately differs from `reload_time_with_speed`,
    whose `(1 - s)` would erase the ramp entirely at up 100%. The negative
    direction agrees with it - both give x2 at down 100%.

    The clamp is per SEGMENT, which is what keeps a warm-up a slow start rather
    than an accelerator: no stretch of the ramp may be tighter than the weapon's
    nominal gap. It binds where the ramp is already nearly at speed - the tail
    runs 1.083 frames a round and floors at +8.3%, while the head still has
    28 frames a round to give.
    """
    if spinup is None or not heating_speed_percent:
        return spinup
    if heating_speed_percent > 0:
        factor = 1.0 / (1 + heating_speed_percent)
    else:
        factor = 1.0 - heating_speed_percent
    nominal = 1.0 / rate_of_fire
    points = [spinup.points[0]]
    start, started_at = spinup.points[0]
    for end, ends_at in spinup.points[1:]:
        span = end - start
        duration = max((ends_at - started_at) * factor, span * nominal)
        points.append((end, points[-1][1] + duration))
        start, started_at = end, ends_at
    return Spinup(points=tuple(points))
```

- [ ] **Step 4: 클램프 바닥 테스트를 다시 조인다**

Task 2에서 램프 총합으로 느슨하게 해 둔 `test_the_clamp_floor_ignores_attack_speed`를, 구간별 클램프가 생겼으니 원래 의도대로 되돌린다. Task 2에서 넣은 두 줄을 교체:

```python
    ramp_tail_gap = (slowed[MG_SPINUP.intervals].time
                     - slowed[MG_SPINUP.intervals - 1].time)
    assert ramp_tail_gap == pytest.approx(1 / RATE_OF_FIRE_60FPS["MG"])
```

- [ ] **Step 5: 테스트를 돌린다**

Run: `cd backend && python -m pytest tests/test_mg_spinup.py -v`
Expected: 전부 PASS.

Run: `cd backend && python -m pytest -q`
Expected: 기준선.

▲ 방향을 소비하는 곳을 먼저 찾아 두면 어디가 움직일지 알고 본다:

Run: `grep -rn "mg_heating_speed_percent" backend/app/skill_rules/ backend/tests/ | grep -v "\.pyc"`

레이(`rei_ayanami_tentative_name`)가 ▲100%를 주는 유일한 유닛이다. 그녀의 예열이 68.5 → **79.5프레임**으로 약해지므로, 옛 값을 박아 둔 테스트가 있으면 새 값으로 고치고 **왜 그 값인지**(꼬리 구간이 공칭에 눌린다)를 주석에 적는다. 「예전엔 68.5였다」는 적지 않는다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_mg_spinup.py
git commit -m "예열 클램프를 구간별로 건다 - 램프의 어느 구간도 공칭 연사를 못 이긴다"
```

---

### Task 5: 캘리 재측정과 문서

**Files:**
- Modify: `docs/engine-gaps.md`, `docs/measurements/mg-spinup.md`, `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`, `docs/roadmap.md`, `docs/superpowers/specs/2026-08-14-mg-ramp-curve-and-retention-design.md`

**Interfaces:**
- Consumes: Task 1-4의 완성된 엔진
- Produces: 없음 (문서)

- [ ] **Step 1: 실기록 캘리브레이션을 다시 잰다**

Run: `cd backend && python ../scripts/measure_record_calibration.py`
Expected: MG 평균이 1.125x에서 **1.17x 부근**으로 올라간다. 합계는 1.033x → 1.05x 부근, ±15% 이내는 20/25 → 19/25.

유닛별로 확인할 것 — 이 배선이 MG를 일괄로 밀어 올리는 것이 아니라는 증거다:

| | 현재 | 기대 |
|---|---:|---:|
| 마스트 | 1.143x | 1.31x 부근 (가장 크게 움직인다) |
| 신데렐라 CW | 1.172x | 1.24x 부근 |
| 크라운 | 1.341x | 1.32x 부근 — **내려간다** |
| 라피 B1 | 1.070x | 1.09x 부근 |
| **미하라** | **0.902x** | **0.900x — 사실상 불변** |

미하라가 대조군이다. 그녀의 재장전 1.906초는 감쇠보다 길어 한 탄창도 잔존을 못 받는다. 그녀가 크게 움직였다면 잔존이 물리면 안 되는 곳에서 물고 있다는 뜻이므로 멈추고 원인을 찾는다.

**추정과 크게 다르면(MG가 1.15 미만이거나 1.20 초과) 멈추고 이유를 찾는다.** 추정은 짧아진 램프 안에서 발을 평탄하게 뿌린 근사였고, 실제 곡선은 앞쪽에 몰아 놓으므로 버프 창 경계에 걸친 발의 재배치만큼만 달라야 한다.

- [ ] **Step 2: 설계문서의 예상 결과 표를 실측값으로 바꾼다**

`docs/superpowers/specs/2026-08-14-mg-ramp-curve-and-retention-design.md`의 "예상 결과" 절 표를 **실제로 나온 수치**로 교체하고, 제목을 "결과"로 바꾼다. 근사였다는 단서 문단은 지운다.

- [ ] **Step 3: `docs/engine-gaps.md`**

"새 갭: MG 예열은 재장전 중에 **시간을 갖고** 빠진다 (2026-08-14)" 절의 제목에 **✅ 해소 (2026-08-14)**를 붙이고, 「이제 필요한 것은 측정이 아니라 설계 판단이다」/「방향 충돌은 그대로다」 문단을 해소 내용으로 대체한다. 남은 미측정(위치 2~24 모양, D의 6~11% 어긋남, 화살표가 감쇠를 바꾸는지, 지연이 MG 전용인지)은 **남긴다**.

무기군 평균 수치가 나오는 곳(`:18`, `:86`, `:354`, `:431`, `:662`)은 MG 값이 박혀 있으므로 새 값으로 갱신한다.

- [ ] **Step 4: `docs/measurements/mg-spinup.md`**

**원본 표는 편집하지 않는다.** "세 판독을 함께 읽기" 절의 해석과 "이 판독들이 아직 가르지 못한 것"에서 닫힌 항목을 갱신한다. 「엔진은 예열 구간을 하나의 낮은 고정 연사로 모델한다」와 「이 모델은 MG 연사에 대해 하한이다」는 **더 이상 참이 아니므로** 현재 모델을 서술하도록 바꾼다.

- [ ] **Step 5: 능력 카탈로그 (CLAUDE.md 규칙 — 같은 변경에서)**

`.claude/skills/nikke-skill-encoding/references/engine-capabilities.md:163`의 `mg_heating_speed_percent` 행에서:
- 클램프 서술을 **구간별**로 바꾼다.
- ▲100%의 값을 **1.1417초 → 1.325초(79.5프레임)**로 고친다. ▼100% 4.5667초는 그대로다.
- 램프가 **곡선**이라는 것과, 짧은 재장전 뒤에는 탄창이 램프 **중간에서** 열린다는 것을 넣는다.

- [ ] **Step 6: `docs/roadmap.md`**

`:27` 부근의 MG 평균 1.125x(n=5)와 캘리 헤드라인을 새 값으로 갱신한다.

- [ ] **Step 7: 전체 스위트와 커밋**

Run: `cd backend && python -m pytest -q`
Expected: 기준선.

```bash
git add docs/ .claude/skills/nikke-skill-encoding/references/engine-capabilities.md
git commit -m "램프 곡선 착륙을 문서와 능력 카탈로그에 반영한다"
```

- [ ] **Step 8: 결정을 기록한다**

`/document`로 docs-keeper에 넘긴다: D=66 선택과 세 추정이 어긋난다는 사실, 지연을 같이 넣은 이유(정합성이지 상쇄가 아님), 구간별 클램프 판정과 그것이 레이를 약화시킨다는 것, 그리고 **크라운이 램프 제거에도 안 움직여서 MG 과대의 진짜 항이 따로 있다는 것**(다음 작업의 표적).

---

## 이 계획이 다루지 않는 것

- **MG의 남은 과대항.** 이 배선이 상쇄를 걷어내면 드러난다. 크라운 1.34x가 그 얼굴이고, 별도 조사다.
- **위치 2~24 사이의 모양.** 직선 근사로 남는다.
- **재장전 속도 100% 초과에서 고정 구간 0.148초의 생사.** 현행 클립을 유지한다.
- **화살표가 감쇠를 바꾸는가.** D는 상수로 남는다.
