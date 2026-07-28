"""Generates normal-attack shot timestamps for a weapon over a fight.

Magazine weapons (AR/MG/SMG/SG) fire at a fixed rate while ammo remains,
then pause for reload_time before the next magazine. Rate of fire isn't in
api.dotgg.gg's character data for these weapons (chargeTime is 0, so it
can't be derived) - RATE_OF_FIRE_60FPS is Fienn's measured 60fps figures
for actual (not theoretical) rate of fire.

Charge weapons (RL/SR) fire max_ammo full-charge shots (charge_time apart,
one charge per shot), THEN reload for reload_time before the next batch -
confirmed by Fienn against how maxAmmo behaves for these weapons in-game,
not a single charge+reload per shot. Partial-charge/uncharged shots aren't
modeled.

reload_speed_percent and max_ammo_percent (from overload options, which are
permanent, or skills, which are often temporary) are threaded through as
callables - `_at(t)` - evaluated at the moment they're needed (magazine
size at the magazine's start time, reload speed at the moment the last
round of that magazine fires) rather than as fixed numbers, since they can
change mid-fight. Magazine size is rounded to the nearest whole round.

attack_speed_percent (magazine weapons) and charge_speed_percent (charge
weapons) are threaded through the SAME `_at(t)` callable pattern and scale the
firing cadence: shot_interval = 1 / (rate_of_fire * (1 + attack_speed)) for
magazine weapons, and `charge_time_with_speed` (which SHORTENS by the buff's
percent rather than dividing - see that helper) for charge weapons. Like max_ammo_percent they're evaluated once per magazine (at
its start), so a buff active for part of a magazine takes full effect from the
next magazine boundary - a deliberate approximation matching the max_ammo/reload
granularity. Default `_zero` leaves cadence untouched, so units with no such
buff keep their exact original timelines.

`{magazine,charge}_last_bullet_times`/`last_bullet_shot_times` mark which of
those same shot times actually EMPTY their magazine (gap #1's residual "last
bullet fired" trigger, e.g. Julia's Crescendo). Only `max_ammo_percent`
matters for WHICH round that is (attack/charge speed change shot CADENCE, not
magazine CAPACITY), but the cadence change shifts that round's TIME, so the
speed callables are threaded here too to keep last-bullet times aligned.
"""

RATE_OF_FIRE_60FPS = {
    "AR": 12.0,
    "MG": 60.0,
    "SMG": 20.0,
    "SG": 1.5,
}

CHARGE_WEAPONS = {"RL", "SR"}


def _zero(_time):
    return 0.0


def reload_time_with_speed(reload_time, reload_speed_percent):
    """Reload TIME from a reload-SPEED modifier, in both directions.

    Speed and time are reciprocal, and the game's two directions are
    symmetric: +50% speed reloads in 1/1.5 of the time, -50% speed takes 1.5x
    as long. Plain `time / (1 + speed)` only models the first direction - at
    speed = -0.5 it DOUBLES the reload instead of adding half. Milk: Blooming
    Bunny's forced reload is the first negative consumer in the roster and
    measures 3s against her 2s base, not 4s (Fienn, 2026-07-20).

    The negative branch rests on that single in-game observation, so it is
    anchored, not proven across magnitudes - revisit if a unit with a
    different reduction ever disagrees. Every pre-existing consumer buffs
    reload speed upward, so the positive branch is unchanged arithmetic.
    """
    if reload_speed_percent >= 0:
        return reload_time / (1 + reload_speed_percent)
    return reload_time * (1 - reload_speed_percent)


# The shortest gap the game allows between charged shots. Anchored to one
# in-game measurement (Fienn, 2026-07-20): Cinderella, whose Flawless Glass
# gives Charge Speed +100% - enough to drive her 1.0-sec charge to zero - fires
# 29-30 shots in 10 sec with a max-ammo overload preventing a reload. The
# conservative 29 is used.
#
# Two caveats, both deliberate rather than hidden. The floor MECHANISM is
# inferred: something bounds the cadence once charge time reaches zero, and a
# minimum gap reproduces the observation, but the game could equally be
# capping charge speed itself - the two are indistinguishable from one data
# point. And the value comes from a Rocket Launcher; whether a Sniper Rifle
# floors at the same number is untested. Only units that reach ~65%+ charge
# speed touch it at all, so today that is Cinderella alone.
CHARGE_INTERVAL_FLOOR_SECONDS = 10.0 / 29


