# Phase C: Laplace 변신 루프 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Laplace: Ultimate Hero의 핵심 DPS인 차지-카운트 무기변형 루프를 기존 weapon-mode 세그먼트로 모델링하고, Over Energy 단계와 Mjolnir의 단계 비례 추가딜을 붙인다.

**Architecture:** 신규 엔진 프리미티브를 만들지 않는다. 이미 있는 opt-in 경로 3개를 조합한다 — `weapon_mode_schedules`(변신 창), `scheduled_nukes`(단계별 버스트 추가딜), 미래 시각 `registry.add`(단계 전이 시점 버프). 유일한 엔진 변경은 스케줄 함수가 라이브 max ammo를 읽게 하는 **컨텍스트 주입 한 줄**이다.

**Tech Stack:** Python 3, pytest, `app.attack_rate.generate_segmented_shots`, `app.raid_simulator`.

## Global Constraints

- 워크트리 `.claude/worktrees/skill-encoding`, 브랜치 `wip/skill-encoding`. 테스트는
  `cd backend && PYTHONIOENCODING=utf-8 "C:/Users/fienn/anaconda3/python.exe" -m pytest ...`
- **딜 계산 핫패스 금지**(Phase B와 동일 제약).
- **변신 주기/창을 상수로 박지 않는다** — [최대 장탄 수 증가] 오버로드에 따라 변하므로
  반드시 라이브 max ammo에서 유도한다(Fienn 명시).

## Fienn 실측 앵커 (2026-07-24)

- Warm Up 5회 풀차지 = **4.0초**(1.0+0.9+0.8+0.7+0.6), 그 직후 변신.
- 변신 무기: **SMG 케이던스 20발/초**, 샷당 **9.45%**, **차지대미지 미적용**.
- 탄창 전부 소모 → 재장전 → RL 복귀.
- Over Energy: **변신 2회마다 단계 +1**, 최대 4단계(Max HP +2/+3/+7/+10.5%).
- 기본 무기(ShiftyPad 원본, Fienn 확인): RL, max_ammo **120**, damage **2.5%**,
  charge_time **1.0s**, reload_time **2.5s**, full charge **250%**.
- 검증: 주기 = 4.0(빌드) + 120/20(창 6.0) + 2.5(재장전) = **12.5초** = 실측 "약 12.5초마다 변신". ✅

## 유도식

```
window_shots  = max(1, round(base_max_ammo * (1 + max_ammo_percent)))   # attack_rate와 동일
window_sec    = window_shots / 20
period        = 4.0 + window_sec + reload_time
transform_n   = 4.0 + (n-1) * period          # n = 1,2,... while < fight_duration
stage(t)      = min(4, floor(완료된 변신 수(t) / 2))
stage s 도달 = transform_{2s} + window_sec    # 2s번째 창이 끝나는 순간
```

---

### Task 1: 라이브 max ammo 플러밍 + 헬퍼 refresh_group

**Files:**
- Modify: `backend/app/raid_simulator.py` (`schedule_fn` 호출 직전)
- Modify: `backend/app/skill_rules/_helpers.py` (`max_hp_scaled_atk_rule`)
- Test: `backend/tests/test_weapon_mode_schedule_max_ammo.py` (신규)

**Interfaces:**
- Produces: `context.max_ammo_percent_at(time) -> float` — 스케줄 함수 호출 직전에
  **그 슬러그용으로** 주입된다. 스케줄 함수 밖에서 읽으면 안 된다(슬러그마다 덮어씀).
- Produces: `max_hp_scaled_atk_rule(..., refresh_group=None)` — `refreshing=True`면 필수.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
from app.raid_simulator import simulate_raid


def test_schedule_fn_can_read_live_max_ammo_percent():
    seen = {}

    def schedule(context, fight_duration):
        seen["pct"] = context.max_ammo_percent_at(0.0)
        return []

    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    base_stats = {m["slug"]: {"atk": 1000, "def": 0, "max_hp": 0} for m in deck}
    simulate_raid(
        deck, {s: [] for s in base_stats}, burst_damage_percents={},
        base_stats=base_stats, enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0,
        weapon_stats={"attacker": {
            "weapon": "SMG", "damage_percent": 10.0, "charge_damage_percent": 100.0,
            "charge_time": 0.0, "max_ammo": 120, "reload_time": 1.0,
        }},
        weapon_mode_schedules={"attacker": schedule},
        base_crit_rate=0.0,
    )
    assert seen["pct"] == 0.0
