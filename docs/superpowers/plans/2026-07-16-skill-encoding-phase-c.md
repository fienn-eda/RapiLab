# Skill Encoding Phase C Implementation Plan (gaps #3 · #6 · #8 · #9)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Unit-encoding tasks additionally follow the `nikke-skill-encoding` skill.

**Goal:** Close the four remaining small/medium engine gaps the inventory has proven demand for — member-subset scope (#3), periodic-during-Full-Burst nukes (#6), resource-fill-triggered ally buffs (#8), first-bullet-after-reload marker (#9) — and immediately consume each with its blocked units: Tove·Ark Ranger Black·Arcana·Ada Wong(신규)·Little Mermaid·Maiden·Jill Valentine.

**Architecture:** No new Effect scopes for subsets — resolve member subsets to the existing `slugs:` scope at trigger time (the `top_atk_slugs` precedent), with `SquadMember` gaining a `weapon` field. Gap #6/#8/#9 are each a small, parallel addition to an existing `simulate_raid` mechanism (`periodic_nukes` window option, a fill-event buff pass, a `first_bullet` per-shot mode mirroring `last_bullet`). One deliberate refactor: RoundGrant→Effect conversion moves to a second pass so per-shot-granted round buffs work (needed by Jill).

**Tech Stack:** Python, pytest. Engine under `backend/app/`, tests under `backend/tests/`.

## Global Constraints

- Run tests with `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q` from `backend/` (`python3`, NOT `python`).
- TDD per step; full suite green before every commit; every extension is opt-in with defaults that keep all 56 existing encodings byte-identical.
- **배치 착수 전 유닛별 검증 필수** (Fienn 방침): each unit task starts by re-reading its Lv10 source text; the slot indexes written below were derived from the local data files on 2026-07-16 and MUST be re-confirmed against the unit's existing test fixture / raw text before use. Never invent a value; when a mechanic is unclear, stop and ask Fienn (standing instruction).
- Damage-formula authority: `.claude/skills/nikke-skill-encoding/references/damage-formula-reference.md`. Relevant here: **Normal Attack Damage Multiplier is a Final ATK modifier on the user's normal attacks only** (multiplies the normal attack's own coefficient — NOT an `attack_damage_up`-group bucket).
- "as additional damage" → `full_burst_bonus_eligible=True`; plain "as damage" → not (Fienn rule). None of this plan's nukes say "additional", so none opt in.
- Docs upkeep at each landing: `docs/encoded-nikkes.md` row, `docs/engine-gaps.md` gap status, `docs/roadmap.md` counters.
- If the frontend-stage-3 plan has landed first, each re-encoded/new unit must also keep/gain its `SKILL_VALUE_MANIFESTS` entry and pass the assembly harness.

## Lv10 source values captured 2026-07-16 (re-verify at each task)

