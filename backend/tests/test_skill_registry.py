import pytest

from app.skill_rules.registry import (
    ENCODED_SLUGS,
    build_nikke_rules,
    get_burst_damage_type,
    get_burst_resolves_after_cast,
    get_burst_hit_count,
    get_clip_reload_splits,
    get_full_burst_duration_delta,
    get_per_shot_rules,
    get_periodic_nuke,
    get_periodic_rules,
)

TAKINA_SKILL_VALUES = {
    "combat_support": {
        "description_value_01": "80.04", "description_value_02": "5",
        "description_value_03": "35.05", "description_value_04": "15",
    },
    "battlefield_control": {
        "description_value_01": "10.09", "description_value_02": "5",
        "description_value_03": "140.49", "description_value_04": "10",
    },
    "suppression_initiated": {
        "description_value_01": "200.64", "description_value_02": "10",
        "description_value_03": "6.04", "description_value_04": "5",
    },
}


def test_core_encoded_nikkes_are_registered():
    assert {"anis-star", "crown", "rapi-red-hood", "helm", "privaty"} <= set(ENCODED_SLUGS)
    assert {"liter", "volume", "miranda"} <= set(ENCODED_SLUGS)


def test_build_returns_rules_and_burst_percent_for_an_attacker():
    # Helm: pass her skill values; expect combat rules plus a burst nuke %.
    skill_values = {
        "frontline_command": {"description_value_01": "14.64", "description_value_02": "5"},
        "fire_away": {"description_value_01": "3.08", "description_value_02": "27.87", "description_value_03": "10", "description_value_04": "178.98"},
        "aegis_cannon": {"description_value_01": "8236.8", "description_value_04": "158.4", "description_value_05": "10"},
    }
    rules, burst_percent = build_nikke_rules("helm", skill_values)
    assert len(rules) > 0
    assert burst_percent == 8236.8


def test_build_returns_none_burst_percent_for_a_pure_support():
    # Crown deals no burst nuke - her burst is buffs only.
    skill_values = {
        "one_for_all": {
            "description_value_01": "64.51", "description_value_02": "15", "description_value_03": "44.35",
            "description_value_04": "15", "description_value_05": "37.44", "description_value_06": "15",
            "description_value_07": "44.35", "description_value_08": "15",
        },
        "royal_attire": {
            "description_value_01": "43", "description_value_02": "4.06",
            "description_value_03": "20", "description_value_04": "5",
            "description_value_05": "5", "description_value_06": "5.23",
            "description_value_07": "20.99", "description_value_08": "7",
        },
        "last_kingdom": {
            "description_value_01": "36.24", "description_value_02": "15",
            "description_value_03": "10.45", "description_value_04": "15",
        },
        "caster_atk": 281952,
        "caster_def": 66196,
        "caster_max_hp": 11621606,
    }
    rules, burst_percent = build_nikke_rules("crown", skill_values)
    assert len(rules) > 0
    assert burst_percent is None


def test_unregistered_slug_raises():
    with pytest.raises(KeyError):
        build_nikke_rules("some-unencoded-nikke", {})


def test_get_periodic_nuke_returns_none_for_most_nikkes():
    assert get_periodic_nuke("crown", {}) is None


def test_get_periodic_nuke_returns_cooldown_and_percent_for_helm_aquamarine():
    skill_values = {
        "admire_accompaniment": {
            "description_value_01": "131.34", "description_value_02": "1.82",
            "description_value_03": "2.2", "description_value_04": "2.6",
        },
        "aegis_cannon_suppression_fire": {
            "description_value_01": "105.58", "description_value_02": "5.64",
            "description_value_03": "5", "description_value_04": "5",
        },
    }
    spec = get_periodic_nuke("helm-aquamarine", skill_values)
    assert spec == {"cooldown": 4.0, "percent": 105.58}


def test_get_periodic_nuke_tags_isabel_pointed_feather_as_her_skill_2():
    # The tag is what lets Arcana's The Magician (a skill_cooldown_reduction_percent
    # buff) reach this periodic nuke's interval - untagged periodic entries
    # (Ada Wong's in-window interval, Snow White's own cadence) must not collect it.
    skill_values = {"pointed_feather": {"description_value_02": "170.58"}}
    spec = get_periodic_nuke("isabel", skill_values)
    assert spec["cooldown_skill_slot"] == 2


def test_get_burst_damage_type_defaults_to_attack():
    assert get_burst_damage_type("crown") == "attack"
    assert get_burst_damage_type("helm") == "attack"


def test_rapi_red_hood_burst_nuke_is_projectile_explosion_typed():
    # Power of Inheritance is a "Projectile Explosion" keyword skill, so its
    # burst-nuke instance benefits from Projectile Explosion Damage buffs.
    assert get_burst_damage_type("rapi-red-hood") == "projectile_explosion"


def test_a_burst_nuke_worded_as_additional_damage_takes_the_full_burst_bonus():
    # Fienn's rule (2026-07-12): a burst skill whose damage is described "as
    # additional damage" is computed later than cast time, so it can land
    # inside the Full Burst window and take the bonus. Liberalio's Submerged
    # World and Red Hood's Stage 3 are the two whose PLAIN burst nuke is
    # worded that way.
    assert get_burst_resolves_after_cast("liberalio") is True
    assert get_burst_resolves_after_cast("rapi-red-hood") is True


