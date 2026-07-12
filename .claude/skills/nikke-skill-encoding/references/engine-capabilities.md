# Engine capability catalog

What the simulation engine can and cannot represent. Verify against the code
(`backend/app/`) if in doubt — this reflects the engine as of the 15-Nikke
encoding pass and will grow as the engine does.

## Effect model

An `Effect(stat, value, scope, duration, source_slug)` is registered at a time
and queried later. `value` is a fraction (e.g. 40% → 0.40). `duration` in
seconds, or `None` for permanent. A `Pulse(stat, value, scope, source_slug)` is
a one-shot instantaneous event, drained and consumed once (used for burst
cooldown reduction).

### Scopes
- `"self"` — only the Nikke that produced it (its `source_slug`).
- `"squad"` — everyone in the deck.
- `"element:<Name>"` — only Nikkes of that element (Fire/Water/Wind/Iron/Electric).
- `"slugs:a,b"` — exactly the listed slugs. Not written by hand — it's produced by
  `highest_atk_buff_rule` / `round_buff_rule` after `SquadContext.top_atk_slugs`
  ranks the deck by live final ATK, for "N allies with the highest final ATK".

There is **no positional scope** (front/back row, "allies on both sides") and
**no weapon-conditional scope** ("SR allies", "shotgun allies"). Approximate
weapon/positional offensive buffs as `squad` (documented), or defer. But
**"N allies with the highest final ATK" is precise now** — use the top-N helpers
(see the `round_buff_rule` / `highest_atk_buff_rule` entries below), not `squad`.

## Stats the engine CONSUMES (encoding these affects output)

Damage stats (fed into `calculate_damage`, so they change damage numbers):
| stat | meaning | game wording |
|---|---|---|
| `atk_percent` | ATK% buff on target's own ATK | "ATK ▲ X%" |
| `flat_atk` | additive flat ATK (usually caster-scaled) | "ATK ▲ X% of caster's ATK" |
| `other_elemental_bonus` | superior/advantageous code damage | "Superior Code / 우월코드 대미지 ▲" |
| `other_critical_damage_sources` | crit damage buff | "Critical Damage ▲ X%" |
| `crit_rate` | crit rate buff (base 15% is added by the sim) | "Critical Rate ▲ X%" |
| `charge_damage_bonus` | extra charge damage | "Charge Damage ▲ X%" |
| `attack_damage_up` | Attack Damage bucket | "Attack Damage ▲ X%" |
| `damage_to_parts_up` | damage to parts/interruption | "Damage to (Interruption) Parts ▲" |
| `pierce_damage_up` | pierce damage (modeled as general damage-up) | "Pierce Damage ▲ X%" |
| `damage_taken_up` | enemy damage-taken debuff — model as **squad** scope (all attackers share it) | "Damage Taken ▲ X%" (on enemy) |
| `other_core_damage_sources` | core-damage buff, **gated on `core_hittable`** (inert if boss has no core) | "Damage dealt when attacking core ▲ X%" |

Scheduling stats (change the burst rotation / shot timing, not per-hit damage):
| stat | mechanism | game wording |
|---|---|---|
| `burst_cooldown_reduction_sec` | **Pulse**, drained at full-burst-end; **scope-aware** (self reduces only the caster's cooldown, squad reduces everyone's) | "Cooldown of Burst Skill ▼ X sec" |
| `max_ammo_percent` | scales base magazine size (increases and decreases both apply to BASE, summed) | "Max Ammunition Capacity ▲/▼ X%" |
| `reload_speed_percent` | shortens reloads | "Reloading Speed ▲ X%" |

Burst nuke: not a stat — exposed via a `<name>_burst_percent(values)` helper and
put in the registry entry, applied as the attack coefficient of a burst hit.

`instant_damage_percent`: a **Pulse**, for "Deals X% of final ATK as damage"
tied to a trigger OTHER than the caster's own burst (e.g. "on Full Burst
enter", regardless of who bursts). Use `_helpers.instant_nuke_pulse_rule`;
`raid_simulator.drain_instant_damage` computes it after every trigger fire
using the pulse's source_slug as caster, exactly like a burst nuke, logged with
`source="instant_nuke"`.

