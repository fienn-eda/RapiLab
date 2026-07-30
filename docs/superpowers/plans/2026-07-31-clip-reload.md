# 클립형 재장전 (engine-gap #19) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 탄창을 여러 번에 나눠 채우는 니케 9슬러그의 재장전 시간을 실제 값(분할 수 × 파일 재장전)으로 고쳐, 센티의 발당 간격을 1.45초에서 실측 1.6167초로 맞춘다.

**Architecture:** 분할 수는 shiftypad 원본의 `shot_detail.reload_bullet`(10000 = 탄창 100%를 한 번에)에서 유도된다. 유도 함수는 `shiftypad_normalize`에, 값은 `registry.CLIP_RELOAD_SPLITS`에 두고(데이터 디렉터리가 전부 gitignore이므로), `user_roster.load_nikke_spec`이 `weapon_stats["reload_time"]`에 한 번 곱한다. `NikkeSpec.weapon_stats`가 단일 깔때기라 시뮬레이션·덱탐색·차지창·스킬값 네 소비자가 모두 자동으로 고쳐지고, `attack_rate.py`는 손대지 않는다.

**Tech Stack:** Python 3.13, pytest. 프런트엔드 변경 없음.

## Global Constraints

- 설계 정본은 `docs/superpowers/specs/2026-07-31-clip-reload-design.md`. 벗어나려면 먼저 Fienn에게 물을 것.
- 재장전은 **탄창 소진 후 n회 연속**이고, 모션 딜레이는 n회가 끝난 뒤 **1회**만 붙는다(Fienn, 2026-07-31). 그 1회는 엔진이 이미 표현하므로 새 상수를 만들지 않는다.
- `attack_rate.py`는 이번 작업에서 수정하지 않는다.
- drake·noir·soda-twinkling-bunny·grave의 `weapon_source`는 건드리지 않는다(범위 밖).
- 덱 탐색 해석 경로의 차지 모션 딜레이 누락은 **별건**이며 이번 브랜치에서 고치지 않는다(Fienn, 2026-07-31). 갭 문서에 항목으로 남긴다.
- 명령은 워크트리 루트 기준. 백엔드 테스트는 `cd backend && python -m pytest`.
- 기준선: 백엔드 1645 passed / 3 skipped.

---

### Task 1: 분할 수 유도 함수

`reload_bullet`이 탄창의 몇 %를 한 번에 채우는지를 분할 횟수로 바꾼다. 게임 데이터 형식에 대한 지식이므로 `shiftypad_normalize`에 둔다. `normalize_shiftypad`의 출력에는 **넣지 않는다** — 그 출력은 dotgg 모양의 무기 스탯 스키마이고, 런타임에 읽히는 값은 레지스트리 테이블이라 두 출처를 만들지 않기 위함이다.

**Files:**
- Modify: `backend/app/shiftypad_normalize.py`
- Test: `backend/tests/test_shiftypad_normalize.py`

**Interfaces:**
- Consumes: 없음
- Produces: `clip_reload_splits(shot_detail: dict) -> int` — raw 번들의 `detail.shot_detail`을 받아 탄창을 다 채우는 데 필요한 장전 횟수를 반환. 10000(=100%)이면 1.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_shiftypad_normalize.py` 끝에 추가:

```python
def _shot(max_ammo, reload_bullet):
    return {"max_ammo": max_ammo, "reload_bullet": reload_bullet}


def test_whole_magazine_reload_is_one_split():
    assert clip_reload_splits(_shot(300, 10000)) == 1


def test_centi_loads_a_six_round_magazine_two_at_a_time():
    # 6 x 33% = 2 rounds a load, so three loads - Fienn watched exactly this
    # (2026-07-30) and the data agrees, which is what pins the field's meaning.
    assert clip_reload_splits(_shot(6, 3300)) == 3


def test_a_nine_round_shotgun_also_takes_three_loads():
    assert clip_reload_splits(_shot(9, 3300)) == 3


def test_grave_reloads_her_sixty_rounds_in_halves():
    assert clip_reload_splits(_shot(60, 5000)) == 2


def test_split_count_survives_a_max_ammo_buff():
    # The field is a FRACTION of the magazine, so a bigger magazine gets a
    # bigger clip and the number of loads does not move. Overload's Max
    # Ammunition therefore cannot change this constant.
    assert clip_reload_splits(_shot(8, 3300)) == 3
    assert clip_reload_splits(_shot(12, 3300)) == 3
