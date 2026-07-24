# Phase B: 라이브 Max HP 스탯 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "ATK ▲ 캐스터 Max HP의 X%" 버프가 정적 캐릭터정보 Max HP 대신 **트리거 시점의 라이브 Max HP**(base + 활성 `flat_max_hp` 버프)를 읽게 한다.

**Architecture:** 딜 계산 핫패스(`_stat_bundle` / `total_for`의 세그먼트 테이블)는 **건드리지 않는다.** 변환은 룰이 발동하는 순간(트리거당 1회, 드묾) 한 번의 `total_for("flat_max_hp", ...)` 조회로 해결한다. 새 헬퍼 `max_hp_scaled_atk_rule` 하나를 만들고 소비자들을 거기로 옮긴다.

**Tech Stack:** Python 3, pytest, 기존 `app.effects.Effect` / `EffectRegistry` / `app.skill_rules._helpers`.

## Global Constraints

- 워크트리 `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\skill-encoding`, 브랜치 `wip/skill-encoding`. 백엔드 명령은 `backend/`에서.
- 테스트: `PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest ...` (시스템 `python`엔 pytest가 없다).
- **핫패스 금지:** `_stat_bundle`, `total_for`, `_build_segment_table`을 수정하지 않는다. 덱 최적화 비용을 늘리지 않는 것이 Fienn의 명시 제약이다.
- **알려진 한계(문서화 필수):** 변환은 **적용 시점 스냅샷**이다. ATK 버프가 걸린 *뒤에* 도착한 Max HP 버프는 그 ATK 버프를 소급해 키우지 않는다. 계속 자라야 하는 케이스(Laplace의 Over Energy 단계)는 Max HP가 바뀌는 시점마다 ATK 버프를 **재적용**해서 해결한다(Phase C).
- 기존 `flat_max_hp` 부여자는 `rouge`(squad) 하나뿐이므로, 이 변경의 실제 수치 영향은 **Rouge가 포함된 덱**(및 Phase B에서 Maxwell의 Max HP 버프를 켠 뒤의 Maxwell 덱)에 한정된다. 그 외 덱은 값이 변하면 안 된다.
- 룰 안에서 캐스터 타겟 dict를 만드는 established 패턴:
  `by_slug = {m.slug: m for m in context.members}` → `{"slug": caster_slug, "element": by_slug[caster_slug].element}` (`squad_engine.py:184-187` 선례).

---

### Task 1: `max_hp_scaled_atk_rule` 헬퍼

**Files:**
- Modify: `backend/app/skill_rules/_helpers.py` (`escalating_buff_rule` 아래에 추가)
- Test: `backend/tests/test_max_hp_scaled_atk_rule.py` (신규)

**Interfaces:**
- Produces: `max_hp_scaled_atk_rule(trigger, percent, scope, duration, base_max_hp, condition=None, refreshing=False) -> SkillRule`
  - `percent`: 소수 비율(예: 4.05% → `0.0405`).
  - `base_max_hp`: 캐스터의 캐릭터정보 Max HP(`values["caster_max_hp"]`).
  - 발동 시 `flat_atk` Effect를 `scope`/`duration`으로 등록. 값 = `(base_max_hp + 활성 flat_max_hp) * percent`.

- [ ] **Step 1: 실패하는 테스트를 작성한다**

`backend/tests/test_max_hp_scaled_atk_rule.py`:

