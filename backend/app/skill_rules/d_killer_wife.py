"""D: Killer Wife (slug "d-killer-wife"), a Burst-1 SR supporter/attacker.
Base skills (no signature).

Modeled (DPS-relevant):
- Calm Sniping (skills[0]): on Full Burst enter, squad Pierce Damage up (the
  skill limits it to Sniper Rifle allies; approximated as squad since the
  scope model has no weapon-conditional targeting, and pierce is already
  treated as general damage-up).
- Kill the Target (skills[2], her burst): a burst nuke, "X% of final ATK".

Not modeled: Assault Formation's burst-cooldown reduction and attack-damage
buff (both gated on a full-charge-shot counter - no charge-count trigger
yet), the self single-shot Pierce, and Kill the Target's Wipe-Out debuff /
area-hit conditional buffs (positional/target-state, unsupported).
"""
from app.skill_rules._helpers import buff_rule


def build_d_killer_wife_rules(values):
    calm = values["calm_sniping"]
    fb_pierce = float(calm["description_value_02"]) / 100
    fb_pierce_duration = float(calm["description_value_03"])
    return [
        buff_rule("full_burst_enter", [
            ("pierce_damage_up", fb_pierce, "squad", fb_pierce_duration),
        ]),
    ]


def kill_the_target_burst_percent(values):
    return float(values["kill_the_target"]["description_value_01"])