```

임포트 줄(현재 5행 `from app.shiftypad_normalize import normalize_shiftypad`)도 고친다:

```python
from app.shiftypad_normalize import clip_reload_splits, normalize_shiftypad
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_shiftypad_normalize.py -q`
Expected: FAIL — `ImportError: cannot import name 'clip_reload_splits'`

- [ ] **Step 3: 최소 구현**

`backend/app/shiftypad_normalize.py`에 추가(`normalize_shiftypad` 위):

```python
def clip_reload_splits(shot_detail):
    """How many separate loads it takes to refill this weapon's magazine.

    `reload_bullet` is the share of the magazine one load restores, fixed-point
    over 10000, so 10000 is the ordinary "whole magazine at once" and anything
    lower is a clip weapon: Centi's 3300 fills 33% of her six rounds, two at a
    time, three times (Fienn watched exactly that on 2026-07-30, which is what
    pins this reading of the field). The magazine empties first and then the
    loads run back-to-back - she does not fire between them.

    Deriving the count from the fraction rather than storing rounds-per-load
    keeps it stable under Overload's Max Ammunition: a bigger magazine gets a
    proportionally bigger clip, so 33% is three loads at 6, 8 or 12 rounds.
    """
    share = shot_detail["reload_bullet"] / 10000
    if share >= 1:
        return 1
    max_ammo = shot_detail["max_ammo"]
    per_load = max(1, round(max_ammo * share))
    return math.ceil(max_ammo / per_load)
```

이 파일에는 아직 임포트가 하나도 없다. 모듈 독스트링 바로 아래에 `import math`를 넣는다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_shiftypad_normalize.py -q`
Expected: PASS (기존 테스트 포함 전부)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/shiftypad_normalize.py backend/tests/test_shiftypad_normalize.py
git commit -m "Read how many loads a magazine takes from reload_bullet"
```

---

### Task 2: 레지스트리 테이블

값을 코드에 고정한다. `data/`가 전부 gitignore라 런타임에 파일에서 읽으면 데이터가 없는 환경에서 조용히 옛 낙관값으로 되돌아간다. `_CHARGE_MOTION_DELAY`와 같은 자리·같은 모양.

**Files:**
- Modify: `backend/app/skill_rules/registry.py`
- Test: `backend/tests/test_skill_registry.py`

**Interfaces:**
- Consumes: 없음
- Produces: `get_clip_reload_splits(slug: str) -> int` — 등록된 클립 슬러그의 분할 수, 그 외 1. `CLIP_RELOAD_SPLITS: dict[str, int]`도 모듈 밖에서 읽는다(감사 스크립트가 쓴다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_skill_registry.py` 끝에 추가:

```python
def test_clip_weapons_carry_their_load_count():
    assert get_clip_reload_splits("centi") == 3
    assert get_clip_reload_splits("centi-signature") == 3
    assert get_clip_reload_splits("grave") == 2


def test_an_ordinary_weapon_reloads_once():
    assert get_clip_reload_splits("liter") == 1
    assert get_clip_reload_splits("not-a-slug") == 1


def test_both_builds_of_a_clip_unit_share_the_count():
    # A Favorite Item does not change the weapon, so a base/signature pair that
    # disagreed here would be a typo, not a mechanic.
    for base in ("centi", "drake", "sugar"):
        assert (get_clip_reload_splits(base)
                == get_clip_reload_splits(f"{base}-signature"))
```

이 파일은 `from app.skill_rules.registry import (...)`로 이름을 하나씩 가져온다(3행부터). 그 목록에 `get_clip_reload_splits`를 알파벳 순서에 맞춰 넣는다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_registry.py -q -k clip`
Expected: FAIL — `AttributeError: module 'app.skill_rules.registry' has no attribute 'get_clip_reload_splits'`

- [ ] **Step 3: 최소 구현**

`backend/app/skill_rules/registry.py`의 `get_charge_motion_delay` 정의 바로 뒤에 추가:

```python
# Nikkes who refill a magazine in several loads instead of one. The count comes
# from ShiftyPad's `shot_detail.reload_bullet` (see
# shiftypad_normalize.clip_reload_splits) and is written here rather than read
# live because every data/ directory is gitignored: a checkout without the raw
# bundles would silently fall back to a single reload, which reads as an 11%
# faster cadence rather than as missing data. `scripts/audit_weapon_data.py`
# compares this table against the bundles whenever they ARE present.
#
# Not only launchers and shotguns - Grave is an AR that reloads in halves.
CLIP_RELOAD_SPLITS = {
    "centi": 3,                  # RL, 6 rounds two at a time
    "centi-signature": 3,
    "drake": 3,                  # SG, 9 rounds three at a time
    "drake-signature": 3,
    "sugar": 3,
    "sugar-signature": 3,
    "noir": 3,
    "soda-twinkling-bunny": 3,
    "grave": 2,                  # AR, 60 rounds in halves
}


