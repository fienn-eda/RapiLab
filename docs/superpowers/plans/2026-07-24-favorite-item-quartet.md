# 애장품 4인방 온보딩 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sugar · Flora · Rosanna · Phantom을 각각 base + `-signature` 듀얼 슬롯으로
덱 추천 엔진에 올린다. 이 문서는 **Sugar 전체**와 나머지 3인이 반복할 태스크 골격을 담는다.

**Architecture:** 매니페스트에 선택적 `weapon_source` 키를 열어 "스킬값은
lootandwaifus(dollskills) · 무기 스탯은 ShiftyPad"를 한 슬러그에서 조합할 수 있게 한
뒤(Task 1), 유닛마다 base 모듈 → signature 모듈 → 프런트/문서 순으로 완주한다.

**Tech Stack:** Python 3 / pytest (backend), TypeScript + Vitest (frontend 슬러그 맵),
데이터는 gitignored `data/` (lootandwaifus HTML+JSON, 정규화된 ShiftyPad JSON).

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-07-24-favorite-item-quartet-design.md`.
- 인코딩 방법론: `.claude/skills/nikke-skill-encoding/SKILL.md` (워크플로 1–12단계).
- 테스트 실행은 항상 `backend/`에서 `PYTHONIOENCODING=utf-8 python -m pytest ...`
  (Windows cp949에서 화살표·한글 깨짐 방지).
- 수집은 **메인 체크아웃**에서 실행 후 워크트리에서 `python scripts/sync_worktree_data.py`
  (`collect.js`의 `node_modules`가 메인에만 있다).
- 값은 **레벨 10**(`levels[-1]`) 기준. 퍼센트는 `/ 100`으로 비율화한다.
- `SIGNATURE_OWNED`는 **건드리지 않는다** (Fienn이 애장품 미보유).
- 기존 회귀 기준선을 깨뜨리지 않는다.

---

### Task 1: `weapon_source` 매니페스트 키

`source: "lootandwaifus"`인 슬러그가 무기 스탯을 ShiftyPad에서 읽을 수 있게 한다.
현재는 dotgg에서만 읽고, dotgg는 죽었으며 네 유닛은 dotgg 파일이 없다.

**Files:**
- Modify: `backend/app/user_roster.py` (모듈 docstring, `load_nikke_spec`의 무기 소스 분기)
- Test: `backend/tests/test_user_roster_shiftypad.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 매니페스트 선택 키 `weapon_source: "shiftypad" | "dotgg"`. 생략 시
  `manifest["source"]`와 동일하게 동작(현행 유지). Task 3이 이 키를 쓴다.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_user_roster_shiftypad.py` 끝에 추가:

```python
def test_lootandwaifus_manifest_can_take_weapon_stats_from_shiftypad(tmp_path, monkeypatch):
    """A signature slug reads dollskills from lootandwaifus but weapon stats from
    the base unit's normalized ShiftyPad file - the unit has no dotgg file at all."""
    from app.skill_rules import registry

    (tmp_path / "shiftypad").mkdir()
    (tmp_path / "lootandwaifus").mkdir()
    (tmp_path / "shiftypad" / "sugar.json").write_text(json.dumps({
        "weapon": "SG", "maxAmmo": 9, "damage": "231.6%", "reloadTime": 0.67,
        "chargeTime": 0.0, "chargeDamage": "100%", "element": "Iron", "burst": "3",
        "skills": [{"levels": [{}]}, {"levels": [{}]},
                   {"cooldown": 40.0, "levels": [{}]}],
    }), encoding="utf-8")
    (tmp_path / "lootandwaifus" / "char_sugar.json").write_text(json.dumps({
        "name": "Sugar", "url": "sugar", "source": "lootandwaifus",
        "class": "Attacker", "weapon": "SG", "element": "Iron", "burst": "3",
        "cooldown": 40.0,
        "skills": [{"name": "s", "cooldown": None, "levels": ["x"] * 10}] * 3,
        "dollskills": [{"name": "d", "cooldown": None, "levels": ["y"] * 10}] * 3,
    }), encoding="utf-8")

    manifest = {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "sugar",
        "test_module": "unused",
        "keys": {},
    }
    monkeypatch.setattr(registry, "get_skill_value_manifest", lambda slug: manifest)
    monkeypatch.setattr("app.user_roster.get_skill_value_manifest", lambda slug: manifest)
    monkeypatch.setattr("app.user_roster.ENCODED_SLUGS", {"sugar-signature"})
    monkeypatch.setattr("app.user_roster.assemble_skill_values",
                        lambda slug, m, levels, data_dir: {})

    spec = load_nikke_spec(_state("sugar-signature"), data_dir=tmp_path)

    assert spec is not None
    assert spec.weapon_stats["weapon"] == "SG"
    assert spec.weapon_stats["max_ammo"] == 9
    assert spec.weapon_stats["damage_percent"] == 231.6
    assert spec.burst_tier == 3
