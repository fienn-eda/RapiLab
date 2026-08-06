# 소다의 풀 버스트 확장 + 게이팅된 넉 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 소다: 트윙클링 바니의 `Beginner's Rewards`(skills[1])를 통째로 인코딩한다 — 골든칩 스택에 따른 풀 버스트 지속 확장(+2/+3초 누적)과, 그 확장 상태에 게이팅된 per-shot 넉(52.04% / 137.06% 누적).

**Architecture:** 칩과 FB 길이의 상호 의존은 `simulate_raid`를 고정점까지 반복(상한 4패스)해서 끊는다. `simulate_burst_cycle`은 `{사이클 인덱스 → 델타}` 테이블을 받아 더하기만 하고 조건은 모른다. 조건 평가는 resolution 패스 뒤의 해석기가 하고, 결과를 다음 패스의 입력으로 되먹인다. **조건부 델타를 가진 유닛이 덱에 없으면 정확히 1패스로 끝나 오늘과 바이트 동일하다.**

**Tech Stack:** Python 3, pytest. 백엔드 전용 — 프론트엔드 변경 없음.

## Global Constraints

- 설계 스펙: `docs/superpowers/specs/2026-08-06-soda-full-burst-extension-design.md`. 이 계획과 어긋나면 **스펙이 우선**이다.
- 작업 디렉터리는 `backend/`. 테스트는 항상 `PYTHONIOENCODING=utf-8 python -m pytest ...` (Windows cp949에서 한글·화살표가 깨진다).
- **시작 기준선: 백엔드 1913 passed / 3 skipped.** 매 태스크 끝에서 이 수 이상이어야 하고, 줄면 회귀다.
- TDD: 실패하는 테스트를 먼저 쓰고, 실패를 **눈으로 확인**한 뒤 구현한다.
- **캘리브레이션(1.078x·17/25)과 골든 테스트는 끝까지 불변이어야 한다.** 기록 덱 5개에 소다가 없다. 움직이면 「소다 없는 덱 불변」이 깨진 것이고, 재기준화가 아니라 버그 수정 대상이다.
- 값은 상수로 박지 않고 스킬 슬롯에서 읽는다. `beginners_rewards`의 자연 번호: `dv03`=10(임계 I), `dv04`=2(초 I), `dv06`=20(임계 II), `dv07`=3(초 II), `dv10`=52.04(넉 I), `dv12`=85.02(넉 II 증분).
- 누적 규칙(`Each subsequent effect triggers all effects before it`): 확장 II = 2+3 = **5.0초**, 넉 II = 52.04+85.02 = **137.06%**. 빌더가 누적해서 값에 반영하고 소비 지점에서 다시 더하지 않는다.
- 커밋은 태스크마다. 메시지는 heredoc으로 쓴다(`git commit -F - <<'EOF'`) — Bash 도구에서 PowerShell here-string(`@'…'@`)을 쓰면 `@`가 메시지에 박힌다.

---

## 파일 구조

| 파일 | 역할 | 태스크 |
|---|---|---|
| `app/burst_cycle.py` | 사이클별 FB 길이에 오버라이드를 더한다 (조건은 모름) | 1 |
| `app/squad_engine.py` | `SquadContext`가 창별 확장 단계를 들고 시각으로 답한다 | 2 |
| `app/skill_rules/soda_twinkling_bunny.py` | 확장 tiers 빌더 · 넉 per-shot 빌더 · 매니페스트 | 3, 7 |
| `app/skill_rules/registry.py` | 조건부 델타 빌더 딕셔너리 · 소다 per_shot 항목에 넉 합류 | 4, 7 |
| `app/roster.py` | `conditional_full_burst_deltas` 조립 | 4 |
| `app/raid_simulator.py` | 본문 rename · 수렴 래퍼 · 해석기 · 단계 싣기 | 5, 6, 7 |

---

### Task 1: `simulate_burst_cycle`이 사이클별 오버라이드를 받는다

**Files:**
- Modify: `backend/app/burst_cycle.py:107-116` (시그니처), `:194-202` (길이 계산)
- Test: `backend/tests/test_burst_cycle.py`

**Interfaces:**
- Consumes: 없음 (가장 안쪽 레이어)
- Produces: `simulate_burst_cycle(deck, gauge_charge_time, fight_duration, mode="auto", full_burst_duration_overrides=None, on_battle_start=None, on_tier_fire=None, on_full_burst_enter=None, on_full_burst_end=None)` — `full_burst_duration_overrides`는 `{cycle_index: float}` 또는 `None`. 사이클 인덱스는 0부터.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_burst_cycle.py` 끝에 추가:

```python
def test_full_burst_duration_overrides_lengthen_named_cycles():
    """사이클별 오버라이드는 그 사이클의 창 길이에만 더해진다 - 소다의
    Beginner's Rewards처럼 값이 사이클마다 다른 확장을 위한 자리."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 20.0},
    ]
    events = simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=100.0,
        full_burst_duration_overrides={0: 5.0, 2: 2.0},
    )
    windows = list(zip(
        [e["time"] for e in events if e["type"] == "full_burst_start"],
        [e["time"] for e in events if e["type"] == "full_burst_end"],
    ))
    lengths = [round(end - start, 6) for start, end in windows]
    assert lengths[0] == 15.0    # 10 + 5
    assert lengths[1] == 10.0    # 오버라이드 없음
    assert lengths[2] == 12.0    # 10 + 2


def test_full_burst_duration_overrides_add_to_the_tier3_units_own_delta():
    """오버라이드는 기존 유닛별 델타(이사벨 -5, 모더니아 +5)를 대체하지 않고
    더한다 - 둘은 다른 조건이라 겹쳐 걸린다."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "shortener", "burst_tier": 3, "cooldown": 20.0,
         "full_burst_duration_delta": -5.0},
    ]
    events = simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=60.0,
        full_burst_duration_overrides={0: 5.0},
    )
    start = next(e["time"] for e in events if e["type"] == "full_burst_start")
    end = next(e["time"] for e in events if e["type"] == "full_burst_end")
    assert round(end - start, 6) == 10.0    # 10 - 5 + 5


