# 소장품 차지대미지 배율을 무기변형 세그먼트로 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RL·SR 소장품의 차지대미지 배율이, 프로파일을 스킬 슬롯에서 만드는 무기변형 세그먼트(maxwell · red-hood)에도 닿게 한다.

**Architecture:** `roster.assemble_simulation_inputs`가 이미 유닛마다 값 딕셔너리를 조립하고 있고, `collectible_modifiers`를 호출해 무기 배율을 버리고 있다. 그 배율을 스칼라 하나로 값에 실어 보내고, 스킬 유래 프로파일을 가진 두 빌더가 곱한다. 나머지 빌더는 곱할 대상이 없거나 이미 `weapon_stats` 경유로 받고 있으므로 건드리지 않는다.

**Tech Stack:** Python 3.13, pytest, 기존 `weapon_mode_schedules` 세그먼트 배관

## Global Constraints

- 새 키 이름은 **`caster_charge_damage_multiplier`**, 읽을 때는 항상 `values.get("caster_charge_damage_multiplier", 1.0)`. 기본값 1.0이 있어야 기존 테스트 픽스처(키 없음)가 안 깨진다.
- **red-hood는 `full_charge_percent`에만 곱한다.** `converted * 100`은 Glaring의 차지속도→차지대미지 변환이라 무기의 기본 스탯이 아니다. 이 분해는 `snow_white_heavy_arms`가 이미 하는 것과 같은 모양이며, 맥스웰 판독이 가르지 못한 부분이므로 스펙에 미해결로 적혀 있다.
- **`snow_white_heavy_arms`는 건드리지 않는다.** 그녀 프로파일은 `weapon["charge_damage_percent"]`(배율 포함)를 읽으므로 이미 받고 있고, 여기서 또 곱하면 이중 적용이다.
- `collectible_modifiers`는 `deck_search.feasible_orderings`의 순열 루프에 앉아 있다. **유닛당 호출 횟수를 늘리지 말 것** — 한 번 호출해 배율과 효과를 둘 다 쓴다.
- 근거 문서: `docs/superpowers/specs/2026-08-03-collectible-charge-damage-in-transform-design.md`
- 실측 기준값: maxwell 소장품 5단계 → **1.0631**, red-hood 15단계 → **1.0947**. 판정 잔차 +4.9e-05(붙는다) 대 −1.5e-01(안 붙는다).

---

## File Structure

| 파일 | 책임 | 변경 |
| --- | --- | --- |
| `backend/app/roster.py` | 시뮬 입력 조립 | 소장품 1회 해석 → 배율을 값에, 효과를 패시브에 |
| `backend/app/skill_rules/maxwell.py` | Pierce Shot 변형 | 프로파일 차지댐에 배율 |
| `backend/app/skill_rules/red_hood.py` | Red Wolf 변형 | `full_charge_percent` 항에만 배율 |
| `backend/tests/test_skill_rules_maxwell.py` | 맥스웰 인코딩 | 배율 소비 테스트 |
| `backend/tests/test_skill_rules_red_hood.py` | 레드후드 인코딩 | 배율 소비 + 항 분해 테스트 |
| `backend/tests/test_weapon_mode_collectible.py` (신규) | 전 변형 빌더 불변식 | 무반응 방어 |
| `docs/engine-gaps.md` · `docs/measurements/` | 지식 베이스 | 8기 → 2기 정정, 판독 기록 |

---

## Task 1: 배율을 값에 싣고 maxwell이 소비한다

**Files:**
- Modify: `backend/app/roster.py:71-82, 143-151`
- Modify: `backend/app/skill_rules/maxwell.py:106-113`
- Test: `backend/tests/test_skill_rules_maxwell.py`

**Interfaces:**
- Consumes: `collectible_modifiers(tid, level, source_slug, weapon) -> (dict[str, float], list[Effect])` (이미 `roster.py:17`에서 import됨)
- Produces: 값 딕셔너리의 새 키 **`caster_charge_damage_multiplier: float`**(기본 1.0). `_passive_effects`의 시그니처가 **`_passive_effects(spec, collectible_effects)`**로 바뀐다.