def test_a_burst_nuke_worded_as_plain_damage_does_not_take_the_bonus():
    # These units DO have an "as additional damage" bullet, but it is a
    # separate resource-gated nuke that carries its own eligibility flag -
    # their plain burst percent is the "as damage" / "as Burst Skill damage"
    # bullet, which is cast-time damage.
    assert get_burst_resolves_after_cast("rosanna") is False       # "as damage"
    assert get_burst_resolves_after_cast("isabel") is False        # "as Burst Skill damage"
    assert get_burst_resolves_after_cast("helm-aquamarine") is False
    assert get_burst_resolves_after_cast("crown") is False         # no burst nuke at all


QUENCY_EXPLORE_ROUTE = {
    "description_value_01": "2", "description_value_02": "1",
    "description_value_03": "1.36", "description_value_04": "10", "description_value_05": "2",
    "description_value_06": "2.45", "description_value_07": "10", "description_value_08": "2",
    "description_value_09": "2", "description_value_10": "1",
    "description_value_11": "2.71", "description_value_12": "10", "description_value_13": "1",
    "description_value_14": "4.9", "description_value_15": "10", "description_value_16": "1",
    "description_value_17": "3", "description_value_18": "2",
    "description_value_19": "4.08", "description_value_20": "5", "description_value_21": "0.5",
    "description_value_22": "7.36", "description_value_23": "5", "description_value_24": "0.5",
}


def test_build_nikke_rules_returns_the_great_thief_burst_percent_for_quency():
    skill_values = {
        "secure_route": {"description_value_01": "49.58", "description_value_02": "25.25", "description_value_03": "16.73"},
        # Explore Route: her ATK / Hit Rate steady states are summed from these
        # per-stage (value, cap) pairs, so the builder needs the whole skill.
        "explore_route": QUENCY_EXPLORE_ROUTE,
        "the_great_thief": {
            "description_value_01": "57.08", "description_value_02": "10",
            "description_value_03": "25.87", "description_value_04": "10",
            "description_value_05": "1736.31",
        },
    }
    rules, burst_percent = build_nikke_rules("quency-escape-queen", skill_values)
    assert len(rules) == 2
    assert burst_percent == 1736.31


def test_get_periodic_rules_returns_none_for_most_nikkes():
    assert get_periodic_rules("crown", {}) is None


def test_get_periodic_rules_returns_battlefield_control_for_takina():
    result = get_periodic_rules("takina-inoue", TAKINA_SKILL_VALUES)
    assert result is not None and len(result) == 1
    cooldown, rules = result[0]
    assert cooldown == 15.0
    assert all(r.trigger == "periodic" for r in rules)


def test_get_periodic_rules_returns_decrescendo_for_julia():
    result = get_periodic_rules("julia", {"decrescendo": {"description_value_01": "26.04", "description_value_02": "10"}})
    assert result is not None and len(result) == 1
    cooldown, rules = result[0]
    assert cooldown == 20.0
    assert all(r.trigger == "periodic" for r in rules)


def test_build_nikke_rules_returns_climax_burst_percent_for_julia():
    rules, burst_percent = build_nikke_rules("julia", {"climax": {"description_value_02": "544.5"}})
    assert rules == []
    assert burst_percent == 544.5


JULIA_SIGNATURE_SKILL_VALUES = {
    "decrescendo": {
        "description_value_01": "26.04", "description_value_02": "10",
        "description_value_03": "20", "description_value_04": "10",
        "description_value_05": "36.16", "description_value_06": "10",
    },
    "climax": {"description_value_01": "544.5", "description_value_02": "5", "description_value_03": "544.5"},
}


def test_get_periodic_rules_returns_decrescendo_for_julia_signature():
    result = get_periodic_rules("julia-signature", JULIA_SIGNATURE_SKILL_VALUES)
    assert result is not None and len(result) == 1
    cooldown, rules = result[0]
    assert cooldown == 20.0
    assert all(r.trigger == "periodic" for r in rules)


def test_build_nikke_rules_returns_battle_start_decrescendo_and_climax_for_julia_signature():
    rules, burst_percent = build_nikke_rules("julia-signature", JULIA_SIGNATURE_SKILL_VALUES)
    assert len(rules) == 1 and rules[0].trigger == "battle_start"
    assert burst_percent == 544.5


def test_get_burst_hit_count_defaults_to_one_and_is_five_for_julia_signature():
    assert get_burst_hit_count("julia") == 1
    assert get_burst_hit_count("julia-signature") == 5


def test_get_per_shot_rules_returns_none_for_most_nikkes():
    # Crown gained one with Royal Attire, so this uses a Nikke that has none.
    assert get_per_shot_rules("liter", {}) is None


