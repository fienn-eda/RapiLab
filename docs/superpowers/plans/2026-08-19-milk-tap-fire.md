# 밀크: 블루밍 바니 톡톡이 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 밀크의 실제 조작 — Pierce 6초 창을 지키는 최소 비용으로 풀차지를 넣고 나머지는 톡톡이 — 을 엔진의 매거진 케이던스로 표현한다.

**Architecture:** 톡톡이 발 간격을 풀차지 뒤 멈춤과 **분리된 실측값**으로 만들고(밀크에서 둘이 16σ 다르다), 매거진 안에 풀차지 `k`발 + 톡톡이 `C−k`발을 섞는다. `k`는 매거진 시작마다 Pierce 창 제약 아래 효율 최대로 고른다.

**Tech Stack:** Python 3 / pytest (backend), TypeScript + vitest (frontend)

**Spec:** `docs/superpowers/specs/2026-08-19-milk-tap-fire-design.md`

## Global Constraints

- 백엔드 테스트는 **반드시 `backend/`에서** 실행한다 — 루트에서는 `No module named 'app'`.
- 프론트 타입체크는 `npx --prefix frontend tsc -b --noEmit frontend`. `npm test`(vitest)는 **타입을 안 본다**.
- 기준선(트렁크 `d1324a05`): 백엔드 **2543 passed / 3 skipped** · 프론트 **943 passed / 73 files** · 타입/lint 0.
  - `collect-blablalink/{roster,details}.json`이 있는 체크아웃 기준이다. 없으면 3건이 skip으로 빠진다 — 회귀가 아니다.
- **앨리스의 타임라인은 한 발도 움직이면 안 된다.** 그녀의 멈춤(15/60)과 톡톡이 간격(15/60)이 같은 값이므로 산술 결과가 같아야 하고, 달라지면 그것이 회귀다.
- 실측값: 밀크 톡톡이 간격 **15/60초**(n=21, 평균 14.810f), 밀크 멈춤 **22/60초**(n=9, 평균 21.889f), 앨리스 멈춤·톡톡이 간격 모두 **15/60초**.
- 밀크 무기: 장탄 6 · 차지 1.00초 · 풀차지 250% · 재장전 2.00초 · Pierce 창 6초.
- **손계산으로 엔진 출력을 재유도해 설명하지 않는다.** 검산은 Task 5에서 엔진에 직접 물어서 한다.

---

### Task 1: 톡톡이 간격을 멈춤에서 분리한다

지금 엔진은 「톡톡이 간격 = 그 유닛의 멈춤」을 법칙으로 삼는다. 밀크의 두 실측이 16σ 떨어져 있으므로 이 법칙이 깨진다. 값을 따로 들게 만드는 것이 이 태스크다.

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (`TAP_FIRE_CANDIDATES` 위 주석 문단 + 새 표 2개)
- Modify: `backend/app/roster.py:208-212`
- Test: `backend/tests/test_manual_tap_fire.py`

**Interfaces:**
- Produces: `registry.TAP_FIRE_INTERVAL`(dict), `registry.get_tap_fire_interval(slug) -> float | None`, `registry.FULL_CHARGE_WINDOW`(dict), `registry.get_full_charge_window(slug) -> float | None`. 무기 timeline의 새 키 `tap_fire_interval`, `full_charge_window`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_manual_tap_fire.py` 끝에 추가:

```python
def test_milks_tap_interval_is_not_her_motion_delay():
    """밀크의 두 실측은 다른 값이다 — 톡톡이 14.810f(n=21) 대 멈춤 21.889f(n=9),
    약 16시그마. 앨리스에서 둘이 같게 나온 것은 우연이었고, 그녀에게 멈춤을
    톡톡이 간격으로 주면 발수를 47% 과소평가한다.
    docs/measurements/milk-blooming-bunny-tap-fire.md
    """
    assert get_tap_fire_interval("milk-blooming-bunny") == pytest.approx(15 * FRAME_SECONDS)
    assert get_charge_motion_delay("milk-blooming-bunny") == pytest.approx(22 * FRAME_SECONDS)


def test_alices_two_values_agree_so_she_does_not_move():
    """앨리스는 멈춤 14.75f · 톡톡이 15.38f로 둘 다 15프레임에 앉는다. 값이 같으므로
    분리해도 그녀의 타임라인은 한 발도 안 움직인다 — 그것이 이 변경의 회귀 기준이다."""
    assert get_tap_fire_interval("alice") == get_charge_motion_delay("alice")


def test_milk_declares_the_window_that_forces_a_full_charge():
    """「Gain Pierce for 6 sec」 — 스킬 원문에서 읽은 값이지 조작에서 나온 값이 아니다."""
    assert get_full_charge_window("milk-blooming-bunny") == pytest.approx(6.0)


def test_alice_has_no_full_charge_window():
    """앨리스의 Pierce는 HP 조건이라 풀차지가 갱신하지 않는다. 창이 없으면 매거진을
    통째로 톡톡이로 쏘는 것이 허용된다."""
    assert get_full_charge_window("alice") is None
```

import 줄을 고친다:

```python
from app.skill_rules.registry import (TAP_FIRE_CANDIDATES,
                                      get_charge_motion_delay,
                                      get_full_charge_window,
                                      get_tap_fire_interval,
                                      is_tap_fire_candidate)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_tap_fire_interval'`

- [ ] **Step 3: registry에 표 두 개를 넣는다**

`backend/app/skill_rules/registry.py`의 `TAP_FIRE_CANDIDATES` **바로 위** 주석 문단에서, 「간격 표가 아니라 옵트인 집합인 이유」로 시작하는 문단을 아래로 **교체**한다(그 문단의 주장이 밀크 판독으로 반증됐다):