```

- [ ] **Step 2: 실패 확인** → `AttributeError: 'SquadContext' object has no attribute 'max_ammo_percent_at'`

- [ ] **Step 3: 주입 한 줄을 추가한다**

`raid_simulator.py`에서 `schedule_fn = weapon_mode_schedules.get(slug)` 바로 위에:

```python
        # 스케줄 함수가 라이브 최대 장탄을 읽을 수 있게 이 슬러그용 조회를 노출한다
        # (Laplace의 변신 창 길이는 [최대 장탄 수 증가]에 비례한다). 슬러그마다
        # 덮어쓰므로 스케줄 함수 안에서만 유효하다.
        context.max_ammo_percent_at = max_ammo_percent_at
```

- [ ] **Step 4: `max_hp_scaled_atk_rule`에 `refresh_group`을 추가한다**

시그니처를 `(trigger, percent, scope, duration, base_max_hp, condition=None, refreshing=False, refresh_group=None)`로 바꾸고, Effect 생성을
`Effect("flat_atk", live_max_hp * percent, scope, duration, caster_slug, refresh_group)`로 바꾼다.

- [ ] **Step 5: 통과 + 전체 스위트 + 커밋**

```bash
git commit -m "Expose live max-ammo to weapon-mode schedules; add refresh_group to the Max-HP ATK helper"
```

---

### Task 2: 변신 창 세그먼트

**Files:**
- Modify: `backend/app/skill_rules/laplace_ultimate_hero.py`
- Modify: `backend/app/skill_rules/registry.py` (`get_weapon_mode_schedules`)
- Modify: `backend/tests/test_skill_rules_laplace_ultimate_hero.py`

**Interfaces:**
- Produces: `build_laplace_transform_schedule(values) -> schedule(context, fight_duration)`
- Produces: `laplace_transform_plan(values, context, fight_duration) -> (times, window_shots, window_sec)`
  — Task 3/4가 같은 스케줄을 재계산하지 않도록 공유하는 순수 함수.

- [ ] **Step 1: 테스트를 쓴다** — 120발/오버로드 0%에서 창 120발·20/sec·9.45%·차지댐 없음,
  첫 변신 4.0초, 주기 12.5초, 180초 전투에서 시각이 `4.0, 16.5, 29.0, ...`인지.
  그리고 max_ammo_percent 0.5(=180발)일 때 창 9.0초·주기 15.5초로 **유도**되는지.

- [ ] **Step 2: 실패 확인**

- [ ] **Step 3: 구현** — 모듈에 상수와 순수 함수를 두고 스케줄을 만든다:

```python
SMG_RATE_OF_FIRE = 20.0        # Fienn 실측: 변신 무기는 SMG 케이던스
WARM_UP_BUILD_SECONDS = 4.0    # Fienn 실측: 풀차지 5회(1.0+0.9+0.8+0.7+0.6)


def laplace_transform_plan(values, context, fight_duration):
    weapon = values["caster_weapon_stats"]
    pct = context.max_ammo_percent_at(0.0)
    shots = max(1, round(int(weapon["max_ammo"]) * (1 + pct)))
    window = shots / SMG_RATE_OF_FIRE
    period = WARM_UP_BUILD_SECONDS + window + float(weapon["reload_time"])
    times, t = [], WARM_UP_BUILD_SECONDS
    while t < fight_duration:
        times.append(t)
        t += period
    return times, shots, window