```

`_state` 헬퍼와 `json`·`load_nikke_spec` import가 그 파일에 이미 있는지 확인하고, 없으면
같은 파일의 기존 테스트가 쓰는 형태를 그대로 재사용한다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_user_roster_shiftypad.py -q -k weapon_stats_from_shiftypad`
Expected: FAIL — `assert spec is not None` 에서 `None` (dotgg 파일을 찾다 `FileNotFoundError` → `return None`)

- [ ] **Step 3: Write minimal implementation**

`backend/app/user_roster.py`의 무기 소스 분기를 교체:

```python
    # dotgg sometimes shortens a unit's slug (url "ada" for "ada-wong"); the
    # optional dotgg_slug manifest key bridges that for the weapon-stats lookup.
    # Weapon stats come from weapon_source, which defaults to the manifest's
    # source - a signature slug reads dollskills from lootandwaifus while taking
    # its weapon from the base unit's ShiftyPad file, since dotgg is dead.
    if manifest.get("weapon_source", manifest["source"]) == "shiftypad":
        try:
            weapon_data = load_character_data("shiftypad", data_slug, data_dir)
        except FileNotFoundError:
            return None
    else:
        try:
            weapon_data = load_character_data(
                "dotgg", manifest.get("dotgg_slug", data_slug), data_dir
            )
        except FileNotFoundError:
            return None
```

모듈 docstring의 마지막 문장도 실제와 맞춘다:

```
weapon stats come from the manifest's `weapon_source` (defaulting to its
`source`) - dotgg for dotgg- and lootandwaifus-source units unless the manifest
overrides it, or the unit's normalized data/shiftypad/<slug>.json.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_user_roster_shiftypad.py tests/test_user_roster.py -q`
Expected: PASS, 회귀 없음 (키를 안 쓰는 기존 매니페스트는 경로가 그대로다)

- [ ] **Step 5: Commit**

```bash
git add backend/app/user_roster.py backend/tests/test_user_roster_shiftypad.py
git commit -m "Let a manifest take weapon stats from a different source than its skill values"
```

---

### Task 2: Sugar base 인코딩 (`sugar`)

**Files:**
- Create: `backend/app/skill_rules/sugar.py`
- Create: `backend/tests/test_skill_rules_sugar.py`
- Modify: `backend/app/skill_rules/registry.py` (import + `_BUILDERS` 항목)

**Interfaces:**
- Consumes: 없음
- Produces: `build_sugar_rules(values) -> list[SkillRule]`, `_shotgun_allies(member, context) -> bool`
  (Task 3이 import한다), `SKILL_VALUE_MANIFESTS["sugar"]`.

수집은 이미 끝나 있다 — `data/lootandwaifus/char_sugar.{html,json}`,
`data/shiftypad/sugar.json` (SG · Iron · Attacker · B3 cd40, maxAmmo 9,
damage 231.6%, reload 0.67).

**Fienn이 승인한 판단 (2026-07-24):**
- Black Typhoon(skills[0])은 **두 빌드 모두 defer** — "엄폐물이 공격받을 때"는 엔진에
  없는 트리거이고 base는 그 위에 20% 확률까지 붙는다. 상시로 근사하지 않는다.
- Hit Rate는 defer (엔진에 소비자가 영원히 없음).

- [ ] **Step 1: Write the failing test**

`backend/tests/test_skill_rules_sugar.py`:

