"""Maps each encoded Nikke slug to a builder that turns its skill values into
(combat SkillRules, burst-nuke percent).

The roster/assembly layer and deck search use this so they never hardcode
which build_* functions a given slug needs. burst_percent is None for Nikkes
whose burst skill is buffs-only (no "X% of ATK" nuke), e.g. Crown/Anis: Star.

Each builder takes a `skill_values` dict keyed by that Nikke's sub-skill names
(plus caster base stats where a skill scales off them, e.g. Crown).

A separate, much smaller `_PERIODIC_NUKE_BUILDERS` map covers the rare Nikke
with a skill that fires repeatedly on its own fixed cooldown, independent of
the burst cycle (e.g. Helm: Aquamarine's Aegis Cannon Suppression Fire) - see
`get_periodic_nuke` and `raid_simulator`'s `periodic_nukes` parameter. Kept
separate from `_BUILDERS` so the ~25 existing builders' 2-tuple return shape
never has to change for the one or two Nikkes that need this.
"""
from app.skill_rules.ade_agent_bunny import build_ade_rules
from app.skill_rules.anchor_innocent_maid import build_anchor_rules
from app.skill_rules.anis_sparkling_summer import build_anis_sparkling_summer_rules
from app.skill_rules.anis_star import build_starfall_rules
from app.skill_rules.arcana import arcana_burst_percent, build_arcana_rules
from app.skill_rules.arcana_fortune_mate import build_fortune_mate_rules, radiant_youth_burst_percent
from app.skill_rules.blanc import build_blanc_rules
from app.skill_rules.brid_silent_track import build_brid_rules
from app.skill_rules.crown import build_last_kingdom_rules, build_one_for_all_rules
from app.skill_rules.d_killer_wife import build_d_killer_wife_rules, kill_the_target_burst_percent
from app.skill_rules.grave import build_grave_rules
from app.skill_rules.helm import (
    aegis_cannon_burst_percent,
    build_fire_away_rules,
    build_frontline_command_rules,
)
from app.skill_rules.helm_aquamarine import (
    AEGIS_CANNON_SUPPRESSION_FIRE_COOLDOWN,
    aegis_cannon_overload_burst_percent,
    aegis_cannon_suppression_fire_percent,
    build_helm_aquamarine_rules,
)
from app.skill_rules.little_mermaid import build_little_mermaid_rules
from app.skill_rules.liter import build_liter_rules
from app.skill_rules.mast_romantic_maid import build_mast_rules
from app.skill_rules.mint import build_mint_rules
from app.skill_rules.miranda import build_miranda_rules
from app.skill_rules.moran import build_moran_rules
from app.skill_rules.nayuta import asceticism_burst_percent, build_nayuta_rules
from app.skill_rules.prika import build_prika_rules
from app.skill_rules.rouge import build_rouge_rules
from app.skill_rules.soline_frost_ticket import build_soline_frost_ticket_rules
from app.skill_rules.tove import build_tove_rules
from app.skill_rules.velvet import build_velvet_rules
from app.skill_rules.privaty import (
    ak_missile_burst_percent,
    build_ak_missile_rules,
    build_ex_magazine_rules,
)
from app.skill_rules.rapi_red_hood import (
    build_battlefield_assessment_rules,
    power_of_inheritance_stage3_burst_percent,
)
from app.skill_rules.volume import build_volume_rules
from app.skill_rules.zwei import build_zwei_rules


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
    "anis-sparkling-summer": lambda sv: (build_anis_sparkling_summer_rules(sv), None),
    "ade-agent-bunny": lambda sv: (build_ade_rules(sv), None),
    "anchor-innocent-maid": lambda sv: (build_anchor_rules(sv), None),
    "arcana": lambda sv: (build_arcana_rules(sv), arcana_burst_percent(sv)),
    "arcana-fortune-mate": lambda sv: (build_fortune_mate_rules(sv), radiant_youth_burst_percent(sv)),
    "blanc": lambda sv: (build_blanc_rules(sv), None),
    "brid-silent-track": lambda sv: (build_brid_rules(sv), None),
    "crown": _build_crown,
    "rapi-red-hood": _build_rapi_red_hood,
    "helm": _build_helm,
    "helm-aquamarine": lambda sv: (build_helm_aquamarine_rules(sv), aegis_cannon_overload_burst_percent(sv)),
    "privaty": _build_privaty,
    "liter": lambda sv: (build_liter_rules(sv), None),
    "volume": lambda sv: (build_volume_rules(sv), None),
    "miranda": lambda sv: (build_miranda_rules(sv), None),
    "rouge": lambda sv: (build_rouge_rules(sv), None),
    "zwei": lambda sv: (build_zwei_rules(sv), None),
    "d-killer-wife": lambda sv: (build_d_killer_wife_rules(sv), kill_the_target_burst_percent(sv)),
    "grave": lambda sv: (build_grave_rules(sv), None),
    "little-mermaid": lambda sv: (build_little_mermaid_rules(sv), None),
    "mast-romantic-maid": lambda sv: (build_mast_rules(sv), None),
    "mint": lambda sv: (build_mint_rules(sv), None),
    "moran": lambda sv: (build_moran_rules(sv), None),
    "nayuta": lambda sv: (build_nayuta_rules(sv), asceticism_burst_percent(sv)),
    "prika": lambda sv: (build_prika_rules(sv), None),
    "tove": lambda sv: (build_tove_rules(sv), None),
    "soline-frost-ticket": lambda sv: (build_soline_frost_ticket_rules(sv), None),
    "velvet": lambda sv: (build_velvet_rules(sv), None),
}

ENCODED_SLUGS = tuple(_BUILDERS)

_PERIODIC_NUKE_BUILDERS = {
    "helm-aquamarine": lambda sv: {
        "cooldown": AEGIS_CANNON_SUPPRESSION_FIRE_COOLDOWN,
        "percent": aegis_cannon_suppression_fire_percent(sv),
    },
}

# A Nikke's burst nuke is "attack"-typed unless its skill deals a specific
# damage type (e.g. a "Projectile Explosion" keyword skill). Only overrides are
# listed; everything else defaults to "attack". The instance's type decides
# which type-gated Damage-Up buff applies (see raid_simulator._TYPE_BUCKETS).
_BURST_DAMAGE_TYPES = {
    "rapi-red-hood": "projectile_explosion",  # Power of Inheritance = Projectile Explosion skill
}


def build_nikke_rules(slug, skill_values):
    if slug not in _BUILDERS:
        raise KeyError(f"no encoded skill rules for slug: {slug!r}")
    return _BUILDERS[slug](skill_values)


def get_burst_damage_type(slug):
    """The damage type of this Nikke's burst nuke ("attack" for the vast
    majority; an override like "projectile_explosion" for keyword skills). Only
    matters for a slug that has a burst nuke - see raid_simulator's
    burst_damage_types."""
    return _BURST_DAMAGE_TYPES.get(slug, "attack")


def get_periodic_nuke(slug, skill_values):
    """{"cooldown": seconds, "percent": float} for a Nikke with a skill that
    fires repeatedly on its own fixed cooldown (see raid_simulator's
    `periodic_nukes` param), or None for the vast majority of Nikkes without
    one."""
    builder = _PERIODIC_NUKE_BUILDERS.get(slug)
    return builder(skill_values) if builder else None
