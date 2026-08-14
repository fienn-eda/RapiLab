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

heating_speed_percent rides the same `_at(t)` pattern and scales the MG's
warm-up (`spinup_with_speed`), sampled at the magazine's start beside
`shot_interval` and `capacity` because the warm-up is a property of the
magazine it opens.

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

    `points` is the warm-up as a CUMULATIVE CURVE: each entry is `(position on
    the ramp, seconds from the magazine's first round to that position)`,
    starting at `(0, 0.0)` and ending where the weapon reaches full speed. The
    rate is constant between two entries, so `elapsed` interpolates linearly
    inside a segment.

    A curve rather than one total because the measurement pins the SHAPE, and
    the shape is what lets a magazine open PART WAY UP the ramp - which is what
    a reload shorter than the heating decay leaves behind.
    """
    points: tuple

    @property
    def intervals(self):
        """Shot gaps the warm-up covers before the weapon is at full speed."""
        return self.points[-1][0]

    @property
    def seconds(self):
        """Seconds a COLD magazine spends warming up."""
        return self.points[-1][1]

    @property
    def cost(self):
        """Seconds a cold magazine loses to warming up, at 60 rounds/sec."""
        return self.seconds - self.intervals / RATE_OF_FIRE_60FPS["MG"]

    def elapsed(self, position):
        """Seconds from the magazine's first round to ramp `position`."""
        if position <= 0:
            return 0.0
        start, started_at = self.points[0]
        for end, ends_at in self.points[1:]:
            if position <= end:
                return started_at + ((ends_at - started_at)
                                     * (position - start) / (end - start))
            start, started_at = end, ends_at
        return self.seconds


# Fienn, 2026-08-07, frame-by-frame (Rosanna solo, 305-round magazine, no reload
# buffs) - docs/measurements/mg-spinup.md. Her first shot lands at frame 863 and
# her 49th at frame 1000, so 48 gaps take 137 frames where top speed would take
# 48; from there to the empty magazine at frame 1256 it is 256 rounds in 256
# frames, exactly one per frame. So the nominal 60/sec was never wrong - it is
# the MAXIMUM, and the engine was handing it out from the first round.
#
# The ramp's SHAPE is measured, not assumed. Three readings that carry ammo
# counts alongside frame numbers put three points on the curve, and the cost sits
# at the front: rounds 0-2 of a cold magazine take 56 frames, 2-24 another 55,
# 24-48 only 26. A rate rising linearly in TIME is ruled out separately (it would
# need a negative starting rate to fit 48 rounds into 137 frames). What is still
# unmeasured is the shape INSIDE 2-24, carried here as a straight line.
#
# The warm-up is per MAGAZINE and a reload re-arms it, including one a skill
# forces by dumping the magazine. Heating does not vanish the instant firing
# stops - it bleeds off over 70 frames (1.16667 sec, Fienn's frame reading of
# the same Rosanna run: last round 1256, fully released 1326), so a gap SHORTER
# than that keeps part of it and the next magazine opens faster than a cold one.
#
# This models every magazine as a cold start, exact whenever the gap clears the
# decay and a floor below it. Natural reloads clear it (Rosanna 1.67 sec, Asuka:
# WILLE 2.478, and 1.080 even on her forced one), so the floor binds on STACKED
# reload speed: Crown plus a level-15 cube leaves a 63-frame gap and an 81-frame
# ramp, Crown plus Privaty a 31-frame gap and a 26-frame ramp, against the cold
# 137 - up to 1.85 sec charged per magazine that the game does not charge.
#
# `magazine_shot_offset` spends this curve, so a cold magazine's TOTAL is the
# measured 137 frames - what the calibration rests on - and the 48 rounds inside
# it sit where they were read rather than evenly. See docs/engine-gaps.md and
# docs/measurements/mg-spinup.md.
#
# Also unsettled by that reading: whether Attack Speed shortens the ramp
# (modeled: no, it is a fixed segment like RELOAD_FIXED_SECONDS).
MG_SPINUP = Spinup(points=((0, 0.0), (2, 56 / 60), (24, 111 / 60), (48, 137 / 60)))

_SPINUP_BY_WEAPON = {"MG": MG_SPINUP}


def spinup_for_weapon(weapon):
    """This weapon class's warm-up, or None for the classes that have none.

    The MG is the only class that has one. `heating` is a term the game applies
    to machine guns alone - the two skills that move it share one word-group id
    and Rei's names `allies with a Machine Gun` as the target - and Fienn
    confirmed in game that an SMG reaches its nominal rate from the first round
    (docs/measurements/smg-no-spinup.md). The SMG still over-reads against the
    record (1.172x, the highest class) but the cause is elsewhere; the leading
    candidate is its 110px spread under the accuracy model.
    """
    return _SPINUP_BY_WEAPON.get(weapon)


