# Special skill mechanics (easy to misencode)

A living catalog of NIKKE mechanics that are **easy to misread** — things that
look defensive or irrelevant but are actually DPS, cross-unit synergies, or
otherwise need care. Both the main agent (encoding) and the subagents
(data-collector when dumping skills, docs-keeper when recording) should consult
this and **append a new entry whenever a special mechanic comes up** (Fienn's
standing request). Keep entries short: what it is, why it's easy to get wrong,
how to encode it, and current engine status.

## Distributed Damage (분산 대미지)
- **What:** `distributed_damage_up` ("Distributed Damage ▲ X%") is a **DPS
  buff** that raises the damage of Nikkes whose kit deals *Distributed Damage*
  (e.g. Scarlet: Black Shadow — https://nikke.gg/characters/scarlet-black-shadow/).
- **Easy mistake:** reading it as a defensive / off-DPS stat and skipping it. It
  is not defensive.
- **Encode:** emit it as a `squad` effect (the buffer buffs the whole squad's
  distributed damage; only distributed-damage units actually have any to boost).
- **Engine status (2026-07-27): fully wired.** `distributed_damage_up` is
  consumed in the Damage-Taken group and is **type-gated** — it multiplies only
  damage instances typed `distributed`, so the "only distributed-damage units
  benefit" requirement falls out of the typing rather than needing a per-unit
  flag. Applied unconditionally (no Damage-Taken-debuff prerequisite,
  Fienn-verified 2026-07-11).
- **Both halves must be encoded or the buff is silently dead:**
  - **Dealers** (nuke must carry `damage_type="distributed"`): Scarlet: Black
    Shadow (6th/9th stages) · Phantom (+signature, burst) · Quency: Escape
    Queen (burst) · Bready (Recommended Taste full-charge hit) · Milk: Blooming
    Bunny (Embarrassment entry + Overconfident ticks).
  - **Buffers** (`distributed_damage_up`): Anchor: Innocent Maid · Mast:
    Romantic Maid (per Drunken stack) · Phantom (self) · Quency (self).
- Both failure modes have actually happened here: Mast's buff was filed as
  "survivability, not modeled" and left out, and Quency's burst was left untyped
  so her own buff could not reach it (both fixed 2026-07-27). The "Easy mistake"
  above is not hypothetical - check BOTH sides when touching a distributed unit.

## Debuff-stack reduction enabling stack retention
- **What:** some supporters reduce an ally-side debuff stack count ("Stack count
  of debuffs ▼ N"), e.g. Anchor: Innocent Maid's Starfish Omurice (Three-times
  tier).
- **Why it matters:** it can keep a self-stacking ally *below* a self-stun /
  self-reset threshold, changing that ally's average buff output. Concretely it
  lets **Mast: Romantic Maid** hold Drunken at 3 stacks instead of hitting the
  max-stack Hangover stun that resets her.
- **Encode:** model as a **deck-composition dependency** on the *consuming* unit,
  not as an emitted effect. Mast checks `deck_contains("anchor-innocent-maid")`
  and picks its Drunken stack schedule accordingly (`min(cycle,3)` with Anchor
  vs `((cycle-1)%3)+1` solo). See `mast_romantic_maid.py`.

## Escalating "Once / Twice / Three times" buffs
- **What:** "Effect changes according to the number of activation times.
  Previous effects trigger repeatedly. Once: … Twice: … Three times: …". Each
  tier unlocks on its activation and all unlocked tiers keep applying.
- **Encode:** use `_helpers.escalating_buff_rule(trigger, tiers)` — it reads
  `SquadContext.activation_count` and applies tiers 1..N on the Nth firing
  (per burst cycle). Put an empty list for a tier whose effect isn't DPS or
  isn't modeled (e.g. a Hit Rate step). **Do not flatten these to a steady-state
  max** — Fienn wants the per-cycle ramp (and it composes with deck-dependent
  behaviour like Mast's). Seen on: Anchor (both passives).
  **Not a blanket rule against steady-state, though:** the reason NOT to flatten
  here is that these ramp on BURST CYCLES (~8-13s apart), a meaningful fraction
  of a 180s raid. A stack chain that ramps on a much faster cadence than its own
  decay window (e.g. Quency's per-shot Explore Route, capping in ~2.5 real
  seconds against a fire rate whose decay windows are 0.5-2s) IS validly
  steady-stated — see `docs/insights.md`'s "Steady-state approximation for
  ramping buffs" for the general rule and `quency_escape_queen.py`.

## Self-scoped, same-squad-ally-gated burst CDR
- **What:** some units reduce **their own** Burst-Skill cooldown ("Affects self.
  Cooldown of Burst Skill ▼ X sec"), often gated on a *same-squad* ally being
  present. E.g. Blanc's Rabbit Twins W self-CDR needs Rouge or Noir in the deck;
  it's what lets her long 60s burst keep pace.
- **Easy mistake:** emitting it as a normal (squad) CDR pulse. The engine's CDR
  reduces cooldowns per pulse **scope**, so a squad-scoped pulse would speed up
  the *dealers'* rotation too and massively over-credit the deck.
- **Encode:** emit a `Pulse("burst_cooldown_reduction_sec", secs, "self", slug)`
  (self scope → reduces only the caster's cooldown) and gate the rule with a
  condition that checks the deck for the required ally (see `blanc.py`,
  `has_squad_twin`). "Same-squad ally" means a specific named unit, not any ally
  — confirm which with Fienn.

## "If self is in status X" where only self's own burst grants X
- **What:** a skill gates a bullet on "if self is in [status] status", where
  that status is granted by the unit's OWN burst (to itself and possibly
  others). E.g. Arcana's "Wheel of Fortune" - granted to Electric Code allies
  including herself by her own burst (Shackles of Destiny); other bullets check
  "if self is in Wheel of Fortune".
- **Encode:** this is equivalent to "did this Nikke's own burst fire earlier in
  the current cycle" - use the `own_burst_fired_this_cycle()` condition
  (`squad_engine.py`), which reads `SquadContext.burst_used_this_cycle` (already
  tracked by the engine, not yet cleared when `full_burst_end` rules run). No
  new status-tracking needed. See `arcana.py`.

## Targeting a per-member subset by tier + element + prior-burst
- **What:** some bullets target a dynamic subset like "all Burst 3 Electric
  Code allies who previously cast their Burst Skill" - a combination of tier,
  element, AND per-member "already burst this cycle" state.
- **Gap:** `Effect.scope` only supports `self` / `squad` / `element:X` - there's
  no way to target an arbitrary computed list of member slugs. This is a real
  engine gap, not a judgment call.
- **Encode:** defer + document (do not approximate onto `squad` or
  `element:X` - the audience is much narrower and these bullets are often large
  numbers precisely because the audience is narrow). Flag it if the deferred
  bullet looks central to the unit's value in a specific deck archetype. See
  `arcana.py`'s deferred "Magician"/"Strength" bullets.

## Weapon-type-scoped buffs ("all shotgun-wielding allies")
- **What:** some buffs target allies by weapon type (e.g. "all shotgun-wielding
  allies except self").
- **Gap:** no weapon-type scope exists (only self/squad/element:X).
- **Encode:** approximate as `squad` scope per the skill's standard
  approximation pattern (intended beneficiaries still get it; over-application
  to other weapon types is usually small). Watch for "except self" - squad
  scope can't exclude the caster, so if the caster is also the intended
  DPS unit, she'll incorrectly also receive the ally-only buff (document this
  self-overstatement explicitly). See `arcana_fortune_mate.py`.

## "Max Ammunition Capacity ▲ N round(s)" - a FLAT count, not a percent - BUILT (`max_ammo_rounds`, 2026-08-02)
- **What:** most ammo buffs are percentages, but some grant whole rounds
  ("Max Ammunition Capacity ▲ 2", Tove's Temporary Modification; +3 Grave,
  +5 Noir). The tell is the missing `%` and the "round(s)" wording.
- **Easy mistake:** filing it under `max_ammo_percent` "close enough". It
  isn't close: the same +6 rounds is +67% on an SG's 9-round magazine, +100%
  on an SR/RL's 6, and +2% on an MG's 300. These bullets are squad-scoped, so
  one percentage cannot serve the squad.
- **Encode:** `max_ammo_rounds`, stating the round count as-is. The caster does
  NOT need to know the recipient's weapon - `raid_simulator` converts against
  each recipient's own base magazine. See `tove.py`, `grave.py`, `noir.py`.
- **Still deferred alongside it:** "Reload N% of the magazine(s)", the partial
  top-up that usually rides in the same bullet. The engine reloads a magazine
  as one uninterruptible block, so a fractional mid-magazine refill has nowhere
  to land.

## A heal or shield whose OCCURRENCE is another bullet's trigger - BUILT (provider lists)
- **What:** a bullet arms on something happening to a unit rather than on a
  timer - "when recovery takes effect" (Crown's Royal Attire), "when a shield is
  placed in front of this unit" (Flora's Favorite Item Iris bullet).
- **Easy mistake:** skipping the heal/shield as survivability and then finding
  the consuming bullet unencodable. The AMOUNT is survivability; the EVENT is a
  trigger, and it is the only way those bullets ever fire.
- **Gap:** the engine models no heal or shield event, so per-occurrence timing
  cannot be asked. Deck presence can: `deck_contains_any(HEAL_PROVIDER_SLUGS)` /
  `SHIELD_PROVIDER_SLUGS` in `_helpers`, both derived from the collected skill
  text and cross-checked by `tests/test_provider_lists_match_data.py`.
- **Encode:** presence promotes the bullet to permanent - the CEILING. Where the
  unit can also arm it herself on a countable schedule, keep that as the FLOOR
  and make the two mutually exclusive, or the same bullet lands twice (Flora).
- **Watch for partial scopes:** Rei: Ayanami shields "all Fire Code allies", so
  her presence does not establish that an Electric consumer got one. Those live
  in `ELEMENT_GATED_SHIELD_SLUGS` rather than being silently dropped.

## "Deals X% as damage" tied to a trigger other than the caster's own burst
- **What:** some passives deal real damage on a trigger like "on entering Full
  Burst" or "after N normal attacks", NOT on the caster's own burst firing.
  E.g. Brid: Silent Track's Ignition Sequence deals 636% of final ATK whenever
  Full Burst starts, regardless of who bursts that cycle.
- **Easy mistake:** assuming all "Deals X% as damage" text is a burst nuke
  (`<name>_burst_percent`, tied to `own_burst_activate`) - it isn't if the
  trigger phrase says something else.
- **Encode:** use `_helpers.instant_nuke_pulse_rule(trigger, percent)`, which
  works for any of the four triggers. If the trigger is a normal-attack-count
  ("after N normal attacks"), it's still undeployable - no such trigger exists
  - defer that specific bullet.

## Enemy-element-conditional debuffs ("if the enemy is [element] Code") - BUILT capability (gap #5, 2026-07-16)
- **What:** some debuffs/bullets only apply against enemies of a specific
  element, e.g. Brid's Wind-Code-only Damage Taken debuff, Helm: Aquamarine's
  and Marciana's Electric-Code bullets.
- **Engine capability:** `SquadContext.boss_element` (injected by
  `raid_simulator`) + the `boss_is_element(element)` condition helper
  (`squad_engine.py`), used like `ally_bursted`/`deck_contains`. The
  `buff_rule` / `refreshing_buff_rule` / `instant_nuke_pulse_rule` helpers gained
  an optional `condition` param, so a gated bullet reuses the same builder as an
  ungated one (and it composes with per-shot window-gated modes - a bullet can be
  both window-gated AND element-gated, see Marciana's High-Risk nuke).
- **Encode:** gate the rule with `condition=boss_is_element("Wind")` etc. False
  when boss_element is unset. See `brid_silent_track.py`, `helm_aquamarine.py`,
  `marciana_marine_study.py`.

## "Elemental Advantage Attack Damage" - Element Bonus Damage, gated on advantage
- **What:** "Elemental Advantage Attack Damage ▲ X%" (e.g. Marciana) is
  **Element Bonus Damage** that only counts when the caster HAS elemental
  advantage over the enemy (the +10% element matchup). Despite the word "Attack
  Damage" in the name, it belongs to the formula's **Element Bonus Damage**
  group (`element_multiplier + other_elemental_bonus`), NOT the Attack Damage /
  Damage-Up group (Fienn, 2026-07-16).
- **Encode:** map to `other_elemental_bonus` (NOT `attack_damage_up`), gated on
  the boss being the element the caster is strong against - i.e.
  `boss_is_element(<caster's advantage target>)`. Iron > Electric, so Marciana's
  is gated on `boss_is_element("Electric")`. Since it's only emitted when the boss
  matches, it correctly adds to the element bonus only when advantage is present.
  See `marciana_marine_study.py`.

## Enemy DEF ▼ debuff - BUILT (enemy_def_percent, 2026-07-16)
- **What:** "DEF ▼ X%" on the enemy (e.g. Marciana's High-Risk Target
  DEF −10.56%). The damage formula's `enemy_def_percent` supported it but
  `raid_simulator` never read it, so it was silently inert.
- **Engine capability:** `raid_simulator._damage_instance` now reads
  `enemy_def_percent` from the registry (a squad-scope enemy debuff, exactly like
  `damage_taken_up`). Emit `Effect("enemy_def_percent", -X/100, "squad", dur,
  caster)` - note the NEGATIVE value for a DEF reduction. No DEF-floor-at-0 clamp
  yet (reference says defense can't drop below 0 through DEF% debuffs; add a clamp
  only when a unit's debuff would push a real boss DEF below 0).

## A continuous buff canceled by a later trigger, not a timer
- **What:** some "continuously" buffs are removed by a specific later event
  rather than expiring after a fixed duration - e.g. Grave's Heat Emission
  (squad Pierce Damage) is removed exactly when she uses her burst again, not
  after a timer. Confirmed by Fienn - the game text's "removed under certain
  conditions" was otherwise ambiguous.
- **Easy mistake:** reading "continuously...removed under certain conditions"
  as effectively permanent (steady-state) and applying it once, forever - this
  overstates uptime by however long the toggle is actually off (here, the
  ~10s window after each reburst).
- **Encode:** add the buff open-ended (`duration=None`) when it activates, then
  call `EffectRegistry.truncate_open_ended(stat, source_slug, time)` in the
  rule that fires on the canceling trigger - it closes the open effect's
  duration to the elapsed time, so replay queries (raid_simulator's later pass
  over normal-attack shots) still see the correct on/off windows regardless of
  processing order. Guard activation/removal with a status flag so repeated
  firings don't double-add or no-op incorrectly. See `grave.py`.

## Fixed-time delayed effects via a custom `applied_at`
- **What:** some passives unlock at a fixed, deck-independent time into the
  fight - e.g. Nayuta's Impermanence stacks once every 3 sec on a pure timer,
  unlocking self-buff tiers at stack thresholds (t=6s/30s/90s in a 180s fight).
  90s is HALF the raid - steady-stating this as "always on" would materially
  overstate her early-fight value.
- **Encode:** no new trigger is needed. `EffectRegistry.add(effect,
  applied_at=X)` accepts ANY `applied_at`, independent of the trigger's own
  firing time - so from a `battle_start` action (which fires once at t=0),
  compute the fixed unlock time(s) and pass them as `applied_at` directly, with
  `duration=None` for a permanent-from-that-point effect. Only valid for
  effects on a fixed, deck/RNG-independent timer (not e.g. burst-cycle-timed
  events, which vary per deck). See `nayuta.py`.

## Read "Affects self" vs "Affects all allies" literally, per bullet
- **What:** within ONE skill, different bullets can have different scopes -
  e.g. Nayuta's Impermanence stage buffs say "Affects self" (her own damage
  only) while Hypocrisy's Memory-Absorption-triggered buffs on the same
  character say "Affects all allies" (squad).
- **Easy mistake:** assuming a supporter's buffs are squad-wide by default and
  skimming past an explicit "Affects self" on one specific bullet.
- **Encode:** check the scope phrase per bullet, not per skill or per Nikke.

## Two-state toggle via activation-count parity
- **What:** some skills flip between two states each time the unit's own burst
  fires (e.g. Mint alternates "Assigned Part: Singing" / "...: Dancing" every
  use of Let's Sing Together!, starting at Dancing on her first use).
- **Encode:** no new status-tracking is needed - read
  `context.activation_count(caster_slug, "own_burst_activate") % 2 == 0` as the
  condition for "currently in the second state" (Singing here). Her own burst
  always fires before `full_burst_enter` in the same cycle (tier 2 before tier
  3), so the parity is already correct by the time a full_burst_enter-gated
  bullet checks it. See `mint.py`.

## "On [own] Full Charge attack" - no per-shot trigger exists
- **What:** some passives grant a squad buff every time the unit personally
  lands a Full Charge (charge-weapon) attack, e.g. Mint's Here I Go! and
  Prika's Let's Get the Show Started!. For an RL/SR unit firing charge shots
  regularly through the fight, this is a REAL, sizeable DPS source (a squad
  ATK buff scaled by the caster's ATK, refreshed every shot).
- **Gap:** normal-attack shots (including charge-weapon full-charge shots) are
  generated in `raid_simulator`'s separate weapon-stats pass, not routed
  through `fire_trigger` - there is no "own full-charge-shot" trigger a
  SkillRule can hook. This is a bigger addition than most (would need to wire
  the shot-generation loop into the trigger system, or a comparable
  mechanism), not a quick one-liner.
- **Encode:** defer + document, and flag clearly if this is a large chunk of
  the unit's kit (it usually is, for units built around it) - don't quietly
  leave the unit looking weak without saying why.

## Cross-character triggers ("when ally X's specific buff takes effect")
- **What:** some kits react to a NAMED OTHER Nikke's specific effect landing,
  not just "any ally bursts" - e.g. Prika's Encore Function activates "when
  Sing Along [Mint's burst buff bundle] takes effect while Prika is in
  Performance status [her own burst's buff window]". lootandwaifus's own notes
  confirm this is a real deck-pairing mechanic ("always used with Mint").
- **Gap, and why it's bigger than `deck_contains`:** `deck_contains(slug)` (used
  for Blanc/Rouge, Mast/Anchor) only checks static deck membership as a
  CONDITION on a rule already tied to the unit's OWN trigger. This mechanic
  needs Prika's rule to fire in reaction to a DIFFERENT unit's trigger event
  (Mint's `own_burst_activate`) - but `own_burst_activate` dispatch is scoped
  to only the firing slug's own rules (see `raid_simulator.on_tier_fire`), so
  there's no way for one Nikke's rules to observe another's trigger firing.
  Would need a new cross-character trigger-dispatch mechanism to model.
- **Encode:** defer + document; flag to the user, since these mechanics are
  often central to the specific pairing they're designed around.

## Escalating tiers on `full_burst_enter` are squad-wide, not self
- **What:** "Once/Twice/Three times" tiers sometimes fire on
  `full_burst_enter` rather than the caster's own burst - e.g. Helm:
  Aquamarine's CDR tiers (1.82/2.2/2.6 sec, summing to 6.62 by cycle 3).
- **Encode:** `context.activation_count(caster_slug, trigger)` works for ANY
  trigger name, not just `own_burst_activate`. `escalating_buff_rule` only
  handles `Effect`s; for an escalating **Pulse** (CDR), write the cumulative
  logic directly (see `helm_aquamarine.py`).

## Named resource / capped stack counter - BUILT capability (gap #2 Pattern A)
- **What:** a quantity-based resource (N-stack counter, EXP, Golden Chip,
  ammo/crit stacks) that fills on a trigger, clamps to a cap, and drives buffs
  whose magnitude scales with the current count. TWO stack lifetimes: PERMANENT
  accumulation ("stacks continuously", ramps then plateaus at the cap - e.g.
  Guillotine EXP, Soda Golden Chip) and TIMED ("stacks up to N, lasts X sec" -
  e.g. Modernia's 10-sec crit stacks). Also a DERIVED LEVEL (Guillotine's Hero
  Level = 1 + EXP//10, capped) that gates/scales further buffs.
- **Engine capability (Fienn-approved, 2026-07-12):** `ResourceSpec(name, fill,
  cap, buffs)` in `effects.py`, threaded via `_RESOURCE_SPEC_BUILDERS` /
  `get_resource_specs` / `roster` into `simulate_raid`'s `resource_specs`. The
  count is a FUNCTION OF TIME (`SquadContext.resource_count`), computed from a
  deterministic fill schedule - never a mutable total, so it's phase-order-safe
  (burst-cycle fills and shot-loop fills coexist). A resolution pass emits each
  buff as a step function of delta Effects over the fill/expiry events. `fill`:
  `("per_shot_every", N)` or `("per_shot_every_core", core_n, noncore_n)`
  (core-hittable-dependent, resolved by the sim's own `core_hittable`). `buffs`:
  `linear_resource_buff(stat, per_stack, scope, lifetime=None)`,
  `leveled_resource_buff(stat, per_level, level_fn, scope, lifetime=None)`, or a
  raw `ResourceBuff` with a threshold `value_fn`. See `engine-capabilities.md`.
- **First consumers:** `modernia.py` (timed capped), `guillotine_winter_slayer.py`
  (permanent + leveled + core-conditional fill), `cinderella.py` (periodic fill,
  see the "periodic" fill kind below).
- **Periodic fill kind (`("periodic", interval)`) - BUILT (2026-07-12):** a
  resource that ticks on a FIXED TIMER, independent of the owner's shots - e.g.
  Cinderella's Beautiful, which ticks every 3 sec while her decoy is up
  (continuously, from battle start). Resolved by `raid_simulator`'s own
  `fight_duration`, no shot timeline needed.
- **Resets (SET to a fixed value) - BUILT (2026-07-12):** a resource that gets
  reset to a fixed value rather than only ever accumulating - e.g. Soda's Golden
  Chip, reset to 17 when her burst consumes whatever had built up.
  `ResourceSpec.resets` (`[{"trigger": "battle_start"|"own_burst", "value": X}]`)
  + `SquadContext.reset_resource`/`resource_count_before_reset` (the latter
  exposes the PRE-reset value, needed for a rule gated on "how much had built up
  right before it was spent" rather than the post-reset value). The resolution
  pass replays fills and resets in chronological order so each reset's
  pre-value correctly reflects everything before it. See "resource_gated_buffs"
  and "dynamic_hit_count_nukes" below.
- **FB-window-gated fill kind (`("per_shot_every_during_full_burst", N)`) - BUILT
  (2026-07-12):** like `per_shot_every` but counting only the owner's shots
  whose time falls within a Full Burst window (Soda's "every 3 normal attacks
  during Full Burst" - shots outside Full Burst don't count at all), computed
  from `simulate_burst_cycle`'s own event log (`full_burst_start`/`full_burst_end`
  pairs). **Distinct from the FB-gated per-shot TRIGGER gap below** - this only
  covers a resource FILL, not a buff/nuke fired directly off an FB-window shot count.
- **Squad-burst-cycle-conditional fill kind (`("squad_burst_cycle_conditional",
  [(event_pred, gate_fn, delta), ...])`) - BUILT (2026-07-12):** a resource whose
  fill is driven by GLOBAL burst-cycle events (any squad member's burst tier
  firing, Full Burst entering - NOT the owner's own shots) AND conditioned on
  the resource's OWN running value at that instant - e.g. Maiden's MP: "+1 if
  MP==0" on any squad member's Burst Stage 1, "+1 if MP>=1" on Full Burst enter.
  Resolved by `_resolve_squad_burst_cycle_resource`, a stateful walk over
  `simulate_burst_cycle`'s own event log (not a flat deterministic schedule like
  every other fill kind). Same-instant ordering between the owner's own-burst
  reset and other events is preserved by checking the reset INLINE against each
  event as the walk reaches it, not via a separate sort/merge step - this
  mattered because Fienn confirmed burst1->burst2->burst3->full-burst-enter is a
  strict, never-violated sequence, so a unit's own burst-tier fire always
  precedes Full Burst entry in the same instant. First consumer:
  `maiden_ice_rose.py` (see "dynamic_hit_count_nukes" below for the consequence
  this had on Diamond Dust's actual hit count).
- **Still deferred:** Pattern B: time-DRAINING gauges + threshold transforms (Ark
  Ranger battery, filled by part-destruction which the engine has no concept of)
  - deferred, don't invent a part-break schedule.

## Resource-scaled / gated burst nuke (incl. repeating DoT ticks) - BUILT capability (2026-07-12)
- **What:** a burst-fired nuke whose magnitude is gated or scaled by a named
  resource's count - a single additional hit gated on a threshold (Julia's
  Climax, "Activates when Crescendo is at max stacks") or scaled by the count
  directly ("mirrors the stack count", Cinderella's Glass Slippers), or a
  REPEATING TICK where each tick independently re-reads the count at ITS OWN
  time (Guillotine's Extermination, "20.87% of final ATK * Hero Level every sec
  for 10 sec" - Hero Level can rise mid-DoT as EXP keeps accumulating).
- **Why this was hard:** the nuke is recorded during the burst cycle
  (`on_tier_fire`), but the resource's fill schedule isn't populated until the
  resolution pass runs, which happens AFTER the whole burst cycle - so reading
  `resource_count` at record time would always see zero fills.
- **Engine capability:** `record()` gained an optional `resource_gate`
  (`resource_name, cap, lifetime, scale_fn`), NOT resolved into a concrete
  percent until PHASE 2 (`_resolve_percent` calls `context.resource_count(slug,
  name, event_time, cap, lifetime)` and multiplies by `scale_fn(count)`) - the
  same "record now, compute later" trick the engine already uses for every
  other damage instance. Wired via `raid_simulator`'s `resource_scaled_nukes`
  param (`{slug: [spec, ...]}`, each spec a dict with `resource`, `cap`,
  `base_percent`, `scale_fn`, `tick_count`, `tick_interval`, optional
  `lifetime`/`damage_type`), exposed per-Nikke via `_RESOURCE_SCALED_NUKE_BUILDERS`
  / `get_resource_scaled_nukes`. `tick_count=1, tick_interval=0.0` covers the
  single-hit case; a repeating DoT sets both. Logged with
  `source="resource_scaled_nuke"`.
- **First consumers:** `julia.py`/`julia_signature.py` (Climax's threshold gate),
  `cinderella.py` (Glass Slippers' mirrored hit), `guillotine_winter_slayer.py`
  (Extermination's Hero-Level DoT).

## Multi-hit burst nuke ("attacks sequentially N times") - BUILT capability (2026-07-12)
- **What:** a burst nuke worded "Deals X% of final ATK as damage. Attacks
  sequentially N times" - N SEPARATE hits, not one hit at N×X%. Defense is a
  FLAT per-hit subtraction (`_base_damage`), so pre-multiplying the percent
  overcounts damage whenever `enemy_def > 0` (defense would only be subtracted
  once instead of N times).
- **Engine capability:** `raid_simulator`'s `burst_hit_counts={slug: N}` (default
  1); `on_tier_fire` records N identical damage events at the same instant.
  Exposed per-Nikke via `_BURST_HIT_COUNTS`/`get_burst_hit_count`. The hit count
  itself is treated as FIXED skill text (a module constant like a cooldown), not
  a scaled data slot - hit counts don't scale with skill level.
- **First consumers:** `cinderella.py` (Glass Slippers, 10x), `julia_signature.py`
  (Climax, 5x).

## `resource_gated_buffs` (buff-side analog of resource-scaled nukes) - BUILT capability (2026-07-12)
- **What:** a burst-fired BUFF gated on (or scaled by) a named resource's count
  AT THE BURST'S OWN TIME - e.g. Soda's ATK +65.25%/15s, granted only if Golden
  Chip had at least 30 stacks right before her burst reset it to 17.
- **Why this needed a different mechanism from `resource_scaled_nukes`:** a nuke
  can defer its percent computation to phase 2 (every damage instance in this
  engine is already record-now/compute-later). A buff has no equivalent second
  pass - `buff_rule`/`registry.add` mutate the registry immediately when the
  triggering action runs, and that action (`on_tier_fire`) runs BEFORE the
  resolution pass that populates the resource's fills/resets for the cycle - so
  a gate check at `on_tier_fire` time would always see a stale/empty resource.
- **Engine capability:** `resource_gated_buffs` specs (`{"resource", "cap",
  "use_pre_reset", "gate_fn", "stat", "value", "scope", "duration"}`) are
  processed IN the resolution pass itself, iterating `context.burst_times[slug]`
  for each of the owner's own burst times and adding the Effect directly once
  `gate_fn(count)` passes (`count` from `resource_count_before_reset` when
  `use_pre_reset` is set, else `resource_count`). Wired via `raid_simulator`'s
  `resource_gated_buffs` param, exposed per-Nikke via
  `_RESOURCE_GATED_BUFF_BUILDERS`/`get_resource_gated_buffs`.
- **First consumer:** `soda_twinkling_bunny.py`.

## `dynamic_hit_count_nukes` (hit count itself is a resource's value) - BUILT capability (2026-07-12)
- **What:** a burst-fired nuke whose HIT COUNT - not just its percent - is a
  named resource's own value at burst time, e.g. Maiden's Diamond Dust ("attacks
  repeatedly based on current MP").
- **Engine capability:** reads the PRE-reset count via
  `resource_count_before_reset` for each of the owner's own bursts, recording
  that many identical damage events (each independently defense-subtracted,
  same reasoning as `burst_hit_counts`). Spec dict: `{"resource", "base_percent",
  "extra_flat_atk_percent_of_max_hp" (optional), "damage_type" (optional)}`;
  wired via `raid_simulator`'s `dynamic_hit_count_nukes` param, exposed
  per-Nikke via `_DYNAMIC_HIT_COUNT_NUKE_BUILDERS`/`get_dynamic_hit_count_nukes`.
  Logged with `source="dynamic_hit_count_nuke"`.
- **`extra_flat_atk` (nuke-scoped flat-ATK bonus, built alongside this):**
  `record()`/`_damage_instance` gained an `extra_flat_atk` parameter (mirroring
  the existing `extra_charge_bonus` parameter's precedent exactly), so a nuke
  like Diamond Dust ("1372.8% of the sum of 10% of final Max HP and ATK") can
  fold a percent-of-Max-HP bonus into ONLY that nuke's own flat_atk term without
  leaking into normal attacks or any other damage instance from the same slug -
  a plain registry `Effect("flat_atk", ...)` would leak everywhere, since
  flat_atk is read unconditionally by every damage instance for that slug.
- **Notable consequence (not a bug):** Maiden's Diamond Dust always hits EXACTLY
  ONCE per cycle in this engine - her own burst provably drains MP to 0 before
  Full Burst's "if MP>=1" fill rule can ever see a nonzero value, given the
  engine's confirmed strict burst-tier ordering (see the
  squad-burst-cycle-conditional fill entry above). Modeled anyway (not silently
  dropped) for documentation honesty, with the reasoning in
  `maiden_ice_rose.py`'s module docstring.
- **First consumer:** `maiden_ice_rose.py`.

## Delayed burst effects (`fire_delay` / `own_burst_delayed`) - BUILT capability (2026-07-12)
- **What:** a burst effect that lands a FIXED NUMBER OF SECONDS after the burst
  fires, not at cast time - e.g. Asuka's Annihilation, which deals damage when
  her "Annihilation State" self-status ends, 9 seconds after her burst, not
  when the burst itself is cast.
- **Engine capability:** `dynamic_hit_count_nukes` spec dicts gained an optional
  `fire_delay` (seconds); the nuke fires - and reads its resource's pre-reset
  count via `resource_count_before_reset` - at `burst_time + fire_delay`
  instead of exactly `burst_time`. `ResourceSpec.resets` gained a matching
  `"own_burst_delayed"` trigger (`{"trigger": "own_burst_delayed", "delay":
  seconds, "value": X}`) so the SAME resource resets at the identical delayed
  instant, using the same delay value for both (guaranteeing an exact
  floating-point match between the reset time and the nuke's lookup time,
  since both compute `burst_time + delay` from the same inputs).
- **First consumer:** `asuka_shikinami_langley_wille.py` (Annihilation, 6.62%,
  9s delay).

## `full_burst_bonus_eligible` (opt-in Full Burst Bonus per damage instance) - BUILT capability (2026-07-12)
- **What:** whether a specific damage instance receives the game's Full Burst
  Bonus (+50% Major Modifier). Fienn's resolving rule (2026-07-12, after an
  earlier retracted per-unit-delay theory - see `docs/decisions.md`): a burst
  skill's damage instance receives it ONLY if its own official description
  contains the phrase "as additional damage"; otherwise the damage is computed
  from cast-time effects only and never gets it.
- **Engine capability:** `record()`/`_damage_instance` and `Pulse` (threaded
  through both `drain_instant_damage` and the per-shot-nuke drain site) gained
  an optional `full_burst_bonus_eligible` flag (default False). When True, the
  instance's recorded time is checked against the ALREADY-EXISTING
  `full_burst_windows` list; if it falls inside one, `full_burst_bonus=1.0` is
  passed to `calculate_damage` (else 0.0). This is opt-in per instance, not a
  blanket engine-wide change - every one of the 45 units encoded before this
  batch defaults to False and is completely unaffected.
- **Same-instant boundary edge case (not yet hit in practice):**
  `full_burst_start` fires at the SAME timestamp as the tier-3 burst that
  triggers it (not strictly after), so a hypothetical eligible nuke fired at
  cast time with zero delay would still read as "inside" the window under the
  inclusive-start check (`start <= time < end`). Watch for this if a future
  unit's "as additional damage" nuke fires exactly at burst time with no
  delay - it would incorrectly get the bonus under this check. Doesn't affect
  any current consumer (Asuka's eligible nukes are either delayed 9s past
  burst or fired on a per-shot timer unrelated to her burst).
- **First consumer:** `asuka_shikinami_langley_wille.py` (both of her "as
  additional damage" nukes - the unconditional 471.86% every-50-shots nuke,
  and the delayed 6.62% Annihilation nuke).

## `resource_scaled_nukes` with no resource (flat repeating DoT) - BUILT capability (2026-07-12)
- **What:** a repeating-tick burst DoT with NO resource scaling at all - e.g.
  Mana's Fatal Error!, a plain 396%-of-ATK-per-second DoT, 10 ticks one second
  apart.
- **Engine capability:** `resource_scaled_nukes` spec dicts can now omit
  `"resource"` (along with `"cap"`/`"scale_fn"`/`"lifetime"`) entirely - the
  tick_count/tick_interval loop still runs, but with `resource_gate=None`, so
  every tick fires at the flat `base_percent` unscaled. Avoids inventing a
  fake resource just to reuse the repeating-tick machinery.
- **First consumer:** `mana.py` (Fatal Error!).

## "After/every N CRITICAL hits" - genuinely unrepresentable (not a to-do)
- **What:** a fill/nuke trigger worded "after landing N critical hit(s) with
  normal attacks" (e.g. Julia's signature Crescendo/Marcato).
- **Why it's different from a normal per-shot counter:** the engine models crit
  as EXPECTED VALUE (`crit_rate * (0.5 + crit_damage)` scaling every hit's
  damage), never rolling per-hit RNG - so there is no "was this specific shot a
  crit" event to count. `per_shot_rules`' existing shot counters (which DO work
  for plain normal-attack / full-charge counts) can't be extended to cover
  this - it's a structural mismatch with the crit model, not a missing trigger.
  Discovered encoding Julia's signature build (2026-07-12); permanently
  deferred, not queued for a future extension. `eve` likely has the same
  mechanic - re-verify before assuming it's fixable.

## Periodic/recurring skills on their own fixed cooldown - BUILT capability
- **What:** some kits have a SEPARATE active skill with its own short
  cooldown (e.g. Helm: Aquamarine's Aegis Cannon Suppression Fire, 4s) that
  auto-fires repeatedly throughout the fight, independent of burst timing -
  not gated on Full Burst, the caster's own burst, or a normal-attack count.
- **Engine capability (Fienn-approved, 2026-07-10):**
  `raid_simulator.simulate_raid`'s `periodic_nukes` param -
  `{slug: {"cooldown": seconds, "percent": float}}`. Each entry ticks at
  t=cooldown, 2*cooldown, ... up to `fight_duration`, computed the same way as
  a burst nuke (live buffs at that instant), logged with `source="periodic"`.
  Fully independent of burst_cycle - fires even if the deck never completes a
  Full Burst. Exposed per-Nikke via `registry.get_periodic_nuke(slug,
  skill_values)`, wired automatically by `roster.assemble_simulation_inputs`.
- **Encode:** add `<name>_periodic_percent(values)` + a module-level cooldown
  constant (the cooldown is fixed skill text, not a data slot) in the Nikke's
  module, then register both in `registry._PERIODIC_NUKE_BUILDERS`. Do NOT
  approximate this onto an existing trigger. See `helm_aquamarine.py`.

## Damage-type buffs apply only to matching-type instances - BUILT capability
- **What:** "Sustained Damage ▲", "Distributed Damage ▲", "True Damage ▲",
  "Projectile Explosion Damage ▲" buffs raise only damage *of that type*, not
  every hit. Easy mistake: wiring them like `attack_damage_up` (blanket), which
  over-credits every normal attack in the deck.
- **Engine capability (2026-07-10):** each damage instance has a `damage_type`;
  `raid_simulator._TYPE_BUCKETS` reads the type-gated bucket only for matching
  instances. See `engine-capabilities.md` "Damage typing" for the full table
  and how to type burst nukes (`registry._BURST_DAMAGE_TYPES`), periodic nukes
  (`"damage_type"` key), and normal attacks (RL weapon → `projectile_explosion`;
  a `normal_attacks_deal_true` self effect → `true`).
- **Consequence for encoding:** emitting one of these buffs is only non-inert if
  the deck also produces an instance of that type. E.g. Mint's Projectile
  Explosion Damage buff needs an RL ally (or a projectile-explosion skill nuke)
  in the deck to matter; a Sustained Damage buff needs a sustained-damage dealer.
  Encode the buff faithfully regardless, but say in the docstring what type of
  dealer it needs to land.
- **Projectile Explosion specifically:** applies to RL Nikkes' normal attacks
  AND to skills carrying the "Projectile Explosion" keyword (e.g. Rapi: Red
  Hood's Power of Inheritance). Confirmed by Fienn.

## Cooldowned Skill 1/2 fire at t=cooldown, not battle start - BUILT capability
- **What (universal battle rule, confirmed by Fienn):** any Skill 1 or Skill 2
  (not the Burst) that has a **cooldown** does NOT activate at battle start - it
  first fires at t=cooldown and then repeats every cooldown. E.g. Takina Inoue's
  Battlefield Control (cd 15s) fires at t=15, 30, 45, ... A skill clause with a
  `for N sec` duration but no "Activates when ..." trigger phrase is usually one
  of these (check the skill's cooldown; lootandwaifus shows it in the S2 title,
  e.g. "Spina di Rosa (Cooldown: 30s)").
- **Easy mistake:** encoding it onto `battle_start` (wrong - it starts at
  t=cooldown, and it repeats). Or guessing an event trigger.
- **Encode:** use the `periodic_rules` capability (see
  `engine-capabilities.md`): build the clause's buffs as
  `buff_rule("periodic", [...])` and register `(cooldown, rules)` in
  `registry._PERIODIC_RULE_BUILDERS`. Rules must be stateless buff appliers. If
  the skill also deals a nuke on its cooldown, that's `periodic_nukes` (a
  separate mechanism); a nuke with an internal duration < cooldown (duty cycle,
  e.g. Rosanna's Spina 15s-on/15s-off in 30s) is still a gap. See
  `takina_inoue.py`.

## Shot-count triggers ("after/every N normal attacks", "N full charge") - BUILT
- **What:** a skill fires when the unit's shot count crosses a threshold -
  "Activates after N normal attack(s)" (recurring every N unless stated once),
  "after N full charge attacks", "every N shots". Fires a nuke (e.g. Brid's
  Journey Ahead: 675% every 5) or a buff (e.g. Ark Ranger, Rouge, Ade).
- **Engine capability (2026-07-11):** `per_shot_rules` (see
  `engine-capabilities.md`). Build with `(threshold, mode, [SkillRule])`,
  `mode` = "after"/"every"; the rule is `buff_rule("per_shot", ...)` or
  `instant_nuke_pulse_rule("per_shot", pct)`. Register in
  `registry._PER_SHOT_RULE_BUILDERS`. The engine counts shots regardless of
  weapon (charge weapons: every shot is a full charge), so a "full charge N"
  and a "normal N" both just count shots - pick N from the skill text.
- **Refresh vs stack (IMPORTANT):** a per-shot buff with a multi-second duration
  applied every shot would STACK, because `total_for` SUMS active effects - an AR
  at 12/s with a 3s buff piles up ~36x. NIKKE refreshes these (no "stacks up to
  N"), so use `refreshing_buff_rule("per_shot", ...)` (→ `add_refreshing`), which
  truncates the prior same-(stat,source,scope) instance so overlaps collapse to
  one value. Different sources still sum. Only a per-shot buff that literally
  says "stacks up to N" should use plain `buff_rule`.
- **Still deferred:** a shot-count trigger whose effect ALSO gates on boss
  element (e.g. Brid's Wind-Code debuff every 10 normals) - the count part
  works, the Wind-Code gating is the separate boss-element gap.

## "On firing the last bullet" (magazine boundary) - BUILT capability (2026-07-12)
- **What:** a skill that fires specifically on the round that EMPTIES its
  magazine, right before reloading - e.g. Julia (base)'s Crescendo, Helm's
  last-bullet trigger. Distinct from a plain shot-COUNT trigger (above): the
  magazine boundary moves whenever the user's [Max Ammo Up] overload option
  or a temporary ammo-boosting skill buff changes magazine size, so a fixed
  "every N shots" approximation would drift out of sync with the real
  trigger over a fight.
- **Engine capability:** `attack_rate.py`'s `magazine_last_bullet_times`/
  `charge_last_bullet_times`/`last_bullet_shot_times` mirror
  `generate_{magazine,charge}_shot_times`/`generate_shot_times`'s exact
  3-tier structure, marking the shot at `magazine_size - 1` within each
  magazine - `magazine_size` is re-derived live from `max_ammo_percent_at`,
  the SAME callable (and same live-buff mechanism) shot generation itself
  already uses, so an overload/skill ammo buff is automatically reflected
  with no extra wiring. A shot that's merely the LAST ONE RECORDED because
  `fight_duration` cut the fight off mid-magazine is correctly excluded -
  only a round that reaches the genuine magazine boundary counts.
  `per_shot_rules` gained a `"last_bullet"` mode (`threshold` unused) that
  checks a shot's time against this set, computed once per unit whenever a
  `"last_bullet"` per_shot_rules entry OR an `("on_last_bullet",)`
  `ResourceSpec` fill is present (skipped otherwise, and shared between the
  two so they see identical magazine boundaries). A STACKING (not one-shot)
  last-bullet effect - e.g. Julia's Crescendo, "stacks up to 5 times" - uses
  the `ResourceSpec` fill kind instead of a per_shot_rules buff/nuke.
- **Attack/charge speed don't need modeling for this:** neither is wired as
  a shot-interval modifier anywhere in this engine (see "Stats the engine
  does NOT consume" in `engine-capabilities.md`) - and even if they were,
  they'd change shot CADENCE (time between shots), not magazine CAPACITY
  (rounds per magazine), so they wouldn't move which round is "last" anyway.
  Only `max_ammo_percent` matters here.
- **Encode:** use `(None, "last_bullet", [rules])` in a unit's `per_shot_rules`
  entry, or `ResourceSpec(fill=("on_last_bullet",), ...)` for a stacking
  variant. First real consumers (2026-07-12): Julia (base)'s Crescendo/Climax,
  Helm's Frontline Command (rewired off a DEAD `on_last_bullet_hit`
  `fire_trigger` placeholder that nothing ever actually dispatched - a
  passing unit test that manually fires a trigger name doesn't prove
  `raid_simulator` ever fires it for real, see `docs/insights.md`), Privaty's
  LD Assault (a conditional-gated last-bullet nuke, additionally scaled by
  whether the target is in a status her own burst applies - see
  `privaty.py`'s docstring for the time-window-check pattern used since no
  built-in TIMED status primitive exists).

## Full-charge-count CDR -> per-cycle CDR approximation
- **Signature:** "when attacking with Full Charge for N time(s): Cooldown of
  Burst Skill down X sec" (D: Killer Wife, Rouge, and others in the backlog).
- **Why not per-shot:** a per-shot CDR pulse would have to feed the burst
  rotation, but the rotation is simulated in phase 1 BEFORE the per-shot pass
  runs, so it can never reach it. Counting shots is the wrong tool here.
- **Model (Fienn, 2026-07-11):** apply the CDR once per cycle instead - a normal
  `cdr_pulse_rule("full_burst_end", X)` (squad). Rationale: the "N full charges"
  condition is met essentially every cycle (a full charge is ~1 sec, so 8 within
  a ~13s+ cycle is near-certain), so once-per-cycle is a faithful approximation,
  and it reuses the existing per-cycle CDR machinery that every other CDR uses.
- **Scope of the approximation:** only for a RECURRING "every N" CDR (not a
  one-time "after N"). Slightly generous in an already-fast rotation (if stacked
  CDR shortens the cycle below the time to fire N full charges, the game would
  skip it that cycle but the model still gives it) - a second-order effect,
  acceptable for a recommender and far better than deferring the value.

## Record-then-compute ordering (why per-shot squad buffs reach burst nukes)
- **What:** `simulate_raid` records all damage instances in phase 1 (applying
  buffs only) and computes them in a phase-2 pass against the final registry.
  This is what lets a per-shot / periodic squad buff applied mid-fight correctly
  raise a burst nuke that fired earlier in the timeline.
- **Encode implication:** you can emit a squad buff from a per-shot or periodic
  rule and trust it reaches every damage instance active in its window,
  including burst nukes - no ordering caveat to work around.

## Cross-unit reactive trigger (one unit reacts to another's burst)
- **Signature:** a skill "activates when [another unit's named buff] takes
  effect" — e.g. Prika's Encore fires "when Sing Along takes effect" (Sing Along
  is Mint's burst buff, so this means "when Mint bursts").
- **Engine capability (2026-07-11):** the `ally_burst_activate` trigger. After
  any unit's burst tier fires, `raid_simulator` sets `context.last_burst_slug`
  and fires `ally_burst_activate` across every unit's rules. Gate the reacting
  rule with `ally_bursted("<other-slug>")` (and combine with more conditions via
  `all_conditions(...)`). Buff appliers only, like `periodic_rules`. See
  `prika.py` (Encore) for the worked example.
- **Modeling a "status you set on the reacting unit":** the Encore also puts the
  bursting unit into a status (Mint → Singing) continuously from that moment. Set
  it time-stamped: `context.set_status(context.last_burst_slug, "<flag>", time)`;
  `status_since(slug, flag)` then tells the other unit's rules WHEN it began.
- **"Extends duration of an existing buff":** don't re-add the buff on each
  re-trigger — same-stat effects SUM, so overlapping re-adds double-count. Model
  the maintained buff as permanent (duration None), gated on the partner being in
  the deck via `deck_contains(...)` in the action (see Prika's Charge Damage).

## Per-shot status that alternates or is pinned mid-fight (time-indexed)
- **Problem:** the per-shot pass runs AFTER the burst cycle and evaluates against
  the FINAL context, so `activation_count` (whole-fight total) and a bare
  `has_status` (final boolean) can't tell you the unit's status AT a given shot
  time. Mint alternates Dancing/Singing each burst, and Prika's Encore pins her
  Singing partway through - both need per-time answers.
- **Fix:** reconstruct the status at each shot time inside the ACTION (which gets
  the shot time). `context.burst_times[slug]` (recorded in `on_tier_fire`) gives
  the unit's burst timeline for a per-cycle parity; `status_since(slug, flag)`
  gives when a pinned status began. See `mint.py::mint_singing_at` - it returns
  Singing if pinned by `time`, else by parity over bursts at or before `time`.
  This models BOTH solo (alternation) and paired-with-Prika (pin) correctly.

## "For N round(s)" is a bullet-count duration, NOT seconds
- **Signature:** a buff "▲ X% for N round(s)" (Zwei's Pierce Equation, Miranda's
  Wake Up crit rate). Easy to misread as a burst-cycle / time duration.
- **What it actually means (Fienn, 2026-07-12):** the buff is consumed by the
  affected ally's NEXT N normal-attack shots (bullets), then gone; re-granted the
  next cycle. So a "1 round" buff granted at Full Burst enter buffs exactly ONE
  shot per affected ally per cycle - NOT continuous uptime, NOT the burst nuke.
- **Model:** `round_buff_rule(trigger, [(stat, value, scope_spec)], shots=N)`.
  It records a `RoundGrant`; `raid_simulator`'s shot loop converts each grant into
  a real timed Effect whose window covers exactly the affected unit's next N shots
  after the grant (from the first covered shot up to the next uncovered shot / fight
  end), scoped `slugs:<unit>`. A squad grant is consumed independently per ally
  (one Effect per unit), matching per-ally bullet consumption.
- **Scope_spec:** `"squad"`/`"self"`/`"element:X"` static, or `("top_atk", n)` for
  the highest-ATK targeting below. See `zwei.py` (squad) and `miranda.py` (top-1).
- **Still deferred:** a round-buff that ALSO stacks per shot inside a Full-Burst
  window (Zwei's normal-attack-during-FB pierce, up to 3) - needs an FB-window-gated
  per-shot trigger, which doesn't exist yet (see "FB-window-gated per-shot TRIGGER"
  below - Soda's co-fired ally buff hits the same gap).

## Highest-final-ATK top-N targeting ("N allies with the highest final ATK")
- **Signature:** "Affects N ally unit(s) with the highest final ATK (except
  caster; including the caster if there are not enough allies)" (Miranda's Wake
  Up / Powering Up). Do NOT approximate as `squad` - in a dual-carry deck a top-1
  buff would wrongly hit the second carry.
- **Model:** `SquadContext.top_atk_slugs(n, caster_slug, registry, time)` ranks the
  deck by LIVE final ATK (base ATK grown by atk_percent + flat_atk read at `time`,
  so a buff applied earlier the same cycle is reflected) and returns the top-n
  slugs, excluding the caster but filling from the caster if there aren't enough
  allies. The resulting `slugs:a,b` Effect scope targets exactly those units.
- **Helpers:** `highest_atk_buff_rule(trigger, n, buffs)` for timed buffs;
  `round_buff_rule(..., ("top_atk", n))` for the bullet-count variant.
- **Why live ranking matters:** Miranda is Burst 1, so her Powering Up (own_burst,
  tier 1) fires BEFORE Wake Up (Full Burst enter, tier 3); resolving the target at
  application time means Wake Up ranks allies with Powering Up's ATK already on.
- **Caveat:** ranking reads the registry at trigger time (phase 1), so per-shot
  buffs (applied in the later shot pass) aren't seen - fine, since those are
  self-scoped and don't change other units' ranking.

## FB-window/own-status-window-gated per-shot TRIGGER (gap #7, distinct from window-gated resource FILL)
- **What:** a buff/nuke fired directly off "every N of the unit's shots, but only
  counting shots inside a window" - e.g. Soda's Lucky Golden Chip co-fired buff
  ("after 3 normal attacks during Full Burst, affects self and the 1 ally with
  the highest final ATK: Attack Damage +10.51% for 2 sec"), or Asuka's Anti A.T.
  Field 15.62%-of-ATK direct-damage bullet ("every 10 shots while in Annihilation
  State, deals 15.62% as damage" - a SEPARATE bullet from her Anti A.T. Field
  stack-buff, which the window-gated FILL below already covers).
- **Why it's a separate gap from the window-gated resource fill (built, see
  above):** `("per_shot_every_during_full_burst", N)` and
  `("per_shot_every_during_own_status_window", N, duration)` only feed a
  resource's count - neither has a path to fire a `per_shot_rules`-style
  buff/nuke action directly. `per_shot_rules` itself has no window filter at all.
- **Easy mistake:** approximating it as a plain "every N shots" `per_shot_rules`
  entry, ignoring the window restriction. This is a REAL overcount, not a
  minor one, whenever the shot cadence makes "every N shots" (elapsed real time)
  comparable to or longer than the buff's own duration - e.g. Soda's SG fires
  1.5 shots/sec, so "every 3 shots" = every 2 sec, exactly the buff's own 2-sec
  duration, which reads as effectively PERMANENT if applied outside Full Burst
  too, instead of only active during her ~10-sec Full Burst window each cycle.
- **Encode:** defer + document (do not approximate). Also blocks Zwei's
  FB-window normal-attack pierce stacking (see "For N round(s)" above). Two
  confirmed consumers as of 2026-07-12: Soda (Lucky Golden Chip co-fired buff),
  Asuka (Anti A.T. Field's 15.62% nuke bullet).

## Resource-fill-triggered squad buff (gap #8, distinct from `resource_gated_buffs`)
- **What:** a buff granted to OTHER units (not the resource owner) triggered by
  the resource's own fill event - e.g. Maiden's Blessings Upon You "when MP is
  replenished" bullet (Elemental Advantage Attack Damage +40.9% / ATK +20.9% of
  caster ATK, for 10 sec, to all other Electric Code allies).
- **Why it's a separate gap from `resource_gated_buffs`:** `resource_gated_buffs`
  (built 2026-07-12) only covers the resource OWNER's own burst-time gate on a
  buff to herself - it has no path for a fill event to grant a buff to a
  different scope (squad/element) of OTHER units.
- **Encode:** defer + document; not built as of 2026-07-12 (only one known
  consumer so far, Maiden - a secondary supporting bullet, not her headline
  mechanic).

## Sequential-hit bursts compute all hits at cast time - NOT Full-Burst-Bonus eligible
- **What:** skills whose text says the burst "attacks **sequentially** N times"
  (e.g. Cinderella, Sakura: Bloom in Summer) - and Maiden: Ice Rose's burst,
  which says "repeatedly" but works identically - compute ALL hits from the
  buffs active at activation time. They therefore CANNOT receive the Full
  Burst bonus.
- **Easy mistake:** "sequentially" suggests hits spread out over time (so some
  might land inside a Full Burst window that opens partway through), but
  mechanically it is a single cast-time computation - all N hits are recorded
  at the same instant (see `burst_hit_counts` above), so none of them can be
  "additional damage" past cast time.
- **By contrast:** repeating-tick DoTs ("deals X% every 1 sec for N sec") read
  live buffs at each tick's own time, so ticks inside the Full Burst window DO
  get the bonus (`full_burst_bonus_eligible=True`) - the Mana/Guillotine rule,
  in-game confirmed 2026-07-12, reaffirmed and generalized by Fienn 2026-07-16:
  the FB bonus is a defined element of the damage formula; exceptions need a
  mechanism-level justification like the sequential cast-time computation
  above. See `ark_ranger_black.py` (Meteor / floor Collider DoTs).

## Summoned entities ("Summons N X") — the skill text lies about the cadence

- **What it looks like:** Ein's Feather Shot reads "Activates when Near Feather
  is summoned. ... Deals 90.81% of final ATK as true damage", next to Feather
  Standby's "Summons 4 Near Feathers". The obvious reading is ONE hit per summon
  — 4 hits at battle start, 6 more per burst.
- **What it actually is:** the feathers PERSIST and keep attacking on their own
  timer, and the timer gets faster the more of them are alive. The summon count
  is a population, not a hit count. Nothing in the text says so (2026-07-17,
  Fienn from a client datamine).
- **Easy mistake:** encoding the literal reading. For Ein it undercounts her main
  damage source by more than an order of magnitude — the persistent feathers land
  31 hits in a single Full Burst, versus 6 for "one hit per summon".
- **Why it matters generally:** a summon skill's DPS is `population x cadence`,
  and BOTH usually live outside the skill text (per-entity lifetimes, cadence
  formula, re-summon/reset rules). **Treat any "Summons N ..." as unencodable
  from the text alone and ask Fienn** — this is exactly the "ask rather than
  guess" case. Engine support: `scheduled_nukes` (see `engine-capabilities.md`).
- **Also worth knowing:** where a formula and a measurement disagree, prefer the
  measurement and say so in the docstring. Ein's -16%-per-feather cooldown
  reduction predicts a hit every 0.267s at 6 feathers; Fienn's recording shows
  0.3s (31 hits/FB, first at +0.8s). The gap is a system throttle nobody
  documents. Modeled as a 0.3s floor, flagged as an assumption — the additive
  vs. multiplicative reading was settled the same way (multiplicative predicts
  ~18 hits against 31 observed).

## "Stacks up to N times and lasts for X sec" — one counter, refreshed; NOT N overlapping DoTs

- **What it looks like:** Raven's Shock Wave — "Activates when performing a Full
  Charge attack. Deals 68.46% of final ATK as sustained damage every 1 sec,
  stacks up to 10 times and lasts for 5 sec." The natural reading is that each
  Full Charge lays its own 5-second DoT and several run concurrently.
- **What it actually is** (Fienn, 2026-07-17): ONE stack counter. The 1st Full
  Charge puts it at 1 stack, the 2nd at 2, up to the cap. **"Lasts for X sec" is
  the counter's life, and every trigger refreshes it back to X** — stacks survive
  as long as you keep triggering inside the window, no matter how old they are.
  Only a gap longer than X drops it back to a single fresh stack.
- **Why the difference is huge:** under the wrong reading the stack count settles
  at `window / trigger_interval`; under the right one it climbs to the cap and
  stays. For Raven that is 5 vs 10 — her main damage source came out **1.9x too
  low** (128M vs 292M over 180s) before Fienn caught it.
- **The cap is a real constraint here, unlike Velvet's ammo pouch.** Do not reuse
  the "it can never bind, skip the resource" shortcut without checking: with
  refresh semantics the counter climbs to the cap and pins there, so the cap sets
  the steady state. Check the unit's actual cadence against the window — Raven's
  RL takes 1s per Full Charge and her longest gap is the 3s reload, so the
  counter never expires at all.
- **How to encode:** a `scheduled_nukes` schedule over `context.shot_times`, with
  each tick time repeated once per live stack (one damage instance per stack, so
  defense comes off each — same rule as a multi-hit burst). See `raven.py`'s
  `_stack_counts` / `_shock_wave_ticks`.
- **Boundary to decide:** when the tick interval equals the trigger interval,
  every tick coincides with a trigger and the ordering decides everything. This
  project resolves it the same way the rest of the engine does — a tick counts
  the stacks standing at its OWN time (cf. `resource_scaled_nukes` re-reading its
  count per tick).

## Staged shot-count table whose requirements the burst rewrites (gap #10)

- **What it looks like:** Scarlet: Black Shadow's Fleetly Fading Breakthrough —
  "Effects vary according to the number of attacks. Only one effect is
  triggered at a time. Three times: [283.03% damage]. Six times: [565%
  Distributed]. Nine times: [848.03% Distributed]." — plus her burst: "Changes
  Full Charge attack count required for Skill 1 to 1 time/2 times/3 times for
  10 sec."
- **What it is:** ONE running full-charge counter walking a staged requirement
  table (fire stage 1 at 3, stage 2 at 6, stage 3 at 9, then reset), where the
  burst swaps the table to 1/2/3 for its window. Not expressible as static
  `every N` entries — the requirement table is time-dependent.
- **How to encode:** `per_shot_rules`' `"sequence"` mode — `threshold` is
  `{"requirements": [...], "own_burst_window": (duration, [...])}` and the
  rules slot holds one rule list per stage. Semantics (Fienn, 2026-07-18): the
  count and stage CARRY OVER across the window boundary; a stage fires once
  count >= the ACTIVE requirement for it (so progress under one table is never
  lost under the other); at most one stage fires per shot.
- **Typing:** the "Distributed Damage" stages are per-shot pulses — pass
  `damage_type="distributed"` (the Pulse carries damage typing since
  2026-07-18) so squad `distributed_damage_up` buffs apply. Vs the solo raid
  boss, single-target and distributed stages alike land fully on the boss.

## Weapon-mode transforms ("changes to a different weapon" burst/status skills) - BUILT capability (v1, 2026-07-19)

- **What it looks like:** a burst or status skill that swaps the unit's
  weapon entirely for a window - "Charges the weapon like a Rocket Launcher
  for X sec... Full Charge deals Y%" (Snow White, Maxwell's Pierce Shot), or
  a sustained high-cadence "true damage every tick while active" window
  (Laplace's Hero Vision, `laplace-signature`). The old approach (Red Hood's
  original 2026-07-18 encoding) approximated this with `scheduled_nukes`
  anchored to an in-game shot-count measurement, folding the charge
  multiplier into a flat percent and subtracting an estimate of the base
  weapon's double-counted shots inside the window - workable, but it meant
  deck Charge Damage / ATK / charge speed buffers couldn't touch the
  transform's damage (baked into a constant), and the subtraction was an
  approximation, not a real silence.
- **Easy mistake:** reusing the `scheduled_nukes` approximation for a NEW
  transform unit just because Red Hood set the precedent - it's a strictly
  worse model now that segments exist (Red Hood herself was migrated off it,
  2026-07-19); the old pattern is kept only for historical context.
- **Encode:** use `weapon_mode_schedules` (`attack_rate.
  generate_segmented_shots`, see `engine-capabilities.md`) instead - a
  schedule function returns windows (`until_shots` for a single-shot burst
  cannon, `end` for a fixed-duration sustained window) each carrying a full
  weapon `profile`. The base weapon is genuinely silenced inside the window
  (no subtraction needed) and resumes with a fresh magazine when it ends. A
  real charge-weapon profile (`charge_time` set) lets deck buffs multiply the
  transform; an explicit `rate_of_fire` profile is for a window with no
  believable charge/magazine model of its own (a pure in-game shot-count
  measurement, e.g. Laplace's 93-tick Hero Vision window) and deliberately
  takes NO cadence buffs, since the measured count already reflects the real
  game's cadence.
- **Not every transform fits the segment primitive - three plan-2 consumers
  confirmed this without ever touching the primitive (2026-07-19):**
  `cinderella-crystal-wave`'s MG/Snipe toggle is a rare-transition,
  held-for-the-whole-fight mode choice, not a short burst/status window -
  modeled instead as two static-profile dual slugs (`-mg`/`-snipe`), each
  just the existing plain weapon-stats path twice, mutually excluded from
  deck search via `registry.MODE_VARIANTS` (see "Multiple deck candidates
  from one owned character" in `engine-capabilities.md`). `rapi-red-hood`'s
  120-normal-attack projectile launch isn't a weapon-profile swap at all
  (her base weapon never changes) - it needed `scheduled_nukes` with Full
  Burst window visibility (`SquadContext.full_burst_windows`) instead, a
  small context-exposure extension, not a segment - see
  "gap #7로 안 풀리는 사례였던 rapi-red-hood" in `docs/engine-gaps.md` for the
  full resolution. `snow-white-heavy-arms`'s charge-lock-on loop turned out
  to need NO new state machine after all: lock-on/ammo accrual is
  deterministic within a fixed charge time (a per-mode constant, not a
  tracked resource), Auto Fire rides the existing per-shot primitive, and
  Fully Active - the one piece that DOES swap her weapon for a window - is
  an ordinary segment. The only genuinely new piece was keeping the
  segment's boosted Auto Fire and the base weapon's plain Auto Fire from
  double-firing on the same shot - see the `every_during_segment`/
  `every_outside_segment` entry below.
- See `docs/superpowers/specs/2026-07-18-weapon-transform-design.md`,
  `snow_white.py`/`maxwell.py`/`laplace_signature.py`/`red_hood.py`/
  `cinderella_crystal_wave.py`/`rapi_red_hood.py`/
  `snow_white_heavy_arms.py` docstrings.

## Segment-gated per-shot modes need record identity, not shot time (`every_during_segment`/`every_outside_segment`) - BUILT capability (plan-2, 2026-07-19)

- **What it looks like:** a per-shot rule that must fire differently inside
  vs. outside a `weapon_mode_schedules` segment - Snow White: Heavy Arms's
  Auto Fire deals a plain all-enemy-hit-plus-sequential-hits nuke on every
  full charge, but while her Fully Active segment is active the same Auto
  Fire is boosted (more loaded ammo, a Sequential-attack-damage buff) - the
  SAME per-shot event, two different payloads depending on segment state.
- **Easy mistake:** filtering by comparing each shot's TIME against the
  segment's `[start, end)` window - v1's confirmed resume semantic is that
  the base weapon picks back up with a FRESH magazine THE INSTANT a segment
  ends (`until_shots` exhausted or `end` reached), so the segment's last
  shot and the resumed base weapon's first shot can land at the exact same
  timestamp. A time-window filter would then let that one boundary shot
  satisfy BOTH "inside" and "outside," double-firing the per-shot rule.
- **Encode:** `per_shot_rules` modes `"every_during_segment"`/
  `"every_outside_segment"` (threshold=N) filter by the shot's
  `ShotRecord.in_segment` FLAG - the record's own identity, set once at
  generation time - never by comparing times. This makes the two modes
  structurally exclusive: a shot is one record with one `in_segment` value,
  so it can satisfy only one of the two filters, no matter how timestamps
  land. See `snow_white_heavy_arms.py`'s `build_seven_dwarves_per_shot_rules`
  and `engine-capabilities.md`'s `per_shot_rules` entry.

## A segment profile that reads the caster's OWN weapon stats (`caster_weapon_stats`) - BUILT capability (plan-2, 2026-07-19)

- **What it looks like:** a weapon-mode segment that isn't an independent
  transform weapon but the unit's OWN normal charge shot with a bonus folded
  in - Snow White: Heavy Arms's Fully Active state doesn't swap to a
  different cannon, it's her regular full-charge shot with Shades of
  White's +528% Charge Damage added on top.
- **Easy mistake:** hardcoding the base charge-damage percent as a literal
  in the segment profile - it silently drifts from the character's real
  weapon data (and duplicates a value that's already assembled elsewhere).
- **Encode:** skill-value assembly now injects `caster_weapon_stats` (the
  unit's fully assembled `weapon_stats` dict) into the values passed to
  every builder, alongside the existing `caster_atk`/`caster_def`/
  `caster_max_hp` keys (`roster.py`). A segment schedule builder reads
  `values["caster_weapon_stats"]["charge_damage_percent"]` and adds the
  skill's own bonus to it, rather than inventing a number. See
  `snow_white_heavy_arms.py`'s `build_fully_active_weapon_mode_schedule`.

## Play/formation choices are a DIFFERENT dual-slug pattern than item-investment dual-slots (`MODE_VARIANTS`) - BUILT capability (plan-2, 2026-07-19)

- **What it looks like:** an owned character who can show up in a deck
  candidate list more than once for a reason that has nothing to do with
  whether the user owns an item - Cinderella: Crystal Wave's player-chosen
  MG/Snipe mode, or Rapi: Red Hood's Combat Assist B1 stand-in vs. her
  nominal Burst 3 self.
- **Easy mistake:** reaching for the existing `-signature` dual-slot pattern
  (Julia/Drake/Laplace base vs. signature). That pattern encodes whether the
  user OWNS an item - real investment data, resolved in the frontend's
  roster import (`DUAL_SLOT_BASES` + the roster's `favorite_item` flag). A mode/formation
  choice isn't investment at all - the user owns exactly one character and
  is choosing how to PLAY her, every candidate is always available, and the
  choice needs to be resolved where deck search actually runs (backend).
- **Encode:** `registry.MODE_VARIANTS` (backend roster loader, not frontend)
  - see "Multiple deck candidates from one owned character" in
  `engine-capabilities.md` for the full mechanism (`MODE_VARIANTS`/
  `VARIANT_BURST_TIERS`/`_WEAPON_PROFILE_OVERRIDE_BUILDERS`/
  `_no_variant_clash`).
- **A variant that seats itself out of a REAL occupant's way, not just its
  own sibling's (`SOLE_TIER1_SLUGS`):** Rapi: Red Hood's Combat Assist is
  gated on "no other Burst 1 ally in the deck" - so seating her B1 stand-in
  next to an actual Burst 1 unit would simulate a formation where her own
  in-game condition is false, a self-contradiction the base `_no_variant_
  clash` check (same-base siblings only) doesn't catch, since the clash
  here is with a DIFFERENT character entirely. `deck_search.
  SOLE_TIER1_SLUGS` blocks that variant from co-seating with ANY other
  tier-1 occupant. Check for this kind of "this variant's whole premise
  requires an empty seat, not a specific rival" self-cancellation whenever
  a mode variant re-seats into a slot it doesn't nominally occupy.

---
*Add new mechanics above this line as they come up.*
