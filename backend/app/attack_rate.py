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

import math
from dataclasses import dataclass, replace

RATE_OF_FIRE_60FPS = {
    "AR": 12.0,
    "MG": 60.0,
    "SMG": 20.0,
    "SG": 1.5,
}

CHARGE_WEAPONS = {"RL", "SR"}


@dataclass(frozen=True)
class Spinup:
    """A weapon that reaches its nominal rate of fire only after warming up.

    `intervals` shot gaps at the head of every magazine together take `seconds`,
    instead of the `intervals / rate_of_fire` they would at top speed; every gap
    after that is the normal one. Stated as a total rather than as a curve
    because a total is what the measurement pins - see the shape note below.
    """
    intervals: int
    seconds: float

    @property
    def cost(self):
        """Seconds a magazine loses to warming up, at 60 rounds/sec."""
        return self.seconds - self.intervals / RATE_OF_FIRE_60FPS["MG"]


# Fienn, 2026-08-07, frame-by-frame (Rosanna solo, 305-round magazine, no reload
# buffs) - docs/measurements/mg-spinup.md. Her first shot lands at frame 863 and
# her 49th at frame 1000, so 48 gaps take 137 frames where top speed would take
# 48; from there to the empty magazine at frame 1256 it is 256 rounds in 256
# frames, exactly one per frame. So the nominal 60/sec was never wrong - it is
# the MAXIMUM, and the engine was handing it out from the first round.
#
# The SHAPE of the ramp is NOT measured: two endpoints and a total cannot tell a
# linear acceleration from any other curve, and a rate rising linearly in time is
# already ruled out (it would need a negative starting rate to fit 48 rounds in
# 137 frames). So the ramp is modeled as one reduced constant rate, which
# reproduces both endpoints and the magazine's total length exactly and differs
# from the truth only in where those 48 rounds sit inside 2.28 sec.
#
# Two things this one reading does not settle, both flagged in the measurement
# doc: whether a reload re-arms the spin-up (modeled: yes, it is per magazine -
# a reload is not firing), and whether Attack Speed shortens the ramp (modeled:
# no, it is a fixed segment like RELOAD_FIXED_SECONDS).
MG_SPINUP = Spinup(intervals=48, seconds=137 / 60)

_SPINUP_BY_WEAPON = {"MG": MG_SPINUP}


def spinup_for_weapon(weapon):
    """This weapon class's warm-up, or None for the classes that have none.

    Only the MG has one measured. An SMG also over-reads against the record
    (1.149x against the MG's 1.193x) but nothing has been timed on it, so it
    stays at its nominal rate rather than borrowing the MG's numbers.
    """
    return _SPINUP_BY_WEAPON.get(weapon)


def magazine_shot_offset(index, shot_interval, spinup):
    """Seconds from a magazine's first round to its `index`-th one.

    The single place the spin-up is applied, because two call sites generate
    magazine timelines - `generate_magazine_shot_times` and the segmented
    `_base_shot_records` - and they are contractually bit-identical when there
    are no segments.
    """
    if spinup is None or index <= 0:
        return index * shot_interval
    ramp_interval = spinup.seconds / spinup.intervals
    if index <= spinup.intervals:
        return index * ramp_interval
    return spinup.seconds + (index - spinup.intervals) * shot_interval


@dataclass(frozen=True)
class AmmoRefund:
    """Rounds handed back into the magazine every N shots fired.

    The Tactical Bear (택티컬 베어) harmony cube is the consumer: "10발 사격 시
    탄환 충전 3발". Two rulings shape it (Fienn, 2026-07-31, in game):

    - The shot counter is CUMULATIVE over the fight, not per magazine. Scarlet:
      Black Shadow holds 9 rounds, so a per-magazine counter would never reach
      10 and the cube would do nothing for her; it does.
    - The refund is CAPPED at the magazine's capacity. Landing on a magazine
      with 8 of 9 left hands back 1, not 3.

    Those two together are why this cannot be a max-ammo percentage: how much a
    refund is worth depends on where in the magazine it lands, and a magazine
    that refills mid-fight shifts every later reload against the Full Burst
    window. Faking it as a flat percentage scores non-monotonically.
    """
    every_shots: int
    rounds: int

    def __post_init__(self):
        if self.rounds >= self.every_shots:
            raise ValueError(
                f"a refund of {self.rounds} every {self.every_shots} shots never "
                "empties the magazine")


