# 아핀 재장전 모델 착륙 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 엔진의 재장전 공식을 실측이 기각한 역수 형태에서 아핀 형태(`파일값 × (1 − s) + 0.148초`)로 바꾼다.

**Architecture:** 변경은 `attack_rate.reload_time_with_speed` **한 함수**다. 재장전을 계산하는 모든 경로(발사 타임라인 9개 호출부 · 차지창 계산기)가 이미 이 함수를 통과하므로 배선은 새로 안 만든다. 파일값에 클립 분할 수를 곱해 넘기는 `user_roster`의 접기도 그대로 두면 고정 구간이 탄창당 한 번 붙어 의도와 일치한다.

**Tech Stack:** Python 3.14 · pytest · 기존 백엔드(`backend/app`), 측정 스크립트(`scripts/`)

## Global Constraints

- 설계 원본: `docs/superpowers/specs/2026-07-31-affine-reload-model-design.md`
- 식: `max(0.0, reload_time * (1 - s) + 0.148)` — **분기 없음**, 음수 방향도 같은 식.
- **고정 구간 0.148초는 전역**이다(Fienn 결정 2026-07-31). 밀크(SR)·센티(RL)가 상수 0으로 읽히지만 판독이 거칠었던 것으로 본다.
- **s=0은 더 이상 항등이 아니다** — 무버프 재장전 = 파일값 + 0.148초. 이를 고정하던 테스트는 갱신이 아니라 **삭제**한다.
- **캘리브레이션 악화는 예상된 결과다**(1.0150x/21·25 → 약 1.0553x/19·25). 이 값이 나빠졌다고 되돌리지 않는다.
- 클립 접기(`user_roster`)와 차지창 계산기는 **코드 변경 없음** — 자동으로 새 식을 탄다.
- 테스트 실행: `cd backend; python -m pytest`. 착수 시점 기준선은 **1668 passed / 3 skipped**.
- 커밋 메시지는 무엇을 하는지 현재형으로 쓴다(변경 이력·"예전엔 이랬다" 금지 — `.claude/CLAUDE.md`).

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/app/attack_rate.py` (수정) | `RELOAD_FIXED_SECONDS` 신설 + `reload_time_with_speed` 재작성 |
| `backend/tests/test_attack_rate.py` (수정) | 공식 테스트 4건 정리 + 실측 6점 앵커 + 0 바닥 |
| `backend/app/user_roster.py` (수정) | 클립 접기 주석을 "해소"로 갱신 (코드 무변경) |
| `backend/tests/test_clip_reload.py` 또는 기존 클립 테스트 (수정) | 클립이 고정 구간을 탄창당 한 번만 받는 것 |
| `docs/measurements/reload-affine.md` (신규) | 실측 6점과 미기록 조건 |
| `docs/engine-gaps.md` (수정) | ★ 항목 해소 + 드러난 과대 항 신규 |
| `docs/roadmap.md` (수정) | To-Do |

---

### Task 1: 공식을 아핀으로 바꾼다

**Files:**
- Modify: `backend/app/attack_rate.py:108-126` (`reload_time_with_speed`)
- Test: `backend/tests/test_attack_rate.py:488-510`

**Interfaces:**
- Produces: `RELOAD_FIXED_SECONDS = 0.148` (모듈 상수), `reload_time_with_speed(reload_time, reload_speed_percent) -> float` — 시그니처 불변, 반환값만 바뀐다

- [ ] **Step 1: Write the failing test**

`backend/tests/test_attack_rate.py`에서 아래 **세 테스트를 지운다** — 셋 다 아핀 모델이 부정하는 성질이라 갱신이 아니라 제거가 맞다:
`test_reload_speed_buff_shortens_the_reload_reciprocally` ·
`test_reload_speed_directions_are_reciprocal_mirrors` ·
`test_reload_speed_zero_is_the_identity_on_both_branches`.

그 자리에 넣는다(`test_reload_speed_reduction_lengthens_the_reload_symmetrically`는 아래 갱신본으로 교체):

```python
# Fienn's six readings, 60fps, 2026-07-29 - the measurements the affine model
# was fitted to, promoted to a regression anchor. Max residual is 1.12 frames
# (Privaty unbuffed), so the bound is 1.2 frames.
RELOAD_READINGS = [
    # (file reload, reload speed, measured seconds)
    (1.0, 0.0000, 1.1667),   # Privaty, AR, unbuffed
    (1.0, 0.2969, 0.8333),   # + Resilience cube
    (1.0, 0.8085, 0.3500),   # + cube and Privaty's own buff
    (2.5, 0.0000, 2.6500),   # Rapi: Red Hood, MG, unbuffed
    (2.5, 0.2969, 1.9000),
    (2.5, 0.8085, 0.6400),
]


