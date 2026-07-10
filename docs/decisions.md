# Decisions

Project decision log (ADR-lite). Newest at the top. Records choices that had
real alternatives — data sources, stack, scope, modeling conventions — not
routine implementation. For *how to encode a Nikke* and the engine capability
catalog, see the `nikke-skill-encoding` skill, not here.

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
