# Weapon-Mode Segments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 발사 타임라인이 구간별로 다른 무기 프로필을 쓸 수 있는 엔진 프리미티브(`weapon_mode_schedules`)를 만들고, 소비자 4건(snow-white·maxwell 신규, laplace-signature 신규 슬러그, red-hood 마이그레이션)을 인코딩한다.

**Architecture:** 유닛 모듈이 `(context, fight_duration) → [세그먼트]` 스케줄을 계산하고(`scheduled_nukes` 선례), `attack_rate`의 새 생성기가 기본 프로필과 오버라이드 프로필을 구간별로 오가며 **샷 레코드**(시각·percent·차지보너스·first/last 플래그)를 만든다. `raid_simulator`의 무기 패스는 모든 유닛을 이 생성기로 통일(세그먼트 없으면 기존 출력과 동일 — 회귀 기준)하고 레코드의 per-샷 percent로 기록한다. 스펙: `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`.

**Tech Stack:** Python (backend/), pytest. 테스트 실행은 `C:/Users/fienn/anaconda3/python.exe -m pytest` (PATH의 python 3.14엔 pytest 없음).

## Global Constraints

- 작업 위치: 워크트리 `.claude/worktrees/encoding-gap10-scarlet` (branch `worktree-encoding-gap10-scarlet`). 시작 시 `python scripts/sync_worktree_data.py` 실행(이미 동기화면 no-op).
- **미등록(세그먼트 없는) 유닛의 시뮬레이션 출력은 한 자리도 변하면 안 된다** — 전체 스위트(798개+) green이 태스크마다의 회귀 기준.
- 변형 창 종료 후 기본 무기는 **가득 찬 새 매거진으로 즉시** 재개 (Fienn 확정, 스펙 참고).
- 세그먼트 안에서는 **재장전 없음**(v1 소비자 중 창 내 재장전 유닛 없음 — YAGNI).
- 명시적 `rate_of_fire` 프로필(실측 앵커)엔 덱의 공속/차지속도 버프를 **적용하지 않는다**(실측에 이미 포함). `charge_time` 프로필엔 `charge_speed_percent_at`을 적용한다.
- "as additional damage" 텍스트 → `full_burst_bonus_eligible=True` (기존 Fienn 규칙).
- 스킬 수치는 하드코딩 금지 — `SKILL_VALUE_MANIFESTS` + `description_value_NN` 슬롯 (lootandwaifus 텍스트의 숫자를 왼쪽부터 번호. `backend/app/skill_values.py` 참고).
- 커밋 메시지에 따옴표(`"`)를 넣지 말 것 — PowerShell 인자 재구성이 깨뜨림. 필요하면 `git commit -F <파일>`.
- 메커니즘이 모호하면 **Fienn에게 질문**하고 추측하지 않는다(각 태스크의 질문 스텝 참고).

---

### Task 1: `attack_rate.generate_segmented_shots()` — 샷 레코드 생성기

**Files:**
- Modify: `backend/app/attack_rate.py` (파일 끝에 추가)
- Test: `backend/tests/test_attack_rate.py` (기존 파일에 추가)

**Interfaces:**
- Produces: `ShotRecord(time, weapon, damage_percent, extra_charge_bonus, is_first_bullet, is_last_bullet, damage_type=None)` (frozen dataclass) · `generate_segmented_shots(base, segments, fight_duration, max_ammo_percent_at=_zero, reload_speed_percent_at=_zero, attack_speed_percent_at=_zero, charge_speed_percent_at=_zero) -> list[ShotRecord]`
- 세그먼트 스펙: `{"start": float, "profile": {...}}` + (`"end": float` 또는 `"until_shots": int` 중 하나). profile 키: `"weapon"`(필수, 데미지 타이핑용) · `"damage_percent"`(필수) · `"charge_damage_percent"`(옵션 — 있으면 `/100 - 1`이 히트당 extra_charge_bonus) · `"charge_time"`(있으면 차지식 케이던스, charge_speed 버프 적용) 또는 `"rate_of_fire"`(고정 케이던스, 버프 미적용) · `"damage_type"`(옵션 — normal_attack_type 오버라이드, 예: laplace true 틱).

- [ ] **Step 1: 실패하는 테스트 작성** — `backend/tests/test_attack_rate.py`에 추가:

```python
from app.attack_rate import (
    ShotRecord,
    first_bullet_shot_times,
    generate_segmented_shots,
    generate_shot_times,
    last_bullet_shot_times,
)

AR_BASE = {"weapon": "AR", "damage_percent": 14.71, "max_ammo": 60,
           "reload_time": 1.5, "charge_time": 0.0, "charge_damage_percent": 100.0}
SR_BASE = {"weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
           "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}
CANNON = {"weapon": "SR", "damage_percent": 499.5,
          "charge_damage_percent": 1000.0, "charge_time": 5.0}
# rate 4.0 → interval 0.25 (이진 정확) — 부동소수점 경계 없는 카운트 단언용.
# 실소비자(laplace 9.3)는 until_shots 형태라 경계 문제가 없다.
TICKER = {"weapon": "SR", "damage_percent": 22.2, "rate_of_fire": 4.0}


def test_no_segments_matches_legacy_generator_exactly():
    for base in (AR_BASE, SR_BASE):
        records = generate_segmented_shots(base, [], 180.0)
        legacy = generate_shot_times(
            base["weapon"], base["max_ammo"], base["reload_time"],
            base["charge_time"], 180.0)
        assert [r.time for r in records] == legacy
        assert {r.time for r in records if r.is_last_bullet} == last_bullet_shot_times(
            base["weapon"], base["max_ammo"], base["reload_time"], base["charge_time"], 180.0)
        assert {r.time for r in records if r.is_first_bullet} == first_bullet_shot_times(
            base["weapon"], base["max_ammo"], base["reload_time"], base["charge_time"], 180.0)
        assert all(r.damage_percent == base["damage_percent"] for r in records)


def test_fixed_window_silences_base_and_fires_profile_rate():
    seg = {"start": 10.0, "end": 20.0, "profile": TICKER}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    inside = [r for r in records if 10.0 <= r.time < 20.0]
    # 창 안은 전부 오버라이드 프로필(고정 rate) — 기본 SR 발사 없음
    assert all(r.damage_percent == 22.2 for r in inside)
    assert inside[0].time == 10.25          # start + 1/rate
    assert len(inside) == 39                # k*0.25 < 10.0 → k <= 39
    assert all(r.extra_charge_bonus == 0.0 for r in inside)


def test_base_resumes_with_fresh_magazine_at_window_end():
    seg = {"start": 10.0, "end": 20.0, "profile": TICKER}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    after = [r for r in records if r.time >= 20.0]
    # 새 매거진 즉시: 첫 발은 20.0 + 차지 1발 시간, first_bullet 플래그
    assert after[0].time == 20.0 + 1.0
    assert after[0].is_first_bullet


def test_until_shots_single_charged_shot_then_resume():
    seg = {"start": 10.0, "until_shots": 1, "profile": CANNON}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    cannon_shots = [r for r in records if r.damage_percent == 499.5]
    assert len(cannon_shots) == 1
    assert cannon_shots[0].time == 15.0            # 10.0 + 차지 5초 (버프 없음)
    assert cannon_shots[0].extra_charge_bonus == 9.0  # 1000%/100 - 1
    # 기본 무기는 그 발사 시각부터 새 매거진으로 재개
    resumed = [r for r in records if r.time > 15.0 and r.damage_percent == 69.04]
    assert resumed[0].time == 15.0 + 1.0


def test_charge_speed_callable_shortens_profile_charge():
    seg = {"start": 10.0, "until_shots": 1, "profile": CANNON}
    records = generate_segmented_shots(
        SR_BASE, [seg], 60.0, charge_speed_percent_at=lambda t: 1.0)
    cannon = [r for r in records if r.damage_percent == 499.5][0]
    assert cannon.time == 10.0 + 5.0 / 2.0


def test_fight_duration_clips_segment_shots():
    seg = {"start": 178.0, "until_shots": 33,
           "profile": {"weapon": "SR", "damage_percent": 51.46,
                       "charge_damage_percent": 343.36, "rate_of_fire": 3.3}}
    records = generate_segmented_shots(SR_BASE, [seg], 180.0)
    seg_shots = [r for r in records if r.damage_percent == 51.46]
    assert all(r.time < 180.0 for r in seg_shots)
    assert len(seg_shots) < 33


def test_overlapping_segments_rejected():
    import pytest
    segs = [{"start": 10.0, "end": 20.0, "profile": TICKER},
            {"start": 15.0, "end": 25.0, "profile": TICKER}]
    with pytest.raises(ValueError):
        generate_segmented_shots(SR_BASE, segs, 60.0)
```

- [ ] **Step 2: 실패 확인**

Run: `C:/Users/fienn/anaconda3/python.exe -m pytest backend/tests/test_attack_rate.py -v -k segmented or fresh_magazine or until_shots or charge_speed_callable or clips or overlapping`
Expected: ImportError (ShotRecord, generate_segmented_shots 미정의)

- [ ] **Step 3: 구현** — `backend/app/attack_rate.py` 끝에 추가:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ShotRecord:
    """One shot of a (possibly mode-switching) unit's timeline: its damage
    parameters ride on the record because different segments fire different
    profiles. damage_type None = derive from `weapon` (raid_simulator's
    normal_attack_type); a segment profile may pin it (e.g. a transform whose
    ticks are true damage)."""
    time: float
    weapon: str
    damage_percent: float
    extra_charge_bonus: float
    is_first_bullet: bool
    is_last_bullet: bool
    damage_type: str | None = None


def _base_shot_records(base, window_start, window_end,
                       max_ammo_percent_at, reload_speed_percent_at,
                       attack_speed_percent_at, charge_speed_percent_at):
    """The base weapon firing over [window_start, window_end) - the same
    arithmetic as generate_{charge,magazine}_shot_times (kept bit-identical so
    a no-segment call reproduces the legacy timeline exactly), restarted with
    a fresh magazine at window_start (the post-transform resume semantic,
    Fienn 2026-07-18). A magazine cut short by window_end gets NO last-bullet
    flag (it never actually emptied - same rule as the fight_duration cutoff)."""
    records = []
    if window_end <= window_start:
        return records
    weapon = base["weapon"]
    if weapon in CHARGE_WEAPONS:
        bonus = base["charge_damage_percent"] / 100 - 1
        magazine_start = window_start
        while magazine_start < window_end:
            effective_charge = base["charge_time"] / (1 + charge_speed_percent_at(magazine_start))
            magazine_size = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            last_shot_time = None
            for i in range(magazine_size):
                shot_time = magazine_start + (i + 1) * effective_charge
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], bonus,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1)))
                last_shot_time = shot_time
            actual_reload = base["reload_time"] / (1 + reload_speed_percent_at(last_shot_time))
            magazine_start = last_shot_time + actual_reload
    else:
        rate = rate_of_fire_for_weapon(weapon)
        magazine_start = window_start
        while magazine_start < window_end:
            interval = 1.0 / (rate * (1 + attack_speed_percent_at(magazine_start)))
            magazine_size = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            for i in range(magazine_size):
                shot_time = magazine_start + i * interval
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], 0.0,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1)))
            magazine_empty_at = magazine_start + magazine_size * interval
            actual_reload = base["reload_time"] / (1 + reload_speed_percent_at(magazine_empty_at))
            magazine_start = magazine_empty_at + actual_reload
    return records


