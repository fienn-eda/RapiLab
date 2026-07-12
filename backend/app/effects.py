"""Time-scoped combat effects (buffs/debuffs) applied during a raid simulation.

Effect.scope selects which squad members an effect applies to:
    "self"            - only the Nikke that produced the effect
    "squad"           - every Nikke in the deck
    "element:<Name>"  - only Nikkes whose element matches <Name>
    "slugs:<a,b,...>" - only the Nikkes named in the comma-separated slug list
                        (used for "N allies with the highest final ATK" buffs,
                        resolved to concrete slugs at application time)
"""
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


class EffectRegistry:
    def __init__(self):
        self._entries: list[tuple[Effect, float]] = []
        self._pulses: list[Pulse] = []
        self._round_grants: list[RoundGrant] = []

    def add(self, effect: Effect, applied_at: float) -> None:
        self._entries.append((effect, applied_at))

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

    def drain_pulses(self, stat: str) -> list[Pulse]:
        matching = [p for p in self._pulses if p.stat == stat]
        self._pulses = [p for p in self._pulses if p.stat != stat]
        return matching

    def _is_active(self, effect: Effect, applied_at: float, now: float) -> bool:
        if effect.duration is None:
            return now >= applied_at
        return applied_at <= now < applied_at + effect.duration

    def total_for(self, stat: str, target: dict, now: float) -> float:
        total = 0.0
        for effect, applied_at in self._entries:
            if effect.stat != stat:
                continue
            if not self._is_active(effect, applied_at, now):
                continue
            if effect.scope == "self":
                if effect.source_slug == target["slug"]:
                    total += effect.value
            elif _matches_scope(effect.scope, target):
                total += effect.value
        return total
