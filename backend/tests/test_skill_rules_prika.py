from app.effects import EffectRegistry
from app.skill_rules.prika import build_lets_get_show_started_rules, build_prika_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Prika is not on dotgg).
GET_READY_FOR_AN_AMAZING_SHOW = {
    "description_value_01": "3.04",   # self HP recovery %/sec (not modeled)
    "description_value_02": "25",     # duration
    "description_value_03": "25",     # squad Charge Damage %
    "description_value_04": "25",     # duration
}
ONE_MORE_SONG = {
    "description_value_01": "19.98",  # self Max HP % of her own
    "description_value_02": "10",     # duration
    "description_value_03": "21",     # Performance duration extension (not modeled)
    "description_value_04": "25.01",  # Encore squad Attack Damage %
    "description_value_05": "10",     # duration
    "description_value_06": "21",     # Encore: self Burst cooldown increase
}
LETS_GET_THE_SHOW_STARTED = {
    "description_value_01": "20",     # squad Projectile Explosion Damage %
    "description_value_02": "3",      # duration
    "description_value_03": "13.09",  # squad Pierce Damage %
    "description_value_04": "3",      # duration
    "description_value_05": "20",     # squad ATK % of caster's ATK
    "description_value_06": "3",      # duration
    "description_value_07": "49.92",  # self outgoing healing % (not modeled)
    "caster_atk": 300000,
}

# Slot-only view of the above (drops the bundled caster_atk) so the assembly
# verification harness compares only the skill's description_value slots.
LETS_GET_THE_SHOW_STARTED_SLOTS = {
    k: v for k, v in LETS_GET_THE_SHOW_STARTED.items() if k.startswith("description_value")
}


def make_context():
    return SquadContext([
        SquadMember("prika", burst_tier=2, element="Water"),
        SquadMember("mint", burst_tier=2, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def solo_context():
    # No Mint -> Charge Damage keeps its stated 25 sec duration (not maintained).
    return SquadContext([
        SquadMember("prika", burst_tier=2, element="Water"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


PRIKA_MAX_HP = 700_000.0


def build():
    return build_prika_rules({
        "get_ready_for_an_amazing_show": GET_READY_FOR_AN_AMAZING_SHOW,
        "one_more_song": ONE_MORE_SONG,
        "caster_max_hp": PRIKA_MAX_HP,
    })


ALLY = {"slug": "ally", "element": "Fire"}
PRIKA = {"slug": "prika", "element": "Water"}


def test_one_more_song_grants_self_max_hp_on_full_burst():
    # 소비자가 덱에 있을 때만 딜이 되지만(Max HP를 ATK로 환산하는 유닛),
    # 스탯 자체는 부여자 쪽에서 정직하게 등록해 둔다.
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"prika": build()}, ctx, registry, time=5.0)
    assert round(registry.total_for("flat_max_hp", PRIKA, now=5.0), 2) == round(PRIKA_MAX_HP * 0.1998, 2)
    assert registry.total_for("flat_max_hp", ALLY, now=5.0) == 0.0  # self 스코프
    assert registry.total_for("flat_max_hp", PRIKA, now=15.1) == 0.0  # 10초


def test_burst_charge_damage_lasts_25s_solo_and_sets_performance_status():
    ctx = solo_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"prika": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("charge_damage_bonus", ALLY, now=5.0), 4) == 0.25
    assert registry.total_for("charge_damage_bonus", ALLY, now=29.9) == 0.25
    assert registry.total_for("charge_damage_bonus", ALLY, now=30.1) == 0.0
    assert ctx.has_status("prika", "performance") is True


def test_burst_charge_damage_is_permanent_when_mint_is_present():
    # With Mint in the deck, Encore keeps extending Performance, so Charge Damage
    # is modeled as permanent (a single +25%, never re-added/stacked).
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"prika": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("charge_damage_bonus", ALLY, now=170.0), 4) == 0.25


def test_encore_fires_on_mint_burst_while_in_performance():
    # Prika bursts first (Performance), then Mint bursts (Sing Along) -> Encore
    # grants squad Attack Damage and pins Mint Singing. Charge Damage is NOT
    # re-added (that would double-count); it's already permanent from the burst.
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"prika": build()}
    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)  # Prika burst
    ctx.last_burst_slug = "mint"
    fire_trigger("ally_burst_activate", rules, ctx, registry, time=30.0)  # Mint burst

    assert round(registry.total_for("attack_damage_up", ALLY, now=30.0), 4) == 0.2501
    assert registry.total_for("attack_damage_up", ALLY, now=40.1) == 0.0  # 10s duration
    # Charge Damage stays a single +25% (permanent from the burst, not stacked).
    assert round(registry.total_for("charge_damage_bonus", ALLY, now=50.0), 4) == 0.25
    assert ctx.has_status("mint", "singing") is True


