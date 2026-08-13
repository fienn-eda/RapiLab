# 부분 재장전 / 탄약 환급 프리미티브 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `AmmoRefund`의 네 축(퍼센트 단위·시각 트리거·아군 대상·로테이션 위상)을 열어, 보류 중인 여섯 줄의 재장전을 인코딩한다.

**Architecture:** 모든 환급 로직은 `attack_rate.magazine_shot_count` 한 곳에 둔다 — 호출부가 11곳이라 생성기 루프에 흩으면 어긋난다. 라운드 시각은 호출부마다 식이 다르므로 `time_of_round(i)` 콜러블로 주입받는다. 시각 트리거는 `simulate_burst_cycle`이 발사 생성보다 먼저 끝난다는 사실에 기댄다.

**Tech Stack:** Python 3.14, pytest. 백엔드 전용, 프론트 변경 없음.

**Spec:** `docs/superpowers/specs/2026-08-13-partial-ammo-refill-design.md`

## Global Constraints

- **테스트는 반드시 `backend/`에서 돌린다.** 루트에서는 `No module named 'app'`으로 수집이 깨진다.
- **기존 `backend/tests/test_ammo_refund.py`의 17건은 한 글자도 수정하지 않는다.** 이것이 「환급이 없으면 비트 동일」의 계약이다. 그 파일에는 **추가만** 한다.
- **`backend/app/charge_window.py`는 이 계획에서 건드리지 않는다.** 전투 절대 시각이 없는 한 창짜리 계산기다.
- 반올림은 `round()`(파이썬 기본, banker's rounding) — 기존 `max_ammo` 용량 계산이 쓰는 것과 **같은 함수**를 쓴다.
- 주석·독스트링은 **무엇을·왜**만 적는다. 「예전엔 이랬다」는 쓰지 않는다.
- 커밋 메시지는 한국어 명령형 한 줄 + 본문.

---

### Task 1: 퍼센트 단위와 `rounds_for`

**Files:**
- Modify: `backend/app/attack_rate.py:124-168` (`AmmoRefund`, `_refund_sequence`), `:171-193` (`magazine_shot_count`)
- Test: `backend/tests/test_ammo_refund.py` (추가만)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `AmmoRefund(every_shots:int, rounds:int=0, percent:float=0.0)`, 메서드 `rounds_for(capacity:int) -> int`. `_refund_sequence(refund, capacity)` — 인자 하나 추가.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_ammo_refund.py` 맨 끝에 추가:

```python
# Tove's Favorite Item build: "Activates after 10 normal attack(s). Affects
# self. Reload 5.31% of the magazine." She is an AR with 60 rounds, so the
# percentage is worth 3 whole rounds - the unit the engine hands back.
TOVE = AmmoRefund(every_shots=10, percent=5.31)


def test_a_percentage_refund_resolves_against_the_magazine_it_lands_in():
    assert TOVE.rounds_for(60) == 3


def test_a_percentage_too_small_for_one_round_hands_back_nothing():
    # 5.31% of 9 is 0.478 - below half a round, so it rounds away.
    assert TOVE.rounds_for(9) == 0


def test_a_refund_declared_in_rounds_ignores_capacity():
    assert BASTION.rounds_for(9) == 3
    assert BASTION.rounds_for(600) == 3


def test_a_percentage_refund_fires_on_the_same_counter_as_a_round_refund():
    # 3 rounds back every 10 shots off a 60-round magazine: shots 10..60 each
    # add 3 when the counter lands, and the magazine walks past its capacity.
    by_percent = magazine_shot_count(60, 0, TOVE)
    by_rounds = magazine_shot_count(60, 0, AmmoRefund(every_shots=10, rounds=3))
    assert by_percent == by_rounds


def test_a_percentage_refund_that_outpaces_the_trigger_is_rejected():
    # 20% of a 60-round magazine is 12 rounds every 10 shots - it never empties.
    greedy = AmmoRefund(every_shots=10, percent=20.0)
    with pytest.raises(ValueError, match="never empties"):
        magazine_shot_count(60, 0, greedy)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v -k "percentage or ignores_capacity"`
Expected: FAIL — `TypeError: AmmoRefund.__init__() got an unexpected keyword argument 'percent'`

- [ ] **Step 3: 최소 구현**

`backend/app/attack_rate.py`의 `AmmoRefund`를 바꾼다:

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

    Those two together are why this cannot be a max-ammo percentage: how much a
    refund is worth depends on where in the magazine it lands, and a magazine
    that refills mid-fight shifts every later reload against the Full Burst
    window. Faking it as a flat percentage scores non-monotonically.

    A refund states its size either in whole `rounds` or as a `percent` of the
    magazine it lands in ("Reload 5.31% of the magazine", Tove's Favorite Item).
    A percentage is rounded to the nearest whole round, the same convention
    magazine capacity itself uses (Fienn, 2026-08-13).
    """
    every_shots: int
    rounds: int = 0
    percent: float = 0.0

    def __post_init__(self):
        if self.rounds and self.rounds >= self.every_shots:
            raise ValueError(
                f"a refund of {self.rounds} every {self.every_shots} shots never "
                "empties the magazine")

    def rounds_for(self, capacity):
        """Whole rounds this hands back into a magazine of `capacity`."""
        if self.rounds:
            return self.rounds
        return round(capacity * self.percent / 100.0)
```

`_refund_sequence`가 용량을 받게 한다:

```python
def _refund_sequence(refund, capacity):
    """`refund` as a tuple, rejecting a set that never empties the magazine.

    A unit can hold more than one source at once - EVE reloads 3 rounds every
    10 shots off her own skill and a Tactical Bear cube hands back 3 more on
    the same cadence - and each keeps its own trigger against the shared shot
    counter. `AmmoRefund` can only vet a whole-round refund by itself, so the
    combined rate is checked here, where the magazine's capacity is known and a
    percentage can finally be resolved: at one round back per shot the walk
    below would never terminate.
    """
    if refund is None:
        return ()
    refunds = (refund,) if isinstance(refund, AmmoRefund) else tuple(refund)
    if sum(r.rounds_for(capacity) / r.every_shots for r in refunds) >= 1:
        raise ValueError(
            f"refunds {refunds} together hand back a round per shot, so the "
            "magazine never empties")
    return refunds
```

`magazine_shot_count` 안의 두 줄을 바꾼다:

```python
    refunds = _refund_sequence(refund, capacity)
    ...
        for one in refunds:
            if counter % one.every_shots == 0:
                rounds = min(capacity, rounds + one.rounds_for(capacity))
```

- [ ] **Step 4: 새 테스트와 기존 17건이 모두 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v`
Expected: PASS, 22 passed. **기존 17건이 수정 없이 초록이어야 한다.**

Run: `cd backend && python -m pytest -q`
Expected: PASS, 2249 passed / 3 skipped. `_refund_sequence`의 시그니처가 바뀌었으므로 전체를 돌려 호출부가 하나뿐임을 확인한다.

- [ ] **Step 5: 가드를 떼서 새 테스트가 진짜 재는지 확인한다**

`rounds_for`의 `return round(...)`를 `return int(...)`(버림)로 잠깐 바꾼다.
Run: `cd backend && python -m pytest tests/test_ammo_refund.py -k resolves_against -v`
Expected: FAIL (3 != 3.186→3... 확인 후) — **버림으로 바꿔도 60의 경우는 3이므로 이 테스트만으로는 부족하다.** `rounds_for(9)`가 0인 테스트도 버림에서 0이라 통과한다. 따라서 **반올림을 실제로 고정하는 값**을 하나 더 넣어야 한다:

```python
def test_a_percentage_rounds_to_the_nearest_round_not_down():
    # 5.31% of 30 is 1.593 - a floor would hand back 1, the game hands back 2.
    assert AmmoRefund(every_shots=10, percent=5.31).rounds_for(30) == 2
```

이 테스트를 추가한 뒤 다시 버림으로 바꿔 **FAIL을 확인하고** 원복한다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_ammo_refund.py
git commit -m "탄약 환급이 탄창 퍼센트로도 선언되게 한다"
```

---

### Task 2: `AmmoRefill` — 시각 트리거를 깔때기에 넣는다

**Files:**
- Modify: `backend/app/attack_rate.py` (`AmmoRefill` 신설, `magazine_shot_count` 시그니처)
- Test: `backend/tests/test_ammo_refund.py` (추가만)

**Interfaces:**
- Consumes: Task 1의 `rounds_for(capacity)`
- Produces: `AmmoRefill(time:float, rounds:int=0, percent:float=0.0)` (같은 `rounds_for`), `magazine_shot_count(capacity, shots_before, refund, *, time_of_round=None, refills=(), stop_time=None) -> (int, int)`, 그리고 두 워크가 공유하는 `_apply_due_refills(pending, now, rounds, capacity) -> int`

**중요 — 워크는 하나가 아니다.** `_shared_magazine_shots`(`attack_rate.py:846`)는 `magazine_shot_count`를 거치지 않고 `_refund_sequence`를 직접 불러 **자기 인라인 워크**로 환급을 적용한다(`:913`). 이 태스크는 두 워크가 쓸 헬퍼를 만들고 `magazine_shot_count` 쪽만 배선한다. 공유 탄창 워크의 배선은 Task 3이 한다.

```python
def _apply_due_refills(pending, now, rounds, capacity):
    """Rounds after every refill due at `now` has landed, capped at capacity.

    Mutates `pending`, which both magazine walks keep as a time-sorted list of
    the refills they have not spent yet.
    """
    while pending and pending[0].time <= now:
        rounds = min(capacity, rounds + pending.pop(0).rounds_for(capacity))
    return rounds
```

`magazine_shot_count`의 워크는 인라인 `while pending ...` 대신 이 헬퍼를 부른다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
from app.attack_rate import AmmoRefill   # 파일 상단 import 블록에 추가


def _uniform_clock(magazine_start, interval):
    """Round i of a magazine that starts at `magazine_start` and fires every
    `interval` seconds - the shape both magazine and charge generators reduce
    to when spinup is absent."""
    return lambda i: magazine_start + i * interval


def test_a_refill_inside_the_magazine_adds_rounds_capped_at_capacity():
    # A 10-round magazine firing 1/sec from t=0: rounds land at 0..9. A refill
    # of 40% (4 rounds) at t=5 finds 4 spent, so all 4 come back.
    size, counter = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=(AmmoRefill(time=5.0, percent=40.0),))
    assert (size, counter) == (14, 14)