def test_get_per_shot_rules_returns_journey_ahead_for_brid():
    result = get_per_shot_rules("brid-silent-track", {
        "journey_ahead": {"description_value_01": "12.12", "description_value_02": "10", "description_value_03": "675"},
    })
    # Two per-shot entries: the 675% nuke every 5 normals, and the Wind-Code
    # Damage Taken debuff every 10 normals.
    assert result is not None and len(result) == 2
    modes = {(threshold, mode) for threshold, mode, _ in result}
    assert modes == {(5, "every"), (10, "every")}
    assert all(r.trigger == "per_shot" for _, _, rules in result for r in rules)


MIRANDA_HEALTH_UP = {
    "description_value_01": "30", "description_value_02": "5.44", "description_value_03": "5",
    "description_value_04": "30", "description_value_05": "3.79", "description_value_06": "5",
}


def test_get_per_shot_rules_returns_health_up_for_mirandas_favorite_item():
    result = get_per_shot_rules("miranda-signature", {
        "health_up": dict(MIRANDA_HEALTH_UP,
                          description_value_07="30", description_value_08="50.06",
                          description_value_09="5"),
    })
    # The two Hit Rate steps both builds share, then the self ATK step only the
    # Favorite Item's text carries.
    assert result is not None and len(result) == 2
    assert all((threshold, mode) == (30, "every") for threshold, mode, _ in result)
    assert all(r.trigger == "per_shot" for _, _, rules in result for r in rules)


def test_base_miranda_has_health_ups_hit_rate_steps_and_nothing_else():
    # Both of Health Up!'s base-build steps are Hit Rate, which the damage model
    # consumes since 2026-08-07 (accuracy.core_hit_rate) - so the base build has
    # per-shot rules now, but only those two. The self ATK step that the Favorite
    # Item adds lives in slots 07-09, which the base array does not have.
    result = get_per_shot_rules("miranda", {"health_up": MIRANDA_HEALTH_UP})
    assert result is not None and len(result) == 1
    threshold, mode, rules = result[0]
    assert (threshold, mode) == (30, "every")
    assert len(rules) == 2   # squad, then the submachine-gun subset
    assert all(r.trigger == "per_shot" for r in rules)


def test_build_nikke_rules_returns_flawless_glass_burst_percent_for_cinderella():
    # Regression: _build_cinderella once passed sv["flawless_glass"] (the
    # already-unwrapped slot dict) to build_flawless_glass_rules, which itself
    # indexes ["flawless_glass"] again - a KeyError only a real sv-shaped dict
    # (not a hand-picked unit test fixture) surfaces.
    skill_values = {
        "flawless_glass": {
            "description_value_01": "2.71", "description_value_02": "10",
            "description_value_03": "100", "description_value_04": "136.6",
        },
        "dirt_resistant_mirror": {
            "description_value_01": "96", "description_value_02": "96",
            "description_value_03": "3", "description_value_04": "1.6", "description_value_05": "12",
        },
        "glass_slippers": {
            "description_value_01": "1365.92", "description_value_02": "10", "description_value_03": "28.9",
        },
        "caster_atk": 60_000, "caster_def": 3_000, "caster_max_hp": 1_000_000,
        "caster_weapon_stats": {"charge_time": 1.0, "max_ammo": 24},
    }
    rules, burst_percent = build_nikke_rules("cinderella", skill_values)
    # Flawless Glass's stage-3 ATK buff and permanent Charge Speed buff, plus
    # Beautiful's Max HP ramp - which the ATK buff reads live, so both must be
    # built from the SAME sv or the ramp is silently absent.
    assert [r.trigger for r in rules] == ["ally_burst_activate", "battle_start", "battle_start"]
    assert burst_percent == 1365.92


def test_takina_event_rules_registered():
    rules, burst_percent = build_nikke_rules("takina-inoue", TAKINA_SKILL_VALUES)
    assert burst_percent is None
    triggers = {r.trigger for r in rules}
    assert {"battle_start", "full_burst_end", "full_burst_enter", "own_burst_activate"} <= triggers
    assert "periodic" not in triggers  # periodic rules come via get_periodic_rules, not here


def test_clip_weapons_carry_their_load_count():
    assert get_clip_reload_splits("centi") == 3
    assert get_clip_reload_splits("centi-signature") == 3
    assert get_clip_reload_splits("grave") == 2


def test_an_ordinary_weapon_reloads_once():
    assert get_clip_reload_splits("liter") == 1
    assert get_clip_reload_splits("not-a-slug") == 1


def test_both_builds_of_a_clip_unit_share_the_count():
    # A Favorite Item does not change the weapon, so a base/signature pair that
    # disagreed here would be a typo, not a mechanic.
    for base in ("centi", "drake", "sugar"):
        assert (get_clip_reload_splits(base)
                == get_clip_reload_splits(f"{base}-signature"))


def test_isabel_shortens_the_full_burst_window():
    # Sonic Chaser: "Full Burst Time (down) 5 sec."
    assert get_full_burst_duration_delta("isabel") == -5.0


def test_modernia_lengthens_the_full_burst_window():
    # New World: "Full Burst Duration (up) 5 sec."
    assert get_full_burst_duration_delta("modernia") == 5.0


def test_a_unit_that_does_not_touch_the_window_reads_zero():
    assert get_full_burst_duration_delta("arcana") == 0.0
