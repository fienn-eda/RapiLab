# Weapon-Transform 계획 2 (cinderella 듀얼 · rapi 발사기 · SWHA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** weapon-transform 스펙의 잔여 범위 3건을 착지한다 — cinderella-crystal-wave-mg/-snipe 듀얼모드 슬러그(정적 프로필 2벌 + 탐색 상호 배제), rapi-red-hood 120노멀 프로젝타일 발사기(`scheduled_nukes` + FB 창 노출), snow-white-heavy-arms 인코딩(per-shot + 세그먼트 조합).

**Architecture:** 엔진 확장은 전부 소규모다: ① `scheduled_nukes` context에 `full_burst_windows`/`core_hittable` 노출 ② `projectile_attachment` 데미지 타입+스탯(기존 explosion과 평행) ③ 듀얼모드 로스터 확장(1 state → N spec) + 탐색 상호 배제 필터 ④ ShotRecord `in_segment` 플래그 + per-shot 세그먼트 게이팅 모드 2종. 유닛 로직은 전부 모듈이 결정론 계산하고 엔진은 방출만 한다(기존 분업 유지). 스펙: `docs/superpowers/specs/2026-07-18-weapon-transform-design.md` (v1은 2026-07-19 착지, 이 계획이 "계획 2로 이동" 항목을 소비).

**Tech Stack:** Python (backend/), pytest. 테스트는 **반드시 `backend/` 디렉터리에서** `C:/Users/fienn/anaconda3/python.exe -m pytest tests -q` (레포 루트에서 돌리면 `app` 임포트 실패 — `python -m pytest`가 CWD를 sys.path에 넣는 구조라 CWD가 backend여야 함).

## Global Constraints

- 작업 위치: 워크트리 `.claude/worktrees/transform-plan2` (branch `worktree-transform-plan2`, `wip/scaffolding` 96dd9b9에서 분기). `scripts/sync_worktree_data.py`는 이미 실행됨(223파일 동기화, 재실행은 no-op).
- 베이스라인: **858 passed** (2026-07-19 확인). 태스크마다 전체 스위트 green이 회귀 기준 — 기존 유닛(세그먼트/스케줄 미등록)의 출력은 한 자리도 변하면 안 된다.
- 스킬 수치 하드코딩 금지 — `SKILL_VALUE_MANIFESTS` + `description_value_NN` 슬롯(`backend/app/skill_values.py`). 이 계획의 토큰 맵은 실제 tokenizer(`extract_lootandwaifus_slots`/`dotgg_slots`)로 추출한 값이다. 어긋나면 `test_skill_value_assembly.py` 하니스가 잡는다.
- 커밋 메시지에 따옴표(`"`) 금지 — PowerShell 인자 재구성이 깨뜨림. 필요하면 `git commit -F <파일>`.
- 메커니즘이 모호하면 **Fienn에게 질문**하고 추측하지 않는다. 이 계획에서 이미 받은 판정(2026-07-19): ① cinderella Snipe 풀차지는 velvet처럼 **실제 1발 발사**, "40발 소모"는 탄소모 집계용 회계 ② rapi 프로젝타일은 **매 120노멀마다 부착딜 반복**, 누적분이 **FB 진입 시 일괄 폭발** ③ SWHA sequential **전탄 보스 적중** ④ SWHA 4.2% 받는피해 디버프는 **상시 근사(권장)**.
- 남은 Fienn 확인 2건은 태스크 안의 질문 스텝으로: cinderella Snipe **재장전 시간**(텍스트 부재), cinderella-crystal-wave의 **resource_id**.
- "as additional damage" 텍스트 → `full_burst_bonus_eligible=True`, 그 외 "as damage"는 False (기존 Fienn 규칙). 이 계획의 FB진입 넉들은 전부 "as damage"라 False.

---

### Task 1: scheduled_nukes context 노출 확장 2건 (`full_burst_windows` · `core_hittable`)

**Files:**
- Modify: `backend/app/squad_engine.py` (SquadContext `__init__` ~48행 부근, 조건 헬퍼 ~197행 부근)
- Modify: `backend/app/raid_simulator.py` (context 생성 ~323행, scheduled_nukes 직전 ~909행)
- Test: `backend/tests/test_squad_engine.py`, `backend/tests/test_raid_simulator.py` (기존 파일에 추가)

**Interfaces:**
- Produces: `context.full_burst_windows: list[tuple[float, float]]` (scheduled_nukes/weapon_mode 스케줄 평가 시점에 채워짐, 기본 `[]`) · `SquadContext(core_hittable=False)` 필드 · `squad_engine.boss_core_hittable() -> condition` (Task 3의 rapi 폭발 스케줄, Task 5의 MG 변종 FB넉이 소비)

- [ ] **Step 1: 실패하는 테스트 작성** — `backend/tests/test_raid_simulator.py`에 (기존 scheduled_nukes 테스트 스타일을 따라):

```python
def test_scheduled_nuke_context_exposes_full_burst_windows():
    seen = {}

    def schedule(context, fight_duration):
        seen["windows"] = list(context.full_burst_windows)
        return []

    simulate_raid(
        deck=[{"slug": "gunner", "burst_tier": 3, "element": "Iron",
               "cooldown": 40.0, "weapon": "SR"}],
        rules_by_slug={}, burst_damage_percents={},
        base_stats={"gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=60.0,
        scheduled_nukes={"gunner": [{"schedule": schedule, "percent": 100.0}]},
    )
    assert seen["windows"], "full burst windows must be visible to schedules"
    assert all(end > start for start, end in seen["windows"])
```

`backend/tests/test_squad_engine.py`에:

```python
def test_boss_core_hittable_condition_reads_context_flag():
    from app.squad_engine import SquadContext, SquadMember, boss_core_hittable
    cond = boss_core_hittable()
    members = [SquadMember("a", 3, "Iron")]
    assert cond(SquadContext(members, core_hittable=True), "a") is True
    assert cond(SquadContext(members), "a") is False
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_raid_simulator.py -k full_burst_windows -v tests/test_squad_engine.py -k core_hittable`
Expected: AttributeError (`full_burst_windows` 없음) / ImportError (`boss_core_hittable` 미정의)

- [ ] **Step 3: 구현** — `squad_engine.py`의 `SquadContext.__init__`에 (part_destructible 처리와 나란히):

```python
        # whether the boss's core is exploitable this sim (raid_simulator's
        # core_hittable flag), so a rule gated on core existence (e.g.
        # Cinderella: Crystal Wave's MG-mode core-strike nuke) can read it.
        self.core_hittable: bool = core_hittable
        # Full Burst [start, end) windows from the burst-cycle pass, so a
        # scheduled_nukes schedule can anchor on FB entry (e.g. Rapi: Red
        # Hood's projectile explosions). Filled by raid_simulator right
        # before schedules run; empty for contexts without a burst cycle.
        self.full_burst_windows: list[tuple[float, float]] = []
```

