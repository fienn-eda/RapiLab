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

**Major Modifiers** (occur without secondary buffs): Critical Damage (base 150% = 0.5; base crit rate 15%), Core Damage (base ~200% = 1), Full Burst Bonus (base 50%), Effective Range Bonus (base 30%; **Rocket Launchers cannot benefit** — see below).

They share ONE additive bucket. A non-crit instance is `1 + core + full_burst + effective_range`; a crit adds `0.5 + critical_damage_up` to that same sum. This is why a crit/non-crit pair of the SAME instance is the sharpest probe there is: everything else cancels and the bucket falls out as `(0.5 + crit_damage_up) / (crit/non-crit − 1)`.

#### Effective Range Bonus — which weapon at which distance

Increases **normal attack damage** when the Nikke's weapon matches the opponent's distance. Base value **30%**. Two exclusions decide whether a unit can ever see it:

| Opponent distance | Weapons that benefit |
|---|---|
| Near | SG, SMG |
| Mid | AR, MG |
| Far | SR |
| — | **RL: never**, at any distance |

- **Normal attacks only.** A skill's damage — a burst nuke, a per-shot rider, a DoT — does not collect it, the same way Core Damage does not. (The one summon exception that applies to Core also applies here in principle; no encoded unit needs it yet.)
- **RL is excluded outright**, which is a fact you can measure with rather than around: an RL unit's non-crit normal attack has a major bucket of exactly `1 + core + full_burst`, with no range term to guess at. Anis: Star's range footage reads 1.000000 before her burst and 1.500000 inside Full Burst for exactly this reason (2026-07-28) — do not read that as "she was standing out of range".
- The engine has no concept of distance, so `effective_range_bonus` is currently never set and every unit computes as out-of-range. Wiring it needs a decision about what fraction of real play is in range, NOT just a flag: see `docs/engine-gaps.md` #16. When that lands, RL units must stay excluded regardless of the answer.

**Element Bonus Damage** — +10% (×1.1) only with elemental advantage.

**Charge Damage** — Charge weapons' normal attacks only (**Sniper Rifles and Rocket Launchers**); base usually 250% (×1.5).

### Damage Up — "Outside of Attack Damage, all of these are exclusive and strictly buff what they specify."
- **Attack Damage** — a **general** damage-up buff. **Affects all damage dealt.**
- **Sustained Damage** — only Sustained Damage (a constant damaging effect over a duration).
- **True Damage** — only True Damage, **which ignores enemy DEF.**
- **Pierce Damage** — only Pierce (normal attacks hitting everything in their path). Two conditions, not one: the unit must HAVE Pierce (`has_pierce`, the [관통 특화] / "Gain Pierce" marker) **and** the damage instance must be her normal attack. A skill nuke fired by a piercing unit is not pierce damage and collects none of this bucket (Fienn, Snow White range footage 2026-07-28).
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
- Damage Taken and Distributed Damage are effectively the same DPS modifier. (The page adds "a Distributed Damage debuff only affects Distributed Damage sources against enemies with a **Damage Taken ▲** buff" — but **Fienn verified in-game (2026-07-11) that a Distributed Damage buff DOES apply with no Damage Taken debuff present**. So do NOT gate `distributed_damage_up` on a Damage Taken debuff; apply it unconditionally, as the engine already does. The page's caveat is inaccurate or narrower than its wording.)
- Damage Taken and DEF% debuffs do nothing to enemies/projectiles that take a **fixed** amount of damage (typically 1).
- Certain Nikkes modify the base final ATK of their skills (e.g. **Bready, EVE**).
- SG and SMG Collection Items boost the Normal Attack Damage Multiplier of Nikkes that equip them; RL/SR Collection Items (and Helm's max-Treasure Burst) boost Charge Damage by `Charge Damage Multiplier × Base Charge Damage` (other charge-damage sources not considered for that). **The "not considered" clause is Fienn-measured (2026-08-03)**: Snow White: Heavy Arms' charge shot against the 41.9% Auto Fire hit from the same shot, with and without her own `Charge Damage ▲528%`, gives 2.9292601 — matching "the buff is NOT scaled" to 3.6e-05, while "the buff is scaled too" misses by 6.24%. The same reading rules out the collectible failing to scale the BASE charge damage, which would predict the same 3.112. See `docs/measurements/collectible-charge-damage-in-transform.md`.
- **Rapi: Red Hood's Attachable Projectile Explosions, and Anis: Star's Stars (from activating her Burst) benefit from Projectile Explosion Damage.**
- *Possible unintended error:* weapon-transforming Nikkes don't use their equipped collection item's unique stat modifier (negatively affects Zwei, Nayuta, K, Snow White, E.H.). **Refuted — Fienn measured in-game (2026-08-03, deck Anis/Brid/Soline/Helm: Aquamarine/Snow White, 작열-element firing range, NEAR position) that a weapon-transforming Nikke's collectible bonus DOES apply during the transform**: Snow White's Seven Dwarves: I transformed burst shot carries her AR collectible's Core Damage +17.04% into the major-modifier bucket, matching prediction to a residual of 5.2e-06 outside Full Burst and 4.9e-08 inside Full Burst; dropping the collectible term from the prediction misses by 6.8%. See `docs/measurements/collectible-during-weapon-transform.md`. One narrower case is NOT refuted by this measurement: RL/SR collectibles placed on the weapon's own base stat (`charge_damage_percent`, "weapon" placement) are read from a static per-segment profile a weapon-mode segment never re-derives from — that gap is real and still open, see `docs/engine-gaps.md`.

## Implications for this engine (how the above maps to our code)

- **Damage typing** (`raid_simulator._TYPE_BUCKETS`) implements the "exclusive" Damage-Up buckets: Sustained / True / Projectile Explosion / Distributed apply only to matching-type instances; **Attack Damage stays global** ("affects all damage dealt"). See `engine-capabilities.md` "Damage typing".
- **True Damage ignores DEF** — a `true`-typed instance is computed with `enemy_def=0`.
- **Projectile Explosion** — RL normal attacks are `projectile_explosion` typed; skills explicitly confirmed here (Rapi: Red Hood, Anis: Star's burst stars) are tagged too.
- **Distributed Damage** sits in the Damage-Taken group in the formula (as coded) and is applied **unconditionally** (no Damage-Taken-debuff prerequisite — Fienn-verified, see Notes). Correctly modeled once a distributed-damage dealer is encoded (the buff is type-gated to `distributed` instances, which none are produced yet).
- Not modeled yet (deferred): Shield Damage, Damage to Interruption Parts vs boss-hitbox overlap, Effective Range / Full Burst major-modifier buffs, DEF floor at 0.