# Some units pause between firing a charged shot and starting the next charge -
# a fire-motion/charge-motion gap that is NOT charge time and NOT reload. Fienn
# timed Snow White: Heavy Arms at about 0.4 sec (2026-07-28), and her 180-sec
# shot count only balances with it: 14 x (3.2 + 0.4) + 72 x (1.2 + 0.4) + 7 x
# 2.0 sec of reloads = 179.6 of 180 sec, against an engine that had her firing
# every 1.2 sec flat and gave her 37% too many base shots.
#
# It is PER UNIT, not per weapon class: Liberalio is also a Sniper Rifle and
# fires her charged shots back to back with no gap (Fienn). Applying it to every
# charge weapon is measurably wrong - it drops Scarlet: Black Shadow from 0.981x
# of her recorded damage to 0.559x and Cinderella from 0.971x to 0.654x. The
# units that have it are listed in skill_rules.registry._CHARGE_MOTION_DELAY.
CHARGE_MOTION_DELAY_SECONDS = 0.4

FRAME_SECONDS = 1.0 / 60


def charge_time_with_speed(charge_time, charge_speed_percent, flat_reduction_sec=0.0):
    """Charge TIME from a charge-SPEED modifier and any flat-seconds cut.

    Charge speed is NOT reciprocal the way reload speed is. A buff of n% cuts
    n% OFF THE CHARGE TIME IT APPLIES TO, so +100% reaches zero rather than
    merely halving - which is why community guides tell you to aim for "99%+
    charge speed" on units like Alice: 100% is the point where the charge
    disappears entirely. The engine previously used `charge_time / (1 + n)`,
    which understated every buff (at +30% it gave 0.769 sec where the game
    gives 0.70) and could never reach zero at all.

    The cut lands in WHOLE FRAMES: community testing works it as "3 sec is 180
    frames, 10.28% of 180 frames is ~18.5 frames". Flooring matters at the
    precision we now measure at - Neon: Vision Eye's 9.47% overload on a 1.0
    sec charge measured 0.9178 sec, which the floored 5-frame step reproduces
    to 0.07 frames where the continuous value is 0.75 frames off.

    `flat_reduction_sec` is for "caster-based" (시전자 기준) buffs, which are a
    genuinely different mechanic rather than a variant of the above: the
    percentage is taken against the CASTER's charge time and handed to the
    ally as absolute seconds, so it does NOT scale with the recipient's own
    charge. Liberalio is the clear case - she is a Sniper Rifle with a 1.5 sec
    charge, so her "Charge Speed +12.74% of the skill user's" is 0.1911 sec for
    whoever receives it. Korean community guides state the same figure ("약
    0.19초 줄어든다"), and it reproduces Fienn's Scarlet measurement (0.7323 ->
    0.5424 sec) to 0.07 frames. Expressing it as a percent would be wrong: the
    equivalent percent is 26.1% on Scarlet's 0.73 sec charge but 19.1% on a
    1.0 sec one.

    The same expression covers slowdowns: at -20% it returns 1.2x the base,
    which is the behaviour Bready's Taste debuff needs.

    NOTE the asymmetry with `reload_time_with_speed`, which divides on its
    positive branch. That is not an oversight here: reload's positive branch
    has never been measured, and changing it without evidence would be
    inventing a number. If reload is ever measured and behaves like charge,
    the two should converge.

    The floor can never make a weapon SLOWER than its own unbuffed charge:
    Scarlet: Black Shadow's base charge is 0.3 sec, already quicker than the
    floor measured on Cinderella's Rocket Launcher, and a blanket minimum
    would have silently slowed her down. That the two disagree is itself
    evidence the floor is not one global constant - see the note above it.
    """
    # The floor is measured against the UNBUFFED charge, so a weapon already
    # quicker than it is bounded by its own base, not slowed to it.
    floor = min(charge_time, CHARGE_INTERVAL_FLOOR_SECONDS)
    return max(_reduced_charge(charge_time, charge_speed_percent, flat_reduction_sec), floor)