시그니처에 `core_hittable: bool = False` 추가. 조건 헬퍼 (기존 `boss_is_element` 옆에):

```python
def boss_core_hittable() -> Callable[[SquadContext, str], bool]:
    """True when the boss has an exploitable core (sim-level core_hittable
    flag) - for effects whose target is "enemies with activated cores"."""

    def condition(context: SquadContext, caster_slug: str) -> bool:
        return context.core_hittable

    return condition
```

`raid_simulator.py`: ① 323행 `SquadContext(...)` 호출에 `core_hittable=core_hittable,` 추가 ② 909행 `context.shot_times = shot_times_by_slug` 바로 다음 줄에 `context.full_burst_windows = full_burst_windows` 추가. **주의:** `weapon_mode_schedules`는 568행(FB 창 계산) 뒤·무기 패스 안에서 평가되므로, FB 창을 무기 스케줄도 읽게 하려면 대입을 573행(무기 패스 시작) 앞으로 올린다 — scheduled_nukes보다 앞이므로 두 소비자 모두 커버된다.

- [ ] **Step 4: 신규 + 전체 스위트 통과 확인**

Run: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests -q`
Expected: 858+2 전부 PASS (기존 출력 불변 — 노출만 추가)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/squad_engine.py backend/app/raid_simulator.py backend/tests/test_squad_engine.py backend/tests/test_raid_simulator.py
git commit -m "engine: expose full_burst_windows and core_hittable on SquadContext"
```

---

### Task 2: `projectile_attachment` 데미지 타입 + 스탯

**Files:**
- Modify: `backend/app/damage_formula.py` (`calculate_damage` 시그니처 + damage_up 합산, 76행 `projectile_explosion_damage_up` 옆)
- Modify: `backend/app/raid_simulator.py` (`_TYPE_EXTRA_STATS` 263행, `_BUNDLE_STATS` 274행)
- Test: `backend/tests/test_raid_simulator.py`

**Interfaces:**
- Produces: 스탯 `projectile_attachment_damage_up` — `damage_type="projectile_attachment"` 인스턴스의 damage_up 버킷에 합산 (Task 3의 부착딜 + 부착딜 버프가 소비)

- [ ] **Step 1: 실패하는 테스트 작성**:

```python
def test_projectile_attachment_damage_up_scales_attachment_typed_nuke():
    from app.effects import Effect
    from app.squad_engine import SkillRule

    def grant(context, caster_slug, time, registry):
        registry.add(Effect("projectile_attachment_damage_up", 1.5, "self", None, caster_slug),
                     applied_at=time)

    kwargs = dict(
        deck=[{"slug": "gunner", "burst_tier": 3, "element": "Iron",
               "cooldown": 40.0, "weapon": "SR"}],
        burst_damage_percents={},
        base_stats={"gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        scheduled_nukes={"gunner": [
            {"schedule": lambda c, d: [5.0], "percent": 100.0,
             "damage_type": "projectile_attachment"}]},
    )
    plain = simulate_raid(rules_by_slug={}, **kwargs)
    buffed = simulate_raid(
        rules_by_slug={"gunner": [SkillRule(trigger="battle_start", action=grant)]}, **kwargs)
    nuke = lambda r: [e for e in r["damage_log"] if e["source"] == "scheduled"][0]["damage"]
    assert nuke(buffed) == pytest.approx(nuke(plain) * 2.5)
```

- [ ] **Step 2: 실패 확인** — Run: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_raid_simulator.py -k attachment -v`
Expected: FAIL (스탯이 어느 버킷에도 안 들어가 배수 1.0)

- [ ] **Step 3: 구현** — `damage_formula.py`: `calculate_damage`에 파라미터 `projectile_attachment_damage_up=0.0` 추가(76행 옆), 97–105행 damage_up 합에 `+ projectile_attachment_damage_up` 추가. `raid_simulator.py`: 263행 맵에 `"projectile_attachment": ["projectile_attachment_damage_up"],` 추가, `_BUNDLE_STATS` 튜플에 `"projectile_attachment_damage_up",` 추가. (타입별 extra 스탯이 damage 계산에 전달되는 기존 배선을 따른다 — `projectile_explosion` 처리부를 grep해서 동형으로.)

- [ ] **Step 4: 전체 스위트 통과 확인** — Run: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests -q`

- [ ] **Step 5: 커밋**

```bash
git add backend/app/damage_formula.py backend/app/raid_simulator.py backend/tests/test_raid_simulator.py
git commit -m "engine: projectile_attachment damage type and damage-up stat"
```

---

### Task 3: rapi-red-hood 프로젝타일 발사기 인코딩

**Files:**
- Modify: `backend/app/skill_rules/rapi_red_hood.py`
- Modify: `backend/app/skill_rules/registry.py` (`_SCHEDULED_NUKE_BUILDERS`에 등록, rapi `_BUILDERS` 엔트리에 rider 룰 추가)
- Test: `backend/tests/test_skill_rules_rapi_red_hood.py` (기존 파일 확장)

**Interfaces:**
- Consumes: Task 1 `context.full_burst_windows`, Task 2 `projectile_attachment` 타입
- Produces: `build_attachable_projectiles_scheduled_nukes(values) -> [spec, spec]`, `build_power_of_inheritance_rules(values) -> [SkillRule]`

토큰 맵 (dotgg — 기존 매니페스트 소스, 실측 덤프 완료):
- `attachable_projectiles`: 01=120(발사 요구 노멀 수), 02=88.11(부착딜%), 03=88.11(폭발딜%), 04=1(Max Ammunition — Fienn 판정으로 누적 모델이라 미사용), 05=150.72(부착딜▲%, 기존 defer 해제), 06=100.6(폭발딜▲%, 이미 모델됨)
- `power_of_inheritance`: 05=2808(이미 모델), 06=421.2(부착딜▲ 창%), 07=10(초), 08=60(요구치▼), 09=10(초)

확정 시맨틱 (Fienn 2026-07-19): 매 120노멀마다 부착딜 발생(카운터는 발사 시 리셋), 부착된 프로젝타일은 **누적**되어 다음 FB 진입 시 **일괄 폭발**(부착 1건당 폭발딜 1히트). 버스트(Stage 3) 후 10초는 요구치가 120−60=60.

- [ ] **Step 1: 실패하는 테스트 작성** — 기존 파일의 픽스처 스타일(VALUES dict)로:

```python
def test_projectile_launcher_attaches_every_120_shots_and_explodes_on_fb_entry():
    specs = build_attachable_projectiles_scheduled_nukes(RAPI_VALUES)
    attach, explosion = specs
    assert attach["percent"] == 88.11 and attach["damage_type"] == "projectile_attachment"
    assert explosion["percent"] == 88.11 and explosion["damage_type"] == "projectile_explosion"

    context = SimpleNamespace(
        shot_times={"rapi-red-hood": [float(i) / 10 for i in range(1, 251)]},  # 0.1s 간격 250샷 (t=0.1~25.0)
        burst_times={"rapi-red-hood": []},
        full_burst_windows=[(30.0, 40.0)],
    )
    # 120번째(t=12.0)·240번째(t=24.0)에서 부착 — 둘 다 FB(30.0) 진입 시 일괄 폭발
    times = attach["schedule"](context, 180.0)
    assert times == [12.0, 24.0]
    assert explosion["schedule"](context, 180.0) == [30.0, 30.0]


def test_projectile_requirement_drops_to_60_inside_own_burst_window():
    specs = build_attachable_projectiles_scheduled_nukes(RAPI_VALUES)
    attach = specs[0]
    shots = [float(i) / 10 for i in range(1, 1201)]          # 0.1s 간격 120초
    context = SimpleNamespace(
        shot_times={"rapi-red-hood": shots},
        burst_times={"rapi-red-hood": [0.05]},               # 시작 직후 버스트 → 10초 창
        full_burst_windows=[],
    )
    times = attach["schedule"](context, 180.0)
    assert times[0] == 6.0     # 창(0.05~10.05) 안: 60번째 샷에서 발사
    assert times[1] == 18.0    # 리셋 후 60카운트 도달 시각 12.0은 창 밖 → 120 요구 복원, 120카운트 = t=18.0


def test_power_of_inheritance_burst_rider_buffs_attachment_window():
    rules = build_power_of_inheritance_rules(RAPI_VALUES)
    # own_burst_activate 트리거 1건: projectile_attachment_damage_up 4.212 / 10s self
    assert len(rules) == 1 and rules[0].trigger == "own_burst_activate"
```

- [ ] **Step 2: 실패 확인** — Run: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_skill_rules_rapi_red_hood.py -v`
Expected: ImportError

- [ ] **Step 3: 구현** — `rapi_red_hood.py`에 추가:

```python
def build_attachable_projectiles_scheduled_nukes(values: dict) -> list[dict]:
    """The 120-normal-attack projectile launcher (Fienn semantics, 2026-07-19):
    every time the shot counter reaches the requirement it fires an attaching
    projectile (attachment damage lands at that shot's time, counter resets),
    attachments ACCUMULATE, and every pending attachment explodes together on
    the next Full Burst entry (one explosion hit per attachment). The Stage 3
    burst lowers the requirement by 60 for 10s (windows from own burst times).
    Attachment/explosion hits are damage-typed so the matching Damage-Up stats
    (S2's permanent 150.72%/100.6%, the burst's windowed 421.2%) multiply them
    in phase 2 - nothing is folded into the percents here."""
    proj = values["attachable_projectiles"]
    burst = values["power_of_inheritance"]
    base_requirement = int(float(proj["description_value_01"]))
    attach_percent = float(proj["description_value_02"])
    explosion_percent = float(proj["description_value_03"])
    requirement_cut = int(float(burst["description_value_08"]))
    cut_duration = float(burst["description_value_09"])

    def attach_times(context, fight_duration):
        shots = context.shot_times.get("rapi-red-hood", [])
        windows = [(t, t + cut_duration)
                   for t in context.burst_times.get("rapi-red-hood", [])]
        times, count = [], 0
        for t in shots:
            count += 1
            requirement = base_requirement - (
                requirement_cut if any(s <= t < e for s, e in windows) else 0)
            if count >= requirement:
                times.append(t)
                count = 0
        return times

    def explosion_times(context, fight_duration):
        entries = [start for start, _end in context.full_burst_windows]
        times = []
        for attached_at in attach_times(context, fight_duration):
            next_entry = next((s for s in entries if s > attached_at), None)
            if next_entry is not None:
                times.append(next_entry)
        return times

    return [
        {"schedule": attach_times, "percent": attach_percent,
         "damage_type": "projectile_attachment"},
        {"schedule": explosion_times, "percent": explosion_percent,
         "damage_type": "projectile_explosion"},
    ]


def build_power_of_inheritance_rules(values: dict) -> list[SkillRule]:
    """Stage 3 rider: Projectile Attachment Damage ^ 421.2% for 10s on her own
    burst. (The requirement cut rides inside the launcher schedule above; the
    Explosion Radius branch stays deferred - radius is not modeled.)"""
    burst = values["power_of_inheritance"]
    return [
        buff_rule("own_burst_activate", [
            ("projectile_attachment_damage_up",
             float(burst["description_value_06"]) / 100, "self",
             float(burst["description_value_07"])),
        ]),
    ]
```

`build_attachable_projectiles_rules`에 부착딜▲ 150.72% 해제 추가 (기존 explosion 버프 옆):

```python
        buff_rule("battle_start", [
            ("projectile_attachment_damage_up",
             float(values["description_value_05"]) / 100, "self", None),
        ]),
```

registry.py: rapi의 `_BUILDERS` 람다에 `+ build_power_of_inheritance_rules(sv["power_of_inheritance"])` 추가(기존 엔트리의 값 전달 형태를 확인해 맞출 것 — battlefield 빌더가 서브딕트를 받는지 전체 sv를 받는지), `_SCHEDULED_NUKE_BUILDERS["rapi-red-hood"] = lambda sv: build_attachable_projectiles_scheduled_nukes(sv)` 추가. 모듈 docstring의 "Not modeled / deferred"에서 발사기·부착딜▲ 항목을 제거하고 위 시맨틱 요약으로 교체.

- [ ] **Step 4: 엔드투엔드 회귀 고정** — 같은 테스트 파일에: 시뮬 2회(발사기 등록 전 상태는 재현 불가하므로, attachment 버프 유/무 덱 비교)로 부착딜이 421.2% 창 안에서 커지는 것을 단언하는 테스트 1개 추가. 그리고 전체 스위트: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests -q` — rapi의 기존 총딜 기대값 테스트가 있으면 발사기 추가로 수치가 (의도대로) 커진다. **기대값 갱신 사유를 커밋 메시지에 명시.**

- [ ] **Step 5: 커밋 + encoded-nikkes 갱신**

```bash
git add backend/app/skill_rules/rapi_red_hood.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_rapi_red_hood.py
git commit -m "encode: Rapi Red Hood projectile launcher - attach every 120 normals, explode on FB entry"
```

`docs/encoded-nikkes.md`의 rapi 행 갱신(발사기 모델됨, 잔여: Explosion Radius·Interruption Parts·Stage1 브랜치 딜) 후 커밋.

---

### Task 4: 듀얼모드 확장 메커니즘 (registry → roster → deck_search → frontend)

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (`MODE_VARIANTS` 맵 + `get_weapon_profile_override`)
- Modify: `backend/app/user_roster.py` (`load_nikke_spec` slug_override + 프로필 오버라이드 적용, `load_roster` 확장 루프)
- Modify: `backend/app/deck_search.py` (`shape_combinations`/`feasible_orderings` 상호 배제 필터)
- Modify: `frontend/src/lib/resourceIdSlugMap.ts`, `backend/tests/test_resource_id_slug_map.py`
- Test: `backend/tests/test_user_roster.py`(로스터 테스트가 있는 파일을 grep으로 확인), `backend/tests/test_deck_search.py`

