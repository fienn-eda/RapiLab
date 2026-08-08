"""Naga (slug "naga"), a Burst-2 Electric SG supporter.
Values from ShiftyPad; effect text cross-read from lootandwaifus.

Modeled (DPS-relevant):
- Guardian of Friendship (skills[0]): when a shield is placed in front of her,
  squad "Damage dealt when attacking core" +85.17% for 10 sec. The engine
  models no shield EVENT, so deck presence is the question that can be asked -
  `deck_contains_any(SHIELD_PROVIDER_SLUGS)` promotes it to permanent, the
  CEILING, exactly as Flora's Iris bullet is ruled. Unlike Flora she has no
  floor: nothing in her own kit places a shield in front of her, so with no
  shielder in the deck the bullet simply never fires.
- Support of Friendship (skills[1]): every 5 of her own normal attacks, the 2
  highest-ATK allies get core damage +40.07% for 5 sec. `per_shot_rules` mode
  "every" plus `highest_atk_buff_rule(..., refreshing=True)` - the refresh is
  load-bearing, not cosmetic: her shotgun reaches the 5th round every 3.3-5.0
  sec against a 5-sec buff, so every re-application overlaps the live one and
  plain adds would sum into a multiple of the printed value.

  She competes for her own two slots (`include_caster=True`): the bullet says
  only "2 ally unit(s) with the highest ATK", with no "except caster" clause,
  and such a bullet includes the caster whenever she meets its conditions
  (Fienn, 2026-08-08). The clause IS spelled out when it applies - Miranda's,
  Mana's and Soda's text all carry it.
- As Long As We're With Friends (skills[2], her burst, cd 20):
  - self Pierce for 10 sec (`has_pierce`), which on a boss whose core sits in
    front of its body turns each of her normal attacks into a second instance.
  - squad ATK +16.18% of HER ATK for 10 sec, unconditional.
  - squad ATK +31.02% of HER ATK for 10 sec, on the same shield condition as
    Guardian of Friendship. Timed here rather than permanent: the bullet's own
    "for 10 sec" is anchored to her burst, which the engine does schedule, so
    only the shield question needs the deck-presence stand-in.

Both core-damage bullets are gated by the engine on `core_hittable` - against a
coreless boss they pay nothing, which is correct.

Not modeled / deferred:
- "After 12 normal attacks, all allies: restores 14.57% of cover HP". The
  cover's health is not a damage quantity, and the cover is not a unit
  receiving recovery (which is why it does not put her in HEAL_PROVIDER_SLUGS
  by itself).
- Support of Friendship's second bullet, "the 2 allies with the lowest HP
  percentage recover 9.58% of her Max HP". The AMOUNT is survivability; the
  heal's OCCURRENCE is what a deck-mate like Crown arms on, so she IS in
  `HEAL_PROVIDER_SLUGS` for this bullet. Targeting by lowest HP percentage is
  undefined in a sim that never damages allies - another reason the amount
  stays out.
"""
from app.skill_rules._helpers import (
    SHIELD_PROVIDER_SLUGS,
    buff_rule,
    highest_atk_buff_rule,
)
from app.squad_engine import deck_contains_any


SKILL_VALUE_MANIFESTS = {
    "naga": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_naga",
        "keys": {
            "guardian_of_friendship": ("skills", 0),
            "support_of_friendship": ("skills", 1),
            "as_long_as_were_with_friends": ("skills", 2),
        },
    },
}


# "Activates after 5 normal attack(s)" - the trigger cadence of Support of
# Friendship, named here because the tests reason about it directly.
SUPPORT_SHOT_COUNT = 5


def build_support_of_friendship_per_shot_rules(support):
    """Every 5th shot, core damage on the 2 highest-ATK allies (see
    raid_simulator's `per_shot_rules`)."""
    shots = int(float(support["description_value_01"]))
    targets = int(float(support["description_value_02"]))
    core_damage = float(support["description_value_03"]) / 100
    duration = float(support["description_value_04"])
    return [
        (shots, "every", [
            highest_atk_buff_rule(
                "per_shot", targets,
                [("other_core_damage_sources", core_damage, duration)],
                refreshing=True, include_caster=True,
            ),
        ]),
    ]


def build_naga_rules(values):
    guardian = values["guardian_of_friendship"]
    friends = values["as_long_as_were_with_friends"]
    caster_atk = values["caster_atk"]

    shielded_core_damage = float(guardian["description_value_03"]) / 100
    pierce_duration = float(friends["description_value_01"])
    squad_atk = float(friends["description_value_02"]) / 100 * caster_atk
    squad_atk_duration = float(friends["description_value_03"])
    shielded_atk = float(friends["description_value_04"]) / 100 * caster_atk
    shielded_atk_duration = float(friends["description_value_05"])

    someone_shields = deck_contains_any(SHIELD_PROVIDER_SLUGS)

    return [
        # Permanent, not the text's 10 sec: with no shield event to count, deck
        # presence is all that can be asked, and presence means it is kept up.
        buff_rule(
            "battle_start",
            [("other_core_damage_sources", shielded_core_damage, "squad", None)],
            condition=someone_shields,
        ),
        buff_rule("own_burst_activate", [
            ("has_pierce", 1.0, "self", pierce_duration),
            ("flat_atk", squad_atk, "squad", squad_atk_duration),
        ]),
        buff_rule(
            "own_burst_activate",
            [("flat_atk", shielded_atk, "squad", shielded_atk_duration)],
            condition=someone_shields,
        ),
    ]
