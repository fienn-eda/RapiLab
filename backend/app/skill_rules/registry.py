"""Maps each encoded Nikke slug to a builder that turns its skill values into
(combat SkillRules, burst-nuke percent).

The roster/assembly layer and deck search use this so they never hardcode
which build_* functions a given slug needs. burst_percent is None for Nikkes
whose burst skill is buffs-only (no "X% of ATK" nuke), e.g. Crown/Anis: Star.

Each builder takes a `skill_values` dict keyed by that Nikke's sub-skill names
(plus caster base stats where a skill scales off them, e.g. Crown).

A separate, much smaller `_PERIODIC_NUKE_BUILDERS` map covers the rare Nikke
with a skill that fires repeatedly on its own fixed cooldown, independent of
the burst cycle (e.g. Helm: Aquamarine's Aegis Cannon Suppression Fire) - see
`get_periodic_nuke` and `raid_simulator`'s `periodic_nukes` parameter. Kept
separate from `_BUILDERS` so the ~25 existing builders' 2-tuple return shape
never has to change for the one or two Nikkes that need this.
"""
from app.skill_rules.ade_agent_bunny import build_ade_rules
from app.skill_rules.anchor_innocent_maid import build_anchor_rules
from app.skill_rules.anis_sparkling_summer import (
    build_anis_sparkling_summer_rules,
    build_sparkling_missile_per_shot_rules,
)
from app.skill_rules.anis_star import (
    build_star_anis_burst_rules,
    build_starfall_full_charge_nuke_rules,
    build_starfall_rules,
    build_stardust_rules,
)
from app.skill_rules.arcana import arcana_burst_percent, build_arcana_rules
from app.skill_rules.arcana_fortune_mate import build_fortune_mate_rules, radiant_youth_burst_percent
from app.skill_rules.asuka_shikinami_langley_wille import (
    build_anti_at_field_per_shot_rules,
    build_anti_at_field_resources,
    build_annihilation_dynamic_hit_count_nukes,
    build_annihilation_state_rules,
    build_emergency_repair_rules,
)
from app.skill_rules.blanc import build_blanc_rules
from app.skill_rules.brid_silent_track import build_brid_rules, build_journey_ahead_rules
from app.skill_rules.chisato_nishikigi import build_chisato_per_shot_rules, build_chisato_rules
from app.skill_rules.cinderella import (
    GLASS_SLIPPERS_HIT_COUNT,
    build_beautiful_resources,
    build_flawless_glass_per_shot_rules,
    build_flawless_glass_rules,
    build_glass_slippers_resource_scaled_nuke,
    glass_slippers_burst_percent,
)
from app.skill_rules.jill_valentine import build_jill_rules
from app.skill_rules.ludmilla_winter_owner import build_ludmilla_per_shot_rules, build_ludmilla_rules
from app.skill_rules.mana import (
    build_fatal_error_dot,
    build_fatal_error_self_buff_rules,
    build_metal_gamma_rules,
    build_metal_sigma_rules,
)
from app.skill_rules.crown import build_last_kingdom_rules, build_one_for_all_rules
from app.skill_rules.d_killer_wife import build_assault_formation_rules, build_d_killer_wife_rules
from app.skill_rules.grave import build_grave_rules, build_overheat_per_shot_rules
from app.skill_rules.guillotine_winter_slayer import (
    build_guillotine_resource_scaled_nukes,
    build_guillotine_resources,
    build_guillotine_rules,
)
from app.skill_rules.modernia import build_modernia_per_shot_rules, build_modernia_resources
from app.skill_rules.helm import (
    aegis_cannon_burst_percent,
    build_fire_away_rules,
    build_frontline_command_per_shot_rules,
)
from app.skill_rules.helm_aquamarine import (
    AEGIS_CANNON_SUPPRESSION_FIRE_COOLDOWN,
    aegis_cannon_overload_burst_percent,
    aegis_cannon_suppression_fire_percent,
    build_admire_accompaniment_per_shot_rules,
    build_helm_aquamarine_rules,
)
from app.skill_rules.isabel import (
    POINTED_FEATHER_COOLDOWN,
    build_isabel_rules,
    pointed_feather_percent,
    sonic_chaser_burst_percent,
)
from app.skill_rules.liberalio import (
    build_liberalio_per_shot_rules,
    build_liberalio_rules,
    submerged_world_burst_percent,
)
from app.skill_rules.julia import DECRESCENDO_COOLDOWN as JULIA_DECRESCENDO_COOLDOWN
from app.skill_rules.julia import (
    build_climax_resource_scaled_nuke,
    build_crescendo_resources,
    build_decrescendo_rules,
    climax_burst_percent,
)
from app.skill_rules import julia_signature
from app.skill_rules.little_mermaid import build_little_mermaid_rules
from app.skill_rules.liter import build_liter_rules
from app.skill_rules.maiden_ice_rose import (
    build_blessings_upon_you_per_shot_rules,
    build_blessings_upon_you_rules,
    build_diamond_dust_dynamic_hit_count_nukes,
    build_mp_resources,
)
from app.skill_rules.mast_romantic_maid import build_mast_rules
from app.skill_rules.mint import build_here_i_go_rules, build_mint_rules
from app.skill_rules.miranda import build_health_up_rules, build_miranda_rules
from app.skill_rules.moran import build_moran_rules
from app.skill_rules.nayuta import asceticism_burst_percent, build_nayuta_rules
from app.skill_rules.noir import build_noir_rules, finale_burst_percent
from app.skill_rules.prika import build_lets_get_show_started_rules, build_prika_rules
from app.skill_rules.quency_escape_queen import build_quency_rules, the_great_thief_burst_percent
from app.skill_rules.rosanna_chic_ocean import build_rosanna_rules
from app.skill_rules.rouge import build_card_throw_rules, build_coin_flip_rules, build_game_master_rules
from app.skill_rules.soda_twinkling_bunny import (
    build_golden_chip_resources,
    build_lucky_golden_chip_per_shot_rules,
    build_onward_soda_resource_gated_buffs,
    onward_soda_burst_percent,
)
from app.skill_rules.soline_frost_ticket import build_soline_frost_ticket_rules
from app.skill_rules.takina_inoue import (
    BATTLEFIELD_CONTROL_COOLDOWN,
    build_battlefield_control_rules,
    build_combat_support_rules,
    build_suppression_initiated_rules,
)
from app.skill_rules.tove import build_tove_rules
from app.skill_rules.velvet import build_bullets_of_love_per_shot_rules, build_velvet_rules
from app.skill_rules.privaty import (
    ak_missile_burst_percent,
    build_ak_missile_rules,
    build_ex_magazine_rules,
    build_ld_assault_per_shot_rules,
)
from app.skill_rules.rapi_red_hood import (
    build_battlefield_assessment_rules,
    power_of_inheritance_stage3_burst_percent,
)
from app.skill_rules.volume import build_volume_rules
from app.skill_rules.zwei import build_zwei_rules


