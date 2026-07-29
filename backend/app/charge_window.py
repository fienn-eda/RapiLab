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
from dataclasses import dataclass

from app.attack_rate import (FRAME_SECONDS, reload_time_with_speed,
                             shot_interval_with_speed)


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


def reload_intervenes(inputs: WindowInputs) -> bool:
    """Whether the magazine empties before the window closes. When it does, the
    last shot depends on the reload formula, which is a known open question -
    see docs/engine-gaps.md. The UI warns instead of quietly answering."""
    return inputs.max_ammo * shot_interval(inputs) < inputs.window_seconds


# How far from a frame boundary a charge-speed total has to be before the
# engine's aggregation rule and the community's can no longer disagree. The
# engine sums the raw lines and floors once; community sources report each line
# rounding to a whole percent, with equal values summed before rounding
# (arca.live/b/nikketgv/169159561). Across every 1-to-4 line combination the two
# differ on 6.7%, and all of those sit within this many percentage points of a
# boundary - so a total alone is enough to flag the doubt. Which rule is right
# is unresolved: every measurement we hold fails to separate them, and overload
# options roll at random so a player cannot compose a decisive one on demand.
BOUNDARY_TOLERANCE_POINTS = 1.10


def aggregate_charge_speed(lines: list[float], charge_time: float) -> float:
    """Overload charge-speed lines (in percent) as the ratio the engine wants.

    `charge_time` is unused today - the engine's rule needs only the sum - and
    is in the signature because the alternative rule quantises against it. If
    the per-line rounding is ever confirmed, this function is the only thing
    that changes.
    """
    return sum(lines) / 100


def near_frame_boundary(lines: list[float], charge_time: float) -> bool:
    """Whether this total sits close enough to a frame boundary that the two
    aggregation rules could disagree - see BOUNDARY_TOLERANCE_POINTS."""
    total_points = sum(lines)
    frames = charge_time / FRAME_SECONDS
    if frames <= 0:
        return False
    points_per_frame = 100 / frames
    return any(
        abs(total_points - points_per_frame * step) <= BOUNDARY_TOLERANCE_POINTS
        for step in range(int(frames) + 1)
    )


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

    The split is exact only while the magazine outlasts the window. Once a
    reload lands inside it the shots are no longer evenly spaced and the
    fraction is an approximation - which is what `reload_intervenes` exists to
    warn about, since the reload formula is itself unsettled.
    """
    low = len(shot_times(inputs, start_charged=False))
    high = len(shot_times(inputs, start_charged=True))
    if high == low:
        return Outcome(low, 1.0, high, 0.0)
    high_probability = inputs.window_seconds / shot_interval(inputs) - low
    high_probability = min(1.0, max(0.0, high_probability))
    return Outcome(low, 1.0 - high_probability, high, high_probability)


def thresholds(inputs: WindowInputs) -> list[Threshold]:
    """One row per charge-speed step that actually changes the cadence."""
    import dataclasses

    rows, previous = [], None
    for step in charge_speed_steps(inputs.charge_time):
        stepped = dataclasses.replace(inputs, charge_speed_percent=step)
        interval = shot_interval(stepped)
        if previous is not None and interval == previous:
            continue
        previous = interval
        rows.append(Threshold(step, interval, outcome(stepped)))
    return rows