- [ ] **Step 1: 기준선을 기록한다**

Run: `cd backend && python -m pytest -q`
기대: `1791 passed, 3 skipped`. 실제 수를 적어둔다.

- [ ] **Step 2: 실패 테스트를 쓴다**

`backend/tests/test_skill_rules_maxwell.py`의 `build_pierce_shot_weapon_mode_schedule`을 쓰는 기존 테스트(85줄 근처) 뒤에 추가한다.

```python
def test_pierce_shot_profile_takes_the_collectible_charge_damage_multiplier():
    """변형 무기의 풀차지 배수는 통째로 스킬 값이라, weapon_stats에 이미 들어가
    있는 소장품 배율이 이 프로파일에는 닿지 않는다. Fienn 실측(2026-08-03)이
    닿아야 한다고 확정했다 - 잔차 4.9e-05."""
    values = {**MAXWELL_VALUES, "caster_charge_damage_multiplier": 1.0631}
    schedule = build_pierce_shot_weapon_mode_schedule(values)
    segments = schedule(SimpleNamespace(burst_times={"maxwell": [20.0]}), 180.0)

    plain = float(PIERCE_SHOT["description_value_03"])
    assert segments[0]["profile"]["charge_damage_percent"] == pytest.approx(
        plain * 1.0631)
    # 다른 슬롯은 배율을 먹지 않는다.
    assert segments[0]["profile"]["damage_percent"] == pytest.approx(
        float(PIERCE_SHOT["description_value_02"]))


def test_pierce_shot_profile_defaults_to_no_multiplier():
    """소장품이 없는 유닛, 그리고 그 키를 넣지 않는 기존 호출자를 위해 기본은 1.0."""
    schedule = build_pierce_shot_weapon_mode_schedule(MAXWELL_VALUES)
    segments = schedule(SimpleNamespace(burst_times={"maxwell": [20.0]}), 180.0)
    assert segments[0]["profile"]["charge_damage_percent"] == pytest.approx(
        float(PIERCE_SHOT["description_value_03"]))
```

파일 상단에 `import pytest`와 `from types import SimpleNamespace`가 없으면 추가한다.

- [ ] **Step 3: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_maxwell.py -q -k "collectible_charge_damage"`
기대: FAIL — 값이 `plain * 1.0631`이 아니라 `plain`으로 나온다

- [ ] **Step 4: maxwell 빌더가 배율을 소비하게 한다**

`backend/app/skill_rules/maxwell.py`의 `build_pierce_shot_weapon_mode_schedule`을 이렇게 만든다.

```python
def build_pierce_shot_weapon_mode_schedule(values):
    pierce = values["pierce_shot"]
    # 변형 무기의 풀차지 배수는 통째로 스킬 값이다. weapon_stats(소장품 배율을
    # 이미 품고 있는)에서 오는 항이 하나도 없으므로, 배율은 여기서 곱해야 닿는다.
    profile = {
        "weapon": "SR",
        "damage_percent": float(pierce["description_value_02"]),
        "charge_damage_percent": (
            float(pierce["description_value_03"])
            * values.get("caster_charge_damage_multiplier", 1.0)),
        "charge_time": float(pierce["description_value_01"]),
    }

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": 1, "profile": profile}
                for t in context.burst_times.get("maxwell", [])]

    return schedule
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_maxwell.py -q`
기대: PASS 전부

- [ ] **Step 6: roster가 배율을 실어 보내게 한다**

`backend/app/roster.py`의 `_passive_effects`가 소장품을 다시 해석하지 않게 바꾼다.

```python
def _passive_effects(spec: NikkeSpec, collectible_effects):
    """Overload, this unit's harmony cube, and the collectible it actually has
    equipped. A collectible's charge-damage 배율 is NOT here - it scales a
    weapon stat - but its normal-attack 배율 IS, because that one shares a buff
    bucket with skills. A cube that hands back rounds instead of moving a stat
    contributes nothing here - see the weapon stats below."""
    return (
        overload_options_to_effects(spec.overload_options, spec.slug)
        + assumed_cube_effects(spec.slug, spec.cube)
        + collectible_effects
    )