```python
"""Sugar (base build) - Full-Burst crit/ammo support plus a self attack-speed burst."""
from app.effects import EffectRegistry
from app.skill_rules.sugar import build_sugar_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

NOIRE_SENSOR = {
    "description_value_01": "13.02", "description_value_02": "10",
    "description_value_03": "83.8", "description_value_04": "10",
}
TROUBLE_SHOOTER = {
    "description_value_01": "66", "description_value_02": "15",
    "description_value_03": "33", "description_value_04": "15",
}
SUGAR = {"noire_sensor": NOIRE_SENSOR, "trouble_shooter": TROUBLE_SHOOTER}

SELF = {"slug": "sugar", "element": "Iron"}
SG_ALLY = {"slug": "sg-ally", "element": "Water"}
AR_ALLY = {"slug": "ar-ally", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("sugar", burst_tier=3, element="Iron", weapon="SG"),
        SquadMember("sg-ally", burst_tier=3, element="Water", weapon="SG"),
        SquadMember("ar-ally", burst_tier=1, element="Fire", weapon="AR"),
    ])


def _fire(trigger, time=0.0):
    reg = EffectRegistry()
    fire_trigger(trigger, {"sugar": build_sugar_rules(SUGAR)}, _ctx(), reg, time)
    return reg


def test_full_burst_gives_self_crit_rate():
    reg = _fire("full_burst_enter")
    assert round(reg.total_for("crit_rate", SELF, 0.0), 4) == 0.1302
    assert reg.total_for("crit_rate", SG_ALLY, 0.0) == 0.0
    assert reg.total_for("crit_rate", SELF, 10.1) == 0.0  # 10s duration


def test_full_burst_gives_max_ammo_to_shotgun_members_only():
    # Exact weapon subset, not a squad approximation: the AR ally is excluded,
    # and Sugar herself is a shotgun so she is included.
    reg = _fire("full_burst_enter")
    assert round(reg.total_for("max_ammo_percent", SELF, 0.0), 4) == 0.838
    assert round(reg.total_for("max_ammo_percent", SG_ALLY, 0.0), 4) == 0.838
    assert reg.total_for("max_ammo_percent", AR_ALLY, 0.0) == 0.0
    assert reg.total_for("max_ammo_percent", SG_ALLY, 10.1) == 0.0


def test_burst_gives_self_attack_speed():
    reg = _fire("own_burst_activate")
    assert round(reg.total_for("attack_speed_percent", SELF, 0.0), 4) == 0.66
    assert reg.total_for("attack_speed_percent", SG_ALLY, 0.0) == 0.0
    assert reg.total_for("attack_speed_percent", SELF, 15.1) == 0.0


def test_inert_and_deferred_effects_are_not_emitted():
    """Hit Rate has no consumer, and Black Typhoon's cover-attack trigger does
    not exist - neither may leak into the registry."""
    for trigger in ("battle_start", "full_burst_enter", "own_burst_activate"):
        reg = _fire(trigger)
        for stat in ("hit_rate", "other_critical_damage_sources", "reload_speed_percent"):
            assert reg.total_for(stat, SELF, 0.0) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_sugar.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.skill_rules.sugar'`

- [ ] **Step 3: Write the module**

`backend/app/skill_rules/sugar.py`:

```python
"""Sugar (slug "sugar"), a Burst-3 Iron shotgun Attacker who enlarges shotgun
allies' magazines on Full Burst and speeds up her own fire with her burst.

Modeled (DPS-relevant):
- Noire Sensor (skills[1], on Full Burst entry): self Critical Rate +13.02% for
  10 sec, and Max Ammunition Capacity +83.8% for 10 sec on every shotgun ally.
  The shotgun subset is EXACT, not a squad approximation - member_subset_buff_rule
  resolves the weapon filter live against SquadMember.weapon.
- Trouble Shooter (skills[2], her burst, cd 40): self Attack Speed +66% for
  15 sec. Attack Speed moves damage since Phase S - attack_rate scales the firing
  cadence from it, so a fixed-length fight fits more shots. Her burst deals no
  damage, so the registry's burst percent is None.

Not modeled / deferred:
- Black Typhoon (skills[0]) entirely: Critical Damage +16.39% and Reload Speed
  +12.12% for 10 sec both hang off "when cover is attacked", a trigger the engine
  has no concept of, behind a 20% roll on top of it. Fienn ruled it deferred
  (2026-07-24) rather than approximated as permanent, because cover-hit frequency
  swings with the boss, its attack pattern and her position. This makes the
  encoding a FLOOR for her.
- Hit Rate +33% from her burst: Hit Rate is not a damage concept in the engine
  and no consumer can exist without a much bigger model.
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule


SKILL_VALUE_MANIFESTS = {
    "sugar": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_sugar",
        "keys": {
            "noire_sensor": ("skills", 1),
            "trouble_shooter": ("skills", 2),
        },
    },
}


def shotgun_allies(member, context):
    """Members carrying a shotgun - Noire Sensor's "all allies with shotguns"."""
    return member.weapon == "SG"


def build_sugar_rules(values):
    sensor = values["noire_sensor"]
    trouble = values["trouble_shooter"]
    crit_rate = float(sensor["description_value_01"]) / 100
    crit_duration = float(sensor["description_value_02"])
    max_ammo = float(sensor["description_value_03"]) / 100
    ammo_duration = float(sensor["description_value_04"])
    attack_speed = float(trouble["description_value_01"]) / 100
    speed_duration = float(trouble["description_value_02"])
    return [
        buff_rule("full_burst_enter", [
            ("crit_rate", crit_rate, "self", crit_duration),
        ]),
        member_subset_buff_rule("full_burst_enter", shotgun_allies, [
            ("max_ammo_percent", max_ammo, ammo_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_speed_percent", attack_speed, "self", speed_duration),
        ]),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_sugar.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Register the slug**

`backend/app/skill_rules/registry.py` — 기존 import 블록 관례에 맞춰 추가:

```python
from app.skill_rules.sugar import build_sugar_rules
```

`_BUILDERS`에 (슬러그 알파벳 순서 자리에):

```python
    "sugar": lambda sv: (build_sugar_rules(sv), None),  # burst is buffs-only
