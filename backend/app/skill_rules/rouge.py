"""Rouge (slug "rouge"), a Burst-1 Electric SR supporter. Base skills.

Rouge is assumed assigned to the BACK ROW (deck position 2 or 4) - Fienn's
modeling assumption - so Coin Flip's back-row Sword Coin is active from the
start of battle.

Modeled (DPS-relevant):
- Coin Flip (skills[1]) Sword Coin: squad Attack Damage (the skill affects self +
  the 2 adjacent allies; approximated as squad, since the scope model has no
  positional targeting). Continuous from battle start given the back-row
  assumption; it also sets the Sword Coin status Game Master reads.
- Coin Flip's full chain: Sword Coin -> Shield Coin (her 30th Full Charge) ->
  Double Sword Coin (her 5th burst), which grants the squad Max HP +15.08% of
  her own, continuously. Shield Coin's own Damage Taken reduction stays
  unmodeled - only its STATUS is set, since two later bullets gate on it.
- Game Master (skills[2], her burst): squad ATK % of caster's ATK, plus Max HP
  buffs gated on Coin statuses (see the Max HP note).

Max HP note: her Max HP buffs are encoded as `flat_max_hp`, which since
2026-07-24 feeds every "ATK ▲ X% of Max HP" conversion (Maiden, Cinderella,
Maxwell, Laplace: Ultimate Hero) - so a deck holding one of those gains real
damage from them. All three Game Master bullets can now fire: the statuses their
gates read are all set by the chain above.

Modeled cooldown:
- Card Throw (skills[0]): its every-8-full-charge squad Cooldown reduction,
  modeled as a per-CYCLE CDR pulse (on full_burst_end) rather than counting shots.
  Rationale (Fienn): 8 full charges is met essentially every cycle (a full charge
  ~1 sec), so applying the reduction once per cycle is a faithful approximation,
  using the existing per-cycle CDR machinery. Its Max HP bullet is survival.

Not modeled:
- Shield Coin's Damage Taken reduction (survival) and Card Throw's Max HP
  bullet, whose own trigger the per-cycle CDR approximation does not track.
"""
from app.effects import Effect
from app.skill_rules._helpers import cdr_pulse_rule
from app.squad_engine import SkillRule, has_status


SKILL_VALUE_MANIFESTS = {
    "rouge": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst1_batch2",
        "keys": {
            "card_throw": ("skills", 0),
            "coin_flip": ("skills", 1),
            "game_master": ("skills", 2),
        },
        "drop_tokens": {
            "coin_flip": [0, 3],
        },
        "fixtures": {
            "card_throw": "ROUGE_CARD_THROW",
            "coin_flip": "ROUGE_COIN_FLIP",
            "game_master": "ROUGE_GAME_MASTER",
        },
    },
}


SWORD_COIN_STATUS = "Sword Coin"
SHIELD_COIN_STATUS = "Shield Coin"
DOUBLE_SWORD_COIN_STATUS = "Double Sword Coin"


def build_card_throw_rules(values):
    """Card Throw's every-8-full-charge squad Cooldown reduction as a per-cycle
    CDR pulse (see the module docstring). Its Max HP is survival, not modeled."""
    cdr_sec = float(values["description_value_04"])
    return [cdr_pulse_rule("full_burst_end", cdr_sec)]


def build_coin_flip_rules(values):
    """The coin chain. Each link needs the previous coin, and the last one pays
    out: Sword Coin (back row, from battle start) -> Shield Coin (30 full
    charges, see build_coin_flip_per_shot_rules) -> Double Sword Coin (her 5th
    burst), which grants the squad Max HP continuously.

    Shield Coin's own effect is a Damage Taken reduction and stays unmodeled -
    only its STATUS is set, because Double Sword Coin and Game Master's middle
    Max HP bullet both gate on it."""
    sword_coin_attack_damage = float(values["description_value_01"]) / 100
    double_coin_bursts = int(float(values["description_value_04"]))
    double_coin_max_hp = values["caster_max_hp"] * float(values["description_value_05"]) / 100

    def apply_sword_coin(context, caster_slug, time, registry):
        context.set_status(caster_slug, SWORD_COIN_STATUS)
        registry.add(
            Effect("attack_damage_up", sword_coin_attack_damage, "squad", None, caster_slug),
            applied_at=time,
        )

    def apply_double_sword_coin(context, caster_slug, time, registry):
        if context.activation_count(caster_slug, "own_burst_activate") != double_coin_bursts:
            return
        context.set_status(caster_slug, DOUBLE_SWORD_COIN_STATUS)
        registry.add(
            Effect("flat_max_hp", double_coin_max_hp, "squad", None, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="battle_start", action=apply_sword_coin),
        SkillRule(
            trigger="own_burst_activate",
            condition=has_status(SHIELD_COIN_STATUS),
            action=apply_double_sword_coin,
        ),
    ]


def build_coin_flip_per_shot_rules(values):
    """Shield Coin arms on the 30th Full Charge while in Sword Coin (she is an
    SR, so every shot is one). Sets the status only - the Damage Taken reduction
    it carries is survivability."""
    threshold = int(float(values["description_value_02"]))

    def action(context, caster_slug, time, registry):
        context.set_status(caster_slug, SHIELD_COIN_STATUS)

    rule = SkillRule(trigger="per_shot", action=action)
    rule.condition = has_status(SWORD_COIN_STATUS)
    return [(threshold, "after", [rule])]


def build_game_master_rules(values):
    caster_atk = values["caster_atk"]
    caster_max_hp = values["caster_max_hp"]
    atk_bonus = caster_atk * float(values["description_value_01"]) / 100
    atk_duration = float(values["description_value_02"])
    sword_max_hp = caster_max_hp * float(values["description_value_03"]) / 100
    sword_max_hp_duration = float(values["description_value_04"])
    shield_max_hp = caster_max_hp * float(values["description_value_05"]) / 100
    shield_max_hp_duration = float(values["description_value_06"])
    double_max_hp = caster_max_hp * float(values["description_value_07"]) / 100
    double_max_hp_duration = float(values["description_value_08"])

    def apply_atk(context, caster_slug, time, registry):
        registry.add(Effect("flat_atk", atk_bonus, "squad", atk_duration, caster_slug), applied_at=time)

    def max_hp_rule(status, value, duration):
        def action(context, caster_slug, time, registry):
            registry.add(Effect("flat_max_hp", value, "squad", duration, caster_slug), applied_at=time)

        return SkillRule(trigger="own_burst_activate", condition=has_status(status), action=action)

    return [
        SkillRule(trigger="own_burst_activate", action=apply_atk),
        max_hp_rule(SWORD_COIN_STATUS, sword_max_hp, sword_max_hp_duration),
        max_hp_rule(SHIELD_COIN_STATUS, shield_max_hp, shield_max_hp_duration),
        max_hp_rule(DOUBLE_SWORD_COIN_STATUS, double_max_hp, double_max_hp_duration),
    ]