```python
# **톡톡이 간격은 멈춤에서 유도할 수 없다.** 한동안 이 자리에는 「톡톡이 간격은 새로
# 잴 값이 아니라 그 유닛의 `TIMED_CHARGE_MOTION_DELAY`(멈춤) 그 자체 - 차지가 0이니
# 남는 것이 멈춤뿐」이라고 적혀 있었고, 앨리스에게서 두 값이 같게 나온 것(14.75f /
# 15.38f)이 그 근거였다. **밀크가 그것을 반증했다** - 그녀의 멈춤은 21.889f(n=9)인데
# 톡톡이 간격은 14.810f(n=21)로, 두 평균이 약 16시그마 떨어져 있다. 앨리스에서의
# 일치는 우연이었고, 밀크에게 그 법칙을 적용하면 발수를 47% 과소평가한다.
# 그래서 톡톡이 간격은 아래 `TAP_FIRE_INTERVAL`이 따로 든다
# (docs/measurements/milk-blooming-bunny-tap-fire.md).
#
# 실측이 없는 유닛은 여전히 멈춤으로 대신한다 - 그것이 지금까지의 동작이고, 값을
# 모른다는 사실이 후보 자격을 막는 것은 `TAP_FIRE_CANDIDATES`가 옵트인이라는 사실
# 쪽이지 이 대체값이 아니다.
TAP_FIRE_INTERVAL = {
    # 앨리스: 톡톡이 발 간격 15.38f(n=8) - 그녀의 멈춤 14.75f와 같은 15프레임에 앉는다
    # (docs/measurements/alice-tap-fire.md).
    "alice": 15 / 60,
    # 밀크: 14.810f(n=21, sd 0.602, 13~16). 그녀의 멈춤 22프레임과 **다른 값**이다.
    "milk-blooming-bunny": 15 / 60,
}


def get_tap_fire_interval(slug):
    """이 니케의 톡톡이 발 간격, 또는 실측이 없으면 `None`(멈춤으로 대신한다)."""
    return TAP_FIRE_INTERVAL.get(slug)


# 풀차지를 얼마마다 다시 쳐야 하는지 - 풀차지가 대미지 말고 **유지해야 할 무언가**를
# 갖는 유닛만 여기 있다. 밀크의 6초는 「Gain Pierce for 6 sec」에서 읽은 스킬 값이지
# 조작에서 나온 값이 아니다. 창이 없는 유닛(앨리스)은 매거진을 통째로 톡톡이로 쏘는
# 것이 허용된다 - 그녀의 Pierce는 HP 조건이라 풀차지가 갱신하지 않기 때문이다.
FULL_CHARGE_WINDOW = {
    "milk-blooming-bunny": 6.0,
}


def get_full_charge_window(slug):
    """이 니케가 풀차지를 다시 쳐야 하는 주기(초), 또는 그런 것이 없으면 `None`."""
    return FULL_CHARGE_WINDOW.get(slug)
```

같은 파일에서 「옵트인인 이유는 …」으로 시작해 「그들 멈춤을 다시 재기 전까지는 끄고 둔다」로 끝나는 문단을 아래로 **교체**한다(밀크 멈춤은 2026-08-15에 이미 실측됐고, 이 문단은 그 뒤로 갱신되지 않았다):

```python
# 옵트인인 이유는 톡톡이 간격이 **유닛마다 따로 재야 하는 값**이기 때문이다. 앨리스와
# 밀크는 실측이 있어 켠다. 아인 등 나머지 SR은 멈춤조차 22프레임 stand-in이고 톡톡이
# 간격은 아예 재지 않았으므로, 켜면 두 겹의 미측정 위에서 모드가 갈린다.
```

- [ ] **Step 4: roster가 새 값을 실어 보내게 한다**

`backend/app/roster.py:208-212`의 블록을 아래로 교체한다:

```python
        if is_tap_fire_candidate(spec.slug):
            # 매거진마다 풀차지 몇 발을 섞을지 저울질한다(registry.TAP_FIRE_CANDIDATES).
            # 톡톡이 간격은 멈춤과 **다른 실측값**이므로 따로 실어 보낸다 - 앨리스는
            # 두 값이 같아 결과가 안 움직이고, 밀크는 22프레임 대 15프레임으로 갈린다.
            timeline["tap_fire"] = True
            tap_interval = get_tap_fire_interval(spec.slug)
            if tap_interval is not None:
                timeline["tap_fire_interval"] = tap_interval
            # 풀차지가 되살리는 창이 있으면 케이던스가 그것을 지켜야 한다(밀크의 Pierce).
            full_charge_window = get_full_charge_window(spec.slug)
            if full_charge_window is not None:
                timeline["full_charge_window"] = full_charge_window
```

`backend/app/roster.py`의 import에 두 이름을 추가한다(`is_tap_fire_candidate` 옆, 알파벳 순서 유지):

```python
    get_full_charge_window,
    get_tap_fire_interval,
```

- [ ] **Step 5: 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -v`
Expected: PASS (새 4건 포함)

- [ ] **Step 6: 앨리스가 안 움직였는지 전체로 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: 기준선과 같은 통과 수. **여기서 깨지는 테스트가 있으면 멈추고 원인을 본다** — 앨리스 타임라인이 움직였다는 뜻이거나, timeline dict를 통째로 비교하는 테스트가 새 키를 본 것이다. 후자면 그 테스트에 새 키를 반영하되, 그 전에 **값이 같은데 왜 dict가 달라졌는지** 한 줄로 설명할 수 있어야 한다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/app/roster.py backend/tests/test_manual_tap_fire.py
git commit -m "톡톡이 간격을 멈춤에서 분리한다 - 밀크가 둘이 같다는 법칙을 반증했다"
```

---

### Task 2: 매거진 안 풀차지 발수를 고르는 순수 함수

**Files:**
- Modify: `backend/app/attack_rate.py` (`tap_fire_wins` 바로 아래)
- Test: `backend/tests/test_manual_tap_fire.py`

**Interfaces:**
- Consumes: 없음 (순수 산술)
- Produces:
  - `attack_rate.optimal_full_charges(capacity, reload_seconds, charge_seconds, full_delay, tap_interval, full_charge_percent, window=None) -> int`
  - `attack_rate.full_charge_positions(capacity, full_charges) -> frozenset[int]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_manual_tap_fire.py`에 추가:

