# NIKKE damage formula — Glossary & Notes (authoritative reference)

Source: **https://nikke.gg/damage-formula/** — the same page the engine's
`damage_formula.py` is built from. This file preserves the page's **Glossary**
(https://nikke.gg/damage-formula/#Glossary) and **Notes**
(https://nikke.gg/damage-formula/#Notes) because they are the authoritative rules
for *how each buff/damage type applies*, and are easy to get wrong. Fienn asked
that this be accessible to Fienn, the main agent, and subagents — consult it
before deciding which multiplier group a buff belongs to or how a damage type
behaves. Quoted/paraphrased from nikke.gg; re-fetch the page if anything looks
stale.

The formula itself (Base Damage × Final ATK modifiers × Major Modifiers ×
Element Bonus × Charge Damage × Damage Up × Damage Taken) lives in
`backend/app/damage_formula.py`; this doc is the *glossary/notes* around it.

## Glossary (key groups)

**Base Damage** = `Base Attack × (1 + ATK%) + flat ATK  −  (Enemy Base DEF × (1 + DEF%) + flat DEF)`.
- ATK% includes all standard ATK% modifiers (incl. reductions).
- "% Caster's ATK" = flat, additive ATK buffs (incl. HP→ATK conversions, e.g. 2B, Cinderella).
- "% caster's DEF" — only Mast has this currently.

**Final ATK modifiers** — directly modify a skill/normal-attack's base multiplier.
- *Final ATK modifier* itself is "incredibly rare".
- **Normal Attack Damage Multiplier** — a lesser version that only affects the **user's normal-attack** damage (e.g. Asuka: Wille's Annihilation −40%).

**Major Modifiers** (occur without secondary buffs): Critical Damage (base 150% = 0.5; base crit rate 15%), Core Damage (base ~200% = 1), Full Burst Bonus (base 50%), Effective Range Bonus (base 30%; **Rocket Launchers cannot benefit**).

**Element Bonus Damage** — +10% (×1.1) only with elemental advantage.

**Charge Damage** — Charge weapons' normal attacks only (**Sniper Rifles and Rocket Launchers**); base usually 250% (×1.5).

### Damage Up — "Outside of Attack Damage, all of these are exclusive and strictly buff what they specify."
- **Attack Damage** — a **general** damage-up buff. **Affects all damage dealt.**
- **Sustained Damage** — only Sustained Damage (a constant damaging effect over a duration).
- **True Damage** — only True Damage, **which ignores enemy DEF.**
- **Pierce Damage** — only Pierce (normal attacks hitting everything in their path).
- **Damage To Parts** — only Parts. Strong with Pierce or Projectile Explosion.
- **Damage to Interruption Parts** — only Interruption Parts (see Notes; usually doesn't affect the boss itself).
- **Shield Damage** — only Shields. Shields ignore Major Modifiers, Damage Taken debuffs, and Element Bonus; only take Normal Attack damage; can be bypassed by Pierce.
- **Projectile Explosion Damage** — **exclusive to Rocket Launchers' basic attack**, plus certain non-RL weapons that are buffed by it regardless.

### Damage Taken (a debuff group — modifies damage received)
- **Damage Taken** — all Damage Taken modifiers (incl. reductions).
- **Distributed Damage** — a buff *on a Nikke* but it enters the equation here. Usually bases its damage on the lowest-DEF target and splits evenly across enemies.

## Notes (nuances that are easy to miss)

- Buffs sharing the same category/color are the **same multiplier** (i.e. they add, not multiply): e.g. True Damage + Damage to Parts (if a part is hit); Critical Damage + Full Burst Bonus.
- **Core Damage** only applies to hits on the core; no core on the target → no bonus.
- A target's defense **cannot drop below 0** through DEF% debuffs.
- If a **Rocket** hits multiple targets, only the primary target can get the Core Damage bonus; the rest take splash unaffected by that multiplier.
- Damage to Interruption Parts normally boosts only the red/grey interrupt circles; but if a basic attack hitting an Interruption Part overlaps the boss hitbox, the boss takes extra damage by that multiplier.
- Damage Taken and Distributed Damage are effectively the same DPS modifier, **but** a Distributed Damage debuff only affects Distributed Damage sources against enemies that have a **Damage Taken ▲** buff.
- Damage Taken and DEF% debuffs do nothing to enemies/projectiles that take a **fixed** amount of damage (typically 1).
- Certain Nikkes modify the base final ATK of their skills (e.g. **Bready, EVE**).
- SG and SMG Collection Items boost the Normal Attack Damage Multiplier of Nikkes that equip them; RL/SR Collection Items (and Helm's max-Treasure Burst) boost Charge Damage by `Charge Damage Multiplier × Base Charge Damage` (other charge-damage sources not considered for that).
- **Rapi: Red Hood's Attachable Projectile Explosions, and Anis: Star's Stars (from activating her Burst) benefit from Projectile Explosion Damage.**
- *Possible unintended error:* weapon-transforming Nikkes don't use their equipped collection item's unique stat modifier (negatively affects Zwei, Nayuta, K, Snow White, E.H.).

## Implications for this engine (how the above maps to our code)

- **Damage typing** (`raid_simulator._TYPE_BUCKETS`) implements the "exclusive" Damage-Up buckets: Sustained / True / Projectile Explosion / Distributed apply only to matching-type instances; **Attack Damage stays global** ("affects all damage dealt"). See `engine-capabilities.md` "Damage typing".
- **True Damage ignores DEF** — a `true`-typed instance is computed with `enemy_def=0`.
- **Projectile Explosion** — RL normal attacks are `projectile_explosion` typed; skills explicitly confirmed here (Rapi: Red Hood, Anis: Star's burst stars) are tagged too.
- **Distributed Damage** sits in the Damage-Taken group in the formula (as coded), with the extra real-game caveat above (only vs enemies already under Damage Taken ▲) — not yet modeled.
- Not modeled yet (deferred): Normal Attack Damage Multiplier, Shield Damage, Damage to Interruption Parts vs boss-hitbox overlap, Effective Range / Full Burst major-modifier buffs, collection-item stat modifiers, DEF floor at 0.