def test_a_refill_is_capped_by_what_the_magazine_has_spent():
    # Same magazine, refill at t=1: only 1 round is gone, so only 1 comes back.
    size, _ = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=(AmmoRefill(time=1.0, percent=40.0),))
    assert size == 11


def test_a_refill_that_lands_during_the_reload_is_wasted():
    # The magazine's last round fires at t=9; a refill at t=20 belongs to no
    # magazine this walk owns, and the NEXT magazine starts after it, so the
    # drop rule (time < magazine_start) throws it away. Fienn, 2026-08-13:
    # the reload finishes and the refill is worth nothing.
    size, _ = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(30.0, 1.0),   # this magazine opens at 30
        refills=(AmmoRefill(time=20.0, percent=40.0),))
    assert size == 10


def test_no_refills_never_touches_the_clock():
    # The clock raises if called - with no refills the walk must not ask for a
    # single round's time, which is what keeps every existing timeline exact.
    def exploding_clock(_i):
        raise AssertionError("time_of_round must not be called without refills")

    assert magazine_shot_count(9, 0, BASTION,
                               time_of_round=exploding_clock) == (9, 9)


def test_refills_and_the_shot_counter_refund_stack():
    # BASTION hands back 3 on shot 10; a refill adds 4 more at t=5.
    size, _ = magazine_shot_count(
        14, 0, BASTION,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=(AmmoRefill(time=5.0, rounds=4),))
    assert size == 21


def test_the_walk_stops_at_the_end_of_the_fight():
    # A refill every round would keep a magazine alive forever - which is what
    # Arcana's rotation really does inside her window. The walk is bounded by
    # the moment the fight (or the segment) ends, not by the magazine draining.
    forever = tuple(AmmoRefill(time=float(t), rounds=1) for t in range(60))
    size, _ = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=forever, stop_time=25.0)
    assert size == 25
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v -k "refill"`
Expected: FAIL — `ImportError: cannot import name 'AmmoRefill'`

- [ ] **Step 3: 구현**

`AmmoRefund` 바로 아래에 넣는다:

```python
@dataclass(frozen=True)
class AmmoRefill:
    """Rounds handed back at a KNOWN TIME rather than on a shot counter.

    "Reload 39.88% magazine(s)" on entering Full Burst (Noir) is this shape: the
    trigger is an event the burst cycle already scheduled, not a count of the
    recipient's own shots, and the recipient may not even be the caster. The
    burst cycle is solved before any shot is generated, so these times are known
    when the magazine walk runs.

    A refill that lands while the recipient is reloading is WASTED - the reload
    finishes on its own and the rounds are worth nothing (Fienn, 2026-08-13).
    The walk gets that for free: such a refill is older than the next magazine's
    start, and the walk drops anything older than the magazine it is filling.
    """
    time: float
    rounds: int = 0
    percent: float = 0.0

    def rounds_for(self, capacity):
        """Whole rounds this hands back into a magazine of `capacity`."""
        if self.rounds:
            return self.rounds
        return round(capacity * self.percent / 100.0)
```

`magazine_shot_count`를 바꾼다:

```python
def magazine_shot_count(capacity, shots_before, refund, *,
                        time_of_round=None, refills=(), stop_time=None):
    """Rounds this magazine actually fires, and the shot counter afterwards.

    Walks the magazine one round at a time because a refund's value depends on
    the rounds remaining when it lands (it is capped at capacity), and the
    counter it triggers on runs across magazines. `refund` is one AmmoRefund, a
    sequence of them, or None; None returns the capacity untouched, so every
    timeline without a refund keeps its exact arithmetic.

    `refills` are `AmmoRefill`s anywhere in the fight; `time_of_round(i)` gives
    the absolute time of this magazine's 0-based round i. It is a callable
    rather than a set of parameters because the formula differs by weapon -
    magazine weapons offset by spinup, charge weapons by charge time - and each
    generator already holds its own. With no refills it is never called, so a
    timeline without one does no time arithmetic at all.

    `stop_time` ends the walk at the moment the fight (or the segment) does. A
    refund can hand back as much as the magazine spends - Arcana's rotation
    reloads 6 rounds every 6 shots, which is exactly the point of it - so a
    magazine can stay alive indefinitely and draining is not a termination
    guarantee once time is in play.
    """
    refunds = _refund_sequence(refund, capacity)
    if not refunds and not refills:
        return capacity, shots_before + capacity
    pending = [r for r in refills
               if time_of_round is None or r.time >= time_of_round(0)]
    pending.sort(key=lambda r: r.time)
    rounds = capacity
    shots = 0
    counter = shots_before
    while rounds > 0:
        now = time_of_round(shots) if time_of_round is not None else None
        if stop_time is not None and now is not None and now >= stop_time:
            break
        while pending and pending[0].time <= now:
            rounds = min(capacity, rounds + pending.pop(0).rounds_for(capacity))
        rounds -= 1
        shots += 1
        counter += 1
        for one in refunds:
            if counter % one.every_shots == 0:
                rounds = min(capacity, rounds + one.rounds_for(capacity))
    return shots, counter
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v`
Expected: PASS, 29 passed. 기존 17건 그대로.

Run: `cd backend && python -m pytest -q`
Expected: PASS, 2249 passed / 3 skipped. `magazine_shot_count`의 조기 반환 조건이 바뀌었으므로 전체를 돌린다.

- [ ] **Step 5: 드롭 규칙을 떼서 확인한다**

`pending = [r for r in refills ...]`의 필터를 `pending = list(refills)`로 잠깐 바꾼다.
Run: `cd backend && python -m pytest tests/test_ammo_refund.py -k wasted -v`
Expected: FAIL (`size == 14`, 기대 10). 확인 후 원복한다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_ammo_refund.py
git commit -m "알려진 시각에 떨어지는 탄약 환급을 표현한다"
```

