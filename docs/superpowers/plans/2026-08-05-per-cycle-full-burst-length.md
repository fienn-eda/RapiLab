# 사이클별 풀 버스트 길이 + 시간을 아는 조건 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 아르카나의 「운명의 수레바퀴 상태라면」 게이트를 원문대로 동작시킨다 — 풀 버스트
길이를 사이클마다 그 사이클을 연 Burst 3이 정하게 하고(이사벨 −5초 · 모더니아 +5초),
조건이 상태의 남은 시간을 볼 수 있게 하고, The Magician의 스킬 2 쿨감을 마저 인코딩한다.

**Architecture:** 프리미티브 셋을 기존 배선 위에 얹는다. ① `burst_cycle`이 티어 3을 쏜
멤버의 `full_burst_duration_delta`로 창 길이를 잰다(`burst_delay`·`self_stun`과 같은
registry → 멤버 dict 경로). ② `SkillRule`에 `time_condition`을 추가해 호출자가 자기 시각을
넘긴다. ③ 신규 스탯 `skill_cooldown_reduction_percent`를 `periodic_nukes`의 non-FB 분기가
매 틱 읽는다. 아래 소비자(FB 보너스 · `during_full_burst` 모드 · 자원 리셋)는 전부
`full_burst_windows` 구간 리스트를 읽으므로 자동으로 따라온다.

**Tech Stack:** Python 3.13, pytest. 백엔드 전용 — 프론트엔드 변경 없음.

**설계 문서:** `docs/superpowers/specs/2026-08-05-per-cycle-full-burst-length-design.md`

## Global Constraints

- 작업 브랜치는 **`wip/arcana-wheel-gate-review`**(이미 존재, 커밋 `a8de231`까지 쌓여 있음).
- 테스트 실행은 항상 `cd backend && PYTHONIOENCODING=utf-8 python -m pytest ...`.
  환경변수를 빼면 한글·화살표 문자에서 cp949 인코딩 에러가 난다.
- **기준선: 백엔드 `1874 passed / 3 skipped`.** 각 태스크 끝에서 이 수치가 유지되거나
  (새 테스트만큼) 늘어나야 한다. 줄면 무언가 깨진 것이다.
- **캘리브레이션 불변: `combined 1.078x over 25 units` · `within ±15%: 17/25`.**
  기록 덱 5개에 이사벨·모더니아·아르카나·소다가 하나도 없으므로 이 값들은 **움직이면 안
  된다**. Task 8에서 확인한다.
- **`git add -A`를 쓰지 말 것.** 이 저장소에 다른 세션이 만든 미추적 파일이 있다
  (`docs/superpowers/specs/2026-08-05-search-reproducibility-design.md`). 커밋할 파일을
  **경로로 하나씩** 지정한다.
- 주석은 **무엇을·왜**만 쓴다. "예전엔 이랬다" / "이번에 바꿨다"류 변경 이력을 코드
  주석에 남기지 않는다(`.claude/CLAUDE.md`).
- 소다: 트윙클링 버니는 **범위 밖**이다. 그녀의 골든칩·FB 확장은 건드리지 않는다.

---

## File Structure

| 파일 | 책임 | 태스크 |
|---|---|---|
| `backend/app/burst_cycle.py` | 사이클마다 창 길이를 티어 3 발사자에게서 읽는다 | 1 |
| `backend/app/skill_rules/registry.py` | `FULL_BURST_DURATION_DELTA` 맵 + 조회기 / 이사벨 항목의 `cooldown_skill_slot` | 2, 6 |
| `backend/app/roster.py` | 델타를 멤버 dict에 싣는다 | 2 |
| `backend/app/squad_engine.py` | `SkillRule.time_condition` · `own_burst_status_active` · `SquadContext.current_full_burst_end` | 3, 5 |
| `backend/app/skill_rules/_helpers.py` | `_rule`/`member_subset_buff_rule`에 `time_condition` 통과 | 3 |
| `backend/app/raid_simulator.py` | 호출 지점 셋에 시각 전달 / `current_full_burst_end` 세팅 / 주기 쿨감 | 3, 5, 6 |
| `backend/app/skill_rules/arcana.py` | 게이트 교체 + Magician 쿨감 튜플 | 4, 7 |
| `backend/app/skill_rules/dorothy_serendipity.py` | 실제 창 길이 사용 | 5 |
| `backend/app/skill_rules/arcana_fortune_mate.py` | 실제 창 길이 사용 | 5 |
| `backend/app/skill_rules/isabel.py`, `modernia.py` | 독스트링을 「보류」에서 「모델됨」으로 | 8 |
| `backend/tests/test_interaction_arcana_isabel.py` | **신규** — 이 수정의 요점을 못박는 테스트 | 8 |

---

### Task 1: 풀 버스트 길이를 티어 3 발사자가 정한다

**Files:**
- Modify: `backend/app/burst_cycle.py:102-205` (`simulate_burst_cycle`)
- Test: `backend/tests/test_burst_cycle.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - 멤버 dict의 선택적 키 `"full_burst_duration_delta": float` — 티어 3으로 발사된
    멤버의 것만 읽힌다. 없으면 0.0.
  - 훅 시그니처 변경: `on_full_burst_enter(start, end)` (기존 `on_full_burst_enter(start)`)
  - 모듈 상수 `MIN_FULL_BURST_DURATION = 0.0`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_burst_cycle.py` 끝에 추가:

```python
def _deck_with_two_b3(delta_a=None, delta_b=None):
    """b3_unit_a와 b3_unit_b가 사이클마다 번갈아 티어 3을 맡는 덱."""
    a = {"slug": "b3_unit_a", "burst_tier": 3, "cooldown": 40.0}
    b = {"slug": "b3_unit_b", "burst_tier": 3, "cooldown": 40.0}
    if delta_a is not None:
        a["full_burst_duration_delta"] = delta_a
    if delta_b is not None:
        b["full_burst_duration_delta"] = delta_b
    return [
        {"slug": "b1_unit", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2_unit", "burst_tier": 2, "cooldown": 20.0},
        a,
        b,
    ]


def _windows(events):
    return list(zip(
        (e["time"] for e in events if e["type"] == "full_burst_start"),
        (e["time"] for e in events if e["type"] == "full_burst_end"),
    ))


def test_full_burst_window_shortens_for_a_tier3_that_cuts_it():
    deck = _deck_with_two_b3(delta_a=-5.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(5.0)


def test_full_burst_window_lengthens_for_a_tier3_that_extends_it():
    deck = _deck_with_two_b3(delta_a=5.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=25.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(15.0)


def test_each_cycle_takes_the_length_of_whichever_burst3_opened_it():
    # 티어 3이 둘이고 쿨다운이 40초라 사이클마다 번갈아 연다. 창 길이는 사이클의
    # 속성이 아니라 그 사이클을 연 유닛의 속성이다.
    deck = _deck_with_two_b3(delta_a=-5.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=60.0, mode="auto")

    lengths = [round(end - start, 6) for start, end in _windows(events)[:2]]
    assert lengths == [5.0, 10.0]


def test_a_delta_below_the_base_duration_gives_a_zero_length_window_not_a_negative_one():
    # 음수 길이의 창은 아래의 모든 `start <= t < end` 검사를 조용히 뒤집는다.
    deck = _deck_with_two_b3(delta_a=-25.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(0.0)


def test_a_member_without_a_delta_keeps_the_base_duration():
    deck = _deck_with_two_b3()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(FULL_BURST_DURATION)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_burst_cycle.py -q -k "shortens or lengthens or whichever or zero_length or without_a_delta"`

Expected: `test_..._shortens_...`, `..._lengthens_...`, `..._whichever_...`, `..._zero_length_...`
넷이 FAIL(창이 계속 10초). `..._without_a_delta_...`는 이미 PASS(회귀 방지용).

- [ ] **Step 3: 최소 구현**

`backend/app/burst_cycle.py` — `FULL_BURST_OPEN_DELAY` 상수 아래에 추가:

```python
# 풀 버스트 창의 하한. 창 길이를 줄이는 유닛(이사벨의 "Full Burst Time -5 sec")이
# 기본 길이보다 큰 값을 깎는 배치는 오늘 데이터에 없지만, 길이가 음수인 창은
# 아래의 모든 [start, end) 검사를 조용히 뒤집으므로 여기서 막는다.
MIN_FULL_BURST_DURATION = 0.0
```

