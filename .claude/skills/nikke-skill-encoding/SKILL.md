---
name: nikke-skill-encoding
description: >
  Encode a NIKKE character's combat skills into this deck-builder's simulation
  engine (a backend/app/skill_rules/ module + tests + registry entry). Use this
  whenever the user wants to add a Nikke to the recommender/simulator, "encode
  X's skills", "add X to the deck builder", model a character's buffs/burst, or
  extend which Nikkes the deck search can consider. It captures the exact
  workflow, which effects the engine can represent vs must defer, and the naming
  conventions - follow it even for a single Nikke so encodings stay consistent.
---

# Encoding a NIKKE's skills into the simulation engine

The deck-builder simulates a raid by applying **effects** (buffs/debuffs) on a
timeline and totaling damage. Encoding a Nikke means translating its three
skills' free-text descriptions into `SkillRule`s that register effects at the
right triggers. The hard part is judgment: the engine can only represent some
mechanics, so you model the DPS-relevant parts it supports and **document what
you deferred** — never silently drop or fake a mechanic.

Work in the `backend/` directory. Tests are TDD and must stay green.

## Workflow

1. **Find the slug and fetch data.** The game data lives at the public
   `api.dotgg.gg` API (no auth). Find the slug, then pull the character:
   ```bash
   curl -s "https://api.dotgg.gg/nikke/characters" | python -c "import sys,json;[print(c['name'],'|',c['url'],'|',c['weapon'],'|',c['element'],'|','burst',c['burst']) for c in json.load(sys.stdin) if 'NAME' in c['name'].lower()]"
   curl -s "https://api.dotgg.gg/nikke/character/SLUG" -o char_SLUG.json
   ```
   See `references/dotgg-data.md` for the response shape and the
   `skills` vs `dollskills` (signature weapon) distinction — **ask the user
   which the character should use** if it has a signature weapon, since that
   changes the numbers and sometimes adds whole new effects.

2. **Dump the values you'll encode.** Print the max-level (`levels[-1]`) values
   per skill so you can see every `description_value_NN`. Read the description
   text alongside them to learn what each slot means.

3. **Classify every effect** into: (a) DPS-relevant AND representable by the
   engine → model it; (b) DPS-relevant but NOT representable → defer + document;
   (c) not DPS-relevant (heals, shields, DEF, taunts, Max HP) → skip. Use
   `references/engine-capabilities.md` for the exact catalog of stats, triggers,
   scopes, and the deferred-mechanics list. When unsure whether a mechanic is
   representable, check that catalog before inventing anything.

4. **Write the module** `backend/app/skill_rules/<slug_with_underscores>.py`.
   Reuse `_helpers.buff_rule(trigger, buffs)` and
   `_helpers.cdr_pulse_rule(trigger, seconds)` — most supporters are just
   bundles of timed buffs plus a cooldown pulse. Each `build_*` function takes a
   `skill_values` dict keyed by that Nikke's sub-skill names.

5. **Handle the burst skill.** If the burst is a nuke ("Deals X% of final ATK
   as Burst Skill damage"), expose a `<name>_burst_percent(values)` helper
   returning that X. If the burst is buffs-only (most supporters), there is no
   nuke — the registry entry's burst percent is `None`.

6. **Write tests** `backend/tests/test_skill_rules_<slug>.py` using the real
   values, asserting the effects land on the right scope/stat/duration and that
   caster-scaled and burst-percent numbers are correct.

7. **Register** the Nikke in `backend/app/skill_rules/registry.py`: import the
   builder(s) and add a `_BUILDERS` entry
   `lambda sv: (build_<slug>_rules(sv), <burst_percent or None>)`.

8. **Document** in the module docstring: a "Modeled (DPS-relevant)" list and a
   "Not modeled / deferred" list naming each skipped mechanic and *why* it
   can't be represented yet. This is not optional — it's how the next person
   knows the encoding is partial and what would make it complete.

9. **Verify**: `PYTHONIOENCODING=utf-8 python -m pytest tests/ -q` (the env var
   avoids cp949 encoding errors with Korean/arrow characters on Windows). Then
   commit on the WIP branch with a message listing what's modeled and deferred.

## Judgment: model, approximate, or defer

The recurring decision is what to do with a mechanic the engine can't express
exactly. In priority order:

- **Model exactly** when it maps cleanly to a stat/trigger/scope.
- **Approximate + document** when the intent is clearly a DPS buff but the
  targeting isn't expressible — e.g. "highest-ATK ally" or "SR allies" buffs
  become `squad` scope. This is right when the intended beneficiary (the deck's
  attacker) still gets the buff and the over-application to low-damage
  supporters barely moves total output. Always say so in the docstring.
- **Steady-state** for escalating/stacking effects ("previous effects trigger
  repeatedly", "stacks up to N", status that ramps): use the max/settled value,
  since a 3-minute raid reaches it almost immediately. Document the assumption.
- **Defer + document** when a trigger or mechanic simply doesn't exist yet
  (normal-attack-count, full-charge-count, ammo-expended counters, positional
  rows, weapon transformation, attack speed, hit rate). Do NOT approximate these
  onto `full_burst_enter` or similar — a wrong trigger silently distorts
  results, which is worse than an honest omission. Equally, do NOT invent a
  placeholder trigger name that nothing fires (e.g. a `shield_applied` trigger)
  and hang the effect off it: that's dead code that reads as "modeled" but never
  runs. Leave the effect out and name it in the deferred list instead.
- **Don't silently change the engine.** If you discover a stat that's inert
  because `raid_simulator.py` doesn't wire it from the registry (see the
  capability catalog's second inert group), do not add the global wiring
  yourself to make your Nikke "work" — it changes every deck's damage numbers.
  Raise it as an engine-extension the user approves, and encode the Nikke
  honestly (deferred) in the meantime.

If a deferred mechanic looks central to the Nikke's value (e.g. a support whose
whole kit is normal-attack-count triggers), say so to the user — it may be
worth extending the engine (a new trigger/condition) instead of encoding a
near-useless stub. That's an architecture decision to raise, not to make
silently.

## Conventions and gotchas

- **Caster-scaled buffs** ("ATK ▲ X% of caster's ATK") use the caster's **base
  character-info ATK** (gear + breakthrough + cube only; excludes overload and
  other skill effects). The assembly layer injects `caster_atk`/`caster_def`/
  `caster_max_hp` into `skill_values`, so read `values["caster_atk"]` — don't
  ask the caller to pass it again.
- **Crit matters now.** Crit Rate and Crit Damage buffs feed the expected-value
  crit model, so encode them (`crit_rate`, `other_critical_damage_sources`).
  But Attack Speed, Hit Rate, Burst Gauge fill speed, and Charge Speed are NOT
  consumed by the engine — encoding them is inert, so defer + document instead.
- **Match the existing style**: look at an already-encoded module of a similar
  archetype (`liter.py`, `crown.py`, `rapi_red_hood.py` for branching) and
  mirror its structure, docstring shape, and test layout.
- Follow the project's TDD rules in `.claude/CLAUDE.md` (tests first, pristine
  output, smallest change, WIP branch, frequent commits).
