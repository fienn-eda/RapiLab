"""Flora's Favorite Item (애장품) build, slug "flora-signature" - a SEPARATE
roster entry from base Flora (slug "flora"), per the dual-slot convention
(2026-07-12). The Favorite Item turns a pure healer into a real ATK buffer via a
combo that is entirely self-contained - it needs no incoming enemy damage.

**The combo** (Fienn's reading of the kit, 2026-07-24), all anchored to Burst
Stage 2 entry:
1. Petunia's Favorite Item bullet raises allies' Max HP by 15.01% of Flora's own
   Max HP **without restoring HP**, so their CURRENT HP is unchanged.
2. That drops every affected ally's HP RATIO below 90%, which is exactly Iris's
   first bullet's trigger ("an adjacent ally's HP drops to 90% or below").
3. Iris places a shield, which is the trigger of the Favorite Item's own Iris
   bullet: ATK +45.12% of Flora's ATK for 10 sec.

So the ATK buff is neither "always on" nor unreachable - it rides the same
per-cycle schedule as the Max-HP bullet, and is encoded on that trigger.

Weapon stats come from base Flora's ShiftyPad file via the manifest's
`weapon_source`, since ShiftyPad exposes no dollskills and dotgg is dead.

Modeled (DPS-relevant):
- Iris (dollskills[1]): squad True Damage +30.97%, permanent - same ruling as the
  base build (allies are always at max HP in the sim, Fienn 2026-07-24).
- Petunia (dollskills[0]): squad Max HP +15.01% of Flora's Max HP for 2 sec on
  entering Burst Stage 2. `flat_max_hp` stopped being inert on 2026-07-24 - it
  feeds every "ATK ▲ X% of the caster's Max HP" conversion - so this pays out
  whenever the deck holds such a consumer.
- Iris (dollskills[1]), the shield bullet: squad ATK +45.12% of Flora's ATK.
  Two paths, never both (the same bullet would land twice):
  - FLOOR - her own combo above, 10 sec on each Burst Stage 2 entry. The only
    path when nobody else in the deck shields.
  - CEILING - an ally who shields the whole squad (`SHIELD_PROVIDER_SLUGS`)
    keeps it up on a schedule the engine cannot count, since it models no shield
    event; deck presence is what can be asked, so it becomes permanent. Same
    ruling and same shape as Crown's Royal Attire heal branch. Rei: Ayanami is
    NOT in that list - her shield is Fire Code only and Flora is Electric.
- Secret Garden (dollskills[2], her burst, cd 40): squad True Damage +42.39%
  AND squad ATK +85.86% of Flora's ATK, both 10 sec. No damage, burst percent
  is None.

Both Stage-2 bullets use `ally_burst_activate` + `burst_stage_entered(2)`, not
`own_burst_activate`: entering Burst Stage 2 is a property of the STAGE, so the
bullets must still fire in a cycle where another Burst-2 ally takes the slot.
(In the engine's auto-mode cycle all three tiers fire at the same instant, so
there is no representable gap between "stage entered" and "burst used" - the
distinction that matters is WHO bursts, not when.)

"Allies in the Peace of Mind state" is Petunia's self + both adjacent allies -
Peace of Mind is granted at battle start and is continuous, so its holders are
that same three for the whole fight. Both bullets that pay it are therefore
SEATED, not squad, and use `seated_buff_rule`; the ATK one is seated on both of
its paths, since the ceiling and the floor are the same bullet. She is in
registry.SEATED_BUFF_SLUGS with no row requirement, so an end seat - one
neighbor instead of two - is among the arrangements the report path measures.

Her other bullets are genuinely squad and must stay so: Iris's True Damage and
the shield read an ADJACENT ally in their trigger but say "Affects all allies",
and Secret Garden says it outright.

Not modeled / skipped:
- The AMOUNT of every heal, shield and Incoming Healing bullet - survivability,
  not damage. Their occurrence is what the engine consumes: the shield is the
  link in the combo above, and Flora is in `HEAL_PROVIDER_SLUGS`, so a deck-mate
  whose bullet arms on any ally healing (Crown) sees her.
(Petunia's "after landing 100 normal attacks, all Electric Code allies:
Increases the stack count of stackable buffs by 1" is modeled, sharing the base
build's `build_petunia_stack_contributions` - same slots, same bullet.)
"""
from app.skill_rules._helpers import (SHIELD_PROVIDER_SLUGS, buff_rule,
                                      seated_buff_rule)
from app.squad_engine import (
    all_conditions,
    burst_stage_entered,
    deck_contains_any,
    not_condition,
)


SKILL_VALUE_MANIFESTS = {
    "flora-signature": {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "flora",
        "test_module": "test_skill_rules_flora_signature",
        "keys": {
            "petunia": ("dollskills", 0),
            "iris": ("dollskills", 1),
            "secret_garden": ("dollskills", 2),
        },
    },
}

BURST_STAGE = 2  # she is Burst 2; her Petunia bullet keys off entering that stage
# The stack-count bullet's ("attacks", "stacks") pair. Her manifest reads
# lootandwaifus, which numbers this bullet one slot later than the base build's
# shiftypad source - see flora.PETUNIA_STACK_SLOTS.
PETUNIA_STACK_SLOTS = ("description_value_04", "description_value_05")


def build_flora_signature_rules(values):
    petunia = values["petunia"]
    iris = values["iris"]
    garden = values["secret_garden"]
    caster_atk = values["caster_atk"]
    caster_max_hp = values["caster_max_hp"]
    max_hp_bonus = caster_max_hp * float(petunia["description_value_07"]) / 100
    max_hp_duration = float(petunia["description_value_08"])
    iris_true_damage = float(iris["description_value_04"]) / 100
    shield_atk = caster_atk * float(iris["description_value_06"]) / 100
    shield_atk_duration = float(iris["description_value_07"])
    burst_true_damage = float(garden["description_value_02"]) / 100
    burst_true_duration = float(garden["description_value_03"])
    burst_atk = caster_atk * float(garden["description_value_04"]) / 100
    burst_atk_duration = float(garden["description_value_05"])
    stage_two = burst_stage_entered(BURST_STAGE)
    shielded_by_ally = deck_contains_any(SHIELD_PROVIDER_SLUGS)
    return [
        buff_rule("battle_start", [
            ("true_damage_up", iris_true_damage, "squad", None),
        ]),
        # An ally who shields the whole squad keeps the bullet up on their own
        # schedule, which the engine cannot count - deck presence is what can be
        # asked, so this is the ceiling (Crown's Royal Attire precedent).
        seated_buff_rule("battle_start", [
            ("flat_atk", shield_atk, None),
        ], condition=shielded_by_ally),
        seated_buff_rule("ally_burst_activate", [
            ("flat_max_hp", max_hp_bonus, max_hp_duration),
        ], condition=stage_two),
        # Her own combo is the floor and the only path when nobody else shields.
        # The two never run together: the same bullet would land twice.
        seated_buff_rule("ally_burst_activate", [
            ("flat_atk", shield_atk, shield_atk_duration),
        ], condition=all_conditions(stage_two, not_condition(shielded_by_ally))),
        buff_rule("own_burst_activate", [
            ("true_damage_up", burst_true_damage, "squad", burst_true_duration),
            ("flat_atk", burst_atk, "squad", burst_atk_duration),
        ]),
    ]