def _reduced_charge(charge_time, charge_speed_percent, flat_reduction_sec):
    frames = int(charge_time / FRAME_SECONDS * charge_speed_percent)
    return charge_time - frames * FRAME_SECONDS - flat_reduction_sec


def shot_interval_with_speed(charge_time, charge_speed_percent, flat_reduction_sec=0.0,
                             motion_delay=0.0):
    """Seconds from one charged shot to the next: the buffed charge plus the
    unit's fire-to-charge motion delay.

    `CHARGE_INTERVAL_FLOOR_SECONDS` applies only when that delay is UNKNOWN.
    The floor is itself a motion delay - what remained of Cinderella's cadence
    once +100% charge speed took her charge to zero - generalised to everyone
    because hers was the only one measured. A unit whose own delay has since
    been timed is already bounded by it, so flooring her charge as well counts
    the same pause twice, and for a charge shorter than the floor it cancels
    charge-speed buffs entirely: Scarlet: Black Shadow charges in 0.30 sec, and
    Liberalio's flat 0.19 sec cut would vanish against a 0.345 floor.
    """
    reduced = _reduced_charge(charge_time, charge_speed_percent, flat_reduction_sec)
    if motion_delay:
        return max(0.0, reduced) + motion_delay
    return max(reduced, min(charge_time, CHARGE_INTERVAL_FLOOR_SECONDS))


def rate_of_fire_for_weapon(weapon: str) -> float:
    return RATE_OF_FIRE_60FPS[weapon]


def generate_magazine_shot_times(
    rate_of_fire,
    max_ammo,
    reload_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
):
    shots = []
    magazine_start = 0.0

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        for i in range(magazine_size):
            shot_time = magazine_start + i * shot_interval
            if shot_time >= fight_duration:
                return shots
            shots.append(shot_time)
        magazine_empty_at = magazine_start + magazine_size * shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time

    return shots


def generate_charge_shot_times(
    charge_time,
    reload_time,
    max_ammo,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
    charge_time_reduction_sec_at=_zero,
):
    shots = []
    magazine_start = 0.0

    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_shot_time = None
        for i in range(magazine_size):
            shot_time = magazine_start + effective_charge + i * effective_charge
            if shot_time >= fight_duration:
                return shots
            shots.append(shot_time)
            last_shot_time = shot_time
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(last_shot_time))
        magazine_start = last_shot_time + actual_reload_time

    return shots


def generate_shot_times(
    weapon,
    max_ammo,
    reload_time,
    charge_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
    charge_time_reduction_sec_at=_zero,
):
    if weapon in CHARGE_WEAPONS:
        return generate_charge_shot_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return generate_magazine_shot_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
    )


def magazine_last_bullet_times(
    rate_of_fire,
    max_ammo,
    reload_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
):
    """The subset of a magazine weapon's shot times that actually EMPTY their
    magazine (the round right before a reload) - for a "last bullet fired"
    per-shot trigger (gap #1's residual variant, e.g. Julia's Crescendo).
    Magazine size is re-derived live from `max_ammo_percent_at` exactly as
    `generate_magazine_shot_times` does, so a buffed magazine's last bullet
    correctly shifts to its new (larger) final round. Attack speed isn't
    involved - it's not modeled as a shot-interval modifier anywhere in this
    engine (see "Stats the engine does NOT consume"), and even if it were,
    it changes shot CADENCE, not magazine CAPACITY, so it wouldn't move which
    round empties the magazine. A shot that's merely the last one recorded
    because `fight_duration` cut the fight off mid-magazine is NOT a last
    bullet - only a round that reaches `magazine_size - 1` counts. Attack speed
    does not change WHICH round empties the magazine, but it does shift its TIME
    (faster cadence), so the interval is threaded through to keep these times
    aligned with `generate_magazine_shot_times`."""
    last_bullets = set()
    magazine_start = 0.0

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_round_time = magazine_start + (magazine_size - 1) * shot_interval
        if last_round_time >= fight_duration:
            return last_bullets
        last_bullets.add(last_round_time)
        magazine_empty_at = magazine_start + magazine_size * shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time

    return last_bullets


