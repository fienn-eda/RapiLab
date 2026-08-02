"""Tove (slug "tove") and her Favorite Item build (slug "tove-signature"), a
Burst-1 AR supporter. Collected from lootandwaifus.

The two builds are separate deck candidates (dual-slot); which one a user fights
with comes from their roster's per-unit `favorite_item` flag.

Uniquely among the split units, both builds share every slot MEANING - only the
numbers move - so one builder serves both. The Favorite Item raises the squad
Crit Rate 3.32% -> 10.08% and stretches both Miracle of Makeshifts windows
10 -> 15 sec; the SG Attack Speed and the two ATK coefficients are identical.

Modeled (DPS-relevant):
- Emergency-Crafted Bullets (dollskills[0]): the Temporary Modification stack
  itself - squad Max Ammunition Capacity +2 ROUNDS per stack (a flat round
  count, not a percent - `max_ammo_rounds`, converted against each recipient's
  own base magazine in raid_simulator) plus the block's squad Critical Damage
  +5.24%. Both continuous under the full-stack assumption below. The crit
  damage does NOT mirror the stack count: "stacks up to 3 time(s)" sits on the
  Max Ammo line only, so it lands once.
- Modification Successful (dollskills[1]): squad Crit Rate up (continuous while
  Temporary Modification is fully stacked); shotgun allies additionally get
  Attack Speed +42.24% continuously (member-subset scope, gap #3 - live-read
  per magazine, so SG allies genuinely fire more shots).
- Miracle of Makeshifts (dollskills[2], her burst): squad ATK up as a flat
  bonus scaled off Tove's own ATK, mirroring the Temporary Modification stack
  count; shotgun allies get a second, bigger ATK bullet (+24.21% of caster ATK
  per stack) with the same "mirrors the stack count" wording, so it uses the
  same max-stack multiplier.

Assumption: Temporary Modification is treated as fully stacked, so the Crit Rate
/ SG Attack Speed are always on and both Miracle bullets use the max stack
multiplier. That is now derived rather than asserted, and it holds on BOTH
builds despite their different triggers (Fienn, 2026-07-24):

  The Favorite Item stacks on "every 10 normal attacks". The base stacks on a
  "5% chance when attacking", which this engine cannot roll - taken at expected
  value that is one proc per 20 shots. At the engine's AR cadence (12 shots/sec)
  20 shots is ~1.7 sec, so the 3-stack cap is reached by ~60 shots (~5 sec) and
  the ~1.7-sec refill interval stays well inside each stack's 5-sec life, so it
  never decays back. In a 180-sec fight the assumption is therefore wrong only
  for the opening ~5 sec, and it is the base build - the weaker one - that
  carries the small overcredit.

Not modeled (both builds):
- Emergency-Crafted Bullets' own partial reload ("Reload 5.31% of the
  magazine(s)"): the engine reloads a magazine as one uninterruptible block, so
  a fractional top-up mid-magazine has nowhere to land. It shortens her own
  downtime slightly and she is a supporter, so the omission is small.
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule


SKILL_VALUE_MANIFESTS = {
    "tove": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "emergency_crafted_bullets": ("skills", 0),
            "modification_successful": ("skills", 1),
            "miracle_of_makeshifts": ("skills", 2),
        },
        "fixtures": {
            "emergency_crafted_bullets": "TOVE_BASE_EMERGENCY_CRAFTED_BULLETS",
            "modification_successful": "TOVE_BASE_MODIFICATION_SUCCESSFUL",
            "miracle_of_makeshifts": "TOVE_BASE_MIRACLE_OF_MAKESHIFTS",
        },
    },
    "tove-signature": {
        "source": "lootandwaifus",
        "data_slug": "tove",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "emergency_crafted_bullets": ("dollskills", 0),
            "modification_successful": ("dollskills", 1),
            "miracle_of_makeshifts": ("dollskills", 2),
        },
        "fixtures": {
            "emergency_crafted_bullets": "TOVE_SIG_EMERGENCY_CRAFTED_BULLETS",
            "modification_successful": "TOVE_SIG_MODIFICATION_SUCCESSFUL",
            "miracle_of_makeshifts": "TOVE_SIG_MIRACLE_OF_MAKESHIFTS",
        },
    },
}


def build_tove_rules(values):
    emergency = values["emergency_crafted_bullets"]
    modification = values["modification_successful"]
    miracle = values["miracle_of_makeshifts"]
    caster_atk = values["caster_atk"]
    # Every "mirrors the Temporary Modification stack count" bullet in the kit
    # reads its cap from here, so the number lives in one place.
    max_stacks = int(float(emergency["description_value_04"]))
    ammo_rounds = float(emergency["description_value_03"]) * max_stacks
    crit_damage = float(emergency["description_value_06"]) / 100
    crit_rate = float(modification["description_value_01"]) / 100
    atk_per_stack = caster_atk * float(miracle["description_value_01"]) / 100
    atk_bonus = atk_per_stack * max_stacks
    atk_duration = float(miracle["description_value_02"])
    sg_attack_speed = float(modification["description_value_02"]) / 100
    sg_atk = caster_atk * float(miracle["description_value_03"]) / 100 * max_stacks
    sg_atk_duration = float(miracle["description_value_04"])

    sg_only = lambda m, context: m.weapon == "SG"

    return [
        buff_rule("battle_start", [
            ("crit_rate", crit_rate, "squad", None),
            ("max_ammo_rounds", ammo_rounds, "squad", None),
            ("other_critical_damage_sources", crit_damage, "squad", None),
        ]),
        buff_rule("own_burst_activate", [("flat_atk", atk_bonus, "squad", atk_duration)]),
        # Modification Successful: continuous under the module's existing
        # full-stack steady-state assumption, like the squad crit rate.
        member_subset_buff_rule("battle_start", sg_only,
                                [("attack_speed_percent", sg_attack_speed, None)]),
        member_subset_buff_rule("own_burst_activate", sg_only,
                                [("flat_atk", sg_atk, sg_atk_duration)]),
    ]