def _segment_shot_records(seg, fight_duration, charge_speed_percent_at):
    """Shots of one override window. Cadence: charge-style profiles
    (charge_time) honor live charge-speed buffs; explicit rate_of_fire
    profiles are measurement anchors and take NO cadence buffs (the measured
    count already includes every in-game modifier). Segments never reload
    (no v1 consumer needs it). Returns (records, segment_end): until_shots
    windows end AT their last shot's time - the base weapon resumes at that
    same instant with a fresh magazine."""
    profile = seg["profile"]
    start = seg["start"]
    if profile.get("charge_time"):
        interval = profile["charge_time"] / (1 + charge_speed_percent_at(start))
    else:
        interval = 1.0 / profile["rate_of_fire"]
    charge = profile.get("charge_damage_percent")
    bonus = charge / 100 - 1 if charge else 0.0
    if "until_shots" in seg:
        times = [start + k * interval for k in range(1, seg["until_shots"] + 1)]
        seg_end = times[-1]
    else:
        seg_end = seg["end"]
        times = []
        k = 1
        while start + k * interval < seg_end:
            times.append(start + k * interval)
            k += 1
    records = [
        ShotRecord(t, profile["weapon"], profile["damage_percent"], bonus,
                   is_first_bullet=False, is_last_bullet=False,
                   damage_type=profile.get("damage_type"))
        for t in times if t < fight_duration
    ]
    return records, min(seg_end, fight_duration)


def generate_segmented_shots(
    base,
    segments,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
):
    """Full shot-record timeline for a unit whose weapon profile changes
    inside module-scheduled windows (weapon transforms - see
    docs/superpowers/specs/2026-07-18-weapon-transform-design.md). With no
    segments this reproduces generate_shot_times bit-for-bit (regression
    anchor), plus first/last-bullet flags equal to the marker trios."""
    records = []
    cursor = 0.0
    for seg in list(segments) + [None]:
        if seg is None:
            stretch_end = fight_duration
        else:
            if seg["start"] < cursor:
                raise ValueError("weapon mode segments overlap or are unsorted")
            stretch_end = min(seg["start"], fight_duration)
        records.extend(_base_shot_records(
            base, cursor, stretch_end, max_ammo_percent_at,
            reload_speed_percent_at, attack_speed_percent_at, charge_speed_percent_at))
        if seg is None or seg["start"] >= fight_duration:
            break
        seg_records, cursor = _segment_shot_records(seg, fight_duration, charge_speed_percent_at)
        records.extend(seg_records)
    return records
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `C:/Users/fienn/anaconda3/python.exe -m pytest backend/tests/test_attack_rate.py -v`
Expected: 전부 PASS (기존 테스트 포함)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/attack_rate.py backend/tests/test_attack_rate.py
git commit -m "engine: generate_segmented_shots - per-segment shot records (weapon transforms)"
```

---

### Task 2: `raid_simulator` 무기 패스 통일 + `weapon_mode_schedules` 파라미터

**Files:**
- Modify: `backend/app/raid_simulator.py` (import부, `simulate_raid` 시그니처 ~283행, 무기 패스 571–697행)
- Test: `backend/tests/test_raid_simulator.py` (추가)

**Interfaces:**
- Consumes: Task 1의 `generate_segmented_shots`/`ShotRecord`
- Produces: `simulate_raid(..., weapon_mode_schedules={slug: schedule_fn})` — schedule_fn은 `(context, fight_duration) -> [세그먼트]`. 미지정 유닛은 빈 세그먼트로 동일 경로를 타며 출력 불변.

- [ ] **Step 1: 실패하는 테스트 작성** — `backend/tests/test_raid_simulator.py`에 추가 (파일 상단의 기존 헬퍼/픽스처 스타일을 따를 것; 아래는 자족적 최소형):

```python
def _one_unit_deck():
    return [{"slug": "gunner", "burst_tier": 3, "element": "Iron",
             "cooldown": 40.0, "weapon": "SR"}]

