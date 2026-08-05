import pytest

from app.effects import Effect, Pulse, ResourceBuff, ResourceSpec
from app.raid_simulator import CORE_HIT_BONUS, simulate_raid
from app.skill_rules._helpers import (
    buff_rule,
    instant_nuke_pulse_rule,
    refreshing_buff_rule,
    round_buff_rule,
)
from app.skill_rules.privaty import build_ex_magazine_rules
from app.skill_rules.zwei import build_pierce_equation_per_shot_rules
from app.squad_engine import SkillRule, ally_bursted

# Real dollskills level-10 values for Privaty's EX Magazine (signature weapon
# completed), matching test_skill_rules_privaty.py.
PRIVATY_EX_MAGAZINE = {
    "description_value_01": "23.61", "description_value_02": "10",
    "description_value_03": "51.16", "description_value_04": "10",
    "description_value_05": "50.66", "description_value_06": "10",
    "description_value_07": "20.16", "description_value_08": "10",
}


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats(attacker_atk=10000):
    return {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "attacker": {"atk": attacker_atk, "def": 0, "max_hp": 0},
    }


def _first_normal_attack(result):
    """The fight's first normal attack - always well before Full Burst opens,
    so it carries only the modifiers a test puts on it."""
    return next(e for e in result["damage_log"] if e["source"] == "normal_attack")


def full_burst_windows(result):
    """The fight's Full Burst windows, read off its own event log."""
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    return list(zip(starts, ends))


def fb_factor(result, time):
    """What a normal attack's damage is multiplied by for landing at `time`.

    A normal attack inside a Full Burst window collects +0.5 in the major
    modifier, so a hit carrying no other major modifier is worth 1.5x there
    (measured 2026-07-28 - see the normal-attack record() call in
    raid_simulator). These fixtures run 20-sec fights whose window opens around
    5 sec, so most of them straddle the boundary; asserting a flat number would
    quietly assert the bonus away.
    """
    return 1.5 if any(s <= time < e for s, e in full_burst_windows(result)) else 1.0


def test_battle_start_buff_is_active_by_the_time_the_burst_fires():
    def grant_atk_buff(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 0.5, "self", None, "attacker"), applied_at=time)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_atk_buff)],
        "midtier": [],
        "attacker": [],
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 1000.0},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )

    assert len(result["damage_log"]) == 1
    entry = result["damage_log"][0]
    assert entry == {"slug": "attacker", "time": 5.0, "damage": 150000.0, "source": "burst", "damage_type": "attack"}
    assert result["total_damage"] == 150000.0


def _core_pair(**over):
    """The same fight with and without an exploitable core."""
    kwargs = dict(
        rules_by_slug={"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    kwargs.update(over)
    return (simulate_raid(make_deck(), core_hittable=False, **kwargs),
            simulate_raid(make_deck(), core_hittable=True, **kwargs))


def test_core_hittable_true_doubles_normal_attack_damage():
    without_core, with_core = _core_pair(weapon_stats={"attacker": _ar_weapon()})
    # per Fienn's in-game tooltip check, core damage is a uniform 200% across
    # every weapon type (+1.0 to the major modifier), i.e. exactly double a
    # hit with no other modifiers active. Compared on the FIRST shot rather
    # than the fight total: core and the Full Burst bonus share one additive
    # bucket, so inside a window the pair is 2.5/1.5 and "double" is only true
    # of a hit that carries neither.
    first_without = _first_normal_attack(without_core)
    first_with = _first_normal_attack(with_core)
    assert fb_factor(without_core, first_without["time"]) == 1.0
    assert first_with["damage"] == first_without["damage"] * 2
    assert without_core["total_damage"] > 0


def test_core_bonus_does_not_reach_burst_damage():
    # Core Damage is a normal-attack-only modifier - skill damage never
    # collects it (Fienn, in-game, 2026-07-26).
    without_core, with_core = _core_pair(burst_damage_percents={"attacker": 500.0})
    assert without_core["total_damage"] == 10000.0
    assert with_core["total_damage"] == without_core["total_damage"]


def test_core_bonus_does_not_reach_per_shot_or_periodic_skill_damage():
    without_core, with_core = _core_pair(
        weapon_stats={"attacker": _ar_weapon(damage_percent=0.0)},
        per_shot_rules={"attacker": [(5, "every", [instant_nuke_pulse_rule("per_shot", 100.0)])]},
        periodic_nukes={"attacker": {"cooldown": 1.0, "percent": 100.0}},
    )
    # the weapon itself deals nothing, so every point here is skill damage
    assert without_core["total_damage"] > 0
    assert with_core["total_damage"] == without_core["total_damage"]


def test_sustained_and_distributed_normal_attacks_never_collect_the_core_bonus():
    # Sustained / Distributed damage cannot hit a core at all, so a normal
    # attack a transform pins to one of those types stays flat, even though
    # ordinary normal attacks in the same fight do get the bonus (Fienn,
    # 2026-07-26).
    for damage_type in ("sustained", "distributed"):
        profile = {"weapon": "AR", "damage_percent": 10.0, "rate_of_fire": 2.0,
                   "damage_type": damage_type}

        def schedule(context, fight_duration, profile=profile):
            return [{"start": 5.0, "end": 15.0, "profile": profile}]

        without_core, with_core = _core_pair(
            weapon_stats={"attacker": _ar_weapon()},
            weapon_mode_schedules={"attacker": schedule},
        )
        in_window = [
            sum(e["damage"] for e in r["damage_log"] if 5.0 <= e["time"] < 15.0)
            for r in (without_core, with_core)
        ]
        assert in_window[0] > 0, damage_type
        assert in_window[1] == in_window[0], damage_type
        # the untyped shots outside the transform still double, so the fight is
        # genuinely core-hittable
        assert with_core["total_damage"] > without_core["total_damage"], damage_type


def test_boss_element_grants_advantage_bonus_to_matching_attackers():
    # make_deck's attacker is Iron; Iron > Electric, so a boss with Electric
    # element gives the attacker +10%, while a Fire boss (Iron neutral) doesn't.
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    kwargs = dict(
        rules_by_slug=rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    neutral = simulate_raid(make_deck(), boss_element="Fire", **kwargs)
    advantaged = simulate_raid(make_deck(), boss_element="Electric", **kwargs)

    assert neutral["total_damage"] == 10000.0
    assert round(advantaged["total_damage"], 5) == round(10000.0 * 1.1, 5)


def test_superior_code_damage_applies_only_with_elemental_advantage():
    # make_deck's attacker is Iron; Iron > Electric. other_elemental_bonus is
    # the "Superior Code Damage" stat, which joins the element bonus group:
    # it must raise damage against an Electric boss and do nothing at all
    # against a neutral Fire boss.
    def grant_superior_code(context, caster_slug, time, registry):
        registry.add(
            Effect("other_elemental_bonus", 0.5, "self", None, "attacker"),
            applied_at=time,
        )

    rules_by_slug = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_superior_code)],
        "midtier": [],
        "attacker": [],
    }
    kwargs = dict(
        rules_by_slug=rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    neutral = simulate_raid(make_deck(), boss_element="Fire", **kwargs)
    advantaged = simulate_raid(make_deck(), boss_element="Electric", **kwargs)

    # Neutral: element bonus group is 1.0 + nothing.
    assert neutral["total_damage"] == 10000.0
    # Advantaged: 1.1 from the element multiplier plus the 0.5 bonus.
    assert round(advantaged["total_damage"], 5) == round(10000.0 * 1.6, 5)


def test_element_advantage_grant_gives_advantage_the_unit_does_not_naturally_have():
    # make_deck's attacker is Iron, which is neutral against an Iron boss. A skill
    # that GRANTS elemental advantage ("applies Elemental Advantage damage to X
    # Code enemies") sets element_advantage_grant, so the element multiplier
    # reads 1.1 exactly as natural advantage would.
    def grant_advantage(context, caster_slug, time, registry):
        registry.add(
            Effect("element_advantage_grant", 1.0, "self", None, "attacker"),
            applied_at=time,
        )

    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        boss_element="Iron",
    )
    without = simulate_raid(
        make_deck(), rules_by_slug={"buffer": [], "midtier": [], "attacker": []}, **kwargs
    )
    with_grant = simulate_raid(
        make_deck(),
        rules_by_slug={
            "buffer": [SkillRule(trigger="battle_start", action=grant_advantage)],
            "midtier": [],
            "attacker": [],
        },
        **kwargs,
    )

    assert without["total_damage"] == 10000.0
    assert round(with_grant["total_damage"], 5) == round(10000.0 * 1.1, 5)


def test_element_advantage_grant_opens_the_superior_code_damage_gate():
    # Superior Code Damage (other_elemental_bonus) only pays out with advantage.
    # A granted advantage is real advantage, so it must let that bonus through.
    def grant_advantage_and_superior_code(context, caster_slug, time, registry):
        registry.add(
            Effect("element_advantage_grant", 1.0, "self", None, "attacker"),
            applied_at=time,
        )
        registry.add(
            Effect("other_elemental_bonus", 0.5, "self", None, "attacker"),
            applied_at=time,
        )

    result = simulate_raid(
        make_deck(),
        rules_by_slug={
            "buffer": [SkillRule(trigger="battle_start", action=grant_advantage_and_superior_code)],
            "midtier": [],
            "attacker": [],
        },
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        boss_element="Iron",  # neutral for the Iron attacker: advantage is purely granted
    )

    # element bonus group = 1.1 (granted) + 0.5 (superior code)
    assert round(result["total_damage"], 5) == round(10000.0 * 1.6, 5)


def test_element_advantage_grant_does_not_stack_with_natural_advantage():
    # A grant is meant to open advantage a unit does NOT naturally have. If the
    # unit already holds natural advantage (Fire attacker vs a Wind boss - Fire
    # beats Wind per elements.py), a grant on top must not double the element
    # multiplier to 1.2 - it must stay at 1.1, same as natural advantage alone.
    # Two simultaneous grants must likewise stay at 1.1, not compound further.
    fire_deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Fire", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Fire", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]

    def grant_advantage(context, caster_slug, time, registry):
        registry.add(
            Effect("element_advantage_grant", 1.0, "self", None, "attacker"),
            applied_at=time,
        )

    def grant_advantage_twice(context, caster_slug, time, registry):
        grant_advantage(context, caster_slug, time, registry)
        registry.add(
            Effect("element_advantage_grant", 1.0, "self", None, "attacker"),
            applied_at=time,
        )

    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        boss_element="Wind",  # Fire > Wind: attacker already has natural advantage
    )
    natural_only = simulate_raid(
        fire_deck, rules_by_slug={"buffer": [], "midtier": [], "attacker": []}, **kwargs
    )
    natural_plus_one_grant = simulate_raid(
        fire_deck,
        rules_by_slug={
            "buffer": [SkillRule(trigger="battle_start", action=grant_advantage)],
            "midtier": [],
            "attacker": [],
        },
        **kwargs,
    )
    natural_plus_two_grants = simulate_raid(
        fire_deck,
        rules_by_slug={
            "buffer": [SkillRule(trigger="battle_start", action=grant_advantage_twice)],
            "midtier": [],
            "attacker": [],
        },
        **kwargs,
    )

    assert round(natural_only["total_damage"], 5) == round(10000.0 * 1.1, 5)
    assert round(natural_plus_one_grant["total_damage"], 5) == round(10000.0 * 1.1, 5)
    assert round(natural_plus_two_grants["total_damage"], 5) == round(10000.0 * 1.1, 5)


def test_element_advantage_grant_expires_with_its_duration():
    # A grant is a skill-scoped buff like any other - a short-duration grant
    # that lapses before the burst fires must not still be raising the element
    # multiplier at damage-computation time.
    def grant_advantage_briefly(context, caster_slug, time, registry):
        registry.add(
            Effect("element_advantage_grant", 1.0, "self", 3.0, "attacker"),
            applied_at=time,
        )

    result = simulate_raid(
        make_deck(),
        rules_by_slug={
            "buffer": [SkillRule(trigger="battle_start", action=grant_advantage_briefly)],
            "midtier": [],
            "attacker": [],
        },
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,  # burst fires at t=5.0, after the grant's 3s duration lapses
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        boss_element="Iron",  # neutral for the Iron attacker: any bonus is purely from the grant
    )

    assert result["total_damage"] == 10000.0  # grant expired at t=3.0; no bonus at t=5.0


def test_base_crit_rate_of_15_percent_raises_damage_by_7_5_percent():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    kwargs = dict(
        rules_by_slug=rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    no_crit = simulate_raid(make_deck(), base_crit_rate=0.0, **kwargs)
    base_crit = simulate_raid(make_deck(), base_crit_rate=0.15, **kwargs)
    # 15% crit chance * 50% base crit damage = +7.5% expected
    assert round(base_crit["total_damage"], 5) == round(no_crit["total_damage"] * 1.075, 5)


def test_crit_rate_buff_raises_expected_damage():
    def grant_crit_rate(context, caster_slug, time, registry):
        registry.add(Effect("crit_rate", 0.35, "squad", None, "buffer"), applied_at=time)

    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.15,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_buff = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="battle_start", action=grant_crit_rate)], "midtier": [], "attacker": []},
        **kwargs,
    )
    # crit rate 0.15 -> 0.50: expected major 1.075 -> 1.25
    assert round(with_buff["total_damage"], 5) == round(without["total_damage"] / 1.075 * 1.25, 5)


def test_crit_damage_buff_raises_expected_damage_scaled_by_crit_rate():
    def grant_crit_damage(context, caster_slug, time, registry):
        registry.add(
            Effect("other_critical_damage_sources", 1.0, "squad", None, "buffer"), applied_at=time
        )

    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.15,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_buff = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="battle_start", action=grant_crit_damage)], "midtier": [], "attacker": []},
        **kwargs,
    )
    # +100% crit damage at 15% crit: expected major 1 + 0.15*(0.5+1.0) = 1.225 vs 1.075
    assert round(with_buff["total_damage"], 5) == round(without["total_damage"] / 1.075 * 1.225, 5)


def test_damage_taken_up_debuff_raises_damage():
    # An enemy "Damage Taken ▲" debuff (e.g. Blanc/Arcana) is modeled as a
    # squad-scoped effect so every attacker's hits gain it. It sits in the
    # formula's Damage Taken bucket and applies regardless of core hits.
    def grant_damage_taken(context, caster_slug, time, registry):
        registry.add(Effect("damage_taken_up", 0.4, "squad", None, "buffer"), applied_at=time)

    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_debuff = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="battle_start", action=grant_damage_taken)], "midtier": [], "attacker": []},
        **kwargs,
    )
    assert without["total_damage"] == 10000.0
    assert round(with_debuff["total_damage"], 5) == round(10000.0 * 1.4, 5)


def test_enemy_def_percent_debuff_lowers_defense_and_raises_damage():
    # An enemy "DEF ▼ X%" debuff (e.g. Marciana's High-Risk Target) is a
    # squad-scoped effect reducing the defense subtracted from every attacker's
    # base damage. With enemy_def=1000 and atk=2000, a burst at 500%: base goes
    # from (2000-1000)=1000 to (2000-800)=1200 under a -20% DEF debuff.
    def grant_def_down(context, caster_slug, time, registry):
        registry.add(Effect("enemy_def_percent", -0.2, "squad", None, "buffer"), applied_at=time)

    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=1000,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_debuff = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="battle_start", action=grant_def_down)], "midtier": [], "attacker": []},
        **kwargs,
    )
    assert without["total_damage"] == 5000.0
    assert round(with_debuff["total_damage"], 5) == 6000.0