---

### Task 3: 여덟 생성기에 배선한다

**Files:**
- Modify: `backend/app/attack_rate.py` — `generate_magazine_shot_times:381`, `generate_charge_shot_times:414`, `generate_shot_times:448`, `magazine_last_bullet_times:475`, `charge_last_bullet_times:524`, `magazine_first_bullet_times:560`, `charge_first_bullet_times:594`, `first_bullet_shot_times:629`, `last_bullet_shot_times:659`, `_base_shot_records`(:742/:761), `generate_segmented_shots:946`
- Test: `backend/tests/test_ammo_refund.py` (추가만)

**Interfaces:**
- Consumes: Task 2의 `magazine_shot_count(..., time_of_round=, refills=)`
- Produces: 위 공개 함수 전부가 `ammo_refills=()` 키워드를 받는다. `generate_segmented_shots`는 `base["ammo_refills"]`로도 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_a_refill_adds_shots_to_a_magazine_weapons_timeline():
    without = generate_shot_times("AR", 60, 1.0, 0.0, 180.0)
    with_refill = generate_shot_times(
        "AR", 60, 1.0, 0.0, 180.0,
        ammo_refills=(AmmoRefill(time=30.0, percent=50.0),))
    assert len(with_refill) == len(without) + 30


def test_a_refill_adds_shots_to_a_charge_weapons_timeline():
    without = generate_shot_times("RL", 9, 2.0, 0.3, 180.0)
    with_refill = generate_shot_times(
        "RL", 9, 2.0, 0.3, 180.0,
        ammo_refills=(AmmoRefill(time=1.0, rounds=4),))
    assert len(with_refill) > len(without)


def test_a_timeline_without_refills_is_unchanged():
    assert generate_shot_times("RL", 9, 2.0, 0.3, 180.0) == \
        generate_shot_times("RL", 9, 2.0, 0.3, 180.0, ammo_refills=())


def test_last_bullet_times_follow_the_refilled_magazine():
    # The refill extends the magazine, so the round that empties it moves.
    kw = dict(ammo_refills=(AmmoRefill(time=5.0, rounds=4),))
    times = generate_shot_times("AR", 60, 1.0, 0.0, 180.0, **kw)
    lasts = last_bullet_shot_times("AR", 60, 1.0, 0.0, 180.0, **kw)
    assert times[63] in lasts
    assert times[59] not in lasts


def test_a_refill_during_a_weapon_transform_is_wasted():
    """A transform silences the base weapon, so a refill that lands inside one
    reaches no magazine - the base weapon resumes AFTER it, and the walk drops
    anything older than the magazine it is filling. Same shape as the reload
    gap, and the segment path already rules that a transform's own shots do not
    count toward a refund's trigger."""
    base = dict(RL, ammo_refills=(AmmoRefill(time=10.0, percent=100.0),))
    segment = {"start": 5.0, "end": 20.0, "weapon": "RL", "damage_percent": 1.0,
               "charge_damage_percent": 100.0, "max_ammo": 5,
               "reload_time": 0.0, "charge_time": 1.0}
    during = generate_segmented_shots(base, [segment], 60.0)
    no_refill = generate_segmented_shots(dict(RL), [segment], 60.0)
    assert [r.time for r in during] == [r.time for r in no_refill]
```

> **구현자 주의:** 위 `segment` 딕셔너리의 키 이름은 **추측이다.** 실제 모양은 `backend/tests/test_ammo_refund.py:89`(`_shared_magazine_case`)에 있다: `dict(start=5.0, until_shots=3, profile=dict(weapon=..., charge_time=..., damage_percent=..., charge_damage_percent=...))`. **이 테스트에는 `shares_magazine=True`를 넣지 말 것** — 그 플래그는 `_shared_magazine_shots`라는 다른 경로로 가고, 거기서는 기저 무기가 침묵하지 않는다. 환급을 base 딕트에 싣는 방법은 같은 파일 `:123`을 볼 것.

그리고 공유 탄창 경로에도 **자기 테스트**가 필요하다(그쪽은 기저 무기가 침묵하지 않으므로 환급이 실제로 도착해야 한다):

```python
def test_a_shared_magazine_segment_receives_timed_refills():
    # Snow White: Heavy Arms' mode draws from her own magazine, so a refill
    # from an ally reaches her the same as it reaches anyone else.
    plain_base, segment = _shared_magazine_case()
    refilled_base, _ = _shared_magazine_case(
        ammo_refills=(AmmoRefill(time=10.0, percent=100.0),))
    plain = generate_segmented_shots(plain_base, segment, 60.0)
    refilled = generate_segmented_shots(refilled_base, segment, 60.0)
    assert len(refilled) > len(plain)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v -k "refill and timeline or follow_the_refilled"`
Expected: FAIL — `TypeError: generate_shot_times() got an unexpected keyword argument 'ammo_refills'`

- [ ] **Step 3: 구현 — 여덟 지점 모두 같은 모양으로**

각 함수에 `ammo_refills=()` 파라미터를 더하고, 그 함수의 지역 변수로 클로저를 만들어 넘긴다. **탄창 무기 지점**(`:400`, `:511`, `:586`, `:761`)은 전부:

```python
        magazine_size, shots_fired = magazine_shot_count(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, iv=shot_interval, sp=spinup: (
                s + magazine_shot_offset(i, iv, sp)),
            refills=ammo_refills, stop_time=fight_duration)
```

`_base_shot_records`의 탄창 가지(`:761`)에서는 지역 이름이 `interval`이고 환급은 `refund`이므로 `iv=interval`, 두 번째 인자는 `refund`, **`stop_time=window_end`** 로 쓴다(그 함수에는 `fight_duration`이 아니라 `window_end`가 있다).

**차지 무기 지점**(`:434`, `:549`, `:622`, `:742`)은 전부:

```python
        magazine_size, shots_fired = magazine_shot_count(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, c=effective_charge: (
                s + c + i * c),
            refills=ammo_refills, stop_time=fight_duration)
```

`_base_shot_records`의 차지 가지(`:742`)에서도 두 번째 인자는 `refund`, `stop_time=window_end`다.

**기본값 인자로 묶는 것이 중요하다** — `lambda i: magazine_start + ...`로 쓰면 while 루프가 변수를 다시 묶어 다음 탄창의 값을 읽는다.

디스패처 둘(`generate_shot_times:448`, `first_bullet_shot_times:629`, `last_bullet_shot_times:659`)은 `ammo_refills`를 그대로 넘기기만 한다.

`_base_shot_records`는 `base.get("ammo_refills", ())`로 읽고, `generate_segmented_shots`는 그 `base` 딕셔너리를 이미 통째로 받으므로 **추가 파라미터가 필요 없다.**

**아홉 번째 지점 — `_shared_magazine_shots`(`:846`).** 이 함수는 `magazine_shot_count`를 거치지 않으므로 위 배선을 **하나도 물려받지 않는다.** 시간 순으로 발마다 걷고 재장전도 인라인(`:921-927`)이라, 오히려 시각을 이미 들고 있어 배선이 더 간단하다:

```python
    refills = sorted(base.get("ammo_refills", ()), key=lambda r: r.time)
    pending = [r for r in refills if r.time >= 0.0]
```

그리고 발마다 `shot_time`이 정해진 직후(`rounds -= 1` **앞**)에:

```python
        rounds = _apply_due_refills(pending, shot_time, rounds, capacity)
