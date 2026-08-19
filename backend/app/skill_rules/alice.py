"""Alice (slug "alice"), a Burst-3 Fire SR Attacker whose whole kit points at one
thing: firing her charge weapon more often.

Her burst deals no damage. Every point of her output is normal attacks, which
makes her cadence - not her buff list - the load-bearing part of this encoding.
See `registry.MANUAL_TAP_FIRE_INTERVAL` for the 17-frame tap floor she is
modelled with, and why that floor only binds inside her own burst window.

Her weapon is the hardest-charging one in the game: **Full Charge Damage 350%**
against 250% for almost every other charge weapon (Cinderella 200%, Scarlet:
Black Shadow 150%). That is what makes waiting for the charge worth it outside
her burst, and it is why the tap floor is a FLOOR rather than a cadence.

Modeled (DPS-relevant):
- Energizing Carrot (skills[0], on Full Burst entry): the 2 allies with the
  highest final ATK get Charge Speed "▲ X% of the skill user's Charge Speed"
  and Charge Damage ▲7%, both 10 sec. The charge-speed half is a CASTER-BASED
  grant, so it travels as absolute seconds (11.67% x her own 1.5 sec charge =
  0.17505 sec), the same mechanism as Liberalio's Calm Depths - encoding it as
  a percent would be wrong for every recipient whose charge time differs from
  hers. The bullet carries no "(except caster)" clause, so she competes for her
  own two slots (`include_caster=True`).
- Healthy Carrot (skills[1]): "Activates when this unit's HP is at 80% or
  above. Gains Pierce." The sim never damages allies, so the condition holds for
  the whole fight and the property is granted permanently from battle start -
  the same reading Milk: Blooming Bunny's Pierce clause gets.
- Wonderland (skills[2], her burst, cd 40): self Charge Speed +80.15% and self
  ATK +55.12%, both 10 sec. The charge speed is what opens her tap-fire window:
  it drives her 90-frame charge down to 10 frames (with the 8.96% overload roll
  on Fienn's account), well under the 17-frame tap. Her burst deals no damage,
  so the registry's burst percent is None.

Not modeled / deferred:
- Healthy Carrot's other branch ("Activates when this unit's HP is below 80%.
  Restores HP equal to 8.12% of attack damage"): the sim never damages allies,
  so the condition never becomes true and the AMOUNT is not a damage stat
  anyway. She IS listed in `_helpers.HEAL_PROVIDER_SLUGS` regardless: that list
  answers "does this deck contain a unit that heals", a question about the real
  fight rather than about the sim's HP model, and in a real fight she drops
  under 80% and heals. Crown's Royal Attire is its only consumer.
- **Partial-charge shots.** A player with fast reloads beats her full-charge
  cadence by tapping OUTSIDE her burst window too, trading the 350% multiplier
  for shots (Fienn, range test 2026-08-19, with Crown + Privaty + a level-15
  Resilience cube, which reach 125.20% Reload Speed and remove the reload
  entirely). The break-even is Reload Speed +62.4%. The engine cannot express
  it: `ShotRecord` has no "was this a full charge" property, so
  `charge_damage_percent` is applied to every shot unconditionally. Until that
  property exists, this encoding is a FLOOR for her in reload-heavy decks. See
  docs/engine-gaps.md.
"""
from app.skill_rules._helpers import buff_rule, highest_atk_buff_rule


SKILL_VALUE_MANIFESTS = {
    "alice": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_alice",
        "keys": {
            "energizing_carrot": ("skills", 0),
            "healthy_carrot": ("skills", 1),
            "wonderland": ("skills", 2),
        },
    },
}

# Energizing Carrot hands its charge speed to "2 ally unit(s) with the highest
# final ATK" and says nothing about excluding the caster, so she is a candidate
# for her own grant - see the `include_caster` axis in the capability catalog.
ENERGIZING_CARROT_TARGETS = 2


def energizing_carrot_charge_cut_seconds(values: dict, caster_weapon_stats: dict) -> float:
    """Energizing Carrot's caster-based charge grant, in absolute seconds.

    "Charge Speed ▲ X% of the skill user's Charge Speed" is a percentage OF HER
    OWN charge time, delivered to the recipient as seconds. Her charge time is
    read from her weapon rather than hardcoded so a re-synced weapon file moves
    the grant.
    """
    percent = float(values["description_value_02"]) / 100
    return percent * float(caster_weapon_stats["charge_time"])


def build_alice_rules(values):
    carrot = values["energizing_carrot"]
    wonderland = values["wonderland"]
    charge_cut = energizing_carrot_charge_cut_seconds(
        carrot, values["caster_weapon_stats"])
    charge_cut_duration = float(carrot["description_value_03"])
    charge_damage = float(carrot["description_value_04"]) / 100
    charge_damage_duration = float(carrot["description_value_05"])
    burst_charge_speed = float(wonderland["description_value_01"]) / 100
    burst_charge_duration = float(wonderland["description_value_02"])
    burst_atk = float(wonderland["description_value_03"]) / 100
    burst_atk_duration = float(wonderland["description_value_04"])
    # `healthy_carrot`'s three slots are the two branches' 80% HP thresholds and
    # the heal rate; none of them reaches the engine, so its Pierce bullet below
    # reads no value at all (see docstring).
    return [
        highest_atk_buff_rule("full_burst_enter", ENERGIZING_CARROT_TARGETS, [
            ("charge_time_reduction_sec", charge_cut, charge_cut_duration),
            ("charge_damage_bonus", charge_damage, charge_damage_duration),
        ], include_caster=True),
        buff_rule("battle_start", [
            ("has_pierce", 1.0, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("charge_speed_percent", burst_charge_speed, "self", burst_charge_duration),
            ("atk_percent", burst_atk, "self", burst_atk_duration),
        ]),
    ]
