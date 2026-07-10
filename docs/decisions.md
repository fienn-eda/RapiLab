# Decisions

Project decision log (ADR-lite). Newest at the top. Records choices that had
real alternatives — data sources, stack, scope, modeling conventions — not
routine implementation. For *how to encode a Nikke* and the engine capability
catalog, see the `nikke-skill-encoding` skill, not here.

## Per-shot triggers + record-then-compute (gap #1)
- Date: 2026-07-11
- Context: ~30 collected units gate their headline damage/buffs on shot counts ("after/every N normal attacks", "N full charge attacks") - the top-ROI engine gap. Naively firing these during the normal-attack pass (which runs after the burst cycle) would mean a per-shot SQUAD buff (e.g. Rouge/Ade buffing a dealer) never reaches a burst nuke computed earlier - understating exactly the support-buffs-dealer synergy the recommender is meant to find. Fienn chose the accurate approach over a lower-risk scoped one.
- Decision: (1) Refactor `simulate_raid` to RECORD every damage instance (burst/instant/periodic/per-shot nukes + normal attacks) as an event during phase 1 (which only applies buffs), then compute them all in a phase-2 pass against the final registry. (2) Add `simulate_raid(..., per_shot_rules={slug: [(threshold, mode, [SkillRule])]})`, fired at the unit's shot counts ("after" once at N / "every" at each multiple of N); rules apply buffs (`buff_rule("per_shot", ...)`) or emit an `instant_damage_percent` pulse recorded as `per_shot_nuke`. Exposed via `registry._PER_SHOT_RULE_BUILDERS` / `get_per_shot_rules`, threaded by `roster`.
- Why: The refactor is provably behavior-preserving (effects are added with `applied_at >= their time`, and `truncate_open_ended` mutates in place, so deferring computation never changes an existing value - the 257 prior tests stayed green) while letting late buffs correctly reach earlier instances. The engine counts shots regardless of weapon (a charge weapon's every shot is a full charge), so "full charge N" and "normal N" unify to a shot count - the encoding picks N.
- Consequences: `per_shot_rules` rules must be stateless and must not affect shot generation (reload/ammo). "On firing the last bullet" is still a gap (needs magazine-boundary markers in `attack_rate`); per-shot nukes default to `attack` type. First consumer: Brid: Silent Track's Journey Ahead (675% every 5 normal attacks). The ~30 blocked units can now be re-encoded as a follow-up batch.

## Periodic skill trigger: cooldowned Skill 1/2 buffs fire on their own cooldown
- Date: 2026-07-11
- Context: Fienn confirmed a universal battle-system rule - a Skill 1/2 (not the Burst) that has a cooldown does NOT fire at battle start; it first fires at t=cooldown and repeats. Takina Inoue's Battlefield Control (cd 15s) applies squad ally True Damage +140% and enemy Damage Taken +10% every 15s starting at t=15 - her headline support - but the engine's only triggers were the 4 burst events, and `periodic_nukes` only handles damage, not buffs.
- Decision: Add `simulate_raid(..., periodic_rules={slug: [(cooldown, [SkillRule, ...])]})`. These fire each rule's action at t=cooldown, 2*cooldown, ... Because the buffs they apply are damage INPUTS (unlike `periodic_nukes`, an output post-pass), the pass runs BEFORE `simulate_burst_cycle` so any nuke computed during the cycle reflects them (effects are replay-safe, so pre-adding at future times is correct). Exposed via `registry._PERIODIC_RULE_BUILDERS` / `get_periodic_rules`, threaded by `roster`; rules built with `buff_rule("periodic", ...)` (a label - never dispatched by `fire_trigger`).
- Why: Generalizes the existing periodic mechanism to buffs; a universal rule so high reuse (Rosanna's Spina di Rosa cd30s buff part could use it later). First-fire-at-t=cooldown already matched `periodic_nukes`, so no inconsistency. Additive, defaults to `{}`/no-op.
- Consequences: Periodic rules run against the initial context, so they must be stateless buff appliers (no dependence on burst-cycle state) - documented. A periodic nuke with an internal duration shorter than its cooldown (duty cycle, e.g. Rosanna's Spina) is still an open gap. First consumer: Takina Inoue.

## Damage typing to make type-specific Damage-Up buffs non-inert
- Date: 2026-07-10
- Context: `sustained_damage_up` / `distributed_damage_up` / `true_damage_up` / `projectile_explosion_damage_up` exist in `damage_formula.py` but `raid_simulator` never read them, so buffs like Rosanna's "Sustained Damage +20%", Takina's "True Damage +140%", and Mint's "Projectile Explosion Damage +X%" were inert. Wiring them blanket (like `attack_damage_up`) would be wrong: they only raise damage OF that type, so a squad-wide sustained buff must not boost everyone's normal attacks. And gating them correctly is still inert unless the engine also produces instances of that type - so it's a coupled feature, not a one-line wire (correcting an earlier "~1 line each" estimate).
- Decision: Give every damage instance a `damage_type`; `raid_simulator._TYPE_BUCKETS` reads a type-gated Damage-Up bucket only for matching instances (always-on buckets stay global, so untyped "attack" instances are unchanged). Types are set via: `registry._BURST_DAMAGE_TYPES` for burst nukes (rapi-red-hood → projectile_explosion), a `"damage_type"` key on `periodic_nukes` entries, RL weapon → `projectile_explosion` for normal attacks, and a self-scoped `normal_attacks_deal_true` effect that converts a unit's normal attacks for a window (Takina).
- Why: Faithful to how the buffs work in-game (per-type multipliers) without over-crediting; additive and no-regression for existing decks (default type "attack" adds no bucket). Refactored the two duplicated `calculate_damage` call sites into one `_damage_instance` helper, so type-gating lives in exactly one place.
- Consequences: Emitting a type-gated buff is now live only when the deck also produces an instance of that type (the buff is a multiplier needing something to multiply). Mint's projectile-explosion buff now reaches RL allies; Rapi's burst nuke benefits from it. Semantics confirmed against the nikke.gg glossary (now captured in `nikke-skill-encoding/references/damage-formula-reference.md`): True Damage **ignores enemy DEF** (true-typed instances use `enemy_def=0`); Attack Damage is a general buff that **affects all damage**, so `attack_damage_up` stays global. Deferred: shield_damage_up and the major-modifier terms remain inert.

## Periodic-nuke engine capability for own-fixed-cooldown skills
- Date: 2026-07-10
- Context: Helm: Aquamarine's Aegis Cannon Suppression Fire is a separate active skill with its own 4-second cooldown, firing repeatedly throughout the fight independent of burst timing entirely (not gated on Full Burst, own burst, or normal-attack count) - a genuinely new mechanic shape, at 105.58% of final ATK per tick (~45 ticks over 180s) likely her primary DPS as an Attacker.
- Decision: Add `simulate_raid(..., periodic_nukes={slug: {"cooldown": sec, "percent": float}})` - each entry ticks independently up to `fight_duration`, computed via the same `_damage_from_percent` helper as burst/instant nukes, logged with `source="periodic"`. Exposed per-Nikke through a new `registry._PERIODIC_NUKE_BUILDERS` map (kept separate from the main `_BUILDERS` dict) and `registry.get_periodic_nuke`, wired automatically by `roster.assemble_simulation_inputs`.
- Why: Fienn approved building the capability over a thin/silent approximation, given the likely DPS weight. Kept as an additive, opt-in parameter (defaults to `{}`/no-op) so the ~25 existing encoded Nikkes are completely unaffected - no change to their builder return shape.
- Consequences: A third category of "how a Nikke deals damage" now exists alongside burst nukes and instant-damage pulses (see `references/special-mechanics.md`). Future Nikkes with a similar own-cooldown skill reuse this directly.

## Character data source priority = lootandwaifus.com first, dotgg fallback
- Date: 2026-07-10
- Context: dotgg (the original data source decision below) lags roughly the last ~2 months of NIKKE releases, so newer Nikkes (e.g. Prika) have no dotgg entry. lootandwaifus.com was found and cross-verified against dotgg (Little Mermaid, all 3 skills, every value at level 10 — exact match, no discrepancies), and its character-listing page carries richer metadata (mechanic tags in CSS classes) than dotgg's summary endpoint.
- Decision: Use lootandwaifus.com as the primary data source for all character collection going forward (not just as a fallback for missing characters); keep dotgg as a fallback/cross-check.
- Why: At least as current as dotgg, richer listing metadata, and validated as accurate. Reduces how often the fallback path is needed at all.
- Consequences: `nikke-data-collector` and the encoding skill's workflow now fetch from lootandwaifus first. lootandwaifus has no `description_value_NN` placeholder structure (unlike dotgg) — slots are numbered by left-to-right order of appearance in the rendered per-level text instead. Raw pages are saved to `data/lootandwaifus/` (gitignored, same as `data/dotgg/`). See `references/character-data-sources.md` (renamed from `dotgg-data.md`).

## Instant-damage pulses for non-own-burst nukes
- Date: 2026-07-10
- Context: Brid: Silent Track's Ignition Sequence deals 636% of final ATK on entering Full Burst, regardless of who bursts that cycle - a real damage source, but the existing engine only computed burst-nuke damage tied to the caster's OWN burst tier firing (`own_burst_activate` + `burst_damage_percents`). Encoding Brid without it would leave her almost valueless (buff-only), understating a deck that includes her.
- Decision: Add an `instant_damage_percent` Pulse (`_helpers.instant_nuke_pulse_rule`) that any trigger's action can emit; `raid_simulator.drain_instant_damage` drains it after every trigger fire (battle_start, own_burst_activate, full_burst_enter, full_burst_end) and computes damage the same way as a burst nuke, using the pulse's source_slug as caster.
- Why: Reuses the existing damage-calculation path (via a shared `_damage_from_percent` helper) rather than duplicating it; keeps the change additive (new pulse type + 4 drain calls) instead of altering the SkillRule action signature for every existing module.
- Consequences: Damage instances from this path are logged with `source="instant_nuke"` (distinct from `"burst"`/`"normal_attack"`). Future Nikkes with the same "deal damage on trigger X, not on own burst" pattern reuse this directly.

## Crit modeled as expected value
- Date: 2026-07-10
- Context: Many Burst-1 supporters (Volume, Miranda, Tove, …) exist mainly to buff Critical Rate / Critical Damage, but the simulator computed every hit as non-critical, so those buffs did nothing and the recommender would rate the units useless.
- Decision: Model crit as expected value — every hit's damage is scaled by `1 + crit_rate*(0.5 + crit_damage_sources)`, with base crit rate 15% and base crit damage +50%.
- Why: Captures the DPS contribution of crit buffs without per-hit RNG; matches nikke.gg/note.com's documented expected-value formula.
- Consequences: Crit-rate and crit-damage buffs now move output. `base_crit_rate` defaults to 0.15 but is overridable to 0.0 for deterministic tests.

## Search scope = single best deck first; encoded Nikkes only
- Date: 2026-07-10
- Context: The end goal is recommending 5 decks (25 Nikkes) that maximize summed damage, but that partition is a large combinatorial layer.
- Decision: Build the single-best-deck optimizer first (feasibility + pruning + exhaustive over intra-tier orderings); the 5-deck partition is a later layer. Candidate pool is restricted to Nikkes with encoded skill rules.
- Why: The single-deck evaluator is the building block for the partition. Engine usefulness scales with how many Nikkes are encoded, so encoding is the real lever.
- Consequences: Recommendations only consider encoded Nikkes; the roadmap includes encoding more and adding the 5-deck partition.

## Fight duration = 180s
- Date: 2026-07-10
- Context: Damage totals depend on the raid time limit.
- Decision: Use 180 seconds (3 minutes) for solo raid / union raid.
- Why: Confirmed by Fienn as the boss-battle time limit.

## Element advantage cycle
- Date: 2026-07-10
- Context: The recommender must credit +10% elemental advantage against a boss.
- Decision: Cycle is Water > Fire > Wind > Iron > Electric > Water; advantaged attacker deals +10%.
- Why: Verified from nikke.gg/code and the Fandom wiki rather than assumed.
- Consequences: `app/elements.py` encodes it; `simulate_raid(boss_element=…)` applies it.

## MVP user data = manual entry
- Date: 2026-07-10
- Context: ShiftyPad (the source of a user's real Nikke investment) requires login and isn't openly queryable.
- Decision: For the MVP, users enter their real stats/investment manually; automation (login-session scraping or API reversing) is deferred.
- Why: Simplest thing that works and isn't brittle to site changes. Overload option values are additive on top of the base character-info stat.
- Consequences: The engine consumes user-supplied real ATK/DEF/HP; the per-character base-stat growth table (dotgg `statTableId`) is unneeded and, conveniently, isn't exposed anyway.

## Tech stack = Python backend + React frontend
- Date: 2026-07-09
- Context: Choosing an implementation stack that fits Fienn's workflow.
- Decision: Python backend (FastAPI planned) + React frontend.
- Why: Fienn works primarily in Jupyter/Python; prototype-in-notebook then move logic into backend modules. React chosen for UI flexibility.

## Data source = api.dotgg.gg
- Date: 2026-07-09
- Context: nikke.gg character pages are client-rendered; a static fetch returns only the navigation shell, not stats/skills.
- Decision: Pull character and skill data from `api.dotgg.gg` — the public, no-auth JSON API that nikke.gg's front end calls (discovered by capturing the page's network requests with Playwright).
- Why: Structured data with no scraping/HTML parsing and no auth. Alternatives rejected: scraping rendered HTML (brittle); the Chrome extension (unavailable in this environment).
- Consequences: `skills` vs `dollskills` (signature weapon) must be distinguished. The `statTableId` base-stat growth table isn't exposed by the API, but isn't needed (see MVP manual-entry decision).
