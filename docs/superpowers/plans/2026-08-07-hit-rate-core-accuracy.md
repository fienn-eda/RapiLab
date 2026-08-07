# 명중률 → 탄착군 → 코어히트율 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 코어 히트를 불리언에서 확률로 바꾼다 — 무기 클래스와 명중률 스탯이 정하는 탄착군이 코어보다 크면 그 면적비만큼만 코어에 든다.

**Architecture:** 순수 함수 모듈(`accuracy.py`)이 탄착군과 확률을 계산하고, `damage_formula`가 그 확률을 크리티컬과 똑같은 기대값 항으로 소비한다. `BossProfile.core_diameter_px`가 None이면 확률은 1.0으로 고정돼 기존 동작이 바이트 단위로 보존된다(opt-in). 부수적으로 `hit_rate` 스탯이 소비자를 얻어 15슬러그의 보류가 풀리고, 지금 수집기가 버리는 명중률 오버로드가 들어온다.

**Tech Stack:** Python 3.14 (백엔드, pytest) · Node `node --test` + jsdom (blablalink 수집기)

설계 문서: `docs/superpowers/specs/2026-08-07-hit-rate-core-accuracy-design.md`

## Global Constraints

- **`hit_rate`는 비율이다** — 명중 33%는 `0.33`. 엔진의 모든 퍼센트 Effect가 그렇다(`overload_effects`가 `value/100`으로 넣는다). 탄착군이 0이 되는 지점은 `1.10`이지 `110`이 아니다.
- **기본값은 opt-in이다** — `core_diameter_px=None`에서 기존 시뮬 결과가 **바이트 동일**해야 한다. 이것이 계약이고 Task 4의 첫 테스트가 그것을 지킨다.
- **값을 지어내지 않는다.** 무기 탄착군은 게임 데이터에서 온 값이고, 오버로드 명중의 값 곡선은 `option_id` 대조 전까지 만들지 않는다.
- 백엔드 테스트: `cd backend && python -m pytest` (루트에서 돌리면 `No module named 'app'`).
- 수집기 테스트: `cd tools/collect-blablalink && npm test`.
- 코드 주석은 **무엇을·왜**만 쓴다. "예전엔 이랬다"를 쓰지 않는다.
- 커밋 메시지는 영어 서술문(이 저장소 관행).
- **`.claude/worktrees/` 아래 사본을 고치지 않는다** — `grep -r`이 그것을 긁는다. 작업 대상은 리포지토리 루트의 파일뿐이다.

---

### Task 1: `accuracy.py` — 탄착군과 코어히트율

순수 함수 모듈. 다른 태스크가 전부 이것을 소비하므로 먼저 만든다.

**Files:**
- Create: `backend/app/accuracy.py`
- Test: `backend/tests/test_accuracy.py`

**Interfaces:**
- Consumes: 없음(순수 함수, 임포트 없음).
- Produces:
  - `WEAPON_SPREAD_DIAMETER: dict[str, float]` — 무기 클래스 → 명중 0%에서의 탄착군 지름(px).
  - `ZERO_SPREAD_HIT_RATE: float = 1.10`
  - `spread_diameter(weapon: str, hit_rate: float) -> float`
  - `core_hit_rate(weapon: str, hit_rate: float, core_diameter: float) -> float`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_accuracy.py`:

```python
import pytest

from app.accuracy import (WEAPON_SPREAD_DIAMETER, ZERO_SPREAD_HIT_RATE,
                          core_hit_rate, spread_diameter)


def test_base_diameters_are_the_values_in_the_game_data():
    # shot_detail.start_accuracy_circle_scale, uniform within each weapon class
    # across the 77 collected units. MG carries its converged `end` value.
    assert WEAPON_SPREAD_DIAMETER == {
        "AR": 75.0, "SG": 250.0, "SMG": 110.0, "MG": 10.0, "SR": 10.0, "RL": 10.0,
    }


def test_hit_rate_narrows_the_spread_linearly():
    assert spread_diameter("SG", 0.0) == 250.0
    assert spread_diameter("SG", 0.55) == pytest.approx(125.0)
    assert spread_diameter("AR", 0.55) == pytest.approx(37.5)


def test_every_weapon_reaches_zero_spread_at_the_same_hit_rate():
    # The article's three per-weapon regressions all cross zero here, which is
    # what makes them one equation rather than three.
    for weapon in WEAPON_SPREAD_DIAMETER:
        assert spread_diameter(weapon, ZERO_SPREAD_HIT_RATE) == 0.0


def test_hit_rate_past_the_singularity_does_not_go_negative():
    # Dorothy: Serendipity stacks two buffs past 110%.
    assert spread_diameter("SG", 1.20) == 0.0


def test_negative_hit_rate_widens_the_spread():
    # Mast: Romantic Maid's Drunken stacks to -107.76%.
    assert spread_diameter("MG", -1.10) == pytest.approx(20.0)


def test_core_hit_rate_is_the_area_ratio():
    assert core_hit_rate("AR", 0.0, 50.0) == pytest.approx((50 / 75) ** 2)
    assert core_hit_rate("SMG", 0.0, 50.0) == pytest.approx((50 / 110) ** 2)
    assert core_hit_rate("SG", 0.0, 50.0) == pytest.approx((50 / 250) ** 2)


def test_a_spread_inside_the_core_always_hits_it():
    assert core_hit_rate("SR", 0.0, 50.0) == 1.0
    assert core_hit_rate("RL", 0.0, 50.0) == 1.0
    assert core_hit_rate("MG", 0.0, 50.0) == 1.0


def test_zero_spread_always_hits():
    assert core_hit_rate("SG", ZERO_SPREAD_HIT_RATE, 50.0) == 1.0


