# Phase A: 버스트 사이클 타이밍 감사 + 문서화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 엔진의 버스트 사이클(게이지→B1→B2→B3→풀버스트)에서 버프 트리거가 각 버스트 넉에 어떻게 착지하는지 실증 테스트로 고정하고 문서화한다. 부수로 Laplace의 "버스트 3단계 진입" 버프를 자기 버스트 게이팅으로 정정한다.

**Architecture:** 순수 검증/문서화 단계. 엔진 동작은 바꾸지 않는다 — 신규 회귀 테스트가 현재 동작을 *핀으로 고정*하고, `docs/insights.md`가 그 이유를 설명한다. 유일한 코드 변경은 Laplace 룰 1건의 트리거 교체(숫자 불변, 게이팅만 정확해짐).

**Tech Stack:** Python 3, pytest, 기존 `app.raid_simulator.simulate_raid` / `app.squad_engine.SkillRule` / `app.effects.Effect`.

## Global Constraints

- 작업 디렉터리는 워크트리 `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\skill-encoding`, 브랜치 `wip/skill-encoding`. 백엔드 명령은 `backend/`에서 실행.
- 테스트 실행은 항상 `PYTHONIOENCODING=utf-8 python -m pytest ...` (Windows cp949 인코딩 에러 회피).
- 엔진 동작(딜 수치)을 바꾸지 않는다. Phase A에서 전체 스위트의 기존 기대값은 하나도 바뀌면 안 된다. Laplace 테스트의 트리거 이름만 갱신된다.
- 커밋은 각 Task 끝에서. 훅을 건너뛰지 않는다.
- 확인된 엔진 사실(스펙에서 인용, 재검증 대상):
  - `effects.py:238` — 버프 active-window는 시작 포함: `applied_at <= now < applied_at + duration`.
  - `burst_cycle.py` — `on_tier_fire`가 tier 1→2→3 순으로 호출(auto gap 0.0, manual gap 0.1), 이후 `on_full_burst_enter(tier3_fire_time)` 호출. 즉 `full_burst_enter` 시각 == B3 발동 시각.
  - `raid_simulator.py:585` — `own_burst_activate` 룰이 먼저 발동, `:632` — 버스트 넉이 그 다음 기록. record-then-compute라 넉 데미지는 2단계에서 넉 시각 기준 라이브 버프를 읽는다.

---

### Task 1: 버스트 타이밍 회귀 테스트 (실증 감사)

현재 엔진 동작을 4개 테스트로 고정한다. 이 테스트들이 Phase A의 "체크" 산출물이다.

**Files:**
- Create: `backend/tests/test_burst_cycle_buff_timing.py`

**Interfaces:**
- Consumes: `app.raid_simulator.simulate_raid`, `app.squad_engine.SkillRule`, `app.effects.Effect` (기존 공개 API, 변경 없음).
- Produces: 없음 (테스트 전용 파일). 후속 Task는 이 파일을 수정하지 않는다.

- [ ] **Step 1: 테스트 파일을 작성한다 (4개 테스트 모두 실패 예상 아님 — 현재 동작을 고정하는 characterization 테스트다)**

`backend/tests/test_burst_cycle_buff_timing.py`:

```python
"""버스트 사이클에서 어떤 트리거의 버프가 어떤 버스트 넉에 닿는가.

Fienn의 정본 로테이션(2026-07-24)에 대한 엔진의 답을 고정한다:
  게이지 충전 -> 1단계 진입 -> B1 사용 -> 2단계 진입 -> B2 사용
  -> 3단계 진입 -> B3 사용 -> 풀버스트 10초
엔진에는 "N단계 진입"이라는 별도 이벤트가 없다: `on_tier_fire`가 곧 "BN 사용"이고
`full_burst_enter`는 tier-3 발동 시각에 발동한다. 해설은 docs/insights.md 참고.
"""
from app.effects import Effect
from app.raid_simulator import simulate_raid
from app.squad_engine import SkillRule


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats():
    return {
        "buffer": {"atk": 10000, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "attacker": {"atk": 10000, "def": 0, "max_hp": 0},
    }


def empty_rules():
    return {"buffer": [], "midtier": [], "attacker": []}


def attack_damage_rule(trigger, target_slug):
    """target_slug 본인에게 Attack Damage +50%를 영구 부여하는 룰."""

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", 0.5, "self", None, target_slug),
            applied_at=time,
        )

    return SkillRule(trigger=trigger, action=action)


def run(rules_by_slug, burst_percents, mode="auto"):
    return simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents=burst_percents,
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode=mode,
        base_crit_rate=0.0,
    )


def test_full_burst_enter_buff_reaches_the_tier3_own_burst_nuke():
    """full_burst_enter 시각 == B3 발동 시각이고 active-window가 시작 포함이라,
    B3 유닛의 자기 버스트 넉은 이 버프를 읽는다."""
    baseline = run(empty_rules(), {"attacker": 1000.0})
    rules = empty_rules()
    rules["attacker"] = [attack_damage_rule("full_burst_enter", "attacker")]
    buffed = run(rules, {"attacker": 1000.0})

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"] * 1.5


def test_own_burst_activate_buff_reaches_the_tier3_own_burst_nuke():
    """own_burst_activate 룰은 넉이 기록되기 전에 발동하므로 당연히 닿는다."""
    baseline = run(empty_rules(), {"attacker": 1000.0})
    rules = empty_rules()
    rules["attacker"] = [attack_damage_rule("own_burst_activate", "attacker")]
    buffed = run(rules, {"attacker": 1000.0})

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"] * 1.5


def test_full_burst_enter_buff_reaches_a_tier1_own_burst_nuke_in_auto_mode():
    """auto 모드는 tier 간 gap이 0이라 B1 넉과 full_burst_enter가 동시각 -> 닿는다."""
    baseline = run(empty_rules(), {"buffer": 1000.0}, mode="auto")
    rules = empty_rules()
    rules["buffer"] = [attack_damage_rule("full_burst_enter", "buffer")]
    buffed = run(rules, {"buffer": 1000.0}, mode="auto")

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"] * 1.5


def test_full_burst_enter_buff_misses_a_tier1_own_burst_nuke_in_manual_mode():
    """manual 모드는 tier 간 0.1초 간격이라 B1 넉이 full_burst_enter보다 0.2초 먼저
    발생한다 -> 그 넉은 버프를 못 읽는다. B1/B2의 자기 버스트딜에 곱해져야 하는
    버프는 own_burst_activate를 써야 한다는 근거."""
    baseline = run(empty_rules(), {"buffer": 1000.0}, mode="manual")
    rules = empty_rules()
    rules["buffer"] = [attack_damage_rule("full_burst_enter", "buffer")]
    buffed = run(rules, {"buffer": 1000.0}, mode="manual")

    assert baseline["total_damage"] > 0
    assert buffed["total_damage"] == baseline["total_damage"]
```

- [ ] **Step 2: 테스트를 실행해 현재 동작을 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_burst_cycle_buff_timing.py -v
```

Expected: 4개 모두 PASS.

**중요 — 만약 실패한다면**, 스펙의 사전 조사 결론이 틀린 것이다. 그 경우 테스트를 억지로 통과시키지 말고 **실제 동작에 맞게 테스트의 기대값과 docstring을 고친 뒤, 달라진 사실을 Task 3의 문서에 반영**한다(이 Task의 목적은 진실을 고정하는 것이지 예상을 관철하는 게 아니다). 특히 `test_full_burst_enter_buff_reaches_the_tier3_own_burst_nuke`가 실패하면 Laplace의 52.14%가 실제로 버스트딜에서 누락돼 온 것이므로, Task 2의 트리거 교체는 숫자를 바꾸는 **버그 수정**이 된다 — 그 사실을 커밋 메시지와 문서에 명시할 것.

- [ ] **Step 3: 전체 스위트가 여전히 그린인지 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```

Expected: 신규 4건이 더해진 상태로 전부 PASS, 기존 실패 없음.

- [ ] **Step 4: 커밋**

```bash
git add backend/tests/test_burst_cycle_buff_timing.py
git commit -m "Pin burst-cycle buff timing: which triggers reach which burst nukes"
```

---

### Task 2: Laplace의 "버스트 3단계 진입" 버프를 자기 버스트 게이팅으로 정정

