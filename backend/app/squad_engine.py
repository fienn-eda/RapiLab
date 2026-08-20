"""General rules engine for conditional skill effects.

NIKKE skills often branch on live squad state ("if there are no other Burst 1
allies...") or on a per-Nikke status flag the skill itself sets/clears
("My Own Star", "Combat Assist"). SquadContext holds that mutable state;
SkillRule pairs a trigger + condition with an action so the same skill data
can be evaluated correctly regardless of which other Nikkes are in the deck.
"""
from dataclasses import dataclass, field
from typing import Callable

from app.effects import EffectRegistry


@dataclass
class SquadMember:
    slug: str
    burst_tier: int
    element: str
    # Weapon type ("AR"/"SG"/...), for member-subset filters like "all Wind
    # Code allies with assault rifles" (gap #3). Optional so contexts that
    # don't need weapon targeting (most tests) stay unchanged.
    weapon: str | None = None


class SquadContext:
    def __init__(
        self,
        members: list[SquadMember],
        base_atk: dict[str, float] | None = None,
        base_charge_time: dict[str, float] | None = None,
        boss_element: str | None = None,
        part_destructible: bool = False,
        part_destruction_times: tuple[float, ...] = (),
        core_hittable: bool = False,
        target_grants: list[dict] | None = None,
        adjacency: dict[str, list[str]] | None = None,
        late_flat_max_hp=None,
    ):
        self.members = members
        # slug -> the 2 allies seated beside it, for a bullet that targets
        # "self and 2 allies on both sides" (Rouge's Sword Coin). This is a
        # SEPARATE axis from the deck list order, which is burst priority (see
        # deck_search._buffer_seat_valid) - in game the player arranges the 5
        # seats freely and taps whichever burst is ready, so reading adjacency
        # off the list index would tie together two things the game keeps
        # apart. None (the search-time default) means no seating was chosen and
        # `neighbor_slugs` falls back to its policy; the report stage supplies a
        # concrete one (deck_search.evaluate_deck_best_seating).
        self.adjacency: dict[str, list[str]] = adjacency or {}
        # each member's base (summary) ATK, so a rule targeting "the N allies with
        # the highest final ATK" can rank them live (see top_atk_slugs). Injected by
        # raid_simulator; empty for contexts that don't need ranking.
        self.base_atk: dict[str, float] = base_atk or {}
        # each member's BASE charge time, so "the ally with the longest basic
        # Charge Time" (Mana's Metal sigma) can be resolved. Basic = the
        # weapon's own value, unmodified by buffs, which is what that wording
        # asks for. Magazine weapons have 0 and never win. Empty for contexts
        # without weapon stats.
        self.base_charge_time: dict[str, float] = base_charge_time or {}
        # the boss's element ("Fire"/"Water"/"Wind"/"Iron"/"Electric"), so a
        # SkillRule gated on "if the enemy is X Code" (e.g. Brid's Wind-Code Damage
        # Taken debuff) can read it via the boss_is_element condition. Only
        # raid_simulator knows the boss; None for element-agnostic contexts.
        self.boss_element: str | None = boss_element
        # whether the boss has a part-destruction gimmick (BossProfile flag,
        # threaded via raid_simulator), so a SkillRule gated on it (e.g. Ark
        # Ranger Black's battery-driven Transformation) can read it via the
        # boss_part_destructible condition. False when unset.
        self.part_destructible: bool = part_destructible
        # 이 인카운터에서 파츠가 실제로 깨지는 시각들(초). 공지가 아니라 그 보스를
        # 관측해서 나오는 값이라 `core_diameter_px`와 같은 계열이고, 비어 있으면
        # (기본값) 파괴에 반응하는 스킬은 `part_destructible` 불리언만 보던 옛
        # 근사 그대로 돈다. 시각이 있으면 그 근사 대신 시각마다 스킬 자신의
        # 지속시간만큼 창이 열린다 - `boss_part_destruction_untimed`가 둘을 가른다.
        self.part_destruction_times: tuple[float, ...] = tuple(part_destruction_times)
        # whether the boss's core is exploitable this sim (raid_simulator's
        # core_hittable flag), so a rule gated on core existence (e.g.
        # Cinderella: Crystal Wave's MG-mode core-strike nuke) can read it.
        self.core_hittable: bool = core_hittable
        # An EffectRegistry holding the `flat_max_hp` that a LATER pass of this
        # same simulation writes - see live_max_hp.
        self._late_flat_max_hp = late_flat_max_hp
        # Whether any rule actually asked for a Max HP conversion. raid_simulator
        # only pays for a second simulation pass when one did: a deck whose late
        # passes write flat_max_hp that nobody converts gains nothing from it.
        self.max_hp_conversion_used: bool = False
        # top-N 대상형 버프가 누구에게 갔는지의 기록. None이면 아무것도 남기지
        # 않는다 - 탐색은 한 요청에 수만 번 돌므로 기본이 off여야 한다.
        # 미란다 계산기가 이 로그를 읽는다(app/miranda_targets.py) - 덱 안의 모든
        # 캐스터의 top-N 대상형 판정이 여기 함께 쌓이므로, 읽는 쪽이
        # 시전자(caster)로 걸러 자기가 찾는 것만 골라낸다.
        self.target_grants: list[dict] | None = target_grants
        # Full Burst [start, end) windows from the burst-cycle pass, so a
        # scheduled_nukes schedule can anchor on FB entry (e.g. Rapi: Red
        # Hood's projectile explosions). Filled by raid_simulator right
        # before the weapon pass; empty for contexts without a burst cycle.
        self.full_burst_windows: list[tuple[float, float]] = []
        # 지금 열려 있는 풀 버스트 창이 닫히는 시각. 원문이 "continuously"인 버프
        # (도로시의 Radiant Wings)는 초 수가 아니라 창의 끝까지 가므로, 그 길이를
        # 정한 Burst 3이 누구였는지에 따라 달라진다. full_burst_enter에서 세워지고
        # 그 순간에만 읽힌다.
        self.current_full_burst_end: float | None = None
        # slug -> every time that unit fires, so a `scheduled_nukes` schedule can
        # derive damage from its owner's own shot timeline (e.g. Raven's Shock
        # Wave, a sustained DoT started by each Full Charge). Filled in by
        # raid_simulator's weapon pass; empty for contexts without weapon stats.
        self.shot_times: dict[str, list[float]] = {}
        # slug -> how many rounds each of those shots ACCOUNTS for toward a
        # squad "total ammo expended by allies" counter (Little Mermaid's
        # Bubble Barrage). Parallel to shot_times, one entry per shot. A pouch
        # skill fires one bullet but spends hundreds of rounds, so the two
        # lists are not interchangeable.
        self.shot_ammo_rounds: dict[str, list[float]] = {}
        # flag -> the earliest time it was set (a "continuous, cannot be removed"
        # status is pinned from its first application). Callers that only care
        # whether a flag is set omit the time (defaults to 0.0).
        self._status: dict[str, dict[str, float]] = {m.slug: {} for m in members}
        self.burst_used_this_cycle: set[str] = set()
        self._activations: dict[tuple[str, str], int] = {}
        # The slug of the unit whose burst tier most recently fired, so an
        # ally_burst_activate rule can react to a SPECIFIC other unit bursting
        # (e.g. Prika's Encore keys off Mint). Set by raid_simulator.
        self.last_burst_slug: str | None = None
        # Each unit's burst-tier fire times, so a post-pass (e.g. Mint's per-shot
        # Here I Go!) can reconstruct a per-cycle-alternating status at any time.
        self.burst_times: dict[str, list[float]] = {m.slug: [] for m in members}
        # (slug, resource-name) -> list of (time, amount) fill events, so a
        # quantity-based resource (battery/ammo pouch/N-stack counter) is DEFINED
        # by its deterministic fill schedule and its count is COMPUTED as a
        # function of time (see resource_count) - never a mutable running total,
        # which would break across the burst-cycle vs shot-loop phase ordering.
        self.resource_fills: dict[tuple[str, str], list[tuple[float, float]]] = {}
        # (slug, resource-name) -> list of (time, pre_value, post_value) resets,
        # for a resource whose value is REPLACED rather than incremented - set
        # to a fixed number (Soda's Golden Chip starting at its 50 cap) or spent
        # down from what it held (her burst spending 17 of it, floored at 1).
        # Fills before a reset no longer
        # count toward the total; resource_count uses the latest reset at or
        # before the query time as its baseline instead of 0.
        self.resource_resets: dict[tuple[str, str], list[tuple[float, float, float]]] = {}
        # (slug, resource-name) -> (lifetime, lifetime_refreshes), registered
        # from each ResourceSpec at simulation setup. It is the ONE place a
        # resource's clock lives, so every reader of the count agrees about
        # when the stack expires - the buffs, and the gates that decide a nuke
        # or a damage typing. See register_resource / resource_count.
        self.resource_semantics: dict[tuple[str, str], tuple[float | None, bool]] = {}
        # 사이클별 Full Burst 확장 단계 [(start, end, {슬러그: 단계})]. 초가 아니라
        # 단계를 싣는 것은 소비자(소다의 per-shot 넉)가 "II단계인가"를 묻지
        # "5.0초인가"를 묻지 않기 때문 - 초에서 단계를 역추론하면 값이 우연히
        # 겹치는 날 조용히 틀린다. 슬러그별인 것은 초가 합산되는 것과 달리 단계는
        # 유닛마다 다르기 때문. raid_simulator가 창을 만들 때 채운다.
        self.full_burst_extension_stages: list[tuple[float, float, dict[str, int]]] = []

    def full_burst_extension_stage(self, time: float, slug: str) -> int:
        """`time`이 속한 Full Burst 창에서 `slug`가 도달한 확장 단계 (0 = 없음).
        창은 [start, end) 반열림이라 창 끝의 샷은 어느 창에도 안 든다."""
        for start, end, stages in self.full_burst_extension_stages:
            if start <= time < end:
                return stages.get(slug, 0)
        return 0

    def record_burst_time(self, slug: str, time: float) -> None:
        self.burst_times[slug].append(time)

    def register_resource(self, slug: str, spec) -> None:
        """Record how long `spec`'s stack lives, so every later count query
        answers with the resource's own clock rather than whatever the call
        site happened to know. Called once per ResourceSpec at setup."""
        self.resource_semantics[(slug, spec.name)] = (spec.lifetime, spec.lifetime_refreshes)

    def fill_resource(self, slug: str, name: str, amount: float, time: float) -> None:
        """Record that `slug`'s resource `name` gained `amount` at `time`."""
        self.resource_fills.setdefault((slug, name), []).append((time, amount))

    def reset_resource(self, slug: str, name: str, time: float, pre_value: float, post_value: float) -> None:
        """Record that `slug`'s resource `name` was SET to `post_value` at
        `time` (it held `pre_value` immediately before) - e.g. a burst that
        consumes the resource down to a fixed remainder. `pre_value` is exposed
        via `resource_count_before_reset` for a rule that gates on how much the
        resource held right before it was spent."""
        self.resource_resets.setdefault((slug, name), []).append((time, pre_value, post_value))

    def resource_count(
        self, slug: str, name: str, time: float, cap: float, lifetime: float | None = None,
        lifetime_refreshes: bool = False,
    ) -> float:
        """`slug`'s resource `name` at `time`, clamped to `cap`. A permanent
        resource (lifetime=None) sums every fill at or before `time`; a timed one
        (lifetime seconds) sums only fills still active - a fill at tf is active
        for [tf, tf+lifetime), i.e. those in (time-lifetime, time]. The latest
        reset at or before `time` (if any) replaces the running baseline with
        its post-value; fills before that reset no longer count.

        `lifetime_refreshes` picks a THIRD semantic: each fill restarts the
        clock for the WHOLE stack, so the count keeps climbing while consecutive
        fills stay within `lifetime` of each other, and the whole stack expires
        together `lifetime` after the LAST one. Maiden: Ice Rose's Meditation
        works this way - "Max HP +6.34% for 15 sec, stacks up to 10" reaches its
        cap because every proc renews the 15 sec, not because ten of them land
        inside one fixed window (Fienn, range test 2026-08-17). Under the plain
        timed rule the count instead settles at "fills per lifetime", which for
        her is about two - the reason her cap was once written off as unable to
        bind.

        A resource REGISTERED on this context (see register_resource) answers
        with its own clock and ignores both arguments, so every call site -
        the buff pass, a nuke's `resource_gate`, a segment's damage typing, a
        deferred gated buff - reads one semantic. The arguments remain for a
        context with no registration, which is how the unit tests drive this
        directly.
        """
        registered = self.resource_semantics.get((slug, name))
        if registered is not None:
            lifetime, lifetime_refreshes = registered
        baseline = 0.0
        baseline_time = float("-inf")
        for reset_time, _pre_value, post_value in self.resource_resets.get((slug, name), []):
            if reset_time <= time and reset_time > baseline_time:
                baseline_time = reset_time
                baseline = post_value
        fills = [
            (fill_time, amount)
            for fill_time, amount in self.resource_fills.get((slug, name), [])
            if fill_time <= time and fill_time > baseline_time
        ]
        if lifetime is not None and lifetime_refreshes:
            chain = 0.0
            last_fill = None
            for fill_time, amount in sorted(fills):
                if last_fill is not None and fill_time - last_fill > lifetime:
                    chain = 0.0  # the gap broke the chain; this fill starts anew
                chain += amount
                last_fill = fill_time
            if last_fill is None or time > last_fill + lifetime:
                return min(cap, baseline)
            return min(cap, baseline + chain)
        total = baseline
        for fill_time, amount in fills:
            if lifetime is not None and fill_time <= time - lifetime:
                continue
            total += amount
        return min(cap, total)

    def resource_count_before_reset(self, slug: str, name: str, time: float) -> float | None:
        """The value `slug`'s resource `name` held immediately BEFORE a reset
        recorded at EXACTLY `time` (e.g. gating a burst's bonus effects on how
        much the resource held right before it was consumed) - None if no
        reset was recorded at that exact time."""
        for reset_time, pre_value, _post_value in self.resource_resets.get((slug, name), []):
            if reset_time == time:
                return pre_value
        return None

    def record_activation(self, slug: str, trigger: str) -> None:
        self._activations[(slug, trigger)] = self._activations.get((slug, trigger), 0) + 1

    def activation_count(self, slug: str, trigger: str) -> int:
        """How many times `trigger` has fired for `slug` so far (1-based inside
        an action, since fire_trigger records before running it). For a per-cycle
        trigger this is the burst-cycle number - used to escalate ramping buffs."""
        return self._activations.get((slug, trigger), 0)

    def has_status(self, slug: str, flag: str) -> bool:
        return flag in self._status[slug]

    def set_status(self, slug: str, flag: str, time: float = 0.0) -> None:
        # Keeps the EARLIEST time the flag was set (re-applications don't move it
        # forward), so status_since gives when a continuous status began.
        self._status[slug].setdefault(flag, time)

    def clear_status(self, slug: str, flag: str) -> None:
        self._status[slug].pop(flag, None)

    def status_since(self, slug: str, flag: str) -> float | None:
        """The time `flag` was first set on `slug`, or None if not set."""
        return self._status[slug].get(flag)

    def members_with_burst_tier(self, tier: int, exclude_slug: str | None = None):
        return [
            m for m in self.members if m.burst_tier == tier and m.slug != exclude_slug
        ]

    def live_max_hp(self, base_max_hp: float, target: dict, time: float,
                    registry) -> float:
        """캐릭터정보 Max HP + `time`에 활성인 `flat_max_hp` 전부.

        「전부」에 **이 시뮬의 나중 패스가 쓸 것**도 포함된다는 게 이 메서드의
        존재 이유다. 환산("ATK ▲ 캐스터 Max HP의 X%")은 버스트 사이클 안에서
        도는데 `flat_max_hp`를 쓰는 곳 둘 - 샷 루프의 per-shot 룰(Rouge의 Card
        Throw)과 자원 해석(Maiden의 Meditation) - 은 그보다 뒤에 돈다. 그래서
        환산이 라이브 레지스트리만 읽으면 그 둘은 통째로 안 보인다(2026-08-17
        측정: 둘 다 100배로 키워도 덱 딜이 0.0000% 움직였다).

        `raid_simulator`가 앞 패스에서 모은 그것들을 레지스트리 하나에 담아
        `late_flat_max_hp`로 넘겨 준다. 읽기 전용 그림자이고 라이브 레지스트리와
        겹치지 않으므로 이중 계상은 없다 - 담기는 건 버스트 사이클이 끝난 뒤에
        붙은 것뿐이다. 시간축을 그대로 가진 Effect들이라 5초짜리 Max HP는 5초
        동안만 보인다.

        스냅샷 의미론은 그대로다: 값은 `time`에 고정되고, 이후 도착할 Max HP는
        이미 걸린 flat_atk를 소급해 키우지 않는다."""
        self.max_hp_conversion_used = True
        total = registry.total_for("flat_max_hp", target, time)
        if self._late_flat_max_hp is not None:
            total += self._late_flat_max_hp.total_for("flat_max_hp", target, time)
        return base_max_hp + total

    def top_atk_slugs(self, n: int, caster_slug: str, registry, time: float,
                      member_filter=None, include_caster: bool = False,
                      grant_stats: tuple[str, ...] | None = None) -> list[str]:
        """The `n` allies with the highest FINAL ATK at `time`. Final ATK is base
        ATK grown by live atk_percent buffs plus flat_atk, so a buff applied
        earlier this cycle (e.g. Miranda's own burst before her Full-Burst-enter
        skill) is reflected in the ranking. Ties break by deck order (stable
        sort).

        **Whether the caster competes is the bullet's wording, not a default to
        assume** (Fienn, 2026-08-08). Two shapes:

        - `include_caster=False` (default): the caster is excluded, and only
          fills a remaining slot when there are not enough other allies. This is
          what Miranda's text spells out ("except caster; including the caster
          if there are not enough allies") and Mana's and Soda's ("except the
          skill user").
        - `include_caster=True`: the caster is in the pool from the start,
          ranked against everyone else. This is the reading for a bullet that
          says only "N ally unit(s) with the highest ATK" with no exclusion
          clause - Maxwell's Straight Shot (ruled 2026-07-19), Leona's pellet
          bullet and Naga's Support of Friendship. The caster still has to meet
          the bullet's own conditions, so `member_filter` applies to her too.

        `member_filter(member) -> bool` narrows the CANDIDATES before ranking,
        for a bullet that is a weapon/element class AND a top-N at once - Leona's
        "the 2 ally unit(s) with shotguns who have the highest final ATK", which
        neither `member_subset_buff_rule` (no ranking) nor a bare top-N (no
        filter) expresses alone. It applies to the caster's fill-in too: a caster
        outside the class must not receive a buff aimed at that class, so a deck
        with no matching member yields an empty list rather than her.

        `grant_stats`는 호출자가 지금 주려는 스탯 이름들이다. 넘기면 이 판정이
        `target_grants`에 기록된다 - 대상 집합만으로는 한 시전자의 서로 다른
        불릿을 구분할 수 없어서(둘 다 같은 랭킹을 쓴다), 무슨 불릿인지는 호출자가
        선언해야만 알 수 있다."""
        by_slug = {m.slug: m for m in self.members}

        def final_atk(slug: str) -> float:
            target = {"slug": slug, "element": by_slug[slug].element}
            base = self.base_atk.get(slug, 0.0)
            return base * (1 + registry.total_for("atk_percent", target, time)) + registry.total_for(
                "flat_atk", target, time
            )

        eligible = [m for m in self.members if member_filter is None or member_filter(m)]
        if include_caster:
            candidates = [m.slug for m in eligible]
        else:
            candidates = [m.slug for m in eligible if m.slug != caster_slug]
            if len(candidates) < n and any(m.slug == caster_slug for m in eligible):
                candidates = candidates + [caster_slug]
        ranked = sorted(candidates, key=final_atk, reverse=True)
        targets = ranked[:n]
        if grant_stats is not None and self.target_grants is not None:
            self.target_grants.append({
                "caster": caster_slug, "time": time,
                "stats": list(grant_stats), "targets": list(targets),
            })
        return targets

    def neighbor_slugs(self, caster_slug: str, registry, time: float) -> list[str]:
        """The 2 allies seated beside `caster_slug` - the other half of a bullet
        that reads "Affects self and 2 allies on both sides".

        A back-row seat (position 2 or 4) always has exactly 2 neighbors, and
        they can be ANY 2 of the other four: seat 2 borders 1 and 3, seat 4
        borders 3 and 5. So this is a free choice the player makes, not a
        property of the deck - which is why an explicit `adjacency` wins when
        one was supplied.

        Without one, the fallback is the 2 allies with the highest ATK. It is a
        POLICY, not a guess at the optimum: the search scores ~1200 decks per
        request and cannot afford to try every arrangement, so it needs one
        answer that is deterministic, cheap and close. Whoever wants the true
        optimum pays for it explicitly
        (deck_search.evaluate_deck_best_seating).

        The policy answers per caster, which is exact for one seated unit - the
        seating it names is a real one the player can field. With TWO in a deck
        (Rouge and Flora's Favorite Item can share one) they answer
        independently, and five seats in a line may not grant both their pick:
        then the RANKING scores an arrangement no formation produces. That is
        tolerable only because ranking is all it does - every reported number
        comes from evaluate_deck_best_seating, which enumerates real
        arrangements. Measured on a deck holding both, the policy sat 4.77%
        BELOW the true optimum (it hands both casters the same two allies
        instead of spreading them), so the error is real but small next to the
        squad-wide scope this replaced."""
        seated = self.adjacency.get(caster_slug)
        if seated is not None:
            return list(seated)
        return self.top_atk_slugs(2, caster_slug, registry, time)

    def longest_charge_time_slugs(self, n: int) -> list[str]:
        """The `n` members with the longest BASIC charge time - Mana's Metal
        sigma targets "1 ally unit(s) with the longest basic Charge Time".
        Static, since "basic" means the weapon's own value rather than a live
        one. Ties break by deck order (stable sort)."""
        ranked = sorted(
            (m.slug for m in self.members),
            key=lambda slug: self.base_charge_time.get(slug, 0.0),
            reverse=True,
        )
        return ranked[:n]

    def lowest_atk_slugs(
        self, n: int, registry, time: float, burst_tier: int | None = None
    ) -> list[str]:
        """The `n` members with the LOWEST final ATK at `time`, optionally
        restricted to one burst tier - Liberalio's Calm Depths targets "the 1
        Burst 3 ally unit(s) with the lowest final ATK".

        Unlike `top_atk_slugs` this does NOT exclude the caster. Liberalio is
        herself a Burst 3, and Korean guides describe exactly that comparison
        ("Liberalio's ATK must be higher than Scarlet's" for Scarlet to get the
        buff), so she is a candidate for her own buff. When she does win it the
        effect is simply wasted, because Strange Currents makes her immune to
        charge-speed effects - which the engine reproduces rather than
        special-cases."""
        by_slug = {m.slug: m for m in self.members}

        def final_atk(slug: str) -> float:
            target = {"slug": slug, "element": by_slug[slug].element}
            base = self.base_atk.get(slug, 0.0)
            return base * (1 + registry.total_for("atk_percent", target, time)) + registry.total_for(
                "flat_atk", target, time
            )

        candidates = [
            m.slug for m in self.members
            if burst_tier is None or m.burst_tier == burst_tier
        ]
        return sorted(candidates, key=final_atk)[:n]


