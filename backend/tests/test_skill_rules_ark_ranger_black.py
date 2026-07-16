from app.effects import EffectRegistry
from app.skill_rules.ark_ranger_black import (
    build_ark_ranger_black_rules,
    build_ark_ranger_dots,
    build_ark_ranger_ceiling_collider,
    build_ark_ranger_per_shot_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real level-10 values (lootandwaifus), slots numbered by left-to-right appearance.
TRANSFORM = {
    "description_value_06": "156.19",  # ATK % while transformed
    "description_value_04": "1",       # battery decay % per interval
    "description_value_05": "0.2",     # decay interval (sec)
    "description_value_08": "30",      # normal-attack threshold (Sustained buff)
    "description_value_09": "59.6",    # Sustained Damage % (skill 1)
    "description_value_10": "5",       # its duration
}
ULTIMATE = {
    "description_value_01": "50",      # battery % after transforming (Emergency Charge)
    "description_value_02": "266.69",  # Meteor DoT % per tick
    "description_value_03": "10",      # Meteor tick count
    "description_value_04": "135.83",  # self Sustained Damage % (burst)
    "description_value_05": "10",      # its duration
}
TREMBLE = {"description_value_01": "45.87"}  # Ark Black Collider % per tick


def build():
    return build_ark_ranger_black_rules({
        "transform": TRANSFORM, "ultimate": ULTIMATE, "caster_atk": 100000.0,
    })


def _ctx(part_destructible):
    return SquadContext(
        [SquadMember("ark-ranger-black", 3, "Wind")],
        part_destructible=part_destructible,
    )


ARK = {"slug": "ark-ranger-black", "element": "Wind"}


def test_floor_atk_buff_on_burst_for_window_duration():
    # part_destructible False: ATK +156.19% applied at burst for D=10s.
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"ark-ranger-black": build()}, _ctx(False), registry, time=5.0)
    assert round(registry.total_for("atk_percent", ARK, now=5.0), 4) == 1.5619
    assert registry.total_for("atk_percent", ARK, now=15.1) == 0.0  # expires after 10s


def test_floor_atk_buff_absent_when_part_destructible():
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"ark-ranger-black": build()}, _ctx(True), registry, time=5.0)
    # the burst-window ATK buff is the floor variant; gone when flag True
    assert registry.total_for("atk_percent", ARK, now=5.0) == 0.0


def test_ceiling_atk_buff_permanent_from_battle_start():
    registry = EffectRegistry()
    fire_trigger("battle_start", {"ark-ranger-black": build()}, _ctx(True), registry, time=0.0)
    assert round(registry.total_for("atk_percent", ARK, now=170.0), 4) == 1.5619  # permanent


def test_ceiling_atk_buff_absent_when_not_part_destructible():
    registry = EffectRegistry()
    fire_trigger("battle_start", {"ark-ranger-black": build()}, _ctx(False), registry, time=0.0)
    assert registry.total_for("atk_percent", ARK, now=1.0) == 0.0


def test_burst_grants_self_sustained_damage_up_both_branches():
    for flag in (False, True):
        registry = EffectRegistry()
        fire_trigger("own_burst_activate", {"ark-ranger-black": build()}, _ctx(flag), registry, time=5.0)
        assert round(registry.total_for("sustained_damage_up", ARK, now=5.0), 4) == 1.3583
        assert registry.total_for("sustained_damage_up", ARK, now=15.1) == 0.0


def test_meteor_dot_is_10_ticks_sustained_both_branches():
    specs = build_ark_ranger_dots({"transform": TRANSFORM, "ultimate": ULTIMATE, "tremble": TREMBLE})
    meteor = [s for s in specs if s.get("requires_part_destructible") is None]
    assert len(meteor) == 1
    assert meteor[0]["base_percent"] == 266.69
    assert meteor[0]["tick_count"] == 10
    assert meteor[0]["tick_interval"] == 1.0
    assert meteor[0]["damage_type"] == "sustained"


def test_floor_collider_dot_gated_off_when_part_destructible():
    specs = build_ark_ranger_dots({"transform": TRANSFORM, "ultimate": ULTIMATE, "tremble": TREMBLE})
    collider = [s for s in specs if s.get("requires_part_destructible") is False]
    assert len(collider) == 1
    assert collider[0]["base_percent"] == 45.87
    assert collider[0]["tick_count"] == 10       # D=10s / 1s interval
    assert collider[0]["damage_type"] == "sustained"


def test_ceiling_collider_is_wholefight_periodic_sustained():
    spec = build_ark_ranger_ceiling_collider({"tremble": {"description_value_01": "45.87"}})
    assert spec["cooldown"] == 1.0
    assert spec["percent"] == 45.87
    assert spec["damage_type"] == "sustained"
    assert spec["requires_part_destructible"] is True


def test_per_shot_sustained_buff_every_30_normals_refreshes():
    rules = build_ark_ranger_per_shot_rules({"transform": TRANSFORM})
    assert len(rules) == 1
    threshold, mode, subrules = rules[0]
    assert (threshold, mode) == (30, "every")

    registry = EffectRegistry()
    ctx = _ctx(False)
    subrules[0].action(ctx, "ark-ranger-black", 3.0, registry)
    assert round(registry.total_for("sustained_damage_up", ARK, now=3.0), 4) == 0.596
    assert registry.total_for("sustained_damage_up", ARK, now=8.1) == 0.0  # 5s duration
    # refresh (not stack): apply again within window -> still 0.596
    subrules[0].action(ctx, "ark-ranger-black", 6.0, registry)
    assert round(registry.total_for("sustained_damage_up", ARK, now=6.0), 4) == 0.596