```

- [ ] **Step 6: Run the slug-map guard and expect it to go red**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_resource_id_slug_map.py -q`
Expected: FAIL — `test_every_encoded_slug_is_reachable_except_known`이 `sugar`를 지적.
이건 가드가 제대로 도는 것이다. Task 4에서 해소한다.

- [ ] **Step 7: Verify the manifest assembles from the real data file**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_value_assembly.py -q -k sugar`
Expected: PASS. 불일치가 나면 **픽스처나 하네스를 고치지 말고** 매니페스트에
`drop_tokens`를 추가해 맞춘다.

- [ ] **Step 8: Commit**

```bash
git add backend/app/skill_rules/sugar.py backend/tests/test_skill_rules_sugar.py backend/app/skill_rules/registry.py
git commit -m "Encode Sugar (base): Full-Burst crit + shotgun-ally ammo, burst attack speed"
```

---

### Task 3: Sugar 애장품 인코딩 (`sugar-signature`)

**Files:**
- Create: `backend/app/skill_rules/sugar_signature.py`
- Create: `backend/tests/test_skill_rules_sugar_signature.py`
- Modify: `backend/app/skill_rules/registry.py`

**Interfaces:**
- Consumes: `from app.skill_rules.sugar import shotgun_allies` (Task 2가 제공)
- Produces: `build_sugar_signature_rules(values) -> list[SkillRule]`,
  `SKILL_VALUE_MANIFESTS["sugar-signature"]` (Task 1의 `weapon_source` 사용)

**슬롯 번호** — lootandwaifus는 인라인 렌더라 좌→우 등장 순서로 직접 매긴다.
`data/lootandwaifus/char_sugar.json`의 `dollskills` 레벨 10 텍스트 기준:

- `[0] Black Typhoon`: 01=16.39(Crit DMG) · 02=10(sec) · 03=12.12(Reload) ·
  04=10(sec) · 05=1.5(Cover HP %) · 06=19.98(Attack Damage)
- `[1] Noire Sensor`: 01=13.02(Crit Rate) · 02=10 · 03=25.01(ATK) · 04=10 ·
  05=83.8(Max Ammo) · 06=15 · 07=40.02(Elem Adv Atk DMG) · 08=15
- `[2] Trouble Shooter`: 01=66(Attack Speed) · 02=15 · 03=33(Hit Rate) · 04=15 ·
  05=20(ATK) · 06=15 · 07=60.01(Elem Adv Atk DMG) · 08=15

**Fienn이 승인한 판단 (2026-07-24):** 애장품 S1의 "엄폐물이 온전할 때 공격데미지
+19.98% 지속"은 **상시 발동으로 모델**한다 (엔진이 엄폐물 파괴를 모델링하지 않아 항상
온전 상태). Black Typhoon의 엄폐 피격 버프는 base와 마찬가지로 defer.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_skill_rules_sugar_signature.py`:

```python
"""Sugar's Favorite Item build - adds permanent Attack Damage, a Fire-Code
elemental-advantage grant, self ATK, and Water/Iron shotgun-ally elemental buffs."""
from app.effects import EffectRegistry
from app.skill_rules.sugar_signature import build_sugar_signature_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

BLACK_TYPHOON = {
    "description_value_01": "16.39", "description_value_02": "10",
    "description_value_03": "12.12", "description_value_04": "10",
    "description_value_05": "1.5", "description_value_06": "19.98",
}
NOIRE_SENSOR = {
    "description_value_01": "13.02", "description_value_02": "10",
    "description_value_03": "25.01", "description_value_04": "10",
    "description_value_05": "83.8", "description_value_06": "15",
    "description_value_07": "40.02", "description_value_08": "15",
}
TROUBLE_SHOOTER = {
    "description_value_01": "66", "description_value_02": "15",
    "description_value_03": "33", "description_value_04": "15",
    "description_value_05": "20", "description_value_06": "15",
    "description_value_07": "60.01", "description_value_08": "15",
}
SUGAR_SIG = {
    "black_typhoon": BLACK_TYPHOON,
    "noire_sensor": NOIRE_SENSOR,
    "trouble_shooter": TROUBLE_SHOOTER,
}

SELF = {"slug": "sugar-signature", "element": "Iron"}
WATER_SG = {"slug": "water-sg", "element": "Water"}
FIRE_SG = {"slug": "fire-sg", "element": "Fire"}
IRON_AR = {"slug": "iron-ar", "element": "Iron"}


def _ctx(boss_element=None):
    return SquadContext([
        SquadMember("sugar-signature", burst_tier=3, element="Iron", weapon="SG"),
        SquadMember("water-sg", burst_tier=3, element="Water", weapon="SG"),
        SquadMember("fire-sg", burst_tier=2, element="Fire", weapon="SG"),
        SquadMember("iron-ar", burst_tier=1, element="Iron", weapon="AR"),
    ], boss_element=boss_element)


def _fire(trigger, boss_element=None, time=0.0):
    reg = EffectRegistry()
    rules = {"sugar-signature": build_sugar_signature_rules(SUGAR_SIG)}
    fire_trigger(trigger, rules, _ctx(boss_element), reg, time)
    return reg


def test_intact_cover_attack_damage_is_permanent():
    reg = _fire("battle_start")
    assert round(reg.total_for("attack_damage_up", SELF, 0.0), 4) == 0.1998
    assert round(reg.total_for("attack_damage_up", SELF, 179.0), 4) == 0.1998
    assert reg.total_for("attack_damage_up", WATER_SG, 0.0) == 0.0


def test_elemental_advantage_is_granted_only_against_fire():
    assert _fire("battle_start", boss_element="Fire").total_for(
        "element_advantage_grant", SELF, 0.0) == 1.0
    assert _fire("battle_start", boss_element="Wind").total_for(
        "element_advantage_grant", SELF, 0.0) == 0.0
    assert _fire("battle_start", boss_element="Fire").total_for(
        "element_advantage_grant", WATER_SG, 0.0) == 0.0


def test_full_burst_adds_self_atk_on_top_of_crit_rate():
    reg = _fire("full_burst_enter")
    assert round(reg.total_for("crit_rate", SELF, 0.0), 4) == 0.1302
    assert round(reg.total_for("atk_percent", SELF, 0.0), 4) == 0.2501
    assert reg.total_for("atk_percent", WATER_SG, 0.0) == 0.0
    assert reg.total_for("atk_percent", SELF, 10.1) == 0.0


def test_shotgun_ammo_buff_runs_15_seconds_in_this_build():
    reg = _fire("full_burst_enter")
    for member in (SELF, WATER_SG, FIRE_SG):
        assert round(reg.total_for("max_ammo_percent", member, 0.0), 4) == 0.838
    assert reg.total_for("max_ammo_percent", IRON_AR, 0.0) == 0.0
    # 15s here, against the base build's 10s.
    assert round(reg.total_for("max_ammo_percent", SELF, 14.9), 4) == 0.838
    assert reg.total_for("max_ammo_percent", SELF, 15.1) == 0.0


def test_elemental_buff_targets_water_and_iron_shotguns_only():
    for trigger, value in (("full_burst_enter", 0.4002), ("own_burst_activate", 0.6001)):
        reg = _fire(trigger)
        assert round(reg.total_for("other_elemental_bonus", SELF, 0.0), 4) == value
        assert round(reg.total_for("other_elemental_bonus", WATER_SG, 0.0), 4) == value
        # The Fire shotgun and the Iron AR both fail the filter.
        assert reg.total_for("other_elemental_bonus", FIRE_SG, 0.0) == 0.0
        assert reg.total_for("other_elemental_bonus", IRON_AR, 0.0) == 0.0
        assert reg.total_for("other_elemental_bonus", SELF, 15.1) == 0.0


def test_burst_keeps_self_attack_speed_and_adds_atk():
    reg = _fire("own_burst_activate")
    assert round(reg.total_for("attack_speed_percent", SELF, 0.0), 4) == 0.66
    assert round(reg.total_for("atk_percent", SELF, 0.0), 4) == 0.20
    assert reg.total_for("atk_percent", SELF, 15.1) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_sugar_signature.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.skill_rules.sugar_signature'`