**Interfaces:**
- Produces: `registry.MODE_VARIANTS = {base_slug: (variant_slug, ...)}` · `registry.get_weapon_profile_override(slug, skill_values) -> dict | None` · `load_nikke_spec(state, data_dir, slug_override=None)` · deck_search가 같은 base의 두 variant를 한 덱에 앉히지 않음. Task 5가 cinderella 항목을 채운다 — 이 태스크는 메커니즘만 (빈 `MODE_VARIANTS`로 착지, 테스트는 테스트 로컬 몽키패치/가짜 그룹으로).

- [ ] **Step 1: 실패하는 테스트 작성** — deck_search 필터부터:

```python
def test_mode_variants_never_share_a_deck(monkeypatch):
    from app import deck_search
    monkeypatch.setattr(deck_search, "_VARIANT_GROUP",
                        {"unit-a-mg": "unit-a", "unit-a-snipe": "unit-a"})
    roster = [
        FakeUnit("b1", 1), FakeUnit("b2", 2),
        FakeUnit("unit-a-mg", 3), FakeUnit("unit-a-snipe", 3), FakeUnit("b3", 3),
    ]
    for deck in deck_search.shape_combinations(roster):
        slugs = {u.slug for u in deck}
        assert not {"unit-a-mg", "unit-a-snipe"} <= slugs
    for deck in deck_search.feasible_orderings(roster):
        slugs = {u.slug for u in deck}
        assert not {"unit-a-mg", "unit-a-snipe"} <= slugs
```

(`FakeUnit`은 해당 테스트 파일의 기존 slug/burst_tier 헬퍼를 재사용 — 없으면 `SimpleNamespace(slug=..., burst_tier=...)`.) 로스터 확장 테스트는 기존 로스터 테스트 파일에서 `load_roster` 픽스처를 grep해 같은 스타일로: `MODE_VARIANTS`에 항목을 몽키패치하고, state 1건이 spec 2건(variant 슬러그)으로 확장됨 + 오버라이드 없는 유닛은 기존과 동일함을 단언.

- [ ] **Step 2: 실패 확인** (AttributeError: `_VARIANT_GROUP` 없음)

- [ ] **Step 3: 구현** — registry.py (`ENCODED_SLUGS` 정의 근처):

```python
# One owned character whose kit is a PRE-BATTLE mode choice held for the whole
# fight (Fienn, 2026-07-18 spec review): each mode is its own statically-wired
# slug. The roster loader candidates every variant from the one owned state;
# deck search never seats two variants of the same base together.
MODE_VARIANTS: dict[str, tuple[str, ...]] = {}


# A variant whose weapon profile differs from the character's dotgg stats
# (e.g. a Snipe mode) registers a builder here; the roster loader swaps the
# assembled profile in after skill values resolve.
_WEAPON_PROFILE_OVERRIDE_BUILDERS = {}


def get_weapon_profile_override(slug, skill_values):
    builder = _WEAPON_PROFILE_OVERRIDE_BUILDERS.get(slug)
    if builder is None:
        return None
    return builder(skill_values)
```

user_roster.py: import에 `MODE_VARIANTS`, `get_weapon_profile_override` 추가(기존 registry import 줄 확장). ① `load_nikke_spec(state, data_dir=DATA_DIR, slug_override=None)` — 본문 첫 줄 `slug = slug_override or state.character_slug`; `assemble_skill_values` 뒤에:

```python
    override = get_weapon_profile_override(slug, skill_values)
    if override is not None:
        weapon_stats = override
```

② `load_roster` 루프를 확장형으로:

```python
    for state in states:
        slugs = MODE_VARIANTS.get(state.character_slug) or (state.character_slug,)
        loaded = [s for s in (load_nikke_spec(state, data_dir, slug_override=slug)
                              for slug in slugs) if s is not None]
        specs.extend(loaded)
        if not loaded and state.character_slug not in seen:
            excluded.append(state.character_slug)
        seen.add(state.character_slug)
```

deck_search.py (`ALLOWED_SHAPES` 근처):

```python
from app.skill_rules.registry import MODE_VARIANTS

# variant slug -> its base, for the seat-exclusion check below.
_VARIANT_GROUP = {variant: base
                  for base, variants in MODE_VARIANTS.items() for variant in variants}


def _no_variant_clash(units):
    seen = set()
    for unit in units:
        base = _VARIANT_GROUP.get(unit.slug)
        if base is not None:
            if base in seen:
                return False
            seen.add(base)
    return True
```

`shape_combinations`의 `yield` 직전과 `feasible_orderings`의 combo 유효성 검사에 `_no_variant_clash(...)` 게이트 추가 (두 열거 경로 모두 — `find_best_decks_pruned`는 shape_combinations를 쓰므로 자동 커버).

- [ ] **Step 4: 전체 스위트 통과 확인** — `MODE_VARIANTS`가 비어 있으므로 기존 출력 불변이어야 정상.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/app/user_roster.py backend/app/deck_search.py backend/tests
git commit -m "engine: mode-variant dual-slug expansion - roster fan-out and deck-search exclusion"
```

---

### Task 5: cinderella-crystal-wave-mg / -snipe 인코딩

**Files:**
- Create: `backend/app/skill_rules/cinderella_crystal_wave.py` (한 파일에 두 슬러그 — drake.py 선례)
- Modify: `backend/app/skill_rules/registry.py` (import, `_BUILDERS`×2, `_PERIODIC_NUKE_BUILDERS`(정확한 맵명은 `get_periodic_nuke` 배선을 grep)×2, `MODE_VARIANTS`, `_WEAPON_PROFILE_OVERRIDE_BUILDERS`)
- Modify: `backend/app/skill_rules/little_mermaid.py` (docstring 교차 노트), `frontend/src/lib/resourceIdSlugMap.ts`, `backend/tests/test_resource_id_slug_map.py`
- Test: `backend/tests/test_skill_rules_cinderella_crystal_wave.py` (신규)

**Interfaces:**
- Consumes: Task 1 `boss_core_hittable`, Task 4 `MODE_VARIANTS`/오버라이드 배선
- Produces: `build_crystal_wave_mg_rules(values)`, `build_crystal_wave_snipe_rules(values)`, `crystal_wave_burst_percent(values)`, `crystal_wave_periodic_nuke(values)`, `build_snipe_weapon_profile(values)`

데이터: `data/lootandwaifus/char_cinderella-crystal-wave.json` + dotgg 동명 파일(MG 5.57%·300발·reload 2.5s — 수동 스텁, 존재 확인 완료). 유닛 메타: B3·Iron·MG·cd 40. 토큰 맵 (lootandwaifus Lv10, tokenizer 실측):
- `beauty_full` (skills,0): 01=1(Snipe 차지초), 02=62.13(Snipe 딜%), 03=250(풀차지%), 04=15(Snipe 장탄), 05·06·08=라벨(1,2,3), 07=40(회계용 소모탄), 09=1(차지 고정초), 10=24(Beauty-Full 공딜%), 11=3·12=6(리로드 고정, 모드전환용), 13=5(주기초), 14=900(주기넉%), 15=200(아군 탄), 16=12(게이지%)
- `mode_swap` (skills,1): 01=70.34(디코이HP%), 02=29(ATK%), 03=26.21(Destroy 파츠%), 04=26(Pinpoint 코어%), 05·07=라벨, 06=1189.66(Snipe FB넉%), 08=833.79(MG FB넉%)
- `glass_slippers` (skills,2): 01=92(공딜%), 02=10, 03=65(ATK%), 04=10, 05=6000(버스트넉%)

- [ ] **Step 1: Fienn 질문 2건** (플랜 실행 시점에 AskUserQuestion): ① Snipe 모드 재장전 시간 — 텍스트 부재. 제안: MG 기본 2.5s 차용(장탄 15·차지 1s라 15초마다 한 번, 민감도 낮음). ② cinderella-crystal-wave의 blablalink resource_id — 모르면 frontend 맵에 항목을 넣지 않고 드리프트 테스트의 `KNOWN_UNMAPPED`에 두 variant를 사유 주석과 함께 등록(후속 임포트에서 id 확인 시 교체).

- [ ] **Step 2: 실패하는 테스트 작성** — 값 픽스처(위 토큰 맵 그대로) + 빌더 단언:

```python
def _applied_buffs(rule):
    """buff_rule의 buffs 리스트를 registry 목킹으로 수집 (기존 테스트 파일들의
    FakeRegistry/수집 헬퍼를 grep해 재사용 — 없으면 rule.action(ctx, slug, 0.0, reg)
    호출 후 reg.added의 (stat, value, scope, duration) 튜플을 반환)."""

