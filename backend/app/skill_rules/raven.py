"""Raven (slug "raven"), a Burst-3 Iron RL attacker. Collected from
lootandwaifus.com.

Her damage is Shock Wave: ONE stack counter, fed by her Full Charges. Read the
skill text carefully - it does not lay an independent DoT per shot:
  - Each Full Charge adds a stack: 1st -> 1, 2nd -> 2, ... capped at 10.
  - "Lasts for 5 sec" is the COUNTER's life, refreshed by every Full Charge -
    stacks survive as long as she keeps firing inside that window, however old
    they are. Only a gap longer than 5 sec drops it back to one fresh stack.
  (Both from Fienn, 2026-07-17.)

Her cadence is what makes this matter: an RL Full Charge takes 1 sec and her
longest gap is the 3-sec reload - inside the 5-sec window, always. So the counter
never expires, she reaches 10 stacks by ~t=12, and holds them for the rest of the
fight. The DoT rides on `scheduled_nukes` reading her own shot times off the
context.

Modeled (DPS-relevant):
- Shock Wave (skills[0]):
  - 68.46% of final ATK as sustained damage per live stack, every 1 sec. Each
    tick emits one damage instance PER stack (defense comes off each one, the
    same reason a multi-hit burst is not folded into a single big hit).
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

# Shock Wave's stack cap and the counter's life, both from skills[0]'s text.
# Defaults for the helpers; the builder reads the real values off the data.
SHOCK_WAVE_STACK_CAP = 10
SHOCK_WAVE_WINDOW = 5.0

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


def _stack_counts(shot_times, window=SHOCK_WAVE_WINDOW, cap=SHOCK_WAVE_STACK_CAP):
    """Shock Wave's stack count immediately after each Full Charge.

    One counter, not one DoT per shot: the 1st Full Charge puts it at 1 stack,
    the 2nd at 2, up to `cap` (Fienn 2026-07-17). "Lasts for 5 sec" is that
    counter's life, and every Full Charge refreshes it - so stacks survive as
    long as she keeps firing inside the window, however old they are. Only a gap
    longer than the window drops it back to a single fresh stack.
    """
    counts, count, expires_at = [], 0, None
    for shot in shot_times:
        count = 1 if expires_at is None or shot > expires_at else min(count + 1, cap)
        expires_at = shot + window
        counts.append(count)
    return counts


def _shock_wave_ticks(shot_times, tick_interval, window=SHOCK_WAVE_WINDOW,
                      cap=SHOCK_WAVE_STACK_CAP):
    """Every moment a Shock Wave stack deals damage.

    The counter ticks once per `tick_interval` while alive, and every live stack
    deals the percent - so a tick time appears once PER stack, giving that many
    separate damage instances (defense comes off each one, the same reason a
    multi-hit burst is not folded into one big hit).
    """
    counts = _stack_counts(shot_times, window, cap)
    ticks = []
    index, total = 0, len(shot_times)
    while index < total:
        # One life of the counter: from the Full Charge that started it at 1
        # stack, through every Full Charge that refreshed it, ending `window`
        # after the last of them.
        last = index
        while last + 1 < total and counts[last + 1] != 1:
            last += 1
        life_end = shot_times[last] + window

        cursor = index
        tick = shot_times[index] + tick_interval
        while tick <= life_end:
            # Each tick counts the stacks standing at its OWN time, like every
            # other deferred count in the engine.
            while cursor + 1 <= last and shot_times[cursor + 1] <= tick:
                cursor += 1
            ticks.extend([tick] * counts[cursor])
            tick += tick_interval
        index = last + 1
    return ticks


def build_raven_scheduled_nukes(values):
    """Shock Wave, her main damage. Driven off her own Full Charge times.

    Her cadence is what makes the cap matter: an RL Full Charge every 1 sec with
    a 3-sec reload gap never exceeds the 5-sec refresh window, so she climbs to
    10 stacks by ~t=12 and holds them for the rest of the fight (measured
    2026-07-17). A steady-state guess would have badly understated this.
    """
    shock_wave = values["shock_wave"]
    percent = float(shock_wave["description_value_01"])
    tick_interval = float(shock_wave["description_value_02"])
    cap = int(float(shock_wave["description_value_03"]))
    window = float(shock_wave["description_value_04"])

    def schedule(context, fight_duration):
        return _shock_wave_ticks(context.shot_times.get("raven", []),
                                 tick_interval, window, cap)

    return [{"schedule": schedule, "percent": percent, "damage_type": "sustained"}]
