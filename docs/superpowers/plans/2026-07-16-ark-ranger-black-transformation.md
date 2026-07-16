# Ark Ranger Black Transformation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Encode Ark Ranger Black (`ark-ranger-black`) so her transformation-gated sustained-damage kit simulates as a floor/ceiling bracket selected by a new `BossProfile.part_destructible` flag.

**Architecture:** Add a boss-profile flag threaded to `SquadContext`. Compose existing engine mechanisms — condition-gated buffs, burst-anchored tick DoTs (`resource_scaled_nukes`), whole-fight DoTs (`periodic_nukes`), and per-shot buffs — selecting floor vs ceiling variants by the flag. No general state-machine primitive.

**Tech Stack:** Python, pytest. Backend engine under `backend/app/`, tests under `backend/tests/`.

## Global Constraints

- Run tests with `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q` from `backend/` (the env var avoids cp949 errors; `python3` is the interpreter that has pytest on this machine, NOT `python`).
- TDD: write the failing test first, watch it fail, implement minimally, watch it pass, commit. Work on branch `wip/scaffolding`.
- Sustained-typed DoTs MUST carry `"damage_type": "sustained"` so `sustained_damage_up` applies (it is wired only for sustained-typed instances).
- The `part_destructible` flag defaults to `False` everywhere; default behavior must be inert for all other units (full suite stays green).
- Design source of truth: `docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md`.
- Derived window duration: `D = post_transform_battery% / (decay_% / decay_interval_s)`. With her values `50 / (1 / 0.2) = 10.0 s`. Floor DoT tick count `= int(round(D / tick_interval))`; floor buff duration `= D`. Never hardcode `10`.

---

## File Structure

- `backend/app/deck_search.py` — add `part_destructible` to `BossProfile`; pass it through `evaluate_deck`.
- `backend/app/raid_simulator.py` — add `part_destructible` param → `SquadContext`; add `requires_part_destructible` filter to the `resource_scaled_nukes` and `periodic_nukes` loops.
- `backend/app/squad_engine.py` — add `part_destructible` to `SquadContext.__init__`; add `boss_part_destructible()` condition.
- `backend/app/skill_rules/ark_ranger_black.py` — NEW: the unit's builders (buffs, DoTs, per-shot).
- `backend/app/skill_rules/registry.py` — register the unit in `_BUILDERS`, `_RESOURCE_SCALED_NUKE_BUILDERS`, `_PERIODIC_NUKE_BUILDERS`, `_PER_SHOT_RULE_BUILDERS`.
- `backend/tests/test_skill_rules_ark_ranger_black.py` — NEW: unit tests.
- `backend/tests/test_ark_ranger_bracket.py` — NEW: end-to-end floor/ceiling bracket test.
- Docs: `docs/roadmap.md`, `docs/encoded-nikkes.md`, `docs/engine-gaps.md`.

---

## Task 1: `part_destructible` boss flag — threading + condition

**Files:**
- Modify: `backend/app/squad_engine.py` (`SquadContext.__init__` ~line 23; add condition near `boss_is_element` ~line 206)
- Modify: `backend/app/raid_simulator.py` (`simulate_raid` signature ~line 216; `SquadContext(...)` construction ~line 243)
- Modify: `backend/app/deck_search.py` (`BossProfile` line 27-34; `evaluate_deck` line 54-64)
- Test: `backend/tests/test_part_destructible_flag.py` (new)

**Interfaces:**
- Produces: `SquadContext(members, base_atk=..., boss_element=None, part_destructible=False)` with attribute `context.part_destructible: bool`; `boss_part_destructible() -> Callable[[SquadContext, str], bool]`; `simulate_raid(..., part_destructible=False, ...)`; `BossProfile(..., part_destructible=False)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_part_destructible_flag.py`:

```python
from app.squad_engine import SquadContext, SquadMember, boss_part_destructible


def _ctx(part_destructible):
    return SquadContext(
        [SquadMember("ark-ranger-black", burst_tier=3, element="Wind")],
        part_destructible=part_destructible,
    )


def test_context_defaults_part_destructible_false():
    assert SquadContext([SquadMember("x", 3, "Wind")]).part_destructible is False


def test_boss_part_destructible_condition_reads_flag():
    assert boss_part_destructible()(_ctx(True), "ark-ranger-black") is True
    assert boss_part_destructible()(_ctx(False), "ark-ranger-black") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_part_destructible_flag.py -q`
