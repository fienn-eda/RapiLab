"""Rouge (slug "rouge"), a Burst-1 SR supporter. Base skills (no signature).

Modeled (DPS-relevant):
- Game Master (skills[2], her burst): squad ATK up as a flat bonus scaled off
  Rouge's own ATK (caster-scaled, like Crown's One for All).

Not modeled: Card Throw's burst-cooldown reduction and Coin Flip's Sword Coin
attack-damage buff. Card Throw triggers on a full-charge-shot counter (no
charge-count trigger exists yet), and Coin Flip is a back-row positional
buff (the engine's scope model has no positional targeting). Max-HP effects
are survivability, not DPS.
"""
from app.skill_rules._helpers import buff_rule


def build_rouge_rules(values):
    game_master = values["game_master"]
    caster_atk = values["caster_atk"]
    atk_bonus = caster_atk * float(game_master["description_value_07"]) / 100
    duration = float(game_master["description_value_08"])
    return [
        buff_rule("own_burst_activate", [("flat_atk", atk_bonus, "squad", duration)]),
    ]
