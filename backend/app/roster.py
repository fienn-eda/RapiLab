"""Assembles per-Nikke specs into the inputs simulate_raid expects.

A NikkeSpec bundles everything that varies per owned Nikke: fixed metadata
(from api.dotgg.gg), the user's investment (skill values, overload options),
and weapon stats. assemble_simulation_inputs turns an ordered deck of
these into the (deck, rules_by_slug, burst_damage_percents, base_stats,
weapon_stats, periodic_nukes) that simulate_raid consumes - applying overload
and cube bonuses as permanent battle-start effects, which the earlier
hand-assembled demo omitted.

Deck ORDER is preserved end to end: burst_cycle picks the leftmost eligible
Nikke per tier, so the order of ordered_deck decides who nukes vs who is a
backup buffer among same-tier Nikkes.
"""
from dataclasses import dataclass, field

from app.attack_rate import CHARGE_ROUNDS_PER_MINUTE, charge_interval_floor_for
from app.collectible_effects import collectible_modifiers
from app.cube_effects import DEFAULT_CUBE, assumed_cube_effects, cube_refund_for
from app.overload_effects import overload_options_to_effects
from app.skill_rules.registry import (
    build_nikke_rules,
    get_ammo_refill_grant,
    get_ammo_rounds_per_shot,
    get_burst_anchored_buffs,
    get_burst_cooldown_reduction,
    get_burst_damage_type,
    get_burst_resolves_after_cast,
    get_charge_motion_delay,
    get_burst_delay,
    get_conditional_full_burst_delta,
    get_full_burst_duration_delta,
    get_self_stun,
    get_skill_ammo_refund,
    get_burst_hit_count,
    get_per_shot_rules,
    get_periodic_nuke,
    get_dynamic_hit_count_nukes,
    get_periodic_rules,
    get_resource_fill_triggered_buffs,
    get_resource_contributions,
    get_resource_gated_buffs,
    get_resource_scaled_nukes,
    get_resource_specs,
    get_scheduled_nukes,
    get_weapon_mode_schedules,
)
from app.squad_engine import SkillRule


@dataclass
class NikkeSpec:
    slug: str
    burst_tier: int
    burst_cooldown: float
    element: str
    weapon: str
    base_stats: dict  # {"atk", "def", "max_hp"}
    skill_values: dict
    weapon_stats: dict
    overload_options: list = field(default_factory=list)
    collectible_tid: int = 0
    collectible_level: int = 0
    # Which harmony cube this unit wears. Everyone is assumed to wear a
    # Resilience cube; the recorded raid is scored with the cubes actually worn
    # (scripts/raid_record.RECORD_CUBES), which is the only caller that sets it.
    cube: str = DEFAULT_CUBE


def _battle_start_effects_rule(effects):
    def action(context, caster_slug, time, registry):
        for effect in effects:
            registry.add(effect, applied_at=time)

    return SkillRule(trigger="battle_start", action=action)


def _passive_effects(spec: NikkeSpec, collectible_effects):
    """Overload, this unit's harmony cube, and the collectible it actually has
    equipped. A collectible's charge-damage 배율 is NOT here - it scales a
    weapon stat - but its normal-attack 배율 IS, because that one shares a buff
    bucket with skills. A cube that hands back rounds instead of moving a stat
    contributes nothing here - see the weapon stats below. The collectible is
    resolved by the caller so that one lookup feeds both this and the
    weapon-mode multiplier."""
    return (
        overload_options_to_effects(spec.overload_options, spec.slug)
        + assumed_cube_effects(spec.slug, spec.cube)
        + collectible_effects
    )


def _add_fill_source(spec, contribution):
    """`ResourceSpec.fill` is either one source or a list of (source, amount)
    pairs (see raid_simulator's `_fill_sources`), so a single-source spec is
    promoted to the list form on first contribution."""
    sources = spec.fill if isinstance(spec.fill, list) else [(spec.fill, 1)]
    spec.fill = [*sources, (contribution["fill"], contribution["amount"])]