def _build_rouge(sv):
    rules = build_card_throw_rules(sv["card_throw"])
    rules += build_coin_flip_rules(sv["coin_flip"])
    rules += build_game_master_rules({
        **sv["game_master"], "caster_atk": sv["caster_atk"], "caster_max_hp": sv["caster_max_hp"],
    })
    return rules, None


def _build_anis_star(sv):
    rules = build_starfall_rules(sv["starfall"])
    rules += build_stardust_rules({**sv["stardust"], "caster_atk": sv["caster_atk"]})
    rules += build_star_anis_burst_rules(sv["star_anis"])
    return rules, None


def _build_crown(sv):
    rules = build_one_for_all_rules(sv["one_for_all"], sv["caster_atk"], sv["caster_def"])
    rules += build_last_kingdom_rules(sv["last_kingdom"], sv["caster_max_hp"])
    return rules, None


def _build_rapi_red_hood(sv):
    rules = build_battlefield_assessment_rules(sv["battlefield_assessment"])
    burst_percent = power_of_inheritance_stage3_burst_percent(sv["power_of_inheritance"])
    return rules, burst_percent


def _build_helm(sv):
    rules = build_fire_away_rules(sv["fire_away"])
    return rules, aegis_cannon_burst_percent(sv["aegis_cannon"])