def test_core_damage_up_only_helps_when_core_is_hittable():
    # "Damage dealt when attacking core ▲" (e.g. Nayuta) raises the major
    # modifier, but only matters when the boss's core is actually hittable -
    # gated the same way as the flat core-hit bonus.
    def grant_core_damage(context, caster_slug, time, registry):
        registry.add(Effect("other_core_damage_sources", 0.3, "squad", None, "buffer"), applied_at=time)

    rules = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_core_damage)],
        "midtier": [],
        "attacker": [],
    }
    # Carried by normal attacks, the only instances that can collect a core
    # bonus at all - a burst nuke would stay flat either way.
    kwargs = dict(
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
    )
    not_core = simulate_raid(make_deck(), rules, core_hittable=False, **kwargs)
    core = simulate_raid(make_deck(), rules, core_hittable=True, **kwargs)
    # core hittable: major modifier = 1 + core_hit_bonus(1.0) + core_damage(0.3) = 2.3.
    # Read off the first shot, which is outside the Full Burst window - the
    # bonus lands in this same additive bucket, so a fight total would mix
    # 2.3/1.0 shots with 2.8/1.5 ones.
    first_not_core = _first_normal_attack(not_core)
    first_core = _first_normal_attack(core)
    assert fb_factor(not_core, first_not_core["time"]) == 1.0
    assert not_core["total_damage"] > 0
    assert round(first_core["damage"], 5) == round(first_not_core["damage"] * 2.3, 5)


def test_boss_element_none_applies_no_advantage():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        boss_element=None,
        base_crit_rate=0.0,
    )
    assert result["total_damage"] == 10000.0


def test_burst_damage_with_no_buffs_uses_plain_percent_of_atk():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    # atk_for_hit = 2000 * 5.0 = 10000; no buffs, no enemy def -> damage == 10000
    assert result["total_damage"] == 10000.0


def test_burst_hit_counts_repeats_the_burst_percent_n_times_at_the_same_instant():
    # A burst that "attacks sequentially N times" (e.g. Cinderella's Glass
    # Slippers) deals N SEPARATE hits, each independently defense-subtracted -
    # not one hit at N*percent (defense is a flat subtraction per nikke.gg's
    # formula, so splitting into hits changes the total when enemy_def > 0).
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=500,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        burst_hit_counts={"attacker": 3},
    )
    burst_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert len(burst_hits) == 3
    # each hit: (2000 - 500) * 1.0 = 1500; all at the same instant.
    assert all(h["damage"] == 1500.0 for h in burst_hits)
    assert len({h["time"] for h in burst_hits}) == 1


def test_burst_hit_counts_defaults_to_one_hit():
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    assert len([e for e in result["damage_log"] if e["source"] == "burst"]) == 1


def test_instant_damage_pulse_deals_damage_at_full_burst_enter_using_casters_own_atk():
    # Some passives (e.g. Brid: Silent Track's Ignition Sequence) deal damage
    # on a trigger OTHER than the caster's own burst firing - not expressible
    # via burst_damage_percents (which is tied to own_burst_activate). An
    # "instant_damage_percent" pulse lets any trigger's action emit one, using
    # the caster's own ATK/live buffs exactly like a burst nuke.
    def deal_nuke(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("instant_damage_percent", 500.0, "self", caster_slug))

    rules_by_slug = {
        "buffer": [SkillRule(trigger="full_burst_enter", action=deal_nuke)],
        "midtier": [],
        "attacker": [],
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats={
            "buffer": {"atk": 2000, "def": 0, "max_hp": 0},
            "midtier": {"atk": 0, "def": 0, "max_hp": 0},
            "attacker": {"atk": 0, "def": 0, "max_hp": 0},
        },
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    instant_hits = [e for e in result["damage_log"] if e["source"] == "instant_nuke"]
    # full_burst_enter fires at t=5.0 in this deck; 2000 atk * 500% coefficient
    # Fires at the instant Full Burst opens, a beat after the tier-3 cast.
    assert len(instant_hits) == 1
    assert instant_hits[0]["time"] == pytest.approx(5.0)
    # It lands AT full_burst_start, so it is inside the window and worth 1.5x.
    assert fb_factor(result, instant_hits[0]["time"]) == 1.5
    assert {k: v for k, v in instant_hits[0].items() if k != "time"} == {
        "slug": "buffer", "damage": 10000.0 * 1.5, "source": "instant_nuke",
        "damage_type": "attack"}


def test_instant_damage_pulse_deals_damage_at_battle_start():
    def deal_nuke(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("instant_damage_percent", 100.0, "self", caster_slug))

    rules_by_slug = {"buffer": [SkillRule(trigger="battle_start", action=deal_nuke)], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats={
            "buffer": {"atk": 500, "def": 0, "max_hp": 0},
            "midtier": {"atk": 0, "def": 0, "max_hp": 0},
            "attacker": {"atk": 0, "def": 0, "max_hp": 0},
        },
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    instant_hits = [e for e in result["damage_log"] if e["source"] == "instant_nuke"]
    assert instant_hits == [{"slug": "buffer", "time": 0.0, "damage": 500.0, "source": "instant_nuke", "damage_type": "attack"}]


def test_instant_damage_pulse_deals_damage_at_full_burst_end():
    def deal_nuke(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("instant_damage_percent", 200.0, "self", caster_slug))

    rules_by_slug = {"buffer": [SkillRule(trigger="full_burst_end", action=deal_nuke)], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats={
            "buffer": {"atk": 1000, "def": 0, "max_hp": 0},
            "midtier": {"atk": 0, "def": 0, "max_hp": 0},
            "attacker": {"atk": 0, "def": 0, "max_hp": 0},
        },
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    instant_hits = [e for e in result["damage_log"] if e["source"] == "instant_nuke"]
    # full_burst_end at t=15.0 (full_burst_enter t=5.0 + FULL_BURST_DURATION 10.0)
    assert len(instant_hits) == 1
    assert instant_hits[0]["time"] == pytest.approx(15.0)
    assert {k: v for k, v in instant_hits[0].items() if k != "time"} == {
        "slug": "buffer", "damage": 2000.0, "source": "instant_nuke",
        "damage_type": "attack"}


def test_instant_damage_pulse_from_own_burst_activate_stacks_with_burst_nuke():
    # An own_burst_activate-triggered instant-damage pulse should ADD to the
    # tier's own burst_damage_percents nuke, not replace or conflict with it.
    def extra_nuke(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("instant_damage_percent", 100.0, "self", caster_slug))

    rules_by_slug = {
        "buffer": [],
        "midtier": [],
        "attacker": [SkillRule(trigger="own_burst_activate", action=extra_nuke)],
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    burst_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    instant_hits = [e for e in result["damage_log"] if e["source"] == "instant_nuke"]
    assert burst_hits == [{"slug": "attacker", "time": 5.0, "damage": 5000.0, "source": "burst", "damage_type": "attack"}]
    assert instant_hits == [{"slug": "attacker", "time": 5.0, "damage": 1000.0, "source": "instant_nuke", "damage_type": "attack"}]


def test_periodic_nuke_fires_repeatedly_on_its_own_fixed_cooldown():
    # A skill on its own fixed cooldown, independent of the burst cycle (e.g.
    # Helm: Aquamarine's Aegis Cannon Suppression Fire, cooldown 4s) - fires
    # at t=cooldown, 2*cooldown, ... regardless of burst timing.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=10.0,
        mode="auto",
        base_crit_rate=0.0,
        periodic_nukes={"buffer": {"cooldown": 4.0, "percent": 100.0}},
    )
    periodic_hits = [e for e in result["damage_log"] if e["source"] == "periodic"]
    assert [e["time"] for e in periodic_hits] == [4.0, 8.0]


def test_periodic_nuke_uses_the_casters_own_atk_and_live_buffs():
    def grant_atk(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 1.0, "self", None, caster_slug), applied_at=time)

    rules = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_atk)],
        "midtier": [],
        "attacker": [],
    }
    result = simulate_raid(
        make_deck(),
        rules,
        burst_damage_percents={},
        base_stats={
            "buffer": {"atk": 1000, "def": 0, "max_hp": 0},
            "midtier": {"atk": 0, "def": 0, "max_hp": 0},
            "attacker": {"atk": 0, "def": 0, "max_hp": 0},
        },
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=5.0,
        mode="auto",
        base_crit_rate=0.0,
        periodic_nukes={"buffer": {"cooldown": 4.0, "percent": 100.0}},
    )
    periodic_hits = [e for e in result["damage_log"] if e["source"] == "periodic"]
    # atk 1000 * (1 + 1.0 atk_percent buff) * 100% coefficient = 2000
    assert periodic_hits == [{"slug": "buffer", "time": 4.0, "damage": 2000.0, "source": "periodic", "damage_type": "attack"}]


def test_periodic_nuke_damage_type_gates_which_damage_up_buff_applies():
    # A "Sustained Damage +50%" squad buff must raise ONLY sustained-typed
    # damage, not a plain attack-typed instance in the same deck.
    def grant_sustained(context, caster_slug, time, registry):
        registry.add(Effect("sustained_damage_up", 0.5, "squad", None, caster_slug), applied_at=time)

    rules = {"buffer": [SkillRule(trigger="battle_start", action=grant_sustained)], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules,
        burst_damage_percents={},
        base_stats={
            "buffer": {"atk": 1000, "def": 0, "max_hp": 0},
            "midtier": {"atk": 0, "def": 0, "max_hp": 0},
            "attacker": {"atk": 1000, "def": 0, "max_hp": 0},
        },
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=5.0,
        mode="auto",
        base_crit_rate=0.0,
        periodic_nukes={
            "buffer": {"cooldown": 4.0, "percent": 100.0, "damage_type": "sustained"},
            "attacker": {"cooldown": 4.0, "percent": 100.0},
        },
    )
    hits = {e["slug"]: e for e in result["damage_log"] if e["source"] == "periodic"}
    assert hits["buffer"]["damage"] == 1500.0  # sustained-typed: 1000 * (1 + 0.5 sustained)
    assert hits["buffer"]["damage_type"] == "sustained"
    assert hits["attacker"]["damage"] == 1000.0  # attack-typed: sustained buff does not apply


def test_burst_nuke_damage_type_gates_type_specific_buff():
    def grant_pe(context, caster_slug, time, registry):
        registry.add(Effect("projectile_explosion_damage_up", 0.5, "squad", None, caster_slug), applied_at=time)

    rules = {"buffer": [SkillRule(trigger="battle_start", action=grant_pe)], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules,
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        burst_damage_types={"attacker": "projectile_explosion"},
    )
    burst_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert burst_hits[0]["damage"] == 15000.0  # 10000 * 1.0 coeff * (1 + 0.5 projectile explosion)
    assert burst_hits[0]["damage_type"] == "projectile_explosion"


def test_true_typed_nuke_ignores_enemy_defense_and_gets_true_damage_up():
    # Per nikke.gg glossary, True Damage ignores enemy DEF. A true-typed
    # instance subtracts no defense, and true_damage_up is type-gated in.
    def grant_true(context, caster_slug, time, registry):
        registry.add(Effect("true_damage_up", 1.0, "squad", None, caster_slug), applied_at=time)

    rules = {"buffer": [SkillRule(trigger="battle_start", action=grant_true)], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules,
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=2000,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        burst_damage_types={"attacker": "true"},
    )
    burst_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    # DEF ignored: base = 10000; * coeff 1.0 * damage_up (1 + 1.0 true) = 20000
    assert burst_hits[0]["damage"] == 20000.0
    assert burst_hits[0]["damage_type"] == "true"


def test_non_true_typed_nuke_still_subtracts_enemy_defense():
    # Sanity: only True Damage ignores DEF; other types subtract it normally.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=2000,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    burst_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert burst_hits[0]["damage"] == 8000.0  # (10000 - 2000) * 1.0 coeff, attack-typed


def test_rocket_launcher_normal_attacks_are_projectile_explosion_typed():
    # RL normal attacks are projectile explosions, so a squad Projectile
    # Explosion Damage buff raises them (on top of the still-global attack buff).
    def grant_pe(context, caster_slug, time, registry):
        registry.add(Effect("projectile_explosion_damage_up", 0.5, "squad", None, caster_slug), applied_at=time)

    weapon_stats = {
        "attacker": {"weapon": "RL", "damage_percent": 100.0, "max_ammo": 3,
                     "reload_time": 1.0, "charge_time": 1.0, "charge_damage_percent": 100.0},
    }
    kwargs = dict(
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000), enemy_def=0,
        gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0, weapon_stats=weapon_stats,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_pe = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="battle_start", action=grant_pe)], "midtier": [], "attacker": []},
        **kwargs,
    )
    na_without = [e for e in without["damage_log"] if e["source"] == "normal_attack"]
    na_with = [e for e in with_pe["damage_log"] if e["source"] == "normal_attack"]
    assert na_without and all(e["damage_type"] == "projectile_explosion" for e in na_without)
    assert sum(e["damage"] for e in na_with) > sum(e["damage"] for e in na_without)


def test_non_rocket_launcher_normal_attacks_are_attack_typed_and_ignore_pe_buff():
    def grant_pe(context, caster_slug, time, registry):
        registry.add(Effect("projectile_explosion_damage_up", 0.5, "squad", None, caster_slug), applied_at=time)

    weapon_stats = {
        "attacker": {"weapon": "MG", "damage_percent": 100.0, "max_ammo": 60,
                     "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0},
    }
    kwargs = dict(
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000), enemy_def=0,
        gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0, weapon_stats=weapon_stats,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_pe = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="battle_start", action=grant_pe)], "midtier": [], "attacker": []},
        **kwargs,
    )
    na_without = [e for e in without["damage_log"] if e["source"] == "normal_attack"]
    assert na_without and all(e["damage_type"] == "attack" for e in na_without)
    assert sum(e["damage"] for e in with_pe["damage_log"] if e["source"] == "normal_attack") == sum(
        e["damage"] for e in na_without
    )


def test_normal_attacks_deal_true_conversion_types_shots_only_while_active():
    # Takina Inoue's burst makes her normal attacks deal true damage for 10s.
    # Modeled as a self-scoped "normal_attacks_deal_true" effect the normal-
    # attack pass reads; only shots inside the window are true-typed.
    def convert(context, caster_slug, time, registry):
        registry.add(Effect("normal_attacks_deal_true", 1.0, "self", 10.0, caster_slug), applied_at=time)
        registry.add(Effect("true_damage_up", 1.0, "squad", None, caster_slug), applied_at=time)

    weapon_stats = {
        "attacker": {"weapon": "MG", "damage_percent": 100.0, "max_ammo": 60,
                     "reload_time": 0.5, "charge_time": 0.0, "charge_damage_percent": 0.0},
    }
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": [SkillRule(trigger="battle_start", action=convert)]},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000), enemy_def=0,
        gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0, weapon_stats=weapon_stats,
    )
    na = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    early = [e for e in na if e["time"] < 10.0]
    late = [e for e in na if e["time"] >= 10.0]
    assert early and all(e["damage_type"] == "true"
                        and e["damage"] == 20000.0 * fb_factor(result, e["time"])
                        for e in early)
    assert late and all(e["damage_type"] == "attack"
                       and e["damage"] == 10000.0 * fb_factor(result, e["time"])
                       for e in late)


def test_periodic_nukes_defaults_to_none_and_is_a_no_op():
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    assert not any(e["source"] == "periodic" for e in result["damage_log"])


def test_periodic_rules_apply_buffs_on_own_cooldown_before_damage_passes():
    # A Skill-1/2 with a cooldown first activates at t=cooldown, then repeats.
    # The debuff it applies must be visible to damage computed at those times,
    # so the periodic-rule pass runs before the burst cycle populates the log.
    periodic_rules = {
        "buffer": [(15.0, [buff_rule("periodic", [("damage_taken_up", 0.1, "squad", 5.0)])])],
    }
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=40.0,
        mode="auto",
        base_crit_rate=0.0,
        periodic_nukes={"attacker": {"cooldown": 1.0, "percent": 100.0}},
        periodic_rules=periodic_rules,
    )
    by_time = {round(e["time"], 3): e["damage"] for e in result["damage_log"] if e["source"] == "periodic"}
    # Each tick also carries its own window position, so the debuff is read
    # against a 1.5x baseline wherever the tick lands inside Full Burst.
    def expect(t, debuffed):
        return round(10000.0 * (1.1 if debuffed else 1.0) * fb_factor(result, t), 4)
    assert by_time[5.0] == expect(5.0, False)    # before first cd fire (t=15): no debuff
    assert by_time[15.0] == expect(15.0, True)   # debuff active [15, 20)
    assert by_time[19.0] == expect(19.0, True)
    assert by_time[25.0] == expect(25.0, False)  # expired at 20; next fire at 30
    assert by_time[30.0] == expect(30.0, True)   # second periodic firing