def charge_last_bullet_times(
    charge_time,
    reload_time,
    max_ammo,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
    charge_time_reduction_sec_at=_zero,
):
    """Charge-weapon equivalent of `magazine_last_bullet_times` - the round
    that empties each `max_ammo`-shot magazine before reloading. Charge speed
    shortens the per-shot charge time, so it's threaded through to keep these
    times aligned with `generate_charge_shot_times`."""
    last_bullets = set()
    magazine_start = 0.0

    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_round_time = magazine_start + effective_charge + (magazine_size - 1) * effective_charge
        if last_round_time >= fight_duration:
            return last_bullets
        last_bullets.add(last_round_time)
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(last_round_time))
        magazine_start = last_round_time + actual_reload_time

    return last_bullets


def magazine_first_bullet_times(
    rate_of_fire,
    max_ammo,
    reload_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
):
    """Mirror of magazine_last_bullet_times: each magazine's FIRST round,
    INCLUDING the battle-opening magazine at t=0 (a "at the start of battle and
    upon reloading to Max Ammunition" trigger, gap #9 - e.g. Jill Valentine's
    Magnum/Acid Ammo). A magazine whose first shot would land at or after
    fight_duration never fires - the while guard excludes it."""
    first_bullets = set()
    magazine_start = 0.0
    while magazine_start < fight_duration:
        first_bullets.add(magazine_start)
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_empty_at = magazine_start + magazine_size * shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time
    return first_bullets


def charge_first_bullet_times(
    charge_time,
    reload_time,
    max_ammo,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
    charge_time_reduction_sec_at=_zero,
):
    """Charge-weapon mirror: the first charged shot of each magazine (lands
    one effective charge after the magazine starts). A first shot at or after
    fight_duration never fires, so it's checked explicitly."""
    first_bullets = set()
    magazine_start = 0.0
    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        first_shot = magazine_start + effective_charge
        if first_shot >= fight_duration:
            return first_bullets
        first_bullets.add(first_shot)
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_round_time = magazine_start + effective_charge + (magazine_size - 1) * effective_charge
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(last_round_time))
        magazine_start = last_round_time + actual_reload_time
    return first_bullets


def first_bullet_shot_times(
    weapon,
    max_ammo,
    reload_time,
    charge_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
    charge_time_reduction_sec_at=_zero,
):
    """Weapon-dispatching counterpart of `last_bullet_shot_times` - the subset
    of the shot timeline that OPENS its magazine, for a "at the start of battle
    and upon reloading to Max Ammunition" per_shot_rules trigger (gap #9)."""
    if weapon in CHARGE_WEAPONS:
        return charge_first_bullet_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return magazine_first_bullet_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
    )


def last_bullet_shot_times(
    weapon,
    max_ammo,
    reload_time,
    charge_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
    charge_time_reduction_sec_at=_zero,
):
    """Weapon-dispatching counterpart of `generate_shot_times` - the subset
    of that same shot timeline that empties its magazine, for a "last bullet
    fired" per_shot_rules trigger."""
    if weapon in CHARGE_WEAPONS:
        return charge_last_bullet_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return magazine_last_bullet_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
    )


from dataclasses import dataclass


@dataclass(frozen=True)
class ShotRecord:
    """One shot of a (possibly mode-switching) unit's timeline: its damage
    parameters ride on the record because different segments fire different
    profiles. damage_type None = derive from `weapon` (raid_simulator's
    normal_attack_type); a segment profile may pin it (e.g. a transform whose
    ticks are true damage)."""
    time: float
    weapon: str
    damage_percent: float
    extra_charge_bonus: float
    is_first_bullet: bool
    is_last_bullet: bool
    damage_type: str | None = None
    in_segment: bool = False


