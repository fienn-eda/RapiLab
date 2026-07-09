---
description: Fetch a NIKKE character's data from dotgg (all skill levels preserved) via the data-collector subagent
argument-hint: [character name]
context: fork
agent: nikke-data-collector
---

Collect the NIKKE character "$ARGUMENTS" from api.dotgg.gg.

Save the full character JSON — with every skill's complete `levels` array
preserved — under `data/dotgg/`, and report:
- metadata: class, weapon, element, burst, and whether a `dollskills`
  (signature-weapon) array is present (flag it if so),
- the weapon / normal-attack stats,
- for each skill: name, cooldown, and the values at the max level with a short
  note on what each `description_value_NN` slot means (read from the description
  text).

Confirm the saved file retains all skill levels, not just the max.
