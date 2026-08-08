"""Emma: Tactical Upgrade - a Burst-1 Fire MG supporter whose Environment Setup
runs on a recurring interval her partner shortens from 30 sec to 10."""
from app.effects import EffectRegistry
from app.skill_rules.emma_tactical_upgrade import (
    ENVIRONMENT_SETUP_PAIRED_INTERVAL,
    ENVIRONMENT_SETUP_SOLO_INTERVAL,
    build_emma_tactical_upgrade_rules,
    build_environment_setup_periodic_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/emma-tactical-upgrade.json, level 10).
ENVIRONMENT_SETUP = {
    "description_value_01": "3.9", "description_value_02": "10",
    "description_value_03": "2.32", "description_value_04": "10",
    "description_value_05": "30",
}
LT_FORMATION = {
    "description_value_01": "23.51", "description_value_02": "2.32",
    "description_value_03": "30.97", "description_value_04": "3.09",
    "description_value_05": "20",
}
BATTLEFIELD_FORMATION = {
    "description_value_01": "40.07", "description_value_02": "10",
    "description_value_03": "29.04",
}
CASTER_ATK = 60000.0
EMMA = {
    "environment_setup": ENVIRONMENT_SETUP,
    "lt_formation": LT_FORMATION,
    "battlefield_formation": BATTLEFIELD_FORMATION,
    "caster_atk": CASTER_ATK,
}

SELF = {"slug": "emma-tactical-upgrade", "element": "Fire"}
EUNHWA = {"slug": "eunhwa-tactical-upgrade", "element": "Fire"}
OUTSIDER = {"slug": "outsider", "element": "Water"}


def _ctx(with_eunhwa=False):
    members = [
        SquadMember("emma-tactical-upgrade", burst_tier=1, element="Fire", weapon="MG"),
        SquadMember("outsider", burst_tier=3, element="Water", weapon="AR"),
    ]
    if with_eunhwa:
        members.append(
            SquadMember("eunhwa-tactical-upgrade", burst_tier=2, element="Fire", weapon="SR"))
    return SquadContext(members)


def test_environment_setup_debuffs_the_enemy_from_battle_start():
    """"Activates at the start of battle" - so unlike a plain cooldowned skill
    it DOES fire at t=0, and the recurring interval takes over from there."""
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(), reg, 0.0,
    )
    assert round(reg.total_for("damage_taken_up", OUTSIDER, 0.0), 4) == 0.039
    assert round(reg.total_for("damage_taken_up", OUTSIDER, 9.9), 4) == 0.039
    assert reg.total_for("damage_taken_up", OUTSIDER, 10.1) == 0.0  # 10 of every 30 sec


def test_the_recurring_interval_shortens_from_thirty_to_ten_beside_eunhwa():
    assert ENVIRONMENT_SETUP_SOLO_INTERVAL == 30.0
    assert ENVIRONMENT_SETUP_PAIRED_INTERVAL == 10.0

    entries = build_environment_setup_periodic_rules(EMMA)
    assert sorted(interval for interval, _rules in entries) == [10.0, 30.0]
    by_interval = dict(entries)

    # Solo: only the 30-sec entry may fire.
    reg = EffectRegistry()
    solo = _ctx(with_eunhwa=False)
    fire_trigger("periodic", {"emma-tactical-upgrade": by_interval[30.0]}, solo, reg, 30.0)
    assert round(reg.total_for("damage_taken_up", OUTSIDER, 30.0), 4) == 0.039
    reg = EffectRegistry()
    fire_trigger("periodic", {"emma-tactical-upgrade": by_interval[10.0]}, solo, reg, 10.0)
    assert reg.total_for("damage_taken_up", OUTSIDER, 10.0) == 0.0

    # Paired: only the 10-sec entry may fire, and a 10-sec effect on a 10-sec
    # interval is continuous uptime.
    reg = EffectRegistry()
    paired = _ctx(with_eunhwa=True)
    fire_trigger("periodic", {"emma-tactical-upgrade": by_interval[10.0]}, paired, reg, 10.0)
    assert round(reg.total_for("damage_taken_up", OUTSIDER, 10.0), 4) == 0.039
    reg = EffectRegistry()
    fire_trigger("periodic", {"emma-tactical-upgrade": by_interval[30.0]}, paired, reg, 30.0)
    assert reg.total_for("damage_taken_up", OUTSIDER, 30.0) == 0.0


