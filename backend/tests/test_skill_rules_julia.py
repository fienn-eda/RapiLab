"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill."""
from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.julia import (
    DECRESCENDO_COOLDOWN,
    build_climax_resource_scaled_nuke,
    build_crescendo_resources,
    build_decrescendo_rules,
    climax_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

JULIA_VALUES = {
    "decrescendo": {"description_value_01": "26.04", "description_value_02": "10"},
    "crescendo": {"description_value_01": "24.79", "description_value_02": "5", "description_value_03": "15"},
    "climax": {"description_value_01": "5", "description_value_02": "544.5", "description_value_03": "544.5"},
}

JULIA = {"slug": "julia", "element": "Water"}


def make_context():
    return SquadContext([
        SquadMember("julia", burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_decrescendo_cooldown_is_20s():
    assert DECRESCENDO_COOLDOWN == 20.0


def test_decrescendo_self_crit_rate_for_10_sec():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_decrescendo_rules(JULIA_VALUES["decrescendo"]):
        rule.action(ctx, "julia", 20.0, reg)
    assert round(reg.total_for("crit_rate", JULIA, now=20.0), 4) == 0.2604
    assert reg.total_for("crit_rate", JULIA, now=30.1) == 0.0  # 10s window


def test_decrescendo_rules_are_labeled_periodic():
    assert all(r.trigger == "periodic" for r in build_decrescendo_rules(JULIA_VALUES["decrescendo"]))


def test_climax_burst_percent_is_base_hit_only():
    assert climax_burst_percent(JULIA_VALUES) == 544.5


def test_crescendo_resource_fills_on_last_bullet_capped_at_5_lasting_15_sec():
    specs = build_crescendo_resources(JULIA_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.name == "crescendo"
    assert spec.fill == ("on_last_bullet",)
    assert spec.cap == 5
    assert len(spec.buffs) == 1
    buff = spec.buffs[0]
    assert buff.stat == "other_critical_damage_sources"
    assert buff.scope == "self"
    assert buff.lifetime == 15.0
    assert round(buff.value_fn(5), 4) == round(0.2479 * 5, 4)


def test_climax_resource_scaled_nuke_gates_on_crescendo_at_max_stacks():
    specs = build_climax_resource_scaled_nuke(JULIA_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["resource"] == "crescendo"
    assert spec["cap"] == 5
    assert spec["base_percent"] == 544.5
    assert spec["tick_count"] == 1
    assert spec["resolves_after_cast"] is True
    assert spec["scale_fn"](4) == 0.0   # below max stacks - gate fails
    assert spec["scale_fn"](5) == 1.0   # at max stacks - gate passes


def _make_julia_deck_and_stats():
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "julia", "burst_tier": 3, "element": "Water", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "julia": {"atk": 10000, "def": 0, "max_hp": 0},
    }
    return deck, base_stats


def test_julia_end_to_end_climax_additional_hit_does_not_fire_below_max_stacks():
    # AR (12/s), 3-round magazine, 1s reload -> magazines empty (Crescendo
    # stacks) at t=2/12 and t=1.25+2/12; her burst fires at t=5.0, so
    # Crescendo is only at 2 stacks (not 5) - gate fails, no additional hit.
    deck, base_stats = _make_julia_deck_and_stats()
    weapon_stats = {
        "julia": {
            "weapon": "AR", "damage_percent": 5.0, "max_ammo": 3,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "julia": []},
        burst_damage_percents={"julia": climax_burst_percent(JULIA_VALUES)},
        base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        weapon_stats=weapon_stats,
        resource_specs={"julia": build_crescendo_resources(JULIA_VALUES)},
        resource_scaled_nukes={"julia": build_climax_resource_scaled_nuke(JULIA_VALUES)},
    )
    gated_hits = [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"]
    assert len(gated_hits) == 1
    assert gated_hits[0]["damage"] == 0.0  # count=2 at burst time -> gate closed
    base_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert len(base_hits) == 1
    assert base_hits[0]["damage"] == 54450.0  # 10000 * 544.5% (base hit unaffected)


def test_julia_end_to_end_climax_additional_hit_fires_once_crescendo_hits_max_stacks():
    # AR (12/s), 1-round magazine + 0.5s reload -> EVERY shot is a last
    # bullet, so Crescendo caps at 5 stacks (each lasting 15s) well before
    # her burst fires at t=5.0 - the gated additional hit fires alongside
    # the base hit, and (per its own "as additional damage" text) gets the
    # Full Burst Bonus, unlike the base hit ("as damage", no bonus).
    deck, base_stats = _make_julia_deck_and_stats()
    weapon_stats = {
        "julia": {
            "weapon": "AR", "damage_percent": 5.0, "max_ammo": 1,
            "reload_time": 0.5, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "julia": []},
        burst_damage_percents={"julia": climax_burst_percent(JULIA_VALUES)},
        base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=6.0, mode="auto", base_crit_rate=0.0,
        weapon_stats=weapon_stats,
        resource_specs={"julia": build_crescendo_resources(JULIA_VALUES)},
        resource_scaled_nukes={"julia": build_climax_resource_scaled_nuke(JULIA_VALUES)},
    )
    gated_hits = [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"]
    assert len(gated_hits) == 1
    assert round(gated_hits[0]["time"], 4) == 5.0
    assert round(gated_hits[0]["damage"], 4) == round(10000 * 5.445 * 1.5, 4)  # 544.5% * (1 + FB bonus*0.5)
    base_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert base_hits[0]["damage"] == 54450.0  # base hit: no FB bonus (not "as additional damage")


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
DECRESCENDO = JULIA_VALUES["decrescendo"]
CRESCENDO = JULIA_VALUES["crescendo"]
CLIMAX = JULIA_VALUES["climax"]