def test_the_model_reproduces_every_measured_reload():
    for file_value, speed, measured in RELOAD_READINGS:
        assert reload_time_with_speed(file_value, speed) == pytest.approx(
            measured, abs=1.2 / 60), f"file {file_value} at {speed:.4%}"


def test_an_unbuffed_reload_is_the_file_value_plus_the_fixed_segment():
    """The model's core reinterpretation: the data file's reloadTime is the part
    a buff scales, not the reload itself. Privaty's 1.0-sec file value measures
    1.1667 in game with nothing on her."""
    assert reload_time_with_speed(1.0, 0.0) == pytest.approx(1.148)
    assert reload_time_with_speed(2.5, 0.0) == pytest.approx(2.648)


def test_reload_speed_reduction_lengthens_the_reload():
    """Milk: Blooming Bunny's forced reload - "reload speed fixed at a 50%
    reduction" - scales her 2-sec file value by 1.5. She reads 3.0 sec in game
    (Fienn, 2026-07-20), which is the file value alone; the fixed segment is
    taken as global anyway (Fienn, 2026-07-31), so the model says 3.148 and that
    reading is treated as too coarse to resolve 9 frames."""
    assert reload_time_with_speed(2.0, -0.5) == pytest.approx(3.148)


def test_enough_reload_speed_removes_the_reload_entirely():
    """The observation that killed the reciprocal form: Crown + Privaty + the
    Resilience cube reach 125.20% and the reload disappears. `time / (1 + s)`
    cannot reach zero at any speed; this form reaches it at 1 + 0.148/file."""
    assert reload_time_with_speed(1.0, 1.148) == pytest.approx(0.0)
    assert reload_time_with_speed(1.0, 1.2520) == 0.0
    assert reload_time_with_speed(2.5, 1.2520) == 0.0


def test_the_reload_never_goes_negative():
    for speed in (1.5, 2.0, 10.0):
        assert reload_time_with_speed(1.0, speed) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; python -m pytest tests/test_attack_rate.py -k reload -v`
Expected: FAIL — 앵커 6점과 0 바닥이 전부 어긋난다(현행은 `1.0/(1+0)=1.0` 대 기대 1.148 등)

- [ ] **Step 3: Write minimal implementation**

`backend/app/attack_rate.py`의 `reload_time_with_speed`를 통째로 바꾼다:

```python
# The part of a reload that no buff scales. Reload is affine, not reciprocal:
# the data file's reloadTime is what a reload-speed buff multiplies, and a fixed
# animation segment sits on top of it. Fienn's six readings (2026-07-29, 60fps)
# fit `file * (1 - s) + 0.148` to 1.12 frames, and solving them per unit returns
# slopes of 1.0029 and 2.4835 against file values of 1.0 and 2.5 - the file is
# right, the old formula was not. Same shape as CHARGE_MOTION_DELAY_SECONDS.
#
# Taken as global (Fienn, 2026-07-31). The two readings that show no fixed
# segment are both charge weapons - Milk's forced reload at -50% (exactly 1.5x
# her file value) and Centi's clip load (exactly her 0.5-sec file value) - so a
# per-weapon-class constant is a live alternative that those readings are too
# coarse to settle.
RELOAD_FIXED_SECONDS = 0.148