def test_shared_kit_battle_start_and_burst_buffs():
    rules = build_crystal_wave_mg_rules(CRYSTAL_WAVE_VALUES)
    starts = [r for r in rules if r.trigger == "battle_start"]
    bursts = [r for r in rules if r.trigger == "own_burst_activate"]
    assert ("attack_damage_up", 0.24, "self", None) in _applied_buffs(starts[0])
    assert ("atk_percent", 0.29, "self", None) in _applied_buffs(starts[0])
    assert ("other_core_damage_sources", 0.26, "self", None) in _applied_buffs(starts[1])
    assert ("attack_damage_up", 0.92, "self", 10.0) in _applied_buffs(bursts[0])
    assert ("atk_percent", 0.65, "self", 10.0) in _applied_buffs(bursts[0])

def test_periodic_900_every_5s():
    assert crystal_wave_periodic_nuke(CRYSTAL_WAVE_VALUES) == {"cooldown": 5.0, "percent": 900.0}

def test_burst_nuke_is_6000():
    assert crystal_wave_burst_percent(CRYSTAL_WAVE_VALUES) == 6000.0

def test_snipe_profile_is_static_sr_charge_weapon():
    assert build_snipe_weapon_profile(CRYSTAL_WAVE_VALUES) == {
        "weapon": "SR", "damage_percent": 62.13, "max_ammo": 15,
        "reload_time": 2.5,  # Step 1 답변 반영
        "charge_time": 1.0, "charge_damage_percent": 250.0,
    }

def test_mg_fb_nuke_gated_on_own_burst_and_core():
    # full_burst_enter 룰의 condition이 (own_burst_fired && core_hittable)일 때만 True:
    # SquadContext(core_hittable=True/False) × burst_used_this_cycle 유/무 4조합 단언

def test_snipe_fb_nuke_gated_on_own_burst_only():
    # 1189.66, core_hittable=False에서도 발화
