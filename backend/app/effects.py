"""Time-scoped combat effects (buffs/debuffs) applied during a raid simulation.

Effect.scope selects which squad members an effect applies to:
    "self"            - only the Nikke that produced the effect
    "squad"           - every Nikke in the deck
    "element:<Name>"  - only Nikkes whose element matches <Name>
"""
from dataclasses import dataclass


@dataclass
class Effect:
    stat: str
    value: float
    scope: str
    duration: float | None  # seconds; None means it never expires
    source_slug: str


def _matches_scope(scope: str, target: dict) -> bool:
    if scope == "self":
        return False  # handled separately via source_slug, see EffectRegistry.total_for
    if scope == "squad":
        return True
    if scope.startswith("element:"):
        return target["element"] == scope.split(":", 1)[1]
    raise ValueError(f"unknown effect scope: {scope}")


class EffectRegistry:
    def __init__(self):
        self._entries: list[tuple[Effect, float]] = []

    def add(self, effect: Effect, applied_at: float) -> None:
        self._entries.append((effect, applied_at))

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