| Unit | Bullet | Values |
|---|---|---|
| Tove (dollskills) | Modification Successful / Miracle SG-ally bullets | Attack Speed +42.24%, flat ATK 24.21% of caster ATK (from `tove.py` docstring; raw file missing — re-collect) |
| Ark Ranger Black | Tremble! skill 2, 2nd bullet | FB enter → Wind-Code AR allies, Sustained Damage ▲77.5% / 10s |
| Arcana | Awakened Destiny "The Magician" | FB end, Burst-3 Electric bursted allies, if Wheel of Fortune: Attack damage ▲180% / 15s (slots 04/05; Skill-2 CDR ▼75% not modeled — ally skill cooldowns aren't simulated) |
| Arcana | Cycle of Destiny "Strength" | same subset/condition: ATK ▲180% of caster's ATK / 15s (slots 02/03) |
| Ada Wong | Covert Support | FB enter, Burst-3 bursted allies: ATK ▲60% of caster ATK / 10s + True Damage ▲50% / 10s (+HP recovery, 비딜) |
| Ada Wong | Flash Grenade | during FB, every 2s: 420% final ATK as **True** damage; burst grants "activation time condition ▼1 sec for 10 sec" → **model: FB windows starting inside [her burst, +10s) tick at 1s** (Fienn ruling 2026-07-16) |
| Ada Wong | Secret Agent (burst, cd 40) | self ATK ▲40% / 10s + True Damage ▲42% / 10s; Special Modification: Charge Speed ▼300% & Charge Damage ▲1500% for 1 round → **model BOTH: charge time ×(1+300/100)=×4 (i.e. `charge_speed_percent = -300/(100+300) = -0.75` under the divide-by-(1+speed) wiring) + `charge_damage_bonus` +15.0, for 1 round** (Fienn ruling 2026-07-16) |
| Little Mermaid | Bubble Wave FB nuke | during FB, every 1s: 63.36% × 4 sequential hits ("as damage") |
| Maiden | Blessings Upon You (MP replenish) | Electric-Code allies **except self**: Elemental Advantage Attack Damage ▲40.9% / 10s + ATK ▲20.9% of caster ATK / 10s |
| Jill Valentine | Magnum Ammo | battle start + each reload-to-max: self Normal Attack Damage Multiplier ▲30% for 9 round(s) |
| Jill Valentine | Acid Ammo | battle start + each reload-to-max: first round applies 192%/1s sustained DoT for 30s |

---

## File Structure

- `backend/app/squad_engine.py` — `SquadMember.weapon` (optional).
- `backend/app/roster.py` — thread `"weapon"` into deck member dicts.
- `backend/app/raid_simulator.py` — `SquadMember(...)` weapon arg; `periodic_nukes` `during_full_burst`/`hit_count`; `resource_fill_triggered_buffs` param + pass; `first_bullet` per-shot mode; RoundGrant second-pass refactor; `normal_attack_damage_multiplier` phase-2 term.
- `backend/app/attack_rate.py` — `magazine_first_bullet_times` / `charge_first_bullet_times` / `first_bullet_shot_times`.
- `backend/app/skill_rules/_helpers.py` — `member_subset_buff_rule`.
- `backend/app/skill_rules/{tove,ark_ranger_black,arcana,little_mermaid,maiden_ice_rose,jill_valentine}.py` — re-encodes; `ada_wong.py` — NEW.
- `backend/app/skill_rules/registry.py` — new maps/entries (`_RESOURCE_FILL_TRIGGERED_BUFF_BUILDERS`, ada-wong, little-mermaid/jill periodic nukes, jill per-shot).
- Tests: `test_member_subset_scope.py`, `test_periodic_fb_nukes.py`, `test_resource_fill_triggered_buffs.py`, `test_first_bullet_marker.py` — NEW; unit test modules extended.

---

## Task 1: gap #3 — `SquadMember.weapon` + `member_subset_buff_rule`

**Files:**
- Modify: `backend/app/squad_engine.py` (SquadMember, ~line 15)
- Modify: `backend/app/raid_simulator.py` (SquadContext construction, ~line 252)
- Modify: `backend/app/roster.py` (deck append, ~line 85)
- Modify: `backend/app/skill_rules/_helpers.py`
- Test: `backend/tests/test_member_subset_scope.py` (new)

**Interfaces:**
- Produces: `SquadMember(slug, burst_tier, element, weapon=None)`; deck member dicts carry `"weapon"`; `member_subset_buff_rule(trigger, member_filter, buffs, condition=None, refreshing=False)` where `member_filter: Callable[[SquadMember, SquadContext], bool]` and `buffs: list[(stat, value, duration)]` — applied with a `"slugs:"` scope resolved at trigger time; empty selection applies nothing.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_member_subset_scope.py`:

```python
from app.effects import EffectRegistry
from app.skill_rules._helpers import member_subset_buff_rule
from app.squad_engine import SquadContext, SquadMember, fire_trigger


def _context():
    return SquadContext([
        SquadMember("caster", burst_tier=1, element="Wind", weapon="AR"),
        SquadMember("wind-ar", burst_tier=3, element="Wind", weapon="AR"),
        SquadMember("wind-sg", burst_tier=3, element="Wind", weapon="SG"),
        SquadMember("iron-ar", burst_tier=3, element="Iron", weapon="AR"),
    ])


def _rules():
    return member_subset_buff_rule(
        "full_burst_enter",
        lambda m, context: m.element == "Wind" and m.weapon == "AR",
        [("sustained_damage_up", 0.775, 10.0)],
    )


def test_buff_lands_only_on_matching_members():
    context, registry = _context(), EffectRegistry()
    fire_trigger("full_burst_enter", {"caster": [_rules()]}, context, registry, time=5.0)
    def total(slug, element, weapon):
        return registry.total_for("sustained_damage_up", {"slug": slug, "element": element, "weapon": weapon}, 6.0)
    assert total("wind-ar", "Wind", "AR") == 0.775
    assert total("caster", "Wind", "AR") == 0.775   # caster matches the filter too
    assert total("wind-sg", "Wind", "SG") == 0.0
    assert total("iron-ar", "Iron", "AR") == 0.0


def test_empty_selection_applies_nothing():
    context, registry = _context(), EffectRegistry()
    rule = member_subset_buff_rule(
        "full_burst_enter", lambda m, c: m.weapon == "MG", [("atk_percent", 1.0, 10.0)]
    )
    fire_trigger("full_burst_enter", {"caster": [rule]}, context, registry, time=5.0)
    assert registry.total_for("atk_percent", {"slug": "wind-ar", "element": "Wind"}, 6.0) == 0.0


def test_weapon_defaults_to_none_for_existing_constructions():
    member = SquadMember("x", burst_tier=1, element="Wind")
    assert member.weapon is None
```

- [ ] **Step 2: Run to verify failure** — `TypeError: SquadMember.__init__() got an unexpected keyword argument 'weapon'`.

- [ ] **Step 3: Implement**

`squad_engine.py`:

```python
@dataclass
class SquadMember:
    slug: str
    burst_tier: int
    element: str
    # Weapon type ("AR"/"SG"/...), for member-subset filters like "all Wind
    # Code allies with assault rifles" (gap #3). Optional so contexts that
    # don't need weapon targeting (most tests) stay unchanged.
    weapon: str | None = None
```

`raid_simulator.py` SquadContext construction:

```python
    context = SquadContext(
        [
            SquadMember(m["slug"], m["burst_tier"], m["element"], m.get("weapon"))
            for m in deck
        ],
        ...
```

`roster.py` deck append gains `"weapon": spec.weapon`:

```python
        deck.append(
            {"slug": spec.slug, "burst_tier": spec.burst_tier, "element": spec.element,
             "cooldown": spec.burst_cooldown, "weapon": spec.weapon}
        )
```

`_helpers.py` (near `highest_atk_buff_rule`):

```python
def member_subset_buff_rule(trigger, member_filter, buffs, condition=None, refreshing=False):
    """Timed buffs on the squad members selected by `member_filter` at trigger
    time - the narrow subsets Effect.scope can't express ("all Wind Code allies
    with assault rifles", "all Burst 3 allies who previously used their Burst
    Skill"). Resolved live to a "slugs:" scope like highest_atk_buff_rule, so
    dynamic state (burst_used_this_cycle) is read at the trigger's own moment.
    member_filter(member, context) -> bool; the caster is included when it
    matches. buffs: (stat, value, duration)."""

    def action(context, caster_slug, time, registry):
        slugs = [m.slug for m in context.members if member_filter(m, context)]
        if not slugs:
            return
        scope = "slugs:" + ",".join(slugs)
        for stat, value, duration in buffs:
            effect = Effect(stat, value, scope, duration, caster_slug)
            if refreshing:
                registry.add_refreshing(effect, applied_at=time)
            else:
                registry.add(effect, applied_at=time)

    return _rule(trigger, action, condition)
```

- [ ] **Step 4: Run new test file + full suite** — all green (weapon default None keeps every existing construction working).
- [ ] **Step 5: Commit** — `feat: member-subset buff scope (SquadMember.weapon + member_subset_buff_rule, gap #3)`

---

## Task 2: Ark Ranger Black skill-2 Wind-AR sustained buff (gap #3 첫 소비)

**Files:**
- Modify: `backend/app/skill_rules/ark_ranger_black.py` (`build_ark_ranger_black_rules` + docstring)
- Test: `backend/tests/test_skill_rules_ark_ranger_black.py` (extend)

**Interfaces:** Consumes Task 1's `member_subset_buff_rule`. No registry change (rule joins the existing builder's list).

- [ ] **Step 1: Verify data** — `data/lootandwaifus/char_ark-ranger-black.json`, Tremble! Lv10, 2nd bullet: "Activates when entering Full Burst. Affects all Wind Code allies with assault rifles. Sustained Damage ▲ 77.5% for 10 sec." Confirm which fixture dict/slots the module's `tremble` values use (left-to-right tokens: 45.87, 1, 77.5, 10 → the buff is slots 03/04); extend the test fixture with those slots if absent.
- [ ] **Step 2: Failing test** — deck-level: Ark + a Wind-AR ally + a Wind-SG ally; after `full_burst_enter` at time T, `total_for("sustained_damage_up", wind_ar_target, T+1) == 0.775` and `== 0.0` for the SG ally. (Ark herself is Wind AR — assert she matches too.)
- [ ] **Step 3: Implement** — in `build_ark_ranger_black_rules`, append:

```python
    tremble = values["tremble"]
    squad_sustained = float(tremble["description_value_03"]) / 100
    squad_sustained_duration = float(tremble["description_value_04"])
    rules.append(
        member_subset_buff_rule(
            "full_burst_enter",
            lambda m, context: m.element == "Wind" and m.weapon == "AR",
            [("sustained_damage_up", squad_sustained, squad_sustained_duration)],
        )
    )
```

Update the module docstring (remove this bullet from "보류"; it stays useful only when the deck has another Wind-AR sustained dealer or Ark herself — her own DoTs are sustained-typed, so it self-applies).
- [ ] **Step 4: Tests + full suite green. Step 5: Commit** — `Ark Ranger Black: Wind-AR ally Sustained Damage buff (gap #3 consumer)`. Update `docs/encoded-nikkes.md` row (보류 목록에서 제거).

---

## Task 3: Arcana "The Magician"/"Strength" tier-subset buffs (gap #3 소비)

**Files:**
- Modify: `backend/app/skill_rules/arcana.py`
- Test: `backend/tests/test_skill_rules_arcana.py` (extend)

- [ ] **Step 1: Verify data** — `data/dotgg/char_arcana.json` Lv10 slots (captured above): Awakened Destiny 04=180, 05=15 (Magician Attack Damage); Cycle of Destiny 02=180, 03=15 (Strength % of caster ATK). Both bullets: "Activates when Full Burst ends. Affects all Burst 3 Electric Code allies who previously cast their Burst Skill **if self is in Wheel of Fortune status**" → condition `own_burst_fired_this_cycle()` (the module's existing equivalence; `burst_used_this_cycle` is still populated during `full_burst_end` rules).
- [ ] **Step 2: Failing test** — context with arcana + a B3 Electric member + a B3 Fire member, both in `burst_used_this_cycle`, arcana too; fire `full_burst_end`; Electric B3 gets `attack_damage_up +1.80` and `flat_atk +1.80 * caster_atk`, Fire B3 gets nothing; without arcana in `burst_used_this_cycle` nothing applies.
- [ ] **Step 3: Implement** — in `build_arcana_rules`:

```python
    magician_attack_damage = float(awakened["description_value_04"]) / 100
    magician_duration = float(awakened["description_value_05"])
    strength_atk = float(cycle["description_value_02"]) / 100 * caster_atk
    strength_duration = float(cycle["description_value_03"])

    def bursted_electric_b3(member, context):
        return (
            member.burst_tier == 3
            and member.element == "Electric"
            and member.slug in context.burst_used_this_cycle
        )
```

and append to the returned list:

```python
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("attack_damage_up", magician_attack_damage, magician_duration)],
            condition=own_burst_fired_this_cycle(),
        ),
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("flat_atk", strength_atk, strength_duration)],
            condition=own_burst_fired_this_cycle(),
        ),
```

Docstring: move these from "Not modeled" to modeled; keep Magician's Skill-2 CDR deferred (ally Skill-2 cooldowns aren't simulated — only `periodic_rules` units have one, and none is Electric B3 today; note it).
- [ ] **Step 4/5: Suite green; commit** — `Arcana: The Magician/Strength bursted-Electric-B3 subset buffs (gap #3)`. Docs row: ⚠→✅ 후보 (남은 보류 확인 후).

---

## Task 4: Tove SG-ally bullets (gap #3 소비, Phase-C 약속분)

**Files:**
- Modify: `backend/app/skill_rules/tove.py`
- Test: `backend/tests/test_skill_rules_burst1_batch2.py` (Tove's tests live in a batch file — locate with `grep -l tove backend/tests/*.py` and extend there)

- [ ] **Step 1: Collect data** — `data/lootandwaifus/char_tove.json` does not exist and `data/dotgg` has no tove file. Run `/collect-nikke tove` (or the nikke-data-collector agent) first. From the collected dollskills Lv10 text, confirm: the Attack Speed +42.24% SG-ally bullet (Modification Successful — trigger/duration/slot) and the ATK +24.21%-of-caster-ATK SG-ally bullet (Miracle of Makeshifts — trigger/duration/slot). **The two percentages are known anchors from `tove.py`'s docstring (deferred 2026-07-16, Fienn); the triggers/durations/slots below are the expected reading — correct them from the collected text before implementing, and ask Fienn if the text is ambiguous.**
- [ ] **Step 2: Failing test** — context with tove (AR) + an SG ally + an AR ally; after the confirmed trigger fires, SG ally has `attack_speed_percent == 0.4224` (and the AR ally 0), and after tove's burst the SG ally has the flat ATK while the AR ally doesn't.
- [ ] **Step 3: Implement** — expected shape (slot indexes TBC per Step 1):

```python
    sg_only = lambda m, context: m.weapon == "SG"
    sg_attack_speed = float(modification["description_value_02"]) / 100   # 42.24 - confirm slot
    sg_atk = caster_atk * float(miracle["description_value_03"]) / 100    # 24.21 - confirm slot
    rules += [
        # Modification Successful: continuous under the module's existing
        # full-stack steady-state assumption, like the squad crit rate.
        member_subset_buff_rule("battle_start", sg_only,
                                [("attack_speed_percent", sg_attack_speed, None)]),
        member_subset_buff_rule("own_burst_activate", sg_only,
                                [("flat_atk", sg_atk, atk_duration)]),
    ]
```

`attack_speed_percent` is live-read per magazine (Phase S wiring), so an SG ally genuinely fires more shots — assert via a small `simulate_raid` run (SG ally shot count with Tove > without).
- [ ] **Step 4/5: Suite green; commit** — `Tove: SG-ally Attack Speed + flat ATK bullets (gap #3, Phase-C promise)`. Docs: tove ✅ 유지·보류 목록 갱신.

---

## Task 5: gap #6 — `periodic_nukes` during-Full-Burst window + `hit_count`

**Files:**
- Modify: `backend/app/raid_simulator.py` (periodic_nukes loop, ~line 740)
- Test: `backend/tests/test_periodic_fb_nukes.py` (new)

**Interfaces:**
- Produces: a `periodic_nukes` spec may carry `"during_full_burst": True` (ticks only inside each Full Burst window, first tick at `window_start + cooldown`, then every `cooldown` while `< window_end`), `"hit_count": N` (each tick records N separate hits — same rationale as `burst_hit_counts`), and `"own_burst_interval": (interval, duration)` — a FB window whose start falls inside `[own_burst_time, own_burst_time + duration)` for any of the owner's `context.burst_times` ticks at `interval` instead of `cooldown` (Ada's Flash Grenade enhancement: 1s ticks for the 10s after her own burst; her burst and the FB start share ~the same instant, so use a `<=` start comparison). Defaults keep existing specs identical.

- [ ] **Step 1: Failing test** — a `simulate_raid` run with one unit and `periodic_nukes={"u": {"cooldown": 2.0, "percent": 100.0, "during_full_burst": True}}`: every `source == "periodic"` damage-log time lies inside a full-burst window (derive windows from `result["events"]`), and there are `floor((window_len - epsilon)/2)` ticks per window (10s window, 2s cd → 4 ticks at +2,+4,+6,+8). Plus a `hit_count: 4` case: 4 log entries per tick time. Plus an `own_burst_interval: (1.0, 10.0)` case: a B3 owner (whose burst opens every FB window) gets 1s ticks (9/window), while the same spec on a unit who never bursts keeps 2s ticks.
- [ ] **Step 2: Implement** — replace the loop body:

```python
    for slug, spec in periodic_nukes.items():
        required = spec.get("requires_part_destructible")
        if required is not None and required != context.part_destructible:
            continue
        cooldown = spec["cooldown"]
        percent = spec["percent"]
        damage_type = spec.get("damage_type", "attack")
        hit_count = spec.get("hit_count", 1)
        eligible = spec.get("full_burst_bonus_eligible", False)

        def _tick(tick_time):
            for _ in range(hit_count):
                record(slug, percent, tick_time, "periodic", damage_type=damage_type,
                       full_burst_bonus_eligible=eligible)

        if spec.get("during_full_burst"):
            # Ticks only inside Full Burst windows, anchored to each window's
            # start (gap #6 - e.g. Ada Wong's Flash Grenade "every 2 sec during
            # Full Burst", Little Mermaid's Bubble Wave "every 1 sec only
            # during Full Burst"). own_burst_interval=(interval, duration):
            # a window starting inside [own burst, +duration) ticks at the
            # enhanced interval instead (Ada's post-burst "activation time
            # condition v 1 sec for 10 sec", Fienn 2026-07-16).
            own_interval = spec.get("own_burst_interval")
            own_bursts = context.burst_times.get(slug, [])
            for start, end in full_burst_windows:
                interval = cooldown
                if own_interval is not None and any(
                    bt <= start < bt + own_interval[1] for bt in own_bursts
                ):
                    interval = own_interval[0]
                tick = start + interval
                while tick < end:
                    _tick(tick)
                    tick += interval
        else:
            tick = cooldown
            while tick < fight_duration:
                _tick(tick)
                tick += cooldown
```

(Beware the classic late-binding pitfall: `_tick` closes over loop variables — keep it defined inside the `for slug, spec` body as shown, where it's re-created per spec.)
- [ ] **Step 3/4: New tests + full suite green (existing helm-aquamarine/isabel/ark periodic tests unchanged). Commit** — `feat: periodic_nukes during_full_burst window + hit_count (gap #6)`

---

## Task 6: Little Mermaid Bubble Wave FB nuke (gap #6 소비)

**Files:**
- Modify: `backend/app/skill_rules/little_mermaid.py`, `backend/app/skill_rules/registry.py` (`_PERIODIC_NUKE_BUILDERS`)
- Test: little-mermaid's test module (locate via `grep -l little_mermaid backend/tests/*.py`)

- [ ] **Step 1: Verify data** — Bubble Wave Lv10, 3rd bullet: "Activates every 1 sec only during Full Burst … Deals 63.36% of final ATK as damage. Attacks sequentially 4 times." Confirm the module's existing `bubble_wave` slot numbering against its fixture (raw tokens: 5.05, 50, 5.05, 3, 1, 63.36, 4, 500, 85, 10 → interval=slot 05, percent=slot 06, hits=slot 07 under plain left-to-right — verify against the fixture the module actually uses).
- [ ] **Step 2: Failing test** — builder returns the spec dict; deck-level assert periodic entries only in FB windows with 4 hits per tick.
- [ ] **Step 3: Implement**:

```python
def build_bubble_wave_fb_nuke(values):
    """Bubble Wave's 3rd bullet: every 1 sec only during Full Burst, 63.36% of
    final ATK x 4 sequential hits ("as damage" - no Full Burst Bonus opt-in)."""
    wave = values["bubble_wave"]
    return {
        "cooldown": float(wave["description_value_05"]),
        "percent": float(wave["description_value_06"]),
        "hit_count": int(float(wave["description_value_07"])),
        "during_full_burst": True,
    }
```

registry:

```python
    "little-mermaid": lambda sv: build_bubble_wave_fb_nuke(sv),
```

(added to `_PERIODIC_NUKE_BUILDERS`; import alongside `build_little_mermaid_rules`).
Docstring/docs: FB창 주기넉 → modeled; Bubble Barrage(아군 총탄 500 카운터)와 버스트게이지 fill은 여전히 보류(스쿼드 합산 탄약 카운터는 별도 갭).
- [ ] **Step 4/5: Suite green; commit** — `Little Mermaid: Bubble Wave during-FB periodic nuke (gap #6)`. Docs row 갱신.

---

## Task 7: Ada Wong 신규 인코딩 (gap #3 + #6 소비)

**Files:**
- Create: `backend/app/skill_rules/ada_wong.py`
- Modify: `backend/app/skill_rules/registry.py` (`_BUILDERS` + `_PERIODIC_NUKE_BUILDERS`)
- Test: `backend/tests/test_skill_rules_ada_wong.py` (new)

- [ ] **Step 1: Verify data** — `data/lootandwaifus/char_ada-wong.json` (exists), Lv10 texts as captured in the table above. Slot numbering (plain left-to-right): Covert Support 01=60, 02=10, 03=50, 04=10, 05=10(HP회복%), 06=10 · Flash Grenade 01=2, 02=420, 03=1, 04=10 · Secret Agent 01=40, 02=10, 03=42, 04=10, 05=1, 06=300, 07=1500.
- [ ] **Step 2: Fienn rulings (2026-07-16, both RESOLVED — implement, don't re-ask):**
  1. **Special Modification** (burst: Charge Speed ▼300% + Charge Damage ▲1500% for 1 round): model BOTH halves. "Charge Speed ▼ X%" = charge time ×(1+X/100), i.e. ×4 here — under the engine's divide-by-(1+speed) wiring that's `charge_speed_percent = -X/(100+X) = -0.75`. Grant `[("charge_speed_percent", -0.75, "self"), ("charge_damage_bonus", 15.0, "self")]` for 1 round via `round_buff_rule("own_burst_activate", ..., shots=1)`. **Verify in a test, don't assume:** charge speed is evaluated once per magazine boundary, so a 1-shot Effect window usually contains NO magazine start — the slowdown may be inert while the +1500% damage applies, which over-credits (the exact thing Fienn's ruling meant to avoid). If the test shows the slowdown never lands, apply the pair as a net approximation instead — e.g. keep the 1-round `charge_damage_bonus` but scale it down by the unpaid time cost (÷4, i.e. +2.75 net) — document whichever was done in the module docstring and report the deviation.
  2. **Flash Grenade enhancement**: model via Task 5's `own_burst_interval` — spec gains `"own_burst_interval": (1.0, enhancement_duration)` (interval slot 03 = 1, duration slot 04 = 10), so FB windows opened by her own burst tick at 1s.
- [ ] **Step 3: Failing tests** — burst percent is None; Covert Support hits exactly bursted B3 members at FB enter (flat ATK `0.60*caster_atk` + `true_damage_up 0.50`); own burst grants self `atk_percent 0.40` + `true_damage_up 0.42` and the 1-round Special Modification pair; deck-level: `source=="periodic"` true-typed 420% ticks only inside FB windows at 1s spacing when Ada bursts (2s for a never-bursting owner), and (interaction) a `true_damage_up` buff raises those ticks (Ada's Flash Grenade is her own true-damage consumer).
- [ ] **Step 4: Implement**

```python
"""Ada Wong (slug "ada-wong"), a Burst-3 Electric RL attacker. Collected from
lootandwaifus (2026-07-16 file).

Modeled (DPS-relevant):
- Covert Support (skills[0], on entering Full Burst): all Burst 3 allies who
  previously used their Burst Skill (member-subset scope, gap #3) get flat ATK
  = 60% of caster's ATK and True Damage ^ 50%, 10 sec. Ada herself matches
  once her burst fired.
- Flash Grenade (skills[1]): during Full Burst, every 2 sec, 420% of final ATK
  as True Damage (periodic_nukes during_full_burst, gap #6; true-typed so
  true_damage_up applies and enemy DEF is ignored). Her burst's "activation
  time condition v 1 sec for 10 sec" makes FB windows opened by HER OWN burst
  tick at 1s instead (own_burst_interval, Fienn 2026-07-16).
- Secret Agent (skills[2], her burst): self ATK ^ 40% and True Damage ^ 42%
  for 10 sec, plus Special Modification for 1 round: charge time x4
  ("Charge Speed v 300%" = charge time x(1+3.0), Fienn 2026-07-16 - wired as
  charge_speed_percent -0.75 under the divide-by-(1+speed) convention) and
  Charge Damage ^ 1500%. Charge speed is evaluated per magazine boundary
  (the engine's documented charge-speed approximation), so the slowdown lands
  on the next magazine starting inside the 1-round window. Buff-only burst
  (no burst nuke percent).

Not modeled / deferred:
- Covert Support's HP recovery (survival, not DPS).
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule, round_buff_rule


def build_ada_wong_rules(values):
    covert = values["covert_support"]
    secret = values["secret_agent"]
    caster_atk = values["caster_atk"]

    covert_flat_atk = caster_atk * float(covert["description_value_01"]) / 100
    covert_atk_duration = float(covert["description_value_02"])
    covert_true = float(covert["description_value_03"]) / 100
    covert_true_duration = float(covert["description_value_04"])
    self_atk = float(secret["description_value_01"]) / 100
    self_atk_duration = float(secret["description_value_02"])
    self_true = float(secret["description_value_03"]) / 100
    self_true_duration = float(secret["description_value_04"])
    special_mod_rounds = int(float(secret["description_value_05"]))          # 1 round
    charge_slow_percent = float(secret["description_value_06"])              # 300 (v)
    charge_speed = -charge_slow_percent / (100 + charge_slow_percent)        # -0.75: charge time x(1+300/100)
    charge_damage = float(secret["description_value_07"]) / 100              # 15.0

    def bursted_b3(member, context):
        return member.burst_tier == 3 and member.slug in context.burst_used_this_cycle

    return [
        member_subset_buff_rule("full_burst_enter", bursted_b3, [
            ("flat_atk", covert_flat_atk, covert_atk_duration),
            ("true_damage_up", covert_true, covert_true_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("atk_percent", self_atk, "self", self_atk_duration),
            ("true_damage_up", self_true, "self", self_true_duration),
        ]),
        round_buff_rule("own_burst_activate", [
            ("charge_speed_percent", charge_speed, "self"),
            ("charge_damage_bonus", charge_damage, "self"),
        ], shots=special_mod_rounds),
    ]


def build_flash_grenade_periodic_nuke(values):
    grenade = values["flash_grenade"]
    return {
        "cooldown": float(grenade["description_value_01"]),
        "percent": float(grenade["description_value_02"]),
        "damage_type": "true",
        "during_full_burst": True,
        "own_burst_interval": (
            float(grenade["description_value_03"]),   # 1 sec
            float(grenade["description_value_04"]),   # for 10 sec
        ),
    }
```

registry: `_BUILDERS["ada-wong"] = lambda sv: (build_ada_wong_rules(sv), None)`; `_PERIODIC_NUKE_BUILDERS["ada-wong"] = lambda sv: build_flash_grenade_periodic_nuke(sv)`.
- [ ] **Step 5: Suite green; commit** — `Encode Ada Wong (subset buffs gap #3 + during-FB true nuke gap #6)`. `docs/encoded-nikkes.md`에 신규 ⚠ 행 추가(57번째), roadmap 카운터 갱신.

---

## Task 8: gap #8 — `resource_fill_triggered_buffs` + Maiden 재인코딩

**Files:**
- Modify: `backend/app/raid_simulator.py` (new param + pass, directly after the `resource_specs` resolution loop, ~line 684)
- Modify: `backend/app/roster.py` + `backend/app/skill_rules/registry.py` (threading: `_RESOURCE_FILL_TRIGGERED_BUFF_BUILDERS` map + `get_resource_fill_triggered_buffs` + assemble key)
- Modify: `backend/app/skill_rules/maiden_ice_rose.py`
- Test: `backend/tests/test_resource_fill_triggered_buffs.py` (new) + maiden test module (extend)

**Interfaces:**
- Produces: `simulate_raid(..., resource_fill_triggered_buffs=None)` — `{owner_slug: [spec]}`, spec = `{"resource": str, "member_filter": Callable[[SquadMember, str], bool] (owner slug is 2nd arg), "buffs": [(stat, value, duration)], "condition": Callable[[SquadContext, str], bool] | None}`. At EVERY fill event of `(owner, resource)`, the buffs are applied (refreshing — consecutive fills inside the duration refresh, NIKKE convention) with a `slugs:` scope over the filtered members. Registry map named `_RESOURCE_FILL_TRIGGERED_BUFF_BUILDERS`, getter `get_resource_fill_triggered_buffs(slug, skill_values)`.

- [ ] **Step 1: Failing engine test** — hand-built `simulate_raid` run: a resource that fills at known times + a fill-triggered squad-subset buff; assert `total_for` rises exactly at fill times for matching members only, and that a `condition=boss_is_element("Water")` spec is inert when `boss_element="Fire"`.
- [ ] **Step 2: Implement the pass** (after the `resource_specs` loop, before `resource_gated_buffs` — fills are all recorded by then; buffs are phase-2-visible):

```python
    # A buff triggered by a resource's FILL events, landing on OTHER squad
    # members (gap #8 - e.g. Maiden's Blessings Upon You: "when MP is
    # replenished, affects all Electric Code allies except for self").
    # resource_gated_buffs reads a count at the owner's burst; this reacts to
    # each fill itself. Refreshing: consecutive fills within the duration
    # refresh rather than stack (one source, NIKKE convention).
    for slug, specs in resource_fill_triggered_buffs.items():
        for spec in specs:
            if spec.get("condition") is not None and not spec["condition"](context, slug):
                continue
            targets = [m.slug for m in context.members if spec["member_filter"](m, slug)]
            if not targets:
                continue
            scope = "slugs:" + ",".join(targets)
            for fill_time, _amount in context.resource_fills.get((slug, spec["resource"]), []):
                for stat, value, duration in spec["buffs"]:
                    registry.add_refreshing(
                        Effect(stat, value, scope, duration, slug), applied_at=fill_time
                    )
```

plus the `resource_fill_triggered_buffs=None` param + `or {}` default, registry map/getter (same pattern as `_RESOURCE_GATED_BUFF_BUILDERS`), and the `assemble_simulation_inputs` key.
- [ ] **Step 3: Maiden re-encode.** Verify Blessings Upon You Lv10 1st bullet (captured above). Two specs — the Elemental Advantage one gated on the boss being Water (Electric>Water, the `other_elemental_bonus` + `boss_is_element` precedent from rei-ayanami/marciana):

```python
def build_blessings_fill_triggered_buffs(values):
    """Blessings Upon You, 1st bullet: when MP is replenished, all Electric
    Code allies EXCEPT Maiden get Elemental Advantage Attack Damage +40.9%
    (only meaningful vs a Water boss - other_elemental_bonus is gated on
    actual advantage) and flat ATK = 20.9% of Maiden's ATK, 10 sec each."""
    blessings = values["blessings_upon_you"]
    caster_atk = values["caster_atk"]
    elemental = float(blessings["description_value_01"]) / 100
    elemental_duration = float(blessings["description_value_02"])
    flat_atk = caster_atk * float(blessings["description_value_03"]) / 100
    atk_duration = float(blessings["description_value_04"])

    def electric_allies_except_owner(member, owner_slug):
        return member.element == "Electric" and member.slug != owner_slug

    return [
        {
            "resource": "mp",
            "member_filter": electric_allies_except_owner,
            "buffs": [("other_elemental_bonus", elemental, elemental_duration)],
            "condition": boss_is_element("Water"),
        },
        {
            "resource": "mp",
            "member_filter": electric_allies_except_owner,
            "buffs": [("flat_atk", flat_atk, atk_duration)],
        },
    ]
```

(Confirm the module's `blessings_upon_you` slot numbering against its existing fixture — the same sub-skill already feeds the modeled self-buffs, so the fill-buff slots must match that established numbering, not a fresh count. Confirm the MP resource's registered name — `"mp"` — from `build_mp_resources`.)
Registry: `_RESOURCE_FILL_TRIGGERED_BUFF_BUILDERS["maiden-ice-rose"] = lambda sv: build_blessings_fill_triggered_buffs(sv)`.
Test: deck with maiden + Electric ally + Fire ally vs a Water boss — Electric ally's `flat_atk`/`other_elemental_bonus` step up at MP fill times; Fire ally and maiden herself unaffected; vs a Fire boss only `flat_atk` applies.
- [ ] **Step 4/5: Suite green; commit** — `feat: resource-fill-triggered ally buffs (gap #8) + Maiden Blessings consumer`. Docs: maiden 보류에서 제거(잔여는 최대체력 스택 비딜만 → ⚠→✅ 검토), engine-gaps #8 완료 표기.

---

## Task 9: gap #9 — first-bullet marker + Jill Valentine 재인코딩

**Files:**
- Modify: `backend/app/attack_rate.py` (first-bullet mirrors of the last-bullet trio)
- Modify: `backend/app/raid_simulator.py` (`"first_bullet"` per-shot mode; RoundGrant second-pass refactor; `normal_attack_damage_multiplier` phase-2 term)
- Modify: `backend/app/skill_rules/jill_valentine.py`, `registry.py`
- Test: `backend/tests/test_first_bullet_marker.py` (new), `backend/tests/test_attack_rate.py` + jill test module (extend)

### 9a. `attack_rate` first-bullet times

- [ ] **Failing test** (`test_attack_rate.py`): for an AR (12/s, 60 ammo, 1s reload), `first_bullet_shot_times(...)` == `{0.0, 6.0, 12.0, ...}`-style set equal to each magazine's `magazine_start` (mirror of the last-bullet test; include t=0 — Jill's trigger text is "at the start of battle and upon reloading to Max Ammunition"). Charge weapon: first shot is `magazine_start + effective_charge`.
- [ ] **Implement** — mirrors of the existing trio (same live-recalc structure):

```python
def magazine_first_bullet_times(rate_of_fire, max_ammo, reload_time, fight_duration,
                                max_ammo_percent_at=_zero, reload_speed_percent_at=_zero,
                                attack_speed_percent_at=_zero):
    """Mirror of magazine_last_bullet_times: each magazine's FIRST round,
    INCLUDING the battle-opening magazine at t=0 (a "at the start of battle and
    upon reloading to Max Ammunition" trigger, gap #9 - e.g. Jill Valentine's
    Magnum/Acid Ammo)."""
    first_bullets = set()
    magazine_start = 0.0
    while magazine_start < fight_duration:
        first_bullets.add(magazine_start)
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_empty_at = magazine_start + magazine_size * shot_interval
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time
    return first_bullets


def charge_first_bullet_times(charge_time, reload_time, max_ammo, fight_duration,
                              max_ammo_percent_at=_zero, reload_speed_percent_at=_zero,
                              charge_speed_percent_at=_zero):
    """Charge-weapon mirror: the first charged shot of each magazine (lands
    one effective charge after the magazine starts)."""
    first_bullets = set()
    magazine_start = 0.0
    while magazine_start < fight_duration:
        effective_charge = charge_time / (1 + charge_speed_percent_at(magazine_start))
        first_shot = magazine_start + effective_charge
        if first_shot >= fight_duration:
            return first_bullets
        first_bullets.add(first_shot)
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_round_time = magazine_start + effective_charge + (magazine_size - 1) * effective_charge
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(last_round_time))
        magazine_start = last_round_time + actual_reload_time
    return first_bullets


def first_bullet_shot_times(weapon, max_ammo, reload_time, charge_time, fight_duration,
                            max_ammo_percent_at=_zero, reload_speed_percent_at=_zero,
                            attack_speed_percent_at=_zero, charge_speed_percent_at=_zero):
    if weapon in CHARGE_WEAPONS:
        return charge_first_bullet_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return magazine_first_bullet_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
    )
```

(A magazine whose first shot lands at `magazine_start >= fight_duration` never fires — the `while` guard already excludes it for magazine weapons; the charge variant checks the charged first-shot time explicitly.)

### 9b. `"first_bullet"` per-shot mode + RoundGrant second pass

- [ ] **Failing tests** (`test_first_bullet_marker.py`): (1) a `per_shot_rules` entry `(None, "first_bullet", [rule])` fires exactly at the unit's first-bullet times; (2) **ordering regression**: a first_bullet rule that emits a `round_buff_rule("per_shot", [("normal_attack_damage_multiplier", 0.30, "self")], shots=9)` grant actually covers that unit's next 9 shots (this fails against today's code, where grants are converted before the unit's own per-shot rules run).
- [ ] **Implement in `raid_simulator.py`:**
  - Compute `first_bullets` next to `last_bullets` (`needs_first_bullets = any(mode == "first_bullet" ...)`; call `first_bullet_shot_times` with the same live-stat lambdas) and add to the shot-loop `fires` disjunction: `or (mode == "first_bullet" and shot_time in first_bullets)`.
  - **Move the RoundGrant→Effect conversion out of the per-unit weapon loop into a second loop** that runs after ALL units' shot loops (using the cached `shot_times_by_slug`), so grants recorded by per-shot rules — of this unit or a later-processed one — convert too. The conversion body is unchanged; only its placement moves. Existing consumers (Zwei, Miranda: burst-cycle-trigger grants) must stay byte-identical — their grants exist before any shot loop, so covering shots are the same.

### 9c. `normal_attack_damage_multiplier` (Final ATK modifier, normal attacks only)

- [ ] **Failing test**: a permanent `Effect("normal_attack_damage_multiplier", 0.30, "self", None, "u")` raises every `source=="normal_attack"` damage entry by exactly 1.30× and leaves burst/periodic entries untouched.
- [ ] **Implement** — per the damage-formula reference, this multiplies the normal attack's own coefficient. In phase 2:

```python
    def _normal_attack_percent(ev):
        # Normal Attack Damage Multiplier is a Final ATK modifier on the
        # user's NORMAL ATTACKS only (damage-formula reference) - it scales
        # the shot's own coefficient, not any Damage-Up bucket, and touches
        # no other damage source.
        multiplier = 1 + registry.total_for(
            "normal_attack_damage_multiplier", target_for(ev["slug"]), ev["time"]
        )
        return _resolve_percent(ev) * multiplier
```

and in the `damage_log` comprehension use `_normal_attack_percent(ev) if ev["source"] == "normal_attack" else _resolve_percent(ev)`.

### 9d. Jill Valentine re-encode

- [ ] **Verify data** — Magnum Ammo / Acid Ammo Lv10 (captured above); confirm the module's existing `magnum_ammo`/`acid_ammo` fixture slot numbering (expected left-to-right: Magnum 01=30, 02=9, 03=34.99, 04=10; Acid 01=192, 02=1, 03=30, 04=40.03, 05=10).
- [ ] **Fienn ruling (2026-07-16, RESOLVED — implement, don't re-ask):** Acid Ammo overlapping applications REFRESH (NIKKE convention). Under refresh, the ~6s reload cadence against the 30s duration makes it a continuous 192%/1s sustained DoT for the whole fight — model as `periodic_nukes {"cooldown": 1.0, "percent": 192.0, "damage_type": "sustained"}` (whole-fight, NOT during_full_burst). Record the ruling in the module docstring.
- [ ] **Implement**

```python
def build_magnum_per_shot_rules(values):
    """Magnum Ammo: at battle start and on each reload to Max Ammunition, her
    next 9 rounds deal +30% normal-attack damage (first_bullet marker, gap #9;
    round-count buff; normal_attack_damage_multiplier = Final ATK modifier on
    normal attacks only)."""
    magnum = values["magnum_ammo"]
    multiplier = float(magnum["description_value_01"]) / 100
    rounds = int(float(magnum["description_value_02"]))
    return [(None, "first_bullet", [
        round_buff_rule("per_shot", [("normal_attack_damage_multiplier", multiplier, "self")], shots=rounds)
    ])]


def build_acid_ammo_periodic_nuke(values):
    """Acid Ammo: refreshed on every reload-to-max (~6s cadence) with a 30s
    duration, so the refresh steady state is a continuous 1 tick/sec sustained
    DoT from battle start (her trigger includes battle start). Modeled as a
    whole-fight periodic sustained nuke - see the Fienn-confirmed refresh
    reading recorded in the module docstring."""
    acid = values["acid_ammo"]
    return {
        "cooldown": float(acid["description_value_02"]),
        "percent": float(acid["description_value_01"]),
        "damage_type": "sustained",
    }
```

registry: `_PER_SHOT_RULE_BUILDERS["jill-valentine"]`, `_PERIODIC_NUKE_BUILDERS["jill-valentine"]` (jill has neither today — pure additions). Import `round_buff_rule` in `jill_valentine.py`.
Tests: 9-shot coverage (shots 1–9 of each magazine boosted 1.30×, shot 10 not); sustained ticks present whole-fight and boosted by a `sustained_damage_up` buff; module docstring updated (Magnum/Acid move from deferred to modeled; 명중·힐은 잔여).
- [ ] **Suite green; commit** — `feat: first-bullet marker + normal-attack multiplier (gap #9); Jill Magnum/Acid consumer`. Docs: jill ⚠ 갱신(잔여 대폭 축소), engine-gaps #9 완료 표기.

---

## Task 10: 마무리 스윕

- [ ] Full suite: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q` — record the new count in `docs/roadmap.md`'s summary line.
- [ ] `docs/engine-gaps.md`: #3(무기종+티어부분집합 통합 소비 4+명)·#6(Ada·Little Mermaid)·#8(Maiden)·#9(Jill) 완료 표기 + "이미 만든 것" 추가; 우선순위 요약 표 갱신 (남는 것: Pattern B 일반 프리미티브·상태머신·무기변형·아군 총탄 카운터·not-in-FB 창 필터).
- [ ] `docs/encoded-nikkes.md`: Ada Wong 신규 행 + tove/ark/arcana/little-mermaid/maiden/jill 행의 완성도·보류 갱신, 총원 카운트(57).
- [ ] `docs/roadmap.md`: Phase 3 카운터·"다음" 문단 갱신 (남은 방향: Pattern B 프리미티브 / 상태머신·무기변형 / dotgg 스탯 수집).
- [ ] `/document`: gap #3 설계 결정(신규 Effect scope 대신 slugs: 해석), Fienn 판정 3건(Ada Special Modification "▼X% = 차지시간 ×(1+X/100)" 해석 · Flash Grenade own-burst 1s 틱 · Acid refresh→정상상태 DoT).
- [ ] Commit — `docs: Phase C sweep (gaps #3/#6/#8/#9 closed)`.

---

## Self-review checklist

- Every extension defaults inert (weapon=None, no `during_full_burst`, empty new params, multiplier stat unused elsewhere) — 기존 56명 출력 불변을 full suite로 증명.
- Consumers per gap: #3 → ark/arcana/tove/ada (drake-signature·arcana-fortune-mate의 SG squad-근사 정밀화는 선택 후속으로 문서에만 기록, 이번 배치 범위 아님). #6 → ada/little-mermaid. #8 → maiden. #9 → jill.
- 이전 Ask-Fienn 게이트 3건(Ada Special Modification·Flash Grenade 강화·Jill Acid refresh)은 2026-07-16 Fienn 판정으로 전부 해소됨 — Tasks 7/9의 RESOLVED 지침대로 구현하고 재질문하지 않는다. 단 Special Modification의 매거진-경계 함정은 테스트로 검증(Task 7 Step 2.1).
- Slot indexes are all marked "verify against the unit's existing fixture first" — fixtures are ground truth, plans are not.