```

매니페스트 등록 확인(두 슬러그 모두 `data_slug`/`dotgg_slug`="cinderella-crystal-wave") + `MODE_VARIANTS` 항목 확인 테스트 포함.

- [ ] **Step 3: 실패 확인 → 구현** — 모듈 골격:

```python
"""Cinderella: Crystal Wave, encoded as TWO static mode slugs (Fienn,
2026-07-18 spec review): the player picks MG or Snipe pre-battle and holds it,
so each mode is a fixed weapon profile + statically wired mode effects, and
deck search shows which mode a recommendation used via the slug itself.

Snipe full-charge semantics (Fienn, 2026-07-19): like Velvet's ammo pouch, a
full charge actually FIRES ONE round - the "expends 40 rounds" text is ammo
ACCOUNTING for consumption-counting synergies, not magazine drain. The
15-round magazine cycles on real shots. That accounting feeds skills we defer
anyway (see below), so it appears only in this docstring and the
little_mermaid cross-note.

Deferred (docstring contract):
- Decoy avatar (survivability, no damage path).
- Burst-gauge +12% per 200 ally rounds (gauge charge time is a fixed sim
  input - same defer as Little Mermaid's Bubble Order).
- Pierce (per convention - not modeled).
- Mode-switch machinery (Preparation for Change, reload-fixed windows):
  meaningless once the mode is held for the whole fight.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule
from app.squad_engine import boss_core_hittable, own_burst_fired_this_cycle

SNIPE_RELOAD_TIME_SEC = 2.5  # 텍스트 부재 - Step 1 Fienn 판정 반영

SKILL_VALUE_MANIFESTS = {
    "cinderella-crystal-wave-mg": {
        "source": "lootandwaifus",
        "data_slug": "cinderella-crystal-wave",
        "dotgg_slug": "cinderella-crystal-wave",
        "test_module": "test_skill_rules_cinderella_crystal_wave",
        "keys": {
            "beauty_full": ("skills", 0),
            "mode_swap": ("skills", 1),
            "glass_slippers": ("skills", 2),
        },
    },
    "cinderella-crystal-wave-snipe": {
        "source": "lootandwaifus",
        "data_slug": "cinderella-crystal-wave",
        "dotgg_slug": "cinderella-crystal-wave",
        "test_module": "test_skill_rules_cinderella_crystal_wave",
        "keys": {
            "beauty_full": ("skills", 0),
            "mode_swap": ("skills", 1),
            "glass_slippers": ("skills", 2),
        },
    },
}


def _shared_rules(values):
    beauty = values["beauty_full"]
    mode_swap = values["mode_swap"]
    glass = values["glass_slippers"]
    return [
        buff_rule("battle_start", [
            ("attack_damage_up", float(beauty["description_value_10"]) / 100, "self", None),
            ("atk_percent", float(mode_swap["description_value_02"]) / 100, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", float(glass["description_value_01"]) / 100, "self",
             float(glass["description_value_02"])),
            ("atk_percent", float(glass["description_value_03"]) / 100, "self",
             float(glass["description_value_04"])),
        ]),
    ]


def build_crystal_wave_mg_rules(values):
    mode_swap = values["mode_swap"]
    fired = own_burst_fired_this_cycle()
    core = boss_core_hittable()

    def own_burst_and_core(context, caster_slug):
        return fired(context, caster_slug) and core(context, caster_slug)

    return _shared_rules(values) + [
        buff_rule("battle_start", [
            ("other_core_damage_sources", float(mode_swap["description_value_04"]) / 100,
             "self", None),                                   # Pinpoint
        ]),
        instant_nuke_pulse_rule(
            "full_burst_enter", float(mode_swap["description_value_08"]),
            condition=own_burst_and_core),                    # 833.79 core strike
    ]


def build_crystal_wave_snipe_rules(values):
    mode_swap = values["mode_swap"]
    return _shared_rules(values) + [
        buff_rule("battle_start", [
            ("damage_to_parts_up", float(mode_swap["description_value_03"]) / 100,
             "self", None),                                   # Destroy
        ]),
        instant_nuke_pulse_rule(
            "full_burst_enter", float(mode_swap["description_value_06"]),
            condition=own_burst_fired_this_cycle()),          # 1189.66
    ]


def crystal_wave_burst_percent(values):
    return float(values["glass_slippers"]["description_value_05"])


def crystal_wave_periodic_nuke(values):
    beauty = values["beauty_full"]
    return {"cooldown": float(beauty["description_value_13"]),
            "percent": float(beauty["description_value_14"])}


def build_snipe_weapon_profile(values):
    beauty = values["beauty_full"]
    return {
        "weapon": "SR",
        "damage_percent": float(beauty["description_value_02"]),
        "max_ammo": int(float(beauty["description_value_04"])),
        "reload_time": SNIPE_RELOAD_TIME_SEC,
        "charge_time": float(beauty["description_value_01"]),
        "charge_damage_percent": float(beauty["description_value_03"]),
    }
```

MG FB넉의 코어 게이팅 주석: 코어 보정은 시뮬 전역 균일 모델(`CORE_HIT_BONUS`, per-instance 미구분)이므로 "코어 활성 적 한정" 넉은 core_hittable 게이트만으로 관례와 정합. registry: 두 슬러그를 `_BUILDERS`(`lambda sv: (build_..., crystal_wave_burst_percent(sv))`)·periodic 넉 맵에 등록, `MODE_VARIANTS["cinderella-crystal-wave"] = ("cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe")`, `_WEAPON_PROFILE_OVERRIDE_BUILDERS["cinderella-crystal-wave-snipe"] = build_snipe_weapon_profile`. 멤버 `weapon` 필드는 두 변종 모두 "MG"(유닛 정체성 — 무기 타입 아군 필터용)이고, **발사 케이던스/타이핑은 weapon_stats 프로필의 "SR"이 결정**함을 주석으로 명시.

little_mermaid.py docstring에 교차 노트 추가: Bubble Order류 아군 탄소모 카운터는 velvet ammo pouch(100/300발 회계)·cinderella-crystal-wave Snipe(풀차지=40발 회계)로 가속되는데 현재 "1샷=1탄" 가정 — 게이지 모델 도입 시 재검토.

- [ ] **Step 4: 드리프트 테스트/프론트 맵** — `test_resource_id_slug_map.py`: `MODE_VARIANTS` variant 슬러그들이 map에 직접 안 나타나도 되도록 "-signature" 차감과 동형 처리(registry의 `MODE_VARIANTS`를 import해 variant를 도달 가능으로 간주). resourceIdSlugMap.ts: Step 1의 id 답변대로 `NNN: 'cinderella-crystal-wave'` 추가(백엔드가 두 변종으로 확장 — 파일 헤더 주석에 base-slug 규약 한 줄 추가), id 미상이면 `KNOWN_UNMAPPED` 경로.

- [ ] **Step 5: 하니스 + 전체 스위트** — Run: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_skill_value_assembly.py tests -q`. 라벨 토큰(05·06·08 등)이 하니스와 어긋나면 그때만 `drop_tokens` 추가.

- [ ] **Step 6: 커밋 + encoded-nikkes 행 2개 추가** (⚠ — 디코이·게이지·Pierce·모드전환 defer 명시)

```bash
git add backend/app/skill_rules/cinderella_crystal_wave.py backend/app/skill_rules/registry.py backend/app/skill_rules/little_mermaid.py backend/tests frontend/src/lib/resourceIdSlugMap.ts docs/encoded-nikkes.md
git commit -m "encode: Cinderella Crystal Wave - MG and Snipe static mode slugs with search exclusion"
```

---

### Task 6: per-shot 세그먼트 게이팅 (`in_segment` 플래그 + 모드 2종) + `caster_weapon_stats` 주입

**Files:**
- Modify: `backend/app/attack_rate.py` (ShotRecord + `_segment_shot_records`)
- Modify: `backend/app/raid_simulator.py` (per-shot 모드 사전계산 블록 621–643행)
- Modify: `backend/app/roster.py` (skill_values 주입부 100–105행)
- Test: `backend/tests/test_attack_rate.py`, `backend/tests/test_raid_simulator.py`

**Interfaces:**
- Produces: `ShotRecord.in_segment: bool = False` (세그먼트 발사만 True) · per-shot 모드 `"every_during_segment"` / `"every_outside_segment"` (threshold = N, 각각 세그먼트 안/밖 샷만 세어 N번째마다 발화) · `skill_values["caster_weapon_stats"]` (spec.weapon_stats 주입 — caster_atk 선례). Task 7의 SWHA가 세 가지 모두 소비.

- [ ] **Step 1: 실패하는 테스트 작성**:

```python
def test_shot_records_carry_in_segment_flag():
    seg = {"start": 10.0, "until_shots": 1, "profile": CANNON}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    assert all(r.in_segment == (r.damage_percent == 499.5) for r in records)
```

raid_simulator 쪽 (Task 2에서 쓴 스타일의 최소 시뮬로): 세그먼트 1개를 가진 유닛에 `per_shot_rules={"gunner": [(1, "every_during_segment", [<pulse 50>]), (1, "every_outside_segment", [<pulse 10>])]}`를 주고, damage_log에서 per_shot_nuke가 세그먼트 샷 시각에는 50, 그 외 시각에는 10으로만 나타남을 단언.

- [ ] **Step 2: 실패 확인** (TypeError: in_segment 파라미터 없음 / 새 모드 미발화)

- [ ] **Step 3: 구현** — attack_rate.py: `ShotRecord`에 `in_segment: bool = False` 필드 추가, `_segment_shot_records`의 레코드 생성에 `in_segment=True` 추가. raid_simulator.py 모드 사전계산 블록(632행 `every_during_own_status_window` 처리 뒤)에:

```python
            elif mode == "every_during_segment":
                seg_times = [r.time for r in shot_records if r.in_segment]
                window_fire_times[idx] = {
                    t for i, t in enumerate(seg_times) if (i + 1) % threshold == 0}
            elif mode == "every_outside_segment":
                base_times = [r.time for r in shot_records if not r.in_segment]
                window_fire_times[idx] = {
                    t for i, t in enumerate(base_times) if (i + 1) % threshold == 0}
```

roster.py 주입부(caster_atk 옆)에 `"caster_weapon_stats": spec.weapon_stats,` 추가 — 무기 프로필에서 파생되는 스케줄(Task 7)이 기본 스탯을 하드코딩 없이 읽는 경로.

- [ ] **Step 4: 전체 스위트 통과 확인** (플래그 기본 False + 신규 모드 미사용 = 기존 출력 불변)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/attack_rate.py backend/app/raid_simulator.py backend/app/roster.py backend/tests
git commit -m "engine: segment-gated per-shot modes and caster weapon stats injection"
```

---

### Task 7: snow-white-heavy-arms 인코딩 (per-shot + 세그먼트 조합)

**Files:**
- Create: `backend/app/skill_rules/snow_white_heavy_arms.py` · Test: `backend/tests/test_skill_rules_snow_white_heavy_arms.py`
- Modify: `backend/app/skill_rules/registry.py` (import, `_BUILDERS`, `_PER_SHOT_RULE_BUILDERS`, `_WEAPON_MODE_SCHEDULE_BUILDERS`), `frontend/src/lib/resourceIdSlugMap.ts` (id **471** — 기존 주석에 명시돼 있음), `docs/encoded-nikkes.md`

**Interfaces:**
- Consumes: Task 6 전부 (세그먼트 게이팅 모드, caster_weapon_stats)
- Produces: `build_snow_white_heavy_arms_rules(values)`, `build_seven_dwarves_per_shot_rules(values)`, `build_fully_active_weapon_mode_schedule(values)`

유닛 메타: B3·Water·SR(차지 1.2s 고정 — dotgg 스탯에 이미 반영: 69.04%·장탄 6·reload 2s·풀차지 250%). 확정 시맨틱(Fienn 2026-07-19): sequential 전탄 보스 적중, 4.2% 받는피해 디버프는 상시 근사. 토큰 맵 (lootandwaifus Lv10, tokenizer 실측):
- `seven_dwarves` (skills,0): 02=5(락온 캡), 04=42.24(DEF%, defer), 05=5(장전 캡), 07=4.2(받는피해%), 08=4(초), 09·11=라벨, 10=41.9(전체히트%), 12=105.59(연타%), 13=1(사용횟수▼)
- `shades_of_white` (skills,1): 01=1.2(차지 고정초), 03=46.84(풀차지 ATK%), 04=5(초), 05=62.64(파츠%), 06=5(초), 07=3(라벨), 08=73.92(B3 진입 ATK%), 09=10(초), 10=528(Fully Active 차지댐%), 11=1(라운드), 12=158.4(연타▲%), 13=1(라운드)
- `fully_active` (skills,2, cd 40): 01=84.48(공딜%), 02=10(초), 03=2(사용횟수), 04·06·08=라벨, 05=3.2(차지초), 07=10(락온+), 09=10(장전+), 10=0, 11=41.9(파괴가능 투사체%, defer)

모델: 매 풀차지(=매 샷, SR 상시 풀차지 관례) Auto Fire가 41.9% + 105.59%×장전수 펄스를 방출. 기본 장전수 5(1.2s 차지 동안 0.2s 틱 6회로 캡 도달), Fully Active 중 15(3.2s 차지, 틱 16회). Fully Active = 자기 버스트마다 `until_shots: 2` 세그먼트(차지 3.2s, 풀차지 250+528=778%) — 세그먼트 샷엔 `every_during_segment` 룰이 강화 연타(105.59×15×(1+1.584)), 그 외 샷엔 `every_outside_segment` 룰이 기본 연타를 방출해 이중계상이 구조적으로 불가능.

- [ ] **Step 1: 실패하는 테스트 작성**:

```python
def test_auto_fire_pulses_base_and_fully_active_variants():
    rules = build_seven_dwarves_per_shot_rules(SWHA_VALUES)
    # (1, "every", [차지창 리프레시 버프: atk 0.4684/5s + parts 0.6264/5s]),
    # (1, "every_outside_segment", [pulse 41.9 + 5*105.59 = 569.85]),
    # (1, "every_during_segment", [pulse 41.9 + 15*105.59*2.584 = 4134.57 (approx)])

def test_fully_active_segment_is_two_slow_charged_shots():
    schedule = build_fully_active_weapon_mode_schedule(SWHA_VALUES)
    segments = schedule(SimpleNamespace(
        burst_times={"snow-white-heavy-arms": [20.0]}), 180.0)
    assert segments == [{"start": 20.0, "until_shots": 2, "profile": {
        "weapon": "SR", "damage_percent": 69.04,
        "charge_damage_percent": pytest.approx(778.0), "charge_time": 3.2}}]

def test_battle_start_and_burst_buffs():
    rules = build_snow_white_heavy_arms_rules(SWHA_VALUES)
    # battle_start: damage_taken_up 0.042 squad 영구 (Fienn 상시 근사)
    # own_burst_activate: attack_damage_up 0.8448/10s self
    # + B3 진입 ATK 0.7392/10s — 트리거는 Step 2 확인 결과를 따름
```

값 픽스처는 위 토큰 맵 그대로. `SWHA_VALUES["caster_weapon_stats"] = {"weapon": "SR", "damage_percent": 69.04, ..., "charge_damage_percent": 250.0}` 포함.

- [ ] **Step 2: 선례 확인 1건** — "Activates when entering Burst Stage 3"의 기존 처리: `grep -rn "Burst Stage 3\|stage3\|entering Burst" backend/app/skill_rules` (nayuta의 stage3 코어딜 등). **선례의 트리거/조건을 그대로 따른다** — 선례가 own_burst_activate 근사라면 SWHA도 동일하게(그녀가 버스트 낙찰된 사이클만 발동 — 근사임을 docstring에 명시); 스테이지 진입 전용 트리거가 있으면 그것을 사용.

- [ ] **Step 3: 실패 확인 → 구현** — 모듈 골격:

```python
"""Snow White: Heavy Arms - the charge-loop kit lands on existing primitives
(the deferred verification pass from the weapon-transform spec, resolved YES):
every full charge fires Auto Fire (41.9% all-enemy hit + 105.59% x loaded-ammo
sequential hits, ALL landing on the single raid boss - Fienn 2026-07-19), and
Seven Dwarves Fully Active is a weapon-mode segment (2 shots at 3.2s charge,
+528% charge damage folded into the profile's charge_damage_percent so deck
charge buffs still stack on top) whose empowered Auto Fire rides the
every_during_segment per-shot mode - the outside/during split makes
double-counting structurally impossible.

