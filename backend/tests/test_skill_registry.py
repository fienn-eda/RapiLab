import pytest

from app.skill_rules.registry import ENCODED_SLUGS, build_nikke_rules, get_periodic_nuke


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