- [ ] **Step 3: Write the module**

`backend/app/skill_rules/sugar_signature.py`:

```python
"""Sugar's Favorite Item (애장품) build, slug "sugar-signature" - a SEPARATE
roster entry from base Sugar (slug "sugar"), per the dual-slot convention
(2026-07-12). The Favorite Item does not just raise numbers here: it adds a
permanent Attack Damage bullet, an elemental-advantage grant, a self ATK buff on
both Full Burst and her burst, and an elemental buff for Water/Iron shotgun
allies that the base build has no trace of.

Weapon stats come from the base unit's ShiftyPad file (`weapon_source`), since
ShiftyPad does not expose dollskills and dotgg is dead.

Modeled (DPS-relevant):
- Black Typhoon (dollskills[0]): Attack Damage +19.98% while her cover is
  intact. The engine models no cover destruction, so cover is always intact -
  Fienn approved encoding it as a permanent battle-start self buff (2026-07-24).
- Black Typhoon (dollskills[0]): "Converts damage to Elemental Advantage damage
  against Fire Code enemies" at battle start. She is Iron, which holds no
  natural advantage over Fire, so this is element_advantage_grant gated on
  boss_is_element("Fire") - the same shape as Rapi: Red Hood's grant. It is
  deliberately NOT other_elemental_bonus, which only pays out to a unit that
  ALREADY has advantage and would be self-cancelling here.
- Noire Sensor (dollskills[1], on Full Burst entry): self Critical Rate +13.02%
  and ATK +25.01% for 10 sec; Max Ammunition Capacity +83.8% for 15 sec on all
  shotgun allies (10 sec in the base build); Elemental Advantage Attack Damage
  +40.02% for 15 sec on Water and Iron Code shotgun allies.
- Trouble Shooter (dollskills[2], her burst, cd 40): self Attack Speed +66% and
  ATK +20% for 15 sec; Elemental Advantage Attack Damage +60.01% for 15 sec on
  Water and Iron Code shotgun allies. No damage, so burst percent is None.

Both member subsets are EXACT, not squad approximations - member_subset_buff_rule
resolves the weapon and element filters live against SquadMember.

Not modeled / deferred:
- Black Typhoon's cover-attack buffs (Critical Damage +16.39%, Reload Speed
  +12.12%, 10 sec). This build drops the base's 20% roll, but "when cover is
  attacked" is still a trigger the engine has no concept of. Fienn ruled it
  deferred (2026-07-24) rather than approximated as permanent, so this encoding
  is a FLOOR.
- Black Typhoon's cover-HP restore (1.5% of final Max HP) - survivability, not
  damage.
- Hit Rate +33% from her burst - not a damage concept in the engine.
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule
from app.skill_rules.sugar import shotgun_allies
from app.squad_engine import boss_is_element


SKILL_VALUE_MANIFESTS = {
    "sugar-signature": {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "sugar",
        "test_module": "test_skill_rules_sugar_signature",
        "keys": {
            "black_typhoon": ("dollskills", 0),
            "noire_sensor": ("dollskills", 1),
            "trouble_shooter": ("dollskills", 2),
        },
    },
}

# "all Water Code and Iron Code allies with shotguns" - Noire Sensor's and
# Trouble Shooter's elemental bullets share the same target set.
_ELEMENTAL_BUFF_ELEMENTS = ("Water", "Iron")


def water_or_iron_shotgun_allies(member, context):
    return member.weapon == "SG" and member.element in _ELEMENTAL_BUFF_ELEMENTS


def build_sugar_signature_rules(values):
    typhoon = values["black_typhoon"]
    sensor = values["noire_sensor"]
    trouble = values["trouble_shooter"]
    intact_cover_damage = float(typhoon["description_value_06"]) / 100
    crit_rate = float(sensor["description_value_01"]) / 100
    crit_duration = float(sensor["description_value_02"])
    fb_atk = float(sensor["description_value_03"]) / 100
    fb_atk_duration = float(sensor["description_value_04"])
    max_ammo = float(sensor["description_value_05"]) / 100
    ammo_duration = float(sensor["description_value_06"])
    fb_elemental = float(sensor["description_value_07"]) / 100
    fb_elemental_duration = float(sensor["description_value_08"])
    attack_speed = float(trouble["description_value_01"]) / 100
    speed_duration = float(trouble["description_value_02"])
    burst_atk = float(trouble["description_value_05"]) / 100
    burst_atk_duration = float(trouble["description_value_06"])
    burst_elemental = float(trouble["description_value_07"]) / 100
    burst_elemental_duration = float(trouble["description_value_08"])
    return [
        buff_rule("battle_start", [
            ("attack_damage_up", intact_cover_damage, "self", None),
        ]),
        buff_rule("battle_start", [
            ("element_advantage_grant", 1.0, "self", None),
        ], condition=boss_is_element("Fire")),
        buff_rule("full_burst_enter", [
            ("crit_rate", crit_rate, "self", crit_duration),
            ("atk_percent", fb_atk, "self", fb_atk_duration),
        ]),
        member_subset_buff_rule("full_burst_enter", shotgun_allies, [
            ("max_ammo_percent", max_ammo, ammo_duration),
        ]),
        member_subset_buff_rule("full_burst_enter", water_or_iron_shotgun_allies, [
            ("other_elemental_bonus", fb_elemental, fb_elemental_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_speed_percent", attack_speed, "self", speed_duration),
            ("atk_percent", burst_atk, "self", burst_atk_duration),
        ]),
        member_subset_buff_rule("own_burst_activate", water_or_iron_shotgun_allies, [
            ("other_elemental_bonus", burst_elemental, burst_elemental_duration),
        ]),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_rules_sugar_signature.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Register the slug**

`backend/app/skill_rules/registry.py`:

```python
from app.skill_rules import sugar_signature
```

`_BUILDERS`에:

```python
    "sugar-signature": lambda sv: (
        sugar_signature.build_sugar_signature_rules(sv), None,
    ),