def test_the_same_squad_crit_damage_reaches_only_absolute_squad_members():
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(with_eunhwa=True), reg, 0.0,
    )
    assert round(reg.total_for("other_critical_damage_sources", SELF, 0.0), 4) == 0.2351
    assert round(reg.total_for("other_critical_damage_sources", EUNHWA, 0.0), 4) == 0.2351
    assert reg.total_for("other_critical_damage_sources", OUTSIDER, 0.0) == 0.0


def test_lt_formations_projectile_explosion_is_squad_wide_and_permanent():
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(), reg, 0.0,
    )
    assert round(reg.total_for("projectile_explosion_damage_up", OUTSIDER, 179.0), 4) == 0.0232


def test_the_as_formation_bonus_needs_eunhwa_in_the_deck():
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(with_eunhwa=False), reg, 0.0,
    )
    assert reg.total_for("true_damage_up", OUTSIDER, 0.0) == 0.0
    assert round(reg.total_for("projectile_explosion_damage_up", OUTSIDER, 0.0), 4) == 0.0232

    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(with_eunhwa=True), reg, 0.0,
    )
    assert round(reg.total_for("true_damage_up", OUTSIDER, 0.0), 4) == 0.3097
    # Both Projectile Explosion bullets are live and they add: 2.32% + 3.09%.
    assert round(reg.total_for("projectile_explosion_damage_up", OUTSIDER, 0.0), 4) == 0.0541


def test_her_burst_grants_a_squad_flat_atk_off_her_own_atk():
    reg = EffectRegistry()
    fire_trigger(
        "own_burst_activate", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(), reg, 5.0,
    )
    assert reg.total_for("flat_atk", OUTSIDER, 5.0) == 0.4007 * CASTER_ATK
    assert reg.total_for("flat_atk", OUTSIDER, 15.1) == 0.0  # 10 sec


def _enhanced_at(burst_time, with_eunhwa):
    """The extra Damage Taken her burst adds when it lands in an Environment
    Setup window, as seen right at the burst."""
    reg = EffectRegistry()
    fire_trigger(
        "own_burst_activate", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(with_eunhwa=with_eunhwa), reg, burst_time,
    )
    return round(reg.total_for("damage_taken_up", OUTSIDER, burst_time), 4)


def test_enhanced_environment_setup_follows_the_windows_own_clock_when_solo():
    """Its gate is "while in Environment Setup status", and that status runs on
    a FIXED timer - 10 sec out of every 30, from t=0 - which is decided by the
    clock alone, not by the deck. So a burst inside a window doubles the debuff
    and one outside does not; `time_condition` gets the trigger's own time and
    can answer this exactly."""
    assert _enhanced_at(5.0, with_eunhwa=False) == 0.039     # inside [0, 10)
    assert _enhanced_at(9.9, with_eunhwa=False) == 0.039
    assert _enhanced_at(10.1, with_eunhwa=False) == 0.0      # window lapsed
    assert _enhanced_at(29.9, with_eunhwa=False) == 0.0
    assert _enhanced_at(30.0, with_eunhwa=False) == 0.039    # next window opens
    assert _enhanced_at(63.0, with_eunhwa=False) == 0.039    # [60, 70)


def test_enhanced_environment_setup_is_always_up_when_paired():
    """Beside Eunhwa the interval shortens to 10 sec against a 10-sec status,
    so there is no gap for a burst to fall into."""
    for burst_time in (5.0, 10.1, 29.9, 47.3, 155.0):
        assert _enhanced_at(burst_time, with_eunhwa=True) == 0.039


def test_the_enhanced_debuff_expires_with_the_window_it_doubles():
    reg = EffectRegistry()
    fire_trigger(
        "own_burst_activate", {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)},
        _ctx(with_eunhwa=True), reg, 5.0,
    )
    # "scaled by 100%" doubles the 3.9%, i.e. adds another 3.9% for 10 sec.
    assert round(reg.total_for("damage_taken_up", OUTSIDER, 14.9), 4) == 0.039
    assert reg.total_for("damage_taken_up", OUTSIDER, 15.1) == 0.0


def test_the_heal_and_the_taunt_register_nothing():
    reg = EffectRegistry()
    ctx = _ctx(with_eunhwa=True)
    rules = {"emma-tactical-upgrade": build_emma_tactical_upgrade_rules(EMMA)}
    for trigger in ("battle_start", "own_burst_activate", "full_burst_enter"):
        fire_trigger(trigger, rules, ctx, reg, 5.0)
    assert reg.total_for("flat_max_hp", SELF, 5.0) == 0.0
    assert reg.total_for("incoming_healing", SELF, 5.0) == 0.0