def _base_shot_records(base, window_start, window_end,
                       max_ammo_percent_at, reload_speed_percent_at,
                       attack_speed_percent_at, charge_speed_percent_at,
                       charge_time_reduction_sec_at=_zero):
    """The base weapon firing over [window_start, window_end) - the same
    arithmetic as generate_{charge,magazine}_shot_times (kept bit-identical so
    a no-segment call reproduces the legacy timeline exactly), restarted with
    a fresh magazine at window_start (the post-transform resume semantic,
    Fienn 2026-07-18). A magazine cut short by window_end gets NO last-bullet
    flag (it never actually emptied - same rule as the fight_duration cutoff)."""
    records = []
    if window_end <= window_start:
        return records
    weapon = base["weapon"]
    if weapon in CHARGE_WEAPONS:
        bonus = base["charge_damage_percent"] / 100 - 1
        magazine_start = window_start
        while magazine_start < window_end:
            effective_charge = shot_interval_with_speed(
                base["charge_time"], charge_speed_percent_at(magazine_start),
                charge_time_reduction_sec_at(magazine_start),
                base.get("charge_motion_delay", 0.0))
            magazine_size = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            last_shot_time = None
            for i in range(magazine_size):
                shot_time = magazine_start + effective_charge + i * effective_charge
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], bonus,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1)))
                last_shot_time = shot_time
            actual_reload = reload_time_with_speed(base["reload_time"], reload_speed_percent_at(last_shot_time))
            magazine_start = last_shot_time + actual_reload
    else:
        rate = rate_of_fire_for_weapon(weapon)
        magazine_start = window_start
        while magazine_start < window_end:
            interval = 1.0 / (rate * (1 + attack_speed_percent_at(magazine_start)))
            magazine_size = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            for i in range(magazine_size):
                shot_time = magazine_start + i * interval
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], 0.0,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1)))
            magazine_empty_at = magazine_start + magazine_size * interval
            actual_reload = reload_time_with_speed(base["reload_time"], reload_speed_percent_at(magazine_empty_at))
            magazine_start = magazine_empty_at + actual_reload
    return records


def _segment_shot_records(seg, fight_duration, charge_speed_percent_at,
                          charge_time_reduction_sec_at=_zero, motion_delay=0.0):
    """Shots of one override window. Cadence: charge-style profiles
    (charge_time) honor live charge-speed buffs; explicit rate_of_fire
    profiles are measurement anchors and take NO cadence buffs (the measured
    count already includes every in-game modifier). Segments never reload
    (no v1 consumer needs it). Returns (records, segment_end): until_shots
    windows end AT their last shot's time - the base weapon resumes at that
    same instant with a fresh magazine. For a MAGAZINE base (AR/MG/SMG/SG)
    that resume is itself a shot landing on that exact instant (round 0 of
    the fresh magazine fires AT magazine_start, per `_base_shot_records`); a
    CHARGE base (RL/SR) instead fires its first shot one charge-time later,
    so only magazine bases coincide with the segment's final-shot time."""
    profile = seg["profile"]
    start = seg["start"]
    if profile.get("charge_time"):
        interval = shot_interval_with_speed(
            profile["charge_time"], charge_speed_percent_at(start),
            charge_time_reduction_sec_at(start), motion_delay)
    else:
        interval = 1.0 / profile["rate_of_fire"]
    charge = profile.get("charge_damage_percent")
    bonus = charge / 100 - 1 if charge is not None else 0.0
    if "until_shots" in seg:
        times = [start + k * interval for k in range(1, seg["until_shots"] + 1)]
        seg_end = times[-1]
    else:
        seg_end = seg["end"]
        times = []
        k = 1
        while start + k * interval < seg_end:
            times.append(start + k * interval)
            k += 1
    records = [
        ShotRecord(t, profile["weapon"], profile["damage_percent"], bonus,
                   is_first_bullet=False, is_last_bullet=False,
                   damage_type=profile.get("damage_type"), in_segment=True)
        for t in times if t < fight_duration
    ]
    return records, min(seg_end, fight_duration)


