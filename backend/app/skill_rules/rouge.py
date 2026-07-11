"""Rouge (slug "rouge"), a Burst-1 Electric SR supporter. Base skills.

Rouge is assumed assigned to the BACK ROW (deck position 2 or 4) - Fienn's
modeling assumption - so Coin Flip's back-row Sword Coin is active from the
start of battle.

Modeled (DPS-relevant):
- Coin Flip (skills[1]) Sword Coin: squad Attack Damage (the skill affects self +
  the 2 adjacent allies; approximated as squad, since the scope model has no
  positional targeting). Continuous from battle start given the back-row
  assumption; it also sets the Sword Coin status Game Master reads.
- Game Master (skills[2], her burst): squad ATK % of caster's ATK, plus Max HP
  buffs gated on Coin statuses (see the Max HP note).

Max HP note: Game Master's Max HP buffs are encoded (as `flat_max_hp`, scaled off
the caster's Max HP) even though nothing consumes Max HP for damage TODAY - Fienn
wants them in place for future units whose damage scales off Max HP. The Sword
Coin one fires (back-row Sword Coin is active); the Shield / Double Sword Coin
ones are gated on statuses whose setters are deferred, so they stay dormant until
those are built.

Not modeled:
- Card Throw (skills[0]) entirely: its Max HP is survival, and its Cooldown
  reduction (every 8 full charges) is a per-shot CDR that can't reach the burst
  rotation (the rotation is simulated before the per-shot pass runs).
- Coin Flip's Shield Coin (a Damage Taken reduction - survival, deferred per
  Fienn; also a per-shot-30 counter) and Double Sword Coin (Max HP, survival,
  per-burst counter).
"""
from app.effects import Effect
from app.squad_engine import SkillRule, has_status

SWORD_COIN_STATUS = "Sword Coin"


def build_coin_flip_rules(values):
    sword_coin_attack_damage = float(values["description_value_01"]) / 100

    def apply_sword_coin(context, caster_slug, time, registry):
        context.set_status(caster_slug, SWORD_COIN_STATUS)
        registry.add(
            Effect("attack_damage_up", sword_coin_attack_damage, "squad", None, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="battle_start", action=apply_sword_coin)]


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
        max_hp_rule("Shield Coin", shield_max_hp, shield_max_hp_duration),
        max_hp_rule("Double Sword Coin", double_max_hp, double_max_hp_duration),
    ]