def _refund_sequence(refund):
    """`refund` as a tuple, rejecting a set that never empties the magazine.

    A unit can hold more than one source at once - EVE reloads 3 rounds every
    10 shots off her own skill and a Tactical Bear cube hands back 3 more on
    the same cadence - and each keeps its own trigger against the shared shot
    counter. `AmmoRefund` can only vet itself, so the combined rate is checked
    here: at one round back per shot the walk below would never terminate.
    """
    if refund is None:
        return ()
    refunds = (refund,) if isinstance(refund, AmmoRefund) else tuple(refund)
    if sum(r.rounds / r.every_shots for r in refunds) >= 1:
        raise ValueError(
            f"refunds {refunds} together hand back a round per shot, so the "
            "magazine never empties")
    return refunds


def magazine_shot_count(capacity, shots_before, refund):
    """Rounds this magazine actually fires, and the shot counter afterwards.

    Walks the magazine one round at a time because a refund's value depends on
    the rounds remaining when it lands (it is capped at capacity), and the
    counter it triggers on runs across magazines. `refund` is one AmmoRefund, a
    sequence of them, or None; None returns the capacity untouched, so every
    timeline without a refund keeps its exact arithmetic.
    """
    refunds = _refund_sequence(refund)
    if not refunds:
        return capacity, shots_before + capacity
    rounds = capacity
    shots = 0
    counter = shots_before
    while rounds > 0:
        rounds -= 1
        shots += 1
        counter += 1
        for one in refunds:
            if counter % one.every_shots == 0:
                rounds = min(capacity, rounds + one.rounds)
    return shots, counter


def _zero(_time):
    return 0.0


# The part of a reload that no buff scales. Reload is affine, not reciprocal:
# the data file's reloadTime is what a reload-speed buff multiplies, and a fixed
# animation segment sits on top of it. Fienn's six readings (2026-07-29, 60fps)
# fit `file * (1 - s) + 0.148` to 1.12 frames, and solving them per unit returns
# slopes of 1.0029 and 2.4835 against file values of 1.0 and 2.5 - the file is
# right, the old formula was not. Same shape as CHARGE_MOTION_DELAY_SECONDS.
#
# Taken as global (Fienn, 2026-07-31). The two readings that show no fixed
# segment are both charge weapons - Milk's forced reload at -50% (exactly 1.5x
# her file value) and Centi's clip load (exactly her 0.5-sec file value) - so a
# per-weapon-class constant is a live alternative that those readings are too
# coarse to settle. Raw: docs/measurements/reload-affine.md.
RELOAD_FIXED_SECONDS = 0.148


def reload_time_with_speed(reload_time, reload_speed_percent):
    """Reload TIME from a reload-SPEED modifier, in both directions.

    One expression, no branch: the negative direction was already
    `file * (1 - s)` (Milk: Blooming Bunny's forced reload measures 3 sec
    against her 2-sec file value at -50%, not 4), and this returns the positive
    direction to the same convention.

    Note what that costs: reload speed 0 is NOT the identity. An unbuffed reload
    is the file value PLUS the fixed segment, because the file value is only the
    scaled part - Privaty's 1.0 sec measures 1.1667 with nothing on her.

    `max(0.0, ...)` is what lets the reload actually disappear. Crown (44.35%)
    plus Privaty (51.16%) plus the Resilience cube (29.69%) reach 125.20% and
    the game stops reloading; `time / (1 + s)` gives 0.888 sec there and cannot
    reach zero at any speed. Whether the fixed segment survives past that point
    or is clipped away with the rest is unmeasured - this clips it, which is the
    reading that needs no second rule.
    """
    return max(0.0, reload_time * (1 - reload_speed_percent) + RELOAD_FIXED_SECONDS)


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
# fires her charged shots back to back with no gap (Fienn), and handing THIS
# value to every charge weapon is measurably wrong - it dropped Scarlet: Black
# Shadow from 0.981x of her recorded damage to 0.559x before either was timed.
# Every unit's own answer lives in skill_rules.registry._CHARGE_MOTION_DELAY,
# where the untimed ones carry a smaller stand-in (22 frames, from the two
# frame-number measurements) rather than a silent zero.
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
    0.19초 줄어든다"). Expressing it as a percent would be wrong: the equivalent
    percent is 26.1% on Scarlet's 0.73 sec charge but 19.1% on a 1.0 sec one.

    The charge left after a flat cut is carried as-is, NOT snapped back onto the
    frame grid. Only the percent cut lands in frames; a flat cut can leave a
    fraction and that fraction survives. Scarlet: Black Shadow receiving
    Liberalio therefore charges in 0.30 - 0.1911 = 0.1089 sec.

    That is a measured ruling, and the measurement it rests on is unusually
    strong because it needs no assumption about the motion delay: subtracting
    her Liberalio-accompanied interval from her solo interval WITHIN one account
    cancels the delay and leaves the grant alone. Across four solo and two
    accompanied Full Burst windows Fienn read 0.19019 sec (2026-07-30), against
    a nominal 0.19110 - 0.05 frames out. Snapping the residual to frames would
    make the effective grant 0.20000 instead, which those readings reject at
    17.6 sigma.

    A SECOND account, measured the same way with the same deck, skill levels,
    cubes and frame rate, instead reads 0.20229 - the snapped value - and
    nothing known separates the two. See
    docs/measurements/scarlet-black-shadow-charge.md for the raw windows, the
    six hypotheses that failed to explain the gap, and why more readings of the
    same kind cannot settle it: Liberalio's grant is 11.466 frames, so every
    recipient of it sits 0.534 frames from a boundary and the two models are
    always exactly that far apart.

    The same expression covers slowdowns: at -20% it returns 1.2x the base,
    which is the behaviour Bready's Taste debuff needs.

    `reload_time_with_speed` now subtracts the same way, so the two agree on
    shape: a percent takes that percent OFF the file value rather than dividing
    it. Reload got there by measurement (six readings, 2026-07-29) and carries a
    fixed segment on top that charge does not - see RELOAD_FIXED_SECONDS.

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


