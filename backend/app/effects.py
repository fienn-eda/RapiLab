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


@dataclass
class Pulse:
    """A one-shot instantaneous effect (e.g. an instant cooldown reduction),
    as opposed to Effect's continuous, queryable-at-any-time buffs."""

    stat: str
    value: float
    scope: str
    source_slug: str
    # Opt-in per instance: only an "instant_damage_percent" pulse whose skill
    # text says "as additional damage" sets this, so raid_simulator can pass it
    # through to record()'s full_burst_bonus_eligible - see damage_formula's
    # full_burst_bonus term and docs/insights.md.
    full_burst_bonus_eligible: bool = False


@dataclass
class RoundGrant:
    """A pending "next-N-shots" (bullet-count / "for N round(s)") buff: granted
    on a trigger, but it expires when each affected ally has fired `shots` normal
    attacks, NOT after a fixed time. Because that boundary depends on shot timing,
    it's recorded here and converted into a concrete timed Effect (covering exactly
    those shots) once the shot timeline is known - see raid_simulator's shot loop.
    `scope` selects the affected units the same way Effect.scope does."""

    stat: str
    value: float
    scope: str
    source_slug: str
    shots: int
    granted_at: float


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
    # Optional list of {"trigger": "battle_start"|"own_burst", "value": X}: the
    # resource is SET to X (not incremented) once at battle start, or at EACH
    # of the owner's own burst-tier fires - e.g. Soda's Golden Chip resetting
    # to 17 when her burst consumes it. See raid_simulator's resolution pass.
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

    def add(self, effect: Effect, applied_at: float) -> None:
        self._entries.append((effect, applied_at))
        self._version += 1

    def add_round_grant(self, grant: RoundGrant) -> None:
        self._round_grants.append(grant)

    def round_grants(self) -> list[RoundGrant]:
        return self._round_grants

    def add_refreshing(self, effect: Effect, applied_at: float) -> None:
        """Add a buff that REFRESHES rather than stacks. Any still-active effect
        with the same (stat, source_slug, scope) is truncated to end at
        `applied_at`, so overlapping re-applications from ONE source collapse to a
        single continuous window at the buff's value (not the sum of overlaps).
        Effects from DIFFERENT sources are untouched, so cross-unit buffs still
        add. For a buff re-applied every shot (e.g. "ATK +X% for 3 sec on every
        Full Charge"), which the game refreshes rather than stacks. Truncation is
        in place, so replay-style queries for earlier times also see one instance."""
        for existing, existing_applied_at in self._entries:
            if (
                existing.stat == effect.stat
                and existing.source_slug == effect.source_slug
                and existing.scope == effect.scope
                and self._is_active(existing, existing_applied_at, applied_at)
            ):
                existing.duration = applied_at - existing_applied_at
        self._entries.append((effect, applied_at))
        self._version += 1

    def add_pulse(self, pulse: Pulse) -> None:
        self._pulses.append(pulse)

    def truncate_open_ended(self, stat: str, source_slug: str, now: float) -> None:
        """Close out a still-open (duration=None) effect from this exact
        (stat, source_slug), so it stops counting as active from `now` onward
        - for a continuous buff a Nikke's own later trigger explicitly ends
        (e.g. Grave's Heat Emission ends when she reuses her burst, rather than
        expiring on a fixed timer). Mutates the stored Effect's duration in
        place, so any later `total_for` query - including ones for times
        before `now`, from raid_simulator's replay-style pass over normal-
        attack shots - correctly respects the closed [applied_at, now) window
        regardless of when this is called relative to the sim's own timeline.
        No-op if there's no matching open effect. If more than one open effect
        shares the same (stat, source_slug), all of them are closed - that
        ambiguity hasn't come up yet."""
        for effect, applied_at in self._entries:
            if effect.stat == stat and effect.source_slug == source_slug and effect.duration is None:
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
        intervals = []
        for effect, applied_at in self._entries:
            if effect.stat != stat:
                continue
            if not _matches_target(effect, target):
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
