"""Noir (slug "noir"), a Burst-3 Wind Shotgun attacker. Base skills.

Modeled (DPS-relevant):
- Lucky Charm (skills[0]): squad ATK up (14.08% of caster's ATK), permanent. The
  ">70% HP" gate is approximated as always-on (true for most of a raid).
- Rabbit Twins B (skills[1]): on Full Burst entry, squad Max Ammunition Capacity
  +5 ROUNDS for 10 sec (a flat round count, `max_ammo_rounds` - raid_simulator
  converts it against each recipient's own base magazine).
- Finale (skills[2], her burst): burst nuke 351.64% of final ATK, plus two
  bullets that each carry a Hit Rate and a Damage-to-Interruption-Parts buff -
  Shotgun allies get +13.93% / +23.23% for 10s, and the whole squad gets +11.61% /
  +19.36% for 30s. The shotgun bullet's Hit Rate uses the EXACT weapon subset;
  its Damage-to-Interruption-Parts twin stays on the squad approximation it was
  encoded with (changing that moves damage, and is not this change's business).
  The second bullet's "with an ally from the same squad still on the
  battlefield" gate is always true in a sim where nobody dies, so it applies
  unconditionally to the squad. "Interruption Parts" (저지 부위) is the zone an
  interruption gimmick makes you hit - NOT a destructible part - so it goes to
  its own stat and, like Damage to Parts, never reaches body damage.
  The two Hit Rate halves stack on a shotgun ally (+25.54% together), which
  narrows a 250px spread to 192px - 4.0% -> 6.8% of a 50px core.
- Rabbit Twins B's instant partial reload ("Reload 39.88% magazine(s)"): a
  timed squad-wide refill grant on Full Burst enter (`get_ammo_refill_grant`).
  It lands at the same instant as the Max Ammunition Capacity +5 rounds above,
  but the engine reads a magazine's capacity once, when the magazine opens - so
  the 39.88% resolves against the capacity the recipient's current magazine was
  built with, the same granularity every max-ammo buff already has here.
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule


SKILL_VALUE_MANIFESTS = {
    "noir": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst3_eb1",
        "keys": {
            "lucky_charm": ("skills", 0),
            "rabbit_twins_b": ("skills", 1),
            "finale": ("skills", 2),
        },
        "drop_tokens": {
            "lucky_charm": [0],
        },
    },
}


def finale_burst_percent(values):
    return float(values["finale"]["description_value_01"])


def rabbit_twins_b_refill(values):
    """Rabbit Twins B's "Reload 39.88% magazine(s)": a squad-wide grant at
    Full Burst entry, alongside (not instead of) the Max Ammunition Capacity
    +5 rounds this same bullet also carries."""
    bullet = values["rabbit_twins_b"]
    return {"percent": float(bullet["description_value_03"]),
            "scope": "squad", "event": "full_burst_enter"}


def shotgun_allies(member, context):
    """Finale's "all allies with a Shotgun" - Noir herself included."""
    return member.weapon == "SG"


def build_noir_rules(values):
    lucky = values["lucky_charm"]
    rabbit_twins = values["rabbit_twins_b"]
    finale = values["finale"]
    caster_atk = values["caster_atk"]
    squad_atk = float(lucky["description_value_01"]) / 100 * caster_atk
    ammo_rounds = float(rabbit_twins["description_value_01"])
    ammo_duration = float(rabbit_twins["description_value_02"])
    sg_hit_rate = float(finale["description_value_02"]) / 100
    sg_duration = float(finale["description_value_03"])
    parts_1 = float(finale["description_value_04"]) / 100
    parts_1_duration = float(finale["description_value_05"])
    squad_hit_rate = float(finale["description_value_06"]) / 100
    squad_hit_rate_duration = float(finale["description_value_07"])
    parts_2 = float(finale["description_value_08"]) / 100
    parts_2_duration = float(finale["description_value_09"])

    return [
        buff_rule("battle_start", [("flat_atk", squad_atk, "squad", None)]),
        buff_rule("full_burst_enter", [
            ("max_ammo_rounds", ammo_rounds, "squad", ammo_duration),
        ]),
        # "Affects all allies with a Shotgun" - the exact weapon subset. A
        # shotgun is the only weapon whose spread has room to narrow, so giving
        # this Hit Rate to the whole squad would both over-apply it and hide how
        # targeted the buff is.
        member_subset_buff_rule("own_burst_activate", shotgun_allies, [
            ("hit_rate", sg_hit_rate, sg_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("hit_rate", squad_hit_rate, "squad", squad_hit_rate_duration),
            # Its Damage-to-Interruption-Parts twin keeps the squad approximation
            # it has carried since the encoding landed - narrowing that one moves
            # real damage numbers, which is a separate change from this one.
            ("damage_to_interruption_parts_up", parts_1, "squad", parts_1_duration),
            ("damage_to_interruption_parts_up", parts_2, "squad", parts_2_duration),
        ]),
    ]