def charge_frames_bought(charge_time, charge_speed_percent):
    """Whole frames a charge-speed ratio takes off this charge time.

    Charge speed only ever lands in whole frames (see `charge_time_with_speed`),
    so this is the one place the ratio meets the frame grid - anything that
    needs to know whether two ratios differ AT ALL asks here rather than
    re-deriving the quantisation."""
    return int(charge_time / FRAME_SECONDS * charge_speed_percent)


def _reduced_charge(charge_time, charge_speed_percent, flat_reduction_sec):
    frames = charge_frames_bought(charge_time, charge_speed_percent)
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
    ammo_refund=None,
    weapon=None,
):
    shots = []
    magazine_start = 0.0
    shots_fired = 0
    spinup = spinup_for_weapon(weapon)

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, ammo_refund)
        for i in range(magazine_size):
            shot_time = magazine_start + magazine_shot_offset(i, shot_interval, spinup)
            if shot_time >= fight_duration:
                return shots
            shots.append(shot_time)
        magazine_empty_at = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup) + shot_interval
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
    ammo_refund=None,
):
    shots = []
    magazine_start = 0.0
    shots_fired = 0

    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, ammo_refund)
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
    ammo_refund=None,
):
    if weapon in CHARGE_WEAPONS:
        return generate_charge_shot_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
            ammo_refund=ammo_refund,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return generate_magazine_shot_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
        ammo_refund=ammo_refund, weapon=weapon,
    )


def magazine_last_bullet_times(
    rate_of_fire,
    max_ammo,
    reload_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    ammo_refund=None,
    weapon=None,
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
    aligned with `generate_magazine_shot_times`. An ammo refund, unlike attack
    speed, DOES move which round empties the magazine - the refunded rounds are
    fired before the reload - so it is threaded through too."""
    last_bullets = set()
    magazine_start = 0.0
    shots_fired = 0
    spinup = spinup_for_weapon(weapon)

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, ammo_refund)
        last_round_time = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup)
        if last_round_time >= fight_duration:
            return last_bullets
        last_bullets.add(last_round_time)
        magazine_empty_at = last_round_time + shot_interval
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
    ammo_refund=None,
):
    """Charge-weapon equivalent of `magazine_last_bullet_times` - the round
    that empties each `max_ammo`-shot magazine before reloading. Charge speed
    shortens the per-shot charge time, so it's threaded through to keep these
    times aligned with `generate_charge_shot_times`; an ammo refund moves which
    round empties the magazine, so it is threaded through as well."""
    last_bullets = set()
    magazine_start = 0.0
    shots_fired = 0

    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, ammo_refund)
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
    ammo_refund=None,
    weapon=None,
):
    """Mirror of magazine_last_bullet_times: each magazine's FIRST round,
    INCLUDING the battle-opening magazine at t=0 (a "at the start of battle and
    upon reloading to Max Ammunition" trigger, gap #9 - e.g. Jill Valentine's
    Magnum/Acid Ammo). A magazine whose first shot would land at or after
    fight_duration never fires - the while guard excludes it. A refund does not
    OPEN a magazine - only a reload does - but it delays the next reload, so it
    is threaded through to keep these times aligned."""
    first_bullets = set()
    magazine_start = 0.0
    shots_fired = 0
    spinup = spinup_for_weapon(weapon)
    while magazine_start < fight_duration:
        first_bullets.add(magazine_start)
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, ammo_refund)
        magazine_empty_at = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup) + shot_interval
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
    ammo_refund=None,
):
    """Charge-weapon mirror: the first charged shot of each magazine (lands
    one effective charge after the magazine starts). A first shot at or after
    fight_duration never fires, so it's checked explicitly. An ammo refund only
    delays the reload, but that moves where the NEXT magazine opens, so it is
    threaded through."""
    first_bullets = set()
    magazine_start = 0.0
    shots_fired = 0
    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        first_shot = magazine_start + effective_charge
        if first_shot >= fight_duration:
            return first_bullets
        first_bullets.add(first_shot)
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, ammo_refund)
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
    ammo_refund=None,
):
    """Weapon-dispatching counterpart of `last_bullet_shot_times` - the subset
    of the shot timeline that OPENS its magazine, for a "at the start of battle
    and upon reloading to Max Ammunition" per_shot_rules trigger (gap #9)."""
    if weapon in CHARGE_WEAPONS:
        return charge_first_bullet_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
            ammo_refund=ammo_refund,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return magazine_first_bullet_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
        ammo_refund=ammo_refund, weapon=weapon,
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
    ammo_refund=None,
):
    """Weapon-dispatching counterpart of `generate_shot_times` - the subset
    of that same shot timeline that empties its magazine, for a "last bullet
    fired" per_shot_rules trigger."""
    if weapon in CHARGE_WEAPONS:
        return charge_last_bullet_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
            ammo_refund=ammo_refund,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return magazine_last_bullet_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
        ammo_refund=ammo_refund, weapon=weapon,
    )


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
    # A transform whose shots land on the core every time, whatever spread the
    # unit's real weapon draws (Nayuta's Memory Incineration). Declared on the
    # segment profile because it is a measured property of that transform - a
    # segment's `weapon` label alone never decides a spread (raid_simulator's
    # _core_hit_rate_at).
    always_core_hit: bool = False