def reload_time_with_speed(reload_time, reload_speed_percent):
    """Reload TIME from a reload-SPEED modifier, in both directions.

    One expression, no branch: the negative direction was already
    `file * (1 - s)` (Milk: Blooming Bunny's forced reload measures 3 sec
    against her 2-sec file value at -50%, not 4), and this returns the positive
    direction to the same convention.

    `max(0.0, ...)` is what lets the reload actually disappear. Crown (44.35%)
    plus Privaty (51.16%) plus the Resilience cube (29.69%) reach 125.20% and
    the game stops reloading; `time / (1 + s)` gives 0.888 sec there and cannot
    reach zero at any speed. Whether the fixed segment survives past that point
    or is clipped away with the rest is unmeasured - this clips it, which is the
    reading that needs no second rule.
    """
    return max(0.0, reload_time * (1 - reload_speed_percent) + RELOAD_FIXED_SECONDS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend; python -m pytest tests/test_attack_rate.py -k reload -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/attack_rate.py backend/tests/test_attack_rate.py
git commit -m "Reload the way it measures: a scaled part plus a fixed one"
```

---

### Task 2: 전체 회귀와 클립 규약

**Files:**
- Modify: `backend/app/user_roster.py:78-95` (주석만)
- Test: `backend/tests/test_attack_rate.py` (클립 케이스 추가)
- Modify: 전체 스위트에서 깨지는 테스트

**Interfaces:**
- Consumes: `RELOAD_FIXED_SECONDS`, 새 `reload_time_with_speed` (Task 1)

- [ ] **Step 1: Write the failing test**

`backend/tests/test_attack_rate.py`에 추가:

```python
def test_a_clip_weapon_pays_the_fixed_segment_once_per_magazine():
    """Centi loads 2 rounds at a time, three times, to fill her 6-round
    magazine. `user_roster` folds that by multiplying her 0.5-sec file value by
    3 BEFORE this function sees it, so the fixed segment lands once for the
    magazine rather than once per load - the convention Fienn confirmed for the
    charge motion delay on the same reload (2026-07-31)."""
    folded = 0.5 * 3
    assert reload_time_with_speed(folded, 0.0) == pytest.approx(1.648)
    per_load = 3 * reload_time_with_speed(0.5, 0.0)
    assert per_load == pytest.approx(1.944)
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd backend; python -m pytest tests/test_attack_rate.py -k clip_weapon -v`
Expected: PASS (Task 1의 식이 이미 이 성질을 갖는다 — 이 테스트는 **규약을 고정**하는 것이지 새 동작을 요구하지 않는다). 실패하면 Task 1의 식이 잘못 들어간 것이다.

- [ ] **Step 3: 전체 스위트를 돌려 낙진을 본다**

Run: `cd backend; python -m pytest -q`
Expected: 재장전을 상수로 기대하던 테스트들이 깨진다. 각각을 **모델이 부정하는 성질인지, 아니면 우연히 재장전에 의존하던 앵커인지** 판단해 고친다:
- 모델이 부정하는 성질(역수·항등·거울대칭) → 삭제
- 실측 앵커인데 재장전이 끼어 값이 바뀐 것 → 새 값으로 갱신하고 **왜 바뀌었는지 주석**
- 발사 시각을 하드코딩한 타이밍 테스트 → 새 재장전으로 재계산

**임의로 허용 오차를 넓히지 말 것.** 그것은 테스트를 지우는 것과 같다.

- [ ] **Step 4: 클립 접기 주석을 해소로 갱신**

`backend/app/user_roster.py`에서 아래 문장을 교체한다:

```
        # in attack_rate leaves all nine of its reload call sites untouched;
        # reload_time_with_speed is linear in reload_time on both branches, so
        # the order does not matter. If the affine reload model lands
        # (docs/engine-gaps.md), whether its fixed 0.148 sec segment is per load
        # or per magazine has to be settled before this fold stays correct.
```

새 문장:

```
        # in attack_rate leaves all nine of its reload call sites untouched;
        # reload_time_with_speed is linear in reload_time, so the order does not
        # matter. The affine model's fixed segment lands ONCE for the magazine
        # because the multiplication happens here, before it - the same
        # convention Fienn confirmed for the charge motion delay after a clip
        # reload, which also lands once rather than per load.
```

- [ ] **Step 5: 전체 스위트가 통과하는지 확인**

Run: `cd backend; python -m pytest -q`
Expected: 전부 통과, skip 3

- [ ] **Step 6: Commit**

```bash
git add backend/app/user_roster.py backend/tests/
git commit -m "Pin that a clip magazine pays the fixed segment once"
```

---

### Task 3: 실기록 재측정과 문서

**Files:**
- Create: `docs/measurements/reload-affine.md`
- Modify: `docs/engine-gaps.md` (★ 항목 · 마지막 갱신 줄 · 갭 요약표)
- Modify: `docs/roadmap.md` (To-Do)
- Modify: `docs/superpowers/specs/2026-07-31-affine-reload-model-design.md` (Status)

**Interfaces:**
- Consumes: Task 1·2의 착륙된 엔진

- [ ] **Step 1: 캘리브레이션을 잰다**

```bash
python scripts/measure_record_calibration.py
```
전/후 비교는 설계 문서의 표를 쓰되, **이 실행의 실제 출력을 기록한다**(설계 시점의 스크래치 측정은 1.0553x/19·25였다 — 착륙본이 다르면 착륙본이 사실이다).

- [ ] **Step 2: 실측을 `docs/measurements/`에 남긴다**

`docs/measurements/reload-affine.md`:

```markdown
# 재장전 아핀 모델 — 실측 (2026-07-29)

- 측정: Fienn, 60fps 영상 판독
- 이 파일이 존재하는 이유: `attack_rate.RELOAD_FIXED_SECONDS = 0.148`이 이 여섯 점
  위에 서 있다. 상수가 근거 없이 떠다니지 않게 원본을 남긴다.

## RAW

| 유닛 | 무기 | 파일값 | 무버프 | 큐브만(29.69%) | 큐브+프리바티(80.85%) |
|---|---|---|---|---|---|
| 프리바티 | AR | 1.0초 | 1.1667 | 0.8333 | 0.3500 |
| 라피: 레드후드 | MG | 2.5초 | 2.65 | 1.90 | 0.64 |

## 이 숫자가 정하는 것

- 유닛별로 직선을 맞추면 기울기 **1.0029 / 2.4835** — 파일값 1.0 / 2.5와 일치.
  **데이터 파일은 맞았고 엔진의 식이 틀렸다.**
- 남는 절편 **0.148초**가 AR·MG에서 같다.
- 잔차 최대 **1.12프레임**(프리바티 무버프).

## 이 숫자가 정하지 못하는 것

- **원 측정 조건이 기록되지 않았다.** 무엇을 시작점과 끝점으로 쟀는지(탄창이 빈
  프레임? 재장전 모션 시작? 다음 발이 나간 프레임?)가 남아 있지 않다. 0.148초가
  실제 애니메이션 구간인지 판독 경계의 산물인지는 이 기록으로 가릴 수 없다.
- **차지 무기에서는 상수가 0으로 읽힌다** — 밀크(SR, 강제 재장전 −50% → 정확히
  2.0×1.5) · 센티(RL, 클립 1회가 정확히 파일값 0.5초). 전역 상수는 Fienn 판정이며,
  무기군별 상수가 살아 있는 대안이다. 가르려면 **차지 무기 하나를 무버프로 재장전
  시켜 프레임을 세면** 된다.
- **s > 1에서 고정 구간이 남는지**는 미측정. 엔진은 `max(0, ...)`로 같이 잘라낸다.
```

- [ ] **Step 3: `docs/engine-gaps.md` ★ 항목을 닫는다**

최상단 ★ 항목의 제목을 **✅ 해소 (2026-07-31)**로 바꾸고, "왜 아직 안 넣었나" 문단을 아래로 교체한다(Step 1에서 잰 실제 숫자를 넣는다):

```markdown
**착륙했다 (2026-07-31)** — 합계 1.0150x → <실측>x, ±15% 이내 21/25 → <실측>.
악화는 예상된 것이고 되돌리지 않는다: 역수 형태는 실측이 **기각**했으므로, 기각된
식을 합계가 예뻐 보인다고 유지하는 것이 안티패턴이다. 자세한 근거는
`docs/superpowers/specs/2026-07-31-affine-reload-model-design.md`.
```

그리고 갭 요약표의 해당 행을 취소선 처리한다.

- [ ] **Step 4: 드러난 과대 항을 새 항목으로 연다**

`docs/engine-gaps.md`에 추가:

```markdown
### 21. 평타를 과대평가하는 항이 있다 — 미착수 (2026-07-31, 아핀 재장전이 드러냄)

- **무엇:** 재장전을 실측대로 고치자 합계가 1.0150x → <실측>x로 **멀어졌다**.
  즉 지금까지의 균형은 **너무 느린 재장전 위에서** 맞춰져 있었고, 재장전이 빨라지자
  가려져 있던 과대가 드러났다.
- **어디에 몰리나 (평타 신호):** mast-romantic-maid 1.108 → 1.305 ·
  helm-signature 1.243 → 1.346 · velvet 1.074 → 1.205 · crown 1.177 → 1.225 ·
  little-mermaid 1.038 → 1.111. 반대로 과소였던 rei-ayanami는 0.936 → 1.008로
  **개선**된다. 차지 무기(흑련 0.999 불변)와 차지 위주 덱(덱4·덱5)은 거의 안 움직인다.
  **재장전이 빨라지면 늘어나는 것은 평타 발수뿐이므로, 과대 항은 평타 경로에 있다.**
- **후보:** 평타의 Full Burst 보너스 · 코어 히트 판정 비율 · `rate_of_fire` 상수.
- **같은 형태의 선례:** 택티컬 베어 탄환 환급(항목 12-b)도 흑련을 0.981 → 0.999로
  정확하게 만들면서 합계를 1.011 → 1.015로 밀어냈다. **두 사건이 같은 항을 가리킬
  가능성이 높다.**
```

- [ ] **Step 5: roadmap To-Do**

```markdown
### 아핀 재장전 착륙 후속 (2026-07-31)

- [x] **아핀 재장전 모델 착륙 — 완료.** `파일값 × (1 − s) + 0.148초`, 분기 없는 한 식.
      s=0이 항등이 아니게 되어(무버프 = 파일값 + 0.148) 역수·거울대칭·항등을 고정하던
      테스트 셋은 삭제했다. 실측 6점은 앵커 테스트로 승격.
- [ ] **평타 과대 항을 찾는다 (engine-gap #21).** 재장전 수정이 드러냈다. 악화가
      평타 비중 큰 유닛에 몰리므로 평타 경로를 먼저 본다.
- [ ] **차지 무기에서 고정 구간을 재측정한다.** 밀크·센티가 상수 0으로 읽힌다 —
      무버프 차지 무기 하나의 재장전을 프레임으로 세면 전역/무기군별이 갈린다.
```

- [ ] **Step 6: 결정·통찰 기록**

`/document`로 docs-keeper에 넘긴다 — 기록할 것: (a) 역수 → 아핀 결정과 캘리브레이션
악화를 받아들인 근거, (b) **파일의 `reloadTime`은 "재장전 시간"이 아니라 "버프가
깎는 부분"**이라는 재해석, (c) 전역 상수 판정과 그 두 반례(밀크·센티).

- [ ] **Step 7: 최종 검증**

```bash
cd backend; python -m pytest
```
Expected: 전부 통과, skip 3

- [ ] **Step 8: Commit**

```bash
git add docs/
git commit -m "Record what the affine reload changed, and what it exposed"
```

## Self-Review

**1. Spec coverage**

| 설계 절 | 태스크 |
|---|---|
| 결정 1 (한 식 + `max(0,...)`) | 1 |
| 결정 2 (s=0 항등 아님, 테스트 삭제) | 1 |
| 결정 3 (전역 상수, 밀크 앵커 갱신) | 1 |
| 결정 4 (클립 무변경 + 주석 갱신) | 2 |
| 결정 5 (캘리브레이션 악화 수용) | 3 Step 1·3 |
| 테스트 절 전부 | 1·2 |
| 문서 절 전부 | 3 |

**2. Placeholder scan** — `<실측>`은 Step 1에서 재는 값을 넣으라는 **지시**이며, 그
측정 명령과 기대 형식이 같은 태스크에 있다. 그 외 미완성 표현 없음.

**3. Type consistency** — `RELOAD_FIXED_SECONDS`는 Task 1이 정의하고 1·2가 쓴다.
`reload_time_with_speed(reload_time, reload_speed_percent) -> float`는 시그니처가
안 바뀌므로 9개 호출부와 차지창 계산기는 무변경이다.