def test_no_overrides_is_todays_behaviour():
    """None이면 오늘과 같다 - 조건부 델타가 없는 덱의 불변식."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 20.0},
    ]
    with_none = simulate_burst_cycle(deck, 5.0, 100.0, full_burst_duration_overrides=None)
    without = simulate_burst_cycle(deck, 5.0, 100.0)
    assert with_none == without
```

- [ ] **Step 2: 실패를 확인한다**

```
cd backend
PYTHONIOENCODING=utf-8 python -m pytest tests/test_burst_cycle.py -q -k full_burst_duration_overrides
```
기대: `TypeError: simulate_burst_cycle() got an unexpected keyword argument 'full_burst_duration_overrides'`

- [ ] **Step 3: 시그니처에 파라미터를 추가한다**

`app/burst_cycle.py`의 `simulate_burst_cycle` 시그니처를 이렇게 바꾼다(기존 훅 인자는 그대로 두고 새 인자만 추가):

```python
def simulate_burst_cycle(
    deck,
    gauge_charge_time,
    fight_duration,
    mode="auto",
    full_burst_duration_overrides=None,
    on_battle_start=None,
    on_tier_fire=None,
    on_full_burst_enter=None,
    on_full_burst_end=None,
):
```

docstring의 훅 설명 아래에 한 문단 추가:

```python
    """... (기존 훅 설명 그대로) ...

    `full_burst_duration_overrides`는 {사이클 인덱스: 초}로, 그 사이클의 창
    길이에 더해진다. 이 스케줄러는 그 값이 어디서 왔는지 모른다 - 값이
    사이클마다 달라지는 확장(소다의 Beginner's Rewards는 골든칩 스택에 따라
    +0/+2/+5초)은 자원 상태를 봐야 정해지는데, 자원은 이 스케줄러가 창을
    확정한 뒤에야 채워지기 때문이다. raid_simulator가 고정점까지 반복하며
    이 테이블을 갱신한다.
    """
```

- [ ] **Step 4: 길이 계산에 반영한다**

`app/burst_cycle.py:198-201`의 `duration` 계산을 바꾼다:

```python
        duration = max(
            MIN_FULL_BURST_DURATION,
            FULL_BURST_DURATION
            + tier3_member.get("full_burst_duration_delta", 0.0)
            + (full_burst_duration_overrides or {}).get(cycle_index, 0.0),
        )
```

`cycle_index`는 이미 이 루프의 지역변수다(`self_stun` 계산이 쓴다) — 새로 만들지 말고 그대로 쓴다.

- [ ] **Step 5: 통과를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_burst_cycle.py -q
```
기대: 전부 PASS

- [ ] **Step 6: 전체 스위트로 회귀가 없는지 본다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1916 passed / 3 skipped** (기준선 1913 + 신규 3)

- [ ] **Step 7: 커밋**

```bash
git add backend/app/burst_cycle.py backend/tests/test_burst_cycle.py
git commit -F - <<'EOF'
Let simulate_burst_cycle take a per-cycle Full Burst length override

The scheduler already reads a per-slug delta off the Burst 3 that opened the
cycle (Isabel -5, Modernia +5). Soda's extension is not that shape: its value
depends on a resource whose fills are only known after this scheduler has
already fixed every window, so it cannot be a constant on the member.

This adds a {cycle index: seconds} table the scheduler adds and otherwise
knows nothing about. Passing None is byte-identical to today.
EOF
```

---

### Task 2: `SquadContext`가 창별 확장 단계를 들고 있는다

**Files:**
- Modify: `backend/app/squad_engine.py` (`SquadContext.__init__` 끝, 그리고 `record_burst_time` 근처에 조회 메서드)
- Test: `backend/tests/test_squad_engine.py`

**Interfaces:**
- Consumes: 없음
- Produces: `context.full_burst_extension_stages: list[tuple[float, float, dict[str, int]]]` (start, end, {슬러그: 단계}) · `context.full_burst_extension_stage(time: float, slug: str) -> int` — 그 창에서 그 슬러그가 도달한 단계, 없으면 0.

단계를 **슬러그별로** 싣는 것은 확장을 주는 유닛이 둘 이상인 덱에서 각자의 게이팅 넉이 자기 단계를 봐야 하기 때문이다. 오늘 소비자는 소다 하나뿐이라 값은 늘 한 개짜리 딕셔너리지만, 「창 전체의 단계」라는 개념은 애초에 존재하지 않는다 — 초는 합산되고 단계는 유닛마다 다르다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_squad_engine.py` 끝에 추가:

```python
def test_full_burst_extension_stage_reads_the_window_a_time_falls_in():
    """소다의 per-shot 넉이 자기 샷의 사이클 확장 단계를 묻는 자리. 단계는
    창마다 다르고(칩이 줄면 내려간다), 창 밖은 0이다."""
    context = SquadContext([SquadMember("soda", burst_tier=3, element="Iron")])
    assert context.full_burst_extension_stage(5.0, "soda") == 0   # 아직 아무것도 안 실림

    context.full_burst_extension_stages = [(2.0, 17.0, {"soda": 2}), (25.0, 37.0, {"soda": 1})]
    assert context.full_burst_extension_stage(2.0, "soda") == 2     # 창 시작 포함
    assert context.full_burst_extension_stage(16.9, "soda") == 2
    assert context.full_burst_extension_stage(17.0, "soda") == 0    # 창 끝 배제
    assert context.full_burst_extension_stage(20.0, "soda") == 0    # 창 사이
    assert context.full_burst_extension_stage(30.0, "soda") == 1
    assert context.full_burst_extension_stage(100.0, "soda") == 0   # 마지막 창 뒤
    assert context.full_burst_extension_stage(5.0, "someone-else") == 0  # 다른 유닛
```

- [ ] **Step 2: 실패를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_squad_engine.py -q -k full_burst_extension_stage
```
기대: `AttributeError: 'SquadContext' object has no attribute 'full_burst_extension_stage'`

- [ ] **Step 3: 구현한다**

`app/squad_engine.py`의 `SquadContext.__init__` 끝(`self.resource_resets` 선언 바로 다음)에 추가:

```python
        # 사이클별 Full Burst 확장 단계 [(start, end, {슬러그: 단계})]. 초가 아니라
        # 단계를 싣는 것은 소비자(소다의 per-shot 넉)가 "II단계인가"를 묻지
        # "5.0초인가"를 묻지 않기 때문 - 초에서 단계를 역추론하면 값이 우연히
        # 겹치는 날 조용히 틀린다. 슬러그별인 것은 초가 합산되는 것과 달리 단계는
        # 유닛마다 다르기 때문. raid_simulator가 창을 만들 때 채운다.
        self.full_burst_extension_stages: list[tuple[float, float, dict[str, int]]] = []
```

같은 클래스에 메서드를 추가한다(`record_burst_time` 바로 위):

```python
    def full_burst_extension_stage(self, time: float, slug: str) -> int:
        """`time`이 속한 Full Burst 창에서 `slug`가 도달한 확장 단계 (0 = 없음).
        창은 [start, end) 반열림이라 창 끝의 샷은 어느 창에도 안 든다."""
        for start, end, stages in self.full_burst_extension_stages:
            if start <= time < end:
                return stages.get(slug, 0)
        return 0
```

- [ ] **Step 4: 통과를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_squad_engine.py -q
```
기대: 전부 PASS

- [ ] **Step 5: 전체 스위트**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1917 passed / 3 skipped**

- [ ] **Step 6: 커밋**

```bash
git add backend/app/squad_engine.py backend/tests/test_squad_engine.py
git commit -F - <<'EOF'
Give SquadContext a per-window Full Burst extension stage

Soda's per-shot nuke is gated on "while in Time Extension I/II state", so a
shot needs to know which stage its own cycle reached. Stored as a stage index
rather than the seconds it bought: the consumer asks "is this tier II", and
deriving that back from 5.0 seconds would break silently the day another
source adds up to the same number.
EOF
```

---

### Task 3: 소다의 확장 tiers 빌더와 매니페스트

**Files:**
- Modify: `backend/app/skill_rules/soda_twinkling_bunny.py` (`SKILL_VALUE_MANIFESTS`, 새 빌더)
- Test: `backend/tests/test_skill_rules_soda_twinkling_bunny.py`

**Interfaces:**
- Consumes: 없음
- Produces: `build_beginners_rewards_full_burst_delta(values) -> dict` — `{"resource": "chip", "cap": 50, "tiers": [(10, 2.0), (20, 5.0)]}`. `tiers`는 (임계, 누적 초) 오름차순.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

먼저 `backend/tests/test_skill_rules_soda_twinkling_bunny.py`의 `SODA_VALUES`에 세 번째 키를 추가한다(기존 두 키는 그대로):

```python
    "beginners_rewards": {
        "description_value_01": "3", "description_value_02": "1",
        "description_value_03": "10", "description_value_04": "2",
        "description_value_05": "2", "description_value_06": "20",
        "description_value_07": "3", "description_value_08": "1",
        "description_value_09": "1", "description_value_10": "52.04",
        "description_value_11": "2", "description_value_12": "85.02",
    },
```

임포트에 새 빌더를 추가하고:

```python
from app.skill_rules.soda_twinkling_bunny import (
    build_beginners_rewards_full_burst_delta,
    build_golden_chip_resources,
    build_lucky_golden_chip_per_shot_rules,
    build_onward_soda_resource_gated_buffs,
    onward_soda_burst_percent,
)
```

테스트를 추가한다:

```python
def test_beginners_rewards_full_burst_tiers_are_cumulative():
    """"Each subsequent effect triggers all effects before it" - 20스택 이상은
    Time Extension I(+2초)과 II(+3초)를 함께 받아 +5초다 (Fienn 실측: 풀 버스트
    15초 = 10 + 2 + 3)."""
    spec = build_beginners_rewards_full_burst_delta(SODA_VALUES)
    assert spec["resource"] == "chip"
    assert spec["cap"] == 50
    assert spec["tiers"] == [(10.0, 2.0), (20.0, 5.0)]


def test_beginners_rewards_reads_thresholds_and_seconds_from_slots():
    """상수로 박지 않는다 - 스킬 레벨이 바뀌면 값도 따라가야 한다."""
    lower = {
        **SODA_VALUES,
        "beginners_rewards": {**SODA_VALUES["beginners_rewards"],
                              "description_value_03": "8", "description_value_04": "1",
                              "description_value_06": "16", "description_value_07": "2"},
    }
    spec = build_beginners_rewards_full_burst_delta(lower)
    assert spec["tiers"] == [(8.0, 1.0), (16.0, 3.0)]
```

- [ ] **Step 2: 실패를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_soda_twinkling_bunny.py -q -k beginners_rewards
```
기대: `ImportError: cannot import name 'build_beginners_rewards_full_burst_delta'`

- [ ] **Step 3: 빌더를 구현한다**

`app/skill_rules/soda_twinkling_bunny.py`의 `build_golden_chip_resources` 위에 추가:

```python
def build_beginners_rewards_full_burst_delta(values):
    """Beginner's Rewards의 첫 불릿: Burst Stage 3 진입 시, 골든칩 스택에 따라
    풀 버스트 지속시간이 늘어난다(10+ 이면 +2초, 20+ 이면 거기에 +3초 더).

    누적이다 - "Each subsequent effect triggers all effects before it"이고,
    Fienn의 실측이 그것을 확인한다(풀 버스트 15초 = 10 + 2 + 3,
    docs/measurements/soda-golden-chip-in-play.md). 누적을 여기서 값에 반영해
    소비 지점이 다시 더하지 않게 한다.

    "Affects all allies"이므로 그녀가 그 사이클의 Burst 3일 필요가 없다 -
    덱에 있고 칩이 임계 위면 누가 창을 열든 걸린다."""
    rewards = values["beginners_rewards"]
    stage1_threshold = float(rewards["description_value_03"])
    stage1_seconds = float(rewards["description_value_04"])
    stage2_threshold = float(rewards["description_value_06"])
    stage2_seconds = float(rewards["description_value_07"])

    return {
        "resource": "chip",
        "cap": int(float(values["lucky_golden_chip"]["description_value_04"])),
        "tiers": [
            (stage1_threshold, stage1_seconds),
            (stage2_threshold, stage1_seconds + stage2_seconds),
        ],
    }
```

- [ ] **Step 4: 통과를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_soda_twinkling_bunny.py -q
```
기대: 전부 PASS

- [ ] **Step 5: 매니페스트에 `beginners_rewards`를 추가한다**

`app/skill_rules/soda_twinkling_bunny.py`의 `SKILL_VALUE_MANIFESTS`에서 `keys`에 한 줄 추가:

```python
        "keys": {
            "lucky_golden_chip": ("skills", 0),
            "beginners_rewards": ("skills", 1),
            "onward_soda": ("skills", 2),
        },
```

`drop_tokens`는 **일단 건드리지 않는다** — 다음 스텝의 하네스가 필요 여부를 알려준다.

새 키를 매니페스트에 추가하면 픽스처 쪽에도 짝이 있어야 한다.
`tests/test_skill_value_assembly.py`는 각 키의 정답 픽스처를
`getattr(fixtures_module, manifest.get("fixtures", {}).get(key, key.upper()))`로
찾는다 - `fixtures` 오버라이드가 없으면 `beginners_rewards`는 모듈에서
`BEGINNERS_REWARDS`라는 이름의 속성을 찾는다.
`backend/tests/test_skill_rules_soda_twinkling_bunny.py` 끝에 이미 있는

```python
LUCKY_GOLDEN_CHIP = SODA_VALUES["lucky_golden_chip"]
ONWARD_SODA = SODA_VALUES["onward_soda"]
```

옆에 같은 패턴으로 한 줄을 추가한다:

```python
BEGINNERS_REWARDS = SODA_VALUES["beginners_rewards"]
```

이 별칭이 없으면 Step 6은 슬롯 번호 불일치가 아니라 `AttributeError`로 실패하고,
그 실패는 `drop_tokens`로 고칠 수 있는 종류가 아니다 - 하네스나 매니페스트가
아니라 픽스처 별칭이 아예 없는 게 원인이기 때문이다.

- [ ] **Step 6: 조립 하네스를 돌린다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_value_assembly.py -q -k soda
```

통과하면 그대로 둔다. 어긋나면 하네스가 슬롯 번호 차이를 출력하므로, **`drop_tokens`로만** 맞춘다 — 픽스처(`SODA_VALUES`)나 하네스 자체는 절대 고치지 않는다(위 Global Constraints).

- [ ] **Step 7: 전체 스위트**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1919 passed / 3 skipped**

- [ ] **Step 8: 커밋**

```bash
git add backend/app/skill_rules/soda_twinkling_bunny.py backend/tests/test_skill_rules_soda_twinkling_bunny.py
git commit -F - <<'EOF'
Build Soda's Full Burst extension tiers from her skill slots

Thresholds (10/20) and seconds (2/3) come from the skill data rather than
being written into the code, so a different skill level follows. The tiers are
stored cumulative - 20+ stacks is +5s, not +3s - because the skill says each
stage triggers the ones before it, and Fienn's in-game reading confirms it
(Full Burst 15s = 10 + 2 + 3).
EOF
```

---

### Task 4: 레지스트리와 로스터 배선

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (임포트, 새 빌더 딕셔너리 + 접근자), `backend/app/roster.py:88-254`
- Test: `backend/tests/test_roster.py`

**Interfaces:**
- Consumes: Task 3의 `build_beginners_rewards_full_burst_delta`
- Produces: `registry.get_conditional_full_burst_delta(slug, skill_values) -> dict | None` · `assemble_simulation_inputs(...)["conditional_full_burst_deltas"] -> {slug: spec}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_roster.py` 끝에 추가:

```python
def test_assemble_wires_sodas_conditional_full_burst_delta():
    """조건부 FB 델타는 member가 아니라 별도 딕셔너리로 나간다 - burst_cycle이
    아니라 resolution 뒤의 해석기가 읽기 때문."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in ("liter", "crown", "soda-twinkling-bunny")
    ]
    specs, excluded = load_roster(states)
    assert not excluded
    inputs = assemble_simulation_inputs(specs)

    deltas = inputs["conditional_full_burst_deltas"]
    assert set(deltas) == {"soda-twinkling-bunny"}
    assert deltas["soda-twinkling-bunny"]["resource"] == "chip"
    assert deltas["soda-twinkling-bunny"]["tiers"] == [(10.0, 2.0), (20.0, 5.0)]
    # member에는 아무것도 안 붙는다
    soda_member = next(m for m in inputs["deck"] if m["slug"] == "soda-twinkling-bunny")
    assert "conditional_full_burst_delta" not in soda_member


