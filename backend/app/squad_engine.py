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


class SquadContext:
    def __init__(self, members: list[SquadMember], base_atk: dict[str, float] | None = None):
        self.members = members
        # each member's base (summary) ATK, so a rule targeting "the N allies with
        # the highest final ATK" can rank them live (see top_atk_slugs). Injected by
        # raid_simulator; empty for contexts that don't need ranking.
        self.base_atk: dict[str, float] = base_atk or {}
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

    def record_burst_time(self, slug: str, time: float) -> None:
        self.burst_times[slug].append(time)

    def fill_resource(self, slug: str, name: str, amount: float, time: float) -> None:
        """Record that `slug`'s resource `name` gained `amount` at `time`."""
        self.resource_fills.setdefault((slug, name), []).append((time, amount))

    def resource_count(
        self, slug: str, name: str, time: float, cap: float, lifetime: float | None = None
    ) -> float:
        """`slug`'s resource `name` at `time`, clamped to `cap`. A permanent
        resource (lifetime=None) sums every fill at or before `time`; a timed one
        (lifetime seconds) sums only fills still active - a fill at tf is active
        for [tf, tf+lifetime), i.e. those in (time-lifetime, time]."""
        total = 0.0
        for fill_time, amount in self.resource_fills.get((slug, name), []):
            if fill_time > time:
                continue
            if lifetime is not None and fill_time <= time - lifetime:
                continue
            total += amount
        return min(cap, total)

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

    def top_atk_slugs(self, n: int, caster_slug: str, registry, time: float) -> list[str]:
        """The `n` allies with the highest FINAL ATK at `time`, excluding the
        caster - but including the caster to fill remaining slots if there aren't
        enough other allies ("except caster; including the caster if there are not
        enough allies"). Final ATK is base ATK grown by live atk_percent buffs plus
        flat_atk, so a buff applied earlier this cycle (e.g. Miranda's own burst
        before her Full-Burst-enter skill) is reflected in the ranking. Ties break
        by deck order (stable sort)."""
        by_slug = {m.slug: m for m in self.members}

        def final_atk(slug: str) -> float:
            target = {"slug": slug, "element": by_slug[slug].element}
            base = self.base_atk.get(slug, 0.0)
            return base * (1 + registry.total_for("atk_percent", target, time)) + registry.total_for(
                "flat_atk", target, time
            )

        candidates = [m.slug for m in self.members if m.slug != caster_slug]
        if len(candidates) < n:
            candidates = candidates + [caster_slug]
        ranked = sorted(candidates, key=final_atk, reverse=True)
        return ranked[:n]


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


def ally_bursted(slug: str) -> Callable[[SquadContext, str], bool]:
    """Condition for an `ally_burst_activate` rule: the unit whose burst just
    fired is `slug` (e.g. Prika's Encore fires when Mint bursts). Reads
    SquadContext.last_burst_slug, set by raid_simulator before the trigger fires."""

    def check(context: SquadContext, caster_slug: str) -> bool:
        return context.last_burst_slug == slug

    return check


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


def not_condition(
    condition: Callable[[SquadContext, str], bool]
) -> Callable[[SquadContext, str], bool]:
    def check(context: SquadContext, caster_slug: str) -> bool:
        return not condition(context, caster_slug)

    return check


def _always_true(context: SquadContext, caster_slug: str) -> bool:
    return True


@dataclass
class SkillRule:
    trigger: str
    action: Callable[[SquadContext, str, float, EffectRegistry], None]
    condition: Callable[[SquadContext, str], bool] = field(default=_always_true)


def fire_trigger(trigger, rules_by_slug, context, registry, time):
    for slug, rules in rules_by_slug.items():
        matching = [rule for rule in rules if rule.trigger == trigger]
        if matching:
            context.record_activation(slug, trigger)
        for rule in matching:
            if rule.condition(context, slug):
                rule.action(context, slug, time, registry)