```python
from app.effects import Effect, EffectRegistry
from app.skill_rules._helpers import max_hp_scaled_atk_rule
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CASTER = {"slug": "caster", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("caster", burst_tier=3, element="Wind", weapon="RL"),
        SquadMember("ally", burst_tier=1, element="Fire", weapon="AR"),
    ])


def test_uses_base_max_hp_when_no_max_hp_buffs_are_active():
    ctx = make_context()
    registry = EffectRegistry()
    rule = max_hp_scaled_atk_rule("battle_start", 0.0405, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    # 800000 * 4.05% = 32400
    assert round(registry.total_for("flat_atk", CASTER, now=0.0), 2) == 32400.0


def test_live_max_hp_buffs_raise_the_converted_atk():
    ctx = make_context()
    registry = EffectRegistry()
    # 먼저 캐스터에게 Max HP +200000을 건다.
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "caster"), applied_at=0.0)
    rule = max_hp_scaled_atk_rule("battle_start", 0.0405, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    # (800000 + 200000) * 4.05% = 40500
    assert round(registry.total_for("flat_atk", CASTER, now=0.0), 2) == 40500.0


def test_squad_scope_pays_allies_using_the_CASTER_s_max_hp():
    ctx = make_context()
    registry = EffectRegistry()
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "caster"), applied_at=0.0)
    rule = max_hp_scaled_atk_rule("own_burst_activate", 0.01, "squad", 15.0, base_max_hp=800_000.0)
    fire_trigger("own_burst_activate", {"caster": [rule]}, ctx, registry, time=5.0)
    # 아군도 캐스터의 라이브 Max HP 기준 1% = 10000을 받는다
    assert round(registry.total_for("flat_atk", ALLY, now=5.0), 2) == 10000.0
    assert registry.total_for("flat_atk", ALLY, now=20.1) == 0.0  # 15초 창


def test_a_max_hp_buff_landing_AFTER_application_does_not_retroactively_grow_it():
    """알려진 한계를 명시적으로 고정한다 - 스냅샷 의미론."""
    ctx = make_context()
    registry = EffectRegistry()
    rule = max_hp_scaled_atk_rule("battle_start", 0.0405, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "caster"), applied_at=1.0)
    assert round(registry.total_for("flat_atk", CASTER, now=5.0), 2) == 32400.0
```

- [ ] **Step 2: 실패를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/test_max_hp_scaled_atk_rule.py -v
```
Expected: FAIL — `ImportError: cannot import name 'max_hp_scaled_atk_rule'`.

- [ ] **Step 3: 헬퍼를 구현한다**

`backend/app/skill_rules/_helpers.py` 파일 끝에 추가:

```python
def max_hp_scaled_atk_rule(
    trigger, percent, scope, duration, base_max_hp, condition=None, refreshing=False
):
    """"ATK ▲ 캐스터 Max HP의 X%"를 캐스터의 LIVE Max HP로 환산해 flat_atk를 건다.

    라이브 = 캐릭터정보 Max HP(`base_max_hp`) + 발동 시점에 활성인 `flat_max_hp`
    버프 총합. 정적 `caster_max_hp`만 쓰던 기존 인코딩은 아군/자기 Max HP 버프를
    통째로 무시했다 (Rouge의 Game Master가 유일한 부여자였고 소비자가 없어
    죽은 스탯이었다).

    의미론은 스냅샷이다 - 값은 이 룰이 발동하는 순간 고정된다. 발동 이후 도착한
    Max HP 버프는 이미 걸린 flat_atk를 소급해 키우지 않으므로, 전투 중 Max HP가
    계속 자라는 유닛은 Max HP가 바뀌는 시점마다 이 룰을 다시 발동시켜야 한다
    (Laplace의 Over Energy 단계). 딜 계산 핫패스를 건드리지 않으려는 의도적
    트레이드오프다 - 변환은 트리거당 한 번만 일어난다.

    `percent`는 소수 비율(4.05% -> 0.0405)."""

    def action(context, caster_slug, time, registry):
        by_slug = {m.slug: m for m in context.members}
        target = {"slug": caster_slug, "element": by_slug[caster_slug].element}
        live_max_hp = base_max_hp + registry.total_for("flat_max_hp", target, time)
        effect = Effect("flat_atk", live_max_hp * percent, scope, duration, caster_slug)
        if refreshing:
            registry.add_refreshing(effect, applied_at=time)
        else:
            registry.add(effect, applied_at=time)

    return _rule(trigger, action, condition)
```

- [ ] **Step 4: 통과를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/test_max_hp_scaled_atk_rule.py -v
```
Expected: 4건 PASS.

- [ ] **Step 5: 전체 스위트 확인 후 커밋**

```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/ -q
```
Expected: 전부 PASS (헬퍼는 아직 아무도 안 쓰므로 회귀 0).

```bash
git add backend/app/skill_rules/_helpers.py backend/tests/test_max_hp_scaled_atk_rule.py
git commit -m "Add max_hp_scaled_atk_rule: convert Max HP to ATK using live Max HP"
```

---

### Task 2: Laplace의 Electric Power를 라이브 Max HP로 이관

**Files:**
- Modify: `backend/app/skill_rules/laplace_ultimate_hero.py`
- Modify: `backend/tests/test_skill_rules_laplace_ultimate_hero.py`

**Interfaces:**
- Consumes: Task 1의 `max_hp_scaled_atk_rule`.
- Produces: `build_laplace_ultimate_hero_rules(values, caster_max_hp)` 시그니처 불변.

