"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill (fixed reference counts like "1 enemy unit(s)" or
"for 1 time(s)" are not data slots).
"""
from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.maiden_ice_rose import (
    MP_CAP,
    build_blessings_upon_you_per_shot_rules,
    build_blessings_upon_you_rules,
    build_diamond_dust_dynamic_hit_count_nukes,
    build_mp_resources,
)
from app.squad_engine import SquadContext, SquadMember

MAIDEN_VALUES = {
    "blessings_upon_you": {
        "description_value_01": "40.9", "description_value_02": "10",
        "description_value_03": "20.9", "description_value_04": "10",
        "description_value_05": "31.68", "description_value_06": "10",
        "description_value_07": "3.2", "description_value_08": "10",
        "description_value_09": "547.62",
    },
    "diamond_dust": {"description_value_01": "1372.8", "description_value_02": "10"},
}

MAIDEN = {"slug": "maiden-ice-rose", "element": "Electric"}


def make_context():
    return SquadContext([
        SquadMember("maiden-ice-rose", burst_tier=3, element="Electric"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_mp_cap_is_twelve():
    assert MP_CAP == 12


def test_mp_resource_fills_only_if_zero_on_squad_tier1_and_resets_on_own_burst():
    specs = build_mp_resources(MAIDEN_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.name == "mp"
    assert spec.cap == 12
    assert spec.fill[0] == "squad_burst_cycle_conditional"
    assert spec.resets == [{"trigger": "own_burst", "value": 0}]
    rules = spec.fill[1]
    tier1_event = {"type": "burst", "tier": 1, "slug": "ally", "time": 5.0}
    fb_event = {"type": "full_burst_start", "time": 5.0}
    matched_tier1 = [r for r in rules if r[0](tier1_event)]
    matched_fb = [r for r in rules if r[0](fb_event)]
    assert len(matched_tier1) == 1 and matched_tier1[0][1](0) is True and matched_tier1[0][1](1) is False
    assert len(matched_fb) == 1 and matched_fb[0][1](1) is True and matched_fb[0][1](0) is False


def test_blessings_upon_you_self_buff_does_not_retroactively_boost_its_own_cast():
    # Fienn confirmed in-game (2026-07-12): Diamond Dust's damage is computed
    # AT CAST TIME - a buff granted by that same cast (like this "MP is used"
    # self-buff) does NOT apply to that cast's own damage, only to whatever
    # comes after. So the buff must not be visible to a query at the EXACT
    # instant it was granted, only strictly after.
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_blessings_upon_you_rules(MAIDEN_VALUES, caster_max_hp=50000):
        rule.action(ctx, "maiden-ice-rose", 5.0, reg)
    assert reg.total_for("other_elemental_bonus", MAIDEN, now=5.0) == 0.0
    assert reg.total_for("flat_atk", MAIDEN, now=5.0) == 0.0


def test_blessings_upon_you_self_buff_is_active_for_damage_after_the_cast():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_blessings_upon_you_rules(MAIDEN_VALUES, caster_max_hp=50000):
        rule.action(ctx, "maiden-ice-rose", 5.0, reg)
    assert round(reg.total_for("other_elemental_bonus", MAIDEN, now=5.1), 4) == 0.3168
    assert round(reg.total_for("flat_atk", MAIDEN, now=5.1), 4) == round(0.032 * 50000, 4)
    assert reg.total_for("other_elemental_bonus", MAIDEN, now=15.1) == 0.0  # 10s window


def test_blessings_upon_you_rules_trigger_on_own_burst_activate():
    rules = build_blessings_upon_you_rules(MAIDEN_VALUES, caster_max_hp=50000)
    assert all(r.trigger == "own_burst_activate" for r in rules)


def test_blessings_upon_you_per_shot_nuke_fires_every_shot():
    ps = build_blessings_upon_you_per_shot_rules(MAIDEN_VALUES)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (1, "every")
    reg = EffectRegistry()
    rules[0].action(make_context(), "maiden-ice-rose", 0.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1 and pulses[0].value == 547.62


def test_diamond_dust_dynamic_hit_count_nuke_spec():
    specs = build_diamond_dust_dynamic_hit_count_nukes(MAIDEN_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["resource"] == "mp"
    assert spec["base_percent"] == 1372.8
    assert round(spec["extra_flat_atk_percent_of_max_hp"], 4) == 0.10


def test_maiden_end_to_end_diamond_dust_hits_once_per_cycle_scaled_by_10pct_max_hp():
    # Full chain: MP fills to 1 (tier1-if-zero) every cycle; her own burst
    # drains it BEFORE full_burst_start's "if MP>=1" rule ever gets a chance
    # (strict burst1->burst2->burst3->full-burst ordering) - so Diamond Dust
    # always hits exactly once per cycle, each hit boosted by 10% of her
    # Max HP folded into the nuke's own ATK term.
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "maiden-ice-rose", "burst_tier": 3, "element": "Electric", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "maiden-ice-rose": {"atk": 10000, "def": 0, "max_hp": 50000},
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "maiden-ice-rose": build_blessings_upon_you_rules(MAIDEN_VALUES, 50000)},
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=60.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"maiden-ice-rose": build_mp_resources(MAIDEN_VALUES)},
        dynamic_hit_count_nukes={
            "maiden-ice-rose": build_diamond_dust_dynamic_hit_count_nukes(MAIDEN_VALUES)
        },
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 2  # 2 burst cycles complete within 60s
    # offense = 10000*(1+0) + (0.10*50000 formula term only) = 15000; the "MP
    # is used" self-buff (Elemental Advantage + ATK-from-Max-HP) is granted BY
    # this same burst, so per Fienn's confirmed in-game behavior it does NOT
    # apply to this same burst's own damage - no +1600 flat_atk, no *1.3168
    # Element Bonus Damage factor.
    expected = 15000 * 13.728
    assert all(round(h["damage"], 4) == round(expected, 4) for h in hits)
