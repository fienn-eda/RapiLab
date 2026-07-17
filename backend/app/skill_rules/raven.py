"""Raven (slug "raven"), a Burst-3 Iron RL attacker. Collected from
lootandwaifus.com.

Her damage is Shock Wave: every Full Charge starts a 5-second sustained DoT on
the boss, and they stack. Her RL fires a Full Charge every ~1 sec inside a
6-round magazine, so several are always live at once - this is what her kit is,
not a rounding detail. The DoT rides on `scheduled_nukes` reading her own shot
times off the context.

Modeled (DPS-relevant):
- Shock Wave (skills[0]):
  - Per Full Charge: 68.46% of final ATK as sustained damage every 1 sec for 5
    sec. Overlapping instances stack, which the schedule reproduces by emitting
    all five ticks per shot.
  - On entering Full Burst: self ATK +47.52% OF THE SKILL USER'S ATK for 10 sec -
    caster-scaled, so it reads `caster_atk`.
- Tempest (skills[2], her burst): 492.3% burst nuke ("all enemies including
  parts" collapses to the one boss), plus A.N. Mode's self Sustained Damage
  +89.44% for 10 sec - which multiplies the Shock Wave ticks.
- Single Point Attack (skills[1]) is bracketed on the boss, NOT dropped - see
  below.

Bracketed on `part_destructible` (Ark Ranger Black's precedent, Fienn 2026-07-17):
- Blue Blade's Single Point Attack (self Sustained Damage +47.32% for 15 sec)
  triggers on "an ally or self destroys an enemy's part". The engine has no part
  concept and cannot say WHEN that happens, but it does know WHETHER the boss has
  destructible parts at all. So:
  - floor (`part_destructible` False): parts can never be destroyed, so Single
    Point Attack never fires. Not granted.
  - ceiling (`part_destructible` True): parts do get destroyed, and Raven's own
    Vital Attack exists to do it, so the buff is treated as up from battle start.
  The real answer sits between the two. The gauge/timing of part destruction is
  still unmodeled - this only brackets it. A.N. Mode's "Removes Single Point
  Attack" is deliberately NOT modeled: it would cut the ceiling's own buff during
  the burst, and we have no evidence Raven's rotation actually loses it there.

Not modeled / deferred:
- Vital Attack (Damage to Parts +21.12%, at battle start and each Full Burst).
  Damage to Parts has no consumer in the engine - there are no parts to hit - so
  wiring it would be inert. It is also the precondition Single Point Attack is
  bracketed over, which is why the ceiling assumes it does its job.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import boss_part_destructible

SKILL_VALUE_MANIFESTS = {
    "raven": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_raven",
        "keys": {
            "shock_wave": ("skills", 0),
            "blue_blade": ("skills", 1),
            "tempest": ("skills", 2),
        },
        # the burst's "Effect 1:" / "Effect 2:" are labels, not values.
        "drop_tokens": {"tempest": (1, 2)},
    },
}


def tempest_burst_percent(values):
    return float(values["tempest"]["description_value_01"])


def build_raven_rules(values):
    shock_wave = values["shock_wave"]
    blue_blade = values["blue_blade"]
    tempest = values["tempest"]

    caster_atk = values["caster_atk"]
    fb_atk = float(shock_wave["description_value_05"]) / 100 * caster_atk
    fb_atk_duration = float(shock_wave["description_value_06"])
    an_mode_sustained = float(tempest["description_value_02"]) / 100
    an_mode_duration = float(tempest["description_value_03"])
    single_point = float(blue_blade["description_value_05"]) / 100
    single_point_duration = float(blue_blade["description_value_06"])

    return [
        buff_rule("full_burst_enter", [("flat_atk", fb_atk, "self", fb_atk_duration)]),
        buff_rule("own_burst_activate", [
            ("sustained_damage_up", an_mode_sustained, "self", an_mode_duration),
        ]),
        # Ceiling only: with destructible parts, Single Point Attack is treated as
        # up all fight. Under the floor it never fires, so nothing is granted.
        buff_rule(
            "battle_start",
            [("sustained_damage_up", single_point, "self", single_point_duration)],
            condition=boss_part_destructible(),
        ),
    ]


def build_raven_scheduled_nukes(values):
    """Shock Wave: each Full Charge starts a 5-tick sustained DoT.

    "Stacks up to 10 times" needs no resource tracking: her RL takes 1 sec per
    Full Charge and reloads every 6 rounds, so at most 5 instances are ever live
    inside a 5-second window - the cap cannot bind (measured 2026-07-17, same
    reasoning as Velvet's ammo pouch).
    """
    shock_wave = values["shock_wave"]
    percent = float(shock_wave["description_value_01"])
    tick_interval = float(shock_wave["description_value_02"])
    duration = float(shock_wave["description_value_04"])
    tick_count = int(duration / tick_interval)

    def schedule(context, fight_duration):
        return [
            shot + tick_interval * n
            for shot in context.shot_times.get("raven", [])
            for n in range(1, tick_count + 1)
        ]

    return [{"schedule": schedule, "percent": percent, "damage_type": "sustained"}]