```

인라인 재장전 뒤(`:925-927`의 `rounds = capacity` 옆)에 **오래된 환급을 버린다**:

```python
            while pending and pending[0].time < cursor:
                pending.pop(0)
```

이것이 「재장전 중에 떨어진 환급은 버려진다」를 이 워크에서 지키는 방법이다. 이 줄이 없으면 재장전 구간에 떨어진 환급이 다음 발에서 적용돼 판정을 어긴다.

**왜 빼면 안 되나:** 이 경로의 소비자는 스노우화이트: 헤비 암즈이고 그녀는 실기록 덱4에 있다. 빼면 느와르의 아군 환급이 네 좌석에는 가고 그녀에게만 안 가, 기능이 조용히 유닛별로 갈린다.

- [ ] **Step 4: 통과와 전체 스위트를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v`
Expected: PASS, 32 passed.

Run: `cd backend && python -m pytest -q`
Expected: PASS, 2249 passed / 3 skipped — **한 건도 안 늘고 안 줄어야 한다.** 늘었다면 어딘가 배선이 새 동작을 켠 것이다.

- [ ] **Step 5: 클로저 늦은 바인딩을 확인한다**

한 지점의 `s=magazine_start` 기본값 묶음을 떼고 `lambda i: magazine_start + ...`로 바꾼다.
Run: `cd backend && python -m pytest tests/test_ammo_refund.py -k "magazine_weapons_timeline" -v`
Expected: FAIL — 두 번째 탄창부터 시각이 어긋나 발수가 달라진다. 확인 후 원복한다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_ammo_refund.py
git commit -m "여덟 발사 타임라인 생성기가 시각 환급을 받게 한다"
```

---

### Task 4: 로테이션 위상 — `first_shot`과 `windows`

**Files:**
- Modify: `backend/app/attack_rate.py` (`AmmoRefund`, `magazine_shot_count`)
- Test: `backend/tests/test_ammo_refund.py` (추가만)

**Interfaces:**
- Consumes: Task 2의 워크
- Produces: `AmmoRefund(..., first_shot:int=0, windows:tuple=())`. `windows`는 `((start, end), ...)`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

위상 자체는 순수 메서드라 **직접** 잰다 — 워크에서 역산하지 않는다.

```python
def test_the_rotation_phase_fires_on_two_eight_and_fourteen():
    # Arcana: "Two times: Reloads 6 rounds" is one phase of a period-6
    # rotation. Fienn counted to the 18th normal in game (2026-07-28): the
    # 12th does NOT reload. A bare "every 6" would give [6, 12, 18].
    rotation = AmmoRefund(every_shots=6, rounds=6, first_shot=2)
    assert [n for n in range(1, 19) if rotation.fires_at(n)] == [2, 8, 14]


def test_a_refund_without_a_phase_keeps_the_bare_period():
    assert [n for n in range(1, 31) if BASTION.fires_at(n)] == [10, 20, 30]


def test_a_refund_without_windows_counts_every_shot_of_the_fight():
    assert BASTION.counts(0.0) and BASTION.counts(179.0)


def test_a_windowed_refund_counts_only_shots_inside_a_window():
    windowed = AmmoRefund(every_shots=6, rounds=6, first_shot=2,
                          windows=((10.0, 20.0), (50.0, 60.0)))
    assert not windowed.counts(9.9)
    assert windowed.counts(10.0)
    assert not windowed.counts(20.0)      # half-open, like every other window
    assert windowed.counts(55.0)
```

그리고 워크가 그 위상을 실제로 쓰는지 **작은 탄창 하나로** 확인한다. 손으로 셀 수 있는 크기만 쓴다.

```python
def test_the_window_local_counter_moves_the_magazine():
    # Capacity 3, one round back, phase (first=2, period=6), 1 shot/sec, all
    # inside the window. Shots: 1 -> 2 left; 2 -> 1 left, refund makes it 2;
    # 3 -> 1 left; 4 -> empty. Four shots out of a three-round magazine.
    phased = AmmoRefund(every_shots=6, rounds=1, first_shot=2,
                        windows=((0.0, 100.0),))
    assert magazine_shot_count(3, 0, phased,
                               time_of_round=_uniform_clock(0.0, 1.0),
                               stop_time=100.0) == (4, 4)


def test_a_bare_period_would_not_reach_that_magazine_at_all():
    # The same refund without the phase fires at shot 6, which a three-round
    # magazine never reaches - so it fires exactly its capacity.
    bare = AmmoRefund(every_shots=6, rounds=1, windows=((0.0, 100.0),))
    assert magazine_shot_count(3, 0, bare,
                               time_of_round=_uniform_clock(0.0, 1.0),
                               stop_time=100.0) == (3, 3)


def test_the_window_local_counter_restarts_with_each_window():
    # Two windows, the magazine spanning both. In the second window the phase
    # must start over at 2 rather than carry the first window's count.
    two = AmmoRefund(every_shots=6, rounds=1, first_shot=2,
                     windows=((0.0, 3.0), (10.0, 13.0)))
    # Rounds land at t = 0,1,2,... Window one counts shots at t=0,1,2 (local
    # 1,2,3 - refund on local 2); window two counts t=10,11,12 (local 1,2,3 -
    # refund again on local 2). Two refunds into a 6-round magazine.
    assert magazine_shot_count(6, 0, two,
                               time_of_round=_uniform_clock(0.0, 1.0),
                               stop_time=100.0) == (8, 8)


def test_shots_outside_every_window_never_trigger():
    late = AmmoRefund(every_shots=6, rounds=1, first_shot=2,
                      windows=((50.0, 60.0),))
    assert magazine_shot_count(6, 0, late,
                               time_of_round=_uniform_clock(0.0, 1.0),
                               stop_time=100.0) == (6, 6)
```

> **구현자 주의:** `test_the_window_local_counter_restarts_with_each_window`의 기대값 `(8, 8)`은 위 주석의 손계산에서 나온 것이다. **먼저 돌려서 실제 값을 보고**, 다르면 손계산을 다시 하라 — 워크의 순서(환급을 라운드 소모 전에 적용하는지 후에 적용하는지)에 따라 한 발 어긋날 수 있다. 값을 맞추려고 구현을 바꾸지 말고, **어느 쪽이 원문에 맞는지** 판단해 기대값이나 구현 중 옳은 쪽을 고칠 것.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v -k "phase or period or window_local or counts or outside_every"`
Expected: FAIL — `TypeError: AmmoRefund.__init__() got an unexpected keyword argument 'first_shot'`

- [ ] **Step 3: 구현**

`AmmoRefund`에 필드 둘을 더하고 발동 판정을 메서드로 뽑는다:

```python
    every_shots: int
    rounds: int = 0
    percent: float = 0.0
    first_shot: int = 0
    windows: tuple = ()

    def fires_at(self, count):
        """Whether the `count`-th shot this refund has counted triggers it.

        `first_shot` is the rotation's phase: Arcana's reload is the 2nd, 8th,
        14th ... attack of a period-6 rotation, not the 6th and 12th. Left at 0
        the phase is the period itself, which is the plain "every N shots" the
        cube and EVE use.
        """
        first = self.first_shot or self.every_shots
        return count >= first and (count - first) % self.every_shots == 0

    def counts(self, time):
        """Whether a shot at `time` advances this refund's counter. A refund
        with no windows counts every shot of the fight."""
        return not self.windows or any(s <= time < e for s, e in self.windows)
```

`magazine_shot_count`의 워크에서 창 있는 환급은 **자기 카운터**를 따로 든다:

```python
    windowed = [r for r in refunds if r.windows]
    plain = [r for r in refunds if not r.windows]
    local = {id(r): 0 for r in windowed}
    last_window = {id(r): None for r in windowed}
    ...
    while rounds > 0:
        now = time_of_round(shots) if time_of_round is not None else None
        ...
        rounds -= 1
        shots += 1
        counter += 1
        for one in plain:
            if one.fires_at(counter):
                rounds = min(capacity, rounds + one.rounds_for(capacity))
        for one in windowed:
            window = next((w for w in one.windows if w[0] <= now < w[1]), None)
            if window is None:
                continue
            if last_window[id(one)] != window:
                last_window[id(one)] = window
                local[id(one)] = 0
            local[id(one)] += 1
            if one.fires_at(local[id(one)]):
                rounds = min(capacity, rounds + one.rounds_for(capacity))
```

`plain` 쪽이 `counter % one.every_shots == 0` 대신 `one.fires_at(counter)`를 쓰게 되는데, `first_shot=0`이면 `first = every_shots`라 **기존과 같은 조건**이다.

`_refund_sequence`의 합계 검사는 창 있는 환급을 그대로 세면 과하게 거절한다(창 밖에서는 안 나가므로). 창 있는 환급은 검사에서 뺀다:

```python
    if sum(r.rounds_for(capacity) / r.every_shots
           for r in refunds if not r.windows) >= 1:
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refund.py -v`
Expected: PASS. 기존 17건 여전히 그대로.

- [ ] **Step 5: 위상을 떼서 확인한다**

`fires_at`의 `first = self.first_shot or self.every_shots`를 `first = self.every_shots`로 바꾼다.
Run: `cd backend && python -m pytest tests/test_ammo_refund.py -k "phase or window_local" -v`
Expected: FAIL — `[2, 8, 14]`가 `[6, 12, 18]`로 나오고, 3발 탄창은 4발이 아니라 3발을 쏜다. **이것이 Fienn의 결정적 부정(12번째에는 안 뜬다)을 테스트가 실제로 재고 있다는 증거다.** 확인 후 원복한다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_ammo_refund.py
git commit -m "환급이 창 안에서 자기 위상으로 도는 로테이션을 표현한다"
```

---

### Task 5: 선언 경로와 아군 팬아웃

**Files:**
- Modify: `backend/app/skill_rules/registry.py:1372-1392` 부근 (새 `_AMMO_REFILL_GRANTS` + `get_ammo_refill_grant`), `backend/app/roster.py:136-155`, `backend/app/raid_simulator.py:151-170`(옆에 `resolve_ammo_refills` 신설), `:1242-1250`(루프 앞 전처리 + `weapon` 합류)
- Test: `backend/tests/test_ammo_refill_fanout.py` (신설)

**Interfaces:**
- Consumes: Task 2의 `AmmoRefill`
- Produces: `registry.get_ammo_refill_grant(slug, skill_values) -> dict | None` — `{"percent"|"rounds": float|int, "scope": "self"|"squad", "event": "own_burst"|"full_burst_enter"}`. `raid_simulator.resolve_ammo_refills(deck, events) -> dict[str, tuple[AmmoRefill, ...]]`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_ammo_refill_fanout.py` 신설:

```python
"""Who receives a refill, and when.

A refill's trigger is an event the burst cycle already scheduled, so the
simulator - not the roster - resolves it: the roster assembles a deck and does
not know the encounter, the same split the boss-element gate on skill refunds
already uses.
"""
from app.attack_rate import AmmoRefill
from app.raid_simulator import resolve_ammo_refills


def _member(slug, grant=None):
    member = {"slug": slug}
    if grant is not None:
        member["ammo_refill_grant"] = grant
    return member


EVENTS = [
    {"type": "burst", "tier": 1, "slug": "noir", "time": 3.0},
    {"type": "full_burst_start", "time": 5.0},
    {"type": "full_burst_end", "time": 15.0},
    {"type": "burst", "tier": 3, "slug": "little-mermaid", "time": 44.0},
    {"type": "full_burst_start", "time": 46.0},
    {"type": "full_burst_end", "time": 56.0},
]


def test_a_squad_refill_reaches_every_member_including_the_caster():
    deck = [_member("noir", {"percent": 39.88, "scope": "squad",
                             "event": "full_burst_enter"}),
            _member("scarlet-black-shadow"), _member("liberalio")]
    refills = resolve_ammo_refills(deck, EVENTS)
    for slug in ("noir", "scarlet-black-shadow", "liberalio"):
        assert [r.time for r in refills[slug]] == [5.0, 46.0]
        assert refills[slug][0].percent == 39.88


def test_a_self_refill_reaches_nobody_else():
    deck = [_member("asuka-shikinami-langley-wille",
                    {"percent": 21.0, "scope": "self", "event": "own_burst"}),
            _member("liberalio")]
    refills = resolve_ammo_refills(deck, [
        {"type": "burst", "tier": 3,
         "slug": "asuka-shikinami-langley-wille", "time": 9.0}])
    assert [r.time for r in refills["asuka-shikinami-langley-wille"]] == [9.0]
    assert refills.get("liberalio", ()) == ()


def test_an_own_burst_refill_reads_the_casters_burst_times_not_full_burst():
    deck = [_member("little-mermaid", {"percent": 33.26, "scope": "squad",
                                       "event": "own_burst"}),
            _member("liberalio")]
    refills = resolve_ammo_refills(deck, EVENTS)
    assert [r.time for r in refills["liberalio"]] == [44.0]


def test_a_deck_with_no_grant_gets_no_refills():
    deck = [_member("liberalio"), _member("scarlet-black-shadow")]
    assert resolve_ammo_refills(deck, EVENTS) == {}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_fanout.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_ammo_refills'`

- [ ] **Step 3: 구현**

`backend/app/raid_simulator.py`의 `resolve_ammo_refunds` 바로 아래:

```python
def resolve_ammo_refills(deck, events):
    """Every timed ammo refill each deck member receives, by slug.

    A grant names its trigger as an event the burst cycle logs - "when entering
    Full Burst" (Noir) or the caster's own burst (Little Mermaid, Asuka, Arcana)
    - and its scope as self or the whole squad. Resolving it here rather than in
    the roster is the same split the boss-element gate on skill refunds uses:
    the roster assembles a deck and does not know the encounter.
    """
    refills = {}
    for member in deck:
        grant = member.get("ammo_refill_grant")
        if not grant:
            continue
        if grant["event"] == "full_burst_enter":
            times = [e["time"] for e in events if e["type"] == "full_burst_start"]
        else:
            times = [e["time"] for e in events
                     if e["type"] == "burst" and e["slug"] == member["slug"]]
        if not times:
            continue
        recipients = ([m["slug"] for m in deck] if grant["scope"] == "squad"
                      else [member["slug"]])
        for slug in recipients:
            refills.setdefault(slug, []).extend(
                AmmoRefill(time=t, rounds=grant.get("rounds", 0),
                           percent=grant.get("percent", 0.0))
                for t in times)
    return {slug: tuple(sorted(items, key=lambda r: r.time))
            for slug, items in refills.items()}
```

`from app.attack_rate import ... AmmoRefill`을 그 파일의 import에 더한다.

유닛 루프 **앞**(`events`/`full_burst_windows` 계산 뒤, `for slug, weapon in weapon_stats.items():` 위)에:

```python
    # 시각 트리거 환급은 버스트 일정이 정해진 뒤에야 시각을 갖는다. 버스트 사이클은
    # 발사 시각을 보지 않으므로 여기서 이미 확정돼 있고, 아군에게 가는 환급도 이
    # 시점에 나눠 담을 수 있다.
    ammo_refills = resolve_ammo_refills(deck, events)
```

루프 안 `weapon = {**weapon, "ammo_refund": ...}` 줄을 바꾼다:

```python
        weapon = {**weapon,
                  "ammo_refund": resolve_ammo_refunds(weapon, boss_element),
                  "ammo_refills": ammo_refills.get(slug, ())}
```

`registry.py`에 `_SKILL_AMMO_REFUNDS` 아래로:

```python
# 시각 트리거 환급을 주는 유닛. 값은 시뮬레이터가 버스트 일정에 맞춰 시각으로
# 바꾼다(raid_simulator.resolve_ammo_refills) - 로스터는 덱을 조립할 뿐 인카운터를
# 모르므로, 보스 원소 게이트와 같은 이유로 여기서 시각을 만들지 않는다.
_AMMO_REFILL_GRANTS = {}


def get_ammo_refill_grant(slug, skill_values):
    """{"percent"|"rounds", "scope", "event"} for a Nikke whose skill reloads a
    magazine at a scheduled moment, else None."""
    builder = _AMMO_REFILL_GRANTS.get(slug)
    return builder(skill_values) if builder else None
```

`roster.py`의 timeline 블록 뒤(멤버 딕셔너리를 만드는 곳)에:

```python
        # 시각 트리거 환급은 스탯이 아니라 받는 쪽의 발사 타임라인을 바꾸고, 스쿼드
        # 스코프면 다른 멤버에게 간다. 그래서 무기가 아니라 멤버에 실어 시뮬레이터가
        # 덱 전체를 보고 나눠 담게 한다.
        refill_grant = get_ammo_refill_grant(spec.slug, spec.skill_values)
        if refill_grant is not None:
            member["ammo_refill_grant"] = refill_grant
```

`roster.py`의 registry import에 `get_ammo_refill_grant`를 더한다.

- [ ] **Step 4: 통과와 전체 스위트를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_fanout.py -v`
Expected: PASS, 4 passed.

Run: `cd backend && python -m pytest -q`
Expected: PASS, 2249 passed / 3 skipped (`_AMMO_REFILL_GRANTS`가 비어 있으므로 아직 아무 유닛도 안 바뀐다).

- [ ] **Step 5: 스코프를 뒤집어 확인한다**

`recipients`의 `"squad"` 분기를 `[member["slug"]]`로 잠깐 바꾼다.
Run: `cd backend && python -m pytest tests/test_ammo_refill_fanout.py -k squad_refill -v`
Expected: FAIL — `KeyError: 'scarlet-black-shadow'`. 확인 후 원복한다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/raid_simulator.py backend/app/roster.py backend/app/skill_rules/registry.py backend/tests/test_ammo_refill_fanout.py
git commit -m "시각 환급의 선언 경로와 아군 팬아웃을 만든다"
```

---

### Task 6: 자기 대상 둘 — 토브 애장품과 아스카

**Files:**
- Modify: `backend/app/skill_rules/tove.py`, `backend/app/skill_rules/asuka_shikinami_langley_wille.py`, `backend/app/skill_rules/registry.py`
- Test: `backend/tests/test_ammo_refill_units.py` (신설)

**Interfaces:**
- Consumes: Task 1의 `percent`, Task 5의 `get_ammo_refill_grant`, `registry.get_skill_ammo_refund`
- Produces: `tove.emergency_crafted_bullets_refund(values) -> AmmoRefund`, `asuka_shikinami_langley_wille.annihilation_state_refill(values) -> dict`

- [ ] **Step 1: 원문 값을 확인한다**

두 유닛의 lv10 원문(스펙 표에 있음):

- `tove-signature` dollskills[0]: `Activates after 10 normal attack(s). Affects self. / Reload 5.31% of the magazine.`
- `asuka` skills[2] Annihilation State: `Effect 2: Reloads 21% magazine(s).` (자기 버스트)

**base `tove`는 건드리지 않는다** — lv10이 `There is a 5% chance of activating when attacking`이라 확률이고, 엔진은 결정론적이다.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/tests/test_ammo_refill_units.py` 신설:

```python
"""The six reload clauses that had no engine shape until the refill primitive.

Each asserts the SHAPE the encoding declares, not a damage number: a damage
delta measured against the same code that produces it proves nothing.
"""
from app.attack_rate import AmmoRefund
from app.skill_rules.registry import (get_ammo_refill_grant,
                                      get_skill_ammo_refund)
from app.user_roster import load_nikke_spec


def _values(slug):
    return load_nikke_spec(slug).skill_values


def test_tove_signature_reloads_a_percentage_every_ten_shots():
    refund, element = get_skill_ammo_refund("tove-signature", _values("tove-signature"))
    assert refund == AmmoRefund(every_shots=10, percent=5.31)
    assert element is None


def test_tove_base_keeps_its_probability_roll_deferred():
    # "There is a 5% chance of activating when attacking" - the engine is
    # deterministic, so the base build stays out.
    assert get_skill_ammo_refund("tove", _values("tove")) is None


def test_tove_signature_hands_back_three_rounds_of_her_sixty():
    refund, _ = get_skill_ammo_refund("tove-signature", _values("tove-signature"))
    assert refund.rounds_for(60) == 3


def test_asuka_reloads_a_fifth_of_her_magazine_at_her_own_burst():
    grant = get_ammo_refill_grant(
        "asuka-shikinami-langley-wille",
        _values("asuka-shikinami-langley-wille"))
    assert grant == {"percent": 21.0, "scope": "self", "event": "own_burst"}
```

> **구현자 주의:** `load_nikke_spec`의 정확한 임포트 경로와 `skill_values` 접근자를 먼저 확인하라. 이 저장소의 다른 스킬 테스트가 값을 어떻게 얻는지 `backend/tests/test_skill_rules_burst1_batch3.py`(토브가 등록된 곳)를 열어 **그 파일과 같은 방식**을 쓸 것. 위 `_values` 헬퍼는 그 확인 후에 확정한다.

- [ ] **Step 3: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_units.py -v`
Expected: FAIL — `get_skill_ammo_refund("tove-signature", ...)` 가 None을 준다.

- [ ] **Step 4: 구현**

`tove.py`에 빌더를 더하고 `SKILL_VALUE_MANIFESTS`에 필요한 슬롯 키를 등록한다:

```python
def emergency_crafted_bullets_refund(values):
    """"Activates after 10 normal attack(s). Affects self. Reload 5.31% of the
    magazine." - the Favorite Item build's trigger, which unlike the base
    build's 5% roll is a plain shot counter. She is an AR with 60 rounds, so the
    percentage is worth 3 whole rounds; it is declared as a percentage anyway so
    a max-ammo buff moves it the way the game does."""
    bullet = values["emergency_crafted_bullets"]
    return AmmoRefund(
        every_shots=int(bullet["description_value_01"]),
        percent=float(bullet["description_value_02"]),
    )
```

`asuka_shikinami_langley_wille.py`:

```python
def annihilation_state_refill(values):
    """Annihilation State's "Effect 2: Reloads 21% magazine(s)" - a one-shot
    percentage refill at her own burst, not a repeating counter."""
    state = values["annihilation_state"]
    return {"percent": float(state["description_value_02"]),
            "scope": "self", "event": "own_burst"}
```

`registry.py`에 등록한다:

```python
_SKILL_AMMO_REFUNDS = {
    ...
    # Emergency-Crafted Bullets on the Favorite Item build: a shot counter, not
    # the base build's probability roll.
    "tove-signature": (emergency_crafted_bullets_refund, None),
}

_AMMO_REFILL_GRANTS = {
    "asuka-shikinami-langley-wille": annihilation_state_refill,
}
```

> **구현자 주의:** `description_value_01/02`의 실제 슬롯 번호는 **추측하지 말 것.** `data/lootandwaifus/char_tove-nikke.json` / `char_asuka-shikinami-langley-wille.json`의 lv10 항목을 열어 어느 슬롯이 10과 5.31, 21인지 확인하고 매니페스트를 그에 맞춰 쓸 것. 이 저장소에는 슬롯 번호를 잘못 짚어 값이 조용히 어긋난 전례가 있다.

