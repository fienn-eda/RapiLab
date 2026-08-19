"""Alice (slug "alice"), a Burst-3 Fire SR Attacker whose whole kit points at one
thing: firing her charge weapon more often.

Her burst deals no damage. Every point of her output is normal attacks, which
makes her cadence - not her buff list - the load-bearing part of this encoding.
Two measured numbers carry it, both from Fienn's frame reading of 2026-08-19
(docs/measurements/alice-tap-fire.md):

- **Her fire-to-charge pause is 15 frames**, the shortest in
  `registry.TIMED_CHARGE_MOTION_DELAY` and a counterexample to handing untimed
  charge weapons the 22-frame stand-in.
- **She is a tap-fire candidate** (`registry.TAP_FIRE_CANDIDATES`): releasing at
  the start of the charge fires a 100% shot every 15 frames, and the engine
  weighs that against a full charge once per magazine. Which one wins is the
  DECK's answer, not hers - reload speed decides it, so she taps outside her
  burst window in a Crown + Privaty + Resilience-cube deck and full-charges
  everywhere else.

Her weapon is the hardest-charging one in the game: **Full Charge Damage 350%**
in the data file (250% for almost every other charge weapon; Cinderella 200%,
Scarlet: Black Shadow 150%), and 383% on Fienn's account once the collectible's
charge-damage multiplier is on. That is why waiting for the charge is usually
worth it, and why the tap only wins where the reload has been removed.

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
- **Partial holds between the two ends.** The engine only ever fires a full
  charge or a bare tap, because nothing in between can win: damage is linear in
  the gauge and the interval is that hold plus a fixed pause, so the efficiency
  `multiplier(h) / (h + delay)` is monotone in h and the optimum is always an
  endpoint (`attack_rate.tap_fire_wins`). A player who releases half-way is
  therefore modelled as doing worse than either mode, which is what the
  arithmetic says they are doing.
- **The frame a tap does bank.** A tap is modelled at exactly 100%, but a real
  hand holds one or two frames and Fienn's readings came out at 104% and 107%.
  The engine therefore UNDERSTATES a tapped shot by 3-7%, which is the safe
  direction: it can only make the recommender prefer tapping less often than the
  game does, never more.
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
