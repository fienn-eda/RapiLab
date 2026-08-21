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

**Seat-scoped targeting IS expressible** (2026-08-13) — do NOT approximate it as
`squad`, which overpays 5 recipients for a 3-recipient bullet. Use
`_helpers.seated_buff_rule` (or `_helpers.seated_scope`, when the action does
more than register buffs), then add the unit's slug to
`registry.SEATED_BUFF_SLUGS`. Consumers: `rouge.py`'s Sword Coin,
`flora_signature.py`'s Peace of Mind bullets.

Two wordings land here:
- **Direct** — "Affects self and 2 allies on both sides" (Rouge).
- **Indirect** — "Affects all allies in the `<state>` state", where a sibling
  bullet granted `<state>` to "self and both adjacent allies" (Flora's Peace of
  Mind). Chase the state to its granter before deciding the scope.

Who the neighbors are is the PLAYER's choice, not a deck property — a back-row
seat (position 2 or 4) borders any 2 of the other four. So `neighbor_slugs`
answers with a supplied seating when there is one, and otherwise with the 2
highest-ATK allies (a cheap deterministic policy the ~1200-sim search can
afford). The report path re-scores every arrangement the five seats can produce
and keeps the best (`deck_search.evaluate_deck_best_seating`), so the number
shown to the player is the optimum and the seating that produces it rides along
in `result["seating"]`.

`SEATED_BUFF_SLUGS` maps the slug to the seats it may occupy (0-indexed), which
is how a bullet's own row condition gets declared — Rouge's needs the back row
(`BACK_ROW_SEATS`), Flora's needs nothing (`ANY_SEAT`). Get this right: the
restriction is what stops an arrangement from seating Rouge in the front row and
paying her buff anyway, and it decides which JOINT arrangements exist when one
deck holds two such units (6 distinct maps for a Rouge deck, 10 for a Flora one,
18 for a deck holding both).

Read the effect line, not the trigger: "Activates when an adjacent ally … .
Affects all allies" is genuinely `squad` (Flora's Iris True Damage), and no
seating changes it. Only a bullet whose AFFECTS clause names the sides — or
names a state that does — belongs here.

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
| `hit_rate` | narrows a normal attack's bullet spread; the share of that spread still inside the boss's core becomes the core-hit probability (`accuracy.core_hit_rate`) | "Hit Rate ▲/▼ X%" |

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

**`hit_rate` reaches damage only through the bullet spread, and only on an
encounter that opts in (2026-08-07).** A weapon's normal-attack rounds land
inside a circle whose diameter shrinks as `hit_rate` rises
(`accuracy.spread_diameter`; converged diameters in `WEAPON_SPREAD_DIAMETER` —
AR 75 · SG 250 · SMG 110 · MG/SR/RL 10px, all read off the game data, all three
weapons' measured regressions crossing zero diameter at the same 110% hit
rate). The share of that circle still inside the boss's core is the area ratio
(`accuracy.core_hit_rate`), fed into `calculate_damage`'s `core_hit_rate`
parameter the same way crit already averages over `crit_rate`. This is gated
on `BossProfile.core_diameter_px` — `None` (the default) leaves every
core-eligible normal attack at p=1.0, the engine's old ceiling, so `hit_rate` is
a genuine no-op until an encounter sets a diameter. Since 2026-08-14 the
calibration harness sets one (`raid_record.CORE_DIAMETER_PX` = 48.89, Annihilio
measured in the fight), so a `hit_rate` bullet DOES move the recorded-raid
numbers for SMG/AR/SG holders; the raid-rotation bosses the app ships still
carry `null`.

**A "chance to activate" trigger is resolved at its EXPECTED VALUE, not rolled
(Fienn, 2026-08-17).** The engine is deterministic and already treats every
other probability this way — each hit scaled by `crit_rate`, each shot by
`core_hit_rate`, `per_critical_hit_every` accumulating the live crit rate rather
than counting real crits. So "there is a p% chance of activating when attacking"
becomes one activation every `100/p` shots, via
`_helpers.expected_shots_per_proc(chance_percent)` (rounded to a whole shot,
because the counters that consume it index shots). First consumer: Tove's base
Emergency-Crafted Bullets, 5% → every 20 shots.