def _base_shot_records(base, window_start, window_end,
                       max_ammo_percent_at, reload_speed_percent_at,
                       attack_speed_percent_at, charge_speed_percent_at,
                       charge_time_reduction_sec_at=_zero):
    """The base weapon firing over [window_start, window_end) - the same
    arithmetic as generate_{charge,magazine}_shot_times (kept bit-identical so
    a no-segment call reproduces the legacy timeline exactly), restarted with
    a fresh magazine at window_start (the post-transform resume semantic,
    Fienn 2026-07-18). A magazine cut short by window_end gets NO last-bullet
    flag (it never actually emptied - same rule as the fight_duration cutoff).

    An ammo refund rides on `base` the way charge_motion_delay does. Its shot
    counter starts fresh per call, which is the same statement as the resume
    semantic: a real weapon transform arrives loaded and its shots are not this
    magazine's, so they do not count toward the refund trigger."""
    records = []
    if window_end <= window_start:
        return records
    weapon = base["weapon"]
    refund = base.get("ammo_refund")
    shots_fired = 0
    if weapon in CHARGE_WEAPONS:
        bonus = base["charge_damage_percent"] / 100 - 1
        magazine_start = window_start
        while magazine_start < window_end:
            effective_charge = shot_interval_with_speed(
                base["charge_time"], charge_speed_percent_at(magazine_start),
                charge_time_reduction_sec_at(magazine_start),
                base.get("charge_motion_delay", 0.0))
            capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, refund)
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
        spinup = spinup_for_weapon(weapon)
        magazine_start = window_start
        while magazine_start < window_end:
            interval = 1.0 / (rate * (1 + attack_speed_percent_at(magazine_start)))
            capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            magazine_size, shots_fired = magazine_shot_count(capacity, shots_fired, refund)
            for i in range(magazine_size):
                shot_time = magazine_start + magazine_shot_offset(i, interval, spinup)
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], 0.0,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1)))
            magazine_empty_at = magazine_start + magazine_shot_offset(
                magazine_size - 1, interval, spinup) + interval
            actual_reload = reload_time_with_speed(base["reload_time"], reload_speed_percent_at(magazine_empty_at))
            magazine_start = magazine_empty_at + actual_reload
    return records