def test_periodic_rules_defaults_to_none_and_is_a_no_op():
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    assert result["total_damage"] > 0


def _ar_weapon(**over):
    w = {"weapon": "AR", "damage_percent": 10.0, "max_ammo": 100,
         "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0}
    w.update(over)
    return w


def test_per_shot_every_n_fires_a_nuke_at_each_nth_shot():
    # AR fires 12/s; "every 5 shots" -> nuke at counts 5 and 10 (indices 4, 9).
    per_shot_rules = {"attacker": [(5, "every", [instant_nuke_pulse_rule("per_shot", 100.0)])]}
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules=per_shot_rules,
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert [round(e["time"], 4) for e in ps] == [round(4 / 12, 4), round(9 / 12, 4)]
    # 100% coeff * atk 10000, no defense - times whatever each shot's own
    # window position is worth.
    assert all(e["damage"] == 10000.0 * fb_factor(result, e["time"]) for e in ps)


def test_per_shot_after_n_fires_a_nuke_once():
    per_shot_rules = {"attacker": [(3, "after", [instant_nuke_pulse_rule("per_shot", 100.0)])]}
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules=per_shot_rules,
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert len(ps) == 1
    assert round(ps[0]["time"], 4) == round(2 / 12, 4)  # count 3 = index 2


def test_per_shot_nuke_takes_the_bonus_when_its_own_shot_lands_in_a_window():
    # A per-shot instant nuke is computed at its shot's time, which has nothing
    # to do with the caster's burst, so the bonus follows whichever shots
    # happen to land inside a window. gauge_charge_time=0.1 -> window
    # [0.1, 10.1); the "after 3" shot lands at t=2/12=0.1667, inside it.
    per_shot_rules = {
        "attacker": [(3, "after", [instant_nuke_pulse_rule("per_shot", 100.0)])]
    }
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=0.1,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules=per_shot_rules,
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert len(ps) == 1
    assert ps[0]["damage"] == 15000.0  # 10000 * (1 + full_burst_bonus*0.5) = 10000*1.5


def test_per_shot_last_bullet_fires_a_nuke_when_the_magazine_empties():
    # gap #1's residual "last bullet" trigger (e.g. Julia's Crescendo) - a
    # "last_bullet" mode entry (threshold unused) fires on the shot that
    # actually empties its magazine, not on a fixed count. AR (12/s), 3-round
    # magazine, 1s reload -> magazines empty at t=2/12 and t=1.25+2/12.
    per_shot_rules = {"attacker": [(None, "last_bullet", [instant_nuke_pulse_rule("per_shot", 100.0)])]}
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=2.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=3)},
        per_shot_rules=per_shot_rules,
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert len(ps) == 2
    # 3-round AR magazine empties at 3/12; the reload is the file 1.25 plus the
    # fixed 0.148 segment, so the second magazine's last bullet is 0.148 later.
    assert [round(e["time"], 4) for e in ps] == [
        round(2 / 12, 4), round(1.398 + 2 / 12, 4)]


def _windowed_nuke_result(mode, threshold):
    return simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=0.1,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules={"attacker": [(threshold, mode, [instant_nuke_pulse_rule("per_shot", 100.0)])]},
    )


def test_per_shot_every_during_full_burst_fires_only_on_in_window_shots():
    # gap #7: "every 3 normal attacks during Full Burst" counts only shots
    # inside a Full Burst window before the every-3rd step (e.g. Soda's Lucky
    # Golden Chip). Compute the expected in-window every-3rd shots from the
    # sim's own Full Burst window so the assertion doesn't hardcode cycle timing.
    result = _windowed_nuke_result("every_during_full_burst", 3)
    windows = list(zip(
        (e["time"] for e in result["events"] if e["type"] == "full_burst_start"),
        (e["time"] for e in result["events"] if e["type"] == "full_burst_end"),
    ))
    shots = [k / 12 for k in range(12)]  # AR 12/s, max_ammo 100 -> no reload in 1s
    in_window = [t for t in shots if any(s <= t < e for s, e in windows)]
    expected = [t for i, t in enumerate(in_window) if (i + 1) % 3 == 0]
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert len(ps) >= 1  # the window is reached, so the mode is actually exercised
    assert [round(e["time"], 4) for e in ps] == [round(t, 4) for t in expected]
    assert all(any(s <= e["time"] < end for s, end in windows) for e in ps)


def test_per_shot_every_during_own_status_window_gated_to_own_burst_window():
    # gap #7: "every 3 shots while in <own status>" (e.g. Asuka's Anti A.T.
    # Field nuke) anchors the window to the CASTER'S OWN burst times, not the
    # squad Full Burst window. threshold carries (N, window_duration).
    result = _windowed_nuke_result("every_during_own_status_window", (3, 9.0))
    own_bursts = [
        e["time"] for e in result["events"] if e["type"] == "burst" and e["slug"] == "attacker"
    ]
    windows = [(bt, bt + 9.0) for bt in own_bursts]
    shots = [k / 12 for k in range(12)]
    in_window = [t for t in shots if any(s <= t < e for s, e in windows)]
    expected = [t for i, t in enumerate(in_window) if (i + 1) % 3 == 0]
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert len(ps) >= 1
    assert [round(e["time"], 4) for e in ps] == [round(t, 4) for t in expected]
    # 100% coeff * atk 10000, no defense - times whatever each shot's own
    # window position is worth.
    assert all(e["damage"] == 10000.0 * fb_factor(result, e["time"]) for e in ps)


def test_own_status_window_can_open_on_only_every_nth_burst():
    # Neon: Vision Eye's Firepower Gauge is spent by the Super Firepower it
    # triggers and takes two more bursts to refill, so the status window opens
    # on her 1st, 4th, 7th ... burst - not on every one. An optional third
    # element on the threshold names that burst period.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=0.1,
        fight_duration=260.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules={"attacker": [
            ((1, 5.0, 3), "every_during_own_status_window",
             [instant_nuke_pulse_rule("per_shot", 100.0)])]},
    )
    own_bursts = [
        e["time"] for e in result["events"] if e["type"] == "burst" and e["slug"] == "attacker"
    ]
    assert len(own_bursts) >= 4  # or the test cannot tell "every" from "every 3rd"
    windows = [(bt, bt + 5.0) for bt in own_bursts[::3]]
    fires = [e["time"] for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert fires
    assert all(any(s <= t < e for s, e in windows) for t in fires)
    # The skipped bursts really are skipped, not merely rarer.
    skipped = [(bt, bt + 5.0) for i, bt in enumerate(own_bursts) if i % 3]
    assert not any(any(s <= t < e for s, e in skipped) for t in fires)


def test_pierce_damage_up_reaches_normal_attacks_but_not_a_skill_nuke():
    """Pierce Damage Up buffs Pierce - "normal attacks hitting everything in
    their path" - so a unit who HAS Pierce still does not collect it on her
    skill damage. Measured on Snow White: Heavy Arms (Fienn, range footage
    2026-07-28): one Auto Fire round against the same shot's 41.9% sweep reads
    a Damage-Up bucket of 1 + 0.8448, where the engine was supplying
    1 + 0.8448 + 0.1309 - the extra term being exactly her pierce_damage_up.
    """
    def grant(context, caster_slug, time, registry):
        registry.add(Effect("has_pierce", 1.0, "self", None, caster_slug), applied_at=time)
        registry.add(Effect("pierce_damage_up", 0.5, "self", None, caster_slug), applied_at=time)

    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [],
         "attacker": [SkillRule(trigger="battle_start", action=grant)]},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules={"attacker": [(1, "every", [instant_nuke_pulse_rule("per_shot", 100.0)])]},
    )
    shot = next(e for e in result["damage_log"] if e["source"] == "normal_attack")
    nuke = next(e for e in result["damage_log"] if e["source"] == "per_shot_nuke")
    per_coefficient = shot["damage"] / (_ar_weapon()["damage_percent"] / 100)

    # ATK 10000, no defense, no crit, and no Full Burst inside this 1-sec fight,
    # so the only thing left in either instance is the Damage-Up bucket.
    assert per_coefficient == pytest.approx(10000.0 * 1.5)   # normal attack: 1 + 0.5
    assert nuke["damage"] == pytest.approx(10000.0)          # skill nuke: 1, no pierce


def test_per_shot_nuke_damage_type_reaches_its_type_bucket_and_the_log():
    # The pulse path carries a damage_type (default "attack"), so a per-shot
    # nuke whose text says "as Distributed Damage" (e.g. Scarlet's 6th/9th
    # Fleetly Fading Breakthrough stages) is boosted by distributed_damage_up
    # and logged with its type.
    def grant_distributed_up(context, caster_slug, time, registry):
        registry.add(Effect("distributed_damage_up", 0.5, "squad", None, caster_slug), applied_at=time)

    per_shot_rules = {
        "attacker": [(3, "after", [instant_nuke_pulse_rule("per_shot", 100.0, damage_type="distributed")])]
    }
    result = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="battle_start", action=grant_distributed_up)], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules=per_shot_rules,
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert len(ps) == 1
    assert ps[0]["damage_type"] == "distributed"
    assert ps[0]["damage"] == 15000.0  # 10000 * (1 + 0.5 distributed_damage_up)


def test_per_shot_every_outside_full_burst_fires_only_on_out_of_window_shots():
    # The complement of gap #7's "every_during_full_burst" (e.g. Velvet's
    # Sticky Fingers, "when attacking with Full Charge while NOT in Full
    # Burst"): only shots OUTSIDE every Full Burst window are counted before
    # the every-Nth step. gauge_charge_time=0.5 leaves the shots before
    # t=0.5 outside the window, so the every-3rd step is actually reached.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=0.5,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules={"attacker": [(3, "every_outside_full_burst", [instant_nuke_pulse_rule("per_shot", 100.0)])]},
    )
    windows = list(zip(
        (e["time"] for e in result["events"] if e["type"] == "full_burst_start"),
        (e["time"] for e in result["events"] if e["type"] == "full_burst_end"),
    ))
    shots = [k / 12 for k in range(12)]  # AR 12/s, max_ammo 100 -> no reload in 1s
    out_of_window = [t for t in shots if not any(s <= t < e for s, e in windows)]
    expected = [t for i, t in enumerate(out_of_window) if (i + 1) % 3 == 0]
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert len(ps) >= 1  # some shots do fall outside the window
    assert [round(e["time"], 4) for e in ps] == [round(t, 4) for t in expected]
    assert all(not any(s <= e["time"] < end for s, end in windows) for e in ps)


def _sequence_result(spec, gauge_charge_time):
    # Three stages with distinct percents so the damage log tells apart WHICH
    # stage fired (100/200/300% of atk 10000 -> 10000/20000/30000).
    stage_rules = [
        [instant_nuke_pulse_rule("per_shot", 100.0)],
        [instant_nuke_pulse_rule("per_shot", 200.0)],
        [instant_nuke_pulse_rule("per_shot", 300.0)],
    ]
    return simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=gauge_charge_time,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules={"attacker": [(spec, "sequence", stage_rules)]},
    )


def test_per_shot_sequence_fires_staged_effects_on_a_repeating_cycle():
    # gap #10 base behaviour (Scarlet's Fleetly Fading Breakthrough): a single
    # running shot counter fires stage 1 at its 3rd shot, stage 2 at the 6th,
    # stage 3 at the 9th, then resets and starts over. gauge_charge_time=5.0
    # keeps every shot before the first burst, so only base requirements apply.
    spec = {"requirements": [3, 6, 9]}
    result = _sequence_result(spec, gauge_charge_time=5.0)
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    # AR 12/s: stages at counts 3/6/9 (t=2/12, 5/12, 8/12), then the cycle
    # restarts and stage 1 fires again at the 12th shot (t=11/12).
    assert [(round(e["time"], 4), e["damage"]) for e in ps] == [
        (round(2 / 12, 4), 10000.0),
        (round(5 / 12, 4), 20000.0),
        (round(8 / 12, 4), 30000.0),
        (round(11 / 12, 4), 10000.0),
    ]


def test_per_shot_sequence_own_burst_window_swaps_requirements_and_carries_the_count():
    """Fienn's scenario (2026-07-27), stated in his own words: Scarlet satisfies
    Skill 1's "6 times" condition just before bursting, and then her very NEXT
    normal attack satisfies the "9 times" condition, because the burst rewrote
    the requirement table to 1/2/3 while the running count carried over.

    Expectations are hardcoded rather than replayed from the same algorithm -
    a test that recomputes what it is checking cannot catch the boundary being
    wrong, which is exactly the boundary in question.
    """
    from app.raid_simulator import _sequence_fire_rules

    spec = {"requirements": [3, 6, 9], "own_burst_window": (10.0, [1, 2, 3])}
    stages = ["stage-1", "stage-2", "stage-3"]
    shots = [float(t) for t in range(1, 13)]
    fires = _sequence_fire_rules(spec, stages, shots, own_burst_times=[6.5])

    assert [fires.get(t) for t in shots] == [
        None, None, "stage-1",      # base table: 3rd shot
        None, None, "stage-2",      # base table: 6th shot - then she bursts
        "stage-3",                  # count 7 vs the window's 3 -> fires at once
        "stage-1", "stage-2", "stage-3",   # and every shot fires from here
        "stage-1", "stage-2",
    ]


def test_per_shot_sequence_carries_progress_back_out_of_the_burst_window():
    # The complement: progress made under the 1/2/3 table is not lost when the
    # window closes - stage 2 still needs the BASE requirement of 6 after it.
    from app.raid_simulator import _sequence_fire_rules

    spec = {"requirements": [3, 6, 9], "own_burst_window": (2.5, [1, 2, 3])}
    stages = ["stage-1", "stage-2", "stage-3"]
    shots = [float(t) for t in range(1, 9)]
    fires = _sequence_fire_rules(spec, stages, shots, own_burst_times=[0.5])

    assert [fires.get(t) for t in shots] == [
        "stage-1", "stage-2",       # inside the window: counts 1 and 2
        None, None, None,           # window shut at 3.0; stage 3 now needs 9
        None, None, None,
    ]


def test_per_shot_squad_buff_reaches_a_burst_nuke_computed_earlier():
    # The record-then-compute payoff: buffer's per-shot squad debuff (applied at
    # its 1st shot, t=0) must raise the attacker's burst nuke fired later.
    per_shot_rules = {
        "buffer": [(1, "after", [buff_rule("per_shot", [("damage_taken_up", 0.5, "squad", 999.0)])])],
    }
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"buffer": _ar_weapon()},
        per_shot_rules=per_shot_rules,
    )
    burst = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert burst  # attacker's burst nuke exists
    assert burst[0]["damage"] == 15000.0  # 10000 * 1.0 * (1 + 0.5 damage_taken)


def test_per_shot_refreshing_buff_does_not_stack_across_shots():
    # A per-shot buff re-applied every shot must REFRESH to a single value, not
    # stack. buffer's AR fires 12/s; a stacking 0.1 damage_taken would balloon,
    # a refreshing one stays 0.1 -> attacker burst = 10000 * 1.1.
    per_shot_rules = {
        "buffer": [(1, "every", [refreshing_buff_rule("per_shot", [("damage_taken_up", 0.1, "squad", 3.0)])])],
    }
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"buffer": _ar_weapon()},
        per_shot_rules=per_shot_rules,
    )
    burst = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert burst[0]["damage"] == 11000.0  # 10000 * (1 + single 0.1), not stacked


def test_on_tier_fire_records_burst_times_on_the_context():
    seen = {}

    def capture(context, caster_slug, time, registry):
        seen["times"] = {slug: list(times) for slug, times in context.burst_times.items()}

    rules_by_slug = {
        "buffer": [],
        "midtier": [],
        "attacker": [SkillRule(trigger="own_burst_activate", action=capture)],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=8.0,  # one cycle
        mode="auto",
    )
    # attacker's own_burst_activate (tier 3) fires after tier 1/2 the same cycle,
    # so all three burst times are recorded by then.
    assert seen["times"]["midtier"] == [5.0]
    assert seen["times"]["attacker"] == [5.0]


