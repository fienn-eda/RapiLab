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
- **Engine status:** `distributed_damage_up` exists in `damage_formula.py` but
  `raid_simulator.py` does not consume it yet, and proper support needs per-unit
  gating so only distributed-damage units benefit. So it is currently **inert** —
  encode it faithfully (so it starts counting once wired) but know it moves no
  damage until (a) the stat is wired and (b) a distributed-damage dealer is
  encoded with a "has distributed damage" flag. Seen on: Anchor: Innocent Maid
  (Starfish Omurice, Twice tier).

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

## Enemy-element-conditional debuffs ("if the enemy is [element] Code")
- **What:** some debuffs only apply against enemies of a specific element, e.g.
  Brid's Wind-Code-only Damage Taken debuff.
- **Gap:** SkillRule actions have no access to the boss's element (only
  `raid_simulator` does, via `boss_element`) - applying the debuff
  unconditionally would be wrong against non-matching bosses.
- **Encode:** defer + document. Don't apply it unconditionally.

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

---
*Add new mechanics above this line as they come up.*
