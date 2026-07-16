import pytest

from app.skill_rules.registry import (
    ENCODED_SLUGS,
    build_nikke_rules,
    get_burst_damage_type,
    get_burst_hit_count,
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
        "fire_away": {"description_value_01": "3.08", "description_value_02": "27.87", "description_value_03": "10"},
        "aegis_cannon": {"description_value_01": "8236.8"},
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


def test_get_burst_damage_type_defaults_to_attack():
    assert get_burst_damage_type("crown") == "attack"
    assert get_burst_damage_type("helm") == "attack"


def test_rapi_red_hood_burst_nuke_is_projectile_explosion_typed():
    # Power of Inheritance is a "Projectile Explosion" keyword skill, so its
    # burst-nuke instance benefits from Projectile Explosion Damage buffs.
    assert get_burst_damage_type("rapi-red-hood") == "projectile_explosion"


def test_build_nikke_rules_returns_the_great_thief_burst_percent_for_quency():
    skill_values = {
        "secure_route": {"description_value_01": "49.58", "description_value_02": "25.25", "description_value_03": "16.73"},
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
    assert get_per_shot_rules("crown", {}) is None


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


def test_get_per_shot_rules_returns_health_up_for_miranda():
    result = get_per_shot_rules("miranda", {
        "health_up": {
            "description_value_07": "30", "description_value_08": "50.06", "description_value_09": "5",
        },
    })
    assert result is not None and len(result) == 1
    threshold, mode, rules = result[0]
    assert (threshold, mode) == (30, "every")
    assert all(r.trigger == "per_shot" for r in rules)


def test_takina_event_rules_registered():
    rules, burst_percent = build_nikke_rules("takina-inoue", TAKINA_SKILL_VALUES)
    assert burst_percent is None
    triggers = {r.trigger for r in rules}
    assert {"battle_start", "full_burst_end", "full_burst_enter", "own_burst_activate"} <= triggers
    assert "periodic" not in triggers  # periodic rules come via get_periodic_rules, not here
