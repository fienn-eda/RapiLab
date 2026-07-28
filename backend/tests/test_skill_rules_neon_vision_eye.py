from app.effects import EffectRegistry
from app.skill_rules.neon_vision_eye import (
    SUPER_FIREPOWER_BURST_PERIOD,
    build_firepower_explosion_per_shot_rules,
    build_neon_vision_eye_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (values rendered inline;
# slots numbered by left-to-right appearance).
HEALTHY_BODY = {
    "description_value_01": "3",       # deferred: invulnerable duration
    "description_value_02": "5",       # deferred: activations per battle
    "description_value_03": "3",       # deferred: debuff immunity duration (count is "∞", not a token)
    "description_value_04": "5",       # deferred: its activations per battle
    "description_value_05": "10.26",   # deferred: Healthy Body incoming healing %
    "description_value_06": "20",      # deferred: its duration
    "description_value_07": "437.98",  # Firepower Explosion base % (every full charge)
    "description_value_08": "262.79",  # Super Firepower additional explosion %
}
FIREPOWER_CHARGE = {
    "description_value_01": "100",     # battle-start gauge (not modeled as resource)
    "description_value_02": "2",       # gauge per normal (not modeled)
    "description_value_03": "45",      # gauge on Firepower Charge end (not modeled)
    "description_value_04": "5",       # deferred: burst gauge fill speed %
    "description_value_05": "5",       # deferred: its duration
    "description_value_06": "80.04",   # Maximum Firepower self ATK %
    "description_value_07": "10",      # its duration
    "description_value_08": "35.05",   # Super Firepower additional self ATK %
    "description_value_09": "10",      # its duration
}
SUPER_FIREPOWER = {
    "description_value_01": "10",      # deferred: recharge duration (gauge < 100 branch)
    "description_value_02": "1",       # deferred: recharge per tick
    "description_value_03": "45.03",   # Super Firepower self Attack Damage %
    "description_value_04": "10",      # its duration
    "description_value_05": "100",     # gauge consumed (not modeled)
    "description_value_06": "200",     # deferred: Explosion Radius %
    "description_value_07": "10",      # its duration
    "description_value_08": "110.21",  # general burst self Attack Damage %
    "description_value_09": "10",      # its duration
}

SUPER_FIREPOWER_WINDOW = 10.0


def make_context():
    return SquadContext([
        SquadMember("neon-vision-eye", burst_tier=3, element="Electric"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def build():
    return build_neon_vision_eye_rules({
        "firepower_charge": FIREPOWER_CHARGE,
        "super_firepower": SUPER_FIREPOWER,
    })


NEON = {"slug": "neon-vision-eye", "element": "Electric"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_no_burst_nuke():
    _, burst_percent = (build(), None)
    assert burst_percent is None  # burst is buff-only; damage is Firepower Explosion


def test_maximum_firepower_self_atk_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"neon-vision-eye": build()}, ctx, registry, time=5.0)

    # Maximum Firepower base 80.04%, on EVERY Full Burst - the skill says
    # "when entering Full Burst", so it lands on cycles another Burst 3 opened
    # too. The Super Firepower additional 35.05% is not here: it needs the
    # status, which only her own gauge-100 burst grants.
    assert round(registry.total_for("atk_percent", NEON, now=5.0), 4) == 0.8004
    assert registry.total_for("atk_percent", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("atk_percent", NEON, now=15.1) == 0.0  # 10s


def _burst(n_times, registry, ctx, rules):
    """Fire her own burst `n_times`, returning the time of the last one."""
    time = 0.0
    for _ in range(n_times):
        time += 20.0
        fire_trigger("own_burst_activate", {"neon-vision-eye": rules}, ctx, registry, time=time)
    return time


def test_the_first_burst_is_a_super_firepower_burst():
    # She enters the fight with the gauge already at 100.
    ctx, registry = make_context(), EffectRegistry()
    time = _burst(1, registry, ctx, build())

    # Super Firepower 45.03% + general burst 110.21% = 155.24%
    assert round(registry.total_for("attack_damage_up", NEON, now=time), 4) == 1.5524
    assert registry.total_for("attack_damage_up", ALLY, now=time) == 0.0  # self-only
    assert registry.total_for("attack_damage_up", NEON, now=time + 10.1) == 0.0


def test_the_two_bursts_after_a_super_firepower_burst_only_recharge():
    # Super Firepower drains the gauge to 0, and refilling it (+2 per normal,
    # +45 when Firepower Charge ends) takes two more bursts - so bursts 2 and 3
    # get the general 110.21% only, with no 45.03% on top.
    for burst_number in (2, 3):
        ctx, registry = make_context(), EffectRegistry()
        time = _burst(burst_number, registry, ctx, build())

        assert round(registry.total_for("attack_damage_up", NEON, now=time), 4) == 1.1021


def test_super_firepower_returns_on_the_fourth_burst():
    ctx, registry = make_context(), EffectRegistry()
    time = _burst(4, registry, ctx, build())

    assert round(registry.total_for("attack_damage_up", NEON, now=time), 4) == 1.5524


def test_maximum_firepowers_additional_atk_rides_the_super_firepower_burst():
    # The additional 35.05% needs Super Firepower status. She is Burst 3, so
    # her own burst and the Full Burst it opens are the same instant - the only
    # Full Burst inside her 10s status window is the one she opened herself.
    ctx, registry = make_context(), EffectRegistry()
    time = _burst(1, registry, ctx, build())

    assert round(registry.total_for("atk_percent", NEON, now=time), 4) == 0.3505

    ctx, registry = make_context(), EffectRegistry()
    time = _burst(2, registry, ctx, build())

    assert registry.total_for("atk_percent", NEON, now=time) == 0.0


def test_firepower_explosion_base_and_super_bonus():
    rules = build_firepower_explosion_per_shot_rules({"healthy_body": HEALTHY_BODY})
    assert len(rules) == 2
    (t1, m1, base_rules), (t2, m2, super_rules) = rules
    assert (t1, m1) == (1, "every")  # base: every full charge
    # The bonus window opens on every 3rd of her bursts, not on all of them.
    assert (t2, m2) == ((1, SUPER_FIREPOWER_WINDOW, SUPER_FIREPOWER_BURST_PERIOD),
                        "every_during_own_status_window")

    registry = EffectRegistry()
    base_rules[0].action(make_context(), "neon-vision-eye", 5.0, registry)
    super_rules[0].action(make_context(), "neon-vision-eye", 5.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    values = sorted(p.value for p in pulses)
    assert values == [262.79, 437.98]
    # A Rocket Launcher's explosion: reads projectile_explosion_damage_up.
    assert all(p.damage_type == "projectile_explosion" for p in pulses)
