from app.effects import EffectRegistry
from app.skill_rules.grave import (
    PREDICTION_DURATION,
    build_grave_rules,
    build_overheat_per_shot_rules,
)
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
OVERHEAT = {
    "description_value_01": "15",     # Overheat I threshold (normals from battle start)
    "description_value_02": "15.48",  # Overheat I self ATK % (permanent once unlocked)
    "description_value_03": "30",     # Overheat II threshold (normals in Prediction)
    "description_value_04": "20.66",  # Overheat II self ATK %
    "description_value_05": "60",     # Overheat III threshold
    "description_value_06": "30.8",   # Overheat III self Attack Damage %
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


def test_overheat_per_shot_rules_structure():
    rules = build_overheat_per_shot_rules({"overheat": OVERHEAT})
    assert len(rules) == 3
    (t1, m1, _), (t2, m2, _), (t3, m3, _) = rules
    assert (t1, m1) == (15, "after")  # Overheat I: 15th normal from battle start
    assert (t2, m2) == ((30, PREDICTION_DURATION), "every_during_own_status_window")
    assert (t3, m3) == ((60, PREDICTION_DURATION), "every_during_own_status_window")


def test_overheat_i_grants_permanent_self_atk_once():
    _, _, oh1 = build_overheat_per_shot_rules({"overheat": OVERHEAT})[0]
    ctx = make_context()
    registry = EffectRegistry()
    oh1[0].action(ctx, "grave", 2.0, registry)
    assert round(registry.total_for("atk_percent", GRAVE, now=2.0), 4) == 0.1548
    assert round(registry.total_for("atk_percent", GRAVE, now=175.0), 4) == 0.1548  # permanent
    # firing again (e.g. via replay) must not stack
    oh1[0].action(ctx, "grave", 50.0, registry)
    assert round(registry.total_for("atk_percent", GRAVE, now=50.0), 4) == 0.1548
    assert registry.total_for("atk_percent", ALLY, now=50.0) == 0.0  # self-scoped


def _prediction_ctx(burst_time):
    ctx = make_context()
    ctx.burst_times["grave"] = [burst_time]
    ctx.set_status("grave", "overheat_i")  # Overheat I is the II/III prerequisite
    return ctx


def test_overheat_ii_is_active_only_within_prediction_window():
    _, _, oh2 = build_overheat_per_shot_rules({"overheat": OVERHEAT})[1]
    ctx = _prediction_ctx(burst_time=5.0)  # Prediction window [5.0, 15.0)
    registry = EffectRegistry()
    oh2[0].action(ctx, "grave", 7.5, registry)  # 30th hit lands 2.5s into the window

    assert round(registry.total_for("atk_percent", GRAVE, now=7.5), 4) == 0.2066
    assert round(registry.total_for("atk_percent", GRAVE, now=14.9), 4) == 0.2066  # still in window
    assert registry.total_for("atk_percent", GRAVE, now=15.0) == 0.0  # fades at Prediction end
    assert registry.total_for("atk_percent", ALLY, now=7.5) == 0.0  # self-scoped


def test_overheat_ii_requires_overheat_i():
    _, _, oh2 = build_overheat_per_shot_rules({"overheat": OVERHEAT})[1]
    ctx = make_context()
    ctx.burst_times["grave"] = [5.0]  # in a Prediction window but no Overheat I yet
    registry = EffectRegistry()
    oh2[0].action(ctx, "grave", 7.5, registry)
    assert registry.total_for("atk_percent", GRAVE, now=7.5) == 0.0


def test_overheat_ii_re_earns_each_prediction_window():
    _, _, oh2 = build_overheat_per_shot_rules({"overheat": OVERHEAT})[1]
    ctx = make_context()
    ctx.set_status("grave", "overheat_i")
    ctx.burst_times["grave"] = [5.0, 45.0]  # two Prediction windows
    registry = EffectRegistry()
    oh2[0].action(ctx, "grave", 7.5, registry)   # window 1
    oh2[0].action(ctx, "grave", 47.5, registry)  # window 2

    assert round(registry.total_for("atk_percent", GRAVE, now=14.9), 4) == 0.2066  # window 1
    assert registry.total_for("atk_percent", GRAVE, now=20.0) == 0.0              # gap between windows
    assert round(registry.total_for("atk_percent", GRAVE, now=54.9), 4) == 0.2066  # window 2
    assert registry.total_for("atk_percent", GRAVE, now=55.0) == 0.0


def test_overheat_ii_leaves_overheat_i_standing():
    """Overheat I's permanent self ATK and Overheat II's windowed self ATK are
    different skill bullets, so II must add on top of I rather than replace it.
    They share (stat, scope, source), which is all `add_refreshing` matched on
    before refresh groups covered hand-written rules."""
    rules = build_overheat_per_shot_rules({"overheat": OVERHEAT})
    oh1 = rules[0][2][0]
    oh2 = rules[1][2][0]
    ctx = make_context()
    ctx.burst_times["grave"] = [5.0]  # Prediction window [5.0, 15.0)
    registry = EffectRegistry()

    oh1.action(ctx, "grave", 2.0, registry)   # 15th normal -> Overheat I, permanent
    oh2.action(ctx, "grave", 7.5, registry)   # 30th in-window hit -> Overheat II

    assert round(registry.total_for("atk_percent", GRAVE, now=7.5), 4) == 0.3614   # 0.1548 + 0.2066
    assert round(registry.total_for("atk_percent", GRAVE, now=14.9), 4) == 0.3614
    assert round(registry.total_for("atk_percent", GRAVE, now=15.0), 4) == 0.1548  # only I survives


def test_overheat_iii_requires_overheat_ii_then_bounded_to_prediction():
    rules = build_overheat_per_shot_rules({"overheat": OVERHEAT})
    oh2 = rules[1][2][0]
    oh3 = rules[2][2][0]
    ctx = _prediction_ctx(burst_time=5.0)  # window [5.0, 15.0)
    registry = EffectRegistry()

    # Overheat III does nothing until Overheat II has been reached.
    oh3.action(ctx, "grave", 8.0, registry)
    assert registry.total_for("attack_damage_up", GRAVE, now=8.0) == 0.0

    oh2.action(ctx, "grave", 7.5, registry)   # 30th hit -> Overheat II reached
    oh3.action(ctx, "grave", 10.0, registry)  # 60th hit -> Overheat III
    assert round(registry.total_for("attack_damage_up", GRAVE, now=10.0), 4) == 0.308
    assert round(registry.total_for("attack_damage_up", GRAVE, now=14.9), 4) == 0.308  # in window
    assert registry.total_for("attack_damage_up", GRAVE, now=15.0) == 0.0  # fades at Prediction end