def test_assemble_leaves_conditional_deltas_empty_without_such_a_unit():
    """소다 없는 덱은 빈 딕셔너리 - 이게 '1패스로 끝난다'의 출발점이다."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in ("liter", "crown", "modernia")
    ]
    specs, _ = load_roster(states)
    assert assemble_simulation_inputs(specs)["conditional_full_burst_deltas"] == {}
```

`test_roster.py` 상단 임포트에 `assemble_simulation_inputs`가 없으면 추가한다.

- [ ] **Step 2: 실패를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_roster.py -q -k conditional_full_burst
```
기대: `KeyError: 'conditional_full_burst_deltas'`

- [ ] **Step 3: 레지스트리에 빌더를 등록한다**

`app/skill_rules/registry.py`의 소다 임포트 블록(`from app.skill_rules.soda_twinkling_bunny import (` — 298줄 근처)에 새 빌더를 추가한다:

```python
from app.skill_rules.soda_twinkling_bunny import (
    build_beginners_rewards_full_burst_delta,
    build_golden_chip_resources,
    build_lucky_golden_chip_per_shot_rules,
    build_onward_soda_resource_gated_buffs,
    onward_soda_burst_percent,
)
```
(기존 임포트 이름은 파일에 있는 그대로 두고 새 줄만 알파벳 순서에 맞춰 끼워 넣는다.)

`FULL_BURST_DURATION_DELTA`와 `get_full_burst_duration_delta` 바로 아래에 추가:

```python
# 자기 버스트가 아니라 "덱에 있고 자원 조건이 맞으면" 풀 버스트를 늘리는 유닛.
# FULL_BURST_DURATION_DELTA는 슬러그당 상수라 이 모양을 담을 수 없다 - 소다의
# 확장은 골든칩 스택에 따라 사이클마다 +0/+2/+5초로 달라지고, 원문이
# "entering Burst Stage 3 / Affects all allies"라 그녀가 그 사이클의 Burst 3일
# 필요도 없다.
_CONDITIONAL_FULL_BURST_DELTA_BUILDERS = {
    "soda-twinkling-bunny": lambda sv: build_beginners_rewards_full_burst_delta(sv),
}


def get_conditional_full_burst_delta(slug, skill_values):
    """이 유닛이 자원 조건에 따라 풀 버스트를 늘리는가 (대부분 None)."""
    builder = _CONDITIONAL_FULL_BURST_DELTA_BUILDERS.get(slug)
    return builder(skill_values) if builder else None
```

- [ ] **Step 4: 로스터에서 조립한다**

`app/roster.py`의 임포트(29줄 근처, `get_full_burst_duration_delta` 옆)에 추가:

```python
    get_conditional_full_burst_delta,
```

`assemble_simulation_inputs`의 지역 딕셔너리 선언부(88-108줄)에 한 줄 추가:

```python
    conditional_full_burst_deltas = {}
```

`skill_values`가 만들어진 뒤의 배선 블록(`per_shot_rule = get_per_shot_rules(...)` 근처)에 추가:

```python
        conditional_full_burst = get_conditional_full_burst_delta(spec.slug, skill_values)
        if conditional_full_burst is not None:
            conditional_full_burst_deltas[spec.slug] = conditional_full_burst
```

`return {...}`(233줄)에 한 줄 추가:

```python
        "conditional_full_burst_deltas": conditional_full_burst_deltas,
```

- [ ] **Step 5: `simulate_raid`가 새 인자를 받아 두게 한다 (아직 쓰지는 않는다)**

`assemble_simulation_inputs`의 출력은 `evaluate_deck`에서 `simulate_raid(**inputs, ...)`로 펼쳐지므로, 키 하나가 늘면 `simulate_raid`가 그것을 받을 줄 알아야 한다. 받지 않으면 `test_assembled_inputs_run_through_simulate_raid`가 `TypeError`로 깨진다 — **빨간 커밋을 남기지 않는다.**

`app/raid_simulator.py`의 `simulate_raid` 시그니처 끝에 한 줄 추가한다(Task 5의 rename이 이것을 그대로 물려받는다):

```python
    ammo_rounds_per_shot=None,
    conditional_full_burst_deltas=None,
):
```

그리고 정규화 블록에:

```python
    conditional_full_burst_deltas = conditional_full_burst_deltas or {}
```

이 태스크에서는 **읽기만 하고 쓰지 않는다.** 값을 소비하는 것은 Task 6의 해석기다.

- [ ] **Step 6: 전체 스위트를 돌린다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1921 passed / 3 skipped** — 전부 초록. 빨간 것이 하나라도 있으면 배선이 잘못된 것이니 다음으로 넘어가지 않는다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/app/roster.py backend/app/raid_simulator.py backend/tests/test_roster.py
git commit -F - <<'EOF'
Wire Soda's conditional Full Burst delta through the roster

The engine does not import the registry (burst_cycle imports nothing at all),
so this spec travels the same way resource_specs and resource_gated_buffs do:
assembled by roster and handed to simulate_raid as an argument.

It does NOT go on the member dict. The existing full_burst_duration_delta
lives there because burst_cycle reads it directly; this one is read by the
resolver that runs after the resource pass, which is a different consumer.

simulate_raid accepts the argument here and ignores it - assemble's output is
splatted into it, so the parameter has to exist for the suite to stay green.
The resolver that reads it comes two commits later.
EOF
```

---

### Task 5: `simulate_raid`를 얇은 래퍼로 분리한다 (동작 불변)

**Files:**
- Modify: `backend/app/raid_simulator.py:487-1542`
- Test: 기존 전체 스위트가 회귀 테스트다

**Interfaces:**
- Consumes: Task 2의 `context.full_burst_extension_stages`, Task 4의 `conditional_full_burst_deltas` 인자
- Produces: `simulate_raid(deck, **kwargs) -> dict` (공개 API, 시그니처 호환) · `_simulate_raid_once(deck, ..., conditional_full_burst_deltas=None, full_burst_stage_overrides=None) -> tuple[dict, dict]` · `_stage_seconds(stage_table, specs) -> dict[int, float]`

**이 태스크는 기능을 추가하지 않는다.** 해석기가 아직 없어 오버라이드가 항상 비어 있으므로, 순수 구조 변경이고 전체 스위트가 초록으로 남는 것이 유일한 성공 기준이다.

**인자는 단계 테이블이지 초 테이블이 아니다.** `_simulate_raid_once`가 받는 것은 `{사이클: {슬러그: 단계}}`이고, 스케줄러에 넘기기 직전에 `_stage_seconds`가 초로 바꾼다. 두 표현을 한 이름으로 섞으면 Task 6에서 조용히 어긋난다.

- [ ] **Step 1: 본문을 rename한다**

`app/raid_simulator.py`에서 `def simulate_raid(` 를 `def _simulate_raid_once(` 로 바꾼다. 시그니처 끝에 두 인자를 추가한다 — `conditional_full_burst_deltas=None`(Task 4가 넘기는 것)과 `full_burst_stage_overrides=None`(래퍼가 넘기는 것):

```python
def _simulate_raid_once(
    deck,
    rules_by_slug,
    burst_damage_percents,
    base_stats,
    enemy_def,
    gauge_charge_time,
    fight_duration,
    mode="auto",
    ...  # 기존 인자 전부 그대로
    ammo_rounds_per_shot=None,
    conditional_full_burst_deltas=None,
    full_burst_stage_overrides=None,
):
```

`conditional_full_burst_deltas=None`은 Task 4가 이미 넣어 뒀다 — 여기서는 `full_burst_stage_overrides=None`만 새로 추가된다. 정규화 블록에도 한 줄만 더한다:

```python
    full_burst_stage_overrides = full_burst_stage_overrides or {}
```

- [ ] **Step 2: 단계 → 초 변환기를 쓴다**

`_simulate_raid_once` 위에 추가:

```python
def _stage_seconds(stage_table, conditional_full_burst_deltas):
    """{사이클: {슬러그: 단계}}를 burst_cycle이 쓰는 {사이클: 초}로 바꾼다.

    단계는 유닛별이고 초는 창 하나에 하나뿐이라 합산한다 - 확장을 주는 유닛이
    둘 있는 덱이라면 창이 둘 다 만큼 길어진다. 오늘 소비자는 소다 하나뿐이라
    합이 곧 그녀 몫이다."""
    seconds = {}
    for cycle_index, stages in stage_table.items():
        total = sum(
            conditional_full_burst_deltas[slug]["tiers"][stage - 1][1]
            for slug, stage in stages.items()
        )
        if total:
            seconds[cycle_index] = total
    return seconds
```

- [ ] **Step 3: 오버라이드를 스케줄러에 넘기고 단계를 context에 싣는다**

`simulate_burst_cycle` 호출(900줄 근처)에 인자를 추가한다:

```python
    events = simulate_burst_cycle(
        deck,
        gauge_charge_time,
        fight_duration,
        mode,
        full_burst_duration_overrides=_stage_seconds(
            full_burst_stage_overrides, conditional_full_burst_deltas
        ),
        on_battle_start=on_battle_start,
        on_tier_fire=on_tier_fire,
        on_full_burst_enter=on_full_burst_enter,
        on_full_burst_end=on_full_burst_end,
    )
```

`context.full_burst_windows = full_burst_windows`(911줄 근처) 바로 다음에 추가:

```python
    # 이번 패스가 받은 단계 테이블을 창에 붙여 context에 싣는다 - 창 길이와 단계가
    # 같은 패스 안에서 항상 같은 출처를 갖도록. per-shot 소비자(소다의 Beginner's
    # Rewards 넉)가 자기 샷이 속한 창의 자기 단계를 여기서 읽는다.
    context.full_burst_extension_stages = [
        (start, end, full_burst_stage_overrides.get(index, {}))
        for index, (start, end) in enumerate(full_burst_windows)
    ]
```

- [ ] **Step 4: 반환을 튜플로 바꾼다**

파일 끝(1538줄)의 반환을 바꾼다. 해석기는 아직 없으므로 **빈 딕셔너리**를 돌려준다(Task 6이 채운다):

```python
    return {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }, {}
```

- [ ] **Step 5: 래퍼를 추가한다**

`_stage_seconds` **바로 위**에 새 `simulate_raid`를 쓴다:

```python
# 조건부 풀 버스트 확장(소다의 Beginner's Rewards)이 있는 덱에서 고정점을 찾는
# 패스 수의 상한. 하한(확장 없음)에서 출발해 위로 가므로 보통 2~3패스면 끝나고,
# 이 상한은 수렴하지 않는 조합에서 무한히 도는 것을 막는 안전장치다.
MAX_FULL_BURST_PASSES = 4


def simulate_raid(deck, **kwargs):
    """한 번의 레이드 시뮬레이션. 대부분의 덱에서는 `_simulate_raid_once`를 정확히
    한 번 부르는 것과 같다.

    풀 버스트 창 길이가 자원 상태에 달린 유닛(소다: 트윙클링 바니)이 덱에 있으면
    고정점까지 반복한다: 창 길이가 그 사이클 진입 시점의 골든칩으로 정해지는데,
    칩은 창 안의 사격으로 차고, 사격은 창이 정해져야 존재한다. 시간 순서로는
    인과가 한 방향이지만(사이클 k의 판정은 k-1까지의 샷만 본다) 이 엔진은
    스케줄러를 통째로 먼저 돌리므로 패스 단위로 같은 답에 도달한다.

    그런 유닛이 없으면 해석기가 빈 딕셔너리를 돌려주고 첫 패스에서 종료한다 -
    결과도 비용도 오늘과 같다.
    """
    overrides = {}
    result = None
    for attempt in range(MAX_FULL_BURST_PASSES):
        result, resolved = _simulate_raid_once(
            deck, **kwargs, full_burst_stage_overrides=overrides
        )
        if resolved == overrides:
            result["full_burst_passes"] = {"passes": attempt + 1, "converged": True}
            return result
        overrides = resolved
    result["full_burst_passes"] = {"passes": MAX_FULL_BURST_PASSES, "converged": False}
    return result
```

- [ ] **Step 6: `result` 딕셔너리를 통째로 비교하는 테스트가 없는지 확인한다**

```
PYTHONIOENCODING=utf-8 grep -rn "== {" tests/ | grep -i "result\|simulate_raid" | head
```
비교하는 테스트가 있으면 `full_burst_passes` 키가 그것을 깬다. 있으면 그 테스트가 무엇을 지키려는지 읽고, **키 추가 대신** 그 테스트가 보는 부분만 비교하도록 좁힌다(테스트를 지우지 않는다).

- [ ] **Step 7: 전체 스위트 — 이것이 이 태스크의 성공 기준이다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1921 passed / 3 skipped** (Task 4에서 빨갛던 `test_assembled_inputs_run_through_simulate_raid` 포함해 전부 초록)

여기서 무엇이든 깨지면 rename이 뭔가를 놓친 것이다. 다음 태스크로 넘어가지 말고 고친다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/raid_simulator.py
git commit -F - <<'EOF'
Split simulate_raid into a fixed-point wrapper and one pass

Pure restructuring: the body becomes _simulate_raid_once and returns
(result, resolved), and a thin simulate_raid loops until the resolved
per-cycle Full Burst overrides stop changing.

The resolver is not written yet, so every deck resolves to {} on the first
pass and this is exactly today's behaviour with one extra key in the result.
The next commit gives the resolver something to say.
EOF
```

---

### Task 6: 해석기 — 진입 시점 칩에서 사이클별 단계를 읽는다

**Files:**
- Modify: `backend/app/raid_simulator.py` (`_resolve_conditional_fb_deltas` 신설, `_simulate_raid_once`의 반환과 창 생성부)
- Test: `backend/tests/test_raid_simulator.py`

**Interfaces:**
- Consumes: Task 2의 `context.full_burst_extension_stages`, Task 4의 `conditional_full_burst_deltas`
- Produces: `_resolve_conditional_fb_deltas(context, events, specs) -> dict[int, dict[str, int]]` — `{사이클 인덱스: {슬러그: 단계 인덱스}}`. 단계 0은 담지 않는다(빈 사이클은 키 자체가 없어야 `{}`와 비교가 성립한다).
- `_simulate_raid_once`는 그 단계 테이블을 (a) `burst_cycle`용 초 테이블로 바꿔 다음 패스에 쓰고, (b) `context.full_burst_extension_stages`에 실어 같은 패스의 per-shot 소비자가 읽게 한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_raid_simulator.py` 끝에 추가:

```python
def test_conditional_full_burst_delta_reads_the_chip_before_the_burst_spends_it():
    """소다 본인이 그 사이클의 Burst 3이면, 같은 순간에 Beginner's Rewards가
    칩을 읽고 Onward Soda!가 17을 쓴다. 판정은 소비 전이다 - 같은 순간의 ATK
    게이트(>=30)가 이미 소비 전을 읽으므로 둘이 같은 값을 봐야 한다.

    칩 28로 진입하면 소비 전 판정은 II단계(>=20), 소비 후라면 11이라 I단계다."""
    from app.raid_simulator import _resolve_conditional_fb_deltas
    from app.squad_engine import SquadContext, SquadMember

    context = SquadContext([SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron")])
    # 전투 시작 28, t=10.0에 버스트가 17을 써서 11로
    context.reset_resource("soda-twinkling-bunny", "chip", 0.0, 0.0, 28.0)
    context.reset_resource("soda-twinkling-bunny", "chip", 10.0, 28.0, 11.0)
    events = [{"type": "burst", "tier": 3, "slug": "soda-twinkling-bunny", "time": 10.0}]
    specs = {"soda-twinkling-bunny": {"resource": "chip", "cap": 50,
                                      "tiers": [(10.0, 2.0), (20.0, 5.0)]}}

    assert _resolve_conditional_fb_deltas(context, events, specs) == {0: {"soda-twinkling-bunny": 2}}


def test_conditional_full_burst_delta_is_empty_below_the_lowest_threshold():
    from app.raid_simulator import _resolve_conditional_fb_deltas
    from app.squad_engine import SquadContext, SquadMember

    context = SquadContext([SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron")])
    context.reset_resource("soda-twinkling-bunny", "chip", 0.0, 0.0, 9.0)
    events = [{"type": "burst", "tier": 3, "slug": "soda-twinkling-bunny", "time": 10.0}]
    specs = {"soda-twinkling-bunny": {"resource": "chip", "cap": 50,
                                      "tiers": [(10.0, 2.0), (20.0, 5.0)]}}

    assert _resolve_conditional_fb_deltas(context, events, specs) == {}


def test_conditional_full_burst_delta_applies_when_another_unit_opened_the_cycle():
    """"Affects all allies" - 소다가 그 사이클의 Burst 3가 아니어도 걸린다."""
    from app.raid_simulator import _resolve_conditional_fb_deltas
    from app.squad_engine import SquadContext, SquadMember

    context = SquadContext([
        SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron"),
        SquadMember("other-b3", burst_tier=3, element="Iron"),
    ])
    context.reset_resource("soda-twinkling-bunny", "chip", 0.0, 0.0, 50.0)
    events = [{"type": "burst", "tier": 3, "slug": "other-b3", "time": 10.0}]
    specs = {"soda-twinkling-bunny": {"resource": "chip", "cap": 50,
                                      "tiers": [(10.0, 2.0), (20.0, 5.0)]}}

    assert _resolve_conditional_fb_deltas(context, events, specs) == {0: {"soda-twinkling-bunny": 2}}


def test_no_conditional_specs_resolves_empty():
    """소다 없는 덱의 불변식 출발점."""
    from app.raid_simulator import _resolve_conditional_fb_deltas
    from app.squad_engine import SquadContext, SquadMember

    context = SquadContext([SquadMember("a", burst_tier=3, element="Iron")])
    events = [{"type": "burst", "tier": 3, "slug": "a", "time": 10.0}]
    assert _resolve_conditional_fb_deltas(context, events, {}) == {}
```

- [ ] **Step 2: 실패를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_raid_simulator.py -q -k conditional_full_burst
```
기대: `ImportError: cannot import name '_resolve_conditional_fb_deltas'`

- [ ] **Step 3: 해석기를 구현한다**

`app/raid_simulator.py`의 `MAX_FULL_BURST_PASSES` 정의 아래에 추가:

```python
# 자원 조회를 리셋 "직전"으로 밀어내는 폭. resource_count는 조회 시각과 같은
# 시각의 리셋을 베이스라인으로 쓰므로, 그냥 버스트 시각을 물으면 소비 후 값이
# 돌아온다. 이 폭이면 같은 순간의 리셋만 벗어나고 직전 fill은 그대로 센다.
_PRE_BURST_EPSILON = 1e-6


def _resolve_conditional_fb_deltas(context, events, conditional_full_burst_deltas):
    """사이클별 {슬러그: 확장 단계}. 단계는 그 사이클의 Burst 3이 발동한 순간,
    자원이 소비되기 직전의 값으로 정해진다.

    원문이 "Activates when entering Burst Stage 3 / Affects all allies"이므로
    스펙 보유자가 그 사이클의 Burst 3일 필요가 없다 - 덱에 있고 조건이 맞으면
    누가 창을 열든 걸린다. 판정 시각도 `full_burst_start`가 아니라 버스트
    발동 시각이다(둘은 FULL_BURST_OPEN_DELAY만큼 떨어져 있다).

    단계 0은 담지 않는다: 아무 유닛도 조건을 못 넘긴 사이클은 키 자체가 없어야
    "빈 딕셔너리"와의 비교로 고정점을 판정할 수 있다."""
    resolved = {}
    if not conditional_full_burst_deltas:
        return resolved
    tier3_times = [e["time"] for e in events if e.get("type") == "burst" and e.get("tier") == 3]
    for cycle_index, fire_time in enumerate(tier3_times):
        stages = {}
        for slug, spec in conditional_full_burst_deltas.items():
            count = context.resource_count(
                slug, spec["resource"], fire_time - _PRE_BURST_EPSILON, spec["cap"]
            )
            stage = 0
            for index, (threshold, _seconds) in enumerate(spec["tiers"], start=1):
                if count >= threshold:
                    stage = index
            if stage:
                stages[slug] = stage
        if stages:
            resolved[cycle_index] = stages
    return resolved
```

- [ ] **Step 4: 통과를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_raid_simulator.py -q -k conditional_full_burst
```
기대: 4건 PASS

- [ ] **Step 5: 판정 시점을 뮤테이션으로 확인한다**

`_PRE_BURST_EPSILON`을 임시로 `0.0`으로 바꾸고 위 명령을 다시 돌린다.
기대: `test_conditional_full_burst_delta_reads_the_chip_before_the_burst_spends_it`가 **FAIL**(단계 2 대신 1). 확인했으면 `1e-6`으로 되돌린다.

이 스텝은 건너뛰지 않는다 — 테스트가 실제로 소비 전/후를 가르는지는 깨봐야 안다.

- [ ] **Step 6: `_simulate_raid_once`가 해석 결과를 반환한다**

Task 5가 이미 단계 테이블을 받아 초로 바꾸고(`_stage_seconds`) context에 싣는 배선을 끝내 놨다. 남은 것은 반환의 `{}`를 실제 해석 결과로 바꾸는 한 줄이다:

```python
    return {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }, _resolve_conditional_fb_deltas(context, events, conditional_full_burst_deltas)
```

- [ ] **Step 7: 불변식 테스트를 쓴다**

`backend/tests/test_raid_simulator.py`에 추가:

```python
def test_deck_without_a_conditional_unit_resolves_in_exactly_one_pass():
    """이 설계에서 가장 중요한 성질: 소다가 없으면 오늘과 같다."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    base_stats = {m["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for m in deck}
    sg = {"weapon": "SG", "damage_percent": 10.0, "max_ammo": 1000,
          "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0}
    result = simulate_raid(
        deck, {m["slug"]: [] for m in deck}, burst_damage_percents={},
        base_stats=base_stats, enemy_def=0, gauge_charge_time=5.0,
        fight_duration=60.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={m["slug"]: sg for m in deck},
    )
    assert result["full_burst_passes"] == {"passes": 1, "converged": True}
```

- [ ] **Step 8: 전체 스위트**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1926 passed / 3 skipped**. 캘리브레이션·골든 테스트가 깨지면 불변식이 무너진 것이니 다음으로 넘어가지 않는다.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/raid_simulator.py backend/tests/test_raid_simulator.py
git commit -F - <<'EOF'
Resolve Soda's Full Burst extension stage from the pre-spend chip

The stage for a cycle is read at the instant that cycle's Burst 3 fires, one
epsilon before it - her own burst spends 17 chip at exactly that time, and the
ATK gate on the same instant already reads the pre-spend count, so the two
have to agree. Verified by mutation: setting the epsilon to zero turns the
tier-II case into tier I.

The spec holder does not have to be the Burst 3 that opened the cycle. The
skill says "entering Burst Stage 3 ... affects all allies", so being in the
deck with enough chip is the whole condition.

Cycles where nobody clears the lowest threshold carry no key at all, which is
what makes the empty dict a usable fixed-point sentinel: a deck with no such
unit still resolves in exactly one pass.
EOF
```

---

### Task 7: 확장 상태에 게이팅된 per-shot 넉

**Files:**
- Modify: `backend/app/skill_rules/soda_twinkling_bunny.py`, `backend/app/skill_rules/registry.py`
- Test: `backend/tests/test_skill_rules_soda_twinkling_bunny.py`

**Interfaces:**
- Consumes: Task 2의 `context.full_burst_extension_stage(time)`, Task 3의 `SODA_VALUES["beginners_rewards"]`
- Produces: `build_beginners_rewards_per_shot_rules(values) -> list[tuple[int, str, list[SkillRule]]]` — `[(1, "every_during_full_burst", [rule])]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_skill_rules_soda_twinkling_bunny.py`에 추가(임포트에 `build_beginners_rewards_per_shot_rules` 추가):

```python
def test_beginners_rewards_nuke_scales_with_the_cycles_extension_stage():
    """넉도 누적이다 (Fienn 확정): II단계 한 발은 52.04 + 85.02 = 137.06%.
    확장이 없는 창(0단계)에서는 아예 안 나간다."""
    rules = build_beginners_rewards_per_shot_rules(SODA_VALUES)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (1, "every_during_full_burst")

    ctx = SquadContext([SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron")])
    reg = EffectRegistry()

    ctx.full_burst_extension_stages = [
        (0.0, 10.0, {}), (20.0, 32.0, {"soda-twinkling-bunny": 1}),
        (40.0, 55.0, {"soda-twinkling-bunny": 2}),
    ]

    skill_rules[0].action(ctx, "soda-twinkling-bunny", 5.0, reg)
    assert reg.drain_pulses("instant_damage_percent") == []      # 0단계: 넉 없음

    skill_rules[0].action(ctx, "soda-twinkling-bunny", 25.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert round(pulses[0].value, 4) == 52.04                    # I단계

    skill_rules[0].action(ctx, "soda-twinkling-bunny", 45.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert round(pulses[0].value, 4) == 137.06                   # II단계 = 52.04 + 85.02
    assert pulses[0].source_slug == "soda-twinkling-bunny"
```

- [ ] **Step 2: 실패를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_soda_twinkling_bunny.py -q -k nuke_scales
```
기대: `ImportError: cannot import name 'build_beginners_rewards_per_shot_rules'`

- [ ] **Step 3: 구현한다**

`app/skill_rules/soda_twinkling_bunny.py`에 추가(임포트에 `Pulse`를 더한다: `from app.effects import Effect, Pulse, ResourceSpec`):

```python
def build_beginners_rewards_per_shot_rules(values):
    """Beginner's Rewards의 둘째 불릿: 풀 버스트 중 평타마다, 그 사이클의 Time
    Extension 단계에 따라 최종 ATK의 52.04%(I) / 137.06%(II)를 넉으로 꽂는다.

    누적이다 - 첫 불릿과 같은 "Each subsequent effect triggers all effects
    before it" 아래에 있고, Fienn이 확인했다(2026-08-06).

    단계는 첫 불릿이 정하므로 이 넉은 확장이 모델되기 전에는 도달할 수 없었다.
    threshold 1 = 창 안 모든 샷. 창 밖 샷은 애초에 이 모드가 세지 않는다."""
    rewards = values["beginners_rewards"]
    stage1_percent = float(rewards["description_value_10"])
    stage2_percent = stage1_percent + float(rewards["description_value_12"])
    by_stage = {1: stage1_percent, 2: stage2_percent}

    def apply(context, caster_slug, time, registry):
        percent = by_stage.get(context.full_burst_extension_stage(time, caster_slug))
        if percent is None:
            return
        registry.add_pulse(
            Pulse("instant_damage_percent", percent, "self", caster_slug)
        )

    return [(1, "every_during_full_burst", [SkillRule(trigger="per_shot", action=apply)])]
```

- [ ] **Step 4: 통과를 확인한다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_soda_twinkling_bunny.py -q
```
기대: 전부 PASS

- [ ] **Step 5: 레지스트리에서 두 per-shot 목록을 합친다**

`app/skill_rules/registry.py`의 소다 per_shot 항목(964줄 근처)을 바꾼다:

```python
    "soda-twinkling-bunny": lambda sv: (
        build_lucky_golden_chip_per_shot_rules(sv)
        + build_beginners_rewards_per_shot_rules(sv)
    ),
```

임포트에도 새 빌더를 추가한다.

- [ ] **Step 6: docstring을 고친다**

`soda_twinkling_bunny.py`의 모듈 docstring에서 `Not modeled / deferred`의 Beginner's Rewards 항목을 통째로 지우고, `Modeled (DPS-relevant)`에 옮겨 쓴다:

```
- Beginner's Rewards (skills[1]), both bullets. On entering Burst Stage 3 the
  chip decides a Full Burst Duration extension - +2 sec at 10+ stacks, a
  further +3 at 20+, cumulative, so 20+ is +5 (Fienn measured 15 sec windows
  in play). It affects ALL allies and does not need her to be the Burst 3 that
  opened the cycle. The extension is registered as a conditional per-cycle
  delta (`build_beginners_rewards_full_burst_delta`, resolved to a fixed point
  by simulate_raid) rather than the per-slug constant Isabel and Modernia use,
  because its value changes cycle to cycle with the chip.
  Gated on that same state, every in-Full-Burst normal attack fires a nuke -
  52.04% of final ATK in Time Extension I, 137.06% in II (also cumulative).
  See docs/superpowers/specs/2026-08-06-soda-full-burst-extension-design.md.
```

`Onward, Soda!`의 Hit Rate 항목은 `Not modeled / deferred`에 그대로 남긴다(여전히 inert).

- [ ] **Step 7: 전체 스위트**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1927 passed / 3 skipped**. 캘리브레이션·골든 불변.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/skill_rules/soda_twinkling_bunny.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_soda_twinkling_bunny.py
git commit -F - <<'EOF'
Encode the nuke gated on Soda's Time Extension state

Every in-Full-Burst normal attack now fires 52.04% of final ATK in Time
Extension I and 137.06% in II - cumulative, same rule as the extension itself
and confirmed by Fienn. Her normal attack is 33%, so this is the larger half
of what the deferral was costing.

It needed no new engine capability: the instant_damage_percent pulse Velvet
uses already becomes a per_shot_nuke. What it needed was the extension, which
is why the two shipped together - the gate reads a state that did not exist
until this branch.
EOF
```

---

### Task 8: 통합 — 실측을 재현하고 두 운영을 가른다

**Files:**
- Create: `backend/tests/test_interaction_soda_full_burst_extension.py`

**Interfaces:**
- Consumes: 앞의 모든 것. 새 프로덕션 코드는 없다.

- [ ] **Step 1: 두 운영을 가르는 통합 테스트를 쓴다**

```python
"""소다의 확장이 두 운영에서 다르게 나오는지 - 이 인코딩의 핵심 주장.

Fienn 실측(docs/measurements/soda-golden-chip-in-play.md): B3가 셋인 덱에서
그녀가 격 사이클로 버스트하면 풀 버스트는 15초이고 칩은 33~50에서 순환한다.
반대로 그녀가 매 사이클 버스트하면 칩이 고갈되고 확장 단계도 따라 내려간다.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules.soda_twinkling_bunny import (
    build_beginners_rewards_full_burst_delta,
    build_beginners_rewards_per_shot_rules,
    build_golden_chip_resources,
    build_lucky_golden_chip_per_shot_rules,
    build_onward_soda_resource_gated_buffs,
    onward_soda_burst_percent,
)
from tests.test_skill_rules_soda_twinkling_bunny import SODA_VALUES

SODA = "soda-twinkling-bunny"
SG = {"weapon": "SG", "damage_percent": 10.0, "max_ammo": 1000,
      "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0}


def _run(deck, fight_duration):
    base_stats = {m["slug"]: {"atk": 10000 if m["slug"] == SODA else 0,
                              "def": 0, "max_hp": 0} for m in deck}
    return simulate_raid(
        deck,
        {m["slug"]: [] for m in deck},
        burst_damage_percents={SODA: onward_soda_burst_percent(SODA_VALUES)},
        base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=fight_duration,
        mode="auto", base_crit_rate=0.0,
        weapon_stats={SODA: SG},
        per_shot_rules={SODA: (build_lucky_golden_chip_per_shot_rules(SODA_VALUES)
                               + build_beginners_rewards_per_shot_rules(SODA_VALUES))},
        resource_specs={SODA: build_golden_chip_resources(SODA_VALUES)},
        resource_gated_buffs={SODA: build_onward_soda_resource_gated_buffs(SODA_VALUES)},
        conditional_full_burst_deltas={
            SODA: build_beginners_rewards_full_burst_delta(SODA_VALUES)},
    )


def _window_lengths(result):
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    return [round(end - start, 3) for start, end in zip(starts, ends)]


def test_full_burst_runs_15_seconds_while_the_chip_stays_above_20():
    """전투 시작 칩이 캡(50)이라 첫 창부터 +5초다. 실측의 15초가 이것이다."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    result = _run(deck, fight_duration=30.0)
    assert _window_lengths(result)[0] == 15.0
    assert result["full_burst_passes"]["converged"] is True


def test_the_extension_falls_as_her_own_bursts_drain_the_chip():
    """매 사이클 버스트하면 -17 대 +fill로 고갈되고, 창 길이가 15 -> 12 -> 10으로
    내려간다. 상수로 접을 수 없다는 것의 실물."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    lengths = _window_lengths(_run(deck, fight_duration=200.0))
    assert lengths[0] == 15.0
    assert lengths[-1] < 15.0, "칩이 고갈되면 확장이 내려가야 한다"
    assert lengths == sorted(lengths, reverse=True), "단조 감소여야 한다"


def test_the_nuke_only_fires_inside_extended_windows():
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    result = _run(deck, fight_duration=30.0)
    nukes = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert nukes, "확장이 걸린 창에서는 평타마다 넉이 나와야 한다"
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    windows = list(zip(starts, ends))
    for nuke in nukes:
        assert any(start <= nuke["time"] < end for start, end in windows), \
            "창 밖에서 넉이 나오면 안 된다"
```

- [ ] **Step 2: 돌린다**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/test_interaction_soda_full_burst_extension.py -q
```

전부 통과해야 한다. `test_the_extension_falls_as_her_own_bursts_drain_the_chip`이 실패하면(창 길이가 안 내려가면) 고정점이 잘못 수렴한 것이니 Task 6으로 돌아간다. 단조 감소 단언이 걸리면 수렴이 진동한다는 뜻이므로 **스펙의 「수렴은 보장이 아니라 기대다」절이 현실이 된 것**이다 — 그 경우 단언을 지우지 말고 실제 시퀀스를 기록해 Fienn에게 보고한다.

- [ ] **Step 3: 전체 스위트**

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1930 passed / 3 skipped**

- [ ] **Step 4: 커밋**

```bash
git add backend/tests/test_interaction_soda_full_burst_extension.py
git commit -F - <<'EOF'
Interaction tests: both of Soda's operating patterns

Alternating (she bursts every other cycle) holds the chip above 20 and the
window at 15 sec, which is what Fienn reads in game. Bursting every cycle
drains it and the window steps back down. A single constant cannot produce
both, which is the whole reason the extension is resolved per cycle.
EOF
```

---

### Task 9: 검증과 문서

**Files:**
- Modify: `backend/app/raid_simulator.py`(상한), `backend/tests/test_raid_simulator.py`, `docs/roadmap.md`, `docs/engine-gaps.md`, `docs/encoded-nikkes.md`, `docs/decisions.md`, `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`

- [ ] **Step 0: `MAX_FULL_BURST_PASSES`를 다시 정한다 — 이건 merge 전에 닫아야 한다**

Task 8에서 드러난 사실: **패스 수는 덱 구성이 아니라 전투 길이의 함수다.** 격번 덱을
길이별로 쓸어보면 3패스(200초) → 5(400초) → 7(600초) → **8(700초)** → 8 → 8로,
700초부터 상한에 붙는다. 상한을 4에서 8로 올릴 때 근거였던 「관측 최악(4)의 두 배」는
**전투 길이가 고정일 때만** 마진이다.

그리고 전투 길이는 **사용자 입력이다** — `frontend/src/components/BossProfileField.tsx`가
폼 필드로 노출하고 `api.py`의 기본값 180.0은 기본값일 뿐이다. 즉 사용자가 700초를
넣으면 상한에 걸려 **고정점이 아닌 답이 `converged: False`만 달고 조용히 나간다**.
(그 플래그는 어디에도 안 닿는다 — Task 6에서 파킹한 그 항목이다.)

`MAX_FULL_BURST_PASSES = 32`로 올린다. 상한은 원래 품질 노브가 아니라 폭주 방지
장치이므로, 수렴하는 덱은 상한과 무관하게 실제 패스 수만 지불한다(700초 덱은 여전히
8패스에서 끝난다). 값을 키우는 비용은 **진동해서 영영 안 끝나는 병리적 조합에만**
붙고, 그런 경우는 어차피 답이 없다. 주석은 「사이클 수에 비례해 늘어난다」는 관측을
적고, 왜 큰 값이 안전한지(수렴이 상한 전에 온다) 밝힌다.

테스트 하나를 추가한다 — 긴 전투(700초)에서도 `converged: True`로 끝나는 것. 이건
상한이 다시 좁아지면 깨진다.

- [ ] **Step 1: 실측과 대조한다**

```
cd C:/Users/fienn/Desktop/NikkeDeckBuilder
PYTHONIOENCODING=utf-8 python scripts/measure_golden_chip.py --deck tove-signature,arcana-fortune-mate,soda-twinkling-bunny,dorothy-serendipity,drake-signature --soda-bursts
```

기대: 격번 쪽 궤적이 실측(50 → 33 → 40/41 → 49/50 → 33)에 맞고, 창 길이가 15초다.
**어긋나면 숫자를 그대로 기록하고 멈춘다** — 문서를 고치기 전에 왜 다른지 답해야 한다.

- [ ] **Step 2: 캘리브레이션이 불변인지 확인한다**

```
PYTHONIOENCODING=utf-8 python scripts/measure_record_calibration.py
```
기대: **1.078x · 17/25 그대로**. 기록 덱 5개에 소다가 없으므로 한 자리도 움직이면 안 된다. 움직이면 「소다 없는 덱 불변」이 깨진 것이니 되돌아가 원인을 찾는다.

- [ ] **Step 3: 시뮬 비용과 실제 패스 수를 잰다**

```
PYTHONIOENCODING=utf-8 python scripts/bench_evaluate_deck.py
```
기준선은 소다 없는 덱 44.4ms(2026-08-06 측정). **이 값이 유지되어야 한다** — 소다 없는 덱은 1패스이므로.

소다가 든 덱은 `evaluate_deck` 결과의 `full_burst_passes`를 찍어 **실제 패스 수를
보고한다**(180초 실 로스터). 세 에이전트가 독립적으로 지적한 미결이 이것이다 — 실
로스터 덱의 수렴 패스 수가 테스트로 고정돼 있지 않아 드리프트가 안 보인다. 지금은
숫자를 기록해 두는 것으로 대신하고, 그 수가 상한에 가까우면 Step 0의 판단을 다시 본다.

- [ ] **Step 4: 덱 추천 변화를 본다**

Step 1의 총딜을 이 브랜치 전후로 비교한다(브랜치 전 값: 스케줄러 로테이션 4.429B, 격번 3.027B). 확장 주입 실험의 예측은 각각 4.841B / 3.282B였다 — 넉이 더해졌으므로 **그보다 높아야 한다**. 실제 값을 기록한다.

- [ ] **Step 5: 문서를 갱신한다**

- `docs/roadmap.md`: 「소다의 FB 확장을 인코딩할 것」항목을 `[x]`로 닫고, 브랜치·커밋·실측 대조 결과·새 기준선·캘리 불변을 적는다.
- `docs/engine-gaps.md`: gap #22의 「보류로 남는 것」에서 소다를 **해소**로 옮기고, 조건부 델타 + 고정점 반복이 그 수단임을 적는다.
- `docs/encoded-nikkes.md`: 소다 행에서 Beginner's Rewards를 보류 목록에서 빼고 모델된 내용으로 옮긴다. 완성도 등급(⚠)이 올라갈 수 있는지 판단한다 — 남은 미모델은 Hit Rate(inert)뿐이다.
- `docs/decisions.md`: 새 ADR 하나. 맨 위에 넣는다(최신이 위). 내용: 순환으로 보이던 것이 순차 의존이었다는 것, 고정점 반복을 고른 이유와 그 대안(사이클 인터리브)을 왜 안 골랐는지, 「소다 없는 덱 불변」이 설계의 중심이라는 것.
- `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`: 사이클별 FB 길이 항목에 **조건부 델타 + 고정점 반복**을 추가한다. 다음 인코더가 같은 모양을 만나면 여기서 찾아야 한다.

- [ ] **Step 6: 최종 전체 스위트**

```
cd backend
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```
기대: **1930 passed / 3 skipped**

- [ ] **Step 7: 커밋**

```bash
git add docs/ .claude/skills/
git commit -F - <<'EOF'
Document Soda's Full Burst extension landing

Closes the roadmap item reopened this morning, moves her out of gap #22's
deferred list, and records in decisions.md why the loop turned out to be a
sequential dependency the implementation shape had disguised.

Numbers, calibration and the in-play comparison are in the commit body of the
verification run rather than guessed here.
EOF
```

---

## 완료 기준

- 백엔드 **1930 passed / 3 skipped** (기준선 1913 + 17)
- 캘리브레이션 **1.078x · 17/25 불변**
- 소다 없는 덱의 `evaluate_deck` 비용이 **44.4ms 수준 유지**, `full_burst_passes.passes == 1`
- `scripts/measure_golden_chip.py`의 격번 궤적이 Fienn 실측(50 → 33 → 40/41 → 49/50 → 33)과 일치, 창 길이 15초
- 문서 5종 갱신 완료