```python
MILK_CAPACITY = 6
MILK_CHARGE_TIME = 1.0
MILK_FULL_CHARGE_PERCENT = 250.0
MILK_RELOAD_TIME = 2.0
MILK_MOTION_DELAY = 22 * FRAME_SECONDS
MILK_TAP_INTERVAL = 15 * FRAME_SECONDS
MILK_WINDOW = 6.0


def _milk_k(capacity=MILK_CAPACITY, reload_seconds=MILK_RELOAD_TIME):
    return optimal_full_charges(
        capacity, reload_seconds, MILK_CHARGE_TIME, MILK_MOTION_DELAY,
        MILK_TAP_INTERVAL, MILK_FULL_CHARGE_PERCENT, MILK_WINDOW)


def test_milk_at_stock_ammo_fires_one_full_charge_a_magazine():
    """Fienn 조작 그대로 — 매거진 첫 탄만 풀차지, 나머지 다섯 발은 톡톡이."""
    assert _milk_k() == 1


def test_a_bigger_magazine_forces_a_second_full_charge():
    """장탄이 커지면 한 매거진이 Pierce 6초를 넘기므로 풀차지가 하나 더 든다 —
    Fienn이 「풀차지 → 톡톡이 → 풀차지 → 톡톡이」라고 적은 그 패턴이고,
    하드코딩이 아니라 창 제약에서 떨어져 나온다."""
    assert _milk_k(capacity=14) == 2


def _milk_worst_gap(capacity, full_charges, reload_seconds):
    """풀차지 `full_charges`발을 균등 배치했을 때 연속한 두 풀차지 사이의 최악 간격.

    `optimal_full_charges`가 후보를 거르는 데 쓰는 식과 같은 것을, 테스트가
    독립적으로 다시 쓴 것이다 - 구현이 자기 식으로 자기를 검증하지 않게.
    """
    block = -(-capacity // full_charges)
    return (MILK_CHARGE_TIME + MILK_MOTION_DELAY
            + (block - 1) * MILK_TAP_INTERVAL + reload_seconds)


def test_the_chosen_cadence_keeps_the_window_whenever_any_cadence_can():
    """**불변식** - 창을 지킬 수 있는 k가 하나라도 있으면 고른 k가 그것을 지킨다.

    전부 풀차지(k=C)가 「언제나 안전」한 것은 **아니다**: 그때 최악 간격은
    `차지+멈춤+재장전`까지 줄지만, 재장전 하나가 창보다 길면 그 값도 창을 넘는다
    (예: 장탄 6 · 재장전 8초 -> 9.37초 > 6초). 그때는 모델이 아니라 게임이 창을
    잃는 것이므로, 주장은 「항상 지킨다」가 아니라 「지킬 수 있으면 지킨다」여야 한다.
    """
    for capacity in range(1, 21):
        for reload_seconds in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0):
            k = _milk_k(capacity=capacity, reload_seconds=reload_seconds)
            assert 1 <= k <= capacity
            feasible = [j for j in range(1, capacity + 1)
                        if _milk_worst_gap(capacity, j, reload_seconds) <= MILK_WINDOW]
            if feasible:
                assert _milk_worst_gap(capacity, k, reload_seconds) <= MILK_WINDOW, (
                    capacity, reload_seconds, k)
            else:
                # 어떤 케이던스로도 못 지킨다 - 최악 간격이 가장 작은 k=C로 물러난다.
                assert k == capacity, (capacity, reload_seconds, k)


def test_without_a_window_the_answer_matches_the_old_two_way_test():
    """앨리스에게는 창이 없으므로 답이 두 끝뿐이고, 그 판정은 기존 `tap_fire_wins`와
    **동치**여야 한다 — 효율이 k에 대해 단조라 f(0) > f(C) ⟺ 톡톡이 승."""
    for capacity in (1, 3, 6, 10):
        for reload_seconds in (0.0, 0.5, 1.0, 2.0, 5.0):
            for charge_seconds in (0.0, 0.25, 1.5, 3.0):
                k = optimal_full_charges(
                    capacity, reload_seconds, charge_seconds, ALICE_MOTION_DELAY,
                    ALICE_MOTION_DELAY, ALICE_FULL_CHARGE_PERCENT, None)
                taps_win = tap_fire_wins(
                    charge_seconds, ALICE_MOTION_DELAY, ALICE_FULL_CHARGE_PERCENT,
                    capacity, reload_seconds)
                assert k == (0 if taps_win else capacity), (
                    capacity, reload_seconds, charge_seconds, k, taps_win)


def test_a_unit_with_no_pause_cannot_tap():
    """톡톡이 간격이 0이면 무한 연사가 된다 — 전부 풀차지로 물러난다."""
    assert optimal_full_charges(6, 2.0, 1.0, 0.0, 0.0, 250.0, None) == 6


def test_full_charges_are_spread_evenly_and_the_first_round_is_one():
    """첫 탄은 항상 풀차지다 — 강제 재장전 직후의 거동이자 Fienn 조작 4번."""
    assert full_charge_positions(6, 1) == frozenset({0})
    assert full_charge_positions(6, 2) == frozenset({0, 3})
    assert full_charge_positions(14, 2) == frozenset({0, 7})
    assert full_charge_positions(6, 6) == frozenset(range(6))
    assert full_charge_positions(6, 0) == frozenset()


def test_the_widest_block_never_exceeds_the_ceiling():
    """제약식이 쓰는 `ceil(C/k)`가 실제 배치의 최대 블록과 맞는지 — 두 곳이
    어긋나면 창을 지킨다고 믿으면서 안 지키게 된다."""
    for capacity in range(1, 21):
        for k in range(1, capacity + 1):
            positions = sorted(full_charge_positions(capacity, k))
            blocks = [b - a for a, b in zip(positions, positions[1:])]
            blocks.append(capacity - positions[-1])
            assert max(blocks) <= -(-capacity // k), (capacity, k)
```

import 줄을 고친다:

```python
from app.attack_rate import (FRAME_SECONDS, full_charge_positions,
                             generate_segmented_shots, optimal_full_charges,
                             shot_interval_with_speed, tap_fire_wins)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -v`
Expected: FAIL — `ImportError: cannot import name 'optimal_full_charges'`

- [ ] **Step 3: 두 함수를 구현한다**

`backend/app/attack_rate.py`의 `tap_fire_wins` **바로 아래**에 넣는다:

```python
def full_charge_positions(capacity, full_charges):
    """매거진 안에서 풀차지로 쏠 탄의 인덱스 - 균등 배치.

    `j=0`이 0번 탄이므로 **첫 탄은 항상 풀차지**다. 그것이 강제 재장전 직후의
    거동이자 Fienn이 적은 조작(「첫 탄 풀차지(관통효과 얻음)」)이고, 덕분에
    매거진 경계가 곧 창을 새로 여는 지점이 된다.
    """
    if full_charges <= 0:
        return frozenset()
    return frozenset((j * capacity) // full_charges for j in range(full_charges))


def optimal_full_charges(capacity, reload_seconds, charge_seconds, full_delay,
                         tap_interval, full_charge_percent, window=None):
    """이 매거진에서 풀차지로 쏠 발수 k(0..capacity).

    한 발은 풀차지면 `charge_seconds + full_delay`, 톡톡이면 `tap_interval`이
    걸리고 배율은 각각 `full_charge_percent/100`과 1.0이다. 그러면

        효율(k) = (C + k(M-1)) / (C*tap + R + k(charge + delay - tap))

    가 되어 `(p+ak)/(q+bk)` 꼴이므로 **k에 대해 단조**다 - 도함수 부호가 k와
    무관하다. 그래서 답은 언제나 허용 구간의 **양 끝** 중 하나이지 중간의 어떤
    k가 아니고, 이는 `tap_fire_wins`의 「중간 지점은 항상 지배당한다」를 한 축
    위로 올린 것이다. 그래도 아래는 0..C를 그냥 훑는다: C가 작아 비용이 없고,
    창 제약의 `ceil(C/k)`를 근사 없이 그대로 처리할 수 있기 때문이다.

    `window`는 **풀차지를 다시 쳐야 하는 주기**다(밀크의 Pierce 6초). k발을
    균등 배치하면 한 블록이 최대 `ceil(C/k)`발이고 재장전은 그중 한 블록에
    통째로 붙으므로, 연속한 두 풀차지 사이의 최악 간격은

        (charge + delay) + (ceil(C/k) - 1)*tap + R

    이다. 이 값이 창을 넘는 k는 후보에서 빠진다.

    **어떤 k도 창을 못 지키면 전부 풀차지로 물러난다.** 그것이 그 상황에서
    풀차지를 가장 자주 치는 배치이기 때문이다 - 그때 최악 간격은
    `(charge + delay) + R`까지 줄고, 그보다 짧게 만들 방법은 없다.

    **다만 그 값도 창을 넘을 수 있다.** 재장전 하나가 창보다 길면 어떤
    케이던스로도 창을 못 지킨다. 그때는 모델이 아니라 게임이 창을 잃는 것이고,
    이 함수는 잃는 폭이 가장 작은 배치를 고를 뿐이다 - 그래서 이 폴백이 보장하는
    것은 「창을 지킨다」가 아니라 「지킬 수 있으면 지킨다」이다. 밀크의 실제 값은
    이 분기에 닿지 않는다(차지+멈춤 1.37초 + 재장전 2.0초 = 3.37초 < 창 6초,
    그녀의 강제 재장전 3.0초를 넣어도 4.37초). **그것이 그녀의 Pierce를 영구로
    두는 근사가 실제로 기대는 사실이다.**
    """
    if tap_interval <= 0:
        # 톡톡이 간격이 0이면 무한 연사가 된다 - 애초에 후보가 아니다.
        return capacity
    full_cost = charge_seconds + full_delay
    multiplier = full_charge_percent / 100
    best_k, best_rate = capacity, None
    for k in range(capacity + 1):
        if window is not None:
            if k == 0:
                # 창이 있는데 풀차지를 한 발도 안 쏘면 창을 잃는다.
                continue
            block = -(-capacity // k)
            worst_gap = (full_cost + (block - 1) * tap_interval + reload_seconds)
            if worst_gap > window:
                continue
        damage = capacity + k * (multiplier - 1)
        duration = (capacity * tap_interval + reload_seconds
                    + k * (full_cost - tap_interval))
        rate = damage / duration
        if best_rate is None or rate > best_rate:
            best_k, best_rate = k, rate
    return best_k
```