같은 파일 `simulate_burst_cycle` 안, 티어 루프에서 `tier3_fire_time`을 잡는 자리를
멤버까지 잡도록 바꾼다:

```python
            if tier == 3:
                tier3_fire_time = fire_time
                tier3_member = chosen
```

루프 위쪽(`tier3_fire_time = None` 자리)에 짝을 맞춘다:

```python
        tier3_fire_time = None
        tier3_member = None
```

그리고 창을 여는 블록을 통째로 아래로 바꾼다 — **종료 시각을 훅보다 먼저 계산**한다:

```python
        full_burst_start = tier3_fire_time + FULL_BURST_OPEN_DELAY
        # 창 길이는 이 사이클을 연 Burst 3이 정한다: 자기 버스트가 풀 버스트 자체를
        # 늘리거나 줄이는 유닛이 있고(이사벨 -5초, 모더니아 +5초), 그 효과는 그 유닛이
        # 연 사이클에만 걸린다.
        duration = max(
            MIN_FULL_BURST_DURATION,
            FULL_BURST_DURATION + tier3_member.get("full_burst_duration_delta", 0.0),
        )
        full_burst_end = full_burst_start + duration
        if on_full_burst_enter:
            on_full_burst_enter(full_burst_start, full_burst_end)

        events.append({"type": "full_burst_start", "time": full_burst_start})
```

(기존의 `full_burst_end = full_burst_start + FULL_BURST_DURATION` 줄과 그 위의
`on_full_burst_enter(full_burst_start)` 호출은 이 블록으로 대체된다.)

- [ ] **Step 4: 훅 시그니처를 쓰는 곳 둘을 고친다**

`backend/app/raid_simulator.py:832`:

```python
    def on_full_burst_enter(time, end):
        fire_trigger("full_burst_enter", rules_by_slug, context, registry, time)
        drain_instant_damage(time)
```

(`end`는 Task 5에서 쓴다. 지금은 시그니처만 맞춘다.)

`backend/tests/test_burst_cycle.py:130-137`의 기존 훅 테스트:

```python
def test_on_full_burst_enter_hook_fires_at_tier3_time():
    deck = make_deck()
    calls = []
    simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto",
        on_full_burst_enter=lambda start, end: calls.append((start, end)),
    )
    assert calls == [(5.0 + FULL_BURST_OPEN_DELAY,
                      5.0 + FULL_BURST_OPEN_DELAY + FULL_BURST_DURATION)]
```

`backend/app/burst_cycle.py`의 docstring에서 훅 설명도 고친다:

```
        on_full_burst_enter(start, end)     - called when tier 3 fires; `end` is
            when the window this Burst 3 opened will close, which the tier-3
            unit's own kit may have moved
```

- [ ] **Step 5: 전체 스위트를 돌린다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1879 passed, 3 skipped` (기준선 1874 + 신규 5).

`test_burst_cycle.py` 밖에서 실패가 나면 **멈추고 보고할 것** — 이 태스크는 델타가 없는
덱의 동작을 바꾸지 않으므로, 다른 실패는 예상 밖이다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/burst_cycle.py backend/app/raid_simulator.py backend/tests/test_burst_cycle.py
git commit -m "Let the Burst 3 that opened a Full Burst decide how long it lasts

The window length was a module constant, so a unit whose burst moves it
(Isabel -5 sec, Modernia +5 sec) had no way to say so. It is a property of
whichever Burst 3 opened the cycle, not of the cycle, so it is read off that
member and clamped at zero - a negative-length window silently inverts every
[start, end) test downstream. on_full_burst_enter now carries the end too."
```

---

### Task 2: 이사벨·모더니아를 배선한다

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (`VARIANT_BURST_TIERS` 근처, 파일 720행 부근)
- Modify: `backend/app/roster.py:108-126` (`assemble_simulation_inputs`)
- Test: `backend/tests/test_skill_rules_registry.py` (없으면 `backend/tests/test_roster.py`)

**Interfaces:**
- Consumes: Task 1의 멤버 dict 키 `"full_burst_duration_delta"`
- Produces:
  - `registry.FULL_BURST_DURATION_DELTA: dict[str, float]`
  - `registry.get_full_burst_duration_delta(slug: str) -> float`

- [ ] **Step 1: 어느 테스트 파일에 쓸지 정한다**

Run: `ls backend/tests/ | grep -E "registry|roster"`

`test_skill_rules_registry.py`가 있으면 거기, 없으면 `test_roster.py`에 쓴다. 둘 다 없으면
`backend/tests/test_roster.py`를 새로 만든다.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

```python
from app.skill_rules.registry import get_full_burst_duration_delta


def test_isabel_shortens_the_full_burst_window():
    # Sonic Chaser: "Full Burst Time (down) 5 sec."
    assert get_full_burst_duration_delta("isabel") == -5.0


def test_modernia_lengthens_the_full_burst_window():
    # New World: "Full Burst Duration (up) 5 sec."
    assert get_full_burst_duration_delta("modernia") == 5.0


def test_a_unit_that_does_not_touch_the_window_reads_zero():
    assert get_full_burst_duration_delta("arcana") == 0.0
```

그리고 `backend/tests/test_roster.py`(또는 위에서 정한 파일)에 배선 테스트:

```python
def test_assemble_puts_the_full_burst_delta_on_the_member_only_when_nonzero():
    from app.models import UserNikkeState
    from app.roster import assemble_simulation_inputs
    from app.user_roster import load_roster

    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200, "core_level": 0,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in ("liter", "arcana", "isabel")
    ]
    specs, _excluded = load_roster(states)
    inputs = assemble_simulation_inputs(specs)
    by_slug = {m["slug"]: m for m in inputs["deck"]}

    assert by_slug["isabel"]["full_burst_duration_delta"] == -5.0
    assert "full_burst_duration_delta" not in by_slug["arcana"]
```

**주의:** `assemble_simulation_inputs`의 실제 반환 형태를 먼저 읽고 `inputs["deck"]`
부분을 맞출 것 (`backend/app/roster.py:87` 이하). 기존 `test_roster.py`에 같은 함수를
쓰는 테스트가 있으면 그 접근 방식을 그대로 따른다.

- [ ] **Step 3: 실패를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q -k "full_burst_delta or full_burst_window or shortens_the_full or lengthens_the_full"`
Expected: FAIL — `ImportError` 또는 `AttributeError: get_full_burst_duration_delta`

- [ ] **Step 4: 구현**

`backend/app/skill_rules/registry.py`, `VARIANT_BURST_TIERS` 정의 바로 위에:

```python
# 자기 버스트가 풀 버스트 창 자체의 길이를 바꾸는 Burst 3. 값이 스킬 데이터 슬롯이
# 아니라 설명문에 박힌 리터럴이라 여기 적는다(그레이브의 "10 sec"와 같은 사정).
# 효과는 그 유닛이 연 사이클에만 걸린다 - burst_cycle이 티어 3을 쏜 멤버에게서 읽는다.
FULL_BURST_DURATION_DELTA: dict[str, float] = {
    "isabel": -5.0,     # Sonic Chaser: "Full Burst Time ▼ 5 sec."
    "modernia": 5.0,    # New World:    "Full Burst Duration ▲ 5 sec."
}


def get_full_burst_duration_delta(slug: str) -> float:
    """이 유닛의 버스트가 풀 버스트 창을 몇 초 움직이는가 (대부분 0.0)."""
    return FULL_BURST_DURATION_DELTA.get(slug, 0.0)
