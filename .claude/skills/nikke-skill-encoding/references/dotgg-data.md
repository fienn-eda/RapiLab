# dotgg.gg character data

The site the deck-builder draws from (nikke.gg is a WordPress front over the
`api.dotgg.gg` JSON API). No auth required.

## Endpoints

- `GET https://api.dotgg.gg/nikke/characters` — array of all characters with
  summary fields: `name`, `url` (the slug), `class`, `weapon`, `element`,
  `burst`, `rarity`. Use this to resolve a display name to its slug. Note names
  like "Anis: Star" have slug `anis-star`, "D: Killer Wife" → `d-killer-wife`.
- `GET https://api.dotgg.gg/nikke/character/<slug>` — the full character.

## Character object

Relevant top-level fields:
- Metadata: `name`, `url`, `class`, `weapon` (AR/MG/SMG/SG/RL/SR),
  `element` (Fire/Water/Wind/Iron/Electric), `burst` ("1"/"2"/"3").
- Weapon stats for normal attacks: `damage` (e.g. "61.3%", the coefficient),
  `chargeTime`, `chargeDamage` (e.g. "250%"), `reloadTime`, `maxAmmo`.
- `skills` — array of 3 skills (base, no signature weapon).
- `dollskills` — array of 3 skills **when the signature weapon ("애장품") is
  unlocked**. Absent/empty when the character has no signature weapon.

## skills vs dollskills (signature weapon)

If `dollskills` is non-empty, the character has a signature weapon whose
completed version changes the skills. **This is not just bigger numbers** — it
can add entirely new effects or slots (e.g. Privaty's EX Magazine gains a 4th
effect; burst nuke percents can triple). Ask the user whether their character
has the signature weapon completed, and build from the matching array.

## Skill object and value slots

Each skill has `name`, `cooldown` (empty for passives, a number for the burst),
`description` (free text with `{description_value_NN}` placeholders and color
markup), and `levels` — an array indexed by skill level. Use `levels[-1]` for
the max level (usually 10; the burst may be lower if the user says so).

Each level is a dict `{"description_value_01": "...", ...}`; empty strings mark
unused slots. The description text tells you what each slot is — read them
together. A dump helper:

```python
import json
d = json.load(open("char_SLUG.json", encoding="utf-8"))
skills = d.get("dollskills") or d["skills"]   # signature if present
for i, s in enumerate(skills):
    lvl = s["levels"][-1]
    vals = {k: v for k, v in lvl.items() if v != ""}
    print(f"[{i}] {s['name']} cd={s.get('cooldown')}: {vals}")
    print("   ", s["description"].replace(chr(10), " | "))
```

On Windows, prefix commands with `PYTHONIOENCODING=utf-8` (arrows and Korean in
descriptions break the default cp949 codec).

## Value-slot conventions seen so far

- A buff and its duration usually come as adjacent slots (value ▲ X% for Y sec).
- "X% of caster's ATK/DEF/Max HP" → multiply the caster's base stat (see the
  main skill's caster-scaled note).
- Escalating "Once / Twice / Three times" tiers occupy consecutive slots; take
  the steady state (all tiers or the third value — read the wording; if
  "previous effects trigger repeatedly" and the tiers are the same stat, they
  stack/sum, if different stats they all apply).
