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