**Files:**
- Modify: `backend/app/skill_rules/laplace_ultimate_hero.py` (docstring + `build_laplace_ultimate_hero_rules`)
- Modify: `backend/tests/test_skill_rules_laplace_ultimate_hero.py` (`test_full_burst_self_attack_damage`)

**Interfaces:**
- Consumes: Task 1이 고정한 사실 — `full_burst_enter`와 `own_burst_activate`는 B3 유닛의 자기 버스트 넉에 대해 **수치적으로 동등**하다.
- Produces: `build_laplace_ultimate_hero_rules(values, caster_max_hp)` 시그니처는 **변경 없음**. 반환 룰 목록에서 Over Energy 버프의 트리거만 `own_burst_activate`로 바뀐다.

**근거:** Fienn 실측(2026-07-24) — 스킬텍스트 `[버스트 3단계 진입 시]`는 'B2 발동 이후, B3 발동 이전' 상태를 뜻하며, 결과적으로 52.14% 공격대미지가 **그녀 자신의 B3 버스트딜에 적용**된다. `full_burst_enter`는 그녀가 버스트하지 않은 사이클(다른 B3가 대신 버스트)에도 발동해 버프를 주므로 과대적용이다. `own_burst_activate`는 자기 버스트에만 발동하고 넉 기록 전에 발동하므로 두 요건을 모두 만족한다.

- [ ] **Step 1: 실패하는 테스트로 바꾼다**

`backend/tests/test_skill_rules_laplace_ultimate_hero.py`에서 `test_full_burst_self_attack_damage`를 아래로 **교체**한다:

```python
def test_burst_stage3_entry_self_attack_damage_fires_on_her_own_burst():
    """스킬텍스트의 [버스트 3단계 진입 시]는 그녀 자신이 B3를 쏘는 순간이다
    (Fienn 실측 2026-07-24). full_burst_enter가 아니라 own_burst_activate라야
    다른 B3가 대신 버스트한 사이클에 잘못 지급되지 않는다."""
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    assert round(registry.total_for("attack_damage_up", LAPLACE, now=5.0), 4) == 0.5214
    assert registry.total_for("attack_damage_up", LAPLACE, now=15.1) == 0.0  # 10 sec window
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0  # self-only


def test_full_burst_enter_alone_does_not_grant_attack_damage():
    """그녀가 버스트하지 않은 사이클엔 지급되지 않아야 한다."""
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    assert registry.total_for("attack_damage_up", LAPLACE, now=5.0) == 0.0
```

- [ ] **Step 2: 테스트를 실행해 실패를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_laplace_ultimate_hero.py -v
```

Expected: `test_burst_stage3_entry_self_attack_damage_fires_on_her_own_burst`가 FAIL (0.0 != 0.5214), `test_full_burst_enter_alone_does_not_grant_attack_damage`도 FAIL (0.5214 != 0.0).

- [ ] **Step 3: 룰의 트리거를 교체한다**

`backend/app/skill_rules/laplace_ultimate_hero.py`의 `build_laplace_ultimate_hero_rules` 반환부에서 `full_burst_enter` 줄을 `own_burst_activate`로 바꾼다. 교체 후 반환부는 다음과 같다:

```python
    return [
        buff_rule("battle_start", [("flat_atk", battle_start_atk_flat, "self", None)]),
        # 스킬텍스트의 [버스트 3단계 진입 시] = 그녀 자신이 B3를 쏘는 순간
        # (Fienn 실측 2026-07-24). own_burst_activate는 넉이 기록되기 전에 발동해
        # 이 버프가 그녀의 버스트딜에 곱해지고, 그녀가 버스트하지 않은 사이클엔
        # 지급되지 않는다 (full_burst_enter는 후자를 못 막는다).
        buff_rule("own_burst_activate", [("attack_damage_up", fb_attack_damage, "self", fb_attack_damage_dur)]),
        buff_rule("own_burst_activate", [("atk_percent", burst_atk, "self", burst_atk_dur)]),
    ]
```

- [ ] **Step 4: docstring을 갱신한다**

같은 파일 docstring의 "Modeled (DPS-relevant)" 항목에서 아래 줄을

```
- Over Energy (skills[1]), on entering Full Burst (Burst Stage 3): self Attack
  Damage +52.14% for 10 sec.
