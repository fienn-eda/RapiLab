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
magazine weapons, effective charge_time = charge_time / (1 + charge_speed) for
charge weapons. Like max_ammo_percent they're evaluated once per magazine (at
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
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(magazine_empty_at))
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
):
    shots = []
    magazine_start = 0.0

    while magazine_start < fight_duration:
        effective_charge = charge_time / (1 + charge_speed_percent_at(magazine_start))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_shot_time = None
        for i in range(magazine_size):
            shot_time = magazine_start + effective_charge + i * effective_charge
            if shot_time >= fight_duration:
                return shots
            shots.append(shot_time)
            last_shot_time = shot_time
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(last_shot_time))
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
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(magazine_empty_at))
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
):
    """Charge-weapon equivalent of `magazine_last_bullet_times` - the round
    that empties each `max_ammo`-shot magazine before reloading. Charge speed
    shortens the per-shot charge time, so it's threaded through to keep these
    times aligned with `generate_charge_shot_times`."""
    last_bullets = set()
    magazine_start = 0.0

    while magazine_start < fight_duration:
        effective_charge = charge_time / (1 + charge_speed_percent_at(magazine_start))
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_round_time = magazine_start + effective_charge + (magazine_size - 1) * effective_charge
        if last_round_time >= fight_duration:
            return last_bullets
        last_bullets.add(last_round_time)
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(last_round_time))
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
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(magazine_empty_at))
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
):
    """Charge-weapon mirror: the first charged shot of each magazine (lands
    one effective charge after the magazine starts). A first shot at or after
    fight_duration never fires, so it's checked explicitly."""
    first_bullets = set()
    magazine_start = 0.0
    while magazine_start < fight_duration:
        effective_charge = charge_time / (1 + charge_speed_percent_at(magazine_start))
        first_shot = magazine_start + effective_charge
        if first_shot >= fight_duration:
            return first_bullets
        first_bullets.add(first_shot)
        magazine_size = max(1, round(max_ammo * (1 + max_ammo_percent_at(magazine_start))))
        last_round_time = magazine_start + effective_charge + (magazine_size - 1) * effective_charge
        actual_reload_time = reload_time / (1 + reload_speed_percent_at(last_round_time))
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


def _base_shot_records(base, window_start, window_end,
                       max_ammo_percent_at, reload_speed_percent_at,
                       attack_speed_percent_at, charge_speed_percent_at):
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
            effective_charge = base["charge_time"] / (1 + charge_speed_percent_at(magazine_start))
            magazine_size = max(1, round(base["max_ammo"] * (1 + max_ammo_percent_at(magazine_start))))
            last_shot_time = None
            for i in range(magazine_size):
                shot_time = magazine_start + (i + 1) * effective_charge
                if shot_time >= window_end:
                    return records
                records.append(ShotRecord(
                    shot_time, weapon, base["damage_percent"], bonus,
                    is_first_bullet=(i == 0), is_last_bullet=(i == magazine_size - 1)))
                last_shot_time = shot_time
            actual_reload = base["reload_time"] / (1 + reload_speed_percent_at(last_shot_time))
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
            actual_reload = base["reload_time"] / (1 + reload_speed_percent_at(magazine_empty_at))
            magazine_start = magazine_empty_at + actual_reload
    return records


def _segment_shot_records(seg, fight_duration, charge_speed_percent_at):
    """Shots of one override window. Cadence: charge-style profiles
    (charge_time) honor live charge-speed buffs; explicit rate_of_fire
    profiles are measurement anchors and take NO cadence buffs (the measured
    count already includes every in-game modifier). Segments never reload
    (no v1 consumer needs it). Returns (records, segment_end): until_shots
    windows end AT their last shot's time - the base weapon resumes at that
    same instant with a fresh magazine."""
    profile = seg["profile"]
    start = seg["start"]
    if profile.get("charge_time"):
        interval = profile["charge_time"] / (1 + charge_speed_percent_at(start))
    else:
        interval = 1.0 / profile["rate_of_fire"]
    charge = profile.get("charge_damage_percent")
    bonus = charge / 100 - 1 if charge else 0.0
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
                   damage_type=profile.get("damage_type"))
        for t in times if t < fight_duration
    ]
    return records, min(seg_end, fight_duration)


def generate_segmented_shots(
    base,
    segments,
    fight_duration,
    max_ammo_percent_at=_zero,
    reload_speed_percent_at=_zero,
    attack_speed_percent_at=_zero,
    charge_speed_percent_at=_zero,
):
    """Full shot-record timeline for a unit whose weapon profile changes
    inside module-scheduled windows (weapon transforms - see
    docs/superpowers/specs/2026-07-18-weapon-transform-design.md). With no
    segments this reproduces generate_shot_times bit-for-bit (regression
    anchor), plus first/last-bullet flags equal to the marker trios."""
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
            reload_speed_percent_at, attack_speed_percent_at, charge_speed_percent_at))
        if seg is None or seg["start"] >= fight_duration:
            break
        seg_records, cursor = _segment_shot_records(seg, fight_duration, charge_speed_percent_at)
        records.extend(seg_records)
    return records