Two things this does NOT license. **It does not unblock a chance sitting on a
trigger the engine has no timeline for** — Sugar's Black Typhoon is "a 20%
chance of activating when COVER IS ATTACKED", and with no incoming attacks
modeled there is no event stream to thin; it stays deferred at p=1.0 as much as
at p=0.2 (gap #14). And **it does not let one builder serve two builds whose
slot means different things**: Tove's `description_value_01` is a chance on the
base and a shot count on the Favorite Item, so each has its own builder. Sharing
one would have reloaded the base every 5 shots — four times too often, and
plausible enough to survive review.

**The spread has a second axis: where the round sits in its magazine
(2026-08-15).** `accuracy.SPREAD_CONVERGENCE` holds `{weapon: (opening
diameter, per-round tightening)}` and today has one entry — MG opens every
magazine at 250px and tightens 7px a round to its converged 10px, which is
`shot_detail.start_accuracy_circle_scale` / `accuracy_change_pershot`. Against
the measured 48.89px Annihilio core that makes an MG's first 29 rounds partial
core hits (p rises 0.038 → 1.0) instead of the guaranteed ones its converged
diameter alone implies. The round index rides on `ShotRecord.magazine_index`
and reaches `_core_hit_rate_at`; `None` means "no magazine position to give"
and takes the converged diameter, which is what a transform segment and the
frontend mirror get. A reload reopens the circle — it is a MAGAZINE
convergence, so the index restarts with each magazine. The two axes multiply:
`hit_rate` scales whatever diameter the round is drawing (UNMEASURED — no
reading separates that from "hit rate only moves the converged end").

**SR/RL still see nothing, and MG only early in a magazine** — SR/RL carry
start == end == 10px in the data, inside any plausible core, so narrowing it
further changes nothing; AR/SG/SMG have room to move at every round, and MG
only until its circle converges. `core_strike`-typed skill damage
and `core_eligible_override` summons (e.g. Anis: Star's Shooting Stars) keep
p=1.0 regardless of `hit_rate` — the text says the hit already lands on the
core, so aim is not in question. A Pierce holder's body-instance (the second
hit on a `pierce_hits_body_behind_core` boss) is weighted by the same
probability: a round that missed the core has no core to pass through. See
`accuracy.py`.

**A weapon-mode segment may declare its own aiming behaviour on its profile.**
Two keys, and both come ONLY from an in-game measurement — never from the
segment's `weapon` string, which is a hand-written archetype.
`_core_hit_rate_at` deliberately reads the unit's REAL weapon for an undeclared
segment.

- **`always_core_hit: True`** (2026-08-07) — that segment's shots are on the
  core with no spread math at all. Measured for Nayuta's Memory Incineration,
  Zwei's Overcharge Formula and Snow White's Seven Dwarves: I.
- **`spread_diameter: <float>`** (2026-08-15) — the segment draws a DIFFERENT
  circle, measured, in the same game units as `accuracy.WEAPON_SPREAD_DIAMETER`
  (AR 75 · SMG 110 · SG 250 · MG/SR/RL 10). Moran's spear mode is the case:
  150, twice her Assault Rifle's 75. Hit rate scales a declared diameter the
  same way it scales a class one; magazine convergence does not apply (measured
  on MG only, and segments never reload).

**An explicit `rate_of_fire` on a segment profile is a MEASUREMENT ANCHOR, so
measure it.** It takes no cadence buffs precisely because the reading already
includes every in-game modifier — which makes a borrowed class constant sitting
in that slot a silent error, not a conservative default. Moran's spear mode
carried the SMG class's 20/sec as an explicit stand-in for three weeks and was
**20% slow**: Fienn's frame reading of her 5-hit trigger puts her at 2.46 ± 0.07
frames a round, rejecting 3 frames at 7.4σ and landing 0.55σ from 2.5 (24/sec,
the SMG's NOMINAL 1440 rpm before the frame-grid rounding). Do not generalise
that to the SMG class — the record's three SMG units read 1.002x at 20/sec and
would go to ~1.15x at 24. `docs/measurements/moran-spear-mode.md`.

**How a diameter gets measured**: only the RATIO of two lengths read in the SAME
frame is usable — there is no screen-px→game-unit formula, and the one written
down in 2026-08-08 was wrong and retracted
(`docs/measurements/accuracy-circle-and-core-px.md`). Moran's 150 came from
100px transformed against 50px untransformed at the same hit rate, so both the
screen scale and the hit-rate factor cancel: `75 × 100/50`.

**Not every transform needs either key.** Fienn checked five in 2026-08-15 and
two came back negative — Grave's circle does not change at all, and
Jill: Valentine's narrows only because her burst raises Hit Rate, which the
engine already models through the ordinary stat. And where the unit's BASE
weapon is an SR/RL (or a converged MG), its 10-unit circle is already inside any
boss core, so the approximation cannot change a number no matter what the
segment does — that covers 12 of the 20 segment slugs.

**Every collected Hit Rate bullet is encoded as of 2026-08-07** (15 units, 19
slugs). `tests/test_hit_rate_bullets_are_encoded.py` cross-checks the skill text
against the modules, so a new unit with a Hit Rate bullet fails the suite until
its module registers the stat — the gap that let this stat ship with a consumer
and no producers for five weeks.

Scheduling stats (change the burst rotation / shot timing, not per-hit damage):
| stat | mechanism | game wording |
|---|---|---|
| `burst_cooldown_reduction_sec` | **Pulse**, drained at full-burst-end; **scope-aware** (self reduces only the caster's cooldown, squad reduces everyone's) | "Cooldown of Burst Skill ▼ X sec" |
| `max_ammo_percent` | scales base magazine size (increases and decreases both apply to BASE, summed) | "Max Ammunition Capacity ▲/▼ X%" |
| `max_ammo_rounds` | adds whole ROUNDS to the magazine, on top of the percent: `round(base × (1+pct) + rounds)`. State the round count as-is - `raid_simulator` converts it against each recipient's own base magazine, so a squad-scope grant correctly means +67% to an SG and +2% to an MG | "Max Ammunition Capacity ▲ N round(s)" (no `%`) |
| `reload_speed_percent` | shortens reloads | "Reloading Speed ▲ X%" |
| `mg_heating_speed_percent` | scales how long a machine gun's per-magazine warm-up lasts. A MACHINE GUN spends 2.2833 sec at the head of a COLD magazine reaching its nominal 60 rounds/sec, and that warm-up is a measured CURVE rather than one flat reduced rate (`attack_rate.MG_SPINUP` is a cumulative point list: rounds 0-2 take 56 of its 137 frames, 2-24 another 55, 24-48 only 26). This stat scales the DURATION, leaving the 48 gaps it covers alone. ▲ divides, ▼ multiplies (Fienn, 2026-08-14 — the same shape as his charge-speed ruling that Ada's ▼300% means charge time ×4). Sampled per magazine at its start, like `attack_speed_percent`. **The clamp is per SEGMENT** — no stretch of the ramp may be tighter than the weapon's nominal gap, because a warm-up is a slow start and not an accelerator. It binds where the ramp is already nearly at speed: the tail runs 1.083 frames a round and floors at +8.3%, so ▲100% gives 79.5 frames (1.325 sec) rather than a whole-ramp halving's 68.5, while ▼100% is untouched at 274 frames (4.5667 sec). No other weapon class has a warm-up, so this reaches MG recipients only | "MG heating up speed ▲/▼ X%" (the game uses "heating" for machine guns alone) |
| — (not a stat) **heating survives a short reload** | a magazine does NOT always open cold. Heating bleeds off linearly over `attack_rate.HEATING_DECAY_SECONDS` (66 frames, measured) from the previous magazine's last round, so `ramp_start_after_gap` opens the next magazine PART WAY UP the curve and it pays only the ramp that is left. The firing gap includes `post_reload_delay_for_weapon` — a measured 12.5-frame pause between a reload completing and the next round, MG only. Nothing to encode: it is automatic for every MG. What it means for a unit is that stacked reload speed buys more than seconds — Crown plus Privaty drives the reload to zero and the next magazine opens near the top of the ramp. Natural reloads all clear the decay (Rosanna 1.67 sec, Asuka: WILLE 2.478, and 1.080 even on her forced one), so an unbuffed MG still opens cold | — |

**Mid-magazine ammo refund — NOT a stat, and NOT a Max Ammo percentage.**
`attack_rate.AmmoRefund(every_shots=N, rounds=R)` hands `R` rounds back into the
magazine every `N` of the unit's own shots. The shot counter is CUMULATIVE over
the fight (not per magazine) and the refund is CAPPED at the magazine's capacity
(Fienn, in game, 2026-07-31). Use it for "Activates when landing N normal
attack(s) ... Reloads R round(s)": what a refund is worth depends on where in
the magazine it lands, and it shifts every later reload against the Full Burst
window, so approximating it as `max_ammo_percent` scores non-monotonically.
`R` must be `< N` or the magazine never empties. `AmmoRefund.__post_init__`
only rejects this AT CONSTRUCTION when `rounds >= every_shots` and neither
`first_shot` nor `windows` is set — a bare `first_shot` (no `windows`) slips
past the dataclass check the same as a window-gated refund does, but this is
not a hole: `_refund_sequence` still sums a phase-only refund into its own
"never empties" check (window-gated refunds are the only ones excluded from
that sum, because their own window bounds the walk instead — see `windows`
below). A unit can hold SEVERAL sources at once — its own skill plus the
Tactical Bear cube — which are vetted together there.

**A refund's size is `rounds` OR `percent` of the magazine it lands in**
("Reload 5.31% of the magazine", Tove's Favorite Item) — a percentage rounds to
the nearest whole round against the CAPACITY the recipient's current magazine
actually opened with, the same granularity every max-ammo buff already uses.

**`first_shot` turns a bare period into a ROTATION PHASE.** Left at 0 (the
default) the refund fires on every multiple of `every_shots`, the plain "every N
shots" shape. Set it and the refund instead fires on the `first_shot`-th shot and
every `every_shots` after — the 2nd, 8th, 14th... of a period-6 rotation, never
the 6th or 12th (Arcana: Fortune Mate's Memories and Moments reload phase).

**`windows` restricts the counter to explicit `[start, end)` spans**, restarting
the count at 0 with each one, for a refund that only runs while some other
status is up rather than fight-long. `needs_own_burst_window=True` flags a
refund whose window cannot be filled at registry-build time (before the burst
schedule exists) — [the caster's own burst, that cycle's Full Burst end) — so
`raid_simulator.resolve_ammo_refund_windows` replaces it with a real `windows`
tuple once the burst schedule is known. **A refund that declares the flag and
resolves to zero windows (its own burst never lands before `fight_duration`)
stays classified as windowed and is therefore permanently inert** — it does NOT
fall back to the fight-wide counter. Every classification site (`_refund_
sequence`, `magazine_shot_count`, `_refund_carries_windows`) reads this off one
shared `attack_rate._gated_to_windows(refund)` helper, so a future consumer of
`windows` cannot reintroduce the fail-open by only fixing one call site.
`_shared_magazine_shots` (Snow White: Heavy Arms' shared-magazine walk, below)
is a fourth consumer of refunds but classifies none of them: it keeps no
per-window counter, so it drops every window-gated refund outright before
walking instead of reading `_gated_to_windows` per shot. **It does NOT support
a window-gated refund** — one reaching it goes permanently inert, the same
outcome the other three sites reach by classification, reached here by
exclusion instead.

Expose it as `<name>_ammo_refund(values)` and register in
`registry._SKILL_AMMO_REFUNDS` as `slug: (builder, required_boss_element or
None)`; the roster carries it as `skill_ammo_refund` and `raid_simulator.
resolve_ammo_refunds` applies the encounter gate, since the roster assembles a
deck and only the simulator knows the boss. Consumers: `eve` (Eagle Eye, gated
Electric), `ludmilla_winter_owner` (The Queen's Gaze, ungated), `tove-signature`
(Emergency-Crafted Bullets, own shot counter — the base build's identical
reload sits behind a probability roll instead, see below), `arcana_fortune_mate`
(the Memories and Moments rotation's reload phase, `first_shot` + `windows`).

**`attack_rate.AmmoRefill(time=T, rounds=R, percent=P)` is the sibling for a
refund at a KNOWN TIME instead of a shot counter** — "Reload 39.88%
magazine(s)" on entering Full Burst (Noir), or at the caster's own burst
(Little Mermaid, Asuka, Arcana: Fortune Mate) — for a trigger that's an event
the burst cycle already scheduled rather than a count of the recipient's own
shots, where the recipient may not even be the caster. Declare it as
`<name>_refill(values) -> {"rounds"|"percent", "scope": "self"|"squad",
"event": "full_burst_enter"|"own_burst"}` and register in `registry.
_AMMO_REFILL_GRANTS`; `raid_simulator.resolve_ammo_refills` reads the trigger
off the burst-cycle event log (`full_burst_start` events for
`"full_burst_enter"`, the caster's own `burst` events otherwise) and fans a
squad-scope grant out to every deck member. **A refill that lands while the
recipient is reloading is WASTED** — a magazine walk always opens a fresh
magazine at full capacity and a refill is capped at capacity, so one that lands
before the magazine it would join finds no room and does nothing; no special
handling needed. Consumers: `noir` (Rabbit Twins B, squad), `little_mermaid`
(Siren's Song, squad), `asuka_shikinami_langley_wille` (Annihilation State,
self), `arcana_fortune_mate` (Radiant Youth's own-burst reload, self).

What neither primitive can express: a refund gated behind a PROBABILITY roll
("There is a 5% chance of activating when attacking", `tove` base) — this
engine is deterministic and has nothing that rolls dice, so a probability-gated
trigger stays deferred regardless of what the refund itself would otherwise be
able to express. (`tove-signature` carries the identical reload on a plain shot
counter instead and is the build that's modeled.)

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

**`"full_burst_rider": [(stat, value, scope, duration), ...]`** (2026-08-16) —
buffs that come WITH a tick, but only when the TICK ITSELF lands inside a Full
Burst window. Snow White's Seven Dwarves: V & VI is the first consumer:
"Activates when **using this skill** during Full Burst. Affects self. Critical
Rate ▲ 26.1% for 10 sec." Note what is gated — the skill ticks on its cooldown
either way, so the clause gates the RIDER, not the nuke. **Do not reach for
`during_full_burst` for this shape**: that one deletes the out-of-window ticks'
damage, which the text does not say. Registered refreshing, so a spec whose
cooldown is shorter than the rider's duration cannot stack the grant with
itself. **This pass is the one that can ask the question** — it runs AFTER the
burst cycle, so `full_burst_windows` is populated; `periodic_rules` runs BEFORE
it and sees an empty `burst_times`, which is why a `time_condition` there
cannot answer "am I in a Full Burst".

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

**★ For a NORMAL ATTACK, delivery and true-damage typing are INDEPENDENT axes**
(Fienn, 2026-08-16). A rocket launcher's shot converted to true damage is still
a rocket, so it collects Projectile Explosion Damage **and** `true_damage_up`,
and ignores DEF. The single `damage_type` tag cannot say both, so
`_damage_instance` adds the weapon's delivery bucket
(`raid_simulator.weapon_delivery_type` — only RL delivers one) on top of
whatever the tag selects, for every `source == "normal_attack"` instance. Skill
damage is NOT covered: a nuke fired by an RL unit is not a projectile explosion
unless its own spec says so. Encoding a converted RL normal attack therefore
needs nothing extra — the engine already keeps both buckets.

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
times - gap #7, Asuka/Grave),
**`"every_during_ally_status_window"`** (2026-08-16, threshold=
`(N, window_duration, ally_slug)`) - the window is anchored at ANOTHER unit's
burst times, for a status a DECKMATE puts on the boss. Two things differ from
the own-status mode: the anchor, and **the count RESTARTS in each window**
(like `cycle_from_own_burst_to_full_burst_end`, unlike
`every_during_own_status_window`, which concatenates every window's shots
before counting). Restart is right when the status is REMOVED at the window's
end, so a part-finished count has nothing to carry. With no such ally in the
deck there are no windows and the rule never fires - the game's own answer,
not a silent zero. First consumer: Rei Ayanami (Tentative Name)'s "after
landing 18 normal attack(s) against a target in Anti A.T. Field status", a
status only Asuka: WILLE applies and only for her Annihilation State's 9 sec.
**The window length belongs to the ALLY, so import it from her module**
(`asuka_shikinami_langley_wille.ANNIHILATION_STATE_DURATION` / `SLUG`) rather
than restating the number - a guard test pins that constant to her skill data.
**`"every_n_critical_hits"`** (threshold=N) counts EXPECTED critical hits rather
than shots: each shot adds that unit's LIVE crit rate at its own time and the
rule fires every time the running total crosses N, carrying the remainder. The
engine never rolls a crit, so there is no "was this shot a crit" event to count -
this is the same expected-value treatment the damage path already uses (see
`_helpers.expected_shots_per_proc` for the rule that generalises it). **Do not
fold it to a fixed shot count at build time** (`N / own_crit_rate`): Fienn's
acceptance condition (2026-07-20) was that a deck's crit buffs must move it, and
a build-time constant ignores every ally buffer. Known limit: the shot loop runs
per unit, so crit buffs applied by an ALLY's per-shot rules processed later are
not reflected (burst / Full-Burst-triggered crit buffs are - that covers the
usual buffers). First consumers: EVE's Unstable Energy (44 crits), Julia:
Signature's Crescendo.
`"sequence"` (gap #10, Scarlet: Black
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
the only consumer, Snow White: Heavy Arms, uses N=1), or `"accumulate"`
(2026-08-07, Dorothy: Serendipity's Flash - the one mode that does NOT count
shots. `threshold` is `(limit, increment_at)` where
`increment_at(context, slug, time, registry, shots_since_fire) -> float` is a
per-shot QUANTITY the unit computes; the rule fires each time the running total
crosses `limit`, which is then SUBTRACTED rather than reset so the overshoot
carries forward. Use it when the skill's trigger counts something other than
shots and the per-shot amount varies - Flash's "80 pellets" is worth 10 a shot
normally, 15 while her burst's "Number of pellets +5" is up, and 1 (+5) for the
3 rounds it fixes the count at 1. The subtract-not-reset arithmetic is what
makes a second rule at 2x the limit ride every second fire of the first.
`shots_since_fire` is passed because a rule CANNOT read its own
`round_buff_rule` grant here: grants become Effects only in the pass after every
unit's shot loop, while this counter runs before it. `None` = has not fired yet,
which must not be confused with the shot right after a fire). The
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
affected ally's next N AMMUNITION-SPENDING normal attacks, not seconds — e.g.
Zwei's Pierce Equation, Miranda's Wake Up. Build with `round_buff_rule(trigger,
[(stat, value, scope_spec)], shots=N)`; it records a `RoundGrant` that
`simulate_raid` turns into a real timed Effect per affected unit (squad grants
are consumed per-ally). `scope_spec` is a static scope string or
`("top_atk", n)`. No engine param to thread — `RoundGrant`s live on the
registry. See `zwei.py` (squad) / `miranda.py` (top-1). Detail in
`special-mechanics.md` ("For N round(s) is a bullet-count duration").

**It is live from the GRANT, and it reaches skill damage (2026-08-18).** The
round count says when the buff ENDS, never when it starts, and while it is up it
covers everything the recipient does — nukes and burst damage included, not just
the bullet that spends it (Fienn, in-game). The tactic that settled it: Miranda's
"Critical Rate 85.42% for 1 round" landing on Marciana: Marine Study as Full
Burst opens, where her Flagged Target Designation nuke fires on that same
trigger and crits under it. Nothing to encode — the window is
`_round_grant_shot_window`'s job — but it does mean a same-trigger nuke on the
recipient IS in scope, which is easy to assume away.

**It ends ON the bullet that spends it, and the gap before that bullet is still
inside it.** A round buff is spent BY a bullet, so between two bullets it is
still held — which is what puts Phantom's own "Attack Damage for 1 round(s) on
every normal attack" on the burst she fires between two of her shots. But
nothing after that bullet is under it: letting the window run to the shot AFTER
the spender (as it did briefly) over-runs by a whole shot gap, which is 3.2 sec
on a recipient in a Fully Active charge window.

**A bullet's grant belongs to the NEXT bullet — pass `from_own_shot=True`**
when the caster's own normal attack is what creates the grant ("Activates when
normal attack hits … for N round(s)"). That bullet has already left, so it
neither carries the buff nor spends it; without the flag every bullet would buff
itself. **Do not infer the flag from the timestamp** — Jill Valentine's Magnum
Ammo activates on RELOADING to max ammunition and only uses the magazine's first
bullet as the marker for when, so that bullet is one of its nine. Consumers with
the flag: `phantom`, `phantom_signature`, `ein`, `d_killer_wife`,
`dorothy_serendipity`, `zwei` (Pierce Equation's per-shot bullet).

**Without a "stacks up to N time(s)" clause a round buff does NOT stack.**
`cap` left out means one at a time, not unbounded — that clause is the only
marker the text gives (Fienn, 2026-08-18), the same rule the timed-buff side
already follows. Two different bullets granting the same stat still add up:
each `round_buff_rule` instance is its own cap group.

**The cap is INSTANTANEOUS.** `_capped_round_grant_segments` resolves each
(bullet, stat) as a step function: at any moment the `cap` newest live grants
count, older ones are pushed out, and an older grant that outlives the ones that
pushed it out is held again. Do not reach for "drop a grant that `cap` newer
ones overlap" — that only agreed with the game while every window began at the
shot it covered, and once windows start at the grant they chain into each other
and it read Zwei's 3-stack Pierce Equation down to 1 on the shot it is meant to
pay 3 on.

**[Unlimited Ammunition] freezes the count (2026-08-18).** A shot fired under
the status spends nothing, so it is covered by the buff and does not tick it
down; the buff is consumed when the WINDOW ends, not one shot later (Fienn,
in-game). Nothing to do when encoding a round buff — `_round_grant_shot_window`
applies it to every one of them. What an encoding DOES owe is the other side:
if the unit you are encoding gets [Unlimited Ammunition], declare how long for.

**Unlimited-ammunition windows:** `registry._UNLIMITED_AMMO_DURATIONS[slug]` →
a function reading the seconds out of the unit's own burst slot, surfaced by
`get_unlimited_ammo_duration` and threaded to `simulate_raid` as
`unlimited_ammo_durations={slug: seconds}`. The window is anchored on the unit's
OWN BURST times, which is where every skill granting the status puts it. Census
(Fienn, 2026-08-18) — `grave` (Prediction, 10s), `nayuta` (Memory Incineration,
10s), `moran`/`moran-signature` (Fair and Square!, 10s), `modernia` (New World,
15s), and nobody else.

Two traps:
- **Read the status off the skill TEXT, never off "does this window reload".**
  Red Hood's Red Wolf swaps in a 99-round magazine that outlasts its own 10-sec
  window, so it never reloads — but her text never says "Unlimited ammunition",
  her shots still spend rounds, and a round buff on her is consumed normally.
- **It is a STATUS axis only — it does not generate shots.** Each of the four
  already models the no-reload side its own way (Grave raises `max_ammo_percent`
  past the window; Nayuta and Moran fire a segment, which never reloads), so
  wiring this into shot generation would model the same thing twice.

**Holding fire through your own Full Burst (2026-08-18):** a round buff is spent
BY a bullet, so a unit who deliberately does not fire keeps an ally's buff for
the whole window and every skill hit in it lands under that buff. Real in-game
tactic on Mihara (chain DoT + Dragging Chain), Ein (Near Feathers) and Ada Wong.
Built with `_helpers.hold_fire_segments(weapon_stats, slug, release_shots=N)`,
one segment per Full Burst the unit opened herself, read off
`context.full_burst_windows` so an extension counts. `release_shots=1` fires the
held full charge one frame inside the close (`HOLD_FIRE_RELEASE_MARGIN`) - on
the bell it would be outside the half-open window and lose the Full Burst bonus
the tactic exists to collect; `0` holds throughout.

**It is a PLAY DECISION, and encoding must not make it a unit property.**
Holding fire adds nothing by itself - it only pays by preserving somebody
else's buff - so in a deck without one it is a straight loss (measured: Mihara
−31.66%, Ein −27.39%). `registry._HOLD_FIRE_TACTICS` only says the tactic
EXISTS for a unit and how many shots she releases; switching it on is
`deck_search.evaluate_deck`'s `hold_fire`, the same category as `max_bursts`.
The chooser is `evaluate_deck_best_seating` (REPORT path, never the search hot
path), gated by `evaluate_deck_hold_fire_options`: a deck is only offered the
alternative when the ENCOUNTER allows the tactic at all AND it holds such a unit
AND somebody in it grants a round buff to an ally. The deck half of that gate
reads `SkillRule.grants_round_buff_to_allies`, set by `round_buff_rule` itself,
so a newly encoded granter is covered the day it lands rather than the day
someone remembers a table.

The ENCOUNTER half is `BossProfile.spawns_adds` (2026-08-20): against a boss
that keeps producing adds the player has to keep shooting, so the tactic is not
on the board however good the deck's buffs are — solo-40's 「사치스러운 거미」 is
the first (Fienn). It is a boss fact, not a unit one, so it lands on the boss
profile beside `part_destructible` and reaches the chooser through
`evaluate_deck_hold_fire_options(ordered_deck, boss)`. Nothing else reads it:
how much damage the adds take, and how many rounds clearing them costs, are not
modeled.

**A hold needs the unit's damage model to survive being fired ONCE.** Ada Wong
was blocked on exactly this until 2026-08-18: her Special Modification is
"Charge Speed ▼300%" + "Charge Damage ▲1500%" for 1 round, and the engine folded
the pair into a NET charge_damage_bonus (15/4 − 1 = +2.75) because a 1-round
charge-speed grant can never reach the magazine boundary where charge speed is
sampled. That approximation pays the ×4 time cost in FEWER SHOTS - which is
exactly what the tactic stops doing. The fix was to stop approximating: a
one-shot SEGMENT states its own charge time, so both halves land (4.0 sec charge,
250% + 1500% = 1750% Charge Damage, `until_shots: 1` = "for 1 round(s)").

**When a hold-fire unit already has a weapon-mode segment, the hold REPLACES
it** - and she has to say so, by declaring the released shot in
`registry._HOLD_FIRE_RELEASE_PROFILE_BUILDERS`. Ada's held charge IS her Special
Modification shot: the damage comes from that profile, the timing from the hold.
A transforming unit with no such declaration raises rather than being resolved
by guess.

**A one-shot segment is the general answer to "for 1 round(s)" that has to
change CADENCE, not just damage.** A round-count buff on a stat the shot loop
samples per magazine (charge speed, attack speed, max ammo) can never land from
a `round_buff_rule` - the grant lives inside a magazine, the sample happens at
its edge. Declare the shot instead.

**Highest-final-ATK top-N targeting:** for "N allies with the highest final
ATK". `highest_atk_buff_rule(trigger, n, [(stat, value, duration), ...])`
applies timed buffs to the top-n; `round_buff_rule(..., ("top_atk", n))` does
the bullet-count variant. Both resolve via `SquadContext.top_atk_slugs(n,
caster, registry, time)`, which ranks by LIVE final ATK at application time (so
an earlier same-cycle ATK buff is reflected) and emits a `slugs:` scope.
`raid_simulator` injects each member's base ATK into the context. See
`miranda.py`.

Two axes on top of the ranking, both read off the bullet's own wording:
- **`include_caster`** (default False) - whether the caster competes for the
  slots. False is Miranda's/Mana's/Soda's "(except caster ...)"; True is a
  bullet with NO such clause (Maxwell, Leona, Naga). Getting it wrong is
  invisible, so check the clause per bullet - see `special-mechanics.md`,
  "Does the caster compete".
- **`member_filter(member) -> bool`** - narrows the CANDIDATES before ranking,
  for a bullet that is a weapon/element class AND a top-N at once ("the 2 ally
  unit(s) with shotguns who have the highest final ATK", Leona). It applies to
  the caster's inclusion too, so a caster outside the class never takes a slot.
  Do NOT re-derive final ATK in a unit module to combine these yourself - a
  second copy of the formula drifts silently (Maxwell carried one from
  2026-07-19 until this landed).

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
at HER burst, not the squad's Full Burst start),
**`("per_shot_every_during_own_status_window_by_ally", N, window_duration,
ally_slug)`** (2026-08-16) = the window is still the OWNER'S, but the shots
counted are the NAMED ALLY'S, and the count RESTARTS in each window. For a
resource one unit holds and another unit's kit writes into: Rei Ayanami
(Tentative Name)'s "Anti A.T. Field stacks ▲ 10" every 18 of HER normal attacks
against the status ASUKA put on the boss. An ally who is not in the deck has no
shot times, so the source contributes nothing on its own. **The owner's `cap`
still clamps the merged total** (`resource_count` takes `spec.cap`), which is
what stops a +10-a-time source running past the 30 the holder's skill states.
See "Writing into an ally's resource" below for how the source gets there.
**`("per_shot_every_by_ally", N, ally_slug)`** (2026-08-17) = the windowless
version of that: every Nth of the NAMED ALLY'S normal attacks, for the whole
fight, with no dependence on the owner's own shots or on any status. Flora's
Petunia, "activates after landing 100 normal attacks ... increases the stack
count of stackable buffs by 1", which her Electric allies hold. Same two
properties: an absent ally contributes nothing, and the owner's `cap` clamps.
`("per_shot_every_outside_own_status_window", N, window_duration)` = that
window's MIRROR, counting only shots OUTSIDE it (Laplace's Hero Vision, fed by
Full Charge attacks: during her Buster transform her weapon is not a charge
weapon at all, and those transform ticks sit in `shot_times` right alongside her
ordinary shots - **do not reach for the outside-Full-Burst kind instead**, the
two windows start together but need not END together, so a 5-sec transform
inside a 10-sec Full Burst would silently drop five seconds of genuine shots),
`("per_shot_every_outside_full_burst", N)` = the mirror of the Full Burst kind,
counting only shots outside any Full Burst window (closed on BOTH ends, so a
shot landing exactly on a boundary counts as inside),
`("per_shot_cycle_from_own_burst_to_full_burst_end", first, period)` = fires at
the `first`-th shot of each own-burst-to-Full-Burst-end window and every
`period` after, with **the count restarted in each window** - that restart is
the whole difference from `per_shot_every_during_own_status_window`, which
concatenates every window's shots before counting (fine for a status whose
stacks reset anyway, wrong for a phase rotation),
`("per_critical_hit_every", N)` = +1 stack per N EXPECTED critical hits with
normal attacks, which needs the owner's LIVE crit rate rather than a shot index
(Julia: Signature's Crescendo), `("at_battle_start",)` = a single fill at t=0,
`("on_full_burst_end_after_own_burst",)` = at each Full Burst end that follows
the owner's own burst (Mihara's Restraint Chains), `("on_last_bullet",)` = +1
stack every time the owner's OWN shot empties its magazine (Julia's
Crescendo, "Activates when the last bullet hits the target" - see
`attack_rate.last_bullet_shot_times`, not any fixed shot count or window),
or `("squad_burst_cycle_conditional", [(event_pred,
gate_fn, delta), ...])` = a stateful walk over the GLOBAL burst-cycle event log
(not the owner's own shots), applying `delta` at each event where `event_pred`
matches AND `gate_fn(current_count)` is true (Maiden's MP: "+1 if MP==0 on any
squad member's Burst Stage 1", "+1 if MP>=1 on Full Burst enter" - see
`_resolve_squad_burst_cycle_resource` below). `buffs` are `ResourceBuff`s built with `linear_resource_buff(stat, per_stack,
scope)` (value = per_stack × count) or `leveled_resource_buff(stat, per_level,
level_fn, scope)` (value = per_level × level_fn(count), for a Hero-Level-style
tier); an arbitrary `value_fn` is allowed for a threshold buff.

**The stack's clock is on the SPEC, not on its buffs** (`lifetime` +
`lifetime_refreshes`, hoisted 2026-08-17). The game gives a stack one clock, so
everything reading the count shares it — the buffs AND the gates that gate a
nuke or a damage typing on it. Two consequences worth knowing: a resource with
NO buffs at all can still carry a lifetime (Laplace's Hero Vision exists only to
answer a gate, and there was nowhere to put its clock while the field lived on
`ResourceBuff`), and two bullets whose durations really do differ need a
resource EACH rather than two buffs on one (Centi's 8-sec ATK and 10-sec
elemental stacks share a counter only because neither can lapse at her cadence;
`build_field_discussion_resources` raises if their caps ever diverge).
`simulate_raid` registers every spec on the context before anything can query a
count, so the count itself is a function of time —
`SquadContext.resource_count(slug, name, time, cap)` — never a mutable total,
and never a per-call-site opinion about when the stack died. The resolution pass emits each buff as a STEP FUNCTION
of delta Effects over the fill/expiry events, so `total_for`'s running sum equals
value_fn(count) at every time. First consumers: `modernia.py` (timed capped),
`guillotine_winter_slayer.py` (permanent + leveled + core-conditional),
`cinderella.py` (periodic fill), `laplace.py` (outside-own-status-window).

**READ THE CLAUSE BEFORE PICKING A LIFETIME.** "stacks up to N time(s) and
lasts for D sec" is NOT N independent D-second timers. It is ONE timer the
whole stack shares, and every new stack restarts it (the Raven ruling, Fienn
2026-07-17; re-confirmed in the range on Maiden: Ice Rose 2026-08-17). So:

- **Fills faster than D → the count reaches the cap and holds.** The chain can
  only break on a gap LONGER than D. If the unit's own cadence never leaves
  such a gap, `lifetime=None` (permanent accumulation) reproduces the game
  exactly, and that is the encoding to use - `leona.py`, `centi.py` and
  `rosanna_signature.py` all say so in their docstrings, with a test asserting
  the inequality (a gap wider than D turns the test red).
- **Only reach for a numeric `lifetime` when the count really does decay** -
  a fill source that stops (a window closing, a transform taking the weapon
  away). `ResourceBuff.lifetime_refreshes` is the flag for "timed, but the
  whole stack shares one clock"; plain `lifetime` means per-stack expiry, which
  is the rarer reading and the one to justify in the docstring.
- **"stacks up to N ... continuously" is the permanent one** - that word is the
  discriminator (Guillotine's EXP, Soda's Golden Chip, Cinderella's Beautiful).
- Arithmetic of the shape "the cap can't bind, the cycle is longer than the
  buff" is the tell that per-stack expiry was assumed. It was wrong on eight
  encodings; `scripts/audit_stack_lifetime_refresh.py` censuses every bullet
  pairing a cap with a duration and measures what the reading is worth.

**Writing into an ALLY's resource** (2026-08-16). A skill can add stacks to a
resource another unit owns - Rei Ayanami (Tentative Name)'s "Anti A.T. Field
stacks ▲ 10" fills Asuka: WILLE's counter. The stacks belong to the HOLDER
(their `cap`, their consumers, their reset), but the numbers belong to the
WRITER's skill data, so the writer declares a CONTRIBUTION and `roster` merges
it onto the holder's spec:

    registry._RESOURCE_CONTRIBUTION_BUILDERS[slug] -> [
        {"target": holder_slug, "resource": name, "fill": <fill kind>, "amount": N},
    ]

`roster._merge_resource_contributions` appends `(fill, amount)` to the target's
`ResourceSpec.fill`, promoting a single-source spec to the list form.
**A contribution whose target is not in the deck is dropped** - the stacks have
nowhere to land, which is what the game does when you field the writer without
the holder. **The cap is never widened**, so the merged total still clamps to
what the holder's own skill states; check that before assuming a contribution
does anything, because a holder who already pins their own cap gives it no
headroom (measured for exactly this pair - see `docs/roadmap.md`).

A bullet that names no target uses `"target_filter"` instead of
`"target"`/`"resource"`, and the merge resolves it against the LIVE deck
(2026-08-17):

    {"target_filter": {"element": "Electric", "stackable_buff": True},
     "fill": ("per_shot_every_by_ally", 100, writer_slug), "amount": 1}

Both keys are matched exactly. Flora's Petunia is the consumer: "affects all
Electric Code allies. Increases the stack count of stackable buffs by 1."

**`ResourceSpec.stackable_buff` is what the second key reads, and it is
DECLARED, never inferred.** It means "this resource is a stacking BUFF in the
game's sense" as opposed to a gauge or counter the engine merely models the same
way. No property of the spec separates the two - Maiden: Ice Rose carries both
at once and takes Flora's +1 on her Meditation stack but not on her MP (Fienn,
range test 2026-08-17). Set it from evidence, not from the shape of the spec.
Holders declared so far: `cinderella.beautiful`, `maiden_ice_rose.meditation`,
and `zwei-signature.pierce_attacks_101` (a Favorite-Item bullet - the base Zwei
has no such stack at all, so measure against the signature build).

What such a bullet raises is the CURRENT count, not the cap (Fienn, 2026-08-16),
so it only pays where a real counter sits below its cap - a stacking buff the
engine already approximates at its steady-state maximum gains nothing from it.

**`("computed", fn)` hands the walk to the owning module** - `fn(shot_times)`
returns the fill times. For a resource whose sources INTERACT: where one
source's next fill depends on when the resource was last spent, per-source
schedules are not independent and cannot be merged after the fact. Its
reset-side partner is `{"trigger": "computed", "times": fn, "value": X}`, and
both sides should come from ONE walk in the module so they cannot disagree
about when the resource emptied. First consumer: Phantom's Thief's Dagger
(`phantom_signature.dagger_timeline`) - spending it strips Calling Card, which
is the very condition re-arming its other source.

**Reach for it only when the interaction is real.** A resource whose sources are
independent belongs on the declarative kinds below: those the engine can reason
about, and no unit can get subtly wrong. Everything after the walk is still the
engine's - `resource_count` replaces its baseline at each spend and expires each
fill on its own clock, which is exactly a self-consuming sawtooth, so a module
that reaches for `computed` should still be handing over times and nothing else.

**A resource may have MORE THAN ONE fill source.** In place of a single fill
spec, `fill` takes a **list of `(fill spec, amount)` pairs**, each running on its
own schedule and granting its own amount - Mihara's Ensnaring Chains is +10 per
chain discharge and +1 per 40 normal attacks during Full Burst. `_fill_sources`
normalises the two shapes, so a bare spec is just sugar for `[(spec, 1)]`. Every
source's times are computed independently and merged before the count is read.

**So "multi-source stacks" is NOT a gap** - together with per-stack expiry
(`lifetime`, below), `cap`, and `resets`, most of what reads like a
"time-decaying gauge" in skill text is already expressible. What genuinely is
NOT: a resource that **consumes itself on reaching its cap** (no reset trigger
fires on "count reached cap"), and - the harder half - one whose consumption
changes when ANOTHER source can fill, since sources are scheduled independently
and merged after the fact rather than walked in order. Phantom's Favorite Item
dagger is the live example; see `docs/engine-gaps.md`.

**Before recording any of this as deferred, check THIS file, not a module
docstring.** A deferral note is a claim about the engine on the day it was
written. The catalog listed 7 of 13 fill kinds and no multi-source form until
2026-08-14, and in the meantime a five-slug "Pattern B" gap sat open for
capabilities that were four of them already built.
`tests/test_capability_catalog_is_current.py` fails if a fill kind or reset
trigger is added without landing here.

**Resource resets (value REPLACED, not incremented):** for a resource that gets
set or spent rather than only ever accumulating - e.g. Soda's Golden Chip,
starting the fight at its 50 cap and spending 17 at each of her bursts.
`ResourceSpec` takes an optional `resets` field: `[{"trigger":
"battle_start"|"own_burst"|"own_burst_delayed"|"full_burst_end"|"computed",
"value": X, "delay": seconds (own_burst_delayed only), "times": fn("computed"
only)}, ...]`. `full_burst_end` fires at
each Full Burst's end whoever opened it (Arcana: Fortune Mate's Happy Memories,
cleared there by Keepsake Album's own third bullet) - distinct from
`own_burst_delayed` with a 10 sec delay, which lands one burst-ordering beat
early and would cut the window's last shots short. Resets from every spec are
replayed in TIME order, so each one's pre-value reflects the fills AND any
earlier reset already applied. There is no declarative "on reaching cap"
trigger - a resource that empties itself at its cap uses `"computed"` (above),
where the module's own walk decides the spend times.

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

**Holding a unit's burst back — `burst_delay` on the deck entry.** For a unit
whose burst is not simply "ready when the cooldown says so". `burst_cycle`'s
member dict takes an optional `burst_delay`, and all three forms fold into one
ready-time (`_ready_at`), so tier selection and eligibility keep the same
arithmetic:

- `{"skip_cycles": N}` — out of the opening N cycles. Diesel: Winter Sweets'
  Highlight needs a cycle to pass before the status is settled, so a static slug
  would over-credit it.
- `{"not_before": T}` — held until T seconds.
- `{"min_interval": S}` — stretches the EFFECTIVE cooldown to S. Elegg: Boom and
  Shock uses `not_before` 78s + `min_interval` 54s, both derived from her own
  fill values.

**The trap: `min_interval` measures from the ACTUAL fire time (`last_fired_at`),
not the CDR-rewound `last_used_at`.** It stands for a resource filling on wall
clock, and a wall-clock resource does not fill faster because an ally cut the
cooldown. A delayed unit alone in its tier would stall the cycle, but
`ALLOWED_SHAPES` puts at least two units in Burst 3, so search never hits that.

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

That loop now iterates a SECOND quantity to the same fixed point: the
`flat_max_hp` written after the burst cycle, which the "ATK ▲ X% of Max HP"
conversion needs and could not otherwise see (see `flat_max_hp` below). The pass
count in `full_burst_passes` counts passes of the whole loop, so it covers both
axes; a deck that needs neither still resolves in exactly one pass.

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

**`"fire_delay"` (optional, seconds) moves the whole tick train later**, for a
rider that rides the burst's own HITS rather than landing with the cast. Absent
= 0.0, so every spec written before it keeps landing exactly where it did. Use
it only with a MEASURED gap - it is not a place to guess a plausible delay.
First consumer: Cinderella's Glass Slippers riders, whose ten hits start 0.95
sec after the cast and are 0.200 sec apart (Fienn, 2026-08-15). Two things
follow from the delay and are the reason it exists: each tick reads the
resource at a different instant (bursting at zero Beautiful stacks, exactly the
four riders landing after the first stack arrived deal damage), and the ticks
sit INSIDE the Full Burst window the cast opened, so they collect its bonus
while the burst bullet - computed at the cast, one beat before the window -
does not. Do not reach for it to model a burst bullet's own sequential hits:
those are settled at the cast and `burst_hit_counts` records them there on
purpose (see below).

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
"core_eligible"(optional), "resource_gate"(optional)}`; wire via
`_SCHEDULED_NUKE_BUILDERS` / `get_scheduled_nukes`, threaded by `roster` into
`simulate_raid`'s `scheduled_nukes` param. Times at or past `fight_duration` are
dropped. Logged with `source="scheduled"`.

**`resource_gate` gates or scales each tick on a named resource, read at that
tick's OWN time** - the same 3-tuple `(name, cap, scale_fn)` that
`resource_scaled_nukes` uses (it names no lifetime: the count comes back on the
resource's own registered clock), and the recorded `percent` is multiplied by
`scale_fn(count)`. Use `lambda count: 1.0 if count >= cap else 0.0` for a
binary "while the stack is at max" gate (Laplace's 11.9% true-damage rider),
or `lambda count: count` to scale with the stack. This resolves in **phase 2**,
after the resource pass, which is why it can read a counter that the schedule
itself could not: schedules run while the shot timeline is still being built.

**A `weapon_mode_schedules` profile can carry the SAME 3-tuple as
`damage_type_gate`** (2026-08-16) — the segment's `damage_type` then applies
only where the gate is open. The profile is still fixed when the segment is
built, so the gate rides the `ShotRecord` and phase 2 answers it at each shot's
own time. A tick whose gate is shut is **not untyped**: it falls back to what
its weapon delivers (`weapon_delivery_type`), i.e. exactly the type an ungated
shot of that weapon would carry, and pays DEF like one. First consumer is
Laplace: Signature's Buster, whose Additional Effect 2 reads "normal damage is
applied as true damage **when** Hero Vision is at max stacks" — it reuses
`hero_vision_max_stack_gate`, the same tuple her 11.9% rider passes as
`resource_gate`, so one counter answers both paths. **`core_eligible: True` opts one
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
**A unit's BASE weapon may fire at a rate its class does not (2026-08-15).**
`attack_rate.RATE_OF_FIRE_60FPS` is per weapon class, and every one of its four
entries falls out of `rounds_per_second(rpm)` = `60 / ceil(60 / (rpm/60))` —
the game data's rounds-per-MINUTE put on the 60fps grid (AR 720→12 · SG 90→1.5 ·
SMG 1440→**20**, its 2.5-frame interval rounding up to 3 · MG 4200→**60**, its
0.857 rounding up to 1, which Fienn's 256-rounds-in-256-frames reading confirms
independently). A unit whose own rpm differs is listed in
`attack_rate.ROUNDS_PER_MINUTE` and `user_roster` joins it onto that unit's
`weapon_stats["rate_of_fire"]`, which `rate_of_fire_for_profile` prefers over
the class constant; ABSENT means "the class rate is right", so an ordinary unit
is untouched. Today the table holds one slug — Jill: Valentine's 9-round AR
fires 150/min, not 720, and the class constant made her normal attack **4.8x**
(Fienn read 24±1 frames between her rounds, 2026-08-15). Do NOT hand-add a slug:
the field lives only in ShiftyPad raw bundles keyed by rid (dotgg, where most
units' weapon stats come from, has no rate field at all), so
`scripts/audit_rate_of_fire.py` is what decides membership by comparing every
encoded slug against the collected data.

**A charge weapon's rpm is a FLOOR, not a cadence, and `input_type` decides
which units have one (2026-08-15).** RL/SR units never read
`RATE_OF_FIRE_60FPS` — their cadence is `charge_time` plus the unit's own
fire-to-charge pause. `shot_detail.input_type` splits the 31 collected charge
weapons cleanly and explains both facts at once:

- **`UP` (26 units)** — fires on RELEASE. You let go to shoot and must press
  again to start charging, so there is a fire-motion→charge-motion **pause**
  (all 11 timed so far are nonzero). Their `rate_of_fire` is 60 for every one
  of them and nobody reads it — it is a placeholder.
- **`DOWN_Charge` (5 units)** — charges and fires while the trigger is HELD.
  Never releasing means **no pause** (four measured at zero), and the loop's
  own speed becomes the floor instead: Laplace: Ultimate Hero and Neon: Vision
  Eye 300/min, Liberalio 200, Cinderella 180, Anis: Star 120 — 12, 12, 18, 20
  and 30 whole frames.

So a pause and a rate-of-fire floor are ALTERNATIVES, not layers (applying both
counts the same wait twice). The floor lives in
`attack_rate.CHARGE_ROUNDS_PER_MINUTE`, joined onto the timeline by `roster` as
`charge_interval_floor` and read by `shot_interval_with_speed`'s
`interval_floor`. The class default 60/min is deliberately absent from the
table — Scarlet: Black Shadow carries it and fires every 0.7325 sec — so a unit
not in the table has no floor but the frame grid.

**Encoding a new charge weapon: read `input_type` first.** It classifies her
before anyone times her — `DOWN_Charge` means zero pause plus her own rpm,
`UP` means a pause (carry `ASSUMED_CHARGE_MOTION_DELAY_SECONDS` until Fienn
times her). `scripts/audit_rate_of_fire.py` checks both implications in both
directions, so a unit that breaks the pattern is the first counterexample and
shows up as a failure rather than passing quietly. It is still a floor and not
a cadence: reading these rpm as sustained fire rates would put Liberalio at
~2.2x of her recorded damage, Neon ~1.95x, Anis: Star ~1.40x.
`registry.INFERRED_NO_CHARGE_MOTION_DELAY` holds the one zero that comes from
this rule rather than from a clock.

**Tap-fire (톡톡이) — a partially charged shot, 2026-08-19.** A player can release
an `UP` weapon the instant the charge starts. Fienn's range readings settled what
that shot is (docs/measurements/alice-tap-fire.md):

- **Damage is exactly the charge gauge percentage the HUD displays**, which
  starts at 100% BEFORE any charge and rises linearly to the weapon's Full Charge
  Damage. Eight readings fit `damage / gauge%` to within 0.4%, all of it explained
  by the displayed integer rounding. So a partial charge is neither "no bonus
  unless full" nor "proportional from zero" — it is 100% plus a linear ramp.
- **A tap fires at gauge 103%, not 100%** (2026-08-20 correction). Gauge 100% is
  the "not charged" state and firing does not go off there; 103% is the lowest
  gauge a shot has ever been observed at
  (Fienn, `docs/measurements/bready-charge-damage.md`).
  `attack_rate.TAP_FIRE_CHARGE_BONUS = 0.03` is that
  floor. This also settled a second question the same reading answered: **a
  tapped shot does not receive the Charge Damage buff** — Charge Damage
  multiplies a FULLY-CHARGED shot and nothing else. The nikke.gg damage-formula
  glossary only says the buff belongs to a charge weapon's normal attacks in
  general (silent on tap vs. full charge); the FULLY-CHARGED-only restriction
  is Fienn's Brady reading above, not the glossary — the engine had been
  multiplying it onto every charge-weapon shot regardless. Raising Charge
  Damage from 7.59% to 11.11% on
  the same account moved the damage of an identically-gauged shot by only
  +0.06% (a direct multiply would have moved it +3.27%). `raid_simulator`
  therefore adds `charge_damage_bonus` for a full-charge `ShotRecord` but not
  for a tap (`is_tap_fire`) one; skills that grant Charge Damage (Alice's
  Energizing Carrot, e.g.) are unaffected in how they are modelled, only in
  which shots the bonus is allowed to land on.
- **Its interval is a separately measured value, not derivable from the
  pause** — `registry.TAP_FIRE_INTERVAL`, joined onto the timeline as
  `tap_fire_interval`. For a while this slot held "the tap interval IS the
  pause", because Alice's two readings sit on the same 15-frame grid step
  (tap 15.38f, pause 14.75f). **Milk: Blooming Bunny broke that rule,
  2026-08-19-20**: her pause is 21.889 frames (n=9) but her tap interval is
  14.810 frames (n=21) — about 16σ apart. Applying Alice's reading to Milk
  would undercount her tap-fire shot rate by 32% (her true rate is 1.48x that
  estimate).
  **Ein found the reason, 2026-08-20** (docs/measurements/ein-tap-fire.md): the
  two tables measure two different INPUTS. `TIMED_CHARGE_MOTION_DELAY` holds
  AUTO-fire pauses — deliberately, because the player works only one of five
  seats by hand — while a tap interval is by definition a manual value. Ein
  timed both on one account: **auto pause 22.524f, manual pause 14.143f, tap
  interval 14.826f.** So Milk's 16σ is auto-vs-manual rather than a fact about
  her, and Alice's agreement was not a coincidence — hers is the table's one
  manual entry, correctly so, because she IS a tap-fire candidate. The two
  tables still have to be kept apart; what changed is **what you must measure**
  for a new candidate: her MANUAL pause, not her auto one.
  A slug absent from the table
  still falls back to the pause (`get_tap_fire_interval` returns `None`,
  `_base_shot_records` substitutes `motion_delay`) — the old behaviour, not a
  new default, and it is only ever safe to READ, never to assume, that the two
  agree.

- **"Tap fire" names the INPUT, not the multiplier — a fast enough charge speed
  makes the same input produce a FULL charge.** Alice is where the two axes come
  apart: inside her burst window the charge is driven to **0 frames** (Wonderland
  80.15% + overload 8.96%, then Skill 1's caster-based 0.17505 sec erasing the
  remainder), so a tapped trigger already reads 383%. The engine expresses this as
  "full charge wins here": with a zero charge, the tap and the full charge take the
  **same** interval (the 15-frame pause), so `tap_fire_wins` picks the larger
  multiplier. Probed across her charge-speed conditions (2026-08-20): she scores
  all-full-charge in every one of them at stock reload, and still all-full-charge
  inside the burst window even in a deck that removes the reload entirely — that
  deck taps only OUTSIDE the window. **So the 103% floor never understates her**;
  had the engine tapped that window it would have scored 1.03 instead of 3.83.
  It also means the UI's "always tap fire" copy does not contradict the engine
  scoring full charges there — the copy describes the hand, the engine computes
  the multiplier.

**Only the two endpoints can ever be optimal — for a single magazine fired in
one mode.** Damage is linear in the hold and the interval is that hold plus a
constant, so `multiplier(h) / (h + delay)` has a derivative whose SIGN does not
depend on h. Full charge or bare tap; nothing between. `attack_rate.tap_fire_wins`
is that comparison, and because it closes in one expression there is no search.
It still answers the whole-magazine, no-window case correctly (see below), and a
test pins the two functions as equivalent there.

**A magazine can MIX the two ends, 2026-08-20.** `tap_fire_wins` only compares
"all full charge" against "all tap" for the WHOLE magazine — correct when
nothing else is at stake, but Milk's full charge also refreshes a state
(`has_pierce`, 6 sec) that a magazine fired entirely as taps would let lapse.
`attack_rate.optimal_full_charges` generalizes the same monotonicity argument
along a second axis: efficiency as a function of `k` (how many of the
magazine's `C` shots are full charges) is still of the shape `(p + ak) / (q +
bk)`, hence monotone in `k`, so picking the best `k` is a plain sweep over
`0..C` rather than a search. `full_charge_positions` spaces those `k` shots
evenly through the magazine (index 0 is always included — the post-reload
"첫 탄 풀차지" behaviour Fienn measured), and `mixed_charge_round_offset` turns
that placement into the cumulative shot-by-shot timeline `_base_shot_records`
actually walks — the two modes are interleaved WITHIN one magazine, not chosen
per-magazine.

**The recall window is a constraint on `k`, not a separate search, 2026-08-20.**
`registry.FULL_CHARGE_WINDOW` (joined onto the timeline as `full_charge_window`)
is for a unit whose full charge grants something with a lifetime that must be
kept alive, not just extra damage — Milk's 6-sec Pierce window is the only
entry so far. With it set, `optimal_full_charges` rejects any `k` whose worst
gap between consecutive full charges — `(charge + delay) + (ceil(C/k) - 1) *
tap + reload` — exceeds the window, then picks the highest-efficiency survivor
among the rest. **If no `k` survives, it falls back to `k = C`** (every shot
full charge), the cadence that revisits full charge most often; that fallback
is a "best available", not a guarantee — a single reload longer than the
window still loses it, and then it is the GAME losing the window, not a bug in
this function (`backend/scripts/audit_milk_tap_fire.py` flags any magazine
whose worst gap between full charges exceeds the window — it does not
distinguish a loss the model could have avoided from one the game itself
forced). A unit with no
`full_charge_window` (Alice — her Pierce is HP-gated, not refreshed by
charging) carries no such constraint and `k=0` (an all-tap magazine) is a
legal answer for her.

**Which cadence wins is still the DECK's answer, not the unit's.** The tap
empties the magazine far faster, so the reload pays for it — and a deck that
removes the reload removes the cost. The same Alice therefore full-charges
inside her own burst window (charge speed makes the full charge nearly free)
and taps outside it when reloads are fast. `_base_shot_records` re-decides `k`
once per magazine, the same granularity at which charge speed is already
sampled, and stamps the chosen bonus onto each `ShotRecord`.

Opt in with `registry.TAP_FIRE_CANDIDATES`; `roster` joins it onto the timeline
as `tap_fire`, plus `tap_fire_interval` and `full_charge_window` when the slug
declares them. Two things gate membership:

- **The unit needs a measured pause.** A zero `get_charge_motion_delay` means
  an unmeasured tap interval falls back to zero too and taps infinitely fast.
  `tests/test_manual_tap_fire.py` pins it.
- **A stand-in pause is not good enough** when the verdict is close, and the
  tap interval needs its OWN measurement rather than riding on the pause (see
  above). Milk: Blooming Bunny is in — pause 21.889f (n=9, measured 2026-08-15)
  and tap interval 14.810f (n=21, measured 2026-08-19). Her pause reading is an
  AUTO one and **a candidate is played by hand**, so it was the wrong regime for
  the full charges her mixed magazine still fires; since her manual pause is
  unmeasured she now carries Ein's manual-equivalent 17.643f via
  `registry.TAP_FIRE_MANUAL_MOTION_DELAY`, which moved her steady-state DPS
  160.5569 → 163.0417 and her tap-fire gain 10.76% → 7.74% (the cadence choice
  does not move — her Pierce window forces one full charge per magazine).
- **A candidate needs a MANUAL pause, and that table overrides the timed one.**
  `TAP_FIRE_MANUAL_MOTION_DELAY` is last in the `_CHARGE_MOTION_DELAY` merge for
  exactly that reason: an auto reading is a real measurement of the wrong input.
  Alice is absent from it because hers was manual from the start. What goes in
  is `shot gap - FILE charge`, not the measured delay — the 3.5-frame gap
  between them is the player's eyes-on-the-gauge reaction, and a tap has no such
  term (nothing to watch), which is why a candidate's two numbers stay apart
  (Milk: 17.643f pause against a 15f tap interval).
- **Measuring her is not the same as admitting her.** Ein was the obvious next
  candidate (same SR weapon) and was fully timed on 2026-08-20 — and she stays
  OFF. Her Feather Shot grants herself Charge Damage on every Full Charge, so
  **her full charges renew their own buff and a single tap breaks the chain**
  (measured: full → tap → full reads gauge 343% → 274%). Full charge wins by
  4.1% with the chain up and 44.8% inside her burst; the unbuffed state where
  taps win exists only on the fight's first shot. Her verdict is also violently
  capacity-sensitive — the flip point runs 30.19f at 6 rounds, 21.14f at 8,
  15.70f at 10 — so it would differ between accounts.

**Do not read a mode flip as instability.** The engine returns the max of two
options, so the damage is continuous even where the reported mode is not — for
Alice the two are within 5% at the default cube's reload speed, and the
collectible's charge-damage multiplier alone flips which one is named.

**Closed (2026-08-20): a tap is modelled at 103%, not 100%.** This used to read
"a tap is modelled at exactly 100%, which understates it by 3-7%" — Alice's
104%/107% readings were misread as a loose hand banking a slice of the ramp
above a 100% floor. They were actually a loose hand above the 103% firing
threshold itself (see the tap-fire section above); the "3-7% understatement"
was really the model's floor being 3 points too low across the board, not
noise from an unsteady trigger finger.

**Charge speed reaches this decision through more than one door.** Alice is the
worked example: her own burst's `charge_speed_percent` (+80.15%) cuts 80 of her 90
frames, and her Skill 1's CASTER-BASED `charge_time_reduction_sec` (0.17505 sec =
10.5 frames, which she is eligible for herself) erases the rest — so inside her
Full Burst the charge is **zero**, not the 10 frames the percentage alone implies.
Do not re-derive a unit's effective charge by hand when explaining a result; spy on
`shot_interval_with_speed` and read what the magazine actually got.

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

**A segment that fires nothing IS an ammo dump + forced reload.** A segment
boundary is this engine's "discard the magazine, resume with a fresh one", so a
window that emits no shots models "Removes N% of ammo" + "forced reload"
exactly, and a zero-length segment models an instant full reload. Two idioms,
both already in production: `milk_blooming_bunny.py` (a
`reload_time_with_speed`-long window whose profile's interval is twice the
window, so no shot fits, and `damage_percent: 0.0` so a boundary shot would be
harmless anyway) and `scarlet_black_shadow.py` (zero length, for Asura's
"Reload 100% of the magazine(s)"). Use an explicit `rate_of_fire` profile, never
`charge_time`: an explicit-rate profile takes NO cadence buffs by contract, so
an ally's Charge Speed cannot shrink the empty window and leak a shot into it.

Do NOT reach for a segment when the window must keep the unit's LIVE cadence
buffs - the same contract that makes an explicit `rate_of_fire` safe here also
freezes attack speed. "Unlimited ammo for a window on the unit's own weapon" is
that case: raise `max_ammo_percent` for the window instead (see `grave.py`'s
`unlimited_ammo_percent`). A weapon MODE swap
that happens to be unlimited-ammo is different, and a segment is right there
(see `moran`'s Fair and Square).

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

**The same instant is a measurement, not a shortcut.** The hits DO land apart
in game - Cinderella's ten span 1.80 sec, starting 0.95 sec after the cast
(Fienn, 2026-08-15) - and they land inside the Full Burst window her own Burst
3 cast opened, yet the range test reads no Full Burst bonus on them. So the
volley's damage is settled at the cast, and recording every hit there is what
reproduces it. Do not "improve" this by spreading the hits over their real
landing times: that hands them a bonus the game does not pay. A rider that
genuinely resolves per-hit is declared separately, with `fire_delay` on a
`resource_scaled_nukes` spec.

**Record-then-compute:** `simulate_raid` RECORDS every damage instance
(burst/instant/periodic/per-shot nukes + normal attacks) as an event during
phase 1 (which only applies buffs), then computes them all in a phase-2 pass
against the final registry. So a buff applied late in the fight (e.g. a per-shot
squad debuff) correctly raises a burst nuke that fired earlier. Safe because
effects are added with `applied_at >= their time` and `truncate_open_ended`
mutates in place, so deferring computation never changes an existing value.

`EffectRegistry.truncate_open_ended(stat, source_slug, now, refresh_group=None)`:
for a continuous (`duration=None`) buff that a LATER trigger explicitly cancels
(not a timer) - e.g. Grave's Heat Emission ends when she reuses her burst. Add
the effect open-ended when it activates; call `truncate_open_ended` in the
canceling trigger's rule to close its duration to the elapsed time. Replay-safe
(mutates the stored Effect, so later queries at any time see the correct window).

**Pass `refresh_group` when the unit holds MORE THAN ONE continuous buff on that
stat** (2026-08-13). Without it every open effect sharing (stat, source_slug) is
closed, which is right for Grave and Arcana but deletes a permanent bullet that
happens to share the stat: Queen (Makoto Nijima)'s Nuke Boost is permanent and
"cannot be removed" while her Nuke Amp names Full Burst end as its deactivation,
and both are Elemental Advantage Attack Damage. Name the cancelable one's
Effects with a `refresh_group` and close by that name. It is the same key
`add_refreshing` already requires, for the same reason - telling one unit's
bullets apart on a shared stat.

## Stats the engine does NOT consume (encoding is inert — defer instead)

Two groups. In both, encoding an effect with these stats is silently inert —
tests can still pass (the effect registers and `total_for` returns it), but the
value never reaches `calculate_damage`, so it does NOT change simulated damage.

**Not a damage concept at all** — no consumer will ever exist without a bigger
model: `shield_amount` and anything HP/heal/DEF/survivability. Defer these;
if a Nikke's contribution is mostly these, say so — a thin encoding is honest.

**`burst_gauge_fill_speed_percent` is NOW consumed (2026-08-22)**, closing the
gap the 2026-08-21 gauge-as-deck-property change opened: gauge fill is computed
per deck from the deck's own shot timeline (`burst_gauge.fill_times`, fed back
through `simulate_raid`'s fixed point), and `fill_times`'s `speed_multiplier_at`
argument — `(slug, time) -> multiplier`, per-SHOT rather than a single scalar —
is what reads this stat. `raid_simulator` wires it as
`lambda slug, time: 1.0 + registry.total_for("burst_gauge_fill_speed_percent",
target_for(slug), time)`, so ordinary `registry.add`/`total_for` semantics
apply: scope decides who benefits (`"squad"` reaches every seat, `"self"` only
the caster), and duration/`truncate_open_ended` decide the window, exactly like
any other stat. The per-shot callable (not a value sampled once) is what makes
scope AND mid-fight toggling both expressible in the same place — a scalar
computed once at t=0 cannot represent a buff that is not up for the whole fight.
**Only multiplies weapon-hit energy, not `bonus_fills`** (the flat skill-granted
fills below) — those are a separately-added term, not a multiplied one, and this
holds for BOTH trigger kinds. Whether this stat is ALSO meant to speed up a
skill's own flat gauge grant (e.g. Little Mermaid's Bubble Order) is unmeasured;
today it doesn't, which is the conservative default until a measurement says
otherwise. Keep the two kinds identical here — a difference between them would
be an inconsistency nothing could explain.
Consumers: `anis_star.py` (squad, permanent from battle start, +6% at lv10),
`grave.py` (squad, windowed to Heat Emission's `heat_emission_duration`, +38.96%
at lv10), `mana.py` (self, an open-ended Effect granted with Metal σ and closed
by `truncate_open_ended` when she spends it at Full Burst entry — the window
until the NEXT entry isn't known when it's granted, so no fixed duration can
express it — +70.4% at lv10). **Not every carrier of this stat is wired**:
`neon_vision_eye.py`'s Firepower Charge scales it off the Firepower Gauge's
live AMOUNT (+5% per point, up to +500%), and that module deliberately does not
carry the gauge as a live quantity — it measured the gauge inert for DAMAGE
(2026-08-14) and replaced it with a fixed burst-period constant instead. That
finding still stands; this is a different question, and it is a deferral of
SIZE, not of knowledge — the trajectory (battle-start 100, +2/normal, +45 on
window end, -100 on a qualifying burst) is already measurement-verified (the
same arithmetic reproduces the in-game 1st/4th/7th reading across six decks).
What's missing is a `ResourceSpec` to carry that trajectory as a live value
readable at each Full Burst end, tracked as an open gap in `docs/engine-gaps.md`
("네온: 비전 아이의 게이지 충전 속도"). See the module docstring and
`gauge-effect-census.md` before building it.

**Flat "Fills Burst Gauge by X%" grants are NOW consumed (2026-08-22)**, a second
charge source alongside weapon hits: `burst_gauge.fill_times`'s `bonus_fills`
argument. It is a list of specs, and **the key an element carries names its
trigger kind** — there is no separate `"kind"` field, so a new trigger is a new
key rather than a new argument. Two kinds exist:

- `{"every_ally_rounds": N, "fraction": X}` — allies' cumulative ammo expended
  crossing a multiple of N (detailed below).
- `{"every_own_full_charge": slug, "fraction": X}` — that seat's own weapon
  firing a Full Charge shot. **Once per shot, on the squad's single gauge:**
  the skill text's "Affects all allies" means the team gauge gets it, NOT that
  five seats each get it. Multiplying by 5 would let Helm fill the gauge in two
  full charges, against the measured three. The trigger is the shot's kind, so
  a tap-fire (partial-charge) shot does NOT count — the text says "Full Charge
  attack" — and neither does a hit her SKILL produced (`skill_hits_by_slug`),
  since no weapon fired it.
  **Only register a CHARGE weapon here.** `fill_times` reads the shot's kind off
  `ShotRecord.is_tap_fire`, which is `False` for every shot a non-charge weapon
  takes, so an AR/MG/SMG/SG seat registered with this key charges the gauge on
  **every single bullet** — a silent 10-100x, not an error. Both consumers today
  are SR, so nothing is wrong now; a future holder on a magazine weapon needs a
  different trigger, not this one. (The engine cannot catch this for you: "not a
  tap" and "a full charge" are the same boolean today.)
  Consumers: `helm.build_frontline_command_gauge_fills`
  (Frontline Command, +14.31%, **Favorite Item only** — base Helm's copy of the
  skill has no gauge bullet at all, which is why the builder is told its slug)
  and `maxwell_ordinary_mechanic.build_output_switching_gauge_fills` (Output
  Switching Sequence, +7.15%).

The ally-ammo kind in detail. Each time the squad's shared counter — the same
channel
Bubble Barrage reads (`context.shot_ammo_rounds`, `_AMMO_ROUNDS_PER_SHOT` for
who books more than 1 round/shot) — crosses a multiple of N, the gauge jumps
+X% of `GAUGE_FULL` at that instant: all-or-nothing, not a rate. **Every fill
in a deck shares ONE counter**: a shot's rounds are booked once regardless of
how many gauge-fill sources are seated, so a deck with two such units doesn't
double-count and charge faster than either alone. A single shot can cross its
own threshold more than once (an ammo-pouch shot booking hundreds of rounds at
once). **The counter never resets** (matches the skill text, "TOTAL ammo
expended by allies", and `build_bubble_barrage_scheduled_nukes`'s own running
`expended`) — a fresh gauge-charge window inherits whatever the counter already
reads at the window's start, found by a `bisect` into the same time-sorted shot
list `fill_times` already builds, rather than starting the count at zero per
window. That distinction is load-bearing whenever a threshold is comparable to
a charge window's length: on the measured deck 2 (Little Mermaid, every 400
rounds against a ~3.4s window at the deck's fire rate) resetting to zero per
window nearly doubles the computed steady-state charge time versus the correct
carried-over count (~5.5s vs ~2.4–2.7s,
`scripts/quantify_ally_rounds_accounting.py`).
Consumers: `little_mermaid`'s Bubble Order (every 400 rounds, +37%),
`cinderella_crystal_wave`'s Beauty-Full (every 200 rounds, +12%, shared by both
mode slugs since Beauty-Full is common to MG and Snipe).

Wire a Nikke's fill spec of EITHER kind via `_GAUGE_FILL_BUILDERS` /
`get_gauge_fills` in `skill_rules/registry.py`; `roster.assemble_simulation_inputs`
collects every seated unit's fills into one flat `gauge_fills` list that
`simulate_raid` forwards to `fill_times`. **The census of explicit gauge fills is
done** (`.superpowers/sdd/2026-08-21-burst-gauge-as-deck-property/
gauge-effect-census.md`, all 104 encoded slugs read end to end): 7 slugs carry
one, 5 are wired, and the 2 that are not are `rosanna` / `rosanna-signature`,
whose trigger ("when a Nikke is incapacitated") this sim never reaches. That is
gap #15, not a gauge gap — the capability exists; the trigger does not.

**Hits a SKILL produces NOW charge the gauge too (2026-08-22)** — riders
("additional damage" on the unit's own hit), drones, Auto Fire, periodic knocks.
The third and last charge source, and **nothing is declared per unit**: one hit
is worth `burst_energy_pershot x pellets` of the CASTER'S OWN WEAPON, whoever or
whatever threw it. Three units confirm that independently (Helm's favorite-item
rider 1.000x, Liberalio's 5-hit rider 1.015x/1.035x, Heavy Arms' Auto Fire
1.015x — `docs/measurements/burst-gauge-fill.md`, sections 「정정」 and
「증분만으로 한 전수 검산」). The full-charge multiplier rides only shots the
unit's own WEAPON fired, so a skill hit never takes it; skill hits spend no
ammunition, so they book 0 rounds into the shared ally-ammo counter; the fill-
speed multiplier above DOES apply to them (the stat's text is "Burst Gauge
charge speed", not "weapon hits charge faster").

**Which hits count is DERIVED, not listed** (`raid_simulator._gauge_skill_hits`,
feeding `fill_times`'s `skill_hits_by_slug`): every `damage_log` row except
(a) `source == "normal_attack"`, which `gauge_shots_by_slug` already counts with
its full-charge flag, and (b) rows whose `damage_type` is in
`burst_gauge.GAUGE_INERT_DAMAGE_TYPES` (today `{"sustained"}` — per-second DoT,
not a projectile; **unmeasured**, and named separately from
`NON_CORE_DAMAGE_TYPES` so a later reading flips one without the other).
`distributed` DOES charge — those are individual hits spread over an area, not
a DoT. Deriving beats a table because a newly-encoded unit is picked up with no
declaration at all, and because `damage_log`'s `slug` is always the CASTER's own
roster slug (drones and summons included), so `weapon_stats[slug]` is already
the right energy. That DoT exclusion currently costs nothing either way
(measured 2026-08-22): emptying the constant so DoT ticks DO charge leaves the
gauge table and total damage bit-identical on all five measured decks, because
those ticks are anchored on Full Burst entry or on a burst cast and so land
INSIDE the window, which never charges.

**A folded volley must DECLARE its hit count.** Some builders express "attacks
sequentially N times" as ONE instance at `N x per_hit`, and counting log rows
would then count it once. Pass `gauge_hits=N` to `instant_nuke_pulse_rule` (it
rides `Pulse.gauge_hits` -> `record(gauge_hits=...)` -> the log row); the default
is 1, so every other call site is unchanged, and damage never reads it. **Do NOT
infer the count from `damage_type == "sequential"`** — that value says which
Damage-Up bucket applies, not how many hits landed, and it would break silently
the day a unit types a genuine single hit that way. **Today exactly one unit
needs the declaration**: `snow_white_heavy_arms`, whose Auto Fire volley is
`base_ammo` (5) outside her Fully Active segment and `boosted_ammo` (15) inside
it. Sakura: Bloom in Summer folds ten hits the same way but is typed
`sustained`, so the DoT exclusion already covers her. Damage sources that fold
by TIME rather than by count are untouched: burst-source N-hit volleys and
`dynamic_hit_count_nuke` are all recorded at the cast.

**Whether a cast-time row can charge the very fill that scheduled it depends on
the TIER, and only tier 3 is safe.** `fill_times` has no "inside a Full Burst
window" test — it only skips rows before the PREVIOUS window's end — so a row is
excluded solely because the loop already broke on a full gauge. A tier-3 cast
lands `end + gauge + 0.2` (two tier gaps), comfortably after the fill at
`end + gauge`, so its rows are never reached. **Tier 1 and 2 are not:** they fire
at `end + quantized_gauge` and `+0.1`, and `quantize` ROUNDS, so on a cycle whose
grid value rounded DOWN the cast sits up to 0.05 s BEFORE the true fill — inside
the accumulation window of the fill that scheduled it. At a fixed point the error
is zero (both times quantize to the same grid point), but a mid-iteration pass
where the cast's energy covers the shortfall can settle on a false fixed point
lower than the true one, and that error is not bounded by the grid.

Measured over the 400-deck convergence sample (2026-08-22), dropping every row at
a tier-1/2 cast time — `burst`, `dynamic_hit_count_nuke`, AND the
`own_burst_activate` `instant_nuke` rows that land at the same instant:
**3 of 400 decks change, and 2 of those 3 are decks that already fail to converge
in BOTH variants** (they are in the stalled list, so their value is a 32-pass
oscillation rather than a fixed point). Exactly **one converged deck** moves: two
cycles shift by one grid step in opposite directions, worth **+0.051%** damage.
This is an OPEN item, not a settled deferral, and NO guard is wired — see
`docs/engine-gaps.md`. The five hand-measured decks cannot see this path at all:
their tier-1/2 seats carry no burst-cast damage rows, so "identical on all five"
was a fact about those rosters, not about the model.

**The scheduler DECLARES which constraint opened each cycle (2026-08-22).** Every
`"burst"` event `simulate_burst_cycle` emits carries `gauge_bound: bool` — whether
that cycle's fire time was set by the gauge (`gauge_ready > max(tier_ready)`)
rather than by a cooldown. It is recorded where `max()` is taken, because nothing
downstream can recover it: the realized gap `tier1_fire - previous_end` equals
the gauge fill time both when the gauge WON and when it merely TIED a cooldown,
and a tie pushed nothing — that cycle would have fired at the same instant with
no gauge at all. The old count re-derived it from that gap with `>=` and so
counted ties; do not reintroduce a timestamp-derived version.

The same event also carries `gauge_delay` — **how many seconds** the gauge pushed
that cycle (`gauge_ready - cooldown_ready`), 0.0 when it did not push. It is
declared for the same reason the boolean is: the event log has no record of when
the cooldowns were ready, so the size cannot be re-derived downstream either.
Two values are pinned to 0.0 deliberately — a cycle the cooldown won (a negative
"delay" is not a push, and summing it would cancel out real ones) and the OPENING
cycle (no cooldown is running, so `cooldown_ready` is `-inf` and the difference is
infinite, which would poison the sum).

`raid_simulator` only COUNTS and SUMS the declarations, into
`result["gauge_bound_cycles"]` and `result["gauge_delay_seconds"]`, and
`deck_search._summarize` carries both plus `total_cycles` (completed
`full_burst_end` events) out to `DeckRecommendation` for the screen. **The opening
cycle is excluded from both**: no cooldown is running yet, so the gauge is its
only start condition and every deck would carry a constant 1. All three fields are
DIAGNOSTIC — nothing in the engine reads them back, and they do not move damage.

Two things the COUNT is not. It is not "cycles where the gauge is the bottleneck"
(that includes ties). And **it is not the discriminating value — the magnitude
is.** Measured on Fienn's five decks (2026-08-22): deck 1 reports 11/14 bound yet
the pushes total 4.30 s of a 180 s fight, while deck 3 reports the same 11/14 for
11.61 s — and his in-game readings call deck 1 "not pushed" and deck 3 "pushed".
The count alone cannot tell those two decks apart, which is why the screen leads
with the seconds (`버충 밀림 +4.3초 · 14 사이클 중 11`) and why both fields ship.
No threshold is applied anywhere; showing the size lets a reader set their own.

**Exact ties do not occur in real decks** — the gauge is quantized to a 0.1 s grid
while cooldown ready times are not, and the closest approach across all five decks
was −0.02 s — so switching `>=` to `>` changed none of their numbers. The tie rule
is still the correct one; it is simply not what made the old number look wrong.

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
`SquadContext.live_max_hp(base_max_hp, caster, time, registry)` when the rule
FIRES and registers the result as `flat_atk`.

**Every source of `flat_max_hp` counts, including ones written by a LATER pass
of the same simulation.** The conversion runs inside the burst cycle, but two
places write Max HP after it — the shot loop's per-shot rules (Rouge's Card
Throw) and the resource-resolution pass (Maiden's Meditation `ResourceBuff`).
`simulate_raid` iterates to a fixed point over those: pass 1 collects the
`flat_max_hp` added after the burst cycle, pass 2 hands it back as a read-only
shadow that `live_max_hp` reads alongside the live registry. Always two passes
at most (Max HP does not affect the timeline), and exactly one when the deck has
no conversion consumer or writes no late Max HP — so encode a Max-HP buff in
whatever pass fits the skill text and do NOT contort it into a burst-cycle rule
to be seen.

Before this the two late sources measured as exactly zero — both of them, and
that had been true of Rouge's since she was encoded (2026-08-17: multiplying
either by 100 moved deck damage 0.0000%).

**Semantics are a snapshot**, deliberately: the conversion happens once per
trigger, so a Max-HP buff that lands AFTER the ATK buff does not retroactively
grow it — the shadow respects each late effect's own window, so a 5-sec Max HP
is only visible for those 5 sec. A unit whose Max HP keeps rising mid-fight must
re-fire the rule at each change. This keeps the damage hot path (`_stat_bundle`
/ `total_for`'s segment tables) untouched — not making deck search heavier is a
hard constraint (Fienn). Consumers: `laplace_ultimate_hero`,
`maxwell_ordinary_mechanic`, `cinderella`, `maiden_ice_rose` (the last inlines
the same conversion because its bullet lands at a delayed instant).

One rule for anyone adding a consumer: **the conversion must run inside the
burst cycle**, i.e. as a `SkillRule`. A conversion placed in a post-pass would
see the late `flat_max_hp` twice — once from the live registry, once from the
shadow.

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
| `ally_burst_activate` | when ANY unit's burst tier fires — for a skill that reacts to another unit bursting (e.g. Prika's Encore on Mint's Sing Along). Fired across all units' rules after the burster's own `own_burst_activate`; gate with `ally_bursted("<slug>")`, which reads `context.last_burst_slug`. **Instant nukes work here too** (2026-08-13): `drain_instant_damage` runs AFTER this trigger, so a reacting bullet may deal damage and not only apply buffs — Queen (Makoto Nijima)'s "when Follow Up takes effect" answers Yukiko's burst with 548.99% as distributed damage. Draining between the two triggers used to bank such a pulse until the next drain point (Full Burst enter), which both moved the hit off the burst it answered and paid it that window's bonus. |
| `full_burst_enter` | when the Full Burst window opens — `FULL_BURST_OPEN_DELAY` AFTER tier-3 fires, so it does NOT reach the B3's own burst damage. Use only for text that really says "at the start of Full Burst" (Crown's One for All is the only encoded one). |
| `full_burst_end` | when the 10s Full Burst window ends |
| `part_destroyed` | at each time in `BossProfile.part_destruction_times` (2026-08-20). "Activates when an ally or self destroys an enemy's part" — the engine has no part concept and cannot DERIVE when a part falls (no enemy/part HP anywhere, and `damage_to_parts_up` has no consumer), so the ENCOUNTER declares the observed times and the rule fires at each of them, buff duration included. **Gated on `part_destructible`**: the boolean says whether the boss HAS destructible parts, so times without it are a contradiction and the boolean wins. Times ≥ `fight_duration` are dropped. Fired beside the `periodic_rules` loop, before the burst cycle, for the same reason: buffs are inputs to damage and Effects are replay-safe. **Use `refreshing_buff_rule` with a named `refresh_group`, not `buff_rule`** — neither consumer's text carries a "Stacks up to N" clause, so two destructions inside one buff's duration must extend the window, not double the value (`buff_rule` sums, and the non-overlapping solo-40 reading hides it in every test). Consumers: `raven` (Single Point Attack), `diesel_winter_sweets` (the Sustained bracket). |

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
on-kill, HP thresholds, "when Raptures appear", or a **probability roll**
("There is a 5% chance of activating when attacking", `tove` base's Emergency-
Crafted Bullets) — this engine is deterministic and has nothing that rolls
dice, so a probability-gated effect stays deferred no matter how simple the
effect behind it is. Effects gated on these must be deferred — or, if central,
raise extending the engine with a new trigger.

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
- `boss_part_destructible()` / `boss_part_indestructible()` — the boss has (or
  has not) destructible parts. A bracket selector for kit whose real driver is
  unmodeled (Ark Ranger Black's battery, Diesel: Winter Sweets' Mute stacks),
  NOT an event.
- `boss_part_destruction_untimed()` — destructible parts but no declared
  destruction times (2026-08-20). Hang the old "treated as up from battle start"
  approximation on THIS, not on `boss_part_destructible()`: the moment an
  encounter declares times, the approximation switches itself off and the
  `part_destroyed` trigger takes its place. Leaving both on double-applies the
  same buff.
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
- `round_buff_rule(trigger, buffs, shots=1, cap=None, from_own_shot=False)`
  where `buffs` is `(stat, value, scope_spec)` - a "for N round(s)"
  bullet-count buff; `scope_spec` is a static scope string or `("top_atk", n)`.
  Live from the grant to the bullet that spends it, covering the recipient's
  skill damage too. The count is in ammunition SPENT: a recipient under
  [Unlimited Ammunition] does not tick it down. `cap` is the skill's "stacks up
  to N time(s)", enforced per instant; omitting it means no stacking, not
  unbounded. `from_own_shot=True` when the caster's own normal attack creates
  the grant.
- `escalating_buff_rule(trigger, tiers)` / `instant_nuke_pulse_rule(trigger, pct)`
  (see their own sections above).

Use these instead of hand-writing action closures unless the skill needs
branching/status logic (then write an explicit `SkillRule` like the branching
examples).