def test_round_grant_buffs_only_the_affected_units_first_shot_after_grant():
    # A "for 1 round" (bullet-count) buff granted at Full Burst enter is consumed
    # by the affected ally's NEXT single shot, then gone. AR fires 12/sec, FB
    # enters at t=5.0, so the attacker's first shot at/after 5.0 is index 60
    # (t=5.0); it alone is buffed - the prior shot and the following shot aren't.
    rule = round_buff_rule("full_burst_enter", [("damage_taken_up", 0.5, "squad")], shots=1)
    result = simulate_raid(
        make_deck(),
        {"buffer": [rule], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=6.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
    )
    na = {round(e["time"], 4): e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack"}
    fb = lambda time: fb_factor(result, time)
    # Full Burst opens just AFTER the tier-3 cast at 5.0, so the shot landing
    # exactly at 5.0 is still pre-window; the covered shot is the next one.
    # Every expectation carries its own Full Burst factor, so what is being
    # asserted is the round grant's 1.5x and nothing else.
    assert na[round(5.0, 4)] == 1000.0 * fb(5.0)          # cast instant: unbuffed, pre-window
    assert na[round(61 / 12, 4)] == 1500.0 * fb(61 / 12)  # covered: 1000 * (1 + 0.5 damage_taken)
    assert na[round(62 / 12, 4)] == 1000.0 * fb(62 / 12)  # next shot: grant consumed


def test_round_grant_re_grants_each_cycle_without_stacking():
    # Re-granted every Full Burst; each cycle it buffs that cycle's first post-FB
    # shot only. A 30s squad CDR forces cycles at t=5 and t=20; the mid-cycle shot
    # at t=12 stays unbuffed (not continuous), and neither covered shot stacks.
    grant = round_buff_rule("full_burst_enter", [("damage_taken_up", 0.5, "squad")], shots=1)

    def emit_cdr(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 30.0, "squad", caster_slug))

    result = simulate_raid(
        make_deck(),
        {"buffer": [grant, SkillRule(trigger="full_burst_end", action=emit_cdr)], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=25.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=1000)},  # no reload over 25s -> clean k/12 shots
    )
    na = {round(e["time"], 4): e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack"}
    # Each cycle's covered shot is the first one strictly after Full Burst
    # opens, which is a beat after the tier-3 cast at 5.0 / 20.0.
    fb = lambda time: fb_factor(result, time)
    assert na[round(61 / 12, 4)] == 1500.0 * fb(61 / 12)     # cycle 1 covered shot
    assert na[round(241 / 12, 4)] == 1500.0 * fb(241 / 12)   # cycle 2 covered shot
    assert na[round(12.0, 4)] == 1000.0 * fb(12.0)           # mid-cycle: unbuffed (not continuous)
    assert na[round(242 / 12, 4)] == 1000.0 * fb(242 / 12)   # after cycle-2 covered: consumed


def test_round_grant_squad_scope_consumes_per_ally_first_shot():
    # A squad "for 1 round" buff is consumed independently by EACH affected ally's
    # own next shot. Two weapon-holders both get their first post-FB shot buffed.
    rule = round_buff_rule("full_burst_enter", [("damage_taken_up", 0.5, "squad")], shots=1)
    result = simulate_raid(
        make_deck(),
        {"buffer": [rule], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats={
            "buffer": {"atk": 0, "def": 0, "max_hp": 0},
            "midtier": {"atk": 10000, "def": 0, "max_hp": 0},
            "attacker": {"atk": 10000, "def": 0, "max_hp": 0},
        },
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=6.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"midtier": _ar_weapon(), "attacker": _ar_weapon()},
    )
    # First shot strictly after Full Burst opens (a beat past the 5.0 cast).
    covered = [e for e in result["damage_log"]
               if e["source"] == "normal_attack" and round(e["time"], 4) == round(61 / 12, 4)]
    assert {e["slug"] for e in covered} == {"midtier", "attacker"}
    # each ally's own first shot buffed; inside the window, so also x1.5
    assert all(e["damage"] == 2250.0 for e in covered)


ZWEI_PIERCE_EQUATION = {
    "pierce_equation": {
        "description_value_01": "20.13", "description_value_02": "1", "description_value_03": "10.06",
        "description_value_04": "10", "description_value_05": "24.99", "description_value_06": "3",
        "description_value_07": "1",
    },
}


def _zwei_pierce_stacks_per_sniper_shot(per_shot_rules):
    """Zwei (SG, 1.5 shots/sec) granting Pierce Equation's "for 1 round" squad
    pierce on each of her Full Burst normal attacks, alongside an SR ally whose
    reload gap (5 charges, then 2 sec reload) lets grants pile up. Returns each
    of the sniper's shot times mapped to how many 24.99% pierce stacks its
    damage reflects."""
    deck = [
        {"slug": "zwei", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "sniper", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    result = simulate_raid(
        deck,
        # Pierce Damage Up credits only a unit that HAS Pierce, so the sniper
        # this test measures has to hold the property for the grants to show.
        {"zwei": [], "midtier": [],
         "sniper": [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]},
        burst_damage_percents={},
        base_stats={
            "zwei": {"atk": 0, "def": 0, "max_hp": 0},
            "midtier": {"atk": 0, "def": 0, "max_hp": 0},
            "sniper": {"atk": 10000, "def": 0, "max_hp": 0},
        },
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=16.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={
            "zwei": {"weapon": "SG", "damage_percent": 10.0, "max_ammo": 9,
                     "reload_time": 1.5, "charge_time": 0.0, "charge_damage_percent": 0.0},
            "sniper": {"weapon": "SR", "damage_percent": 10.0, "max_ammo": 5,
                       "reload_time": 2.0, "charge_time": 1.5, "charge_damage_percent": 10.0},
        },
        per_shot_rules={"zwei": per_shot_rules},
    )
    shots = [e for e in result["damage_log"]
             if e["source"] == "normal_attack" and e["slug"] == "sniper"]
    # Divide the Full Burst bonus back out before counting stacks: it is a
    # major modifier, so it multiplies a shot's damage alongside the pierce
    # stacks this helper is trying to read, and every sniper shot here lands
    # inside a window while the unbuffed baseline need not.
    plain = {round(e["time"], 4): e["damage"] / fb_factor(result, e["time"]) for e in shots}
    unbuffed = min(plain.values())
    return {time: round((damage / unbuffed - 1) / 0.2499, 4) for time, damage in plain.items()}


def test_uncapped_round_grants_pile_up_on_a_charge_weapon_allys_post_reload_shot():
    # Baseline for the cap: without one, every grant Zwei made during the SR's
    # charge+reload gap lands on the single shot that ends it. The gap is 3.648
    # sec (the reload carries the fixed 0.148 segment), which fits six grants.
    uncapped = round_buff_rule("per_shot", [("pierce_damage_up", 0.2499, "squad")], shots=1)
    stacks = _zwei_pierce_stacks_per_sniper_shot([(1, "every_during_full_burst", [uncapped])])
    assert stacks[round(11.148, 4)] == 6.0
    assert max(stacks.values()) == 6.0


def test_capped_round_grant_holds_a_charge_weapon_ally_to_the_skills_stack_cap():
    # Pierce Equation "stacks up to 3 time(s)": the SR's post-reload shot must
    # see 3 stacks, not the 5 grants that overlap it. Faster shots, which never
    # hold more than a stack or two, are untouched by the cap.
    stacks = _zwei_pierce_stacks_per_sniper_shot(
        build_pierce_equation_per_shot_rules(ZWEI_PIERCE_EQUATION)
    )
    assert stacks[round(11.148, 4)] == 3.0
    assert max(stacks.values()) == 3.0
    assert stacks[round(6.0, 4)] == 1.0      # mid-magazine shot: one grant only
    assert stacks[round(12.648, 4)] == 2.0   # 1.5-sec gap: two grants, under the cap


def test_miranda_top_atk_burst_buff_reaches_the_top_two_carries_end_to_end():
    # End-to-end: Miranda's Powering Up (highest_atk_buff_rule -> "slugs:" scope,
    # applied at her tier-1 burst) must raise the two highest-ATK carries' own
    # burst nukes (fired later the same cycle) via record-then-compute, and leave
    # the caster out. Proves top-N ranking + slugs scope integrate in simulate_raid.
    from app.skill_rules.miranda import build_miranda_rules

    miranda_values = {
        "wake_up": {
            "description_value_01": "32.99", "description_value_02": "10", "description_value_03": "30.1",
            "description_value_04": "10", "description_value_05": "23.7", "description_value_06": "10",
            "description_value_07": "1", "description_value_08": "85.42", "description_value_09": "1",
        },
        "powering_up": {
            "description_value_01": "2", "description_value_02": "40.4", "description_value_03": "10",
            "description_value_04": "56.23", "description_value_05": "10",
        },
    }
    deck = [
        {"slug": "miranda", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "carry_b", "burst_tier": 2, "element": "Fire", "cooldown": 20.0},
        {"slug": "carry_a", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]
    base_stats = {
        "miranda": {"atk": 40000, "def": 0, "max_hp": 0},
        "carry_b": {"atk": 80000, "def": 0, "max_hp": 0},
        "carry_a": {"atk": 90000, "def": 0, "max_hp": 0},
    }
    result = simulate_raid(
        deck,
        {"miranda": build_miranda_rules(miranda_values), "carry_b": [], "carry_a": []},
        burst_damage_percents={"carry_a": 100.0, "carry_b": 100.0},
        base_stats=base_stats,
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    burst = {e["slug"]: e["damage"] for e in result["damage_log"] if e["source"] == "burst"}
    # both carries are the top-2 highest ATK -> ATK +40.4% on their burst nukes
    assert round(burst["carry_a"], 2) == round(90000 * 1.404, 2)
    assert round(burst["carry_b"], 2) == round(80000 * 1.404, 2)


def test_round_grants_default_to_none_and_are_a_no_op():
    # No round buffs -> normal attacks are computed exactly as before.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=6.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
    )
    na = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert na and all(e["damage"] == 1000.0 * fb_factor(result, e["time"]) for e in na)


def test_per_shot_rules_defaults_to_none_and_is_a_no_op():
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    assert not any(e["source"] == "per_shot_nuke" for e in result["damage_log"])
    assert result["total_damage"] > 0


def test_own_burst_activate_only_fires_for_the_unit_whose_tier_just_fired():
    fired = []

    def record(context, caster_slug, time, registry):
        fired.append(caster_slug)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="own_burst_activate", action=record)],
        "midtier": [SkillRule(trigger="own_burst_activate", action=record)],
        "attacker": [SkillRule(trigger="own_burst_activate", action=record)],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    # each unit's own_burst_activate should fire exactly once, for itself only
    assert sorted(fired) == ["attacker", "buffer", "midtier"]


def test_ally_burst_activate_lets_a_unit_react_to_another_units_burst():
    # A unit's rule reacts to a DIFFERENT unit bursting (e.g. Prika's Encore on
    # Mint's Sing Along). buffer's ally_burst_activate rule keyed on
    # ally_bursted("attacker") applies a squad debuff that, via
    # record-then-compute, reaches attacker's own burst nuke fired that instant.
    def apply_debuff(context, caster_slug, time, registry):
        registry.add(Effect("damage_taken_up", 0.5, "squad", None, caster_slug), applied_at=time)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="ally_burst_activate", condition=ally_bursted("attacker"), action=apply_debuff)],
        "midtier": [],
        "attacker": [],
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    burst = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert burst[0]["damage"] == 15000.0  # 10000 * (1 + 0.5 damage_taken)


def test_ally_burst_activate_gates_on_which_unit_bursted():
    # The same reacting rule keyed on ally_bursted("midtier") must fire ONLY when
    # midtier bursts, never on any other unit's burst.
    fired = []

    def note(context, caster_slug, time, registry):
        fired.append(context.last_burst_slug)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="ally_burst_activate", condition=ally_bursted("midtier"), action=note)],
        "midtier": [],
        "attacker": [],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    assert fired  # fired at least once
    assert all(slug == "midtier" for slug in fired)  # never on another unit's burst


def test_cooldown_reduction_pulse_from_full_burst_end_enables_a_second_cycle():
    def emit_cdr_pulse(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 30.0, "squad", caster_slug))

    rules_by_slug = {
        "buffer": [SkillRule(trigger="full_burst_end", action=emit_cdr_pulse)],
        "midtier": [],
        "attacker": [],
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=35.0,
        mode="auto",
    )
    # Without the pulse, cycle 2 (fire_time=20) would need attacker's 40s
    # cooldown satisfied (used at t=5, ready at t=45) - it isn't. A 30s
    # reduction applied to every Nikke's last-used-at at t=15 makes tier1/2
    # (20s cooldown, needs >=5s reduction) AND attacker (40s cooldown, needs
    # >=25s reduction) all eligible again by t=20.
    attacker_hits = [e for e in result["damage_log"] if e["slug"] == "attacker"]
    # The second cycle starts one FULL_BURST_OPEN_DELAY later than the first,
    # since each Full Burst now opens a beat after the cast that triggers it.
    assert [e["time"] for e in attacker_hits] == pytest.approx([5.0, 20.0])


def test_self_scoped_cdr_only_reduces_the_casters_cooldown():
    # A self-scoped burst-cooldown pulse (e.g. Blanc's own CDR) must reduce only
    # the caster's cooldown, not the whole squad's - otherwise it would speed up
    # the dealers' rotation too. Here the attacker self-CDRs 25s; the 2nd cycle
    # stays gunner-gated at t=45 (gunner's 40s cooldown is untouched), NOT the
    # t=20 a squad-wide CDR would produce.
    deck = [
        {"slug": "gunner", "burst_tier": 1, "element": "Iron", "cooldown": 40.0},
        {"slug": "mid", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]

    def self_cdr(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 25.0, "self", caster_slug))

    rules = {"gunner": [], "mid": [], "attacker": [SkillRule(trigger="full_burst_end", action=self_cdr)]}
    result = simulate_raid(
        deck,
        rules,
        burst_damage_percents={},
        base_stats={s: {"atk": 0, "def": 0, "max_hp": 0} for s in ("gunner", "mid", "attacker")},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=60.0,
        mode="auto",
    )
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    assert starts == pytest.approx([5.0, 45.0])


