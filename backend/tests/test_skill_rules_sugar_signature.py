"""Sugar's Favorite Item build - adds permanent Attack Damage, a Fire-Code
elemental-advantage grant, self ATK, and Water/Iron shotgun-ally elemental buffs."""
from app.effects import EffectRegistry
from app.skill_rules.sugar_signature import build_sugar_signature_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

BLACK_TYPHOON = {
    "description_value_01": "16.39", "description_value_02": "10",
    "description_value_03": "12.12", "description_value_04": "10",
    "description_value_05": "1.5", "description_value_06": "19.98",
}
NOIRE_SENSOR = {
    "description_value_01": "13.02", "description_value_02": "10",
    "description_value_03": "25.01", "description_value_04": "10",
    "description_value_05": "83.8", "description_value_06": "15",
    "description_value_07": "40.02", "description_value_08": "15",
}
TROUBLE_SHOOTER = {
    "description_value_01": "66", "description_value_02": "15",
    "description_value_03": "33", "description_value_04": "15",
    "description_value_05": "20", "description_value_06": "15",
    "description_value_07": "60.01", "description_value_08": "15",
}
SUGAR_SIG = {
    "black_typhoon": BLACK_TYPHOON,
    "noire_sensor": NOIRE_SENSOR,
    "trouble_shooter": TROUBLE_SHOOTER,
}

SELF = {"slug": "sugar-signature", "element": "Iron"}
WATER_SG = {"slug": "water-sg", "element": "Water"}
FIRE_SG = {"slug": "fire-sg", "element": "Fire"}
IRON_AR = {"slug": "iron-ar", "element": "Iron"}


def _ctx(boss_element=None):
    return SquadContext([
        SquadMember("sugar-signature", burst_tier=3, element="Iron", weapon="SG"),
        SquadMember("water-sg", burst_tier=3, element="Water", weapon="SG"),
        SquadMember("fire-sg", burst_tier=2, element="Fire", weapon="SG"),
        SquadMember("iron-ar", burst_tier=1, element="Iron", weapon="AR"),
    ], boss_element=boss_element)


def _fire(trigger, boss_element=None, time=0.0):
    reg = EffectRegistry()
    rules = {"sugar-signature": build_sugar_signature_rules(SUGAR_SIG)}
    fire_trigger(trigger, rules, _ctx(boss_element), reg, time)
    return reg


def test_intact_cover_attack_damage_is_permanent():
    reg = _fire("battle_start")
    assert round(reg.total_for("attack_damage_up", SELF, 0.0), 4) == 0.1998
    assert round(reg.total_for("attack_damage_up", SELF, 179.0), 4) == 0.1998
    assert reg.total_for("attack_damage_up", WATER_SG, 0.0) == 0.0


def test_elemental_advantage_is_granted_only_against_fire():
    assert _fire("battle_start", boss_element="Fire").total_for(
        "element_advantage_grant", SELF, 0.0) == 1.0
    assert _fire("battle_start", boss_element="Wind").total_for(
        "element_advantage_grant", SELF, 0.0) == 0.0
    assert _fire("battle_start", boss_element="Fire").total_for(
        "element_advantage_grant", WATER_SG, 0.0) == 0.0


def test_full_burst_adds_self_atk_on_top_of_crit_rate():
    reg = _fire("full_burst_enter")
    assert round(reg.total_for("crit_rate", SELF, 0.0), 4) == 0.1302
    assert round(reg.total_for("atk_percent", SELF, 0.0), 4) == 0.2501
    assert reg.total_for("atk_percent", WATER_SG, 0.0) == 0.0
    assert reg.total_for("atk_percent", SELF, 10.1) == 0.0


def test_shotgun_ammo_buff_runs_15_seconds_in_this_build():
    reg = _fire("full_burst_enter")
    for member in (SELF, WATER_SG, FIRE_SG):
        assert round(reg.total_for("max_ammo_percent", member, 0.0), 4) == 0.838
    assert reg.total_for("max_ammo_percent", IRON_AR, 0.0) == 0.0
    # 15s here, against the base build's 10s.
    assert round(reg.total_for("max_ammo_percent", SELF, 14.9), 4) == 0.838
    assert reg.total_for("max_ammo_percent", SELF, 15.1) == 0.0


def test_elemental_buff_targets_water_and_iron_shotguns_only():
    for trigger, value in (("full_burst_enter", 0.4002), ("own_burst_activate", 0.6001)):
        reg = _fire(trigger)
        assert round(reg.total_for("other_elemental_bonus", SELF, 0.0), 4) == value
        assert round(reg.total_for("other_elemental_bonus", WATER_SG, 0.0), 4) == value
        # The Fire shotgun and the Iron AR both fail the filter.
        assert reg.total_for("other_elemental_bonus", FIRE_SG, 0.0) == 0.0
        assert reg.total_for("other_elemental_bonus", IRON_AR, 0.0) == 0.0
        assert reg.total_for("other_elemental_bonus", SELF, 15.1) == 0.0


def test_burst_keeps_self_attack_speed_and_adds_atk():
    reg = _fire("own_burst_activate")
    assert round(reg.total_for("attack_speed_percent", SELF, 0.0), 4) == 0.66
    assert round(reg.total_for("atk_percent", SELF, 0.0), 4) == 0.20
    assert reg.total_for("atk_percent", SELF, 15.1) == 0.0
