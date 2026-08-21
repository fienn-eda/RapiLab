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

# 풀 버스트 창의 하한. 창 길이를 줄이는 유닛(이사벨의 "Full Burst Time -5 sec")이
# 기본 길이보다 큰 값을 깎는 배치는 오늘 데이터에 없지만, 길이가 음수인 창은
# 아래의 모든 [start, end) 검사를 조용히 뒤집으므로 여기서 막는다.
MIN_FULL_BURST_DURATION = 0.0


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
    full_burst_duration_overrides=None,
    gauge_charge_overrides=None,
    on_battle_start=None,
    on_tier_fire=None,
    on_full_burst_enter=None,
    on_full_burst_end=None,
):
    """Optional hooks let a caller (e.g. raid_simulator) interleave skill
    triggers with the scheduling without duplicating this algorithm:
        on_battle_start(time)             - called once, before the first cycle
        on_tier_fire(tier, slug, time)     - called as each burst tier fires
        on_full_burst_enter(start, end)     - called when tier 3 fires; `end` is
            when the window this Burst 3 opened will close, which the tier-3
            unit's own kit may have moved
        on_full_burst_end(time) -> {slug: seconds} - called when Full Burst
            ends; each Nikke's last-used-at is reduced by its entry (an instant
            cooldown pulse). Returning a per-slug map lets a self-scoped pulse
            (e.g. Blanc's own CDR) reduce only the caster's cooldown while a
            squad-scoped one reduces everyone's.

    `full_burst_duration_overrides`는 {사이클 인덱스: 초}로, 그 사이클의 창
    길이에 더해진다. 이 스케줄러는 그 값이 어디서 왔는지 모른다 - 값이
    사이클마다 달라지는 확장(소다의 Beginner's Rewards는 골든칩 스택에 따라
    +0/+2/+5초)은 자원 상태를 봐야 정해지는데, 자원은 이 스케줄러가 창을
    확정한 뒤에야 채워지기 때문이다. raid_simulator가 고정점까지 반복하며
    이 테이블을 갱신한다.

    `gauge_charge_overrides`는 {사이클 인덱스: 초}로, 그 사이클의 게이지 하한을
    통째로 대체한다(`gauge_charge_time`은 그 표에 없는 사이클의 값이자 첫 패스의
    시드다). 게이지는 덱이 넣은 **타격 수**로 차므로 사이클마다 다르다 - 재장전과
    MG 예열이 창 안 어디에 떨어지느냐가 그 사이클의 채움 속도를 정한다.
    이 스케줄러는 값이 어디서 왔는지 모른다. raid_simulator가 고정점까지
    반복하며 이 표를 갱신한다.

    각 "burst" 이벤트는 `gauge_bound`와 `gauge_delay`를 달고 나온다 - 그 사이클의
    발동 시각을 **게이지가 정했는가**(쿨다운보다 늦게 준비됐는가)와 **몇 초나
    늦었는가**다. 등호는 거짓이고 밀리지 않은 사이클의 지연은 0이다.
    이 자리에서만 알 수 있어서 여기서 싣는다: 이벤트 로그의 시각만으로는
    게이지와 쿨다운이 같은 사이클을 게이지가 이긴 사이클과 구별할 수 없고,
    쿨다운이 언제 준비됐는지가 로그에 없어 지연의 크기도 되유도할 수 없다.
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
        gauge_ready = time + (gauge_charge_overrides or {}).get(cycle_index, gauge_charge_time)

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

        # A tier whose every member is out for good - the lone member of its
        # tier holding a `skip_cycles` delay (the delay lifts on the cycle
        # AFTER this one, and this one is the cycle that would have advanced
        # the count), or one that has spent its `max_bursts` - is the same dead
        # end as a tier with no members at all: no amount of waiting fixes it.
        # It reports the same way rather than leaving through the end-of-fight
        # branch below, where an empty event list reads as "the fight ended".
        if any(tier_ready_time[tier] == float("inf") for tier in (1, 2, 3)):
            events.append({"type": "full_burst_missed", "time": gauge_ready})
            break

        cooldown_ready = max(tier_ready_time.values())
        fire_time = max(gauge_ready, cooldown_ready)
        # 게이지가 이 사이클을 **밀었는가**, 그리고 **얼마나** - 쿨다운은 전부
        # 돌았는데 게이지가 안 차서 기다린 사이클과 그 시간(Fienn의 용어로
        # **버충 밀림**). 등호는 밀림이 아니다: 두 시각이 같으면 게이지가 없었어도
        # 같은 때 터졌으므로 아무것도 밀리지 않았다. `max()`를 고르는 이 자리가
        # 어느 쪽이 얼마나 이겼는지 아는 유일한 자리라 여기서 선언한다 - 나중에
        # 실현된 간격에서 되유도하면 그 동점을 다시 가려낼 수 없다.
        #
        # 개수와 시간을 **둘 다** 싣는 이유: 둘은 서로를 못 대신한다. 실측 덱 1과
        # 덱 3은 똑같이 14사이클 중 11이 밀리는데 합계가 4.3초 대 11.6초이고,
        # Fienn의 판독은 그 둘을 「안 밀림」과 「밀림」으로 가른다.
        gauge_bound = gauge_ready > cooldown_ready
        # 안 밀었으면 0이다 - 「쿨다운이 게이지를 몇 초 이겼는가」는 밀림이 아니라
        # 합계에 들어갈 자리가 없다. 첫 사이클도 0이다: 돌고 있던 쿨다운이 없어
        # (`cooldown_ready`가 -inf) 무엇에 대해 밀렸는지 말할 수 없고, 빼면
        # 무한대가 나와 합계를 통째로 오염시킨다. 개수가 첫 사이클을 빼는 것과
        # 같은 이유로 같은 사이클이 빠진다.
        gauge_delay = (gauge_ready - cooldown_ready
                       if gauge_bound and cooldown_ready > float("-inf") else 0.0)

        if fire_time >= fight_duration:
            break

        tier3_fire_time = None
        tier3_member = None
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
            # `gauge_bound`/`gauge_delay`는 사이클의 성질이라 그 사이클의 세
            # 버스트가 모두 같은 값을 단다 - 셋이 함께 밀린 것이지 하나만 밀린
            # 것이 아니다.
            events.append({"type": "burst", "tier": tier, "slug": chosen["slug"],
                           "time": fire_time, "gauge_bound": gauge_bound,
                           "gauge_delay": gauge_delay})
            last_used_at[chosen["slug"]] = fire_time
            last_fired_at[chosen["slug"]] = fire_time
            fire_count[chosen["slug"]] += 1
            if on_tier_fire:
                on_tier_fire(tier, chosen["slug"], fire_time)
            if tier == 3:
                tier3_fire_time = fire_time
                tier3_member = chosen
            fire_time += gap

        full_burst_start = tier3_fire_time + FULL_BURST_OPEN_DELAY
        # 창 길이는 이 사이클을 연 Burst 3이 정한다: 자기 버스트가 풀 버스트 자체를
        # 늘리거나 줄이는 유닛이 있고(이사벨 -5초, 모더니아 +5초), 그 효과는 그 유닛이
        # 연 사이클에만 걸린다.
        duration = max(
            MIN_FULL_BURST_DURATION,
            FULL_BURST_DURATION
            + tier3_member.get("full_burst_duration_delta", 0.0)
            + (full_burst_duration_overrides or {}).get(cycle_index, 0.0),
        )
        full_burst_end = full_burst_start + duration
        if on_full_burst_enter:
            on_full_burst_enter(full_burst_start, full_burst_end)

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