- [ ] **Step 4: 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_manual_tap_fire.py
git commit -m "매거진 안 풀차지 발수를 창 제약 아래 고른다"
```

---

### Task 3: 매거진 안에서 두 모드를 섞는다

**Files:**
- Modify: `backend/app/attack_rate.py` (`_base_shot_records`의 차지 분기)
- Test: `backend/tests/test_manual_tap_fire.py`

**Interfaces:**
- Consumes: `optimal_full_charges`, `full_charge_positions` (Task 2)
- Produces: `attack_rate.mixed_charge_round_offset(index, capacity, full_cost, tap_cost, full_positions) -> float`. 무기 timeline 키 `tap_fire_interval`, `full_charge_window`를 `_base_shot_records`가 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def _milk_weapon(**overrides):
    weapon = {
        "weapon": "SR",
        "charge_time": MILK_CHARGE_TIME,
        "charge_damage_percent": MILK_FULL_CHARGE_PERCENT,
        "damage_percent": 100.0,
        "max_ammo": MILK_CAPACITY,
        "reload_time": MILK_RELOAD_TIME,
        "charge_motion_delay": MILK_MOTION_DELAY,
        "tap_fire": True,
        "tap_fire_interval": MILK_TAP_INTERVAL,
        "full_charge_window": MILK_WINDOW,
    }
    weapon.update(overrides)
    return weapon


def test_milks_magazine_mixes_one_full_charge_with_five_taps():
    """매거진 여섯 발 가운데 첫 탄만 차지 보너스를 갖는다."""
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    magazine = shots[:MILK_CAPACITY]
    assert [s.extra_charge_bonus > 0 for s in magazine] == [True, False, False, False, False, False]


def test_the_taps_are_spaced_by_the_tap_interval_not_the_pause():
    """톡톡이끼리의 간격은 15프레임이지 그녀의 멈춤 22프레임이 아니다 — 이 구분이
    없으면 발수를 47% 과소평가한다."""
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    gaps = [b.time - a.time for a, b in zip(shots, shots[1:])][:4]
    for gap in gaps:
        assert gap == pytest.approx(MILK_TAP_INTERVAL)


def test_the_full_charge_shot_costs_charge_plus_pause():
    """첫 탄은 차지 1초와 멈춤 22프레임을 함께 치른다."""
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    assert shots[0].time == pytest.approx(MILK_CHARGE_TIME + MILK_MOTION_DELAY)


def test_a_unit_without_a_tap_interval_falls_back_to_its_pause():
    """실측이 없으면 지금까지의 동작 그대로 멈춤을 톡톡이 간격으로 쓴다.

    **재장전을 0으로 두어 톡톡이가 이기는 지점에서 재야** 폴백값이 간격에 드러난다.
    그녀의 기본 재장전 2초에서는 22프레임 톡톡이가 풀차지에 진다(매거진당 1.4286 대
    1.4706). 그러면 매거진이 통째로 풀차지가 되고 발 간격은 폴백값이 아니라
    차지+멈춤이 되어, 폴백이 통째로 깨져도 이 테스트가 초록일 수 있다.

    같은 계산이 이 인코딩의 근거이기도 하다 - 22프레임과 15프레임이 **부호를
    뒤집는다**. 그래서 밀크의 톡톡이 간격을 따로 잰 것이다.
    """
    weapon = _milk_weapon(full_charge_window=None, reload_time=0.0)
    weapon.pop("tap_fire_interval")
    shots = generate_segmented_shots(weapon, (), 6.0)
    gaps = [b.time - a.time for a, b in zip(shots, shots[1:])][:3]
    for gap in gaps:
        assert gap == pytest.approx(MILK_MOTION_DELAY)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -k milk -v`
Expected: FAIL — 매거진이 통째로 한 모드로 나오므로 `[True, False, ...]` 비교가 깨진다.

- [ ] **Step 3: 누적 오프셋 헬퍼를 넣는다**

`backend/app/attack_rate.py`의 `full_charge_positions` 아래에 넣는다:

```python
def mixed_charge_round_offset(index, capacity, full_cost, tap_cost, full_positions):
    """매거진 시작에서 `index`번째 탄이 발사되기까지의 시간.

    발마다 소요가 갈리므로 균등 간격이 아니라 누적합이다. 탄환 환급으로 매거진이
    용량을 넘어 이어질 수 있으므로 배치는 `capacity`를 주기로 **순환**한다 -
    풀차지 주기가 유지되어야 창도 유지되기 때문이다.
    """
    whole, rest = divmod(index + 1, capacity)
    full_rounds = len(full_positions)
    total = whole * (full_rounds * full_cost + (capacity - full_rounds) * tap_cost)
    for i in range(rest):
        total += full_cost if i in full_positions else tap_cost
    return total
```

- [ ] **Step 4: 차지 분기가 혼합 케이던스를 만들게 한다**

`_base_shot_records`의 차지 분기에서, `bonus = full_bonus`로 시작해
`effective_charge, bonus = motion_delay, 0.0`으로 끝나는 블록을 아래로 교체한다:

```python
            # 톡톡이를 저울질하는 유닛은 매거진마다 풀차지 몇 발을 섞을지 고른다.
            # 차지속도가 이미 이 granularity로 샘플되므로 새 축이 생기지 않는다.
            # 톡톡이 간격은 멈춤과 **다른 실측값**이고(밀크 22f 대 15f), 실측이
            # 없는 유닛만 멈춤으로 대신한다 - `registry.TAP_FIRE_INTERVAL` 참고.
            full_positions = None
            tap_cost = None
            if base.get("tap_fire") and motion_delay:
                tap_cost = base.get("tap_fire_interval") or motion_delay
                full_charges = optimal_full_charges(
                    capacity,
                    reload_time_with_speed(
                        base["reload_time"], reload_speed_percent_at(magazine_start)),
                    effective_charge - motion_delay, motion_delay, tap_cost,
                    base["charge_damage_percent"], base.get("full_charge_window"))
                if full_charges < capacity:
                    full_positions = full_charge_positions(capacity, full_charges)
            if full_positions is None:
                # 전부 풀차지 - 예전 경로와 산술이 바이트 단위로 같아야 한다.
                def time_of_round_i(i, s=magazine_start, c=effective_charge):
                    return s + c + i * c
            else:
                def time_of_round_i(i, s=magazine_start, c=effective_charge,
                                    t=tap_cost, cap=capacity, p=full_positions):
                    return s + mixed_charge_round_offset(i, cap, c, t, p)
            magazine_size, shots_fired = _walk_magazine(
                capacity, shots_fired, refund,
                time_of_round=time_of_round_i,
                refills=refills, stop_time=window_end)
```

이어지는 `for i in range(magazine_size):` 루프에서 `shot_time`과 `bonus`를 발마다 뽑게 고친다:

```python
            for i in range(magazine_size):
                shot_time = time_of_round_i(i)
                if shot_time >= window_end:
                    return records
                is_full = full_positions is None or (i % capacity) in full_positions
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"],
                    full_bonus if is_full else 0.0,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1),
                    magazine_index=i))
                last_shot_time = shot_time
```

기존 `magazine_size, shots_fired = _walk_magazine(...)` 호출과 `bonus` 변수는 위 교체에 흡수되므로 남기지 않는다.

- [ ] **Step 5: 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -v`
Expected: PASS

- [ ] **Step 6: 앨리스와 나머지 전부가 안 움직였는지 본다**

Run: `cd backend && python -m pytest -q`
Expected: 기준선과 같은 통과 수. 밀크는 아직 후보가 아니므로(Task 4에서 등록) **밀크 딜도 안 움직여야 한다**.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_manual_tap_fire.py
git commit -m "매거진 안에서 풀차지와 톡톡이를 섞는다"
```

---

### Task 4: 밀크를 후보로 등록하고 Pierce 근거를 바꾼다

**이 태스크가 이번 변경에서 제일 조심할 곳이다.** 밀크의 Pierce는 `battle_start`에 영구로 부여되는데, 그 근거인 「그녀의 모든 샷이 풀차지라서」가 톡톡이를 넣는 순간 거짓이 된다. 근거를 바꾸지 않고 케이던스만 켜면 엔진은 톡톡이만 쏘면서 Pierce를 공짜로 받는다.

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (`TAP_FIRE_CANDIDATES`)
- Modify: `backend/app/skill_rules/milk_blooming_bunny.py` (docstring)
- Modify: `backend/tests/test_manual_tap_fire.py` (낡은 근거를 담은 docstring)
- Test: `backend/tests/test_skill_rules_milk_blooming_bunny.py`

**Interfaces:**
- Consumes: Task 1~3 전부
- Produces: 없음 (등록과 문서)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_skill_rules_milk_blooming_bunny.py`에 추가:

```python
def test_milk_is_a_tap_fire_candidate():
    """그녀의 조작은 Pierce 창을 지키는 최소 비용으로 풀차지를 넣고 나머지를
    톡톡이로 쏘는 것이다 — docs/measurements/milk-blooming-bunny-tap-fire.md"""
    from app.skill_rules.registry import is_tap_fire_candidate
    assert is_tap_fire_candidate("milk-blooming-bunny")


def test_milks_permanent_pierce_rests_on_the_cadence_keeping_the_window():
    """Pierce를 영구로 두는 근사의 **유일한** 논거는 케이던스가 창을 지킨다는 것이다.
    창을 지키는 k가 없으면 전부 풀차지로 물러나고, 그때도 모든 샷이 풀차지라
    창은 지켜진다. 어느 분기에서도 Pierce가 안 끊긴다."""
    from app.attack_rate import FRAME_SECONDS, optimal_full_charges
    for capacity in range(1, 21):
        for reload_seconds in (0.0, 1.0, 2.0, 4.0, 8.0):
            k = optimal_full_charges(
                capacity, reload_seconds, 1.0, 22 * FRAME_SECONDS,
                15 * FRAME_SECONDS, 250.0, 6.0)
            assert k >= 1
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_milk_blooming_bunny.py -v`
Expected: FAIL — `assert is_tap_fire_candidate("milk-blooming-bunny")`

- [ ] **Step 3: 밀크를 등록한다**

`backend/app/skill_rules/registry.py`:

```python
TAP_FIRE_CANDIDATES = frozenset({"alice", "milk-blooming-bunny"})
```

- [ ] **Step 4: Pierce 근거를 교체한다**

`backend/app/skill_rules/milk_blooming_bunny.py`의 docstring에서, 「Gain Pierce for 6 sec」 항목을 아래로 교체한다:

```
- "Gain Pierce for 6 sec" on every full charge (skills[0]): the `has_pierce`
  property, which is what lets her two "Pierce Damage +X%" clauses pay out at
  all. It is granted permanently from battle start, and what justifies that is
  her CADENCE rather than her weapon: she is a tap-fire candidate
  (`registry.TAP_FIRE_CANDIDATES`), and `attack_rate.optimal_full_charges`
  picks the number of full charges per magazine under the constraint that no
  two of them are more than `FULL_CHARGE_WINDOW` = 6 sec apart. Where no such
  number exists it falls back to firing the whole magazine at full charge -
  the arrangement that strikes a full charge as often as the magazine allows,
  whose worst gap is `charge + delay + reload`.

  That fallback is the best available cadence, but it is NOT an unconditional
  guarantee: a reload longer than the window outruns every cadence, and then
  it is the GAME losing the window rather than the model. What makes the
  permanent grant sound for HER is an inequality about her own numbers -
  `charge + delay + reload` = 1.37 + 2.0 = **3.37 sec against a 6 sec window**,
  and 4.37 sec even under her forced reload's fixed 3 sec. She never reaches
  the branch where the window cannot be kept. The day that inequality breaks,
  this grant stops being an approximation and becomes an error.

  **This is the load-bearing approximation of her encoding.** The earlier
  justification - "she is an SR, so every shot IS a full charge" - became false
  the moment tap fire arrived: a tapped shot does not renew Pierce (the clause
  reads "when performing a Full Charge attack"). Had the grant been left
  standing on that sentence, the engine would have tapped the whole magazine
  and collected Pierce for free, overstating her.
