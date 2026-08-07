from app.effects import EffectRegistry
from app.skill_rules.anchor_innocent_maid import build_anchor_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
# Starfish (Shaped) Omurice (skills[0]) - escalating on Full Burst enter.
STARFISH_OMURICE = {
    "description_value_01": "30.96",  # Once: Potency of HP (not modeled)
    "description_value_02": "5",
    "description_value_03": "30.4",   # Twice: Distributed Damage %
    "description_value_04": "10",
    "description_value_05": "1",      # Three times: debuff stack -1 (Mast synergy)
    "description_value_06": "3.04",
    "description_value_07": "8",
}
# Sea Anemone (Shaped) Pasta (skills[1]) - escalating on Full Burst end.
SEA_ANEMONE_PASTA = {
    "description_value_01": "10.13",  # Once: squad Hit Rate %
    "description_value_02": "10",
    "description_value_03": "35.02",  # Twice: ATK % of caster's ATK
    "description_value_04": "10",
    "description_value_05": "40.04",  # Three times: Reloading Speed %
    "description_value_06": "15",
}
# Seaside Stroll (skills[2], burst).
SEASIDE_STROLL = {
    "description_value_01": "60.19",
    "description_value_02": "25",
    "description_value_03": "40.18",  # heal (not modeled)
    "description_value_04": "30.09",  # ATK % of caster's ATK
    "description_value_05": "10",
}


def make_context():
    return SquadContext(
        [
            SquadMember("anchor-innocent-maid", burst_tier=2, element="Water"),
            SquadMember("ally", burst_tier=3, element="Fire"),
        ]
    )


def build(caster_atk=10000):
    values = {
        "starfish_omurice": STARFISH_OMURICE,
        "sea_anemone_pasta": SEA_ANEMONE_PASTA,
        "seaside_stroll": SEASIDE_STROLL,
        "caster_atk": caster_atk,
    }
    return build_anchor_rules(values)


def test_starfish_omurice_grants_distributed_damage_from_the_twice_tier():
    # Starfish escalates on Full Burst enter; its Twice tier is a squad
    # Distributed Damage buff (DPS synergy for Distributed-Damage dealers).
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"anchor-innocent-maid": build()}
    ally = {"slug": "ally", "element": "Fire"}

    # Cycle 1 (Once): Potency of HP only - no distributed-damage buff yet.
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    assert registry.total_for("distributed_damage_up", ally, now=5.0) == 0.0

    # Cycle 2 (Twice): Distributed Damage unlocks. 30.4% for 10 sec.
    fire_trigger("full_burst_enter", rules, ctx, registry, time=20.0)
    assert round(registry.total_for("distributed_damage_up", ally, now=20.0), 4) == 0.304
    assert registry.total_for("distributed_damage_up", ally, now=30.1) == 0.0


def test_sea_anemone_pasta_escalates_over_burst_cycles():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"anchor-innocent-maid": build()}
    ally = {"slug": "ally", "element": "Fire"}

    # Cycle 1 (Once): only Hit Rate, which is not modeled -> no DPS effects.
    fire_trigger("full_burst_end", rules, ctx, registry, time=10.0)
    assert registry.total_for("flat_atk", ally, now=10.0) == 0.0
    assert registry.total_for("reload_speed_percent", ally, now=10.0) == 0.0

    # Cycle 2 (Twice): ATK buff unlocks. 35.02% of caster ATK 10000 = 3502.
    fire_trigger("full_burst_end", rules, ctx, registry, time=30.0)
    assert registry.total_for("flat_atk", ally, now=30.0) == 3502.0
    assert registry.total_for("reload_speed_percent", ally, now=30.0) == 0.0

    # Cycle 3 (Three times): Reloading Speed unlocks; ATK re-applied fresh.
    fire_trigger("full_burst_end", rules, ctx, registry, time=50.0)
    assert registry.total_for("flat_atk", ally, now=50.0) == 3502.0
    assert round(registry.total_for("reload_speed_percent", ally, now=50.0), 4) == 0.4004


def test_sea_anemone_pasta_hit_rate_unlocks_on_the_first_activation():
    """The Once tier, which sat empty while Hit Rate had no consumer. Cumulative
    like the rest: every later cycle re-applies it alongside the tiers above."""
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"anchor-innocent-maid": build()}
    ally = {"slug": "ally", "element": "Fire"}

    fire_trigger("full_burst_end", rules, ctx, registry, time=10.0)   # cycle 1
    assert round(registry.total_for("hit_rate", ally, now=10.0), 4) == 0.1013
    assert registry.total_for("hit_rate", ally, now=20.1) == 0.0      # 10s duration

    fire_trigger("full_burst_end", rules, ctx, registry, time=30.0)   # cycle 2
    assert round(registry.total_for("hit_rate", ally, now=30.0), 4) == 0.1013


def test_sea_anemone_pasta_atk_buff_scales_with_caster_atk():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"anchor-innocent-maid": build(caster_atk=20000)}
    ally = {"slug": "ally", "element": "Fire"}

    fire_trigger("full_burst_end", rules, ctx, registry, time=10.0)  # cycle 1
    fire_trigger("full_burst_end", rules, ctx, registry, time=30.0)  # cycle 2 unlocks ATK
    assert registry.total_for("flat_atk", ally, now=30.0) == 7004.0  # 35.02% of 20000


def test_seaside_stroll_grants_squad_atk_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"anchor-innocent-maid": build()}
    ally = {"slug": "ally", "element": "Fire"}

    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)
    # 30.09% of caster ATK 10000 = 3009, for 10 sec.
    assert registry.total_for("flat_atk", ally, now=5.0) == 3009.0
    assert registry.total_for("flat_atk", ally, now=15.1) == 0.0