- [ ] **Step 5: 통과와 전체 스위트를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_units.py -v`
Expected: PASS, 4 passed.

Run: `cd backend && python -m pytest -q`
Expected: PASS — 실패 0. 두 유닛의 딜이 움직이므로 **값을 고정한 기존 테스트가 있으면 여기서 빨개진다.** 빨개지면 그 테스트가 무엇을 재는지 읽고, 새 값이 옳은지 판단해 갱신할 것(값을 맞추려고 구현을 바꾸지 말 것).

- [ ] **Step 6: 두 독스트링의 보류 항목을 옮긴다**

`tove.py`의 `Not modeled (both builds)` 불릿에서 재장전 줄을 빼고, **base만** 남긴다. 그 줄의 「5.31% of an SG magazine rounds to zero」는 사실이 아니다 — 그녀는 AR이고 탄창이 60이라 3발이다. `asuka_...py`의 `Annihilation State's 21% magazine reload` 불릿을 `Modeled` 쪽으로 옮긴다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/skill_rules/tove.py backend/app/skill_rules/asuka_shikinami_langley_wille.py backend/app/skill_rules/registry.py backend/tests/test_ammo_refill_units.py
git commit -m "토브 애장품과 아스카의 재장전을 인코딩한다"
```

---

### Task 7: 아군 대상 둘 — 느와르와 리틀머메이드

**Files:**
- Modify: `backend/app/skill_rules/noir.py`, `backend/app/skill_rules/little_mermaid.py`, `backend/app/skill_rules/registry.py`
- Test: `backend/tests/test_ammo_refill_units.py` (추가만)

**Interfaces:**
- Consumes: Task 5의 팬아웃
- Produces: `noir.rabbit_twins_b_refill(values) -> dict`, `little_mermaid.sirens_song_refill(values) -> dict`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_noir_reloads_the_whole_squad_on_full_burst_entry():
    grant = get_ammo_refill_grant("noir", _values("noir"))
    assert grant == {"percent": 39.88, "scope": "squad",
                     "event": "full_burst_enter"}


def test_little_mermaid_reloads_the_whole_squad_at_her_own_burst():
    grant = get_ammo_refill_grant("little-mermaid", _values("little-mermaid"))
    assert grant == {"percent": 33.26, "scope": "squad", "event": "own_burst"}
```

그리고 팬아웃이 실제 덱에서 도는지 한 건:

```python
def test_a_deck_with_noir_refills_every_seat(monkeypatch):
    """Not a damage assertion - the point is that four other units' shot
    timelines receive a refill they could not have declared themselves."""
    from app.raid_simulator import resolve_ammo_refills
    deck = [{"slug": "noir",
             "ammo_refill_grant": get_ammo_refill_grant("noir", _values("noir"))},
            {"slug": "liberalio"}, {"slug": "scarlet-black-shadow"}]
    refills = resolve_ammo_refills(
        deck, [{"type": "full_burst_start", "time": 5.0}])
    assert set(refills) == {"noir", "liberalio", "scarlet-black-shadow"}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_units.py -v -k "noir or mermaid"`
Expected: FAIL — `get_ammo_refill_grant("noir", ...)` 가 None.

- [ ] **Step 3: 구현**

```python
def rabbit_twins_b_refill(values):
    """Rabbit Twins B's "Activates when entering Full Burst. Affects all
    allies. Reload 39.88% magazine(s)."

    The same bullet's Max Ammunition Capacity +5 rounds is already encoded as a
    squad `max_ammo_rounds` buff. The engine reads a magazine's capacity once,
    when the magazine opens, so this refill resolves against the capacity the
    recipient's current magazine was built with - the same granularity every
    max-ammo buff already has.
    """
    bullet = values["rabbit_twins_b"]
    return {"percent": float(bullet["description_value_02"]),
            "scope": "squad", "event": "full_burst_enter"}
```

```python
def sirens_song_refill(values):
    """Siren's Song's "Affects all allies. Reloads 33.26% magazine(s)" - her
    burst, so the trigger is her own cast rather than Full Burst entry."""
    song = values["sirens_song"]
    return {"percent": float(song["description_value_02"]),
            "scope": "squad", "event": "own_burst"}
```

`registry.py`의 `_AMMO_REFILL_GRANTS`에 둘을 더한다.

> **구현자 주의:** 여기서도 슬롯 번호는 원본 데이터로 확인할 것. 느와르의 그 불릿에는 값이 **둘**(발수 5, 퍼센트 39.88) 들어 있어 잘못 짚기 쉽다.

- [ ] **Step 4: 통과와 전체 스위트를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_units.py -v`
Expected: PASS, 7 passed.

Run: `cd backend && python -m pytest -q`
Expected: 실패 0. 리틀머메이드는 실기록 덱2에 있으므로 캘리브레이션을 고정한 테스트가 있으면 여기서 움직인다.

- [ ] **Step 5: 두 독스트링의 보류 항목을 옮긴다**

`noir.py`의 `Not modeled` 재장전 불릿과 `little_mermaid.py`의 「Siren's Song's instant partial reload」 절반을 `Modeled` 쪽으로 옮긴다. 리틀머메이드 쪽 불릿은 버스트 게이지 절반과 한 문장에 묶여 있으므로, **게이지 부분만 보류로 남긴다.**

- [ ] **Step 6: 커밋**

```bash
git add backend/app/skill_rules/noir.py backend/app/skill_rules/little_mermaid.py backend/app/skill_rules/registry.py backend/tests/test_ammo_refill_units.py
git commit -m "느와르와 리틀머메이드가 아군 전원의 탄창을 채우게 한다"
```

---

### Task 8: 아르카나 두 줄

**Files:**
- Modify: `backend/app/skill_rules/arcana_fortune_mate.py`, `backend/app/skill_rules/registry.py`, `backend/app/raid_simulator.py` (창 계산)
- Test: `backend/tests/test_ammo_refill_units.py` (추가만)

**Interfaces:**
- Consumes: Task 4의 `first_shot`/`windows`, Task 5의 팬아웃
- Produces: `arcana_fortune_mate.making_memories_burst_refill(values) -> dict`, `arcana_fortune_mate.rotation_reload_refund(values) -> AmmoRefund` (창은 시뮬레이터가 채워 넣는다)

- [ ] **Step 1: 원문을 다시 읽는다**

`skills[2]` Making Memories: `Effect 2: Reloads 2 round(s).` — 자기 버스트, 자기, **2발**.
`skills[1]` 로테이션: `Two times: Reloads 6 rounds.` + `Resets when Making Memories is removed.` — 창 안 2·8·14…번째, **6발**.

창은 **그녀의 버스트 시각 → 그 사이클의 풀버스트 종료**다. 두 시각 모두 `events`에 있다.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

```python
def test_arcana_burst_reloads_two_rounds_at_her_own_cast():
    grant = get_ammo_refill_grant("arcana-fortune-mate",
                                  _values("arcana-fortune-mate"))
    assert grant == {"rounds": 2, "scope": "self", "event": "own_burst"}


def test_arcana_rotation_reloads_six_on_the_second_of_a_period_six_phase():
    refund, _ = get_skill_ammo_refund("arcana-fortune-mate",
                                      _values("arcana-fortune-mate"))
    assert refund.rounds == 6
    assert refund.first_shot == 2
    assert refund.every_shots == 6


def test_arcanas_rotation_window_runs_from_her_burst_to_full_burst_end():
    """Her counter "Resets when Making Memories is removed", which is that
    cycle's Full Burst end - so a deck whose Burst 3 lengthens Full Burst
    lengthens her window too, rather than a 10-second constant."""
    from app.raid_simulator import resolve_ammo_refund_windows
    events = [
        {"type": "burst", "tier": 2, "slug": "arcana-fortune-mate", "time": 3.0},
        {"type": "full_burst_start", "time": 5.0},
        {"type": "full_burst_end", "time": 17.0},
        {"type": "burst", "tier": 2, "slug": "arcana-fortune-mate", "time": 43.0},
        {"type": "full_burst_start", "time": 45.0},
        {"type": "full_burst_end", "time": 55.0},
    ]
    assert resolve_ammo_refund_windows("arcana-fortune-mate", events) == \
        ((3.0, 17.0), (43.0, 55.0))
