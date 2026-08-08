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
from app.attack_rate import CHARGE_INTERVAL_FLOOR_SECONDS, CHARGE_MOTION_DELAY_SECONDS
from app.skill_rules._helpers import (SQUAD_DISTRIBUTED_DAMAGE_BUFF_SLUGS,
                                      SQUAD_SUSTAINED_DAMAGE_BUFF_SLUGS)
from app.skill_rules.ada_wong import build_ada_wong_rules, build_flash_grenade_periodic_nuke
from app.skill_rules.ade_agent_bunny import build_ade_rules
from app.skill_rules.anchor_innocent_maid import build_anchor_rules
from app.skill_rules.anis_sparkling_summer import (
    build_anis_sparkling_summer_rules,
    build_sparkling_missile_per_shot_rules,
)
from app.skill_rules.anis_star import (
    build_shooting_stars_scheduled_nukes,
    build_star_anis_burst_rules,
    build_starfall_full_charge_nuke_rules,
    build_starfall_rules,
    build_stardust_rules,
)
from app.skill_rules.arcana import arcana_burst_percent, build_arcana_rules
from app.skill_rules.arcana_fortune_mate import (
    build_fortune_mate_rules,
    build_keepsake_album_resource_gated_buffs,
    build_memories_and_moments_resources,
    radiant_youth_burst_percent,
)
from app.skill_rules.ark_ranger_black import (
    build_ark_ranger_black_rules,
    build_ark_ranger_dots,
    build_ark_ranger_ceiling_collider,
    build_ark_ranger_per_shot_rules,
)
from app.skill_rules.asuka_shikinami_langley_wille import (
    build_anti_at_field_per_shot_rules,
    build_anti_at_field_resources,
    build_annihilation_dynamic_hit_count_nukes,
    build_annihilation_state_rules,
    build_emergency_repair_rules,
)
from app.skill_rules.blanc import build_blanc_rules
from app.skill_rules.diesel_winter_sweets import (
    HIGHLIGHT_BURST_DELAY as _DIESEL_BURST_DELAY,
    build_diesel_burst_dot,
    build_diesel_full_burst_dot,
    build_diesel_highlight_rules,
    build_diesel_intro_rules,
    build_diesel_resource_specs,
)
from app.skill_rules.bready import (
    build_aftertaste_scheduled_nukes,
    build_bready_lingering_rules,
    build_bready_recommended_rules,
    build_lingering_per_shot_rules,
    build_recommended_per_shot_rules,
)
from app.skill_rules.brid_silent_track import build_brid_rules, build_journey_ahead_rules
from app.skill_rules.chisato_nishikigi import build_chisato_per_shot_rules, build_chisato_rules
from app.skill_rules.cinderella_crystal_wave import (
    build_crystal_wave_mg_rules,
    build_crystal_wave_snipe_rules,
    build_snipe_weapon_profile,
    crystal_wave_burst_percent,
    crystal_wave_periodic_nuke,
)
from app.skill_rules.cinderella import (
    GLASS_SLIPPERS_HIT_COUNT,
    build_beautiful_max_hp_rules,
    build_beautiful_resources,
    build_flawless_glass_charge_speed_rules,
    build_flawless_glass_per_shot_rules,
    build_flawless_glass_rules,
    build_glass_slippers_resource_scaled_nuke,
    glass_slippers_burst_percent,
)
from app.skill_rules.jill_valentine import (
    build_acid_ammo_periodic_nuke,
    build_jill_rules,
    build_magnum_per_shot_rules,
)
from app.skill_rules.marciana_marine_study import (
    build_marciana_per_shot_rules,
    build_marciana_rules,
)
from app.skill_rules.maxwell import build_maxwell_rules, build_pierce_shot_weapon_mode_schedule
from app.skill_rules.ludmilla_winter_owner import (
    build_ludmilla_per_shot_rules,
    build_ludmilla_rules,
    queens_gaze_ammo_refund,
)
from app.skill_rules.mana import (
    build_fatal_error_dot,
    build_fatal_error_self_buff_rules,
    build_metal_gamma_rules,
    build_metal_sigma_charge_rules,
    build_metal_sigma_rules,
)
from app.skill_rules.crown import (
    build_last_kingdom_rules,
    build_one_for_all_rules,
    build_royal_attire_per_shot_rules,
    build_royal_attire_rules,
)
from app.skill_rules.d_killer_wife import build_assault_formation_rules, build_d_killer_wife_rules
from app.skill_rules.delta_ninja_thief import (
    build_delta_ninja_thief_rules,
    ninja_overdrive_burst_percent,
)
from app.skill_rules.dolla import (
    ENTREPRENEURSHIP_COOLDOWN,
    build_dolla_rules,
    build_entrepreneurship_periodic_rules,
    rnd_shot_burst_percent,
)
from app.skill_rules.emma_tactical_upgrade import (
    build_emma_tactical_upgrade_rules,
    build_environment_setup_periodic_rules,
)
from app.skill_rules.eunhwa_tactical_upgrade import (
    build_camouflage_per_shot_rules,
    build_eunhwa_tactical_upgrade_rules,
    build_explosive_round_weapon_mode_schedule,
)
from app.skill_rules.grave import build_grave_rules, build_overheat_per_shot_rules
from app.skill_rules.rei_ayanami import (
    annihilation_burst_percent,
    build_preemptive_subdual_per_shot_rules,
    build_rei_ayanami_rules,
)
from app.skill_rules.rei_ayanami_tentative_name import (
    attack_state_burst_percent,
    build_annihilation_support_per_shot_rules,
    build_rei_tentative_rules,
)
from app.skill_rules.neon_vision_eye import (
    build_firepower_explosion_per_shot_rules,
    build_neon_vision_eye_rules,
)
from app.skill_rules.raven import (
    build_raven_rules,
    build_raven_scheduled_nukes,
    tempest_burst_percent,
)
from app.skill_rules.scarlet_black_shadow import (
    build_breakthrough_per_shot_rules,
    build_scarlet_black_shadow_rules,
    build_scarlet_weapon_mode_schedule,
)
from app.skill_rules.sakura_bloom_in_summer import (
    EPHEMERAL_SPENDER_HIT_COUNT,
    FULL_GLORY_COOLDOWN,
    build_sakura_bloom_in_summer_rules,
    build_sakura_periodic_rules,
    build_sakura_resource_scaled_nukes,
    build_sakura_scheduled_nukes,
    ephemeral_spender_burst_hit_count,
    ephemeral_spender_burst_percent,
)
from app.skill_rules.ein import (
    build_ein_per_shot_rules,
    build_ein_rules,
    build_ein_scheduled_nukes,
    feather_all_range_burst_percent,
)
from app.skill_rules.elegg_boom_and_shock import (
    build_elegg_boom_and_shock_rules,
    build_elegg_burst_delay,
    build_elegg_ghost_resources,
    build_ghostbuster_scheduled_nukes,
    build_thirteen_ghosts_dynamic_hit_count_nukes,
)
from app.skill_rules.eve import (
    COUNTER_CHAIN_HIT_COUNT,
    build_eve_rules,
    build_unstable_energy_per_shot_rules,
    counter_chain_burst_percent,
    eagle_eye_ammo_refund,
)
from app.skill_rules.milk_blooming_bunny import (
    build_milk_burst_anchored_buffs,
    build_milk_rules,
    build_milk_scheduled_nukes,
    build_milk_weapon_mode_schedule,
)
from app.skill_rules.drake import (
    build_drake_rules,
    build_drake_signature_rules,
    build_thunderbolt_per_shot_rules,
    build_thunderbolt_signature_per_shot_rules,
    drake_signature_burst_percent,
    drake_special_burst_percent,
)
from app.skill_rules.laplace import (
    build_buster_weapon_mode_schedule,
    build_hero_bomber_per_shot_rules,
    build_laplace_rules,
    laplace_buster_burst_percent,
)
from app.skill_rules import flora_signature
from app.skill_rules import phantom
from app.skill_rules import phantom_signature
from app.skill_rules import rosanna_signature
from app.skill_rules import laplace_signature
from app.skill_rules.laplace_ultimate_hero import (
    build_laplace_stage_nukes,
    build_laplace_transform_schedule,
    build_laplace_ultimate_hero_rules,
    laplace_ultimate_hero_burst_percent,
)
from app.skill_rules.maxwell_ordinary_mechanic import (
    build_matis_uberbuster_weapon_mode_schedule,
    build_maxwell_ordinary_mechanic_rules,
)
from app.skill_rules.dorothy_serendipity import (
    build_dorothy_serendipity_rules,
    build_flash_per_shot_rules,
)
from app.skill_rules.guillotine_winter_slayer import (
    build_guillotine_resource_scaled_nukes,
    build_guillotine_resources,
    build_guillotine_rules,
)
from app.skill_rules.mihara_bonding_chain import (
    build_dragging_chain_resource_scaled_nukes,
    build_ensnaring_chain_resources,
    build_mihara_bonding_chain_rules,
    build_mihara_scheduled_nukes,
)
from app.skill_rules.modernia import (
    build_modernia_per_shot_rules,
    build_modernia_resources,
    build_modernia_rules,
)
from app.skill_rules.helm import (
    aegis_cannon_burst_percent,
    build_aegis_cannon_rules,
    build_fire_away_per_shot_rules,
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
    build_calm_depths_charge_rules,
    build_liberalio_per_shot_rules,
    build_liberalio_rules,
    build_strange_currents_immunity_rules,
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
from app.skill_rules.leona import (
    build_leona_resources,
    build_leona_rules,
    build_lions_heart_resource_gated_buffs,
)
from app.skill_rules.little_mermaid import (
    build_bubble_barrage_scheduled_nukes,
    build_bubble_wave_fb_nuke,
    build_little_mermaid_rules,
)
from app.skill_rules.liter import build_liter_rules
from app.skill_rules.naga import (
    build_naga_rules,
    build_support_of_friendship_per_shot_rules,
)
from app.skill_rules.maiden_ice_rose import (
    build_blessings_fill_triggered_buffs,
    build_blessings_upon_you_per_shot_rules,
    build_blessings_upon_you_rules,
    build_diamond_dust_dynamic_hit_count_nukes,
    build_meditation_per_shot_rules,
    build_mp_resources,
)
from app.skill_rules.mast_romantic_maid import (build_mast_rules,
                                                build_mast_self_stun)
from app.skill_rules.mint import build_here_i_go_rules, build_mint_rules
from app.skill_rules.miranda import (
    build_health_up_hit_rate_rules,
    build_health_up_rules,
    build_miranda_base_rules,
    build_miranda_rules,
)
from app.skill_rules.moran import (
    build_bring_it_on_per_shot_rules,
    build_fair_and_square_weapon_mode_schedule,
    build_moran_base_rules,
    build_moran_fervor_cooldown_reduction,
    build_moran_rules,
)
from app.skill_rules.nayuta import (
    asceticism_burst_percent,
    build_memory_incineration_scheduled_nukes,
    build_memory_incineration_weapon_mode_schedule,
    build_nayuta_rules,
)
from app.skill_rules.noir import build_noir_rules, finale_burst_percent
from app.skill_rules.prika import build_lets_get_show_started_rules, build_prika_rules
from app.skill_rules.quency_escape_queen import build_quency_rules, the_great_thief_burst_percent
from app.skill_rules.rosanna_chic_ocean import (
    build_rosanna_rules,
    build_spina_periodic_rules,
    build_spina_scheduled_nukes,
)
from app.skill_rules.rouge import (
    build_card_throw_per_shot_rules,
    build_card_throw_rules,
    build_coin_flip_per_shot_rules,
    build_coin_flip_rules,
    build_game_master_rules,
)
from app.skill_rules.soda_twinkling_bunny import (
    build_beginners_rewards_full_burst_delta,
    build_beginners_rewards_per_shot_rules,
    build_golden_chip_resources,
    build_lucky_golden_chip_per_shot_rules,
    build_onward_soda_resource_gated_buffs,
    onward_soda_burst_percent,
)
from app.skill_rules.snow_white import (
    build_determination_per_shot_rules,
    build_seven_dwarves_weapon_mode_schedule,
    build_snow_white_rules,
    snow_white_periodic_nuke,
)
from app.skill_rules.snow_white_heavy_arms import (
    build_fully_active_weapon_mode_schedule,
    build_seven_dwarves_per_shot_rules,
    build_snow_white_heavy_arms_rules,
)
from app.skill_rules import centi
from app.skill_rules.flora import build_flora_rules
from app.skill_rules import rosanna as rosanna_base
from app.skill_rules.soline_frost_ticket import build_soline_frost_ticket_rules
from app.skill_rules import sugar_signature
from app.skill_rules.sugar import build_sugar_rules
from app.skill_rules.takina_inoue import (
    BATTLEFIELD_CONTROL_COOLDOWN,
    build_battlefield_control_rules,
    build_combat_support_rules,
    build_suppression_initiated_rules,
    build_suppression_initiated_weapon_mode_schedule,
)
from app.skill_rules.tove import build_tove_rules
from app.skill_rules.velvet import build_velvet_per_shot_rules, build_velvet_rules
from app.skill_rules.red_hood import (
    build_red_hood_rules,
    build_red_wolf_weapon_mode_schedule,
)
from app.skill_rules.privaty import (
    build_ex_magazine_base_rules,
    build_ld_assault_base_per_shot_rules,
    ak_missile_burst_percent,
    build_ak_missile_rules,
    build_ex_magazine_rules,
    build_ld_assault_per_shot_rules,
)
from app.skill_rules.rapi_red_hood import (
    build_attachable_projectiles_rules,
    build_attachable_projectiles_scheduled_nukes,
    build_battlefield_assessment_rules,
    build_power_of_inheritance_rules,
    build_power_of_inheritance_stage1_rules,
    power_of_inheritance_stage3_burst_percent,
)
from app.skill_rules.volume import build_volume_rules
from app.skill_rules.zwei import (
    build_overcharge_weapon_mode_schedule,
    build_frame_analysis_resources,
    build_pierce_equation_per_shot_rules,
    build_zwei_base_rules,
    build_zwei_rules,
)


def _build_rouge(sv):
    rules = build_card_throw_rules(sv["card_throw"])
    rules += build_coin_flip_rules({**sv["coin_flip"], "caster_max_hp": sv["caster_max_hp"]})
    rules += build_game_master_rules({
        **sv["game_master"], "caster_atk": sv["caster_atk"], "caster_max_hp": sv["caster_max_hp"],
    })
    return rules, None


def _build_anis_star(sv):
    rules = build_starfall_rules(sv["starfall"])
    rules += build_stardust_rules({**sv["stardust"], "caster_atk": sv["caster_atk"]})
    rules += build_star_anis_burst_rules({
        **sv["star_anis"],
        "caster_weapon_stats": sv["caster_weapon_stats"],
        "caster_max_hp": sv["caster_max_hp"],
    })
    return rules, None


def _build_crown(sv):
    rules = build_one_for_all_rules(sv["one_for_all"], sv["caster_atk"], sv["caster_def"])
    rules += build_last_kingdom_rules(sv["last_kingdom"], sv["caster_max_hp"])
    rules += build_royal_attire_rules(sv["royal_attire"])
    return rules, None


def _build_rapi_red_hood(sv):
    rules = build_battlefield_assessment_rules(sv["battlefield_assessment"])
    rules += build_attachable_projectiles_rules(sv["attachable_projectiles"])
    rules += build_power_of_inheritance_rules(sv)
    burst_percent = power_of_inheritance_stage3_burst_percent(sv["power_of_inheritance"])
    return rules, burst_percent


def _build_rapi_red_hood_b1(sv):
    # Combat Assist / B1 stand-in seat (Task 7) - Stage 1 Power of Inheritance
    # is support-only (no damage), and does NOT get the Stage 3 rider
    # (build_power_of_inheritance_rules): the 421.2% attachment window and the
    # requirement cut are Stage-3-only.
    rules = build_battlefield_assessment_rules(sv["battlefield_assessment"])
    rules += build_attachable_projectiles_rules(sv["attachable_projectiles"])
    rules += build_power_of_inheritance_stage1_rules(sv)
    return rules, None  # Stage 1 use deals no damage


def _build_helm(sv):
    # Base Helm has no Charge Damage rider - that effect exists only in the
    # Favorite Item's text (and the base array's slots 04/05 mean something else).
    return build_fire_away_rules(sv["fire_away"]), aegis_cannon_burst_percent(
        sv["aegis_cannon"]
    )


def _build_helm_signature(sv):
    rules = build_fire_away_rules(sv["fire_away"])
    rules += build_aegis_cannon_rules(sv["aegis_cannon"])
    return rules, aegis_cannon_burst_percent(sv["aegis_cannon"])


def _build_privaty(sv):
    # AK Missile's self elemental bonus (slots 05/06) is the Favorite Item's
    # text; the base burst is a plain nuke plus an inert stun.
    return build_ex_magazine_base_rules(sv["ex_magazine"]), ak_missile_burst_percent(
        sv["ak_missile"]
    )


def _build_privaty_signature(sv):
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
    rules = build_flawless_glass_rules(sv, sv["caster_max_hp"])
    rules += build_flawless_glass_charge_speed_rules(sv)
    rules += build_beautiful_max_hp_rules(sv, sv["caster_max_hp"])
    return rules, glass_slippers_burst_percent(sv)


def _build_maiden(sv):
    rules = build_blessings_upon_you_rules(sv, sv["caster_max_hp"])
    return rules, None  # Diamond Dust is a dynamic_hit_count_nuke, not burst_damage_percents


def _build_asuka(sv):
    rules = build_annihilation_state_rules(sv, sv["caster_atk"])
    rules += build_emergency_repair_rules(sv)
    return rules, None  # Annihilation is a dynamic_hit_count_nuke, not burst_damage_percents


def _build_laplace_ultimate_hero(sv):
    rules = build_laplace_ultimate_hero_rules(sv, sv["caster_max_hp"])
    return rules, laplace_ultimate_hero_burst_percent(sv)


def _build_maxwell_ordinary_mechanic(sv):
    rules = build_maxwell_ordinary_mechanic_rules(sv, sv["caster_max_hp"])
    return rules, None  # Matis Uberbuster is a self weapon transform, not a burst nuke


def _build_mana(sv):
    rules = build_metal_gamma_rules(sv)
    rules += build_metal_sigma_rules(sv)
    rules += build_metal_sigma_charge_rules(sv)
    rules += build_fatal_error_self_buff_rules(sv)
    return rules, None  # Fatal Error! is a resource_scaled_nuke (flat DoT), not burst_damage_percents


_BUILDERS = {
    "ada-wong": lambda sv: (build_ada_wong_rules(sv), None),  # Secret Agent is buff-only
    "anis-star": _build_anis_star,
    "anis-sparkling-summer": lambda sv: (build_anis_sparkling_summer_rules(sv), None),
    "ade-agent-bunny": lambda sv: (build_ade_rules(sv), None),
    "anchor-innocent-maid": lambda sv: (build_anchor_rules(sv), None),
    "arcana": lambda sv: (build_arcana_rules(sv), arcana_burst_percent(sv)),
    "arcana-fortune-mate": lambda sv: (build_fortune_mate_rules(sv), radiant_youth_burst_percent(sv)),
    "ark-ranger-black": lambda sv: (build_ark_ranger_black_rules(sv), None),
    "blanc": lambda sv: (build_blanc_rules(sv), None),
    "brid-silent-track": lambda sv: (build_brid_rules(sv), None),
    # Her burst is the same in both builds; the Favorite Item's buffs ride
    # Skill 2's cycle, so they arrive through _PERIODIC_RULE_BUILDERS instead.
    "centi": lambda sv: (centi.build_centi_rules(sv), centi.start_construction_burst_percent(sv)),
    "centi-signature": lambda sv: (
        centi.build_centi_rules(sv), centi.start_construction_burst_percent(sv)
    ),
    "cinderella": _build_cinderella,
    "cinderella-crystal-wave-mg": lambda sv: (
        build_crystal_wave_mg_rules(sv), crystal_wave_burst_percent(sv)
    ),
    "cinderella-crystal-wave-snipe": lambda sv: (
        build_crystal_wave_snipe_rules(sv), crystal_wave_burst_percent(sv)
    ),
    "crown": _build_crown,
    "rapi-red-hood": _build_rapi_red_hood,
    "rapi-red-hood-b1": _build_rapi_red_hood_b1,
    "helm": _build_helm,
    "helm-signature": _build_helm_signature,
    "helm-aquamarine": lambda sv: (build_helm_aquamarine_rules(sv), aegis_cannon_overload_burst_percent(sv)),
    "isabel": lambda sv: (build_isabel_rules(sv), sonic_chaser_burst_percent(sv)),
    "julia": lambda sv: ([], climax_burst_percent(sv)),  # Decrescendo is periodic-only; Crescendo is a resource
    "julia-signature": lambda sv: (
        julia_signature.build_decrescendo_battle_start_rules(sv["decrescendo"]),
        julia_signature.climax_burst_percent(sv),
    ),
    "liberalio": lambda sv: (
        build_liberalio_rules(sv)
        + build_strange_currents_immunity_rules(sv["strange_currents"])
        + build_calm_depths_charge_rules(sv, sv["caster_weapon_stats"]),
        submerged_world_burst_percent(sv),
    ),
    "ludmilla-winter-owner": lambda sv: (build_ludmilla_rules(sv), None),
    "mana": _build_mana,
    # Her burst deals no direct damage - Overconfident is buffs plus the
    # Distributed ticks in _SCHEDULED_NUKE_BUILDERS.
    "milk-blooming-bunny": lambda sv: (build_milk_rules(sv), None),
    "chisato-nishikigi": lambda sv: (build_chisato_rules(sv), None),
    "maiden-ice-rose": _build_maiden,
    "asuka-shikinami-langley-wille": _build_asuka,
    "jill-valentine": lambda sv: (build_jill_rules(sv), None),
    "marciana-marine-study": lambda sv: (build_marciana_rules(sv), None),  # burst is buff-only; damage is Flagged Target nukes (per-shot + full-burst)
    "maxwell": lambda sv: (build_maxwell_rules(sv), None),  # burst is the Pierce Shot weapon transform (weapon-mode segment), no direct nuke
    "maxwell-ordinary-mechanic": _build_maxwell_ordinary_mechanic,
    "laplace-ultimate-hero": _build_laplace_ultimate_hero,
    "privaty": _build_privaty,
    "privaty-signature": _build_privaty_signature,
    # Lion's Heart is buffs only; her burst deals no damage.
    "leona": lambda sv: (build_leona_rules(sv), None),
    "liter": lambda sv: (build_liter_rules(sv), None),
    "volume": lambda sv: (build_volume_rules(sv), None),
    "miranda": lambda sv: (build_miranda_base_rules(sv), None),
    "miranda-signature": lambda sv: (build_miranda_rules(sv), None),
    "rouge": _build_rouge,
    "zwei": lambda sv: (build_zwei_base_rules(sv), None),
    "zwei-signature": lambda sv: (build_zwei_rules(sv), None),
    "d-killer-wife": lambda sv: (build_d_killer_wife_rules(sv), None),  # Kill the Target (burst) deferred
    "delta-ninja-thief": lambda sv: (
        build_delta_ninja_thief_rules(sv), ninja_overdrive_burst_percent(sv)),
    "dolla": lambda sv: (build_dolla_rules(sv), rnd_shot_burst_percent(sv)),
    # Both Tactical Upgrades' bursts are buff-only as far as a burst PERCENT
    # goes: Emma's is pure buffs, and Eunhwa's damage is the weapon-mode
    # segment her burst swaps in (see _WEAPON_MODE_SCHEDULE_BUILDERS).
    "emma-tactical-upgrade": lambda sv: (build_emma_tactical_upgrade_rules(sv), None),
    "eunhwa-tactical-upgrade": lambda sv: (build_eunhwa_tactical_upgrade_rules(sv), None),
    "grave": lambda sv: (build_grave_rules(sv), None),
    "rei-ayanami": lambda sv: (build_rei_ayanami_rules(sv), annihilation_burst_percent(sv)),
    "rei-ayanami-tentative-name": lambda sv: (build_rei_tentative_rules(sv), attack_state_burst_percent(sv)),
    "neon-vision-eye": lambda sv: (build_neon_vision_eye_rules(sv), None),  # burst is buff-only; damage is Firepower Explosion (per-shot)
    "ein": lambda sv: (build_ein_rules(sv), feather_all_range_burst_percent(sv)),
    "eve": lambda sv: (build_eve_rules(sv), counter_chain_burst_percent(sv)),
    # 13 Ghosts fires via dynamic_hit_count_nukes (branching hit count), not a flat burst percent.
    "elegg-boom-and-shock": lambda sv: (build_elegg_boom_and_shock_rules(sv), None),
    # La La La's damage is its 9-tick DoT (see _RESOURCE_SCALED_NUKE_BUILDERS),
    # not a flat burst nuke.
    "diesel-winter-sweets-intro": lambda sv: (build_diesel_intro_rules(sv), None),
    "diesel-winter-sweets-highlight": lambda sv: (build_diesel_highlight_rules(sv), None),
    # Neither Taste mode has a burst nuke - New Flavor is buffs only.
    "bready-lingering": lambda sv: (build_bready_lingering_rules(sv), None),
    "bready-recommended": lambda sv: (build_bready_recommended_rules(sv), None),
    # Bonding Pain is a resource-scaled DoT, not a flat burst nuke.
    "mihara-bonding-chain": lambda sv: (build_mihara_bonding_chain_rules(sv), None),
    "raven": lambda sv: (build_raven_rules(sv), tempest_burst_percent(sv)),
    "sakura-bloom-in-summer": lambda sv: (
        build_sakura_bloom_in_summer_rules(sv), ephemeral_spender_burst_percent(sv)
    ),
    "red-hood": lambda sv: (build_red_hood_rules(sv), None),  # burst is the Step 3 weapon transform (weapon-mode segment), no direct nuke
    "scarlet-black-shadow": lambda sv: (build_scarlet_black_shadow_rules(sv), None),  # burst is buff-only; damage is the Breakthrough sequence (per-shot)
    "snow-white": lambda sv: (build_snow_white_rules(sv), None),  # burst is the weapon transform (weapon-mode segment), no direct nuke
    "snow-white-heavy-arms": lambda sv: (build_snow_white_heavy_arms_rules(sv), None),  # burst is the Fully Active state change (weapon-mode segment), no direct nuke
    "drake": lambda sv: (build_drake_rules(sv), drake_special_burst_percent(sv)),
    "drake-signature": lambda sv: (build_drake_signature_rules(sv), drake_signature_burst_percent(sv)),
    "laplace": lambda sv: (build_laplace_rules(sv), laplace_buster_burst_percent(sv)),  # no ally buffs; Hero Vision deferred
    "laplace-signature": lambda sv: (
        laplace_signature.build_laplace_signature_rules(sv),
        laplace_signature.laplace_buster_signature_burst_percent(sv),
    ),
    "dorothy-serendipity": lambda sv: (build_dorothy_serendipity_rules(sv), None),  # burst is buff-only (self Attack Speed + ATK)
    "guillotine-winter-slayer": lambda sv: (build_guillotine_rules(sv), None),  # Extermination DoT (Hero-Level-scaled) deferred
    "modernia": lambda sv: (build_modernia_rules(sv), None),  # burst deferred; the rest is per-shot + resource
    "little-mermaid": lambda sv: (build_little_mermaid_rules(sv), None),
    "mast-romantic-maid": lambda sv: (build_mast_rules(sv), None),
    "mint": lambda sv: (build_mint_rules(sv), None),
    "moran": lambda sv: (build_moran_base_rules(sv), None),
    "moran-signature": lambda sv: (build_moran_rules(sv), None),
    # As Long As We're With Friends is buffs only; her burst deals no damage.
    "naga": lambda sv: (build_naga_rules(sv), None),
    "nayuta": lambda sv: (build_nayuta_rules(sv), asceticism_burst_percent(sv)),
    "noir": lambda sv: (build_noir_rules(sv), finale_burst_percent(sv)),
    "prika": lambda sv: (build_prika_rules(sv), None),
    "quency-escape-queen": lambda sv: (build_quency_rules(sv), the_great_thief_burst_percent(sv)),
    "rosanna-chic-ocean": lambda sv: (build_rosanna_rules(sv), None),
    "soda-twinkling-bunny": lambda sv: ([], onward_soda_burst_percent(sv)),
    "tove": lambda sv: (build_tove_rules(sv), None),
    "tove-signature": lambda sv: (build_tove_rules(sv), None),
    "soline-frost-ticket": lambda sv: (build_soline_frost_ticket_rules(sv), None),
    "flora": lambda sv: (build_flora_rules(sv), None),  # burst is heal + buffs, no nuke
    "phantom": lambda sv: (
        phantom.build_phantom_rules(sv), phantom.secret_trick_burst_percent(sv),
    ),
    "phantom-signature": lambda sv: (
        phantom_signature.build_phantom_signature_rules(sv),
        phantom_signature.secret_trick_signature_burst_percent(sv),
    ),
    "rosanna": lambda sv: (
        rosanna_base.build_rosanna_base_rules(sv),
        rosanna_base.vendetta_burst_percent(sv),
    ),
    "rosanna-signature": lambda sv: (
        rosanna_signature.build_rosanna_signature_rules(sv),
        rosanna_signature.vendetta_signature_burst_percent(sv),
    ),
    "flora-signature": lambda sv: (
        flora_signature.build_flora_signature_rules(sv), None,
    ),
    "sugar": lambda sv: (build_sugar_rules(sv), None),  # burst is buffs-only, no nuke
    "sugar-signature": lambda sv: (
        sugar_signature.build_sugar_signature_rules(sv), None,
    ),
    "velvet": lambda sv: (build_velvet_rules(sv), None),
    "takina-inoue": _build_takina,
}

ENCODED_SLUGS = tuple(_BUILDERS)

# One owned character who yields MULTIPLE deck candidates (Fienn, 2026-07-18/19):
# a pre-battle mode choice (Cinderella: Crystal Wave MG/Snipe) or a formation
# role choice (Rapi: Red Hood B3/B1). The tuple lists every candidate slug the
# roster loader fans the one owned state out to (include the base slug itself
# when it stays a candidate).
#
# This is the FAN-OUT table - what the engine may CHOOSE between - and only
# that. It is not the identity table: "may these two hold a seat at once" is
# `character_map()`, which also covers the Favorite Item builds. A build the
# player either owns or does not own is settled data, never a candidate, so it
# belongs there and must never be added here - fanning one out would offer the
# search an item's effects the player may not have.
MODE_VARIANTS: dict[str, tuple[str, ...]] = {
    "bready": ("bready-lingering", "bready-recommended"),
    "diesel-winter-sweets": ("diesel-winter-sweets-intro", "diesel-winter-sweets-highlight"),
    "cinderella-crystal-wave": ("cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe"),
    "rapi-red-hood": ("rapi-red-hood", "rapi-red-hood-b1"),
}

# Units the player deliberately holds back rather than bursting the instant
# the cooldown allows (see burst_cycle's `burst_delay`). Builders, not plain
# specs, because a delay may be derived from the unit's own skill values -
# Elegg waits out her ghost fill, whose length is cap x capture interval.
_BURST_DELAY_BUILDERS = {
    "diesel-winter-sweets-highlight": lambda sv: _DIESEL_BURST_DELAY,
    "elegg-boom-and-shock": lambda sv: build_elegg_burst_delay(sv),
}


# A Nikke whose own burst grants a buff at an OFFSET from the burst, possibly
# lasting until that unit's NEXT own burst rather than a fixed duration - see
# raid_simulator's `burst_anchored_buffs` param and UNTIL_NEXT_OWN_BURST. Each
# entry returns a list of spec dicts: {"offset", "stat", "value", "scope",
# "duration"}.
_BURST_ANCHORED_BUFF_BUILDERS = {
    "milk-blooming-bunny": lambda sv: build_milk_burst_anchored_buffs(sv),
}


def get_burst_anchored_buffs(slug, skill_values):
    """List of burst-anchored-buff spec dicts for a Nikke whose own burst opens
    a state at an offset (see raid_simulator's `burst_anchored_buffs`), or None
    for the vast majority without one."""
    builder = _BURST_ANCHORED_BUFF_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


# A Nikke who takes HERSELF out of the rotation on a recurring, mid-fight
# event (burst_cycle's `self_stun`). Deck-dependent, unlike every other builder
# here: Mast: Romantic Maid only reaches the Drunken cap that stuns her when no
# Anchor is clearing a stack each cycle, so the builder is handed the deck.
_SELF_STUN_BUILDERS = {
    "mast-romantic-maid": build_mast_self_stun,
}


def get_self_stun(slug, skill_values, deck_slugs):
    """This unit's self-inflicted downtime in THIS deck, or None - which is
    everyone but Mast, and Mast herself beside an Anchor."""
    builder = _SELF_STUN_BUILDERS.get(slug)
    return builder(skill_values, deck_slugs) if builder else None


def has_burst_delay(slug):
    """Whether this slug's kit holds its first burst back at all. The seat rules
    ask this before `get_burst_delay`, which needs the unit's skill values -
    only the handful of units with a delay builder are worth reading them for,
    and a caller holding something less than a full spec should not have to."""
    return slug in _BURST_DELAY_BUILDERS


def get_burst_delay(slug, skill_values):
    builder = _BURST_DELAY_BUILDERS.get(slug)
    if builder is None:
        return None
    return builder(skill_values)


# A Nikke whose own kit cuts her OWN burst cooldown CONTINUOUSLY, as a standing
# property rather than a per-cycle pulse - so it belongs to the number the
# scheduler starts from, not to `burst_cooldown_reduction_sec` (which rewinds
# one cycle at a time and is how the squad-scoped, trigger-gated cuts work).
_BURST_COOLDOWN_REDUCTION_BUILDERS = {
    "moran-signature": lambda sv: build_moran_fervor_cooldown_reduction(sv),
}


def get_burst_cooldown_reduction(slug, skill_values):
    """Seconds permanently off this Nikke's own burst cooldown (0.0 for the
    vast majority, which have no such effect)."""
    builder = _BURST_COOLDOWN_REDUCTION_BUILDERS.get(slug)
    return builder(skill_values) if builder else 0.0


# 자기 버스트가 풀 버스트 창 자체의 길이를 바꾸는 Burst 3. 값이 스킬 데이터 슬롯이
# 아니라 설명문에 박힌 리터럴이라 여기 적는다(그레이브의 "10 sec"와 같은 사정).
# 효과는 그 유닛이 연 사이클에만 걸린다 - burst_cycle이 티어 3을 쏜 멤버에게서 읽는다.
FULL_BURST_DURATION_DELTA: dict[str, float] = {
    "isabel": -5.0,     # Sonic Chaser: "Full Burst Time ▼ 5 sec."
    "modernia": 5.0,    # New World:    "Full Burst Duration ▲ 5 sec."
}


def get_full_burst_duration_delta(slug: str) -> float:
    """이 유닛의 버스트가 풀 버스트 창을 몇 초 움직이는가 (대부분 0.0)."""
    return FULL_BURST_DURATION_DELTA.get(slug, 0.0)


# 자기 버스트가 아니라 "덱에 있고 자원 조건이 맞으면" 풀 버스트를 늘리는 유닛.
# FULL_BURST_DURATION_DELTA는 슬러그당 상수라 이 모양을 담을 수 없다 - 소다의
# 확장은 골든칩 스택에 따라 사이클마다 +0/+2/+5초로 달라지고, 원문이
# "entering Burst Stage 3 / Affects all allies"라 그녀가 그 사이클의 Burst 3일
# 필요도 없다.
_CONDITIONAL_FULL_BURST_DELTA_BUILDERS = {
    "soda-twinkling-bunny": lambda sv: build_beginners_rewards_full_burst_delta(sv),
}


def get_conditional_full_burst_delta(slug, skill_values):
    """이 유닛이 자원 조건에 따라 풀 버스트를 늘리는가 (대부분 None)."""
    builder = _CONDITIONAL_FULL_BURST_DELTA_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


# A variant seated in a different burst-rotation slot than the character's
# nominal tier (e.g. Rapi: Red Hood's Combat Assist B1 stand-in).
VARIANT_BURST_TIERS: dict[str, int] = {
    "rapi-red-hood-b1": 1,
}


# A variant whose kit only exists while a state HER DECK has to induce is live,
# mapped to the slugs that can induce it. Bready alone: she enters Lingering
# Taste on "gaining a buff that increases sustained damage" and Recommended
# Taste on one that increases distributed damage (char_bready.json), and BOTH of
# Favorite Candy's bullets plus two thirds of New Flavor are gated on the
# status. A deck holding neither kind of buffer therefore simulates a unit the
# game does not produce - measured on Fienn's deck 5 (2026-08-04) as
# 1,066,561,255 of credited damage she could not deal, 18.7% of that deck.
#
# The other MODE_VARIANTS bases need no entry: Cinderella: Crystal Wave's
# MG/Snipe and Diesel's burst timing are the PLAYER's choice, and Rapi: Red
# Hood's B3/B1 is already constrained by burst-tier legality.
TASTE_INDUCER_SLUGS: dict[str, frozenset[str]] = {
    "bready-lingering": SQUAD_SUSTAINED_DAMAGE_BUFF_SLUGS,
    "bready-recommended": SQUAD_DISTRIBUTED_DAMAGE_BUFF_SLUGS,
}


# A variant whose weapon profile differs from the character's dotgg stats
# (e.g. a Snipe mode) registers a builder here; the roster loader swaps the
# assembled profile in after skill values resolve.
_WEAPON_PROFILE_OVERRIDE_BUILDERS = {
    "cinderella-crystal-wave-snipe": build_snipe_weapon_profile,
}


def get_weapon_profile_override(slug, skill_values, weapon_stats=None):
    """The unit's weapon profile when its own kit replaces or corrects the
    collected one. `weapon_stats` is the profile read from data, so a builder
    can override a single field instead of restating the whole thing."""
    builder = _WEAPON_PROFILE_OVERRIDE_BUILDERS.get(slug)
    if builder is None:
        return None
    return builder(skill_values, weapon_stats)


_PERIODIC_NUKE_BUILDERS = {
    "ada-wong": lambda sv: build_flash_grenade_periodic_nuke(sv),
    "ark-ranger-black": lambda sv: build_ark_ranger_ceiling_collider(sv),
    "cinderella-crystal-wave-mg": lambda sv: crystal_wave_periodic_nuke(sv),
    "cinderella-crystal-wave-snipe": lambda sv: crystal_wave_periodic_nuke(sv),
    "helm-aquamarine": lambda sv: {
        "cooldown": AEGIS_CANNON_SUPPRESSION_FIRE_COOLDOWN,
        "percent": aegis_cannon_suppression_fire_percent(sv),
    },
    "isabel": lambda sv: {
        "cooldown": POINTED_FEATHER_COOLDOWN,
        "percent": pointed_feather_percent(sv),
        # Pointed Feather는 그녀의 스킬 2다 - 아르카나의 The Magician이 깎는 바로
        # 그 쿨다운. 태그가 없는 주기 항목은 스킬 쿨다운을 모델한 것이 아니므로
        # (에이다의 창 내 간격, 스노우 화이트의 자체 주기) 감소를 받지 않는다.
        "cooldown_skill_slot": 2,
    },
    "jill-valentine": lambda sv: build_acid_ammo_periodic_nuke(sv),
    "little-mermaid": lambda sv: build_bubble_wave_fb_nuke(sv),
    "snow-white": lambda sv: snow_white_periodic_nuke(sv),
}

# A Nikke's burst nuke is "attack"-typed unless its skill deals a specific
# damage type (e.g. a "Projectile Explosion" keyword skill). Only overrides are
# listed; everything else defaults to "attack". The instance's type decides
# which type-gated Damage-Up buff applies (see raid_simulator._TYPE_BUCKETS).
# A burst whose PLAIN nuke (the `burst_damage_percents` one) is worded "as
# additional damage" - computed later than cast time, so it can land inside the
# Full Burst window and take the bonus (Fienn, 2026-07-12). Membership is read
# off the collected skill text, and it is deliberately narrow: several units
# have an "as additional damage" bullet that is NOT their plain nuke (Julia's
# max-Crescendo hit, Isabel's Marked Target tiers, Cinderella's Beautiful
# mirror, Helm: Aquamarine's Electric-gated hit) - those are separate
# resource-gated nukes that already carry their own eligibility flag, while the
# plain nuke beside them reads "as damage" / "as Burst Skill damage".
#
# Only a Burst 3 can actually collect it: Burst 1 and 2 cast before
# full_burst_start, so the window test in _damage_instance excludes them on
# timing (Fienn, 2026-07-26).
_BURST_RESOLVES_AFTER_CAST = {
    "liberalio",       # Submerged World: "Deals 925% of final ATK as additional damage."
    "rapi-red-hood",   # Stage 3: "Deals 2808% of final ATK as additional damage."
}

# How many rounds a unit's ONE shot accounts for toward the squad's
# "total ammo expended by allies" counters, as (in Full Burst, outside it).
# Absent = 1 round per shot, the ordinary magazine case.
#
# A skill that "expends N rounds from the ammo pouch" fires one real bullet;
# the N is ammo ACCOUNTING that exists to feed consumption-counting synergies
# (Fienn, 2026-07-19), which is exactly what these counters are. Little
# Mermaid's Bubble Barrage (every 500) and Bubble Order's gauge fill (every
# 400) are the consumers.
_AMMO_ROUNDS_PER_SHOT = {
    # Bullets of Love spends 300 per Full-Charge shot during Full Burst;
    # Sticky Fingers spends 100 per Full-Charge shot outside it. An SR full
    # charge is one shot, so each shot is exactly one proc.
    "velvet": (300.0, 100.0),
    # Snipe mode's full charge "expends 40 rounds" off the same accounting.
    # MG mode is an ordinary magazine and stays at 1.
    "cinderella-crystal-wave-snipe": (40.0, 40.0),
}

_BURST_DAMAGE_TYPES = {
    "phantom": "distributed",  # Rampages of Thieves deals its nuke "as Distributed Damage"
    "phantom-signature": "distributed",
    # The Great Thief: "Deals 1736.31% of final ATK as Distributed Damage" -
    # her whole burst, and the one her own Secure Route Stage-1 buff
    # (+49.58% Distributed Damage) exists to multiply.
    "quency-escape-queen": "distributed",
    # Ninja Overdrive "deals 170% of final ATK as distributed damage", and her
    # own +20% Distributed Damage buff is what it multiplies.
    "delta-ninja-thief": "distributed",
    "rapi-red-hood": "projectile_explosion",  # Power of Inheritance = Projectile Explosion skill
    "ein": "true",  # Feather-All Range deals its nuke "as true damage"
}

# A Nikke whose damage lands on a cadence it computes for itself, rather than a
# fixed interval (see raid_simulator's `scheduled_nukes`). Rare - only summoned
# entities so far.
_SCHEDULED_NUKE_BUILDERS = {
    "anis-star": lambda sv: build_shooting_stars_scheduled_nukes(sv["star_anis"]),  # Shooting Stars, 40 ticks per burst
    "ein": lambda sv: build_ein_scheduled_nukes(sv),
    "elegg-boom-and-shock": lambda sv: build_ghostbuster_scheduled_nukes(sv),  # capture at the ghost cap
    "mihara-bonding-chain": lambda sv: build_mihara_scheduled_nukes(sv),  # chain attacks + Ensnaring DoT
    "milk-blooming-bunny": lambda sv: build_milk_scheduled_nukes(sv),  # Embarrassment entry + Overconfident ticks
    "bready-lingering": lambda sv: build_aftertaste_scheduled_nukes(sv),  # Aftertaste DoT windows
    "diesel-winter-sweets-intro": lambda sv: build_diesel_full_burst_dot(sv),  # per-Full-Burst DoT
    "diesel-winter-sweets-highlight": lambda sv: build_diesel_full_burst_dot(sv),
    "little-mermaid": lambda sv: build_bubble_barrage_scheduled_nukes(sv),  # squad-wide 500-ammo counter
    "raven": lambda sv: build_raven_scheduled_nukes(sv),           # Shock Wave, per Full Charge
    "sakura-bloom-in-summer": lambda sv: build_sakura_scheduled_nukes(sv),  # Sakura Petals
    "rosanna-chic-ocean": lambda sv: build_spina_scheduled_nukes(sv),  # Spina di Rosa, 15 ticks per cast
    "laplace-ultimate-hero": lambda sv: build_laplace_stage_nukes(sv),  # Mjolnir's 934.76% x Over Energy stage
    "nayuta": lambda sv: build_memory_incineration_scheduled_nukes(sv),  # Full Charge in Memory Incineration
    "laplace-signature": lambda sv: laplace_signature.build_buster_scheduled_nukes(sv),  # per-tick true-damage rider
    "rapi-red-hood": lambda sv: build_attachable_projectiles_scheduled_nukes(sv),  # Attachable Projectiles launcher
    "rapi-red-hood-b1": lambda sv: build_attachable_projectiles_scheduled_nukes(
        sv, slug="rapi-red-hood-b1", stage3_requirement_cut=False),
}

# A Nikke whose burst swaps her weapon profile for a window (weapon-mode
# segments - see raid_simulator's `weapon_mode_schedules` and the design spec).
_WEAPON_MODE_SCHEDULE_BUILDERS = {
    # Explosive Round: one true-damage exploding shot per own-burst (Fienn,
    # in-game 2026-08-08 - the text names no duration).
    "eunhwa-tactical-upgrade": lambda sv: build_explosive_round_weapon_mode_schedule(sv),
    "red-hood": lambda sv: build_red_wolf_weapon_mode_schedule(sv),  # Step 3 transform window, 33 measured shots
    "snow-white": lambda sv: build_seven_dwarves_weapon_mode_schedule(sv),  # single 5s-charge cannon shot per own-burst
    "snow-white-heavy-arms": lambda sv: build_fully_active_weapon_mode_schedule(sv),  # 2-shot 3.2s-charge segment per own-burst
    "maxwell": lambda sv: build_pierce_shot_weapon_mode_schedule(sv),  # single 2s-charge cannon shot per own-burst
    # One charged shot per own-burst too, but its charge time is fixed BY the
    # Overcurrent stage, so each segment carries its own profile: 3s at her
    # first burst down to 0.4s from the fifth on.
    "maxwell-ordinary-mechanic": lambda sv: build_matis_uberbuster_weapon_mode_schedule(sv),
    "laplace-signature": lambda sv: laplace_signature.build_buster_weapon_mode_schedule(sv),  # Buster mode, 93 measured ticks
    "milk-blooming-bunny": lambda sv: build_milk_weapon_mode_schedule(sv),  # forced reload: a segment that fires nothing
    "nayuta": lambda sv: build_memory_incineration_weapon_mode_schedule(sv),  # Memory Incineration, 10s
    # Overcharge Formula: one charged Pierce shot per burst (1.5s base, 1.2s with
    # the Favorite Item). Each slug anchors on its own burst times.
    "zwei": lambda sv: build_overcharge_weapon_mode_schedule(sv),
    "zwei-signature": lambda sv: build_overcharge_weapon_mode_schedule(sv, slug="zwei-signature"),
    "laplace": lambda sv: build_buster_weapon_mode_schedule(sv),  # Laplace Buster Normal Damage, 5s ~46 ticks
    "takina-inoue": lambda sv: build_suppression_initiated_weapon_mode_schedule(sv),  # Suppression Initiated, 25 measured true-damage shots
    # Fair and Square: unlimited-ammo SMG at the canonical 20/s. Each slug
    # anchors on its own burst times.
    "moran": lambda sv: build_fair_and_square_weapon_mode_schedule(sv),
    "moran-signature": lambda sv: build_fair_and_square_weapon_mode_schedule(sv, slug="moran-signature"),
    "scarlet-black-shadow": lambda sv: build_scarlet_weapon_mode_schedule(sv),  # Asura's instant magazine reload on Full Burst entry
    "laplace-ultimate-hero": lambda sv: build_laplace_transform_schedule(sv),  # Warm Up transform, magazine-length window at SMG cadence
}

# A Nikke whose burst nuke "attacks sequentially N times" - N separate hits at
# the same instant, not one hit at N*percent (see raid_simulator's
# burst_hit_counts). Only overrides are listed; everything else defaults to 1.
_BURST_HIT_COUNTS = {
    "julia-signature": julia_signature.CLIMAX_HIT_COUNT,
    "cinderella": GLASS_SLIPPERS_HIT_COUNT,
    "sakura-bloom-in-summer": EPHEMERAL_SPENDER_HIT_COUNT,
    "eve": COUNTER_CHAIN_HIT_COUNT,
}

# A Nikke with a Skill 1/2 on its own cooldown (fires at t=cooldown, 2*cooldown,
# ... applying buffs/debuffs) - see raid_simulator's `periodic_rules`. Kept
# separate from _BUILDERS (event-triggered rules) and _PERIODIC_NUKE_BUILDERS.
_PERIODIC_RULE_BUILDERS = {
    # Her Full Charge hits keep cutting Field Discussion's cooldown, so the
    # cycle it fires on is shorter than the listed 9 sec.
    "centi-signature": lambda sv: [
        (
            centi.field_discussion_effective_cooldown(sv),
            centi.build_field_discussion_periodic_rules(sv),
        ),
    ],
    "dolla": lambda sv: [
        (
            ENTREPRENEURSHIP_COOLDOWN,
            build_entrepreneurship_periodic_rules(sv["entrepreneurship"]),
        ),
    ],
    # Two entries, 30s and 10s, mutually excluded by whether Eunhwa is in the
    # deck - an entry's cooldown is fixed at build time, so a deck-dependent
    # interval needs one entry per possibility.
    "emma-tactical-upgrade": lambda sv: build_environment_setup_periodic_rules(sv),
    "sakura-bloom-in-summer": lambda sv: build_sakura_periodic_rules(sv),
    "rosanna-chic-ocean": lambda sv: build_spina_periodic_rules(sv),  # Spina di Rosa, cd 30
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
    "ark-ranger-black": lambda sv: build_ark_ranger_per_shot_rules(sv),
    "crown": lambda sv: build_royal_attire_per_shot_rules(sv["royal_attire"]),  # Royal Attire, 860 normals
    "bready-lingering": lambda sv: build_lingering_per_shot_rules(sv),
    "bready-recommended": lambda sv: build_recommended_per_shot_rules(sv),
    "dorothy-serendipity": lambda sv: build_flash_per_shot_rules(sv),  # Flash, 80 pellets
    "jill-valentine": lambda sv: build_magnum_per_shot_rules(sv),
    "anis-star": lambda sv: build_starfall_full_charge_nuke_rules(sv["starfall"]),
    "asuka-shikinami-langley-wille": lambda sv: build_anti_at_field_per_shot_rules(sv),
    "cinderella": lambda sv: build_flawless_glass_per_shot_rules(sv),
    # Camouflage re-armed by every Full Charge inside Full Burst.
    "eunhwa-tactical-upgrade": lambda sv: build_camouflage_per_shot_rules(sv["camouflage_scarf"]),
    "modernia": lambda sv: build_modernia_per_shot_rules(sv),
    "naga": lambda sv: build_support_of_friendship_per_shot_rules(sv["support_of_friendship"]),
    "ein": lambda sv: build_ein_per_shot_rules(sv),
    "eve": lambda sv: build_unstable_energy_per_shot_rules(sv),
    "anis-sparkling-summer": lambda sv: build_sparkling_missile_per_shot_rules(sv["sparkling_missile"]),
    "grave": lambda sv: build_overheat_per_shot_rules(sv),
    "rei-ayanami": lambda sv: build_preemptive_subdual_per_shot_rules(sv),
    "rei-ayanami-tentative-name": lambda sv: build_annihilation_support_per_shot_rules(sv),
    "neon-vision-eye": lambda sv: build_firepower_explosion_per_shot_rules(sv),
    "drake": lambda sv: build_thunderbolt_per_shot_rules(sv),
    "drake-signature": lambda sv: build_thunderbolt_signature_per_shot_rules(sv),
    "julia-signature": lambda sv: julia_signature.build_marcato_per_shot_rules(sv),
    "phantom": lambda sv: phantom.build_phantom_per_shot_rules(sv),
    "phantom-signature": lambda sv: phantom_signature.build_phantom_signature_per_shot_rules(sv),
    "rosanna": lambda sv: rosanna_base.build_rosanna_base_per_shot_rules(sv),
    "rosanna-signature": lambda sv: rosanna_signature.build_rosanna_signature_per_shot_rules(sv),
    "laplace": lambda sv: build_hero_bomber_per_shot_rules(sv),
    "laplace-signature": lambda sv: laplace_signature.build_hero_bomber_signature_per_shot_rules(sv),
    "scarlet-black-shadow": lambda sv: build_breakthrough_per_shot_rules(sv),
    "snow-white": lambda sv: build_determination_per_shot_rules(sv),
    "snow-white-heavy-arms": lambda sv: build_seven_dwarves_per_shot_rules(sv),
    "soda-twinkling-bunny": lambda sv: (
        build_lucky_golden_chip_per_shot_rules(sv)
        + build_beginners_rewards_per_shot_rules(sv)
    ),
    "velvet": lambda sv: build_velvet_per_shot_rules(sv),
    "brid-silent-track": lambda sv: build_journey_ahead_rules(sv["journey_ahead"]),
    "helm-aquamarine": lambda sv: build_admire_accompaniment_per_shot_rules(sv["admire_accompaniment"]),
    "marciana-marine-study": lambda sv: build_marciana_per_shot_rules(sv),
    # Base Helm keeps only the last-bullet crit rate; the full-charge nuke is
    # text the Favorite Item adds.
    "helm": lambda sv: build_frontline_command_per_shot_rules(sv["frontline_command"]),
    "helm-signature": lambda sv: (
        build_frontline_command_per_shot_rules(sv["frontline_command"])
        + build_fire_away_per_shot_rules(sv["fire_away"])
    ),
    "moran": lambda sv: build_bring_it_on_per_shot_rules(sv),
    "moran-signature": lambda sv: build_bring_it_on_per_shot_rules(sv),
    "privaty": lambda sv: build_ld_assault_base_per_shot_rules(sv),
    "privaty-signature": lambda sv: build_ld_assault_per_shot_rules(sv),
    "zwei-signature": lambda sv: build_pierce_equation_per_shot_rules(sv),
    "d-killer-wife": lambda sv: build_assault_formation_rules(sv["assault_formation"]),
    "liberalio": lambda sv: build_liberalio_per_shot_rules(sv),
    "ludmilla-winter-owner": lambda sv: build_ludmilla_per_shot_rules(sv),
    "chisato-nishikigi": lambda sv: build_chisato_per_shot_rules(sv),
    "maiden-ice-rose": lambda sv: (build_blessings_upon_you_per_shot_rules(sv)
                                   + build_meditation_per_shot_rules(sv, sv["caster_max_hp"])),
    "miranda": lambda sv: build_health_up_hit_rate_rules(sv["health_up"]),
    "miranda-signature": lambda sv: build_health_up_rules(sv["health_up"]),
    "mint": lambda sv: build_here_i_go_rules({**sv["here_i_go"], "caster_atk": sv["caster_atk"]}),
    "rouge": lambda sv: (build_coin_flip_per_shot_rules(sv["coin_flip"])
                         + build_card_throw_per_shot_rules(sv["card_throw"], sv["caster_max_hp"])),
    "prika": lambda sv: build_lets_get_show_started_rules(
        {**sv["lets_get_the_show_started"], "caster_atk": sv["caster_atk"]}
    ),
}


# A Nikke with a quantity-based resource (battery / ammo pouch / N-stack counter)
# that fills deterministically and drives count-scaled buffs - see
# raid_simulator's `resource_specs` param and effects.ResourceSpec. Each entry
# returns a list of ResourceSpec.
_RESOURCE_SPEC_BUILDERS = {
    "arcana-fortune-mate": lambda sv: build_memories_and_moments_resources(sv),
    "asuka-shikinami-langley-wille": lambda sv: build_anti_at_field_resources(sv),
    "julia": lambda sv: build_crescendo_resources(sv),
    "julia-signature": lambda sv: julia_signature.build_crescendo_signature_resources(sv),
    "leona": lambda sv: build_leona_resources(sv),
    "modernia": lambda sv: build_modernia_resources(sv),
    "guillotine-winter-slayer": lambda sv: build_guillotine_resources(sv),
    "cinderella": lambda sv: build_beautiful_resources(sv),
    "soda-twinkling-bunny": lambda sv: build_golden_chip_resources(sv),
    "maiden-ice-rose": lambda sv: build_mp_resources(sv),
    "elegg-boom-and-shock": lambda sv: build_elegg_ghost_resources(sv),
    "mihara-bonding-chain": lambda sv: build_ensnaring_chain_resources(sv),
    "diesel-winter-sweets-intro": lambda sv: build_diesel_resource_specs(sv),
    "diesel-winter-sweets-highlight": lambda sv: build_diesel_resource_specs(sv),
    "zwei-signature": lambda sv: build_frame_analysis_resources(sv),
}

# A Nikke with a burst-fired nuke whose magnitude is gated/scaled by a named
# resource's count (e.g. a "mirrors the stack count" additional hit, or a
# Hero-Level-scaled DoT) - see raid_simulator's `resource_scaled_nukes` param.
# Each entry returns a list of spec dicts: {"resource", "cap", "base_percent",
# "scale_fn", "tick_count", "tick_interval", "lifetime"(optional),
# "damage_type"(optional)}.
_RESOURCE_SCALED_NUKE_BUILDERS = {
    "ark-ranger-black": lambda sv: build_ark_ranger_dots(sv),
    "cinderella": lambda sv: build_glass_slippers_resource_scaled_nuke(sv),
    "diesel-winter-sweets-intro": lambda sv: build_diesel_burst_dot(sv),
    "diesel-winter-sweets-highlight": lambda sv: build_diesel_burst_dot(sv),
    "guillotine-winter-slayer": lambda sv: build_guillotine_resource_scaled_nukes(sv),
    "julia": lambda sv: build_climax_resource_scaled_nuke(sv),
    "julia-signature": lambda sv: julia_signature.build_climax_signature_resource_scaled_nuke(sv),
    "mana": lambda sv: build_fatal_error_dot(sv),
    "mihara-bonding-chain": lambda sv: build_dragging_chain_resource_scaled_nukes(sv),
    "sakura-bloom-in-summer": lambda sv: build_sakura_resource_scaled_nukes(sv),
}

# A Nikke with a BUFF gated/scaled by a named resource's count, read at the
# owner's own burst times by default - see raid_simulator's
# `resource_gated_buffs` param. Each entry returns a list of spec dicts:
# {"resource", "cap", "use_pre_reset"(optional), "lifetime"(optional),
# "gate_fn"+"value" OR "value_per_stack", "scope" OR "member_filter",
# "at"(optional, "full_burst_end"), "stat", "duration"}.
_RESOURCE_GATED_BUFF_BUILDERS = {
    "arcana-fortune-mate": lambda sv: build_keepsake_album_resource_gated_buffs(sv),
    "leona": lambda sv: build_lions_heart_resource_gated_buffs(sv),
    "soda-twinkling-bunny": lambda sv: build_onward_soda_resource_gated_buffs(sv),
}

# A Nikke with a buff triggered by a named resource's FILL events, landing on
# a live-filtered member subset - see raid_simulator's
# `resource_fill_triggered_buffs` param (gap #8). Each entry returns a list of
# spec dicts: {"resource", "member_filter"(member, owner_slug) -> bool,
# "buffs": [(stat, value, duration)], "condition"(optional)}.
_RESOURCE_FILL_TRIGGERED_BUFF_BUILDERS = {
    "maiden-ice-rose": lambda sv: build_blessings_fill_triggered_buffs(sv),
}

# A Nikke with a burst-fired nuke whose HIT COUNT (not just its percent) is
# itself a resource's value at burst time - see raid_simulator's
# `dynamic_hit_count_nukes` param. Each entry returns a list of spec dicts:
# {"resource", "base_percent", "extra_flat_atk_percent_of_max_hp"(optional),
# "damage_type"(optional)}.
_DYNAMIC_HIT_COUNT_NUKE_BUILDERS = {
    "maiden-ice-rose": lambda sv: build_diamond_dust_dynamic_hit_count_nukes(sv),
    "asuka-shikinami-langley-wille": lambda sv: build_annihilation_dynamic_hit_count_nukes(sv),
    "elegg-boom-and-shock": lambda sv: build_thirteen_ghosts_dynamic_hit_count_nukes(sv),
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


# Seconds a unit pauses between firing a charged shot and starting the next
# charge. It is a property of the UNIT: Liberalio is a Sniper Rifle with no gap
# at all, and handing the delay to every charge weapon drops Scarlet: Black
# Shadow from 0.981x of her recorded damage to 0.559x (2026-07-28).
#
# Fienn times these off the Full Burst clock, reading when the charged bullet
# leaves against when the next charge gauge starts filling - deliberately NOT
# the gap between damage numbers, which an RL grenade's travel time distorts
# with distance. Each timing also checks itself: the shot-to-shot gap must come
# out as charge time + delay.
TIMED_CHARGE_MOTION_DELAY = {
    "snow-white-heavy-arms": CHARGE_MOTION_DELAY_SECONDS,   # 0.4
    "anchor-innocent-maid": 0.4,
    "mint": 0.39,                # 0.39 / 0.40 / 0.39, shot gaps 1.40
    "ade-agent-bunny": 0.35,
    "prika": 0.34,               # 0.36 / 0.34 / 0.33, shot gaps 1.36 / 1.35
    # The two sword-swinging "Rocket Launchers". Their data-file charge times
    # were long suspected wrong because the whole interval measured 2-3x longer;
    # timing the pause instead vindicates the files, because interval - delay
    # lands back on the listed charge (Scarlet 0.7325 - 0.43 = 0.3025 vs 0.30;
    # Raven 2.0275 - 1.014 = 1.0135 vs 1.0). It is the melee animation, not the
    # charge, that makes them slow.
    "scarlet-black-shadow": 0.43,   # 0.44 / 0.42 / 0.44 / 0.42 / 0.43
    "raven": 1.014,                 # 1.02 / 0.99 / 1.02 / 1.02 / 1.02
    # Timed 2026-07-29 off the Full Burst clock. Their shot gaps (1.380 / 1.393)
    # minus the delay return the measured charge (0.987 / 0.997), so the reading
    # checks the interval = charge + delay model, not just the number.
    "helm": 0.4,                    # 0.39 / 0.40 / 0.39 / 0.40 / 0.40
    "helm-signature": 0.4,
    "velvet": 0.4,                  # 0.40 / 0.40 / 0.40 / 0.39 / 0.40
    # Bready is read off raw video frame numbers instead of the Full Burst
    # clock, which shows 0.01 sec steps and skips 0.04 in places - too coarse to
    # tell 22 frames from 24. Her pause is 22 frames across 49 readings, and it
    # checks against her charge (57 frames) and shot gap (78.9696 +- 0.0319
    # frames) to 0.042 of a frame. Written as a frame count because that is the
    # grid the measurement resolved - docs/measurements/bready-charge.md.
    "bready-lingering": 22 / 60,    # 0.36667
    "bready-recommended": 22 / 60,
    # Centi lands on the same 22 frames (Fienn, 2026-07-30). Both builds share
    # one weapon, so both slugs share the pause.
    "centi": centi.CHARGE_MOTION_DELAY,
    "centi-signature": centi.CHARGE_MOTION_DELAY,
    # Cinderella's was measured before this table existed and was filed as
    # something else: `attack_rate.CHARGE_INTERVAL_FLOOR_SECONDS` (10/29 sec) is
    # what remained of her cadence once Flawless Glass's +100% Charge Speed took
    # her 1.0-sec charge to zero, i.e. 29 shots in 10 sec with no reload. What
    # remains when the charge vanishes IS the pause, so it is her timing, not a
    # generic floor - snow_white_heavy_arms.py's docstring reaches the same
    # reading independently. Naming it here also stops the double count:
    # `shot_interval_with_speed` applies the floor only to a unit with no
    # delay of her own.
    "cinderella": CHARGE_INTERVAL_FLOOR_SECONDS,   # 0.34483
}

# Charge weapons Fienn has checked and found NO pause on. The engine's default
# is already 0, so these change no number - they exist because "0" otherwise
# cannot be told apart from "nobody looked", and an unchecked unit is a silent
# over-estimate (Mint read 1.502x of her record until hers was timed).
# `scripts/audit_charge_motion_delay.py` reads both tables to report which
# encoded charge weapons still have no answer.
NO_CHARGE_MOTION_DELAY = frozenset({
    "liberalio",
    "neon-vision-eye",
    "laplace-ultimate-hero",
    "anis-star",
})

# What an untimed charge weapon carries until someone puts a clock on her.
#
# Zero is NOT the neutral choice. It models her as the fastest possible version
# of herself, and a pause is the common case: of the 18 units checked so far 14
# have one. Mint read 1.502x of her recorded damage on exactly this assumption.
#
# 22 frames is the value the two FRAME-NUMBER readings agree on - Bready (SR,
# 49 readings, checked against her charge and shot gap to 0.042 of a frame) and
# Centi (RL). Those two are the best-resolved measurements in the table and they
# span both charge weapon classes, which is why the stand-in comes from them
# rather than from the Full-Burst-clock readings, whose 0.01-sec display skips
# 0.04 in places (docs/measurements/bready-charge.md).
#
# This is a STAND-IN, not an answer: the real values run 0.34 to 0.43 and four
# units have none at all, so every slug below is still a question for Fienn and
# `scripts/audit_charge_motion_delay.py` keeps asking.
ASSUMED_CHARGE_MOTION_DELAY_SECONDS = 22 / 60

_ASSUMED_CHARGE_MOTION_DELAY = frozenset({
    "ada-wong",
    "arcana",
    "d-killer-wife",
    "diesel-winter-sweets-highlight",
    "diesel-winter-sweets-intro",
    "dolla",
    "ein",
    "eunhwa-tactical-upgrade",
    "laplace",
    "laplace-signature",
    "maiden-ice-rose",
    "maxwell",
    "maxwell-ordinary-mechanic",
    "milk-blooming-bunny",
    "red-hood",
    "rouge",
    "takina-inoue",
})

_CHARGE_MOTION_DELAY = {
    **{slug: ASSUMED_CHARGE_MOTION_DELAY_SECONDS for slug in _ASSUMED_CHARGE_MOTION_DELAY},
    # A measured answer always wins over the stand-in, including a measured zero.
    **TIMED_CHARGE_MOTION_DELAY,
    **{slug: 0.0 for slug in NO_CHARGE_MOTION_DELAY},
}


def get_charge_motion_delay(slug):
    """Seconds this Nikke waits between a charged shot and the next charge; 0
    for the vast majority - see `_CHARGE_MOTION_DELAY`."""
    return _CHARGE_MOTION_DELAY.get(slug, 0.0)


# Nikkes who refill a magazine in several loads instead of one. The count comes
# from ShiftyPad's `shot_detail.reload_bullet` (see
# shiftypad_normalize.clip_reload_splits) and is written here rather than read
# live because every data/ directory is gitignored: a checkout without the raw
# bundles would silently fall back to a single reload, which reads as an 11%
# faster cadence rather than as missing data. `scripts/audit_weapon_data.py`
# compares this table against the bundles whenever they ARE present.
#
# Not only launchers and shotguns - Grave is an AR that reloads in halves.
CLIP_RELOAD_SPLITS = {
    "centi": 3,                  # RL, 6 rounds two at a time
    "centi-signature": 3,
    "drake": 3,                  # SG, 9 rounds three at a time
    "drake-signature": 3,
    "sugar": 3,
    "sugar-signature": 3,
    "noir": 3,
    "soda-twinkling-bunny": 3,
    "grave": 2,                  # AR, 60 rounds in halves
}


def get_clip_reload_splits(slug):
    """How many loads this Nikke needs to refill her magazine; 1 for nearly
    everyone - see `CLIP_RELOAD_SPLITS`."""
    return CLIP_RELOAD_SPLITS.get(slug, 1)


def get_burst_resolves_after_cast(slug):
    """Whether this Nikke's burst nuke resolves a beat AFTER the cast rather
    than at it - see `_BURST_RESOLVES_AFTER_CAST`. False for the vast majority,
    whose burst damage is dealt at cast time. For a Burst 3 the difference is
    exactly whether the hit lands inside its own Full Burst window, which is
    what decides the bonus; the engine reads that off the recorded time."""
    return slug in _BURST_RESOLVES_AFTER_CAST


def get_ammo_rounds_per_shot(slug):
    """(rounds in Full Burst, rounds outside) that one of this Nikke's shots
    accounts for toward squad ammo-expended counters - see
    `_AMMO_ROUNDS_PER_SHOT`. (1.0, 1.0) for everyone with a plain magazine."""
    return _AMMO_ROUNDS_PER_SHOT.get(slug, (1.0, 1.0))


# A Nikke whose own skill reloads rounds back into her magazine mid-fight, as
# (builder, the boss element it needs or None). Distinct from the Tactical Bear
# cube's refund, which its wearer gets against any boss and which stacks with
# this one - a unit can hold both.
_SKILL_AMMO_REFUNDS = {
    # Eagle Eye-Type Exospine: "when landing 10 normal attack(s) on an Electric
    # Code target, Reloads 3 round(s)".
    "eve": (eagle_eye_ammo_refund, "Electric"),
    # The Queen's Gaze: "when landing 60 normal attack(s), Reloads 20 round(s)
    # of ammunition" - no boss condition on this one.
    "ludmilla-winter-owner": (queens_gaze_ammo_refund, None),
}


def get_skill_ammo_refund(slug, skill_values):
    """(AmmoRefund, required boss element or None) for a Nikke whose own skill
    hands rounds back, else None - see `_SKILL_AMMO_REFUNDS`. The element is
    returned rather than applied because the roster assembles a deck, not an
    encounter; the simulator holds the boss and resolves the gate."""
    entry = _SKILL_AMMO_REFUNDS.get(slug)
    if entry is None:
        return None
    builder, required_element = entry
    return builder(skill_values), required_element


def get_periodic_nuke(slug, skill_values):
    """{"cooldown": seconds, "percent": float} for a Nikke with a skill that
    fires repeatedly on its own fixed cooldown (see raid_simulator's
    `periodic_nukes` param), or None for the vast majority of Nikkes without
    one."""
    builder = _PERIODIC_NUKE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_scheduled_nukes(slug, skill_values):
    """List of specs for a Nikke whose damage lands on a self-computed schedule
    (see raid_simulator's `scheduled_nukes`), or None for Nikkes without one."""
    builder = _SCHEDULED_NUKE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_weapon_mode_schedules(slug, skill_values):
    """Schedule function for a Nikke whose burst swaps her weapon profile for a
    window (see raid_simulator's `weapon_mode_schedules`), or None for Nikkes
    without one."""
    builder = _WEAPON_MODE_SCHEDULE_BUILDERS.get(slug)
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
    for Nikkes without one. `mode` is "after" (once at the Nth shot), "every"
    (at every Nth shot), or "accumulate", whose `threshold` is instead
    `(limit, increment_at)` - a per-shot quantity the unit computes, fired when
    the running total crosses `limit` (Dorothy: Serendipity's 80 pellets)."""
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


def get_resource_fill_triggered_buffs(slug, skill_values):
    """List of resource-fill-triggered-buff spec dicts for a Nikke with a buff
    fired at a named resource's FILL events (see raid_simulator's
    `resource_fill_triggered_buffs` param, gap #8), or None for the vast
    majority without one."""
    builder = _RESOURCE_FILL_TRIGGERED_BUFF_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


def get_dynamic_hit_count_nukes(slug, skill_values):
    """List of dynamic-hit-count-nuke spec dicts for a Nikke with a burst-fired
    nuke whose HIT COUNT is itself a resource's value (see raid_simulator's
    `dynamic_hit_count_nukes` param), or None for the vast majority without
    one."""
    builder = _DYNAMIC_HIT_COUNT_NUKE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None


import importlib
import pkgutil
from collections import defaultdict

import app.skill_rules as _skill_rules_package

_skill_value_manifest_cache = None


def get_skill_value_manifest(slug):
    """The colocated SKILL_VALUE_MANIFESTS entry for `slug`, or None. A module
    without a manifest is simply not loadable from user data (excluded +
    reported, same as a non-encoded slug) - see user_roster.load_nikke_spec."""
    global _skill_value_manifest_cache
    if _skill_value_manifest_cache is None:
        merged = {}
        for info in pkgutil.iter_modules(_skill_rules_package.__path__):
            if info.name.startswith("_"):
                continue
            module = importlib.import_module(f"app.skill_rules.{info.name}")
            merged.update(getattr(module, "SKILL_VALUE_MANIFESTS", {}))
        _skill_value_manifest_cache = merged
    return _skill_value_manifest_cache.get(slug)


_character_map_cache = None


def character_map():
    """Slug -> the one OWNED CHARACTER whose build it is, for every slug whose
    character has more than one encoded build.

    This is the IDENTITY table: it answers "may these two hold a seat at the
    same time", and the answer is no for two builds of one character, since the
    player owns her once. A character with a single build is absent because
    `.get(slug, slug)` already names her.

    It is NOT MODE_VARIANTS, which answers the separate question of what the
    engine may CHOOSE between. A Favorite Item build belongs here and must never
    be fanned out: owning the item is a fact about the player, not a choice the
    search gets to make for them.

    Identity comes from the manifest's `data_slug`, which already names the
    character a build's data is collected from; test_character_map pins the
    grouping so a data-sourcing change cannot redraw it silently.

    Built on first use, not at import: resolving the manifests walks every
    module in this package, which includes this one.
    """
    global _character_map_cache
    if _character_map_cache is None:
        by_character = defaultdict(list)
        for slug in ENCODED_SLUGS:
            manifest = get_skill_value_manifest(slug) or {}
            by_character[manifest.get("data_slug", slug)].append(slug)
        _character_map_cache = {
            slug: character
            for character, slugs in by_character.items() if len(slugs) > 1
            for slug in slugs
        }
    return _character_map_cache