def _build_privaty(sv):
    rules = build_ex_magazine_rules(sv["ex_magazine"])
    rules += build_ak_missile_rules(sv["ak_missile"])
    return rules, ak_missile_burst_percent(sv["ak_missile"])


def _build_takina(sv):
    # Battlefield Control (Skill 2) is not here - it's a periodic (own-cooldown)
    # skill, exposed via _PERIODIC_RULE_BUILDERS / get_periodic_rules.
    rules = build_combat_support_rules(sv["combat_support"])
    rules += build_suppression_initiated_rules(sv["suppression_initiated"])
    return rules, None


def _build_cinderella(sv):
    rules = build_flawless_glass_rules(sv["flawless_glass"], sv["caster_max_hp"])
    return rules, glass_slippers_burst_percent(sv)


def _build_maiden(sv):
    rules = build_blessings_upon_you_rules(sv, sv["caster_max_hp"])
    return rules, None  # Diamond Dust is a dynamic_hit_count_nuke, not burst_damage_percents


def _build_asuka(sv):
    rules = build_annihilation_state_rules(sv, sv["caster_atk"])
    rules += build_emergency_repair_rules(sv)
    return rules, None  # Annihilation is a dynamic_hit_count_nuke, not burst_damage_percents


def _build_mana(sv):
    rules = build_metal_gamma_rules(sv)
    rules += build_metal_sigma_rules(sv)
    rules += build_fatal_error_self_buff_rules(sv)
    return rules, None  # Fatal Error! is a resource_scaled_nuke (flat DoT), not burst_damage_percents


_BUILDERS = {
    "anis-star": _build_anis_star,
    "anis-sparkling-summer": lambda sv: (build_anis_sparkling_summer_rules(sv), None),
    "ade-agent-bunny": lambda sv: (build_ade_rules(sv), None),
    "anchor-innocent-maid": lambda sv: (build_anchor_rules(sv), None),
    "arcana": lambda sv: (build_arcana_rules(sv), arcana_burst_percent(sv)),
    "arcana-fortune-mate": lambda sv: (build_fortune_mate_rules(sv), radiant_youth_burst_percent(sv)),
    "blanc": lambda sv: (build_blanc_rules(sv), None),
    "brid-silent-track": lambda sv: (build_brid_rules(sv), None),
    "cinderella": _build_cinderella,
    "crown": _build_crown,
    "rapi-red-hood": _build_rapi_red_hood,
    "helm": _build_helm,
    "helm-aquamarine": lambda sv: (build_helm_aquamarine_rules(sv), aegis_cannon_overload_burst_percent(sv)),
    "isabel": lambda sv: (build_isabel_rules(sv), sonic_chaser_burst_percent(sv)),
    "julia": lambda sv: ([], climax_burst_percent(sv)),  # Decrescendo is periodic-only; Crescendo is a resource
    "julia-signature": lambda sv: (
        julia_signature.build_decrescendo_battle_start_rules(sv["decrescendo"]),
        julia_signature.climax_burst_percent(sv),
    ),
    "liberalio": lambda sv: (build_liberalio_rules(sv), submerged_world_burst_percent(sv)),
    "ludmilla-winter-owner": lambda sv: (build_ludmilla_rules(sv), None),
    "mana": _build_mana,
    "chisato-nishikigi": lambda sv: (build_chisato_rules(sv), None),
    "maiden-ice-rose": _build_maiden,
    "asuka-shikinami-langley-wille": _build_asuka,
    "jill-valentine": lambda sv: (build_jill_rules(sv), None),
    "privaty": _build_privaty,
    "liter": lambda sv: (build_liter_rules(sv), None),
    "volume": lambda sv: (build_volume_rules(sv), None),
    "miranda": lambda sv: (build_miranda_rules(sv), None),
    "rouge": _build_rouge,
    "zwei": lambda sv: (build_zwei_rules(sv), None),
    "d-killer-wife": lambda sv: (build_d_killer_wife_rules(sv), None),  # Kill the Target (burst) deferred
    "grave": lambda sv: (build_grave_rules(sv), None),
    "guillotine-winter-slayer": lambda sv: (build_guillotine_rules(sv), None),  # Extermination DoT (Hero-Level-scaled) deferred
    "modernia": lambda sv: ([], None),  # all modeled content is per-shot + resource; burst deferred
    "little-mermaid": lambda sv: (build_little_mermaid_rules(sv), None),
    "mast-romantic-maid": lambda sv: (build_mast_rules(sv), None),
    "mint": lambda sv: (build_mint_rules(sv), None),
    "moran": lambda sv: (build_moran_rules(sv), None),
    "nayuta": lambda sv: (build_nayuta_rules(sv), asceticism_burst_percent(sv)),
    "noir": lambda sv: (build_noir_rules(sv), finale_burst_percent(sv)),
    "prika": lambda sv: (build_prika_rules(sv), None),
    "quency-escape-queen": lambda sv: (build_quency_rules(sv), the_great_thief_burst_percent(sv)),
    "rosanna-chic-ocean": lambda sv: (build_rosanna_rules(sv), None),
    "soda-twinkling-bunny": lambda sv: ([], onward_soda_burst_percent(sv)),
    "tove": lambda sv: (build_tove_rules(sv), None),
    "soline-frost-ticket": lambda sv: (build_soline_frost_ticket_rules(sv), None),
    "velvet": lambda sv: (build_velvet_rules(sv), None),
    "takina-inoue": _build_takina,
}