`periodic_nukes`: not a stat or Pulse — a `simulate_raid` param
(`{slug: {"cooldown": seconds, "percent": float}}`) for a skill that fires
repeatedly on its OWN fixed cooldown, fully independent of the burst cycle
(e.g. Helm: Aquamarine's Aegis Cannon Suppression Fire, "Cooldown: 4s"). Ticks
at t=cooldown, 2*cooldown, ... up to `fight_duration`, logged with
`source="periodic"`. Expose per-Nikke via `<name>_periodic_percent(values)` +
register in `registry._PERIODIC_NUKE_BUILDERS` (see
`registry.get_periodic_nuke`).

## Damage typing (which Damage-Up buff applies to which instance)

Every damage instance has a `damage_type`; a type-specific Damage-Up bucket is
read from the registry ONLY for instances of that type, so e.g. a "Sustained
Damage +X%" buff boosts only sustained-typed damage, not every hit.
`raid_simulator._TYPE_BUCKETS` maps type → bucket(s):

| damage_type | type-gated bucket |
|---|---|
| `attack` (default) | (none) |
| `sustained` | `sustained_damage_up` |
| `distributed` | `distributed_damage_up` |
| `true` | `true_damage_up` |
| `projectile_explosion` | `projectile_explosion_damage_up` |

The always-on buckets (`attack_damage_up`, `pierce_damage_up`,
`damage_to_parts_up`, `damage_taken_up`) apply to EVERY instance regardless of
type. So encoding one of the type-gated buffs is now live **only if the deck
also produces an instance of that type** — the buff is a multiplier with nothing
to multiply otherwise.

How an instance gets a non-`attack` type:
- **Burst nuke:** add `slug → type` to `registry._BURST_DAMAGE_TYPES` (default
  `attack`); `roster` threads it as `burst_damage_types`. E.g. Rapi: Red Hood's
  Power of Inheritance (a Projectile Explosion skill) → `projectile_explosion`.
- **Periodic nuke:** add `"damage_type"` to the `periodic_nukes` entry dict.
- **Normal attacks:** a rocket launcher's (`weapon == "RL"`) normal attacks are
  `projectile_explosion` typed automatically. A skill can also convert a unit's
  normal attacks for a window by registering a self-scoped
  `Effect("normal_attacks_deal_true", 1.0, "self", <dur>, slug)` (the type is
  encoded in the stat name; the normal-attack pass reads it at each shot time) -
  e.g. Takina Inoue's burst "normal attacks deal true damage for 10 sec".
- **instant nukes** are always `attack` for now (no unit needs otherwise).

Semantics (confirmed against the nikke.gg glossary - see
`damage-formula-reference.md`): `true` damage **ignores enemy DEF** (a
`true`-typed instance is computed with `enemy_def=0`); `attack_damage_up` is a
general buff that **affects all damage**, so it stays global across every type.

`periodic_rules`: a `simulate_raid` param
(`{slug: [(cooldown, [SkillRule, ...]), ...]}`) for a Skill 1/2 that fires on
its OWN cooldown - **a universal battle rule: a cooldowned Skill 1/2 first fires
at t=cooldown (not battle start) and repeats every cooldown.** Unlike
`periodic_nukes` (a damage OUTPUT, computed in a post-pass), these rules apply
buffs/debuffs that are damage INPUTS, so they run as a pre-pass BEFORE the burst
cycle (which computes nukes that must reflect them). Fired against the initial
context, so periodic rules must be **stateless buff appliers** (no dependence on
burst-cycle state / activation_count / status). Build with
`buff_rule("periodic", [...])` ("periodic" is a label; these rules aren't in
`rules_by_slug`, so `fire_trigger` never dispatches them). Expose per-Nikke via
`registry._PERIODIC_RULE_BUILDERS` / `get_periodic_rules`; `roster` threads it.
See `takina_inoue.py` (Battlefield Control, cd 15s).

`per_shot_rules`: a `simulate_raid` param
(`{slug: [(threshold, mode, [SkillRule, ...]), ...]}`) for a skill that fires
after/every N of the unit's own shots - "after N normal attacks", "N full charge
attacks", "every N shots". `mode` is `"after"` (once, at the Nth shot) or
`"every"` (at each multiple of N). The engine counts the unit's generated shots
(a charge weapon's every shot is a full charge, so "full charge N" == "shot N";
the encoding knows the weapon and picks N - no weapon gating in the engine). A
firing rule either applies a buff or emits an `instant_damage_percent` pulse
(`instant_nuke_pulse_rule("per_shot", pct)`) recorded as `source="per_shot_nuke"`.
For a per-shot BUFF use `refreshing_buff_rule("per_shot", ...)`, NOT
`buff_rule` - a multi-second buff applied every shot must refresh (one active
value), not stack to the sum of overlaps (see the Helpers note on
`add_refreshing`). Rules must not change shot generation (reload/ammo). To gate
on a status that varies over time (alternating or pinned mid-fight), do it inside
the action using the shot time + `context.burst_times` / `status_since` - see
`mint.py::mint_singing_at`. Expose via `registry._PER_SHOT_RULE_BUILDERS`
/ `get_per_shot_rules`; `roster` threads it. See `brid_silent_track.py`
(Journey Ahead: 675% every 5 normal attacks). Not yet supported: "on firing the
last bullet" (needs magazine-boundary markers in `attack_rate`); per-shot nukes
default to `attack` damage type.

**"For N round(s)" buffs (bullet-count duration):** a buff whose duration is the
affected ally's next N normal-attack shots, not seconds — e.g. Zwei's Pierce
Equation, Miranda's Wake Up. Build with `round_buff_rule(trigger, [(stat, value,
scope_spec)], shots=N)`; it records a `RoundGrant` that `simulate_raid`'s shot
loop turns into a real timed Effect covering exactly the next N shots per affected
unit (squad grants are consumed per-ally). `scope_spec` is a static scope string
or `("top_atk", n)`. No engine param to thread — `RoundGrant`s live on the
registry. See `zwei.py` (squad) / `miranda.py` (top-1). Detail in
`special-mechanics.md` ("For N round(s) is a bullet-count duration").

**Highest-final-ATK top-N targeting:** for "N allies with the highest final ATK
(except caster; including caster if not enough allies)". `highest_atk_buff_rule(
trigger, n, [(stat, value, duration), ...])` applies timed buffs to the top-n;
`round_buff_rule(..., ("top_atk", n))` does the bullet-count variant. Both resolve
via `SquadContext.top_atk_slugs(n, caster, registry, time)`, which ranks by LIVE
final ATK at application time (so an earlier same-cycle ATK buff is reflected) and
emits a `slugs:` scope. `raid_simulator` injects each member's base ATK into the
context. See `miranda.py`.

**Named resource / capped stack counter (gap #2 Pattern A):** a quantity-based
resource (battery / ammo pouch / N-stack counter) driving count-scaled buffs.
Declare a `ResourceSpec(name, fill, cap, buffs)` (in `effects.py`); wire it via
`_RESOURCE_SPEC_BUILDERS` / `get_resource_specs` and `roster` threads it into
`simulate_raid`'s `resource_specs`. `fill` is deterministic:
`("per_shot_every", N)` = +1 stack every Nth of the owner's shots,
`("per_shot_every_core", core_n, noncore_n)` = core_n on a core-hittable boss
else noncore_n (Guillotine's "3 Core hits" vs "6 normals without the core"), or
`("periodic", interval)` = +1 stack every `interval` seconds regardless of shots
(Cinderella's Beautiful, which ticks while her decoy is up from battle start).
`buffs` are `ResourceBuff`s built with `linear_resource_buff(stat, per_stack,
scope, lifetime=None)` (value = per_stack × count) or `leveled_resource_buff(stat,
per_level, level_fn, scope, lifetime=None)` (value = per_level × level_fn(count),
for a Hero-Level-style tier); an arbitrary `value_fn` is allowed for a threshold
buff. `lifetime=None` = a permanent stack that accumulates (ramps then plateaus at
the cap); a number = a timed stack that expires that many seconds after each fill.
The count itself is a function of time — `SquadContext.resource_count(slug, name,
time, cap, lifetime)` — never a mutable total, so it's safe across the burst-cycle
vs shot-loop phase ordering. The resolution pass emits each buff as a STEP FUNCTION
of delta Effects over the fill/expiry events, so `total_for`'s running sum equals
value_fn(count) at every time. First consumers: `modernia.py` (timed capped),
`guillotine_winter_slayer.py` (permanent + leveled + core-conditional),
`cinderella.py` (periodic fill). Pattern B time-draining gauges / transforms (Ark
Ranger battery, blocked additionally on part-destruction fills) remain deferred.
See `special-mechanics.md`.

**Resource-scaled / gated burst nuke (incl. repeating DoT ticks):** a burst-fired
nuke whose magnitude is gated or scaled by a named resource's count - a single
additional hit (Julia's Climax gated on Crescendo at max stacks; Cinderella's
Glass Slippers additional hit scaled by Beautiful's count) or a repeating tick
(Guillotine's Extermination, 10 ticks/1s each independently reading Hero Level at
ITS OWN time). Declare spec dicts `{"resource", "cap", "base_percent", "scale_fn",
"tick_count", "tick_interval", "lifetime"(optional), "damage_type"(optional)}`;
wire via `_RESOURCE_SCALED_NUKE_BUILDERS` / `get_resource_scaled_nukes`, threaded
by `roster` into `simulate_raid`'s `resource_scaled_nukes` param. Fired from
`on_tier_fire` (own_burst_activate), which records `tick_count` damage events
(`tick_interval` apart) each carrying a `resource_gate`; **the percent is resolved
in PHASE 2**, not at record time - `_resolve_percent` calls
`context.resource_count(slug, name, event_time, cap, lifetime)` and multiplies by
`scale_fn(count)`, since the resource's fills aren't populated until the
resolution pass runs (after the burst cycle that records the event). Logged with
`source="resource_scaled_nuke"`.

**Multi-hit burst nuke:** a burst that "attacks sequentially N times" is N
SEPARATE damage instances at the same instant, not one instance at N×percent -
defense is a flat per-hit subtraction, so pre-multiplying overcounts whenever
`enemy_def > 0`. `burst_hit_counts={slug: N}` (default 1) wired via
`_BURST_HIT_COUNTS`/`get_burst_hit_count`; `on_tier_fire` records N identical
events. First consumers: Cinderella (10x), Julia-signature (5x).

**Record-then-compute:** `simulate_raid` RECORDS every damage instance
(burst/instant/periodic/per-shot nukes + normal attacks) as an event during
phase 1 (which only applies buffs), then computes them all in a phase-2 pass
against the final registry. So a buff applied late in the fight (e.g. a per-shot
squad debuff) correctly raises a burst nuke that fired earlier. Safe because
effects are added with `applied_at >= their time` and `truncate_open_ended`
mutates in place, so deferring computation never changes an existing value.

`EffectRegistry.truncate_open_ended(stat, source_slug, now)`: for a continuous
(`duration=None`) buff that a LATER trigger explicitly cancels (not a timer) -
e.g. Grave's Heat Emission ends when she reuses her burst. Add the effect
open-ended when it activates; call `truncate_open_ended` in the canceling
trigger's rule to close its duration to the elapsed time. Replay-safe (mutates
the stored Effect, so later queries at any time see the correct window).

## Stats the engine does NOT consume (encoding is inert — defer instead)

Two groups. In both, encoding an effect with these stats is silently inert —
tests can still pass (the effect registers and `total_for` returns it), but the
value never reaches `calculate_damage`, so it does NOT change simulated damage.

**Not a damage concept at all** — no consumer will ever exist without a bigger
model: `attack_speed` / Attack Speed, `hit_rate` / Hit Rate,
`burst_gauge_fill_speed_percent` (gauge charge time is a fixed sim input),
`charge_speed_percent`, `shield_amount`, and anything HP/heal/DEF/survivability.
Defer these; if a Nikke's contribution is mostly these, say so — a thin
encoding is honest.

Exception: `flat_max_hp` (a Max-HP buff scaled off the caster's Max HP, e.g.
Rouge's Game Master) is encoded but inert TODAY — Fienn wants Max-HP buffs in
place for future units whose DAMAGE scales off Max HP. So encode Max-HP buffs as
`flat_max_hp` (don't defer them), knowing they don't move damage until such a
consumer + the `total_for("flat_max_hp", ...)` wiring exist.

**Valid formula terms that raid_simulator just doesn't wire from the registry
yet** — a real gap, not a dead end: `shield_damage_up`, and the major-modifier
terms `full_burst_bonus` / `effective_range_bonus` / `final_atk_modifier`.
(`sustained_damage_up`, `distributed_damage_up`, `true_damage_up`, and
`projectile_explosion_damage_up` are NOW wired but **type-gated** — see "Damage
typing" above; they only move damage when the deck also produces an instance of
that type.)

These exist in `damage_formula.py` but are absent from `raid_simulator.py`'s
`total_for(...)` calls. Do NOT encode a Nikke's headline effect onto one of
these and pretend it works — verify against the "engine CONSUMES" list above
(and `grep registry.total_for raid_simulator.py`). If a Nikke needs one, wiring
is ~one line per `calculate_damage` call site (mirroring how `pierce_damage_up`
/ `damage_to_parts_up` / `damage_taken_up` are wired). Raise it as a small
engine-extension decision rather than making it silently mid-encoding.

## Triggers (when a SkillRule fires)

| trigger | fires when |
|---|---|
| `battle_start` | once at t=0 (permanent passives, at-start-of-battle skills) |
| `own_burst_activate` | when THIS Nikke's burst tier fires (its burst skill) |
| `ally_burst_activate` | when ANY unit's burst tier fires — for a skill that reacts to another unit bursting (e.g. Prika's Encore on Mint's Sing Along). Fired across all units' rules after the burster's own `own_burst_activate`; gate with `ally_bursted("<slug>")`, which reads `context.last_burst_slug`. Buff appliers only (no instant nukes), like `periodic_rules`. |
| `full_burst_enter` | when tier-3 fires and Full Burst begins |
| `full_burst_end` | when the 10s Full Burst window ends |

There is **no** trigger for: normal-attack counts ("after N normal attacks"),
full-charge-shot counts ("full charge N times"), ally-ammo-expended counters,
on-kill, HP thresholds, or "when Raptures appear". Effects gated on these must
be deferred — or, if central, raise extending the engine with a new trigger.

SkillRule actions also have **no access to the boss's element** (only
`raid_simulator` does, via `boss_element`) - an effect gated on "if the enemy
is [element] Code" (e.g. a Wind-Code-only debuff) can't be conditioned
correctly and must be deferred, not applied unconditionally.
For an always-on-in-raid condition like "when Raptures appear" you may treat it
as active (document the assumption) since a raid always has enemies.

## Conditional / branching skills

For skills that branch on squad composition or a per-Nikke status flag, use
`squad_engine`:
- `no_other_burst_tier_allies(tier)` — true if the caster is the only one of
  its burst tier (e.g. Anis: Star / Rapi: Red Hood "if no other Burst 1 ally").
- `has_status(flag)` / `not_condition(cond)` — gate on a status the skill sets
  via `context.set_status/clear_status` (e.g. "My Own Star", "Combat Assist").
- `deck_contains(slug)` — another named Nikke is in the deck (static synergy).
- `ally_bursted(slug)` — for an `ally_burst_activate` rule: the unit that just
  bursted is `slug` (cross-unit reactive trigger, e.g. Prika↔Mint).
- `all_conditions(*conds)` — logical AND of conditions (e.g. Prika's Encore needs
  `ally_bursted("mint")` AND her own Performance `has_status`).
- `context.burst_used_this_cycle` — which slugs have burst this cycle (Crown's
  "allies who previously cast their Burst Skill").

See `rapi_red_hood.py` and `anis_star.py` for worked branching examples, and
`crown.py` for a per-member `burst_used_this_cycle` branch.

## Helpers

`app/skill_rules/_helpers.py`:
- `buff_rule(trigger, buffs)` where `buffs` is a list of
  `(stat, value, scope, duration)` tuples.
- `refreshing_buff_rule(trigger, buffs)` - same, but each buff REFRESHES rather
  than stacks (`registry.add_refreshing`): a re-application from the same source
  truncates the prior same-(stat,scope) instance so overlapping windows collapse
  to one value. Use for per-shot buffs re-applied every shot; different sources
  still sum.
- `cdr_pulse_rule(trigger, seconds, scope="squad")`.
- `highest_atk_buff_rule(trigger, n, buffs)` where `buffs` is `(stat, value,
  duration)` - timed buffs on the n highest-final-ATK allies (except caster).
- `round_buff_rule(trigger, buffs, shots=1)` where `buffs` is `(stat, value,
  scope_spec)` - a "for N round(s)" bullet-count buff; `scope_spec` is a static
  scope string or `("top_atk", n)`.
- `escalating_buff_rule(trigger, tiers)` / `instant_nuke_pulse_rule(trigger, pct)`
  (see their own sections above).

Use these instead of hand-writing action closures unless the skill needs
branching/status logic (then write an explicit `SkillRule` like the branching
examples).