def test_full_burst_enter_and_full_burst_end_triggers_fire_for_all_members():
    enter_calls = []
    end_calls = []

    rules_by_slug = {
        "buffer": [
            SkillRule(trigger="full_burst_enter", action=lambda c, s, t, r: enter_calls.append((s, t))),
            SkillRule(trigger="full_burst_end", action=lambda c, s, t, r: end_calls.append((s, t))),
        ],
        "midtier": [],
        "attacker": [],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    assert [c[0] for c in enter_calls] == ["buffer"]
    assert [c[0] for c in end_calls] == ["buffer"]
    # Full Burst opens just after the tier-3 cast at 5.0, and runs 10 sec.
    assert enter_calls[0][1] == pytest.approx(5.0)
    assert end_calls[0][1] == pytest.approx(15.0)


def test_normal_attack_damage_is_accumulated_for_magazine_weapons():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    weapon_stats = {
        "attacker": {
            "weapon": "AR", "damage_percent": 10.0, "max_ammo": 2,
            "reload_time": 100.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        weapon_stats=weapon_stats,
        base_crit_rate=0.0,
    )
    # AR fires at 12/sec (Fienn's 60fps table); with a 100s reload, only the
    # first magazine's shots within the 1s fight matter: shots at t=0 and
    # t=1/12 (2nd shot at 2/12=0.1667s is still <1.0, so both of the 2-round
    # magazine's shots land). damage_percent=10% -> atk_for_hit=100 each hit.
    normal_hits = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert len(normal_hits) == 2
    assert all(e["damage"] == 100.0 for e in normal_hits)
    assert result["total_damage"] == 200.0


def test_normal_attack_schedule_speeds_up_after_a_reload_speed_buff():
    # A permanent (e.g. overload-sourced) reload_speed_percent buff granted
    # at battle_start should shorten every subsequent reload, producing more
    # shots within the same fight_duration than the unbuffed case.
    def grant_reload_speed(context, caster_slug, time, registry):
        registry.add(
            Effect("reload_speed_percent", 1.0, "self", None, "attacker"), applied_at=time
        )

    weapon_stats = {
        "attacker": {
            "weapon": "AR", "damage_percent": 10.0, "max_ammo": 2,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }
    }
    unbuffed = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=3.0,
        mode="auto",
        weapon_stats=weapon_stats,
    )
    buffed = simulate_raid(
        make_deck(),
        {
            "buffer": [SkillRule(trigger="battle_start", action=grant_reload_speed)],
            "midtier": [],
            "attacker": [],
        },
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=3.0,
        mode="auto",
        weapon_stats=weapon_stats,
    )
    unbuffed_shots = [e for e in unbuffed["damage_log"] if e["source"] == "normal_attack"]
    buffed_shots = [e for e in buffed["damage_log"] if e["source"] == "normal_attack"]
    assert len(buffed_shots) > len(unbuffed_shots)


def test_privaty_ex_magazine_reload_buff_speeds_up_squad_reloads_end_to_end():
    # Regression guard: Privaty's real EX Magazine, built from its actual skill
    # values, must feed its squad-wide reload_speed_percent buff into an ally's
    # normal-attack schedule. Measured on the reload GAP directly rather than
    # net shot count, because EX Magazine also cuts max ammo, which otherwise
    # masks the reload benefit in a raw shot tally (that interaction is real -
    # see the ammo-reduction test - just not what this test is isolating).
    #
    # The ally's first magazine starts at t=0 (before Full Burst at ~2.2s, so
    # its size is unreduced), fires 36 AR rounds at 12/sec, and empties at
    # t=3.0s - inside the buff window - so its reload is the one that should
    # speed up.
    deck = [
        {"slug": "privaty", "burst_tier": 3, "element": "Water", "cooldown": 40.0},
        {"slug": "ally", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    ]
    base_stats = {s: {"atk": 1000, "def": 0, "max_hp": 0} for s in ("privaty", "ally", "b2")}
    weapon_stats = {
        "ally": {
            "weapon": "AR", "damage_percent": 10.0, "max_ammo": 36,
            "reload_time": 3.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }
    }

    def second_magazine_start(rules):
        result = simulate_raid(
            deck, rules, burst_damage_percents={}, base_stats=base_stats, enemy_def=0,
            gauge_charge_time=2.0, fight_duration=8.0, mode="manual", weapon_stats=weapon_stats,
        )
        shots = [e["time"] for e in result["damage_log"] if e["source"] == "normal_attack"]
        # 36-round first magazine -> shot index 36 is the second magazine's first shot
        return shots[36]

    with_ex = second_magazine_start(
        {"privaty": build_ex_magazine_rules(PRIVATY_EX_MAGAZINE), "ally": [], "b2": []}
    )
    without_ex = second_magazine_start({"privaty": [], "ally": [], "b2": []})

    # without buff: 2nd magazine at 3.0 (empty) + 3.148 (file 3.0 reload plus
    # the fixed segment) = 6.148s. With the buff the scaled part shrinks by
    # 51.16%, so the magazine starts earlier.
    assert without_ex == pytest.approx(6.148)
    assert with_ex < without_ex


def test_ammo_increase_and_decrease_both_apply_to_base_ammo_through_the_registry():
    # End-to-end version of test_attack_rate's additive-on-base test, driven by
    # real summed Effects: a +200% ammo buff and a -50.66% ammo reduction (the
    # magnitudes of a maxed overload option and Privaty's EX Magazine) net to
    # base*(1 + 2.0 - 0.5066), i.e. the reduction comes off BASE, never off the
    # 3x-overloaded total (which would give 444, not 748). Both are applied at
    # battle_start so both are active when the single magazine starts at t=0 -
    # this test targets the base-only summing math, not EX Magazine's full-
    # burst timing (magazine size is evaluated at each magazine's start).
    deck = [
        {"slug": "gunner", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    base_stats = {s: {"atk": 1000, "def": 0, "max_hp": 0} for s in ("gunner", "b2", "b3")}
    weapon_stats = {
        "gunner": {
            "weapon": "MG", "damage_percent": 1.0, "max_ammo": 300,
            "reload_time": 1000.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }
    }

    def grant_ammo_effects(context, caster_slug, time, registry):
        registry.add(Effect("max_ammo_percent", 2.0, "self", None, "gunner"), applied_at=time)
        registry.add(Effect("max_ammo_percent", -0.5066, "self", None, "gunner"), applied_at=time)

    result = simulate_raid(
        deck,
        {"gunner": [SkillRule(trigger="battle_start", action=grant_ammo_effects)], "b2": [], "b3": []},
        burst_damage_percents={},
        base_stats=base_stats,
        enemy_def=0,
        gauge_charge_time=2.0,
        # end before the 1000s reload so all shots come from the one first
        # magazine, whose size is exactly what's under test.
        fight_duration=20.0,
        mode="manual",
        weapon_stats=weapon_stats,
    )
    shots = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert len(shots) == 748


def test_normal_attack_damage_uses_live_buffs_at_shot_time():
    def grant_atk_buff(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 1.0, "self", None, "attacker"), applied_at=time)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_atk_buff)],
        "midtier": [],
        "attacker": [],
    }
    weapon_stats = {
        "attacker": {
            "weapon": "AR", "damage_percent": 10.0, "max_ammo": 1,
            "reload_time": 100.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        weapon_stats=weapon_stats,
        base_crit_rate=0.0,
    )
    # atk_for_hit=100, atk_percent buff of +100% (granted at battle_start,
    # active for the shot at t=0) doubles it to 200.
    normal_hits = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert normal_hits[0]["damage"] == 200.0


def test_normal_attack_damage_for_charge_weapon_applies_charge_damage_bonus():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    weapon_stats = {
        "attacker": {
            "weapon": "RL", "damage_percent": 10.0, "max_ammo": 6,
            "reload_time": 100.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        }
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.5,
        mode="auto",
        weapon_stats=weapon_stats,
        base_crit_rate=0.0,
    )
    # one shot at t=1.0 (charge_time); atk_for_hit=100, charge_damage_bonus
    # = 250/100-1 = 1.5 -> charge_damage multiplier = 1+1.5 = 2.5 -> 250.
    normal_hits = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert len(normal_hits) == 1
    assert normal_hits[0]["damage"] == 250.0


def _normals(result, slug="attacker"):
    return [e for e in result["damage_log"] if e["source"] == "normal_attack" and e["slug"] == slug]


def test_resource_spec_permanent_linear_buff_steps_up_and_caps():
    # A named resource filled every 2 shots, granting a permanent damage_taken_up
    # of 0.5 PER stack, capped at 2 stacks. AR fires 12/s; per_shot_every 2 fires
    # at counts 2,4,6,... = shot indices 1,3,5,... So a shot at index i sees
    # min(2, fills-at-or-before-i) stacks -> damage 1000*(1 + 0.5*stacks).
    spec = ResourceSpec(
        name="evo", fill=("per_shot_every", 2), cap=2,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.5 * c)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=1.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [spec]},
    )
    dmg = {round(e["time"], 4): e["damage"] for e in _normals(result)}
    assert dmg[0.0] == 1000.0                    # index 0: 0 fills
    assert dmg[round(2 / 12, 4)] == 1500.0       # index 2: 1 fill (at index 1)
    assert dmg[round(4 / 12, 4)] == 2000.0       # index 4: 2 fills
    assert dmg[round(6 / 12, 4)] == 2000.0       # index 6: 3 fills, capped at 2


def test_resource_spec_timed_stacks_expire_after_lifetime():
    # Same fill (every 2 shots -> fills at shot indices 1,3,5,...), but each stack
    # lasts only 0.5s. AR fires 12/s, so a shot at index i (t=i/12) sees stacks
    # filled in (t-0.5, t] = fills at odd j with i-6 < j <= i.
    spec = ResourceSpec(
        name="evo", fill=("per_shot_every", 2), cap=5,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.5 * c, lifetime=0.5)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [spec]},
    )
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert dmg[4] == 2000.0   # fills j=1,3 in window -> 2 stacks
    # index 10: fills j=5,7,9 in window (1,3 expired) -> 3 stacks -> 2500. Without
    # expiry all 5 fills (j=1,3,5,7,9) would give cap 5 -> 3500.
    assert dmg[10] == 2500.0


def test_resource_spec_leveled_buff_scales_by_derived_level():
    # A tiered buff: level = stacks // 3, damage_taken_up = 0.5 per level. Fill
    # every shot (a shot sees its own fill, matching per_shot_rules), cap 9 stacks
    # -> max level 3. At shot index i, stacks = min(9, i+1), level = stacks // 3.
    spec = ResourceSpec(
        name="exp", fill=("per_shot_every", 1), cap=9,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.5 * (c // 3))],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [spec]},
    )
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert dmg[2] == 1500.0   # 3 stacks -> level 1 -> +0.5
    assert dmg[5] == 2000.0   # 6 stacks -> level 2
    assert dmg[8] == 2500.0   # 9 stacks -> level 3 (capped)
    assert dmg[15] == 2500.0  # count capped at 9 -> still level 3


def test_resource_spec_buff_can_target_other_units_by_scope():
    # A resource owned/filled by one unit can buff a DIFFERENT scope (e.g.
    # Guillotine's Hero Level buffs Water allies). Here attacker's resource grants
    # a squad damage_taken_up that raises midtier's... use burst nuke on attacker.
    spec = ResourceSpec(
        name="exp", fill=("per_shot_every", 1), cap=100,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="squad", value_fn=lambda c: 0.01 * c)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=10000)},
        resource_specs={"attacker": [spec]},
    )
    # burst fires after gauge charge (~t=5); by then many fills happened, so the
    # squad damage_taken_up is well above 0 -> burst nuke > base 10000.
    burst = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert burst and burst[0]["damage"] > 10000.0


def test_resource_spec_core_conditional_fill_uses_core_hittable():
    # A fill whose rate depends on the boss: ("per_shot_every_core", 3, 6) fills
    # every 3rd shot on a core-hittable boss (Guillotine's "hit Core 3 times"),
    # every 6th otherwise ("6 normals without hitting the core"). damage_taken_up
    # +1.0 per stack, cap 1 -> a shot's damage doubles once the first fill lands.
    spec = ResourceSpec(
        name="exp", fill=("per_shot_every_core", 3, 6), cap=1,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 1.0 * c)],
    )
    def run(core):
        return simulate_raid(
            make_deck(),
            {"buffer": [], "midtier": [], "attacker": []},
            burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
            enemy_def=0, gauge_charge_time=5.0, fight_duration=1.0, mode="auto", base_crit_rate=0.0,
            core_hittable=core, weapon_stats={"attacker": _ar_weapon()},
            resource_specs={"attacker": [spec]},
        )
    core_dmg = {i: e["damage"] for i, e in enumerate(_normals(run(True)))}
    nocore_dmg = {i: e["damage"] for i, e in enumerate(_normals(run(False)))}
    # core run: base is 2000/shot (core_hit_bonus doubles); first fill at shot
    # index 2 (count 3) -> the +1.0 damage_taken doubles index 2 to 4000.
    assert core_dmg[1] == 2000.0 and core_dmg[2] == 4000.0
    # non-core run: base 1000/shot; first fill at shot index 5 (count 6).
    assert nocore_dmg[2] == 1000.0 and nocore_dmg[5] == 2000.0


def test_resource_core_conditional_fill_adds_exactly_one_stack_per_fill():
    # Guards against reading the fill tuple's 3rd element (the non-core rate) as a
    # per-fill stack amount: each fill must add exactly 1 stack. cap 2, per_stack
    # 0.5 -> after the 1st fill (index 2) exactly 1 stack (1500), after the 2nd
    # (index 5) exactly 2 stacks (2000), not more.
    spec = ResourceSpec(
        name="exp", fill=("per_shot_every_core", 3, 6), cap=2,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.5 * c)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=1.0, mode="auto", base_crit_rate=0.0,
        core_hittable=True, weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [spec]},
    )
    # attacker_atk with core doubling: base 2000. 1 stack -> *1.5 = 3000; 2 -> 4000.
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert dmg[2] == 3000.0   # exactly 1 stack (would be capped 2 -> 4000 if amount were 3)
    assert dmg[5] == 4000.0   # exactly 2 stacks (cap)


def test_resource_spec_periodic_fill_ticks_on_a_fixed_timer_independent_of_shots():
    # A resource filled purely on a fixed timer (e.g. Cinderella's Beautiful,
    # "every 3 sec when a decoy is present" - decoy up from battle start),
    # independent of the owner's shot timeline. AR fires 12/s; a shot's damage
    # reflects however many periodic fills (every 3s) have landed by its time.
    spec = ResourceSpec(
        name="beautiful", fill=("periodic", 3.0), cap=3,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.5 * c)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=10.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=10000)},  # no reload within 10s
        resource_specs={"attacker": [spec]},
    )
    # AR fires 12/s (shot i at t=i/12); fills land exactly at t=3,6,9.
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert dmg[35] == 1000.0   # t=35/12=2.9167, before first fill: 0 stacks
    assert dmg[36] == 1500.0   # t=36/12=3.0, first fill lands here: 1 stack
    assert dmg[72] == 2000.0   # t=6.0, 2nd fill: 2 stacks
    assert dmg[108] == 2500.0  # t=9.0, 3rd fill: 3 stacks (cap)


