"""Time-scoped combat effects (buffs/debuffs) applied during a raid simulation.

Effect.scope selects which squad members an effect applies to:
    "self"            - only the Nikke that produced the effect
    "squad"           - every Nikke in the deck
    "element:<Name>"  - only Nikkes whose element matches <Name>
    "slugs:<a,b,...>" - only the Nikkes named in the comma-separated slug list
                        (used for "N allies with the highest final ATK" buffs,
                        resolved to concrete slugs at application time)
"""
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Effect:
    stat: str
    value: float
    scope: str
    duration: float | None  # seconds; None means it never expires
    source_slug: str
    # Which skill bullet this came from, for add_refreshing. A unit can grant
    # the same stat from several bullets (Liberalio's permanent Raging Current
    # and her per-shot on-core buff are both self attack_damage_up), and only
    # re-applications of the SAME bullet may collapse into one another - see
    # add_refreshing, which requires it. None means the effect is never
    # refreshed: plainly-added effects keep it, which is what stops a
    # refreshing bullet from truncating a permanent one on the same stat.
    refresh_group: str | None = None


@dataclass
class Pulse:
    """A one-shot instantaneous effect (e.g. an instant cooldown reduction),
    as opposed to Effect's continuous, queryable-at-any-time buffs."""

    stat: str
    value: float
    scope: str
    source_slug: str
    # Damage typing for "instant_damage_percent" pulses whose text names a
    # type (e.g. "as Distributed Damage") - passed through to record() so the
    # type-gated Damage-Up buckets apply. Other pulse stats ignore it.
    damage_type: str = "attack"


@dataclass
class RoundGrant:
    """A pending "next-N-shots" (bullet-count / "for N round(s)") buff: granted
    on a trigger, but it expires when each affected ally has fired `shots` normal
    attacks, NOT after a fixed time. Because that boundary depends on shot timing,
    it's recorded here and converted into a concrete timed Effect (covering exactly
    those shots) once the shot timeline is known - see raid_simulator's shot loop.
    `scope` selects the affected units the same way Effect.scope does.
    `cap` (opt-in) is the skill's "stacks up to N time(s)" limit: no recipient
    ever holds more than `cap` concurrent grants sharing this grant's
    `cap_group`, which identifies the ONE skill bullet the grants came from
    (grants from other skills, even of the same caster and stat, cap
    separately). Enforced per recipient in raid_simulator's conversion pass,
    because how many grants pile up depends on the recipient's own fire rate."""

    stat: str
    value: float
    scope: str
    source_slug: str
    shots: int
    granted_at: float
    cap: int | None = None
    cap_group: str | None = None


@dataclass
class ResourceBuff:
    """One buff derived from a named resource's current stack count. `value_fn`
    maps the resource's count (already clamped to the spec's cap) to the buff's
    value - linear (per_stack * count) or tiered (per_level * level(count)). It's
    emitted as a step function over the resource's fill schedule (see
    raid_simulator's resolution pass). `lifetime` None = a permanent stack that
    accumulates (Guillotine's EXP); a number = a timed stack that expires that
    many seconds after each fill (Modernia's 10-sec stacks)."""

    stat: str
    scope: str
    value_fn: Callable[[float], float]
    lifetime: float | None = None


@dataclass
class ResourceSpec:
    """A quantity-based resource (battery / ammo pouch / N-stack counter) that
    the current status-flag primitive can't express. Filled deterministically
    (`fill`, e.g. ("per_shot_every", N) = +1 every Nth of the owner's shots),
    clamped to `cap`, driving one or more count-scaled `buffs`. Passed to
    simulate_raid keyed by owner slug; its buffs are emitted in a resolution pass
    once the owner's shot timeline is known."""

    name: str
    fill: tuple
    cap: float
    buffs: list[ResourceBuff] = field(default_factory=list)
    # Optional list of {"trigger": "battle_start"|"own_burst"|
    # "own_burst_delayed"|"full_burst_end", "value": X}: the resource is SET to
    # X (not incremented) once at battle start - e.g. Soda's Golden Chip
    # starting the fight at its 50 cap - at EACH of the owner's own burst-tier
    # fires, a fixed delay after those, or at each Full Burst's end. `value_fn`
    # replaces `value` for a spend that reads the count it consumes (Soda's
    # burst spending 17 of the chip, Elegg's ghosts spending 9 at the cap). See
    # raid_simulator's resolution pass.
    resets: list[dict] = field(default_factory=list)


def _matches_scope(scope: str, target: dict) -> bool:
    if scope == "self":
        return False  # handled separately via source_slug, see EffectRegistry.total_for
    if scope == "squad":
        return True
    if scope.startswith("element:"):
        return target["element"] == scope.split(":", 1)[1]
    if scope.startswith("slugs:"):
        return target["slug"] in scope.split(":", 1)[1].split(",")
    raise ValueError(f"unknown effect scope: {scope}")


