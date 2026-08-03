"""How many normal attacks a charge weapon lands inside one Full Burst window.

The cadence itself is NOT computed here - `attack_rate.shot_interval_with_speed`
owns it, including the motion delay and the frame grid the charge snaps to. This
module only walks that interval across a 10-second window, spending magazine and
reloading when it runs out, so a re-measured charge time or delay moves the
calculator without anyone editing it.

The magazine is assumed FULL at window start. For Scarlet: Black Shadow that is
a fact - Fleetly Fading: Asura reloads her instantly on Full Burst entry - and
for Liberalio and Neon it is an assumption the UI states, since nothing records
how much they fired just before the window opened.
"""
from dataclasses import dataclass, replace

from app.attack_rate import (FRAME_SECONDS, reload_time_with_speed,
                             shot_interval_with_speed)
from app.overload_decode import charge_speed_percent_from_lines


@dataclass(frozen=True)
class WindowInputs:
    charge_time: float
    motion_delay: float
    max_ammo: int                      # overload and self-buffs already folded in
    reload_time: float
    charge_speed_percent: float
    charge_time_reduction_sec: float   # Liberalio's caster-based grant, in seconds
    reload_speed_percent: float
    window_seconds: float = 10.0


def shot_interval(inputs: WindowInputs) -> float:
    return shot_interval_with_speed(
        inputs.charge_time,
        inputs.charge_speed_percent,
        inputs.charge_time_reduction_sec,
        motion_delay=inputs.motion_delay,
    )


def shot_times(inputs: WindowInputs, start_charged: bool) -> list[float]:
    """Shot timestamps strictly inside [0, window_seconds).

    `start_charged` is the phase the window opens at: a charge that completed
    exactly as the window opened fires at t=0, an empty one fires a full
    interval later. Fienn's three measured runs opened at 0.05, 0.29 and 0.39
    sec, so neither end is the normal case - the caller reports both.
    """
    interval = shot_interval(inputs)
    reload_gap = reload_time_with_speed(inputs.reload_time, inputs.reload_speed_percent)
    times = []
    time = 0.0 if start_charged else interval
    fired = 0
    while time < inputs.window_seconds:
        times.append(time)
        fired += 1
        if fired >= inputs.max_ammo:
            time += reload_gap
            fired = 0
        time += interval
    return times


def shots_without_magazine_limit(inputs: WindowInputs) -> int:
    """What the cadence alone would land, which is what the magazine is measured
    against.

    A ladder whose rows read the same count says nothing about WHICH axis is
    flat: charge speed that buys a frame but no shot looks exactly like a
    magazine that runs out. Comparing against a magazine the window cannot empty
    separates them - and raising the magazine past that size is the same as
    removing it, so this is the real ceiling rather than an arbitrary number.
    """
    roomy = replace(
        inputs, max_ammo=int(inputs.window_seconds / shot_interval(inputs)) + 2)
    return len(shot_times(roomy, start_charged=True))


def reload_intervenes(inputs: WindowInputs) -> bool:
    """Whether the magazine empties before the window closes. When it does, the
    last shot depends on the reload formula, which is a known open question -
    see docs/engine-gaps.md. The UI warns instead of quietly answering."""
    return inputs.max_ammo * shot_interval(inputs) < inputs.window_seconds


def aggregate_charge_speed(lines: list[float]) -> float:
    """Overload charge-speed ROLLS (in percent) as the ratio the engine wants.

    Rolls of the same value sum first and each group rounds to a whole percent,
    which is why this needs the rolls and not their total - see
    `overload_decode.charge_speed_percent_from_lines` for the rule and the
    measurement behind it.
    """
    return charge_speed_percent_from_lines(lines) / 100


def charge_speed_steps(charge_time: float) -> list[float]:
    """Every charge-speed ratio that buys one more frame, and nothing between.

    Charge speed lands in whole frames, so the useful values are enumerable
    rather than searchable: a 0.30 sec charge is 18 frames and moves only every
    1/18 = 5.56%. Anything in between is money that changes no number.
    """
    frames = int(round(charge_time / FRAME_SECONDS))
    return [step / frames for step in range(frames + 1)]


@dataclass(frozen=True)
class Outcome:
    low_shots: int
    low_probability: float
    high_shots: int
    high_probability: float


@dataclass(frozen=True)
class Threshold:
    charge_speed_percent: float
    interval: float
    outcome: Outcome


def outcome(inputs: WindowInputs) -> Outcome:
    """The two shot counts this cadence can produce, and how often each.

    The phase the window opens at is not the player's to choose - Fienn's three
    runs opened at 0.05, 0.29 and 0.39 sec - so a single number would be either
    an over- or under-statement. Reporting the guaranteed count alone hides that
    Scarlet reads 19 shots 87% of the time at zero charge speed.

    The split is exact, reload or no reload. Opening the window a delay d after
    a charge completes shifts EVERY shot of the fully-charged timeline by that
    same d, reloads included, because each gap - charge or reload - is measured
    from the shot before it. So the high count survives exactly while
    d < window_seconds - T[high - 1], and d is uniform over one interval. With
    no reload T[high - 1] is (high - 1) intervals and the fraction is the plain
    window/interval - low; with one it is not, and only the timeline knows.
    """
    times = shot_times(inputs, start_charged=True)
    high = len(times)
    low = len(shot_times(inputs, start_charged=False))
    if high == low:
        return Outcome(low, 1.0, high, 0.0)
    high_probability = (inputs.window_seconds - times[high - 1]) / shot_interval(inputs)
    high_probability = min(1.0, max(0.0, high_probability))
    return Outcome(low, 1.0 - high_probability, high, high_probability)


def thresholds(inputs: WindowInputs) -> list[Threshold]:
    """One row per charge-speed step that actually changes the cadence."""
    rows, previous = [], None
    for step in charge_speed_steps(inputs.charge_time):
        stepped = replace(inputs, charge_speed_percent=step)
        interval = shot_interval(stepped)
        if previous is not None and interval == previous:
            continue
        previous = interval
        rows.append(Threshold(step, interval, outcome(stepped)))
    return rows