```

`backend/app/roster.py` — import에 `get_full_burst_duration_delta`를 더하고,
`member` dict를 만든 직후 `burst_delay` 처리 바로 위에:

```python
        full_burst_delta = get_full_burst_duration_delta(spec.slug)
        if full_burst_delta:
            member["full_burst_duration_delta"] = full_burst_delta
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1883 passed, 3 skipped` (1879 + 신규 4)

**여기서 이사벨·모더니아 덱의 수치가 실제로 움직인다.** 다른 테스트가 깨지면 그 테스트가
「FB는 항상 10초」를 전제로 그 두 유닛의 수치를 못박고 있는 것이다 — **고치기 전에 어떤
테스트가 왜 깨졌는지 보고할 것.**

- [ ] **Step 6: 눈으로 확인한다**

Run: `PYTHONIOENCODING=utf-8 python scripts/measure_deck_breakdown.py --deck anis-star,arcana,isabel,crown,cinderella`

이사벨이 티어 3을 맡은 사이클이 짧아져 **전체 사이클 수가 늘어야** 한다. 값을 기록해 둘 것
(Task 8에서 다시 본다).

- [ ] **Step 7: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/app/roster.py \n  backend/tests/test_skill_rules_registry.py backend/tests/test_roster.py
git commit -m "Register Isabel's and Modernia's Full Burst length changes

Isabel's Sonic Chaser cuts the window to 5 sec and Modernia's New World
stretches it to 15; both numbers are literals in the skill description rather
than data slots, so they live in a registry map beside VARIANT_BURST_TIERS.
Wired through assemble_simulation_inputs the same way burst_delay and self_stun
are - facts that change a unit's burst schedule already travel that path."
```

---

### Task 3: `SkillRule.time_condition`

**Files:**
- Modify: `backend/app/squad_engine.py:383-401`
- Modify: `backend/app/skill_rules/_helpers.py:17-24` (`_rule`), `:128-151` (`member_subset_buff_rule`)
- Modify: `backend/app/raid_simulator.py:869`, `:1105`
- Test: `backend/tests/test_squad_engine.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `SkillRule.time_condition: Callable[[SquadContext, str, float], bool]`
    (기본값 `_always_true_at`)
  - `squad_engine.own_burst_status_active(seconds: float) -> Callable[[SquadContext, str, float], bool]`
  - `_helpers._rule(trigger, action, condition, time_condition=None)`
  - `_helpers.member_subset_buff_rule(trigger, member_filter, buffs, condition=None, refreshing=False, time_condition=None)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_squad_engine.py` 끝에 추가:

```python
def test_time_condition_defaults_to_always_true():
    fired = []
    rule = SkillRule(trigger="t", action=lambda c, s, time, r: fired.append(time))
    ctx = SquadContext([SquadMember("a", burst_tier=1, element="Fire")])
    fire_trigger("t", {"a": [rule]}, ctx, EffectRegistry(), time=3.0)
    assert fired == [3.0]


def test_a_false_time_condition_blocks_the_action():
    fired = []
    rule = SkillRule(
        trigger="t", action=lambda c, s, time, r: fired.append(time),
        time_condition=lambda c, s, time: time < 5.0,
    )
    ctx = SquadContext([SquadMember("a", burst_tier=1, element="Fire")])
    fire_trigger("t", {"a": [rule]}, ctx, EffectRegistry(), time=3.0)
    fire_trigger("t", {"a": [rule]}, ctx, EffectRegistry(), time=7.0)
    assert fired == [3.0]


def test_own_burst_status_active_is_true_only_while_the_status_runs():
    check = own_burst_status_active(10.0)
    ctx = SquadContext([SquadMember("a", burst_tier=2, element="Electric")])

    # 한 번도 버스트하지 않았으면 상태가 없다.
    assert check(ctx, "a", 5.0) is False

    ctx.record_burst_time("a", 2.5)
    assert check(ctx, "a", 12.4) is True     # 만료 직전
    assert check(ctx, "a", 12.5) is False    # 정확히 만료
    assert check(ctx, "a", 12.6) is False    # 만료 후


def test_own_burst_status_active_measures_from_the_latest_burst():
    check = own_burst_status_active(10.0)
    ctx = SquadContext([SquadMember("a", burst_tier=2, element="Electric")])
    ctx.record_burst_time("a", 2.5)
    ctx.record_burst_time("a", 42.5)
    assert check(ctx, "a", 50.0) is True
```

파일 상단 import에 `SkillRule`, `own_burst_status_active`, `EffectRegistry`가 없으면 더한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_squad_engine.py -q -k "time_condition or own_burst_status_active"`
Expected: FAIL — `ImportError: cannot import name 'own_burst_status_active'`

- [ ] **Step 3: 구현**

`backend/app/squad_engine.py` — `_always_true` 바로 아래:

```python
def _always_true_at(context: SquadContext, caster_slug: str, time: float) -> bool:
    return True
```

`SkillRule`에 필드를 더한다:

```python
@dataclass
class SkillRule:
    trigger: str
    action: Callable[[SquadContext, str, float, EffectRegistry], None]
    condition: Callable[[SquadContext, str], bool] = field(default=_always_true)
    # 상태의 남은 시간처럼, 트리거가 발동한 시각을 봐야만 답할 수 있는 게이트.
    # 시각은 언제나 호출자가 넘긴다 - 컨텍스트에 현재 시각을 찍어두고 나중에 읽는
    # 방식은 호출 지점 하나가 찍기를 빠뜨리면 낡은 값을 에러 없이 반환한다.
    time_condition: Callable[[SquadContext, str, float], bool] = field(
        default=_always_true_at
    )
```

`fire_trigger`:

```python
        for rule in matching:
            if rule.condition(context, slug) and rule.time_condition(context, slug, time):
                rule.action(context, slug, time, registry)
```

조건 팩토리를 `own_burst_fired_this_cycle` 바로 아래에 더한다:

```python
def own_burst_status_active(seconds: float) -> Callable[[SquadContext, str, float], bool]:
    """자기 버스트가 자신에게 건 상태가 그 시각에 아직 살아 있는가.

    부여 시점은 그 버스트를 쓴 시각이므로 별도 상태 기록이 필요 없다
    (`SquadContext.burst_times`). 한 번도 버스트하지 않았으면 거짓.

    `own_burst_fired_this_cycle()`가 답할 수 없는 질문이다: 그쪽은 시계가 없어서
    부여 이후 `seconds`가 지났는지 구별하지 못한다. 풀 버스트 창 하나를 사이에 둔
    `full_burst_end` 게이트에서는 그 차이가 전부다 - 아르카나의 운명의 수레바퀴는
    10초짜리인데 그녀는 버스트 스테이지 2에서 시전하므로, 표준 10초 창이 끝날 때는
    이미 만료돼 있다.
    """

    def check(context: SquadContext, caster_slug: str, time: float) -> bool:
        times = context.burst_times.get(caster_slug)
        if not times:
            return False
        return times[-1] + seconds > time

    return check
```

`backend/app/skill_rules/_helpers.py`의 `_rule`:

```python
def _rule(trigger, action, condition, time_condition=None):
    """Build a SkillRule, attaching `condition`/`time_condition` only when given
    (None keeps SkillRule's own always-true defaults) - so a gated bullet (e.g. a
    boss-element-conditional debuff, or one gated on a status that may have
    lapsed) reuses the same builder as an ungated one."""
    rule = SkillRule(trigger=trigger, action=action)
    if condition is not None:
        rule.condition = condition
    if time_condition is not None:
        rule.time_condition = time_condition
    return rule
```

`member_subset_buff_rule`의 시그니처와 반환:

```python
def member_subset_buff_rule(trigger, member_filter, buffs, condition=None,
                            refreshing=False, time_condition=None):
```

```python
    return _rule(trigger, action, condition, time_condition)
```

`backend/app/raid_simulator.py:869` (periodic_rules 패스):

```python
                for rule in rules:
                    if rule.condition(context, slug) and rule.time_condition(context, slug, tick):
                        rule.action(context, slug, tick, registry)
```

`backend/app/raid_simulator.py:1105` (per-shot 패스):

```python
                    for rule in rules:
                        if (rule.condition(context, slug)
                                and rule.time_condition(context, slug, shot_time)):
                            rule.action(context, slug, shot_time, registry)
```

- [ ] **Step 4: 호출 지점 셋을 전부 덮는 테스트를 쓴다**

`backend/tests/test_raid_simulator.py` 끝에 추가. **이것이 이 태스크의 핵심 테스트다** —
periodic이나 per-shot을 빼먹으면 조용히 썩는 자리다.