```

- [ ] **Step 3: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_units.py -v -k arcana`
Expected: FAIL — `ImportError: cannot import name 'resolve_ammo_refund_windows'`

- [ ] **Step 4: 구현**

`raid_simulator.py`에 창 계산을 더한다:

```python
def resolve_ammo_refund_windows(slug, events):
    """[caster's burst, that cycle's Full Burst end) for every cycle it fires.

    Arcana: Fortune Mate's reload rotation counts only the normal attacks she
    lands while Making Memories is up and "Resets when Making Memories is
    removed", which is the Full Burst end that clears it. Reading the end off
    the event log rather than a 10-second constant keeps her window honest in a
    deck whose Burst 3 moves Full Burst's length.
    """
    windows = []
    for event in events:
        if event["type"] != "burst" or event["slug"] != slug:
            continue
        end = next((e["time"] for e in events
                    if e["type"] == "full_burst_end" and e["time"] > event["time"]),
                   None)
        if end is not None:
            windows.append((event["time"], end))
    return tuple(windows)
```

유닛 루프 앞, `ammo_refills` 옆에서 창 있는 환급의 창을 채운다. `resolve_ammo_refunds`가 `weapon`에서 환급을 꺼내는 지점에 창 주입을 더한다:

```python
        refunds = resolve_ammo_refunds(weapon, boss_element)
        refunds = tuple(
            replace(r, windows=resolve_ammo_refund_windows(slug, events))
            if r.windows == ("PENDING",) else r
            for r in refunds)
```

> **구현자 주의:** 위의 `("PENDING",)` 센티널은 **예시일 뿐 채택안이 아니다.** 레지스트리가 창을 모른다는 사실을 표현할 방법을 구현자가 정하라 — 후보 둘: (a) 빌더가 `windows=()`로 두고 시뮬레이터가 `_WINDOWED_REFUND_SLUGS` 집합으로 판단, (b) 빌더가 `needs_own_burst_window=True` 같은 필드를 두고 시뮬레이터가 그걸 보고 채움. **센티널 문자열은 쓰지 말 것** — 타입이 거짓말을 하게 된다. 정한 방식을 독스트링에 한 줄로 남길 것.

`arcana_fortune_mate.py`:

```python
def making_memories_burst_refill(values):
    """Making Memories' "Effect 2: Reloads 2 round(s)" - a single event at her
    own cast, separate from the rotation's reload phase below."""
    memories = values["making_memories"]
    return {"rounds": int(memories["description_value_02"]),
            "scope": "self", "event": "own_burst"}


def rotation_reload_refund(values):
    """The reload phase of the Making Memories rotation: "Two times: Reloads 6
    rounds", one of three effects on a period-6 rotation that counts only the
    normal attacks she lands inside the window and "Resets when Making Memories
    is removed".

    The phase is what makes this a rotation rather than an "every 6 shots"
    refund - it fires on the 2nd, 8th and 14th attack of a window, never the
    6th or 12th (Fienn counted to the 18th in game, 2026-07-28). The window
    itself is filled in by the simulator, which is where the burst schedule is.
    """
    rotation = values["memories_and_moments"]
    return AmmoRefund(every_shots=6,
                      rounds=int(rotation["description_value_01"]),
                      first_shot=2)
```

> **구현자 주의:** `every_shots=6`과 `first_shot=2`는 로테이션의 구조이지 데이터 슬롯이 아니다(원문에 "Two times / Four times / Six times"로 적혀 있다). **발수 6만** 슬롯에서 읽고 나머지는 상수로 두되, 그 이유를 독스트링에 남길 것.

- [ ] **Step 5: 통과와 전체 스위트를 확인한다**

Run: `cd backend && python -m pytest tests/test_ammo_refill_units.py -v -k arcana`
Expected: PASS, 3 passed.

Run: `cd backend && python -m pytest -q`
Expected: 실패 0.

- [ ] **Step 6: 위상이 실제로 재지는지 확인한다**

`rotation_reload_refund`의 `first_shot=2`를 지운다(기본 0 = 6·12·18).
Run: `cd backend && python -m pytest tests/test_ammo_refill_units.py -k period_six_phase -v`
Expected: FAIL. 확인 후 원복한다.

- [ ] **Step 7: 독스트링을 옮기고 커밋**

`arcana_fortune_mate.py`의 `Not modeled \ deferred` 첫 불릿(로테이션의 재장전 단계)을 `Modeled` 쪽으로 옮긴다.

```bash
git add backend/app/skill_rules/arcana_fortune_mate.py backend/app/skill_rules/registry.py backend/app/raid_simulator.py backend/tests/test_ammo_refill_units.py
git commit -m "아르카나의 버스트 재장전과 로테이션 재장전 단계를 인코딩한다"
```

---

### Task 9: 측정과 문서

**Files:**
- Modify: `docs/engine-gaps.md`, `backend/app/skill_rules/scarlet_black_shadow.py`
- Run: `scripts/measure_record_calibration.py`, `scripts/bench_evaluate_deck.py`

**Interfaces:**
- Consumes: Task 1–8 전부
- Produces: 없음 (측정과 기록)

- [ ] **Step 1: 캘리브레이션을 잰다**

Run: `python scripts/measure_record_calibration.py`

착륙 전 값은 **1.060x · 18/25 · 과대 합계 +1.961B**(2026-08-13)다. 아스카(덱3)와 리틀머메이드(덱2)가 floor를 잃었으므로 **위로 움직일 것으로 예상**한다. 리틀머메이드는 1.154x에서 더 멀어진다 — **되돌리지 않는다.** `sim/record`는 목표가 아니라 상한이고, 이 판단은 Fienn이 2026-08-13에 확인했다.

- [ ] **Step 2: 성능을 잰다**

Run: `python scripts/bench_evaluate_deck.py`

환급이 없는 유닛은 빈 튜플이라 비용이 0이어야 한다. **눈에 띄는 회귀가 있으면 멈추고 보고할 것** — 스펙은 「작을 것으로 보이지만 가정하지 않는다」고 적어 두었다.

- [ ] **Step 3: 스칼렛의 낡은 보류 사유를 갱신한다**

`scarlet_black_shadow.py`의 `Asura's PARTIAL reload at skill levels below 7` 불릿은 이제 표현 수단이 있다(`AmmoRefill(percent=...)` @ 풀버스트 진입). 프로덕션은 lv10(100%)이라 **여전히 작업이 없지만**, 사유가 「세그먼트가 전부 아니면 전무라서」가 아니라 「lv10에서는 100%라 세그먼트 경로가 더 정확해서」로 바뀐다. 그렇게 고친다.

- [ ] **Step 4: `docs/engine-gaps.md`를 갱신한다**

맨 위 「재집계」 절의 임팩트 순위에서 3번 항목(부분 재장전/탄약 환급)을 **해소**로 바꾼다. 적을 것: 여섯 줄 각각의 인코딩 결과, 착륙 전후 캘리브레이션 수치, 남은 것(`tove` base의 확률 롤, `charge_window`). 우선순위 표의 해당 행도 같이 고친다.

- [ ] **Step 5: 전체 스위트를 마지막으로 돌린다**

Run: `cd backend && python -m pytest -q`
Expected: 실패 0.

- [ ] **Step 6: 커밋**

```bash
git add docs/engine-gaps.md backend/app/skill_rules/scarlet_black_shadow.py
git commit -m "부분 재장전 착륙 결과를 갭 인벤토리에 기록한다"
```

---

## 남은 보류 (이 계획이 닫지 않는 것)

- **`tove`(base)** — `There is a 5% chance of activating when attacking`. 확률 롤.
- **`asuka`의 `Removes 100% of ammo`** — 탄약 제거 상태머신. 별건.
- **`charge_window.py`** — 전투 절대 시각이 없는 한 창짜리 계산기.
- **`arcana`의 나머지 두 위상** — Happy Memories·Precious Moments는 이미 인코딩돼 있고 이 계획이 건드리지 않는다.