ENCODED_SLUGS = tuple(_BUILDERS)

_PERIODIC_NUKE_BUILDERS = {
    "helm-aquamarine": lambda sv: {
        "cooldown": AEGIS_CANNON_SUPPRESSION_FIRE_COOLDOWN,
        "percent": aegis_cannon_suppression_fire_percent(sv),
    },
    "isabel": lambda sv: {
        "cooldown": POINTED_FEATHER_COOLDOWN,
        "percent": pointed_feather_percent(sv),
    },
}

# A Nikke's burst nuke is "attack"-typed unless its skill deals a specific
# damage type (e.g. a "Projectile Explosion" keyword skill). Only overrides are
# listed; everything else defaults to "attack". The instance's type decides
# which type-gated Damage-Up buff applies (see raid_simulator._TYPE_BUCKETS).
_BURST_DAMAGE_TYPES = {
    "rapi-red-hood": "projectile_explosion",  # Power of Inheritance = Projectile Explosion skill
}

# A Nikke whose burst nuke "attacks sequentially N times" - N separate hits at
# the same instant, not one hit at N*percent (see raid_simulator's
# burst_hit_counts). Only overrides are listed; everything else defaults to 1.
_BURST_HIT_COUNTS = {
    "julia-signature": julia_signature.CLIMAX_HIT_COUNT,
    "cinderella": GLASS_SLIPPERS_HIT_COUNT,
}

# A Nikke with a Skill 1/2 on its own cooldown (fires at t=cooldown, 2*cooldown,
# ... applying buffs/debuffs) - see raid_simulator's `periodic_rules`. Kept
# separate from _BUILDERS (event-triggered rules) and _PERIODIC_NUKE_BUILDERS.
_PERIODIC_RULE_BUILDERS = {
    "takina-inoue": lambda sv: [
        (BATTLEFIELD_CONTROL_COOLDOWN, build_battlefield_control_rules(sv["battlefield_control"])),
    ],
    "julia": lambda sv: [
        (JULIA_DECRESCENDO_COOLDOWN, build_decrescendo_rules(sv["decrescendo"])),
    ],
    "julia-signature": lambda sv: [
        (
            julia_signature.DECRESCENDO_COOLDOWN,
            julia_signature.build_decrescendo_periodic_rules(sv["decrescendo"]),
        ),
    ],
}

