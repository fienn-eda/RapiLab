# 톡톡이 샷 부분 차지 대미지 정정 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 톡톡이 샷의 배율을 게이지 103%로 올리고, 차지 대미지 버프를 톡톡이 샷에서 떼어낸다.

**Architecture:** 먼저 `ShotRecord.is_tap_fire` 플래그를 도입해 값 비교로 톡톡이를 판별하던 세 자리를 옮긴다(**동작 불변**). 그 위에서 배율을 0.0 → 0.03으로 올리고, 마지막으로 차지 대미지 버프를 톡톡이 샷에서 뗀다. 셋을 나눈 이유는 각각이 딜을 다른 방향으로 움직이므로 리뷰어가 따로 판정할 수 있어야 하기 때문이다.

**Tech Stack:** Python 3 / pytest

**Spec:** `docs/superpowers/specs/2026-08-20-tap-fire-charge-damage-design.md`
**측정 근거:** `docs/measurements/bready-charge-damage.md`

## Global Constraints

- 백엔드 테스트는 **반드시 `backend/`에서** 실행한다 — 루트에서는 `No module named 'app'`. 전체 스위트는 약 4분이니 포그라운드로 타임아웃 600000ms.
- **현재 기준선: 백엔드 2565 passed / 3 skipped.** 프론트 949 passed / 74 files, 타입 0.
- 실측값: 톡톡이 게이지 **103%**(= `extra_charge_bonus` 0.03), 밀크 톡톡이 간격 15/60초 · 멈춤 22/60초 · 차지 1.0초 · 장탄 6 · 풀차지 250% · 재장전 2.0초 · Pierce 창 6.0초.
- **풀차지 경로는 건드리지 않는다.** 브래디 판독이 풀차지 쪽 공식을 정하지 못했다(스펙의 「정하지 못한 것」).
- `docs/measurements/`의 **RAW는 절대 편집하지 않는다.** 해석 절만 고친다.
- 프로젝트 규칙: 가장 작은 합리적 변경. 주석은 무엇을·왜만 적고 변경 이력은 안 적는다.
- **딜 변화를 손계산으로 재유도해 설명하지 않는다.** 이 저장소가 세 번 틀린 자리다 — 검산은 Task 4에서 엔진에 물어서 한다.

---

### Task 1: `is_tap_fire` 플래그를 도입한다 (동작 불변)

지금 코드는 `extra_charge_bonus` **값으로** 톡톡이를 판별하는 자리가 셋이다. Task 2가 그 값을 0.0에서 0.03으로 바꾸면 셋이 전부 조용히 뒤집힌다. 먼저 판별을 플래그로 옮겨 그 지뢰를 없앤다.

**Files:**
- Modify: `backend/app/attack_rate.py` (`ShotRecord` 필드, `_base_shot_records` 샷 생성)
- Modify: `backend/app/raid_simulator.py` (`full_charges_per_mixed_magazine`, `tap_fire_used` 감지)
- Test: `backend/tests/test_manual_tap_fire.py`

**Interfaces:**
- Produces: `ShotRecord.is_tap_fire: bool`(기본 False). Task 2·3이 이것을 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_manual_tap_fire.py` 끝에 추가한다. `_milk_weapon`은 이 파일에 이미 있는 헬퍼다:

```python
def test_tap_shots_carry_an_explicit_flag():
    """톡톡이 판별을 값이 아니라 플래그로 한다.

    `extra_charge_bonus`로 판별하던 자리가 셋 있었고, 톡톡이 배율이 100%가 아니게
    되는 순간 전부 조용히 뒤집힌다 - 집계는 톡톡이를 풀차지로 세고, 화면 안내는
    톡톡이를 못 찾는다. 플래그는 그 결합을 끊는다.
    """
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    magazine = shots[:MILK_CAPACITY]
    assert [s.is_tap_fire for s in magazine] == [False, True, True, True, True, True]


