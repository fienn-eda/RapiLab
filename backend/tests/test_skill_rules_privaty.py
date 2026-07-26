from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.privaty import (
    build_ex_magazine_base_rules,
    build_ld_assault_base_per_shot_rules,
    ak_missile_burst_percent,
    build_ak_missile_rules,
    build_ex_magazine_rules,
    build_ld_assault_per_shot_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Privaty has her signature weapon ("dollskills") completed, so these are the
# dollskills level-10 values, not the base skills - Fienn confirmed the
# cherished-weapon version applies. It adds a 4th effect to EX Magazine
# (Attack Damage up) that the base skill doesn't have at all, and roughly
# triples AK Missile's burst damage percent (457.87% base -> 1407.64%).
# Base ("skills") level-10 values - slug "privaty". EX Magazine stops at slot 06
# and LD Assault at slot 02 (its second slot is the Stunned rider, deferred).
EX_MAGAZINE_BASE = {
    "description_value_01": "23.61", "description_value_02": "10",
    "description_value_03": "51.16", "description_value_04": "10",
    "description_value_05": "50.66", "description_value_06": "10",
}
LD_ASSAULT_BASE = {
    "description_value_01": "85.79",
    "description_value_02": "1089",  # "if Stunned" - deferred, bosses never are
}
AK_MISSILE_BASE = {
    "description_value_01": "457.87", "description_value_02": "3",
}
PRIVATY_BASE = {"ld_assault": LD_ASSAULT_BASE, "ak_missile": AK_MISSILE_BASE}

EX_MAGAZINE_VALUES = {
    "description_value_01": "23.61",
    "description_value_02": "10",
    "description_value_03": "51.16",
    "description_value_04": "10",
    "description_value_05": "50.66",
    "description_value_06": "10",
    "description_value_07": "20.16",
    "description_value_08": "10",
}

AK_MISSILE_VALUES = {
    "description_value_01": "1407.64",
    "description_value_02": "3",
    "description_value_03": "5.02",
    "description_value_04": "10",
    "description_value_05": "130",
    "description_value_06": "10",
}

LD_ASSAULT_VALUES = {
    "description_value_01": "256.17",  # last-bullet nuke % of final ATK
    "description_value_02": "1687",    # Designated Target bonus nuke %
    "description_value_03": "10.01",   # squad Damage Taken debuff %
    "description_value_04": "10",      # its duration
}

PRIVATY_VALUES = {"ld_assault": LD_ASSAULT_VALUES, "ak_missile": AK_MISSILE_VALUES}


def make_context():
    return SquadContext(
        [
            SquadMember("privaty", burst_tier=3, element="Water"),
            SquadMember("ally", burst_tier=1, element="Iron"),
        ]
    )


def test_ex_magazine_grants_squad_atk_and_reload_speed_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ex_magazine_rules(EX_MAGAZINE_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("atk_percent", ally, now=5.0), 4) == 0.2361
    assert round(registry.total_for("reload_speed_percent", ally, now=5.0), 4) == 0.5116
    assert registry.total_for("atk_percent", ally, now=15.1) == 0.0


def test_ex_magazine_reduces_max_ammo_capacity():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ex_magazine_rules(EX_MAGAZINE_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    # value is a reduction, stored as a negative percent so consumers can just sum it
    assert round(registry.total_for("max_ammo_percent", ally, now=5.0), 4) == -0.5066


def test_ex_magazine_grants_squad_attack_damage_up():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ex_magazine_rules(EX_MAGAZINE_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.2016
    assert registry.total_for("attack_damage_up", ally, now=15.1) == 0.0


def test_ak_missile_grants_self_elemental_bonus_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ak_missile_rules(AK_MISSILE_VALUES)}

    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)

    privaty = {"slug": "privaty", "element": "Water"}
    assert round(registry.total_for("other_elemental_bonus", privaty, now=5.0), 4) == 1.30
    assert registry.total_for("other_elemental_bonus", privaty, now=15.1) == 0.0

    ally = {"slug": "ally", "element": "Iron"}
    assert registry.total_for("other_elemental_bonus", ally, now=5.0) == 0.0


def test_ak_missile_burst_percent_reads_the_damage_slot():
    assert ak_missile_burst_percent(AK_MISSILE_VALUES) == 1407.64


def test_ld_assault_last_bullet_grants_debuff_and_base_hit_when_not_designated():
    ps = build_ld_assault_per_shot_rules(PRIVATY_VALUES)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (None, "last_bullet")
    ctx = make_context()
    registry = EffectRegistry()
    rules[0].action(ctx, "privaty", 3.0, registry)

    privaty = {"slug": "privaty", "element": "Water"}
    assert round(registry.total_for("damage_taken_up", privaty, now=3.0), 4) == 0.1001
    assert registry.total_for("damage_taken_up", privaty, now=13.1) == 0.0  # 10s duration
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 256.17
    assert pulses[0].full_burst_bonus_eligible is True


def test_ld_assault_damage_taken_refreshes_instead_of_stacking():
    """Two last bullets inside the 10s window leave ONE debuff, not two.

    The skill text has no "stacks up to", so it refreshes like every other
    NIKKE buff (Fienn, 2026-07-26). Stacking it inflated the whole SQUAD,
    since Damage Taken is an enemy debuff every ally multiplies by: against
    Fienn's recorded deck 2 it pushed Nayuta to 1.10x, Little Mermaid 1.13x
    and Velvet 1.15x, all three of which land on 0.96-1.00x once it refreshes.
    """
    ps = build_ld_assault_per_shot_rules(PRIVATY_VALUES)
    _, _, rules = ps[0]
    ctx = make_context()
    registry = EffectRegistry()
    rules[0].action(ctx, "privaty", 3.0, registry)
    rules[0].action(ctx, "privaty", 6.0, registry)

    privaty = {"slug": "privaty", "element": "Water"}
    assert round(registry.total_for("damage_taken_up", privaty, now=6.0), 4) == 0.1001
    # the refreshed window runs from the LATER application
    assert round(registry.total_for("damage_taken_up", privaty, now=13.0), 4) == 0.1001
    assert registry.total_for("damage_taken_up", privaty, now=16.1) == 0.0


def test_ld_assault_last_bullet_adds_designated_target_hit_within_ak_missiles_window():
    ps = build_ld_assault_per_shot_rules(PRIVATY_VALUES)
    _, _, rules = ps[0]
    ctx = make_context()
    ctx.record_burst_time("privaty", 5.0)  # AK Missile fired at t=5.0, Designated Target for 10s
    registry = EffectRegistry()
    rules[0].action(ctx, "privaty", 12.0, registry)  # within [5.0, 15.0)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 2
    assert {round(p.value, 2) for p in pulses} == {256.17, 1687.0}
    assert all(p.full_burst_bonus_eligible for p in pulses)


def test_ld_assault_last_bullet_no_designated_hit_after_ak_missiles_window_closes():
    ps = build_ld_assault_per_shot_rules(PRIVATY_VALUES)
    _, _, rules = ps[0]
    ctx = make_context()
    ctx.record_burst_time("privaty", 5.0)
    registry = EffectRegistry()
    rules[0].action(ctx, "privaty", 15.1, registry)  # after [5.0, 15.0)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 256.17


def test_privaty_end_to_end_ld_assault_fires_on_last_bullet():
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "privaty", "burst_tier": 3, "element": "Water", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "privaty": {"atk": 10000, "def": 0, "max_hp": 0},
    }
    weapon_stats = {
        "privaty": {
            "weapon": "AR", "damage_percent": 5.0, "max_ammo": 3,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "privaty": []},
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=2.0, mode="auto", base_crit_rate=0.0,
        weapon_stats=weapon_stats,
        per_shot_rules={"privaty": build_ld_assault_per_shot_rules(PRIVATY_VALUES)},
    )
    hits = sorted(
        [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"],
        key=lambda e: e["time"],
    )
    # AR (12/s), 3-round magazine, 1s reload -> last bullets at t=2/12, t=1.25+2/12
    assert len(hits) == 2
    # 1st hit: its OWN Damage Taken debuff (10.01%, applied at the same
    # instant) already boosts this same hit under the engine's default
    # same-instant-inclusive semantics - 256.17% * (1 + 0.1001).
    assert round(hits[0]["damage"], 4) == round(10000 * 2.5617 * 1.1001, 4)
    # 2nd hit (1.25s later, well within the 1st debuff's 10s window): the
    # debuff REFRESHES rather than stacking, so this hit sees the same 10.01%
    # the first one did. This assertion used to read 1 + 2*0.1001 - the
    # stacking reading, flagged in privaty.py as unverified, which Fienn's
    # recorded deck 2 disproved (it lifted the whole squad ~13%).
    assert round(hits[1]["damage"], 4) == round(10000 * 2.5617 * 1.1001, 4)


def test_base_ex_magazine_keeps_the_ammo_cost_and_omits_the_attack_damage_step():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ex_magazine_base_rules(EX_MAGAZINE_BASE)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=0.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("atk_percent", ally, 0.0), 4) == 0.2361
    assert round(registry.total_for("reload_speed_percent", ally, 0.0), 4) == 0.5116
    # The downside is squad-wide and belongs in the model too.
    assert round(registry.total_for("max_ammo_percent", ally, 0.0), 4) == -0.5066
    # Attack Damage is text only the Favorite Item has.
    assert registry.total_for("attack_damage_up", ally, 0.0) == 0.0


def test_base_ld_assault_fires_one_nuke_and_defers_the_stun_rider():
    # Raid bosses cannot be stunned, so the 1089% second bullet must not be
    # credited - exactly one pulse, and no Damage Taken debuff (that is the
    # Favorite Item's text).
    ps = build_ld_assault_base_per_shot_rules(PRIVATY_BASE)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (None, "last_bullet")

    ctx = make_context()
    registry = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "privaty", 3.0, registry)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert [p.value for p in pulses] == [85.79]
    assert pulses[0].full_burst_bonus_eligible is True
    ally = {"slug": "ally", "element": "Iron"}
    assert registry.total_for("damage_taken_up", ally, 3.0) == 0.0