```

스케줄은 각 시각에 `{"start": t, "until_shots": shots, "profile": profile}`을 낸다.
profile은 `{"weapon": "SMG", "damage_percent": 9.45, "rate_of_fire": SMG_RATE_OF_FIRE}` —
**`charge_damage_percent`를 넣지 않는다**(Fienn: SMG 대미지에 차지댐 미적용).

`registry.py`의 `get_weapon_mode_schedules`에 슬러그 분기를 추가한다.

- [ ] **Step 4: 통과 + 전체 스위트 + 커밋**

---

### Task 3: Over Energy 단계 — Max HP 부여 + Electric Power ATK 재적용

**Files:** 위와 동일

- [ ] **Step 1: 테스트** — 180초 전투에서 단계 1~4가 각각
  `transform_{2s} + window` 시각에 서고, 그 시각부터 `flat_max_hp`가
  해당 단계 값(2/3/7/10.5%)이 되며(누적 아님, 아래 가정), 같은 시각에
  Electric Power의 `flat_atk`가 커진 Max HP로 재계산되는지.

- [ ] **Step 2: 실패 확인**

- [ ] **Step 3: 구현** — `battle_start` 룰이 미래 시각 효과를 미리 등록한다
  (`periodic_rules`의 pre-add 선례와 동형, replay-safe):

```python
OVER_ENERGY_TRANSFORMS_PER_STAGE = 2   # Fienn 실측
OVER_ENERGY_MAX_STAGE = 4
```

각 단계 s에 대해 `at = times[2s-1] + window`에서
`add_refreshing(Effect("flat_max_hp", caster_max_hp*stage_pct, "self", None, slug, "over_energy_stage"), at)`,
이어서 그 시점 라이브 Max HP로 Electric Power ATK를
`add_refreshing(..., refresh_group="electric_power")` 재적용.
battle_start의 최초 Electric Power 버프도 **같은 refresh_group으로 refreshing** 등록해야
단계 재적용이 중복 합산되지 않는다(Task 1에서 헬퍼에 `refresh_group` 추가한 이유).

**가정(문서화 필수):** 단계 Max HP 2/3/7/10.5%는 **누적이 아니라 그 단계의 값으로 대체**된다고
읽었다(escalating tier 관례). 원문이 누적이면 값만 바꾸면 된다 — Fienn 확인 대상.

- [ ] **Step 4: 통과 + 전체 스위트 + 커밋**

---

### Task 4: Mjolnir의 단계 비례 추가딜

**Files:** 위와 동일 + `registry.py`의 `scheduled_nukes` 맵

- [ ] **Step 1: 테스트** — 각 버스트에서 `934.76% × 그 시점 단계`가 히트로 기록되고,
  단계 0인 초기 버스트는 히트가 없는지.

- [ ] **Step 2: 실패 확인**

- [ ] **Step 3: 구현** — `scheduled_nukes`는 스펙당 percent가 하나이므로 **단계별로 스펙을 나눈다**:
  s = 1..4에 대해 `{"percent": 934.76*s, "schedule": <그 시점 단계가 정확히 s인 자기 버스트 시각들>,
  "full_burst_bonus_eligible": True}`. 버스트 시각은 `context.burst_times[slug]`,
  단계는 Task 3과 같은 `laplace_transform_plan`으로 계산 —
  **시점별 정확 단계**(Fienn 승인).
  "as additional damage"라 `full_burst_bonus_eligible=True`(velvet 선례).

- [ ] **Step 4: 통과 + 전체 스위트 + 커밋**

---

### Task 5: docstring / 문서 갱신

- [ ] Laplace docstring의 "WARNING - THIN ENCODING" 경고를 제거하고 modeled/deferred 목록을 갱신
  (남는 deferred: Warm Up 차지속도 버프 자체 — 세그먼트 케이던스 실측에 이미 반영,
  변신 종료 후 재장전 공백 동안 기본 무기가 계속 발사되는 근사, 단계 Max HP 누적/대체 가정).
- [ ] `docs/engine-gaps.md`의 gap #13을 **해소**로 표시 — 일반 프리미티브를 만든 게 아니라
  기존 세그먼트 + 실측 앵커로 우회했다는 점을 명시.
- [ ] `docs/encoded-nikkes.md`에서 Laplace를 🔶 → ✅/⚠로 승격.
- [ ] 전체 스위트 그린 후 커밋.

## Phase C 완료 기준

- [ ] 변신 창이 라이브 max ammo에서 유도되고, 120발에서 주기 12.5초로 실측과 일치
- [ ] 단계별 Max HP + Electric Power 재적용 + Mjolnir 단계 추가딜 테스트 그린
- [ ] 전체 스위트 그린
- [ ] Fienn 보고: Laplace 총딜이 변신 루프 도입 전후로 얼마나 올랐는지