def test_a_full_charge_only_magazine_flags_nothing():
    """톡톡이를 안 쓰는 유닛의 샷에는 플래그가 안 붙는다."""
    weapon = _milk_weapon()
    weapon["tap_fire"] = False
    shots = generate_segmented_shots(weapon, (), 6.0)
    assert not any(s.is_tap_fire for s in shots[:MILK_CAPACITY])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -k explicit_flag -v`
Expected: FAIL — `AttributeError: 'ShotRecord' object has no attribute 'is_tap_fire'`

- [ ] **Step 3: `ShotRecord`에 필드를 더한다**

`backend/app/attack_rate.py`의 `class ShotRecord` 맨 끝(`magazine_index` 다음)에 넣는다:

```python
    # 톡톡이(차지를 안 채우고 곧바로 놓은) 샷인가. 배율과 차지 대미지 적용이 이것으로
    # 갈린다. 값(`extra_charge_bonus`)으로 추론하지 않고 명시적으로 드는 이유는, 그
    # 값이 톡톡이의 배율이기도 해서 배율이 바뀌면 판별이 함께 뒤집히기 때문이다.
    is_tap_fire: bool = False
```

- [ ] **Step 4: 샷 생성이 플래그를 세운다**

같은 파일 `_base_shot_records`의 차지 분기에서, `records.append(ShotRecord(...))` 호출에 인자를 하나 더한다. `is_full`은 그 자리에 이미 있는 지역 변수다:

```python
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"],
                    full_bonus if is_full else 0.0,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1),
                    magazine_index=i, is_tap_fire=not is_full))
```

- [ ] **Step 5: 두 판별을 플래그로 바꾼다**

`backend/app/raid_simulator.py`의 `full_charges_per_mixed_magazine` 안:

```python
        if not record.is_tap_fire:
            current_full += 1
        else:
            current_has_tap = True
```

(바꾸기 전은 `if record.extra_charge_bonus > 0:`)

같은 파일 `tap_fire_used` 감지:

```python
        if weapon.get("tap_fire") and any(r.is_tap_fire for r in shot_records):
```

(바꾸기 전은 `any(r.extra_charge_bonus == 0.0 for r in shot_records)`)

그 바로 위 주석의 마지막 문장도 사실에 맞게 고친다 — 지금은 「톡톡이 샷은 차지 보너스가 0이고 풀차지 샷은 0보다 크므로 기록에서 그대로 읽힌다」인데, 이제 기록이 플래그로 답한다:

```
        # 「이 덱에서 어떻게 계산했는지」를 말해야 하는데, 그 답이 이제 유닛의 속성이
        # 아니라 **덱의 재장전 속도와 차속 창**에 달렸다. 어느 샷이 톡톡이인지는
        # 기록의 `is_tap_fire`가 답한다.
```

- [ ] **Step 6: 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -v`
Expected: PASS

- [ ] **Step 7: 전체 스위트 — 동작 불변이어야 한다**

Run: `cd backend && python -m pytest -q`
Expected: **2565 + 2 = 2567 passed / 3 skipped.** 이 태스크는 판별 방식만 옮겼고 값은 그대로이므로 **어떤 유닛의 딜도 움직이면 안 된다.** 딜 관련 테스트가 깨지면 멈추고 보고한다.

(엄밀히는 한 경우에 동작이 달라진다: 풀차지 배율이 정확히 100%인 차지 무기가 있다면 옛 판별이 그 풀차지 샷을 톡톡이로 오인했다. 그런 무기는 데이터에 없고, 새 방식이 옳다.)

- [ ] **Step 8: 커밋**

```bash
git add backend/app/attack_rate.py backend/app/raid_simulator.py backend/tests/test_manual_tap_fire.py
git commit -m "톡톡이 판별을 값에서 플래그로 옮긴다 - 배율이 바뀌면 값 판별이 뒤집힌다"
```

---

### Task 2: 톡톡이 배율을 게이지 103%로 올린다

**Files:**
- Modify: `backend/app/attack_rate.py` (상수 추가, 샷 생성, `tap_fire_wins`, `optimal_full_charges`)
- Test: `backend/tests/test_manual_tap_fire.py`

