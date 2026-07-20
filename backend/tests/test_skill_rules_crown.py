from app.effects import EffectRegistry
from app.skill_rules.crown import (
    build_last_kingdom_rules,
    build_one_for_all_rules,
    build_royal_attire_per_shot_rules,
    build_royal_attire_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg for crown's skills[0] "One for All"
# and skills[2] "Last Kingdom".
ONE_FOR_ALL_VALUES = {
    "description_value_01": "64.51",
    "description_value_02": "15",
    "description_value_03": "44.35",
    "description_value_04": "15",
    "description_value_05": "37.44",
    "description_value_06": "15",
    "description_value_07": "44.35",
    "description_value_08": "15",
}

LAST_KINGDOM_VALUES = {
    "description_value_01": "36.24",
    "description_value_02": "15",
    "description_value_03": "10.45",
    "description_value_04": "15",
}


def make_context():
    return SquadContext(
        [
            SquadMember("crown", burst_tier=2, element="Iron"),
            SquadMember("b3-a", burst_tier=3, element="Fire"),
            SquadMember("b3-b", burst_tier=3, element="Water"),
        ]
    )


def test_one_for_all_grants_flat_atk_and_reload_to_members_who_already_burst():
    ctx = make_context()
    ctx.burst_used_this_cycle = {"crown", "b3-a"}
    registry = EffectRegistry()
    rules = {"crown": build_one_for_all_rules(ONE_FOR_ALL_VALUES, caster_atk=10000, caster_def=2000)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    crown_target = {"slug": "crown", "element": "Iron"}
    b3a_target = {"slug": "b3-a", "element": "Fire"}
    assert registry.total_for("flat_atk", crown_target, now=5.0) == 6451.0
    assert round(registry.total_for("reload_speed_percent", crown_target, now=5.0), 4) == 0.4435


def test_one_for_all_grants_flat_def_and_reload_to_members_who_have_not_burst_yet():
    ctx = make_context()
    ctx.burst_used_this_cycle = {"crown", "b3-a"}
    registry = EffectRegistry()
    rules = {"crown": build_one_for_all_rules(ONE_FOR_ALL_VALUES, caster_atk=10000, caster_def=2000)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    b3b_target = {"slug": "b3-b", "element": "Water"}
    assert registry.total_for("flat_def", b3b_target, now=5.0) == 748.8
    assert round(registry.total_for("reload_speed_percent", b3b_target, now=5.0), 4) == 0.4435
    # b3-b hasn't burst, so it should NOT get the flat_atk bonus
    assert registry.total_for("flat_atk", b3b_target, now=5.0) == 0.0


def test_one_for_all_buffs_expire_after_their_duration():
    ctx = make_context()
    ctx.burst_used_this_cycle = {"crown"}
    registry = EffectRegistry()
    rules = {"crown": build_one_for_all_rules(ONE_FOR_ALL_VALUES, caster_atk=10000, caster_def=2000)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    crown_target = {"slug": "crown", "element": "Iron"}
    assert registry.total_for("flat_atk", crown_target, now=19.9) == 6451.0
    assert registry.total_for("flat_atk", crown_target, now=20.1) == 0.0


def test_last_kingdom_applies_squad_wide_attack_damage_up_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"crown": build_last_kingdom_rules(LAST_KINGDOM_VALUES, caster_max_hp=50000)}

    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)

    ally = {"slug": "b3-a", "element": "Fire"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.3624
    assert round(registry.total_for("shield_amount", ally, now=5.0), 2) == 5225.0


# Royal Attire (skills[1]). 43 normal attacks per Relax stack, 20 stacks to the
# heal that arms the squad buff -> 860 of her own normal attacks.
ROYAL_ATTIRE_VALUES = {
    "description_value_01": "43",    # normal attacks per Relax stack
    "description_value_02": "4.06",  # Relax potency (incoming healing, not DPS)
    "description_value_03": "20",    # Relax max stacks
    "description_value_04": "5",     # invulnerable sec
    "description_value_05": "5",     # taunt sec
    "description_value_06": "5.23",  # self heal % of max HP
    "description_value_07": "20.99", # squad Attack Damage %
    "description_value_08": "7",     # its duration
}


def _ctx(*slugs):
    return SquadContext(
        [SquadMember("crown", burst_tier=2, element="Iron")]
        + [SquadMember(s, burst_tier=3, element="Iron") for s in slugs]
    )


def test_royal_attire_self_proc_fires_every_860_normal_attacks():
    ps = build_royal_attire_per_shot_rules(ROYAL_ATTIRE_VALUES)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (860, "every")  # 43 attacks x 20 stacks

    ctx = _ctx("attacker")
    reg = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "crown", 22.0, reg)

    ally = {"slug": "attacker", "element": "Iron"}
    assert round(reg.total_for("attack_damage_up", ally, now=22.0), 4) == 0.2099
    assert reg.total_for("attack_damage_up", ally, now=29.1) == 0.0  # 7s window


def test_royal_attire_self_proc_refreshes_rather_than_stacking():
    _, _, rules = build_royal_attire_per_shot_rules(ROYAL_ATTIRE_VALUES)[0]
    ctx = _ctx("attacker")
    reg = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "crown", 22.0, reg)
        rule.action(ctx, "crown", 25.0, reg)
    ally = {"slug": "attacker", "element": "Iron"}
    assert round(reg.total_for("attack_damage_up", ally, now=25.0), 4) == 0.2099  # not 0.4198


def test_royal_attire_is_maintained_when_another_ally_heals():
    # "Activates when recovery takes effect" reads ANY ally's healing, and the
    # engine has no heal event - so a healer in the deck means the 7s buff is
    # kept alive (see module docstring: this is the ceiling reading).
    rules = {"crown": build_royal_attire_rules(ROYAL_ATTIRE_VALUES)}

    with_healer = _ctx("helm")  # helm heals on every Full Charge
    reg = EffectRegistry()
    fire_trigger("battle_start", rules, with_healer, reg, time=0.0)
    ally = {"slug": "helm", "element": "Iron"}
    assert round(reg.total_for("attack_damage_up", ally, now=170.0), 4) == 0.2099


def test_royal_attire_is_not_maintained_without_another_healer():
    # Crown heals herself, but only at the end of the 860-shot chain, so her own
    # presence must not arm the permanent branch.
    rules = {"crown": build_royal_attire_rules(ROYAL_ATTIRE_VALUES)}
    no_healer = _ctx("attacker")
    reg = EffectRegistry()
    fire_trigger("battle_start", rules, no_healer, reg, time=0.0)
    ally = {"slug": "attacker", "element": "Iron"}
    assert reg.total_for("attack_damage_up", ally, now=1.0) == 0.0


def test_royal_attire_does_not_cancel_last_kingdoms_squad_attack_damage():
    # Both bullets grant squad attack_damage_up from Crown. Royal Attire
    # refreshes; Last Kingdom does not. Keyed only by (stat, source, scope) the
    # refresh truncated the burst buff, so adding Royal Attire silently cost
    # every Crown deck its 36.24% - caught 2026-07-21.
    ctx = _ctx("attacker")
    reg = EffectRegistry()
    ally = {"slug": "attacker", "element": "Iron"}

    fire_trigger("own_burst_activate",
                 {"crown": build_last_kingdom_rules(LAST_KINGDOM_VALUES, 1e7)},
                 ctx, reg, time=10.0)
    _, _, royal = build_royal_attire_per_shot_rules(ROYAL_ATTIRE_VALUES)[0]
    for rule in royal:
        rule.action(ctx, "crown", 11.0, reg)

    assert round(reg.total_for("attack_damage_up", ally, now=11.5), 4) == 0.5723
