"""Schedules burst-skill activations and Full Burst windows over a fight.

Models the rotation Fienn described: burst gauge (charged jointly by all 5
squad members) fills over `gauge_charge_time`, then burst tiers 1/2/3 fire in
order (auto-battle: back to back; manual: 0.1s apart), triggering a 10s Full
Burst window. Gauge only starts refilling once Full Burst ends.

Per-Nikke burst cooldowns are tracked from time-of-use, matching the game
rule Fienn gave. Attack-rate-driven gauge fill time and cooldown-reduction
effects are intentionally out of scope here - gauge_charge_time and each
Nikke's `cooldown` are supplied by the caller.
"""

FULL_BURST_DURATION = 10.0


def simulate_burst_cycle(
    deck,
    gauge_charge_time,
    fight_duration,
    mode="auto",
    on_battle_start=None,
    on_tier_fire=None,
    on_full_burst_enter=None,
    on_full_burst_end=None,
):
    """Optional hooks let a caller (e.g. raid_simulator) interleave skill
    triggers with the scheduling without duplicating this algorithm:
        on_battle_start(time)             - called once, before the first cycle
        on_tier_fire(tier, slug, time)     - called as each burst tier fires
        on_full_burst_enter(time)          - called when tier 3 fires
        on_full_burst_end(time) -> seconds - called when Full Burst ends; the
            returned number of seconds (if any) is subtracted from every
            Nikke's last-used-at, i.e. an instant squad-wide cooldown pulse.
    """
    gap = 0.0 if mode == "auto" else 0.1
    last_used_at = {member["slug"]: float("-inf") for member in deck}
    events = []
    time = 0.0

    if on_battle_start:
        on_battle_start(0.0)

    while True:
        charge_end = time + gauge_charge_time
        if charge_end >= fight_duration:
            break

        fire_time = charge_end
        tier3_fire_time = None
        cycle_completed = True

        for tier in (1, 2, 3):
            eligible = [
                member
                for member in deck
                if member["burst_tier"] == tier
                and fire_time - last_used_at[member["slug"]] >= member["cooldown"]
            ]
            if not eligible:
                cycle_completed = False
                break

            chosen = eligible[0]
            events.append({"type": "burst", "tier": tier, "slug": chosen["slug"], "time": fire_time})
            last_used_at[chosen["slug"]] = fire_time
            if on_tier_fire:
                on_tier_fire(tier, chosen["slug"], fire_time)
            if tier == 3:
                tier3_fire_time = fire_time
            fire_time += gap

        if not cycle_completed:
            events.append({"type": "full_burst_missed", "time": fire_time})
            break

        if on_full_burst_enter:
            on_full_burst_enter(tier3_fire_time)

        full_burst_end = tier3_fire_time + FULL_BURST_DURATION
        events.append({"type": "full_burst_start", "time": tier3_fire_time})
        events.append({"type": "full_burst_end", "time": full_burst_end})

        cooldown_reduction = on_full_burst_end(full_burst_end) if on_full_burst_end else None
        if cooldown_reduction:
            for slug in last_used_at:
                last_used_at[slug] -= cooldown_reduction

        time = full_burst_end

    return events