def _merge_resource_contributions(resource_specs, contributions, members):
    """Append each contributor's fill source to the TARGET's ResourceSpec.

    A contribution names its targets one of two ways:

    - `"target"` + `"resource"` - one named slug's one named resource (Rei
      Ayanami writing into Asuka's Anti A.T. Field).
    - `"target_filter"` - a CLASS of resources, resolved against the live deck.
      Flora's Petunia says "affects all Electric Code allies: increases the
      stack count of stackable buffs by 1" and names nobody, so its targets are
      whichever fielded members match. Keys are `element` and `stackable_buff`,
      both matched exactly; `stackable_buff` is what keeps the bump off a gauge
      that merely happens to be modeled as a resource (Maiden's MP).

    A contribution is dropped when nothing matches - the stacks have nowhere to
    land, which is the game's own answer to fielding the writer without a
    holder. Each target's `cap` is untouched, so it still clamps the merged
    total (`SquadContext.resource_count` takes it) - a contribution can never
    push a count past what the holder's own skill states.
    """
    element_of = {m["slug"]: m["element"] for m in members}
    for contribution in contributions:
        target_filter = contribution.get("target_filter")
        if target_filter is None:
            for spec in resource_specs.get(contribution["target"], []):
                if spec.name == contribution["resource"]:
                    _add_fill_source(spec, contribution)
            continue
        for slug, specs in resource_specs.items():
            if element_of.get(slug) != target_filter["element"]:
                continue
            for spec in specs:
                if spec.stackable_buff == target_filter["stackable_buff"]:
                    _add_fill_source(spec, contribution)