def get_clip_reload_splits(slug):
    """How many loads this Nikke needs to refill her magazine; 1 for nearly
    everyone - see `CLIP_RELOAD_SPLITS`."""
    return CLIP_RELOAD_SPLITS.get(slug, 1)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_skill_registry.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/tests/test_skill_registry.py
git commit -m "Name the nine slugs that reload a magazine in several loads"
```

---

### Task 3: 배선 — 재장전 시간에 분할 수를 곱한다

**Files:**
- Modify: `backend/app/user_roster.py` (`load_nikke_spec`, 무기 프로필 오버라이드 직후)
- Modify: `backend/tests/test_user_roster.py` (drake의 `reload_time`을 고정한 기존 테스트가 깨진다 — 이번 변경의 회귀 신호이므로 값을 고치고 이유를 남긴다)
- Test: `backend/tests/test_user_roster.py`, `backend/tests/test_attack_rate.py`

**Interfaces:**
- Consumes: `registry.get_clip_reload_splits(slug)` (Task 2)
- Produces: `NikkeSpec.weapon_stats["reload_time"]`의 의미가 "탄창을 다시 채우는 데 걸리는 시간"이 된다. 네 소비자(`roster.py`, `closed_form.py`, `charge_window_inputs.py`, `caster_weapon_stats`)가 그대로 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_user_roster.py` 끝에 추가:

```python
def test_a_clip_weapon_carries_the_time_to_refill_the_whole_magazine():
    # Centi loads two of her six rounds at a time, three times, so the gap after
    # her magazine empties is 3 x the 0.5 sec in the data file.
    spec = load_nikke_spec(_state("centi"))
    assert spec.weapon_stats["reload_time"] == 1.5


def test_an_ordinary_weapon_keeps_the_file_reload():
    spec = load_nikke_spec(_state("liter"))
    assert spec.weapon_stats["reload_time"] == 1.5  # SMG, one load


def test_grave_reloads_her_magazine_in_two_loads():
    spec = load_nikke_spec(_state("grave"))
    assert spec.weapon_stats["reload_time"] == 2.0
```

그리고 `test_loads_drake_end_to_end_from_real_data_files`의 기대값을 고친다:

```python
    # weapon stats from data/dotgg/char_drake-nikke.json ("damage": "214.3%", maxAmmo 9, ...)
    # reload_time is the file's 0.5 sec x 3, because Drake is a clip shotgun:
    # she loads three of her nine rounds at a time (registry.CLIP_RELOAD_SPLITS).
    assert spec.weapon_stats == {
        "weapon": "SG", "damage_percent": 214.3, "max_ammo": 9,
        "reload_time": 1.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
    }
```

`backend/tests/test_attack_rate.py` 끝에 실측 앵커를 추가:

```python
def _centi_weapon(reload_time):
    """Centi's real weapon profile: RL, 6 rounds, 1.0 sec charge, and the 22
    frame pause Fienn timed between a shot and the next charge."""
    return {
        "weapon": "RL", "charge_time": 1.0, "max_ammo": 6,
        "reload_time": reload_time, "damage_percent": 100.0,
        "charge_damage_percent": 250.0, "charge_motion_delay": 22 / 60,
    }


def _shot_times(reload_time, duration=60.0):
    return [r.time for r in generate_segmented_shots(
        _centi_weapon(reload_time), [], duration)]


def test_centis_clip_reload_reproduces_her_measured_cadence():
    # Fienn timed her at 1.617 sec a shot. Six shots at charge + pause is
    # 8.2 sec; the three 0.5 sec loads close the cycle at 9.7, and 9.7 / 6 is
    # 1.6167. Modelling one reload gives 8.7 / 6 = 1.45 - about 11% fast.
    clip = _shot_times(1.5)
    assert round(clip[6] - clip[0], 4) == 9.7
    assert round((clip[6] - clip[0]) / 6, 4) == 1.6167


def test_the_clip_reload_only_moves_shots_after_the_magazine_empties():
    # The loads run back-to-back once the magazine is out, so her first six
    # shots are untouched and the seventh is a full second later.
    clip, single = _shot_times(1.5), _shot_times(0.5)
    assert clip[:6] == single[:6]
    assert round(clip[6], 4) == 11.0667
    assert round(single[6], 4) == 10.0667
    assert round(clip[11], 4) == 17.9
    assert len(clip) == 37
    assert len(single) == 41


@pytest.mark.parametrize("speed", [0.2969, 0.8085, -0.5])
def test_load_count_multiplies_cleanly_through_a_reload_speed_buff(speed):
    # Why the multiplication is allowed to happen at roster assembly instead of
    # inside attack_rate: reload_time_with_speed is linear in reload_time on
    # both its branches, so scaling before or after a buff is the same number.
    # (0.2969 is the cube, 0.8085 cube + Privaty, -0.5 the negative branch.)
    assert (reload_time_with_speed(0.5 * 3, speed)
            == pytest.approx(reload_time_with_speed(0.5, speed) * 3, abs=1e-12))
```

`test_attack_rate.py` 상단 임포트 목록(`from app.attack_rate import (...)`)에 `generate_segmented_shots`가 없으면 추가한다. `reload_time_with_speed`와 `pytest`는 이미 있다.

그리고 `backend/tests/test_skill_rules_centi_signature.py` 끝에 전파를 고정하는 테스트를 추가한다:

```python
def test_her_cooldown_cut_follows_the_clip_reload():
    # Her Skill 2 cooldown is derived from her shot interval, so the reload
    # model propagates into how often the squad ATK buff lands. Modelling one
    # reload made her cycle 5.74 sec; three loads make it 5.96.
    def values(reload_time):
        return {
            "maintain_fortification": {"description_value_02": "9.16"},
            "caster_weapon_stats": {
                "charge_time": 1.0, "max_ammo": 6, "reload_time": reload_time,
            },
        }

    assert round(field_discussion_effective_cooldown(values(1.5)), 4) == 5.9605
    assert round(field_discussion_effective_cooldown(values(0.5)), 4) == 5.7378
```

그 파일의 임포트에 `field_discussion_effective_cooldown`이 없으면
`from app.skill_rules.centi import field_discussion_effective_cooldown`을 추가한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_user_roster.py tests/test_attack_rate.py -q`
Expected: FAIL — 센티/Grave/drake의 `reload_time`이 아직 파일값(0.5 / 1.0 / 0.5)

(`test_attack_rate.py`의 세 테스트와 센티 시그니처 쿨다운 테스트는 weapon dict를 직접
만들므로 Step 3 없이도 통과한다. 이들은 배선이 아니라 **모델**을 고정하는 테스트이고,
실패해야 하는 것은 `test_user_roster.py` 쪽 넷이다.)

- [ ] **Step 3: 최소 구현**

`backend/app/user_roster.py`의 19행 `from app.skill_rules.registry import (...)` 목록에 `get_clip_reload_splits`를 알파벳 순서대로(=`get_skill_value_manifest` 앞) 넣는다.

`load_nikke_spec`의 무기 프로필 오버라이드 블록 바로 뒤(현재 79행 `weapon_stats = override` 다음, 80행 `variant_tier = ...` 앞)에 추가:

```python
        # A clip weapon empties its magazine and then loads it back in several
        # goes, so the gap before the next magazine is that many file reloads.
        # Folded into the weapon's own reload_time because every consumer -
        # the deck simulation, closed_form's shot count, the charge-window
        # calculator, and caster_weapon_stats - already reads that field as
        # "the pause after the magazine runs out". Multiplying here rather than
        # in attack_rate keeps all nine of its reload call sites untouched;
        # reload_time_with_speed is linear in reload_time on both branches, so
        # the order does not matter. If the affine reload model lands
        # (docs/engine-gaps.md), its fixed 0.148 sec segment has to be settled
        # per load or per magazine before this fold stays correct.
        splits = get_clip_reload_splits(slug)
        if splits > 1:
            weapon_stats = {**weapon_stats, "reload_time": weapon_stats["reload_time"] * splits}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_user_roster.py tests/test_attack_rate.py -q`
Expected: PASS

이어서 전체를 돌린다: `cd backend && python -m pytest -q`
Expected: 1645+ passed / 3 skipped. **다른 테스트가 깨지면 멈추고 왜 깨졌는지 보고할 것** — 클립 9슬러그의 총딜은 내려가는 게 맞지만, 그 외 유닛이 움직였다면 배선이 새는 것이다.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/user_roster.py backend/tests/test_user_roster.py backend/tests/test_attack_rate.py
git commit -m "Make a clip weapon wait for every load, not just one"
```

