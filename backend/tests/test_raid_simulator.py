from app.effects import Effect, Pulse
from app.raid_simulator import simulate_raid
from app.skill_rules.privaty import build_ex_magazine_rules
from app.squad_engine import SkillRule

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


def test_core_hittable_true_doubles_burst_damage_via_200_percent_core_bonus():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    without_core = simulate_raid(
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
    with_core = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        core_hittable=True,
        base_crit_rate=0.0,
    )
    # per Fienn's in-game tooltip check, core damage is a uniform 200% across
    # every weapon type (+1.0 to the major modifier), i.e. exactly double a
    # hit with no other modifiers active.
    assert with_core["total_damage"] == without_core["total_damage"] * 2
    assert without_core["total_damage"] == 10000.0


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
    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    not_core = simulate_raid(make_deck(), rules, core_hittable=False, **kwargs)
    core = simulate_raid(make_deck(), rules, core_hittable=True, **kwargs)
    # no core: core-damage sources inert -> plain 10000.
    assert not_core["total_damage"] == 10000.0
    # core hittable: major modifier = 1 + core_hit_bonus(1.0) + core_damage(0.3) = 2.3.
    assert round(core["total_damage"], 5) == round(10000.0 * 2.3, 5)


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
    assert instant_hits == [{"slug": "buffer", "time": 5.0, "damage": 10000.0, "source": "instant_nuke", "damage_type": "attack"}]


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
    assert instant_hits == [{"slug": "buffer", "time": 15.0, "damage": 2000.0, "source": "instant_nuke", "damage_type": "attack"}]


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


def test_true_typed_nuke_gets_true_damage_up_and_still_subtracts_defense():
    # Decision: our nikke.gg-derived formula treats true_damage_up as a plain
    # Damage-Up bucket with NO defense bypass. A true-typed instance still
    # subtracts enemy DEF; only the true_damage_up buff is type-gated in.
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
    # base = (10000 - 2000) = 8000; * coeff 1.0 * damage_up (1 + 1.0 true) = 16000
    assert burst_hits[0]["damage"] == 16000.0
    assert burst_hits[0]["damage_type"] == "true"


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
    assert early and all(e["damage_type"] == "true" and e["damage"] == 20000.0 for e in early)
    assert late and all(e["damage_type"] == "attack" and e["damage"] == 10000.0 for e in late)


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
    assert [e["time"] for e in attacker_hits] == [5.0, 20.0]


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
    assert starts == [5.0, 45.0]


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
    assert enter_calls == [("buffer", 5.0)]
    assert end_calls == [("buffer", 15.0)]


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

    # without buff: 2nd magazine at 3.0 (empty) + 3.0 (reload) = 6.0s
    # with buff: reload = 3.0 / (1 + 0.5116) ~= 1.98s -> ~4.98s
    assert without_ex == 6.0
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