```

같은 파일 docstring 앞머리의 타임라인 문단에, [부끄러움] 진입이 톡톡이로는 안 켜진다는 사실을 한 문장 보탠다:

```
Embarrassment's entry clause reads "when Full Charge lasts for 0.5 sec or
more", so a tapped shot cannot arm it either - the entry offset below is
unchanged by tap fire.
```

- [ ] **Step 5: 낡은 근거를 담은 테스트 docstring을 고친다**

`backend/tests/test_manual_tap_fire.py`의 `test_every_tap_fire_candidate_has_a_motion_delay`
docstring을 교체한다(불변식 자체는 그대로 두고 근거만 바꾼다):

```python
def test_every_tap_fire_candidate_has_a_motion_delay():
    """멈춤이 0인 유닛은 후보가 될 수 없다.

    톡톡이 간격이 멈춤과 다른 값이라는 것이 밀크에서 드러났지만(TAP_FIRE_INTERVAL),
    멈춤 0은 여전히 배제 조건이다 - 멈춤을 안 재놓고 톡톡이 간격만 재는 일이
    없어야 하고, 실측이 없는 유닛은 멈춤으로 대신하므로 그때 무한 연사가 된다.
    """
```

같은 파일 모듈 docstring의 마지막 문단(「남는 것은 매거진마다 두 끝 중 어느 쪽이
나은지 고르는 일뿐이다」)을 교체한다:

```
그래서 이건 「바닥값」이 아니라 **한 샷을 어디서 놓느냐**의 문제이고, 중간 지점은 볼
필요가 없다(`tap_fire_wins`의 독스트링 참고).

**밀크가 여기에 한 축을 더했다.** 그녀의 풀차지는 대미지 말고도 Pierce 6초를
되살리므로, 매거진을 통째로 한 모드로 쏘는 것이 답이 아니다 - 매거진 **안에서**
섞어야 하고, 몇 발을 섞을지는 `optimal_full_charges`가 창 제약 아래 고른다.
```

- [ ] **Step 6: 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_skill_rules_milk_blooming_bunny.py tests/test_manual_tap_fire.py -v`
Expected: PASS

- [ ] **Step 7: 전체 스위트를 돌린다**

Run: `cd backend && python -m pytest -q`
Expected: **밀크 딜이 움직인다.** 그녀의 딜을 고정한 테스트가 있으면 새 값으로 갱신하되, 갱신 전에 Task 5의 검산을 먼저 해서 **왜 그 방향으로 움직였는지** 설명할 수 있어야 한다. 설명을 못 쓰면 그것이 신호다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/app/skill_rules/milk_blooming_bunny.py backend/tests/
git commit -m "밀크를 톡톡이 후보로 올리고 Pierce 영구 부여의 근거를 케이던스로 옮긴다"
```

---

### Task 5: 엔진에게 직접 물어 검산하고 문서를 갱신한다

앨리스 때 같은 건을 세 번 고쳤고 **매번 원인은 손계산**이었다. 여기서는 엔진에 물어서 확인한다.

**Files:**
- Create: `backend/scripts/audit_milk_tap_fire.py`
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`
- Modify: `docs/engine-gaps.md`, `docs/insights.md`, `docs/decisions.md`, `docs/roadmap.md`, `docs/encoded-nikkes.md`
- Modify: `frontend/src/components/DeckCard.tsx` (필요하면)

- [ ] **Step 1: 검산 스크립트를 쓴다**

`backend/scripts/audit_milk_tap_fire.py` — 언제 쓰나: 밀크의 케이던스가 바뀌었을 때, 그 변화가 **엔진이 실제로 만든 타임라인**과 맞는지 확인할 때. 손으로 만든 표를 믿지 않기 위한 도구다.

```python
"""밀크의 톡톡이 케이던스를 엔진에게 직접 물어 찍는다.

손계산으로 발수를 재유도하면 버프를 하나씩 조용히 빠뜨린다(앨리스에서 세 번
당했다). 그래서 이 스크립트는 산술을 다시 하지 않고 `generate_segmented_shots`가
실제로 만든 ShotRecord를 세어 보여준다.

쓸 때: 밀크의 장탄/재장전/차속이 바뀌는 변경 뒤, 또는 `optimal_full_charges`를
손댄 뒤. 출력의 「풀차지 간 최대 간격」이 6초를 넘으면 Pierce 근사가 깨진 것이다.

    cd backend && python scripts/audit_milk_tap_fire.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.attack_rate import FRAME_SECONDS, generate_segmented_shots

WINDOW = 6.0
FIGHT = 30.0


def milk_weapon(max_ammo=6, reload_time=2.0):
    return {
        "weapon": "SR", "charge_time": 1.0, "charge_damage_percent": 250.0,
        "damage_percent": 100.0, "max_ammo": max_ammo, "reload_time": reload_time,
        "charge_motion_delay": 22 * FRAME_SECONDS, "tap_fire": True,
        "tap_fire_interval": 15 * FRAME_SECONDS, "full_charge_window": WINDOW,
    }


def report(label, weapon):
    shots = generate_segmented_shots(weapon, (), FIGHT)
    fulls = [s.time for s in shots if s.extra_charge_bonus > 0]
    gaps = [b - a for a, b in zip(fulls, fulls[1:])]
    worst = max(gaps) if gaps else 0.0
    damage = sum(s.damage_percent * (1 + s.extra_charge_bonus) for s in shots)
    print(f"{label:28s} 발수 {len(shots):3d}  풀차지 {len(fulls):3d}  "
          f"최대간격 {worst:5.2f}s  누적배율 {damage:8.1f}"
          f"{'  ** 창 초과 **' if worst > WINDOW + 1e-9 else ''}")


if __name__ == "__main__":
    print(f"전투 {FIGHT}초 · Pierce 창 {WINDOW}초\n")
    for ammo in (6, 10, 14):
        for reload_time in (2.0, 1.0, 0.5):
            report(f"장탄 {ammo:2d} · 재장전 {reload_time}s",
                   milk_weapon(max_ammo=ammo, reload_time=reload_time))
    print("\n대조 - 톡톡이 없이 전부 풀차지:")
    weapon = milk_weapon()
    weapon["tap_fire"] = False
    report("장탄  6 · 재장전 2.0s", weapon)
```

- [ ] **Step 2: 돌려서 스펙의 예측과 맞는지 본다**

Run: `cd backend && python scripts/audit_milk_tap_fire.py`
Expected: 장탄 6·재장전 2.0s에서 **풀차지 수 = 매거진 수**(k=1), 최대 간격이 6초 이하, 「창 초과」 표시가 **한 줄도 없음**. 스펙의 손계산 표(C=6→k=1, C=14→k=2)와 맞는지 눈으로 대조한다. **어긋나면 손계산이 아니라 엔진을 믿고, 어긋난 이유를 찾는다.**

- [ ] **Step 3: 능력 카탈로그를 갱신한다**

`.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`에 추가한다 — 적히지 않은 능력은 다음 세션이 갭으로 다시 기록한다:

- **매거진 안 혼합 케이던스**: `TAP_FIRE_CANDIDATES` 유닛은 매거진마다 풀차지 `k`발 + 톡톡이 `C−k`발로 쏜다. `k`는 `attack_rate.optimal_full_charges`가 고른다.
- **톡톡이 발 간격은 멈춤과 별개의 실측값**: `registry.TAP_FIRE_INTERVAL`. 없으면 멈춤으로 대신한다.
- **풀차지가 되살리는 창**: `registry.FULL_CHARGE_WINDOW`. 풀차지가 대미지 말고 유지해야 할 상태를 갖는 유닛이 선언한다.

- [ ] **Step 4: 나머지 living document를 갱신한다**

- `docs/engine-gaps.md` — 밀크 관련 항목이 이 변경으로 닫히거나 줄어들면 반영한다.
- `docs/insights.md` — 「한 유닛에서 우연히 일치한 두 값을 법칙으로 읽으면 다른 유닛에서 반증된다」.
- `docs/decisions.md` — 톡톡이 간격 분리, 창 제약 아래 `k` 선택, Pierce 근거 이전.
- `docs/encoded-nikkes.md` — 밀크의 완성도 등급과 남은 보류를 갱신한다.
- `docs/roadmap.md` — To-Do 반영.

- [ ] **Step 5: 프론트는 Task 6에서 다룬다 — 여기서는 건드리지 않는다**

확인은 이미 끝났다: `DeckCard.tsx`는 슬러그를 하드코딩하지 않고 백엔드가 주는 `partial_charge_slugs`를 그대로 렌더하므로 밀크가 저절로 들어간다. 문제는 렌더가 아니라 **문구가 밀크에게 거짓이 된다**는 것이고(「항상 톡톡이로 계산했어요」), 그것은 Task 6이 고친다.

- [ ] **Step 6: 전체 검증**

```bash
cd backend && python -m pytest -q
cd ../frontend && npm test
npx --prefix frontend tsc -b --noEmit frontend
```
Expected: 백엔드·프론트 모두 통과, 타입에러 0.

- [ ] **Step 7: 커밋**

```bash
git add backend/scripts/audit_milk_tap_fire.py docs/ .claude/skills/
git commit -m "밀크 톡톡이 검산 스크립트와 문서 갱신"
```


---

### Task 6: 매거진당 풀차지 발수를 화면까지 나른다

현재 문구는 `${names}는 항상 톡톡이로 계산했어요.`인데 **밀크에게는 거짓**이다 - 그녀는 매거진마다 풀차지를 섞어야 Pierce가 산다. 화면이 「항상 톡톡이」라고 말하면 플레이어가 풀차지를 빼먹고 관통특화를 잃는다. 앨리스 때 안내 문구가 버스트 중에 손을 늦추게 만들었던 것과 같은 실패 모드다.

Fienn 문안(2026-08-19): **「바밀크 풀차지 1회 + 톡톡이로 계산했어요.」** - 발수를 숫자로 말한다. 그러려면 엔진이 그 수를 실어 보내야 한다.

**Files:**
- Modify: `backend/app/raid_simulator.py` (`tap_fire_used` 감지 옆)
- Modify: `backend/app/deck_search.py:675` 근처
- Modify: `backend/app/api.py:198, 491, 538, 671`
- Modify: `frontend/src/types/recommend.ts:66` 근처
- Modify: `frontend/src/lib/helpText.ts` (`tapFireAlways` 옆)
- Modify: `frontend/src/components/DeckCard.tsx:107-113`
- Test: `backend/tests/test_manual_tap_fire.py`, `frontend/src/components/DeckCard.test.tsx`

**Interfaces:**
- Consumes: Task 3의 혼합 케이던스 (`ShotRecord.extra_charge_bonus`, `ShotRecord.magazine_index`)
- Produces: 시뮬레이터 결과 키 `tap_fire_full_rounds: dict[str, int]` -> API 필드 `partial_charge_full_rounds: dict[str, int]` -> 프론트 `deck.partial_charge_full_rounds`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_manual_tap_fire.py`에 추가한다. `_milk_weapon`은 Task 3이 정의한 헬퍼다:

```python
def test_full_charges_per_magazine_reads_the_timeline():
    """화면이 「풀차지 N회 + 톡톡이」라고 말할 때의 N - 손으로 세지 않고
    엔진이 만든 기록에서 읽는다."""
    from app.raid_simulator import full_charges_per_magazine
    shots = generate_segmented_shots(_milk_weapon(), (), 30.0)
    assert full_charges_per_magazine(shots) == 1


def test_a_magazine_fired_entirely_at_full_charge_counts_them_all():
    """톡톡이를 안 쓰는 유닛은 매거진 전체가 풀차지다."""
    from app.raid_simulator import full_charges_per_magazine
    weapon = _milk_weapon()
    weapon["tap_fire"] = False
    shots = generate_segmented_shots(weapon, (), 30.0)
    assert full_charges_per_magazine(shots) == MILK_CAPACITY


def test_an_all_tap_magazine_reports_zero():
    """앨리스처럼 창이 없어 매거진을 통째로 톡톡이로 쏘면 0 - 화면은 그때
    기존의 「항상 톡톡이」 문구를 골라야 한다."""
    from app.raid_simulator import full_charges_per_magazine
    shots = generate_segmented_shots(
        _milk_weapon(full_charge_window=None, reload_time=0.0), (), 30.0)
    assert full_charges_per_magazine(shots) == 0
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -k full_charges_per_magazine -v`
Expected: FAIL - `ImportError: cannot import name 'full_charges_per_magazine'`

- [ ] **Step 3: 시뮬레이터가 발수를 센다**

`backend/app/raid_simulator.py`에 모듈 스코프 함수를 넣는다(`tap_fire_used`를 쓰는 함수보다 위):

```python
def full_charges_per_magazine(shot_records):
    """매거진 하나에 든 풀차지 발수 - 화면이 「풀차지 N회 + 톡톡이」라고 말할 때의 N.

    매거진마다 다를 수 있으므로(차속 창이 열린 구간은 다른 k가 나온다) **최빈값**을
    쓴다. 평균은 정수가 아니고, 첫 매거진 하나는 전투 시작 구간이라 대표성이 없다.
    매거진 위치가 없는 기록(세그먼트 샷)은 세지 않는다 - 그 샷들은 자기 매거진에서
    온 것이 아니다.
    """
    per_magazine = []
    current = None
    for record in shot_records:
        if record.magazine_index is None:
            continue
        if record.magazine_index == 0:
            if current is not None:
                per_magazine.append(current)
            current = 0
        if current is None:
            continue
        if record.extra_charge_bonus > 0:
            current += 1
    if current is not None:
        per_magazine.append(current)
    if not per_magazine:
        return 0
    return Counter(per_magazine).most_common(1)[0][0]