# Heating does not vanish when firing stops - it bleeds off, and a magazine that
# opens before it is gone starts PART WAY UP the ramp. Fienn read the release
# three ways (2026-08-14) and they land 6-11% apart: 62 frames from the 31-frame
# gap that kept 24 rounds, 65.8 from the 63-frame gap that kept 2, and 70 read
# directly as "fully released". 66 is where the line through the two RETENTION
# readings crosses zero, and retention is what this constant has to reproduce.
# docs/measurements/mg-spinup.md.
HEATING_DECAY_SECONDS = 66 / 60


def ramp_start_after_gap(spinup, gap_seconds):
    """The ramp position a magazine opens at, `gap_seconds` after the previous
    magazine's last round left the barrel.

    Linear from that last round: a gap that clears `HEATING_DECAY_SECONDS`
    opens a cold magazine, half that gap keeps half the ramp. The front-loaded
    curve does the rest of the work - a magazine that keeps only 3 of the 48
    ramp rounds still skips 56 of the ramp's 89 wasted frames, because that is
    where they were.
    """
    if spinup is None:
        return 0.0
    retained = 1.0 - gap_seconds / HEATING_DECAY_SECONDS
    return max(0.0, min(float(spinup.intervals), spinup.intervals * retained))


# A machine gun does not fire the instant its reload completes: Fienn read 13,
# 12 and 12 frames of pause across the three readings that carry ammo counts
# (docs/measurements/mg-spinup.md). It is part of the firing gap that decides
# how much heating survives, so the two are modeled together. MG only - all
# three readings are machine guns and no other class has been timed.
_POST_RELOAD_DELAY_BY_WEAPON = {"MG": 12.5 / 60}


def post_reload_delay_for_weapon(weapon):
    """Seconds between this weapon's reload completing and its next round."""
    return _POST_RELOAD_DELAY_BY_WEAPON.get(weapon, 0.0)


def spinup_with_speed(spinup, heating_speed_percent, rate_of_fire):
    """This warm-up under a live "MG heating up speed" buff or debuff.

    Fienn's ruling (2026-08-14): the arrow scales the DURATION, so up 100%
    halves the ramp and down 100% doubles it - the same shape as his ruling
    that Ada's charge speed down 300% means charge time x4. The number of gaps
    the ramp covers (`intervals`) does NOT move; those 48 rounds just take
    longer or less long.

    The positive direction deliberately differs from `reload_time_with_speed`,
    whose `(1 - s)` would erase the ramp entirely at up 100%. The negative
    direction agrees with it - both give x2 at down 100%.

    The clamp is per SEGMENT, which is what keeps a warm-up a slow start rather
    than an accelerator: no stretch of the ramp may be tighter than the weapon's
    nominal gap. It binds where the ramp is already nearly at speed - MG_SPINUP's
    tail runs 1.083 frames a round and floors at +8.3%, while its head still has
    28 frames a round to give. So up 100% takes a cold 137 frames to 79.5, not to
    the 68.5 a whole-ramp halving would give.
    """
    if spinup is None or not heating_speed_percent:
        return spinup
    if heating_speed_percent > 0:
        factor = 1.0 / (1 + heating_speed_percent)
    else:
        factor = 1.0 - heating_speed_percent
    nominal = 1.0 / rate_of_fire
    points = [spinup.points[0]]
    start, started_at = spinup.points[0]
    for end, ends_at in spinup.points[1:]:
        span = end - start
        duration = max((ends_at - started_at) * factor, span * nominal)
        points.append((end, points[-1][1] + duration))
        start, started_at = end, ends_at
    return Spinup(points=tuple(points))


def magazine_shot_offset(index, shot_interval, spinup, ramp_start=0.0):
    """Seconds from a magazine's first round to its `index`-th one.

    `ramp_start` is the ramp position this magazine OPENS at - 0.0 for a cold
    magazine, higher when the reload before it was short enough that some
    heating survived. It defaults to a cold start, so a caller that does not
    track heating gets the timeline it always had.

    The single place the spin-up is applied, because four call sites generate
    magazine timelines - `generate_magazine_shot_times`, the segmented
    `_base_shot_records` and the two bullet-marker walks - and they are
    contractually bit-identical when there are no segments.
    """
    if spinup is None or index <= 0:
        return index * shot_interval
    position = ramp_start + index
    spent = spinup.elapsed(ramp_start)
    if position <= spinup.intervals:
        return spinup.elapsed(position) - spent
    return ((spinup.seconds - spent)
            + (position - spinup.intervals) * shot_interval)


