"""Fit-free closed-form deck scorer (cascade Phase 1, option B).

Ranks a deck WITHOUT running simulate_raid and without fitting anything on
sampled simulations - the alternative to surrogate.py's sample regression,
whose fit cost grows with the roster.

How it can work at all: the skill encodings are thin closures over data. A
supporter's `buff_rule` action does nothing but `registry.add(Effect(stat,
value, scope, duration))`, so FIRING the rules once against a real registry
harvests the deck's whole buff table - no timeline, no shot loop, no damage
events. What this module adds on top is a static damage estimate over that
snapshot, mirroring raid_simulator's own `_damage_instance` term-for-term so
the multiplicative buckets (Base / Major / Element / Damage Up / Damage Taken)
combine the way the real formula combines them.

The approximation, stated plainly:

- ONE representative burst cycle is fired at t=0 (battle_start, every member's
  own_burst_activate + the ally_burst_activate it triggers, then
  full_burst_enter). Nothing is replayed over the fight.
- A timed buff counts at `duration / ASSUMED_CYCLE_SECONDS` of its value
  (capped at 1); a permanent buff counts fully. That is what keeps a 3-second
  buff from ranking like a permanent one, which snapshotting alone would do.
- Damage = each member's normal-attack stream over the fight + the best burst
  nuke available in each tier (the tier's leftmost unit is the one that
  bursts, and the caller's target is the combination's BEST ordering, so the
  tier max is the right proxy).

Deliberately NOT modeled: cooldown-reduction pulses, instant/periodic/
scheduled/resource-scaled nukes, "for N rounds" grants, resource stacks, and
weapon-mode transforms. Those need the timeline this module exists to avoid.
The scorer only has to RANK combinations well enough to feed a cascade - the
real simulate_raid stays the final judge of the top-K.

See docs/superpowers/specs/2026-07-23-cascade-surrogate-deck-search-design.md.
"""
from app.attack_rate import CHARGE_WEAPONS, generate_shot_times
from app.damage_formula import calculate_damage
from app.effects import EffectRegistry, _matches_target
from app.elements import element_multiplier
from app.raid_simulator import BASE_CRIT_RATE, CORE_HIT_BONUS, _TYPE_BUCKETS
from app.roster import assemble_simulation_inputs
from app.squad_engine import SquadContext, SquadMember

# One burst cycle: the gauge charge plus the Full Burst window it opens. Real
# cycles vary with the deck's own cooldown reduction, which this scorer cannot
# see - a single representative period is what makes buff durations comparable
# across decks at all.
ASSUMED_CYCLE_SECONDS = 20.0
FULL_BURST_SECONDS = 10.0

_shot_count_cache = {}


class _SnapshotRegistry(EffectRegistry):
    """EffectRegistry that can also total a stat with each effect weighted by
    how much of a burst cycle it actually covers.

    `total_for` answers "what is active at time t", which after firing every
    trigger at t=0 would credit a 3-second buff and a permanent one equally.
    Ranking decks is largely a question of buff UPTIME, so the scorer needs
    this view instead. Rules still call the inherited `total_for` (e.g. via
    SquadContext.top_atk_slugs), so this has to BE an EffectRegistry, not a
    recorder standing in for one.
    """

    def uptime_weighted_total(self, stat, target, cycle_seconds=ASSUMED_CYCLE_SECONDS):
        total = 0.0
        for effect, _applied_at in self._entries:
            if effect.stat != stat or not _matches_target(effect, target):
                continue
            weight = (
                1.0 if effect.duration is None
                else min(1.0, effect.duration / cycle_seconds)
            )
            total += effect.value * weight
        return total


def _fire(trigger, rules_by_slug, context, registry, failures):
    """squad_engine.fire_trigger, but a bullet that blows up on this
    timeline-less context is skipped rather than killing the whole score.

    Some rules read state only the simulator fills in (shot timelines,
    resource fills). Counting the skips in `failures` keeps that honest -
    callers can see how much of the deck the estimate had to ignore.
    """
    for slug, rules in rules_by_slug.items():
        matching = [rule for rule in rules if rule.trigger == trigger]
        if matching:
            context.record_activation(slug, trigger)
        for rule in matching:
            try:
                if rule.condition(context, slug):
                    rule.action(context, slug, 0.0, registry)
            except Exception:
                failures.append((slug, trigger))


def _snapshot(inputs, boss):
    """Fire one representative burst cycle and return its effect registry."""
    members = [
        SquadMember(m["slug"], m["burst_tier"], m["element"], m.get("weapon"))
        for m in inputs["deck"]
    ]
    context = SquadContext(
        members,
        base_atk={slug: stats["atk"] for slug, stats in inputs["base_stats"].items()},
        base_charge_time={
            slug: ws.get("charge_time", 0.0) for slug, ws in inputs["weapon_stats"].items()
        },
        boss_element=boss.element,
        part_destructible=boss.part_destructible,
        core_hittable=boss.core_hittable,
    )
    context.full_burst_windows = [(0.0, FULL_BURST_SECONDS)]
    registry = _SnapshotRegistry()
    rules = inputs["rules_by_slug"]
    failures = []

    _fire("battle_start", rules, context, registry, failures)
    for member in members:
        context.record_burst_time(member.slug, 0.0)
        context.burst_used_this_cycle.add(member.slug)
        _fire("own_burst_activate", {member.slug: rules.get(member.slug, [])},
              context, registry, failures)
        context.last_burst_slug = member.slug
        _fire("ally_burst_activate", rules, context, registry, failures)
    _fire("full_burst_enter", rules, context, registry, failures)

    return members, registry, failures