```

`assemble_simulation_inputs`의 루프에서, `# inject caster base stats` 주석 바로 위에 소장품을 한 번 해석한다.

```python
        # One resolution per unit: the weapon 배율 feeds weapon-mode profiles
        # that are built from skill data, the effects feed the buff registry.
        # collectible_modifiers sits on deck_search's permutation loop, so this
        # must stay a single call.
        weapon_multipliers, collectible_effects = collectible_modifiers(
            spec.collectible_tid, spec.collectible_level, spec.slug, spec.weapon)
```

값 딕셔너리에 키를 더한다.

```python
            "caster_weapon_stats": spec.weapon_stats,
            "caster_charge_damage_multiplier": weapon_multipliers.get(
                "charge_damage_percent", 1.0),
```

그리고 호출부를 바꾼다.

```python
        passive = _passive_effects(spec, collectible_effects)
```

- [ ] **Step 7: 배선 테스트를 쓴다**

`backend/tests/test_collectible_effects.py` 끝에 추가한다.

```python
def test_the_charge_damage_multiplier_reaches_skill_values():
    """무기변형 프로파일은 스킬 슬롯에서 만들어지므로 weapon_stats를 안 거친다.
    roster가 배율을 값으로 실어 보내야 그 프로파일이 소장품을 받을 수 있다."""
    from app.models import UserNikkeState
    from app.roster import assemble_simulation_inputs
    from app.user_roster import load_roster

    state = UserNikkeState.model_validate({
        "character_slug": "maxwell", "level": 200,
        "hp": 1_000_000.0, "atk": 300_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 1, "skill2": 1, "burst": 1},
        "collectible_tid": SR_COLLECTIBLE_TID, "collectible_level": 5,
    })
    specs, excluded = load_roster([state])
    assert not excluded

    captured = {}
    import app.roster as roster_module
    original = roster_module.build_nikke_rules

    def spy(slug, skill_values):
        captured[slug] = skill_values
        return original(slug, skill_values)

    roster_module.build_nikke_rules = spy
    try:
        assemble_simulation_inputs([(specs[0], 3)])
    finally:
        roster_module.build_nikke_rules = original

    assert captured["maxwell"]["caster_charge_damage_multiplier"] == pytest.approx(1.0631)
```

> `assemble_simulation_inputs`의 인자 모양(`ordered_deck`)이 `(spec, burst_tier)` 튜플이 아니면, 이 파일에 이미 있는 다른 테스트나 `backend/tests/test_roster*.py`에서 실제 호출 모양을 확인해 맞춘다. 검증하려는 것은 **`captured["maxwell"]`에 그 키가 1.0631로 들어 있다**는 것 하나다.

- [ ] **Step 8: 전체를 돌린다**

Run: `cd backend && python -m pytest -q`
기대: Step 1의 수 + 3, 실패 0

- [ ] **Step 9: 커밋**

```bash
git add backend/app/roster.py backend/app/skill_rules/maxwell.py \
        backend/tests/test_skill_rules_maxwell.py backend/tests/test_collectible_effects.py
git commit -m "Carry the collectible charge-damage multiplier into Maxwell's transform"
```

---

## Task 2: red-hood의 무기 항에만 배율을 붙인다

**Files:**
- Modify: `backend/app/skill_rules/red_hood.py:104-109`
- Test: `backend/tests/test_skill_rules_red_hood.py`

**Interfaces:**
- Consumes: Task 1이 넣은 `values["caster_charge_damage_multiplier"]`(기본 1.0)
- Produces: 없음 — 이 태스크로 끝난다

- [ ] **Step 1: 실패 테스트를 쓴다**

`backend/tests/test_skill_rules_red_hood.py`의 `build_red_wolf_weapon_mode_schedule`을 쓰는 기존 테스트(94줄 근처) 뒤에 추가한다.