- [ ] **Step 1: 라이브 반영을 요구하는 테스트를 추가한다**

`backend/tests/test_skill_rules_laplace_ultimate_hero.py` 끝에 추가:

```python
def test_battle_start_atk_uses_live_max_hp_when_a_max_hp_buff_is_active():
    from app.effects import Effect

    ctx = make_context()
    registry = EffectRegistry()
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "laplace-ultimate-hero"), applied_at=0.0)
    fire_trigger("battle_start", {"laplace-ultimate-hero": rules()}, ctx, registry, time=0.0)
    # (800000 + 200000) * 4.05% = 40500 (정적이면 32400에 머문다)
    assert round(registry.total_for("flat_atk", LAPLACE, now=0.0), 2) == 40500.0
```

- [ ] **Step 2: 실패를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/test_skill_rules_laplace_ultimate_hero.py -v
```
Expected: 새 테스트가 FAIL (32400.0 != 40500.0).

- [ ] **Step 3: 룰을 이관한다**

`laplace_ultimate_hero.py`의 import를 바꾼다:

```python
from app.skill_rules._helpers import buff_rule, max_hp_scaled_atk_rule
```

`build_laplace_ultimate_hero_rules`에서 `battle_start_atk_flat` 계산 줄을 지우고
(그 줄: `battle_start_atk_flat = caster_max_hp * float(s1["description_value_01"]) / 100`)
대신 비율만 뽑는다:

```python
    battle_start_atk_pct = float(s1["description_value_01"]) / 100  # Max HP의 4.05%
```

반환부 첫 줄을 교체한다:

```python
        max_hp_scaled_atk_rule("battle_start", battle_start_atk_pct, "self", None, caster_max_hp),
```

- [ ] **Step 4: docstring을 갱신한다**

docstring의 아래 줄을

```
- Electric Power, Full Full Charge (skills[0]), at battle start: self ATK +
  (4.05% of her final Max HP) continuously (self flat_atk, caster-Max-HP-scaled).
```

다음으로 교체한다:

```
- Electric Power, Full Full Charge (skills[0]), at battle start: self ATK +
  (4.05% of her LIVE Max HP) continuously - resolved through
  max_hp_scaled_atk_rule, so ally/self Max HP buffs feed it. Snapshot at
  battle start: her own Over Energy stages raise Max HP later in the fight
  and must re-apply this buff to be reflected (see the deferred list).
```

- [ ] **Step 5: 통과 + 회귀를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/ -q
```
Expected: 전부 PASS. Laplace 덱에 `flat_max_hp` 부여자가 없으면 수치는 그대로여야 한다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/skill_rules/laplace_ultimate_hero.py backend/tests/test_skill_rules_laplace_ultimate_hero.py
git commit -m "Laplace: Electric Power reads live Max HP"
```

---

### Task 3: Maxwell — 라이브 Max HP 이관 + Sequential Limit Release의 Max HP 버프 인코딩

Maxwell은 자기 Max HP를 **올리는** 스킬과 그 Max HP를 **ATK로 환산하는** 스킬을 동시에 가진 첫 유닛이라, Phase B의 실효성을 증명하는 케이스다.

**Files:**
- Modify: `backend/app/skill_rules/maxwell_ordinary_mechanic.py`
- Modify: `backend/tests/test_skill_rules_maxwell_ordinary_mechanic.py`

**Interfaces:**
- Consumes: Task 1의 `max_hp_scaled_atk_rule`.
- Produces: `build_maxwell_ordinary_mechanic_rules(values, caster_max_hp)` 시그니처 불변.

**모델링 판단:** Sequential Limit Release의 "풀차지마다 Max HP +1%(그녀 Max HP 기준), 최대 30스택"은 트리거가 풀차지 카운트(엔진 미지원)다. SR은 매 발사가 풀차지이므로 30스택은 전투 초반에 도달해 이후 유지된다 → **정착 캡(+30%)을 battle_start에 부여**하고 그 가정을 docstring에 명시한다(red-hood의 Glaring Eyes 10스택 정착 선례와 동형).

- [ ] **Step 1: 실패하는 테스트를 추가한다**

`backend/tests/test_skill_rules_maxwell_ordinary_mechanic.py` 끝에 추가
(`MAXWELL`/`ALLY`/`CASTER_MAX_HP`/`rules()`/`make_context()`는 그 파일의 기존
헬퍼를 그대로 쓴다 — 이름이 다르면 파일에 정의된 실제 이름으로 맞춘다):

```python
def test_sequential_limit_release_grants_settled_max_hp_at_battle_start():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=0.0)
    # 그녀 Max HP의 1% x 30스택 = 30%
    assert round(registry.total_for("flat_max_hp", MAXWELL, now=0.0), 2) == round(CASTER_MAX_HP * 0.30, 2)