def test_resource_scaled_nuke_single_hit_scaled_by_resource_count_at_burst_time():
    # A burst-fired additional hit whose magnitude "mirrors the stack count" of
    # a resource (e.g. Cinderella's Beautiful) - percent = base_percent *
    # scale_fn(count), resolved from the resource's count AT THE NUKE'S OWN
    # TIME (deferred to phase 2, since fills aren't known until the resolution
    # pass runs, which is after the burst cycle that records this event).
    spec = ResourceSpec(name="beautiful", fill=("periodic", 3.0), cap=12, buffs=[])
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=10.0, fight_duration=15.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        resource_scaled_nukes={"attacker": [{
            "resource": "beautiful", "cap": 12, "base_percent": 28.9,
            "scale_fn": lambda c: c, "tick_count": 1, "tick_interval": 0.0,
        }]},
    )
    # burst fires at t=10 (gauge_charge_time); by then 3 periodic fills have
    # landed (t=3,6,9) -> count=3 -> percent = 28.9*3 = 86.7% of 10000 = 8670.
    hits = [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"]
    assert len(hits) == 1
    assert round(hits[0]["time"], 4) == 10.0
    assert round(hits[0]["damage"], 4) == round(10000 * 0.867, 4)


def test_resource_scaled_nuke_threshold_gate_zero_below_cap():
    # A gate (not a scale): fires only if the resource is AT its cap - e.g.
    # Julia's Climax additional hit, gated on Crescendo at max stacks.
    spec = ResourceSpec(name="crescendo", fill=("periodic", 100.0), cap=5, buffs=[])
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=10.0, fight_duration=15.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},  # fill interval 100s -> never fills within the fight
        resource_scaled_nukes={"attacker": [{
            "resource": "crescendo", "cap": 5, "base_percent": 544.5,
            "scale_fn": lambda c: 1.0 if c >= 5 else 0.0, "tick_count": 1, "tick_interval": 0.0,
        }]},
    )
    hits = [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"]
    assert len(hits) == 1
    assert hits[0]["damage"] == 0.0  # count=0 at burst time -> gate closed


def test_resource_scaled_nuke_multi_tick_dot_reads_count_at_each_ticks_own_time():
    # A repeating tick (e.g. Guillotine's Extermination): tick_count ticks,
    # tick_interval apart, each independently scaled by the resource's count AT
    # THAT TICK'S time (not frozen at burst-fire time) - so a resource still
    # accumulating during the DoT window changes the later ticks' damage.
    spec = ResourceSpec(name="exp", fill=("periodic", 1.0), cap=100, buffs=[])
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=2.0, fight_duration=10.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        resource_scaled_nukes={"attacker": [{
            "resource": "exp", "cap": 100, "base_percent": 10.0,
            "scale_fn": lambda c: c, "tick_count": 3, "tick_interval": 1.0,
            "damage_type": "sustained",
        }]},
    )
    hits = sorted(
        [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"],
        key=lambda e: e["time"],
    )
    assert len(hits) == 3
    assert [round(h["time"], 4) for h in hits] == [2.0, 3.0, 4.0]
    # count at t=2,3,4 (periodic fills every 1s from t=1): 2, 3, 4 stacks, each
    # times its own tick's window position.
    assert [round(h["damage"], 4) for h in hits] == [
        round(n * 1000.0 * fb_factor(result, t), 4) for n, t in ((2, 2.0), (3, 3.0), (4, 4.0))]
    assert all(h["damage_type"] == "sustained" for h in hits)


def test_resource_scaled_nuke_without_a_resource_ticks_at_a_flat_percent():
    # Mana's Fatal Error!: a plain repeating DoT (396%/sec for 10 ticks), not
    # scaled by any resource - "resource" omitted means every tick fires at
    # spec["base_percent"] unscaled, reusing the same tick_count/tick_interval
    # machinery as a resource-scaled DoT without requiring a fake resource.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=2.0, fight_duration=10.0, mode="auto", base_crit_rate=0.0,
        resource_scaled_nukes={"attacker": [{
            "base_percent": 10.0, "tick_count": 3, "tick_interval": 1.0, "damage_type": "sustained",
        }]},
    )
    hits = sorted(
        [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"],
        key=lambda e: e["time"],
    )
    assert len(hits) == 3
    assert [round(h["time"], 4) for h in hits] == [2.0, 3.0, 4.0]
    # 10% coeff * atk 10000, no scaling - times each tick's own window position.
    assert all(h["damage"] == 1000.0 * fb_factor(result, h["time"]) for h in hits)
    assert all(h["damage_type"] == "sustained" for h in hits)


def test_resource_scaled_nuke_that_resolves_after_the_cast_gets_the_bonus_on_every_tick():
    # Mana's Fatal Error!, confirmed in-game (Fienn, 2026-07-12): every tick of
    # her DoT takes the +50% bonus. `resolves_after_cast` is what says the DoT
    # starts a beat AFTER the burst instant rather than on it - a modelling
    # choice about WHEN, not an eligibility switch. Everything follows from
    # that: the shifted ticks land inside the window her own Burst 3 opened, so
    # the engine's time test gives them the bonus.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=2.0, fight_duration=10.0, mode="auto", base_crit_rate=0.0,
        resource_scaled_nukes={"attacker": [{
            "base_percent": 10.0, "tick_count": 3, "tick_interval": 1.0, "damage_type": "sustained",
            "resolves_after_cast": True,
        }]},
    )
    hits = sorted(
        [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"],
        key=lambda e: e["time"],
    )
    assert len(hits) == 3
    assert [round(h["time"], 4) for h in hits] == [2.0, 3.0, 4.0]  # all inside [2.0, 12.0)
    assert all(h["damage"] == 1500.0 for h in hits)  # 1000 * (1 + full_burst_bonus*0.5)


def test_resource_scaled_nukes_defaults_to_none_and_is_a_no_op():
    baseline = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
    )
    with_empty = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
        resource_scaled_nukes={},
    )
    assert with_empty["total_damage"] == baseline["total_damage"]


def test_resource_spec_fill_during_own_status_window_only_counts_in_window_shots():
    # Asuka's Anti A.T. Field: "every 10 shots, only while in Annihilation
    # State" - a per-shot fill gated to a FIXED-duration window anchored to
    # the owner's OWN burst (not the global Full Burst window - Annihilation
    # State is 9s and starts at her burst, ending well before Full Burst
    # does). gauge_charge_time=1.0 -> her burst fires at t=1.0, window
    # [1.0, 10.0); AR fires 12/s -> shot index 12 lands at exactly t=1.0.
    spec = ResourceSpec(
        name="at_field", fill=("per_shot_every_during_own_status_window", 3, 9.0), cap=10,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 1.0 * c)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=1.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [spec]},
    )
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    # shots before t=1.0 (index < 12) are pre-window, never counted regardless
    # of raw shot index.
    assert dmg[11] == 1000.0
    # in-window shots start at index 12 (t=1.0); the 3rd in-window shot is 14.
    assert dmg[13] == 1000.0   # 2nd in-window shot: still 0 stacks
    assert dmg[14] == 2000.0   # 3rd in-window shot: 1 stack lands here
    assert dmg[16] == 2000.0   # 5th in-window shot: still 1 stack
    assert dmg[17] == 3000.0   # 6th in-window shot: 2nd stack


def test_resource_spec_fill_on_last_bullet_stacks_only_when_the_magazine_empties():
    # Julia's Crescendo: "Activates when the last bullet hits the target" -
    # +1 stack every time this unit's magazine empties, not on any fixed shot
    # count. AR (12/s), 3-round magazine, 1s reload -> magazines empty at
    # shot index 2 (t=2/12) and index 5 (t=1.25+2/12).
    spec = ResourceSpec(
        name="crescendo", fill=("on_last_bullet",), cap=5,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.1 * c, lifetime=15.0)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=3)},
        resource_specs={"attacker": [spec]},
    )
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert dmg[0] == 1000.0    # 0 stacks
    assert dmg[1] == 1000.0    # still 0 stacks, before this magazine's last bullet
    assert dmg[2] == 1100.0    # this shot IS the last bullet - sees its own new stack
    assert dmg[3] == 1100.0    # next magazine, still 1 stack (15s lifetime)
    assert dmg[4] == 1100.0
    assert dmg[5] == 1200.0    # this magazine's own last bullet - 2nd stack


def test_resource_spec_fill_during_full_burst_only_counts_in_window_shots():
    # A fill gated to Full Burst (e.g. Soda's Golden Chip, "every 3 normal
    # attacks during Full Burst") counts ONLY shots whose time falls within a
    # Full Burst window, ignoring shots before/after entirely - the "every 3rd"
    # counter is over the FILTERED in-window shots, not the raw shot index.
    # gauge_charge_time=1.0 -> full burst starts at t=1.0 (FULL_BURST_DURATION
    # =10s); AR fires 12/s -> shot index 12 lands at exactly t=1.0 (in-window).
    spec = ResourceSpec(
        name="chip", fill=("per_shot_every_during_full_burst", 3), cap=10,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 1.0 * c)],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=1.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [spec]},
    )
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    # Shots 0-12 are pre-FB: Full Burst opens a beat AFTER the tier-3 cast at
    # t=1.0, so even the shot landing exactly at 1.0 (index 12) is outside.
    assert dmg[12] == 1000.0
    # in-FB shots start at index 13; the 3rd in-FB shot is index 15.
    assert dmg[14] == 1000.0   # 2nd in-FB shot: still 0 stacks
    assert dmg[15] == 2000.0   # 3rd in-FB shot: 1 stack lands here
    assert dmg[17] == 2000.0   # 5th in-FB shot: still 1 stack
    assert dmg[18] == 3000.0   # 6th in-FB shot: 2nd stack


def test_resource_spec_battle_start_reset_sets_initial_value():
    # Soda's Golden Chip starts at 50 (the cap) from battle start, not 0 -
    # modeled as a battle_start reset, not a fill.
    spec = ResourceSpec(
        name="chip", fill=("per_shot_every", 1000), cap=50,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.01 * c)],
        resets=[{"trigger": "battle_start", "value": 50}],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=1.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [spec]},
    )
    # 50 stacks * 0.01 = 0.5 damage_taken_up from the very first shot.
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert dmg[0] == 1500.0  # 1000 * 1.5


def test_resource_spec_own_burst_reset_replaces_the_running_count():
    # Soda's Golden Chip resets to 17 each time her burst fires, discarding
    # whatever it had accumulated - modeled as an own_burst reset.
    spec = ResourceSpec(
        name="chip", fill=("per_shot_every", 1), cap=50,
        buffs=[ResourceBuff(stat="damage_taken_up", scope="self", value_fn=lambda c: 0.01 * c)],
        resets=[
            {"trigger": "battle_start", "value": 50},
            {"trigger": "own_burst", "value": 17},
        ],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=10000)},
        resource_specs={"attacker": [spec]},
    )
    # burst fires at t=5.0 (gauge_charge_time), resetting chip to 17 right
    # then - the shot immediately after should reflect 17, not 50(+fills).
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    shots_before_burst = [t for t in range(60) if t / 12 < 5.0]  # AR fires 12/s
    last_pre_burst_index = shots_before_burst[-1]
    first_post_burst_index = last_pre_burst_index + 1
    assert dmg[last_pre_burst_index] > dmg[first_post_burst_index]  # dropped from ~50+ to 17-ish
    assert round(dmg[first_post_burst_index], 4) == round(1000 * (1 + 0.01 * 17), 4)


def test_resource_gated_buff_fires_when_pre_reset_count_meets_the_gate():
    # Soda's Golden Chip: ATK+65.25%/15s IF she had >=30 stacks right before her
    # burst consumed it down to 17 (a buff gated on the PRE-reset count, not
    # the post-reset value that's active going forward). Verified via a normal
    # attack's damage right after the burst, which should reflect the buff.
    spec = ResourceSpec(
        name="chip", fill=("per_shot_every", 1), cap=50,
        resets=[
            {"trigger": "battle_start", "value": 50},
            {"trigger": "own_burst", "value": 17},
        ],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=10000)},
        resource_specs={"attacker": [spec]},
        resource_gated_buffs={"attacker": [{
            "resource": "chip", "cap": 50, "use_pre_reset": True,
            "gate_fn": lambda c: c >= 30,
            "stat": "atk_percent", "value": 0.6525, "scope": "self", "duration": 15.0,
        }]},
    )
    # burst fires at t=5.0; pre-reset count there is 50 (starts at cap, stays
    # there) -> gate passes. Shot index 60 (t=5.0) reflects the buff.
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert round(dmg[60], 4) == round(1000 * 1.6525, 4)


def test_resource_gated_buff_does_not_fire_when_gate_fails():
    spec = ResourceSpec(
        name="chip", fill=("per_shot_every", 1000), cap=50,
        resets=[
            {"trigger": "battle_start", "value": 10},
            {"trigger": "own_burst", "value": 5},
        ],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=10000)},
        resource_specs={"attacker": [spec]},
        resource_gated_buffs={"attacker": [{
            "resource": "chip", "cap": 50, "use_pre_reset": True,
            "gate_fn": lambda c: c >= 30,  # pre-reset count is 10 -> gate fails
            "stat": "atk_percent", "value": 0.6525, "scope": "self", "duration": 15.0,
        }]},
    )
    # Full Burst divided back out: these expectations encode STACK COUNTS,
    # and the bonus multiplies the same shot alongside them.
    dmg = {i: e["damage"] / fb_factor(result, e["time"])
           for i, e in enumerate(_normals(result))}
    assert dmg[60] == 1000.0


def test_resource_gated_buffs_defaults_to_none_and_is_a_no_op():
    baseline = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
    )
    with_empty = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
        resource_gated_buffs={},
    )
    assert with_empty["total_damage"] == baseline["total_damage"]


def _tier1_fire(event):
    return event["type"] == "burst" and event["tier"] == 1


def _full_burst_enter_event(event):
    return event["type"] == "full_burst_start"


def test_squad_burst_cycle_conditional_fill_and_dynamic_hit_count_nuke():
    # Maiden's MP: +1 if MP==0 whenever ANY squad tier-1 fires; +1 if MP>=1 on
    # entering Full Burst; her own burst drains it, and its hit count IS the
    # pre-drain MP. The engine's strict burst1->burst2->burst3->full-burst
    # ordering means her own burst ALWAYS fires before full_burst_start - so
    # MP is always exactly 1 (from the tier-1 rule alone) at her burst, every
    # cycle; the "Full Burst entry" rule can never actually contribute
    # (by the time it checks, MP is already back to 0).
    spec = ResourceSpec(
        name="mp", fill=("squad_burst_cycle_conditional", [
            (_tier1_fire, lambda count: count == 0, 1),
            (_full_burst_enter_event, lambda count: count >= 1, 1),
        ]), cap=12, buffs=[],
        resets=[{"trigger": "own_burst", "value": 0}],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=60.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        dynamic_hit_count_nukes={"attacker": [{"resource": "mp", "base_percent": 100.0}]},
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 2  # 2 burst cycles complete within 60s (t=5.0, t=40.0)
    assert all(h["damage"] == 10000.0 for h in hits)  # 1 hit * 100% coefficient, no buffs


def test_dynamic_hit_count_nuke_with_extra_flat_atk_from_max_hp():
    # Maiden's Diamond Dust: 1372.8% of (10% final Max HP + ATK) - the 10%
    # Max HP term must boost ONLY this nuke, not her normal attacks or any
    # other damage instance from the same slug.
    spec = ResourceSpec(
        name="mp", fill=("squad_burst_cycle_conditional", [(_tier1_fire, lambda c: c == 0, 1)]),
        cap=12, buffs=[], resets=[{"trigger": "own_burst", "value": 0}],
    )
    base_stats = make_base_stats(attacker_atk=10000)
    base_stats["attacker"]["max_hp"] = 50000
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        dynamic_hit_count_nukes={
            "attacker": [{"resource": "mp", "base_percent": 1372.8, "extra_flat_atk_percent_of_max_hp": 0.10}]
        },
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 1
    # (10000 + 0.10*50000) * 13.728 = 15000 * 13.728
    assert round(hits[0]["damage"], 4) == round(15000 * 13.728, 4)


def test_dynamic_hit_count_nukes_defaults_to_none_and_is_a_no_op():
    baseline = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
    )
    with_empty = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
        dynamic_hit_count_nukes={},
    )
    assert with_empty["total_damage"] == baseline["total_damage"]


def test_dynamic_hit_count_nuke_fire_delay_fires_and_resets_at_burst_time_plus_delay():
    # Asuka's Annihilation: fires 9s AFTER her burst (when Annihilation State
    # ends), not at cast time - hit count is the Anti A.T. Field stack count
    # right before THAT moment (not right before the burst itself), and the
    # resource resets there too, not at burst time.
    spec = ResourceSpec(
        name="at_field", fill=("periodic", 1.0), cap=30,
        resets=[{"trigger": "own_burst_delayed", "delay": 9.0, "value": 0}],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        dynamic_hit_count_nukes={
            "attacker": [{"resource": "at_field", "base_percent": 100.0, "fire_delay": 9.0}]
        },
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    # burst fires at t=5.0; delayed fire time = 14.0. Periodic fills land at
    # t=1..14 by then (14 stacks) - NOT the count at t=5.0 (which would be 5).
    assert len(hits) == 14
    assert all(round(h["time"], 4) == 14.0 for h in hits)
    # 1000 atk * 100% coefficient. The delayed fire time (14.0) lands inside
    # the window its own burst opened at t=5.0 - that is the delay doing it,
    # not any property of the skill's wording.
    assert all(h["damage"] == 1000.0 * fb_factor(result, h["time"]) for h in hits)


def test_dynamic_hit_count_nuke_takes_the_bonus_when_its_delay_lands_in_a_window():
    # Same setup as above. The delay puts the fire time at 14.0, inside the
    # Full Burst window [5.0, 15.0) (full_burst_start fires at the same instant
    # as the tier-3 burst and FULL_BURST_DURATION is 10s), and that is the
    # entire reason it collects the bonus.
    spec = ResourceSpec(
        name="at_field", fill=("periodic", 1.0), cap=30,
        resets=[{"trigger": "own_burst_delayed", "delay": 9.0, "value": 0}],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        dynamic_hit_count_nukes={
            "attacker": [{
                "resource": "at_field", "base_percent": 100.0, "fire_delay": 9.0,
            }]
        },
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 14
    assert all(h["damage"] == 1500.0 for h in hits)  # 1000 * (1 + full_burst_bonus*0.5) = 1000*1.5


def test_dynamic_hit_count_nuke_without_a_delay_fires_at_cast_time_and_takes_no_bonus():
    # No `fire_delay`, so the nuke resolves AT the cast - and the engine fires
    # a unit's own burst strictly before full_burst_start, so the instant it is
    # computed at is outside every window. This is the shape that made the old
    # "as damage" text rule look right: such bullets never had a window to be
    # inside of, whatever their description happened to say.
    spec = ResourceSpec(
        name="mp", fill=("squad_burst_cycle_conditional", [(_tier1_fire, lambda c: c == 0, 1)]),
        cap=12, buffs=[], resets=[{"trigger": "own_burst", "value": 0}],
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        dynamic_hit_count_nukes={"attacker": [{"resource": "mp", "base_percent": 100.0}]},
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 1
    assert hits[0]["damage"] == 1000.0  # no full_burst_bonus applied


def test_resource_specs_defaults_to_none_and_is_a_no_op():
    baseline = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
    )
    with_empty = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 100.0}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={},
    )
    assert with_empty["total_damage"] == baseline["total_damage"]


