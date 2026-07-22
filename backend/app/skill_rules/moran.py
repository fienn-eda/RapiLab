"""Moran (slug "moran"), a Burst-1 AR Defender, signature weapon done
(dollskills). Fienn's Moran has hers completed.

Modeled (DPS-relevant):
- Leave It To Me! (dollskills[1]): on Full Burst enter while in Fervor, squad
  burst-cooldown reduction.
- Fair and Square! (dollskills[2], her burst): squad ATK up as a flat bonus
  scaled off Moran's own ATK.
- Fair and Square!'s weapon transform: for 10 sec her AR becomes an
  unlimited-ammo SMG dealing 14.7% of final ATK per shot - a
  `weapon_mode_schedules` segment (see
  build_fair_and_square_weapon_mode_schedule). Infinite ammo makes an in-game
  shot count impractical to measure (Fienn 2026-07-22), and no community guide
  publishes one, so the cadence is anchored to the engine's canonical SMG rate
  (20 shots/sec) - the transform IS an SMG, so this reuses a measured constant
  rather than inventing one. burst_percent stays None (the transform is her
  burst damage, not a single nuke).

Assumption: Fervor is triggered by "Raptures appear" and is treated as always
active in a raid. Not modeled: DEF / damage-taken / Max-HP survivability buffs
(the squad "Damage Taken +" line reads as an ally-side effect, not an enemy
DPS debuff), taunts, the HP-recovery on the transform, and the HP-threshold
Perseverance effect.
"""
from app.attack_rate import rate_of_fire_for_weapon
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule

# Fienn's Moran has the signature weapon completed, so the manifest reads the
# "dollskills" array, not "skills" (see module docstring).
SKILL_VALUE_MANIFESTS = {
    "moran": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "leave_it_to_me": ("dollskills", 1),
            "fair_and_square": ("dollskills", 2),
        },
    },
}


def build_moran_rules(values):
    leave = values["leave_it_to_me"]
    fair = values["fair_and_square"]
    caster_atk = values["caster_atk"]
    cdr_sec = float(leave["description_value_10"])
    atk_bonus = caster_atk * float(fair["description_value_09"]) / 100
    atk_duration = float(fair["description_value_10"])

    return [
        cdr_pulse_rule("full_burst_enter", cdr_sec),
        buff_rule("own_burst_activate", [("flat_atk", atk_bonus, "squad", atk_duration)]),
    ]


def build_fair_and_square_weapon_mode_schedule(values):
    """Fair and Square!'s weapon transform: for 10 sec her AR becomes an
    unlimited-ammo SMG dealing 14.7% of final ATK per shot.

    A `weapon_mode_schedules` segment fits cleanly - the skill grants "Unlimited
    ammunition" for exactly the transform window, and segments never reload, so
    there is no magazine to interrupt (the same reason the primitive suited
    Nayuta's Memory Incineration). The window is `end`-bounded by that duration
    rather than a measured `until_shots`: no shot count exists to anchor to
    (infinite ammo makes an in-game count impractical, and no guide publishes
    one), so the count follows from the rate and the 10-sec window.

    The cadence is the engine's canonical SMG rate (`rate_of_fire_for_weapon`,
    20 shots/sec) - the transform IS an SMG, so this is a measured weapon-class
    constant, not an invented number (Fienn approved this proxy 2026-07-22). As
    an explicit `rate_of_fire` it takes no cadence buffs, matching every other
    measurement-anchored segment; revisit if the transform's real rate is ever
    measured."""
    fair = values["fair_and_square"]
    profile = {
        "weapon": "SMG",
        "damage_percent": float(fair["description_value_01"]),  # 14.7
        "rate_of_fire": rate_of_fire_for_weapon("SMG"),
    }
    window = float(fair["description_value_04"])  # unlimited-ammo duration, 10s

    def schedule(context, fight_duration):
        return [
            {"start": t, "end": t + window, "profile": profile}
            for t in context.burst_times.get("moran", [])
        ]

    return schedule
