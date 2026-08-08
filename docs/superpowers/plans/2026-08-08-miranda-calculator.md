# 미란다 계산기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 계산기 탭에 서브탭을 두고, 미란다를 포함한 덱 5인을 편성하면 파워업!(버스트)과 웨이크업! 3번불릿을 누가 받는지 뱃지로 답하고, 못 받는 니케에게는 받는 데 필요한 오버로드 공격력을 알려주는 화면을 만든다.

**Architecture:** 엔진의 `top_atk_slugs`가 이미 하고 있는 실시간 최종 공격력 랭킹의 **결과를 opt-in으로 기록**해(`SquadContext.target_grants`) 읽는다. 대상 판정을 계산기가 다시 구현하지 않는 것이 이 설계의 전부다. 오버로드 임계값은 닫힌형이 아니라 실제 시뮬을 이진탐색해서 구한다 — `evaluate_deck` 1회가 0.107초다.

**Tech Stack:** 백엔드 FastAPI + pydantic + pytest / 프론트 React + Vite + TypeScript + vitest + @testing-library/react

**설계문서:** `docs/superpowers/specs/2026-08-08-miranda-calculator-design.md` — 판단의 근거는 전부 거기 있다. 이 계획은 그 문서를 읽었다고 가정하지 않지만, 어떤 결정이 "왜" 그런지 궁금하면 절 번호를 따라가면 된다.

## Global Constraints

- **작업 브랜치는 `wip/miranda-calculator`다.** 이미 만들어져 있고 설계 커밋 4개가 올라가 있다.
- **백엔드 테스트는 반드시 `backend/`에서 돌린다.** 루트에서 돌리면 `No module named 'app'`으로 수집이 깨진다. 명령: `cd backend && python -m pytest`
- **프론트 테스트는 타입을 보지 않는다.** `npm test`(vitest)와 별개로 `npx tsc -b --noEmit`을 반드시 따로 돌린다. 둘 다 `frontend/`에서.
- **기준선**: 백엔드 2145 passed / 3 skipped, 프론트 638 passed / 62 skipped, 타입에러 0. 이 계획이 끝났을 때 실패는 0이어야 한다.
- **워크트리에 `tools/collect-blablalink/node_modules`가 없다.** `tools/` 아래 `parse.test.js`가 깨지는 것은 이 작업과 무관한 기존 상태다. 백엔드/프론트 스위트에는 포함되지 않는다.
- **딜 수치는 1비트도 움직이면 안 된다.** 새 계측은 전부 기본 off이고, 기존 두 컴포넌트의 새 prop은 전부 기본값이 오늘의 동작이다. `total_damage`가 바뀌는 변경이 나오면 그것은 버그다.
- **한글 UI 문구는 정확한 맞춤법으로.** 기존 화면의 말투(친근한 해요체)를 따른다.
- **코드 주석은 WHAT과 WHY만.** "예전엔 이랬다" / "이 부분을 바꿨다"는 절대 쓰지 않는다.
- **커밋 메시지는 한글**, 기존 로그 스타일(제목 한 줄 + 빈 줄 + 이유)을 따른다.

---

### Task 1: `SquadContext`에 대상 기록 훅

랭킹 결과를 남길 자리를 만든다. 기본은 `None`이라 아무것도 기록하지 않는다.

**Files:**
- Modify: `backend/app/squad_engine.py:27-35` (`SquadContext.__init__`), `backend/app/squad_engine.py:202-249` (`top_atk_slugs`)
- Test: `backend/tests/test_squad_engine.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `SquadContext(..., target_grants: list[dict] | None = None)` — 생성자 마지막 키워드 인자
  - `SquadContext.target_grants` 속성
  - `SquadContext.top_atk_slugs(n, caster_slug, registry, time, member_filter=None, include_caster=False, grant_stats: tuple[str, ...] | None = None) -> list[str]`
  - 기록 한 건의 모양: `{"caster": str, "time": float, "stats": list[str], "targets": list[str]}`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_squad_engine.py` 맨 아래에 붙인다.

```python
def test_top_atk_slugs_records_the_grant_when_asked():
    log = []
    ctx = SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Fire"),
            SquadMember("scarlet", burst_tier=3, element="Fire"),
            SquadMember("blast", burst_tier=1, element="Wind"),
        ],
        base_atk={"miranda": 50000, "scarlet": 70000, "blast": 60000},
        target_grants=log,
    )
    registry = EffectRegistry()
    ctx.top_atk_slugs(1, "miranda", registry, time=2.5, grant_stats=("crit_rate",))
    assert log == [{"caster": "miranda", "time": 2.5,
                    "stats": ["crit_rate"], "targets": ["scarlet"]}]


def test_top_atk_slugs_records_nothing_without_grant_stats():
    # 스탯 이름을 안 넘기는 호출자(맥스웰·레오나·나가·마나·소다)는 기록에 안 남는다 -
    # 무슨 불릿인지 말하지 않은 호출을 무슨 불릿인지 아는 척 적을 수 없다.
    log = []
    ctx = SquadContext(
        [SquadMember("a", burst_tier=1, element="Fire"),
         SquadMember("b", burst_tier=3, element="Fire")],
        base_atk={"a": 1, "b": 2},
        target_grants=log,
    )
    ctx.top_atk_slugs(1, "a", EffectRegistry(), time=0.0)
    assert log == []


def test_top_atk_slugs_records_nothing_without_a_log():
    # 기본 컨텍스트는 로그가 없다 - grant_stats를 넘겨도 조용하다.
    ctx = SquadContext(
        [SquadMember("a", burst_tier=1, element="Fire"),
         SquadMember("b", burst_tier=3, element="Fire")],
        base_atk={"a": 1, "b": 2},
    )
    assert ctx.target_grants is None
    assert ctx.top_atk_slugs(1, "a", EffectRegistry(), 0.0, grant_stats=("atk_percent",)) == ["b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_squad_engine.py -k "records" -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'target_grants'`

- [ ] **Step 3: Write minimal implementation**

`SquadContext.__init__`의 인자 목록 끝(`core_hittable: bool = False,` 다음)에 추가:

```python
        target_grants: list[dict] | None = None,
```

본문에서 `self.core_hittable` 대입 근처에 추가:

```python
        # top-N 대상형 버프가 누구에게 갔는지의 기록. None이면 아무것도 남기지
        # 않는다 - 탐색은 한 요청에 수만 번 돌므로 기본이 off여야 한다.
        # 미란다 계산기가 이 로그를 읽는다(app/miranda_targets.py).
        self.target_grants: list[dict] | None = target_grants
```

`top_atk_slugs`의 시그니처를 바꾸고:

```python
    def top_atk_slugs(self, n: int, caster_slug: str, registry, time: float,
                      member_filter=None, include_caster: bool = False,
                      grant_stats: tuple[str, ...] | None = None) -> list[str]:
```

docstring 끝에 한 문단을 더한다:

```
        `grant_stats`는 호출자가 지금 주려는 스탯 이름들이다. 넘기면 이 판정이
        `target_grants`에 기록된다 - 대상 집합만으로는 한 시전자의 서로 다른
        불릿을 구분할 수 없어서(둘 다 같은 랭킹을 쓴다), 무슨 불릿인지는 호출자가
        선언해야만 알 수 있다.
```

`return ranked[:n]`을 다음으로 교체:

```python
        targets = ranked[:n]
        if grant_stats is not None and self.target_grants is not None:
            self.target_grants.append({
                "caster": caster_slug, "time": time,
                "stats": list(grant_stats), "targets": list(targets),
            })
        return targets
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_squad_engine.py -v`
Expected: PASS (새 3개 포함, 기존 전부 그대로)

- [ ] **Step 5: Commit**

```bash
git add backend/app/squad_engine.py backend/tests/test_squad_engine.py
git commit -m "top-N 대상 판정을 기록할 자리를 만든다

미란다 계산기가 「누가 받는가」에 답하려면 랭킹 결과가 필요한데, 그 랭킹을
계산기가 다시 구현하면 에러 없이 틀린 답을 낸다. 엔진이 이미 하고 있는
판정을 기록해 읽는다.

기본은 None이라 아무것도 기록하지 않는다 - 탐색은 한 요청에 수만 번 돈다.
무슨 불릿인지는 grant_stats로 호출자가 선언한다: 대상 집합만으로는 한
시전자의 두 불릿을 구분할 수 없다."
```

---

### Task 2: 미란다의 두 불릿이 자기 스탯 이름을 넘긴다

`highest_atk_buff_rule`(파워업!)과 `round_buff_rule`의 top_atk 분기(웨이크업!3)만 기록된다.

**Files:**
- Modify: `backend/app/skill_rules/_helpers.py:126-133` (`_resolve_scope`), `:136-175` (`highest_atk_buff_rule`), `:205-227` (`round_buff_rule`)
- Test: `backend/tests/test_skill_helpers.py`

**Interfaces:**
- Consumes: Task 1의 `top_atk_slugs(..., grant_stats=...)`, `SquadContext(target_grants=...)`
- Produces:
  - `_resolve_scope(scope_spec, context, caster_slug, registry, time, grant_stats=None)` — 인자 하나 추가
  - `highest_atk_buff_rule`이 자기 `buffs`의 스탯 이름을 기록에 싣는다
  - `round_buff_rule`이 버프별로 그 스탯 이름 하나를 기록에 싣는다

- [ ] **Step 1: Write the failing test**

`backend/tests/test_skill_helpers.py` 맨 아래에 붙인다. 파일 상단의 import에 필요한 이름이 없으면 더한다 (`from app.skill_rules._helpers import highest_atk_buff_rule, round_buff_rule`, `from app.effects import EffectRegistry`, `from app.squad_engine import SquadContext, SquadMember`).

```python
def _three_member_context(log):
    return SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Fire"),
            SquadMember("scarlet", burst_tier=3, element="Fire"),
            SquadMember("blast", burst_tier=2, element="Wind"),
        ],
        base_atk={"miranda": 50000, "scarlet": 90000, "blast": 80000},
        target_grants=log,
    )


def test_highest_atk_buff_rule_records_its_own_stats():
    log = []
    ctx = _three_member_context(log)
    rule = highest_atk_buff_rule("own_burst_activate", 2, [
        ("atk_percent", 0.404, 10.0),
        ("other_critical_damage_sources", 0.5623, 10.0),
    ])
    rule.action(ctx, "miranda", 5.0, EffectRegistry())
    assert log == [{
        "caster": "miranda", "time": 5.0,
        "stats": ["atk_percent", "other_critical_damage_sources"],
        "targets": ["scarlet", "blast"],
    }]


def test_round_buff_rule_records_a_top_atk_scope():
    log = []
    ctx = _three_member_context(log)
    rule = round_buff_rule("full_burst_enter",
                           [("crit_rate", 0.8542, ("top_atk", 1))], shots=1)
    rule.action(ctx, "miranda", 5.000001, EffectRegistry())
    assert log == [{
        "caster": "miranda", "time": 5.000001,
        "stats": ["crit_rate"], "targets": ["scarlet"],
    }]


def test_round_buff_rule_records_nothing_for_a_static_scope():
    # "squad"/"self"는 랭킹을 안 쓰므로 기록할 판정 자체가 없다.
    log = []
    ctx = _three_member_context(log)
    rule = round_buff_rule("full_burst_enter", [("crit_rate", 0.1, "squad")], shots=1)
    rule.action(ctx, "miranda", 1.0, EffectRegistry())
    assert log == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_skill_helpers.py -k "records" -v`
Expected: FAIL — `assert [] == [{...}]` (기록이 안 남는다)

- [ ] **Step 3: Write minimal implementation**

`_resolve_scope`:

```python
def _resolve_scope(scope_spec, context, caster_slug, registry, time, grant_stats=None):
    """A buff's scope can be a static string ("squad", "self", "element:X") or a
    dynamic ("top_atk", n) that resolves - at application time - to the n allies
    with the highest final ATK, encoded as a "slugs:a,b" scope.

    `grant_stats`는 이 판정이 무슨 스탯을 주는지로, 대상 기록에 실린다
    (SquadContext.top_atk_slugs). 정적 스코프에는 판정 자체가 없어 무시된다."""
    if isinstance(scope_spec, tuple) and scope_spec[0] == "top_atk":
        slugs = context.top_atk_slugs(scope_spec[1], caster_slug, registry, time,
                                      grant_stats=grant_stats)
        return "slugs:" + ",".join(slugs)
    return scope_spec
```

`highest_atk_buff_rule`의 `action` 안, `targets = ...` 호출에 인자를 더한다:

```python
    def action(context, caster_slug, time, registry):
        targets = context.top_atk_slugs(n, caster_slug, registry, time,
                                        member_filter=member_filter,
                                        include_caster=include_caster,
                                        grant_stats=tuple(stat for stat, _, _ in buffs))
```

`round_buff_rule`의 `action` 안, `_resolve_scope` 호출에 인자를 더한다:

```python
    def action(context, caster_slug, time, registry):
        for stat, value, scope_spec in buffs:
            scope = _resolve_scope(scope_spec, context, caster_slug, registry, time,
                                   grant_stats=(stat,))
```

- [ ] **Step 4: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS — 2145 + 6 = 2151 passed / 3 skipped. 실패 0.

`_resolve_scope`는 다른 곳에서도 불리므로 전체 스위트를 돌려서 호출부가 안 깨졌는지 본다.

- [ ] **Step 5: Commit**

```bash
git add backend/app/skill_rules/_helpers.py backend/tests/test_skill_helpers.py
git commit -m "top-N 대상형 룰 둘이 자기 스탯 이름을 기록에 싣는다

미란다의 파워업!과 웨이크업!3은 같은 랭킹을 쓰므로 대상 집합만으로는
구분되지 않는다. 주는 스탯이 그 둘을 가르는 유일한 선언이다.

이 두 헬퍼는 미란다 전용이 아니라 공유 헬퍼라 grant_stats가 무조건 넘어간다 -
top-N 대상형 버프는 전부 자기 스탯을 선언해 기록되고, 소비자가 시전자(caster)로
걸러 읽는다."
```

---

### Task 3: 시뮬레이터가 기록을 밖으로 내보낸다

**Files:**
- Modify: `backend/app/raid_simulator.py:674-713` (`_simulate_raid_once` 시그니처), `:739-741` (`SquadContext` 생성), `:1841-1845` (반환)
- Modify: `backend/app/deck_search.py:440-463` (`evaluate_deck`)
- Test: `backend/tests/test_raid_simulator.py`