def assemble_simulation_inputs(ordered_deck):
    deck = []
    rules_by_slug = {}
    burst_damage_percents = {}
    base_stats = {}
    weapon_stats = {}
    periodic_nukes = {}
    periodic_rules = {}
    per_shot_rules = {}
    resource_specs = {}
    # Fill sources one Nikke's kit adds to ANOTHER's resource, merged after the
    # per-unit loop so the target's spec exists by then. Collected rather than
    # applied inline because a contributor can be assembled before its target.
    resource_contributions = []
    burst_damage_types = {}
    burst_resolves_after_cast = set()
    ammo_rounds_per_shot = {}
    burst_hit_counts = {}
    resource_scaled_nukes = {}
    resource_gated_buffs = {}
    dynamic_hit_count_nukes = {}
    resource_fill_triggered_buffs = {}
    scheduled_nukes = {}
    weapon_mode_schedules = {}
    burst_anchored_buffs = {}
    conditional_full_burst_deltas = {}

    for spec in ordered_deck:
        # A standing self-scoped cut to the unit's own burst cooldown (Moran's
        # Fervor) is part of the number the scheduler starts from, unlike the
        # trigger-gated pulses that rewind it one cycle at a time.
        cooldown = max(
            0.0, spec.burst_cooldown - get_burst_cooldown_reduction(spec.slug, spec.skill_values)
        )
        member = {"slug": spec.slug, "burst_tier": spec.burst_tier, "element": spec.element,
                  "cooldown": cooldown, "weapon": spec.weapon}
        burst_delay = get_burst_delay(spec.slug, spec.skill_values)
        if burst_delay:
            member["burst_delay"] = burst_delay
        full_burst_delta = get_full_burst_duration_delta(spec.slug)
        if full_burst_delta:
            member["full_burst_duration_delta"] = full_burst_delta
        # Deck-dependent, so it is read here rather than baked into the spec:
        # who else is seated decides whether Mast ever reaches the Drunken cap
        # that stuns her.
        self_stun = get_self_stun(spec.slug, spec.skill_values,
                                  [u.slug for u in ordered_deck])
        if self_stun:
            member["self_stun"] = self_stun
        deck.append(member)
        base_stats[spec.slug] = spec.base_stats
        # Facts that change a unit's shot TIMELINE rather than its stats ride on
        # its weapon stats, so every shot-timeline path picks them up: the gap
        # between a charged shot and the next charge (see
        # attack_rate.CHARGE_MOTION_DELAY_SECONDS), and the rounds a Tactical
        # Bear cube hands back mid-magazine (attack_rate.AmmoRefund).
        timeline = {}
        motion_delay = get_charge_motion_delay(spec.slug)
        if motion_delay:
            timeline["charge_motion_delay"] = motion_delay
        # 멈춤이 없는 차지 무기는 대신 자기 연사에 걸린다 - 클래스 기본값을 쓰는
        # 유닛은 안 실어 보내야 타임라인이 예전과 바이트 단위로 같다
        # (attack_rate.CHARGE_ROUNDS_PER_MINUTE).
        if spec.slug in CHARGE_ROUNDS_PER_MINUTE:
            timeline["charge_interval_floor"] = charge_interval_floor_for(spec.slug)
        ammo_refund = cube_refund_for(spec.cube)
        if ammo_refund is not None:
            timeline["ammo_refund"] = ammo_refund
        # A refund off the unit's OWN skill can be gated on the boss's element,
        # which this layer does not know - it assembles a deck, not an
        # encounter - so the requirement travels with it for the simulator to
        # resolve (raid_simulator.resolve_ammo_refunds).
        skill_refund = get_skill_ammo_refund(spec.slug, spec.skill_values)
        if skill_refund is not None:
            timeline["skill_ammo_refund"] = skill_refund
        weapon_stats[spec.slug] = (
            {**spec.weapon_stats, **timeline} if timeline else spec.weapon_stats
        )
        # 시각 트리거 환급은 스탯이 아니라 받는 쪽의 발사 타임라인을 바꾸고, 스쿼드
        # 스코프면 다른 멤버에게 간다. 그래서 무기가 아니라 멤버에 실어 시뮬레이터가
        # 덱 전체를 보고 나눠 담게 한다.
        refill_grant = get_ammo_refill_grant(spec.slug, spec.skill_values)
        if refill_grant is not None:
            member["ammo_refill_grant"] = refill_grant
        rounds = get_ammo_rounds_per_shot(spec.slug)
        if rounds != (1.0, 1.0):
            ammo_rounds_per_shot[spec.slug] = rounds

        # One resolution per unit: the weapon 배율 feeds weapon-mode profiles
        # that are built from skill data (weapon_stats never reaches those), the
        # effects feed the buff registry. collectible_modifiers sits on
        # deck_search's permutation loop, so this stays a single call.
        weapon_multipliers, collectible_effects = collectible_modifiers(
            spec.collectible_tid, spec.collectible_level, spec.slug, spec.weapon)

        # inject caster base stats so skills that scale off them (e.g. Crown's
        # "X% of caster's ATK") resolve without the caller duplicating them
        skill_values = {
            **spec.skill_values,
            "caster_atk": spec.base_stats["atk"],
            "caster_def": spec.base_stats["def"],
            "caster_max_hp": spec.base_stats["max_hp"],
            "caster_weapon_stats": spec.weapon_stats,
            "caster_charge_damage_multiplier": weapon_multipliers.get(
                "charge_damage_percent", 1.0),
        }
        rules, burst_percent = build_nikke_rules(spec.slug, skill_values)

        passive = _passive_effects(spec, collectible_effects)
        if passive:
            rules = rules + [_battle_start_effects_rule(passive)]
        rules_by_slug[spec.slug] = rules

        if burst_percent is not None:
            burst_damage_percents[spec.slug] = burst_percent
            damage_type = get_burst_damage_type(spec.slug)
            if damage_type != "attack":
                burst_damage_types[spec.slug] = damage_type
            if get_burst_resolves_after_cast(spec.slug):
                burst_resolves_after_cast.add(spec.slug)
            hit_count = get_burst_hit_count(spec.slug)
            if hit_count != 1:
                burst_hit_counts[spec.slug] = hit_count

        periodic_nuke = get_periodic_nuke(spec.slug, skill_values)
        if periodic_nuke is not None:
            periodic_nukes[spec.slug] = periodic_nuke

        periodic_rule = get_periodic_rules(spec.slug, skill_values)
        if periodic_rule:
            periodic_rules[spec.slug] = periodic_rule

        per_shot_rule = get_per_shot_rules(spec.slug, skill_values)
        if per_shot_rule:
            per_shot_rules[spec.slug] = per_shot_rule

        conditional_full_burst = get_conditional_full_burst_delta(spec.slug, skill_values)
        if conditional_full_burst is not None:
            conditional_full_burst_deltas[spec.slug] = conditional_full_burst

        resource_spec = get_resource_specs(spec.slug, skill_values)
        if resource_spec:
            resource_specs[spec.slug] = resource_spec

        contribution = get_resource_contributions(spec.slug, skill_values)
        if contribution:
            resource_contributions.extend(contribution)

        resource_scaled_nuke = get_resource_scaled_nukes(spec.slug, skill_values)
        if resource_scaled_nuke:
            resource_scaled_nukes[spec.slug] = resource_scaled_nuke

        resource_gated_buff = get_resource_gated_buffs(spec.slug, skill_values)
        if resource_gated_buff:
            resource_gated_buffs[spec.slug] = resource_gated_buff

        dynamic_hit_count_nuke = get_dynamic_hit_count_nukes(spec.slug, skill_values)
        if dynamic_hit_count_nuke:
            dynamic_hit_count_nukes[spec.slug] = dynamic_hit_count_nuke

        resource_fill_triggered_buff = get_resource_fill_triggered_buffs(spec.slug, skill_values)
        if resource_fill_triggered_buff:
            resource_fill_triggered_buffs[spec.slug] = resource_fill_triggered_buff

        scheduled_nuke = get_scheduled_nukes(spec.slug, skill_values)
        if scheduled_nuke:
            scheduled_nukes[spec.slug] = scheduled_nuke

        weapon_mode_schedule = get_weapon_mode_schedules(spec.slug, skill_values)
        if weapon_mode_schedule:
            weapon_mode_schedules[spec.slug] = weapon_mode_schedule

        burst_anchored_buff = get_burst_anchored_buffs(spec.slug, skill_values)
        if burst_anchored_buff:
            burst_anchored_buffs[spec.slug] = burst_anchored_buff

    _merge_resource_contributions(resource_specs, resource_contributions, deck)

    return {
        "deck": deck,
        "rules_by_slug": rules_by_slug,
        "burst_damage_percents": burst_damage_percents,
        "base_stats": base_stats,
        "weapon_stats": weapon_stats,
        "periodic_nukes": periodic_nukes,
        "periodic_rules": periodic_rules,
        "per_shot_rules": per_shot_rules,
        "resource_specs": resource_specs,
        "burst_damage_types": burst_damage_types,
        "burst_resolves_after_cast": burst_resolves_after_cast,
        "ammo_rounds_per_shot": ammo_rounds_per_shot,
        "burst_hit_counts": burst_hit_counts,
        "resource_scaled_nukes": resource_scaled_nukes,
        "resource_gated_buffs": resource_gated_buffs,
        "dynamic_hit_count_nukes": dynamic_hit_count_nukes,
        "resource_fill_triggered_buffs": resource_fill_triggered_buffs,
        "scheduled_nukes": scheduled_nukes,
        "weapon_mode_schedules": weapon_mode_schedules,
        "burst_anchored_buffs": burst_anchored_buffs,
        "conditional_full_burst_deltas": conditional_full_burst_deltas,
    }
