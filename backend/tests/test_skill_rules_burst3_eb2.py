"""Burst-3 attacker batch eb2: Ludmilla: Winter Owner, Chisato Nishikigi, Jill
Valentine. Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill.
"""
from app.effects import EffectRegistry
from app.skill_rules.chisato_nishikigi import build_chisato_per_shot_rules, build_chisato_rules
from app.skill_rules.jill_valentine import build_jill_rules
from app.skill_rules.ludmilla_winter_owner import (
    build_ludmilla_per_shot_rules,
    build_ludmilla_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Iron"}


def deck_ctx(src_slug, element):
    return SquadContext([
        SquadMember(src_slug, burst_tier=3, element=element),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


# --- Ludmilla: Winter Owner (MG/Water) ---
LUDMILLA = {
    "queens_gaze": {
        "description_value_01": "60", "description_value_02": "12.56", "description_value_03": "3",
        "description_value_04": "158.43", "description_value_05": "60", "description_value_06": "20",
    },
    "snowstorm": {
        "description_value_01": "60", "description_value_02": "109.64",
        "description_value_03": "14.6", "description_value_04": "10",
    },
    "guiding_lantern": {
        "description_value_01": "62.54", "description_value_02": "10",
        "description_value_03": "67.2", "description_value_04": "20",
    },
}
LUD = {"slug": "ludmilla", "element": "Water"}


def test_ludmilla_full_burst_crit_and_burst_atk_reload():
    reg = EffectRegistry()
    rules = {"ludmilla": build_ludmilla_rules(LUDMILLA)}
    ctx = deck_ctx("ludmilla", "Water")
    fire_trigger("full_burst_enter", rules, ctx, reg, 0.0)
    assert round(reg.total_for("crit_rate", LUD, 0.0), 4) == 0.146
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", LUD, 0.0), 4) == 0.6254
    assert round(reg.total_for("reload_speed_percent", LUD, 0.0), 4) == 0.672
    assert reg.total_for("reload_speed_percent", LUD, 21.0) == 0.0  # 20s expired


def test_ludmilla_per_shot_every_60_normal_debuff_and_nuke():
    ps = build_ludmilla_per_shot_rules(LUDMILLA)
    assert len(ps) == 2  # The Queen's Gaze, plus Snowstorm's core-60 nuke.
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (60, "every")
    reg = EffectRegistry()
    ctx = deck_ctx("ludmilla", "Water")
    for rule in rules:
        rule.action(ctx, "ludmilla", 5.0, reg)
    assert round(reg.total_for("damage_taken_up", ALLY, 5.0), 4) == 0.1256  # squad debuff
    assert reg.total_for("damage_taken_up", ALLY, 8.1) == 0.0  # 3s expired
    assert [round(p.value, 2) for p in reg.drain_pulses("instant_damage_percent")] == [158.43]


def test_snowstorm_core_nuke_fires_every_60_shots_only_when_the_core_is_hittable():
    _queens, snow = build_ludmilla_per_shot_rules(LUDMILLA)
    threshold, mode, rules = snow
    assert (threshold, mode) == (60, "every")

    # Core hittable -> the nuke lands.
    ctx = deck_ctx("ludmilla", "Water")
    ctx.core_hittable = True
    reg = EffectRegistry()
    for rule in rules:
        if rule.condition is None or rule.condition(ctx, "ludmilla"):
            rule.action(ctx, "ludmilla", 5.0, reg)
    assert [round(p.value, 2) for p in reg.drain_pulses("instant_damage_percent")] == [109.64]

    # No exploitable core -> "hitting the Core 60 times" never happens.
    ctx2 = deck_ctx("ludmilla", "Water")
    ctx2.core_hittable = False
    reg2 = EffectRegistry()
    for rule in rules:
        if rule.condition is None or rule.condition(ctx2, "ludmilla"):
            rule.action(ctx2, "ludmilla", 5.0, reg2)
    assert reg2.drain_pulses("instant_damage_percent") == []


def test_queens_gaze_reloads_twenty_rounds_every_sixty_shots():
    """"Activates when landing 60 normal attack(s). Affects self. Reloads 20
    round(s) of ammunition." Both numbers are the skill's own slots, and the
    rider needs no boss element."""
    from app.attack_rate import AmmoRefund
    from app.skill_rules.ludmilla_winter_owner import queens_gaze_ammo_refund
    from app.skill_rules.registry import get_skill_ammo_refund

    assert queens_gaze_ammo_refund(LUDMILLA) == AmmoRefund(every_shots=60, rounds=20)
    assert get_skill_ammo_refund("ludmilla-winter-owner", LUDMILLA) == (
        AmmoRefund(every_shots=60, rounds=20), None)


# --- Chisato Nishikigi (SMG/Iron) ---
CHISATO = {
    "extrasensory": {"description_value_06": "53.69", "description_value_08": "48.62",
                     "description_value_10": "22.37"},
    "ap_rounds": {"description_value_01": "10", "description_value_02": "48", "description_value_03": "472.18"},
    "emergency_charge": {"description_value_01": "100", "description_value_02": "73.16", "description_value_03": "10"},
}
CHI = {"slug": "chisato-nishikigi", "element": "Iron"}


def test_chisato_extrasensory_steady_state_self_buffs():
    reg = EffectRegistry()
    rules = {"chisato-nishikigi": build_chisato_rules(CHISATO)}
    ctx = deck_ctx("chisato-nishikigi", "Iron")
    fire_trigger("battle_start", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", CHI, 100.0), 4) == 0.5369       # permanent
    assert round(reg.total_for("true_damage_up", CHI, 100.0), 4) == 0.4862    # permanent
    # The >25% tier: the lowest threshold of the three, so it holds wherever the
    # other two do. Her SMG's 110px spread narrows to 87.6px.
    assert round(reg.total_for("hit_rate", CHI, 100.0), 4) == 0.2237          # permanent
    assert reg.total_for("atk_percent", ALLY, 100.0) == 0.0                   # self-only
    assert reg.total_for("hit_rate", ALLY, 100.0) == 0.0                      # self-only


def test_chisato_burst_atk_and_true_conversion():
    reg = EffectRegistry()
    rules = {"chisato-nishikigi": build_chisato_rules(CHISATO)}
    ctx = deck_ctx("chisato-nishikigi", "Iron")
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", CHI, 0.0), 4) == 0.7316
    assert reg.total_for("normal_attacks_deal_true", CHI, 0.0) == 1.0
    assert reg.total_for("normal_attacks_deal_true", CHI, 10.1) == 0.0  # 10s window


def test_chisato_per_shot_true_nuke_every_48():
    ps = build_chisato_per_shot_rules(CHISATO)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (48, "every")
    reg = EffectRegistry()
    ctx = deck_ctx("chisato-nishikigi", "Iron")
    for rule in rules:
        rule.action(ctx, "chisato-nishikigi", 5.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert [round(p.value, 2) for p in pulses] == [472.18]
    # AP Rounds' nuke is True Damage: ignores enemy DEF, reads true_damage_up.
    assert all(p.damage_type == "true" for p in pulses)


# --- Jill Valentine (AR/Electric) ---
JILL = {
    "magnum_ammo": {"description_value_01": "30", "description_value_02": "9", "description_value_03": "34.99", "description_value_04": "10"},
    "acid_ammo": {"description_value_01": "192", "description_value_02": "1", "description_value_03": "30", "description_value_04": "40.03", "description_value_05": "10"},
    "supercop": {
        "description_value_01": "99.96", "description_value_02": "10", "description_value_03": "100",
        "description_value_04": "80.78", "description_value_05": "10", "description_value_06": "75",
        "description_value_07": "10", "description_value_08": "10",
    },
}
JIL = {"slug": "jill-valentine", "element": "Electric"}


def test_jill_full_burst_self_atk():
    reg = EffectRegistry()
    rules = {"jill-valentine": build_jill_rules(JILL)}
    ctx = deck_ctx("jill-valentine", "Electric")
    fire_trigger("full_burst_enter", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", JIL, 0.0), 4) == 0.4003


def test_jill_burst_true_damage_attack_damage_reload_and_conversion():
    reg = EffectRegistry()
    rules = {"jill-valentine": build_jill_rules(JILL)}
    ctx = deck_ctx("jill-valentine", "Electric")
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert round(reg.total_for("true_damage_up", JIL, 0.0), 4) == 0.3499
    assert round(reg.total_for("attack_damage_up", JIL, 0.0), 4) == 0.75
    assert round(reg.total_for("reload_speed_percent", JIL, 0.0), 4) == 0.9996
    assert reg.total_for("normal_attacks_deal_true", JIL, 0.0) == 1.0
    assert reg.total_for("normal_attacks_deal_true", JIL, 10.1) == 0.0
    # +80.78% shrinks an AR's 75px spread to 19.9px, inside any plausible core,
    # so for these 10 sec every round of hers lands on it.
    assert round(reg.total_for("hit_rate", JIL, 0.0), 4) == 0.8078
    assert reg.total_for("hit_rate", ALLY, 0.0) == 0.0     # "Affects self"
    assert reg.total_for("hit_rate", JIL, 10.1) == 0.0


def test_jill_magnum_per_shot_rules_shape():
    from app.skill_rules.jill_valentine import build_magnum_per_shot_rules
    rules = build_magnum_per_shot_rules(JILL)
    assert len(rules) == 1
    threshold, mode, subrules = rules[0]
    assert (threshold, mode) == (None, "first_bullet")
    # the rule records a 9-shot normal_attack_damage_multiplier grant
    reg = EffectRegistry()
    subrules[0].action(deck_ctx("jill-valentine", "Electric"), "jill-valentine", 0.0, reg)
    grants = reg.round_grants()
    assert len(grants) == 1
    assert grants[0].stat == "normal_attack_damage_multiplier"
    assert grants[0].value == 0.30
    assert grants[0].shots == 9
    assert grants[0].scope == "self"


def test_jill_acid_ammo_periodic_nuke_spec():
    from app.skill_rules.jill_valentine import build_acid_ammo_periodic_nuke
    assert build_acid_ammo_periodic_nuke(JILL) == {
        "cooldown": 1.0, "percent": 192.0, "damage_type": "sustained",
    }


def _jill_raid(rules, per_shot_rules=None, periodic_nukes=None, fight_duration=4.0):
    from app.raid_simulator import simulate_raid
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "jill-valentine", "burst_tier": 3, "element": "Electric", "cooldown": 40.0},
    ]
    return simulate_raid(
        deck=deck,
        rules_by_slug={"buffer": [], "midtier": [], "jill-valentine": rules},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        weapon_stats={"jill-valentine": {
            "weapon": "AR", "damage_percent": 10.0, "max_ammo": 12,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }},
        per_shot_rules=per_shot_rules or {},
        periodic_nukes=periodic_nukes or {},
    )


def test_jill_magnum_boosts_first_9_rounds_of_each_magazine():
    from app.skill_rules.jill_valentine import build_magnum_per_shot_rules
    baseline = _jill_raid([])
    boosted = _jill_raid([], per_shot_rules={"jill-valentine": build_magnum_per_shot_rules(JILL)})
    base = [(e["time"], e["damage"]) for e in baseline["damage_log"] if e["source"] == "normal_attack"]
    boost = [(e["time"], e["damage"]) for e in boosted["damage_log"] if e["source"] == "normal_attack"]
    assert [t for t, _ in base] == [t for t, _ in boost]
    # AR 12/s, 12 ammo, 1s reload: magazines open at 0.0 and 2.0 - rounds 1-9
    # of each magazine are 1.30x, rounds 10-12 are not.
    index_in_magazine = {}
    for (t, base_damage), (_, boost_damage) in zip(base, boost):
        magazine = 0 if t < 2.0 else 1
        idx = index_in_magazine[magazine] = index_in_magazine.get(magazine, 0) + 1
        expected = base_damage * 1.30 if idx <= 9 else base_damage
        assert round(boost_damage, 6) == round(expected, 6), (t, idx)


def test_jill_acid_ammo_ticks_whole_fight_and_scales_with_sustained_damage_up():
    from app.skill_rules._helpers import buff_rule
    from app.skill_rules.jill_valentine import build_acid_ammo_periodic_nuke
    spec = {"jill-valentine": build_acid_ammo_periodic_nuke(JILL)}
    result = _jill_raid([], periodic_nukes=spec, fight_duration=6.0)
    ticks = [(e["time"], e["damage"], e["damage_type"]) for e in result["damage_log"]
             if e["source"] == "periodic"]
    assert [t for t, _, _ in ticks] == [1.0, 2.0, 3.0, 4.0, 5.0]  # whole fight, 1/s
    assert all(dt == "sustained" for _, _, dt in ticks)
    # a sustained_damage_up buff raises the ticks
    buffed = _jill_raid(
        [buff_rule("battle_start", [("sustained_damage_up", 0.5, "self", None)])],
        periodic_nukes=spec, fight_duration=6.0,
    )
    buffed_ticks = [e["damage"] for e in buffed["damage_log"] if e["source"] == "periodic"]
    for base_damage, buffed_damage in zip([d for _, d, _ in ticks], buffed_ticks):
        assert round(buffed_damage, 6) == round(base_damage * 1.5, 6)


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
EXTRASENSORY = CHISATO["extrasensory"]
AP_ROUNDS = CHISATO["ap_rounds"]
EMERGENCY_CHARGE = CHISATO["emergency_charge"]
MAGNUM_AMMO = JILL["magnum_ammo"]
ACID_AMMO = JILL["acid_ammo"]
SUPERCOP = JILL["supercop"]
QUEENS_GAZE = LUDMILLA["queens_gaze"]
SNOWSTORM = LUDMILLA["snowstorm"]
GUIDING_LANTERN = LUDMILLA["guiding_lantern"]
