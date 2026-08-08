# 유닛별 코어 대미지 배율 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 코어 히트 한 발의 배율을 전원 공통 2.0배에서 유닛별 상수로 바꾼다 — 미란다·퀀시: 이스케이프 퀸·리틀 머메이드·치사토 니시키기(그리고 미란다 애장품 빌드)는 2.5배다.

**Architecture:** 게임 데이터의 `shot_detail.core_damage_rate`(만분율)를 슬러그별 표로 코드에 두고 `core_hit_bonus_for(slug) = rate/10000 - 1`로 환산한다. 엔진 소비 지점은 `raid_simulator._damage_instance` 한 줄. 표가 낡는 것은 `data/shiftypad/raw/*.json`과 대조하는 감사 스크립트가 막는다.

**Tech Stack:** Python 3.14, pytest. 백엔드 전용 — 프론트엔드 변경 없음.

## Global Constraints

- **설계문서:** `docs/superpowers/specs/2026-08-08-per-unit-core-damage-rate-design.md`. 이 계획과 어긋나면 설계문서가 맞다.
- **테스트는 반드시 `backend/`에서 돌린다.** 저장소 루트에서는 `No module named 'app'`으로 수집이 깨진다.
- **기준선: 2145 passed / 3 skipped** (이 워크트리에서 2026-08-08 확인). 모든 태스크 끝에 이 수 이상이어야 한다.
- **`data/`와 `tools/`는 gitignore다.** 수집 데이터에 의존하는 것은 테스트가 아니라 스크립트로 만든다. `data/`가 이 워크트리에 있는지 확인하려면 `python3 scripts/sync_worktree_data.py`(이미 동기화됨: dotgg 71 / shiftypad 13 / raw 83).
- **환산은 코드 한 곳에만 있다:** `core_hit_bonus_for`. 다른 파일에서 `/10000 - 1`을 다시 쓰지 않는다.
- **테스트는 비율이 아니라 값을 박는다.** "1.25배"라고 적으면 두 상수가 함께 움직여도 통과한다 — `test_core_hit_rate.py`의 관례.
- **주석은 WHAT과 WHY만.** "예전엔 CORE_HIT_BONUS였다" 같은 변경 이력을 코드에 남기지 않는다.
- 커밋 메시지는 한국어, 기존 로그와 같은 어조(명령형 서술).

---

### Task 1: `core_damage` 모듈 — 표와 환산

**Files:**
- Create: `backend/app/core_damage.py`
- Test: `backend/tests/test_core_damage.py`

**Interfaces:**
- Consumes: 없음 (이 태스크가 사슬의 시작)
- Produces:
  - `DEFAULT_CORE_DAMAGE_RATE: int = 20000`
  - `CORE_DAMAGE_RATE: dict[str, int]` — 슬러그 → 만분율
  - `core_hit_bonus_for(slug: str) -> float` — major modifier에 더할 값 (기본 1.0)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_core_damage.py`:

```python
"""유닛별 코어 대미지 배율 — 표가 수집 데이터와 맞는가.

`data/`는 gitignore라 101슬러그 전수 대조는 감사 스크립트
(`scripts/audit_core_damage_rate.py`)가 한다. 여기서는 추적되는 픽스처로
양쪽 방향을 박는다: 표에 있는 유닛은 그 값이 맞고, 표에 없는 유닛은 기본값이
맞다. 한쪽만 박으면 표가 통째로 비어도 절반은 통과한다.
"""
import json
from pathlib import Path

from app.core_damage import (
    CORE_DAMAGE_RATE,
    DEFAULT_CORE_DAMAGE_RATE,
    core_hit_bonus_for,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"


def _collected_rate(slug):
    """이 유닛의 raw 번들이 적은 core_damage_rate."""
    bundle = json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))
    return bundle["detail"]["shot_detail"]["core_damage_rate"]


def test_the_table_carries_the_collected_rate_for_a_25000_unit():
    assert _collected_rate("miranda") == 25000
    assert CORE_DAMAGE_RATE["miranda"] == 25000


def test_a_unit_absent_from_the_table_is_20000_in_the_data():
    assert _collected_rate("julia") == DEFAULT_CORE_DAMAGE_RATE
    assert "julia" not in CORE_DAMAGE_RATE


