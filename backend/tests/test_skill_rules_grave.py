from app.effects import EffectRegistry
from app.skill_rules.grave import build_grave_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
HEAT_EMISSION = {
    "description_value_01": "100",    # bullets removed % (not modeled)
    "description_value_02": "50",     # self Reload Ratio down % (not modeled)
    "description_value_03": "2",      # self HP regen %/sec (not modeled)
    "description_value_04": "38.96",  # Burst Gauge fill speed % (not modeled)
    "description_value_05": "48.4",   # squad Pierce Damage % (continuous)
}
PLOT_SPOILER = {
    "description_value_01": "1",      # self HP drain %/sec (not modeled)
    "description_value_02": "52.8",   # self Pierce Damage %
    "description_value_03": "48.2",   # squad Attack Damage %
    "description_value_04": "39.98",  # squad Pierce Damage %
    "description_value_05": "3",      # squad Max Ammo +N rounds (not modeled)
    "description_value_06": "85.19",  # squad Critical Rate %
}


def make_context():
    return SquadContext([
        SquadMember("grave", burst_tier=2, element="Fire"),
        SquadMember("ally", burst_tier=3, element="Wind"),
    ])


def build():
    return build_grave_rules({"heat_emission": HEAT_EMISSION, "plot_spoiler": PLOT_SPOILER})


GRAVE = {"slug": "grave", "element": "Fire"}
ALLY = {"slug": "ally", "element": "Wind"}


def test_plot_spoiler_grants_self_pierce_and_squad_buffs():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"grave": build()}, ctx, registry, time=5.0)

    # Grave herself is in the squad, so she gets her self-scoped Pierce Damage
    # (52.8%) PLUS the squad-wide Pierce Damage (39.98%) = 92.78%.
    assert round(registry.total_for("pierce_damage_up", GRAVE, now=5.0), 4) == 0.9278
    assert round(registry.total_for("pierce_damage_up", ALLY, now=5.0), 4) == 0.3998
    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.482
    assert round(registry.total_for("crit_rate", ALLY, now=5.0), 4) == 0.8519
    assert registry.total_for("attack_damage_up", ALLY, now=15.1) == 0.0  # 10s hardcoded duration


def test_heat_emission_only_triggers_if_grave_burst_this_cycle():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_end", {"grave": build()}, ctx, registry, time=15.0)
    assert registry.total_for("pierce_damage_up", ALLY, now=15.0) == 0.0

    ctx.burst_used_this_cycle.add("grave")
    registry2 = EffectRegistry()
    fire_trigger("full_burst_end", {"grave": build()}, ctx, registry2, time=15.0)
    assert round(registry2.total_for("pierce_damage_up", ALLY, now=15.0), 4) == 0.484


def test_heat_emission_applies_only_once_while_still_active():
    # If full_burst_end fires again while Heat Emission is already active
    # (e.g. she didn't reburst that cycle but the condition still holds from a
    # stale flag in a hand-built test), it must not double up.
    ctx = make_context()
    ctx.burst_used_this_cycle.add("grave")
    registry = EffectRegistry()
    rules = {"grave": build()}

    fire_trigger("full_burst_end", rules, ctx, registry, time=15.0)
    fire_trigger("full_burst_end", rules, ctx, registry, time=45.0)

    # should NOT double up - still just 48.4%, not 96.8%
    assert round(registry.total_for("pierce_damage_up", ALLY, now=45.0), 4) == 0.484


def test_heat_emission_is_removed_when_grave_bursts_again():
    # Per Fienn: Heat Emission's "removed under certain conditions" means it's
    # removed exactly when Grave uses her burst again - it's a toggle, off
    # during each ~10s Prediction window right after she bursts, on otherwise.
    ctx = make_context()
    ctx.burst_used_this_cycle.add("grave")
    registry = EffectRegistry()

    fire_trigger("full_burst_end", {"grave": build()}, ctx, registry, time=15.0)  # Heat Emission activates
    assert round(registry.total_for("pierce_damage_up", ALLY, now=39.9), 4) == 0.484

    # Isolate the removal rule (build()[1]) so Plot Spoiler's own reburst buff
    # (a separate, temporary squad Pierce Damage grant) doesn't mask whether
    # Heat Emission specifically was closed out.
    removal_only = {"grave": [build()[1]]}
    fire_trigger("own_burst_activate", removal_only, ctx, registry, time=40.0)
    assert registry.total_for("pierce_damage_up", ALLY, now=40.0) == 0.0
    assert registry.total_for("pierce_damage_up", ALLY, now=100.0) == 0.0


def test_heat_emission_reactivates_after_the_next_full_burst_end():
    ctx = make_context()
    ctx.burst_used_this_cycle.add("grave")
    registry = EffectRegistry()
    rules = {"grave": build()}

    fire_trigger("full_burst_end", rules, ctx, registry, time=15.0)   # cycle 1: activates
    fire_trigger("own_burst_activate", rules, ctx, registry, time=40.0)  # cycle 2 burst: removed
    fire_trigger("full_burst_end", rules, ctx, registry, time=50.0)   # cycle 2 ends: reactivates

    assert round(registry.total_for("pierce_damage_up", ALLY, now=175.0), 4) == 0.484