```python
def test_time_condition_is_honoured_by_the_periodic_and_per_shot_passes():
    """세 호출 지점(fire_trigger / periodic_rules / per_shot_rules)이 전부
    time_condition을 존중하는지. 하나라도 빠지면 그 경로의 게이트가 조용히 열린다."""
    seen = {"periodic": [], "per_shot": []}

    def never(context, caster_slug, time):
        return False

    def always(context, caster_slug, time):
        return True

    def record(bucket):
        def action(context, caster_slug, time, registry):
            seen[bucket].append(round(time, 3))
        return action

    def run(time_condition):
        seen["periodic"].clear()
        seen["per_shot"].clear()
        return simulate_raid(
            make_deck(),
            {"buffer": [], "midtier": [], "attacker": []},
            burst_damage_percents={},
            base_stats=make_base_stats(attacker_atk=10000),
            enemy_def=0,
            gauge_charge_time=5.0,
            fight_duration=40.0,
            mode="auto",
            base_crit_rate=0.0,
            periodic_rules={"buffer": [(15.0, [SkillRule(
                trigger="periodic", action=record("periodic"),
                time_condition=time_condition)])]},
            per_shot_rules={"attacker": [(5, "every", [SkillRule(
                trigger="per_shot", action=record("per_shot"),
                time_condition=time_condition)])]},
        )

    run(always)
    assert seen["periodic"], "periodic 패스가 아예 안 돌았다 - 픽스처가 잘못됐다"
    assert seen["per_shot"], "per-shot 패스가 아예 안 돌았다 - 픽스처가 잘못됐다"

    run(never)
    assert seen == {"periodic": [], "per_shot": []}
```

파일 상단 import에 `SkillRule`이 없으면 `from app.squad_engine import SkillRule`을 더한다.
`make_deck` · `make_base_stats` · `simulate_raid`는 이 파일에 이미 있다
(`test_periodic_nuke_fires_repeatedly_on_its_own_fixed_cooldown` 참고).

`always`로 먼저 돌리는 것이 핵심이다 — `never`만 단언하면 픽스처가 애초에 그 패스를 안
태워도 테스트가 초록으로 통과한다.

- [ ] **Step 5: 전체 스위트를 돌린다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1888 passed, 3 skipped` (1883 + 신규 5). 기본값이 항상 참이므로 **기존 동작은
하나도 바뀌지 않아야 한다.**

- [ ] **Step 6: 커밋**

```bash
git add backend/app/squad_engine.py backend/app/skill_rules/_helpers.py backend/app/raid_simulator.py backend/tests/test_squad_engine.py backend/tests/test_raid_simulator.py
git commit -m "Give a SkillRule a gate that can see the trigger's own time

Condition factories take (context, caster_slug), which cannot answer whether a
timed status is still running - the question Arcana's Wheel of Fortune bullets
actually ask. time_condition takes the time as well, and every one of the three
call sites already holds it, so it is passed rather than stamped on the context
where a site that forgets would read a stale value with no error.

own_burst_status_active reads SquadContext.burst_times, so a status a unit's own
burst grants needs no separate bookkeeping."
```

---

### Task 4: 아르카나의 게이트를 원문대로 바꾼다

**Files:**
- Modify: `backend/app/skill_rules/arcana.py:115-131` (룰 리스트)
- Test: `backend/tests/test_skill_rules_arcana.py:78-95`, `:136-151`

**Interfaces:**
- Consumes: Task 3의 `own_burst_status_active`, `member_subset_buff_rule(..., time_condition=)`
- Produces: 없음 (아르카나 모듈 내부)

- [ ] **Step 1: 기존 테스트 둘을 새 전제로 고쳐 쓴다**

`backend/tests/test_skill_rules_arcana.py`에서
`test_cycle_of_destiny_death_bullet_requires_arcana_burst_this_cycle` 과
`test_magician_and_strength_require_bursted_target_and_wheel_of_fortune` 을 아래로 교체한다.

`fire_trigger`는 `ctx.burst_times`를 채우지 않으므로 테스트가 직접
`ctx.record_burst_time("arcana", t)`를 부른다. 수레바퀴는 10초짜리다
(`SHACKLES_OF_DESTINY["description_value_02"]`).

```python
def test_death_bullet_needs_the_wheel_still_running_at_full_burst_end():
    # 수레바퀴는 그녀가 버스트 스테이지 2에서 시전할 때 시작하는 10초짜리다.
    ctx = make_context()
    ctx.record_burst_time("arcana", 2.5)
    registry = EffectRegistry()
    # 표준 10초 창: 그녀의 시전은 창이 열리기 전이므로 종료 시점엔 이미 만료다.
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=12.6)

    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []
    # Awakened Destiny의 무조건 5%만 적용된다 (Death의 50%는 아니다)
    assert registry.total_for("flat_atk", FIRE_ALLY, now=12.6) == 500.0

    # 이사벨이 창을 5초로 줄인 사이클에서는 아직 살아 있다.
    ctx2 = make_context()
    ctx2.record_burst_time("arcana", 2.5)
    registry2 = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx2, registry2, time=7.6)

    pulses = registry2.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 6.0
    assert pulses[0].scope == "squad"
    # Awakened의 5% (500) + Death의 50% (5000)
    assert registry2.total_for("flat_atk", FIRE_ALLY, now=7.6) == 5500.0


def test_death_bullet_does_not_fire_when_arcana_never_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=7.6)
    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []
    assert registry.total_for("flat_atk", FIRE_ALLY, now=7.6) == 500.0


def test_magician_and_strength_need_the_wheel_still_running():
    ctx = _b3_context()
    ctx.burst_used_this_cycle.update({"arcana", "electric-b3", "fire-b3"})
    ctx.record_burst_time("arcana", 2.5)

    # 10초 창: 만료 - 스쿼드 공댐 7.5%와 Awakened의 500만 남는다.
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=12.6)
    assert round(registry.total_for("attack_damage_up", ELECTRIC_B3, now=12.6), 4) == 0.075
    assert registry.total_for("flat_atk", ELECTRIC_B3, now=12.6) == 500.0

    # 5초 창: 살아 있다 - Magician 1.80 + 스쿼드 0.075
    registry2 = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry2, time=7.6)
    assert round(registry2.total_for("attack_damage_up", ELECTRIC_B3, now=7.6), 4) == 1.875
    assert round(registry2.total_for("attack_damage_up", FIRE_B3, now=7.6), 4) == 0.075
    # Awakened 500 + Death 5000 + Strength 18000
    assert registry2.total_for("flat_atk", ELECTRIC_B3, now=7.6) == 23500.0
    assert registry2.total_for("flat_atk", FIRE_B3, now=7.6) == 5500.0


def test_magician_and_strength_skip_a_target_that_did_not_burst():
    ctx = _b3_context()
    ctx.burst_used_this_cycle.add("arcana")   # 수레바퀴는 있지만 대상이 안 터졌다
    ctx.record_burst_time("arcana", 2.5)
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=7.6)
    assert round(registry.total_for("attack_damage_up", ELECTRIC_B3, now=7.6), 4) == 0.075
    assert registry.total_for("flat_atk", ELECTRIC_B3, now=7.6) == 5500.0
```

기존 `test_magician_and_strength_hit_bursted_electric_b3_allies`는 `time=15.0`으로 부르고
`ctx.record_burst_time`을 안 하므로 **새 게이트에서 실패한다.** 그 테스트의 `ctx` 설정에
`ctx.record_burst_time("arcana", 10.0)`을 더하고 호출 시각을 `time=15.0` 그대로 두면
(15.0 < 10.0+10.0) 통과한다. 15초 지속 단언(`now=30.1`)은 그대로 둔다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_arcana.py -q`
Expected: 새 테스트들이 FAIL — 게이트가 아직 시계를 안 본다.

- [ ] **Step 3: 구현**

`backend/app/skill_rules/arcana.py` — import를 바꾼다:

```python
from app.squad_engine import SkillRule, own_burst_status_active
```

`build_arcana_rules` 안에서 수레바퀴 지속시간은 이미 `wheel_duration`으로 읽고 있다.
룰 리스트를 아래로 바꾼다:

```python
    wheel_active = own_burst_status_active(wheel_duration)

    return [
        SkillRule(trigger="own_burst_activate", action=apply_shackles_buffs),
        SkillRule(trigger="full_burst_end", action=apply_awakened_squad_atk),
        SkillRule(trigger="full_burst_end", action=apply_cycle_death,
                  time_condition=wheel_active),
        SkillRule(trigger="full_burst_end", action=apply_cycle_attack_damage),
        # The Magician / Strength: bursted Electric Burst-3 subset (gap #3).
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("attack_damage_up", magician_attack_damage, magician_duration)],
            time_condition=wheel_active,
        ),
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("flat_atk", strength_atk, strength_duration)],
            time_condition=wheel_active,
        ),
    ]
```

