"""Sakura: Bloom in Summer (slug "sakura-bloom-in-summer"), a Burst-3 Wind AR
attacker. Collected from lootandwaifus.com.

Her damage is two DoTs. Sakura Petals runs off Full Glory, which Bloom force-
fires at battle start and which then repeats on its own 30s cooldown - so its
whole timeline (t=0, 30, 60, ...) is fixed before the fight starts and needs
nothing from the deck. That makes it a `scheduled_nukes` schedule that ignores
the context entirely.

Modeled (DPS-relevant):
- Bloom (skills[0]) force-fires Full Glory at battle start, so Full Glory lands
  at t=0 and every 30 sec after - NOT the usual "first fires at t=cooldown".
- Full Glory (skills[1], cd 30):
  - Dancing Flower: self Attack Damage +15.64% for 15 sec. 50% uptime, since the
    buff is half as long as the cooldown - modeled per activation, not flattened
    to a steady state.
  - Sakura Petals: 256% of final ATK as sustained damage every 1 sec for 15 sec,
    on `scheduled_nukes`. "The enemy with the highest final ATK" is the solo
    raid's only boss.
- Ephemeral Spender (skills[2], her burst):
  - 457.14% attacking sequentially 10 times - 10 separate hits (`burst_hit_counts`),
    since defense is subtracted per hit.
  - A 35.16%/sec sustained DoT for 10 sec at TEN stacks: each of those 10 hits
    lays down its own stack, which is why the hit count and the stack cap are
    both 10 (Fienn 2026-07-17). Modeled as 351.6%/sec for 10 ticks.

Not modeled / deferred:
- All three of Bloom's part-destruction riders - self Sustained Damage +5.1%/30s,
  Dancing Flower Duration +10.02s, Sakura Petals Duration +10.02s. The engine has
  no concept of parts or of destroying them (see engine-gaps.md gap #2 Pattern B),
  so there is no honest trigger to hang them on. All three would only ADD damage,
  so this encoding is a floor.
"""
from app.skill_rules._helpers import buff_rule

SKILL_VALUE_MANIFESTS = {
    "sakura-bloom-in-summer": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_sakura_bloom_in_summer",
        "keys": {
            "bloom": ("skills", 0),
            "full_glory": ("skills", 1),
            "ephemeral_spender": ("skills", 2),
        },
        # skill1's "Forcefully uses Skill 2" names a skill, it isn't a value.
        "drop_tokens": {"bloom": (0,)},
    },
}

# Bloom force-fires Full Glory at t=0; it then repeats on its own cooldown.
FULL_GLORY_COOLDOWN = 30.0
# "Attacks sequentially 10 times". It IS a data slot, but reads 10 at every skill
# level, and get_burst_hit_count only takes a slug - so a constant, like Cinderella's.
EPHEMERAL_SPENDER_HIT_COUNT = 10


def _full_glory_times(fight_duration):
    times, t = [], 0.0
    while t < fight_duration:
        times.append(t)
        t += FULL_GLORY_COOLDOWN
    return times


def ephemeral_spender_burst_percent(values):
    return float(values["ephemeral_spender"]["description_value_01"])


def ephemeral_spender_burst_hit_count(values):
    return int(float(values["ephemeral_spender"]["description_value_02"]))


def build_sakura_bloom_in_summer_rules(values):
    """Dancing Flower, on every Full Glory. Bloom's battle-start force-fire is
    the t=0 activation; `periodic_rules` covers t=30, 60, ..."""
    full_glory = values["full_glory"]
    attack_damage = float(full_glory["description_value_01"]) / 100
    duration = float(full_glory["description_value_02"])
    return [buff_rule("battle_start", [("attack_damage_up", attack_damage, "self", duration)])]


def build_sakura_periodic_rules(values):
    full_glory = values["full_glory"]
    attack_damage = float(full_glory["description_value_01"]) / 100
    duration = float(full_glory["description_value_02"])
    return [(FULL_GLORY_COOLDOWN, [
        buff_rule("periodic", [("attack_damage_up", attack_damage, "self", duration)]),
    ])]


def build_sakura_scheduled_nukes(values):
    """Sakura Petals: a 15-tick sustained DoT on each Full Glory. The schedule is
    fixed by Full Glory's cooldown alone, so it reads nothing off the context."""
    full_glory = values["full_glory"]
    percent = float(full_glory["description_value_03"])
    tick_interval = float(full_glory["description_value_04"])
    duration = float(full_glory["description_value_05"])
    tick_count = int(duration / tick_interval)

    def schedule(context, fight_duration):
        return [
            cast + tick_interval * n
            for cast in _full_glory_times(fight_duration)
            for n in range(1, tick_count + 1)
        ]

    return [{"schedule": schedule, "percent": percent, "damage_type": "sustained"}]


def build_sakura_resource_scaled_nukes(values):
    """Ephemeral Spender's DoT. Its 10 sequential hits each lay a stack, so all
    ten are live from the cast - one tick at 10x the per-stack percent (Fienn
    2026-07-17). No resource: the stack count never varies."""
    spender = values["ephemeral_spender"]
    per_stack = float(spender["description_value_03"])
    tick_interval = float(spender["description_value_04"])
    stacks = int(float(spender["description_value_05"]))
    duration = float(spender["description_value_06"])
    return [{
        "base_percent": per_stack * stacks,
        "tick_count": int(duration / tick_interval),
        "tick_interval": tick_interval,
        "damage_type": "sustained",
    }]
