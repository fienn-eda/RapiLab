from app.effects import EffectRegistry
from app.skill_rules.ark_ranger_black import (
    build_ark_ranger_black_rules,
    build_ark_ranger_dots,
    build_ark_ranger_ceiling_collider,
    build_ark_ranger_per_shot_rules,
    transformation_window_seconds,
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
TREMBLE = {
    "description_value_01": "45.87",  # Ark Black Collider % per tick
    "description_value_03": "77.5",   # Wind-AR ally Sustained Damage % (FB enter)
    "description_value_04": "10",     # its duration
}


def build():
    return build_ark_ranger_black_rules({
        "transform": TRANSFORM, "ultimate": ULTIMATE, "tremble": TREMBLE,
        "caster_atk": 100000.0,
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
    assert meteor[0]["resolves_after_cast"] is True


def test_floor_collider_dot_gated_off_when_part_destructible():
    specs = build_ark_ranger_dots({"transform": TRANSFORM, "ultimate": ULTIMATE, "tremble": TREMBLE})
    collider = [s for s in specs if s.get("requires_part_destructible") is False]
    assert len(collider) == 1
    assert collider[0]["base_percent"] == 45.87
    assert collider[0]["tick_count"] == 10       # D=10s / 1s interval
    assert collider[0]["damage_type"] == "sustained"
    assert collider[0]["resolves_after_cast"] is True


def test_ceiling_collider_is_wholefight_periodic_sustained():
    spec = build_ark_ranger_ceiling_collider({"tremble": {"description_value_01": "45.87"}})
    assert spec["cooldown"] == 1.0
    assert spec["percent"] == 45.87
    assert spec["damage_type"] == "sustained"
    assert spec["requires_part_destructible"] is True


def test_transformation_window_derives_from_battery_values_not_hardcoded():
    # Every existing fixture happens to yield D=10, which collides with two
    # unrelated 10s elsewhere in the fixtures - a hardcoded window=10.0 would
    # pass every other test in this file. Alter the decay interval so D must
    # move, proving it's actually derived from the skill values.
    altered_transform = dict(TRANSFORM, description_value_05="0.1")  # decay twice as fast
    values = {"transform": altered_transform, "ultimate": ULTIMATE, "tremble": TREMBLE}
    assert transformation_window_seconds(values) == 5.0  # 50 / (1/0.1)

    specs = build_ark_ranger_dots(values)
    collider = [s for s in specs if s.get("requires_part_destructible") is False]
    assert collider[0]["tick_count"] == 5

    registry = EffectRegistry()
    rules = build_ark_ranger_black_rules(values)
    fire_trigger("own_burst_activate", {"ark-ranger-black": rules}, _ctx(False), registry, time=5.0)
    assert round(registry.total_for("atk_percent", ARK, now=9.9), 4) == 1.5619
    assert registry.total_for("atk_percent", ARK, now=10.1) == 0.0  # expires after 5s, not 10s


def test_fb_enter_sustained_buff_hits_only_wind_ar_allies():
    # Tremble! 2nd bullet: FB enter -> all Wind Code allies with assault
    # rifles get Sustained Damage +77.5% for 10s (member-subset scope, gap #3).
    registry = EffectRegistry()
    ctx = SquadContext([
        SquadMember("ark-ranger-black", 3, "Wind", weapon="AR"),
        SquadMember("wind-ar-ally", 3, "Wind", weapon="AR"),
        SquadMember("wind-sg-ally", 3, "Wind", weapon="SG"),
    ])
    fire_trigger("full_burst_enter", {"ark-ranger-black": build()}, ctx, registry, time=5.0)
    def total(slug, element):
        return registry.total_for("sustained_damage_up", {"slug": slug, "element": element}, 6.0)
    assert total("wind-ar-ally", "Wind") == 0.775
    assert total("ark-ranger-black", "Wind") == 0.775  # Ark herself is Wind AR
    assert total("wind-sg-ally", "Wind") == 0.0
    # 10s duration
    assert registry.total_for("sustained_damage_up", {"slug": "wind-ar-ally", "element": "Wind"}, 15.1) == 0.0


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
