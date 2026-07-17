"""SkillRule encoding of Helm's "Frontline Command" (skills[0]) and "Fire
Away" (skills[1]) from api.dotgg.gg slug "helm".

Fienn's Helm has her signature weapon completed, so callers must build these
rules from the "dollskills" array's values, not "skills" - the cherished-
weapon version changes more than numbers (e.g. Frontline Command gains an
entirely new full-charge-hit effect) even where a stat's own value carries
over unchanged (e.g. the crit rate on Frontline Command is the same in both).

"Aegis Cannon" (skills[2]/dollskills[2], her burst skill) is mostly a pure
damage instance - use aegis_cannon_burst_percent() for the "X% of final ATK"
figure raid_simulator needs; the damage-proportional heal-over-time isn't
modeled since it doesn't affect DPS output.

"Frontline Command" fires "when the last bullet hits the target" - modeled
via `per_shot_rules`' `"last_bullet"` mode (gap #1's residual variant, built
2026-07-12) as a REFRESHING squad Crit Rate buff (SR's small magazine can
empty faster than the buff's own 5s window, so repeated last-bullet hits
must refresh, not stack - see the Prika/Mint per-shot-refresh precedent).

Not modeled / deferred: both skills' "on Full Charge attack" bonus effects
(Frontline Command's Max-HP recovery + Burst Gauge fill; Fire Away's 178.98%
additional-damage hit) - a DIFFERENT trigger from last-bullet (every shot on
a charge weapon is a full charge, so this is really `per_shot_rules`' plain
"every 1" mode, not gated on the gap #1 fix - just not built in this pass).
Aegis Cannon's post-burst Charge Damage Multiplier (+158.4% for 10 rounds)
is also deferred (a "for N round(s)" bullet-count buff on herself).
"""
from app.effects import Effect
from app.skill_rules._helpers import refreshing_buff_rule
from app.squad_engine import SkillRule

# Fienn's Helm has the signature weapon completed, so the manifest reads the
# "dollskills" array, not "skills" (see module docstring).
SKILL_VALUE_MANIFESTS = {
    "helm": {
        "source": "dotgg",
        "test_module": "test_skill_rules_helm",
        "keys": {
            "frontline_command": ("dollskills", 0),
            "fire_away": ("dollskills", 1),
            "aegis_cannon": ("dollskills", 2),
        },
        "fixtures": {
            "frontline_command": "FRONTLINE_COMMAND_VALUES",
            "fire_away": "FIRE_AWAY_VALUES",
            "aegis_cannon": "AEGIS_CANNON_VALUES",
        },
    },
}


def build_frontline_command_per_shot_rules(values: dict) -> list:
    crit_rate_up = float(values["description_value_01"]) / 100
    duration = float(values["description_value_02"])
    return [(None, "last_bullet", [
        refreshing_buff_rule("per_shot", [("crit_rate", crit_rate_up, "squad", duration)])
    ])]


def build_fire_away_rules(values: dict) -> list[SkillRule]:
    damage_to_parts_up = float(values["description_value_01"]) / 100
    attack_damage_up = float(values["description_value_02"]) / 100
    attack_damage_duration = float(values["description_value_03"])

    def grant_damage_to_parts(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "Fire Away Granted"):
            return
        context.set_status(caster_slug, "Fire Away Granted")
        registry.add(
            Effect("damage_to_parts_up", damage_to_parts_up, "squad", None, caster_slug),
            applied_at=time,
        )

    def grant_attack_damage_up(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", attack_damage_up, "squad", attack_damage_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="battle_start", action=grant_damage_to_parts),
        SkillRule(trigger="full_burst_enter", action=grant_attack_damage_up),
    ]


def aegis_cannon_burst_percent(values: dict) -> float:
    return float(values["description_value_01"])