def test_squad_atk_uses_her_live_max_hp_including_her_own_max_hp_stacks():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=0.0)
    fire_trigger("own_burst_activate", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=5.0)
    # squad ATK = 라이브 Max HP(=1.30 x base)의 1%
    expected = CASTER_MAX_HP * 1.30 * 0.01
    assert round(registry.total_for("flat_atk", ALLY, now=5.0), 2) == round(expected, 2)
```

- [ ] **Step 2: 실패를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/test_skill_rules_maxwell_ordinary_mechanic.py -v
```
Expected: 두 테스트 FAIL.

- [ ] **Step 3: 룰을 구현한다**

`maxwell_ordinary_mechanic.py`의 import:

```python
from app.skill_rules._helpers import buff_rule, escalating_buff_rule, max_hp_scaled_atk_rule
```

`build_maxwell_ordinary_mechanic_rules` 안에서 `squad_atk_flat` 계산 줄을
(`squad_atk_flat = caster_max_hp * float(s2["description_value_01"]) / 100`)
아래로 바꾸고, Sequential Limit Release의 Max HP 슬롯을 읽는다.
**슬롯 번호는 추측하지 말고** `SKILL_VALUE_MANIFESTS`가 가리키는 실제 픽스처
(`backend/tests/test_skill_rules_maxwell_ordinary_mechanic.py`의 `SEQUENTIAL_LIMIT_RELEASE`)
에서 "Max HP % per stack"과 "stack cap"에 해당하는 키를 확인해 쓴다.

```python
    squad_atk_pct = float(s2["description_value_01"]) / 100      # 그녀 Max HP의 1%
    max_hp_per_stack = float(s1["<확인한 키>"]) / 100             # 스택당 Max HP 1%
    max_hp_stack_cap = int(float(s1["<확인한 키>"]))              # 30스택
```

반환 리스트에서 `own_burst_activate`의 `("flat_atk", squad_atk_flat, "squad", squad_atk_dur)` 항목을 **제거**하고, 대신 리스트에 다음 두 룰을 추가한다:

```python
        # 풀차지마다 Max HP +1%, 캡 30 - SR은 매 발사가 풀차지라 초반에 캡에
        # 도달해 유지되므로 정착 캡을 battle_start에 부여한다(근사, 아래 docstring).
        buff_rule("battle_start", [
            ("flat_max_hp", caster_max_hp * max_hp_per_stack * max_hp_stack_cap, "self", None),
        ]),
        # squad ATK = 그녀의 LIVE Max HP의 1% (위 스택을 포함해 읽는다)
        max_hp_scaled_atk_rule("own_burst_activate", squad_atk_pct, "squad", squad_atk_dur, caster_max_hp),
```

- [ ] **Step 4: docstring을 갱신한다**

"Not modeled / deferred"의 첫 항목(Sequential Limit Release의 Max HP +1% 관련
"Skipped." 로 끝나는 항목)을 **삭제**하고, "Modeled (DPS-relevant)"에 다음을 추가한다:

```
- Sequential Limit Release (skills[0]) Max HP: +1% of her Max HP per Full
  Charge, capped at 30 stacks. The full-charge-count trigger does not exist,
  but her SR fires a full charge every shot, so the cap is reached early and
  held - modeled as the settled +30% granted at battle start (same settling
  approximation as red-hood's Glaring Eyes). It is no longer inert: it feeds
  Output Switching Sequence's squad ATK below through the live-Max-HP path.
- Output Switching Sequence (skills[1]) squad ATK: 1% of her LIVE Max HP
  (base + the Max HP stacks above) for 15 sec, via max_hp_scaled_atk_rule.
```

- [ ] **Step 5: 통과 + 회귀를 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/ -q
```
Expected: 전부 PASS. **Maxwell이 포함된 E2E 딜 테스트가 있으면 값이 30% 오른 squad ATK만큼 올라가는 게 정상** — 깨지면 기대값을 새 모델에 맞게 갱신하고, 변화 폭을 커밋 메시지에 적는다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/skill_rules/maxwell_ordinary_mechanic.py backend/tests/test_skill_rules_maxwell_ordinary_mechanic.py
git commit -m "Maxwell: encode Sequential Limit Release Max HP stacks and feed them into her squad ATK"
```

