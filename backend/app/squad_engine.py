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