def test_encore_does_not_fire_before_prika_bursts():
    # No Performance status yet -> Mint bursting must not trigger Encore.
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"prika": build()}
    ctx.last_burst_slug = "mint"
    fire_trigger("ally_burst_activate", rules, ctx, registry, time=30.0)

    assert registry.total_for("attack_damage_up", ALLY, now=30.0) == 0.0
    assert ctx.has_status("mint", "singing") is False


def test_encore_ignores_a_non_mint_ally_burst():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"prika": build()}
    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)  # Prika in Performance
    ctx.last_burst_slug = "ally"
    fire_trigger("ally_burst_activate", rules, ctx, registry, time=30.0)

    assert registry.total_for("attack_damage_up", ALLY, now=30.0) == 0.0


def test_lets_get_show_started_full_charge_squad_buffs():
    rules = build_lets_get_show_started_rules(LETS_GET_THE_SHOW_STARTED)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (1, "every")  # every full charge (SR)

    ctx = make_context()
    registry = EffectRegistry()
    for rule in skill_rules:
        rule.action(ctx, "prika", 8.0, registry)

    assert round(registry.total_for("projectile_explosion_damage_up", ALLY, now=8.0), 4) == 0.20
    assert round(registry.total_for("pierce_damage_up", ALLY, now=8.0), 4) == 0.1309
    assert round(registry.total_for("flat_atk", ALLY, now=8.0), 2) == round(300000 * 0.20, 2)
    assert registry.total_for("flat_atk", ALLY, now=11.1) == 0.0  # 3s duration


def test_lets_get_show_started_buffs_refresh_not_stack_over_shots():
    # Applied every full charge - overlapping re-applications must REFRESH to a
    # single value, not stack to their sum.
    rules = build_lets_get_show_started_rules(LETS_GET_THE_SHOW_STARTED)
    _, _, skill_rules = rules[0]
    ctx = make_context()
    registry = EffectRegistry()
    for shot_time in (8.0, 9.0, 10.0):  # three overlapping 3s applications
        for rule in skill_rules:
            rule.action(ctx, "prika", shot_time, registry)

    assert round(registry.total_for("flat_atk", ALLY, now=10.5), 2) == round(300000 * 0.20, 2)  # not x3
    assert round(registry.total_for("projectile_explosion_damage_up", ALLY, now=10.5), 4) == 0.20


def test_prika_bursts_once_then_mint_owns_the_tier2_slot():
    # Fienn (2026-07-17): Encore raises Prika's own burst cooldown +21s per
    # trigger, so after her cycle-1 burst Mint bursts every later cycle.
    # Encore itself only needs a deck member SLUGGED "mint" to burst (the
    # ally_bursted gate) - Mint's own rules aren't required for rotation.
    from app.raid_simulator import simulate_raid

    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Fire", "cooldown": 20.0},
        {"slug": "prika", "burst_tier": 2, "element": "Water", "cooldown": 40.0},
        {"slug": "mint", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "element": "Fire", "cooldown": 20.0},
    ]
    result = simulate_raid(
        deck=deck,
        rules_by_slug={"prika": build(), "b1": [], "mint": [], "b3": []},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=180.0,
        base_crit_rate=0.0,
    )
    bursts = [e for e in result["events"] if e["type"] == "burst" and e["tier"] == 2]
    prika_bursts = [e for e in bursts if e["slug"] == "prika"]
    mint_bursts = [e for e in bursts if e["slug"] == "mint"]
    assert len(prika_bursts) == 1 and prika_bursts[0]["time"] < 10.0
    assert len(mint_bursts) >= 5  # every later cycle