def _rounds_from_declaration(rounds, percent, capacity):
    """Whole rounds a fixed `rounds` count (or `percent` of `capacity`, if
    `rounds` is unset) hands back.

    Shared by `AmmoRefund` and `AmmoRefill`, which differ in what TRIGGERS a
    hand-back (a shot counter vs. a known time) but not in how big one is.
    Exactly one of `rounds`/`percent` must be nonzero: a caller building one
    from an unvalidated dict of keys (`raid_simulator.resolve_ammo_refills`'s
    grant) would otherwise get a silently inert refund from two missing keys,
    or a silently ignored `percent` from two present ones (`rounds` wins the
    `if` below).
    """
    if bool(rounds) == bool(percent):
        raise ValueError(
            f"a refund/refill needs exactly one of rounds or percent, got "
            f"rounds={rounds!r} percent={percent!r}")
    if rounds:
        return rounds
    return round(capacity * percent / 100.0)


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

    A refund states its size either in whole `rounds` or as a `percent` of the
    magazine it lands in ("Reload 5.31% of the magazine", Tove's Favorite Item).
    A percentage is rounded to the nearest whole round, the same convention
    magazine capacity itself uses (Fienn, 2026-08-13).

    `first_shot` and `windows` express a ROTATION rather than a plain "every N
    shots": Arcana: Fortune Mate's skill text reads "Two times: Reloads 6
    rounds... Resets when Making Memories is removed" - the reload is the 2nd,
    8th, 14th... attack of a period-6 rotation that only runs while her buff is
    up, never the 6th or 12th (Fienn counted to the 18th in game, 2026-07-28).
    `first_shot` is that phase (0 falls back to the bare period); `windows` are
    the `[start, end)` spans the counter is even running in, restarting at 0
    with each one - see `fires_at` and `counts`.

    `needs_own_burst_window` flags a refund whose `windows` a registry builder
    cannot fill in: the window is [the caster's own burst, that cycle's Full
    Burst end), which only exists once the burst schedule is solved, and a
    registry builder runs before that (it is building the shot generator's
    INPUT). The simulator reads the flag and replaces the refund with one
    carrying real `windows`, once `events` holds the burst times to read them
    from.
    """
    every_shots: int
    rounds: int = 0
    percent: float = 0.0
    first_shot: int = 0
    windows: tuple = ()
    needs_own_burst_window: bool = False

    def __post_init__(self):
        # A bare refund's only termination guarantee is the magazine draining
        # to 0, so rounds >= every_shots (net zero or positive drain) is
        # rejected outright. A rotation is different: it is only ever
        # meaningful paired with a window (Arcana's counter IS the window
        # being up), and a window's own end is what stops the walk - the
        # magazine draining is not required, matching `magazine_shot_count`'s
        # stop_time break. `first_shot` alone (not just `windows`) has to
        # exempt it too, because the window can arrive later via `replace()`
        # (the simulator fills it in once the burst schedule is known) - at
        # the moment a phased refund is first built, windows may still be ().
        if (self.rounds and self.rounds >= self.every_shots
                and not self.first_shot and not self.windows):
            raise ValueError(
                f"a refund of {self.rounds} every {self.every_shots} shots never "
                "empties the magazine")

    def rounds_for(self, capacity):
        """Whole rounds this hands back into a magazine of `capacity`."""
        return _rounds_from_declaration(self.rounds, self.percent, capacity)

    def fires_at(self, count):
        """Whether the `count`-th shot this refund has counted triggers it.

        `first_shot` is the rotation's phase: Arcana's reload is the 2nd, 8th,
        14th ... attack of a period-6 rotation, not the 6th and 12th. Left at 0
        the phase is the period itself, which is the plain "every N shots" the
        cube and EVE use.
        """
        first = self.first_shot or self.every_shots
        return count >= first and (count - first) % self.every_shots == 0

    def counts(self, time):
        """Whether a shot at `time` advances this refund's counter. A refund
        with no windows counts every shot of the fight."""
        return not self.windows or any(s <= time < e for s, e in self.windows)


@dataclass(frozen=True)
class AmmoRefill:
    """Rounds handed back at a KNOWN TIME rather than on a shot counter.

    "Reload 39.88% magazine(s)" on entering Full Burst (Noir) is this shape: the
    trigger is an event the burst cycle already scheduled, not a count of the
    recipient's own shots, and the recipient may not even be the caster. The
    burst cycle is solved before any shot is generated, so these times are known
    when the magazine walk runs.

    A refill that lands while the recipient is reloading is WASTED - the reload
    finishes on its own and the rounds are worth nothing (Fienn, 2026-08-13).
    No special handling is needed for this: a walk always starts a magazine at
    full capacity, and a refill is capped at capacity, so one dated before the
    magazine it would join lands on a magazine with no room and does nothing.
    """
    time: float
    rounds: int = 0
    percent: float = 0.0

    def rounds_for(self, capacity):
        """Whole rounds this hands back into a magazine of `capacity`."""
        return _rounds_from_declaration(self.rounds, self.percent, capacity)


def _gated_to_windows(refund):
    """Whether `refund` fires only inside explicit windows, rather than on the
    plain fight-wide shot counter.

    True if it already carries `windows`, OR if it is DECLARED to need them
    (`needs_own_burst_window`) even before any have been resolved. The
    declaration has to count on its own, not just a non-empty `windows`: a
    refund built with `needs_own_burst_window=True` whose `windows` resolved
    to `()` (its owner's own burst never landed before the fight ended, so no
    window exists to gate it) must stay classified as windowed - and therefore
    permanently inert, since an empty `windows` tuple never matches any shot -
    rather than falling through to the plain "counts every shot of the fight"
    treatment, which would silently UNGATE it (Arcana's rotation reload firing
    all fight long instead of only inside Making Memories). Shared by every
    place that splits refunds into "windowed" vs "plain" so the two
    classifications can never drift apart.
    """
    return bool(refund.windows) or refund.needs_own_burst_window


def _refund_sequence(refund, capacity):
    """`refund` as a tuple, rejecting a set that never empties the magazine.

    A unit can hold more than one source at once - EVE reloads 3 rounds every
    10 shots off her own skill and a Tactical Bear cube hands back 3 more on
    the same cadence - and each keeps its own trigger against the shared shot
    counter. `AmmoRefund` can only vet a whole-round refund by itself, so the
    combined rate is checked here, where the magazine's capacity is known and a
    percentage can finally be resolved: at one round back per shot the walk
    below would never terminate.

    A refund gated to windows (`_gated_to_windows`) is excluded from the sum:
    its window is what bounds the walk (see `magazine_shot_count`'s
    `stop_time`), not the magazine draining, so it legitimately hands back as
    much as it spends - Arcana's rotation does exactly that. One resolved to
    zero windows hands back nothing at all, which the sum would only
    UNDERSTATE by excluding, never overstate into a false "never empties"
    rejection.
    """
    if refund is None:
        return ()
    refunds = (refund,) if isinstance(refund, AmmoRefund) else tuple(refund)
    if sum(r.rounds_for(capacity) / r.every_shots
           for r in refunds if not _gated_to_windows(r)) >= 1:
        raise ValueError(
            f"refunds {refunds} together hand back a round per shot, so the "
            "magazine never empties")
    return refunds


def _apply_due_refills(pending, now, rounds, capacity):
    """Rounds after every refill due at `now` has landed, capped at capacity.

    Mutates `pending`, which both magazine walks keep as a time-sorted list of
    the refills they have not spent yet.
    """
    while pending and pending[0].time <= now:
        rounds = min(capacity, rounds + pending.pop(0).rounds_for(capacity))
    return rounds


def magazine_shot_count(capacity, shots_before, refund, *,
                        time_of_round=None, refills=(), stop_time=None):
    """Rounds this magazine actually fires, and the shot counter afterwards.

    Walks the magazine one round at a time because a refund's value depends on
    the rounds remaining when it lands (it is capped at capacity), and the
    counter it triggers on runs across magazines. `refund` is one AmmoRefund, a
    sequence of them, or None; None returns the capacity untouched, so every
    timeline without a refund keeps its exact arithmetic.

    `refills` are `AmmoRefill`s anywhere in the fight; `time_of_round(i)` gives
    the absolute time of this magazine's 0-based round i. It is a callable
    rather than a set of parameters because the formula differs by weapon -
    magazine weapons offset by spinup, charge weapons by charge time - and each
    generator already holds its own. With no refills the clock is never asked
    for a time, so a timeline without one does no time arithmetic at all. A
    refill older than this magazine needs no special handling to be worthless:
    the walk always starts a magazine at full capacity, and a refill is capped
    at capacity, so one dated before the magazine it would join lands on a
    magazine with no room and does nothing.

    `stop_time` ends the walk at the moment the fight (or the segment) does. A
    refund can hand back as much as the magazine spends - Arcana's rotation
    reloads 6 rounds every 6 shots, which is exactly the point of it - so a
    magazine can stay alive indefinitely and draining is not a termination
    guarantee once time is in play.

    A refund gated to windows (`_gated_to_windows` - `AmmoRefund.windows` set,
    or `needs_own_burst_window` declared even if `windows` resolved empty)
    keeps its OWN local counter, separate from `counter` - its phase is read
    against "the shot's position inside the current window", not the
    fight-wide count. That local counter restarts at 0 every time THIS
    function is called - once per magazine, since `local`/`last_window` are
    built fresh on each call - which also restarts it on a window boundary
    (Arcana's counter "resets when Making Memories is removed") whenever the
    window happens to still be open across a reload too; Fienn's readings
    bound what that costs Arcana's real rate/capacity combinations at <=1
    shot. A refund resolved to zero windows never finds one to sit inside, so
    its local counter never advances and it never fires - permanently inert
    rather than falling into the plain bucket below and firing on every shot
    of the fight ungated. A plain refund reads `counter` (the fight-wide
    count) through the same `fires_at`.
    """
    refunds = _refund_sequence(refund, capacity)
    if not refunds and not refills:
        return capacity, shots_before + capacity
    pending = list(refills)
    pending.sort(key=lambda r: r.time)
    windowed = [r for r in refunds if _gated_to_windows(r)]
    plain = [r for r in refunds if not _gated_to_windows(r)]
    if time_of_round is None:
        if pending:
            raise ValueError(
                "magazine_shot_count needs time_of_round to place timed refills")
        if windowed:
            raise ValueError(
                "magazine_shot_count needs time_of_round to place a windowed refund")
    local = {id(r): 0 for r in windowed}
    last_window = {id(r): None for r in windowed}
    rounds = capacity
    shots = 0
    counter = shots_before
    while rounds > 0:
        now = (time_of_round(shots)
               if time_of_round is not None
               and (pending or stop_time is not None or windowed)
               else None)
        if stop_time is not None and now is not None and now >= stop_time:
            break
        rounds = _apply_due_refills(pending, now, rounds, capacity)
        rounds -= 1
        shots += 1
        counter += 1
        for one in plain:
            if one.fires_at(counter):
                rounds = min(capacity, rounds + one.rounds_for(capacity))
        for one in windowed:
            window = next((w for w in one.windows if w[0] <= now < w[1]), None)
            if window is None:
                continue
            if last_window[id(one)] != window:
                last_window[id(one)] = window
                local[id(one)] = 0
            local[id(one)] += 1
            if one.fires_at(local[id(one)]):
                rounds = min(capacity, rounds + one.rounds_for(capacity))
    return shots, counter


def _refund_carries_windows(refund):
    """Whether `refund` (a single AmmoRefund, a sequence of them, or None)
    includes one gated to windows (`_gated_to_windows`).

    A shape check rather than a call to `_refund_sequence`: that needs a
    magazine capacity to resolve a percentage, which `_walk_magazine` does not
    have a reason to ask for otherwise - whether a windowed refund is present
    is a property of the refund's declaration, not of any magazine it lands
    in.
    """
    if refund is None:
        return False
    refunds = (refund,) if isinstance(refund, AmmoRefund) else refund
    return any(_gated_to_windows(r) for r in refunds)


def _walk_magazine(capacity, shots_fired, refund, *,
                   time_of_round=None, refills=(), stop_time=None):
    """magazine_shot_count, wired for the clock only when something actually
    reads it: timed refills, or a windowed refund reading which window a shot
    falls in.

    `magazine_shot_count` only skips asking its clock for a time when BOTH
    `time_of_round` and `stop_time` are left unpassed - passing `stop_time`
    alone (even with no refills queued) opens a new time-bounded exit that
    a refund-only call never had. Gating the whole keyword group on `refills`
    OR a windowed refund is what every magazine-walking generator in this
    module relies on to keep a refund-free (or plain-refund) timeline doing
    no time arithmetic and reaching exactly the shot count it always did.
    Same keyword shape as `magazine_shot_count` itself, so every call site
    differs from it only by name."""
    if not refills and not _refund_carries_windows(refund):
        return magazine_shot_count(capacity, shots_fired, refund)
    return magazine_shot_count(
        capacity, shots_fired, refund,
        time_of_round=time_of_round, refills=refills, stop_time=stop_time)


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
    heating_speed_percent_at=_zero,
    ammo_refund=None,
    weapon=None,
    ammo_refills=(),
):
    shots = []
    magazine_start = 0.0
    shots_fired = 0
    base_spinup = spinup_for_weapon(weapon)
    post_reload_delay = post_reload_delay_for_weapon(weapon)
    ramp_start = 0.0

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        spinup = spinup_with_speed(
            base_spinup, heating_speed_percent_at(magazine_start), rate_of_fire)
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, iv=shot_interval, sp=spinup, rs=ramp_start: (
                s + magazine_shot_offset(i, iv, sp, rs)),
            refills=ammo_refills, stop_time=fight_duration)
        for i in range(magazine_size):
            shot_time = magazine_start + magazine_shot_offset(i, shot_interval, spinup, ramp_start)
            if shot_time >= fight_duration:
                return shots
            shots.append(shot_time)
        last_round_at = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup, ramp_start)
        magazine_empty_at = last_round_at + shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time + post_reload_delay
        ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_at)

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
    ammo_refills=(),
):
    shots = []
    magazine_start = 0.0
    shots_fired = 0

    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, c=effective_charge: (
                s + c + i * c),
            refills=ammo_refills, stop_time=fight_duration)
        if magazine_size == 0:
            # A refill's stop_time can end the walk before this magazine's
            # OWN first round (magazine_start + a full charge) - unlike a
            # magazine weapon's round 0, which fires at magazine_start itself
            # and so is always inside the window. Nothing else is left to
            # fire before fight_duration either.
            break
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
    ammo_refills=(),
):
    if weapon in CHARGE_WEAPONS:
        return generate_charge_shot_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
            ammo_refund=ammo_refund, ammo_refills=ammo_refills,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return generate_magazine_shot_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
        ammo_refund=ammo_refund, weapon=weapon, ammo_refills=ammo_refills,
    )


def magazine_last_bullet_times(
    rate_of_fire,
    max_ammo,
    reload_time,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    heating_speed_percent_at=_zero,
    ammo_refund=None,
    weapon=None,
    ammo_refills=(),
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
    fired before the reload - so it is threaded through too, and a timed refill
    alongside it."""
    last_bullets = set()
    magazine_start = 0.0
    shots_fired = 0
    base_spinup = spinup_for_weapon(weapon)
    post_reload_delay = post_reload_delay_for_weapon(weapon)
    ramp_start = 0.0

    while magazine_start < fight_duration:
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        spinup = spinup_with_speed(
            base_spinup, heating_speed_percent_at(magazine_start), rate_of_fire)
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, iv=shot_interval, sp=spinup, rs=ramp_start: (
                s + magazine_shot_offset(i, iv, sp, rs)),
            refills=ammo_refills, stop_time=fight_duration)
        last_round_time = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup, ramp_start)
        if last_round_time >= fight_duration:
            return last_bullets
        last_bullets.add(last_round_time)
        magazine_empty_at = last_round_time + shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time + post_reload_delay
        ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_time)

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
    ammo_refills=(),
):
    """Charge-weapon equivalent of `magazine_last_bullet_times` - the round
    that empties each `max_ammo`-shot magazine before reloading. Charge speed
    shortens the per-shot charge time, so it's threaded through to keep these
    times aligned with `generate_charge_shot_times`; an ammo refund moves which
    round empties the magazine, so it is threaded through as well, along with
    any timed refill."""
    last_bullets = set()
    magazine_start = 0.0
    shots_fired = 0

    while magazine_start < fight_duration:
        effective_charge = charge_time_with_speed(
            charge_time, charge_speed_percent_at(magazine_start),
            charge_time_reduction_sec_at(magazine_start))
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, c=effective_charge: (
                s + c + i * c),
            refills=ammo_refills, stop_time=fight_duration)
        if magazine_size == 0:
            # This magazine's own first round (magazine_start + a full charge)
            # already reached fight_duration - nothing of it fired, so there is
            # no last bullet to record and nothing later will fire either.
            return last_bullets
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
    heating_speed_percent_at=_zero,
    ammo_refund=None,
    weapon=None,
    ammo_refills=(),
):
    """Mirror of magazine_last_bullet_times: each magazine's FIRST round,
    INCLUDING the battle-opening magazine at t=0 (a "at the start of battle and
    upon reloading to Max Ammunition" trigger, gap #9 - e.g. Jill Valentine's
    Magnum/Acid Ammo). A magazine whose first shot would land at or after
    fight_duration never fires - the while guard excludes it. A refund does not
    OPEN a magazine - only a reload does - but it delays the next reload, so it
    is threaded through to keep these times aligned, along with any timed
    refill."""
    first_bullets = set()
    magazine_start = 0.0
    shots_fired = 0
    base_spinup = spinup_for_weapon(weapon)
    post_reload_delay = post_reload_delay_for_weapon(weapon)
    ramp_start = 0.0
    while magazine_start < fight_duration:
        first_bullets.add(magazine_start)
        shot_interval = 1.0 / (rate_of_fire * (1 + attack_speed_percent_at(magazine_start)))
        spinup = spinup_with_speed(
            base_spinup, heating_speed_percent_at(magazine_start), rate_of_fire)
        capacity = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, iv=shot_interval, sp=spinup, rs=ramp_start: (
                s + magazine_shot_offset(i, iv, sp, rs)),
            refills=ammo_refills, stop_time=fight_duration)
        last_round_at = magazine_start + magazine_shot_offset(
            magazine_size - 1, shot_interval, spinup, ramp_start)
        magazine_empty_at = last_round_at + shot_interval
        actual_reload_time = reload_time_with_speed(reload_time, reload_speed_percent_at(magazine_empty_at))
        magazine_start = magazine_empty_at + actual_reload_time + post_reload_delay
        ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_at)
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
    ammo_refills=(),
):
    """Charge-weapon mirror: the first charged shot of each magazine (lands
    one effective charge after the magazine starts). A first shot at or after
    fight_duration never fires, so it's checked explicitly. An ammo refund only
    delays the reload, but that moves where the NEXT magazine opens, so it is
    threaded through, along with any timed refill."""
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
        magazine_size, shots_fired = _walk_magazine(
            capacity, shots_fired, ammo_refund,
            time_of_round=lambda i, s=magazine_start, c=effective_charge: (
                s + c + i * c),
            refills=ammo_refills, stop_time=fight_duration)
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
    heating_speed_percent_at=_zero,
    ammo_refund=None,
    ammo_refills=(),
):
    """Weapon-dispatching counterpart of `last_bullet_shot_times` - the subset
    of the shot timeline that OPENS its magazine, for a "at the start of battle
    and upon reloading to Max Ammunition" per_shot_rules trigger (gap #9)."""
    if weapon in CHARGE_WEAPONS:
        return charge_first_bullet_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
            ammo_refund=ammo_refund, ammo_refills=ammo_refills,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return magazine_first_bullet_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
        heating_speed_percent_at=heating_speed_percent_at,
        ammo_refund=ammo_refund, weapon=weapon, ammo_refills=ammo_refills,
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
    heating_speed_percent_at=_zero,
    ammo_refund=None,
    ammo_refills=(),
):
    """Weapon-dispatching counterpart of `generate_shot_times` - the subset
    of that same shot timeline that empties its magazine, for a "last bullet
    fired" per_shot_rules trigger."""
    if weapon in CHARGE_WEAPONS:
        return charge_last_bullet_times(
            charge_time, reload_time, max_ammo, fight_duration,
            max_ammo_percent_at, reload_speed_percent_at, charge_speed_percent_at,
            ammo_refund=ammo_refund, ammo_refills=ammo_refills,
        )
    rate_of_fire = rate_of_fire_for_weapon(weapon)
    return magazine_last_bullet_times(
        rate_of_fire, max_ammo, reload_time, fight_duration,
        max_ammo_percent_at, reload_speed_percent_at, attack_speed_percent_at,
        heating_speed_percent_at=heating_speed_percent_at,
        ammo_refund=ammo_refund, weapon=weapon, ammo_refills=ammo_refills,
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
    # This round's position in its own magazine, which is what an MG's aiming
    # circle tightens against (accuracy.SPREAD_CONVERGENCE). None where the
    # magazine has no position to give: a segment fires a declared profile and
    # never reloads, and its `weapon` label is a hand-written archetype rather
    # than a measured circle, so it takes the converged diameter.
    magazine_index: int | None = None


def _base_shot_records(base, window_start, window_end,
                       max_ammo_percent_at, reload_speed_percent_at,
                       attack_speed_percent_at, charge_speed_percent_at,
                       charge_time_reduction_sec_at=_zero,
                       heating_speed_percent_at=_zero):
    """The base weapon firing over [window_start, window_end) - the same
    arithmetic as generate_{charge,magazine}_shot_times (kept bit-identical so
    a no-segment call reproduces the legacy timeline exactly), restarted with
    a fresh magazine at window_start (the post-transform resume semantic,
    Fienn 2026-07-18). A magazine cut short by window_end gets NO last-bullet
    flag (it never actually emptied - same rule as the fight_duration cutoff).

    An ammo refund rides on `base` the way charge_motion_delay does. Its shot
    counter starts fresh per call, which is the same statement as the resume
    semantic: a real weapon transform arrives loaded and its shots are not this
    magazine's, so they do not count toward the refund trigger. A timed refill
    rides on `base` the same way; it needs no such carve-out (its trigger is a
    clock, not this magazine's own shots), but it is bounded by `window_end`
    exactly like the fight-duration cutoff elsewhere, so one dated inside a
    segment that silences the base weapon finds no magazine here to land on."""
    records = []
    if window_end <= window_start:
        return records
    weapon = base["weapon"]
    refund = base.get("ammo_refund")
    refills = base.get("ammo_refills", ())
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
            magazine_size, shots_fired = _walk_magazine(
                capacity, shots_fired, refund,
                time_of_round=lambda i, s=magazine_start, c=effective_charge: (
                    s + c + i * c),
                refills=refills, stop_time=window_end)
            if magazine_size == 0:
                # Same boundary as generate_charge_shot_times: this magazine's
                # own first round already reached window_end before firing.
                return records
            last_shot_time = None
            for i in range(magazine_size):
                shot_time = magazine_start + effective_charge + i * effective_charge
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], bonus,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1),
                    magazine_index=i))
                last_shot_time = shot_time
            actual_reload = reload_time_with_speed(base["reload_time"], reload_speed_percent_at(last_shot_time))
            magazine_start = last_shot_time + actual_reload
    else:
        rate = rate_of_fire_for_weapon(weapon)
        base_spinup = spinup_for_weapon(weapon)
        post_reload_delay = post_reload_delay_for_weapon(weapon)
        ramp_start = 0.0
        magazine_start = window_start
        while magazine_start < window_end:
            interval = 1.0 / (rate * (1 + attack_speed_percent_at(magazine_start)))
            spinup = spinup_with_speed(
                base_spinup, heating_speed_percent_at(magazine_start), rate)
            capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            magazine_size, shots_fired = _walk_magazine(
                capacity, shots_fired, refund,
                time_of_round=lambda i, s=magazine_start, iv=interval, sp=spinup, rs=ramp_start: (
                    s + magazine_shot_offset(i, iv, sp, rs)),
                refills=refills, stop_time=window_end)
            for i in range(magazine_size):
                shot_time = magazine_start + magazine_shot_offset(i, interval, spinup, ramp_start)
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], 0.0,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1),
                    magazine_index=i))
            last_round_at = magazine_start + magazine_shot_offset(
                magazine_size - 1, interval, spinup, ramp_start)
            magazine_empty_at = last_round_at + interval
            actual_reload = reload_time_with_speed(base["reload_time"], reload_speed_percent_at(magazine_empty_at))
            magazine_start = magazine_empty_at + actual_reload + post_reload_delay
            ramp_start = ramp_start_after_gap(base_spinup, magazine_start - last_round_at)
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

    A refund gated to windows (`_gated_to_windows`) is dropped before the walk
    rather than applied: this walk keeps no per-window counter the way
    `magazine_shot_count` does, so a windowed refund reaching here has no
    gate left to enforce it. Going inert is the same fail-safe
    `magazine_shot_count` uses for a refund whose windows resolved to zero -
    firing it unrestricted would silently ungate it instead.

    The refunds that remain fire on a bare `shots_fired % one.every_shots ==
    0` rather than through `one.fires_at`, the call `magazine_shot_count`'s
    equivalent loop makes. `first_shot` is therefore not honoured here: a
    refund whose rotation phase differs from its period fires on the period
    alone, off phase.

    A timed refill is wired straight into the walk rather than through
    `magazine_shot_count` - this function never calls it, since one magazine
    runs straight through the segments instead of restarting per window. No
    drop rule is needed for a refill dated before this magazine opened: the
    walk here consumes each refill at most once (`pending_refills` is popped,
    not reissued per magazine), and applying it against whatever the current
    magazine holds - full or partly spent - already gives the "wasted during
    reload" answer for free, the same cap that does it everywhere else.
    """
    weapon = base["weapon"]
    base_bonus = base["charge_damage_percent"] / 100 - 1
    records = []
    pending = list(segments)
    cursor = 0.0                 # instant the next charge starts from
    capacity = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(0.0))))
    refunds = _refund_sequence(base.get("ammo_refund"), capacity)
    refunds = tuple(r for r in refunds if not _gated_to_windows(r))
    refills = sorted(base.get("ammo_refills", ()), key=lambda r: r.time)
    pending_refills = [r for r in refills if r.time >= 0.0]
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
        rounds = _apply_due_refills(pending_refills, shot_time, rounds, capacity)
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
                rounds = min(capacity, rounds + one.rounds_for(capacity))
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
    heating_speed_percent_at=_zero,
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
            charge_time_reduction_sec_at, heating_speed_percent_at))
        if seg is None or seg["start"] >= fight_duration:
            break
        reopened_at = (windows[index + 1]["start"]
                       if index + 1 < len(windows) else None)
        seg_records, cursor = _segment_shot_records(
            seg, fight_duration, charge_speed_percent_at, charge_time_reduction_sec_at,
            base.get("charge_motion_delay", 0.0), stop_at=reopened_at)
        records.extend(seg_records)
    return records