```

`from collections import Counter`가 이미 import되어 있는지 확인하고, 없으면 파일 관례에 맞는 자리에 추가한다.

`tap_fire_used = set()` 옆에 초기화를 더한다:

```python
    tap_fire_full_rounds = {}
```

`tap_fire_used.add(slug)` 바로 아래에 한 줄:

```python
            tap_fire_full_rounds[slug] = full_charges_per_magazine(shot_records)
```

`result["tap_fire_used"] = sorted(tap_fire_used)` 옆에:

```python
        result["tap_fire_full_rounds"] = tap_fire_full_rounds
```

- [ ] **Step 4: deck_search와 api가 나른다**

`backend/app/deck_search.py`의 `"partial_charge_slugs": result.get("tap_fire_used", []),` 바로 아래:

```python
        "partial_charge_full_rounds": result.get("tap_fire_full_rounds", {}),
```

`backend/app/api.py`의 `partial_charge_slugs: list[str] = []` 바로 아래:

```python
    partial_charge_full_rounds: dict[str, int] = {}
```

`api.py`에서 `partial_charge_slugs=` 가 나오는 **세 자리 전부**(491·538·671 근처)에, 그 줄 바로 아래에 같은 소스 변수를 쓰는 줄을 더한다. 예를 들어 그 자리가 `partial_charge_slugs=r["partial_charge_slugs"],` 이면:

```python
                partial_charge_full_rounds=r["partial_charge_full_rounds"],
```

이고, `d[...]`를 쓰는 자리에서는 `d`를 쓴다. **세 자리를 모두 고쳐야 한다** - 한 곳이라도 빠지면 그 응답 경로에서만 필드가 비어 화면이 조용히 기존 문구로 돌아간다.

- [ ] **Step 5: 백엔드 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest -q`
Expected: 통과.

- [ ] **Step 6: 프론트 타입과 문구**

`frontend/src/types/recommend.ts`의 `partial_charge_slugs: string[]` 아래:

```ts
  partial_charge_full_rounds: Record<string, number>
```

`frontend/src/lib/helpText.ts`의 `tapFireAlways` 아래에 문구를 더한다(Fienn 문안, 2026-08-19):

```ts
    tapFireMixed: (names: string, fullRounds: number) =>
      `${names} 풀차지 ${fullRounds}회 + 톡톡이로 계산했어요.`,
```

`tapFireAlways` 위 주석 블록의 마지막 줄 앞에 한 문단을 더한다:

```
     * 매거진 안에서 두 모드를 **섞는** 유닛은 세 번째 문구를 쓴다(`tapFireMixed`).
     * 밀크: 블루밍 바니의 풀차지는 Pierce 6초를 되살리므로, 「항상 톡톡이」는 그녀에게
     * 거짓이고 그대로 두면 플레이어가 관통특화를 잃는다.
```

`frontend/src/components/DeckCard.tsx`에서 `partial_charge_slugs`를 렌더하는 블록(현재 107~113줄, `tapFireAlways`를 부르는 `<p>` 하나)을 아래로 교체한다. 풀차지 발수가 0이면 기존 「항상 톡톡이」, 1 이상이면 새 문구다:

```tsx
      {deck.partial_charge_slugs.filter((slug) => !deck.partial_charge_full_rounds[slug]).length >
        0 && (
        <p className="deck-results__hold">
          <span aria-hidden="true">&#128070;</span>{' '}
          <HelpText>
            {HELP.results.tapFireAlways(
              deck.partial_charge_slugs
                .filter((slug) => !deck.partial_charge_full_rounds[slug])
                .map(nameFor)
                .join(', '),
            )}
          </HelpText>
        </p>
      )}
      {deck.partial_charge_slugs
        .filter((slug) => deck.partial_charge_full_rounds[slug] > 0)
        .map((slug) => (
          <p className="deck-results__hold" key={`tap-mixed-${slug}`}>
            <span aria-hidden="true">&#128070;</span>{' '}
            <HelpText>
              {HELP.results.tapFireMixed(nameFor(slug), deck.partial_charge_full_rounds[slug])}
            </HelpText>
          </p>
        ))}
```

**주의**: 위의 `&#128070;`는 기존 코드에 있는 손가락 이모지 자리다. 교체할 때 **기존 줄의 이모지 문자를 그대로 옮겨 쓰고**, HTML 엔티티로 바꾸지 마라.

- [ ] **Step 7: 프론트 테스트**

`frontend/src/components/DeckCard.test.tsx`의 덱 fixture에 `partial_charge_full_rounds`를 더해 타입을 맞추고, 새 테스트를 하나 추가한다. fixture 헬퍼의 이름은 그 파일에서 실제로 쓰이는 것으로 맞춘다:

```tsx
it('풀차지를 섞는 좌석은 발수를 적어 안내한다', () => {
  renderDeckCard(
    makeDeck({
      partial_charge_slugs: ['milk-blooming-bunny'],
      partial_charge_full_rounds: { 'milk-blooming-bunny': 1 },
    }),
  )
  expect(screen.getByText(/풀차지 1회 \+ 톡톡이로 계산했어요/)).toBeInTheDocument()
  expect(screen.queryByText(/항상 톡톡이로 계산했어요/)).not.toBeInTheDocument()
})
```

- [ ] **Step 8: 프론트 검증**

```bash
cd frontend && npm test
cd .. && npx --prefix frontend tsc -b --noEmit frontend
```
Expected: 통과, 타입에러 0. `partial_charge_full_rounds`를 안 넣은 다른 fixture가 타입에러를 낼 수 있다 - 그 fixture들에도 빈 객체를 더한다.

- [ ] **Step 9: 커밋**

```bash
git add backend/ frontend/
git commit -m "톡톡이 안내가 풀차지 발수를 말한다 - 「항상 톡톡이」는 밀크에게 거짓이다"
```

---

## Self-Review

**스펙 커버리지**

| 스펙 절 | 태스크 |
|---|---|
| §설계 1 최적 k | Task 2 |
| §설계 2 매거진 안 배치 | Task 3 |
| §설계 3 registry 선언 + 낡은 주석 | Task 1, Task 4 Step 3 |
| §설계 4 Pierce 근거 교체 | Task 4 Step 4 |
| §설계 5 앨리스 회귀 방지 | Task 1 Step 6, Task 2 (동치 테스트), Task 3 Step 6 |
| §설계 6 테스트 8종 | Task 1~4에 분산 |
| §설계 7 파일 목록 | 전부 |
| §손계산 예측 재확인 | Task 5 Step 2 |
| 화면 문구 (스펙 밖 — Fienn 문안 2026-08-19) | Task 6 |

**타입 일관성** — `optimal_full_charges`의 인자 순서가 Task 2 정의, Task 3 호출, Task 4 테스트에서 모두 `(capacity, reload_seconds, charge_seconds, full_delay, tap_interval, full_charge_percent, window)`로 같다. `full_charge_positions(capacity, full_charges)`, `mixed_charge_round_offset(index, capacity, full_cost, tap_cost, full_positions)`도 정의와 호출이 일치한다.