Expected: FAIL (`ImportError: cannot import name 'boss_part_destructible'`).

- [ ] **Step 3: Add the SquadContext field and the condition**

In `backend/app/squad_engine.py`, add `part_destructible` to `SquadContext.__init__`. The signature currently is:

```python
    def __init__(
        self,
        members,
        base_atk=None,
        boss_element: str | None = None,
    ):
```

Change to add the parameter and store it (place the assignment next to `self.boss_element`):

```python
    def __init__(
        self,
        members,
        base_atk=None,
        boss_element: str | None = None,
        part_destructible: bool = False,
    ):
```
```python
        self.boss_element: str | None = boss_element
        self.part_destructible: bool = part_destructible
```

Then add the condition next to `boss_is_element` (after its definition, ~line 214):

```python
def boss_part_destructible() -> Callable[[SquadContext, str], bool]:
    """True when the boss has a part-destruction gimmick (BossProfile flag,
    threaded via raid_simulator). Ark Ranger Black uses it to select her
    permanent-transformation ceiling vs her burst-driven battery floor."""

    def condition(context: "SquadContext", caster_slug: str) -> bool:
        return context.part_destructible

    return condition
```

- [ ] **Step 4: Thread the flag through simulate_raid**

In `backend/app/raid_simulator.py`, add `part_destructible=False` to the `simulate_raid` signature (next to `boss_element=None`, ~line 219) and pass it into the `SquadContext(...)` call (~line 243):

```python
    boss_element=None,
    part_destructible=False,
```
```python
    context = SquadContext(
        [SquadMember(m["slug"], m["burst_tier"], m["element"]) for m in deck],
        base_atk={m["slug"]: base_stats[m["slug"]]["atk"] for m in deck},
        boss_element=boss_element,
        part_destructible=part_destructible,
    )
```

- [ ] **Step 5: Add the flag to BossProfile and evaluate_deck**

In `backend/app/deck_search.py`, add the field to `BossProfile` (after `mode`):

```python
@dataclass
class BossProfile:
    element: str | None = None
    core_hittable: bool = False
    enemy_def: float = 0.0
    fight_duration: float = 180.0
    gauge_charge_time: float = 2.0
    mode: str = "manual"
    part_destructible: bool = False
```

And pass it in `evaluate_deck`:

```python
    return simulate_raid(
        **inputs,
        enemy_def=boss.enemy_def,
        gauge_charge_time=boss.gauge_charge_time,
        fight_duration=boss.fight_duration,
        mode=boss.mode,
        core_hittable=boss.core_hittable,
        boss_element=boss.element,
        part_destructible=boss.part_destructible,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_part_destructible_flag.py -q`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git add backend/app/squad_engine.py backend/app/raid_simulator.py backend/app/deck_search.py backend/tests/test_part_destructible_flag.py
git commit -m "Add BossProfile.part_destructible flag + boss_part_destructible condition"
```

---

## Task 2: `requires_part_destructible` filter on DoT specs

Lets a `resource_scaled_nukes` or `periodic_nukes` spec opt into firing only when `context.part_destructible` matches. Absent field = always active (backward compatible).

**Files:**
- Modify: `backend/app/raid_simulator.py` (`resource_scaled_nukes` loop ~line 379; `periodic_nukes` loop ~line 720)
- Test: `backend/tests/test_part_destructible_dot_filter.py` (new)

**Interfaces:**
- Consumes: `context.part_destructible` (Task 1).
- Produces: DoT specs may carry `"requires_part_destructible": True | False`; when present and `!= context.part_destructible`, the spec is skipped. `periodic_nukes` values may now be filtered the same way.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_part_destructible_dot_filter.py`:

```python
from app.raid_simulator import simulate_raid
from app.roster import NikkeSpec


def _one_unit_inputs():
    # Minimal single-unit deck; only the DoT specs matter for this test.
    deck = [{"slug": "ark-ranger-black", "burst_tier": 3, "element": "Wind"}]
    base_stats = {"ark-ranger-black": {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0}}
    return deck, base_stats


def _total(part_destructible, floor_spec, ceiling_periodic):
    deck, base_stats = _one_unit_inputs()
    result = simulate_raid(
        deck=deck,
        base_stats=base_stats,
        resource_scaled_nukes={"ark-ranger-black": floor_spec},
        periodic_nukes={"ark-ranger-black": ceiling_periodic},
        fight_duration=20.0,
        part_destructible=part_destructible,
    )
    return result["total_damage"]


FLOOR = [{
    "base_percent": 100.0, "tick_count": 1, "tick_interval": 1.0,
    "damage_type": "sustained", "requires_part_destructible": False,
}]
CEILING = {
    "cooldown": 1.0, "percent": 100.0, "damage_type": "sustained",
    "requires_part_destructible": True,
}


def test_floor_dot_only_fires_when_not_part_destructible():
    assert _total(False, FLOOR, CEILING) > 0  # floor spec active, ceiling skipped
    # Same floor spec must be skipped when part_destructible is True:
    only_floor = _total(True, FLOOR, {"cooldown": 1.0, "percent": 0.0})
    only_floor_off = _total(False, [], {"cooldown": 1.0, "percent": 0.0})
    assert only_floor == only_floor_off  # floor contributed nothing when flag True


def test_ceiling_periodic_only_fires_when_part_destructible():
    with_flag = _total(True, [], CEILING)
    without_flag = _total(False, [], CEILING)
    assert with_flag > 0
    assert without_flag == 0
```

