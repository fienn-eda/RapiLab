"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill (fixed reference counts like "1 enemy unit(s)" or
"for 1 time(s)" are not data slots).
"""
import pytest

from app.effects import Effect, EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.maiden_ice_rose import (
    MP_CAP,
    build_blessings_fill_triggered_buffs,
    build_blessings_upon_you_per_shot_rules,
    build_blessings_upon_you_rules,
    build_diamond_dust_dynamic_hit_count_nukes,
    build_meditation_resources,
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
    # 03 = shots per proc, 04 = Max HP %, 05 = sec, 06 = stack cap. The two
    # "maximum of 12" mentions are MP_CAP restated and are dropped, not numbered.
    "meditation": {
        "description_value_01": "1", "description_value_02": "1",
        "description_value_03": "6", "description_value_04": "6.34",
        "description_value_05": "15", "description_value_06": "10",
    },
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


def test_meditation_is_a_capped_stack_whose_life_refreshes_on_every_proc():
    """"Max HP ▲ 6.34% for 15 sec, stacks up to 10", one stack per 6 Full
    Charges. Each new stack restarts the 15 sec for the whole stack (Fienn,
    range test 2026-08-17), so the count climbs to the cap instead of settling
    at "procs per 15 sec".

    That cap used to be written off as unable to bind - the reasoning assumed
    all ten had to land inside ONE fixed 15-sec window. They do not; the window
    keeps moving, so the cap is real and the engine was holding her at about two
    stacks."""
    (spec,) = build_meditation_resources(MAIDEN_VALUES, caster_max_hp=50000)
    assert spec.name == "meditation"
    assert spec.cap == 10
    assert spec.fill == ("per_shot_every", 6)

    (buff,) = spec.buffs
    assert buff.stat == "flat_max_hp"
    assert buff.scope == "self"
    assert spec.lifetime == 15.0
    assert spec.lifetime_refreshes is True
    # 6.34% of her own Max HP per stack.
    assert buff.value_fn(1) == pytest.approx(0.0634 * 50000)
    assert buff.value_fn(10) == pytest.approx(10 * 0.0634 * 50000)


def test_blessings_upon_you_self_buff_is_active_for_damage_after_the_cast():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_blessings_upon_you_rules(MAIDEN_VALUES, caster_max_hp=50000):
        rule.action(ctx, "maiden-ice-rose", 5.0, reg)
    assert round(reg.total_for("other_elemental_bonus", MAIDEN, now=5.1), 4) == 0.3168
    assert round(reg.total_for("flat_atk", MAIDEN, now=5.1), 4) == round(0.032 * 50000, 4)
    assert reg.total_for("other_elemental_bonus", MAIDEN, now=15.1) == 0.0  # 10s window


def test_meditation_stacks_do_not_expire_one_by_one():
    """The test this replaces pinned the OPPOSITE rule - it asserted the first
    stack lapsing 15 sec after its own proc while the second lived on. That is
    the plain timed semantic, and it is what held her at about two stacks and
    made her "stacks up to 10" look unreachable. Each proc renews the whole
    stack (Fienn, range test 2026-08-17), so nothing lapses until 15 sec after
    the LAST one - and then all of it does."""
    ctx = make_context()
    per_stack = 50000 * 0.0634
    (spec,) = build_meditation_resources(MAIDEN_VALUES, caster_max_hp=50000)
    for t in (10.0, 16.0):
        ctx.fill_resource("maiden-ice-rose", spec.name, 1, time=t)
    (buff,) = spec.buffs

    def value_at(t):
        return buff.value_fn(ctx.resource_count(
            "maiden-ice-rose", spec.name, t, spec.cap, spec.lifetime,
            lifetime_refreshes=spec.lifetime_refreshes))

    assert value_at(10.0) == pytest.approx(per_stack)
    assert value_at(16.0) == pytest.approx(2 * per_stack)
    # The old rule dropped the t=10 stack here. The refresh keeps both.
    assert value_at(25.1) == pytest.approx(2 * per_stack)
    # 15 sec after the LAST proc, the whole stack goes at once.
    assert value_at(30.9) == pytest.approx(2 * per_stack)
    assert value_at(31.1) == pytest.approx(0.0)


def test_meditation_stacks_feed_her_own_max_hp_scaled_atk():
    # 그녀는 이 엔진에서 자기 Max HP를 ATK로 환산하는 몇 안 되는 소비자인데,
    # 자기 Meditation 스택은 "엔진이 Max HP를 안 쓴다"는 사유로 빠져 있었다.
    ctx = make_context()
    reg = EffectRegistry()
    # One Meditation stack, as the resolution pass would emit it.
    (spec,) = build_meditation_resources(MAIDEN_VALUES, caster_max_hp=50000)
    (buff,) = spec.buffs
    reg.add(Effect(buff.stat, buff.value_fn(1), buff.scope, None, "maiden-ice-rose"),
            applied_at=1.0)
    for rule in build_blessings_upon_you_rules(MAIDEN_VALUES, caster_max_hp=50000):
        rule.action(ctx, "maiden-ice-rose", 5.0, reg)
    live_max_hp = 50000 * (1 + 0.0634)
    assert round(reg.total_for("flat_atk", MAIDEN, now=5.1), 4) == round(0.032 * live_max_hp, 4)


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


def test_blessings_fill_triggered_buff_specs():
    specs = build_blessings_fill_triggered_buffs({**MAIDEN_VALUES, "caster_atk": 10000})
    assert len(specs) == 2
    elemental, atk = specs
    assert elemental["resource"] == "mp"
    assert elemental["buffs"] == [("other_elemental_bonus", 0.409, 10.0)]
    assert elemental["condition"] is not None  # boss_is_element("Water") gate
    assert atk["resource"] == "mp"
    assert atk["buffs"] == [("flat_atk", 10000 * 0.209, 10.0)]
    assert "condition" not in atk or atk.get("condition") is None
    # filter: Electric allies except Maiden herself
    electric = SquadMember("e", 2, "Electric")
    fire = SquadMember("f", 2, "Fire")
    maiden = SquadMember("maiden-ice-rose", 3, "Electric")
    for spec in specs:
        assert spec["member_filter"](electric, "maiden-ice-rose") is True
        assert spec["member_filter"](fire, "maiden-ice-rose") is False
        assert spec["member_filter"](maiden, "maiden-ice-rose") is False


def _fill_buff_deck_run(boss_element):
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "maiden-ice-rose", "burst_tier": 3, "element": "Electric", "cooldown": 40.0},
        {"slug": "electric-ally", "burst_tier": 3, "element": "Electric", "cooldown": 40.0},
        {"slug": "fire-ally", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]
    weapon = {"weapon": "AR", "damage_percent": 10.0, "max_ammo": 10000,
              "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 100.0}
    return simulate_raid(
        deck,
        {m["slug"]: [] for m in deck},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000, "def": 0, "max_hp": 50000} for m in deck},
        enemy_def=0, gauge_charge_time=5.0, fight_duration=25.0, mode="auto", base_crit_rate=0.0,
        boss_element=boss_element,
        weapon_stats={"electric-ally": weapon, "fire-ally": weapon},
        resource_specs={"maiden-ice-rose": build_mp_resources(MAIDEN_VALUES)},
        resource_fill_triggered_buffs={
            "maiden-ice-rose": build_blessings_fill_triggered_buffs(
                {**MAIDEN_VALUES, "caster_atk": 10000}
            )
        },
    )


def _shots_of(result, slug):
    """(time, damage) per normal attack, Full Burst bonus divided back out.

    A normal attack inside a Full Burst window carries +0.5 in the major
    modifier (measured 2026-07-28), which would otherwise multiply the very
    ATK steps these tests read off each shot.
    """
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    windows = list(zip(starts, ends))
    return [(e["time"],
             e["damage"] / (1.5 if any(s <= e["time"] < x for s, x in windows) else 1.0))
            for e in result["damage_log"]
            if e["source"] == "normal_attack" and e["slug"] == slug]


def test_blessings_fill_buffs_step_up_at_mp_fill_times_vs_water_boss():
    # MP fills at t=5 (squad tier-1, MP==0); the 10s buffs cover [5, 15).
    # Electric ally vs Water boss: 1.1 advantage baseline; inside the window
    # flat ATK +20.9% of Maiden's ATK and Elemental Advantage Attack Damage
    # +40.9% (element bonus group) both apply. Fire ally: never buffed.
    result = _fill_buff_deck_run("Water")
    for t, damage in _shots_of(result, "electric-ally"):
        if 5.0 <= t < 15.0:
            expected = (10000 + 2090) * 0.1 * (1.1 + 0.409)
        else:
            expected = 10000 * 0.1 * 1.1
        assert round(damage, 4) == round(expected, 4), (t, damage)
    assert all(round(d, 4) == 1000.0 for _, d in _shots_of(result, "fire-ally"))


def test_blessings_fill_buffs_only_flat_atk_vs_non_water_boss():
    # Against a Fire boss the Elemental-Advantage spec is gated off (no actual
    # advantage); only the flat ATK bullet lands.
    result = _fill_buff_deck_run("Fire")
    for t, damage in _shots_of(result, "electric-ally"):
        expected = (10000 + 2090) * 0.1 if 5.0 <= t < 15.0 else 1000.0
        assert round(damage, 4) == round(expected, 4), (t, damage)


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


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
BLESSINGS_UPON_YOU = MAIDEN_VALUES["blessings_upon_you"]
DIAMOND_DUST = MAIDEN_VALUES["diamond_dust"]
MEDITATION = MAIDEN_VALUES["meditation"]
