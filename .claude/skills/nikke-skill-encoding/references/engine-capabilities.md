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

There is **no positional scope** (front/back row, "allies on both sides") —
approximate positional offensive buffs as `squad` (documented), or defer.

**Weapon- and element-conditional targeting IS precise** ("shotgun allies",
"all Wind Code allies with assault rifles", "Water and Iron Code allies with
shotguns"): use `member_subset_buff_rule` with a `member_filter` reading
`SquadMember.weapon` / `.element`. It resolves to a live `slugs:` scope at
trigger time, so do NOT approximate these as `squad`. Consumers: `tove.py`,
`sugar.py`, `sugar_signature.py`.

**"N allies with the highest final ATK" is precise too** — use the top-N helpers
(see the `round_buff_rule` / `highest_atk_buff_rule` entries below), not `squad`.

## Stats the engine CONSUMES (encoding these affects output)

Damage stats (fed into `calculate_damage`, so they change damage numbers):
| stat | meaning | game wording |
|---|---|---|
| `atk_percent` | ATK% buff on target's own ATK | "ATK ▲ X%" |
| `flat_atk` | additive flat ATK (usually caster-scaled) | "ATK ▲ X% of caster's ATK" |
| `other_elemental_bonus` | superior/advantageous code damage — **advantage-gated**: only pays out when the wielder ALREADY holds elemental advantage over the boss (`damage_formula`'s element bonus group adds it to `element_multiplier` only if `element_multiplier > 1.0`) | "Elemental Advantage Attack Damage ▲ N%" (conditional buff — the overwhelming majority of this phrasing) |
| `element_advantage_grant` | grants the wielder elemental advantage it does NOT naturally have (`raid_simulator.element_bonus_for` returns `1 + ELEMENT_ADVANTAGE_BONUS` instead of the natural multiplier when set — it does not add to `other_elemental_bonus`, so it can't double up with natural advantage, and it does not change the unit's element identity for `element:<Name>`-scoped buffs) | "Applies Elemental Advantage damage to `<X>` Code enemies" (advantage-granting skill — rare; see `rapi_red_hood.py` for the only current consumer) |
| `other_critical_damage_sources` | crit damage buff | "Critical Damage ▲ X%" |
| `crit_rate` | crit rate buff (base 15% is added by the sim) | "Critical Rate ▲ X%" |
| `normal_attack_crit_rate` | crit rate that reaches ONLY the holder's normal attacks (2026-08-07). Added to `crit_rate` before the 1.0 cap, so the cap sits on the sum | "Critical Rate **of normal attack(s)** ▲ X%", "**Normal Attack** Critical Rate ▲ X%" |
| `charge_damage_bonus` | extra charge damage | "Charge Damage ▲ X%" |
| `attack_damage_up` | Attack Damage bucket | "Attack Damage ▲ X%" |
| `pierce_damage_up` | pierce damage — **gated on the wielder holding the Pierce PROPERTY** (`has_pierce`), so a Pierce Damage buff on a unit that never gains Pierce pays nothing | "Pierce Damage ▲ X%" |
| `damage_taken_up` | enemy damage-taken debuff — model as **squad** scope (all attackers share it) | "Damage Taken ▲ X%" (on enemy) |
| `other_core_damage_sources` | core-damage buff, **gated on `core_hittable`** (inert if boss has no core) | "Damage dealt when attacking core ▲ X%" |
| `has_pierce` | the Pierce PROPERTY itself, as a 0/1 self-scoped Effect (2026-07-26) — it gates `pierce_damage_up`, and on a `pierce_hits_body_behind_core` boss it makes one normal attack produce a second instance on the body behind the core | "Gain(s) Pierce", "Additional Effect: Pierce" |

**Read the crit bullet's own wording before reaching for `crit_rate`.** A skill
that says "Critical Rate **of normal attack**" is a different bucket from a bare
"Critical Rate", and the two appear side by side in one skill (Julia signature's
Decrescendo grants both). Folding the narrow one into `crit_rate` credits every
burst nuke in its scope - Helm's squad-wide grant did exactly that. Note the
scope is the RECIPIENT's normal attacks, so a squad-scope grant still pays only
each ally's own shots, never their skills. Consumers: `helm`, `julia_signature`.

**Encode "Gains Pierce" — it is not a no-op.** The property has its own stat, so
a bullet that grants Pierce for a window is credited for exactly that window and
nothing outside it. Match the duration to the text: continuous → `None`, "for N
sec" → the number, one charged shot → `round_buff_rule(..., shots=1)`, gated on a
status → the same duration that status holds. Consumers: `red_hood`, `ade_agent_
bunny`, `prika`, `milk_blooming_bunny` (continuous), `laplace*`, `grave` (timed),
`snow_white`, `maxwell`, `zwei`, `d_killer_wife` (per-round).

`core_hittable` isn't only an automatic gate on the stat above - it's also exposed
on `SquadContext` (plan-2 weapon-transform batch, 2026-07-19) via the
`boss_core_hittable()` condition helper (`squad_engine.py`, same shape as
`boss_part_destructible()`/`boss_is_element()`), so a SkillRule can gate an
entire bullet on "enemies with an activated core" directly - e.g. Cinderella:
Crystal Wave (MG mode)'s 833.79% core-strike Full Burst nuke, which the skill
text scopes to "enemies with activated cores" and this engine's uniform
per-instance core correction has no per-enemy distinction for, so gating the
whole nuke is the established convention.

Scheduling stats (change the burst rotation / shot timing, not per-hit damage):
| stat | mechanism | game wording |
|---|---|---|
| `burst_cooldown_reduction_sec` | **Pulse**, drained at full-burst-end; **scope-aware** (self reduces only the caster's cooldown, squad reduces everyone's) | "Cooldown of Burst Skill ▼ X sec" |
| `max_ammo_percent` | scales base magazine size (increases and decreases both apply to BASE, summed) | "Max Ammunition Capacity ▲/▼ X%" |
| `max_ammo_rounds` | adds whole ROUNDS to the magazine, on top of the percent: `round(base × (1+pct) + rounds)`. State the round count as-is - `raid_simulator` converts it against each recipient's own base magazine, so a squad-scope grant correctly means +67% to an SG and +2% to an MG | "Max Ammunition Capacity ▲ N round(s)" (no `%`) |
| `reload_speed_percent` | shortens reloads | "Reloading Speed ▲ X%" |

**Mid-magazine ammo refund — NOT a stat, and NOT a Max Ammo percentage.**
`attack_rate.AmmoRefund(every_shots=N, rounds=R)` hands `R` rounds back into the
magazine every `N` of the unit's own shots. The shot counter is CUMULATIVE over
the fight (not per magazine) and the refund is CAPPED at the magazine's capacity
(Fienn, in game, 2026-07-31). Use it for "Activates when landing N normal
attack(s) ... Reloads R round(s)": what a refund is worth depends on where in
the magazine it lands, and it shifts every later reload against the Full Burst
window, so approximating it as `max_ammo_percent` scores non-monotonically.
`R` must be `< N` or the magazine never empties (the dataclass rejects it), and
a unit can hold SEVERAL sources at once — its own skill plus the Tactical Bear
cube — which are vetted together in `_refund_sequence`.

Expose it as `<name>_ammo_refund(values)` and register in
`registry._SKILL_AMMO_REFUNDS` as `slug: (builder, required_boss_element or
None)`; the roster carries it as `skill_ammo_refund` and `raid_simulator.
resolve_ammo_refunds` applies the encounter gate, since the roster assembles a
deck and only the simulator knows the boss. Consumers: `eve` (Eagle Eye, gated
Electric), `ludmilla_winter_owner` (The Queen's Gaze, ungated).

What it CANNOT express: a refund that is a PERCENT of the magazine (Noir, Tove,
Little Mermaid, Asuka), one granted to allies rather than the owner, and one
whose trigger is anything but the owner's own shot count (a burst, a status
window, a level-up). Those stay deferred.

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
| `projectile_attachment` | `projectile_attachment_damage_up` |

The always-on buckets (`attack_damage_up`, `pierce_damage_up`,
`damage_taken_up`) apply to EVERY instance regardless of type. So encoding one
of the type-gated buffs is now live **only if the deck also produces an instance
of that type** — the buff is a multiplier with nothing to multiply otherwise.

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
attacks", "every N shots" - or on the shot that empties its magazine ("on
firing the last bullet"). `mode` is `"after"` (once, at the Nth shot),
`"every"` (at each multiple of N), `"last_bullet"` (`threshold` unused/
`None` - fires whenever the current shot's time is in that unit's
`last_bullet_shot_times(...)`, computed once per unit only if a `"last_bullet"`
entry is present), `"first_bullet"` (its mirror: the round that OPENS each
magazine, incl. t=0 - gap #9, Jill's Magnum), `"every_during_full_burst"`
(threshold=N, counts only shots inside a Full Burst window - gap #7, Soda/
Velvet), `"every_outside_full_burst"` (its complement: only shots outside
every FB window - Velvet's Sticky Fingers), `"every_during_own_status_window"`
(threshold=`(N, window_duration)`, window anchored at the CASTER'S OWN burst
times - gap #7, Asuka/Grave), `"sequence"` (gap #10, Scarlet: Black
Shadow: `threshold` is `{"requirements": [3, 6, 9], "own_burst_window":
(duration, [1, 2, 3])}` and the rules slot holds ONE RULE LIST PER STAGE -
a single running counter fires stage k once count >= the ACTIVE requirement
for it, resets after the last stage, and swaps the requirement table inside
the caster's own-burst window with count/stage carrying over across the
boundary; at most one stage fires per shot), or `"every_during_segment"`/
`"every_outside_segment"` (threshold=N, plan-2 weapon-transform batch,
2026-07-19: counts only shots whose `ShotRecord.in_segment` is True/False -
for a unit whose per-shot rule must fire differently inside vs. outside its
own `weapon_mode_schedules` segment, e.g. Snow White: Heavy Arms's boosted
Auto Fire during Fully Active vs. its plain form otherwise. Matched by
record IDENTITY, not shot TIME - a segment's last shot (`until_shots`
exhausted) and the resumed base weapon's first shot can share the exact same
timestamp (v1's "resume with a fresh magazine immediately" semantic), so a
time-based filter would let both modes fire on that one boundary shot;
identity matching makes the two modes structurally mutually exclusive). The
count runs across ALL segments merged, not reset per segment - a threshold
>1 carries its count from one transform window into the next (inert today:
the only consumer, Snow White: Heavy Arms, uses N=1). The
engine counts the unit's generated shots (a charge
weapon's every shot is a full charge, so "full charge N" == "shot N"; the
encoding knows the weapon and picks N - no weapon gating in the engine). A
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
(Journey Ahead: 675% every 5 normal attacks). Per-shot/instant nukes default
to `attack` damage type; when the text names one (e.g. "as Distributed
Damage"), pass `instant_nuke_pulse_rule(..., damage_type="distributed")` -
the Pulse carries it to record() so the type-gated Damage-Up buckets apply
(2026-07-18, first consumer Scarlet: Black Shadow).

**"Last bullet fired" (magazine-boundary marker) - BUILT capability
(2026-07-12):** `attack_rate.py`'s `magazine_last_bullet_times`/
`charge_last_bullet_times`/`last_bullet_shot_times` mirror
`generate_{magazine,charge}_shot_times`/`generate_shot_times`'s exact 3-tier
structure (low-level raw-rate functions + a weapon-dispatching wrapper),
marking which shot in each magazine actually empties it
(`magazine_size - 1`, re-derived live from `max_ammo_percent_at` - so a
user's [Max Ammo Up] overload option or a temporary ammo-boosting skill
buff correctly shifts which round is "last", same mechanism shot generation
itself already used). A shot that only LOOKS like the last one because
`fight_duration` cut the fight off mid-magazine is correctly NOT marked
(only a round that reaches the true magazine boundary counts). Attack/charge
speed need no new modeling here - they're not wired as shot-interval
modifiers anywhere in this engine (see "Stats the engine does NOT consume"
below), and even if they were, they'd change shot CADENCE, not magazine
CAPACITY, so they wouldn't move which round empties the magazine. Consume
via `per_shot_rules`' `"last_bullet"` mode (above) for a direct buff/nuke, or
`ResourceSpec`'s `("on_last_bullet",)` fill kind for a stack that accumulates
per last bullet (e.g. Julia's Crescendo). First real consumers (2026-07-12):
Julia (base)'s Crescendo/Climax, Helm's Frontline Command, Privaty's LD
Assault.

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
else noncore_n (Guillotine's "3 Core hits" vs "6 normals without the core"),
`("periodic", interval)` = +1 stack every `interval` seconds regardless of shots
(Cinderella's Beautiful, which ticks while her decoy is up from battle start),
`("per_shot_every_during_full_burst", N)` = like `per_shot_every` but only
counting the owner's shots whose time falls within a Full Burst window (Soda's
"every 3 normal attacks during Full Burst" - shots outside Full Burst don't
count at all, computed from `simulate_burst_cycle`'s own event log rather than
re-deriving burst timing), `("per_shot_every_during_own_status_window", N,
window_duration)` = the same idea but the window is anchored to the OWNER'S
OWN burst-fire times (`context.burst_times`) instead of the squad's global
Full Burst window - for a self-status whose window starts at the owner's own
burst and has a different length/offset than Full Burst (Asuka's Anti A.T.
Field, "every 10 shots while in Annihilation State" - a 9s window that starts
at HER burst, not the squad's Full Burst start), `("on_last_bullet",)` = +1
stack every time the owner's OWN shot empties its magazine (Julia's
Crescendo, "Activates when the last bullet hits the target" - see
`attack_rate.last_bullet_shot_times`, not any fixed shot count or window),
or `("squad_burst_cycle_conditional", [(event_pred,
gate_fn, delta), ...])` = a stateful walk over the GLOBAL burst-cycle event log
(not the owner's own shots), applying `delta` at each event where `event_pred`
matches AND `gate_fn(current_count)` is true (Maiden's MP: "+1 if MP==0 on any
squad member's Burst Stage 1", "+1 if MP>=1 on Full Burst enter" - see
`_resolve_squad_burst_cycle_resource` below). `buffs` are `ResourceBuff`s built with `linear_resource_buff(stat, per_stack,
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

**Resource resets (value REPLACED, not incremented):** for a resource that gets
set or spent rather than only ever accumulating - e.g. Soda's Golden Chip,
starting the fight at its 50 cap and spending 17 at each of her bursts.
`ResourceSpec` takes an optional `resets` field: `[{"trigger":
"battle_start"|"own_burst"|"own_burst_delayed", "value": X, "delay": seconds
(own_burst_delayed only)}, ...]`.

**A spend uses `value_fn(pre_value)` in place of `value`** - for a consumption
that reads the count it is spending, rather than landing on a fixed number.
Elegg's ghosts spend 9 at the 13 cap and 6 below it, floored at 1; Soda's burst
spends 17, floored at 1. Reach for this whenever the skill text says
`stacks ▼ N`: **`▼` is a SUBTRACTION marker throughout this data** (Isabel
`Full Burst Time ▼ 5 sec`, Arcana `▼ 6 sec`), so `▼ 17` means "spend 17", NOT
"set to 17" - reading it as a set parks the unit in a steady state instead of
draining her, and the two readings agree on the FIRST activation, so a test
that only checks one fire will not tell them apart. The floor is usually not in
the text at all and has to be measured in game (Soda's is 1: bursting at 16
stacks leaves 1).

`"own_burst_delayed"` resets `delay` seconds AFTER each own-burst fire
instead of at the burst itself - e.g. Asuka's Anti A.T. Field, cleared when
Annihilation State ends (9s later), not when the burst that started it fires;
pair with `dynamic_hit_count_nukes`' matching `fire_delay` (below) so the nuke
reads the resource at the SAME delayed instant it resets.
`SquadContext.reset_resource(slug, name, time, pre_value, post_value)`
records the reset; `resource_count(slug, name, time, ...)` uses the LATEST reset
at or before the query time as its baseline, discarding fills recorded before
it. `resource_count_before_reset(slug, name, time)` exposes the value the
resource held immediately BEFORE a reset recorded at an exact instant - needed
for a rule gated on "how much had built up right before it was spent" (not the
post-reset value). The resolution pass merges the flat additive fill schedule
with reset events (sorted by time, using `context.burst_times[slug]` for
`"own_burst"` resets) and replays them chronologically, so each reset's
pre-value correctly reflects prior fills AND any earlier reset already applied.
Verified to produce identical output to the pre-existing behavior when no
`resets` are present (a regression risk since it touches the shared resolution
pass every resource-using Nikke relies on). Consumers: `soda_twinkling_bunny.py`
(set at battle start + `value_fn` spend at her burst), `elegg_boom_and_shock.py`
(`value_fn` spend), `asuka_shikinami_langley_wille.py` (delayed clear),
`arcana_fortune_mate.py` (`full_burst_end` clear).

**`resource_gated_buffs` (the buff-side analog of resource-scaled nukes):** a
burst-fired BUFF gated on (or scaled by) a resource's count AT THE BURST'S OWN
TIME. Unlike a nuke (which defers its percent computation to phase 2 via
`resource_gate`, below), a buff has no equivalent deferred-computation stage -
so `resource_gated_buffs` specs (`{"resource", "cap", "use_pre_reset", "gate_fn",
"stat", "value", "scope", "duration"}`) are processed IN the resolution pass
itself (not at `on_tier_fire`, when the burst actually fires), iterating
`context.burst_times[slug]` for each of the owner's own burst times and adding
the Effect directly once `gate_fn(count)` passes - using `resource_count_before_reset`
when `use_pre_reset` is set. Wired via `raid_simulator`'s `resource_gated_buffs`
param, exposed per-Nikke via `_RESOURCE_GATED_BUFF_BUILDERS` /
`get_resource_gated_buffs`. First consumer: Soda's ATK +65.25%/15s (gated on
Golden Chip's pre-reset count >= 30).

**Per-cycle Full Burst length.** Two shapes, and picking the wrong one is the
whole difficulty:

1. **Fixed per slug** — `FULL_BURST_DURATION_DELTA` (`skill_rules/registry.py`)
   maps a slug to seconds. `burst_cycle` reads it off the unit that OPENED the
   cycle (`tier3_member`), so it applies only to cycles that unit's own Burst 3
   started. Isabel's `Full Burst Time ▼ 5 sec` and Modernia's `▲ 5 sec`.
2. **Conditional on a resource** — `_CONDITIONAL_FULL_BURST_DELTA_BUILDERS`
   (same file, `get_conditional_full_burst_delta`) returns
   `{"resource", "cap", "tiers": [(threshold, seconds), ...]}`; wired through
   `roster.py` into `simulate_raid`'s `conditional_full_burst_deltas`. Use this
   when the extension is `Activates when entering Burst Stage 3 / Affects all
   allies`, i.e. the holder does NOT have to be the unit that opened the cycle -
   shape 1 would silently drop every cycle a same-tier ally takes the seat.
   Thresholds are `>=` and the seconds are CUMULATIVE (build the total into the
   tier so the consumer never re-adds). Stage 0 means "no extension" and must be
   absent from the resolved table, not present as a zero. First consumer: Soda's
   Beginner's Rewards (chip 10+ -> +2s, 20+ -> +5s total).

**Shape 2 needs a fixed point, and `simulate_raid` runs one for you.** The
window length is decided by the resource at the cycle's Burst 3, the resource is
filled by shots, and the shots exist only once the window is known. That reads
circular but is not: in TIME the dependency is one-way (cycle k's threshold sees
only shots up to k-1). It only looks circular because this engine schedules the
whole fight before simulating it. So `simulate_raid` is a wrapper that calls
`_simulate_raid_once` from the no-extension lower bound and feeds each pass's
resolved stage table back in as `full_burst_stage_overrides` until a pass
reproduces its own input. Results carry
`full_burst_passes = {"passes": N, "converged": bool}`.

Two properties to preserve if you add a second consumer. **A deck with no such
unit resolves in exactly one pass** - the resolver returns an empty dict and the
loop exits, so cost and output are unchanged for everyone else; that invariant is
what makes the feature free, and it is worth a test of its own. And **the pass
count tracks FIGHT DURATION, not deck composition**, because each pass propagates
the change one cycle further: a draining alternating deck needs 3 passes at 200s
and 8 at 700s. `MAX_FULL_BURST_PASSES` is therefore a runaway guard, not a
quality knob - size it far above any plausible fight, never at "twice the worst
deck I measured", since `fight_duration` is a user-entered form field.

**`dynamic_hit_count_nukes` (hit count itself is a resource's value):** a
burst-fired nuke whose HIT COUNT - not just its percent - is a named resource's
value at burst time, e.g. Maiden's Diamond Dust ("attacks repeatedly based on
current MP"). Reads the PRE-reset count via `resource_count_before_reset` for
each of the owner's own bursts, recording that many identical damage events
(each independently defense-subtracted, same reasoning as `burst_hit_counts`).
Spec dict: `{"resource", "base_percent", "extra_flat_atk_percent_of_max_hp"
(optional), "damage_type" (optional), "fire_delay" (optional, seconds),
"full_burst_bonus_eligible" (optional, bool)}`; wired via `raid_simulator`'s
`dynamic_hit_count_nukes` param, exposed per-Nikke via
`_DYNAMIC_HIT_COUNT_NUKE_BUILDERS` / `get_dynamic_hit_count_nukes`. Logged with
`source="dynamic_hit_count_nuke"`. `fire_delay` (default 0) makes the nuke fire
- and read/reset its resource - at `burst_time + fire_delay` instead of exactly
`burst_time`, for an effect that lands when a fixed-duration self-status ends
rather than at cast time (Asuka's Annihilation, 6.62%, fires 9s after burst;
pair with a matching `"own_burst_delayed"` reset, above, using the SAME delay
value so the reset and the nuke's `resource_count_before_reset` lookup land at
the identical instant). First consumers: `maiden_ice_rose.py` (no delay),
`asuka_shikinami_langley_wille.py` (9s delay).

**`extra_flat_atk` (nuke-scoped flat-ATK bonus):** `record()`/`_damage_instance`
gained an `extra_flat_atk` parameter (mirroring the existing `extra_charge_bonus`
parameter's precedent exactly), so a specific nuke can fold a percent-of-caster-
Max-HP (or similar) bonus into ONLY that nuke's own flat_atk term - e.g. Maiden's
Diamond Dust, "1372.8% of the sum of 10% of final Max HP and ATK" - without
leaking into normal attacks or any other damage instance from the same slug. A
plain registry `Effect("flat_atk", ...)` would leak everywhere, since flat_atk
is read unconditionally by every damage instance for that slug.

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
`source="resource_scaled_nuke"`. **`"resource"` is optional** - omit it (along
with `cap`/`scale_fn`/`lifetime`) for a PLAIN repeating DoT with no resource
scaling at all (`resource_gate=None`, every tick at the flat `base_percent`);
this reuses the same tick_count/tick_interval loop instead of requiring a fake
resource just to get repeating ticks. First consumer: Mana's Fatal Error!
(396%/sec flat Sustained-typed DoT, 10 ticks).

**Self-scheduled nuke (summoned entities):** damage on a cadence the UNIT
computes, for when `periodic_nukes`' fixed interval can't express it - a summoned
entity whose attack rate depends on how many of it are alive (Ein's Near
Feathers: 6 max, per-feather lifetimes, her burst re-summons all six and resets
their cooldowns, and each attacks every `8 * (1 - 0.16*(alive-1))` sec). The
schedule is still deterministic - summons come from battle start plus the
owner's burst times - so the unit module precomputes the time list and the
engine only emits it, keeping summon bookkeeping out of the simulator. Declare
spec dicts `{"schedule": fn(context, fight_duration) -> times, "percent",
"damage_type"(optional), "full_burst_bonus_eligible"(optional),
"core_eligible"(optional)}`; wire via
`_SCHEDULED_NUKE_BUILDERS` / `get_scheduled_nukes`, threaded by `roster` into
`simulate_raid`'s `scheduled_nukes` param. Times at or past `fight_duration` are
dropped. Logged with `source="scheduled"`. **`core_eligible: True` opts one
scheduled instance into the Core Damage bonus**, against the general rule that
only `source == "normal_attack"` collects it. Reach for it when the ticks are a
SUMMON shooting rather than an effect ticking - a star or drone that aims and
fires is a normal attack, just not its owner's, and the game lands it on the
core. Anis: Star's Shooting Stars are the first consumer, settled by measuring
one tick against one of her own shots in the same instant: the ratio came out as
the bare coefficient ratio (0.0018%), meaning every modifier cancelled, so the
tick sits in her normal attack's exact state - core AND its damage-type bucket
(hers are `projectile_explosion`). Do NOT extend this to the same unit's other
skill damage by association: her Starfall rider, measured the same day by a
crit/non-crit pair, reads a major bucket of exactly 1.0 / 1.5 - no core.
The schedule may also read the owner's
own firing timeline off `context.shot_times[slug]` (filled by the weapon pass;
empty without weapon stats) - that is how "a DoT per Full Charge" is expressed
(Raven's Shock Wave). `context.shot_times` holds EVERY squad member's timeline,
not just the owner's, so a SQUAD-WIDE bullet/ammo counter is also expressible by
merging all members' shot times in the schedule (Little Mermaid's Bubble
Barrage, "allies' total ammo expended reaches 500" - no engine extension
needed). It also anchors on `context.burst_times[slug]` for own-burst-window
schedules (Red Hood's measured 33-shot transform window), or on
`context.full_burst_windows` (a `[start, end)` list, filled by `raid_simulator`
right before the weapon pass - plan-2 weapon-transform batch, 2026-07-19) for a
schedule that needs "the next Full Burst entry AFTER some other event," not a
fixed window relative to the unit's own burst - e.g. Rapi: Red Hood's
Attachable Projectiles: each attaching shot's damage lands immediately, but
its EXPLOSION lands at the next Full Burst entry that follows it (found by
scanning `full_burst_windows` for the first start time past the attach time),
which could be one cycle or several away depending on when the attachment
happened. A schedule can also emit the SAME time more than once -
that is how a stacking DoT is expressed: one damage instance per live stack, so
defense comes off each, exactly like a multi-hit burst. First consumer: Ein
(`ein.py` - see
its docstring for how a datamine + a video measurement, NOT the skill text,
settled the mechanics; the text's "Activates when Near Feather is summoned"
misreads as one hit per summon). Reach for this only when the cadence genuinely
varies - a fixed interval is still `periodic_nukes`.

**Weapon-mode segments (v1, 2026-07-19):** for a skill that swaps the unit's
ENTIRE weapon profile for a window - a burst-triggered cannon transform
(Snow White, Maxwell), a sustained buffed-cadence window (Laplace's Hero
Vision, via the dual slug `laplace-signature`), or a migrated
`scheduled_nukes` approximation (Red Hood's Step 3, see below).
`attack_rate.generate_segmented_shots()` builds a per-segment ShotRecord
timeline instead of one flat cadence: inside a segment the unit's BASE
weapon is genuinely silenced (not just double-counted-and-subtracted) and
shots come from the segment's own `profile` dict (same shape as a
`weapon_stats` entry - `weapon`, `damage_percent`, `charge_damage_percent`,
`max_ammo`, `reload_time`, `charge_time`, or an explicit `rate_of_fire` for
a profile with no real charge/magazine model); when the segment ends (its
`until_shots` count is reached or its `end` time passes) the base weapon
resumes with a FRESH magazine immediately (no reload wait). A `charge_time`
profile inside a segment still reads live `charge_speed_percent_at` etc., so
a deck's charge speed / charge damage / ATK buffers actually multiply the
transform's shots - an explicit `rate_of_fire` profile is a MEASUREMENT
ANCHOR instead (its shot count already bakes in Fienn's real-game-measured
cadence), so it takes NO cadence buffs, by contract. A profile may also
carry its own optional `damage_type`. Wire via `simulate_raid(...,
weapon_mode_schedules={slug: schedule_fn})` where `schedule_fn(context,
fight_duration)` returns a list of `{"start", "until_shots" or "end",
"profile"}` dicts (same signature family as `scheduled_nukes` - the module
computes window anchors, e.g. `context.burst_times`, the engine only
emits). **Every unit's weapon pass now runs through
`generate_segmented_shots` regardless of whether it has any segments** - an
empty schedule reproduces the pre-existing flat-cadence generator's output
bit-for-bit (verified by an SR_ODD 1.19s-charge equivalence test), so this
was a safe, non-opt-in unification rather than a per-unit switch.
First/last-bullet markers for a segmented unit now come directly off the
record's flags instead of a separate marker recomputation. Registry map
`_WEAPON_MODE_SCHEDULE_BUILDERS` / `get_weapon_mode_schedules`; `roster`
threads it. First consumers: `snow_white.py`/`maxwell.py` (burst
`until_shots: 1` single-cannon-shot windows), `laplace_signature.py` (a
fixed 10s window, First hit + 93 `rate_of_fire`-profile ticks),
`red_hood.py` (migrated off a `scheduled_nukes` approximation that could
not let deck buffs touch the transform - see its docstring for the
before/after). A segment profile that needs to fold in the caster's OWN
base weapon stats (rather than an independent transform weapon) reads them
from `caster_weapon_stats` (plan-2 batch, 2026-07-19: `roster.py`'s skill-
value assembly injects the unit's assembled `weapon_stats` dict alongside
the existing `caster_atk`/`caster_def`/`caster_max_hp` keys) -
`snow_white_heavy_arms.py`'s Fully Active segment reads its own
`charge_damage_percent` this way and adds the Fully Active bonus on top, so
the segment is "my own charge shot, buffed" rather than a separate cannon.
See `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`.

**Not every weapon-transform kit needs the segment primitive itself - three
plan-2 consumers resolved without touching it (2026-07-19):**
`cinderella-crystal-wave`'s MG/Snipe choice is a pre-battle, held-for-the-
whole-fight mode pick, not a short burst/status window - modeled as two
static-profile dual slugs instead (see "Multiple deck candidates from one
owned character" below). `rapi-red-hood`'s 120-normal-attack projectile
launcher never swaps her weapon profile at all - it needed
`SquadContext.full_burst_windows` exposure (above) for its `scheduled_nukes`
schedule, not a segment. `snow-white-heavy-arms`'s charge-lock-on loop
looked like it might need a new state machine but didn't - see the
`every_during_segment`/`every_outside_segment` per-shot modes above; it DOES
consume one segment (Fully Active, `until_shots: 2`) for the burst window
itself, just not for the charge-loop mechanic that made it look harder.

## Multiple deck candidates from one owned character (mode-variant dual slugs)

Some owned characters yield more than one deck-search candidate from a
single roster entry - a pre-battle mode choice (Cinderella: Crystal Wave's
MG/Snipe) or a formation-role choice (Rapi: Red Hood's Combat Assist B1
stand-in vs. her nominal Burst 3 self). Distinct from the existing
`-signature` dual-slot pattern (Julia/Drake/Laplace base vs. signature,
which expresses the user's ITEM INVESTMENT and is resolved in the frontend's
roster import): a mode variant expresses a PLAY/FORMATION choice and is
resolved in the backend roster loader.

- `registry.MODE_VARIANTS: {base_slug: (candidate_slug, ...)}` - `user_roster.
  load_roster` fans one owned `UserNikkeState` out to every candidate slug
  (`MODE_VARIANTS.get(state.character_slug) or (state.character_slug,)`,
  loading a `NikkeSpec` per candidate), so all candidates compete for deck
  slots independently.
- `registry.VARIANT_BURST_TIERS: {variant_slug: tier}` - overrides a
  candidate's burst tier when it seats somewhere other than the character's
  nominal slot (Rapi: Red Hood's Combat Assist stand-in seats at tier 1, not
  her real tier 3).
- `registry._WEAPON_PROFILE_OVERRIDE_BUILDERS` / `get_weapon_profile_
  override(slug, skill_values)` - for a candidate whose weapon profile
  differs from the character's assembled dotgg/lootandwaifus stats (Snipe
  mode's SR profile); `user_roster` swaps the assembled profile after skill
  values resolve.
- `deck_search._no_variant_clash(units)` - deck search never seats two
  candidates of the same base together. Both enumeration paths (combination
  generation and permutation refinement) call it, and the pruning
  heuristic's own internal reference-deck construction (`_reference_deck`/
  `_variant_safe_top`/`_swap_slot`/`_cross_tier_reference`) was hardened to
  respect the same rule for ITS candidate measurements too, not just real
  output decks - a cross-tier variant sibling sitting in the reference deck
  is measured against an alternate reference with that sibling swapped out,
  rather than starved to an unmeasured 0.0 score.
- `deck_search.SOLE_TIER1_SLUGS` - a variant whose own role is self-
  cancelling next to a real occupant of the same tier (Rapi: Red Hood's
  Combat Assist reads as "no other Burst 1 ally," so seating her alongside
  an actual Burst 1 unit would simulate a formation the game can't produce).
  Blocks that variant from co-seating with ANY other tier-1 unit, not just
  its own MODE_VARIANTS sibling.

First consumers: `cinderella-crystal-wave-mg`/`-snipe`, `rapi-red-hood`/
`rapi-red-hood-b1`. See `docs/superpowers/specs/2026-07-18-weapon-
transform-design.md`.

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
model: `hit_rate` / Hit Rate, `burst_gauge_fill_speed_percent` (gauge charge
time is a fixed sim input), `shield_amount`, and anything HP/heal/DEF/
survivability. Defer these; if a Nikke's contribution is mostly these, say so —
a thin encoding is honest.

**`damage_to_parts_up` and `damage_to_interruption_parts_up` are inert too**, and
deliberately so. `calculate_damage` still TAKES `damage_to_parts_up` but leaves
it out of the damage-up bucket on purpose: it raises damage dealt to PARTS, and
this engine models one boss body with no parts, so riding the general bucket
would treat every hit as a parts hit — a ceiling Fienn's recorded run disproves
(see `damage_formula.py`'s comment, 2026-07-26). `damage_to_interruption_parts_up`
is not even a formula parameter. Both are worth RECORDING so an encoding stays
faithful and pays out the day parts become real targets, but never claim a
"Damage to Parts ▲" bullet moves damage today. Consumers that record it:
`cinderella_crystal_wave`, `rosanna_chic_ocean`, `anis_sparkling_summer`,
`helm`, `noir`.

**NOW consumed (Phase S, 2026-07-16):** `attack_speed_percent` (magazine weapons)
and `charge_speed_percent` (charge weapons) DO move damage — in a fixed 180s
fight a shorter shot interval means more shots. `attack_rate.py` scales the
firing cadence from these (evaluated per magazine boundary), so emit them as
`Effect("attack_speed_percent"|"charge_speed_percent", value, scope, duration)`.
A "shotgun allies only" speed buff is expressible — Tove's rides
`member_subset_buff_rule`, which resolves the weapon filter to a live `slugs:`
scope. See `docs/decisions.md`.

`flat_max_hp` (a Max-HP buff, e.g. Rouge's Game Master, Maxwell's Sequential
Limit Release) is **no longer inert** — since 2026-07-24 it feeds every
"ATK ▲ X% of the caster's Max HP" conversion. Encode Max-HP buffs as
`flat_max_hp` (don't defer them); they now move damage whenever the deck holds
a Max-HP-scaled ATK consumer.

The consumer side is `_helpers.max_hp_scaled_atk_rule(trigger, percent, scope,
duration, base_max_hp, condition=None, refreshing=False)` — use it instead of
multiplying the static `values["caster_max_hp"]` at build time. It resolves
`base_max_hp + total_for("flat_max_hp", caster, time)` when the rule FIRES and
registers the result as `flat_atk`.

**Semantics are a snapshot**, deliberately: the conversion happens once per
trigger, so a Max-HP buff that lands AFTER the ATK buff does not retroactively
grow it. A unit whose Max HP keeps rising mid-fight must re-fire the rule at
each change. This keeps the damage hot path (`_stat_bundle` / `total_for`'s
segment tables) untouched — not making deck search heavier is a hard constraint
(Fienn). Consumers: `laplace_ultimate_hero`, `maxwell_ordinary_mechanic`,
`cinderella`, `maiden_ice_rose` (the last inlines the same conversion because
its bullet lands at a delayed instant).

**Valid formula terms that raid_simulator just doesn't wire from the registry
yet** — a real gap, not a dead end: `shield_damage_up` and `final_atk_modifier`.
(`effective_range_bonus` is NO LONGER one of them: since 2026-07-31 the
encounter sets it via `BossProfile.effective_range_band` (`near`/`mid`/`far`),
which decides WHICH weapon classes collect the measured +0.30 — a Rocket
Launcher never does, and the scope is Core Damage's exactly, normal attacks
only. It is not a registry stat and no skill emits it, so a unit whose weapon
sits outside the encounter's band simply gets nothing.)
(`sustained_damage_up`, `distributed_damage_up`, `true_damage_up`, and
`projectile_explosion_damage_up` are NOW wired but **type-gated** — see "Damage
typing" above; they only move damage when the deck also produces an instance of
that type. `full_burst_bonus` is NOW wired too, but **opt-in per damage
instance**, not read unconditionally from the registry like the others — see
`full_burst_bonus_eligible` above and `docs/decisions.md` ("full_burst_bonus
wiring is opt-in per damage instance, gated on skill-text phrase").

**Decide it by COMPUTATION TIME, not by the phrase** (Fienn, 2026-07-26/27 —
this frames the older phrase rule rather than replacing it). The bonus applies
when the instance is *computed* inside a Full Burst window; "as additional
damage" was only ever a textual proxy for "computed some delay after the cast".
So:

1. **If you can tell when it is computed, ignore the phrase.** A per-shot
   nuke, a summon's ticks, a DoT tick, anything anchored to a concrete later
   time -> pass `full_burst_bonus_eligible=True` and let the engine's own
   window test (`start <= time < end`, against that instance's OWN time)
   decide. The flag only ENABLES the check, so instances outside the window
   still get nothing - this is exact, not an approximation.
2. **Keep the phrase check only for a single-instant nuke** whose timing is
   genuinely ambiguous from text alone.
3. Timing fact that still holds: a Burst 1/2 unit's instance fired at its OWN
   burst time is strictly BEFORE `full_burst_start`, so marking it eligible is
   dead code (Helm: Aquamarine). A Burst 3's lands at that same instant and
   does collect it.

Applied this way to Nayuta's Full-Charge nuke, Scarlet: Black Shadow's staged
nukes and Anis: Star's Shooting Stars - all three read "as damage" and all
three were wrong to be excluded. Every other damage instance defaults to False
and is unaffected. `enemy_def_percent` is NOW wired too (2026-07-16),
read unconditionally like `damage_taken_up` - emit a "DEF ▼ X%" enemy debuff as
`Effect("enemy_def_percent", -X/100, "squad", dur, caster)`, negative value.)

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
| `full_burst_enter` | when the Full Burst window opens — `FULL_BURST_OPEN_DELAY` AFTER tier-3 fires, so it does NOT reach the B3's own burst damage. Use only for text that really says "at the start of Full Burst" (Crown's One for All is the only encoded one). |
| `full_burst_end` | when the 10s Full Burst window ends |

**"Activates when entering Burst (Skill) Stage N" is NOT `own_burst_activate`.**
It describes the STAGE, so it fires in every cycle ANY ally of that tier takes
the slot — encode it as `ally_burst_activate` + `burst_stage_entered(N)`
(`squad_engine`). Wiring it to `own_burst_activate` silently drops the cycles a
same-tier ally bursts instead, which in a two-Burst-3 deck is about half of
them; seven units shipped that way before it was caught. The stage trigger
still fires before the burst damage is recorded, so the caster loses nothing in
the cycles it does burst. Watch for the wording variant "Burst **Skill** Stage
N" (Ein). `scripts/audit_burst_stage_triggers.py` checks text against wiring
across every encoded slug — run it after encoding a unit.

There is **no** trigger for: normal-attack counts ("after N normal attacks"),
full-charge-shot counts ("full charge N times"), ally-ammo-expended counters,
on-kill, HP thresholds, or "when Raptures appear". Effects gated on these must
be deferred — or, if central, raise extending the engine with a new trigger.

A rule's ACTION has no access to the boss's element, but its **condition does**:
gate "if the enemy is [element] Code" bullets with
`squad_engine.boss_is_element("<Element>")`, which reads
`SquadContext.boss_element` (False when the sim is element-agnostic). Consumers:
`rapi_red_hood.py`'s advantage grant, `sugar_signature.py`'s Fire-Code grant.
Never apply such a bullet unconditionally.
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