---

### Task 4: 나머지 소비자 이관 (cinderella, maiden_ice_rose)

**Files:**
- Modify: `backend/app/skill_rules/cinderella.py`
- Modify: `backend/app/skill_rules/maiden_ice_rose.py`
- Modify: 각 유닛의 테스트 파일(기대값이 정적 Max HP를 하드코딩하고 있으면 그대로 둔다 — `flat_max_hp` 버프가 없으면 값이 동일해야 하므로 원칙적으로 수정 불필요)

**Interfaces:**
- Consumes: Task 1의 `max_hp_scaled_atk_rule`.

**범위 밖(이관하지 않음):** `rouge.py`(Max HP를 *부여*할 뿐 ATK로 환산하지 않는다), `crown.py`(실드 — 딜 무관), `maiden_ice_rose`의 `extra_flat_atk_percent_of_max_hp`(넉 전용 좁은 경로로 `raid_simulator`가 `base_stats`에서 직접 읽는다 — 핫패스 근처라 이번 Phase에서 손대지 않고 docstring에 한계로 남긴다).

- [ ] **Step 1: cinderella의 Flawless Glass를 이관한다**

`cinderella.py`의 `build_flawless_glass_rules`를 아래로 바꾼다:

```python
def build_flawless_glass_rules(values, caster_max_hp):
    fg = values
    atk_pct_of_max_hp = float(fg["description_value_01"]) / 100
    duration = float(fg["description_value_02"])
    return [max_hp_scaled_atk_rule("own_burst_activate", atk_pct_of_max_hp, "self", duration, caster_max_hp)]
```

import 줄에 `max_hp_scaled_atk_rule`을 추가한다. **주의:** 위 코드의
`description_value_02`(duration)는 기존 구현이 읽던 슬롯을 그대로 유지한 것이다 —
바꾸기 전에 파일의 실제 기존 줄을 읽고 같은 슬롯을 쓰는지 확인할 것.

- [ ] **Step 2: cinderella docstring의 죽은-스탯 서술을 갱신한다**

docstring에서 "the engine has no live max_hp stat consumer (base_stats' max_hp is
a fixed input, never read back from the registry)"라고 적힌 문장을 찾아, 아래로 바꾼다:

```
  Max HP는 더 이상 죽은 스탯이 아니다 - `max_hp_scaled_atk_rule`이 적용 시점에
  라이브 Max HP(base + flat_max_hp 버프)를 읽는다(Phase B, 2026-07-24). Beautiful
  자신의 "Max HP +1.6% per stack"은 여전히 미부여 상태로 남아 있다(스택 COUNT만
  쓰인다) - 부여하려면 별도 인코딩이 필요하다.
```

- [ ] **Step 3: maiden_ice_rose의 self ATK 환산을 이관한다**

`maiden_ice_rose.py`의 `build_blessings_upon_you_rules` 안에서
`self_atk_from_max_hp = caster_max_hp * float(blessings["description_value_07"]) / 100`
로 계산해 `Effect("flat_atk", self_atk_from_max_hp, "self", self_atk_duration, caster_slug)`를
등록하는 부분을, 같은 트리거의 `max_hp_scaled_atk_rule`로 교체한다. 그 함수가 커스텀
액션 안에서 여러 효과를 한꺼번에 등록하고 있다면, **flat_atk 항목만** 빼내
별도 룰로 반환 리스트에 추가하고 나머지는 그대로 둔다.

- [ ] **Step 4: 전체 스위트로 확인한다**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/ -q
```
Expected: 전부 PASS. 이 두 유닛의 덱에 `flat_max_hp` 부여자(rouge/maxwell)가 없으면 **수치가 변하면 안 된다** — 변했다면 슬롯을 잘못 읽은 것이니 되돌아가 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/skill_rules/cinderella.py backend/app/skill_rules/maiden_ice_rose.py
git commit -m "Migrate Cinderella/Maiden Max-HP-scaled ATK to the live Max HP path"
```

---

### Task 5: 크로스유닛 회귀 검증 + 문서화