def test_the_rate_converts_to_the_major_modifier_term():
    # 25000 = 250% = 1 + 1.5, 20000 = 200% = 1 + 1.0
    assert core_hit_bonus_for("miranda") == 1.5
    assert core_hit_bonus_for("julia") == 1.0


def test_an_unknown_slug_gets_the_default():
    assert core_hit_bonus_for("no-such-nikke") == 1.0


def test_the_favorite_item_build_shares_the_base_units_weapon_rate():
    # 애장품 빌드는 load_weapon_data가 base 유닛의 무기 파일을 읽으므로 같은
    # 무기이고, 따라서 같은 배율이다.
    assert CORE_DAMAGE_RATE["miranda-signature"] == CORE_DAMAGE_RATE["miranda"]
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_core_damage.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core_damage'`

- [ ] **Step 3: 모듈을 만든다**

`backend/app/core_damage.py`:

```python
"""코어 히트 한 발이 몇 배를 때리는가 — 유닛별 상수.

게임 데이터의 `shot_detail.core_damage_rate`가 이 값이고, 같은 `shot_detail`의
원문이 뜻을 적어 준다: "Deals {core_damage_rate}% damage when attacking core."
만분율이라 20000은 200% = 2.0배다. 엔진의 major modifier는 가산 버킷이라
`1 + 1.0 = 2.0`이 되므로 더할 값은 `rate/10000 - 1`이다.

**무기 클래스에서 유도할 수 없다.** SMG 7유닛이 3(20000)/4(25000)로 갈린다 —
나유타·볼륨·리타는 2.0배, 아래 넷은 2.5배다. `accuracy.WEAPON_SPREAD_DIAMETER`가
클래스 내 분산 0이라 클래스별 표로 끝나는 것과 갈리는 지점이다.

**수집 데이터를 타고 오지 못하는 이유:** 이 값이 있는 곳은 ShiftyPad raw뿐인데
(`data/shiftypad/raw/*.json`), 그 파일은 rid로 키가 잡혀 있고 슬러그 매핑은
데이터가 아니라 사람이 준다. 로더가 읽는 dotgg 파일에는 필드 자체가 없고,
인코딩 101슬러그 중 83개가 무기를 dotgg에서 읽는다 — 아래 다섯도 전부 그쪽이다.

그래서 표는 손으로 적고, 낡는 것은 `scripts/audit_core_damage_rate.py`가
수집 데이터와 대조해 막는다.
"""

# 200% = 2.0배. 오늘 수집된 83유닛 중 79유닛이 이 값이다.
DEFAULT_CORE_DAMAGE_RATE = 20000

# 250%인 유닛들. 미란다 애장품 빌드는 base의 무기 파일을 읽으므로 같이 오른다.
CORE_DAMAGE_RATE = {
    "miranda": 25000,
    "miranda-signature": 25000,
    "quency-escape-queen": 25000,
    "little-mermaid": 25000,
    "chisato-nishikigi": 25000,
}


def core_hit_bonus_for(slug):
    """이 유닛의 코어 히트가 major modifier에 더하는 값."""
    return CORE_DAMAGE_RATE.get(slug, DEFAULT_CORE_DAMAGE_RATE) / 10000 - 1
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_core_damage.py -q`
Expected: PASS — 5 passed

- [ ] **Step 5: 커밋한다**

```bash
git add backend/app/core_damage.py backend/tests/test_core_damage.py
git commit -m "코어 대미지 배율은 유닛별이다 — 표와 환산"
```

---

### Task 2: 엔진 배선 — `CORE_HIT_BONUS`를 `core_hit_bonus_for`로

`CORE_HIT_BONUS`를 참조하는 곳 **전부**를 한 태스크에서 옮긴다. 상수만 지우고 소비자를 남기면 `measure_normal_attack_residual.py`가 깨진 채로 브랜치에 남는다.

**Files:**
- Modify: `backend/app/raid_simulator.py:106-118`(import·상수), `:907`(소비 지점)
- Modify: `backend/tests/test_raid_simulator.py:4`, `:3386`, `:3389`
- Modify: `backend/tests/test_core_hit_rate.py:1-6`(독스트링), `backend/tests/test_core_pierce_hits_body.py:8`(독스트링), `backend/tests/test_core_strike_damage.py:44`(주석)
- Modify: `backend/app/skill_rules/cinderella_crystal_wave.py:104`(주석)
- Modify: `scripts/measure_normal_attack_residual.py:18`, `:36`, `:72-78`, `:121-126`
- Modify: `scripts/raid_record.py:28`
- Test: `backend/tests/test_core_damage.py` (Task 1이 만든 파일에 이어 쓴다)

**Interfaces:**
- Consumes: `app.core_damage.core_hit_bonus_for(slug) -> float` (Task 1)
- Produces: `raid_simulator`가 `core_hit_bonus_for`를 **모듈 이름으로** 들고 있다 — `raid_simulator.core_hit_bonus_for`를 patch하면 시뮬레이터가 그 patch를 본다. `measure_normal_attack_residual.py`가 이 성질에 기댄다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_core_damage.py` 끝에 이어 붙인다. 상단 import에 `from app.raid_simulator import simulate_raid`를 추가한다.

```python
# --- 엔진이 실제로 그 값을 쓰는가 ---
#
# ATK 10000 x 발당 100%, 적 DEF 0, 크리 0%, 풀버스트 창이 열리기 전에 전투가
# 끝나므로 한 발의 major modifier는 코어 보너스 하나뿐이다. 그래서 한 발은 곧
# 10000 x (1 + 보너스)이고, 값으로 박을 수 있다.
_WEAPON = {"weapon": "AR", "damage_percent": 100.0, "max_ammo": 999,
           "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0}


def _first_shot(striker_slug, *, core_hittable=True):
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": striker_slug, "burst_tier": 3, "element": "Iron",
         "cooldown": 20.0, "weapon": "AR"},
    ]
    log = simulate_raid(
        deck,
        {"b1": [], "b2": [], striker_slug: []},
        burst_damage_percents={striker_slug: 100.0},
        base_stats={s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in deck},
        enemy_def=0,
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={striker_slug: _WEAPON},
        core_hittable=core_hittable,
    )["damage_log"]
    return next(e["damage"] for e in log if e["source"] == "normal_attack")


def test_a_25000_unit_hits_the_core_for_more_than_a_20000_unit():
    assert _first_shot("miranda") == 25000.0      # 10000 x (1 + 1.5)
    assert _first_shot("julia") == 20000.0        # 10000 x (1 + 1.0)


def test_the_higher_rate_needs_a_core_to_land_on():
    # 코어가 없는 보스에서는 아무도 보너스를 받지 않는다 - 2.5배 유닛도 마찬가지다.
    assert _first_shot("miranda", core_hittable=False) == 10000.0
    assert _first_shot("julia", core_hittable=False) == 10000.0


def test_the_body_hit_behind_the_core_is_untouched_by_the_higher_rate():
    """관통 유닛의 발은 코어를 뚫고 본체에 또 맞는다 - 그 본체 인스턴스는
    코어 보너스를 받지 않으므로 2.5배 유닛이라도 그대로 10000이다."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "miranda", "burst_tier": 3, "element": "Iron",
         "cooldown": 20.0, "weapon": "AR"},
    ]
    log = simulate_raid(
        deck,
        {"b1": [], "b2": [],
         "miranda": [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]},
        burst_damage_percents={"miranda": 100.0},
        base_stats={s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in deck},
        enemy_def=0,
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={"miranda": _WEAPON},
        core_hittable=True,
        pierce_hits_body_behind_core=True,
    )["damage_log"]
    shots = [e["damage"] for e in log if e["source"] == "normal_attack"]
    # core 10000 x (1 + 1.5), body 10000 x 1
    assert shots[:2] == [25000.0, 10000.0]
```

상단 import에 `from app.skill_rules._helpers import buff_rule`도 추가한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_core_damage.py -q`
Expected: FAIL 2건 — `test_a_25000_unit_hits_the_core_for_more_than_a_20000_unit`에서 미란다가 `20000.0`으로, `test_the_body_hit_behind_the_core_is_untouched_by_the_higher_rate`에서 `[20000.0, 10000.0]`으로 나온다(엔진이 아직 전원 공통 상수를 쓴다). 나머지는 통과한다.

- [ ] **Step 3: 엔진을 배선한다**

`backend/app/raid_simulator.py` — import 블록(알파벳 순서라 `attack_rate` 앞)에 한 줄:

```python
from app.accuracy import WEAPON_SPREAD_DIAMETER, core_hit_rate
from app.attack_rate import CHARGE_WEAPONS, generate_segmented_shots
from app.burst_cycle import FULL_BURST_OPEN_DELAY, simulate_burst_cycle
from app.core_damage import core_hit_bonus_for
from app.damage_formula import calculate_damage
```

118행의 `CORE_HIT_BONUS = 1.0`을 **지운다**(`BASE_CRIT_RATE = 0.15`는 그대로).

907행:

```python
            core_hit_bonus=core_hit_bonus_for(slug) if hits_core else 0.0,
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_core_damage.py -q`
Expected: PASS — 8 passed

- [ ] **Step 5: `CORE_HIT_BONUS`를 읽던 테스트를 옮긴다**

`backend/tests/test_raid_simulator.py:4`:

```python
from app.core_damage import core_hit_bonus_for
from app.raid_simulator import simulate_raid
```

`:3386` 주석과 `:3389` 단언 — 이 테스트의 시전자 슬러그는 `"gunner"`(표에 없으므로 기본값):

```python
    # The tick lands inside a Full Burst window, so its bucket is 1 + 0.5
    # without a core hit and 1 + 0.5 + the caster's core bonus with one - core
    # sits in the SAME additive bucket as the Full Burst bonus, it does not
    # multiply it.
    assert tick(plain)["damage"] == pytest.approx(1000.0 * 1.5)
    assert tick(opted)["damage"] == pytest.approx(
        1000.0 * (1.5 + core_hit_bonus_for("gunner")))
```

- [ ] **Step 6: 남은 주석·독스트링의 이름을 맞춘다**

이 네 곳은 사라진 심볼 이름을 부르고 있다. 뜻은 그대로 두고 이름만 고친다.

`backend/tests/test_core_hit_rate.py` 독스트링 3-5행:

```
숫자를 비율이 아니라 값으로 박는다. ATK 10000 x 발당 100%에 다른 major
modifier가 없으므로 한 발은 곧 10000 x (1 + p x 시전자의 코어 보너스)이고,
"1.44배"라고만 적으면 그 보너스가 움직여도 테스트가 계속 통과한다.
```

`backend/tests/test_core_pierce_hits_body.py` 독스트링 5-9행:

```
The body hit is the same instance minus the core bonus (Fienn, 2026-08-03), so
with no other major modifiers the pair reads (1 + 1.0) + 1 = 3.0 against the core
hit's 2.0. The numbers below are pinned rather than expressed as "1.5x": that
ratio is only true at this unit's core bonus of 1.0 (`core_damage.py`), and a
test that hides the constant would keep passing if the constant moved.
```

`backend/tests/test_core_strike_damage.py:44`:

```python
    # This caster's core bonus is 1.0, so the core bonus doubles an otherwise
    # bare hit.
```

`backend/app/skill_rules/cinderella_crystal_wave.py:104`:

```python
        # model (core_damage.core_hit_bonus_for, no per-enemy distinction), so
        # gating the whole
```

- [ ] **Step 7: 측정 스크립트의 patch 지점을 옮긴다**

`scripts/measure_normal_attack_residual.py`는 코어 항을 0으로 눌러 잔차를 재려고 `raid_simulator.CORE_HIT_BONUS`를 monkey-patch했다. 이제 시뮬레이터는 슬러그를 보고 값을 정하므로, 누를 대상은 시뮬레이터가 부르는 **함수**다.

`:72-78`:

```python
def _run_decks(by_slug, zero_core):
    """Every recorded deck, seated as played, with the core term on or off.

    The core bonus is per-unit (`core_damage.core_hit_bonus_for`) and reaches
    the simulator as a module-level name, so zeroing it means swapping that
    name for the duration of the run. The caller restores it.
    """
    if zero_core:
        raid_simulator.core_hit_bonus_for = lambda slug: 0.0
```

`:121-126`:

```python
    live = raid_simulator.core_hit_bonus_for
    try:
        with_core, weapons = _run_decks(by_slug, zero_core=False)
        without_core, _ = _run_decks(by_slug, zero_core=True)
    finally:
        raid_simulator.core_hit_bonus_for = live
```

`:18`과 `:36`의 독스트링에서 `CORE_HIT_BONUS`를 `core_hit_bonus_for`로 바꾼다. `:36`의 문장("...is why nothing here proposes changing CORE_HIT_BONUS")은 뜻이 그대로 성립하므로 이름만 바꾼다.

`scripts/raid_record.py:27-28`:

```
The engine has no core hit rate: every core-eligible shot hits the core
(`core_damage.core_hit_bonus_for`), which is the CEILING of that run, not the run.
```

- [ ] **Step 8: 사라진 이름이 남아 있지 않은지 확인한다**

Run: `grep -rn "CORE_HIT_BONUS" --include="*.py" backend/ scripts/ | grep -v __pycache__`
Expected: 출력 없음

- [ ] **Step 9: 전수 테스트**

Run: `cd backend && python -m pytest -q`
Expected: `2153 passed, 3 skipped` (기준선 2145 + Task 1의 5 + Task 2의 3)

실패가 하나라도 나오면 **멈추고 원인을 찾는다.** 이 변경으로 값이 움직이는 테스트가 있다면 그것은 회귀가 아니라 **2.5배 유닛의 딜을 기존에 박아 둔 테스트**일 수 있다 — 어느 쪽인지 확인한 뒤에 고친다.

- [ ] **Step 10: 커밋한다**

```bash
git add -u
git commit -m "코어 보너스는 시전자가 정한다 — 소비 지점을 유닛별 조회로"
```

---

### Task 3: 감사 스크립트 — 표가 수집 데이터와 갈라지면 잡는다

**Files:**
- Create: `scripts/audit_core_damage_rate.py`

**Interfaces:**
- Consumes: `app.core_damage.{CORE_DAMAGE_RATE, DEFAULT_CORE_DAMAGE_RATE}` (Task 1), `app.skill_rules.registry.{ENCODED_SLUGS, get_skill_value_manifest}`, `app.skill_values.load_character_data`
- Produces: exit 0(일치) / exit 1(어긋남). 다른 코드가 import하지 않는다.

- [ ] **Step 1: 스크립트를 쓴다**

`scripts/audit_core_damage_rate.py`:

```python
"""`core_damage.CORE_DAMAGE_RATE`를 수집 데이터와 대조한다.

언제 쓰나: 로스터를 재동기화한 뒤, 새 니케를 온보딩한 뒤, 그리고 코어 관련
값을 만지기 전에. 표는 손으로 적혀 있고 데이터는 갱신되므로 둘이 갈라지는 날이
온다.

무엇을 보나: `data/shiftypad/raw/*.json`의 `shot_detail.core_damage_rate`를
인코딩된 슬러그마다 찾아 표와 대조한다. raw 번들은 rid로 키가 잡혀 있어
슬러그가 없으므로, 캐릭터 데이터의 영문 이름으로 잇는다.

이름이 안 풀리는 슬러그는 **통과가 아니라 실패다.** 매칭이 조용히 비면 감사가
아무것도 안 보고 초록을 낸다.

테스트가 아니라 스크립트인 이유: `data/`는 gitignore라 워크트리나 CI에서 없을
수 있고, 조건부 테스트로 만들면 데이터가 없는 곳에서 조용히 skip된다.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.core_damage import CORE_DAMAGE_RATE, DEFAULT_CORE_DAMAGE_RATE  # noqa: E402
from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest  # noqa: E402
from app.skill_values import load_character_data  # noqa: E402

# 콜라보 유닛은 raw 쪽 이름이 짧다. 우리 슬러그가 쓰는 성까지 붙은 이름과 이어야
# 한다 - 이 일곱만 예외이고, 나머지는 영문 이름이 그대로 일치한다.
RAW_NAME_ALIASES = {
    "ada-wong": "Ada",
    "asuka-shikinami-langley-wille": "Asuka: WILLE",
    "chisato-nishikigi": "Chisato",
    "jill-valentine": "Jill",
    "rei-ayanami": "Rei",
    "rei-ayanami-tentative-name": "Rei (Tentative Name)",
    "takina-inoue": "Takina",
}


def collect(raw_dir):
    """{영문 이름: (rid, core_damage_rate)} - 수집된 번들이 적은 배율."""
    observed = {}
    for path in sorted(raw_dir.glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        name = bundle["directory"]["name_localkey"]["name"].strip()
        observed[name] = (path.stem, bundle["detail"]["shot_detail"]["core_damage_rate"])
    return observed


def character_name(slug):
    """이 슬러그의 영문 캐릭터 이름, 못 찾으면 None.

    ShiftyPad 소스의 정규화 파일에는 `name`이 없으므로 lootandwaifus로 떨어진다.
    """
    manifest = get_skill_value_manifest(slug) or {}
    data_slug = manifest.get("data_slug", slug)
    for source in (manifest.get("source"), "lootandwaifus"):
        if source is None:
            continue
        try:
            data = load_character_data(source, data_slug)
        except (FileNotFoundError, KeyError):
            continue
        if data.get("name"):
            return data["name"].strip()
    return None


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
        print(f"{args.raw_dir}에서 번들을 하나도 못 읽었다", file=sys.stderr)
        return 1

    problems, checked, differing = [], 0, []
    for slug in sorted(ENCODED_SLUGS):
        name = RAW_NAME_ALIASES.get(slug) or character_name(slug)
        if name is None:
            problems.append(f"{slug}: 캐릭터 이름을 못 읽었다")
            continue
        if name not in observed:
            problems.append(f"{slug}: raw에 {name!r}가 없다")
            continue
        rid, rate = observed[name]
        expected = CORE_DAMAGE_RATE.get(slug, DEFAULT_CORE_DAMAGE_RATE)
        checked += 1
        if rate != expected:
            problems.append(
                f"{slug}: 데이터는 {rate}(rid {rid})인데 표는 {expected}")
        if rate != DEFAULT_CORE_DAMAGE_RATE:
            differing.append(f"{slug} {rate} (rid {rid})")

    print(f"{checked}/{len(ENCODED_SLUGS)}슬러그 대조, 기본값 {DEFAULT_CORE_DAMAGE_RATE}")
    for line in differing:
        print(f"  {line}")

    for slug in sorted(set(CORE_DAMAGE_RATE) - ENCODED_SLUGS):
        print(f"  (표에만 있고 인코딩 안 된 슬러그: {slug})")

    if problems:
        print("\n어긋남:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\ncore_damage.CORE_DAMAGE_RATE는 수집 데이터와 일치한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 초록을 확인한다**

Run: `python3 scripts/audit_core_damage_rate.py`
Expected: exit 0. `101/101슬러그 대조`, 그 아래 2.5배 5줄(`chisato-nishikigi` / `little-mermaid` / `miranda` / `miranda-signature` / `quency-escape-queen`), 마지막 줄 "일치한다".

101에 못 미치면 이름 매칭이 샌 것이다 — 별칭 표를 고친다. **못 맞춘 채로 넘어가지 않는다.**

- [ ] **Step 3: 실제로 잡는지 확인한다**

표를 일부러 틀리게 만들어 exit 1이 나오는지 본다:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path("backend/app/core_damage.py")
p.write_text(p.read_text(encoding="utf-8").replace('"miranda": 25000', '"miranda": 20000'), encoding="utf-8")
PY
python3 scripts/audit_core_damage_rate.py; echo "exit=$?"
git checkout backend/app/core_damage.py
```

Expected: `miranda: 데이터는 25000(rid 32)인데 표는 20000`, `exit=1`. 되돌린 뒤 다시 돌리면 exit 0.

"테스트가 잡는다고 적은 것은 실제로 깨보고 확인할 것" — 이 저장소의 규칙이다.

- [ ] **Step 4: 커밋한다**

```bash
git add scripts/audit_core_damage_rate.py
git commit -m "코어 배율 표가 수집 데이터와 갈라지면 잡는다"
```

---

### Task 4: 영향과 캘리브레이션을 측정한다

코드 변경 없음. **숫자를 만들어 보고하는 태스크**다. 설계문서 §5가 "실제 수치는 구현 후 측정으로 보고한다"고 약속했다.

**Files:**
- Modify: (측정 결과가 요구하면) `scripts/raid_record.py`의 캘리브레이션 관련 독스트링 숫자

**Interfaces:**
- Consumes: Task 2가 배선한 엔진
- Produces: 보고할 숫자 — 덱 2 비율, 5덱 합산 비율, `little-mermaid` 개별 비율의 전/후

**변경 전 값은 이미 잡혀 있다** — 이 워크트리에서 엔진 변경 전에 재어
`calib-before.txt`(워크트리 루트, **untracked**)에 넣어 뒀다. 임시 워크트리는
필요 없다.

| | 변경 전 |
|---|---|
| combined | **1.055x** (25유닛) |
| ±15% 안 | **19/25** |
| deck2 | **1.121x** (record 7.743B) |
| `little-mermaid` | **1.081x** — sim이 record 2.087B보다 +0.168B |
| SMG 그룹 평균 | **1.148x** (n=3) |

- [ ] **Step 1: 변경 후 캘리브레이션을 잰다**

```bash
python3 scripts/measure_record_calibration.py > calib-after.txt 2>&1
diff calib-before.txt calib-after.txt
```

- [ ] **Step 2: 움직인 것과 안 움직인 것을 확인한다**

기대: `little-mermaid`(덱 2의 유일한 영향 좌석)만 오르고, 덱 2 비율과 5덱 합산이 따라 오른다. **나머지 24좌석은 한 자리도 움직이면 안 된다** — 움직였다면 표에 없는 슬러그가 값을 받았다는 뜻이므로 멈추고 원인을 찾는다.

- [ ] **Step 3: SMG 그룹을 따로 본다**

`little-mermaid`는 SMG 3유닛 중 하나이고, 그 그룹은 이미 평균 1.148x로 **가장 크게 과대 계상 중인 무기군**이다(`docs/engine-gaps.md`의 남은 최대 항). 이 변경은 그 평균을 **더 나쁘게** 만든다.

그 자체는 이 변경에 대한 반증이 아니다 — 코어 배율은 게임 데이터가 적어 준 값이고, 실기록의 코어 히트율이 1.0으로 고정된 이상 sim/record는 원래 상한이다. 하지만 **정보는 된다**: SMG 잔차가 「코어 보너스를 덜 주고 있어서」였다면 이 변경으로 줄었어야 하는데 늘어난다면, 그 가설은 죽는다. 새 SMG 평균을 적고 그 함의를 한 줄로 남긴다.

- [ ] **Step 4: 한 발의 크기를 확인한다**

설계문서 §5는 맨 인스턴스가 1.25배, 풀버스트·유효사거리·크리가 다 붙으면 1.174배라고 적었다. 실제 덱에서의 몫은 `diff`가 보여주는 `little-mermaid` 이동폭이다. 그 수를 그대로 보고한다.

- [ ] **Step 5: 측정 파일을 치운다**

```bash
rm calib-before.txt calib-after.txt
```

이 둘은 untracked 산출물이다. **`git add -A`를 쓰지 않는다** — 저장소에 들어가면 안 된다.

- [ ] **Step 6: 필요하면 기록된 숫자를 갱신하고 커밋한다**

`scripts/raid_record.py`나 `docs/measurements/`가 옛 비율을 문장으로 들고 있으면 새 수로 고친다. 고칠 게 없으면 이 스텝은 건너뛴다(빈 커밋을 만들지 않는다).

```bash
git add -u && git commit -m "실기록 캘리브레이션을 유닛별 코어 배율 뒤의 값으로 갱신"
```

---

### Task 5: 문서를 갱신한다

**Files:**
- Modify: `docs/engine-gaps.md`(139행 갭 항목 + 775행 요약 표)
- Modify: `docs/decisions.md`, `docs/insights.md` — **`/document` 명령(docs-keeper 서브에이전트)으로 갱신한다.** 직접 쓰지 않는다.

`docs/roadmap.md`에는 이 갭에 대응하는 To-Do 항목이 **없다**(확인함). 새로 만들지 않는다 — 착륙 기록은 `engine-gaps.md`가 갖는다.

- [ ] **Step 1: `engine-gaps.md`의 갭 항목을 해소로 옮긴다**

139행 제목을 `## 코어 보너스 배율이 유닛별로 다르다 — ✅ 착륙 (2026-08-08)`으로 바꾸고, 본문에 실제로 한 것을 적는다: `core_damage.CORE_DAMAGE_RATE`, 소비 지점은 `raid_simulator`의 한 줄, 감사는 `scripts/audit_core_damage_rate.py`.

**숫자를 4에서 5로 고친다** — `miranda-signature`가 빠져 있었다. 775행 요약 표의 해당 행도 같이.

- [ ] **Step 2: Task 4가 잰 캘리브레이션 이동을 적는다**

갭 항목 본문에 덱 2와 5덱 합산의 전/후를 적는다. "예상대로 올랐다"가 아니라 숫자로.

- [ ] **Step 3: `/document`로 결정과 인사이트를 넘긴다**

docs-keeper에 넘길 내용:

- **결정:** 수집 데이터에 값이 있는데도 표를 코드에 둔 판단. 근거는 dotgg 파일에 필드가 없고 인코딩 101슬러그 중 83개가 무기를 dotgg에서 읽는다는 것(영향 5슬러그 전부 포함). 대가로 감사 스크립트를 함께 만들었다.
- **결정:** 배율을 평타로 좁히지 않고 `hits_core`가 참인 모든 인스턴스에 걸기로 한 것(Fienn, 2026-08-08). 오늘은 결과가 같고, 정하는 것은 앞으로 인코딩될 유닛의 기본값이다.
- **인사이트:** 같은 무기 클래스 안에서 갈리는 스탯이 있다 — SMG가 3/4로 갈린다. `WEAPON_SPREAD_DIAMETER`처럼 클래스로 끝나는 표를 보고 유추하면 틀린다.
- **인사이트:** 애장품(`-signature`) 빌드는 base의 무기 파일을 읽으므로 무기에서 오는 상수를 같이 받는다. 무기 유래 표를 만들 때 base만 적으면 애장품 빌드가 조용히 기본값으로 떨어진다.
- **인사이트:** 측정 스크립트가 엔진 상수를 monkey-patch하고 있으면, 그 상수를 함수로 바꾸는 순간 patch가 무력화된다. 이번엔 읽는 줄이 먼저 AttributeError를 내 소리가 났지만, patch만 하고 읽지 않는 스크립트였다면 **에러 없이 틀린 숫자**가 나왔다.
- **인사이트(Task 4가 숫자를 낸 뒤에만):** SMG 잔차 1.148x에 대해 이 변경이 무엇을 말하는가. 코어 보너스를 덜 준 탓이라는 가설은 이 변경으로 **죽거나 살아난다** — Task 4 Step 3이 잰 새 SMG 평균을 근거로 한 줄 적는다.

- [ ] **Step 4: 전수 테스트와 커밋**

Run: `cd backend && python -m pytest -q`
Expected: `2153 passed, 3 skipped`

```bash
git add docs/
git commit -m "문서: 유닛별 코어 배율 착륙"
```

---

## 마무리

- [ ] `python3 scripts/audit_core_damage_rate.py` → exit 0
- [ ] `python3 scripts/audit_weapon_accuracy_scales.py` → exit 0 (같은 데이터를 읽는 이웃 감사가 안 깨졌는지)
- [ ] `cd backend && python -m pytest -q` → 2153 passed / 3 skipped
- [ ] `git status`에 `calib-*.txt`가 남아 있지 않다
- [ ] `grep -rn "CORE_HIT_BONUS" --include="*.py" backend/ scripts/ | grep -v __pycache__` → 출력 없음
- [ ] 브랜치를 트렁크에 착륙시키는 절차는 `superpowers:finishing-a-development-branch`를 따른다. 메인 체크아웃은 `wip/scaffolding`에 있고, 이 워크트리에서는 메인을 만질 수 없다 — `git push origin HEAD:wip/scaffolding`으로 origin을 ff시키고 Fienn이 당기는 것이 그때의 경로다.
