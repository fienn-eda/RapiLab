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

## Ammo pouch / stored-resource mechanics
- **What:** some kits (e.g. Velvet) have a personal resource that fills from
  stealing enemy ammo or a flat grant, and drains to power self-buffs.
- **Gap:** no resource-tracking primitive exists, and the triggers that
  spend/fill it are usually already-deferred (own full-charge-shot,
  normal-attack-count).
- **Encode:** defer the whole chain; note in the docstring what it gates.

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
- **Still deferred:** "on firing the LAST bullet" (needs magazine-boundary
  markers). And a shot-count trigger whose effect ALSO gates on boss element
  (e.g. Brid's Wind-Code debuff every 10 normals) - the count part works, the
  Wind-Code gating is the separate boss-element gap.

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
  per-shot trigger, which doesn't exist yet.

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

---
*Add new mechanics above this line as they come up.*