**`own_burst_fired_this_cycle`은 이 모듈에서 완전히 빠진다** — 둘을 AND로 묶으면 원문보다
엄격해진다(원문은 「수레바퀴 상태라면」이지 「이번 사이클에 버스트했다면」이 아니다).
import에서도 지운다. `squad_engine`의 함수 자체는 그레이브·아스카·마나·신크웨·마르시아나가
계속 쓰므로 남긴다.

- [ ] **Step 4: 모듈 독스트링에서 KNOWN DEFECT 블록을 고친다**

`arcana.py` 상단의 `KNOWN DEFECT (2026-08-05):` 로 시작하는 문단을 지우고, 그 위 문단을
아래로 바꾼다:

```
"Wheel of Fortune" is a status her own burst (Shackles of Destiny) grants to
all Electric Code allies, including herself (she is Electric). Her other two
skills gate three bullets on "if self is in Wheel of Fortune status" at Full
Burst END - and the status runs 10 sec from her Burst Stage 2 cast, which is
strictly before the Burst 3 cast that opens the window. So with a standard 10
sec Full Burst it has always lapsed by the time those bullets check, and the
only thing that opens the gate is a shortened window: today that means Isabel
alone ("Full Burst Time -5 sec"). Modeled with `own_burst_status_active`, which
reads the grant off her own burst time and compares it against the trigger's
time - `own_burst_fired_this_cycle()` carries no clock and cannot tell the two
cases apart.
```

- [ ] **Step 5: 전체 스위트를 돌린다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1890 passed, 3 skipped` (1888 + 신규 2 — Step 1에서 2개를 4개로 늘렸다)

`test_skill_rules_arcana.py` 밖에서 실패가 나면 **멈추고 보고할 것.**

- [ ] **Step 6: 커밋**

```bash
git add backend/app/skill_rules/arcana.py backend/tests/test_skill_rules_arcana.py
git commit -m "Gate Arcana's conditional bullets on the Wheel actually still running

The skill text says 'if self is in Wheel of Fortune status', which the encoding
read as 'did her own burst fire this cycle'. That drops the status's clock, and
these three bullets fire a whole Full Burst window after the grant - so the
proxy answered true in every deck she bursts in, worth +25-29% of deck total on
a real roster.

The two conditions are not equivalent and are not ANDed: the text asks only
whether the status is up, and requiring both would be stricter than the text -
at a 5 sec window the cycles run 7.6 sec apart, which clears a 10 sec status by
only 2.7 sec."
```

---

### Task 5: 「풀 버스트가 끝날 때까지」 버프가 실제 창을 따른다

**Files:**
- Modify: `backend/app/squad_engine.py` (`SquadContext.__init__`)
- Modify: `backend/app/raid_simulator.py:832` (`on_full_burst_enter`)
- Modify: `backend/app/skill_rules/dorothy_serendipity.py:21,56`
- Modify: `backend/app/skill_rules/arcana_fortune_mate.py:82,127,130`
- Test: `backend/tests/test_skill_rules_dorothy_serendipity.py`,
  `backend/tests/test_skill_rules_arcana_fortune_mate.py`

**Interfaces:**
- Consumes: Task 1의 `on_full_burst_enter(start, end)`
- Produces: `SquadContext.current_full_burst_end: float | None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_skill_rules_dorothy_serendipity.py`에 추가:

`backend/tests/test_skill_rules_dorothy_serendipity.py`의 기존 픽스처
(`make_context` · `build` · `DOROTHY`)를 그대로 쓴다.

```python
def test_radiant_wings_lasts_exactly_the_window_that_is_open():
    # 원문이 "continuously" - 초 수가 아니라 풀 버스트가 끝날 때까지다. 이사벨이 연
    # 5초짜리 창에서는 5초만 간다.
    ctx = make_context()
    ctx.current_full_burst_end = 10.0          # t=5.0에 열린 5초짜리 창
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("atk_percent", DOROTHY, now=9.9), 4) == 0.7524
    assert registry.total_for("atk_percent", DOROTHY, now=10.1) == 0.0


def test_radiant_wings_falls_back_to_the_base_duration_without_a_window():
    # 버스트 사이클이 없는 컨텍스트(대부분의 단위 테스트)는 엔진 기본값으로 떨어진다.
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("atk_percent", DOROTHY, now=14.9), 4) == 0.7524
    assert registry.total_for("atk_percent", DOROTHY, now=15.1) == 0.0
```

기존 `test_radiant_wings_grants_self_atk_during_full_burst`는
`ctx.current_full_burst_end`를 세우지 않으므로 기본 10초로 떨어져 **그대로 통과해야 한다.**

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_dorothy_serendipity.py -q`

Expected: `test_radiant_wings_lasts_exactly_the_window_that_is_open`이 FAIL —
`now=10.1`에서 버프가 아직 0.7524다(창을 무시하고 10초를 쓰므로 15.0까지 간다).
`..._falls_back_...`은 이미 PASS(회귀 방지용).

- [ ] **Step 3: 구현**

`backend/app/squad_engine.py` — `SquadContext.__init__`의 `full_burst_windows` 정의 옆:

```python
        # 지금 열려 있는 풀 버스트 창이 닫히는 시각. 원문이 "continuously"인 버프
        # (도로시의 Radiant Wings, 포츈 메이트의 Making Memories)는 초 수가 아니라
        # 창의 끝까지 가므로, 그 길이를 정한 Burst 3이 누구였는지에 따라 달라진다.
        # full_burst_enter에서 세워지고 그 순간에만 읽힌다.
        self.current_full_burst_end: float | None = None
```

`backend/app/raid_simulator.py`:

```python
    def on_full_burst_enter(time, end):
        context.current_full_burst_end = end
        fire_trigger("full_burst_enter", rules_by_slug, context, registry, time)
        drain_instant_damage(time)
```

`backend/app/skill_rules/dorothy_serendipity.py` — `FULL_BURST_DURATION` import를 지우고
액션에서 창 길이를 계산한다. 지금 `buff_rule("full_burst_enter", [(..., FULL_BURST_DURATION)])`
형태이므로 `SkillRule`로 바꾼다:

```python
def _full_burst_window_length(context, time):
    """지금 열린 창이 남긴 시간. 컨텍스트가 창을 모르면(버스트 사이클 없는 테스트)
    엔진 기본값으로 떨어진다."""
    end = context.current_full_burst_end
    return FULL_BURST_DURATION if end is None else max(0.0, end - time)
```

이 헬퍼는 **두 모듈이 같이 쓰므로 `backend/app/skill_rules/_helpers.py`에 둔다**
(`from app.burst_cycle import FULL_BURST_DURATION` 포함). 두 모듈은 거기서 import 한다.

`dorothy_serendipity.py`:

```python
    def apply_full_burst_atk(context, caster_slug, time, registry):
        registry.add(
            Effect("atk_percent", fb_atk, "self",
                   _full_burst_window_length(context, time), caster_slug),
            applied_at=time,
        )
```
룰 리스트에서 해당 `buff_rule(...)` 자리를
`SkillRule(trigger="full_burst_enter", action=apply_full_burst_atk)` 로 바꾼다.

`arcana_fortune_mate.py:127,130`도 같은 방식으로 `FULL_BURST_DURATION`을
`_full_burst_window_length(context, time)`으로 바꾼다. **169·180행의
`per_shot_cycle_in_own_status_window` 튜플에 든 `FULL_BURST_DURATION`은 건드리지 않는다**
— 그쪽은 창 길이가 아니라 그녀 자신의 상태 창 길이이고, 테스트가 그 값을 튜플째로
단언한다(`test_skill_rules_arcana_fortune_mate.py:246,256`).

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1892 passed, 3 skipped` (1890 + 신규 2)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/squad_engine.py backend/app/raid_simulator.py \n  backend/app/skill_rules/_helpers.py backend/app/skill_rules/dorothy_serendipity.py \n  backend/app/skill_rules/arcana_fortune_mate.py \n  backend/tests/test_skill_rules_dorothy_serendipity.py
git commit -m "Let 'continuously during Full Burst' buffs follow the real window

Dorothy: Serendipity's Radiant Wings and Arcana: Fortune Mate's Making Memories
are worded 'continuously', meaning until Full Burst ends - they took the module
constant because every window used to be 10 sec. Now that a Burst 3 can move it,
the constant is wrong for exactly the decks this change exists to model, so the
window's own end is published on the context at full_burst_enter and both read
it. A context with no burst cycle still falls back to the base duration."
```