# A Nikke with a skill that fires after/every N of its own shots (see
# raid_simulator's `per_shot_rules`). Each entry is a list of
# (threshold, mode, [SkillRule]); mode is "after" or "every".
_PER_SHOT_RULE_BUILDERS = {
    "anis-star": lambda sv: build_starfall_full_charge_nuke_rules(sv["starfall"]),
    "asuka-shikinami-langley-wille": lambda sv: build_anti_at_field_per_shot_rules(sv),
    "cinderella": lambda sv: build_flawless_glass_per_shot_rules(sv),
    "modernia": lambda sv: build_modernia_per_shot_rules(sv),
    "anis-sparkling-summer": lambda sv: build_sparkling_missile_per_shot_rules(sv["sparkling_missile"]),
    "grave": lambda sv: build_overheat_per_shot_rules(sv),
    "soda-twinkling-bunny": lambda sv: build_lucky_golden_chip_per_shot_rules(sv),
    "velvet": lambda sv: build_bullets_of_love_per_shot_rules(sv),
    "brid-silent-track": lambda sv: build_journey_ahead_rules(sv["journey_ahead"]),
    "helm-aquamarine": lambda sv: build_admire_accompaniment_per_shot_rules(sv["admire_accompaniment"]),
    "helm": lambda sv: build_frontline_command_per_shot_rules(sv["frontline_command"]),
    "privaty": lambda sv: build_ld_assault_per_shot_rules(sv),
    "d-killer-wife": lambda sv: build_assault_formation_rules(sv["assault_formation"]),
    "liberalio": lambda sv: build_liberalio_per_shot_rules(sv),
    "ludmilla-winter-owner": lambda sv: build_ludmilla_per_shot_rules(sv),
    "chisato-nishikigi": lambda sv: build_chisato_per_shot_rules(sv),
    "maiden-ice-rose": lambda sv: build_blessings_upon_you_per_shot_rules(sv),
    "miranda": lambda sv: build_health_up_rules(sv["health_up"]),
    "mint": lambda sv: build_here_i_go_rules({**sv["here_i_go"], "caster_atk": sv["caster_atk"]}),
    "prika": lambda sv: build_lets_get_show_started_rules(
        {**sv["lets_get_the_show_started"], "caster_atk": sv["caster_atk"]}
    ),
}


# A Nikke with a quantity-based resource (battery / ammo pouch / N-stack counter)
# that fills deterministically and drives count-scaled buffs - see
# raid_simulator's `resource_specs` param and effects.ResourceSpec. Each entry
# returns a list of ResourceSpec.
_RESOURCE_SPEC_BUILDERS = {
    "asuka-shikinami-langley-wille": lambda sv: build_anti_at_field_resources(sv),
    "julia": lambda sv: build_crescendo_resources(sv),
    "modernia": lambda sv: build_modernia_resources(sv),
    "guillotine-winter-slayer": lambda sv: build_guillotine_resources(sv),
    "cinderella": lambda sv: build_beautiful_resources(sv),
    "soda-twinkling-bunny": lambda sv: build_golden_chip_resources(sv),
    "maiden-ice-rose": lambda sv: build_mp_resources(sv),
}

# A Nikke with a burst-fired nuke whose magnitude is gated/scaled by a named
# resource's count (e.g. a "mirrors the stack count" additional hit, or a
# Hero-Level-scaled DoT) - see raid_simulator's `resource_scaled_nukes` param.
# Each entry returns a list of spec dicts: {"resource", "cap", "base_percent",
# "scale_fn", "tick_count", "tick_interval", "lifetime"(optional),
# "damage_type"(optional)}.
_RESOURCE_SCALED_NUKE_BUILDERS = {
    "cinderella": lambda sv: build_glass_slippers_resource_scaled_nuke(sv),
    "guillotine-winter-slayer": lambda sv: build_guillotine_resource_scaled_nukes(sv),
    "julia": lambda sv: build_climax_resource_scaled_nuke(sv),
    "mana": lambda sv: build_fatal_error_dot(sv),
}

