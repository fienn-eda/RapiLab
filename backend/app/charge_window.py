"""How many normal attacks a charge weapon lands inside one Full Burst window.

The cadence itself is NOT computed here - `attack_rate.shot_interval_with_speed`
owns it, including the motion delay and the frame grid the charge snaps to. This
module only walks that interval across a 10-second window, spending magazine and
reloading when it runs out, so a re-measured charge time or delay moves the
calculator without anyone editing it.

The magazine is assumed FULL at window start. For Scarlet: Black Shadow that is
a fact - Fleetly Fading: Asura reloads her instantly on Full Burst entry - and
for Liberalio and Neon it is an assumption the UI states, since nothing records
how much they fired just before the window opened. A Tactical Bear's refund
counter is assumed to start there too, which is a plainer assumption than the
magazine: that counter is cumulative over the whole fight and Asura's reload
does not touch it, so the window opens at a phase nothing records.
"""
from dataclasses import dataclass, replace

from app.attack_rate import (FRAME_SECONDS, AmmoRefund, magazine_shot_count,
                             reload_time_with_speed, shot_interval_with_speed)
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
    # Rounds the wearer's harmony cube hands back mid-magazine. A Tactical Bear
    # decides whether the magazine empties inside the window at all, which on
    # this screen is the difference between two whole shot counts.
    ammo_refund: AmmoRefund | None = None
    # 멈춤이 없는 무기를 대신 묶는 자기 연사 상한
    # (attack_rate.charge_interval_floor_for). None이면 클래스 기본값.
    interval_floor: float | None = None


def shot_interval(inputs: WindowInputs) -> float:
    return shot_interval_with_speed(
        inputs.charge_time,
        inputs.charge_speed_percent,
        inputs.charge_time_reduction_sec,
        motion_delay=inputs.motion_delay,
        interval_floor=inputs.interval_floor,
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
    # How many rounds a magazine actually fires is `magazine_shot_count`'s to
    # say, because a refund is capped at capacity and its counter runs across
    # magazines - the same walker the deck search fires shots through.
    magazine, counter = magazine_shot_count(inputs.max_ammo, 0, inputs.ammo_refund)
    fired = 0
    while time < inputs.window_seconds:
        times.append(time)
        fired += 1
        if fired >= magazine:
            time += reload_gap
            magazine, counter = magazine_shot_count(
                inputs.max_ammo, counter, inputs.ammo_refund)
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
    magazine, _ = magazine_shot_count(inputs.max_ammo, 0, inputs.ammo_refund)
    return magazine * shot_interval(inputs) < inputs.window_seconds


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


def _same_answer(a: Outcome, b: Outcome) -> bool:
    """두 행이 읽는 사람에게 같은 답인가.

    표는 확률을 정수 퍼센트로 적으므로(프론트 `ChargeWindowLadder`의 `odds`)
    그보다 잔 차이는 화면에서 구분되지 않는다. 여기서 그 정밀도를 기준으로 삼는
    이유는, 표에 같은 숫자가 뜨는 행을 남기면 사다리가 답이 아니라 프레임 격자를
    읽게 만들기 때문이다.

    `low_probability`는 `1 - high_probability`라 따로 보지 않는다.
    """
    return (a.low_shots == b.low_shots
            and a.high_shots == b.high_shots
            and round(a.high_probability * 100) == round(b.high_probability * 100))


def thresholds(inputs: WindowInputs, ceiling: float | None = None) -> list[Threshold]:
    """One row per charge-speed step that actually changes the ANSWER.

    간격이 바뀌는 것만으로는 행을 만들지 않는다. 탄창이 상한이면 프레임을 사도
    발이 늘지 않아 표가 같은 숫자를 반복하는데, 그것은 "이만큼 사면 무엇이
    달라지나"에 답하지 않는다 (Fienn, 2026-08-11).

    `ceiling` is the highest total the reader could actually reach - overload
    tops out well before the frame grid does, and steps past it are money that
    does not exist. Left out, the ladder answers the pure frame-grid question
    and runs until the answer stops moving.
    """
    rows, previous = [], None
    for step in charge_speed_steps(inputs.charge_time):
        if ceiling is not None and step > ceiling + 1e-9:
            break
        stepped = replace(inputs, charge_speed_percent=step)
        result = outcome(stepped)
        if previous is not None and _same_answer(result, previous):
            continue
        previous = result
        rows.append(Threshold(step, shot_interval(stepped), result))
    return rows


def ladder_stop_reason(inputs: WindowInputs, rows: list[Threshold],
                       ceiling: float | None = None) -> str:
    """사다리가 왜 거기서 끝났는가 - `"answer"` / `"ceiling"` / `"charge"`.

    화면은 마지막 행 아래에 이유별로 다른 말을 적는데, 그 판정을 프론트가 행
    목록만 보고 추측하면 틀린다: 마지막 행이 상한보다 낮다는 사실만으로는 "상한이
    잘랐다"와 "답이 먼저 멈췄다"를 구분할 수 없다(격자 간격을 알아야 한다).
    그래서 격자를 아는 이쪽이 답한다.

    - `"ceiling"` — 상한 안에서 살 수 있는 마지막 칸까지 답이 계속 바뀌었고,
      격자에는 그 위가 더 있었다. 돈이 모자란 것이다.
    - `"answer"` — 더 살 수 있는데도 살 이유가 없다. 여기서부터는 타수도 확률도
      그대로다.
    - `"charge"` — 격자 자체가 끝났다. 차지가 남아 있지 않다.
    """
    steps = charge_speed_steps(inputs.charge_time)
    last_row = rows[-1].charge_speed_percent if rows else None
    if ceiling is not None and steps[-1] > ceiling + 1e-9:
        affordable = [s for s in steps if s <= ceiling + 1e-9]
        if last_row is not None and affordable and last_row < affordable[-1] - 1e-9:
            return "answer"
        return "ceiling"
    if last_row is not None and last_row < steps[-1] - 1e-9:
        return "answer"
    return "charge"