**Interfaces:**
- Consumes: `ShotRecord.is_tap_fire` (Task 1)
- Produces: `attack_rate.TAP_FIRE_CHARGE_BONUS = 0.03`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_a_tap_shot_is_gauge_103_not_100():
    """게이지 100%는 「차지하지 않은 판정」이라 발사가 안 된다 - 발사에 필요한
    관측된 최소값이 103%다(Fienn, 2026-08-20, docs/measurements/bready-charge-damage.md).

    한동안 엔진은 0.0(게이지 100%)을 썼고, 그 근거였던 「톡톡이는 게이지를 전혀 안
    채운다」는 「게이지가 오르는 첫 프레임과 발사 프레임이 같다」를 잘못 읽은 것이었다.
    """
    from app.attack_rate import TAP_FIRE_CHARGE_BONUS
    assert TAP_FIRE_CHARGE_BONUS == pytest.approx(0.03)
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    taps = [s for s in shots[:MILK_CAPACITY] if s.is_tap_fire]
    assert taps, "이 매거진에 톡톡이 샷이 있어야 이 테스트가 무언가를 검증한다"
    for shot in taps:
        assert shot.extra_charge_bonus == pytest.approx(0.03)


def test_the_cadence_choice_weighs_taps_at_103():
    """케이던스 선택이 타임라인과 **같은 배율**로 저울질해야 한다.

    타임라인은 103%로 쏘는데 「어느 모드가 이기나」를 100%로 판단하면, 엔진이 자기가
    쏘는 것과 다른 것을 놓고 고르게 된다. 톡톡이가 3% 유리해졌으므로 손익분기 탭
    간격이 올라가고, 그 경계 바로 위에 있던 조합에서 답이 뒤집힌다.
    """
    from app.attack_rate import TAP_FIRE_CHARGE_BONUS, tap_fire_wins
    # 톡톡이 배율 1.00으로는 지고 1.03으로는 이기는 지점을 이분법으로 찾는다.
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if tap_fire_wins(1.0, mid, 250.0, 6, 2.0):
            lo = mid
        else:
            hi = mid
    breakeven = lo
    # 그 손익분기에서 100% 가정이라면 톡톡이가 정확히 비긴다. 1.03이면 이겨야 한다.
    naive = 6 * 1.00 / (6 * breakeven + 2.0)
    lifted = 6 * (1 + TAP_FIRE_CHARGE_BONUS) / (6 * breakeven + 2.0)
    full = 6 * 2.5 / (6 * (1.0 + breakeven) + 2.0)
    assert naive == pytest.approx(full, rel=1e-6)
    assert lifted > full
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -k "gauge_103 or weighs_taps" -v`
Expected: FAIL — `ImportError: cannot import name 'TAP_FIRE_CHARGE_BONUS'`

- [ ] **Step 3: 상수를 넣는다**

`backend/app/attack_rate.py`에서 `tap_fire_wins` **바로 위**에 넣는다:

```python
# 톡톡이 샷의 차지 보너스 - HUD 게이지 103%.
#
# 게이지 100%는 **차지하지 않은 판정**이라 발사가 되지 않고, 103%가 발사에 필요한
# 관측된 최소값이다(Fienn, 2026-08-20). 브래디를 차지 대미지 두 세팅으로 잰 판독에서
# 두 세팅 모두 최소 게이지가 103%였다 - 차지 대미지는 발사 문턱을 옮기지 않는다.
#
# 유닛별 표가 아니라 상수인 이유: 브래디와 앨리스 두 유닛에서 같은 하한이 나왔고,
# 엔진은 케이던스도 이상적 수동 플레이로 모델링한다(앨리스 멈춤 15프레임은 자동사격
# 26.1프레임이 아니라 수동 기준이다). 유닛별로 가르면 없는 정밀도를 주장하게 된다.
#
# docs/measurements/bready-charge-damage.md
TAP_FIRE_CHARGE_BONUS = 0.03
```

- [ ] **Step 4: 세 자리가 그 값을 쓰게 한다**

`_base_shot_records`의 샷 생성:

```python
                    full_bonus if is_full else TAP_FIRE_CHARGE_BONUS,
