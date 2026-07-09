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

There is **no positional scope** (front/back row, "allies on both sides") and
**no weapon-conditional scope** ("SR allies", "shotgun allies"). Approximate
weapon/positional offensive buffs as `squad` (documented), or defer.

## Stats the engine CONSUMES (encoding these affects output)

Damage stats (fed into `calculate_damage`, so they change damage numbers):
| stat | meaning | game wording |
|---|---|---|
| `atk_percent` | ATK% buff on target's own ATK | "ATK ▲ X%" |
| `flat_atk` | additive flat ATK (usually caster-scaled) | "ATK ▲ X% of caster's ATK" |
| `other_elemental_bonus` | superior/advantageous code damage | "Superior Code / 우월코드 대미지 ▲" |
| `other_critical_damage_sources` | crit damage buff | "Critical Damage ▲ X%" |
| `crit_rate` | crit rate buff (base 15% is added by the sim) | "Critical Rate ▲ X%" |
| `charge_damage_bonus` | extra charge damage | "Charge Damage ▲ X%" |
| `attack_damage_up` | Attack Damage bucket | "Attack Damage ▲ X%" |
| `damage_to_parts_up` | damage to parts/interruption | "Damage to (Interruption) Parts ▲" |
| `pierce_damage_up` | pierce damage (modeled as general damage-up) | "Pierce Damage ▲ X%" |
| `damage_taken_up` | enemy damage-taken debuff — model as **squad** scope (all attackers share it) | "Damage Taken ▲ X%" (on enemy) |
| `other_core_damage_sources` | core-damage buff, **gated on `core_hittable`** (inert if boss has no core) | "Damage dealt when attacking core ▲ X%" |

Scheduling stats (change the burst rotation / shot timing, not per-hit damage):
| stat | mechanism | game wording |
|---|---|---|
| `burst_cooldown_reduction_sec` | **Pulse**, drained at full-burst-end; **scope-aware** (self reduces only the caster's cooldown, squad reduces everyone's) | "Cooldown of Burst Skill ▼ X sec" |
| `max_ammo_percent` | scales base magazine size (increases and decreases both apply to BASE, summed) | "Max Ammunition Capacity ▲/▼ X%" |
| `reload_speed_percent` | shortens reloads | "Reloading Speed ▲ X%" |

Burst nuke: not a stat — exposed via a `<name>_burst_percent(values)` helper and
put in the registry entry, applied as the attack coefficient of a burst hit.

## Stats the engine does NOT consume (encoding is inert — defer instead)

Two groups. In both, encoding an effect with these stats is silently inert —
tests can still pass (the effect registers and `total_for` returns it), but the
value never reaches `calculate_damage`, so it does NOT change simulated damage.

**Not a damage concept at all** — no consumer will ever exist without a bigger
model: `attack_speed` / Attack Speed, `hit_rate` / Hit Rate,
`burst_gauge_fill_speed_percent` (gauge charge time is a fixed sim input),
`charge_speed_percent`, `shield_amount`, and anything HP/heal/DEF/survivability.
Defer these; if a Nikke's contribution is mostly these, say so — a thin
encoding is honest.

**Valid formula terms that raid_simulator just doesn't wire from the registry
yet** — a real gap, not a dead end: `sustained_damage_up`, `true_damage_up`,
`shield_damage_up`, `projectile_explosion_damage_up`, `distributed_damage_up`,
and the major-modifier terms `full_burst_bonus` / `effective_range_bonus` /
`final_atk_modifier`.

All exist in `damage_formula.py` but are absent from `raid_simulator.py`'s
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
| `full_burst_enter` | when tier-3 fires and Full Burst begins |
| `full_burst_end` | when the 10s Full Burst window ends |

There is **no** trigger for: normal-attack counts ("after N normal attacks"),
full-charge-shot counts ("full charge N times"), ally-ammo-expended counters,
on-kill, HP thresholds, or "when Raptures appear". Effects gated on these must
be deferred — or, if central, raise extending the engine with a new trigger.
For an always-on-in-raid condition like "when Raptures appear" you may treat it
as active (document the assumption) since a raid always has enemies.

## Conditional / branching skills

For skills that branch on squad composition or a per-Nikke status flag, use
`squad_engine`:
- `no_other_burst_tier_allies(tier)` — true if the caster is the only one of
  its burst tier (e.g. Anis: Star / Rapi: Red Hood "if no other Burst 1 ally").
- `has_status(flag)` / `not_condition(cond)` — gate on a status the skill sets
  via `context.set_status/clear_status` (e.g. "My Own Star", "Combat Assist").
- `context.burst_used_this_cycle` — which slugs have burst this cycle (Crown's
  "allies who previously cast their Burst Skill").

See `rapi_red_hood.py` and `anis_star.py` for worked branching examples, and
`crown.py` for a per-member `burst_used_this_cycle` branch.

## Helpers

`app/skill_rules/_helpers.py`:
- `buff_rule(trigger, buffs)` where `buffs` is a list of
  `(stat, value, scope, duration)` tuples.
- `cdr_pulse_rule(trigger, seconds, scope="squad")`.

Use these instead of hand-writing action closures unless the skill needs
branching/status logic (then write an explicit `SkillRule` like the branching
examples).