def _shared_magazine_shots(base, segments, fight_duration, max_ammo_percent_at,
                           reload_speed_percent_at, charge_speed_percent_at,
                           charge_time_reduction_sec_at):
    """One magazine walked straight through the segments instead of a fresh one
    on each side of them - for a mode that is NOT a weapon swap and keeps
    firing the unit's own ammo.

    Snow White: Heavy Arms' Seven Dwarves Fully Active is the case this exists
    for: it only re-times her charge (1.2 -> 3.2 sec) and widens Auto Fire, and
    Fienn confirmed in game (2026-07-28) that its shots draw from the same
    magazine as her normal state. Under the default resume semantic she was
    getting both halves of a free lunch - the Fully Active shots cost no ammo
    AND the base weapon restarted full afterwards - which left her reloading
    once in a 180-sec fight.

    A real transform (Scarlet, Maxwell, Laplace, Cinderella's snipe mode) keeps
    the default: a different weapon arrives loaded. Hence the opt-in.
    """
    weapon = base["weapon"]
    base_bonus = base["charge_damage_percent"] / 100 - 1
    records = []
    pending = list(segments)
    cursor = 0.0                 # instant the next charge starts from
    capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(0.0))))
    rounds = capacity
    seg, seg_left = None, 0
    while cursor < fight_duration:
        if seg is None and pending and pending[0]["start"] <= cursor:
            seg = pending.pop(0)
            seg_left = seg["until_shots"]
        if seg is None:
            profile, bonus, in_segment = base, base_bonus, False
        else:
            profile = seg["profile"]
            charge_percent = profile.get("charge_damage_percent")
            bonus = charge_percent / 100 - 1 if charge_percent is not None else 0.0
            in_segment = True
        charge = shot_interval_with_speed(
            profile["charge_time"], charge_speed_percent_at(cursor),
            charge_time_reduction_sec_at(cursor), base.get("charge_motion_delay", 0.0))
        shot_time = cursor + charge
        # A segment opening mid-charge takes over: the pending shot is
        # abandoned exactly as the default path drops base shots past a
        # segment's start.
        if seg is None and pending and pending[0]["start"] < shot_time:
            cursor = pending[0]["start"]
            continue
        if shot_time >= fight_duration:
            break
        rounds -= 1
        records.append(ShotRecord(
            shot_time, profile["weapon"], profile["damage_percent"], bonus,
            is_first_bullet=(rounds == capacity - 1), is_last_bullet=(rounds == 0),
            damage_type=profile.get("damage_type") if in_segment else None,
            in_segment=in_segment))
        cursor = shot_time
        if in_segment:
            seg_left -= 1
            if seg_left == 0:
                seg = None
        if rounds == 0:
            cursor = shot_time + reload_time_with_speed(
                base["reload_time"], reload_speed_percent_at(shot_time))
            capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(cursor))))
            rounds = capacity
    return records


def generate_segmented_shots(
    base,
    segments,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
    charge_time_reduction_sec_at=_zero,
):
    """Full shot-record timeline for a unit whose weapon profile changes
    inside module-scheduled windows (weapon transforms - see
    docs/superpowers/specs/2026-07-18-weapon-transform-design.md). With no
    segments this reproduces generate_shot_times bit-for-bit (regression
    anchor), plus first/last-bullet flags equal to the marker trios.

    A segment marked `"shares_magazine": True` is not a weapon swap and draws
    from the unit's own magazine - see `_shared_magazine_shots`."""
    if any(seg.get("shares_magazine") for seg in segments):
        return _shared_magazine_shots(
            base, segments, fight_duration, max_ammo_percent_at,
            reload_speed_percent_at, charge_speed_percent_at, charge_time_reduction_sec_at)
    records = []
    cursor = 0.0
    for seg in list(segments) + [None]:
        if seg is None:
            stretch_end = fight_duration
        else:
            if seg["start"] < cursor:
                raise ValueError("weapon mode segments overlap or are unsorted")
            stretch_end = min(seg["start"], fight_duration)
        records.extend(_base_shot_records(
            base, cursor, stretch_end, max_ammo_percent_at,
            reload_speed_percent_at, attack_speed_percent_at, charge_speed_percent_at,
            charge_time_reduction_sec_at))
        if seg is None or seg["start"] >= fight_duration:
            break
        seg_records, cursor = _segment_shot_records(
            seg, fight_duration, charge_speed_percent_at, charge_time_reduction_sec_at,
            base.get("charge_motion_delay", 0.0))
        records.extend(seg_records)
    return records