```

`tap_fire_wins`의 반환:

```python
    return (per_magazine(0.0, 1 + TAP_FIRE_CHARGE_BONUS)
            > per_magazine(charge_seconds, charge_damage_percent / 100))
```

`optimal_full_charges`의 대미지 식 — 지금은 톡톡이 배율을 1.0으로 **암묵 가정**하고 있다:

```python
        tap_multiplier = 1 + TAP_FIRE_CHARGE_BONUS
        damage = capacity * tap_multiplier + k * (multiplier - tap_multiplier)
```

(바꾸기 전은 `damage = capacity + k * (multiplier - 1)`)

같은 함수 docstring의 대미지 식도 사실에 맞게 고친다 — 지금 `(C + k(M-1))`로 적혀 있는 자리를 `(C·tap + k(M−tap))`로.

- [ ] **Step 5: 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -v`
Expected: PASS

- [ ] **Step 6: 전체 스위트 — 여기서 딜이 움직인다**

Run: `cd backend && python -m pytest -q`
Expected: 톡톡이를 쓰는 유닛(앨리스·밀크)의 딜을 고정한 테스트가 있으면 **오른다**(+3% 방향). 새 값으로 갱신하되, **왜 그 방향인지 한 줄로 쓸 수 있어야** 한다. 못 쓰겠으면 멈추고 보고한다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_manual_tap_fire.py
git commit -m "톡톡이 샷은 게이지 103%다 - 100%로는 발사가 안 된다"
```

---

### Task 3: 톡톡이 샷에서 차지 대미지 버프를 뗀다

`raid_simulator`의 주석이 이미 「Charge Damage multiplies a **fully-charged SHOT** and nothing else」라고 적고 있다. 톡톡이 샷은 fully-charged가 아니다 — 주석이 맞았고 코드가 그것을 안 따랐다.

**Files:**
- Modify: `backend/app/raid_simulator.py` (`record` 시그니처·dict, `_damage_instance` 시그니처·차지대미지, 두 호출부)
- Test: `backend/tests/test_manual_tap_fire.py`

**Interfaces:**
- Consumes: `ShotRecord.is_tap_fire` (Task 1), `TAP_FIRE_CHARGE_BONUS` (Task 2)

**플래그가 대미지 계산까지 가는 경로** — `_damage_instance`는 `ShotRecord`를 받지 않으므로 파라미터로 통과시킨다. 경로는 하나이고 손댈 지점이 넷이다:

```
_base_shot_records -> ShotRecord.is_tap_fire
   -> record(..., is_tap_fire=rec.is_tap_fire)        [지점 A: 호출부]
   -> record()가 damage_events dict에 저장             [지점 B: 시그니처 + dict]
   -> _damage_instance(..., is_tap_fire=ev[...])      [지점 C: 소비부]
   -> charge_damage_bonus 계산                         [지점 D: 시그니처 + 계산]
```

**하나라도 빠지면 그 샷은 조용히 옛 계산을 탄다.**

- [ ] **Step 1: 실패하는 테스트를 쓴다**

이 계약은 **단위로는 검증할 수 없다** — 게이팅은 「누가 무엇을 넘기는가」이지
`calculate_damage`가 받은 값을 어떻게 쓰는가가 아니다. 그래서 통합 테스트로 간다.

`backend/tests/test_charge_damage_is_charge_weapons_only.py`가 정확히 이 주제의
파일이고 `_normal_damage(weapon_stats, charge_bonus)` 헬퍼를 이미 갖고 있다.
그 파일의 `SR` 상수 아래에 픽스처를 하나 더한다:

```python
# 재장전이 0이면 톡톡이가 언제나 이기므로 이 무기는 매거진을 통째로 톡톡이로 쏜다 -
# 그래야 아래 테스트가 톡톡이 샷만 보고 있다는 것이 보장된다.
TAP_SR = {**SR, "reload_time": 0.0, "tap_fire": True,
          "tap_fire_interval": 15 / 60, "charge_motion_delay": 22 / 60}
