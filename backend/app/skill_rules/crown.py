"""SkillRule encoding of Crown's "One for All" (skills[0]) and "Last Kingdom"
(skills[2], her burst skill) from api.dotgg.gg slug "crown".

"X% of caster's ATK/DEF" bonuses use Crown's base ATK/DEF from her character
info tab - per Fienn, that excludes overload/other skill effects and only
reflects gear+breakthrough+cube - so callers pass those as plain numbers
resolved once, not derived from the live EffectRegistry.

"Royal Attire" (skills[1]) is a chain whose only DPS-relevant link is the last
one: 43 normal attacks grant a Relax stack, 20 stacks trigger a self-heal, and
"when recovery takes effect" the whole squad gets Attack Damage +20.99% for 7
sec. Everything before that link is survivability (Relax raises INCOMING
healing potency; the max-stack proc is invulnerability, a taunt, and the heal
itself), so only the final buff is modeled.

Two paths reach it, because the trigger reads ANY ally's healing, not just her
own (Fienn, 2026-07-20), and the engine has no heal event to hook:

- Her own chain: 43 x 20 = 860 of her own normal attacks, as `per_shot_rules`
  ("every", 860). At MG cadence (60 rounds/sec, 300-round magazine, 2.5 sec
  reload) that is ~21.5 sec of firing, so roughly 8 procs and ~31% uptime
  across a 180-sec fight. This is the floor, and the only path when she is the
  squad's sole healer.
- Any OTHER healer in the deck: modeled as the buff simply being maintained.
  This is the CEILING, and deliberately so - a healer whose heals land often
  (Helm recovers on every Full Charge; Mint on Here I Go!) really does keep a
  7-sec window alive, but one that heals rarely would not. Deck membership is
  the most the engine can ask, since it models no heal events; the roster of
  healers is derived from skill text by scripts/find_heal_providers.py rather
  than hand-listed, and lives in `_helpers.HEAL_PROVIDER_SLUGS`.

Crown is herself in that roster (she heals at the end of her own chain), so the
presence check EXCLUDES the caster - otherwise she would arm her own ceiling
branch and the 860-shot floor would never matter.
"""
from app.effects import Effect
from app.skill_rules._helpers import HEAL_PROVIDER_SLUGS, refreshing_buff_rule
from app.squad_engine import SkillRule, deck_contains_any

SKILL_VALUE_MANIFESTS = {
    "crown": {
        "source": "dotgg",
        "test_module": "test_skill_rules_crown",
        "keys": {
            "one_for_all": ("skills", 0),
            "royal_attire": ("skills", 1),
            "last_kingdom": ("skills", 2),
        },
        "fixtures": {
            "one_for_all": "ONE_FOR_ALL_VALUES",
            "royal_attire": "ROYAL_ATTIRE_VALUES",
            "last_kingdom": "LAST_KINGDOM_VALUES",
        },
    },
}


def build_one_for_all_rules(values: dict, caster_atk: float, caster_def: float) -> list[SkillRule]:
    atk_bonus = caster_atk * float(values["description_value_01"]) / 100
    atk_duration = float(values["description_value_02"])
    reload_burst_users = float(values["description_value_03"]) / 100
    reload_duration_burst_users = float(values["description_value_04"])
    def_bonus = caster_def * float(values["description_value_05"]) / 100
    def_duration = float(values["description_value_06"])
    reload_non_burst_users = float(values["description_value_07"]) / 100
    reload_duration_non_burst_users = float(values["description_value_08"])

    def action(context, caster_slug, time, registry):
        for member in context.members:
            if member.slug in context.burst_used_this_cycle:
                registry.add(
                    Effect("flat_atk", atk_bonus, "self", atk_duration, member.slug),
                    applied_at=time,
                )
                registry.add(
                    Effect(
                        "reload_speed_percent",
                        reload_burst_users,
                        "self",
                        reload_duration_burst_users,
                        member.slug,
                    ),
                    applied_at=time,
                )
            else:
                registry.add(
                    Effect("flat_def", def_bonus, "self", def_duration, member.slug),
                    applied_at=time,
                )
                registry.add(
                    Effect(
                        "reload_speed_percent",
                        reload_non_burst_users,
                        "self",
                        reload_duration_non_burst_users,
                        member.slug,
                    ),
                    applied_at=time,
                )

    return [SkillRule(trigger="full_burst_enter", action=action)]


def build_last_kingdom_rules(values: dict, caster_max_hp: float) -> list[SkillRule]:
    attack_damage_up = float(values["description_value_01"]) / 100
    attack_damage_duration = float(values["description_value_02"])
    shield_amount = caster_max_hp * float(values["description_value_03"]) / 100
    shield_duration = float(values["description_value_04"])

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", attack_damage_up, "squad", attack_damage_duration, caster_slug),
            applied_at=time,
        )
        # shield_amount has no consumer yet - it's survivability, not damage output.
        registry.add(
            Effect("shield_amount", shield_amount, "squad", shield_duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="own_burst_activate", action=action)]


def _royal_attire_buff(values):
    attack_damage_up = float(values["description_value_07"]) / 100
    duration = float(values["description_value_08"])
    return attack_damage_up, duration


def build_royal_attire_per_shot_rules(values: dict) -> list:
    """Her own path to the buff: `description_value_01` normal attacks per Relax
    stack, `description_value_03` stacks to the heal that arms it. Refreshing,
    not stacking - repeated procs re-arm one window."""
    per_stack = int(values["description_value_01"])
    max_stacks = int(values["description_value_03"])
    attack_damage_up, duration = _royal_attire_buff(values)
    return [(per_stack * max_stacks, "every", [
        refreshing_buff_rule("per_shot", [
            ("attack_damage_up", attack_damage_up, "squad", duration),
        ])
    ])]


def build_royal_attire_rules(values: dict) -> list[SkillRule]:
    """The ally-healing path: with another healer in the deck the 7-sec window
    is treated as maintained. See the module docstring for why this is the
    ceiling and why the caster is excluded from the presence check."""
    attack_damage_up, _duration = _royal_attire_buff(values)

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", attack_damage_up, "squad", None, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(
            trigger="battle_start",
            condition=deck_contains_any(HEAL_PROVIDER_SLUGS),
            action=action,
        ),
    ]
