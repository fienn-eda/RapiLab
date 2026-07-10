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
    def __init__(self, members: list[SquadMember]):
        self.members = members
        self._status: dict[str, set[str]] = {m.slug: set() for m in members}
        self.burst_used_this_cycle: set[str] = set()
        self._activations: dict[tuple[str, str], int] = {}
        # The slug of the unit whose burst tier most recently fired, so an
        # ally_burst_activate rule can react to a SPECIFIC other unit bursting
        # (e.g. Prika's Encore keys off Mint). Set by raid_simulator.
        self.last_burst_slug: str | None = None

    def record_activation(self, slug: str, trigger: str) -> None:
        self._activations[(slug, trigger)] = self._activations.get((slug, trigger), 0) + 1

    def activation_count(self, slug: str, trigger: str) -> int:
        """How many times `trigger` has fired for `slug` so far (1-based inside
        an action, since fire_trigger records before running it). For a per-cycle
        trigger this is the burst-cycle number - used to escalate ramping buffs."""
        return self._activations.get((slug, trigger), 0)

    def has_status(self, slug: str, flag: str) -> bool:
        return flag in self._status[slug]

    def set_status(self, slug: str, flag: str) -> None:
        self._status[slug].add(flag)

    def clear_status(self, slug: str, flag: str) -> None:
        self._status[slug].discard(flag)

    def members_with_burst_tier(self, tier: int, exclude_slug: str | None = None):
        return [
            m for m in self.members if m.burst_tier == tier and m.slug != exclude_slug
        ]


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
