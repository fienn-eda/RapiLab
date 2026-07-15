from app.burst_cycle import FULL_BURST_DURATION
from app.effects import EffectRegistry
from app.skill_rules.dorothy_serendipity import build_dorothy_serendipity_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (values rendered inline).
RADIANT_WINGS = {
    "description_value_01": "55.08",  # self Pierce Damage % (continuous)
    "description_value_02": "75.24",  # self ATK % (during Full Burst)
    "description_value_03": "40.68",  # deferred: Hit Rate %
}
FALSE_SALVATION = {
    "description_value_01": "65",     # self Attack Speed %
    "description_value_02": "15",     # its duration
    "description_value_03": "88.12",  # self ATK %
    "description_value_04": "15",     # its duration
    "description_value_05": "5",      # deferred: pellet count +
    "description_value_06": "15",     # its duration
}


def make_context():
    return SquadContext([
        SquadMember("dorothy-serendipity", burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def build():
    return build_dorothy_serendipity_rules({
        "radiant_wings": RADIANT_WINGS,
        "false_salvation": FALSE_SALVATION,
    })


DOROTHY = {"slug": "dorothy-serendipity", "element": "Water"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_radiant_wings_grants_permanent_self_pierce_at_battle_start():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"dorothy-serendipity": build()}, ctx, registry, time=0.0)
    assert round(registry.total_for("pierce_damage_up", DOROTHY, now=0.0), 4) == 0.5508
    assert round(registry.total_for("pierce_damage_up", DOROTHY, now=175.0), 4) == 0.5508  # permanent
    assert registry.total_for("pierce_damage_up", ALLY, now=0.0) == 0.0  # self-only


def test_radiant_wings_grants_self_atk_during_full_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)
    assert round(registry.total_for("atk_percent", DOROTHY, now=5.0), 4) == 0.7524
    assert registry.total_for("atk_percent", DOROTHY, now=5.0 + FULL_BURST_DURATION + 0.1) == 0.0


def test_false_salvation_burst_grants_self_atk_and_attack_speed():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)
    assert round(registry.total_for("atk_percent", DOROTHY, now=5.0), 4) == 0.8812
    assert round(registry.total_for("attack_speed_percent", DOROTHY, now=5.0), 4) == 0.65
    assert registry.total_for("attack_speed_percent", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("attack_speed_percent", DOROTHY, now=20.1) == 0.0  # 15s