def no_other_burst_tier_allies(tier: int) -> Callable[[SquadContext, str], bool]:
    def check(context: SquadContext, caster_slug: str) -> bool:
        return len(context.members_with_burst_tier(tier, exclude_slug=caster_slug)) == 0

    return check


def has_status(flag: str) -> Callable[[SquadContext, str], bool]:
    def check(context: SquadContext, caster_slug: str) -> bool:
        return context.has_status(caster_slug, flag)

    return check


def own_burst_fired_this_cycle() -> Callable[[SquadContext, str], bool]:
    """Condition: this Nikke's own burst tier already fired earlier in the
    current cycle (e.g. Arcana's "if self is in Wheel of Fortune status" -
    a self-status only her own burst grants). Reads
    SquadContext.burst_used_this_cycle, which is populated before
    own_burst_activate fires and cleared only after full_burst_end rules run."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return caster_slug in context.burst_used_this_cycle

    return check


def own_burst_status_active(seconds: float) -> Callable[[SquadContext, str, float], bool]:
    """자기 버스트가 자신에게 건 상태가 그 시각에 아직 살아 있는가.

    부여 시점은 그 버스트를 쓴 시각이므로 별도 상태 기록이 필요 없다
    (`SquadContext.burst_times`). 한 번도 버스트하지 않았으면 거짓.

    `own_burst_fired_this_cycle()`가 답할 수 없는 질문이다: 그쪽은 시계가 없어서
    부여 이후 `seconds`가 지났는지 구별하지 못한다. 풀 버스트 창 하나를 사이에 둔
    `full_burst_end` 게이트에서는 그 차이가 전부다 - 아르카나의 운명의 수레바퀴는
    10초짜리인데 그녀는 버스트 스테이지 2에서 시전하므로, 표준 10초 창이 끝날 때는
    이미 만료돼 있다.

    **버스트 사이클 트리거에서만 의미가 있다** — `battle_start` ·
    `own_burst_activate` · `ally_burst_activate` · `full_burst_enter` ·
    `full_burst_end`. `burst_times[caster][-1]`이 「가장 최근 버스트」인 것은
    `simulate_burst_cycle` 워크가 도는 동안뿐이고, `raid_simulator`의 나머지 두
    호출 지점에서는 다른 것을 가리킨다:

    - `periodic_rules` 패스는 `simulate_burst_cycle`보다 **먼저** 돌아
      `burst_times`가 아직 비어 있다 → 이 술어는 무조건 거짓이다.
    - per-shot 패스는 **나중에** 돌아 `burst_times`가 전투 전체를 담고 있다 →
      `[-1]`은 그 전투의 **마지막** 버스트이고, 그 버스트가 일어나기 한참 전인
      사격 시각에서도 참을 돌려준다.

    `SkillRule.time_condition` 필드 자체는 세 지점이 모두 존중한다
    (`test_raid_simulator.py`의
    `test_time_condition_is_honoured_by_the_periodic_and_per_shot_passes`).
    제약은 이 술어의 것이지 필드의 것이 아니다.
    """

    def check(context: SquadContext, caster_slug: str, time: float) -> bool:
        times = context.burst_times.get(caster_slug)
        if not times:
            return False
        return times[-1] + seconds > time

    return check


def ally_bursted(slug: str) -> Callable[[SquadContext, str], bool]:
    """Condition for an `ally_burst_activate` rule: the unit whose burst just
    fired is `slug` (e.g. Prika's Encore fires when Mint bursts). Reads
    SquadContext.last_burst_slug, set by raid_simulator before the trigger fires."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return context.last_burst_slug == slug

    return check


def burst_stage_entered(tier: int) -> Callable[[SquadContext, str], bool]:
    """Condition for an `ally_burst_activate` rule: the burst that just fired
    belongs to `tier`, i.e. the squad has entered Burst Stage `tier`.

    "Activates when entering Burst Stage N" is about the STAGE, not about the
    caster - so it must still fire in a cycle where a DIFFERENT ally of that
    tier took the slot (Flora's Favorite Item Max-HP bullet). Using
    `own_burst_activate` instead would silently drop those cycles. Because
    `ally_burst_activate` fires across every unit's rules, the caster is covered
    in the cycles it bursts itself."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        burster = next(
            (m for m in context.members if m.slug == context.last_burst_slug), None
        )
        return burster is not None and burster.burst_tier == tier

    return check


def boss_is_element(element: str) -> Callable[[SquadContext, str], bool]:
    """Condition: the boss is `element` Code (e.g. Brid's Wind-Code Damage Taken
    debuff, Helm: Aquamarine's Electric-Code bullets). Reads
    SquadContext.boss_element, set by raid_simulator - False when it's unset
    (element-agnostic sim)."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return context.boss_element == element

    return check


def boss_part_destructible() -> Callable[[SquadContext, str], bool]:
    """True when the boss has a part-destruction gimmick (BossProfile flag,
    threaded via raid_simulator). Ark Ranger Black uses it to select her
    permanent-transformation ceiling vs her burst-driven battery floor."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return context.part_destructible

    return check


def boss_part_indestructible() -> Callable[[SquadContext, str], bool]:
    """The other side of the same flag - for an effect that a part-destruction
    gimmick CANCELS. Diesel: Winter Sweets' Noise Pollution is the case: the
    squad's immunity to it is restocked by destroying parts, so it only bites
    on a boss with none."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return not context.part_destructible

    return check


def boss_part_destruction_untimed() -> Callable[[SquadContext, str], bool]:
    """파괴 가능한 파츠는 있는데 파괴 **시각**은 선언되지 않은 인카운터.

    파괴에 반응하는 버프는 시각을 모르면 「전투 내내 걸려 있다」는 ceiling으로
    근사할 수밖에 없다. 그 근사를 이 조건에 매달아 두면, 시각이 선언된 순간
    자동으로 꺼지고 `part_destroyed` 트리거가 그 자리를 대신한다 - 둘 다 켜지면
    같은 버프가 두 번 걸린다."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return context.part_destructible and not context.part_destruction_times

    return check


def boss_core_hittable() -> Callable[[SquadContext, str], bool]:
    """True when the boss has an exploitable core (sim-level core_hittable
    flag) - for effects whose target is "enemies with activated cores"."""

    def condition(context: SquadContext, caster_slug: str) -> bool:
        return context.core_hittable

    return condition


def all_conditions(
    *conditions: Callable[[SquadContext, str], bool]
) -> Callable[[SquadContext, str], bool]:
    """Condition that holds only when every given condition holds (logical AND),
    e.g. Prika's Encore needs both ally_bursted("mint") AND her own Performance
    status."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return all(condition(context, caster_slug) for condition in conditions)

    return check


def deck_contains(slug: str) -> Callable[[SquadContext, str], bool]:
    """Condition: another named Nikke is in the deck (e.g. Mast keys its Drunken
    stack retention off Anchor's presence)."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return any(m.slug == slug for m in context.members)

    return check


def deck_contains_any(slugs) -> Callable[[SquadContext, str], bool]:
    """Condition: the deck holds at least one of `slugs`, EXCLUDING the caster.
    For "does someone else in this squad do X" questions where the engine has
    no event for X itself - Crown's Royal Attire keys off any ally healing,
    and the engine models no heal events, so presence is what can be asked."""
    wanted = frozenset(slugs)

    def check(context: SquadContext, caster_slug: str) -> bool:
        return any(m.slug in wanted and m.slug != caster_slug for m in context.members)

    return check


def not_condition(
    condition: Callable[[SquadContext, str], bool]
) -> Callable[[SquadContext, str], bool]:
    def check(context: SquadContext, caster_slug: str) -> bool:
        return not condition(context, caster_slug)

    return check


def _always_true(context: SquadContext, caster_slug: str) -> bool:
    return True


def _always_true_at(context: SquadContext, caster_slug: str, time: float) -> bool:
    return True


@dataclass
class SkillRule:
    trigger: str
    action: Callable[[SquadContext, str, float, EffectRegistry], None]
    condition: Callable[[SquadContext, str], bool] = field(default=_always_true)
    # 상태의 남은 시간처럼, 트리거가 발동한 시각을 봐야만 답할 수 있는 게이트.
    # 시각은 언제나 호출자가 넘긴다 - 컨텍스트에 현재 시각을 찍어두고 나중에 읽는
    # 방식은 호출 지점 하나가 찍기를 빠뜨리면 낡은 값을 에러 없이 반환한다.
    time_condition: Callable[[SquadContext, str, float], bool] = field(
        default=_always_true_at
    )


def fire_trigger(trigger, rules_by_slug, context, registry, time):
    for slug, rules in rules_by_slug.items():
        matching = [rule for rule in rules if rule.trigger == trigger]
        if matching:
            context.record_activation(slug, trigger)
        for rule in matching:
            if rule.condition(context, slug) and rule.time_condition(context, slug, time):
                rule.action(context, slug, time, registry)