Lock-on/ammo accrual is deterministic: 0.2s ticks during charge reach the
5-round cap within the 1.2s base charge (6 ticks) and the 15-round boosted cap
within 3.2s (16 ticks), so loaded ammo is a constant per mode.

The lock-on "Damage Taken up 4.2% for 4s" tick is approximated as a permanent
squad-scope debuff (charging uptime is ~100%, 4s duration >> 0.2s tick -
Fienn, 2026-07-19).

Deferred: DEF up 42.24% (defensive, inert), Pierce (convention), the 41.9%
destructible-projectile sweep (no destructible projectiles modeled), Lock-On
multi-target bookkeeping (single boss).
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule

SKILL_VALUE_MANIFESTS = {
    "snow-white-heavy-arms": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_snow_white_heavy_arms",
        "keys": {
            "seven_dwarves": ("skills", 0),
            "shades_of_white": ("skills", 1),
            "fully_active": ("skills", 2),
        },
    },
}


def build_snow_white_heavy_arms_rules(values):
    dwarves = values["seven_dwarves"]
    shades = values["shades_of_white"]
    burst = values["fully_active"]
    return [
        buff_rule("battle_start", [
            ("damage_taken_up", float(dwarves["description_value_07"]) / 100, "squad", None),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", float(burst["description_value_01"]) / 100, "self",
             float(burst["description_value_02"])),
            ("atk_percent", float(shades["description_value_08"]) / 100, "self",
             float(shades["description_value_09"])),   # Step 2 선례에 따라 트리거 조정
        ]),
    ]