SR_WEAPON = {"weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
             "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}


def test_weapon_mode_schedule_swaps_profile_inside_window():
    def schedule(context, fight_duration):
        return [{"start": 5.0, "until_shots": 1,
                 "profile": {"weapon": "SR", "damage_percent": 499.5,
                             "charge_damage_percent": 1000.0, "charge_time": 5.0}}]

    kwargs = dict(
        deck=_one_unit_deck(), rules_by_slug={}, burst_damage_percents={},
        base_stats={"gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        weapon_stats={"gunner": SR_WEAPON},
    )
    plain = simulate_raid(**kwargs)
    with_transform = simulate_raid(**kwargs, weapon_mode_schedules={"gunner": schedule})
    # 창 안(5~10초) 기본 SR 발사가 사라지고 10초 시점 대포 1발로 대체
    plain_shots = [e for e in plain["damage_log"] if e["source"] == "normal_attack"]
    transformed = [e for e in with_transform["damage_log"] if e["source"] == "normal_attack"]
    cannon = [e for e in transformed if e["time"] == 10.0]
    assert len(cannon) == 1
    assert not [e for e in transformed if 5.0 <= e["time"] < 10.0]
    assert [e for e in plain_shots if 5.0 <= e["time"] < 10.0]
    # 대포 1발 = 499.5% x (1 + 9.0 차지보너스) — 동일 스탯 기본샷과 비율 비교
    base_shot = plain_shots[0]["damage"]          # 69.04% x (1+1.5)
    assert cannon[0]["damage"] > base_shot * 20
```

- [ ] **Step 2: 실패 확인**

Run: `C:/Users/fienn/anaconda3/python.exe -m pytest backend/tests/test_raid_simulator.py -k weapon_mode -v`
Expected: TypeError (simulate_raid에 weapon_mode_schedules 파라미터 없음)

- [ ] **Step 3: 구현.** 변경 3곳:

(a) import부 — `generate_shot_times`, `first_bullet_shot_times`, `last_bullet_shot_times` import 제거, `generate_segmented_shots` 추가.

(b) `simulate_raid` 시그니처에 `weapon_mode_schedules=None` 추가 + 본문 초입 `weapon_mode_schedules = weapon_mode_schedules or {}`.

(c) 무기 패스(571행~): `generate_shot_times` 호출과 `needs_last_bullets`/`last_bullets`/`needs_first_bullets`/`first_bullets` 블록(586–639행)을 다음으로 교체하고, 발사 루프를 레코드 기반으로 변경:

```python
        schedule_fn = weapon_mode_schedules.get(slug)
        segments = schedule_fn(context, fight_duration) if schedule_fn is not None else []
        shot_records = generate_segmented_shots(
            weapon, segments, fight_duration,
            max_ammo_percent_at=max_ammo_percent_at,
            reload_speed_percent_at=reload_speed_percent_at,
            attack_speed_percent_at=attack_speed_percent_at,
            charge_speed_percent_at=charge_speed_percent_at,
        )
        shot_times = [r.time for r in shot_records]
        last_bullets = {r.time for r in shot_records if r.is_last_bullet}
        first_bullets = {r.time for r in shot_records if r.is_first_bullet}
```

`extra_charge_bonus`/`is_charge_weapon` 지역 변수는 삭제(레코드가 실어옴). `last_bullet_times_by_slug[slug] = last_bullets`는 유지. 발사 루프는:

```python
        for shot_index, rec in enumerate(shot_records):
            shot_time = rec.time
            ...  # per-shot 룰 발화 로직은 shot_time/count 기준 그대로
            damage_type = rec.damage_type or normal_attack_type(slug, rec.weapon, shot_time)
            record(slug, rec.damage_percent, shot_time, "normal_attack",
                   damage_type=damage_type, extra_charge_bonus=rec.extra_charge_bonus)
```

`normal_attack_type(slug, weapon, time)`은 `weapon["weapon"]` 대신 무기 타입 문자열을 받도록 시그니처 변경(`weapon_type == "RL"` 비교) — 호출부는 위 한 곳뿐.

- [ ] **Step 4: 신규 + 전체 스위트 통과 확인** (통일 경로의 출력 불변이 핵심)

Run: `C:/Users/fienn/anaconda3/python.exe -m pytest backend/tests -q`
Expected: 전부 PASS. 하나라도 수치가 달라지면 Task 1의 동일성(비트 일치)이 깨진 것 — 생성기 산술을 레거시와 비교해 수정(허용오차로 테스트를 느슨하게 만들지 말 것).

- [ ] **Step 5: 커밋**

```bash
git add backend/app/raid_simulator.py backend/tests/test_raid_simulator.py
git commit -m "engine: weapon_mode_schedules - unified weapon pass over shot records"
```

---

### Task 3: registry/roster 스레딩

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (`_SCHEDULED_NUKE_BUILDERS` 부근에 맵 추가, getter들 옆에 함수 추가)
- Modify: `backend/app/roster.py` (import, assemble 루프, 반환 dict)
- Test: `backend/tests/test_raid_simulator.py` 또는 로스터 조립 테스트가 있는 파일 (기존 `scheduled_nukes` 스레딩 테스트를 grep해 같은 자리에 추가)

**Interfaces:**
- Produces: `registry.get_weapon_mode_schedules(slug, skill_values) -> schedule_fn | None`, `_WEAPON_MODE_SCHEDULE_BUILDERS = {slug: lambda sv: ...}`. `assemble_simulation_inputs` 반환 dict에 `"weapon_mode_schedules"` 키.

- [ ] **Step 1: 실패하는 테스트** — 기존 `scheduled_nukes` 조립 스레딩을 검증하는 테스트를 grep (`grep -rn "get_scheduled_nukes\|scheduled_nukes" backend/tests`)해 같은 파일·같은 스타일로 `weapon_mode_schedules` 버전을 추가. 없다면 최소형: 등록 슬러그의 NikkeSpec으로 `assemble_simulation_inputs`를 부르고 반환 dict에 `weapon_mode_schedules` 키가 (빈 dict라도) 존재함을 확인.
- [ ] **Step 2: 실패 확인** (KeyError/AttributeError)
- [ ] **Step 3: 구현** — registry.py에 (builder는 Task 4에서 채움):

```python
# A Nikke whose burst swaps her weapon profile for a window (weapon-mode
# segments - see raid_simulator's `weapon_mode_schedules` and the design spec).
_WEAPON_MODE_SCHEDULE_BUILDERS = {}


def get_weapon_mode_schedules(slug, skill_values):
    builder = _WEAPON_MODE_SCHEDULE_BUILDERS.get(slug)
    if builder is None:
        return None
    return builder(skill_values)
```

(기존 getter들의 실제 본문 형태를 확인해 맞출 것 — `get_scheduled_nukes` 546행 참고.) roster.py: import에 `get_weapon_mode_schedules` 추가, 루프에:

```python
        weapon_mode_schedule = get_weapon_mode_schedules(spec.slug, skill_values)
        if weapon_mode_schedule:
            weapon_mode_schedules[spec.slug] = weapon_mode_schedule
```

초기화 `weapon_mode_schedules = {}` + 반환 dict에 `"weapon_mode_schedules": weapon_mode_schedules`.

- [ ] **Step 4: 전체 스위트 통과 확인** — Run: `C:/Users/fienn/anaconda3/python.exe -m pytest backend/tests -q`
- [ ] **Step 5: 커밋** — `git commit -m "engine: thread weapon_mode_schedules through registry and roster assembly"`

---

### Task 4: red-hood 마이그레이션 (scheduled_nukes → weapon-mode segment)

**Files:**
- Modify: `backend/app/skill_rules/red_hood.py`
- Modify: `backend/app/skill_rules/registry.py` (red-hood를 `_SCHEDULED_NUKE_BUILDERS`에서 제거, `_WEAPON_MODE_SCHEDULE_BUILDERS`에 등록, import 갱신)
- Test: `backend/tests/test_skill_rules_red_hood.py` (89행~ 스케줄 테스트 3개 교체)

**Interfaces:**
- Consumes: Task 1 프로필 계약, Task 3 레지스트리 맵
- Produces: `build_red_wolf_weapon_mode_schedule(values) -> schedule_fn`

- [ ] **Step 1: 실패하는 테스트** — 기존 `test_red_wolf_*` 3개(33발 스케줄·fight-end 드롭·오버랩 차감)를 다음으로 교체:

```python
def test_red_wolf_schedule_is_33_shot_window_per_own_burst():
    schedule = build_red_wolf_weapon_mode_schedule(RED_HOOD_VALUES)
    context = SimpleNamespace(burst_times={"red-hood": [20.0]})
    segments = schedule(context, 180.0)
    assert len(segments) == 1
    seg = segments[0]
    assert seg["start"] == 20.0
    assert seg["until_shots"] == 33
    profile = seg["profile"]
    assert profile["rate_of_fire"] == pytest.approx(3.3)
    assert profile["damage_percent"] == 51.46
    # 250% 풀차지 + 93.36%p Glaring 변환이 charge_damage로 접힘 (차감 없음)
    assert profile["charge_damage_percent"] == pytest.approx(343.36, abs=0.01)


def test_red_wolf_deck_charge_damage_buff_now_scales_transform_shots():
    # 엔드투엔드: 동일 덱에 charge_damage_bonus 버프를 추가하면 변형샷 딜이 증가
    # (기존 scheduled_nukes 모델의 한계 해소를 회귀로 고정).
    # 기존 파일의 red-hood 시뮬 픽스처를 재사용해 buff 유/무 두 번 돌리고
    # 창 안(버스트+0~10초) normal_attack 합이 버프 시 커짐을 단언한다.
    ...  # 파일의 기존 시뮬 헬퍼 스타일로 작성
```

(두 번째 테스트의 `...`는 기존 파일 픽스처를 그대로 쓰라는 뜻 — 새 헬퍼를 만들지 말 것.)

- [ ] **Step 2: 실패 확인** — ImportError
- [ ] **Step 3: 구현** — `red_hood.py`에서 `build_red_wolf_scheduled_nukes`와 오버랩 차감 상수(`_SR_*` 5개, `_steady`분 제외)를 삭제하고:

```python
def build_red_wolf_weapon_mode_schedule(values):
    glaring = values["glaring_eyes"]
    red_wolf = values["red_wolf"]
    shot_percent = float(red_wolf["description_value_11"])
    full_charge_percent = float(red_wolf["description_value_12"])   # 250
    duration = float(red_wolf["description_value_13"])              # 10
    window_charge_speed = float(red_wolf["description_value_16"]) / 100
    steady = _steady_charge_speed(glaring)
    threshold = float(glaring["description_value_04"]) / 100
    rate = float(glaring["description_value_05"]) / 100
    converted = (steady + window_charge_speed - threshold) * rate   # 0.9336
    profile = {
        "weapon": "SR",
        "damage_percent": shot_percent,
        "charge_damage_percent": full_charge_percent + converted * 100,
        "rate_of_fire": TRANSFORM_SHOTS / duration,
    }

    def schedule(context, fight_duration):
        return [
            {"start": t, "until_shots": TRANSFORM_SHOTS, "profile": profile}
            for t in context.burst_times.get("red-hood", [])
        ]

    return schedule
```

docstring 재작성: 이중계상 차감·상수 접기 한계 문단을 "세그먼트 창이 기본 SR을 침묵시키고, 덱 차지댐/ATK 버프가 변형샷에 곱해진다(차지속도 변환은 여전히 own-sources-only 상수 — Fienn 시맨틱)"로 교체. registry.py: `_SCHEDULED_NUKE_BUILDERS`에서 "red-hood" 줄 삭제, `_WEAPON_MODE_SCHEDULE_BUILDERS["red-hood"] = lambda sv: build_red_wolf_weapon_mode_schedule(sv)`.

- [ ] **Step 4: 전체 스위트** — red-hood의 기존 총딜 기대값 테스트가 있으면 수치가 (의도대로) 변한다: 정적 차감 제거 + 창 내 기본샷 실제 억제로 순액이 달라짐. **기대값을 갱신하고 커밋 메시지에 사유를 명시**(회귀가 아니라 모델 개선).
- [ ] **Step 5: 커밋** — `git commit -m "encode: red-hood transform migrated to weapon-mode segment (deck buffs now apply)"`

---

### Task 5: snow-white 신규 인코딩

**Files:**
- Create: `backend/app/skill_rules/snow_white.py`
- Modify: `backend/app/skill_rules/registry.py` (import, `_BUILDERS`, `_PER_SHOT_RULE_BUILDERS`, `_PERIODIC_NUKE_BUILDERS`, `_WEAPON_MODE_SCHEDULE_BUILDERS`)
- Test: `backend/tests/test_skill_rules_snow_white.py` (신규)

**Interfaces:**
- Produces: `build_snow_white_rules(values)` (빈 리스트 반환 가능), `build_determination_per_shot_rules(values)`, `snow_white_periodic_nuke(values)`, `build_seven_dwarves_weapon_mode_schedule(values)`

데이터: `data/lootandwaifus/char_snow-white.json` (수집 완료), dotgg 무기 AR 14.71%·60발·1.5s. Lv10 토큰 맵:
- `determination` (skills,0): 01=30(발), 02=82.8(추가딜%), 03=30(중복 발수), 04=8.28(자ATK%), 05=5(초)
- `seven_dwarves_v_vi` (skills,1): 01=144.73(딜%), 02=26.1(크리율%), 03=10(초) — 스킬 cooldown 필드 15.0
- `seven_dwarves_i` (skills,2): 01=5(차지초), 02=499.5(딜%), 03=1000(풀차지%), 04=1(장탄)

- [ ] **Step 1: 실패하는 테스트** — `test_skill_rules_scarlet_black_shadow.py`의 구조(값 픽스처 + 빌더 단위 단언 + SKILL_VALUE_MANIFESTS 등록 확인)를 본떠 작성:

```python
def test_determination_fires_every_30_shots_with_additional_damage():
    rules = build_determination_per_shot_rules(SNOW_WHITE_VALUES)
    assert rules == 형태: [(30, "every", [<pulse 82.8 eligible>, <self atk 0.0828/5s>])]
    # pulse.full_burst_bonus_eligible True ("as additional damage")

def test_seven_dwarves_v_vi_is_cd15_periodic_nuke():
    assert snow_white_periodic_nuke(SNOW_WHITE_VALUES) == {"cooldown": 15.0, "percent": 144.73}

def test_burst_transform_is_single_5s_charged_cannon_shot():
    schedule = build_seven_dwarves_weapon_mode_schedule(SNOW_WHITE_VALUES)
    segments = schedule(SimpleNamespace(burst_times={"snow-white": [20.0]}), 180.0)
    assert segments == [{"start": 20.0, "until_shots": 1, "profile": {
        "weapon": "SR", "damage_percent": 499.5,
        "charge_damage_percent": 1000.0, "charge_time": 5.0}}]
```

- [ ] **Step 2: 실패 확인** — ModuleNotFoundError
- [ ] **Step 3: 구현** — 모듈 골격 (docstring에 반드시: 크리율 26.1%는 "FB 중 사용 시" 조건이라 periodic 틱의 창 판정 경로가 없어 **defer**; 변형샷이 Determination 노멀 카운터에 포함되는지는 엔진 통일 타임라인상 포함됨 — 스펙의 미해결 질문, Fienn 확인 시 조정):

```python
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

SEVEN_DWARVES_V_VI_COOLDOWN = 15.0

SKILL_VALUE_MANIFESTS = {
    "snow-white": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_snow_white",
        "keys": {
            "determination": ("skills", 0),
            "seven_dwarves_v_vi": ("skills", 1),
            "seven_dwarves_i": ("skills", 2),
        },
    },
}


def build_snow_white_rules(values):
    return []


def build_determination_per_shot_rules(values):
    det = values["determination"]
    n = int(float(det["description_value_01"]))
    return [(n, "every", [
        instant_nuke_pulse_rule("per_shot", float(det["description_value_02"]),
                                full_burst_bonus_eligible=True),
        buff_rule("per_shot", [("atk_percent", float(det["description_value_04"]) / 100,
                                "self", float(det["description_value_05"]))]),
    ])]


def snow_white_periodic_nuke(values):
    return {"cooldown": SEVEN_DWARVES_V_VI_COOLDOWN,
            "percent": float(values["seven_dwarves_v_vi"]["description_value_01"])}


def build_seven_dwarves_weapon_mode_schedule(values):
    burst = values["seven_dwarves_i"]
    profile = {
        "weapon": "SR",
        "damage_percent": float(burst["description_value_02"]),
        "charge_damage_percent": float(burst["description_value_03"]),
        "charge_time": float(burst["description_value_01"]),
    }

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": 1, "profile": profile}
                for t in context.burst_times.get("snow-white", [])]

    return schedule
