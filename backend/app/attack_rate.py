"""Generates normal-attack shot timestamps for a weapon over a fight.

Magazine weapons (AR/MG/SMG/SG) fire at a fixed rate while ammo remains,
then pause for reload_time before the next magazine. Rate of fire isn't in
api.dotgg.gg's character data for these weapons (chargeTime is 0, so it
can't be derived) - RATE_OF_FIRE_60FPS is Fienn's measured 60fps figures
for actual (not theoretical) rate of fire.

Charge weapons (RL/SR) charge for charge_time, fire one shot, then reload
for reload_time before charging again - one shot per (charge_time +
reload_time) cycle. This assumes every shot is a full charge (the higher-
DPS, standard way to play these weapons); partial-charge/uncharged shots
aren't modeled.

Not modeled: reload_speed_percent and max_ammo_percent effects (several
skills grant these) changing the schedule dynamically mid-fight - shot
timing here uses each Nikke's base reload_time/max_ammo throughout.
"""

RATE_OF_FIRE_60FPS = {
    "AR": 12.0,
    "MG": 60.0,
    "SMG": 20.0,
    "SG": 1.5,
}

CHARGE_WEAPONS = {"RL", "SR"}


def rate_of_fire_for_weapon(weapon: str) -> float:
    return RATE_OF_FIRE_60FPS[weapon]


def generate_magazine_shot_times(rate_of_fire, max_ammo, reload_time, fight_duration):
    shot_interval = 1.0 / rate_of_fire
    cycle_duration = max_ammo * shot_interval + reload_time
    shots = []
    cycle_start = 0.0

    while cycle_start < fight_duration:
        for i in range(max_ammo):
            shot_time = cycle_start + i * shot_interval
            if shot_time >= fight_duration:
                return shots
            shots.append(shot_time)
        cycle_start += cycle_duration

    return shots


def generate_charge_shot_times(charge_time, reload_time, fight_duration):
    cycle_duration = charge_time + reload_time
    shots = []
    i = 0

    while True:
        shot_time = charge_time + i * cycle_duration
        if shot_time >= fight_duration:
            break
        shots.append(shot_time)
        i += 1

    return shots


def generate_shot_times(weapon, max_ammo, reload_time, charge_time, fight_duration):
    if weapon in CHARGE_WEAPONS:
        return generate_charge_shot_times(charge_time, reload_time, fight_duration)
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return generate_magazine_shot_times(rate_of_fire, max_ammo, reload_time, fight_duration)
