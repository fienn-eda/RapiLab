from app.models import OverloadOption
from app.raid_simulator import simulate_raid
from app.roster import NikkeSpec, assemble_simulation_inputs


def helm_spec(overload_options=None, cube=None):
    return NikkeSpec(
        slug="helm",
        burst_tier=3,
        burst_cooldown=40.0,
        element="Water",
        weapon="SR",
        base_stats={"atk": 398398, "def": 52659, "max_hp": 9198954},
        skill_values={
            "frontline_command": {"description_value_01": "14.64", "description_value_02": "5"},
            "fire_away": {"description_value_01": "3.08", "description_value_02": "27.87", "description_value_03": "10", "description_value_04": "178.98"},
            "aegis_cannon": {"description_value_01": "8236.8", "description_value_04": "158.4", "description_value_05": "10"},
        },
        weapon_stats={
            "weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        },
        overload_options=overload_options or [],
        cube=cube,
    )


def anis_star_spec():
    return NikkeSpec(
        slug="anis-star",
        burst_tier=1,
        burst_cooldown=20.0,
        element="Electric",
        weapon="RL",
        base_stats={"atk": 260890, "def": 69656, "max_hp": 10720232},
        skill_values={
            "starfall": {
                "description_value_01": "1", "description_value_02": "40.01",
                "description_value_03": "7.48", "description_value_04": "120.13", "description_value_05": "6",
            },
            "stardust": {
                "description_value_01": "35.01", "description_value_02": "10", "description_value_03": "1.26",
                "description_value_04": "92.03", "description_value_05": "10", "description_value_06": "34",
                "description_value_07": "10",
            },
            "star_anis": {
                "description_value_01": "40.01", "description_value_02": "10",
                "description_value_03": "35.2", "description_value_04": "10",
                "description_value_05": "0.7",
            },
        },
        weapon_stats={
            "weapon": "RL", "damage_percent": 61.3, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        },
    )


def rapi_red_hood_spec():
    return NikkeSpec(
        slug="rapi-red-hood",
        burst_tier=3,
        burst_cooldown=40.0,
        element="Fire",
        weapon="MG",
        base_stats={"atk": 300000, "def": 60000, "max_hp": 10000000},
        skill_values={
            "battlefield_assessment": {
                "description_value_01": "1", "description_value_02": "1",
                "description_value_03": "1", "description_value_04": "7.48",
                "description_value_05": "8.02", "description_value_06": "10",
                "description_value_07": "95.04", "description_value_08": "10",
                "description_value_09": "48", "description_value_10": "10",
            },
            "attachable_projectiles": {
                "description_value_01": "150.72", "description_value_02": "100.6",
                "description_value_03": "120", "description_value_04": "88.11",
                "description_value_05": "88.11",
            },
            "power_of_inheritance": {
                "description_value_08": "339.98",
                "description_value_11": "421.2", "description_value_12": "10",
                "description_value_14": "60", "description_value_15": "10",
            },
        },
        weapon_stats={
            "weapon": "MG", "damage_percent": 20.0, "max_ammo": 300,
            "reload_time": 2.0, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    )


def takina_spec():
    return NikkeSpec(
        slug="takina-inoue",
        burst_tier=2,
        burst_cooldown=20.0,
        element="Iron",
        weapon="SR",
        base_stats={"atk": 280000, "def": 60000, "max_hp": 10000000},
        skill_values={
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
        },
        weapon_stats={
            "weapon": "SR", "damage_percent": 69.0, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        },
    )


def crown_spec():
    return NikkeSpec(
        slug="crown",
        burst_tier=2,
        burst_cooldown=20.0,
        element="Iron",
        weapon="MG",
        base_stats={"atk": 281952, "def": 66196, "max_hp": 11621606},
        skill_values={
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
        },
        weapon_stats={
            "weapon": "MG", "damage_percent": 5.57, "max_ammo": 300,
            "reload_time": 2.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )


def minimal_feasible_deck(helm_overload=None, helm_cube=None):
    return [anis_star_spec(), crown_spec(), helm_spec(helm_overload, helm_cube)]


def helm_aquamarine_spec():
    return NikkeSpec(
        slug="helm-aquamarine",
        burst_tier=2,
        burst_cooldown=20.0,
        element="Iron",
        weapon="AR",
        base_stats={"atk": 300000, "def": 50000, "max_hp": 9000000},
        skill_values={
            "admire_accompaniment": {
                "description_value_01": "131.34", "description_value_02": "1.82",
                "description_value_03": "2.2", "description_value_04": "2.6",
            },
            "aegis_cannon_overload": {"description_value_01": "164.83"},
            "aegis_cannon_suppression_fire": {
                "description_value_01": "105.58", "description_value_02": "5.64",
                "description_value_03": "5", "description_value_04": "5",
            },
        },
        weapon_stats={
            "weapon": "AR", "damage_percent": 13.65, "max_ammo": 60,
            "reload_time": 2.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )


def test_assemble_produces_deck_entries_with_scheduler_fields():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    deck = inputs["deck"]
    assert [m["slug"] for m in deck] == ["anis-star", "crown", "helm"]
    helm = next(m for m in deck if m["slug"] == "helm")
    assert helm["burst_tier"] == 3
    assert helm["element"] == "Water"
    assert helm["cooldown"] == 40.0


def test_burst_damage_percents_only_includes_nikkes_with_a_burst_nuke():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    # helm has a nuke (Aegis Cannon 8236.8%); anis-star and crown are buff bursts
    assert inputs["burst_damage_percents"] == {"helm": 8236.8}


def test_burst_damage_types_tags_projectile_explosion_nukes():
    # Attack-typed burst nukes are omitted (default); only overrides are listed.
    assert assemble_simulation_inputs(minimal_feasible_deck())["burst_damage_types"] == {}
    inputs = assemble_simulation_inputs([rapi_red_hood_spec()])
    assert inputs["burst_damage_types"] == {"rapi-red-hood": "projectile_explosion"}


def test_base_stats_and_weapon_stats_are_keyed_by_slug():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    assert inputs["base_stats"]["helm"]["atk"] == 398398
    assert inputs["weapon_stats"]["helm"]["weapon"] == "SR"


def test_assembled_inputs_run_through_simulate_raid():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    result = simulate_raid(
        **inputs, enemy_def=0, gauge_charge_time=2.0, fight_duration=60.0, mode="manual",
    )
    assert result["total_damage"] > 0
    assert any(e["source"] == "burst" for e in result["damage_log"])
    assert any(e["source"] == "normal_attack" for e in result["damage_log"])


def test_overload_atk_up_increases_total_damage():
    without = assemble_simulation_inputs(minimal_feasible_deck())
    with_ov = assemble_simulation_inputs(
        minimal_feasible_deck(helm_overload=[OverloadOption(name="공격력 증가", value=40.20)])
    )
    kwargs = dict(enemy_def=0, gauge_charge_time=2.0, fight_duration=60.0, mode="manual")
    dmg_without = simulate_raid(**without, **kwargs)["total_damage"]
    dmg_with = simulate_raid(**with_ov, **kwargs)["total_damage"]
    assert dmg_with > dmg_without


def test_periodic_nukes_only_includes_nikkes_with_one():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    assert inputs["periodic_nukes"] == {}

    inputs_with_aqua = assemble_simulation_inputs([anis_star_spec(), helm_aquamarine_spec()])
    assert inputs_with_aqua["periodic_nukes"] == {
        "helm-aquamarine": {"cooldown": 4.0, "percent": 105.58}
    }


def test_periodic_rules_only_includes_nikkes_with_one():
    assert assemble_simulation_inputs(minimal_feasible_deck())["periodic_rules"] == {}

    inputs = assemble_simulation_inputs([takina_spec()])
    assert set(inputs["periodic_rules"]) == {"takina-inoue"}
    cooldown, rules = inputs["periodic_rules"]["takina-inoue"][0]
    assert cooldown == 15.0
    assert all(r.trigger == "periodic" for r in rules)


def test_periodic_rules_flow_through_simulate_raid():
    inputs = assemble_simulation_inputs([takina_spec()])
    result = simulate_raid(
        **inputs, enemy_def=0, gauge_charge_time=2.0, fight_duration=40.0, mode="manual",
    )
    assert result["total_damage"] > 0


def test_periodic_nukes_flow_through_simulate_raid():
    inputs = assemble_simulation_inputs([anis_star_spec(), helm_aquamarine_spec()])
    result = simulate_raid(
        **inputs, enemy_def=0, gauge_charge_time=2.0, fight_duration=20.0, mode="manual",
    )
    periodic_hits = [e for e in result["damage_log"] if e["source"] == "periodic"]
    assert len(periodic_hits) > 0
    assert all(e["slug"] == "helm-aquamarine" for e in periodic_hits)


def test_cube_superior_code_damage_increases_total_damage():
    without = assemble_simulation_inputs(minimal_feasible_deck())
    with_cube = assemble_simulation_inputs(
        minimal_feasible_deck(
            helm_cube={"name": "Relic Bear Cube", "reload_speed_percent": 29.69, "superior_code_damage_percent": 19.09}
        )
    )
    kwargs = dict(enemy_def=0, gauge_charge_time=2.0, fight_duration=60.0, mode="manual")
    dmg_without = simulate_raid(**without, **kwargs)["total_damage"]
    dmg_with = simulate_raid(**with_cube, **kwargs)["total_damage"]
    assert dmg_with > dmg_without


def test_weapon_mode_schedules_key_exists_in_assembled_inputs():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    assert "weapon_mode_schedules" in inputs
    assert inputs["weapon_mode_schedules"] == {}