```

그리고 테스트 둘을 파일 끝에 더한다:

```python
def test_the_tap_fire_fixture_actually_taps():
    """아래 테스트가 무언가를 검증하려면 이 무기가 **실제로** 톡톡이를 써야 한다.

    안 그러면 「차지 대미지가 톡톡이에 안 붙는다」가 톡톡이 샷이 하나도 없어서
    참인 항진명제가 된다.
    """
    from app.attack_rate import generate_segmented_shots
    shots = generate_segmented_shots(TAP_SR, (), 10.0)
    assert shots, "이 무기가 한 발도 안 쏜다"
    assert all(s.is_tap_fire for s in shots)


def test_a_charge_damage_buff_does_not_reach_a_tap_fired_shot():
    """톡톡이 샷은 차지를 안 채웠으므로 fully-charged가 아니다 - 이 파일의 첫
    문단이 말하는 그 조건을 만족하지 않는다.

    브래디 실측(2026-08-20)이 그것을 보였다: 차지 대미지를 7.59%에서 11.11%로
    올려도 같은 게이지의 대미지가 +0.06%밖에 안 달라진다. 직접 곱해진다면
    +3.27%여야 한다. docs/measurements/bready-charge-damage.md

    바로 위 `test_a_charge_damage_buff_still_reaches_a_charge_weapon`이 같은 SR을
    풀차지로 쏠 때는 버프가 통한다는 것을 지키고 있으므로, 이 둘이 함께
    「풀차지에는 붙고 톡톡이에는 안 붙는다」를 못박는다.
    """
    assert _normal_damage(TAP_SR, 1.008) == _normal_damage(TAP_SR, 0.0)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py -k charge_damage -v`
Expected: FAIL

- [ ] **Step 3: 플래그를 `record()`에 통과시킨다**

`backend/app/raid_simulator.py`의 `def record(` 시그니처에 인자를 더한다(`magazine_index=None,` 옆):

```python
        is_tap_fire=False,
```

같은 함수의 `damage_events.append({...})` dict에 항목을 더한다:

```python
            "is_tap_fire": is_tap_fire,
```

- [ ] **Step 4: 호출부가 플래그를 넘긴다**

같은 파일에서 `record(slug, rec.damage_percent, shot_time, "normal_attack", ...)`를 부르는 자리(`extra_charge_bonus=rec.extra_charge_bonus,`가 있는 곳)에 더한다:

```python
                   is_tap_fire=rec.is_tap_fire,
```

- [ ] **Step 5: `_damage_instance`가 받아서 쓴다**

`def _damage_instance(` 시그니처에 더한다:

```python
        is_tap_fire=False,
```

그 함수의 `charge_damage_bonus=(...)` 블록을 아래로 교체한다:

```python
            charge_damage_bonus=(
                (extra_charge_bonus if is_tap_fire
                 else bundle["charge_damage_bonus"] + extra_charge_bonus)
                if on_charge_weapon
                else 0.0
            ),
```

그 위 주석에 한 문단을 더한다(기존 주석의 「fully-charged SHOT」 문장 바로 아래):

```
            # 그래서 **톡톡이 샷은 이 버프를 안 받는다** - 차지를 안 채운 샷이므로
            # fully-charged가 아니다. 브래디 실측(2026-08-20)이 그것을 보였다: 차지
            # 대미지를 7.59%에서 11.11%로 올려도 같은 게이지의 대미지가 +0.06%밖에
            # 안 달라진다(직접 곱해진다면 +3.27%). 남는 것은 그 샷 자신의 게이지분
            # (`extra_charge_bonus` = 103%)뿐이다.
```

- [ ] **Step 6: 이벤트 소비부가 넘긴다**

같은 파일에서 `_damage_instance(ev["slug"], percent, ev["time"], ...)`를 부르는 자리에 더한다:

```python
                    is_tap_fire=ev["is_tap_fire"],
```

- [ ] **Step 7: 테스트가 통과하는지 본다**

Run: `cd backend && python -m pytest tests/test_manual_tap_fire.py tests/test_raid_simulator.py -q`
Expected: PASS

- [ ] **Step 8: 전체 스위트 — 여기서 딜이 반대로 움직인다**

Run: `cd backend && python -m pytest -q`
Expected: 차지 대미지 버프를 받는 톡톡이 유닛의 딜이 **내린다**. 고정값 테스트를 갱신하되 방향을 설명할 수 있어야 한다.

**`ev["is_tap_fire"]`에서 `KeyError`가 나면** dict에 안 담긴 경로가 있다는 뜻이다 — Step 3의 dict 항목을 빠뜨렸거나, `record()`를 우회해 `damage_events`에 직접 넣는 자리가 따로 있다. 후자면 멈추고 보고한다.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/raid_simulator.py backend/tests/
git commit -m "차지 대미지는 풀차지된 샷에만 붙는다 - 주석은 맞았고 코드가 안 따랐다"
```

---

### Task 4: 엔진에 물어 검산하고 문서를 고친다

**Files:**
- Modify: `backend/scripts/audit_milk_tap_fire.py` (톡톡이 배율을 함께 찍게)
- Modify: `docs/measurements/alice-tap-fire.md` (해석 절만)
- Modify: `backend/app/skill_rules/alice.py` (보류 항목이 닫혔다)
- Modify: `docs/roadmap.md`, `docs/engine-gaps.md`, `docs/encoded-nikkes.md`
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`

- [ ] **Step 1: 검산 스크립트가 배율을 함께 찍게 한다**

`backend/scripts/audit_milk_tap_fire.py`의 `report()`가 지금 발수·풀차지 수·최대간격·누적배율을 찍는다. 톡톡이 샷의 **차지 배율**을 한 칸 더한다 — 이번 변경이 옳게 들어갔는지 이 스크립트가 답해야 한다:

```python
    taps = [s for s in shots if s.is_tap_fire]
    tap_mult = (1 + taps[0].extra_charge_bonus) if taps else float("nan")
```

출력 줄에 `톡톡이배율 {tap_mult:.3f}`를 더한다.

- [ ] **Step 2: 돌려서 밀크의 새 수치를 얻는다**

Run: `cd backend && python scripts/audit_milk_tap_fire.py`
Expected: 톡톡이배율 **1.030**, 「창 초과」 0건.

그리고 밀크 덱 딜의 새 값을 얻는다 — 스크립트가 톡톡이 on/off 대조 행을 이미 찍으므로 그 비가 새 이득이다. **이 값이 문서에 들어갈 유일한 근거다. 손으로 계산하지 말 것.**

- [ ] **Step 3: 앨리스 측정 문서의 해석 절을 고친다**

`docs/measurements/alice-tap-fire.md`의 「### 톡톡이 샷은 정확히 100%」 절을 아래로 교체한다. **RAW 블록과 판독 표는 건드리지 않는다:**

```
### 톡톡이 샷은 게이지 103%다 (2026-08-20 정정)

이 자리에는 「게이지가 오르는 첫 프레임과 발사 프레임이 같으므로 톡톡이는 게이지를
전혀 안 채운다 - 배율 100%」라고 적혀 있었다. **발사 자체가 게이지 3%를 요구한다는
것을 못 봤다** — 게이지 100%는 「차지하지 않은 판정」이라 방아쇠가 안 나간다
(Fienn, 2026-08-20). 발사에 필요한 관측된 최소값은 **103%**이고, 브래디를 차지 대미지
두 세팅으로 잰 판독에서 두 세팅 모두 최소 게이지가 103%였다
(`bready-charge-damage.md`).

**위 판독의 104%·107%도 그것과 맞는다** — 손이 한두 프레임 더 붙든 경우다. 당시
그 둘을 「모델은 100%인데 실측이 104~107%이니 3~7% 과소」로 읽었는데, 과소의 정체는
손의 여유가 아니라 **발사 문턱 자체**였다.
```

- [ ] **Step 4: 앨리스 인코딩의 보류 항목을 닫는다**

`backend/app/skill_rules/alice.py`의 「**The frame a tap does bank.**」 항목을 아래로 교체한다:

```
- **A tap fires at gauge 103%, not 100%.** Gauge 100% is the "not charged" state
  and the trigger does not go off there; 103% is the lowest gauge a shot has been
  observed at (Fienn, 2026-08-20, docs/measurements/bready-charge-damage.md).
  The engine models a tapped shot at that 103% (`attack_rate.TAP_FIRE_CHARGE_BONUS`).
  This closes what used to stand here as a 3-7% understatement: the readings of
  104% and 107% above were not a loose hand against a 100% model, they were a
  loose hand against a 103% floor.
```

- [ ] **Step 5: 나머지 living document를 갱신한다**

- `docs/roadmap.md` — 이 작업의 To-Do 항목을 더한다. 밀크의 새 이득 수치(Step 2에서 잰 값)와 새 기준선을 적는다.
- `docs/engine-gaps.md` — 톡톡이 배율/차지대미지 관련 항목이 있으면 갱신한다.
- `docs/encoded-nikkes.md` — 앨리스·밀크의 수치가 적혀 있으면 갱신한다.
- `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md` — 톡톡이 능력 항목에 **배율 103%**와 **차지 대미지를 안 받는다**를 더한다. 이 카탈로그는 프로젝트의 일곱 번째 living document이고, 적히지 않은 능력은 다음 세션이 갭으로 다시 기록한다.

**`docs/decisions.md`와 `docs/insights.md`는 건드리지 않는다** — 컨트롤러가 docs-keeper로 따로 처리한다(프로젝트 CLAUDE.md 규칙).

- [ ] **Step 6: 전체 검증**

```bash
cd backend && python -m pytest -q
cd ../frontend && npm test -- --run
cd .. && npx --prefix frontend tsc -b --noEmit frontend
```
Expected: 백엔드·프론트 통과, 타입에러 0. 프론트는 이 변경이 안 건드리므로 **949 passed / 74 files 그대로**여야 한다.

- [ ] **Step 7: 커밋**

```bash
git add backend/ docs/ .claude/skills/
git commit -m "톡톡이 배율 정정을 검산하고 문서를 고친다"
```

---

## Self-Review

**스펙 커버리지**

| 스펙 절 | 태스크 |
|---|---|
| §설계 1 배율 103% (세 자리) | Task 2 |
| §설계 2 차지대미지 게이팅 | Task 3 |
| §설계 3 `is_tap_fire` 플래그 + 값 판별 셋 | Task 1 (판별 둘) · Task 3 (차지대미지) |
| §설계 3 플래그를 나르는 경로 | Task 3 Step 3~6 (네 지점) |
| §설계 4 103% 고정값 근거 | Task 2 Step 3 (상수 docstring) |
| §영향 (밀크·아인) | Task 4 Step 2 — **엔진에 물어서** |
| §테스트 1~9 | Task 1(1·2·6·7) · Task 2(5) · Task 3(3·4·8) · Task 4(9) |
| §「뒤집는 기존 결론」 | Task 4 Step 3·4 |
| §범위 밖 (풀차지 공식 · 아인 B/C) | 손대지 않음 — 계획에 없음 |

**스펙과 다른 점 하나**: 스펙이 플래그 전달 경로를 「둘(직접 호출 / 이벤트 큐)」이라 적었는데, 실제로는 `record()` → dict → `_damage_instance` **한 경로에 네 지점**이다. 계획은 실제 구조를 따랐다.

**타입 일관성** — `is_tap_fire`가 `ShotRecord` 필드(Task 1), `record()` 인자, `damage_events` dict 키, `_damage_instance` 인자(Task 3)에서 모두 같은 이름·같은 bool 타입이다. `TAP_FIRE_CHARGE_BONUS`는 Task 2가 정의하고 Task 2·4가 읽는다.
