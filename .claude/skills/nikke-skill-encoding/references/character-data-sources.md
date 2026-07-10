# NIKKE character data sources

**Primary source: lootandwaifus.com.** Use it first for every character,
including ones already covered by dotgg — it's at least as current (dotgg lags
roughly the last ~2 months of releases) and its listing page carries richer
metadata (mechanic tags) than dotgg's. Fall back to **dotgg.gg** only if
lootandwaifus is unreachable, or use it as a cross-check when a value looks
surprising (see "Cross-verification" below — the two sources matched exactly
on every value checked so far).

## lootandwaifus.com (primary)

### Character listing (name/slug/metadata lookup)

`GET https://lootandwaifus.com/nikke-characters/` — one large page listing
every character. **WebFetch returns HTTP 403** on this site (blocks
non-browser requests); always use `curl` with a browser `User-Agent`:

```bash
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://lootandwaifus.com/nikke-characters/" -o characters.html
```

Each character is an `<a href="/character/<slug>-nikke" ...>` entry. The slug
is the display name, lowercased and hyphenated, **plus a `-nikke` suffix**
(e.g. "Little Mermaid" → `little-mermaid-nikke`, "Mint" → `mint-nikke`,
"Prika" → `prika-nikke`). Not yet verified for every naming edge case (e.g.
colons like "D: Killer Wife").

The `class` attribute on each `<a>` tag is a whitespace-separated bag of CSS
classes encoding metadata directly — no need to open the character page just
to learn class/weapon/element/burst:
- Weapon: `assault-rifle` / `machine-gun` / `submachine-gun` / `shotgun` /
  `rocket-launcher` / `sniper-rifle`.
- Element: `fire` / `water` / `wind` / `iron` / `electric`.
- Class: `attacker` / `defender` / `supporter`.
- Burst tier: `burst-1` / `burst-2` / `burst-3`.
- Burst cooldown: `cd-<N>` (e.g. `cd-20`).
- Rough mechanic tags (useful for triage before even opening the page):
  `attack-buff--self-` / `attack-buff--allies-`, `critical-rate-buff--*`,
  `critical-damage-buff--*`, `increase-pierce-damage--*`, `hp-recovery--*`,
  `attack-damage-buff--allies-`, `max-ammo-capacity-increase`, etc.
- `data-character-name` / `title` carry the display name; `data-character-id`
  is lootandwaifus's internal numeric ID (not the same as dotgg's).

### Character page (skill data)

`GET https://lootandwaifus.com/character/<slug>-nikke/` (same `curl -A`
requirement). The raw HTML is server-rendered and already contains **all 10
levels'** full description text per skill (not just max level) — strip HTML
tags and read directly, no client-side JS rendering needed. Skill names,
cooldowns, and the complete free-text description (numbers already filled in
per level, not placeholder-templated) are all present in one fetch.

Unlike dotgg, there's **no `description_value_NN` placeholder structure** —
each level's text has the real numbers substituted inline. When transcribing
into a `skill_values` dict for encoding (matching this project's existing
`description_value_01`, `description_value_02`, ... convention used by every
`build_*_rules` function), number the slots by **left-to-right order of
appearance** in that skill's description text at the level you're encoding.
This is an internal numbering (only needs to be consistent between the values
dict and the encoding code reading it) — it does not need to match dotgg's
numbering for the same character, though in practice it usually will since
both sites render the same underlying game text.

Bonus content dotgg doesn't have: skill-priority recommendations, cube/OL gear
build notes, and solo-raid usage-rate charts (sourced from enikk.app) — not
currently used by the encoding workflow, but could inform which Nikkes are
worth encoding first.

## dotgg.gg (fallback / cross-check)

`api.dotgg.gg` JSON API (nikke.gg is a WordPress front over it). No auth
required.

- `GET https://api.dotgg.gg/nikke/characters` — array of all characters:
  `name`, `url` (slug), `class`, `weapon`, `element`, `burst`, `rarity`.
  Names like "Anis: Star" have slug `anis-star`, "D: Killer Wife" →
  `d-killer-wife` (no `-nikke` suffix, unlike lootandwaifus).
- `GET https://api.dotgg.gg/nikke/character/<slug>` — full character:
  `damage`/`chargeTime`/`chargeDamage`/`reloadTime`/`maxAmmo` (normal-attack
  weapon stats), `skills` (3 base skills), `dollskills` (3 skills when the
  signature weapon is completed — **not just bigger numbers**, can add whole
  new effects/slots; ask the user which their character has).
- Each skill has `name`, `cooldown`, `description` (`{description_value_NN}`
  placeholders + color markup), and `levels[]` indexed by level —
  `levels[-1]` is max (usually 10). A dump helper:
  ```python
  import json
  d = json.load(open("char_SLUG.json", encoding="utf-8"))
  skills = d.get("dollskills") or d["skills"]
  for i, s in enumerate(skills):
      lvl = s["levels"][-1]
      vals = {k: v for k, v in lvl.items() if v != ""}
      print(f"[{i}] {s['name']} cd={s.get('cooldown')}: {vals}")
      print("   ", s["description"].replace(chr(10), " | "))
  ```
  On Windows, prefix commands with `PYTHONIOENCODING=utf-8` (arrows/Korean
  break the default cp949 codec).

### Cross-verification

Little Mermaid's 3 skills, every value, at level 10, were checked against
lootandwaifus on 2026-07-10 and matched dotgg **exactly** — no discrepancies.
Treat either source as reliable; prefer lootandwaifus per the policy above.

## Value-slot conventions seen so far (apply to either source)

- A buff and its duration usually come as adjacent slots (value ▲ X% for Y sec).
- "X% of caster's ATK/DEF/Max HP" → multiply the caster's base stat (see the
  main skill's caster-scaled note).
- Escalating "Once / Twice / Three times" tiers occupy consecutive slots; take
  the steady state (all tiers or the third value — read the wording; if
  "previous effects trigger repeatedly" and the tiers are the same stat, they
  stack/sum, if different stats they all apply).
- **"Exceeds N stack(s)" means "reaches N stacks" (>= N), not a strict > N.**
  Confirmed by Fienn against in-game behavior (Nayuta's Impermanence) - a
  literal > N reading is off by one activation and can even be impossible when
  N is also the stat's max cap. Applies generally to "exceeds/stacks" stack-
  threshold wording, not just that one skill.