def build_seven_dwarves_per_shot_rules(values):
    dwarves = values["seven_dwarves"]
    shades = values["shades_of_white"]
    burst = values["fully_active"]
    all_hit = float(dwarves["description_value_10"])
    seq_hit = float(dwarves["description_value_12"])
    base_ammo = int(float(dwarves["description_value_05"]))
    boosted_ammo = base_ammo + int(float(burst["description_value_09"]))
    seq_up = float(shades["description_value_12"]) / 100
    charge_window_buffs = refreshing_buff_rule("per_shot", [
        ("atk_percent", float(shades["description_value_03"]) / 100, "self",
         float(shades["description_value_04"])),
        ("damage_to_parts_up", float(shades["description_value_05"]) / 100, "self",
         float(shades["description_value_06"])),
    ])
    return [
        (1, "every", [charge_window_buffs]),
        (1, "every_outside_segment",
         [instant_nuke_pulse_rule("per_shot", all_hit + base_ammo * seq_hit)]),
        (1, "every_during_segment",
         [instant_nuke_pulse_rule("per_shot",
                                  all_hit + boosted_ammo * seq_hit * (1 + seq_up))]),
    ]


def build_fully_active_weapon_mode_schedule(values):
    shades = values["shades_of_white"]
    burst = values["fully_active"]
    weapon = values["caster_weapon_stats"]
    profile = {
        "weapon": weapon["weapon"],
        "damage_percent": weapon["damage_percent"],
        "charge_damage_percent": weapon["charge_damage_percent"]
        + float(shades["description_value_10"]),
        "charge_time": float(burst["description_value_05"]),
    }
    uses = int(float(burst["description_value_03"]))

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": uses, "profile": profile}
                for t in context.burst_times.get("snow-white-heavy-arms", [])]

    return schedule
```

registry 등록: `_BUILDERS["snow-white-heavy-arms"] = lambda sv: (build_snow_white_heavy_arms_rules(sv), None)` (버스트 자체 딜 없음 — 상태머신 기동이 본체), per-shot·weapon-mode 맵. resourceIdSlugMap.ts에 `471: 'snow-white-heavy-arms',` 추가하고 220행 주석에서 "(471 = Snow White: Heavy Arms, neither encoded)" 문구 갱신.

- [ ] **Step 4: 하니스 + 전체 스위트** — Run: `cd backend` 후 `C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_skill_value_assembly.py tests -q`. 라벨 토큰 어긋나면 `drop_tokens`.

- [ ] **Step 5: 엔드투엔드 스모크** — 시뮬 1회로: FB 창 안에 3.2s 간격 세그먼트 샷 2발(강화 펄스 동반) 후 1.2s 케이던스 복귀를 damage_log에서 단언하는 테스트 추가.

- [ ] **Step 6: 커밋** — `git commit -m "encode: Snow White Heavy Arms - Auto Fire per-shot with Fully Active segment"` + encoded-nikkes 행(⚠ — DEF·Pierce·투사체 스윕 defer).

---

### Task 8: 문서 갱신 + 마무리 검증 + 머지

**Files:**
- Modify: `docs/roadmap.md` (Phase 3 백로그 — 무기변형/상태머신 항목 소거·카운트 갱신), `docs/engine-gaps.md` ("이미 만든 것"에 컨텍스트 노출·attachment 타입·듀얼모드 확장·세그먼트 게이팅 추가, "막힌 유닛" 목록에서 cinderella-crystal-wave·rapi-red-hood·snow-white-heavy-arms 상태 갱신), `docs/superpowers/specs/2026-07-18-weapon-transform-design.md` (상태: 계획 2 착지 표기), `nikke-skill-encoding` 스킬의 `references/engine-capabilities.md`·`special-mechanics.md` (mode-variant 듀얼슬러그 패턴·프로젝타일 발사기 패턴·세그먼트 게이팅 per-shot 모드 추가)

- [ ] **Step 1: 위 문서들 갱신** (각 파일의 기존 서술 밀도·형식 유지)
- [ ] **Step 2: engine-test-runner로 전체 스위트 최종 실행** (`/test-engine`) — 858+신규 전부 PASS 확인
- [ ] **Step 3: 커밋** — `git commit -m "docs: weapon-transform plan 2 landed - dual-mode slugs, launcher, SWHA"`
- [ ] **Step 4: `/document`로 결정 기록** — docs-keeper에: (1) 듀얼모드 슬러그 메커니즘(로스터 fan-out + 탐색 배제, 시그니처 승격과의 차이 — 투자 아닌 플레이 선택) (2) cinderella Snipe/velvet 탄소모 회계 시맨틱 (3) rapi 발사기 시맨틱(누적-일괄폭발, 요구치 창) (4) SWHA가 신규 상태머신 없이 세그먼트+per-shot 게이팅으로 풀린 것(스펙의 검증 패스 종결) (5) per-shot 세그먼트 게이팅 모드의 이중계상 방지 설계
- [ ] **Step 5: `wip/scaffolding` 머지** — 메인 체크아웃이 깨끗한지 확인 후 `git -C C:/Users/fienn/Desktop/NikkeDeckBuilder merge worktree-transform-plan2`

---

## 계획 3 백로그 (이 계획에 포함되지 않음)

- **velvet 변형딜** (보류 확정 유지, 저가치) · **laplace base 5초 변형** (실측 없음) — 스펙의 명시적 보류 항목 그대로.
- **버스트 게이지 충전 모델** (cinderella 12%/Little Mermaid 37%/helm 등 누적 수요 — `gauge_charge_time` 고정 입력 가정을 깨는 엔진 확장, ROI 판단 필요).
- **rapi Stage 1 (Combat Assist) 브랜치의 버스트 딜/버프** — 탐색 덱은 항상 B1을 포함해(ALLOWED_SHAPES) Combat Assist가 발동하지 않으므로 현행 defer 유지 (deck_search의 2026-07-17 명목 티어 결정).
