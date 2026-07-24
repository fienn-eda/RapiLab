"""Sugar (base build) - Full-Burst crit/ammo support plus a self attack-speed burst."""
from app.effects import EffectRegistry
from app.skill_rules.sugar import build_sugar_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

NOIRE_SENSOR = {
    "description_value_01": "13.02", "description_value_02": "10",
    "description_value_03": "83.8", "description_value_04": "10",
}
TROUBLE_SHOOTER = {
    "description_value_01": "66", "description_value_02": "15",
    "description_value_03": "33", "description_value_04": "15",
}
SUGAR = {"noire_sensor": NOIRE_SENSOR, "trouble_shooter": TROUBLE_SHOOTER}

SELF = {"slug": "sugar", "element": "Iron"}
SG_ALLY = {"slug": "sg-ally", "element": "Water"}
AR_ALLY = {"slug": "ar-ally", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("sugar", burst_tier=3, element="Iron", weapon="SG"),
        SquadMember("sg-ally", burst_tier=3, element="Water", weapon="SG"),
        SquadMember("ar-ally", burst_tier=1, element="Fire", weapon="AR"),
    ])


def _fire(trigger, time=0.0):
    reg = EffectRegistry()
    fire_trigger(trigger, {"sugar": build_sugar_rules(SUGAR)}, _ctx(), reg, time)
    return reg


def test_full_burst_gives_self_crit_rate():
    reg = _fire("full_burst_enter")
    assert round(reg.total_for("crit_rate", SELF, 0.0), 4) == 0.1302
    assert reg.total_for("crit_rate", SG_ALLY, 0.0) == 0.0
    assert reg.total_for("crit_rate", SELF, 10.1) == 0.0  # 10s duration


def test_full_burst_gives_max_ammo_to_shotgun_members_only():
    # Exact weapon subset, not a squad approximation: the AR ally is excluded,
    # and Sugar herself carries a shotgun so she is included.
    reg = _fire("full_burst_enter")
    assert round(reg.total_for("max_ammo_percent", SELF, 0.0), 4) == 0.838
    assert round(reg.total_for("max_ammo_percent", SG_ALLY, 0.0), 4) == 0.838
    assert reg.total_for("max_ammo_percent", AR_ALLY, 0.0) == 0.0
    assert reg.total_for("max_ammo_percent", SG_ALLY, 10.1) == 0.0


def test_burst_gives_self_attack_speed():
    reg = _fire("own_burst_activate")
    assert round(reg.total_for("attack_speed_percent", SELF, 0.0), 4) == 0.66
    assert reg.total_for("attack_speed_percent", SG_ALLY, 0.0) == 0.0
    assert reg.total_for("attack_speed_percent", SELF, 15.1) == 0.0


def test_inert_and_deferred_effects_are_not_emitted():
    """Hit Rate has no consumer, and Black Typhoon's cover-attack trigger does
    not exist - neither may leak into the registry."""
    for trigger in ("battle_start", "full_burst_enter", "own_burst_activate"):
        reg = _fire(trigger)
        for stat in ("hit_rate", "other_critical_damage_sources", "reload_speed_percent"):
            assert reg.total_for(stat, SELF, 0.0) == 0.0