```

다음으로 교체한다:

```
- Over Energy (skills[1]), on her OWN Burst-3 activation ("[Burst Stage 3
  entry]" = after B2 fires, before B3 fires - Fienn's in-game reading,
  2026-07-24): self Attack Damage +52.14% for 10 sec. Encoded on
  own_burst_activate, not full_burst_enter: the two are numerically
  identical for a B3 unit's own nuke (same timestamp, inclusive buff
  window - see tests/test_burst_cycle_buff_timing.py), but
  full_burst_enter would also pay out on cycles where a DIFFERENT B3 unit
  bursts instead of her.
```

- [ ] **Step 5: 테스트를 실행해 통과를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_laplace_ultimate_hero.py -v
```

Expected: 전부 PASS.

- [ ] **Step 6: 전체 스위트로 회귀가 없는지 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```

Expected: 전부 PASS. **딜 수치를 검증하는 기존 E2E 테스트가 깨지면 안 된다** — 깨졌다면 그 유닛이 Laplace를 포함한 덱이고 수치가 실제로 변한 것이므로, 원인을 확인하고 보고할 것(예상치 못한 결과).

- [ ] **Step 7: 커밋**

```bash
git add backend/app/skill_rules/laplace_ultimate_hero.py backend/tests/test_skill_rules_laplace_ultimate_hero.py
git commit -m "Laplace: gate Over Energy's Attack Damage on her own burst, not any Full Burst"
```

---

### Task 3: 버스트 사이클 타이밍을 docs/insights.md에 문서화

**Files:**
- Modify: `docs/insights.md` (기존 `## Burst rotation` 섹션 바로 위에 신규 `##` 섹션 추가)

**Interfaces:**
- Consumes: Task 1의 테스트가 확정한 사실. **Task 1에서 기대값을 고쳤다면 그 실제 결과를 여기 반영한다.**
- Produces: 없음(문서).

- [ ] **Step 1: 문서 섹션을 추가한다**

`docs/insights.md`에서 `## Burst rotation` 줄을 찾아, **그 바로 위에** 아래 섹션을 삽입한다:

```markdown
## 버스트 사이클에는 "N단계 진입"이라는 별도 이벤트가 없다 — `[버스트 N단계 진입 시]`는 그 티어 유닛의 `own_burst_activate`다

Fienn의 정본 로테이션은 `게이지 충전 → 1단계 진입 → B1 사용 → 2단계 진입 →
B2 사용 → 3단계 진입 → B3 사용 → 풀버스트 10초`지만, 엔진(`burst_cycle.py`)은
"진입"과 "사용"을 하나로 접는다 — `on_tier_fire(tier, slug, time)`이 곧 "BN
사용"이고, 그 뒤 `on_full_burst_enter(tier3_fire_time)`이 호출된다. 즉
**`full_burst_enter` 시각 == tier-3 발동 시각 == B3 버스트 넉 시각**이다.

버프가 넉에 닿는지는 두 가지가 결정한다:
1. `effects.py`의 active-window는 **시작 포함**(`applied_at <= now < applied_at
   + duration`).
2. `raid_simulator`는 record-then-compute라, 넉 데미지는 2단계에서 **넉 시각
   기준 라이브 버프**를 읽는다 — 워크 도중의 등록 *순서*는 무관하고 오직
   버프 시작 시각 vs 넉 시각만 중요하다.

따라서 (`tests/test_burst_cycle_buff_timing.py`가 고정한 결과):
- **B3 유닛의 자기 버스트 넉**: `full_burst_enter` 버프도 `own_burst_activate`
  버프도 **둘 다 닿는다**(동시각 + 시작 포함). 수치적으로 동등.
- **B1/B2 유닛의 자기 버스트 넉**: `auto` 모드는 티어 간 gap이 0이라 동시각 →
  `full_burst_enter` 버프가 닿지만, **`manual` 모드는 티어 간 0.1초 간격이라
  B1 넉이 `full_burst_enter`보다 0.2초 먼저 발생 → 못 닿는다.**

**인코딩 규칙:** 스킬텍스트가 `[버스트 N단계 진입 시]`라고 말하면
`full_burst_enter`가 아니라 **그 유닛의 `own_burst_activate`로 인코딩하라.**
이유는 두 가지다 — (a) B1/B2에서는 manual 모드에서 자기 버스트딜을 놓치고,
(b) 어느 티어든 `full_burst_enter`는 **그 유닛이 버스트하지 않은 사이클에도**
발동해 버프를 과대 지급한다(같은 티어의 다른 유닛이 대신 버스트한 경우).
`full_burst_enter`는 진짜로 "풀버스트 창 진입"이 조건인 효과에만 쓴다.
첫 정정 사례: `laplace_ultimate_hero`의 Over Energy 52.14% (2026-07-24).
```

