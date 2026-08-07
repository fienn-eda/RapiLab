from app.burst_cycle import FULL_BURST_DURATION
from app.effects import EffectRegistry
from app.skill_rules.dorothy_serendipity import (
    build_dorothy_serendipity_rules,
    build_flash_per_shot_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (values rendered inline).
FLASH = {
    "description_value_01": "80",     # pellets that arm the first bullet
    "description_value_02": "3",      # its "for 3 round(s)"
    "description_value_03": "98.18",  # self Hit Rate %
    "description_value_04": "3",      # its duration in rounds
    "description_value_05": "72",     # self Attack Damage %
    "description_value_06": "3",      # its duration in rounds
    "description_value_07": "1",      # pellet count is fixed at this
    "description_value_08": "3",      # its duration in rounds
    "description_value_09": "160",    # deferred: pellets for the second bullet
    "description_value_10": "200",    # deferred: Pierce range expansion %
    "description_value_11": "3",      # its duration in rounds
}
RADIANT_WINGS = {
    "description_value_01": "55.08",  # self Pierce Damage % (continuous)
    "description_value_02": "75.24",  # self ATK % (during Full Burst)
    "description_value_03": "40.68",  # self Hit Rate % (during Full Burst)
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


VALUES = {
    "flash": FLASH,
    "radiant_wings": RADIANT_WINGS,
    "false_salvation": FALSE_SALVATION,
}


def build():
    return build_dorothy_serendipity_rules(VALUES)


def flash_rule():
    """The single (threshold, mode, rules) triple Flash contributes."""
    rules = build_flash_per_shot_rules(VALUES)
    assert len(rules) == 1
    return rules[0]


def pellets_at(registry, time, shots_since_fire, ctx=None):
    (_limit, increment_at), _mode, _rules = flash_rule()
    return increment_at(ctx or make_context(), "dorothy-serendipity", time,
                        registry, shots_since_fire)


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


def test_radiant_wings_grants_self_hit_rate_on_the_same_window():
    """Her other Full Burst bullet, and the only Hit Rate she gets: Flash's
    +98.18% is behind a pellet counter this engine does not have."""
    ctx = make_context()
    ctx.current_full_burst_end = 10.0
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)
    assert round(registry.total_for("hit_rate", DOROTHY, now=9.9), 4) == 0.4068
    assert registry.total_for("hit_rate", DOROTHY, now=10.1) == 0.0
    assert registry.total_for("hit_rate", ALLY, now=9.9) == 0.0   # "Affects self"
    # And nothing outside the window: her shotgun spends most of a raid at its
    # full 250px spread.
    assert registry.total_for("hit_rate", DOROTHY, now=4.9) == 0.0


def test_radiant_wings_lasts_exactly_the_window_that_is_open():
    # 원문이 "continuously" - 초 수가 아니라 풀 버스트가 끝날 때까지다. 이사벨이 연
    # 5초짜리 창에서는 5초만 간다.
    ctx = make_context()
    ctx.current_full_burst_end = 10.0          # t=5.0에 열린 5초짜리 창
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("atk_percent", DOROTHY, now=9.9), 4) == 0.7524
    assert registry.total_for("atk_percent", DOROTHY, now=10.1) == 0.0


def test_radiant_wings_falls_back_to_the_base_duration_without_a_window():
    # 버스트 사이클이 없는 컨텍스트(대부분의 단위 테스트)는 엔진 기본값으로 떨어진다.
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("atk_percent", DOROTHY, now=14.9), 4) == 0.7524
    assert registry.total_for("atk_percent", DOROTHY, now=15.1) == 0.0


def test_false_salvation_burst_grants_self_atk_and_attack_speed():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)
    assert round(registry.total_for("atk_percent", DOROTHY, now=5.0), 4) == 0.8812
    assert round(registry.total_for("attack_speed_percent", DOROTHY, now=5.0), 4) == 0.65
    assert registry.total_for("attack_speed_percent", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("attack_speed_percent", DOROTHY, now=20.1) == 0.0  # 15s


def test_battle_start_no_longer_grants_a_permanent_pierce_property():
    """The Pierce PROPERTY is Flash's, for 3 rounds after 80 pellets - the skill
    text grants it nowhere else. Holding it permanently was worth 13.4% of her
    damage on its own, since `pierce_damage_up` only pays a holder."""
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"dorothy-serendipity": build()}, ctx, registry, time=0.0)
    assert registry.total_for("has_pierce", DOROTHY, now=0.0) == 0.0
    # Radiant Wings' Pierce DAMAGE is separate and genuinely permanent.
    assert round(registry.total_for("pierce_damage_up", DOROTHY, now=0.0), 4) == 0.5508


def test_flash_arms_on_the_pellet_threshold_from_the_skill_text():
    (limit, _increment), mode, _rules = flash_rule()
    assert (limit, mode) == (80.0, "accumulate")


def test_flash_grants_hit_rate_attack_damage_and_pierce_for_three_rounds():
    ctx = make_context()
    registry = EffectRegistry()
    _threshold, _mode, rules = flash_rule()
    fire_trigger("per_shot", {"dorothy-serendipity": rules}, ctx, registry, time=5.0)
    grants = {g.stat: g for g in registry.round_grants()}
    assert set(grants) == {"hit_rate", "attack_damage_up", "has_pierce"}
    assert round(grants["hit_rate"].value, 4) == 0.9818
    assert round(grants["attack_damage_up"].value, 4) == 0.72
    assert all(g.shots == 3 for g in grants.values())


def test_flash_hit_rate_collapses_her_spread_inside_a_50px_core():
    """The whole point of the bullet: 98.18% alone puts an SG's 250px spread at
    26.9px, so those 3 shots hit the core outright - her idle rate is 4%."""
    from app.accuracy import core_hit_rate, spread_diameter
    assert round(spread_diameter("SG", 0.9818), 1) == 26.9
    assert core_hit_rate("SG", 0.9818, 50.0) == 1.0
    assert round(core_hit_rate("SG", 0.0, 50.0), 4) == 0.04


def test_flash_counts_ten_pellets_a_shot_normally():
    assert pellets_at(EffectRegistry(), time=1.0, shots_since_fire=None) == 10.0


def test_flash_counts_the_bursts_extra_pellets_while_it_is_up():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)
    assert pellets_at(registry, time=5.0, shots_since_fire=None, ctx=ctx) == 15.0
    assert pellets_at(registry, time=20.1, shots_since_fire=None, ctx=ctx) == 10.0  # 15s over


def test_flash_fixes_the_pellet_count_for_its_own_three_rounds():
    # "Pellet count is fixed at 1 for 3 round(s)" - the shots right after a
    # fire barely advance the counter, which is what stretches the next cycle.
    registry = EffectRegistry()
    assert [pellets_at(registry, 1.0, since) for since in (0, 1, 2)] == [1.0, 1.0, 1.0]
    assert pellets_at(registry, 1.0, shots_since_fire=3) == 10.0


def test_the_fixed_count_and_the_bursts_bonus_add_up():
    # Fienn confirmed in-game (2026-08-07) that "fixed at 1" and "+5" combine
    # to 6 rather than the fix winning outright - which is why her cycle runs
    # 7.9 shots and not 9.1.
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"dorothy-serendipity": build()}, ctx, registry, time=5.0)
    assert pellets_at(registry, time=5.0, shots_since_fire=0, ctx=ctx) == 6.0
