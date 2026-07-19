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

A member may carry a `burst_delay` holding its FIRST burst back rather than
firing it the instant the cooldown allows, for units the player deliberately
saves: `{"skip_cycles": N}` keeps it out of the opening N cycles (Diesel:
Winter Sweets, whose locked Intro/Highlight state is decided by whether she
bursts into the first Full Burst), `{"not_before": T}` holds it until T
seconds (Elegg: Boom and Shock, held until her Ghosts reach the cap). The
two forms are not interchangeable - one unit's reason is a cycle count and
the other's is a resource's fill time, and a fight's cycle length varies
with the deck's cooldowns.

A deck missing any member of a burst tier can never complete a cycle at
all - that's the one case still reported as "full_burst_missed" and ends
the simulation, since no amount of waiting fixes it. Attack-rate-driven
gauge fill time and cooldown-reduction effects are intentionally out of
scope here - gauge_charge_time and each Nikke's `cooldown` are supplied by
the caller.
"""

FULL_BURST_DURATION = 10.0


def _ready_at(member, last_used_at, cycle_index):
    """When `member` may next burst: its plain cooldown, pushed later by any
    `burst_delay`. Returns infinity while a `skip_cycles` delay still holds,
    which drops the member out of its tier for that cycle - if it is the
    tier's only member the cycle simply doesn't fire, rather than crediting
    the unit a burst it would not have taken."""
    ready = last_used_at[member["slug"]] + member["cooldown"]
    delay = member.get("burst_delay")
    if not delay:
        return ready
    if cycle_index < delay.get("skip_cycles", 0):
        return float("inf")
    return max(ready, delay.get("not_before", float("-inf")))


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
        on_full_burst_end(time) -> {slug: seconds} - called when Full Burst
            ends; each Nikke's last-used-at is reduced by its entry (an instant
            cooldown pulse). Returning a per-slug map lets a self-scoped pulse
            (e.g. Blanc's own CDR) reduce only the caster's cooldown while a
            squad-scoped one reduces everyone's.
    """
    gap = 0.0 if mode == "auto" else 0.1
    last_used_at = {member["slug"]: float("-inf") for member in deck}
    members_by_tier = {
        tier: [member for member in deck if member["burst_tier"] == tier] for tier in (1, 2, 3)
    }
    events = []
    time = 0.0
    cycle_index = 0

    if on_battle_start:
        on_battle_start(0.0)

    while True:
        gauge_ready = time + gauge_charge_time

        if any(not members_by_tier[tier] for tier in (1, 2, 3)):
            events.append({"type": "full_burst_missed", "time": gauge_ready})
            break

        tier_ready_time = {
            tier: min(_ready_at(member, last_used_at, cycle_index) for member in members_by_tier[tier])
            for tier in (1, 2, 3)
        }
        fire_time = max(gauge_ready, *tier_ready_time.values())

        if fire_time >= fight_duration:
            break

        tier3_fire_time = None
        for tier in (1, 2, 3):
            # Same arithmetic as tier_ready_time (last + cooldown vs fire_time):
            # subtracting instead (fire_time - last >= cooldown) rounds
            # differently and can reject the very member whose ready time
            # defined fire_time (e.g. 51.44 - 31.44 = 19.999...996 < 20.0).
            eligible = [
                member
                for member in members_by_tier[tier]
                if _ready_at(member, last_used_at, cycle_index) <= fire_time
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
            for slug, reduction in cooldown_reduction.items():
                last_used_at[slug] -= reduction

        time = full_burst_end
        cycle_index += 1

    return events
