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

1. **Find the slug and fetch data.**
   - **Non-signature units (`skills`, no dollskills) — ShiftyPad first.** This is
     the canonical source for a unit the roster loader must also assemble
     (weapon stats + skill base values in one fetch, so no manual weapon entry;
     dotgg is dead for anything released after 2026-05). Run
     `cd tools/collect-blablalink && node collect.js --nikke <rid|name> --headless`
     (public data, no login — it bundles playwright-core), then normalize with
     `python scripts/normalize_shiftypad_raw.py <rid>:<slug>` →
     `data/shiftypad/<slug>.json`. The manifest (step 9) then declares
     `source: "shiftypad"`. See `docs/new-nikke-detection.md`.
   - **Still fetch lootandwaifus for the effect text.** ShiftyPad's normalized
     output is value slots; the free-text descriptions that tell you what each
     slot *means* (and the portrait for step 11) come from lootandwaifus. Fetch
     the character page with curl + a browser User-Agent (WebFetch gets HTTP 403).
   - **Signature (`dollskills`) builds** stay on the lootandwaifus/dotgg path +
     weapon stub (ShiftyPad doesn't expose dollskills) — **ask the user which
     build** when a unit has a signature weapon, since it changes the numbers and
     sometimes adds whole new effects.

   See `references/character-data-sources.md` for both sites' endpoints, slug
   conventions, and the `skills` vs `dollskills` distinction.

2. **Dump the values you'll encode.** Get the max-level values per skill (and
   for dotgg, the raw `description_value_NN` slots + description text; for
   lootandwaifus, number the slots yourself by left-to-right order of
   appearance — see the reference doc). Read the description text alongside
   them to learn what each slot means.

3. **Classify every effect** into: (a) DPS-relevant AND representable by the
   engine → model it; (b) DPS-relevant but NOT representable → defer + document;
   (c) not DPS-relevant (heals, shields, DEF, taunts, Max HP) → skip. Use
   `references/engine-capabilities.md` for the exact catalog of stats, triggers,
   scopes, and the deferred-mechanics list. When unsure whether a mechanic is
   representable, check that catalog before inventing anything. Also check
   `references/special-mechanics.md` for mechanics that are easy to misread
   (e.g. Distributed Damage is a DPS buff, not defensive) — and **append a new
   entry there whenever you hit a special mechanic**, so it's captured for next
   time. For *how a buff or damage type actually applies* (which multiplier
   group it belongs to, e.g. True Damage ignores DEF, Attack Damage affects all
   damage, Projectile Explosion is RL-only), consult
   `references/damage-formula-reference.md` — the authoritative nikke.gg
   glossary/notes. It also carries the **scope rules for the major modifiers**,
   which decide whether an effect can reach a given damage instance at all:
   Core Damage and the Effective Range Bonus are **normal-attack only** (range
   additionally maps distance to weapon — Near SG/SMG, Mid AR/MG, Far SR — and
   **RLs never get it**), while the Full Burst Bonus is decided purely by *when*
   the instance is computed. Getting scope wrong is invisible in tests and shows
   up only against the real game, so check it there rather than inferring it
   from a skill's wording.

4. **Consolidate judgment calls and review in one batch (the encoding plan).**
   Before writing any code, gather **every judgment call from step 3 into a
   single encoding plan and present it to Fienn all at once**. Do not raise
   ambiguities one at a time as you hit them — eliminating round-trips is the
   whole point. The plan contains:
   - **Per-skill classification summary**: one line per effect saying whether it
     was handled as model / approximate / defer / skip.
   - **Judgment-call list**: for each item that is ambiguous or needs game
     knowledge — (a) your **recommended interpretation**, (b) a one-line
     **rationale**, (c) **how you'll encode it** in the engine if approved — so
     Fienn only has to approve or correct each item.
   - If nothing is ambiguous, say so and proceed.

   Do not re-ask about the clear items — state how you handled them and reserve
   questions for the calls that genuinely fork. Fold in any decision already
   pending from earlier steps (e.g. the signature-weapon `skills` vs
   `dollskills` choice from step 1) so Fienn reviews everything in one pass.
   The rule is still "ask rather than guess on unclear mechanics" — this just
   batches those questions into one review instead of drip-feeding them.

5. **Write the module** `backend/app/skill_rules/<slug_with_underscores>.py`.
   Reuse the `_helpers`: `buff_rule(trigger, buffs)` and
   `cdr_pulse_rule(trigger, seconds)` for the common "timed buffs + cooldown
   pulse" supporter, and `escalating_buff_rule(trigger, tiers)` for
   "Once/Twice/Three times" ramps. For deck-composition-dependent behaviour use
   the `deck_contains(slug)` condition. Each `build_*` function takes a
   `skill_values` dict keyed by that Nikke's sub-skill names.

