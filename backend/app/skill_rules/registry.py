"""Maps each encoded Nikke slug to a builder that turns its skill values into
(combat SkillRules, burst-nuke percent).

The roster/assembly layer and deck search use this so they never hardcode
which build_* functions a given slug needs. burst_percent is None for Nikkes
whose burst skill is buffs-only (no "X% of ATK" nuke), e.g. Crown/Anis: Star.

Each builder takes a `skill_values` dict keyed by that Nikke's sub-skill names
(plus caster base stats where a skill scales off them, e.g. Crown).
"""
from app.skill_rules.anis_star import build_starfall_rules
from app.skill_rules.crown import build_last_kingdom_rules, build_one_for_all_rules
from app.skill_rules.helm import (
    aegis_cannon_burst_percent,
    build_fire_away_rules,
    build_frontline_command_rules,
)
from app.skill_rules.privaty import (
    ak_missile_burst_percent,
    build_ak_missile_rules,
    build_ex_magazine_rules,
)
from app.skill_rules.rapi_red_hood import (
    build_battlefield_assessment_rules,
    power_of_inheritance_stage3_burst_percent,
)


def _build_anis_star(sv):
    return build_starfall_rules(sv["starfall"]), None


def _build_crown(sv):
    rules = build_one_for_all_rules(sv["one_for_all"], sv["caster_atk"], sv["caster_def"])
    rules += build_last_kingdom_rules(sv["last_kingdom"], sv["caster_max_hp"])
    return rules, None


def _build_rapi_red_hood(sv):
    rules = build_battlefield_assessment_rules(sv["battlefield_assessment"])
    burst_percent = power_of_inheritance_stage3_burst_percent(sv["power_of_inheritance"])
    return rules, burst_percent


def _build_helm(sv):
    rules = build_frontline_command_rules(sv["frontline_command"])
    rules += build_fire_away_rules(sv["fire_away"])
    return rules, aegis_cannon_burst_percent(sv["aegis_cannon"])


def _build_privaty(sv):
    rules = build_ex_magazine_rules(sv["ex_magazine"])
    rules += build_ak_missile_rules(sv["ak_missile"])
    return rules, ak_missile_burst_percent(sv["ak_missile"])


_BUILDERS = {
    "anis-star": _build_anis_star,
    "crown": _build_crown,
    "rapi-red-hood": _build_rapi_red_hood,
    "helm": _build_helm,
    "privaty": _build_privaty,
}

ENCODED_SLUGS = tuple(_BUILDERS)


def build_nikke_rules(slug, skill_values):
    if slug not in _BUILDERS:
        raise KeyError(f"no encoded skill rules for slug: {slug!r}")
    return _BUILDERS[slug](skill_values)