def test_slug_missing_from_weapon_stats_gets_no_normal_attack_damage():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=10.0,
        mode="auto",
        weapon_stats={},
    )
    assert result["damage_log"] == []


def test_burst_used_this_cycle_resets_between_cycles():
    seen_at_second_cycle = []

    def emit_cdr_pulse(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 15.0, "squad", caster_slug))

    def check_burst_used(context, caster_slug, time, registry):
        if time > 15.0:  # only care about the second cycle's tier-1 firing
            seen_at_second_cycle.append(set(context.burst_used_this_cycle))

    rules_by_slug = {
        "buffer": [
            SkillRule(trigger="full_burst_end", action=emit_cdr_pulse),
            SkillRule(trigger="own_burst_activate", action=check_burst_used),
        ],
        "midtier": [],
        "attacker": [],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=35.0,
        mode="auto",
    )
    # at the moment buffer's tier1 burst fires in cycle 2, only itself should
    # be recorded as "used this cycle" so far - the previous cycle's usage
    # must have been cleared.
    assert seen_at_second_cycle == [{"buffer"}]


# --- Phase S: attack speed / charge speed move damage end-to-end ---

def _grant(stat, value, slug="attacker"):
    def action(context, caster_slug, time, registry):
        registry.add(Effect(stat, value, "self", None, slug), applied_at=time)
    return SkillRule(trigger="battle_start", action=action)


def test_attack_speed_buff_increases_normal_attack_shots_and_damage():
    # AR fires 12/s; +100% attack speed -> 24/s, so ~double the shots (and damage)
    # over a window with no reload. Proves the buff is consumed through simulate_raid.
    kwargs = dict(
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000), enemy_def=0,
        gauge_charge_time=5.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_as = simulate_raid(
        make_deck(), {"buffer": [], "midtier": [], "attacker": [_grant("attack_speed_percent", 1.0)]}, **kwargs
    )
    na_without = [e for e in without["damage_log"] if e["source"] == "normal_attack"]
    na_with = [e for e in with_as["damage_log"] if e["source"] == "normal_attack"]
    assert na_without and len(na_with) > len(na_without)
    assert len(na_with) >= 1.8 * len(na_without)  # ~2x cadence, no reload in the window
    assert sum(e["damage"] for e in na_with) > sum(e["damage"] for e in na_without)


def test_attack_speed_default_leaves_normal_attacks_unchanged():
    # Regression: no attack_speed_percent buff -> identical normal-attack timeline.
    kwargs = dict(
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000), enemy_def=0,
        gauge_charge_time=5.0, fight_duration=3.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
    )
    a = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    b = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": [_grant("attack_speed_percent", 0.0)]}, **kwargs)
    na_a = [(round(e["time"], 6), e["damage"]) for e in a["damage_log"] if e["source"] == "normal_attack"]
    na_b = [(round(e["time"], 6), e["damage"]) for e in b["damage_log"] if e["source"] == "normal_attack"]
    assert na_a == na_b


def test_attack_speed_increases_per_shot_trigger_firings():
    # Faster cadence -> more shots -> an "every 5 shots" nuke fires more often
    # (the shot-count ripple Phase S was flagged to affect).
    per_shot_rules = {"attacker": [(5, "every", [instant_nuke_pulse_rule("per_shot", 100.0)])]}
    kwargs = dict(
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000), enemy_def=0,
        gauge_charge_time=5.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()}, per_shot_rules=per_shot_rules,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_as = simulate_raid(
        make_deck(), {"buffer": [], "midtier": [], "attacker": [_grant("attack_speed_percent", 1.0)]}, **kwargs
    )
    ps_without = [e for e in without["damage_log"] if e["source"] == "per_shot_nuke"]
    ps_with = [e for e in with_as["damage_log"] if e["source"] == "per_shot_nuke"]
    assert ps_without and len(ps_with) > len(ps_without)


def test_charge_speed_buff_increases_charge_shots():
    # RL charge weapon: +100% charge speed halves charge time -> more charged shots.
    weapon_stats = {"attacker": {"weapon": "RL", "damage_percent": 100.0, "max_ammo": 3,
                                 "reload_time": 1.0, "charge_time": 1.0, "charge_damage_percent": 100.0}}
    kwargs = dict(
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000), enemy_def=0,
        gauge_charge_time=5.0, fight_duration=5.0, mode="auto", base_crit_rate=0.0, weapon_stats=weapon_stats,
    )
    without = simulate_raid(make_deck(), {"buffer": [], "midtier": [], "attacker": []}, **kwargs)
    with_cs = simulate_raid(
        make_deck(), {"buffer": [], "midtier": [], "attacker": [_grant("charge_speed_percent", 1.0)]}, **kwargs
    )
    na_without = [e for e in without["damage_log"] if e["source"] == "normal_attack"]
    na_with = [e for e in with_cs["damage_log"] if e["source"] == "normal_attack"]
    assert na_without and len(na_with) > len(na_without)


def _one_unit_deck():
    return [{"slug": "gunner", "burst_tier": 3, "element": "Iron",
             "cooldown": 40.0, "weapon": "SR"}]