---

### Task 4: 감사 — 신규 니케가 클립이면 잡아낸다

`scripts/audit_weapon_data.py`는 이미 인코딩된 전 슬러그의 무기 6필드를 shiftypad raw와 대조한다. 분할 수를 일곱 번째로 붙인다. 새 스크립트를 만들지 않는 이유는 같은 raw 파일을 같은 슬러그 집합에 대해 이미 읽고 있기 때문이다.

**Files:**
- Modify: `scripts/audit_weapon_data.py`
- Test: `backend/tests/test_audit_weapon_data.py`

**Interfaces:**
- Consumes: `clip_reload_splits` (Task 1), `CLIP_RELOAD_SPLITS` (Task 2)
- Produces: `audit()` 결과 행에 `"reload_splits_diff": (ours, live) | None`. 값이 있으면 verdict가 `MISMATCH`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_audit_weapon_data.py` 끝에 추가:

```python
def test_an_unregistered_clip_weapon_is_a_mismatch():
    # The failure this guards: a newly onboarded clip Nikke nobody added to
    # CLIP_RELOAD_SPLITS reads as 11% faster than she fires, and nothing else
    # in the pipeline would say so.
    assert audit.reload_splits_diff("liter", {"max_ammo": 6, "reload_bullet": 3300}) == (1, 3)


def test_a_registered_clip_weapon_agrees():
    assert audit.reload_splits_diff("centi", {"max_ammo": 6, "reload_bullet": 3300}) is None


def test_an_ordinary_weapon_agrees():
    assert audit.reload_splits_diff("liter", {"max_ammo": 120, "reload_bullet": 10000}) is None


def test_a_stale_table_entry_is_a_mismatch():
    # The mirror case: a balance patch that makes Centi load her whole magazine
    # at once leaves the table one reload too slow.
    assert audit.reload_splits_diff("centi", {"max_ammo": 6, "reload_bullet": 10000}) == (3, 1)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_audit_weapon_data.py -q`
Expected: FAIL — `AttributeError: module 'audit_weapon_data' has no attribute 'reload_splits_diff'`

- [ ] **Step 3: 최소 구현**

`scripts/audit_weapon_data.py`의 임포트에 추가:

```python
from app.shiftypad_normalize import clip_reload_splits, normalize_shiftypad
from app.skill_rules.registry import get_clip_reload_splits
```

`compare` 정의 뒤에 추가:

```python
def reload_splits_diff(slug, shot_detail):
    """(ours, live) when the registry's load count disagrees with the bundle.

    Kept next to the weapon-field comparison because it is the same kind of
    claim - an engine input that has to still be the game's - but it reads the
    RAW shot_detail rather than the normalized weapon stats, since the count is
    deliberately not part of that schema (registry.CLIP_RELOAD_SPLITS holds it).
    """
    ours = get_clip_reload_splits(slug)
    live = clip_reload_splits(shot_detail)
    return (ours, live) if ours != live else None