def _segment_shot_records(seg, fight_duration, charge_speed_percent_at,
                          charge_time_reduction_sec_at=_zero, motion_delay=0.0,
                          stop_at=None):
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
    so only magazine bases coincide with the segment's final-shot time.

    `stop_at` is when the NEXT window opens, if one opens while this is still
    running: the transform refreshes from the new cast, so this window ends
    there rather than running its own course (see
    `_reject_unrepresentable_overlaps`)."""
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
        # The window ends at its last shot - which may be past the bell, and
        # then it is the BELL that ends it, not that shot. Folding it back to
        # the last shot that actually landed would hand the base weapon the
        # closing seconds it never had.
        seg_end = times[-1]
        if stop_at is not None and stop_at < seg_end:
            times = [t for t in times if t < stop_at]
            seg_end = stop_at
    else:
        seg_end = seg["end"] if stop_at is None else min(seg["end"], stop_at)
        times = []
        k = 1
        while start + k * interval < seg_end:
            times.append(start + k * interval)
            k += 1
    records = [
        ShotRecord(t, profile["weapon"], profile["damage_percent"], bonus,
                   is_first_bullet=False, is_last_bullet=False,
                   damage_type=profile.get("damage_type"), in_segment=True,
                   always_core_hit=bool(profile.get("always_core_hit")))
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

    The same reasoning decides the ammo refund: shots taken here spend this
    magazine, so they count toward the refund's trigger. Because a refund can
    top a partly-spent magazine back up, whether a shot OPENS or EMPTIES its
    magazine can no longer be read off the rounds remaining - `opening` tracks
    the first and the last is stamped after the refund has been applied.
    """
    weapon = base["weapon"]
    base_bonus = base["charge_damage_percent"] / 100 - 1
    refunds = _refund_sequence(base.get("ammo_refund"))
    records = []
    pending = list(segments)
    cursor = 0.0                 # instant the next charge starts from
    capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(0.0))))
    rounds = capacity
    shots_fired = 0
    opening = True               # is the next shot this magazine's first?
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
        shots_fired += 1
        records.append(ShotRecord(
            shot_time, profile["weapon"], profile["damage_percent"], bonus,
            is_first_bullet=opening, is_last_bullet=False,
            damage_type=profile.get("damage_type") if in_segment else None,
            in_segment=in_segment,
            always_core_hit=in_segment and bool(profile.get("always_core_hit"))))
        opening = False
        for one in refunds:
            if shots_fired % one.every_shots == 0:
                rounds = min(capacity, rounds + one.rounds)
        cursor = shot_time
        if in_segment:
            seg_left -= 1
            if seg_left == 0:
                seg = None
        if rounds == 0:
            records[-1] = replace(records[-1], is_last_bullet=True)
            cursor = shot_time + reload_time_with_speed(
                base["reload_time"], reload_speed_percent_at(shot_time))
            capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(cursor))))
            rounds = capacity
            opening = True
    return records


def _reject_unrepresentable_overlaps(segments):
    """Windows must arrive in order, and two that overlap must be the SAME
    transform.

    A window re-opening while it still runs is ordinary, not an error: a
    schedule anchored on its owner's bursts emits one window per burst, and her
    burst comes back before the window closes as soon as the deck cycles faster
    than the window is long. Nothing capped that before - a cycle cost at least
    `FULL_BURST_DURATION` + the gauge, which exceeded every window in the
    registry - until per-cycle Full Burst lengths landed and Isabel's -5 sec
    let a heavy-cooldown deck cycle in 9.45 sec against Nayuta's 10-sec Memory
    Incineration (2026-08-06). In game the second cast refreshes the duration
    from itself (Fienn), which `_segment_shot_records`' `stop_at` expresses by
    ending the running window where the new one opens.

    Two DIFFERENT profiles overlapping has no such reading - there is no answer
    to which weapon she is holding - so it stays an error. An `until_shots`
    window has no end until it is walked, so an overlap involving one cannot be
    seen from here; the caller's own cursor check is the backstop.
    """
    for previous, seg in zip(segments, segments[1:]):
        if seg["start"] < previous["start"]:
            raise ValueError("weapon mode segments overlap or are unsorted")
        end = previous.get("end")
        if (end is not None and seg["start"] < end
                and seg["profile"] != previous["profile"]):
            raise ValueError("weapon mode segments overlap or are unsorted")


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
    _reject_unrepresentable_overlaps(segments)
    if any(seg.get("shares_magazine") for seg in segments):
        return _shared_magazine_shots(
            base, segments, fight_duration, max_ammo_percent_at,
            reload_speed_percent_at, charge_speed_percent_at, charge_time_reduction_sec_at)
    records = []
    cursor = 0.0
    windows = list(segments)
    for index, seg in enumerate(windows + [None]):
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
        reopened_at = (windows[index + 1]["start"]
                       if index + 1 < len(windows) else None)
        seg_records, cursor = _segment_shot_records(
            seg, fight_duration, charge_speed_percent_at, charge_time_reduction_sec_at,
            base.get("charge_motion_delay", 0.0), stop_at=reopened_at)
        records.extend(seg_records)
    return records