```

registry 등록: `_BUILDERS["snow-white"] = lambda sv: (build_snow_white_rules(sv), None)` (버스트는 무기변형이라 직접 넉 없음 — red-hood 주석 선례), per-shot·periodic·weapon-mode 맵 각각. per-shot 버프의 트리거 문자열은 per-shot 루프가 소비하지 않음(기존 per-shot 빌더들과 동일하게 `"per_shot"` 사용 — 기존 모듈에서 실제 관례 확인 후 맞출 것).

- [ ] **Step 4: 값 조립 하니스 + 전체 스위트** — Run: `C:/Users/fienn/anaconda3/python.exe -m pytest backend/tests/test_skill_value_assembly.py backend/tests -q`. 토큰 번호가 어긋나면 하니스가 잡는다 — 그때만 `drop_tokens` 추가(스펙 규칙).
- [ ] **Step 5: 커밋** — `git commit -m "encode: Snow White - burst cannon via weapon-mode segment"`
- [ ] **Step 6: docs/encoded-nikkes.md에 행 추가** (⚠ — 크리율 rider·Pierce 미모델 명시) 후 커밋.

---

### Task 6: maxwell 신규 인코딩

**Files:**
- Create: `backend/app/skill_rules/maxwell.py` · Test: `backend/tests/test_skill_rules_maxwell.py` · Modify: registry.py

**Interfaces:**
- Produces: `build_maxwell_rules(values)`, `build_pierce_shot_weapon_mode_schedule(values)`

토큰 맵: `straight_shot` (skills,0): 01=2(인원), 02=4.48(차지속도%), 03=10(초), 04=43.1(ATK%), 05=10(초). `pierce_shot` (skills,2): 01=2(차지초), 02=813.42, 03=300, 04=1. `spark_shot`(skills,1)은 **인코딩하지 않음** — "적 5기 초과" 조건이 레이드 보스(1기)에서 항상 거짓 (docstring에 명시).

- [ ] **Step 1: Fienn 질문 (AskUserQuestion)** — Straight Shot의 "2 allies with the highest final ATK"에 **maxwell 자신이 포함되는가?** (포함이면 자기 변형 차지 5→2초 단축에 자기 버프가 걸리는 셈이라 딜 차이가 큼.) 포함 → `context.top_atk_slugs`가 캐스터를 제외하므로 커스텀 액션으로 자신 포함 랭킹; 제외 → 기존 `highest_atk_buff_rule("full_burst_enter", 2, ...)` 그대로.
- [ ] **Step 2: 실패하는 테스트** — snow-white와 동형: straight_shot 룰 형태(트리거 full_burst_enter, (charge_speed_percent, 0.0448, 10.0)·(atk_percent, 0.431, 10.0)), 변형 스케줄 `{"start": t, "until_shots": 1, "profile": {"weapon": "SR", "damage_percent": 813.42, "charge_damage_percent": 300.0, "charge_time": 2.0}}`.
- [ ] **Step 3: 실패 확인 → 구현** — Step 1 답변대로 룰 작성; 나머지는 snow-white 골격과 동일(값·이름만 교체). registry 3맵 등록(per-shot 없음, periodic 없음).
- [ ] **Step 4: 하니스 + 전체 스위트 통과**
- [ ] **Step 5: 커밋** — `git commit -m "encode: Maxwell - Pierce Shot cannon via weapon-mode segment"` + encoded-nikkes.md 행(⚠ — Spark Shot inert·Pierce 미모델).

---

### Task 7: laplace-signature 신규 슬러그

**Files:**
- Create: `backend/app/skill_rules/laplace_signature.py` (julia_signature.py 선례) · Test: `backend/tests/test_skill_rules_laplace_signature.py` · Modify: registry.py (import + `_BUILDERS`·`_PER_SHOT_RULE_BUILDERS`·`_WEAPON_MODE_SCHEDULE_BUILDERS`)

**Interfaces:**
- Produces: `build_laplace_signature_rules(values)`, `laplace_buster_signature_burst_percent(values)`, `build_hero_bomber_signature_per_shot_rules(values)`, `build_buster_weapon_mode_schedule(values)`, `BUSTER_SHOTS = 93`

데이터: `data/lootandwaifus/char_laplace.json`의 `dollskills` (존재 확인 완료). Fienn 실측(2026-07-19): 변형 10초 창 = First 1회 + 노멀 93회. 토큰 맵:
- `hero_vision` (dollskills,0): 01=3.57, 02=5, 03=15 — Explosion Radius, **inert** (radius 미모델, docstring)
- `hero_bomber` (dollskills,1): 01=132.45(풀차지 추가딜%), 02=14.78(파츠 — defer)
- `laplace_buster` (dollskills,2): 원시 토큰 [1455.72, 22.2, 10, 1, 2, 11.9] — `drop_tokens: {"laplace_buster": (3, 4)}`(Additional Effect 번호 1·2 제거) → 01=1455.72(First%), 02=22.2(노멀%), 03=10(초), 04=11.9(맥스스택 true%)

- [ ] **Step 1: Fienn 질문 (AskUserQuestion)** — Buster의 "Hero Vision 맥스스택 시 11.9% true"는 어느 히트에 붙나요? (a) 변형 노멀 틱마다 +11.9% true 추가 히트 (b) 별개 단발 (c) 정보 부족 — defer. 그리고 "Normal damage is applied as true damage at max stacks" — RL 케이던스상 첫 ~5발 내 맥스 도달·15초 수명이라 상시 맥스로 보고 **틱 전체를 true로 고정**(red-hood Glaring 정상상태 선례)해도 되는지 확인.
- [ ] **Step 2: 실패하는 테스트** — 매니페스트(등록·data_slug="laplace"·drop_tokens) 확인 + 버스트 percent 1455.72 + per-shot `[(1, "every_outside_full_burst", [<pulse 132.45 eligible>])]` + 스케줄 `{"start": t, "until_shots": 93, "profile": {"weapon": "RL", "damage_percent": 22.2, "rate_of_fire": 9.3, "damage_type": "true"}}` (rate = BUSTER_SHOTS / dv_03; damage_type은 Step 1 답변 반영).
- [ ] **Step 3: 실패 확인 → 구현** — julia_signature.py의 매니페스트/모듈 구조를 본뜬다. docstring 필수 내용: Fienn 실측 앵커(1+93/10s), Hero Bomber 트리거가 base(last_bullet)와 달리 풀차지마다임, 변형 창(자기 B3 버스트=FB 창 10초)엔 풀차지가 없어 `every_outside_full_burst`가 인게임과 일치, ammo/parts/radius defer 목록. registry: `_BUILDERS["laplace-signature"] = lambda sv: (build_laplace_signature_rules(sv), laplace_buster_signature_burst_percent(sv))`.
- [ ] **Step 4: 로스터 노출 확인** — `grep -rn "julia-signature" backend/app backend/tests frontend/src`로 julia-signature가 유저 로스터에 노출되는 경로(별도 로스터 슬러그인지, frontend/src/lib/resourceIdSlugMap.ts에 항목이 필요한지)를 확인하고 laplace-signature를 동일하게 처리.
- [ ] **Step 5: 하니스 + 전체 스위트 통과 → 커밋** — `git commit -m "encode: Laplace signature - Buster transform via weapon-mode segment (1+93 measured)"` + encoded-nikkes.md 행.

---

### Task 8: 문서 갱신 + 마무리 검증

**Files:**
- Modify: `docs/roadmap.md` (Phase 3 백로그 — 무기변형 카운트 갱신, laplace 시그니처 항목 정정), `docs/engine-gaps.md` ("이미 만든 것"에 weapon-mode segments 추가, "남은 방향"에서 상태머신/무기변형 항목 갱신 — 잔여: cinderella 듀얼·rapi·SWHA = 계획 2), `docs/encoded-nikkes.md` (red-hood 비고 갱신), `docs/superpowers/specs/2026-07-18-weapon-transform-design.md` (상태: v1 구현 완료 표기), `nikke-skill-encoding` 스킬의 `references/engine-capabilities.md`·`special-mechanics.md` (weapon-mode segments 능력·패턴 항목 추가 — Phase C 배치의 서술 스타일 준수)

- [ ] **Step 1: 위 문서들 갱신** (각 파일의 기존 서술 밀도·형식 유지)
- [ ] **Step 2: engine-test-runner로 전체 스위트 최종 실행** (`/test-engine`) — 798+신규 전부 PASS 확인
- [ ] **Step 3: 커밋** — `git commit -m "docs: weapon-mode segments v1 landed - backlog counters updated"`
- [ ] **Step 4: `/document`로 결정 기록** — docs-keeper에 전달: (1) 무기 패스 통일(전 유닛이 generate_segmented_shots 경유) 결정과 비트 동일성 근거 (2) 명시적 rate_of_fire엔 케이던스 버프 미적용(실측 앵커 원칙) (3) laplace-signature 듀얼슬러그 신설 (4) 계획 2 백로그(cinderella-crystal-wave-mg/-snipe 듀얼 + rapi FB창 노출 + SWHA 검증 패스)
- [ ] **Step 5: `wip/scaffolding` 머지** — 메인 체크아웃이 깨끗한지 확인 후 `git -C C:/Users/fienn/Desktop/NikkeDeckBuilder merge worktree-encoding-gap10-scarlet`

---

## 계획 2 백로그 (이 계획에 포함되지 않음)

세그먼트 프리미티브와 독립적인 나머지 스펙 범위 — 별도 계획으로 작성 예정:
- **cinderella-crystal-wave-mg / -snipe 듀얼슬러그** (정적 프로필 2벌 + 모드별 FB 넉/버프 + 덱 탐색 상호 배제 + Snipe 프로필 세부 Fienn 확인)
- **rapi-red-hood** (`scheduled_nukes` context에 `full_burst_windows` 노출 + 120노멀 프로젝타일 발사→FB 폭발 모듈 계산 + 원소상성/버스트 분기 Fienn 확인)
- **snow-white-heavy-arms 검증 패스** (기존 per-shot + multi-hit 프리미티브로 풀리는지)