# A Nikke with a burst-fired BUFF gated/scaled by a named resource's count at
# the burst's own time - see raid_simulator's `resource_gated_buffs` param.
# Each entry returns a list of spec dicts: {"resource", "cap",
# "use_pre_reset"(optional), "lifetime"(optional), "gate_fn", "stat", "value",
# "scope", "duration"}.
_RESOURCE_GATED_BUFF_BUILDERS = {
    "soda-twinkling-bunny": lambda sv: build_onward_soda_resource_gated_buffs(sv),
}

# A Nikke with a burst-fired nuke whose HIT COUNT (not just its percent) is
# itself a resource's value at burst time - see raid_simulator's
# `dynamic_hit_count_nukes` param. Each entry returns a list of spec dicts:
# {"resource", "base_percent", "extra_flat_atk_percent_of_max_hp"(optional),
# "damage_type"(optional)}.
_DYNAMIC_HIT_COUNT_NUKE_BUILDERS = {
    "maiden-ice-rose": lambda sv: build_diamond_dust_dynamic_hit_count_nukes(sv),
    "asuka-shikinami-langley-wille": lambda sv: build_annihilation_dynamic_hit_count_nukes(sv),
}


def build_nikke_rules(slug, skill_values):
    if slug not in _BUILDERS:
        raise KeyError(f"no encoded skill rules for slug: {slug!r}")
    return _BUILDERS[slug](skill_values)


def get_burst_damage_type(slug):
    """The damage type of this Nikke's burst nuke ("attack" for the vast
    majority; an override like "projectile_explosion" for keyword skills). Only
    matters for a slug that has a burst nuke - see raid_simulator's
    burst_damage_types."""
    return _BURST_DAMAGE_TYPES.get(slug, "attack")


def get_periodic_nuke(slug, skill_values):
    """{"cooldown": seconds, "percent": float} for a Nikke with a skill that
    fires repeatedly on its own fixed cooldown (see raid_simulator's
    `periodic_nukes` param), or None for the vast majority of Nikkes without
    one."""
    builder = _PERIODIC_NUKE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_periodic_rules(slug, skill_values):
    """List of (cooldown, [SkillRule, ...]) for a Nikke with a Skill 1/2 on its
    own cooldown (see raid_simulator's `periodic_rules`), or None for the vast
    majority of Nikkes without one."""
    builder = _PERIODIC_RULE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_per_shot_rules(slug, skill_values):
    """List of (threshold, mode, [SkillRule, ...]) for a Nikke with a skill that
    fires after/every N shots (see raid_simulator's `per_shot_rules`), or None
    for Nikkes without one. `mode` is "after" (once at the Nth shot) or "every"
    (at every Nth shot)."""
    builder = _PER_SHOT_RULE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_resource_specs(slug, skill_values):
    """List of ResourceSpec for a Nikke with a quantity-based resource (see
    raid_simulator's `resource_specs` param), or None for the vast majority
    without one."""
    builder = _RESOURCE_SPEC_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_burst_hit_count(slug):
    """How many separate hits this Nikke's burst nuke fires (see
    raid_simulator's `burst_hit_counts`); 1 for the vast majority."""
    return _BURST_HIT_COUNTS.get(slug, 1)


def get_resource_scaled_nukes(slug, skill_values):
    """List of resource-scaled-nuke spec dicts for a Nikke with a burst-fired
    nuke gated/scaled by a named resource's count (see raid_simulator's
    `resource_scaled_nukes` param), or None for the vast majority without one."""
    builder = _RESOURCE_SCALED_NUKE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_resource_gated_buffs(slug, skill_values):
    """List of resource-gated-buff spec dicts for a Nikke with a burst-fired
    buff gated/scaled by a named resource's count (see raid_simulator's
    `resource_gated_buffs` param), or None for the vast majority without one."""
    builder = _RESOURCE_GATED_BUFF_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_dynamic_hit_count_nukes(slug, skill_values):
    """List of dynamic-hit-count-nuke spec dicts for a Nikke with a burst-fired
    nuke whose HIT COUNT is itself a resource's value (see raid_simulator's
    `dynamic_hit_count_nukes` param), or None for the vast majority without
    one."""
    builder = _DYNAMIC_HIT_COUNT_NUKE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None