- [ ] **Step 2: 문서가 Task 1의 실제 테스트 결과와 일치하는지 대조한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_burst_cycle_buff_timing.py -v
```

Expected: 4건 PASS. 각 테스트 이름이 위 문서의 4개 결론과 1:1로 대응하는지 눈으로 확인한다. 어긋나면 **문서를 실제 결과에 맞춘다.**

- [ ] **Step 3: 커밋**

```bash
git add docs/insights.md
git commit -m "Document burst-cycle buff timing and the [Burst Stage N entry] encoding rule"
```

---

### Task 4: 같은 오트리거 패턴 스윕 (보고 전용)

`full_burst_enter`로 인코딩됐지만 실제로는 `own_burst_activate`여야 하는 다른 유닛을 찾아 **목록화만** 한다. 이번 Phase에서 수정하지 않는다(각 건이 스킬 원문 확인을 요구하고, 수정은 딜 수치를 바꾸므로 별도 승인이 필요).

**Files:**
- Modify: `docs/insights.md` (Task 3에서 추가한 섹션 끝에 후보 목록 추가)

**Interfaces:**
- Consumes: Task 3의 인코딩 규칙.
- Produces: 없음(문서).

- [ ] **Step 1: 후보를 기계적으로 좁힌다**

**self 스코프 버프만** 추린다(스쿼드 버프는 이 규칙의 대상이 아니다 —
아군 전체에 주는 버프는 "풀버스트 창" 조건이 자연스럽다):

```bash
cd backend && grep -rn "full_burst_enter" app/skill_rules/*.py | grep '"self"'
```

- [ ] **Step 2: 추려진 각 모듈의 docstring을 읽고 판정한다**

Step 1의 결과에 나온 모듈마다 해당 파일 docstring의 그 효과 설명을 읽고, 원문이
"**[버스트 N단계 진입 시]** / on entering Burst Stage N"인지 "**풀버스트 진입 시** /
on entering Full Burst"인지 구분한다.
- 전자 → 후보(수정 필요, 목록에 올린다)
- 후자 → 정상(그대로 둔다)

원문이 docstring에 없으면 판정하지 말고 "원문 확인 필요"로 분류한다. **추측하지
않는다**(CLAUDE.md: 기술적 세부를 지어내지 않는다).

- [ ] **Step 3: 결과를 문서에 기록한다**

Task 3에서 추가한 섹션의 맨 끝에 아래 형식으로 덧붙인다. `<...>`는 Step 2에서
실제로 확인한 내용으로 채운다(빈 목록이면 "후보 없음"이라고 명시).

```markdown
**스윕 결과 (2026-07-24, self 스코프 `full_burst_enter` 전수):**
- 수정 후보(원문이 `[버스트 N단계 진입 시]`): <슬러그 목록 또는 "없음">
- 원문 확인 필요(docstring에 원문 근거 없음): <슬러그 목록 또는 "없음">
- 정상(진짜 풀버스트 창 조건): <건수>건
수정은 딜 수치를 바꾸므로 별도 승인 후 진행한다.
```

- [ ] **Step 4: 커밋**

```bash
git add docs/insights.md
git commit -m "Record full_burst_enter mis-trigger sweep results"
```

---

## Phase A 완료 기준

- [ ] `tests/test_burst_cycle_buff_timing.py` 4건 그린
- [ ] Laplace 트리거 정정 + 그 테스트 그린
- [ ] `docs/insights.md`에 타이밍 규칙 + 스윕 결과 기록
- [ ] `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q` 전체 그린
- [ ] Fienn에게 보고: 감사 결론(특히 52.14%가 원래 적용되고 있었는지 여부)과 스윕 후보 목록

이후 Phase B(라이브 Max HP) 계획을 별도로 작성한다.