**Interfaces:**
- Consumes: Task 1의 `SquadContext(target_grants=...)`
- Produces:
  - `simulate_raid(..., collect_target_grants: bool = False)` → 결과 dict에 `"target_grants": list[dict]` (플래그가 켜졌을 때만 키가 존재)
  - `evaluate_deck(ordered_deck, boss, max_bursts=None, collect_target_grants=False)`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_raid_simulator.py` 맨 아래에 붙인다. 파일 안의 기존 미란다 테스트(`test_miranda_top_atk_burst_buff_reaches_the_top_two_carries_end_to_end`)와 같은 덱 모양을 쓴다.

```python
def test_target_grants_are_absent_unless_asked_for():
    # 계측이 기본 off라는 것이 탐색 핫패스 무변경의 증거다.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    assert "target_grants" not in result


def test_target_grants_carry_mirandas_two_bullets_when_asked_for():
    from app.skill_rules.miranda import build_miranda_rules

    miranda_values = {
        "wake_up": {
            "description_value_01": "32.99", "description_value_02": "10",
            "description_value_03": "30.1", "description_value_04": "10",
            "description_value_05": "23.7", "description_value_06": "10",
            "description_value_07": "1", "description_value_08": "85.42",
            "description_value_09": "1",
        },
        "powering_up": {
            "description_value_01": "2", "description_value_02": "40.4",
            "description_value_03": "10", "description_value_04": "56.23",
            "description_value_05": "10",
        },
    }
    deck = [
        {"slug": "miranda", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "carry_b", "burst_tier": 2, "element": "Fire", "cooldown": 20.0},
        {"slug": "carry_a", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]
    result = simulate_raid(
        deck,
        {"miranda": build_miranda_rules(miranda_values), "carry_b": [], "carry_a": []},
        burst_damage_percents={},
        base_stats={"miranda": {"atk": 40000, "def": 0, "max_hp": 0},
                    "carry_b": {"atk": 80000, "def": 0, "max_hp": 0},
                    "carry_a": {"atk": 90000, "def": 0, "max_hp": 0}},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        collect_target_grants=True,
    )
    grants = result["target_grants"]
    powering_up = [g for g in grants if "atk_percent" in g["stats"]]
    wake_up = [g for g in grants if "crit_rate" in g["stats"]]
    assert len(powering_up) == 1 and len(wake_up) == 1
    assert powering_up[0]["targets"] == ["carry_a", "carry_b"]
    assert wake_up[0]["targets"] == ["carry_a"]
    # 파워업!은 B1 시전 순간, 웨이크업!3은 그 직후 풀버스트 진입 순간.
    assert wake_up[0]["time"] > powering_up[0]["time"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_raid_simulator.py -k "target_grants" -v`
Expected: 첫 번째는 PASS(키가 원래 없다), 두 번째는 FAIL — `TypeError: _simulate_raid_once() got an unexpected keyword argument 'collect_target_grants'`

- [ ] **Step 3: Write minimal implementation**

`_simulate_raid_once`의 인자 목록에서 `full_burst_stage_overrides=None,` **바로 앞**에 추가:

```python
    collect_target_grants=False,
```

`context = SquadContext(` 호출 바로 앞에 추가:

```python
    # 대상 판정 기록은 계산기 화면 전용이라 기본이 off다. 켜져야만 리스트가
    # 생기고, 그래야 탐색이 도는 수만 번의 시뮬이 오늘과 같은 할당을 한다.
    target_grants = [] if collect_target_grants else None
```

`SquadContext(...)` 호출의 마지막 인자(`core_hittable=core_hittable,`) 다음에 추가:

```python
        target_grants=target_grants,
```

반환부(`return {` … `}, _resolve_conditional_fb_deltas(...)`)를 교체:

```python
    result = {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }
    if target_grants is not None:
        result["target_grants"] = target_grants
    return result, _resolve_conditional_fb_deltas(
        context, events, conditional_full_burst_deltas)
```

`backend/app/deck_search.py`의 `evaluate_deck`:

```python
def evaluate_deck(ordered_deck, boss: BossProfile, max_bursts=None,
                  collect_target_grants=False):
```

docstring 끝에 한 문단:

```
    `collect_target_grants`는 top-N 대상형 버프가 누구에게 갔는지를 결과에
    싣는다 - 미란다 계산기(app/miranda_targets.py)가 읽는 기록이고, 기본 off라
    탐색 경로는 오늘 그대로다.
```

`simulate_raid(` 호출의 마지막 인자 다음에 추가:

```python
        collect_target_grants=collect_target_grants,
```

- [ ] **Step 4: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS — 2153 passed / 3 skipped. 실패 0.

- [ ] **Step 5: Commit**

```bash
git add backend/app/raid_simulator.py backend/app/deck_search.py backend/tests/test_raid_simulator.py
git commit -m "시뮬 결과에 대상 판정 기록을 실어 보낸다

플래그가 켜졌을 때만 키가 생긴다. simulate_raid 래퍼는 마지막 패스의
result를 그대로 돌려주므로, 풀버스트 확장이 고정점까지 반복하는 덱에서도
수렴한 패스의 기록이 나온다."
```

---

### Task 4: 타이밍 검증을 회귀로 못박는다

이 태스크는 **테스트만** 만든다. 2026-08-08에 확인한 사실(설계문서 §1.2, §1.3)이 조용히 뒤집히지 않게 하는 것이 전부다.

**Files:**
- Create: `backend/tests/test_miranda_buff_timing.py`

**Interfaces:**
- Consumes: Task 3의 `evaluate_deck(..., collect_target_grants=True)`
- Produces: 없음 (테스트 전용)

- [ ] **Step 1: Write the test file**

```python
"""미란다의 두 대상형 불릿이 언제 대상을 정하고, 그 순간의 「최종 공격력」이
무엇을 세는가.

2026-08-08에 확인한 사실을 고정한다:
- 파워업!(버스트)은 B1 시전 순간에 판정한다 - 같은 순간 뒤이어 터지는 B2/B3의
  버스트 효과는 아직 없다.
- 웨이크업! 3번불릿은 풀버스트 진입 순간에 판정한다 - 같은 사이클 파워업!의
  공격력 버프가 이미 실려 있다.
- 랭킹은 오버로드 공격력을 센다. 표시 공격력에 접혀 있는 값이 아니라 엔진이
  따로 얹는 영구 효과다(app/overload_effects.py).
"""
from app.deck_search import BossProfile, evaluate_deck
from app.models import OverloadOption, SkillLevels, UserNikkeState
from app.user_roster import load_roster

DECK = ["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"]
MAXED = SkillLevels(skill1=10, skill2=10, burst=10)


def a_state(slug, overload_atk=0.0):
    options = ([OverloadOption(name="공격력 증가", value=overload_atk)]
               if overload_atk else [])
    return UserNikkeState(
        character_slug=slug, level=400, hp=500_000.0, atk=100_000.0, def_=10_000.0,
        skill_levels=MAXED, overload_options=options,
    )


def a_run(overload_on=None, overload_atk=12.0):
    """DECK 순서 그대로 좌석을 고정해 한 번 돌린다 - 이 파일이 묻는 것은
    타이밍이지 최적 배치가 아니다."""
    states = [a_state(slug, overload_atk if slug == overload_on else 0.0)
              for slug in DECK]
    specs, _excluded = load_roster(states)
    by_slug = {spec.slug: spec for spec in specs}
    ordered = [by_slug[slug] for slug in DECK]
    return evaluate_deck(ordered, BossProfile(fight_duration=40.0),
                         collect_target_grants=True)


def _grants(result):
    powering_up = [g for g in result["target_grants"]
                   if g["caster"] == "miranda-signature" and "atk_percent" in g["stats"]]
    wake_up = [g for g in result["target_grants"]
               if g["caster"] == "miranda-signature" and "crit_rate" in g["stats"]]
    return powering_up, wake_up


def test_powering_up_judges_at_the_burst_1_cast():
    result = a_run()
    powering_up, _ = _grants(result)
    b1_times = [e["time"] for e in result["events"]
                if e["type"] == "burst" and e["slug"] == "miranda-signature"]
    assert powering_up, "파워업!이 한 번도 판정되지 않았다"
    assert [g["time"] for g in powering_up] == b1_times


def test_wake_up_third_bullet_judges_at_full_burst_entry():
    result = a_run()
    _, wake_up = _grants(result)
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    assert wake_up, "웨이크업!3이 한 번도 판정되지 않았다"
    assert [g["time"] for g in wake_up] == starts


def test_wake_up_ranks_after_powering_up_landed():
    # 같은 사이클 안에서 파워업!이 먼저다. 두 시각이 같은 순간으로 접히면
    # 웨이크업!의 랭킹이 파워업!의 공격력 버프를 못 보게 된다.
    result = a_run()
    powering_up, wake_up = _grants(result)
    assert len(powering_up) == len(wake_up)
    for p, w in zip(powering_up, wake_up):
        assert w["time"] > p["time"]


def test_overload_atk_alone_decides_the_ranking():
    # 표시 공격력이 다섯 다 같으므로, 오버로드가 안 세어지면 다섯이 동점이라
    # 좌석 순서로만 갈린다. ada-wong이 이기면 오버로드가 세어진 것이다.
    without = a_run()
    with_overload = a_run(overload_on="ada-wong")
    powering_up_without, _ = _grants(without)
    powering_up_with, wake_up_with = _grants(with_overload)
    assert "ada-wong" not in powering_up_without[0]["targets"]
    assert powering_up_with[0]["targets"][0] == "ada-wong"
    assert wake_up_with[0]["targets"] == ["ada-wong"]


def test_miranda_never_targets_herself_in_a_five_unit_deck():
    # 원문이 "except caster"이고 후보가 넷이므로 그녀가 채울 빈자리가 없다.
    result = a_run(overload_on="ada-wong")
    powering_up, wake_up = _grants(result)
    for grant in powering_up + wake_up:
        assert "miranda-signature" not in grant["targets"]
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && python -m pytest tests/test_miranda_buff_timing.py -v`
Expected: **PASS 전부.** 이 태스크는 이미 참인 사실을 고정하는 것이므로 실패하면 안 된다.

FAIL이 나면 **거기서 멈추고 보고한다** — 앞선 세 태스크 중 하나가 계측을 잘못 배선했다는 뜻이다. `test_overload_atk_alone_decides_the_ranking`이 `powering_up_without[0]["targets"]`에서 IndexError를 내면 좌석 배치가 풀버스트를 못 여는 것이니 `DECK` 구성을 확인한다(1·1·3 모양이어야 한다: 미란다 B1 / crown B2 / 나머지 셋 B3).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_miranda_buff_timing.py
git commit -m "미란다 두 불릿의 판정 시각을 회귀로 고정한다

파워업!은 B1 시전 순간, 웨이크업!3은 풀버스트 진입 순간에 판정하고 후자의
랭킹이 전자를 반영한다. 두 시각이 한 순간으로 접히면 계산기의 답이 조용히
틀려지므로, 계산기보다 이 사실을 먼저 못박는다.

랭킹이 오버로드 공격력을 센다는 것도 함께 고정한다 - 표시 공격력이 같은
다섯에서 오버로드만으로 순위가 갈리는지를 본다."
```

---

### Task 5: 오버로드 공격력 상한을 테이블에서 뽑는다

**Files:**
- Modify: `backend/app/overload_effects.py` (`max_charge_speed_percent` 바로 아래)
- Test: `backend/tests/test_overload_effects.py`

**Interfaces:**
- Consumes: 없음
- Produces: `overload_effects.max_atk_percent(tables) -> float` — 오늘의 테이블에서 `58.52`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_overload_effects.py` 맨 아래에 붙인다. 파일 상단 import에 없으면 더한다 (`from app.overload_effects import max_atk_percent`, `from app.stat_assembly import load_stat_tables`).

```python
def test_max_atk_percent_is_a_top_roll_on_every_slot():
    # 부위당 최고 굴림 14.63% x 4부위. 상수로 적지 않는 이유는 테이블이
    # 재적합되면 값이 따라가야 하기 때문이다.
    assert max_atk_percent(load_stat_tables()) == 58.52


def test_max_atk_percent_raises_when_the_tables_have_no_atk_type():
    import pytest
    with pytest.raises(KeyError):
        max_atk_percent({"overload": {"type_name": {}, "type_value": {}}})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_overload_effects.py -k max_atk_percent -v`
Expected: FAIL — `ImportError: cannot import name 'max_atk_percent'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/overload_effects.py`의 `max_charge_speed_percent` 함수 **아래**에 추가:

```python
def max_atk_percent(tables) -> float:
    """The most ATK overload alone can grant: a top roll on every gear slot.

    Same shape as max_charge_speed_percent and for the same reason - nothing
    here is written down, so a re-fitted table moves this number without an
    edit. The difference is the arithmetic: charge speed rounds per roll before
    the frame grid sees it, while ATK is used exactly as displayed (see
    granted_percent), so this is a plain sum.

    Raises KeyError if the tables carry no ATK effect type.
    """
    for effect_type, name in tables["overload"]["type_name"].items():
        if NAME_TO_STAT.get(name) != "atk_percent":
            continue
        return overload_value(tables, int(effect_type), MAX_LEVEL) * len(GEAR_SLOTS)
    raise KeyError("the overload tables carry no ATK effect type")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_overload_effects.py -v`
Expected: PASS

`14.63 * 4`는 부동소수에서도 정확히 `58.52`다(2026-08-08 확인). 그래서 구현에도 테스트에도 반올림이 없다 — 상한은 UI 문구에 그대로 나가는 숫자라 어디서 반올림하는지가 계약이고, 필요 없는 반올림을 넣지 않는 것이 그 계약을 가장 단순하게 유지한다.

- [ ] **Step 5: Commit**

```bash
git add backend/app/overload_effects.py backend/tests/test_overload_effects.py
git commit -m "오버로드 공격력 상한을 테이블에서 뽑는다

미란다 계산기가 「상한까지 올려도 못 받는다」를 말하려면 상한이 필요한데,
숫자를 코드에 적으면 테이블 재적합 때 조용히 낡는다. 차지속도가 이미 같은
방식으로 뽑고 있다."
```

---

### Task 6: `miranda_targets.py` — 사이클별 대상 리포트

**Files:**
- Create: `backend/app/miranda_targets.py`
- Test: `backend/tests/test_miranda_targets.py`

**Interfaces:**
- Consumes: Task 3의 `evaluate_deck(..., collect_target_grants=True)`, 기존 `deck_evaluation.evaluate_decks`
- Produces:
  - `MIRANDA_SLUGS = ("miranda", "miranda-signature")`
  - `miranda_slug_in(slugs: Iterable[str]) -> str | None`
  - `miranda_target_report(deck_specs, boss, spec_index, alternatives=None) -> dict`
    반환: `{"seats": [{"slug", "burst_tier"}], "miranda_slug": str, "has_favorite_item": bool, "cycles": [{"index", "powering_up", "wake_up_crit_rate"}], "notes": [str]}`
    (`overload_thresholds`는 Task 7에서 이 dict에 더해진다)

- [ ] **Step 1: Write the failing test**

`backend/tests/test_miranda_targets.py`:

```python
"""덱 5인 중 누가 미란다의 파워업!과 웨이크업!3을 받는가."""
from app.deck_search import BossProfile
from app.miranda_targets import MIRANDA_SLUGS, miranda_slug_in, miranda_target_report
from app.models import SkillLevels, UserNikkeState
from app.user_roster import load_roster

MAXED = SkillLevels(skill1=10, skill2=10, burst=10)
BOSS = BossProfile(fight_duration=180.0)


def a_state(slug, atk=100_000.0):
    return UserNikkeState(
        character_slug=slug, level=400, hp=500_000.0, atk=atk, def_=10_000.0,
        skill_levels=MAXED, overload_options=[],
    )


def a_report(deck, atk_by_slug=None):
    atk_by_slug = atk_by_slug or {}
    states = [a_state(slug, atk_by_slug.get(slug, 100_000.0)) for slug in deck]
    specs, _excluded = load_roster(states)
    spec_index = {spec.slug: spec for spec in specs}
    deck_specs = [spec_index[slug] for slug in deck]
    return miranda_target_report(deck_specs, BOSS, spec_index)


def test_miranda_slug_in_finds_either_build():
    assert miranda_slug_in(["crown", "miranda"]) == "miranda"
    assert miranda_slug_in(["crown", "miranda-signature"]) == "miranda-signature"
    assert miranda_slug_in(["crown", "isabel"]) is None
    assert set(MIRANDA_SLUGS) == {"miranda", "miranda-signature"}


def test_favorite_item_build_grants_two_and_one():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    assert report["miranda_slug"] == "miranda-signature"
    assert report["has_favorite_item"] is True
    assert report["cycles"], "풀 버스트가 한 번도 안 열렸다"
    for cycle in report["cycles"]:
        assert len(cycle["powering_up"]) == 2
        assert len(cycle["wake_up_crit_rate"]) == 1
        assert cycle["wake_up_crit_rate"][0] in cycle["powering_up"]


def test_base_build_grants_one_and_has_no_third_bullet():
    report = a_report(["miranda", "crown", "ada-wong", "cinderella", "isabel"])
    assert report["has_favorite_item"] is False
    for cycle in report["cycles"]:
        assert len(cycle["powering_up"]) == 1
        assert cycle["wake_up_crit_rate"] == []
    assert any("애장품" in note for note in report["notes"])


def test_miranda_is_never_her_own_target():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    for cycle in report["cycles"]:
        assert "miranda-signature" not in cycle["powering_up"]
        assert "miranda-signature" not in cycle["wake_up_crit_rate"]


def test_cycles_are_numbered_from_one_and_are_contiguous():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    assert [c["index"] for c in report["cycles"]] == list(
        range(1, len(report["cycles"]) + 1))


def test_seats_report_the_engines_own_ordering():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    assert len(report["seats"]) == 5
    assert {s["slug"] for s in report["seats"]} == {
        "miranda-signature", "crown", "ada-wong", "cinderella", "isabel"}
    tiers = sorted(s["burst_tier"] for s in report["seats"])
    assert tiers == [1, 2, 3, 3, 3]


def test_a_cycle_miranda_does_not_burst_has_no_powering_up_but_still_wakes_up():
    # 1티어가 둘이면 스케줄러는 덱 순서상 먼저인 하나만 쏜다. 웨이크업!은
    # 미란다의 버스트와 무관하게 매 풀버스트마다 발동하므로 계속 채워진다.
    #
    # 2·1·2 대형이다 - 미란다와 리터가 B1, 크라운이 B2, 나머지 둘이 B3.
    # B1 둘에 B3 셋(2·0·3)은 ALLOWED_SHAPES에 없어 InfeasibleDeck으로 죽는다.
    report = a_report(["miranda-signature", "liter", "crown", "ada-wong", "cinderella"])
    assert report["cycles"]
    # 이것이 이 테스트가 증명하는 것이다: 웨이크업!의 방아쇠는 풀버스트 진입이지
    # 미란다의 버스트가 아니므로, 그녀가 못 쏜 사이클에도 3번불릿은 나간다.
    assert all(cycle["wake_up_crit_rate"] for cycle in report["cycles"])
    # 두 B1은 쿨다운이 같아 스케줄러가 매번 같은 하나를 고른다 - 즉 한쪽은
    # 전부 쏘고 다른 쪽은 한 번도 못 쏜다. 어느 쪽이든 파워업!은 전부이거나
    # 전무이고, 그 중간은 이 덱에서 나올 수 없다.
    bursts = sum(1 for c in report["cycles"] if c["powering_up"])
    assert bursts in (0, len(report["cycles"]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_miranda_targets.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.miranda_targets'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/miranda_targets.py`:

```python
"""덱 5인 중 누가 미란다의 파워업!(버스트)과 웨이크업! 3번불릿을 받는가.

두 불릿 다 「최종 공격력 상위 N명(시전자 제외)」을 대상으로 하고, 그 순위는
판정 순간 살아 있는 공격력 버프까지 반영한 값이다 - 로스터의 표시 공격력만
보고는 답이 안 나온다. 그래서 이 모듈은 순위를 다시 구현하지 않고 엔진이 이미
한 판정의 기록(SquadContext.target_grants)을 읽는다.

좌석 순서는 evaluate_decks가 정한다. 유니온 탭이 채점에 쓰는 것과 같은
함수라, 이 화면이 보여주는 배치와 그 탭이 매기는 점수가 어긋날 수 없다.
"""
from app.deck_evaluation import evaluate_decks
from app.deck_search import evaluate_deck

MIRANDA_SLUGS = ("miranda", "miranda-signature")

# 미란다의 기록(캐스터로 이미 걸러진 뒤)에서 두 불릿을 가르는 스탯. 미란다의
# 다른 불릿들도 같은 스탯을 주지만(애장품 헬스업!의 자신 ATK, 웨이크업! 2번불릿의
# 자신 크확) 그것들은 top-N 룰이 아니라서 미란다의 기록에도 안 들어온다 - 그래서
# 이 두 줄로 충분하다.
POWERING_UP_STAT = "atk_percent"
WAKE_UP_CRIT_RATE_STAT = "crit_rate"

FAVORITE_ITEM_SLUG = "miranda-signature"

NO_THIRD_BULLET_NOTE = (
    "이 미란다는 애장품이 없어서 웨이크업!에 3번불릿이 아예 없어요 — "
    "크확 버프를 받는 니케가 없는 게 정상이에요."
)
NO_FULL_BURST_NOTE = "이 편성으로는 풀 버스트가 한 번도 열리지 않아요."


def miranda_slug_in(slugs):
    """`slugs` 안의 미란다 슬러그, 없으면 None. 어느 빌드인지가 답을 바꾸므로
    (애장품이면 파워업! 2명 + 웨이크업!3, 아니면 파워업! 1명뿐) 존재 여부가
    아니라 슬러그 자체를 돌려준다."""
    for slug in slugs:
        if slug in MIRANDA_SLUGS:
            return slug
    return None


def _cycle_end_times(events):
    """풀 버스트가 닫히는 시각들. 사이클 k는 (직전 종료, 이번 종료] 구간이다."""
    return [event["time"] for event in events if event["type"] == "full_burst_end"]


def _first_targets(window, stat):
    for grant in window:
        if stat in grant["stats"]:
            return list(grant["targets"])
    return []


def cycles_from_result(result, miranda_slug):
    """시뮬 결과 하나를 사이클별 대상 목록으로 접는다."""
    grants = [g for g in result.get("target_grants", ())
              if g["caster"] == miranda_slug]
    cycles = []
    start = float("-inf")
    for index, end in enumerate(_cycle_end_times(result["events"]), start=1):
        window = [g for g in grants if start < g["time"] <= end]
        cycles.append({
            "index": index,
            "powering_up": _first_targets(window, POWERING_UP_STAT),
            "wake_up_crit_rate": _first_targets(window, WAKE_UP_CRIT_RATE_STAT),
        })
        start = end
    return cycles


def order_deck(deck_specs, boss, spec_index, alternatives=None):
    """유니온 탭과 같은 기준으로 고른 좌석 순서의 스펙 목록.

    `spec_index`는 로스터의 **모든** 로드 가능한 스펙이어야 한다({slug: NikkeSpec},
    load_roster의 출력). 엔진이 MODE_VARIANTS 좌석을 `deck_specs`에 없는 변형으로
    확정할 수 있어서, 다섯만 담은 색인으로는 되짚을 수 없다."""
    summary = evaluate_decks([deck_specs], [boss], alternatives=alternatives)["decks"][0]
    return [spec_index[slug] for slug in summary["deck"]]


def miranda_target_report(deck_specs, boss, spec_index, alternatives=None):
    ordered = order_deck(deck_specs, boss, spec_index, alternatives)
    miranda_slug = miranda_slug_in(spec.slug for spec in ordered)
    if miranda_slug is None:
        raise ValueError("이 덱에는 미란다가 없다")

    result = evaluate_deck(ordered, boss, collect_target_grants=True)
    cycles = cycles_from_result(result, miranda_slug)

    notes = []
    if miranda_slug != FAVORITE_ITEM_SLUG:
        notes.append(NO_THIRD_BULLET_NOTE)
    if not cycles:
        notes.append(NO_FULL_BURST_NOTE)

    return {
        "seats": [{"slug": spec.slug, "burst_tier": spec.burst_tier} for spec in ordered],
        "miranda_slug": miranda_slug,
        "has_favorite_item": miranda_slug == FAVORITE_ITEM_SLUG,
        "cycles": cycles,
        "notes": notes,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_miranda_targets.py -v`
Expected: PASS 전부

버스트 티어는 2026-08-08 기준 `miranda-signature`·`liter` = 1, `crown` = 2, `ada-wong`·`cinderella`·`isabel`·`julia`·`helm` = 3이다. 다른 슬러그로 바꿔야 하면 먼저 확인한다:

```bash
cd backend && PYTHONPATH=$PWD python -c "from app.supported_units import supported_units; print({u['slug']: u['burst_tier'] for u in supported_units()})"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/miranda_targets.py backend/tests/test_miranda_targets.py
git commit -m "사이클별로 누가 미란다의 두 버프를 받는지 접는다

좌석 순서는 유니온 탭이 쓰는 evaluate_decks가 정하고, 그 순서로 한 번 더
돌려 기록을 얻는다 - 선택 로직을 복제하면 두 화면이 어긋날 수 있다.

애장품 없는 미란다는 웨이크업!3이 스킬에 아예 없으므로 그 사실을 안내에
싣는다. 안 적으면 빈 결과가 고장으로 읽힌다."
```

---

### Task 7: 오버로드 임계값 탐색

**Files:**
- Modify: `backend/app/miranda_targets.py`
- Test: `backend/tests/test_miranda_overload_threshold.py`

**Interfaces:**
- Consumes: Task 5의 `max_atk_percent`, Task 6의 `cycles_from_result` / `order_deck`
- Produces:
  - `OVERLOAD_ATK_NAME = "공격력 증가"`, `THRESHOLD_PRECISION = 0.01`
  - `overload_thresholds(ordered, boss, miranda_slug, cap) -> list[dict]`
    각 항목 `{"slug": str, "current_percent": float, "kind": "gain"|"keep", "threshold_percent": float | None}`
  - `miranda_target_report`의 반환 dict에 `"overload_thresholds"` 키가 추가된다

- [ ] **Step 1: Write the failing test**

`backend/tests/test_miranda_overload_threshold.py`:

```python
"""어떤 니케가 웨이크업!3을 받으려면 오버로드 공격력이 얼마나 필요한가.

닫힌형(격차 나누기 표시공격력)은 필요치를 과대평가한다 - 오버로드가 오르면
파워업!(B1 시전) 판정도 같이 움직여, 상위 N에 새로 들어가는 계단이 생기기
때문이다. 그래서 실제로 돌려서 이진탐색한다. 이 파일이 보는 것은 「보고된
값에서 실제로 받고, 한 눈금 아래에서는 못 받는가」다.
"""
from app.deck_search import BossProfile
from app.miranda_targets import (THRESHOLD_PRECISION, cycles_from_result,
                                 miranda_target_report, order_deck,
                                 with_overload_atk)
from app.deck_search import evaluate_deck
from app.models import OverloadOption, SkillLevels, UserNikkeState
from app.overload_effects import max_atk_percent
from app.stat_assembly import load_stat_tables
from app.user_roster import load_roster

MAXED = SkillLevels(skill1=10, skill2=10, burst=10)
BOSS = BossProfile(fight_duration=180.0)
DECK = ["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"]


def a_state(slug, atk, overload_atk=0.0):
    options = ([OverloadOption(name="공격력 증가", value=overload_atk)]
               if overload_atk else [])
    return UserNikkeState(
        character_slug=slug, level=400, hp=500_000.0, atk=atk, def_=10_000.0,
        skill_levels=MAXED, overload_options=options,
    )


def a_report(atk_by_slug, overload_by_slug=None):
    overload_by_slug = overload_by_slug or {}
    states = [a_state(slug, atk_by_slug[slug], overload_by_slug.get(slug, 0.0))
              for slug in DECK]
    specs, _excluded = load_roster(states)
    spec_index = {spec.slug: spec for spec in specs}
    deck_specs = [spec_index[slug] for slug in DECK]
    return miranda_target_report(deck_specs, BOSS, spec_index), spec_index, deck_specs


def receives_all_cycles(spec_index, deck_specs, slug, percent):
    """`slug`의 오버로드 공격력을 `percent`로 놓고 돌렸을 때 전 사이클
    웨이크업!3을 받는가."""
    ordered = order_deck(deck_specs, BOSS, spec_index)
    trial = [with_overload_atk(spec, percent) if spec.slug == slug else spec
             for spec in ordered]
    result = evaluate_deck(trial, BOSS, collect_target_grants=True)
    cycles = cycles_from_result(result, "miranda-signature")
    return bool(cycles) and all(slug in c["wake_up_crit_rate"] for c in cycles)


ATK = {"miranda-signature": 100_000.0, "crown": 100_000.0,
       "ada-wong": 120_000.0, "cinderella": 100_000.0, "isabel": 100_000.0}


def by_slug(thresholds):
    return {t["slug"]: t for t in thresholds}


def test_the_recipient_gets_a_keep_threshold_and_the_others_a_gain_one():
    report, _index, _deck = a_report(ATK)
    thresholds = by_slug(report["overload_thresholds"])
    # 미란다는 자기 대상이 될 수 없으므로 목록에 없다.
    assert "miranda-signature" not in thresholds
    assert set(thresholds) == {"crown", "ada-wong", "cinderella", "isabel"}
    winner = report["cycles"][0]["wake_up_crit_rate"][0]
    assert thresholds[winner]["kind"] == "keep"
    for slug, entry in thresholds.items():
        if slug != winner:
            assert entry["kind"] == "gain"


def test_a_gain_threshold_is_a_value_that_actually_works():
    report, index, deck = a_report(ATK)
    thresholds = by_slug(report["overload_thresholds"])
    loser = next(t for t in thresholds.values()
                 if t["kind"] == "gain" and t["threshold_percent"] is not None)
    at = loser["threshold_percent"]
    assert receives_all_cycles(index, deck, loser["slug"], at)
    assert not receives_all_cycles(index, deck, loser["slug"],
                                   at - 2 * THRESHOLD_PRECISION)


def test_a_keep_threshold_is_the_edge_of_still_receiving():
    report, index, deck = a_report(ATK, overload_by_slug={"ada-wong": 20.0})
    thresholds = by_slug(report["overload_thresholds"])
    keeper = next(t for t in thresholds.values() if t["kind"] == "keep")
    floor = keeper["threshold_percent"]
    assert receives_all_cycles(index, deck, keeper["slug"], floor)
    if floor > 0:
        assert not receives_all_cycles(index, deck, keeper["slug"],
                                       floor - 2 * THRESHOLD_PRECISION)


def test_an_unreachable_unit_reports_no_threshold():
    # 다른 넷보다 압도적으로 낮은 공격력이면 상한(58.52%)으로도 못 넘는다.
    atk = dict(ATK)
    atk["isabel"] = 10_000.0
    report, index, deck = a_report(atk)
    thresholds = by_slug(report["overload_thresholds"])
    assert thresholds["isabel"]["threshold_percent"] is None
    cap = max_atk_percent(load_stat_tables())
    assert not receives_all_cycles(index, deck, "isabel", cap)


def test_current_percent_is_read_off_the_roster():
    report, _index, _deck = a_report(ATK, overload_by_slug={"crown": 7.25})
    thresholds = by_slug(report["overload_thresholds"])
    assert thresholds["crown"]["current_percent"] == 7.25
    assert thresholds["isabel"]["current_percent"] == 0.0


def test_the_base_build_has_no_thresholds_at_all():
    # 애장품이 없으면 웨이크업!3이 스킬에 없으므로 넘어설 경계가 없다.
    deck = ["miranda", "crown", "ada-wong", "cinderella", "isabel"]
    states = [a_state(slug, ATK.get(slug, 100_000.0)) for slug in deck]
    specs, _excluded = load_roster(states)
    spec_index = {spec.slug: spec for spec in specs}
    report = miranda_target_report([spec_index[s] for s in deck], BOSS, spec_index)
    assert report["overload_thresholds"] == []


def test_with_overload_atk_replaces_only_the_atk_line():
    states = [a_state("crown", 100_000.0, 5.0)]
    specs, _excluded = load_roster(states)
    spec = specs[0]
    spec.overload_options.append(OverloadOption(name="크리티컬 확률 증가", value=3.0))
    swapped = with_overload_atk(spec, 12.0)
    names = [o.name for o in swapped.overload_options]
    assert names.count("공격력 증가") == 1
    assert "크리티컬 확률 증가" in names
    atk_line = next(o for o in swapped.overload_options if o.name == "공격력 증가")
    assert atk_line.value == 12.0
    # 0을 주면 라인이 통째로 사라진다 - 0%짜리 라인은 없는 라인과 같다.
    assert all(o.name != "공격력 증가" for o in with_overload_atk(spec, 0.0).overload_options)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_miranda_overload_threshold.py -v`
Expected: FAIL — `ImportError: cannot import name 'with_overload_atk' from 'app.miranda_targets'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/miranda_targets.py` 상단 import에 추가:

```python
import math
from dataclasses import replace

from app.models import OverloadOption
from app.overload_effects import max_atk_percent
from app.stat_assembly import load_stat_tables
```

모듈 상수에 추가:

```python
# 블라블라링크가 오버로드를 소수 둘째 자리로 보여주므로 그보다 가늘 이유가 없다.
THRESHOLD_PRECISION = 0.01
OVERLOAD_ATK_NAME = "공격력 증가"
```

함수들을 `miranda_target_report` **앞**에 추가:

```python
def with_overload_atk(spec, percent):
    """`spec`의 오버로드 공격력 라인만 `percent`로 바꾼 사본. 다른 라인은 그대로
    둔다 - 이 탐색이 묻는 것은 공격력 하나를 움직였을 때의 답이다.

    0이면 라인을 아예 뺀다: 0%짜리 라인은 없는 라인과 같고, 값 0을 남기면
    overload_options_to_effects가 값 0짜리 효과를 하나 더 만든다."""
    others = [o for o in spec.overload_options if o.name != OVERLOAD_ATK_NAME]
    if percent > 0:
        others = others + [OverloadOption(name=OVERLOAD_ATK_NAME, value=percent)]
    return replace(spec, overload_options=others)


def current_overload_atk(spec):
    return sum(o.value for o in spec.overload_options if o.name == OVERLOAD_ATK_NAME)


def _smallest_true(predicate, false_at, true_at):
    """`predicate`가 참인 가장 작은 값. `false_at`은 거짓이 확인된 쪽,
    `true_at`은 참이 확인된 쪽이고 `false_at < true_at`이다.

    돌려주는 값은 **실제로 돌려서 참으로 확인된 쪽 끝을 올림한 것**이라, 반올림
    때문에 「모자란데 된다고 적힌」 값이 나오지 않는다. 술어는 단조라고 가정한다
    (설계문서 §5.2: 공격력을 순위로 나눠주는 규칙이 저장소에 없다)."""
    while true_at - false_at > THRESHOLD_PRECISION:
        middle = (false_at + true_at) / 2
        if predicate(middle):
            true_at = middle
        else:
            false_at = middle
    return math.ceil(true_at * 100) / 100


def overload_thresholds(ordered, boss, miranda_slug, cap):
    """좌석마다 「전 사이클 웨이크업!3을 받는」 오버로드 공격력의 경계.

    좌석 순서는 여기서 고정이다 - 값마다 배치를 다시 고르면 다른 덱의 답이 된다.
    시전자는 자기 대상이 될 수 없으므로 빠진다."""
    def receives_all(slug, percent):
        trial = [with_overload_atk(spec, percent) if spec.slug == slug else spec
                 for spec in ordered]
        result = evaluate_deck(trial, boss, collect_target_grants=True)
        cycles = cycles_from_result(result, miranda_slug)
        return bool(cycles) and all(slug in c["wake_up_crit_rate"] for c in cycles)

    rows = []
    for spec in ordered:
        if spec.slug == miranda_slug:
            continue
        current = current_overload_atk(spec)
        predicate = lambda percent, slug=spec.slug: receives_all(slug, percent)
        if predicate(current):
            # 지금 받고 있다 - 어디까지 떨어져도 유지되는가.
            threshold = 0.0 if predicate(0.0) else _smallest_true(predicate, 0.0, current)
            rows.append({"slug": spec.slug, "current_percent": current,
                         "kind": "keep", "threshold_percent": threshold})
            continue
        # 지금 못 받는다 - 상한에서도 못 받으면 오버로드로는 답이 없다.
        threshold = _smallest_true(predicate, current, cap) if predicate(cap) else None
        rows.append({"slug": spec.slug, "current_percent": current,
                     "kind": "gain", "threshold_percent": threshold})
    return rows
```

`miranda_target_report`의 반환 직전에 임계값을 계산하고 dict에 싣는다. 애장품이 없으면 넘어설 경계 자체가 없으므로 빈 목록이다:

```python
    cap = max_atk_percent(load_stat_tables())
    thresholds = (overload_thresholds(ordered, boss, miranda_slug, cap)
                  if miranda_slug == FAVORITE_ITEM_SLUG and cycles else [])

    return {
        "seats": [{"slug": spec.slug, "burst_tier": spec.burst_tier} for spec in ordered],
        "miranda_slug": miranda_slug,
        "has_favorite_item": miranda_slug == FAVORITE_ITEM_SLUG,
        "cycles": cycles,
        "overload_thresholds": thresholds,
        "overload_atk_cap_percent": cap,
        "notes": notes,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_miranda_overload_threshold.py tests/test_miranda_targets.py -v`
Expected: PASS 전부. 이 파일은 시뮬을 수십 번 돌리므로 20~40초 걸린다.

`test_a_gain_threshold_is_a_value_that_actually_works`가 실패하면 술어가 단조가 아닌 덱을 만든 것이다 — **그때는 값을 조정해 맞추지 말고 멈추고 보고한다.** 설계문서 §5.2가 근거를 대고 있고, 반례가 있으면 그것이 새 사실이다.

- [ ] **Step 5: Commit**

```bash
git add backend/app/miranda_targets.py backend/tests/test_miranda_overload_threshold.py
git commit -m "받으려면 오버로드 공격력이 얼마나 필요한지 답한다

닫힌형 나눗셈은 과대평가한다: 오버로드가 오르면 파워업!(B1 시전) 판정도
같이 움직여 상위 N에 새로 들어가는 계단이 생긴다. evaluate_deck 1회가
0.107초라 실제로 돌려서 이진탐색한다.

보고하는 값은 언제나 돌려서 참으로 확인된 쪽 끝을 올림한 것이다.
받고 있는 니케에게는 반대로 어디까지 떨어져도 유지되는지를 답한다."
```

---

### Task 8: `POST /api/miranda-targets`

**Files:**
- Modify: `backend/app/api.py` (import 블록, 모델 정의는 `ChargeWindowResponse` 뒤, 라우트는 `charge_window_route` 뒤)
- Test: `backend/tests/test_api_miranda_targets.py`

**Interfaces:**
- Consumes: Task 6·7의 `miranda_target_report`, `miranda_slug_in`, `MIRANDA_SLUGS`
- Produces: `POST /api/miranda-targets` — 요청 `{roster, units}`, 응답 아래 `MirandaTargetsResponse`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_miranda_targets.py`:

```python
"""POST /api/miranda-targets - 미란다 계산기의 surface."""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)

MAXED = {"skill1": 10, "skill2": 10, "burst": 10}
DECK = ["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"]


def a_unit(slug, atk=100_000):
    return {"character_slug": slug, "level": 400, "hp": 500_000, "atk": atk,
            "def_": 10_000, "skill_levels": MAXED, "overload_options": []}


def post(units, roster=None):
    roster = roster if roster is not None else [a_unit(slug) for slug in DECK]
    return client.post("/api/miranda-targets", json={"roster": roster, "units": units})


def test_a_full_deck_reports_cycles_seats_and_thresholds():
    response = post(DECK)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["miranda_slug"] == "miranda-signature"
    assert body["has_favorite_item"] is True
    assert len(body["seats"]) == 5
    assert body["cycles"]
    assert [c["index"] for c in body["cycles"]] == list(range(1, len(body["cycles"]) + 1))
    assert {t["slug"] for t in body["overload_thresholds"]} == set(DECK) - {"miranda-signature"}
    assert body["overload_atk_cap_percent"] > 0
    assert body["engine_version"]
    # 고정한 보스 전제는 언제나 화면에 닿아야 한다.
    assert any("무속성" in note for note in body["notes"])


def test_a_deck_that_is_not_five_units_is_rejected():
    response = post(DECK[:4])
    assert response.status_code == 422
    assert "5" in response.json()["detail"]


def test_a_deck_without_miranda_is_rejected():
    deck = ["liter", "crown", "ada-wong", "cinderella", "isabel"]
    response = post(deck, roster=[a_unit(slug) for slug in deck])
    assert response.status_code == 422
    assert "미란다" in response.json()["detail"]


def test_a_slug_the_engine_cannot_use_is_rejected():
    deck = ["miranda-signature", "crown", "ada-wong", "cinderella", "not-a-nikke"]
    roster = [a_unit(slug) for slug in DECK[:4]] + [a_unit("not-a-nikke")]
    response = post(deck, roster=roster)
    assert response.status_code == 422
    assert "not-a-nikke" in response.json()["detail"]


def test_a_deck_with_no_feasible_burst_order_is_rejected():
    # B3 다섯 - 1·1·3 / 1·2·2 / 2·1·2 중 어느 모양도 아니다.
    deck = ["ada-wong", "cinderella", "isabel", "julia", "helm"]
    response = post(deck, roster=[a_unit(slug) for slug in deck])
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_api_miranda_targets.py -v`
Expected: FAIL — 404 (라우트 없음)

- [ ] **Step 3: Write minimal implementation**

`backend/app/api.py`의 import 블록에 추가 (`from app.models import UserNikkeState` 앞, 알파벳 순서 유지):

```python
from app.miranda_targets import MIRANDA_SLUGS, miranda_slug_in, miranda_target_report
```

`ChargeWindowResponse` 클래스 정의 **뒤**에 모델을 추가:

```python
class MirandaTargetsRequest(BaseModel):
    roster: list[UserNikkeState]
    units: list[str]


class MirandaSeat(BaseModel):
    slug: str
    burst_tier: int


class MirandaCycle(BaseModel):
    index: int
    powering_up: list[str]
    wake_up_crit_rate: list[str]


class MirandaOverloadThreshold(BaseModel):
    """이 니케가 전 사이클 웨이크업!3을 받는 오버로드 공격력의 경계."""
    slug: str
    current_percent: float
    # gain: 지금 못 받는다 - threshold_percent 이상이면 받는다
    # keep: 지금 받는다 - threshold_percent 밑으로 내려가면 놓친다
    kind: Literal["gain", "keep"]
    # gain에서 오버로드 상한 안에 답이 없으면 None. 누락이 아니라 「그런 값이
    # 없다」는 뜻을 지닌 값이다.
    threshold_percent: float | None


class MirandaTargetsResponse(BaseModel):
    seats: list[MirandaSeat]
    miranda_slug: str
    has_favorite_item: bool
    cycles: list[MirandaCycle]
    overload_thresholds: list[MirandaOverloadThreshold]
    overload_atk_cap_percent: float
    notes: list[str]
    engine_version: str
```

`charge_window_route` **뒤**에 라우트를 추가:

```python
# 이 계산기는 보스를 묻지 않는다. 답하는 것은 「누가 받는가」 하나이고, 그
# 순위를 정하는 것은 대부분 덱 자신의 버프이기 때문이다. 그래서 BossProfileIn의
# 기본값(무속성·180초)을 쓰고, 그 전제는 notes로 언제나 화면에 닿는다.
MIRANDA_CALCULATOR_BOSS = BossProfileIn()

MIRANDA_BOSS_NOTE = (
    "무속성 보스·180초 전투를 가정해 계산했어요. 보스 속성에 걸린 공격력 버프를 "
    "가진 니케가 있으면 실제 레이드와 순위가 다를 수 있어요."
)


def _miranda_targets_sync(request: MirandaTargetsRequest, cancel) -> MirandaTargetsResponse:
    # 평가와 임계값 탐색을 합쳐 수 초다. SimPool을 만들지 않으므로 토큰에 접을
    # 풀이 없다 - 인자는 _run_cancellable의 계약을 맞추기 위한 것.
    _reject_unknown_overload_options(request.roster)
    if len(request.units) != DECK_SIZE:
        raise HTTPException(422, f"덱은 {DECK_SIZE}명이어야 해요.")
    if miranda_slug_in(request.units) is None:
        raise HTTPException(422, "덱에 미란다가 없어요. 미란다를 넣어야 계산할 수 있어요.")

    specs, _excluded = load_roster(request.roster)
    by_slug, alternatives = _variant_alternatives(specs)
    deck_specs = []
    for slug in request.units:
        options = alternatives.get(slug)
        if options is None and slug not in by_slug:
            raise HTTPException(422, f"엔진이 쓸 수 없는 슬러그예요: {slug}")
        deck_specs.append(options[0] if options else by_slug[slug])

    alternatives = {options[0].slug: options for options in alternatives.values()}
    try:
        report = miranda_target_report(deck_specs, boss_profile(MIRANDA_CALCULATOR_BOSS),
                                       by_slug, alternatives=alternatives)
    except InfeasibleDeck:
        raise HTTPException(
            422, "이 다섯으로는 성립하는 버스트 순서가 없어요. 버스트 1·2·3단계 "
                 "인원 수가 1·1·3, 1·2·2, 2·1·2 중 하나여야 해요.") from None

    return MirandaTargetsResponse(
        seats=[MirandaSeat(**seat) for seat in report["seats"]],
        miranda_slug=report["miranda_slug"],
        has_favorite_item=report["has_favorite_item"],
        cycles=[MirandaCycle(**cycle) for cycle in report["cycles"]],
        overload_thresholds=[MirandaOverloadThreshold(**row)
                             for row in report["overload_thresholds"]],
        overload_atk_cap_percent=report["overload_atk_cap_percent"],
        notes=[*report["notes"], MIRANDA_BOSS_NOTE],
        engine_version=engine_version(),
    )


@app.post("/api/miranda-targets", response_model=MirandaTargetsResponse)
async def miranda_targets_route(
    request: MirandaTargetsRequest, http_request: Request
) -> MirandaTargetsResponse:
    """덱 5인 중 누가 미란다의 파워업!과 웨이크업!3을 받는가."""
    return await _run_cancellable(http_request, _miranda_targets_sync, request)
```

**주의:** `MIRANDA_CALCULATOR_BOSS`와 `_miranda_targets_sync`는 `DECK_SIZE`(현재 `api.py:539`)와 `_variant_alternatives`(`:370`) 뒤에 와야 한다. 둘 다 모듈 로드 시점이 아니라 호출 시점에 읽히므로 파일 안 위치는 자유롭지만, 읽는 사람을 위해 `charge_window_route` 뒤에 둔다.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_miranda_targets.py -v`
Expected: PASS 전부

`test_a_deck_with_no_feasible_burst_order_is_rejected`에서 쓴 다섯 슬러그가 전부 B3인지 확인이 필요하면: `cd backend && PYTHONPATH=$PWD python -c "from app.supported_units import supported_units; print({u['slug']: u['burst_tier'] for u in supported_units() if u['slug'] in ('ada-wong','cinderella','isabel','julia','helm')})"`

- [ ] **Step 5: Run the whole backend suite and commit**

Run: `cd backend && python -m pytest -q`
Expected: 실패 0

```bash
git add backend/app/api.py backend/tests/test_api_miranda_targets.py
git commit -m "미란다 계산기 엔드포인트를 연다

보스를 묻지 않는다 - 답하는 것은 「누가 받는가」 하나이고 순위를 정하는 것은
대부분 덱 자신의 버프다. 그 전제는 notes로 언제나 화면에 닿는다.

덱에 미란다가 없다는 422는 화면에서는 좌석이 고정이라 닿지 않지만, API는
화면 밖에서도 불릴 수 있으므로 가드로 남긴다."
```

---

### Task 9: 프론트 wire 타입 + API 클라이언트

**Files:**
- Create: `frontend/src/types/mirandaTargets.ts`, `frontend/src/api/mirandaTargets.ts`
- Test: `frontend/src/types/mirandaTargets.test.ts`

**Interfaces:**
- Consumes: Task 8의 `POST /api/miranda-targets` 응답 모양
- Produces:
  - `MirandaTargetsResultWire`(snake_case) / `MirandaTargetsResult`(camelCase)
  - `mapMirandaTargetsResult(wire) -> MirandaTargetsResult`
  - `postMirandaTargets({roster, units}) -> Promise<MirandaTargetsResult>`
  - 타입: `MirandaSeat {slug, burstTier}`, `MirandaCycle {index, poweringUp, wakeUpCritRate}`, `MirandaOverloadThreshold {slug, currentPercent, kind: 'gain'|'keep', thresholdPercent: number | null}`

- [ ] **Step 1: Write the failing test**

`frontend/src/types/mirandaTargets.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { mapMirandaTargetsResult } from './mirandaTargets'
import type { MirandaTargetsResultWire } from './mirandaTargets'

const WIRE: MirandaTargetsResultWire = {
  seats: [
    { slug: 'miranda-signature', burst_tier: 1 },
    { slug: 'crown', burst_tier: 2 },
    { slug: 'ada-wong', burst_tier: 3 },
  ],
  miranda_slug: 'miranda-signature',
  has_favorite_item: true,
  cycles: [
    { index: 1, powering_up: ['ada-wong', 'crown'], wake_up_crit_rate: ['ada-wong'] },
  ],
  overload_thresholds: [
    { slug: 'crown', current_percent: 8, kind: 'gain', threshold_percent: 11.47 },
    { slug: 'ada-wong', current_percent: 12, kind: 'keep', threshold_percent: 0 },
  ],
  overload_atk_cap_percent: 58.52,
  notes: ['무속성 보스·180초 전투를 가정해 계산했어요.'],
  engine_version: 'abc123',
}

describe('mapMirandaTargetsResult', () => {
  it('renames every wire field to camelCase', () => {
    const result = mapMirandaTargetsResult(WIRE)
    expect(result.seats).toEqual([
      { slug: 'miranda-signature', burstTier: 1 },
      { slug: 'crown', burstTier: 2 },
      { slug: 'ada-wong', burstTier: 3 },
    ])
    expect(result.mirandaSlug).toBe('miranda-signature')
    expect(result.hasFavoriteItem).toBe(true)
    expect(result.cycles).toEqual([
      { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
    ])
    expect(result.overloadAtkCapPercent).toBe(58.52)
    expect(result.notes).toEqual(WIRE.notes)
  })

  it('keeps a null threshold as null rather than dropping it', () => {
    // null은 「상한 안에 답이 없다」는 뜻을 지닌 값이지 누락이 아니다.
    const wire = {
      ...WIRE,
      overload_thresholds: [
        { slug: 'isabel', current_percent: 0, kind: 'gain' as const, threshold_percent: null },
      ],
    }
    expect(mapMirandaTargetsResult(wire).overloadThresholds).toEqual([
      { slug: 'isabel', currentPercent: 0, kind: 'gain', thresholdPercent: null },
    ])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- mirandaTargets`
Expected: FAIL — 모듈을 못 찾는다

- [ ] **Step 3: Write minimal implementation**

`frontend/src/types/mirandaTargets.ts`:

```ts
// Wire and view shapes for POST /api/miranda-targets. The backend speaks
// snake_case; everything past the api client speaks camelCase.
//
// No field is optional. An optional field would let a wiring gap pass the
// type-checker, which is exactly the failure this project has already paid
// for. `thresholdPercent: null` is a VALUE - "no overload total inside the
// cap wins this buff" - not a missing field.

export interface MirandaSeatWire {
  slug: string
  burst_tier: number
}

export interface MirandaCycleWire {
  index: number
  powering_up: string[]
  wake_up_crit_rate: string[]
}

export interface MirandaOverloadThresholdWire {
  slug: string
  current_percent: number
  kind: 'gain' | 'keep'
  threshold_percent: number | null
}

export interface MirandaTargetsResultWire {
  seats: MirandaSeatWire[]
  miranda_slug: string
  has_favorite_item: boolean
  cycles: MirandaCycleWire[]
  overload_thresholds: MirandaOverloadThresholdWire[]
  overload_atk_cap_percent: number
  notes: string[]
  engine_version: string
}

export interface MirandaSeat {
  slug: string
  burstTier: number
}

export interface MirandaCycle {
  index: number
  poweringUp: string[]
  wakeUpCritRate: string[]
}

export interface MirandaOverloadThreshold {
  slug: string
  currentPercent: number
  kind: 'gain' | 'keep'
  thresholdPercent: number | null
}

export interface MirandaTargetsResult {
  seats: MirandaSeat[]
  mirandaSlug: string
  hasFavoriteItem: boolean
  cycles: MirandaCycle[]
  overloadThresholds: MirandaOverloadThreshold[]
  overloadAtkCapPercent: number
  notes: string[]
  engineVersion: string
}

export const mapMirandaTargetsResult = (
  wire: MirandaTargetsResultWire,
): MirandaTargetsResult => ({
  seats: wire.seats.map((seat) => ({ slug: seat.slug, burstTier: seat.burst_tier })),
  mirandaSlug: wire.miranda_slug,
  hasFavoriteItem: wire.has_favorite_item,
  cycles: wire.cycles.map((cycle) => ({
    index: cycle.index,
    poweringUp: cycle.powering_up,
    wakeUpCritRate: cycle.wake_up_crit_rate,
  })),
  overloadThresholds: wire.overload_thresholds.map((row) => ({
    slug: row.slug,
    currentPercent: row.current_percent,
    kind: row.kind,
    thresholdPercent: row.threshold_percent,
  })),
  overloadAtkCapPercent: wire.overload_atk_cap_percent,
  notes: wire.notes,
  engineVersion: wire.engine_version,
})
```

`frontend/src/api/mirandaTargets.ts`:

```ts
// Typed client for POST /api/miranda-targets - who receives Miranda's two
// top-ATK buffs, and what overload ATK would change that.

import type { MirandaTargetsResult, MirandaTargetsResultWire } from '../types/mirandaTargets'
import { mapMirandaTargetsResult } from '../types/mirandaTargets'
import { RecommendApiError } from './recommendApiError'

export interface MirandaTargetsRequest {
  roster: unknown[]
  units: string[]
}

export const postMirandaTargets = async (
  request: MirandaTargetsRequest,
): Promise<MirandaTargetsResult> => {
  const response = await fetch('/api/miranda-targets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ roster: request.roster, units: request.units }),
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return mapMirandaTargetsResult((await response.json()) as MirandaTargetsResultWire)
}
```

- [ ] **Step 4: Run test and typecheck**

Run: `cd frontend && npm test -- mirandaTargets`
Expected: PASS

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 출력 없음(에러 0)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/mirandaTargets.ts frontend/src/api/mirandaTargets.ts frontend/src/types/mirandaTargets.test.ts
git commit -m "미란다 계산기 응답의 타입과 클라이언트

어떤 필드도 옵셔널로 두지 않는다 - 옵셔널이면 배선 누락이 타입 검사를
통과한다. thresholdPercent의 null은 「상한 안에 답이 없다」는 뜻을 지닌
값이지 누락이 아니라 유니온으로 적는다."
```

---

### Task 10: `DraftEditor`에 고정 좌석

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx:15-35` (props), `:188-199` (`handleSeatDrop`), `:253-322` (좌석 렌더)
- Modify: `frontend/src/App.css`
- Test: `frontend/src/components/DraftEditor.test.tsx`

**Interfaces:**
- Consumes: 없음
- Produces: `DraftEditor`의 `fixedSlugs?: string[]` prop (기본 `[]` = 오늘 동작)

- [ ] **Step 1: Write the failing test**

`frontend/src/components/DraftEditor.test.tsx`의 마지막 `describe` 뒤에 붙인다. 파일에 이미 있는 렌더 헬퍼가 있으면 그것을 쓰고, 없으면 아래를 그대로 쓴다.

```ts
describe('fixedSlugs', () => {
  const tiersFor = (slug: string): BurstTier[] =>
    slug === 'miranda-signature' ? [1] : [3]
  const renderWith = (fixedSlugs?: string[]) => {
    const onChange = vi.fn()
    const value: Draft = {
      decks: [[
        { slug: 'miranda-signature', locked: false },
        { slug: 'ada-wong', locked: false },
      ]],
    }
    render(
      <DraftEditor
        numDecks={1}
        value={value}
        onChange={onChange}
        portraitFor={() => null}
        nameFor={nameFromSlug}
        burstTiersFor={tiersFor}
        showLocks={false}
        fixedSlugs={fixedSlugs}
      />,
    )
    return onChange
  }

  it('draws no remove button for a fixed seat', () => {
    renderWith(['miranda-signature'])
    expect(
      screen.queryByRole('button', { name: /miranda-signature 제거/ }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ada-wong 제거/ })).toBeInTheDocument()
  })

  it('refuses a swap dropped onto a fixed seat', () => {
    // 제거 버튼과 드래그만 막으면 뒷문이 열려 있다 - 스왑은 점유자를 밀어낸다.
    const onChange = renderWith(['miranda-signature'])
    const fixed = screen.getByText('miranda-signature').closest('li')!
    fireEvent.drop(fixed, {
      dataTransfer: { getData: (type: string) => (type === DRAG_SLUG_TYPE ? 'crown' : '') },
    })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('leaves every seat removable when no slug is fixed', () => {
    renderWith()
    expect(
      screen.getByRole('button', { name: /miranda-signature 제거/ }),
    ).toBeInTheDocument()
  })
})
```

`nameFromSlug`가 슬러그를 그대로 돌려주지 않으면 위의 `getByRole` 이름 정규식이 안 맞는다 — 그때는 `nameFor={(slug) => slug}`로 바꾼다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- DraftEditor`
Expected: FAIL — 고정 좌석에도 제거 버튼이 있고, 스왑이 `onChange`를 부른다

- [ ] **Step 3: Write minimal implementation**

props 인터페이스에 추가 (`showLocks?: boolean` 뒤):

```tsx
  /** Slugs whose seat the player may not vacate — the Miranda calculator seats
   * her itself and asks for the other four. Removing, dragging out, and being
   * swapped away all have to be closed: a swap displaces the occupant, so
   * closing the first two alone leaves a back door. */
  fixedSlugs?: string[]
```

구조 분해에 추가:

```tsx
  fixedSlugs = [],
```

컴포넌트 본문 상단(`nominalTierFor` 정의 근처)에 추가:

```tsx
  const fixedSet = new Set(fixedSlugs)
```

`handleSeatDrop`의 `event.stopPropagation()` 다음에 추가:

```tsx
    if (fixedSet.has(occupant)) return
```

좌석 렌더 안, `const tier = ...` 다음에 추가:

```tsx
                  const isFixed = fixedSet.has(seat.slug)
```

좌석 `<li>`의 `className`을 교체:

```tsx
                      className={[
                        'draft-editor__slot',
                        swapTarget === seat.slug ? 'draft-editor__slot--swap-target' : '',
                        isFixed ? 'draft-editor__slot--fixed' : '',
                      ].filter(Boolean).join(' ')}
```

좌석 `<li>`의 `onDragOver`에서 고정 좌석은 드롭 대상으로 보이지 않게 한다 — `setSwapTarget(seat.slug)` 줄을 교체:

```tsx
                        if (!isFixed) setSwapTarget(seat.slug)
```

그립의 `draggable`을 교체:

```tsx
                        draggable={!isFixed}
```

제거 버튼을 감싼다 (`<button className="draft-editor__slot-remove" …>` 전체를 조건부로):

```tsx
                      {!isFixed && (
                        <button
                          type="button"
                          className="draft-editor__slot-remove"
                          aria-label={`${where}에서 ${name} 제거`}
                          onClick={() => onChange(removeUnit(value, deckIndex, seatIndex))}
                        >
                          <span aria-hidden="true">×</span>
                        </button>
                      )}
```

`frontend/src/App.css`의 `.draft-editor__slot--swap-target` 규칙 근처에 추가:

```css
/* 고정 좌석은 비울 수 없다. 테두리 하나로 「여기는 손대는 자리가 아니다」를
   말하고, 없는 × 버튼이 나머지를 말한다. */
.draft-editor__slot--fixed {
  outline: 1px solid var(--accent);
  outline-offset: -1px;
}
```

- [ ] **Step 4: Run tests and typecheck**

Run: `cd frontend && npm test -- DraftEditor`
Expected: PASS (새 3개 + 기존 전부)

Run: `cd frontend && npm test && npx tsc -b --noEmit`
Expected: 프론트 스위트 실패 0, 타입에러 0. 추천 탭·유니온 탭 테스트가 그대로 통과해야 한다 — `fixedSlugs` 기본값이 오늘의 동작이라는 증거다.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx frontend/src/App.css
git commit -m "비울 수 없는 좌석을 만든다

미란다 계산기는 그녀를 직접 앉히고 나머지 넷만 묻는다. 막을 곳이 셋이다 -
제거 버튼, 드래그 그립, 그리고 그 좌석으로의 스왑 드롭. 스왑은 점유자를
밀어내므로 앞의 둘만 막으면 뒷문이 열린 채다.

기본값이 빈 목록이라 기존 두 호출자는 오늘 그대로 동작한다."
```

---

### Task 11: `UnitPalette`의 제외 토글을 옵셔널로

**Files:**
- Modify: `frontend/src/components/UnitPalette.tsx:53-80` (props), `:150-160` (face 버튼)
- Test: `frontend/src/components/UnitPalette.test.tsx`

**Interfaces:**
- Consumes: 없음
- Produces: `UnitPalette`의 `excludedSlugs?: string[]`(기본 `[]`), `onToggleExclude?: (slug: string) => void`. 후자가 없으면 칩이 토글이 아니다.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/UnitPalette.test.tsx` 마지막에 붙인다. 파일에 이미 있는 렌더 헬퍼(로스터/supportedUnits 픽스처)를 재사용하고, 없으면 기존 테스트에서 그대로 복사한다.

```ts
describe('without onToggleExclude', () => {
  it('draws the chip as a plain drag source rather than a toggle', () => {
    // 이 화면(미란다 계산기)에는 탐색이 없어 후보 풀이라는 개념이 없다.
    // 켤 수는 있는데 아무 일도 안 일어나는 컨트롤을 남기지 않는다.
    renderPalette({ onToggleExclude: undefined, excludedSlugs: undefined })
    const chip = screen.getByRole('button', { name: '크라운' })
    expect(chip).not.toHaveAttribute('aria-pressed')
  })

  it('still toggles when the handler is given', () => {
    const onToggleExclude = vi.fn()
    renderPalette({ onToggleExclude })
    const chip = screen.getByRole('button', { name: /크라운 사용/ })
    expect(chip).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(chip)
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })
})
```

`renderPalette`가 이 파일에 없으면 기존 테스트의 `render(<UnitPalette … />)` 호출을 그대로 복사해 옵션만 덮어쓰는 헬퍼로 만든다. 이름(`크라운`)은 이 파일의 `supportedUnits` 픽스처가 쓰는 표시 이름에 맞춘다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- UnitPalette`
Expected: FAIL — `onToggleExclude is not a function` (클릭 핸들러가 undefined를 부른다) 또는 `aria-pressed`가 그대로 붙어 있다

- [ ] **Step 3: Write minimal implementation**

props 인터페이스를 교체:

```tsx
  /** Slugs the user has toggled OUT of the candidate pool. Absent on a screen
   * with no pool to narrow. */
  excludedSlugs?: string[]
  /** Omit on a screen where excluding a unit would do nothing — the chip then
   * stays a drag source instead of pretending to be a toggle. */
  onToggleExclude?: (slug: string) => void
```

구조 분해를 교체:

```tsx
  excludedSlugs = [],
  onToggleExclude,
```

face 버튼의 세 속성을 교체:

```tsx
                      aria-pressed={onToggleExclude ? !isExcluded : undefined}
                      aria-label={onToggleExclude ? `${unit.name} 사용` : unit.name}
                      ...
                      onClick={onToggleExclude ? () => onToggleExclude(unit.slug) : undefined}
```

(`draggable` 줄은 그대로 둔다 — `isExcluded`는 토글이 없으면 항상 false다.)

- [ ] **Step 4: Run tests and typecheck**

Run: `cd frontend && npm test && npx tsc -b --noEmit`
Expected: 실패 0, 타입에러 0. 추천 탭·유니온 탭 테스트가 그대로 통과해야 한다.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/UnitPalette.tsx frontend/src/components/UnitPalette.test.tsx
git commit -m "제외 토글이 아무 일도 안 하는 화면에서는 안 그린다

제외가 하는 일은 탐색 후보 풀에서 빼는 것인데, 미란다 계산기에는 탐색이
없고 제출되는 것은 배치된 다섯뿐이다. 기존 두 호출자는 계속 핸들러를
넘기므로 오늘 그대로 동작한다."
```

---

### Task 12: `MirandaTargets` — 뱃지와 임계값

**Files:**
- Create: `frontend/src/components/MirandaTargets.tsx`
- Modify: `frontend/src/App.css`
- Test: `frontend/src/components/MirandaTargets.test.tsx`

**Interfaces:**
- Consumes: Task 9의 `MirandaTargetsResult`
- Produces: `<MirandaTargets result={…} portraitFor={…} nameFor={…} />`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/MirandaTargets.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MirandaTargets } from './MirandaTargets'
import type { MirandaTargetsResult } from '../types/mirandaTargets'

const NAMES: Record<string, string> = {
  'miranda-signature': '미란다', crown: '크라운', 'ada-wong': '에이다 웡',
  cinderella: '신데렐라', isabel: '이사벨', miranda: '미란다',
}
const nameFor = (slug: string) => NAMES[slug] ?? slug

const base: MirandaTargetsResult = {
  seats: [
    { slug: 'miranda-signature', burstTier: 1 },
    { slug: 'crown', burstTier: 2 },
    { slug: 'ada-wong', burstTier: 3 },
    { slug: 'cinderella', burstTier: 3 },
    { slug: 'isabel', burstTier: 3 },
  ],
  mirandaSlug: 'miranda-signature',
  hasFavoriteItem: true,
  cycles: [
    { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
    { index: 2, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
  ],
  overloadThresholds: [],
  overloadAtkCapPercent: 58.52,
  notes: [],
  engineVersion: 'abc',
}

const renderResult = (result: MirandaTargetsResult) =>
  render(<MirandaTargets result={result} portraitFor={() => null} nameFor={nameFor} />)

const row = (name: string) => screen.getByRole('listitem', { name })

describe('MirandaTargets', () => {
  it('gives the wake-up recipient both badges and the powering-up-only unit the silver pair', () => {
    renderResult(base)
    expect(within(row('에이다 웡')).getByText('크확')).toBeInTheDocument()
    expect(within(row('에이다 웡')).getByText('공격력')).toBeInTheDocument()
    expect(within(row('크라운')).queryByText('크확')).not.toBeInTheDocument()
    expect(within(row('크라운')).getByText('크댐')).toBeInTheDocument()
    expect(within(row('이사벨')).queryByText('공격력')).not.toBeInTheDocument()
  })

  it('marks a badge that only holds in some cycles with n/T', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: ['ada-wong', 'isabel'], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    expect(within(row('크라운')).getByText('1/2')).toBeInTheDocument()
    expect(within(row('에이다 웡')).queryByText('1/2')).not.toBeInTheDocument()
  })

  it('names the cycles where powering-up changed hands', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: ['ada-wong', 'isabel'], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    expect(screen.getByText(/2사이클/)).toBeInTheDocument()
  })

  it('says outright when Miranda could not burst every cycle', () => {
    renderResult({
      ...base,
      cycles: [
        { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
        { index: 2, poweringUp: [], wakeUpCritRate: ['ada-wong'] },
      ],
    })
    expect(screen.getByText(/미란다는 2사이클 중 1번만 버스트해요/)).toBeInTheDocument()
  })

  it('states what a unit needs, what it can lose, and when nothing is enough', () => {
    renderResult({
      ...base,
      overloadThresholds: [
        { slug: 'crown', currentPercent: 8, kind: 'gain', thresholdPercent: 11.47 },
        { slug: 'ada-wong', currentPercent: 12, kind: 'keep', thresholdPercent: 9.9 },
        { slug: 'cinderella', currentPercent: 0, kind: 'keep', thresholdPercent: 0 },
        { slug: 'isabel', currentPercent: 0, kind: 'gain', thresholdPercent: null },
      ],
    })
    expect(screen.getByText(/8\.00% → 11\.47% 필요 \(\+3\.47%p\)/)).toBeInTheDocument()
    expect(screen.getByText(/9\.90% 밑으로 내려가면 놓쳐요/)).toBeInTheDocument()
    expect(screen.getByText(/오버로드 공격력이 없어도 유지돼요/)).toBeInTheDocument()
    expect(screen.getByText(/상한\(58\.52%\)까지 올려도 못 받아요/)).toBeInTheDocument()
  })

  it('shows every note the backend sent', () => {
    renderResult({ ...base, notes: ['무속성 보스·180초 전투를 가정해 계산했어요.'] })
    expect(screen.getByText(/무속성 보스/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- MirandaTargets`
Expected: FAIL — 모듈을 못 찾는다

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/MirandaTargets.tsx`:

```tsx
// 덱 5인 중 누가 미란다의 두 대상형 버프를 받는지, 초상화 옆 뱃지로.
//
// 금색 [크확] = 웨이크업! 3번불릿, 은색 [공격력][크댐] = 파워업!(버스트).
// 두 불릿의 대상은 사이클마다 바뀔 수 있어서, 뱃지는 「전 사이클」이 기본이고
// 일부 사이클에서만 받으면 n/T가 붙는다.

import type { MirandaTargetsResult } from '../types/mirandaTargets'

interface MirandaTargetsProps {
  result: MirandaTargetsResult
  portraitFor: (slug: string) => string | null
  nameFor: (slug: string) => string
}

const percent = (value: number) => `${value.toFixed(2)}%`

const countIn = (cycles: string[][], slug: string) =>
  cycles.filter((targets) => targets.includes(slug)).length

export function MirandaTargets({ result, portraitFor, nameFor }: MirandaTargetsProps) {
  const { cycles, seats, mirandaSlug, overloadThresholds, overloadAtkCapPercent } = result
  const total = cycles.length
  const poweringUp = cycles.map((cycle) => cycle.poweringUp)
  const wakeUp = cycles.map((cycle) => cycle.wakeUpCritRate)
  const thresholdFor = new Map(overloadThresholds.map((row) => [row.slug, row]))

  // 미란다가 버스트한 사이클과 못 한 사이클. 후자가 있으면 파워업!의 n/T가
  // 「밀렸다」가 아니라 「그녀가 못 쐈다」는 뜻이 되므로 따로 말해야 한다.
  const burstCycles = poweringUp.filter((targets) => targets.length > 0).length

  // 파워업! 대상이 사이클마다 갈리는가 - 갈리면 어느 사이클인지 짚어준다.
  const firstPoweringUp = poweringUp[0] ?? []
  const changedCycles = cycles
    .filter((cycle) =>
      cycle.poweringUp.length > 0 &&
      (cycle.poweringUp.length !== firstPoweringUp.length ||
        cycle.poweringUp.some((slug) => !firstPoweringUp.includes(slug))))
    .map((cycle) => cycle.index)

  const describeThreshold = (slug: string): string | null => {
    const row = thresholdFor.get(slug)
    if (!row) return null
    if (row.kind === 'gain') {
      if (row.thresholdPercent === null) {
        return `오버로드 공격력을 상한(${percent(overloadAtkCapPercent)})까지 올려도 못 받아요`
      }
      const gap = row.thresholdPercent - row.currentPercent
      return `오버로드 공격력 ${percent(row.currentPercent)} → ${percent(row.thresholdPercent)} 필요 (+${gap.toFixed(2)}%p)`
    }
    if (row.thresholdPercent === 0) return '오버로드 공격력이 없어도 유지돼요'
    const slack = row.currentPercent - row.thresholdPercent
    return `오버로드 공격력이 ${percent(row.thresholdPercent)} 밑으로 내려가면 놓쳐요 (지금 ${percent(row.currentPercent)}, 여유 ${slack.toFixed(2)}%p)`
  }

  return (
    <section className="miranda-targets">
      <ul className="miranda-targets__list">
        {seats.map((seat) => {
          const name = nameFor(seat.slug)
          const portrait = portraitFor(seat.slug)
          const wakeCount = countIn(wakeUp, seat.slug)
          const powerCount = countIn(poweringUp, seat.slug)
          const threshold = describeThreshold(seat.slug)
          return (
            <li className="miranda-targets__row" key={seat.slug} aria-label={name}>
              {portrait ? (
                <img className="miranda-targets__portrait" src={portrait} alt="" />
              ) : (
                <span className="miranda-targets__portrait miranda-targets__portrait--missing" />
              )}
              <span className="miranda-targets__name">{name}</span>
              {seat.slug === mirandaSlug ? (
                <span className="miranda-targets__caster">시전자</span>
              ) : (
                <span className="miranda-targets__badges">
                  {wakeCount > 0 && (
                    <span className="miranda-badge miranda-badge--gold">
                      <span>크확</span>
                      {wakeCount < total && <b>{wakeCount}/{total}</b>}
                    </span>
                  )}
                  {powerCount > 0 && (
                    <>
                      <span className="miranda-badge miranda-badge--silver"><span>공격력</span></span>
                      <span className="miranda-badge miranda-badge--silver">
                        <span>크댐</span>
                        {powerCount < total && <b>{powerCount}/{total}</b>}
                      </span>
                    </>
                  )}
                </span>
              )}
              {threshold && <span className="miranda-targets__threshold">{threshold}</span>}
            </li>
          )
        })}
      </ul>

      {changedCycles.length > 0 && (
        <p className="miranda-targets__caveat">
          ⚠ {changedCycles.join('·')}사이클에는 파워업!을 받는 니케가 달라요
        </p>
      )}
      {burstCycles < total && (
        <p className="miranda-targets__caveat">
          ⚠ 미란다는 {total}사이클 중 {burstCycles}번만 버스트해요 (같은 1티어에 니케가 둘이에요)
        </p>
      )}
      {result.notes.map((note) => (
        <p className="miranda-targets__note" key={note}>{note}</p>
      ))}
    </section>
  )
}
```

`frontend/src/App.css` 맨 아래에 추가:

```css
/* 미란다 계산기 결과 — 초상화 한 줄에 뱃지와 임계값. 금은 웨이크업!3(단 한
   명), 은은 파워업!(둘). 색만으로 구분되지 않도록 글자가 스탯 이름을 말한다. */
.miranda-targets__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.miranda-targets__row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.miranda-targets__portrait {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  object-fit: cover;
}

.miranda-targets__portrait--missing {
  background: var(--rule);
}

.miranda-targets__name {
  font-weight: 550;
  min-width: 7ch;
}

.miranda-targets__badges {
  display: flex;
  gap: var(--sp-1);
  flex-wrap: wrap;
}

.miranda-badge {
  display: inline-flex;
  align-items: baseline;
  gap: 0.25em;
  padding: 0.1em 0.5em;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  border: 1px solid;
}

.miranda-badge--gold {
  color: #8a6b12;
  border-color: #d8b13a;
  background: #fdf4dc;
}

.miranda-badge--silver {
  color: #55585c;
  border-color: #b9bdc2;
  background: #f2f3f5;
}

.miranda-badge b {
  font-weight: 500;
  opacity: 0.75;
}

.miranda-targets__caster,
.miranda-targets__threshold,
.miranda-targets__caveat,
.miranda-targets__note {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.miranda-targets__threshold {
  flex-basis: 100%;
  padding-left: calc(40px + var(--sp-2));
}
```

- [ ] **Step 4: Run tests and typecheck**

Run: `cd frontend && npm test -- MirandaTargets`
Expected: PASS 전부

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 에러 0

`row(name)`의 `getByRole('listitem', { name })`이 안 잡히면 `<li aria-label={name}>`이 붙었는지 확인한다.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/MirandaTargets.tsx frontend/src/components/MirandaTargets.test.tsx frontend/src/App.css
git commit -m "누가 받는지를 초상화 옆 뱃지로 답한다

금색 [크확]이 웨이크업!3, 은색 [공격력][크댐]이 파워업!이다. 대상이 사이클
마다 갈리면 어느 사이클인지 짚고, 미란다가 못 쏜 사이클이 있으면 n/T가
「밀렸다」로 읽히지 않게 따로 말한다.

색만으로는 구분되지 않게 뱃지가 스탯 이름을 글자로 쓴다."
```

---

### Task 13: `MirandaCalculatorPanel` — 편성과 실행

**Files:**
- Create: `frontend/src/components/MirandaCalculatorPanel.tsx`
- Test: `frontend/src/components/MirandaCalculatorPanel.test.tsx`

**Interfaces:**
- Consumes: Task 9의 `postMirandaTargets`, Task 10의 `fixedSlugs`, Task 11의 옵셔널 제외, Task 12의 `MirandaTargets`
- Produces: `<MirandaCalculatorPanel roster supportedUnits portraitFor nameFor burstTiersFor investmentFor />`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/MirandaCalculatorPanel.test.tsx`:

```tsx
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MirandaCalculatorPanel, seatedMirandaSlug } from './MirandaCalculatorPanel'
import { DRAG_SLUG_TYPE } from './UnitPalette'
import type { SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'

const UNITS: SupportedUnit[] = [
  { slug: 'miranda-signature', name: '미란다', burstTier: 1, element: 'Fire' },
  { slug: 'miranda', name: '미란다', burstTier: 1, element: 'Fire' },
  { slug: 'crown', name: '크라운', burstTier: 2, element: 'Iron' },
  { slug: 'ada-wong', name: '에이다 웡', burstTier: 3, element: 'Fire' },
  { slug: 'cinderella', name: '신데렐라', burstTier: 3, element: 'Water' },
  { slug: 'isabel', name: '이사벨', burstTier: 3, element: 'Wind' },
]

const FULL = ['miranda-signature', 'crown', 'ada-wong', 'cinderella', 'isabel']

const WIRE = {
  seats: FULL.map((slug, i) => ({ slug, burst_tier: i === 0 ? 1 : i === 1 ? 2 : 3 })),
  miranda_slug: 'miranda-signature',
  has_favorite_item: true,
  cycles: [{ index: 1, powering_up: ['ada-wong', 'crown'], wake_up_crit_rate: ['ada-wong'] }],
  overload_thresholds: [],
  overload_atk_cap_percent: 58.52,
  notes: [],
  engine_version: 'abc',
}

const state = (slug: string) => ({ character_slug: slug, atk: 100000 }) as unknown as UserNikkeState

const renderPanel = (roster: UserNikkeState[]) =>
  render(
    <MirandaCalculatorPanel
      roster={roster}
      supportedUnits={UNITS}
      portraitFor={() => null}
      nameFor={(slug) => UNITS.find((u) => u.slug === slug)?.name ?? slug}
      burstTiersFor={(slug) => {
        const tier = UNITS.find((u) => u.slug === slug)?.burstTier
        return tier ? [tier] : []
      }}
    />,
  )

/** 팔레트에서 덱으로 끌어다 놓는 것과 같은 경로 - DraftEditor의 덱 컨테이너가
 * 드롭을 받아 자리에 앉힌다. */
const seat = (container: HTMLElement, ...slugs: string[]) => {
  for (const slug of slugs) {
    const deck = container.querySelector('.draft-editor__deck')!
    fireEvent.drop(deck, {
      dataTransfer: { getData: (type: string) => (type === DRAG_SLUG_TYPE ? slug : '') },
    })
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('MirandaCalculatorPanel', () => {
  it('seats Miranda before the player touches anything', () => {
    renderPanel([state('miranda-signature'), state('crown'), state('ada-wong')])
    // 좌석은 하나 차 있고 나머지 넷이 비어 있다.
    expect(screen.getByText('1/5')).toBeInTheDocument()
    // 그리고 그 자리는 비울 수 없다.
    expect(screen.queryByRole('button', { name: /미란다 제거/ })).not.toBeInTheDocument()
  })

  it('prefers the favorite-item build, falls back to the base one, and reports neither', () => {
    // 어느 빌드가 앉는지는 답을 바꾼다(애장품이면 파워업! 2명 + 웨이크업!3,
    // 아니면 파워업! 1명뿐). 화면 글자로는 둘 다 "미란다"라 구분되지 않으므로
    // 고르는 함수를 직접 본다.
    expect(seatedMirandaSlug([state('miranda'), state('crown')])).toBe('miranda')
    expect(seatedMirandaSlug([state('miranda-signature'), state('crown')]))
      .toBe('miranda-signature')
    expect(seatedMirandaSlug([state('crown')])).toBeNull()
  })

  it('asks the player to sync when the roster has no Miranda at all', () => {
    renderPanel([state('crown'), state('ada-wong')])
    expect(screen.getByText(/미란다가 로스터에 없어요/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /계산/ })).not.toBeInTheDocument()
  })

  it('keeps the run button disabled until all five seats are filled', () => {
    renderPanel([state('miranda-signature'), state('crown'), state('ada-wong')])
    expect(screen.getByRole('button', { name: /계산/ })).toBeDisabled()
  })

  it('submits the five seated slugs once the deck is full', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(WIRE) })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderPanel(FULL.map(state))
    seat(container, 'crown', 'ada-wong', 'cinderella', 'isabel')
    const run = screen.getByRole('button', { name: '계산' })
    await waitFor(() => expect(run).toBeEnabled())
    await userEvent.click(run)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string)
    expect(body.units.sort()).toEqual([...FULL].sort())
  })

  it('shows the backend detail when the request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 422,
      json: () => Promise.resolve({ detail: '이 다섯으로는 성립하는 버스트 순서가 없어요.' }),
    }))
    const { container } = renderPanel(FULL.map(state))
    seat(container, 'crown', 'ada-wong', 'cinderella', 'isabel')
    await userEvent.click(screen.getByRole('button', { name: '계산' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('버스트 순서')
    // 실패해도 편성은 남는다 - 다시 짜게 만들면 화면이 유저를 벌주는 셈이다.
    expect(screen.getByText('5/5')).toBeInTheDocument()
  })
})
```

프론트의 `SupportedUnit`은 camelCase(`burstTier`)다 — wire 쪽만 `burst_tier`다
(`frontend/src/types/supportedUnit.ts`). `seat()`가 아무것도 안 앉히면
`.draft-editor__deck` 클래스 이름이 바뀐 것이니 `DraftEditor.tsx`에서 확인한다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- MirandaCalculatorPanel`
Expected: FAIL — 모듈을 못 찾는다

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/MirandaCalculatorPanel.tsx`:

```tsx
// 미란다 계산기: 미란다를 포함한 5인을 편성하면 파워업!과 웨이크업! 3번불릿을
// 누가 받는지 답한다.
//
// 미란다는 처음부터 앉아 있고 유저는 남은 네 자리만 채운다. 「맨 왼쪽」에
// 장치가 없는 이유는 DraftEditor가 좌석을 버스트 티어 순으로 그리기 때문이다 -
// 그녀는 B1이라 언제나 첫 칸이고, 같은 B1이 하나 더 들어와도 정렬이 안정적이라
// 먼저 앉은 그녀가 앞에 남는다.

import { useMemo, useState } from 'react'
import { postMirandaTargets } from '../api/mirandaTargets'
import { RecommendApiError, describeRecommendApiError } from '../api/recommendApiError'
import { isDraftComplete, makeEmptyDraft, type Draft } from '../types/draft'
import type { MirandaTargetsResult } from '../types/mirandaTargets'
import type { BurstTier, SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { DraftEditor, placeUnit } from './DraftEditor'
import { MirandaTargets } from './MirandaTargets'
import { UnitPalette, type UnitInvestment } from './UnitPalette'

// 애장품을 보유하면 로스터 임포트가 이미 "-signature"로 승격해 둔다. 어느
// 빌드인지가 답을 바꾸므로(애장품이면 파워업! 2명 + 웨이크업!3, 아니면 파워업!
// 1명뿐) 로스터가 가진 쪽을 그대로 앉힌다.
const MIRANDA_SLUGS = ['miranda-signature', 'miranda']

/** 이 로스터에 앉힐 미란다. 애장품 빌드가 있으면 그쪽이다 - 어느 빌드인지가
 * 답을 바꾸므로 화면 글자("미란다", 둘 다 같다)가 아니라 이 함수가 결정을
 * 쥔다. Exported so the decision can be tested without seating a whole deck. */
export const seatedMirandaSlug = (roster: UserNikkeState[]): string | null =>
  MIRANDA_SLUGS.find((slug) => roster.some((n) => n.character_slug === slug)) ?? null

interface MirandaCalculatorPanelProps {
  roster: UserNikkeState[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
  nameFor: (slug: string) => string
  burstTiersFor: (slug: string) => BurstTier[]
  investmentFor?: (slug: string) => UnitInvestment
}

export function MirandaCalculatorPanel({
  roster,
  supportedUnits,
  portraitFor,
  nameFor,
  burstTiersFor,
  investmentFor,
}: MirandaCalculatorPanelProps) {
  const mirandaSlug = useMemo(() => seatedMirandaSlug(roster), [roster])
  const [draft, setDraft] = useState<Draft>(() =>
    mirandaSlug ? placeUnit(makeEmptyDraft(1), 0, mirandaSlug) : makeEmptyDraft(1),
  )
  const [result, setResult] = useState<MirandaTargetsResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const seats = draft.decks[0] ?? []
  const usedSlugs = seats.map((seat) => seat.slug)
  const full = isDraftComplete(draft, 1)

  if (mirandaSlug === null) {
    return (
      <section className="card" aria-label="미란다 계산기">
        <p className="empty__text">
          미란다가 로스터에 없어요. 동기화 탭에서 로스터를 다시 가져와 주세요.
        </p>
      </section>
    )
  }

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      setResult(await postMirandaTargets({ roster, units: usedSlugs }))
    } catch (err) {
      setResult(null)
      setError(
        err instanceof RecommendApiError
          ? describeRecommendApiError(err)
          : '계산에 실패했습니다.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card" aria-label="미란다 계산기">
      <header className="card__header">
        <h2 className="card__title">미란다 계산기</h2>
      </header>
      <p className="group__hint">
        미란다는 이미 앉아 있어요. 남은 네 자리를 채우면 파워업!과 웨이크업!
        3번불릿을 누가 받는지 알려줘요.
      </p>

      <div className="draft-layout">
        <UnitPalette
          roster={roster}
          supportedUnits={supportedUnits}
          usedSlugs={usedSlugs}
          draggable
          investmentFor={investmentFor}
        />
        <div className="draft-layout__decks">
          <DraftEditor
            numDecks={1}
            value={draft}
            onChange={setDraft}
            portraitFor={portraitFor}
            nameFor={nameFor}
            burstTiersFor={burstTiersFor}
            showLocks={false}
            fixedSlugs={[mirandaSlug]}
          />
          <div className="recommend-form__actions">
            <button type="button" className="btn btn--primary" onClick={run} disabled={!full || busy}>
              {busy ? '계산 중…' : '계산'}
            </button>
          </div>
        </div>
      </div>

      {busy && (
        <p className="recommend-form__progress" role="status">
          시뮬레이션을 돌리는 중이에요 — 몇 초 걸려요.
        </p>
      )}
      {error && <p className="field__error" role="alert">{error}</p>}
      {result && (
        <MirandaTargets result={result} portraitFor={portraitFor} nameFor={nameFor} />
      )}
    </section>
  )
}
```

- [ ] **Step 4: Run tests and typecheck**

Run: `cd frontend && npm test -- MirandaCalculatorPanel`
Expected: PASS 전부

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 에러 0

`UnitInvestment`가 `UnitPalette`에서 export되지 않으면 `investmentFor`의 타입을 `(slug: string) => { grade?: number; core?: number; favoriteItem?: boolean }`로 직접 적지 말고, `UnitPalette.tsx`의 실제 export 이름을 확인해 그것을 import한다.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/MirandaCalculatorPanel.tsx frontend/src/components/MirandaCalculatorPanel.test.tsx
git commit -m "미란다를 앉힌 채로 시작하는 편성 화면

편성은 유니온 탭과 같은 컴포넌트라 드래그·초상화·티어 뱃지 동작이 자동으로
일치한다. 로스터가 애장품을 가졌으면 그 빌드가 앉는다 - 어느 빌드인지가
답을 바꾸기 때문이다.

로스터에 미란다가 아예 없으면 빈 덱을 그려 두고 422를 기다리는 대신
안내만 띄운다. 그 화면에서 유저가 할 수 있는 일이 없다."
```

---

### Task 14: 계산기 탭에 서브탭을 두고 App에 연결

**Files:**
- Create: `frontend/src/components/CalculatorPanel.tsx`
- Modify: `frontend/src/App.tsx:22` (import), `:261-276` (계산기 패널)
- Modify: `frontend/src/App.css`
- Test: `frontend/src/components/CalculatorPanel.test.tsx`

**Interfaces:**
- Consumes: 기존 `ChargeWindowPanel`, Task 13의 `MirandaCalculatorPanel`
- Produces: `<CalculatorPanel roster supportedUnits portraitFor nameFor burstTiersFor investmentFor />`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/CalculatorPanel.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CalculatorPanel } from './CalculatorPanel'
import type { SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'

const UNITS: SupportedUnit[] = [
  { slug: 'miranda-signature', name: '미란다', burstTier: 1, element: 'Fire' },
  { slug: 'scarlet-black-shadow', name: '홍련: 흑영', burstTier: 3, element: 'Fire' },
]
const ROSTER = [
  { character_slug: 'miranda-signature', atk: 100000 },
  { character_slug: 'scarlet-black-shadow', atk: 100000 },
] as unknown as UserNikkeState[]

const renderPanel = () =>
  render(
    <CalculatorPanel
      roster={ROSTER}
      supportedUnits={UNITS}
      portraitFor={() => null}
      nameFor={(slug) => UNITS.find((u) => u.slug === slug)?.name ?? slug}
      burstTiersFor={(slug) => {
        const tier = UNITS.find((u) => u.slug === slug)?.burstTier
        return tier ? [tier] : []
      }}
    />,
  )

describe('CalculatorPanel', () => {
  it('opens on the charge calculator', () => {
    renderPanel()
    expect(screen.getByRole('tab', { name: '차속 + 타수 계산기' })).toHaveAttribute(
      'aria-selected', 'true')
    expect(screen.getByRole('tab', { name: '미란다 계산기' })).toHaveAttribute(
      'aria-selected', 'false')
  })

  it('switches to the Miranda calculator', async () => {
    renderPanel()
    await userEvent.click(screen.getByRole('tab', { name: '미란다 계산기' }))
    expect(screen.getByRole('tab', { name: '미란다 계산기' })).toHaveAttribute(
      'aria-selected', 'true')
    expect(screen.getByRole('heading', { name: '미란다 계산기' })).toBeVisible()
  })

  it('keeps the hidden calculator mounted so its typed input survives a switch', async () => {
    // 언마운트하면 차지 계산기에 입력한 값이 탭을 오갈 때 날아간다.
    renderPanel()
    const field = screen.getByRole('spinbutton', { name: /차지속도 합계/ })
    await userEvent.type(field, '12.5')
    await userEvent.click(screen.getByRole('tab', { name: '미란다 계산기' }))
    await userEvent.click(screen.getByRole('tab', { name: '차속 + 타수 계산기' }))
    expect(screen.getByRole('spinbutton', { name: /차지속도 합계/ })).toHaveValue(12.5)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- CalculatorPanel`
Expected: FAIL — 모듈을 못 찾는다

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/CalculatorPanel.tsx`:

```tsx
// 계산기 탭의 서브탭. 계산기를 늘리는 일은 아래 배열에 항목 하나를 넣는 일이다.
//
// 두 패널을 다 마운트한 채 hidden으로 감춘다 - 메인 탭이 이미 그렇고, 그래야
// 차지 계산기에 입력한 값이 서브탭을 오갈 때 날아가지 않는다.

import { useState } from 'react'
import type { BurstTier, SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { ChargeWindowPanel } from './ChargeWindowPanel'
import { MirandaCalculatorPanel } from './MirandaCalculatorPanel'
import type { UnitInvestment } from './UnitPalette'

type CalculatorId = 'charge' | 'miranda'

const CALCULATORS: { id: CalculatorId; label: string }[] = [
  { id: 'charge', label: '차속 + 타수 계산기' },
  { id: 'miranda', label: '미란다 계산기' },
]

interface CalculatorPanelProps {
  roster: UserNikkeState[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
  nameFor: (slug: string) => string
  burstTiersFor: (slug: string) => BurstTier[]
  investmentFor?: (slug: string) => UnitInvestment
}

export function CalculatorPanel({
  roster,
  supportedUnits,
  portraitFor,
  nameFor,
  burstTiersFor,
  investmentFor,
}: CalculatorPanelProps) {
  const [active, setActive] = useState<CalculatorId>('charge')

  return (
    <div className="calculators">
      <div className="tabs tabs--sub" role="tablist" aria-label="계산기">
        {CALCULATORS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`calc-tab-${id}`}
            aria-controls={`calc-panel-${id}`}
            aria-selected={active === id}
            className={active === id ? 'tabs__tab tabs__tab--active' : 'tabs__tab'}
            onClick={() => setActive(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id="calc-panel-charge"
        aria-labelledby="calc-tab-charge"
        hidden={active !== 'charge'}
      >
        <ChargeWindowPanel roster={roster} nameFor={nameFor} />
      </div>

      <div
        role="tabpanel"
        id="calc-panel-miranda"
        aria-labelledby="calc-tab-miranda"
        hidden={active !== 'miranda'}
      >
        <MirandaCalculatorPanel
          roster={roster}
          supportedUnits={supportedUnits}
          portraitFor={portraitFor}
          nameFor={nameFor}
          burstTiersFor={burstTiersFor}
          investmentFor={investmentFor}
        />
      </div>
    </div>
  )
}
```

`frontend/src/App.tsx:22`의 import를 교체:

```tsx
import { CalculatorPanel } from './components/CalculatorPanel'
```

`frontend/src/App.tsx:268-275`의 `<ChargeWindowPanel …/>`를 교체:

```tsx
              <CalculatorPanel
                // Same reasoning as RecommendPanel's key: a result computed for
                // one profile must not stay on screen after a switch, and the
                // panels' own state is the only place it lives.
                key={state.activeKey ?? 'none'}
                roster={validRoster}
                supportedUnits={supportedUnits.units}
                portraitFor={portraitFor}
                nameFor={nameFor}
                burstTiersFor={burstTiersResolver}
                investmentFor={investmentFor}
              />
```

`frontend/src/App.css`의 `.tabs__tab--active` 규칙 뒤에 추가:

```css
/* 서브탭은 메인 탭보다 한 단 작다 - 같은 줄로 보이면 어느 쪽이 화면을
   가르는지 읽히지 않는다. */
.tabs--sub .tabs__tab {
  padding: var(--sp-2) var(--sp-3);
  font-size: 0.9rem;
}

.calculators {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  width: 100%;
}
```

- [ ] **Step 4: Run the whole frontend suite and typecheck**

Run: `cd frontend && npm test`
Expected: 실패 0. `App.test.tsx`가 계산기 탭을 이름으로 찾고 있으면 여기서 깨진다 — 깨지면 그 테스트가 무엇을 확인하려던 것인지 읽고, 새 구조에 맞게 고친다(탭 이름이 바뀐 것이지 기능이 없어진 것이 아니다).

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 에러 0

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CalculatorPanel.tsx frontend/src/components/CalculatorPanel.test.tsx frontend/src/App.tsx frontend/src/App.css
git commit -m "계산기 탭에 서브탭을 둔다

계산기를 늘리는 일이 배열에 항목 하나 넣는 일이 되게 한다. 두 패널을 다
마운트한 채 hidden으로 감추는 것은 메인 탭과 같은 이유다 - 차지 계산기에
입력한 값이 서브탭을 오갈 때 날아가면 안 된다."
```

---

### Task 15: 전체 확인과 문서 갱신

**Files:**
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: Task 1~14 전부
- Produces: 없음

- [ ] **Step 1: 백엔드 전체 스위트**

Run: `cd backend && python -m pytest -q`
Expected: 실패 0. 기준선 2145에 이 계획이 더한 만큼 늘어 있어야 한다.

- [ ] **Step 2: 프론트 전체 스위트와 타입 검사**

Run: `cd frontend && npm test`
Expected: 실패 0 (기준선 638 + 신규)

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 에러 0

**둘 다 돌려야 한다** — vitest는 타입을 보지 않는다.

- [ ] **Step 3: 딜 수치가 안 움직였는지 확인**

계측이 기본 off라는 주장의 마지막 확인이다.

Run: `cd backend && python -m pytest tests/test_raid_simulator.py tests/test_deck_search.py tests/test_deck_allocation.py tests/test_deck_evaluation.py -q`
Expected: 실패 0. 이 네 파일이 딜 수치를 못박는 곳이고, 하나라도 깨지면 계측이 핫패스에 샌 것이다.

- [ ] **Step 4: 로드맵 갱신**

`docs/roadmap.md`의 To-Do 체크리스트에서 계산기 관련 항목을 찾아 미란다 계산기를 완료로 적는다. 해당 항목이 없으면 계산기 섹션에 한 줄을 더한다:

```markdown
- [x] 미란다 계산기 — 덱 5인 중 누가 파워업!·웨이크업!3을 받는지, 받으려면 오버로드 공격력이 얼마나 필요한지 (2026-08-08)
```

- [ ] **Step 5: Commit**

```bash
git add docs/roadmap.md
git commit -m "로드맵: 미란다 계산기 착륙"
```

- [ ] **Step 6: 앱을 띄워 실제로 확인**

CSS 결함은 테스트로 안 잡힌다(vitest는 `css: false`). `/run` 스킬이나 아래로 직접 확인한다.

```bash
# 포트 8000에 Fienn의 --reload 개발 백엔드가 이미 떠 있을 수 있다.
# 그러면 uvicorn이 exit 3 (10048)로 죽는다 - 그때는 이미 떠 있는 쪽을 쓴다. 죽이지 말 것.
cd backend && python -m uvicorn app.api:app --port 8000
# 다른 터미널에서
cd frontend && npm run dev   # :5173 -> :8000 프록시
```

확인할 것: 계산기 탭에 서브탭 둘이 보인다 · 미란다 계산기에 그녀가 첫 칸에 앉아 있고 ×가 없다 · 네 자리를 채우면 계산 버튼이 켜진다 · 결과의 금/은 뱃지가 읽힌다 · 임계값 문장이 잘리지 않는다.

---

## Self-Review

**1. Spec coverage**

| 설계문서 | 태스크 |
|---|---|
| §1.2 타이밍 검증 | Task 4 |
| §1.3 최종 공격력이 세는 항 | Task 4 (`test_overload_atk_alone_decides_the_ranking`) |
| §3 엔진 계측 opt-in | Task 1·2·3 |
| §4 miranda_targets 모듈 | Task 6 |
| §4.1 불릿 가려내기 | Task 6 (`POWERING_UP_STAT`/`WAKE_UP_CRIT_RATE_STAT`) + Task 2의 테스트 |
| §4.2 사이클 묶기 | Task 6 (`cycles_from_result`) |
| §4.3 반환 | Task 6·7 |
| §5 오버로드 임계값 | Task 5·7 |
| §6 API | Task 8 |
| §7.1 서브탭 | Task 14 |
| §7.2 편성·고정 좌석·팔레트 | Task 10·11·13 |
| §7.3 뱃지 | Task 12 |
| §7.4 임계값 표시 | Task 12 |
| §7.5 파일 | Task 9~14 |
| §8 애장품 | Task 6(안내) · Task 13(슬러그 선택) |
| §9 안 바뀌는 것 | Task 15 Step 3 |
| §10 테스트 | 각 태스크 |

**2. Placeholder scan** — "TBD"/"적절히"/"위의 테스트를 작성" 없음. 모든 코드 스텝에 실제 코드가 있다.

**3. Type consistency** — `cycles_from_result` / `order_deck` / `with_overload_atk` / `current_overload_atk` / `overload_thresholds`는 Task 6·7에서 정의된 이름 그대로 Task 7의 테스트와 Task 8이 쓴다. `MirandaTargetsResult`의 camelCase 필드명(`poweringUp`, `wakeUpCritRate`, `thresholdPercent`, `overloadAtkCapPercent`)은 Task 9에서 정의되어 Task 12·13이 그대로 쓴다. `fixedSlugs`(Task 10)와 `onToggleExclude` 옵셔널화(Task 11)는 Task 13이 소비한다.