**Files:**
- Modify: `docs/insights.md` (Effects / stats 섹션)
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md` (Max HP 항목)

- [ ] **Step 1: Rouge + 소비자가 같은 덱에 있을 때 값이 실제로 움직이는지 E2E로 확인한다**

`backend/tests/test_max_hp_scaled_atk_rule.py`에 통합 테스트를 추가한다.
Rouge가 squad `flat_max_hp`를 걸고, 같은 덱의 Max-HP-스케일 소비자의 flat_atk가
그만큼 커지는지 본다 — 유닛 룰을 직접 조립하는 대신 헬퍼 두 개로 최소 재현한다:

```python
def test_an_allys_squad_max_hp_buff_raises_a_consumers_converted_atk():
    ctx = make_context()
    registry = EffectRegistry()
    # 아군이 스쿼드 전체에 Max HP를 건다 (Rouge의 Game Master 형태)
    registry.add(Effect("flat_max_hp", 100_000.0, "squad", None, "ally"), applied_at=0.0)
    rule = max_hp_scaled_atk_rule("battle_start", 0.01, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    # (800000 + 100000) * 1% = 9000
    assert round(registry.total_for("flat_atk", CASTER, now=0.0), 2) == 9000.0
```

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/test_max_hp_scaled_atk_rule.py -v
```
Expected: PASS. 이것이 "Rouge가 미리 심어둔 Max HP 버프가 드디어 딜을 움직인다"는 증거다.

- [ ] **Step 2: `docs/insights.md`의 `## Effects / stats` 섹션에 항목을 추가한다**

```markdown
- **Max HP는 2026-07-24부터 살아있는 딜 스탯이다 — 단 "적용 시점 스냅샷"이다.** `flat_max_hp`는 오래 부여만 되고(rouge의 Game Master) 아무도 소비하지 않는 죽은 스탯이었고, "ATK ▲ 캐스터 Max HP의 X%" 버프들은 전부 정적 캐릭터정보 Max HP를 빌드 시점에 곱하고 있었다. `_helpers.max_hp_scaled_atk_rule`이 이 환산을 **룰 발동 시점**으로 옮겨 `base_max_hp + total_for("flat_max_hp", caster, time)`을 읽는다. 딜 계산 핫패스(`_stat_bundle`/`total_for`의 세그먼트 테이블)는 의도적으로 건드리지 않았다 — 덱 최적화 비용을 늘리지 않는 것이 제약이었고, 환산은 트리거당 한 번이면 충분하기 때문이다. **대가는 스냅샷 의미론**: ATK 버프가 걸린 뒤 도착한 Max HP 버프는 그것을 소급해 키우지 않으므로, 전투 중 Max HP가 자라는 유닛은 Max HP가 바뀌는 시점마다 ATK 룰을 재발동시켜야 한다. 소비자: `laplace_ultimate_hero`, `maxwell_ordinary_mechanic`(자기 Max HP 스택을 자기 squad ATK로 먹이는 첫 유닛), `cinderella`, `maiden_ice_rose`.
```

- [ ] **Step 3: 스킬 카탈로그를 갱신한다**

`.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`에서 Max HP가
"inert / 딜 무관"으로 분류된 서술을 찾아, 위 내용을 요약해 갱신한다(정적이 아니라
라이브이며, 스냅샷 한계가 있고, 헬퍼 이름이 `max_hp_scaled_atk_rule`이라는 점).
해당 서술이 없으면 스탯 카탈로그의 적절한 위치에 새 줄로 추가한다.

- [ ] **Step 4: 전체 스위트 + 커밋**

```bash
cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest tests/ -q
```

```bash
git add docs/insights.md .claude/skills/nikke-skill-encoding/references/engine-capabilities.md backend/tests/test_max_hp_scaled_atk_rule.py
git commit -m "Document the live Max HP path and its snapshot limitation"
```

---

## Phase B 완료 기준

- [ ] `max_hp_scaled_atk_rule` + 테스트 그린
- [ ] Laplace / Maxwell / Cinderella / Maiden 이관 완료
- [ ] Maxwell의 Max HP 스택이 실제로 그녀의 squad ATK를 키우는 것을 테스트가 증명
- [ ] 아군 squad Max HP 버프가 소비자의 ATK를 키우는 것을 테스트가 증명
- [ ] `docs/insights.md` + `engine-capabilities.md` 갱신
- [ ] 전체 스위트 그린, 수치 변화는 Rouge/Maxwell 관련 덱에 한정됨을 확인
- [ ] Fienn 보고: 어떤 유닛의 수치가 얼마나 움직였는지

이후 Phase C(Laplace 변신 루프) 계획을 별도로 작성한다.
