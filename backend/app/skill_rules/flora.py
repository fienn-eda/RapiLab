"""Flora (slug "flora"), a Burst-2 Electric MG Supporter. She is a healer, so
almost her whole kit is outside the damage model - what she contributes to a
raid deck is True Damage.

Modeled (DPS-relevant):
- Iris (skills[1]): squad True Damage +30.97%, permanent. The skill text gates it
  on "when either adjacent ally reaches max HP", but the sim never damages
  allies, so they are always at max HP - Fienn ruled it always-on (2026-07-24).
  Adjacency has no scope model, so the squad-wide half of the bullet is what
  lands (Rouge's precedent for "self + both adjacent allies"). Modelling it as
  permanent also erases the base/Favorite-Item duration difference on this
  bullet (5 sec vs 10 sec), which is the cost of the ruling.
- Secret Garden (skills[2], her burst, cd 40): squad True Damage +42.39% for
  10 sec. A separate source from Iris, so the two sum. Her burst deals no
  damage, so the registry's burst percent is None.

Not modeled / skipped:
- Every heal, shield and Incoming Healing bullet (Petunia's 1%/sec regen and
  +4% Incoming Healing, Iris's 10.22% Max-HP shield, Secret Garden's 10.45%
  Max-HP heal) - survivability, not damage.
- Petunia's "after landing 100 normal attacks, all Electric Code allies:
  Increases the stack count of stackable buffs by 1". The 100-shot counter is
  expressible (per_shot_rules), but the EFFECT is not: the engine has no notion
  of reaching into another unit's stackable buff and incrementing its count.
  Deferred as a whole rather than encoded as some substitute stat.
"""
from app.skill_rules._helpers import buff_rule


SKILL_VALUE_MANIFESTS = {
    "flora": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_flora",
        "keys": {
            "iris": ("skills", 1),
            "secret_garden": ("skills", 2),
        },
    },
}


def build_flora_rules(values):
    iris = values["iris"]
    garden = values["secret_garden"]
    iris_true_damage = float(iris["description_value_04"]) / 100
    burst_true_damage = float(garden["description_value_02"]) / 100
    burst_duration = float(garden["description_value_03"])
    return [
        buff_rule("battle_start", [
            ("true_damage_up", iris_true_damage, "squad", None),
        ]),
        buff_rule("own_burst_activate", [
            ("true_damage_up", burst_true_damage, "squad", burst_duration),
        ]),
    ]