def test_an_unknown_weapon_raises():
    with pytest.raises(KeyError):
        spread_diameter("BOW", 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_accuracy.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.accuracy'`

- [ ] **Step 3: Write the implementation**

`backend/app/accuracy.py`:

```python
"""탄착군(bullet spread)의 크기와, 그로부터 나오는 코어 히트 확률.

명중률 스탯은 탄착군의 지름을 좁힌다. 무기별로 따로 측정된 회귀식 셋
(SG y=-2.18x+240 · AR y=-0.69x+76 · SMG y=-1x+110 — 아카라이브 니케 채널
96243965)은 전부 명중 110%에서 지름 0에 닿으므로 같은 한 식이다:

    지름 = 기본지름 x (1 - 명중/1.10)

코어에 드는 비율은 탄착이 그 원 안에 균등 분포한다고 보고 면적비로 낸다.
글이 준 실측 네 점은 그 가정에서 코어 지름 51.1px +- 6.1%로 모이고(중앙
집중 분포로 풀면 37.9~59.0px로 흩어진다), 그 51.1px는 이 프로젝트가 따로
세운 50px 가정과 2% 차이다.
"""

# 탄착군이 한 점으로 수렴하는 명중률. 세 무기의 측정된 회귀식이 모두 여기서
# 만나므로 무기별 상수가 아니라 게임 전체의 상수다.
ZERO_SPREAD_HIT_RATE = 1.10

# 명중 0%에서 각 무기가 그리는 탄착군의 지름(px).
#
# `data/shiftypad/raw/*.json`의 `shot_detail.start_accuracy_circle_scale`에서
# 온 값이고, 수집된 77유닛에서 클래스 내 분산이 0이다. 손으로 유지되는 표라
# `scripts/audit_weapon_accuracy_scales.py`가 데이터와 대조한다.
#
# MG만 탄창 안에서 좁아진다(start 250 -> end 10, 발당 -7). 여기 적힌 것은
# 그 수렴값이므로, 탄창 앞 29발이 코어를 놓치는 구간은 이 모델에 없다.
WEAPON_SPREAD_DIAMETER = {
    "AR": 75.0,
    "SG": 250.0,
    "SMG": 110.0,
    "MG": 10.0,
    "SR": 10.0,
    "RL": 10.0,
}


def spread_diameter(weapon, hit_rate):
    """이 무기가 이 명중률에서 그리는 탄착군의 지름(px).

    명중이 `ZERO_SPREAD_HIT_RATE`를 넘어도 지름은 음수가 되지 않는다 —
    도로시: 세렌디피티가 두 버프를 겹쳐 실제로 넘는다. 명중이 음수면
    (마스트: 로맨틱 메이드의 Drunken) 반대로 지름이 커진다.

    모르는 무기는 KeyError. 조용히 넓거나 좁은 기본값을 주면 그 유닛의
    코어히트율이 근거 없이 정해진다.
    """
    base = WEAPON_SPREAD_DIAMETER[weapon]
    return base * max(0.0, 1.0 - hit_rate / ZERO_SPREAD_HIT_RATE)


def core_hit_rate(weapon, hit_rate, core_diameter):
    """조준점이 코어 중심에 있을 때 코어에 드는 발의 비율.

    탄착군 전체가 코어 안에 들어가면 전부 맞고, 그렇지 않으면 두 원의
    면적비다.
    """
    diameter = spread_diameter(weapon, hit_rate)
    if diameter <= core_diameter:
        return 1.0
    return (core_diameter / diameter) ** 2
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_accuracy.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/accuracy.py backend/tests/test_accuracy.py
git commit -m "The bullet spread is one equation, not three per-weapon ones

All three measured regressions cross zero diameter at 110% hit rate, so
the spread is base_diameter x (1 - hit_rate/1.10) and the per-weapon part
is just the base. Those bases come from shot_detail in the collected data,
where they are uniform within each weapon class."
```

---

### Task 2: `damage_formula`의 기대값 코어 항

크리티컬이 이미 기대값이다. 코어를 같은 모양으로 만든다.

**Files:**
- Modify: `backend/app/damage_formula.py:29-49` (`_major_modifiers`), `:52-96` (`calculate_damage`)
- Test: `backend/tests/test_damage_formula.py`

**Interfaces:**
- Consumes: 없음.
- Produces: `calculate_damage(..., core_hit_rate=1.0, ...)` — 코어 항에 곱해지는 확률. 기본값 1.0이라 기존 호출의 의미는 그대로다.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_damage_formula.py` 끝에 추가:

```python
def test_core_hit_rate_defaults_to_certainty():
    # Every existing caller omits it, so the default must leave them unchanged.
    assert (calculate_damage(atk=1000, enemy_def=0, core_hit_bonus=1.0)
            == calculate_damage(atk=1000, enemy_def=0, core_hit_bonus=1.0,
                                core_hit_rate=1.0))


def test_core_hit_rate_scales_the_core_term_only():
    # 1 + 0.5 * 1.0 = 1.5 against the certain hit's 1 + 1.0 = 2.0
    assert calculate_damage(atk=1000, enemy_def=0, core_hit_bonus=1.0,
                            core_hit_rate=0.5) == 1500


def test_core_damage_sources_ride_inside_the_probability():
    # They only pay out on a round that actually hit the core.
    # 1 + 0.5 * (1.0 + 0.4) = 1.7
    assert calculate_damage(atk=1000, enemy_def=0, core_hit_bonus=1.0,
                            other_core_damage_sources=0.4,
                            core_hit_rate=0.5) == 1700


def test_core_hit_rate_leaves_the_other_major_modifiers_alone():
    # crit / full burst / effective range are untouched by the core probability:
    # 1 + 0.15*0.5 + 0.5*1.0 + 1.0*0.5 + 1.0*0.3 = 2.375
    assert calculate_damage(
        atk=1000, enemy_def=0, crit_rate=0.15, core_hit_bonus=1.0,
        core_hit_rate=0.5, full_burst_bonus=1.0, effective_range_bonus=1.0,
    ) == 2375


def test_a_missed_core_pays_nothing():
    assert (calculate_damage(atk=1000, enemy_def=0, core_hit_bonus=1.0,
                             core_hit_rate=0.0)
            == calculate_damage(atk=1000, enemy_def=0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_damage_formula.py -q`
Expected: FAIL — `TypeError: calculate_damage() got an unexpected keyword argument 'core_hit_rate'`

- [ ] **Step 3: Add the parameter and the expected-value term**

`backend/app/damage_formula.py` — `_major_modifiers`를 교체:

```python
def _major_modifiers(
    crit_rate,
    other_critical_damage_sources,
    core_hit_rate,
    core_hit_bonus,
    other_core_damage_sources,
    full_burst_bonus,
    effective_range_bonus,
):
    # Expected-value crit: a hit crits with probability crit_rate, and a crit
    # adds (0.5 base + crit damage sources) to the major modifier. Averaged over
    # many hits that is crit_rate * (0.5 + sources). Crit damage sources are
    # therefore inert without any crit chance, matching the game.
    expected_crit_term = crit_rate * (0.5 + other_critical_damage_sources)
    # Expected-value core, the same shape. Aiming at the core is not the same as
    # landing on it: the bullet spread can be wider than the core, and
    # core_hit_rate is the share of rounds that fall inside it (see accuracy.py).
    # Core damage sources sit INSIDE the probability because they pay out only on
    # a round that hit the core.
    expected_core_term = core_hit_rate * (core_hit_bonus + other_core_damage_sources)
    return (
        1
        + expected_crit_term
        + expected_core_term
        + full_burst_bonus * 0.5
        + effective_range_bonus * 0.3
    )
```

`calculate_damage`의 시그니처에서 `core_hit_bonus=0.0` 바로 앞에 추가:

```python
    core_hit_rate=1.0,
    core_hit_bonus=0.0,
```

그리고 `_major_modifiers` 호출을 키워드로 교체(인자가 일곱이라 위치로 세면 조용히 틀린다):

```python
    major_modifiers = _major_modifiers(
        crit_rate=crit_rate,
        other_critical_damage_sources=other_critical_damage_sources,
        core_hit_rate=core_hit_rate,
        core_hit_bonus=core_hit_bonus,
        other_core_damage_sources=other_core_damage_sources,
        full_burst_bonus=full_burst_bonus,
        effective_range_bonus=effective_range_bonus,
    )
```

- [ ] **Step 4: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS — 기존 1984 + 새 5 + Task 1의 9. 실패가 하나라도 나오면 기본값 1.0이 중립이 아니라는 뜻이므로 멈추고 원인을 볼 것.

- [ ] **Step 5: Commit**

```bash
git add backend/app/damage_formula.py backend/tests/test_damage_formula.py
git commit -m "Core damage becomes an expected value, like crit already was

A hit crits with a probability and the formula averages over it; a round
lands on the core with a probability too, and now the formula averages
over that the same way. Core damage sources sit inside the probability
because they only pay out on a round that hit the core. The default of 1.0
is what every existing caller means today."
```

---

### Task 3: `BossProfile.core_diameter_px`를 엔진까지 배선

아직 아무도 소비하지 않는다 — 값이 끝까지 도달하는 것만 만든다. 배선 지점이 셋이고, 이 저장소는 그중 하나를 빠뜨려 `effective_range_band`가 엔진에 도달하지 못한 적이 있다.

**Files:**
- Modify: `backend/app/deck_search.py` (`BossProfile` 필드, `evaluate_deck`의 `simulate_raid(...)` 호출 — 446-457행)
- Modify: `backend/app/api.py` (`BossProfileIn` 필드 — 51-68행)
- Modify: `backend/app/raid_simulator.py` (`_simulate_raid_once` 파라미터 — 644행 근처)
- Test: `backend/tests/test_api_boss_profile.py`

**Interfaces:**
- Consumes: 없음.
- Produces: `BossProfile.core_diameter_px: float | None`, `BossProfileIn.core_diameter_px: float | None`, `_simulate_raid_once(..., core_diameter_px=None, ...)`.

**이 태스크의 테스트는 이미 존재한다.** `test_api_boss_profile.py`가 필드 **집합**을 비교하는 두 테스트를 갖고 있다 — `test_every_request_field_reaches_the_engine_profile`(BossProfileIn ⊆ BossProfile)과 `test_evaluate_deck_forwards_every_boss_field_the_simulator_accepts`(BossProfile ∩ `_simulate_raid_once` 파라미터 ⊆ `evaluate_deck`이 넘긴 kwargs). 이름 하나를 검사하는 게 아니라 집합을 비교하므로, **새 필드는 추가되는 날 자동으로 커버된다.** 그래서 실패를 먼저 만드는 방법이 다르다: 필드를 절반만 배선하면 기존 테스트가 떨어진다.

- [ ] **Step 1: Add the field to the dataclass and the engine only — deliberately not to `evaluate_deck`**

`backend/app/deck_search.py`의 `BossProfile`에 `pierce_hits_body_behind_core` 아래로 추가:

```python
    # 코어의 지름(px). None이면 이 인카운터는 코어히트율을 모델링하지 않고
    # 적격 평타가 전부 코어에 든다고 본다 - 엔진이 오래 모델해 온 상한이다.
    # 값을 주면 무기 탄착군과의 면적비가 그 비율을 정한다(app/accuracy.py).
    # `core_hittable`이 거짓이면 무시된다: 코어가 없으면 크기를 물을 수 없다.
    core_diameter_px: float | None = None
```

`backend/app/raid_simulator.py`의 `_simulate_raid_once` 시그니처에서 `pierce_hits_body_behind_core=False` 아래로 추가:

```python
    core_diameter_px=None,
```

- [ ] **Step 2: Run the test to watch the existing guard catch the gap**

Run: `cd backend && python -m pytest tests/test_api_boss_profile.py -q`
Expected: FAIL — `evaluate_deck drops boss fields the simulator accepts: ['core_diameter_px']`

이 실패가 이 태스크의 요점이다. 이 저장소는 정확히 이 지점에서 `effective_range_band`를 잃은 적이 있고, 그때 만들어진 가드가 지금 일하고 있다.

- [ ] **Step 3: Finish the wiring**

`backend/app/deck_search.py`의 `evaluate_deck` 안 `simulate_raid(...)` 호출에 추가(`pierce_hits_body_behind_core=boss.pierce_hits_body_behind_core,` 다음 줄):

```python
        core_diameter_px=boss.core_diameter_px,
```

`backend/app/api.py`의 `BossProfileIn`에 같은 이름으로 추가(`boss_profile`이 `**model_dump()`로 스프레드하므로 이름만 맞으면 건너간다):

```python
    # See BossProfile.core_diameter_px - only meaningful together with
    # core_hittable.
    core_diameter_px: float | None = None
```

- [ ] **Step 4: Pin the opt-in default explicitly**

집합 비교 테스트는 필드가 **도달하는지**만 보고 기본값이 무엇인지는 안 본다. 기본값은 이 작업 전체의 계약이므로 따로 박는다. `backend/tests/test_api_boss_profile.py` 끝에 추가:

```python
def test_an_omitted_core_diameter_models_the_old_ceiling():
    # None means "this encounter does not model a core hit rate", which is what
    # every caller sent before the field existed - and what the recorded-raid
    # harness keeps sending, so the calibration is untouched by this work.
    assert boss_profile(BossProfileIn()).core_diameter_px is None


def test_the_core_diameter_a_caller_sends_is_the_one_the_engine_gets():
    assert boss_profile(BossProfileIn(
        core_hittable=True, core_diameter_px=62.5)).core_diameter_px == 62.5
```

- [ ] **Step 5: Run the tests**

Run: `cd backend && python -m pytest tests/test_api_boss_profile.py -q`
Expected: PASS

Run: `cd backend && python -m pytest -q`
Expected: PASS — 전부 초록.

- [ ] **Step 6: Commit**

```bash
git add backend/app/deck_search.py backend/app/api.py backend/app/raid_simulator.py backend/tests/test_api_boss_profile.py
git commit -m "Carry the core diameter from the request down to the engine

Nothing reads it yet. Wiring it on its own means the test that proves it
arrives is not tangled with the test that proves what it does, and this
repo has already shipped a boss field that stopped at BossProfile."
```

---

### Task 4: 코어히트율을 소비한다

핵심 태스크. `hit_rate`가 소비자를 얻고, 코어 히트가 확률이 된다.

**Files:**
- Modify: `backend/app/raid_simulator.py` (`_BUNDLE_STATS` 496-507행 · `_damage_instance` 786-789행과 824-827행 · `_entries` 1667-1709행)
- Test: `backend/tests/test_core_hit_rate.py` (신규)

**Interfaces:**
- Consumes: Task 1의 `WEAPON_SPREAD_DIAMETER` / `core_hit_rate`, Task 2의 `calculate_damage(core_hit_rate=...)`, Task 3의 `core_diameter_px`.
- Produces: 없음(엔진 내부).

- [ ] **Step 1: Write the failing test**

`backend/tests/test_core_hit_rate.py` (신규). 픽스처는 `test_core_pierce_hits_body.py`의 것을 그대로 따랐다 — ATK 10000 · 발당 100% · 재장전 0 · 크리 0 · 전투 1.5초라 **풀 버스트 창이 열리기 전에 끝나므로 평타 한 발의 데미지가 곧 major modifier 자체**다(코어 확실히 맞으면 20000, 안 맞으면 10000):

```python
"""코어히트율 — 탄착군이 코어보다 크면 평타의 일부만 코어 보너스를 받는다.

숫자를 비율이 아니라 값으로 박는다. ATK 10000 x 발당 100%에 다른 major
modifier가 없으므로 한 발은 곧 10000 x (1 + p x CORE_HIT_BONUS)이고,
"1.44배"라고만 적으면 CORE_HIT_BONUS가 움직여도 테스트가 계속 통과한다.
"""
import pytest

from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule

BASE_STATS = {s: {"atk": 10000, "def": 0, "max_hp": 0}
              for s in ("b1", "b2", "striker")}


def _deck(weapon):
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "striker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0,
         "weapon": weapon},
    ]


def _weapon(weapon):
    return {"weapon": weapon, "damage_percent": 100.0, "max_ammo": 999,
            "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0}


def _log(weapon, *, core_diameter_px, striker_rules=(), two_pierce=False):
    return simulate_raid(
        _deck(weapon),
        {"b1": [], "b2": [], "striker": list(striker_rules)},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        # The fight ends before any Full Burst window opens, so the core bonus is
        # the only major modifier in play.
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={"striker": _weapon(weapon)},
        core_hittable=True,
        core_diameter_px=core_diameter_px,
        pierce_hits_body_behind_core=two_pierce,
    )["damage_log"]


def _shots(log):
    return [e["damage"] for e in log if e["source"] == "normal_attack"]


def _first_shot(weapon, **kwargs):
    return _shots(_log(weapon, **kwargs))[0]


# SR and RL are charge weapons (attack_rate.CHARGE_WEAPONS), so firing them here
# would drag the charge model into a test about spread. Their 10px spread is
# already covered by test_accuracy.py, and MG stands in for "spread inside the
# core" among the sustained-fire weapons.
FIRING_WEAPONS = ("AR", "SG", "SMG", "MG")


def test_no_core_diameter_leaves_every_shot_on_the_core():
    # The opt-in contract: with no diameter the engine models its old ceiling.
    for weapon in FIRING_WEAPONS:
        assert _first_shot(weapon, core_diameter_px=None) == 20000.0


@pytest.mark.parametrize("weapon,expected", [
    ("AR", 10000.0 * (1 + (50 / 75) ** 2)),
    ("SMG", 10000.0 * (1 + (50 / 110) ** 2)),
    ("SG", 10000.0 * (1 + (50 / 250) ** 2)),
    # An MG's spread converges to 10px, already inside a 50px core.
    ("MG", 20000.0),
])
def test_each_weapon_collects_its_area_ratio(weapon, expected):
    assert _first_shot(weapon, core_diameter_px=50.0) == pytest.approx(expected)


def test_a_hit_rate_buff_narrows_the_spread_and_raises_the_damage():
    # Without this wiring hit_rate registers and nothing happens - which is
    # exactly what fifteen slugs had been recording as a deferral.
    bare = _first_shot("SG", core_diameter_px=50.0)
    # 55% halves an SG's 250px spread to 125px, so p goes 0.04 -> 0.16.
    buffed = _first_shot(
        "SG", core_diameter_px=50.0,
        striker_rules=[buff_rule("battle_start", [("hit_rate", 0.55, "self", None)])],
    )
    assert bare == pytest.approx(10400.0)
    assert buffed == pytest.approx(11600.0)


def test_hit_rate_past_the_singularity_reaches_every_core():
    # Dorothy: Serendipity stacks two buffs past 110%, where the spread is a
    # point and even a shotgun cannot miss.
    assert _first_shot(
        "SG", core_diameter_px=50.0,
        striker_rules=[buff_rule("battle_start", [("hit_rate", 1.20, "self", None)])],
    ) == 20000.0


def test_a_negative_hit_rate_widens_the_spread():
    # Mast: Romantic Maid's Drunken. An AR at -55% spreads to 112.5px.
    assert _first_shot(
        "AR", core_diameter_px=50.0,
        striker_rules=[buff_rule("battle_start", [("hit_rate", -0.55, "self", None)])],
    ) == pytest.approx(10000.0 * (1 + (50 / 112.5) ** 2))


def test_core_strike_ignores_the_spread():
    """Skill damage whose own text says it strikes the core is not a question of
    aim. The same `is_normal_attack` gate also covers a summon that aims and
    shoots on its own (Anis: Star's Shooting Stars, `core_eligible_override`)."""
    result = simulate_raid(
        _deck("SG"),
        {s: [] for s in ("b1", "b2", "striker")},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        core_hittable=True,
        core_diameter_px=50.0,
        burst_damage_types={"striker": "core_strike"},
    )
    burst = next(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    # An SG's own normal attacks would only collect 4% of the bonus here.
    assert burst == 20000.0


def test_the_pierce_body_instance_is_weighted_by_the_core_hit_rate():
    # A round that missed the core has no core to pass through, so there is
    # nothing behind it to hit: the body instance exists only for the share
    # that hit.
    holds_pierce = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]
    shots = _shots(_log("AR", core_diameter_px=50.0,
                        striker_rules=holds_pierce, two_pierce=True))
    p = (50 / 75) ** 2
    assert shots[:2] == [pytest.approx(10000.0 * (1 + p)),
                         pytest.approx(10000.0 * p)]


def test_pierce_is_unchanged_when_no_diameter_is_given():
    holds_pierce = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]
    shots = _shots(_log("AR", core_diameter_px=None,
                        striker_rules=holds_pierce, two_pierce=True))
    assert shots[:2] == [20000.0, 10000.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_core_hit_rate.py -q`
Expected: FAIL — 코어히트율이 아직 1.0으로 고정이라 무기별 비율 테스트가 전부 떨어진다.

- [ ] **Step 3: Add `hit_rate` to the stat bundle**

`backend/app/raid_simulator.py`의 `_BUNDLE_STATS` 끝에 추가:

```python
    "normal_attack_crit_rate",
    "hit_rate",
)
```

- [ ] **Step 4: Compute the rate and pass it to the formula**

`backend/app/raid_simulator.py` 상단 임포트에 추가:

```python
from app.accuracy import WEAPON_SPREAD_DIAMETER, core_hit_rate
```

`_in_effective_range` 바로 아래에 헬퍼를 추가(같은 클로저 안이라 `weapon_stats` · `core_diameter_px` · `_stat_bundle`이 보인다):

```python
    def _core_hit_rate_at(slug, time, is_normal_attack):
        """이 인스턴스의 발 중 코어에 드는 비율.

        탄착군이 좌우하는 것은 평타뿐이다. `core_strike`는 스킬이 코어를
        때린다고 원문에 적힌 딜이고, 소환물은 스스로 조준하므로(아니스:
        스타의 Shooting Stars) 둘 다 겨냥의 문제가 아니다 - 둘 다 평타가
        아니라서 이 한 줄로 함께 걸러진다.

        `core_diameter_px`가 없으면 이 인카운터는 코어히트율을 모델링하지
        않는다: 적격 인스턴스는 엔진이 오래 모델해 온 상한인 1.0을 받는다.
        """
        if core_diameter_px is None or not is_normal_attack:
            return 1.0
        weapon = (weapon_stats.get(slug) or {}).get("weapon")
        if weapon not in WEAPON_SPREAD_DIAMETER:
            return 1.0
        return core_hit_rate(
            weapon, _stat_bundle(slug, time)["hit_rate"], core_diameter_px
        )
```

`_damage_instance`의 시그니처에 `core_hit_rate` 인자를 추가하되 **이름이 임포트한 함수와 겹치므로 파라미터명을 `core_hit_share`로 둔다**:

```python
    def _damage_instance(
        slug, percent, time, damage_type="attack", extra_charge_bonus=0.0, extra_flat_atk=0.0,
        hits_core=False, on_charge_weapon=None, is_normal_attack=False, core_hit_share=1.0,
    ):
```

같은 함수의 `terms` dict에서 `core_hit_bonus` 바로 앞에 추가:

```python
            core_hit_rate=core_hit_share,
            core_hit_bonus=CORE_HIT_BONUS if hits_core else 0.0,
```

- [ ] **Step 5: Weight the instances in `_entries`**

`backend/app/raid_simulator.py`의 `_entries`에서 `hits_core` 계산 아래에 확률을 구하고, `instance`가 가중치를 받게 한다:

```python
        share = _core_hit_rate_at(ev["slug"], ev["time"], is_normal_attack)

        def instance(on_core, weight=1.0):
            return {
                "slug": ev["slug"],
                "time": ev["time"],
                "damage": _damage_instance(
                    ev["slug"], percent, ev["time"],
                    damage_type=ev["damage_type"],
                    extra_charge_bonus=ev["extra_charge_bonus"],
                    extra_flat_atk=ev["extra_flat_atk"],
                    hits_core=on_core,
                    core_hit_share=share,
                    on_charge_weapon=ev["on_charge_weapon"],
                    is_normal_attack=is_normal_attack,
                ) * weight,
                "source": ev["source"],
                "damage_type": ev["damage_type"],
            }
```

그리고 마지막 줄을 교체한다. 관통의 본체 타격은 **코어를 맞춘 발에만** 생기므로 그 확률만큼 가중된다:

```python
        # 코어를 놓친 발은 본체에 맞고 그대로 나가므로 뚫고 나갈 코어가 없다.
        # 그래서 본체 인스턴스는 코어를 맞춘 비율만큼만 존재한다.
        return ([instance(True), instance(False, weight=share)] if pierces
                else [instance(hits_core)])
```

- [ ] **Step 6: Run the tests**

Run: `cd backend && python -m pytest tests/test_core_hit_rate.py -q`
Expected: PASS

Run: `cd backend && python -m pytest -q`
Expected: PASS — **기존 테스트가 하나라도 깨지면 opt-in 계약이 깨진 것이다.** `core_diameter_px=None`에서 `share`는 항상 1.0이므로 모든 경로가 기존과 같은 값을 내야 한다.

- [ ] **Step 7: Verify the opt-in contract against a real deck**

Run: `cd backend && python -m pytest tests/test_deck_search.py tests/test_raid_simulator.py -q`
Expected: PASS

그리고 실기록 캘리브레이션이 안 움직였는지 확인:

Run: `python scripts/measure_record_calibration.py`
Expected: 합계 **1.047x · 19/25** — `RECORD_BOSS`에 `core_diameter_px`가 없으므로 한 자리도 안 움직여야 한다. 움직였다면 기본값이 중립이 아니다.

- [ ] **Step 8: Commit**

```bash
git add backend/app/raid_simulator.py backend/tests/test_core_hit_rate.py
git commit -m "A core hit is a probability the weapon's spread decides

hit_rate finally has a consumer: it narrows the spread, the spread against
the core's diameter gives the share of rounds that land on it, and the
formula averages over that share. Fifteen slugs had been recording the stat
into a registry nobody read.

Pierce's body instance is weighted by the same share - a round that missed
the core has no core to pass through, so there is nothing behind it to hit."
```

---

### Task 5: 무기 탄착군 상수를 데이터와 대조하는 감사

`WEAPON_SPREAD_DIAMETER`는 손으로 유지되는 표다. 이 저장소에서 손으로 유지되는 목록은 조용히 낡은 전례가 있다.

**Files:**
- Create: `scripts/audit_weapon_accuracy_scales.py`

**Interfaces:**
- Consumes: Task 1의 `WEAPON_SPREAD_DIAMETER`.
- Produces: 없음(CLI).

- [ ] **Step 1: Write the script**

`scripts/audit_weapon_accuracy_scales.py`:

```python
"""`accuracy.WEAPON_SPREAD_DIAMETER`를 수집 데이터와 대조한다.

언제 쓰나: 로스터를 재동기화한 뒤, 새 니케를 온보딩한 뒤, 그리고 탄착군이
관련된 값을 만지기 전에. 표는 손으로 적혀 있고 데이터는 갱신되므로 둘이
갈라지는 날이 온다.

무엇을 보나: `data/shiftypad/raw/*.json`의 `shot_detail`에서 무기 클래스별
`start_accuracy_circle_scale`(MG는 `end_accuracy_circle_scale`)을 모아,
클래스 안에서 균일한지와 표의 값과 같은지를 본다. 어긋나면 exit 1.

MG를 다르게 보는 이유는 그것만 탄창 안에서 좁아지기 때문이다
(start 250 -> end 10, 발당 -7). 엔진은 수렴값만 모델한다.
"""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.accuracy import WEAPON_SPREAD_DIAMETER  # noqa: E402

# MG는 탄창 안에서 좁아지므로 표가 담은 것은 수렴값(`end`)이다.
CONVERGING_WEAPONS = {"MG"}


def _shot_detail(node):
    """이 JSON 어딘가에 있는 무기 shot 레코드, 없으면 None."""
    if isinstance(node, dict):
        if "weapon_type" in node and "start_accuracy_circle_scale" in node:
            return node
        for value in node.values():
            found = _shot_detail(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _shot_detail(value)
            if found is not None:
                return found
    return None


def collect(raw_dir):
    """{무기: {지름: [파일명, ...]}} - 클래스별로 관측된 지름과 그 출처."""
    observed = collections.defaultdict(lambda: collections.defaultdict(list))
    for path in sorted(raw_dir.glob("*.json")):
        detail = _shot_detail(json.loads(path.read_text(encoding="utf-8")))
        if detail is None:
            continue
        weapon = detail["weapon_type"]
        field = ("end_accuracy_circle_scale" if weapon in CONVERGING_WEAPONS
                 else "start_accuracy_circle_scale")
        observed[weapon][float(detail[field])].append(path.stem)
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=pathlib.Path,
                        default=pathlib.Path("data/shiftypad/raw"),
                        help="수집된 ShiftyPad raw 번들 디렉터리")
    args = parser.parse_args()

    if not args.raw_dir.is_dir():
        print(f"수집 데이터가 없다: {args.raw_dir}", file=sys.stderr)
        return 1

    observed = collect(args.raw_dir)
    if not observed:
        print(f"{args.raw_dir}에서 shot_detail을 하나도 못 읽었다", file=sys.stderr)
        return 1

    problems = []
    for weapon in sorted(observed):
        diameters = observed[weapon]
        expected = WEAPON_SPREAD_DIAMETER.get(weapon)
        units = sum(len(v) for v in diameters.values())
        print(f"{weapon:4} {units:3}유닛  관측 {sorted(diameters)}  표 {expected}")
        if expected is None:
            problems.append(f"{weapon}: 표에 없는 무기 클래스가 데이터에 있다")
            continue
        if len(diameters) > 1:
            spread = {d: sorted(u)[:3] for d, u in diameters.items()}
            problems.append(f"{weapon}: 클래스 안에서 지름이 갈린다 - {spread}")
            continue
        only = next(iter(diameters))
        if only != expected:
            problems.append(f"{weapon}: 데이터는 {only}인데 표는 {expected}")

    for weapon in sorted(set(WEAPON_SPREAD_DIAMETER) - set(observed)):
        print(f"{weapon:4}   0유닛  (수집 데이터에 없음 - 표만 존재)")

    if problems:
        print("\n어긋남:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\naccuracy.WEAPON_SPREAD_DIAMETER는 수집 데이터와 일치한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it — it must pass on today's data**

Run: `python scripts/audit_weapon_accuracy_scales.py`
Expected: 무기 6종 중 데이터에 있는 것들이 표와 일치하고 exit 0. 출력에 AR 18유닛/SG 11/SMG 7/MG 12/SR 15/RL 14가 보여야 한다.

- [ ] **Step 3: Prove the audit actually catches a drift**

`backend/app/accuracy.py`의 `"AR": 75.0`을 잠시 `76.0`으로 바꾸고:

Run: `python scripts/audit_weapon_accuracy_scales.py; echo "exit=$?"`
Expected: `AR: 데이터는 75.0인데 표는 76.0`이 찍히고 `exit=1`.

**되돌릴 것** — 75.0으로 복원한 뒤 다시 돌려 exit 0을 확인한다. 이 저장소에는 "테스트가 잡는다고 적은 것이 실제로는 안 잡혔다"는 전례가 있으므로 이 단계를 건너뛰지 않는다.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit_weapon_accuracy_scales.py
git commit -m "Audit the spread table against the data it was copied from

WEAPON_SPREAD_DIAMETER is maintained by hand while the collected data keeps
moving, and hand-maintained lists in this repo have gone stale quietly
before. Verified by breaking AR on purpose and watching it exit 1."
```

---

### Task 6: 명중률 오버로드를 수집한다

`hit_rate`에 소비자가 생겼으므로 수집기가 그것을 버릴 이유가 사라졌다.

**Files:**
- Modify: `tools/collect-blablalink/parse.js:34-42` (`OVERLOAD_LABEL_TO_NAME`), `:44-46` (주석)
- Modify: `tools/collect-blablalink/parse.test.js:28-43`
- Modify: `backend/app/overload_effects.py:15-23` (`NAME_TO_STAT`)
- Test: `backend/tests/test_overload_effects.py`

**Interfaces:**
- Consumes: Task 4의 `hit_rate` 소비.
- Produces: `NAME_TO_STAT["명중률 증가"] == "hit_rate"`.

- [ ] **Step 1: Write the failing tests**

`tools/collect-blablalink/parse.test.js`의 `parseOverload` 테스트에서 **드롭을 못박은 단언을 뒤집는다.** 36-40행을 교체:

```js
  // Moran confirms Charge Speed. Hit Rate is now mapped; DEF still drops
  // (the engine consumes enemy DEF only, so an ally DEF stat would be inert).
  const moran = parseOverload(doc('moran'))
  assert.ok(moran.some((o) => o.name === '차지 속도 증가' && o.value === 4.92))
  assert.ok(moran.some((o) => o.name === '크리티컬 대미지 증가' && o.value === 16.44))
  assert.ok(moran.some((o) => o.name === '명중률 증가' && o.value === 17.99))
  assert.ok(!moran.some((o) => /DEF|방어/.test(o.name)))
  // Three more fixtures carry a Hit Rate row, at three different totals.
  const hitRate = (slug) =>
    parseOverload(doc(slug)).find((o) => o.name === '명중률 증가')?.value
  assert.equal(hitRate('blanc'), 23.62)
  assert.equal(hitRate('liter'), 11.81)
  assert.equal(hitRate('maxwell'), 7.59)
```

`backend/tests/test_overload_effects.py`에 추가(임포트는 이 파일이 이미 갖고 있다 — `from app.models import OverloadOption`, `from app.overload_effects import overload_options_to_effects`. 값 비교도 이 파일 관행대로 `round(x, 4)`를 쓴다):

```python
def test_hit_rate_overload_maps_to_the_hit_rate_stat():
    # Moran's fixture total. The engine reads hit_rate to size the bullet
    # spread, so this line is what makes an overload roll reach core hits.
    effects = overload_options_to_effects(
        [OverloadOption(name="명중률 증가", value=17.99)], source_slug="moran"
    )
    assert len(effects) == 1
    assert effects[0].stat == "hit_rate"
    assert round(effects[0].value, 4) == 0.1799
    assert effects[0].scope == "self"
    assert effects[0].duration is None
```

- [ ] **Step 2: Run both suites to verify they fail**

Run: `cd tools/collect-blablalink && npm test`
Expected: FAIL — `명중률 증가` 행이 없다.

Run: `cd backend && python -m pytest tests/test_overload_effects.py -q`
Expected: FAIL — `ValueError: unknown overload option: 명중률 증가`

- [ ] **Step 3: Map the label**

`tools/collect-blablalink/parse.js`의 `OVERLOAD_LABEL_TO_NAME`에 추가:

```js
  'Increase Hit Rate': '명중률 증가',
```

같은 파일 46행의 주석을 고친다:

```js
// each row text is "<English label><NN.NN>%". Unmapped labels (DEF) drop.
```

`backend/app/overload_effects.py`의 `NAME_TO_STAT`에 추가:

```python
    "명중률 증가": "hit_rate",
```

같은 파일 상단 독스트링의 "no consumer yet" 목록에서 명중은 제외돼 있어야 한다(애초에 없었다) — 손댈 것 없음.

- [ ] **Step 4: Run both suites**

Run: `cd tools/collect-blablalink && npm test`
Expected: PASS

Run: `cd backend && python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/collect-blablalink/parse.js tools/collect-blablalink/parse.test.js backend/app/overload_effects.py backend/tests/test_overload_effects.py
git commit -m "Collect the hit rate overload we had been dropping on purpose

The label was dropped because the engine had no consumer for it, and the
comment on line 46 said so by name. Now there is one. Four fixtures already
carried the row, and a test had been pinning the fact that it was thrown
away - so the change is mostly that assertion turning around.

DEF keeps dropping: the engine consumes enemy DEF, never an ally's."
```

---

### Task 7: 문서 갱신

**Files:**
- Modify: `docs/engine-gaps.md` · `docs/encoded-nikkes.md` · `docs/decisions.md` · `docs/insights.md` · `docs/roadmap.md` · `tools/collect-blablalink/RECIPE.md`

- [ ] **Step 1: Record the decisions and insights**

`/document` 커맨드(docs-keeper 서브에이전트)에 다음을 넘긴다:

- **결정:** 균등 원판 분포 채택, 가우시안 기각. 근거는 오차가 아니라 **역산된 코어 크기의 산포**(균등 51.1px ± 6.1% vs 가우시안 ± 21.0%)이고, 가우시안은 D = C에서 100%에 닿지 못하는데 실측은 닿는다.
- **결정:** `core_diameter_px` 기본값 `None`(opt-in). 50px를 실기록에 켜면 SMG 1.145x → 0.69x · AR 1.116x → 0.81x로 과대가 과소로 뒤집히고, engine-gap #21이 세운 "상한 모델" 해석이 무너진다.
- **인사이트:** 세 무기 회귀식이 **110%에서 하나로 만난다**. 무기별 상수는 기본 지름뿐이다.
- **인사이트:** 실제 코어히트율은 **두 항의 곱**이다 — `p_조준`(플레이 조건·좌석별, gap #21이 다룬 것) × `p_탄착`(무기·명중·결정론, 이 작업). 둘은 직교하므로 gap #21의 결론은 살아 있다.
- **인사이트:** **수집 단계에서 버린 데이터는 "게임에 없다"로 오독된다.** 오버로드 7종을 보고 "게임에 명중 오버로드가 없다"고 결론냈으나 실제로는 `parse.js`가 라벨 미등록으로 버리고 있었고, 그 사실이 같은 파일 주석에 이름까지 적혀 있었다. 데이터 부재를 결론 삼기 전에 수집 경로의 필터부터 볼 것.

- [ ] **Step 2: Update the gap inventory and the encoded-nikke table**

`docs/engine-gaps.md`:
- `hit_rate` inert 갭을 **해소**로 적는다. 소비자는 `accuracy.core_hit_rate`.
- **새 갭:** MG 정확도 예열(탄창 앞 29발, start 250 → end 10, 발당 −7). 막는 것은 MG 평타의 탄창 초반 코어 손실이고, 필요한 배선은 탄창 내 발 인덱스가 데미지 이벤트까지 흐르는 것.
- **새 갭:** `core_damage_rate`가 유닛별로 다르다 — 미란다 · 퀀시: 이스케이프 퀸 · 리틀 머메이드 · 치사토가 25000(2.5배)인데 엔진은 `CORE_HIT_BONUS = 1.0`(2.0배)을 전원에게 쓴다. 이 넷은 코어 보너스가 **과소**다.

`docs/encoded-nikkes.md` — 15슬러그의 Hit Rate 보류 문구를 갱신하되 **두 부류를 구분**한다:
- **해소(11):** dorothy-serendipity · jill-valentine · phantom · chisato-nishikigi · miranda · quency-escape-queen · nayuta · soda-twinkling-bunny · sugar · drake · noir
- **여전히 inert, 그러나 사유가 바뀜(4):** diesel-winter-sweets · mast-romantic-maid · modernia · anchor-innocent-maid — RL/MG라 기본 탄착군 10px가 이미 코어 안이다. 「엔진이 안 읽는다」가 아니라 「명중이 바꿀 것이 없다」. **단 디젤의 −100%는 아군 대상이므로 SG/SMG/AR 아군에게는 무해하지 않다** — 그쪽은 이제 실제로 모델된다.

- [ ] **Step 3: Update the roadmap and the collector recipe**

`docs/roadmap.md` — To-Do 반영. **로스터 재동기화가 필요한 변경**임을 명시한다(차지속도 `lines` 신설과 같은 성격). 재동기화 전까지 기존 로스터에는 명중 오버로드 값이 없다.

`tools/collect-blablalink/RECIPE.md` — 명중 행이 이제 수집된다는 것과, 드롭되는 라벨이 DEF만 남았다는 것.

- [ ] **Step 4: Commit**

```bash
git add docs/ tools/collect-blablalink/RECIPE.md
git commit -m "Document the accuracy model and the two gaps it opened"
```

---

## Fienn 게이트 — 여기서 멈추고 재동기화를 요청한다

Task 6까지 착륙하면 **HTML 경로는 동작하지만 기존 로스터에는 명중 값이 없다.** 다음은 사람이 해야 한다:

1. **Fienn이 로스터를 재동기화한다.**
2. 재동기화된 드래프트에 `명중률 증가` 줄이 실제로 들어왔는지 확인한다.
3. 같은 유닛의 `{slot}_equip_option{n}_id`와 HTML 합계를 대조해 **명중의 효과 타입 번호와 값 곡선을 fit**한다. 이 단계가 `base_stat_folded = [6, 13]`의 정체를 확정한다.
4. 그 결과로 `data/nikke-stat-tables/tables.json`의 `overload.values` / `type_name`을 채우고 `base_stat_folded`를 교정한다.

**픽스처가 준 힌트(추론이지 확정이 아니다):** 네 값 23.62 · 17.99 · 11.81 · 7.59가 전부 타입 8/9의 곡선(lv1 = 4.77, 등차 0.704, lv15 = 14.63)에 앉는다 — 11.81 = lv11, 7.59 = lv5, 23.62 = lv11 두 줄. 같은 페이지의 DEF(6.88 = lv4, 11.81 = lv11)도 그렇다. **합계는 여러 (레벨, 줄 수) 조합으로 분해되므로 HTML만으로는 갈리지 않는다** — 17.99가 그 예다. 이 힌트로 곡선을 채워 넣지 말고, fit이 확인하면 그때 적는다.

한 점만 관측되면 곡선을 못 만든다. 그 경우 API 경로는 기존 warning 후 드롭을 유지한다(`known_effect_type`이 이미 그렇게 설계돼 있다).

---

## 착륙 후 측정 (선택)

이 계획은 실기록 캘리브레이션을 **의도적으로 안 건드린다**(`RECORD_BOSS`에 `core_diameter_px`가 없다). 모델이 실기록을 어떻게 움직이는지 보려면:

Run: `python scripts/measure_engine_change_delta.py`를 `core_diameter_px`를 준 보스로 한 번, 안 준 보스로 한 번.

예상: SG · SMG · AR만 움직이고 MG · SR · RL은 바이트 불변. 50px에서는 SMG · AR이 과소로 넘어간다(설계 문서 §7). **이 숫자를 캘리브레이션 회귀로 읽지 말 것** — 실기록 보스의 코어 크기가 50px이라는 근거는 없다.