---

### Task 6: 주기 넉의 쿨다운을 깎을 수 있게 한다

**Files:**
- Modify: `backend/app/raid_simulator.py:1408-1412` (`periodic_nukes`의 non-FB 분기)
- Modify: `backend/app/skill_rules/registry.py:767-770` (이사벨의 `periodic_nukes` 항목)
- Test: `backend/tests/test_raid_simulator.py`

**Interfaces:**
- Consumes: Task 3의 없음 (독립)
- Produces:
  - 레지스트리 스탯 이름 `"skill_cooldown_reduction_percent"` (0.75 = 75% 감소)
  - `periodic_nukes` 항목의 선택적 키 `"cooldown_skill_slot": int`
  - `raid_simulator.MIN_COOLDOWN_FACTOR = 0.05`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_raid_simulator.py`에 추가. **틱 개수가 아니라 틱 시각을 단언한다** —
개수만 세면 경계 오차를 놓친다.

```python
def _periodic_times(result):
    return [round(e["time"], 3) for e in result["damage_log"] if e["source"] == "periodic"]


def _run_with_skill_cdr(nuke_spec, reduction=0.75, buff_duration=30.0):
    """`buffer`가 전투 시작에 스킬 쿨감을 자기 자신에게 걸고, 그 주기 넉이 어떻게
    도는지 본다. 아르카나가 이사벨에게 하는 일과 같은 모양이다."""
    rules = {
        "buffer": [buff_rule("battle_start", [
            ("skill_cooldown_reduction_percent", reduction, "self", buff_duration)])],
        "midtier": [],
        "attacker": [],
    }
    return simulate_raid(
        make_deck(),
        rules,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=60.0,
        mode="auto",
        base_crit_rate=0.0,
        periodic_nukes={"buffer": nuke_spec},
    )


def test_a_skill_cooldown_reduction_shortens_a_periodic_nuke_s_interval():
    """스킬 2 쿨다운을 깎는 버프가 살아 있는 동안 주기 넉이 더 자주 터진다 -
    아르카나의 The Magician이 이사벨의 Pointed Feather(쿨 15초)에 하는 일이다.

    개수가 아니라 시각을 단언한다: 개수만 세면 경계에서 한 틱 어긋나도 통과한다."""
    result = _run_with_skill_cdr(
        {"cooldown": 15.0, "percent": 100.0, "cooldown_skill_slot": 2})

    # 첫 틱은 쿨다운 그대로 t=15. 그 뒤 버프가 살아 있는 동안 15 * 0.25 = 3.75 간격.
    # t=30.0에서 버프는 이미 만료(30.0 < 0+30.0이 거짓)라 다음 간격은 다시 15초.
    assert _periodic_times(result) == [15.0, 18.75, 22.5, 26.25, 30.0, 45.0]


def test_the_interval_returns_to_the_base_cooldown_when_the_buff_lapses():
    # 20초짜리 버프: t=15, 18.75 뒤 t=22.5에서는 이미 만료라 그다음은 37.5.
    result = _run_with_skill_cdr(
        {"cooldown": 15.0, "percent": 100.0, "cooldown_skill_slot": 2},
        buff_duration=20.0)

    assert _periodic_times(result) == [15.0, 18.75, 22.5, 37.5, 52.5]


def test_a_periodic_nuke_without_the_skill_slot_tag_ignores_the_reduction():
    """태그가 없으면 그 주기 항목은 스킬 2 쿨다운을 모델한 것이 아니다
    (에이다의 창 내 간격, 스노우 화이트의 자체 주기)."""
    result = _run_with_skill_cdr({"cooldown": 15.0, "percent": 100.0})

    assert _periodic_times(result) == [15.0, 30.0, 45.0]


def test_a_reduction_at_or_above_one_cannot_stall_the_tick_loop():
    # MIN_COOLDOWN_FACTOR가 없으면 간격이 0이 되어 루프가 전진하지 않는다.
    result = _run_with_skill_cdr(
        {"cooldown": 15.0, "percent": 100.0, "cooldown_skill_slot": 2},
        reduction=1.5)

    times = _periodic_times(result)
    assert times[0] == 15.0
    assert all(b > a for a, b in zip(times, times[1:]))
```

파일 상단 import에 `buff_rule`이 없으면
`from app.skill_rules._helpers import buff_rule`를 더한다.

**주의:** `_run_with_skill_cdr`가 `always`로 도는지부터 확인하려면 태그 없는 테스트가
`[15.0, 30.0, 45.0]`을 내는 것이 그 역할을 한다 — 주기 넉이 아예 안 돌면 빈 리스트가 되어
그 테스트가 먼저 실패한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_raid_simulator.py -q -k "skill_cooldown"`
Expected: FAIL — 틱이 `[15.0, 30.0, 45.0]`으로만 난다.

- [ ] **Step 3: 구현**

`backend/app/raid_simulator.py` 모듈 상단 상수 근처:

```python
# 스킬 쿨다운 감소의 하한 배수. 감소가 100%에 닿으면 주기 루프가 전진하지 않는다.
# 오늘 데이터로는 스킬 쿨감을 주는 유닛이 아르카나 하나뿐이라(75%) 겹칠 수 없고,
# 그래서 합산 규칙이 가산인지 승산인지는 알 수 없다 - 이 상수는 그 규칙이 아니라
# 무한 루프 방어다.
MIN_COOLDOWN_FACTOR = 0.05
```

`periodic_nukes`의 `else` 분기(고정 간격) 를 바꾼다:

```python
        else:
            skill_slot = spec.get("cooldown_skill_slot")
            target = target_for(slug)
            tick = cooldown
            while tick < fight_duration:
                _tick(tick)
                factor = 1.0
                if skill_slot == 2:
                    reduction = registry.total_for(
                        "skill_cooldown_reduction_percent", target, tick)
                    factor = max(MIN_COOLDOWN_FACTOR, 1.0 - reduction)
                tick += cooldown * factor
```

`backend/app/skill_rules/registry.py`의 이사벨 항목:

```python
    "isabel": lambda sv: {
        "cooldown": POINTED_FEATHER_COOLDOWN,
        "percent": pointed_feather_percent(sv),
        # Pointed Feather는 그녀의 스킬 2다 - 아르카나의 The Magician이 깎는 바로
        # 그 쿨다운. 태그가 없는 주기 항목은 스킬 쿨다운을 모델한 것이 아니므로
        # (에이다의 창 내 간격, 스노우 화이트의 자체 주기) 감소를 받지 않는다.
        "cooldown_skill_slot": 2,
    },
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1896 passed, 3 skipped` (1892 + 신규 4). 아직 아무도 이 스탯을 주지 않으므로
**실제 수치는 변하지 않아야 한다.**

- [ ] **Step 5: 커밋**

```bash
git add backend/app/raid_simulator.py backend/app/skill_rules/registry.py backend/tests/test_raid_simulator.py
git commit -m "Let a periodic nuke's interval answer to a skill-cooldown buff

A skill whose cooldown an ally can cut needs its tick interval read per tick
rather than fixed, and the effect registry already answers 'what is stat X for
unit Y at time T' - so the reduction rides as an ordinary timed stat with no new
bookkeeping. Only entries tagged cooldown_skill_slot=2 collect it: Ada Wong's
in-window interval and Snow White's own cadence are not Skill 2 cooldowns and
must not silently benefit. Isabel's Pointed Feather is tagged; nothing grants
the stat yet, so no damage number moves."
```

---

### Task 7: The Magician의 스킬 2 쿨감을 인코딩한다

**Files:**
- Modify: `backend/app/skill_rules/arcana.py`
- Test: `backend/tests/test_skill_rules_arcana.py`

**Interfaces:**
- Consumes: Task 6의 `"skill_cooldown_reduction_percent"` 스탯, Task 4의 `wheel_active`
- Produces: 없음

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_magician_also_cuts_the_targets_skill_2_cooldown():
    # "The Magician: Cooldown of Skill 2 ▼ 75% for 15 sec."
    ctx = _b3_context()
    ctx.burst_used_this_cycle.update({"arcana", "electric-b3", "fire-b3"})
    ctx.record_burst_time("arcana", 2.5)
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=7.6)

    assert registry.total_for("skill_cooldown_reduction_percent", ELECTRIC_B3, now=7.6) == 0.75
    # 대상 부분집합 밖에는 안 간다
    assert registry.total_for("skill_cooldown_reduction_percent", FIRE_B3, now=7.6) == 0.0
    # 15초짜리다
    assert registry.total_for("skill_cooldown_reduction_percent", ELECTRIC_B3, now=22.7) == 0.0