def _matches_target(effect: Effect, target: dict) -> bool:
    """One matching semantics for both the per-stat segment tables and the
    merged epoch timeline: "self" matches via source_slug, everything else
    via _matches_scope."""
    if effect.scope == "self":
        return effect.source_slug == target["slug"]
    return _matches_scope(effect.scope, target)


class EffectRegistry:
    def __init__(self):
        self._entries: list[tuple[Effect, float]] = []
        self._pulses: list[Pulse] = []
        self._round_grants: list[RoundGrant] = []
        # total_for is served from per-(stat, slug, element) segment tables;
        # every mutation bumps _version so stale tables rebuild on next query.
        # Mutations happen ONLY through the methods below (audited 2026-07-17).
        self._version = 0
        self._segment_tables: dict[tuple, tuple[int, list, list]] = {}
        self._epoch_tables: dict[tuple, tuple[int, list]] = {}
        # (slug, stat) pairs where the unit ignores that stat from every source
        # but itself - see set_external_stat_immunity.
        self._external_immunities: set[tuple[str, str]] = set()

    def add(self, effect: Effect, applied_at: float) -> None:
        self._entries.append((effect, applied_at))
        self._version += 1

    def set_external_stat_immunity(self, slug: str, stat: str) -> None:
        """`slug` stops receiving `stat` from anyone but itself - Liberalio's
        "Gains immunity to Increase/Decrease Charge Speed effects".

        Self-sourced effects still land, which is what makes this the right
        shape: a unit's overload rolls and cube are registered with its OWN
        slug as source (see roster._passive_effects), so her gear keeps
        working while allies' buffs stop reaching her. That is exactly the
        distinction Fienn specified (2026-07-20)."""
        self._external_immunities.add((slug, stat))
        self._version += 1

    def add_round_grant(self, grant: RoundGrant) -> None:
        self._round_grants.append(grant)

    def round_grants(self) -> list[RoundGrant]:
        return self._round_grants

    def add_refreshing(self, effect: Effect, applied_at: float) -> None:
        """Add a buff that REFRESHES rather than stacks. Any still-active effect
        with the same (stat, source_slug, scope, refresh_group) is truncated to end at
        `applied_at`, so overlapping re-applications from ONE source collapse to a
        single continuous window at the buff's value (not the sum of overlaps).
        Effects from DIFFERENT sources are untouched, so cross-unit buffs still
        add - and so are effects from a different `refresh_group`, i.e. a
        different skill bullet of the SAME unit. Without that last key, a
        unit's permanent buff on a stat was silently truncated by its own
        smaller per-shot buff on the same stat (Liberalio's Raging Current,
        found 2026-07-21). For a buff re-applied every shot (e.g. "ATK +X% for 3 sec on every
        Full Charge"), which the game refreshes rather than stacks. Truncation is
        in place, so replay-style queries for earlier times also see one instance.

        The group is REQUIRED: naming the bullet is the caller's decision, and
        leaving it unset used to drop every hand-written refresher into one
        shared bucket - together with plainly-added effects, which a refresher
        must never touch (Grave's permanent Overheat I, deleted by her own
        windowed Overheat II). Use `truncate_open_ended` for the separate case
        of a unit's later trigger deliberately ending its own continuous buff."""
        if effect.refresh_group is None:
            raise ValueError(
                f"add_refreshing needs a refresh_group naming the skill bullet "
                f"({effect.source_slug}'s {effect.stat}); see EffectRegistry.add_refreshing"
            )
        for existing, existing_applied_at in self._entries:
            if (
                existing.stat == effect.stat
                and existing.source_slug == effect.source_slug
                and existing.scope == effect.scope
                and existing.refresh_group == effect.refresh_group
                and self._is_active(existing, existing_applied_at, applied_at)
            ):
                existing.duration = applied_at - existing_applied_at
        self._entries.append((effect, applied_at))
        self._version += 1

    def add_pulse(self, pulse: Pulse) -> None:
        self._pulses.append(pulse)

    def truncate_open_ended(self, stat: str, source_slug: str, now: float,
                            refresh_group: str | None = None) -> None:
        """Close out a still-open (duration=None) effect from this exact
        (stat, source_slug), so it stops counting as active from `now` onward
        - for a continuous buff a Nikke's own later trigger explicitly ends
        (e.g. Grave's Heat Emission ends when she reuses her burst, rather than
        expiring on a fixed timer). Mutates the stored Effect's duration in
        place, so any later `total_for` query - including ones for times
        before `now`, from raid_simulator's replay-style pass over normal-
        attack shots - correctly respects the closed [applied_at, now) window
        regardless of when this is called relative to the sim's own timeline.
        No-op if there's no matching open effect. Every open effect sharing the
        (stat, source_slug) is closed, which is what Grave and Arcana want.
        Pass `refresh_group` to close only the effects added under that bullet
        name: a unit can hold two continuous buffs on ONE stat where a later
        trigger ends just one of them (Queen (Makoto Nijima)'s Nuke Boost is
        permanent, her Nuke Amp stops at Full Burst end, and both are Elemental
        Advantage Attack Damage). It is the same key `add_refreshing` requires
        for the same reason - telling a unit's bullets apart on a shared stat."""
        for effect, applied_at in self._entries:
            if effect.stat != stat or effect.source_slug != source_slug:
                continue
            if effect.duration is not None:
                continue
            if refresh_group is not None and effect.refresh_group != refresh_group:
                continue
            effect.duration = now - applied_at
        self._version += 1

    def drain_pulses(self, stat: str) -> list[Pulse]:
        matching = [p for p in self._pulses if p.stat == stat]
        self._pulses = [p for p in self._pulses if p.stat != stat]
        return matching

    def _is_active(self, effect: Effect, applied_at: float, now: float) -> bool:
        if effect.duration is None:
            return now >= applied_at
        return applied_at <= now < applied_at + effect.duration

    def total_for(self, stat: str, target: dict, now: float) -> float:
        # .get for element: the old loop only read target["element"] when an
        # element:-scoped effect was actually present, so the cache key must
        # not introduce a new KeyError for element-less targets.
        key = (stat, target["slug"], target.get("element"))
        cached = self._segment_tables.get(key)
        if cached is None or cached[0] != self._version:
            cached = self._build_segment_table(stat, target)
            self._segment_tables[key] = cached
        _, boundaries, totals = cached
        return totals[bisect_right(boundaries, now)]

    def _build_segment_table(self, stat: str, target: dict):
        """Piecewise-constant totals for one (stat, target) query key: between
        consecutive interval boundaries the active set is constant, so each
        segment's total is precomputed and a query is one bisect. Each segment
        is summed over entries in insertion order - the exact additions the
        old linear scan performed for any time inside that segment - so
        results are bit-identical to it, not approximately equal."""
        immune = (target["slug"], stat) in self._external_immunities
        intervals = []
        for effect, applied_at in self._entries:
            if effect.stat != stat:
                continue
            if not _matches_target(effect, target):
                continue
            if immune and effect.source_slug != target["slug"]:
                continue
            end = None if effect.duration is None else applied_at + effect.duration
            intervals.append((applied_at, end, effect.value))
        boundary_set = set()
        for start, end, _ in intervals:
            boundary_set.add(start)
            if end is not None:
                boundary_set.add(end)
        boundaries = sorted(boundary_set)
        totals = [0.0]  # the earliest boundary is the earliest start, so
        for b in boundaries:  # queries before it see no active effect
            total = 0.0
            for start, end, value in intervals:
                if start <= b and (end is None or b < end):
                    total += value
            totals.append(total)
        return (self._version, boundaries, totals)

    @property
    def version(self) -> int:
        """Monotonic mutation counter - lets callers key their own memos on
        registry state (see raid_simulator's stat-bundle memo)."""
        return self._version

    def state_epoch(self, target: dict, now: float) -> int:
        """Index of the piecewise-constant state segment `now` falls in for
        this target: within one epoch NO effect matching the target starts or
        ends (under any stat), so every stat total is constant - callers may
        resolve whole stat bundles once per (target, epoch, version)."""
        key = (target["slug"], target.get("element"))
        cached = self._epoch_tables.get(key)
        if cached is None or cached[0] != self._version:
            boundary_set = set()
            for effect, applied_at in self._entries:
                if not _matches_target(effect, target):
                    continue
                boundary_set.add(applied_at)
                if effect.duration is not None:
                    boundary_set.add(applied_at + effect.duration)
            cached = (self._version, sorted(boundary_set))
            self._epoch_tables[key] = cached
        return bisect_right(cached[1], now)


def max_ammo_percent_total(registry, target: dict, now: float, base_max_ammo: int) -> float:
    """[최대 장탄 수] 버프 전체가 만드는 하나의 배율.

    게임은 이 스탯을 두 형태로 준다. 오버로드와 대부분의 스킬은 퍼센트지만
    일부 스킬은 무기와 무관한 고정 발수를 준다("최대 장탄 수 ▲ 2발"). 후자는
    받는 유닛의 기본 장탄에 대한 비율로 환산해 합류시킨다 -
    `round(base × (1 + pct + flat/base))` 는 `round(base × (1 + pct) + flat)`
    와 같은 값이라, 탄창 크기를 계산하는 쪽은 지금까지처럼 배율 하나만 알면
    된다. 퍼센트가 기본 장탄에만 걸리고 플랫이 그 위에 얹히는 순서는 Fienn의
    판단(2026-08-02)이다.
    """
    return (registry.total_for("max_ammo_percent", target, now)
            + registry.total_for("max_ammo_rounds", target, now) / base_max_ammo)