```python
def test_red_wolf_profile_scales_only_the_weapon_full_charge_term():
    """차지댐이 두 항의 합이다. 소장품 배율은 변형 무기 자신의 풀차지 배수에만
    붙는다 - converted 항은 Glaring의 차속->차지댐 변환이라 무기의 기본 스탯이
    아니다. snow_white_heavy_arms가 하는 분해와 같은 모양."""
    plain = build_red_wolf_weapon_mode_schedule(RED_HOOD_VALUES)(
        SimpleNamespace(burst_times={"red-hood": [20.0]}), 180.0
    )[0]["profile"]["charge_damage_percent"]

    scaled = build_red_wolf_weapon_mode_schedule(
        {**RED_HOOD_VALUES, "caster_charge_damage_multiplier": 1.0947}
    )(SimpleNamespace(burst_times={"red-hood": [20.0]}), 180.0
      )[0]["profile"]["charge_damage_percent"]

    weapon_term = float(RED_WOLF["description_value_12"])
    converted_term = plain - weapon_term
    assert scaled == pytest.approx(weapon_term * 1.0947 + converted_term)
    # 전체에 곱한 값이 아니어야 한다 - 그것이 이 테스트가 지키는 구분이다.
    assert scaled != pytest.approx(plain * 1.0947)
```

파일 상단에 `import pytest`와 `from types import SimpleNamespace`가 없으면 추가한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_red_hood.py -q -k "only_the_weapon_full_charge"`
기대: FAIL — `scaled`가 `plain`과 같다(배율을 아직 안 먹는다)

- [ ] **Step 3: 빌더를 고친다**

`backend/app/skill_rules/red_hood.py`의 `profile` 블록을 이렇게 만든다.

```python
    profile = {
        "weapon": "SR",
        "damage_percent": shot_percent,
        # 소장품의 차지대미지 배율은 변형 무기 자신의 풀차지 배수에만 붙는다.
        # converted 항은 Glaring이 차지속도를 차지대미지로 바꾼 몫이라 무기의
        # 기본 스탯이 아니다.
        "charge_damage_percent": (
            full_charge_percent * values.get("caster_charge_damage_multiplier", 1.0)
            + converted * 100),
        "rate_of_fire": TRANSFORM_SHOTS / duration,
    }
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_rules_red_hood.py -q`
기대: PASS 전부

- [ ] **Step 5: 커밋**

```bash
git add backend/app/skill_rules/red_hood.py backend/tests/test_skill_rules_red_hood.py
git commit -m "Scale Red Hood's transform full-charge term by her collectible"
```

---

## Task 3: 무반응 방어 테스트와 문서

**Files:**
- Create: `backend/tests/test_weapon_mode_collectible.py`
- Modify: `docs/engine-gaps.md`
- Create: `docs/measurements/collectible-charge-damage-in-transform.md`

**Interfaces:**
- Consumes: `_WEAPON_MODE_SCHEDULE_BUILDERS`, `get_weapon_mode_schedules(slug, skill_values)`, `get_skill_value_manifest(slug)`, `assemble_skill_values(slug, manifest, skill_levels)`

- [ ] **Step 1: 방어 테스트를 쓴다**

손으로 유지하는 유닛 목록은 조용히 낡으므로(`docs/insights.md`의 힐 제공자 목록 전례) 행동 불변식을 검사한다.

```python
"""무기변형 프로파일이 소장품 배율에 닿는지를 목록 없이 지킨다.

프로파일의 charge_damage_percent가 0이 아니면, 그 값은 caster_weapon_stats에서
왔거나(그 경로는 user_roster가 이미 배율을 곱해 둔다) caster_charge_damage_multiplier를
소비하거나 둘 중 하나여야 한다. 둘 다에 무반응이면 그 유닛은 소장품을 잃는다 -
maxwell과 red-hood가 정확히 그 상태였다(Fienn 실측 2026-08-03)."""
from types import SimpleNamespace

import pytest

from app.skill_rules.registry import (_WEAPON_MODE_SCHEDULE_BUILDERS,
                                      get_skill_value_manifest,
                                      get_weapon_mode_schedules)
from app.skill_values import assemble_skill_values

MAX_LEVELS = {"skill1": 10, "skill2": 10, "burst": 10}