def test_magician_skill_2_cooldown_cut_needs_the_wheel_too():
    ctx = _b3_context()
    ctx.burst_used_this_cycle.update({"arcana", "electric-b3"})
    ctx.record_burst_time("arcana", 2.5)
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"arcana": build()}, ctx, registry, time=12.6)
    assert registry.total_for("skill_cooldown_reduction_percent", ELECTRIC_B3, now=12.6) == 0.0
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_arcana.py -q -k "skill_2"`
Expected: FAIL — `0.0 != 0.75`

- [ ] **Step 3: 구현**

`backend/app/skill_rules/arcana.py`의 `build_arcana_rules` 안, 값 읽는 자리에 두 줄 추가:

```python
    magician_skill2_cdr = float(awakened["description_value_02"]) / 100
    magician_skill2_cdr_duration = float(awakened["description_value_03"])
```

Magician의 `member_subset_buff_rule`에 튜플을 하나 더 얹는다:

```python
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("attack_damage_up", magician_attack_damage, magician_duration),
             ("skill_cooldown_reduction_percent", magician_skill2_cdr,
              magician_skill2_cdr_duration)],
            time_condition=wheel_active,
        ),
```

- [ ] **Step 4: 독스트링의 "Not modeled" 블록을 고친다**

Task 4에서 남긴 The Magician 관련 문단을 지우고, Modeled 목록의 Magician 항목에 더한다:

```
- "The Magician" (skills[0]) / "Strength" (skills[1]) first bullets: on Full
  Burst end, all Burst 3 Electric Code allies who previously cast their Burst
  Skill - if Arcana is still in Wheel of Fortune status - get Attack damage
  +180% and Skill 2 cooldown -75% (Magician, 15 sec each) and ATK +180% of
  caster's ATK (Strength, 15 sec). The Skill 2 cut has exactly one consumer:
  Isabel's Pointed Feather (Skill 2, cooldown 15 sec). The other Electric
  Burst-3 units with cooldown-driven damage carry no skill cooldown at all -
  Jill Valentine's Acid Ammo and Ada Wong's Flash Grenade tick on an interval
  inside their own window, and Ein's Feather Shot is a summon cadence.
```

「Not modeled」 항목이 하나도 안 남으면 그 섹션을 지우지 말고 아래를 남긴다:

```
Not modeled: nothing. All six bullets are encoded.
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1898 passed, 3 skipped` (1896 + 신규 2)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/skill_rules/arcana.py backend/tests/test_skill_rules_arcana.py
git commit -m "Encode The Magician's Skill 2 cooldown cut

Its deferral reason was wrong rather than stale: it claimed no Electric Burst-3
ally has a cooldowned Skill 2, and Isabel's Pointed Feather is one. Checking the
other three closes the list - Jill Valentine, Ada Wong and Ein all tick on an
interval or a summon cadence, not a skill cooldown - so the bullet has exactly
one consumer, and it is the same unit whose Full Burst shortening opens the gate
these bullets sit behind. Arcana's six bullets are now fully encoded."
```

---

### Task 8: 상호작용 테스트 · 뮤테이션 · 문서 · 검증

**Files:**
- Create: `backend/tests/test_interaction_arcana_isabel.py`
- Modify: `backend/app/skill_rules/isabel.py`, `backend/app/skill_rules/modernia.py` (독스트링)
- Modify: `docs/encoded-nikkes.md`, `docs/engine-gaps.md`, `docs/insights.md`,
  `.claude/skills/nikke-skill-encoding/references/special-mechanics.md`, `docs/roadmap.md`

**Interfaces:**
- Consumes: Task 1~7 전부
- Produces: 없음 (마무리)

- [ ] **Step 1: 상호작용 테스트를 쓴다**

`backend/tests/test_interaction_arcana_isabel.py` 신규. 기존 상호작용 테스트
(`ls backend/tests/test_interaction_*.py`) 하나를 열어 픽스처 형태를 그대로 따른다.

```python
"""아르카나 x 이사벨: 풀 버스트를 줄이는 Burst 3만이 수레바퀴 게이트를 연다.

아르카나의 조건부 불릿 셋은 풀 버스트 종료 시에 그녀가 아직 수레바퀴 상태인지 묻는다.
그녀는 버스트 스테이지 2에서 시전하므로 표준 10초 창에서는 항상 만료돼 있고, 창을
5초로 줄이는 이사벨과 같은 사이클에 터질 때만 조건이 성립한다.
"""
```

본문. **좌석 순서를 직접 고정한다** — `feasible_orderings`로 탐색시키면 테스트가 좌석
선택에 의존하게 된다. `burst_cycle`은 티어별로 가장 왼쪽의 준비된 멤버를 쏘므로 아르카나와
이사벨을 각자 티어의 첫 자리에 둔다. 로스터는 **합성 스탯**으로 만든다(동기화 로스터는
git에 없다).

```python
from app.deck_search import BossProfile, evaluate_deck
from app.models import UserNikkeState
from app.user_roster import load_roster

BOSS = BossProfile(enemy_def=0, fight_duration=60.0, element="Iron",
                   gauge_charge_time=2.4, core_hittable=False,
                   part_destructible=False, effective_range_band=None)


def _specs(slugs):
    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200, "core_level": 0,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in slugs
    ]
    specs, excluded = load_roster(states)
    assert not excluded, f"not usable: {excluded}"
    by_slug = {s.slug: s for s in specs}
    return [by_slug[slug] for slug in slugs]


def _run(slugs):
    return evaluate_deck(_specs(slugs), BOSS)


def _damage(result, slug, source=None):
    return sum(e["damage"] for e in result["damage_log"]
               if e["slug"] == slug and (source is None or e["source"] == source))


def _periodic_ticks(result, slug):
    return len([e for e in result["damage_log"]
                if e["slug"] == slug and e["source"] == "periodic"])
```

**구현자에게:** `BossProfile(...)`의 인자 이름은 `backend/app/deck_search.py:186` 부근의
정의를 열어 실제 필드에 맞출 것. 위 목록에 없는 필수 필드가 있으면 더한다.

`liter`(B1) · `crown`(B2) 을 채움용으로 쓴다. 세 테스트:

```python
def test_the_bullets_land_when_isabel_opens_the_cycle():
    """이사벨이 창을 5초로 줄이면 아르카나의 수레바퀴가 풀 버스트 종료까지 살아남아
    Magician/Strength/Death가 발동한다."""
    with_isabel = _run(["liter", "arcana", "crown", "isabel", "cinderella"])
    # Strength(자ATK 180% flat) + Magician(공댐 +180%)을 받은 이사벨의 딜이
    # 아르카나를 뺀 같은 자리 대비 크게 높아야 한다.
    without_arcana = _run(["liter", "crown", "moran", "isabel", "cinderella"])
    assert _damage(with_isabel, "isabel") > _damage(without_arcana, "isabel") * 1.2


def test_the_bullets_do_not_land_behind_a_burst3_that_keeps_the_window_at_ten_seconds():
    """네온: 비전 아이도 전기 B3라 Magician/Strength의 대상 조건은 만족하지만,
    풀 버스트를 줄이지 않으므로 아르카나의 게이트가 열리지 않는다."""
    from app.effects import EffectRegistry  # noqa: F401  (문서용)

    result = _run(["liter", "arcana", "crown", "neon-vision-eye", "cinderella"])
    baseline = _run(["liter", "moran", "crown", "neon-vision-eye", "cinderella"])
    # 아르카나의 무조건 불릿(스쿼드 ATK 5%·공댐 7.5%)만 남으므로 차이가 작아야 한다.
    ratio = _damage(result, "neon-vision-eye") / _damage(baseline, "neon-vision-eye")
    assert ratio < 1.2, (
        "네온이 Magician/Strength를 받고 있다 - 이사벨 없이 게이트가 열렸다는 뜻")


def test_isabel_pointed_feather_ticks_more_often_with_arcana_seated():
    """The Magician의 스킬 2 쿨감(-75%, 15초)이 이사벨의 Pointed Feather에 닿는다."""
    with_arcana = _run(["liter", "arcana", "crown", "isabel", "cinderella"])
    without_arcana = _run(["liter", "moran", "crown", "isabel", "cinderella"])

    assert _periodic_ticks(with_arcana, "isabel") > _periodic_ticks(without_arcana, "isabel")
```