def _shot_count(weapon_stats, fight_duration):
    """Unbuffed normal-attack shots over the fight, memoized per weapon.

    Cadence buffs (attack/charge speed, max ammo) are ignored - they need the
    live timeline. The count depends only on the weapon, so identical units
    across combinations resolve it once.
    """
    key = (
        weapon_stats["weapon"], weapon_stats["max_ammo"], weapon_stats["reload_time"],
        weapon_stats["charge_time"], fight_duration,
    )
    cached = _shot_count_cache.get(key)
    if cached is None:
        cached = len(generate_shot_times(
            weapon_stats["weapon"], weapon_stats["max_ammo"], weapon_stats["reload_time"],
            weapon_stats["charge_time"], fight_duration,
        ))
        _shot_count_cache[key] = cached
    return cached


def _terms(slug, element, inputs, registry, boss):
    """raid_simulator._damage_instance's term dict, off the static snapshot."""
    target = {"slug": slug, "element": element}

    def stat(name):
        return registry.uptime_weighted_total(name, target)

    advantage_grant = stat("element_advantage_grant")
    if boss.element is None:
        element_bonus = 1.0
    elif advantage_grant > 0:
        element_bonus = 1.1
    else:
        element_bonus = element_multiplier(element, boss.element)

    return {
        "atk": inputs["base_stats"][slug]["atk"],
        "enemy_def": boss.enemy_def,
        "enemy_def_percent": stat("enemy_def_percent"),
        "atk_percent": stat("atk_percent"),
        "flat_atk": stat("flat_atk"),
        "other_elemental_bonus": stat("other_elemental_bonus"),
        "other_critical_damage_sources": stat("other_critical_damage_sources"),
        "crit_rate": min(1.0, BASE_CRIT_RATE + stat("crit_rate")),
        "core_hit_bonus": CORE_HIT_BONUS if boss.core_hittable else 0.0,
        "other_core_damage_sources": (
            stat("other_core_damage_sources") if boss.core_hittable else 0.0
        ),
        "element_multiplier": element_bonus,
        "charge_damage_bonus": stat("charge_damage_bonus"),
        "attack_damage_up": stat("attack_damage_up"),
        "damage_to_parts_up": stat("damage_to_parts_up"),
        "pierce_damage_up": stat("pierce_damage_up"),
        "damage_taken_up": stat("damage_taken_up"),
    }


def _typed(terms, registry, slug, element, damage_type):
    """Add the Damage-Up bucket that only this damage type collects."""
    typed = dict(terms)
    target = {"slug": slug, "element": element}
    for bucket in _TYPE_BUCKETS[damage_type]:
        typed[bucket] = registry.uptime_weighted_total(bucket, target)
    if damage_type == "true":
        typed["enemy_def"] = 0.0  # True Damage ignores enemy DEF
    return typed


def closed_form_score(ordered_deck, boss):
    """A cheap damage estimate for ranking `ordered_deck`, no simulation.

    The absolute number is NOT comparable to simulate_raid's total damage -
    only the ORDER it induces over decks is meaningful.
    """
    return score_with_diagnostics(ordered_deck, boss)[0]


def score_with_diagnostics(ordered_deck, boss):
    """(score, skipped_bullets) - see `_fire` for what gets skipped."""
    inputs = assemble_simulation_inputs(ordered_deck)
    members, registry, failures = _snapshot(inputs, boss)

    cycles = boss.fight_duration / ASSUMED_CYCLE_SECONDS
    full_burst_uptime = FULL_BURST_SECONDS / ASSUMED_CYCLE_SECONDS
    total = 0.0
    best_burst_per_tier = {}

    for member in members:
        slug, element = member.slug, member.element
        terms = _terms(slug, element, inputs, registry, boss)

        weapon_stats = inputs["weapon_stats"][slug]
        weapon = weapon_stats["weapon"]
        normal_type = "projectile_explosion" if weapon == "RL" else "attack"
        normal_terms = _typed(terms, registry, slug, element, normal_type)
        normal_terms["attack_coefficient"] = weapon_stats["damage_percent"] / 100
        # Full Burst covers only part of the cycle, so the stream collects the
        # bonus fractionally - the formula's term is linear in it.
        normal_terms["full_burst_bonus"] = full_burst_uptime
        if weapon in CHARGE_WEAPONS:
            normal_terms["charge_damage_bonus"] += (
                weapon_stats["charge_damage_percent"] / 100 - 1
            )
        total += _shot_count(weapon_stats, boss.fight_duration) * calculate_damage(**normal_terms)

        burst_percent = inputs["burst_damage_percents"].get(slug)
        if burst_percent:
            burst_type = inputs["burst_damage_types"].get(slug, "attack")
            burst_terms = _typed(terms, registry, slug, element, burst_type)
            burst_terms["attack_coefficient"] = burst_percent / 100
            burst_terms["full_burst_bonus"] = 1.0
            hits = inputs["burst_hit_counts"].get(slug, 1)
            burst = cycles * hits * calculate_damage(**burst_terms)
            # Only the tier's leftmost unit bursts, and the caller ranks a
            # combination by its BEST ordering - so the tier's best burst is
            # the one that ordering would use.
            best_burst_per_tier[member.burst_tier] = max(
                best_burst_per_tier.get(member.burst_tier, 0.0), burst
            )

    return total + sum(best_burst_per_tier.values()), failures
