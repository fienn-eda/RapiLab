"""Tests for the third batch of Burst-1 supporters: Little Mermaid, Moran,
Tove, Soline: Frost Ticket. Values are the real max-level (dollskill for
Moran/Tove) figures from dotgg.
"""
from app.effects import EffectRegistry
from app.skill_rules.little_mermaid import build_little_mermaid_rules
from app.skill_rules.moran import build_bring_it_on_per_shot_rules, build_moran_rules
from app.skill_rules.soline_frost_ticket import build_soline_frost_ticket_rules
from app.skill_rules.tove import build_tove_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Fire"}


def deck_ctx(src_slug):
    return SquadContext([
        SquadMember(src_slug, burst_tier=1, element="Water"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


LM = {
    "bubble_order": {
        "description_value_01": "7.48", "description_value_02": "4", "description_value_03": "10",
        "description_value_04": "400", "description_value_05": "37",
    },
    "bubble_wave": {
        # dotgg-native slot numbering (this module's established convention -
        # dotgg reuses value_01 for Explosive Bubble, so left-to-right counting
        # of the lootandwaifus text runs one slot ahead; caught by the
        # assembly verification harness at Phase C integration).
        "description_value_01": "5.05",   # Bubble: enemy Damage Taken %, continuous
        "description_value_04": "1",      # FB nuke: every N sec during Full Burst
        "description_value_05": "63.36",  # FB nuke: % of final ATK per hit
        "description_value_06": "4",      # FB nuke: sequential hit count
        "description_value_07": "500",    # Bubble Barrage: allies' total ammo threshold
        "description_value_08": "85",     # Bubble Barrage: % of final ATK per hit
        "description_value_09": "10",     # Bubble Barrage: sequential hit count
    },
    "sirens_song": {
        "description_value_01": "10.13", "description_value_02": "10", "description_value_03": "33.26",
        "description_value_04": "17.28", "description_value_05": "10",
    },
}

# Module-level aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
BUBBLE_ORDER = LM["bubble_order"]
BUBBLE_WAVE = LM["bubble_wave"]
SIRENS_SONG = LM["sirens_song"]


def test_little_mermaid_cdr_and_attack_damage_and_self_atk():
    reg = EffectRegistry()
    rules = {"little-mermaid": build_little_mermaid_rules(LM)}
    fire_trigger("full_burst_end", rules, deck_ctx("little-mermaid"), reg, 0.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 7.48
    fire_trigger("full_burst_enter", rules, deck_ctx("little-mermaid"), reg, 0.0)
    assert round(reg.total_for("attack_damage_up", ALLY, 0.0), 4) == 0.04
    reg2 = EffectRegistry()
    fire_trigger("own_burst_activate", rules, deck_ctx("little-mermaid"), reg2, 0.0)
    assert round(reg2.total_for("attack_damage_up", ALLY, 0.0), 4) == 0.1013
    lm = {"slug": "little-mermaid", "element": "Water"}
    assert round(reg2.total_for("atk_percent", lm, 0.0), 4) == 0.1728


def test_little_mermaid_bubble_debuff_is_a_permanent_squad_enemy_damage_taken():
    reg = EffectRegistry()
    rules = {"little-mermaid": build_little_mermaid_rules(LM)}
    # "Bubble: Damage Taken +5.05% continuously" activates when the enemy
    # appears (= battle start in a raid), permanent, squad-scoped enemy debuff.
    fire_trigger("battle_start", rules, deck_ctx("little-mermaid"), reg, 0.0)
    assert round(reg.total_for("damage_taken_up", ALLY, 0.0), 4) == 0.0505
    assert round(reg.total_for("damage_taken_up", ALLY, 170.0), 4) == 0.0505  # permanent


# Base ("skills") level-10 values - slug "moran". Leave It To Me! has no slot 10
# (the burst-cooldown cut) and Fair and Square! no slots 09/10 (the squad ATK):
# both are text the Favorite Item adds, which is why base Moran has no SkillRules.
MORAN_BASE_BRING_IT_ON = {
    "description_value_01": "3.51",   # DEF per 1% HP lost (survivability, skipped)
    "description_value_02": "47.18",  # additional damage %
    "description_value_03": "5",      # normal attacks, while weapon is changed
}
MORAN_BASE_LEAVE_IT_TO_ME = {
    "description_value_01": "91", "description_value_02": "3",
    "description_value_03": "69.84", "description_value_04": "3",
    "description_value_05": "51.09", "description_value_06": "3",
    "description_value_07": "3", "description_value_08": "4", "description_value_09": "20",
}
MORAN_BASE_FAIR_AND_SQUARE = {
    "description_value_01": "14.7", "description_value_02": "36.14",
    "description_value_03": "10", "description_value_04": "10",
    "description_value_05": "35.14", "description_value_06": "10",
    "description_value_07": "14.85", "description_value_08": "10",
}
MORAN_BASE = {
    "bring_it_on": MORAN_BASE_BRING_IT_ON,
    "leave_it_to_me": MORAN_BASE_LEAVE_IT_TO_ME,
    "fair_and_square": MORAN_BASE_FAIR_AND_SQUARE,
    "caster_atk": 300000,
}

# Favorite Item ("dollskills") - slug "moran-signature".
MORAN_SIG_BRING_IT_ON = dict(MORAN_BASE_BRING_IT_ON, description_value_04="20")
MORAN_SIG_LEAVE_IT_TO_ME = dict(MORAN_BASE_LEAVE_IT_TO_ME, description_value_10="7.48")
MORAN_SIG_FAIR_AND_SQUARE = dict(
    MORAN_BASE_FAIR_AND_SQUARE, description_value_09="42.57", description_value_10="10"
)

MORAN = {
    "bring_it_on": MORAN_SIG_BRING_IT_ON,
    "leave_it_to_me": {"description_value_10": "7.48"},
    "fair_and_square": {
        "description_value_01": "14.7",   # weapon-transform damage % per shot
        "description_value_04": "10",     # unlimited-ammo / transform window sec
        "description_value_09": "42.57",  # squad ATK % of caster
        "description_value_10": "10",     # ATK duration
    },
    "caster_atk": 300000,
}


def test_moran_squad_cdr_and_caster_scaled_flat_atk():
    reg = EffectRegistry()
    rules = {"moran": build_moran_rules(MORAN)}
    fire_trigger("full_burst_enter", rules, deck_ctx("moran"), reg, 0.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 7.48
    fire_trigger("own_burst_activate", rules, deck_ctx("moran"), reg, 0.0)
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == round(300000 * 0.4257, 2)


def test_moran_transform_is_an_unlimited_ammo_smg_at_canonical_rate():
    from app.attack_rate import rate_of_fire_for_weapon
    from app.skill_rules.moran import build_fair_and_square_weapon_mode_schedule

    schedule = build_fair_and_square_weapon_mode_schedule(MORAN)
    ctx = deck_ctx("moran")
    ctx.burst_times["moran"] = [10.0, 60.0]

    segments = schedule(ctx, 180.0)
    assert [seg["start"] for seg in segments] == [10.0, 60.0]
    assert [seg["end"] for seg in segments] == [20.0, 70.0]  # 10 sec window

    profile = segments[0]["profile"]
    assert profile["weapon"] == "SMG"
    assert profile["damage_percent"] == 14.7
    # infinite ammo -> no measured count; anchored to the canonical SMG rate.
    assert profile["rate_of_fire"] == rate_of_fire_for_weapon("SMG") == 20.0
    assert "until_shots" not in segments[0]  # end-bounded, not a measured count
    assert "damage_type" not in profile      # ordinary attack damage, no true conversion


TOVE = {
    "modification_successful": {"description_value_01": "10.08", "description_value_02": "42.24"},
    "miracle_of_makeshifts": {
        "description_value_01": "2.32", "description_value_02": "15",
        "description_value_03": "24.21", "description_value_04": "15",
    },
    "caster_atk": 300000,
}


def test_tove_squad_crit_rate_and_stacked_flat_atk():
    reg = EffectRegistry()
    rules = {"tove": build_tove_rules(TOVE)}
    fire_trigger("battle_start", rules, deck_ctx("tove"), reg, 0.0)
    assert round(reg.total_for("crit_rate", ALLY, 0.0), 4) == 0.1008
    fire_trigger("own_burst_activate", rules, deck_ctx("tove"), reg, 0.0)
    # 2.32% of ATK per stack * 3 max stacks = 6.96% of 300000 = 20880
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == round(300000 * 0.0232 * 3, 2)


def _tove_weapon_ctx():
    return SquadContext([
        SquadMember("tove", burst_tier=1, element="Water", weapon="AR"),
        SquadMember("sg-ally", burst_tier=3, element="Fire", weapon="SG"),
        SquadMember("ar-ally", burst_tier=3, element="Fire", weapon="AR"),
    ])


SG_ALLY = {"slug": "sg-ally", "element": "Fire"}
AR_ALLY = {"slug": "ar-ally", "element": "Fire"}


def test_tove_sg_ally_attack_speed_continuous():
    # Modification Successful 2nd bullet: SG allies Attack Speed +42.24%,
    # continuous under the module's full-stack steady-state assumption (gap #3).
    reg = EffectRegistry()
    rules = {"tove": build_tove_rules(TOVE)}
    fire_trigger("battle_start", rules, _tove_weapon_ctx(), reg, 0.0)
    assert round(reg.total_for("attack_speed_percent", SG_ALLY, 100.0), 4) == 0.4224
    assert reg.total_for("attack_speed_percent", AR_ALLY, 100.0) == 0.0


def test_tove_sg_ally_burst_flat_atk():
    # Miracle of Makeshifts 2nd bullet: SG allies ATK +24.21% of caster's ATK
    # per stack, mirroring the 3 max Temporary Modification stacks, 15s.
    reg = EffectRegistry()
    rules = {"tove": build_tove_rules(TOVE)}
    fire_trigger("own_burst_activate", rules, _tove_weapon_ctx(), reg, 5.0)
    squad_part = 300000 * 0.0232 * 3
    sg_part = 300000 * 0.2421 * 3
    assert round(reg.total_for("flat_atk", SG_ALLY, 5.0), 2) == round(squad_part + sg_part, 2)
    assert round(reg.total_for("flat_atk", AR_ALLY, 5.0), 2) == round(squad_part, 2)
    assert reg.total_for("flat_atk", SG_ALLY, 20.1) == 0.0  # 15s duration


def test_tove_attack_speed_raises_sg_ally_shot_count():
    # Deck-level: the SG ally genuinely fires more shots with Tove present
    # (attack_speed_percent is live-read per magazine, Phase S wiring).
    from app.raid_simulator import simulate_raid

    def run(rules):
        return simulate_raid(
            deck=[
                {"slug": "tove", "burst_tier": 1, "element": "Water", "cooldown": 20.0, "weapon": "AR"},
                {"slug": "sg-ally", "burst_tier": 3, "element": "Fire", "cooldown": 40.0, "weapon": "SG"},
            ],
            rules_by_slug={"tove": rules, "sg-ally": []},
            burst_damage_percents={},
            base_stats={"tove": {"atk": 300000}, "sg-ally": {"atk": 200000}},
            enemy_def=0,
            gauge_charge_time=5.0,
            fight_duration=5.0,
            base_crit_rate=0.0,
            weapon_stats={"sg-ally": {"weapon": "SG", "damage_percent": 200.0, "max_ammo": 9,
                                      "reload_time": 1.5, "charge_time": 0.0,
                                      "charge_damage_percent": 100.0}},
        )

    without = run([])
    with_tove = run(build_tove_rules(TOVE))
    shots_without = [e for e in without["damage_log"] if e["source"] == "normal_attack"]
    shots_with = [e for e in with_tove["damage_log"] if e["source"] == "normal_attack"]
    assert shots_without and len(shots_with) > len(shots_without)


def test_little_mermaid_bubble_wave_fb_nuke_spec():
    from app.skill_rules.little_mermaid import build_bubble_wave_fb_nuke
    spec = build_bubble_wave_fb_nuke(LM)
    assert spec == {
        "cooldown": 1.0, "percent": 63.36, "hit_count": 4, "during_full_burst": True,
    }


def test_little_mermaid_bubble_barrage_fires_per_500_squad_bullets():
    from app.skill_rules.little_mermaid import build_bubble_barrage_scheduled_nukes

    specs = build_bubble_barrage_scheduled_nukes(LM)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["percent"] == 85.0
    assert not spec.get("full_burst_bonus_eligible", False)  # "as damage"

    # 600 squad-wide bullets (two units x 300): the merged timeline crosses 500
    # once, at the moment the 500th bullet fires - 10 hits at that instant.
    ctx = deck_ctx("little-mermaid")
    ctx.shot_times = {
        "little-mermaid": [t * 0.1 for t in range(1, 301)],       # 0.1..30.0
        "ally": [t * 0.1 + 0.05 for t in range(1, 301)],          # 0.15..30.05
    }
    times = spec["schedule"](ctx, 180.0)
    merged = sorted(ctx.shot_times["little-mermaid"] + ctx.shot_times["ally"])
    assert times == [merged[499]] * 10


def test_little_mermaid_bubble_barrage_drops_hits_past_fight_end():
    from app.skill_rules.little_mermaid import build_bubble_barrage_scheduled_nukes

    spec = build_bubble_barrage_scheduled_nukes(LM)[0]
    ctx = deck_ctx("little-mermaid")
    # 500th bullet lands after the fight is over -> nothing fires.
    ctx.shot_times = {"little-mermaid": [t * 1.0 for t in range(1, 501)]}
    assert spec["schedule"](ctx, 180.0) == []


def test_little_mermaid_bubble_wave_ticks_only_in_fb_windows():
    from app.raid_simulator import simulate_raid
    from app.skill_rules.little_mermaid import build_bubble_wave_fb_nuke

    deck = [
        {"slug": "little-mermaid", "burst_tier": 1, "element": "Water", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Fire", "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "element": "Fire", "cooldown": 20.0},
    ]
    result = simulate_raid(
        deck=deck,
        rules_by_slug={m["slug"]: [] for m in deck},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        periodic_nukes={"little-mermaid": build_bubble_wave_fb_nuke(LM)},
    )
    windows = list(zip(
        (e["time"] for e in result["events"] if e["type"] == "full_burst_start"),
        (e["time"] for e in result["events"] if e["type"] == "full_burst_end"),
    ))
    ticks = [e["time"] for e in result["damage_log"] if e["source"] == "periodic"]
    assert ticks
    for t in ticks:
        assert any(start < t < end for start, end in windows)
    start, end = windows[0]
    assert ticks.count(start + 1.0) == 4  # 4 sequential hits per tick


CHECK_TICKET = {"description_value_03": "7.48"}


def test_soline_frost_ticket_only_cdr():
    reg = EffectRegistry()
    rules = {"soline-frost-ticket": build_soline_frost_ticket_rules({"check_ticket": CHECK_TICKET})}
    fire_trigger("full_burst_enter", rules, deck_ctx("soline-frost-ticket"), reg, 0.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 7.48


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
MODIFICATION_SUCCESSFUL = TOVE["modification_successful"]
MIRACLE_OF_MAKESHIFTS = TOVE["miracle_of_makeshifts"]
LEAVE_IT_TO_ME = MORAN["leave_it_to_me"]
FAIR_AND_SQUARE = MORAN["fair_and_square"]


def test_moran_bring_it_on_rider_only_counts_shots_inside_the_transform():
    # "While weapon is changed" is her own transform window, so the rider rides
    # the weapon-mode segment rather than her ordinary AR fire. Identical text in
    # both builds, so one builder serves both slugs.
    ps = build_bring_it_on_per_shot_rules(MORAN_BASE)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (5, "every_during_segment")

    reg = EffectRegistry()
    for rule in rules:
        rule.action(deck_ctx("moran"), "moran", 3.0, reg)

    pulses = reg.drain_pulses("instant_damage_percent")
    assert [p.value for p in pulses] == [47.18]
    # "as additional damage" -> eligible for the Full Burst bonus.
    assert pulses[0].full_burst_bonus_eligible is True


def test_base_moran_registers_no_skill_rules():
    # Everything base Moran does outside the transform is survivability or an
    # ally-side Damage Taken cut. Her buffer role - the burst-cooldown cut and
    # the squad flat ATK - is entirely the Favorite Item's text.
    from app.skill_rules.registry import build_nikke_rules

    rules, burst_percent = build_nikke_rules("moran", MORAN_BASE)
    assert rules == []
    assert burst_percent is None


def test_moran_transform_schedule_anchors_on_the_slug_it_is_built_for():
    from app.skill_rules.moran import build_fair_and_square_weapon_mode_schedule

    schedule = build_fair_and_square_weapon_mode_schedule(MORAN, slug="moran-signature")
    ctx = deck_ctx("moran")
    ctx.burst_times["moran"] = [10.0]
    ctx.burst_times["moran-signature"] = [20.0]
    assert [w["start"] for w in schedule(ctx, 120.0)] == [20.0]
