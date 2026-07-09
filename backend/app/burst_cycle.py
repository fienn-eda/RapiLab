"""Schedules burst-skill activations and Full Burst windows over a fight.

Models the rotation Fienn described: gauge charge is fast enough that a
raid-viable deck always finishes charging before the next burst tier's
cooldown clears, so the real bottleneck on when the next Full Burst starts
is whichever tier's cooldown comes off latest - burst skills fire the
instant their cooldown allows, not on a fixed delay. `gauge_charge_time` is
kept only as a floor (the minimum time after Full Burst ends before the
next cycle can even begin), matching "gauge finishes charging before the
cooldown does" rather than gating the cycle on its own.

Burst tiers 1/2/3 then fire in order (auto-battle: back to back; manual:
0.1s apart), triggering a 10s Full Burst window. Per-Nikke cooldowns are
tracked from time-of-use, matching the game rule Fienn gave.

A deck missing any member of a burst tier can never complete a cycle at
all - that's the one case still reported as "full_burst_missed" and ends
the simulation, since no amount of waiting fixes it. Attack-rate-driven
gauge fill time and cooldown-reduction effects are intentionally out of
scope here - gauge_charge_time and each Nikke's `cooldown` are supplied by
the caller.
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
    members_by_tier = {
        tier: [member for member in deck if member["burst_tier"] == tier] for tier in (1, 2, 3)
    }
    events = []
    time = 0.0

    if on_battle_start:
        on_battle_start(0.0)

    while True:
        gauge_ready = time + gauge_charge_time

        if any(not members_by_tier[tier] for tier in (1, 2, 3)):
            events.append({"type": "full_burst_missed", "time": gauge_ready})
            break

        tier_ready_time = {
            tier: min(last_used_at[member["slug"]] + member["cooldown"] for member in members_by_tier[tier])
            for tier in (1, 2, 3)
        }
        fire_time = max(gauge_ready, *tier_ready_time.values())

        if fire_time >= fight_duration:
            break

        tier3_fire_time = None
        for tier in (1, 2, 3):
            eligible = [
                member
                for member in members_by_tier[tier]
                if fire_time - last_used_at[member["slug"]] >= member["cooldown"]
            ]
            chosen = eligible[0]
            events.append({"type": "burst", "tier": tier, "slug": chosen["slug"], "time": fire_time})
            last_used_at[chosen["slug"]] = fire_time
            if on_tier_fire:
                on_tier_fire(tier, chosen["slug"], fire_time)
            if tier == 3:
                tier3_fire_time = fire_time
            fire_time += gap

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
