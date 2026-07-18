"""Anis: Star (slug "anis-star"), a Burst-1 Electric RL Defender.

Modeled (DPS-relevant):
- Starfall (skills[0]): the formation-branch buffs (alone -> My Own Star self
  ATK + squad burst-cooldown reduction; with a Burst-1 ally -> Everyone's Star)
  and its full-charge additional damage (120.13% of final ATK on every Full
  Charge -> a per-shot nuke, since an RL's every shot is a full charge; see
  `build_starfall_full_charge_nuke_rules`).
- Stardust (skills[1]): squad ATK % of caster's ATK while My Own Star; squad
  Projectile Explosion Damage (the skill says "self + allies with lower DEF";
  she's a Defender so ~everyone qualifies -> squad approx); squad Attack Damage.
- Star Anis (burst): self Attack Damage while My Own Star.

Not modeled: Starfall's Burst Gauge filling speed (inert stat) and the
Everyone's Star "Re-enters Burst / Stage" branch (no multi-stage burst re-entry);
the burst's Shooting Stars auto-attack (40.01% every 0.25s for 10s during the
burst window - needs a periodic-during-burst-window capability, deferred), its
Explosion Radius / fixed charge time / DEF, and all heal / Max HP (survival).
"""
from app.effects import Effect, Pulse
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule
from app.squad_engine import SkillRule, has_status, no_other_burst_tier_allies, not_condition

SKILL_VALUE_MANIFESTS = {
    "anis-star": {
        "source": "dotgg",
        "test_module": "test_skill_rules_anis_star",
        "keys": {
            "starfall": ("skills", 0),
            "stardust": ("skills", 1),
            "star_anis": ("skills", 2),
        },
        "fixtures": {"starfall": "LEVEL_10_VALUES"},
        "drop_tokens": {
            # The fixture keeps only the modeled My Own Star Attack Damage pair
            # (35.2 / 10s); dropped slots are the burst's unmodeled Shooting
            # Stars auto-attack (40.01/10/100), DEF 55.01, Everyone's Star Max
            # HP (15.02/10) and the fixed 0.7s charge time.
            "star_anis": [0, 1, 2, 3, 6, 7, 8],
        },
    },
}


def build_starfall_rules(values: dict) -> list[SkillRule]:
    own_burst_tier = int(values["description_value_01"])
    my_own_star_atk = float(values["description_value_02"]) / 100
    cooldown_reduction_sec = float(values["description_value_03"])
    gauge_fill_speed = float(values["description_value_05"]) / 100

    def grant_gauge_fill_speed(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "Starfall Gauge Buff Granted"):
            return
        context.set_status(caster_slug, "Starfall Gauge Buff Granted")
        registry.add(
            Effect(
                stat="burst_gauge_fill_speed_percent",
                value=gauge_fill_speed,
                scope="squad",
                duration=None,
                source_slug=caster_slug,
            ),
            applied_at=time,
        )

    def alone_branch(context, caster_slug, time, registry):
        context.clear_status(caster_slug, "Everyone's Star")
        if not context.has_status(caster_slug, "My Own Star"):
            context.set_status(caster_slug, "My Own Star")
            registry.add(
                Effect(
                    stat="atk_percent",
                    value=my_own_star_atk,
                    scope="self",
                    duration=None,
                    source_slug=caster_slug,
                ),
                applied_at=time,
            )
        registry.add_pulse(
            Pulse(
                stat="burst_cooldown_reduction_sec",
                value=cooldown_reduction_sec,
                scope="squad",
                source_slug=caster_slug,
            )
        )

    def with_ally_branch(context, caster_slug, time, registry):
        context.clear_status(caster_slug, "My Own Star")
        context.set_status(caster_slug, "Everyone's Star")

    alone = no_other_burst_tier_allies(own_burst_tier)
    with_ally = not_condition(alone)

    return [
        SkillRule(trigger="battle_start", action=grant_gauge_fill_speed),
        SkillRule(trigger="battle_start", condition=alone, action=alone_branch),
        SkillRule(trigger="battle_start", condition=with_ally, action=with_ally_branch),
        SkillRule(trigger="full_burst_end", condition=alone, action=alone_branch),
        SkillRule(trigger="full_burst_end", condition=with_ally, action=with_ally_branch),
    ]


def build_starfall_full_charge_nuke_rules(values: dict):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): Starfall deals
    additional damage (`description_value_04`% of final ATK) on every Full Charge
    attack - an RL's every shot is a full charge, so it fires each shot."""
    nuke_percent = float(values["description_value_04"])
    return [(1, "every", [instant_nuke_pulse_rule("per_shot", nuke_percent)])]


def build_stardust_rules(values: dict) -> list[SkillRule]:
    my_own_star_atk = float(values["description_value_01"]) / 100 * values["caster_atk"]
    my_own_star_atk_duration = float(values["description_value_02"])
    projectile_explosion = float(values["description_value_04"]) / 100
    projectile_explosion_duration = float(values["description_value_05"])
    attack_damage = float(values["description_value_06"]) / 100
    attack_damage_duration = float(values["description_value_07"])

    def apply_my_own_star_atk(context, caster_slug, time, registry):
        registry.add(
            Effect("flat_atk", my_own_star_atk, "squad", my_own_star_atk_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(
            trigger="full_burst_enter",
            condition=has_status("My Own Star"),
            action=apply_my_own_star_atk,
        ),
        buff_rule("full_burst_enter", [
            ("projectile_explosion_damage_up", projectile_explosion, "squad", projectile_explosion_duration),
            ("attack_damage_up", attack_damage, "squad", attack_damage_duration),
        ]),
    ]


def build_star_anis_burst_rules(values: dict) -> list[SkillRule]:
    self_attack_damage = float(values["description_value_01"]) / 100
    self_attack_damage_duration = float(values["description_value_02"])

    def apply_self_attack_damage(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(
            trigger="own_burst_activate",
            condition=has_status("My Own Star"),
            action=apply_self_attack_damage,
        ),
    ]
