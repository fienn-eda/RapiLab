# Ark Ranger Black — Transformation encoding (design)

- Date: 2026-07-16
- Status: approved (design + judgment calls), pending spec review
- Scope: **Ark Ranger Black only** (slug `ark-ranger-black`), Wind AR Burst-3
  Attacker. NOT a general "Pattern B" primitive — Fienn de-scoped to this one
  unit after we found the roadmap's "Pattern B" bucket is really several
  unrelated per-unit mechanics.

## Goal

Encode Ark Ranger Black's transformation-driven kit into the simulation engine.
Her damage is almost entirely **sustained-typed DoTs**, and most of it is gated
on being in **Transformation** state, which is driven by a self-depleting
battery gauge.

## Key constraint: the battery fill is deferred, so we bracket

Her battery fills two ways:
1. **On part-destruction** (+50% per part destroyed) — **DEFERRED**: the engine
   has no "enemy part" concept, and how often a player destroys parts is
   per-player and per-boss, so we do not invent a fill schedule (Fienn,
   2026-07-12 / reaffirmed 2026-07-16).
2. **Via her burst** (Emergency Charge Protocol): when not transformed, her
   burst sets battery to 100% → transforms → drops to 50% "after transforming".

Because the part-destruction fill is unknowable, we model her as a **floor/
ceiling bracket** selected by a new boss-property flag:

| Boss has part-destruction gimmick | Transformation model | Meaning |
|---|---|---|
| No (`part_destructible=False`) | Burst-driven battery (window `[burst, burst+D]`) | **floor** — a lower bound |
| Yes (`part_destructible=True`) | **Permanent** transformation (whole fight) | **ceiling** — the max potential |

The player supplies this as a boss profile input, exactly like `element` /
`core_hittable` / `enemy_def` already work — there is no season-boss database.
When unsure of a boss, running both settings brackets her real output.

## Approach (C — compose existing mechanisms, no general state machine)

The floor-branch transformation window is exactly `[t_burst, t_burst + D]`
because transformation *starts at* the burst (Emergency Charge). So it is the
same shape as a **burst-anchored N-tick DoT**, which already exists. No general
time-decay state machine is needed; we select existing mechanisms by the flag.

**Window duration is derived, not hardcoded:**
`D = post_transform_battery% / decay_per_second = 50 / (1%/0.2s = 5%/s) = 10 s`.
That drives both the state-gated buff duration and the DoT tick count
(`ticks = D / tick_interval = 10 / 1 = 10`). If the skill values change, D
follows.

### Effect → mechanism map

| Effect (skill) | Floor (`part_destructible=False`) | Ceiling (`part_destructible=True`) |
|---|---|---|
| ATK +156.19% while transformed (skill 1) | `atk_percent` buff on `own_burst_activate`, duration `D` | `atk_percent` buff on `battle_start`, permanent |
| Ark Black Collider 45.87%/s while transformed (skill 2) | burst-anchored `D`-tick sustained DoT (Mana-style `resource_scaled_nukes`, no resource) | whole-fight `periodic_nukes`, 1 s cooldown |
| Ark Black Meteor 266.69%/s ×10 (skill 3 burst) | burst-anchored 10-tick sustained DoT — **same both branches** | same |
| Self Sustained Damage +135.83% for 10 s (skill 3 burst) | `sustained_damage_up` buff on `own_burst_activate` — **same both** | same |
| Sustained Damage +59.6% for 5 s, every 30 normals (skill 1) | `per_shot` every-30 `sustained_damage_up` buff — **same both** | same |

