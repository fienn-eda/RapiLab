from app.models import OverloadOption, UserNikkeState
from app.roster import assemble_simulation_inputs
from app.user_roster import load_nikke_spec, load_roster


def _state(slug, **overrides):
    payload = {
        "character_slug": slug,
        "level": 200,
        "core_level": 0,
        "hp": 1_000_000.0,
        "atk": 60_000.0,
        "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }
    payload.update(overrides)
    return UserNikkeState(**payload)


def test_loads_drake_end_to_end_from_real_data_files():
    spec = load_nikke_spec(_state("drake"))
    assert spec is not None
    assert spec.burst_tier == 3
    assert spec.element == "Fire"
    assert spec.weapon == "SG"
    assert spec.burst_cooldown == 40.0
    assert spec.base_stats == {"atk": 60_000.0, "def": 3_000.0, "max_hp": 1_000_000.0}
    # weapon stats from data/dotgg/char_drake-nikke.json ("damage": "214.3%", maxAmmo 9, ...)
    assert spec.weapon_stats == {
        "weapon": "SG", "damage_percent": 214.3, "max_ammo": 9,
        "reload_time": 0.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
    }
    # skill values assembled at max level (DRAKE_SPECIAL fixture ground truth)
    assert float(spec.skill_values["drake_special"]["description_value_01"]) == 1254.0


def test_skill_levels_flow_into_assembled_values():
    lv1 = load_nikke_spec(_state("drake", skill_levels={"skill1": 10, "skill2": 10, "burst": 1}))
    lv10 = load_nikke_spec(_state("drake"))
    assert float(lv1.skill_values["drake_special"]["description_value_01"]) < float(
        lv10.skill_values["drake_special"]["description_value_01"]
    )


def test_overload_and_cube_pass_through():
    # overload_options stay OverloadOption models: roster._passive_effects hands
    # them to overload_options_to_effects, which reads .name/.value attributes.
    spec = load_nikke_spec(_state(
        "drake",
        overload_options=[{"name": "공격력 증가", "value": 10.0}],
        pve_cube={"name": "Resilience Cube", "level": 7},
    ))
    assert spec.overload_options == [OverloadOption(name="공격력 증가", value=10.0)]
    assert spec.cube == {"name": "Resilience Cube", "level": 7}
    # the assembled spec must survive roster assembly (cube stats resolve via
    # .get - a name/level-only cube contributes no effects rather than raising)
    assemble_simulation_inputs([spec])


def test_dotgg_slug_manifest_key_bridges_source_slug_mismatch():
    # ada-wong's lootandwaifus slug is "ada-wong" but dotgg's url is "ada"
    # (dotgg shortens collab names); the manifest's dotgg_slug key points the
    # weapon-stats lookup at the right file while skill values stay on the
    # lootandwaifus slug.
    spec = load_nikke_spec(_state("ada-wong"))
    assert spec is not None
    assert spec.burst_tier == 3
    assert spec.element == "Electric"
    assert spec.weapon_stats["weapon"] == "RL"
    assert spec.weapon_stats["max_ammo"] == 6


def test_unloadable_units_are_excluded_not_errors():
    assert load_nikke_spec(_state("totally-unknown")) is None          # not encoded
    # every encoded unit now carries a manifest (KNOWN_MANIFEST_EXCEPTIONS is
    # empty) - privaty, the last holdout used here, loads.
    assert load_nikke_spec(_state("privaty")) is not None


def test_load_roster_partitions_specs_and_excluded():
    specs, excluded = load_roster([_state("drake"), _state("totally-unknown"), _state("privaty")])
    assert [s.slug for s in specs] == ["drake", "privaty"]
    assert excluded == ["totally-unknown"]
