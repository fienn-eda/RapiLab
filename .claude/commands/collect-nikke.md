---
description: Fetch a NIKKE character's data (lootandwaifus.com first, dotgg fallback; all skill levels preserved) via the data-collector subagent
argument-hint: [character name]
context: fork
agent: nikke-data-collector
---

Collect the NIKKE character "$ARGUMENTS" from lootandwaifus.com (primary),
falling back to api.dotgg.gg only if lootandwaifus is unreachable.

Save the full raw page/JSON — with every skill's complete level data
preserved — under `data/lootandwaifus/` or `data/dotgg/` as appropriate, and report:
- metadata: class, weapon, element, burst, and whether a `dollskills`
  (signature-weapon) array is present (flag it if so),
- the weapon / normal-attack stats,
- for each skill: name, cooldown, and the values at the max level with a short
  note on what each `description_value_NN` slot means (read from the description
  text).

Confirm the saved file retains all skill levels, not just the max.

After saving a lootandwaifus collection, also secure the unit's dotgg
weapon stats (the engine reads maxAmmo/damage/reloadTime/chargeTime/
chargeDamage from data/dotgg/, and lootandwaifus only has the weapon TYPE):
run `python3 scripts/collect_dotgg_weapons.py`. If it reports the unit as
NOT ON DOTGG (dotgg stopped updating around 2026-05), rerun with
`--stub <slug>` and report that Fienn must fill the stub's `_todo` fields
(then delete `_todo`); include the stub path in your report. If it reports
ALIAS NEEDED, note that the unit's manifest needs that `dotgg_slug` when it
gets encoded.
