# Insights

Engine gotchas and reusable patterns — the things that surprised us or would
trip up the next person. Grouped by topic. For the encoding procedure and the
full stat/trigger/scope catalog, see the `nikke-skill-encoding` skill.

## Damage formula
- **The attack/skill coefficient scales the whole Base Damage, not the ATK stat.** A normal attack's "% of ATK" or a skill's "X% of final ATK" multiplies Base Damage *after* defense is subtracted — pass raw summary ATK plus a separate `attack_coefficient` to `calculate_damage`. Folding the coefficient into ATK mis-scales the defense subtraction and any flat ATK (~14% overstatement against a defended boss, and unevenly across Nikkes since coefficients range from ~5% normal attacks to ~8000% bursts, which would skew deck rankings). See `damage_formula.calculate_damage`.

## Crit
- **Crit is expected value, not per-hit RNG.** The major modifier gains `crit_rate*(0.5 + crit_damage_sources)`. Base crit rate is 15%, base crit damage +50%; both buff types are additive. Crit-damage buffs are inert with no crit chance. See `damage_formula._major_modifiers` and `raid_simulator.BASE_CRIT_RATE` (overridable via `base_crit_rate`, set 0.0 for deterministic tests).

## Effects / stats
- **Some formula terms are inert — registered but not consumed.** `other_core_damage_sources` (core damage) and `damage_taken_up` (enemy damage-taken debuff) are valid `damage_formula` params, but `raid_simulator` does not read them from the effect registry. Encoding an effect with them passes tests yet moves no simulated damage. Wiring them is an engine extension to raise, not to fake. (Cross-check the "engine CONSUMES" list in the skill's `references/engine-capabilities.md` and `grep registry.total_for raid_simulator.py`.)
- **`pierce_damage_up` is a general damage-up term.** It's applied to every hit, not gated to actual pierce hits — a known simplification.
- **Caster-scaled buffs use the base character-info ATK.** "ATK X% of caster's ATK" multiplies the caster's base ATK (gear + breakthrough + cube only; excludes overload and other skill effects), modeled as `flat_atk` via `values["caster_atk"]`, which `roster.assemble_simulation_inputs` injects.
- **Steady-state approximation for ramping buffs.** Escalating "previous effects trigger repeatedly" or "stacks up to N" effects are encoded at their max/settled value — a 3-minute raid reaches it almost immediately. Documented per module.

## Burst rotation
- **"Who bursts vs who buffs" = deck left-to-right order.** `burst_cycle` fires the leftmost eligible Nikke per burst tier, so the intra-tier ordering *is* the role assignment. The deck search explores those orderings. See `burst_cycle.py`.
- **Cycle timing waits for the slowest tier's cooldown.** The next Full Burst starts when whichever burst tier's cooldown clears latest (the gauge always charges faster than cooldowns for a raid-viable deck). A cycle is only "missed" when a burst tier is structurally absent from the deck, not when cooldowns lag.

## Data (dotgg)
- **Skill values are per level; retain all levels.** Encoding builders take a single-level values dict, so the user's actual skill level selects `levels[level-1]`. Users invest to different levels (Privaty's burst was used at level 7, not 10), so data collection must keep the full `levels` array, never just max.
- **Signature weapon = `dollskills`, and it can add effects.** When `dollskills` is present the character's signature weapon is completed; it changes values and can add entirely new effects/slots, not just bigger numbers. Always check `dollskills` vs `skills`.
- **max_ammo changes apply to base ammo and sum.** An overload ammo increase and a skill's ammo decrease (e.g. Privaty EX Magazine) both compute against BASE ammo and add — the decrease is not taken off the already-increased total. See `attack_rate`.