6. **Handle the burst skill.** If the burst is a nuke ("Deals X% of final ATK
   as Burst Skill damage"), expose a `<name>_burst_percent(values)` helper
   returning that X. If the burst is buffs-only (most supporters), there is no
   nuke — the registry entry's burst percent is `None`.

7. **Write tests** `backend/tests/test_skill_rules_<slug>.py` using the real
   values, asserting the effects land on the right scope/stat/duration and that
   caster-scaled and burst-percent numbers are correct.

8. **Register** the Nikke in `backend/app/skill_rules/registry.py`: import the
   builder(s) and add a `_BUILDERS` entry
   `lambda sv: (build_<slug>_rules(sv), <burst_percent or None>)`.

   **Expect `tests/test_resource_id_slug_map.py` to go red the moment you do
   this.** That guard cross-checks `ENCODED_SLUGS` against the frontend's
   `resource_id → slug` table (`frontend/src/lib/resourceIdSlugMap.ts`), so a
   newly encoded slug with no entry there fails `test_every_encoded_slug_is_
   reachable_except_known`. This is the guard working, not a broken test.
   Resolve it one of two ways:
   - **You know the unit's blablalink `resource_id`** (it appears in a collected
     `roster.json`, i.e. someone owns it): add `<id>: '<slug>',` to the map with
     a `// <name_en>` comment.
   - **You do not know it** — look it up in
     `tools/collect-blablalink/nikke-directory.json`, the committed snapshot of the
     public nikke directory, which lists every unit's `resource_id` and English name
     whether or not anyone owns it. If the unit is too new to appear, refresh the
     snapshot (`node collect.js --directory`) or add the slug to `KNOWN_UNMAPPED` in
     the test with a one-line reason. **Never guess a resource_id** (CLAUDE.md: don't
     invent technical details); a wrong-but-valid id silently mis-maps a real user's
     unit.

   `tests/test_resource_id_directory.py` then checks your entry against that
   snapshot, so a slug pointing at the wrong unit fails rather than shipping. If the
   unit's ShiftyPad name is a short form of the slug's full name (collab units —
   "Ada" vs `ada-wong`), add it to that test's `SLUG_NAME_EXCEPTIONS` pinned to the
   exact directory name.

   If the unit is a base/signature pair (`<slug>` **and** `<slug>-signature`
   both encoded), `test_dual_slot_bases_match_encoded_pairs` also fails: add the
   base to `DUAL_SLOT_BASES` in the same frontend file. The map itself must keep
   pointing at the **base** slug — signature promotion is per-user investment and
   comes from the roster's per-unit `favorite_item` flag, never from the identity
   map. Nothing else may promote: a roster that cannot report ownership stays on
   the base slug.

9. **Declare the skill-value manifest** so the roster loader can assemble the
   unit from local data files at any skill level: add a `SKILL_VALUE_MANIFESTS`
   dict at the top of the module (right after the imports) mapping each
   sub-skill key to its `("skills" | "dollskills", index)` slot, with `source`
   (which site the slot numbering was transcribed from), `test_module` (where
   the ground-truth fixtures live, module-level, named `KEY_NAME.upper()` or
   listed under `fixtures`), and — only where the verification harness fails —
   per-key `drop_tokens` (0-based token indexes the encoder skipped when
   numbering). Then run the harness:
   `PYTHONIOENCODING=utf-8 python -m pytest tests/test_skill_value_assembly.py -q -k <slug>`
   and fix mismatches with `drop_tokens`, never by editing fixtures or the
   harness. See `backend/app/skill_rules/drake.py` for the manifest shape.

10. **Document** in the module docstring: a "Modeled (DPS-relevant)" list and a
   "Not modeled / deferred" list naming each skipped mechanic and *why* it
   can't be represented yet. This is not optional — it's how the next person
   knows the encoding is partial and what would make it complete.

11. **Fetch the portrait** for the palette UI: run
   `python scripts/download_portraits.py`. It reads the now-registered slug from
   `_BUILDERS`, pulls the portrait path out of the lootandwaifus HTML collected
   in step 1, downloads the icon into `frontend/public/portraits/`, and rewrites
   `manifest.json` (slug → filename). Idempotent — existing icons are skipped, so
   it only fetches the new unit. If the Nikke is an engine-only build variant
   with no character page of its own (e.g. `<slug>-signature`, `rapi-red-hood-b1`),
   the script reports it as `UNMAPPED`; add one line to `SLUG_ALIASES` in the
   script mapping it to the base character's html slug, then re-run. See
   `frontend/public/portraits/README.md`.

12. **Verify**: `PYTHONIOENCODING=utf-8 python -m pytest tests/ -q` (the env var
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
- **Cycle-aware escalation** for "Once/Twice/Three times, previous effects
  trigger repeatedly": use `escalating_buff_rule` so each tier unlocks on its
  activation and ramps per burst cycle. Do NOT flatten these to a steady-state
  max — Fienn wants the real per-cycle ramp, and it composes with deck-dependent
  behaviour (e.g. Anchor's debuff-clear letting Mast hold 3 Drunken stacks). For
  a plain "stacks up to N" that just settles (no per-tier effects, no cross-unit
  coupling), the settled max is still fine — document the assumption.
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
  **Attack Speed and Charge Speed are damage stats too** since Phase S
  (2026-07-16): `attack_rate.py` scales the firing cadence from
  `attack_speed_percent` / `charge_speed_percent`, so in a fixed-length fight
  they mean more shots. Encode them. Only Hit Rate and Burst Gauge fill speed
  are still inert — defer + document those.
- **A "deferred" note is a claim about the engine on the day it was written.**
  Before honouring one, check that the capability it names is still missing —
  `references/engine-capabilities.md` and `docs/engine-gaps.md` are the current
  truth; module docstrings are not. Several units carried defers long after the
  blocking primitive shipped (Anis: Star's Shooting Stars cited gap #6, which
  had landed; Crown's Royal Attire cited "an attack-rate model that doesn't
  exist yet", which exists; Helm's own docstring admitted its bullet was "just
  not built in this pass"). When you clear one, correct the docstring's reason
  rather than only deleting the line.
- **Match the existing style**: look at an already-encoded module of a similar
  archetype (`liter.py`, `crown.py`, `rapi_red_hood.py` for branching) and
  mirror its structure, docstring shape, and test layout.
- Follow the project's TDD rules in `.claude/CLAUDE.md` (tests first, pristine
  output, smallest change, WIP branch, frequent commits).
