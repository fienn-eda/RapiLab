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
        boss_element: str | None = None,
        part_destructible: bool = False,
        core_hittable: bool = False,
    ):
        self.members = members
        # each member's base (summary) ATK, so a rule targeting "the N allies with
        # the highest final ATK" can rank them live (see top_atk_slugs). Injected by
        # raid_simulator; empty for contexts that don't need ranking.
        self.base_atk: dict[str, float] = base_atk or {}
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
        # whether the boss's core is exploitable this sim (raid_simulator's
        # core_hittable flag), so a rule gated on core existence (e.g.
        # Cinderella: Crystal Wave's MG-mode core-strike nuke) can read it.
        self.core_hittable: bool = core_hittable
        # Full Burst [start, end) windows from the burst-cycle pass, so a
        # scheduled_nukes schedule can anchor on FB entry (e.g. Rapi: Red
        # Hood's projectile explosions). Filled by raid_simulator right
        # before the weapon pass; empty for contexts without a burst cycle.
        self.full_burst_windows: list[tuple[float, float]] = []
        # slug -> every time that unit fires, so a `scheduled_nukes` schedule can
        # derive damage from its owner's own shot timeline (e.g. Raven's Shock
        # Wave, a sustained DoT started by each Full Charge). Filled in by
        # raid_simulator's weapon pass; empty for contexts without weapon stats.
        self.shot_times: dict[str, list[float]] = {}
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
        # for a resource that's SET to a fixed value rather than incremented
        # (e.g. Soda's Golden Chip resetting to 17 when her burst fires,
        # consuming whatever it had built up). Fills before a reset no longer
        # count toward the total; resource_count uses the latest reset at or
        # before the query time as its baseline instead of 0.
        self.resource_resets: dict[tuple[str, str], list[tuple[float, float, float]]] = {}

    def record_burst_time(self, slug: str, time: float) -> None:
        self.burst_times[slug].append(time)

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
        self, slug: str, name: str, time: float, cap: float, lifetime: float | None = None
    ) -> float:
        """`slug`'s resource `name` at `time`, clamped to `cap`. A permanent
        resource (lifetime=None) sums every fill at or before `time`; a timed one
        (lifetime seconds) sums only fills still active - a fill at tf is active
        for [tf, tf+lifetime), i.e. those in (time-lifetime, time]. The latest
        reset at or before `time` (if any) replaces the running baseline with
        its post-value; fills before that reset no longer count."""
        baseline = 0.0
        baseline_time = float("-inf")
        for reset_time, _pre_value, post_value in self.resource_resets.get((slug, name), []):
            if reset_time <= time and reset_time > baseline_time:
                baseline_time = reset_time
                baseline = post_value
        total = baseline
        for fill_time, amount in self.resource_fills.get((slug, name), []):
            if fill_time > time or fill_time <= baseline_time:
                continue
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