```

- [ ] **Step 6: Verify the manifest assembles from the real data file**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_value_assembly.py -q -k sugar`
Expected: PASS. 좌→우 번호가 파서의 토큰 순서와 어긋나면 매니페스트의 해당 키에
`drop_tokens`를 추가한다 (픽스처·하네스는 건드리지 않는다).

- [ ] **Step 7: Commit**

```bash
git add backend/app/skill_rules/sugar_signature.py backend/tests/test_skill_rules_sugar_signature.py backend/app/skill_rules/registry.py
git commit -m "Encode Sugar's Favorite Item build: permanent Attack Damage, Fire-Code advantage grant, elemental shotgun buffs"
```

---

### Task 4: 프런트 슬러그 맵 + 포트레이트

**Files:**
- Modify: `frontend/src/lib/resourceIdSlugMap.ts`
- Modify: `scripts/download_portraits.py` (`SLUG_ALIASES`에 signature 별칭)

**Interfaces:**
- Consumes: Task 2·3이 등록한 `sugar` / `sugar-signature`
- Produces: `RESOURCE_ID_TO_SLUG[140] === 'sugar'`, `DUAL_SLOT_BASES`에 `'sugar'`

- [ ] **Step 1: Add the identity-map entry and the dual-slot registration**

`RESOURCE_ID_TO_SLUG`에 숫자 순서에 맞는 자리로:

```ts
  140: 'sugar', // Sugar — dual-slot base; see SIGNATURE_OWNED
```

`DUAL_SLOT_BASES`:

```ts
export const DUAL_SLOT_BASES: ReadonlySet<string> = new Set(['drake', 'julia', 'laplace', 'sugar'])
```

`SIGNATURE_OWNED`는 **변경하지 않는다** — Fienn이 아직 애장품을 만들지 못했으므로
로스터는 base `sugar`로 해소되어야 한다.