Note: check the exact `simulate_raid` keyword names for `deck`/`base_stats` in `raid_simulator.py` before running; if the assembled-inputs keys differ, adjust the test's kwargs to match the real signature (they are the same keys `evaluate_deck` passes via `**inputs`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_part_destructible_dot_filter.py -q`
Expected: FAIL (both DoT specs fire regardless of the flag, so `test_ceiling_periodic_only_fires_when_part_destructible`'s `without_flag == 0` assertion fails).

- [ ] **Step 3: Add the filter to both loops**

In `backend/app/raid_simulator.py`, in the `resource_scaled_nukes` loop (~line 379), skip specs whose requirement doesn't match. Insert at the top of the `for spec in resource_scaled_nukes.get(slug, []):` body:

```python
        for spec in resource_scaled_nukes.get(slug, []):
            required = spec.get("requires_part_destructible")
            if required is not None and required != context.part_destructible:
                continue
```

In the `periodic_nukes` loop (~line 720), add the same guard:

```python
    for slug, spec in periodic_nukes.items():
        required = spec.get("requires_part_destructible")
        if required is not None and required != context.part_destructible:
            continue
        cooldown = spec["cooldown"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_part_destructible_dot_filter.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Run full suite (no regressions from the filter)**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: PASS (all existing tests green; the filter is inert for specs without the field).

- [ ] **Step 6: Commit**

```bash
git add backend/app/raid_simulator.py backend/tests/test_part_destructible_dot_filter.py
git commit -m "Filter resource_scaled_nukes/periodic_nukes on requires_part_destructible"
```

---

## Task 3: Ark Ranger module — transformation buffs

The state-gated ATK buff (floor: 10s on burst / ceiling: permanent) and the always-on burst self Sustained Damage buff. Skill values are provided per sub-skill dict, mirroring `mana.py` / `rei_ayanami.py`.

**Files:**
- Create: `backend/app/skill_rules/ark_ranger_black.py`
- Modify: `backend/app/skill_rules/registry.py` (`_BUILDERS` ~line 243, import block ~line 20-160)
- Test: `backend/tests/test_skill_rules_ark_ranger_black.py` (new)

**Interfaces:**
- Consumes: `boss_part_destructible` (Task 1); `buff_rule`, `not_condition`.
- Produces: `build_ark_ranger_black_rules(values) -> list[SkillRule]`; registry `_BUILDERS["ark-ranger-black"] = lambda sv: (build_ark_ranger_black_rules(sv), None)`. Sub-skill keys: `values["transform"]`, `values["ultimate"]`, `values["caster_atk"]` (unused here but injected).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_skill_rules_ark_ranger_black.py`:

```python
from app.effects import EffectRegistry
from app.skill_rules.ark_ranger_black import build_ark_ranger_black_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real level-10 values (lootandwaifus), slots numbered by left-to-right appearance.
TRANSFORM = {
    "description_value_06": "156.19",  # ATK % while transformed
    "description_value_04": "1",       # battery decay % per interval
    "description_value_05": "0.2",     # decay interval (sec)
    "description_value_08": "30",      # normal-attack threshold (Sustained buff)
    "description_value_09": "59.6",    # Sustained Damage % (skill 1)
    "description_value_10": "5",       # its duration
}
ULTIMATE = {
    "description_value_01": "50",      # battery % after transforming (Emergency Charge)
    "description_value_02": "266.69",  # Meteor DoT % per tick
    "description_value_03": "10",      # Meteor tick count
    "description_value_04": "135.83",  # self Sustained Damage % (burst)
    "description_value_05": "10",      # its duration
}


def build():
    return build_ark_ranger_black_rules({
        "transform": TRANSFORM, "ultimate": ULTIMATE, "caster_atk": 100000.0,
    })


def _ctx(part_destructible):
    return SquadContext(
        [SquadMember("ark-ranger-black", 3, "Wind")],
        part_destructible=part_destructible,
    )


ARK = {"slug": "ark-ranger-black", "element": "Wind"}


def test_floor_atk_buff_on_burst_for_window_duration():
    # part_destructible False: ATK +156.19% applied at burst for D=10s.
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"ark-ranger-black": build()}, _ctx(False), registry, time=5.0)
    assert round(registry.total_for("atk_percent", ARK, now=5.0), 4) == 1.5619
    assert registry.total_for("atk_percent", ARK, now=15.1) == 0.0  # expires after 10s


def test_floor_atk_buff_absent_when_part_destructible():
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"ark-ranger-black": build()}, _ctx(True), registry, time=5.0)
    # the burst-window ATK buff is the floor variant; gone when flag True
    assert registry.total_for("atk_percent", ARK, now=5.0) == 0.0


def test_ceiling_atk_buff_permanent_from_battle_start():
    registry = EffectRegistry()
    fire_trigger("battle_start", {"ark-ranger-black": build()}, _ctx(True), registry, time=0.0)
    assert round(registry.total_for("atk_percent", ARK, now=170.0), 4) == 1.5619  # permanent


def test_ceiling_atk_buff_absent_when_not_part_destructible():
    registry = EffectRegistry()
    fire_trigger("battle_start", {"ark-ranger-black": build()}, _ctx(False), registry, time=0.0)
    assert registry.total_for("atk_percent", ARK, now=1.0) == 0.0


def test_burst_grants_self_sustained_damage_up_both_branches():
    for flag in (False, True):
        registry = EffectRegistry()
        fire_trigger("own_burst_activate", {"ark-ranger-black": build()}, _ctx(flag), registry, time=5.0)
        assert round(registry.total_for("sustained_damage_up", ARK, now=5.0), 4) == 1.3583
        assert registry.total_for("sustained_damage_up", ARK, now=15.1) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_ark_ranger_black.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.skill_rules.ark_ranger_black'`).

- [ ] **Step 3: Write the module (buffs only for now)**

Create `backend/app/skill_rules/ark_ranger_black.py`:

```python
"""Ark Ranger Black (slug "ark-ranger-black"), a Burst-3 Wind AR attacker.
Base skills. Her damage is almost entirely sustained-typed DoTs gated on
Transformation, which is driven by a self-depleting battery.

Modeled as a floor/ceiling bracket selected by BossProfile.part_destructible
(see docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md):
- floor (no part-destruction): transformation window [burst, burst+D], where
  D = post_transform_battery / (decay% / decay_interval) = 50 / (1/0.2) = 10 s.
- ceiling (part-destruction gimmick): permanent transformation.

Modeled (DPS-relevant):
- Transform! (skills[0]): while transformed, ATK +156.19%. Floor: applied at
  own_burst_activate for D sec. Ceiling: permanent from battle_start.
- Transform! per-30-normals: Sustained Damage +59.6% for 5 sec (per_shot, see
  build_ark_ranger_per_shot_rules) - both branches.
- Ark Black Collider (skills[1]): 45.87% sustained DoT while transformed. Floor:
  burst-anchored D-tick DoT; ceiling: whole-fight periodic 1s DoT (see
  build_ark_ranger_dots / build_ark_ranger_ceiling_collider).
- Ultimate! (skills[2], burst): Meteor 266.69% sustained DoT x10 (both
  branches); self Sustained Damage +135.83% for 10 sec (both branches).

Not modeled / deferred:
- Part-destruction battery fill (no enemy-part concept) - the reason for the
  floor/ceiling flag.
- Skill 2 Full-Burst "Wind Code allies with assault rifles: Sustained Damage
  +77.5%" - needs gap #3 (weapon+element scope); deferred to avoid overestimation.
- Damage to Parts +20% (skill 1) - situational part damage, not raid DPS.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import boss_part_destructible, not_condition


def transformation_window_seconds(values):
    """Public: seconds a floor-branch transformation lasts, derived from the
    skill values (post-transform battery drained at decay%/interval)."""
    transform = values["transform"]
    ultimate = values["ultimate"]
    post_transform = float(ultimate["description_value_01"])
    decay_pct = float(transform["description_value_04"])
    decay_interval = float(transform["description_value_05"])
    return post_transform / (decay_pct / decay_interval)


def build_ark_ranger_black_rules(values):
    transform = values["transform"]
    ultimate = values["ultimate"]
    atk = float(transform["description_value_06"]) / 100
    window = transformation_window_seconds(values)
    self_sustained = float(ultimate["description_value_04"]) / 100
    self_sustained_duration = float(ultimate["description_value_05"])

    floor = not_condition(boss_part_destructible())
    ceiling = boss_part_destructible()

    return [
        # ATK +156.19% while transformed - floor: window buff on burst.
        buff_rule("own_burst_activate", [("atk_percent", atk, "self", window)], condition=floor),
        # ceiling: permanent from battle start.
        buff_rule("battle_start", [("atk_percent", atk, "self", None)], condition=ceiling),
        # Burst self Sustained Damage +135.83% for 10s - both branches.
        buff_rule("own_burst_activate", [("sustained_damage_up", self_sustained, "self", self_sustained_duration)]),
    ]
```

- [ ] **Step 4: Register in `_BUILDERS`**

In `backend/app/skill_rules/registry.py`, add the import (with the other skill_rules imports) and the `_BUILDERS` entry:

```python
from app.skill_rules.ark_ranger_black import (
    build_ark_ranger_black_rules,
    build_ark_ranger_dots,
    build_ark_ranger_ceiling_collider,
    build_ark_ranger_per_shot_rules,
)
```
(the latter three are added in Tasks 4-5; add all four imports now and the modules follow, or add imports incrementally per task — if running tasks strictly in order, import only `build_ark_ranger_black_rules` here and extend the import in Tasks 4/5.)

```python
    "ark-ranger-black": lambda sv: (build_ark_ranger_black_rules(sv), None),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_ark_ranger_black.py -q`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/skill_rules/ark_ranger_black.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_ark_ranger_black.py
git commit -m "Ark Ranger Black: transformation ATK buff (floor/ceiling) + burst self sustained buff"
```

---

## Task 4: Ark Ranger DoTs — Meteor + Collider (floor tick DoT / ceiling periodic)

**Files:**
- Modify: `backend/app/skill_rules/ark_ranger_black.py`
- Modify: `backend/app/skill_rules/registry.py` (`_RESOURCE_SCALED_NUKE_BUILDERS` ~line 407; `_PERIODIC_NUKE_BUILDERS` ~line 306)
- Test: extend `backend/tests/test_skill_rules_ark_ranger_black.py`

**Interfaces:**
- Consumes: `transformation_window_seconds` (Task 3); `requires_part_destructible` filter (Task 2).
- Produces: `build_ark_ranger_dots(values) -> list[dict]` (Meteor always + floor Collider `requires_part_destructible=False`); `build_ark_ranger_ceiling_collider(values) -> dict` (ceiling Collider periodic, `requires_part_destructible=True`).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_skill_rules_ark_ranger_black.py`:

```python
from app.skill_rules.ark_ranger_black import (
    build_ark_ranger_dots,
    build_ark_ranger_ceiling_collider,
)


def test_meteor_dot_is_10_ticks_sustained_both_branches():
    specs = build_ark_ranger_dots({"transform": TRANSFORM, "ultimate": ULTIMATE})
    meteor = [s for s in specs if s.get("requires_part_destructible") is None]
    assert len(meteor) == 1
    assert meteor[0]["base_percent"] == 266.69
    assert meteor[0]["tick_count"] == 10
    assert meteor[0]["tick_interval"] == 1.0
    assert meteor[0]["damage_type"] == "sustained"


def test_floor_collider_dot_gated_off_when_part_destructible():
    specs = build_ark_ranger_dots({"transform": TRANSFORM, "ultimate": ULTIMATE})
    collider = [s for s in specs if s.get("requires_part_destructible") is False]
    assert len(collider) == 1
    assert collider[0]["base_percent"] == 45.87
    assert collider[0]["tick_count"] == 10       # D=10s / 1s interval
    assert collider[0]["damage_type"] == "sustained"


def test_ceiling_collider_is_wholefight_periodic_sustained():
    spec = build_ark_ranger_ceiling_collider({"tremble": {"description_value_01": "45.87"}})
    assert spec["cooldown"] == 1.0
    assert spec["percent"] == 45.87
    assert spec["damage_type"] == "sustained"
    assert spec["requires_part_destructible"] is True
```

Update `TREMBLE` and pass it where needed — add near the fixtures:

```python
TREMBLE = {"description_value_01": "45.87"}  # Ark Black Collider % per tick
```

And update `build_ark_ranger_dots`/`build_ark_ranger_ceiling_collider` calls in the tests to pass `"tremble": TREMBLE`:

```python
def test_meteor_dot_is_10_ticks_sustained_both_branches():
    specs = build_ark_ranger_dots({"transform": TRANSFORM, "ultimate": ULTIMATE, "tremble": TREMBLE})
    ...
```
(apply the same `"tremble": TREMBLE` addition to `test_floor_collider_dot_gated_off_when_part_destructible`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_ark_ranger_black.py -q`
Expected: FAIL (`ImportError: cannot import name 'build_ark_ranger_dots'`).

- [ ] **Step 3: Implement the DoT builders**

Append to `backend/app/skill_rules/ark_ranger_black.py`:

```python
def build_ark_ranger_dots(values):
    """Burst-anchored sustained tick DoTs (resource_scaled_nukes shape):
    - Meteor (skills[2]): 266.69% x10 ticks, always (both branches).
    - Collider FLOOR (skills[1]): 45.87% for D ticks, only when NOT
      part_destructible (transformation lasts one burst window)."""
    ultimate = values["ultimate"]
    tremble = values["tremble"]
    meteor_percent = float(ultimate["description_value_02"])
    meteor_ticks = int(float(ultimate["description_value_03"]))
    collider_percent = float(tremble["description_value_01"])
    window = transformation_window_seconds(values)
    collider_ticks = int(round(window / 1.0))
    return [
        {  # Meteor - both branches
            "base_percent": meteor_percent, "tick_count": meteor_ticks,
            "tick_interval": 1.0, "damage_type": "sustained",
        },
        {  # Collider floor - burst-anchored window DoT
            "base_percent": collider_percent, "tick_count": collider_ticks,
            "tick_interval": 1.0, "damage_type": "sustained",
            "requires_part_destructible": False,
        },
    ]


def build_ark_ranger_ceiling_collider(values):
    """Collider CEILING: permanent transformation => a whole-fight 1s periodic
    sustained DoT, only when part_destructible."""
    collider_percent = float(values["tremble"]["description_value_01"])
    return {
        "cooldown": 1.0, "percent": collider_percent, "damage_type": "sustained",
        "requires_part_destructible": True,
    }
```

- [ ] **Step 4: Register the DoT builders**

In `backend/app/skill_rules/registry.py`, extend the import from Task 3 to include `build_ark_ranger_dots` and `build_ark_ranger_ceiling_collider`, then add:

```python
# in _RESOURCE_SCALED_NUKE_BUILDERS (~line 407):
    "ark-ranger-black": lambda sv: build_ark_ranger_dots(sv),
```
```python
# in _PERIODIC_NUKE_BUILDERS (~line 306):
    "ark-ranger-black": lambda sv: build_ark_ranger_ceiling_collider(sv),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_ark_ranger_black.py -q`
Expected: PASS (8 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/skill_rules/ark_ranger_black.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_ark_ranger_black.py
git commit -m "Ark Ranger Black: Meteor + Collider sustained DoTs (floor tick / ceiling periodic)"
```

---

## Task 5: Ark Ranger per-shot — skill-1 Sustained Damage per 30 normals

**Files:**
- Modify: `backend/app/skill_rules/ark_ranger_black.py`
- Modify: `backend/app/skill_rules/registry.py` (`_PER_SHOT_RULE_BUILDERS` ~line 354)
- Test: extend `backend/tests/test_skill_rules_ark_ranger_black.py`

**Interfaces:**
- Consumes: `refreshing_buff_rule` (`_helpers`).
- Produces: `build_ark_ranger_per_shot_rules(values) -> list` of `(threshold, mode, [rules])`; registry `_PER_SHOT_RULE_BUILDERS["ark-ranger-black"]`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_skill_rules_ark_ranger_black.py`:

```python
from app.skill_rules.ark_ranger_black import build_ark_ranger_per_shot_rules


def test_per_shot_sustained_buff_every_30_normals_refreshes():
    rules = build_ark_ranger_per_shot_rules({"transform": TRANSFORM})
    assert len(rules) == 1
    threshold, mode, subrules = rules[0]
    assert (threshold, mode) == (30, "every")

    registry = EffectRegistry()
    ctx = _ctx(False)
    subrules[0].action(ctx, "ark-ranger-black", 3.0, registry)
    assert round(registry.total_for("sustained_damage_up", ARK, now=3.0), 4) == 0.596
    assert registry.total_for("sustained_damage_up", ARK, now=8.1) == 0.0  # 5s duration
    # refresh (not stack): apply again within window -> still 0.596
    subrules[0].action(ctx, "ark-ranger-black", 6.0, registry)
    assert round(registry.total_for("sustained_damage_up", ARK, now=6.0), 4) == 0.596
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_ark_ranger_black.py::test_per_shot_sustained_buff_every_30_normals_refreshes -q`
Expected: FAIL (`ImportError: cannot import name 'build_ark_ranger_per_shot_rules'`).

- [ ] **Step 3: Implement the per-shot builder**

Add `refreshing_buff_rule` to the module's `_helpers` import, then append:

```python
def build_ark_ranger_per_shot_rules(values):
    """Skill 1: after every 30 normal attacks, self Sustained Damage +59.6% for
    5 sec (refreshes rather than stacks). Both branches."""
    transform = values["transform"]
    threshold = int(float(transform["description_value_08"]))
    sustained = float(transform["description_value_09"]) / 100
    duration = float(transform["description_value_10"])
    return [(threshold, "every", [
        refreshing_buff_rule("per_shot", [("sustained_damage_up", sustained, "self", duration)]),
    ])]
```

Update the import line at the top of the module:

```python
from app.skill_rules._helpers import buff_rule, refreshing_buff_rule
```

- [ ] **Step 4: Register the per-shot builder**

In `backend/app/skill_rules/registry.py`, extend the Ark Ranger import to include `build_ark_ranger_per_shot_rules` and add:

```python
# in _PER_SHOT_RULE_BUILDERS (~line 354):
    "ark-ranger-black": lambda sv: build_ark_ranger_per_shot_rules(sv),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_ark_ranger_black.py -q`
Expected: PASS (9 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/skill_rules/ark_ranger_black.py backend/app/skill_rules/registry.py backend/tests/test_skill_rules_ark_ranger_black.py
git commit -m "Ark Ranger Black: per-30-normals Sustained Damage buff (both branches)"
```

---

## Task 6: End-to-end bracket test + docs

Confirms ceiling total damage > floor for a real deck, and that `sustained_damage_up` actually moves the DoTs. Then update the knowledge-base docs.

**Files:**
- Test: `backend/tests/test_ark_ranger_bracket.py` (new)
- Modify: `docs/roadmap.md`, `docs/encoded-nikkes.md`, `docs/engine-gaps.md`

**Interfaces:**
- Consumes: everything above, end to end via `deck_search.find_best_decks` / `evaluate_deck` or directly `simulate_raid`.

- [ ] **Step 1: Write the bracket test**

Create `backend/tests/test_ark_ranger_bracket.py`. Build a feasible 5-unit deck with Ark Ranger as the B3 attacker plus already-encoded fillers for tiers 1 and 2 (pick from the registry, e.g. `liter` (B1) and an existing B2 supporter), using the project's standard deck-assembly path. Assert:

```python
def test_ceiling_beats_floor_for_ark_ranger():
    floor = _evaluate_ark_ranger_deck(part_destructible=False)
    ceiling = _evaluate_ark_ranger_deck(part_destructible=True)
    assert ceiling["total_damage"] > floor["total_damage"]


def test_default_boss_reproduces_floor():
    default = _evaluate_ark_ranger_deck()  # part_destructible defaults False
    floor = _evaluate_ark_ranger_deck(part_destructible=False)
    assert default["total_damage"] == floor["total_damage"]
```

Model `_evaluate_ark_ranger_deck` on an existing end-to-end test (search `backend/tests/` for a test that calls `evaluate_deck` or `simulate_raid` with a full assembled deck, e.g. an existing `test_interaction_*.py`, and copy its assembly helper). Add a third assertion that flipping a Sustained Damage Up source changes the DoT total (guards the sustained tagging), or assert the floor result already includes nonzero sustained-typed damage in `result["damage_log"]`.

- [ ] **Step 2: Run test to verify it fails, then passes**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_ark_ranger_bracket.py -q`
Expected: PASS once the deck helper is correct (if it fails on assembly, fix the helper to match the real `evaluate_deck` inputs — not the engine).

- [ ] **Step 3: Run the FULL suite**

Run: `cd backend && PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: PASS (all green; new unit adds tests, no regressions).

- [ ] **Step 4: Update docs**

- `docs/encoded-nikkes.md`: add an Ark Ranger Black row (Burst 3, Wind, MG/AR — confirm weapon from data: AR). Rating: `⚠` (floor/ceiling bracket modeled; part-destruction fill + gap #3 Wind-AR buff + Damage-to-Parts deferred). Note the `part_destructible` boss flag.
- `docs/engine-gaps.md`: mark gap #2 Pattern B's Ark Ranger as addressed via the floor/ceiling `part_destructible` bracket (not a general time-decay primitive); note part-destruction fill still deferred.
- `docs/roadmap.md`: update the top test count and add a Phase 3 line for Ark Ranger Black (floor/ceiling bracket, new `part_destructible` boss flag).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_ark_ranger_bracket.py docs/roadmap.md docs/encoded-nikkes.md docs/engine-gaps.md
git commit -m "Ark Ranger Black: end-to-end floor/ceiling bracket test + docs"
```

---

## Self-Review notes (for the implementer)

- **Spec coverage:** flag+threading (T1), DoT branch filter (T2), ATK buff floor/ceiling + burst self buff (T3), Meteor + Collider floor/ceiling DoTs (T4), per-30 sustained buff (T5), bracket + sustained-wiring + docs (T6). Deferred items (part-destruction fill, gap #3 Wind-AR buff, Damage-to-Parts) are intentionally NOT tasks — they stay documented as deferred.
- **Slot numbers** in the fixtures are numbered by left-to-right appearance per the lootandwaifus convention; when wiring the real per-unit `skill_values`, confirm the builder's slot reads match how the values are transcribed (same as every existing encoded unit — the test fixture is the contract).
- **Weapon type:** the data says AR — confirm in `data/lootandwaifus/char_ark-ranger-black.json` when writing the encoded-nikkes row.
- **burst_percent is `None`** — her burst damage is the Meteor DoT, not a single-hit nuke.