SR_WEAPON = {"weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
             "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}


def test_weapon_mode_schedule_swaps_profile_inside_window():
    def schedule(context, fight_duration):
        return [{"start": 5.0, "until_shots": 1,
                 "profile": {"weapon": "SR", "damage_percent": 499.5,
                             "charge_damage_percent": 1000.0, "charge_time": 5.0}}]

    kwargs = dict(
        deck=_one_unit_deck(), rules_by_slug={}, burst_damage_percents={},
        base_stats={"gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        weapon_stats={"gunner": SR_WEAPON},
    )
    plain = simulate_raid(**kwargs)
    with_transform = simulate_raid(**kwargs, weapon_mode_schedules={"gunner": schedule})
    # window (5-10s): base SR shots vanish and are replaced by one cannon shot at t=10.0
    plain_shots = [e for e in plain["damage_log"] if e["source"] == "normal_attack"]
    transformed = [e for e in with_transform["damage_log"] if e["source"] == "normal_attack"]
    cannon = [e for e in transformed if e["time"] == 10.0]
    assert len(cannon) == 1
    assert not [e for e in transformed if 5.0 <= e["time"] < 10.0]
    assert [e for e in plain_shots if 5.0 <= e["time"] < 10.0]
    # cannon shot = 499.5% x (1 + 9.0 charge bonus) - compare ratio against a base shot at the same stats
    base_shot = plain_shots[0]["damage"]          # 69.04% x (1+1.5)
    assert cannon[0]["damage"] > base_shot * 20


def test_per_shot_every_during_segment_and_every_outside_segment_are_mutually_exclusive():
    # Task 8: gates a per-shot rule to fire only on segment (transform)
    # shots or only on base-weapon shots, off the same in_segment flag that
    # ShotRecord now carries - so a transform's empowered attack (in-segment)
    # and its normal attack (outside-segment) can never both count the same
    # shot (Task 9's Snow White: Heavy Arms consumes both to avoid double-
    # counting).
    def schedule(context, fight_duration):
        return [{"start": 5.0, "until_shots": 1,
                 "profile": {"weapon": "SR", "damage_percent": 499.5,
                             "charge_damage_percent": 1000.0, "charge_time": 5.0}}]

    result = simulate_raid(
        deck=_one_unit_deck(), rules_by_slug={}, burst_damage_percents={},
        base_stats={"gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        mode="auto", base_crit_rate=0.0,
        weapon_stats={"gunner": SR_WEAPON},
        weapon_mode_schedules={"gunner": schedule},
        per_shot_rules={"gunner": [
            (1, "every_during_segment", [instant_nuke_pulse_rule("per_shot", 50.0)]),
            (1, "every_outside_segment", [instant_nuke_pulse_rule("per_shot", 10.0)]),
        ]},
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    seg_shots = [e for e in ps if e["damage"] == 500.0]   # atk 1000 * 50%
    base_shots = [e for e in ps if e["damage"] == 100.0]  # atk 1000 * 10%
    assert seg_shots and base_shots  # both modes actually fired
    assert [e["time"] for e in seg_shots] == [10.0]  # the segment's one cannon shot
    assert all(e["time"] != 10.0 for e in base_shots)


def test_per_shot_every_during_segment_and_every_outside_segment_stay_exclusive_at_a_shared_time():
    # Fix pass (Task 8 finding): for a MAGAZINE base weapon (AR/MG/SMG/SG),
    # an until_shots segment's last shot and the resumed base magazine's
    # first shot land at the exact same instant - the documented resume
    # semantic in attack_rate._base_shot_records ("a fresh magazine at
    # window_start"). The prior SR-based exclusivity test can't exercise this
    # because a charge weapon's resumed first shot always lands one
    # charge-time AFTER the segment ends, never coincident with it. Here a
    # rate_of_fire=2.0/until_shots=1 segment starting at t=0 ends its one
    # tick at t=0.5, and the AR base's fresh magazine also fires its first
    # round at t=0.5 - two distinct ShotRecords (in_segment=True and False)
    # sharing time=0.5. Matching by time value (not record identity) let
    # BOTH per-shot rules fire on BOTH records at that instant.
    def schedule(context, fight_duration):
        return [{"start": 0.0, "until_shots": 1,
                 "profile": {"weapon": "AR", "damage_percent": 500.0, "rate_of_fire": 2.0}}]

    weapon_stats = {
        "attacker": {"weapon": "AR", "damage_percent": 10.0, "max_ammo": 3,
                     "reload_time": 100.0, "charge_time": 0.0, "charge_damage_percent": 100.0},
    }
    result = simulate_raid(
        make_deck(), {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=1.0,
        mode="auto", base_crit_rate=0.0,
        weapon_stats=weapon_stats,
        weapon_mode_schedules={"attacker": schedule},
        per_shot_rules={"attacker": [
            (1, "every_during_segment", [instant_nuke_pulse_rule("per_shot", 50.0)]),
            (1, "every_outside_segment", [instant_nuke_pulse_rule("per_shot", 10.0)]),
        ]},
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    seg_shots = [e for e in ps if e["damage"] == 500.0]   # atk 1000 * 50%
    base_shots = [e for e in ps if e["damage"] == 100.0]  # atk 1000 * 10%
    assert seg_shots and base_shots  # both modes actually fired
    assert [e["time"] for e in seg_shots] == [0.5]  # only the segment's own shot fires during_segment
    collision = [e for e in ps if e["time"] == 0.5]
    assert len(collision) == 2  # exactly one fire per record at the shared instant, not one each
    assert {e["damage"] for e in collision} == {500.0, 100.0}


def test_per_shot_every_outside_full_burst_does_not_fire_on_a_shot_exactly_at_fb_end():
    # Regression for the boundary leak (final-review Fix 1): a shot landing
    # EXACTLY at a Full Burst window's end must count as "in" Full Burst, not
    # "outside" it - mirrors laplace-signature's 93rd Buster tick nominally
    # landing at burst+10.0 == FB end (backend/app/skill_rules/laplace_
    # signature.py). gauge_charge_time=0.0 makes the single attacker's own
    # burst (tier 3, all tiers present via make_deck()) fire at t=0.0, so the
    # Full Burst window is exactly [0.0, 10.0) - and a weapon-mode segment
    # anchored to that same burst time with rate_of_fire=1.0/until_shots=10
    # lands its LAST tick at exactly 0.0 + 10*1.0 == 10.0 (exact float
    # arithmetic, no rounding drift), the FB window's end instant.
    def schedule(context, fight_duration):
        return [
            {"start": t, "until_shots": 10,
             "profile": {"weapon": "RL", "damage_percent": 100.0, "rate_of_fire": 1.0}}
            for t in context.burst_times.get("attacker", [])
        ]

    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=0.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": SR_WEAPON},
        weapon_mode_schedules={"attacker": schedule},
        per_shot_rules={"attacker": [(1, "every_outside_full_burst", [instant_nuke_pulse_rule("per_shot", 100.0)])]},
    )
    ps = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    # The segment's 10 ticks (t=1..10) all fall inside [0.0, 10.0] - none of
    # them, including the boundary tick at exactly t=10.0, fire the
    # outside-Full-Burst rule.
    assert not [e for e in ps if e["time"] <= 10.0]
    # Positive control: the base weapon's resumed shots after the window
    # (t>10.0) are genuinely outside Full Burst and DO fire the rule, so this
    # isn't just "the rule never fires".
    assert [e for e in ps if e["time"] > 10.0]


def test_scheduled_nuke_context_exposes_full_burst_windows():
    seen = {}

    def schedule(context, fight_duration):
        seen["windows"] = list(context.full_burst_windows)
        return []

    simulate_raid(
        deck=[{"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
               {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
               {"slug": "gunner", "burst_tier": 3, "element": "Iron", "cooldown": 40.0, "weapon": "SR"}],
        rules_by_slug={}, burst_damage_percents={},
        base_stats={"buffer": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
                    "midtier": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
                    "gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=60.0,
        scheduled_nukes={"gunner": [{"schedule": schedule, "percent": 100.0}]},
    )
    assert seen["windows"], "full burst windows must be visible to schedules"
    assert all(end > start for start, end in seen["windows"])


def test_a_scheduled_nuke_can_opt_in_to_the_core_hit_bonus():
    # Core Damage is a normal-attack-only modifier, so scheduled ticks are ruled
    # out by default. A SUMMON's auto-attack is the exception: Anis: Star's
    # Shooting Stars land as core hits in game (Fienn, range footage
    # 2026-07-28), so the spec can opt one in.
    def schedule(context, fight_duration):
        return [5.0]

    kwargs = dict(
        deck=[{"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
              {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
              {"slug": "gunner", "burst_tier": 3, "element": "Iron", "cooldown": 40.0, "weapon": "SR"}],
        rules_by_slug={}, burst_damage_percents={},
        base_stats={"buffer": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
                    "midtier": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
                    "gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        core_hittable=True, base_crit_rate=0.0,
    )
    plain = simulate_raid(scheduled_nukes={
        "gunner": [{"schedule": schedule, "percent": 100.0}]}, **kwargs)
    opted = simulate_raid(scheduled_nukes={
        "gunner": [{"schedule": schedule, "percent": 100.0, "core_eligible": True}]}, **kwargs)

    def tick(result):
        return next(e for e in result["damage_log"] if e["source"] == "scheduled")

    # The tick lands inside a Full Burst window, so its bucket is 1 + 0.5
    # without a core hit and 1 + 0.5 + CORE_HIT_BONUS with one - core sits in
    # the SAME additive bucket as the Full Burst bonus, it does not multiply it.
    assert tick(plain)["damage"] == pytest.approx(1000.0 * 1.5)
    assert tick(opted)["damage"] == pytest.approx(1000.0 * (1.5 + CORE_HIT_BONUS))


def test_a_scheduled_nuke_that_does_not_opt_in_still_never_cores():
    def schedule(context, fight_duration):
        return [5.0]

    result = simulate_raid(
        deck=[{"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
              {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
              {"slug": "gunner", "burst_tier": 3, "element": "Iron", "cooldown": 40.0, "weapon": "SR"}],
        rules_by_slug={}, burst_damage_percents={},
        base_stats={"buffer": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
                    "midtier": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
                    "gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        core_hittable=True, base_crit_rate=0.0,
        scheduled_nukes={"gunner": [{"schedule": schedule, "percent": 100.0}]},
    )
    tick = next(e for e in result["damage_log"] if e["source"] == "scheduled")
    # 100% of ATK 1000, no crit, no buffs, x1.5 for the Full Burst window it
    # lands in - and no core bonus, which is the point.
    assert tick["damage"] == pytest.approx(1000.0 * 1.5)


def test_projectile_attachment_damage_up_scales_attachment_typed_nuke():
    import pytest

    def grant(context, caster_slug, time, registry):
        registry.add(Effect("projectile_attachment_damage_up", 1.5, "self", None, caster_slug),
                     applied_at=time)

    kwargs = dict(
        deck=[{"slug": "gunner", "burst_tier": 3, "element": "Iron",
               "cooldown": 40.0, "weapon": "SR"}],
        burst_damage_percents={},
        base_stats={"gunner": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0}},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        scheduled_nukes={"gunner": [
            {"schedule": lambda c, d: [5.0], "percent": 100.0,
             "damage_type": "projectile_attachment"}]},
    )
    plain = simulate_raid(rules_by_slug={}, **kwargs)
    buffed = simulate_raid(
        rules_by_slug={"gunner": [SkillRule(trigger="battle_start", action=grant)]}, **kwargs)
    nuke = lambda r: [e for e in r["damage_log"] if e["source"] == "scheduled"][0]["damage"]
    assert nuke(buffed) == pytest.approx(nuke(plain) * 2.5)


def _elegg_ghost_spec(interval):
    """Elegg's ghosts: her burst spends 9 at the 13 cap and 6 below it, never
    dropping below 1 - a consumption that reads the count itself, which a
    fixed SET value can't express."""
    return ResourceSpec(
        name="ghosts", fill=("periodic", interval), cap=13, buffs=[],
        resets=[{
            "trigger": "own_burst",
            "value_fn": lambda pre: max(1.0, pre - (9.0 if pre >= 13 else 6.0)),
        }],
    )


def test_resource_reset_value_fn_consumes_relative_to_the_pre_reset_count():
    # Bursts land at t=5/45/85; ghosts tick every 6s and never reach the cap
    # here, so each burst's pre-count carries the PREVIOUS burst's floored
    # leftover (0 -> 1, 1+7 = 8 -> 2, 2+7 = 9). A reset that SET a fixed 0
    # would instead give 0/7/7, so the hit counts discriminate the two.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=100.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [_elegg_ghost_spec(6.0)]},
        dynamic_hit_count_nukes={"attacker": [{"resource": "ghosts", "base_percent": 100.0}]},
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 0 + 8 + 9


def test_dynamic_hit_count_nuke_hit_count_fn_branches_on_the_resource_count():
    # Elegg's 13 Ghosts: 13 sequential hits at the cap, 6 otherwise. Ghosts
    # tick every 2s here, so she is capped by her second burst onward.
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=100.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [_elegg_ghost_spec(2.0)]},
        dynamic_hit_count_nukes={"attacker": [{
            "resource": "ghosts", "base_percent": 100.0,
            "hit_count_fn": lambda count: 13 if count >= 13 else 6,
        }]},
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 6 + 13 + 13


def test_resource_fill_from_several_sources_grants_each_source_its_own_amount():
    # Mihara's Ensnaring Chains: +10 per chain discharge (battle start here)
    # and +1 per 40 normal attacks, on ONE counter capped at 20.
    spec = ResourceSpec(
        name="ensnaring", cap=20, buffs=[],
        fill=[(("at_battle_start",), 10), (("per_shot_every", 40), 1)],
        resets=[{"trigger": "own_burst", "value": 0}],  # so the nuke can read a pre-reset count
    )
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        dynamic_hit_count_nukes={"attacker": [{"resource": "ensnaring", "base_percent": 100.0}]},
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    # Her burst at t=5 reads the battle-start +10; no weapon stats are supplied
    # here, so the per-shot source contributes nothing.
    assert len(hits) == 10


def test_scheduled_nuke_resource_gate_scales_each_tick_by_the_live_count():
    # A whole-fight DoT ticking at 100% PER stack, with the stack count
    # climbing 10 at battle start and 10 more at t=3.
    spec = ResourceSpec(
        name="ensnaring", cap=20, buffs=[],
        fill=[(("at_battle_start",), 10), (("periodic", 3.0), 10)],
    )
    schedule = lambda context, fight_duration: [1.0, 4.0]
    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={}, base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        resource_specs={"attacker": [spec]},
        scheduled_nukes={"attacker": [{
            "percent": 100.0, "schedule": schedule,
            "resource_gate": ("ensnaring", 20, None, lambda count: count),
        }]},
    )
    ticks = sorted(
        (e for e in result["damage_log"] if e["source"] == "scheduled"), key=lambda e: e["time"]
    )
    assert [t["time"] for t in ticks] == [1.0, 4.0]
    assert ticks[0]["damage"] == 10 * 10000.0   # 10 stacks * 100% of 10000 ATK
    assert ticks[1]["damage"] == 20 * 10000.0   # capped at 20 after the t=3 fill


def _crit_counter_result(threshold, base_crit_rate, attacker_rules=()):
    """EVE's `every_n_critical_hits`: shots contribute their LIVE crit rate to a
    running total that fires the rule each time it crosses `threshold`."""
    return simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": list(attacker_rules)},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=base_crit_rate,
        weapon_stats={"attacker": _ar_weapon()},
        per_shot_rules={
            "attacker": [
                (threshold, "every_n_critical_hits",
                 [instant_nuke_pulse_rule("per_shot", 100.0)])
            ]
        },
    )


def _per_shot_indices(result):
    # AR fires 12/s from t=0, so shot index == round(time * 12).
    return [round(e["time"] * 12) for e in result["damage_log"]
            if e["source"] == "per_shot_nuke"]


def test_every_n_critical_hits_converts_the_threshold_at_the_live_crit_rate():
    # 50% crit rate, "every 2 critical hits" -> one proc per 4 shots.
    result = _crit_counter_result(threshold=2.0, base_crit_rate=0.5)

    assert _per_shot_indices(result) == [3, 7, 11]


def test_every_n_critical_hits_speeds_up_when_the_deck_buffs_crit_rate():
    # The whole reason the mode reads the rate per shot instead of folding a
    # fixed shot count at build time (Fienn, 2026-07-20): a crit-rate buff must
    # make the trigger fire genuinely more often. 50% -> 100% halves the gap.
    unbuffed = _crit_counter_result(threshold=2.0, base_crit_rate=0.5)
    buffed = _crit_counter_result(
        threshold=2.0, base_crit_rate=0.5,
        attacker_rules=[buff_rule("battle_start", [("crit_rate", 0.5, "self", None)])],
    )

    assert _per_shot_indices(unbuffed) == [3, 7, 11]
    assert _per_shot_indices(buffed) == [1, 3, 5, 7, 9, 11]


def test_every_n_critical_hits_carries_the_remainder_forward():
    # 30% per shot against a threshold of 1 does not divide evenly: procs land
    # at cumulative 1.2 / 2.1 / 3.0 (shots 4, 7, 10), not every 4th shot.
    result = _crit_counter_result(threshold=1.0, base_crit_rate=0.3)

    assert _per_shot_indices(result) == [3, 6, 9]


def test_every_n_critical_hits_caps_the_live_rate_at_one():
    # crit_rate is capped at 100% in the damage path; the counter uses the same
    # cap, so an over-100% buff cannot make the trigger fire faster than 1/shot.
    result = _crit_counter_result(
        threshold=1.0, base_crit_rate=1.0,
        attacker_rules=[buff_rule("battle_start", [("crit_rate", 5.0, "self", None)])],
    )

    assert _per_shot_indices(result) == list(range(12))


def _burst_anchored_result(specs, fight_duration=120.0):
    return simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=fight_duration,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon()},
        burst_anchored_buffs={"attacker": specs},
    )


def _attacker_bursts(result):
    return [e["time"] for e in result["events"]
            if e["type"] == "burst" and e["slug"] == "attacker"]


def test_burst_anchored_buff_starts_at_the_offset_not_at_the_burst():
    # Identical buff, identical duration - the only difference is when it opens.
    # A buff delayed 15s past each burst covers strictly less of the fight than
    # one that opens at the burst, so if the offset were ignored these would tie.
    at_burst = _burst_anchored_result([
        {"offset": 0.0, "stat": "atk_percent", "value": 2.0,
         "scope": "self", "duration": 10.0},
    ])
    delayed = _burst_anchored_result([
        {"offset": 15.0, "stat": "atk_percent", "value": 2.0,
         "scope": "self", "duration": 10.0},
    ])

    # Totals alone can't show this - the shot rate is uniform, so two windows
    # of equal length buff the same NUMBER of shots wherever they sit. The
    # offset is only visible in WHICH shots got buffed.
    first = _attacker_bursts(at_burst)[0]
    just_after = lambda r: next(
        e["damage"] for e in r["damage_log"]
        if e["source"] == "normal_attack" and e["time"] > first + 0.5
    )

    assert just_after(at_burst) > just_after(delayed)
    assert _attacker_bursts(at_burst) == _attacker_bursts(delayed)


def test_burst_anchored_buff_until_next_own_burst_spans_the_whole_gap():
    from app.raid_simulator import UNTIL_NEXT_OWN_BURST

    fixed = _burst_anchored_result([
        {"offset": 0.0, "stat": "atk_percent", "value": 1.0,
         "scope": "self", "duration": 1.0},
    ])
    spanning = _burst_anchored_result([
        {"offset": 0.0, "stat": "atk_percent", "value": 1.0,
         "scope": "self", "duration": UNTIL_NEXT_OWN_BURST},
    ])

    # Same buff, same start times - the spanning one just never lapses between
    # bursts, so it must strictly out-damage the 1-second version.
    assert spanning["total_damage"] > fixed["total_damage"]


def test_burst_anchored_buff_is_visible_to_shot_generation_not_just_damage():
    # The pass runs BEFORE the shot loop, so a max-ammo buff placed here has to
    # actually change the magazine (fewer reloads -> strictly more shots).
    baseline = _burst_anchored_result([])
    buffed = _burst_anchored_result([
        {"offset": 0.0, "stat": "max_ammo_percent", "value": 2.0,
         "scope": "self", "duration": 1000.0},
    ])

    shots = lambda r: sum(1 for e in r["damage_log"] if e["source"] == "normal_attack")
    assert shots(buffed) > shots(baseline)


def test_burst_anchored_buff_skips_an_offset_landing_past_the_fight():
    # An offset that pushes the last burst's state past fight_duration must not
    # emit an Effect at all (rather than one clamped to zero length).
    result = _burst_anchored_result([
        {"offset": 10_000.0, "stat": "atk_percent", "value": 5.0,
         "scope": "self", "duration": 10.0},
    ])
    baseline = _burst_anchored_result([])

    assert result["total_damage"] == baseline["total_damage"]


def _crit_fill_result(threshold, base_crit_rate, cap=5):
    """A resource filled by EXPECTED critical hits (Julia's signature
    Crescendo), asserted through the damage a per-stack buff produces."""
    return simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        base_crit_rate=base_crit_rate,
        weapon_stats={"attacker": _ar_weapon()},
        resource_specs={"attacker": [ResourceSpec(
            name="crescendo",
            fill=("per_critical_hit_every", threshold),
            cap=cap,
            buffs=[ResourceBuff(stat="atk_percent", scope="self",
                                value_fn=lambda count: count)],
        )]},
    )


def test_per_critical_hit_every_fill_uses_the_live_crit_rate():
    # 50% crit rate, a stack per 2 expected crits -> a stack every 4 shots.
    # More crit rate must fill it faster, exactly as the per-shot mode does.
    slow = _crit_fill_result(threshold=2.0, base_crit_rate=0.5)
    fast = _crit_fill_result(threshold=2.0, base_crit_rate=1.0)

    assert fast["total_damage"] > slow["total_damage"]


def test_per_critical_hit_every_fill_respects_the_cap():
    uncapped = _crit_fill_result(threshold=1.0, base_crit_rate=1.0, cap=99)
    capped = _crit_fill_result(threshold=1.0, base_crit_rate=1.0, cap=2)

    # 12 shots at one stack each would blow well past a cap of 2.
    assert uncapped["total_damage"] > capped["total_damage"]


def _burst_three_damage_with_full_burst_enter_buff(mode):
    """The Burst 3's own burst nuke, in a deck whose Burst 1 hands out a big
    self-ATK buff the moment Full Burst opens."""
    def grant_on_full_burst(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 1.0, "self", None, "attacker"), applied_at=time)

    result = simulate_raid(
        make_deck(),
        {"buffer": [SkillRule(trigger="full_burst_enter", action=grant_on_full_burst)],
         "midtier": [], "attacker": []},
        burst_damage_percents={"attacker": 1000.0},
        base_stats=make_base_stats(),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode=mode,
        base_crit_rate=0.0,
    )
    return next(e["damage"] for e in result["damage_log"] if e["source"] == "burst")


def test_burst_three_cast_does_not_see_buffs_that_land_when_full_burst_opens():
    # The cycle is [stage 3 entered -> B3 casts -> Full Burst opens], so the
    # Burst 3's own burst damage is settled before any full_burst_enter buff
    # exists (Fienn, in-game range measurement 2026-07-27).
    for mode in ("manual", "auto"):
        assert _burst_three_damage_with_full_burst_enter_buff(mode) == 10000 * 10.0


def test_burst_three_cast_is_outside_the_full_burst_window():
    # Same fact seen through the Full Burst bonus rather than through a buff:
    # damage recorded at the Burst 3's own cast is NOT inside the window that
    # cast opens, so it takes no bonus. This is the whole of what the deleted
    # "as damage" text rule was really observing.
    def nuke_at_own_burst(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("instant_damage_percent", 1000.0, "self",
                                 "attacker", "attack"))

    result = simulate_raid(
        make_deck(),
        {"buffer": [], "midtier": [],
         "attacker": [SkillRule(trigger="own_burst_activate", action=nuke_at_own_burst)]},
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode="auto",
        base_crit_rate=0.0,
    )
    nuke = next(e for e in result["damage_log"] if e["source"] == "instant_nuke")
    assert nuke["damage"] == 10000 * 10.0  # no +0.5 Full Burst bonus


def test_time_condition_is_honoured_by_the_periodic_and_per_shot_passes():
    """세 호출 지점(fire_trigger / periodic_rules / per_shot_rules)이 전부
    time_condition을 존중하는지. 하나라도 빠지면 그 경로의 게이트가 조용히 열린다."""
    seen = {"periodic": [], "per_shot": []}

    def never(context, caster_slug, time):
        return False

    def always(context, caster_slug, time):
        return True

    def record(bucket):
        def action(context, caster_slug, time, registry):
            seen[bucket].append(round(time, 3))
        return action

    def run(time_condition):
        seen["periodic"].clear()
        seen["per_shot"].clear()
        return simulate_raid(
            make_deck(),
            {"buffer": [], "midtier": [], "attacker": []},
            burst_damage_percents={},
            base_stats=make_base_stats(attacker_atk=10000),
            enemy_def=0,
            gauge_charge_time=5.0,
            fight_duration=40.0,
            mode="auto",
            base_crit_rate=0.0,
            periodic_rules={"buffer": [(15.0, [SkillRule(
                trigger="periodic", action=record("periodic"),
                time_condition=time_condition)])]},
            weapon_stats={"attacker": _ar_weapon()},
            per_shot_rules={"attacker": [(5, "every", [SkillRule(
                trigger="per_shot", action=record("per_shot"),
                time_condition=time_condition)])]},
        )

    run(always)
    assert seen["periodic"], "periodic 패스가 아예 안 돌았다 - 픽스처가 잘못됐다"
    assert seen["per_shot"], "per-shot 패스가 아예 안 돌았다 - 픽스처가 잘못됐다"

    run(never)
    assert seen == {"periodic": [], "per_shot": []}