- [ ] **Step 2: Run the backend guards that cross-check the frontend file**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_resource_id_slug_map.py tests/test_resource_id_directory.py -q`
Expected: PASS — Task 2 Step 6에서 빨갛던 `test_every_encoded_slug_is_reachable_except_known`이
녹색이 되고, `test_dual_slot_bases_match_encoded_pairs`도 통과한다.
디렉토리 가드는 rid 140이 실제로 "Sugar"인지 대조한다.

- [ ] **Step 3: Run the frontend unit tests**

Run: `cd frontend && npm test -- resourceIdSlugMap`
Expected: PASS — `resolveSlugForUnit(140)`이 `'sugar'`(승격 아님)를 돌려준다.

- [ ] **Step 4: Fetch the portrait**

Run: `python scripts/download_portraits.py`
Expected: `sugar` 아이콘이 `frontend/public/portraits/`에 받아지고 `manifest.json`이 갱신된다.
`sugar-signature`는 자기 캐릭터 페이지가 없어 `UNMAPPED`로 보고되므로, 스크립트의
`SLUG_ALIASES`에 `"sugar-signature": "sugar",` 한 줄을 추가하고 다시 실행한다.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/resourceIdSlugMap.ts scripts/download_portraits.py frontend/public/portraits/manifest.json
git commit -m "Wire Sugar into the roster slug map as a dual-slot base"
```

---

### Task 5: 전체 스위트 + 문서

**Files:**
- Modify: `docs/encoded-nikkes.md`, `docs/roadmap.md`, `docs/decisions.md`,
  `docs/engine-gaps.md`
- Modify: `.claude/skills/nikke-skill-encoding/references/engine-capabilities.md`
  (아래 낡은 서술 2건)

**Interfaces:**
- Consumes: Task 1–4 전부
- Produces: 없음 (문서화로 마감)

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: PASS. 기존 기준선 + 이번에 추가한 테스트 수만큼 증가, 실패 0.

- [ ] **Step 2: Correct the two stale claims in the capability catalog**

이 인코딩이 반증한 서술이다 (스킬의 "보류 메모는 작성 당일의 주장일 뿐" 원칙):
- 스코프 절의 *"**no weapon-conditional scope** ("SR allies", "shotgun allies").
  Approximate ... as `squad`"* → `member_subset_buff_rule`이 정확한 부분집합을
  만들므로, 근사 대신 그 헬퍼를 쓰라고 고친다.
- `attack_speed_percent` 항목의 *"a "shotgun allies only" speed buff (e.g. Tove)
  still needs weapon-type scope (deferred)"* → Tove는 이미
  `member_subset_buff_rule`로 그걸 하고 있다. 문장을 사실에 맞게 고친다.
- 트리거 절의 *"SkillRule actions have no access to the boss's element"* →
  `squad_engine.boss_is_element()` 조건이 있고 Rapi: Red Hood가 쓴다. 조건으로는
  가능하다고 명시한다.

- [ ] **Step 3: Update the knowledge base**

- `docs/encoded-nikkes.md` — Burst 3 표에 `sugar` · `sugar-signature` 두 행 추가,
  완성도 ⚠(둘 다 Black Typhoon defer로 floor), 총계·티어 분포 갱신, 듀얼슬롯 목록에
  Sugar 추가.
- `docs/roadmap.md` — 애장품 4인방 배치의 Sugar 완료 기록.
- `docs/decisions.md` — (1) 매니페스트 `weapon_source` 도입(맥락: dotgg 사망 +
  ShiftyPad가 dollskills 미노출), (2) Sugar의 엄폐 트리거 defer와 온전-엄폐 상시
  모델링에 대한 Fienn 판단.
- `docs/engine-gaps.md` — "엄폐물 피격 트리거"를 갭으로 등록(현재 차단 유닛: sugar,
  sugar-signature). 이후 3인에서 재등장하면 카운트를 올린다.

- [ ] **Step 4: Commit**

```bash
git add docs/ .claude/skills/nikke-skill-encoding/references/engine-capabilities.md
git commit -m "Document Sugar's encoding and correct two stale capability claims"
```

---

## 나머지 3인 (Flora · Rosanna · Phantom)

Sugar가 끝나면 유닛마다 **Task 2 → 3 → 4 → 5를 그대로 반복**한다. Task 1은 1회성이다.
유닛별로 달라지는 입력만 갈아끼운다:

| 유닛 | resource_id | lootandwaifus 슬러그 |
|---|---|---|
| Flora | 411 | `flora` |
| Rosanna | 280 | `rosanna` (⚠ `rosanna-chic-ocean`은 별개 유닛) |
| Phantom | 580 | `phantom` |

각 유닛은 Task 2 착수 전에 **수집(스펙 Phase 1)과 판단 사항 일괄 검토**(인코딩 스킬
4단계)를 먼저 거친다 — 스킬 내용이 다르면 판단도 달라지므로 Sugar의 결론을 그대로
옮기지 않는다.