```

`load_live` 뒤에 raw 로더를 추가:

```python
def load_live_shot_details(raw_dir: Path) -> dict[int, dict]:
    """resource_id -> raw shot_detail, for the fields normalization drops."""
    details = {}
    for path in sorted(raw_dir.glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        details[int(path.stem)] = bundle["detail"]["shot_detail"]
    return details
```

`audit()`에서 `live_by_rid = load_live(raw_dir)` 다음 줄에:

```python
    shot_by_rid = load_live_shot_details(raw_dir)
```

그리고 결과 행 조립을 고친다:

```python
        splits_diff = reload_splits_diff(slug, shot_by_rid[rid])
        rows.append(
            {
                **row,
                "verdict": "MISMATCH" if weapon_diffs or splits_diff else "ok",
                "weapon_diffs": weapon_diffs,
                "reload_splits_diff": splits_diff,
                "meta_diffs": meta_diffs,
                "burst_cooldown_diff": cooldown_diff,
            }
        )
```

`main()`의 리포트 루프에서 `burst_cooldown_diff`를 찍는 블록 바로 앞에 같은 형태로 추가한다:

```python
        if row.get("reload_splits_diff"):
            ours, live = row["reload_splits_diff"]
            print(f"            (reload splits) ours={ours} shiftypad={live}")
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_audit_weapon_data.py -q`
Expected: PASS

그리고 실제로 돌려서 전 로스터가 깨끗한지 본다:

Run: `python scripts/audit_weapon_data.py`
Expected: 클립 9슬러그를 포함해 MISMATCH 0건. (raw 번들이 없는 유닛은 `no-live`로 남는 게 정상이다.)

- [ ] **Step 5: 커밋**

```bash
git add scripts/audit_weapon_data.py backend/tests/test_audit_weapon_data.py
git commit -m "Audit the load count against the game data too"
```

---

### Task 5: 문서와 인코딩 체크리스트

**Files:**
- Modify: `docs/engine-gaps.md` (#19 해소, 그리고 새 항목: 덱 탐색 해석 경로의 모션 딜레이 누락)
- Modify: `docs/insights.md`
- Modify: `docs/decisions.md`
- Modify: `docs/roadmap.md` (To-Do 반영)
- Modify: `backend/app/skill_rules/centi.py` (docstring의 보류 사유 삭제)
- Modify: `.claude/skills/nikke-skill-encoding/SKILL.md`의 데이터 확인 단계

**Interfaces:**
- Consumes: Task 1~4의 결과
- Produces: 없음(문서)

- [ ] **Step 1: `centi.py`의 보류 사유를 지운다**

`Not modeled / deferred:` 목록에서 "She is a CLIP launcher..." 항목을 삭제하고, 그 사실을 현재형으로 옮긴다:

```python
- She is a clip launcher: her six-round magazine comes back two rounds at a
  time, so the gap after it empties is three 0.5-sec loads, not one
  (registry.CLIP_RELOAD_SPLITS). Her cadence - and the cooldown cut derived
  from it - accounts for that.
```

`field_discussion_effective_cooldown`의 독스트링에 재장전 모델을 사유로 든 문구가 남아 있으면 같이 고친다.

- [ ] **Step 2: `docs/engine-gaps.md`를 고친다**

- 우선순위 표의 19행을 `~~19~~ ... **해소 (2026-07-31)**`로 바꾸고 "막힌 유닛"을 **9슬러그**로, 성격을 "데이터에 이미 있었음"으로 고친다.
- 상세 섹션 "### 19."를 해소로 다시 쓴다. 반드시 담을 것: `reload_bullet` 필드와 10000 규약 · 6유닛 표 · **Grave가 AR이라 제목의 "런처·샷건"이 틀렸다** · 재장전은 소진 후 연속이고 모션 딜레이는 1회(Fienn) · 값을 코드에 둔 이유(gitignore) · 아핀 재장전 모델과의 미결 상호작용.
- 새 항목을 추가한다: **덱 탐색의 해석 경로가 차지 모션 딜레이를 무시한다.** `closed_form._shot_count`가 `generate_shot_times`를 부르는데 그 함수에는 딜레이 인자가 없고 캐시 키에도 없다. 영향은 `TIMED_CHARGE_MOTION_DELAY`에 든 13슬러그이고 센티 기준 60초에 41발 대 실제 37발. 시뮬레이션 경로(`_base_shot_records`)는 제대로 접는다. Fienn이 클립 작업과 분리하기로 결정(2026-07-31).
- 문서 상단 "마지막 갱신"에 이번 항목을 얹는다(기존 형식 그대로).

- [ ] **Step 3: `docs/insights.md`에 교훈을 추가한다**

주제: **"데이터에 없다"는 문서의 단정을 원본으로 검증하라.** 갭 #19는 "분할 수가 어디에도 없어 실측 상수 테이블이 필요하다"고 적혀 있었고 그 때문에 측정 캠페인이 필요한 작업으로 분류돼 있었다. 실제로는 shiftypad 원본 `shot_detail`에 `reload_bullet`이 있었고, 정규화 단계(`normalize_shiftypad`가 6필드만 뽑는다)에서 떨어져 나가 보이지 않았을 뿐이다. 일반화: **정규화된 데이터에 없다는 것은 원본에 없다는 뜻이 아니다.** 갭을 착수하기 전에 원본 페이로드의 필드를 한 번 훑을 것. 같은 형태로 `reload_start_ammo`도 미해석 필드로 남아 있다(전 유닛 `max_ammo - 1`이라 판별력이 없음).

- [ ] **Step 4: `docs/decisions.md`에 결정을 기록한다**

제목은 "클립 분할 수는 데이터에서 유도하고 값은 코드에 둔다" 형태. Context: 값의 출처는 shiftypad(방침상 1순위)인데 `data/`가 전부 gitignore다. Decision: 유도 함수는 `shiftypad_normalize`, 값은 `registry.CLIP_RELOAD_SPLITS`, 대조는 `audit_weapon_data.py`. Why: 데이터에서 런타임에 읽으면 raw 번들이 없는 체크아웃에서 조용히 단일 재장전으로 되돌아가고, 그건 "데이터 없음"이 아니라 "11% 빠른 케이던스"로 보인다. 기각한 대안: 클립 4유닛의 `weapon_source`를 shiftypad로 옮기기 — 무기 6필드가 이미 동일해 얻는 게 없고, `data/shiftypad/<slug>.json`이 git에 없어 유닛이 조용히 로스터에서 빠진다. Consequences: 신규 클립 니케는 사람이 등록해야 하며, 그 누락은 감사 스크립트가 잡는다.

- [ ] **Step 5: 인코딩 스킬 체크리스트에 한 줄 넣는다**

`.claude/skills/nikke-skill-encoding/SKILL.md`의 데이터 수집/확인 단계에 추가:

```markdown
- 수집한 ShiftyPad 번들의 `detail.shot_detail.reload_bullet`이 10000이 아니면
  클립 무기다(탄창을 여러 번에 나눠 채운다). `registry.CLIP_RELOAD_SPLITS`에
  등록할 것 — 빠뜨리면 그 유닛의 케이던스가 조용히 낙관적이 된다.
  `python scripts/audit_weapon_data.py`가 사후에 잡아준다.
```

넣을 위치는 그 파일의 기존 데이터 확인 항목 옆이다. 파일을 먼저 읽고 형식을 맞출 것.

- [ ] **Step 6: `docs/roadmap.md`의 To-Do를 갱신한다**

868행 "### 클립형 재장전 (2026-07-30, Centi 인코딩에서 발견)" 섹션이 이 작업의 To-Do다.
하위 체크박스 중 "클립형 유닛 명단 확정 — 분할 수는 게임 데이터 파일에 없으므로 Fienn
실측이 필요"는 **전제가 틀렸으므로 완료 처리하면서 그 사실을 적는다**(명단은
`reload_bullet`로 확정, 실측 불필요). `attack_rate`에 `reload_splits`를 넣는 항목도
실제로 한 일(로스터 조립에서 `reload_time`에 곱함, `attack_rate` 무변경)로 고쳐
완료 표시한다. 그 아래에 새 항목으로 덱 탐색 모션 딜레이 누락을 연다.

- [ ] **Step 7: 전체 테스트를 돌린다**

Run: `cd backend && python -m pytest -q`
Expected: 1645+ passed / 3 skipped

Run: `cd frontend && npm test`
Expected: 452 passed (프런트 변경 없음 — 회귀만 확인)

- [ ] **Step 8: 커밋**

```bash
git add docs backend/app/skill_rules/centi.py .claude/skills/nikke-skill-encoding
git commit -m "Record that the clip reload was in the data all along"
```

---

## 완료 기준

- 센티 발당 간격이 1.6167초(Fienn 실측), 60초 발수 41 → 37
- `python scripts/audit_weapon_data.py`가 MISMATCH 0건
- 백엔드 1645+ passed / 3 skipped, 프런트 452 passed
- `docs/engine-gaps.md` #19가 해소로 닫히고, 모션 딜레이 누락이 새 항목으로 열림
