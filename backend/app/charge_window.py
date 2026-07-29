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

from app.attack_rate import reload_time_with_speed, shot_interval_with_speed


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
