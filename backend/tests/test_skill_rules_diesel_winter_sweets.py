"""Real max-level figures from lootandwaifus for Diesel: Winter Sweets (slugs
"diesel-winter-sweets-intro" / "diesel-winter-sweets-highlight"), slots
numbered left-to-right per skill.
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.diesel_winter_sweets import (
    HIGHLIGHT_BURST_DELAY,
    build_diesel_highlight_rules,
    build_diesel_intro_rules,
    build_diesel_burst_dot,
    build_diesel_full_burst_dot,
    build_diesel_resource_specs,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

MIC_TEST = {
    "description_value_01": "20.28",   # Intro Critical Damage %
    "description_value_02": "20.28",   # Highlight Critical Damage %
    "description_value_03": "60.19",   # Intro Sustained Damage %
    "description_value_04": "10",      # its duration sec
    "description_value_05": "235.03",  # Highlight Sustained Damage %
    "description_value_06": "10",      # its duration sec
}
SING_NOW = {
    "description_value_01": "3",       # Mute stack cap (not modeled)
    "description_value_02": "68.04",   # part-destruction Sustained Damage %
    "description_value_03": "15",      # its duration sec
    "description_value_04": "318.14",  # Full Charge Sustained Damage %
    "description_value_05": "3",       # its duration sec
    "description_value_06": "2",       # its stack cap
    "description_value_07": "63.33",   # Full Burst DoT % of final ATK
    "description_value_08": "1",       # its tick interval sec
    "description_value_09": "9",       # its duration sec
}
LA_LA_LA = {
    "description_value_01": "25.09",   # burst Damage Taken %
    "description_value_02": "10",      # its duration sec
    "description_value_03": "18.43",   # all-enemy DoT % of final ATK
    "description_value_04": "1",       # its tick interval sec
    "description_value_05": "9",       # its duration sec
    "description_value_06": "181.2",   # stage-target DoT % of final ATK
    "description_value_07": "1",       # its tick interval sec
    "description_value_08": "9",       # its duration sec
    "description_value_09": "100",     # Noise Pollution Hit Rate ▼ %
    "description_value_10": "1",       # its duration sec
    "description_value_11": "1",       # Mute stacks consumed (not modeled)
}

VALUES = {"mic_test": MIC_TEST, "sing_now": SING_NOW, "la_la_la": LA_LA_LA}

DIESEL_INTRO = "diesel-winter-sweets-intro"
DIESEL_HIGHLIGHT = "diesel-winter-sweets-highlight"


def _context(slug, part_destructible=False):
    return SquadContext(
        [SquadMember(slug, 3, "Fire", "RL")], part_destructible=part_destructible
    )


def _target(slug):
    return {"slug": slug, "element": "Fire", "burst_tier": 3, "weapon": "RL"}


def _apply(rules, slug, trigger, time=0.0, part_destructible=False):
    registry = EffectRegistry()
    context = _context(slug, part_destructible)
    fire_trigger(trigger, {slug: rules}, context, registry, time)
    return registry


# --- Locked Intro / Highlight state ------------------------------------


def test_intro_locks_the_weaker_sustained_buff_on_every_full_burst():
    registry = _apply(build_diesel_intro_rules(VALUES), DIESEL_INTRO, "full_burst_enter", 5.0)
    assert registry.total_for("sustained_damage_up", _target(DIESEL_INTRO), 6.0) == 0.6019


def test_highlight_locks_the_stronger_sustained_buff_on_every_full_burst():
    registry = _apply(
        build_diesel_highlight_rules(VALUES), DIESEL_HIGHLIGHT, "full_burst_enter", 5.0
    )
    assert registry.total_for("sustained_damage_up", _target(DIESEL_HIGHLIGHT), 6.0) == 2.3503


def test_the_sustained_buff_expires_after_ten_seconds():
    registry = _apply(
        build_diesel_highlight_rules(VALUES), DIESEL_HIGHLIGHT, "full_burst_enter", 5.0
    )
    assert registry.total_for("sustained_damage_up", _target(DIESEL_HIGHLIGHT), 15.1) == 0.0


def test_crit_damage_starts_at_the_first_full_burst_and_is_permanent():
    rules = build_diesel_intro_rules(VALUES)
    registry = EffectRegistry()
    context = _context(DIESEL_INTRO)
    fire_trigger("full_burst_enter", {DIESEL_INTRO: rules}, context, registry, 5.0)

    assert registry.total_for("other_critical_damage_sources", _target(DIESEL_INTRO), 4.9) == 0.0
    assert registry.total_for("other_critical_damage_sources", _target(DIESEL_INTRO), 179.0) == 0.2028


def test_crit_damage_does_not_restack_on_later_full_bursts():
    # The state is entered once and "cannot be removed" - re-entering Full
    # Burst must not add a second copy.
    rules = build_diesel_intro_rules(VALUES)
    registry = EffectRegistry()
    context = _context(DIESEL_INTRO)
    for time in (5.0, 25.0, 45.0):
        fire_trigger("full_burst_enter", {DIESEL_INTRO: rules}, context, registry, time)

    assert registry.total_for("other_critical_damage_sources", _target(DIESEL_INTRO), 50.0) == 0.2028


def test_only_highlight_carries_the_skip_a_cycle_burst_delay():
    assert HIGHLIGHT_BURST_DELAY == {"skip_cycles": 1}


# --- Part-destruction bracket ------------------------------------------


def test_part_destruction_sustained_buff_applies_only_on_a_destructible_boss():
    rules = build_diesel_intro_rules(VALUES)
    ceiling = _apply(rules, DIESEL_INTRO, "battle_start", 0.0, part_destructible=True)
    floor = _apply(rules, DIESEL_INTRO, "battle_start", 0.0, part_destructible=False)

    assert ceiling.total_for("sustained_damage_up", _target(DIESEL_INTRO), 100.0) == pytest.approx(0.6804)
    assert floor.total_for("sustained_damage_up", _target(DIESEL_INTRO), 100.0) == 0.0


# --- Full Charge stacks -------------------------------------------------


def test_full_charge_stacks_cap_at_two_and_expire_after_three_seconds():
    specs = build_diesel_resource_specs(VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.fill == ("per_shot_every", 1)
    assert spec.cap == 2

    buff = spec.buffs[0]
    assert buff.stat == "sustained_damage_up"
    assert buff.scope == "self"
    assert buff.lifetime == 3.0
    assert buff.value_fn(1) == 3.1814
    assert buff.value_fn(2) == 6.3628


# --- Damage-over-time nukes ---------------------------------------------


def test_full_burst_dot_ticks_once_per_second_for_nine_seconds():
    spec = build_diesel_full_burst_dot(VALUES)[0]
    assert spec["percent"] == 63.33
    assert spec["damage_type"] == "sustained"

    context = SquadContext([SquadMember(DIESEL_HIGHLIGHT, 3, "Fire", "RL")])
    context.full_burst_windows = [(5.0, 15.0), (30.0, 40.0)]
    times = spec["schedule"](context, 180.0)

    assert times[:9] == [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]
    assert len(times) == 18


def test_burst_dot_sums_the_all_enemy_and_stage_target_ticks():
    # A raid is a single boss, so it is always the stage target and takes both.
    spec = build_diesel_burst_dot(VALUES)[0]
    assert spec["base_percent"] == 199.63
    assert spec["tick_count"] == 9
    assert spec["tick_interval"] == 1.0
    assert spec["damage_type"] == "sustained"


def test_burst_puts_damage_taken_up_on_the_boss_for_ten_seconds():
    registry = _apply(
        build_diesel_highlight_rules(VALUES), DIESEL_HIGHLIGHT, "own_burst_activate", 20.0
    )
    assert registry.total_for("damage_taken_up", _target(DIESEL_HIGHLIGHT), 25.0) == 0.2509
    assert registry.total_for("damage_taken_up", _target(DIESEL_HIGHLIGHT), 30.1) == 0.0


def test_both_modes_share_every_non_state_effect():
    intro = build_diesel_intro_rules(VALUES)
    highlight = build_diesel_highlight_rules(VALUES)
    # Highlight carries exactly one rule Intro does not: Noise Pollution, which
    # only exists while she is in Highlight status.
    assert len(intro) + 1 == len(highlight)
    assert build_diesel_burst_dot(VALUES) == build_diesel_burst_dot(VALUES)


def _squad_context(slug, part_destructible=False):
    """Diesel plus two allies, so "all allies (except self)" has somewhere to
    land and someone to skip."""
    return SquadContext([
        SquadMember(slug, 3, "Fire", "RL"),
        SquadMember("sg-ally", 1, "Iron", "SG"),
        SquadMember("ar-ally", 2, "Wind", "AR"),
    ], part_destructible=part_destructible)


def test_noise_pollution_blinds_the_allies_but_not_diesel():
    reg = EffectRegistry()
    rules = {DIESEL_HIGHLIGHT: build_diesel_highlight_rules(VALUES)}
    ctx = _squad_context(DIESEL_HIGHLIGHT)
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert reg.total_for("hit_rate", _target(DIESEL_HIGHLIGHT), 0.0) == 0.0
    for ally in ("sg-ally", "ar-ally"):
        target = {"slug": ally, "element": "Iron"}
        assert reg.total_for("hit_rate", target, 0.0) == -1.0
        assert reg.total_for("hit_rate", target, 1.1) == 0.0  # 1 sec, and gone


def test_a_part_destructible_boss_keeps_the_squad_muted():
    """Mute (immunity to Noise Pollution) is restocked by destroying a part, and
    her burst spends only one stack - so where parts fall the penalty never
    lands. Same reading as her Sustained bracket, other side of the flag."""
    reg = EffectRegistry()
    rules = {DIESEL_HIGHLIGHT: build_diesel_highlight_rules(VALUES)}
    ctx = _squad_context(DIESEL_HIGHLIGHT, part_destructible=True)
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert reg.total_for("hit_rate", {"slug": "sg-ally", "element": "Iron"}, 0.0) == 0.0


def test_noise_pollution_reaches_an_allys_damage_in_a_real_fight():
    """End to end, not just in the registry: the second inside Noise Pollution
    costs a shotgun ally real damage.

    It takes a whole fight to see, because the bullet hangs off HER burst and
    Highlight skips the opening cycle - a deck without a Burst-3 tier-mate to
    cover that cycle never opens a Full Burst at all and she never bursts
    (`burst_cycle` reports that as `full_burst_missed`). So the deck here is the
    shape ALLOWED_SHAPES guarantees: a second Burst 3, on a long enough cooldown
    that the cycle after the skipped one falls to her."""
    from app.raid_simulator import simulate_raid

    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "sg-ally", "burst_tier": 3, "element": "Iron", "cooldown": 60.0,
         "weapon": "SG"},
        {"slug": DIESEL_HIGHLIGHT, "burst_tier": 3, "element": "Fire",
         "cooldown": 40.0, "weapon": "RL",
         "burst_delay": HIGHLIGHT_BURST_DELAY},
    ]
    result = simulate_raid(
        deck,
        {"b1": [], "b2": [], "sg-ally": [],
         DIESEL_HIGHLIGHT: build_diesel_highlight_rules(VALUES)},
        burst_damage_percents={},
        base_stats={s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in deck},
        enemy_def=0,
        gauge_charge_time=2.4,
        fight_duration=90.0,
        base_crit_rate=0.0,
        weapon_stats={
            "sg-ally": {"weapon": "SG", "damage_percent": 100.0, "max_ammo": 999,
                        "reload_time": 0.0, "charge_time": 0.0,
                        "charge_damage_percent": 100.0},
        },
        core_hittable=True,
        core_diameter_px=50.0,
    )

    bursts = [e["time"] for e in result["events"]
              if e["type"] == "burst" and e["slug"] == DIESEL_HIGHLIGHT]
    assert bursts, "fixture broken: Diesel never took a Burst-3 seat"

    fired = bursts[0]
    shots = [(e["time"], e["damage"]) for e in result["damage_log"]
             if e["slug"] == "sg-ally" and e["source"] == "normal_attack"]
    blinded = [d for t, d in shots if fired <= t < fired + 1.0]
    clear = [d for t, d in shots if fired + 1.0 <= t < fired + 4.0]
    assert blinded and clear, "fixture broken: no shots on either side of the second"
    # -100% doubles the spread (250px -> 477px), so the share of it inside a
    # 50px core falls from 4.0% to 1.1%.
    assert max(blinded) < min(clear)


def test_intro_never_pays_noise_pollution():
    """It is gated on Highlight STATUS, which the Intro build never enters."""
    reg = EffectRegistry()
    rules = {DIESEL_INTRO: build_diesel_intro_rules(VALUES)}
    ctx = _squad_context(DIESEL_INTRO)
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert reg.total_for("hit_rate", {"slug": "sg-ally", "element": "Iron"}, 0.0) == 0.0