**구현자에게 — 두 가지 주의:**

1. `moran`은 아르카나와 같은 Burst 2인 **대조군 채움**이다. 이 저장소에 인코딩돼 있는지
   먼저 확인할 것(`python -c "import sys; sys.path.insert(0,'backend'); from app.skill_rules.registry import ENCODED_SLUGS; print([s for s in ENCODED_SLUGS if 'moran' in s])"`).
   없으면 다른 B2 인코딩 유닛으로 바꾼다. **대조군은 스킬 쿨감도 FB 델타도 없는 B2여야
   한다** — `FULL_BURST_DURATION_DELTA`에 없고 `arcana`가 아니면 된다.
2. 배수 임계(`1.2`)는 자리표시가 아니라 **실제로 재고 나서 확정할 것.** 먼저 위 세
   테스트를 `assert` 없이 값만 print 하도록 돌려 실제 비율을 보고, 여유를 둔 임계를 박는다.
   너무 빡빡하면 무관한 변경에 깨지고, 너무 헐거우면 아무것도 안 지킨다. **확정한 실제
   값을 테스트 주석에 남길 것.**

- [ ] **Step 2: 통과를 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_interaction_arcana_isabel.py -q`
Expected: PASS 3개

- [ ] **Step 3: 뮤테이션 확인 — 셋을 되돌려 각각 깨지는지 본다**

「테스트가 잡는다고 적은 것은 실제로 깨보고 확인할 것」. 하나씩 되돌리고 스위트를 돌린 뒤
**반드시 원복**한다.

| 되돌릴 것 | 깨져야 하는 테스트 |
|---|---|
| `FULL_BURST_DURATION_DELTA["isabel"]`를 `0.0`으로 | Task 2의 registry 테스트 + Task 8의 상호작용 1·2 |
| 아르카나의 `time_condition=wheel_active`를 지움 | Task 4의 게이트 테스트 + 상호작용 2 |
| 이사벨의 `"cooldown_skill_slot": 2`를 지움 | Task 6의 태그 테스트 + 상호작용 3 |

**어느 하나라도 스위트가 초록으로 남으면 그 테스트는 아무것도 안 지키고 있는 것이므로,
보고하고 테스트를 고칠 것.**

- [ ] **Step 4: 검증 — 캘리브레이션이 움직이지 않아야 한다**

Run: `PYTHONIOENCODING=utf-8 python scripts/measure_record_calibration.py 2>&1 | grep -E "combined|within"`

Expected (**정확히 이 값**):
```
combined   1.078x   over 25 units
within +-15%: 17/25
```

기록 덱 5개에 이사벨·모더니아·아르카나·소다가 하나도 없으므로 이 값들은 **한 자리도
움직이면 안 된다.** 움직였다면 변경이 의도 밖으로 샌 것이다 — **멈추고 보고할 것.**

- [ ] **Step 5: 검증 — 제보된 증상과 두 덱**

```bash
PYTHONIOENCODING=utf-8 python scripts/measure_deck_breakdown.py --deck anis-star,arcana,isabel,crown,cinderella
PYTHONIOENCODING=utf-8 python scripts/measure_deck_breakdown.py --deck anis-star,arcana,crown,cinderella,neon-vision-eye
```

기대:
- 네온 덱(이사벨 없음)은 세 불릿을 **통째로 잃는다** — 변경 전 8.42B에서 크게 내려간다.
- 이사벨 덱은 탐색이 **이사벨을 신데렐라 왼쪽으로** 옮겨야 조합이 성립한다. 좌석 순서가
  바뀌는지, 이사벨의 `periodic` 항목이 오르는지 확인한다.

두 출력을 그대로 최종 보고에 붙일 것.

- [ ] **Step 6: 문서를 고친다**

- `backend/app/skill_rules/isabel.py` — 독스트링의 "Not modeled" 문단을 「모델됨」으로.
  Pointed Feather가 `cooldown_skill_slot=2`로 태그돼 아르카나의 Magician을 받는다는 것도
  적는다.
- `backend/app/skill_rules/modernia.py` — New World의 FB +5초가 모델됨을 적는다.
- `docs/encoded-nikkes.md` — 아르카나·이사벨 행을 ⚠에서 ✅로 되돌리고, 무엇이 닫혔는지
  한 줄로. 모더니아 행도 갱신.
- `docs/engine-gaps.md` — gap #22를 `~~22~~ ... **완료 (2026-08-05)**`로. 소비자 목록에
  아르카나(간접)·도로시·포츈메이트를 적는다.
- `docs/insights.md` — 「`own_burst_fired_this_cycle()`가 full_burst_end에서 UNSOUND」
  항목에 **해소되었음**과 새 조건 이름(`own_burst_status_active`)을 덧붙인다. 교훈
  (빼기를 할 것 / 상태가 켜지길 원하는지 꺼지길 원하는지 물을 것)은 **남긴다**.
- `.claude/skills/nikke-skill-encoding/references/special-mechanics.md` — 「If self is in
  status X」 항목에서 「오늘은 표현할 수 없다」는 문장을 지우고 `own_burst_status_active`를
  쓰라고 적는다. `FULL_BURST_DURATION`이 전역 상수라는 문장도 고친다.
- `docs/roadmap.md` — To-Do에 이번 작업 항목을 `[x]`로 추가(소다 항목 바로 위). 스펙·계획
  경로와 커밋 범위, 최종 기준선을 적는다.

- [ ] **Step 7: 최종 스위트**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: `1901 passed, 3 skipped` (1898 + 상호작용 3)

- [ ] **Step 8: 커밋**

```bash
git add backend/tests/test_interaction_arcana_isabel.py backend/app/skill_rules/isabel.py backend/app/skill_rules/modernia.py docs/encoded-nikkes.md docs/engine-gaps.md docs/insights.md docs/roadmap.md .claude/skills/nikke-skill-encoding/references/special-mechanics.md
git commit -m "Pin the Arcana x Isabel pairing and close engine gap 22

The interaction test is the only one that pins what this change is for: the
three bullets land behind a Burst 3 that shortens Full Burst and do not land
behind one that does not, and Isabel's Pointed Feather ticks more often with
Arcana seated. Mutating each of the three new levers was checked to break a
test rather than assumed to.

Calibration is unchanged at 1.078x over 25 units, 17/25 within 15% - none of the
affected units sits in a recorded deck, so this moves deck recommendations only."
```

---

## Self-Review

**Spec coverage:**

| 스펙 절 | 태스크 |
|---|---|
| A.1 사이클별 FB 길이 | 1, 2 |
| A.2 시간을 아는 조건 | 3 |
| A.3 실제 창 길이를 아는 버프 | 5 |
| B.1 아르카나 게이트 교체 | 4 |
| B.2 이사벨·모더니아 | 2, 8 |
| B.3 파급 | 2, 5, 8 |
| C.1~C.5 스킬 2 쿨감 | 6, 7 |
| D 테스트 | 각 태스크 + 8 |
| E 검증 기준 | 8 (Step 4·5) |
| F 한계 | 코드 변경 없음 — 문서에만 남는다 |

**Type consistency:** `full_burst_duration_delta`(멤버 dict 키) ·
`FULL_BURST_DURATION_DELTA`(registry 맵) · `get_full_burst_duration_delta`(조회기) ·
`time_condition`(SkillRule 필드) · `own_burst_status_active`(조건 팩토리) ·
`current_full_burst_end`(SquadContext 필드) · `cooldown_skill_slot`(periodic 항목 키) ·
`skill_cooldown_reduction_percent`(레지스트리 스탯) · `MIN_FULL_BURST_DURATION` ·
`MIN_COOLDOWN_FACTOR` — 태스크 간 표기 일치 확인함.

**테스트 수 누적:** 1874 → 1879(T1) → 1883(T2) → 1888(T3) → 1890(T4) → 1892(T5) →
1896(T6) → 1898(T7) → 1901(T8). 각 태스크의 기대치가 어긋나면 그 자리에서 멈춘다.