**Full Burst Bonus addendum (Fienn, 2026-07-16):** Meteor and BOTH Colliders
are `full_burst_bonus_eligible=True` per the repeating-tick-DoT rule (each
tick reads live buffs at its own time, so ticks landing inside the Full Burst
window get the bonus). The `periodic_nukes` loop originally had no FB-bonus
parameter; Fienn approved extending it the same day (optional opt-in field,
default False, so periodic units encoded earlier are unchanged until each is
deliberately flagged) — the ceiling Collider is the first consumer. Whether
existing periodic units (e.g. Helm: Aquamarine's Suppression Fire) should also
be flagged is a per-unit follow-up decision.

`sustained_damage_up` is already wired (gated to sustained-typed instances,
`raid_simulator.py:200`), and the Mana-precedent tick-DoT machinery
(`resource_scaled_nukes` with no `resource` key) is already present. The DoTs
must be tagged **damage_type "sustained"** so `sustained_damage_up` applies.

**DoT ticks read live buffs.** Each tick computes damage at its own tick time
against the currently-active Effects (same as a burst nuke). So the ATK +156.19%
buff and the Sustained Damage Up buffs — which are active during the same
`[burst, burst+D]` window (floor) or continuously (ceiling) — automatically
multiply the Collider and Meteor DoT ticks. This is the whole point of gating the
buff to the transformation window rather than modeling the DoT damage as fixed.

There is **no separate single-hit burst nuke** — her burst damage IS the Meteor
DoT — so the registry `burst_percent` for this unit is `None`.

### Branch-selection wiring (the one small engine touch)

Add `part_destructible: bool = False` to `BossProfile`, thread it through
`simulate_raid` into `SquadContext` (mirroring `boss_element`).

- **Buffs** are `SkillRule`s, so they gate with `condition=` — add a
  `boss_part_destructible()` condition (mirror of `boss_is_element`), and use it
  / `not_condition(...)` to select the floor vs ceiling buff variants.
- **DoTs** (`periodic_nukes` / `resource_scaled_nukes`) are separate spec maps,
  not `SkillRule`s, so they cannot carry a `condition`. Their floor/ceiling
  selection happens where `raid_simulator` assembles/processes this unit's DoT
  specs, reading `SquadContext.part_destructible`. The exact shape of that
  localized read is a plan-phase decision; the design commitment is only:
  *flag lives on SquadContext; buffs branch via condition, DoTs branch at the
  sim level.*

## Deferred / approximated (confirmed with Fienn 2026-07-16)

- **Part-destruction battery fill** — deferred; it is the reason for the
  floor/ceiling flag.
- **Skill 2 Full-Burst buff** "Wind Code allies with assault rifles: Sustained
  Damage +77.5% for 10 s" — **fully deferred**. It needs gap #3 (weapon-type +
  element narrow scope); approximating it as `element:Wind` would over-apply and
  risk overestimation, which Fienn wants to avoid. Encode accurately later when
  gap #3 lands.
- **Damage to Parts +20%** (skill 1, battle start) — deferred (situational
  part damage, not general raid DPS).
- **Battle-start battery = 0** — confirmed in-game (Fienn). Not an assumption:
  she is not transformed at battle start; the first transformation is at her
  first burst (floor branch).
- **Ceiling assumes transformed from battle start** (Fienn approved,
  2026-07-16). Strictly, even with a part-destruction gimmick the battery starts
  at 0 and needs a brief ramp-up to first reach 100%; the ceiling ignores that
  ramp and treats her as transformed for the whole fight. This is intentional:
  the ceiling is the theoretical maximum-potential upper bound, not an expected
  value, so the small early-game ramp is deliberately optimistic.

## Testing strategy

- **Floor branch:** first transformation at first burst; ATK +156.19% and the
  Collider DoT active only within `[burst, burst+10s]` windows; no transformation
  before the first burst.
- **Ceiling branch:** ATK +156.19% permanent; Collider DoT ticks whole fight.
- **Bracket:** ceiling total damage > floor total damage for the same roster/boss.
- **Sustained wiring:** a Sustained Damage Up buff actually moves the DoT
  damage (guards against the DoTs being mistagged as non-sustained).
- **Meteor DoT:** 10 ticks of 266.69% sustained damage from burst, both branches.
- **Boss flag:** flipping `part_destructible` switches floor↔ceiling behavior and
  changes total damage; leaving it default (`False`) reproduces the floor.
- Full suite stays green (no other unit reads `part_destructible`, default
  `False` is inert for everyone else).

## Reference — skill values (lootandwaifus, level 10)

- skill 1 *Transform!*: Damage to Parts +20% (deferred); part-destruction
  battery +50% cap 100% (deferred); at 100% → Transformation: battery −1%/0.2s,
  **ATK +156.19%**, deactivate at 0%; after 30 normals: Sustained Damage +59.6%
  for 5 s.
- skill 2 *Tremble!*: **Collider** 45.87% final ATK sustained damage every 1 s
  while transformed; FB → Wind AR allies Sustained Damage +77.5% for 10 s
  (deferred).
- skill 3 *Ultimate Attack!* (burst, cd 40): while transformed → battery +50%;
  while not → Emergency Charge (battery 100% → 50% after transforming);
  **Meteor** 266.69% final ATK sustained damage every 1 s for 10 s on the
  highest-max-HP enemy; self Sustained Damage +135.83% for 10 s.
