from app.effects import EffectRegistry
from app.skill_rules.helm import (
    aegis_cannon_burst_percent,
    build_fire_away_rules,
    build_frontline_command_per_shot_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Helm has her signature weapon ("dollskills" in api.dotgg.gg) completed, so
# these are the dollskills level-10 values, not the base skills - Fienn
# confirmed the cherished-weapon version applies. It changes more than just
# numbers: Fire Away's full-burst Attack Damage bonus is 27.87% here vs
# 11.85% on the base (non-cherished) skill.
FRONTLINE_COMMAND_VALUES = {
    "description_value_01": "14.64",
    "description_value_02": "5",
}

FIRE_AWAY_VALUES = {
    "description_value_01": "3.08",
    "description_value_02": "27.87",
    "description_value_03": "10",
}

AEGIS_CANNON_VALUES = {
    "description_value_01": "8236.8",
    "description_value_02": "54.45",
    "description_value_03": "10",
    "description_value_04": "158.4",
    "description_value_05": "10",
}


def make_context():
    return SquadContext(
        [
            SquadMember("helm", burst_tier=3, element="Water"),
            SquadMember("ally", burst_tier=1, element="Iron"),
        ]
    )


def test_frontline_command_grants_squad_crit_rate_on_last_bullet_hit():
    ps = build_frontline_command_per_shot_rules(FRONTLINE_COMMAND_VALUES)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (None, "last_bullet")
    ctx = make_context()
    registry = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "helm", 3.0, registry)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("crit_rate", ally, now=3.0), 4) == 0.1464
    assert registry.total_for("crit_rate", ally, now=8.1) == 0.0


def test_frontline_command_refreshes_instead_of_stacking_on_repeated_last_bullets():
    # A charge weapon's small magazine can empty faster than the 5s buff
    # window, so repeated last-bullet hits must REFRESH (one active value),
    # not stack (see the "per-shot buff refresh" precedent, Prika/Mint).
    ps = build_frontline_command_per_shot_rules(FRONTLINE_COMMAND_VALUES)
    _, _, rules = ps[0]
    ctx = make_context()
    registry = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "helm", 3.0, registry)
        rule.action(ctx, "helm", 4.0, registry)  # 2nd last bullet before the 1st buff expires

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("crit_rate", ally, now=4.0), 4) == 0.1464  # not 0.2928


def test_fire_away_grants_permanent_squad_damage_to_parts():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"helm": build_fire_away_rules(FIRE_AWAY_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("damage_to_parts_up", ally, now=99999), 4) == 0.0308


def test_fire_away_grants_squad_attack_damage_up_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"helm": build_fire_away_rules(FIRE_AWAY_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.2787
    assert registry.total_for("attack_damage_up", ally, now=15.1) == 0.0


def test_aegis_cannon_burst_percent_reads_the_damage_slot():
    assert aegis_cannon_burst_percent(AEGIS_CANNON_VALUES) == 8236.8