BASE_WEAPON = {"weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
               "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}

TRANSFORM_SLUGS = sorted(_WEAPON_MODE_SCHEDULE_BUILDERS)


class _AnyContext:
    """burst_times 말고 무엇을 읽든 0.0을 돌려주는 문맥 - 이 테스트는 프로파일의
    수치만 보므로 스케줄이 무엇을 조회하든 상관없다."""

    def __init__(self, slug):
        self.burst_times = {slug: [20.0]}
        self.shot_times = {}

    def __getattr__(self, name):
        return lambda *args, **kwargs: 0.0


def _charge_damage(slug, weapon_charge, multiplier):
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        pytest.skip(f"{slug} has no skill-value manifest")
    values = {
        **assemble_skill_values(slug, manifest, MAX_LEVELS),
        "caster_atk": 300_000.0, "caster_def": 3_000.0, "caster_max_hp": 1_000_000.0,
        "caster_weapon_stats": {**BASE_WEAPON, "charge_damage_percent": weapon_charge},
        "caster_charge_damage_multiplier": multiplier,
    }
    schedule = get_weapon_mode_schedules(slug, values)
    segments = schedule(_AnyContext(slug), 180.0)
    if not segments:
        return None
    return segments[0]["profile"].get("charge_damage_percent")


@pytest.mark.parametrize("slug", TRANSFORM_SLUGS)
def test_a_transform_profile_with_charge_damage_is_reachable_by_the_collectible(slug):
    baseline = _charge_damage(slug, 250.0, 1.0)
    if not baseline:
        return  # 차지댐이 없는 프로파일은 곱할 대상이 없다

    moved_by_weapon = _charge_damage(slug, 500.0, 1.0) != baseline
    moved_by_multiplier = _charge_damage(slug, 250.0, 2.0) != baseline

    assert moved_by_weapon or moved_by_multiplier, (
        f"{slug}의 변형 프로파일 차지댐이 weapon_stats에도 소장품 배율에도 "
        f"반응하지 않는다 - 그 유닛은 변형 중 소장품을 잃는다")
```

- [ ] **Step 2: 돌린다**

Run: `cd backend && python -m pytest tests/test_weapon_mode_collectible.py -q`
기대: PASS 전부(Task 1·2가 이미 끝났으므로). 어떤 슬러그가 문맥 조회나 값 조립에서 터지면 그 원인을 고친다 — **테스트에서 그 슬러그를 제외하지 말 것.** 제외는 이 테스트가 막으려는 바로 그 침묵이다.

- [ ] **Step 3: `engine-gaps.md`를 2기로 정정한다**

현재 이 갭이 **8기**(anis-star · laplace-signature · maxwell · milk-blooming-bunny · red-hood · scarlet-black-shadow · snow-white-heavy-arms · takina-inoue)로, 그중 셋이 캘리브레이션 덱에 있다고 적혀 있다. 둘 다 틀렸다. 실제로 걸린 유닛은 **maxwell · red-hood 둘**이고 **캘리브레이션 덱에 없다**. 스펙의 분류표를 근거로 항목을 다시 쓰고, 이제 해소됐음을 반영한다.

| 분류 | 유닛 |
| --- | --- |
| 걸렸음(이번에 해소) | maxwell · red-hood |
| `weapon_stats`를 읽음 | snow-white-heavy-arms |
| 침묵 세그먼트 | milk-blooming-bunny · scarlet-black-shadow |
| 프로파일에 차지댐 없음 | laplace · laplace-signature · takina-inoue · moran(-signature) · laplace-ultimate-hero |
| 소장품이 `"effect"` 배치 | snow-white · zwei(-signature) · nayuta |
| 변형 빌더 없음 | anis-star · modernia |

**미해결로 남는 것**: 가산 스킬 항(red-hood의 `converted * 100`, heavy-arms의 `shades` 항)에도 배율이 붙는지는 측정되지 않았다.

- [ ] **Step 4: 측정 기록을 만든다**

`docs/measurements/collectible-charge-damage-in-transform.md`. `docs/measurements/bready-charge.md`의 형식을 따른다(원본 수치는 이후 편집하지 않는다).

조건: Fienn 2026-08-03, 편성 로자나 / 센티 / 맥스웰, 작열 속성 사격장(수냉 약점), **MID** 위치, 맥스웰 스킬레벨 1/1/1, 소장품 SR 5단계(6.31% → 1.0631).

원본(논크리):

```
사이클 A   변형샷 코어 7014461   기본풀차지 코어 2786144   기본풀차지 논코어 1671686
사이클 B   변형샷 논코어 4208677  기본풀차지 코어 2786144   기본풀차지 논코어 1671686
```

파생값과 판정:

```
기본무기  코어/논코어 1.6666671  ->  M = 1.4999991
변형샷    코어/논코어 1.6666665  ->  M = 1.5000004     M이 같으므로 보정 1

논코어 비율 (변형 ÷ 기본풀차지)                          2.5176220
  배율이 붙는다  (144.85×3.00) ÷ (69.04×2.50)            2.5176700   잔차 +4.9e-05
  안 붙는다      위 ÷ 1.0631                             2.3682400   잔차 -1.5e-01
```

**반드시 적을 것 — 이 판독의 캐비엇**: 비율은 분자·분모에 공통인 인자에 눈이 먼다. 위가 엄밀히 말하는 것은 `k_변형 = k_기본`이지 `k = 1.0631`이 아니다. 기본 무기 쪽이 1.0631이라는 것은 에이드: 에이전트 바니의 사격장 판독 7개(절대값 적합, `250% × 1.0631 = 265.775%`, 0.002% 이내)가 확정했고, 이 측정은 그 위에 얹혀야 체인이 닫힌다.

**가르지 못한 것**: 가산 스킬 항에도 붙는지 · 변형 캐논의 유효사거리 밴드(MID에서 항이 0이라는 것만 확인, `far`인지 `near`인지는 미상) · 소장품 사다리의 다른 칸 · RL 유닛에서의 동일성.

- [ ] **Step 5: 전체를 돌린다**

Run: `cd backend && python -m pytest -q`
기대: 실패 0

- [ ] **Step 6: 캘리브레이션이 안 움직이는지 확인한다**

Run: `python scripts/measure_record_calibration.py`
기대: **1.082x, 16/25 그대로.** 두 유닛 다 기록 덱에 없으므로 움직이면 안 된다. 움직이면 의도 밖의 무언가를 건드린 것이다.

- [ ] **Step 7: 커밋**

```bash
git add backend/tests/test_weapon_mode_collectible.py docs/
git commit -m "Guard transform profiles against losing the collectible, and record the measurement"
```

---

## Self-Review

**스펙 커버리지**

| 스펙 절 | 태스크 |
| --- | --- |
| 설계 1 — 배율을 값에 싣는다 | Task 1 Step 6 |
| 설계 2 — maxwell | Task 1 Step 4 |
| 설계 2 — red-hood(무기 항에만) | Task 2 Step 3 |
| 설계 2 — 다른 빌더는 안 건드린다 | Task 3 Step 1의 불변식이 지킨다(제외 금지 명시) |
| 설계 3 — 무반응 방어 테스트 | Task 3 Step 1 |
| 설계 4 — 회귀 기대값(캘리 불변) | Task 3 Step 6 |
| 문제 절 — 8기 → 2기 정정 | Task 3 Step 3 |
| 측정 절 + 캐비엇 | Task 3 Step 4 |
| 가르지 못한 것 | Task 3 Step 4 |

**타입 일관성**: 키 이름 `caster_charge_damage_multiplier`가 Task 1(생산)·Task 1 Step 4·Task 2 Step 3·Task 3 Step 1(소비)에서 동일. `_passive_effects(spec, collectible_effects)`는 Task 1 Step 6 안에서 정의와 호출부가 함께 바뀐다.

**알려진 미확정 하나**: Task 1 Step 7의 `assemble_simulation_inputs` 호출 모양은 실제 시그니처를 확인해 맞추라고 지시했다. 검증 대상(값 딕셔너리에 키가 1.0631로 들어간다)은 모양과 무관하게 동일하다.
