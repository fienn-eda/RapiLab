"""Schedules burst-skill activations and Full Burst windows over a fight.

Models the rotation Fienn described: burst skills fire the instant their
cooldown allows, not on a fixed delay, and `gauge_charge_time` is the minimum
time after Full Burst ends before the next cycle can even begin.

That floor is inert in MOST decks - gauge charge finishes before the next
tier's cooldown clears, so the cooldown is the only bottleneck. It stops being
inert where a deck's own cooldown reduction is large enough to outrun the
gauge: with Volume's Drop the Beat read correctly as cumulative (up to 8.21 sec
off every ally's cooldown from the third Full Burst on), the steady-state cycle
becomes exactly `FULL_BURST_DURATION + gauge_charge_time + tier gap` and this
floor sets the rotation's rate, scaling every unit's damage.

The real gauge fills from damage dealt, so it is a property of the DECK, not
the boss, and no single constant is right for both regimes. See
BossProfile.gauge_charge_time for why the default is set low, and
docs/roadmap.md for the measured error that leaves.

Burst tiers 1/2/3 then fire in order (auto-battle: back to back; manual:
0.1s apart), triggering a 10s Full Burst window. Per-Nikke cooldowns are
tracked from time-of-use, matching the game rule Fienn gave.

A member may carry a `burst_delay` holding its FIRST burst back rather than
firing it the instant the cooldown allows, for units the player deliberately
saves: `{"skip_cycles": N}` keeps it out of the opening N cycles (Diesel:
Winter Sweets, whose locked Intro/Highlight state is decided by whether she
bursts into the first Full Burst), `{"not_before": T}` holds it until T
seconds, and `{"min_interval": S}` stretches its EFFECTIVE cooldown to S when
the resource it waits on refills slower than the cooldown clears (Elegg: held
until her Ghosts reach the cap, and again for each refill after her burst
spends them). The cycle-count and the time forms are not interchangeable -
one unit's reason is a cycle count and the other's is a resource's fill time,
and a fight's cycle length varies with the deck's cooldowns.

A member may instead take ITSELF out of the rotation: `self_stun` of
`{"seconds": S, "cycles": N}` makes it unavailable for S seconds after every
Nth Full Burst ends. Unlike `burst_delay` this recurs and is anchored on a
mid-fight event, which is what Mast: Romantic Maid's Hangover is - at max
Drunken stacks she stuns herself, and without an Anchor to clear a stack each
cycle she reaches that cap every third one. A tier-mate covers the cycles she
misses; alone in her tier, the cycle waits for her.

A member may also carry `max_bursts`, capping how many times that SEAT spends
its burst: 0 is a totem, seated for its passive kit and never burst at all, and
1 is an opening burst then held for the rest of the fight. Unlike `burst_delay`,
which is a property of the unit's own kit, this is a decision the player made in
one particular run, so it only ever reaches the scheduler from a caller holding
a real record - never from the registry.

A deck missing any member of a burst tier can never complete a cycle at
all - that's the one case still reported as "full_burst_missed" and ends
the simulation, since no amount of waiting fixes it. Attack-rate-driven
gauge fill time and cooldown-reduction effects are intentionally out of
scope here - gauge_charge_time and each Nikke's `cooldown` are supplied by
the caller.
"""

FULL_BURST_DURATION = 10.0

# Full Burst opens AFTER the Burst 3's cast resolves: the cycle is
# [stage 3 entered -> B3 uses its burst -> Full Burst starts], so the B3's own
# burst damage is settled before the window exists (Fienn, in-game range
# measurement 2026-07-27 - see docs/decisions.md). This constant carries that
# ORDERING, not a duration: the real gap is below measurement resolution, but
# the order is certain. Keeping the two instants distinct is what stops a
# `full_burst_enter` buff - and the Full Burst bonus itself - from leaking
# backwards into the cast that opened the window.
FULL_BURST_OPEN_DELAY = 1e-6


def _ready_at(member, last_used_at, last_fired_at, cycle_index, fire_count,
              stunned_until):
    """When `member` may next burst: its plain cooldown, pushed later by any
    `burst_delay` and by a self-stun still running. Returns infinity while a
    `skip_cycles` delay still holds, which drops the member out of its tier for
    that cycle - if it is the tier's only member the cycle simply doesn't fire,
    rather than crediting the unit a burst it would not have taken. A seat that
    has already spent its `max_bursts` is out of its tier the same way,
    permanently."""
    max_bursts = member.get("max_bursts")
    if max_bursts is not None and fire_count[member["slug"]] >= max_bursts:
        return float("inf")
    # A stun is not a cooldown: it starts from a mid-fight event and simply
    # makes her unavailable until it lapses, whatever her cooldown says.
    ready = max(last_used_at[member["slug"]] + member["cooldown"],
                stunned_until[member["slug"]])
    delay = member.get("burst_delay")
    if not delay:
        return ready
    if cycle_index < delay.get("skip_cycles", 0):
        return float("inf")
    if "min_interval" in delay:
        # Measured from when the unit ACTUALLY fired, not from the
        # CDR-rewound last_used_at: a min_interval stands for a resource
        # refilling on wall clock, which no ally's cooldown reduction speeds
        # up.
        ready = max(ready, last_fired_at[member["slug"]] + delay["min_interval"])
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
    # Mirrors last_used_at but is never rewound by cooldown reduction, so a
    # burst_delay's min_interval measures real elapsed time.
    last_fired_at = dict(last_used_at)
    fire_count = {member["slug"]: 0 for member in deck}
    # A member who stuns HERSELF is out of the rotation until it lapses - see
    # `self_stun` in the module docstring.
    stunned_until = {member["slug"]: float("-inf") for member in deck}
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
            tier: min(
                _ready_at(member, last_used_at, last_fired_at, cycle_index,
                          fire_count, stunned_until)
                for member in members_by_tier[tier]
            )
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
                if _ready_at(member, last_used_at, last_fired_at, cycle_index,
                             fire_count, stunned_until) <= fire_time
            ]
            chosen = eligible[0]
            events.append({"type": "burst", "tier": tier, "slug": chosen["slug"], "time": fire_time})
            last_used_at[chosen["slug"]] = fire_time
            last_fired_at[chosen["slug"]] = fire_time
            fire_count[chosen["slug"]] += 1
            if on_tier_fire:
                on_tier_fire(tier, chosen["slug"], fire_time)
            if tier == 3:
                tier3_fire_time = fire_time
            fire_time += gap

        full_burst_start = tier3_fire_time + FULL_BURST_OPEN_DELAY
        if on_full_burst_enter:
            on_full_burst_enter(full_burst_start)

        full_burst_end = full_burst_start + FULL_BURST_DURATION
        events.append({"type": "full_burst_start", "time": full_burst_start})
        events.append({"type": "full_burst_end", "time": full_burst_end})

        for member in deck:
            stun = member.get("self_stun")
            if stun and (cycle_index + 1) % stun["cycles"] == 0:
                stunned_until[member["slug"]] = full_burst_end + stun["seconds"]

        cooldown_reduction = on_full_burst_end(full_burst_end) if on_full_burst_end else None
        if cooldown_reduction:
            for slug, reduction in cooldown_reduction.items():
                last_used_at[slug] -= reduction

        time = full_burst_end
        cycle_index += 1

    return events
