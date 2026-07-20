"""Real max-level figures from lootandwaifus for Elegg: Boom and Shock
(slug "elegg-boom-and-shock"), slots numbered left-to-right per skill.
"""
from app.effects import EffectRegistry
from app.skill_rules.elegg_boom_and_shock import (
    build_elegg_boom_and_shock_rules,
    build_elegg_burst_delay,
    build_elegg_ghost_resources,
    build_ghostbuster_scheduled_nukes,
    build_thirteen_ghosts_dynamic_hit_count_nukes,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

HELLO_GHOST = {
    "description_value_01": "1",     # random enemy possessed
    "description_value_02": "6",     # possession duration sec
    "description_value_03": "100",   # required hit count, squad-cumulative
    "description_value_04": "1",     # ghosts captured per completion
    "description_value_05": "100",   # required hit count reached %
    "description_value_06": "13",    # max ghosts (the cap)
    "description_value_07": "6",     # recurring interval sec
    "description_value_08": "1",     # ghost threshold for the ATK buff
    "description_value_09": "16.2",  # ATK % of the skill user's ATK
    "description_value_10": "4",     # ghost threshold for the elemental buff
    "description_value_11": "35",    # Elemental Advantage Attack Damage %
}
GHOSTBUSTER = {
    "description_value_01": "40",    # self ATK %
    "description_value_02": "10",    # its duration sec
    "description_value_03": "1100",  # overflow-capture damage %
}
THIRTEEN_GHOSTS = {
    "description_value_01": "13",   # "if the number of ghosts is not 13"
    "description_value_02": "800",  # damage % per hit
    "description_value_03": "6",    # hits below the cap
    "description_value_04": "6",    # ghosts spent below the cap
    "description_value_05": "1",    # minimum ghosts maintained
    "description_value_06": "13",   # "if the number of ghosts is 13"
    "description_value_07": "800",  # damage % per hit (same figure)
    "description_value_08": "13",   # hits at the cap
    "description_value_09": "9",    # ghosts spent at the cap
}
ELEGG_ATK = 80000.0
ELEGG_VALUES = {
    "hello_ghost": HELLO_GHOST,
    "ghostbuster": GHOSTBUSTER,
    "thirteen_ghosts": THIRTEEN_GHOSTS,
    "caster_atk": ELEGG_ATK,
}
ELEGG = {"slug": "elegg-boom-and-shock", "element": "Water"}
WATER_ALLY = {"slug": "water-ally", "element": "Water"}
FIRE_ALLY = {"slug": "fire-ally", "element": "Fire"}


def make_context():
    return SquadContext(
        [
            SquadMember("elegg-boom-and-shock", burst_tier=3, element="Water"),
            SquadMember("water-ally", burst_tier=1, element="Water"),
            SquadMember("fire-ally", burst_tier=2, element="Fire"),
        ],
        base_atk={"elegg-boom-and-shock": ELEGG_ATK, "water-ally": 0.0, "fire-ally": 0.0},
    )


def ghost_spec():
    return build_elegg_ghost_resources(ELEGG_VALUES)[0]


def test_ghosts_fill_every_capture_interval_up_to_the_cap():
    spec = ghost_spec()
    assert spec.name == "ghosts"
    assert spec.fill == ("periodic", 6.0)
    assert spec.cap == 13.0


def test_ghost_atk_buff_is_caster_scaled_and_gated_at_one_ghost():
    atk_buff = ghost_spec().buffs[0]
    assert atk_buff.stat == "flat_atk"
    assert atk_buff.scope == "element:Water"  # she is Water, so it includes her
    assert atk_buff.lifetime is None  # "continuously"
    assert atk_buff.value_fn(0) == 0.0
    assert atk_buff.value_fn(1) == ELEGG_ATK * 0.162
    assert atk_buff.value_fn(13) == ELEGG_ATK * 0.162  # a threshold, not a ramp


def test_elemental_advantage_buff_is_gated_at_four_ghosts():
    elem_buff = ghost_spec().buffs[1]
    assert elem_buff.stat == "other_elemental_bonus"
    assert elem_buff.scope == "element:Water"
    assert elem_buff.value_fn(3) == 0.0
    assert elem_buff.value_fn(4) == 0.35


def test_burst_spends_nine_ghosts_at_the_cap_and_six_below_it_floored_at_one():
    spend = ghost_spec().resets[0]["value_fn"]
    assert ghost_spec().resets[0]["trigger"] == "own_burst"
    assert spend(13) == 4.0    # at the cap: v 9
    assert spend(12) == 6.0    # below the cap: v 6
    assert spend(4) == 1.0     # floored - "maintains at least 1 ghost"
    assert spend(0) == 1.0


def test_burst_fires_thirteen_hits_at_the_cap_and_six_below_it():
    spec = build_thirteen_ghosts_dynamic_hit_count_nukes(ELEGG_VALUES)[0]
    assert spec["resource"] == "ghosts"
    assert spec["base_percent"] == 800.0
    assert spec["hit_count_fn"](13) == 13
    assert spec["hit_count_fn"](12) == 6
    assert spec["hit_count_fn"](0) == 6


def test_overflow_nuke_fires_only_on_captures_landing_at_the_cap():
    spec = build_ghostbuster_scheduled_nukes(ELEGG_VALUES)[0]
    assert spec["percent"] == 1100.0
    context = make_context()
    for tick in range(1, 30):  # captures at 6s, 12s, ... - the cap lands at 78s
        context.fill_resource("elegg-boom-and-shock", "ghosts", 1, tick * 6.0)

    times = spec["schedule"](context, 120.0)

    # The 13th capture (t=78) reaches the cap; every capture AFTER it overflows.
    assert min(times) == 84.0
    assert times == [t for t in times if t >= 84.0]
    assert 78.0 not in times


def test_burst_grants_self_atk_for_ten_seconds():
    context = make_context()
    registry = EffectRegistry()
    rules = {"elegg-boom-and-shock": build_elegg_boom_and_shock_rules(ELEGG_VALUES)}

    fire_trigger("own_burst_activate", rules, context, registry, 10.0)

    assert registry.total_for("atk_percent", ELEGG, 19.9) == 0.40
    assert registry.total_for("atk_percent", ELEGG, 20.1) == 0.0
    assert registry.total_for("atk_percent", WATER_ALLY, 12.0) == 0.0  # self-scoped


# --- Held until the ghost cap ------------------------------------------


def test_her_burst_is_held_until_the_ghosts_reach_the_cap():
    # 13 Ghosts hits 13 times at the cap and only 6 below it, so firing her
    # the instant the cooldown allows throws away most of her burst. The
    # delay is derived from the fill, not hardcoded: cap x capture interval.
    delay = build_elegg_burst_delay(ELEGG_VALUES)

    # cap 13 x 6s to the first cap; spend 9 x 6s to refill for each one after,
    # which outlasts her 40s cooldown and sets her real cadence.
    assert delay == {"not_before": 78.0, "min_interval": 54.0}


def test_end_to_end_she_bursts_twice_and_always_at_the_ghost_cap():
    """The point of the delay: both her bursts take the 13-hit branch. Fired
    on cooldown instead she would burst five times over the same fight, four
    of them on the 6-hit branch."""
    from app.raid_simulator import simulate_raid
    from app.roster import NikkeSpec, assemble_simulation_inputs
    from tests.test_roster import anis_star_spec, helm_spec, takina_spec

    elegg = NikkeSpec(
        slug="elegg-boom-and-shock", burst_tier=3, burst_cooldown=40.0,
        element="Water", weapon="MG",
        base_stats={"atk": 350000, "def": 60000, "max_hp": 10000000},
        skill_values={k: v for k, v in ELEGG_VALUES.items() if k != "caster_atk"},
        weapon_stats={"weapon": "MG", "damage_percent": 10.0, "max_ammo": 300, "reload_time": 2.0},
    )
    deck = [anis_star_spec(), takina_spec(), elegg, helm_spec()]
    result = simulate_raid(
        **assemble_simulation_inputs(deck),
        enemy_def=0, gauge_charge_time=2.0, fight_duration=180.0, mode="manual",
    )

    fires = [
        e["time"] for e in result["events"]
        if e["type"] == "burst" and e["slug"] == "elegg-boom-and-shock"
    ]
    assert len(fires) == 2
    assert fires[0] >= 78.0
    # 9 ghosts spent, back at 6s each: the second burst is at the cap again.
    assert fires[1] - fires[0] >= 54.0
