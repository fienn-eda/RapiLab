"""Eunhwa: Tactical Upgrade (slug "eunhwa-tactical-upgrade"), a Burst-2 Fire SR
attacker. Values from ShiftyPad; effect text cross-read from lootandwaifus.

Modeled (DPS-relevant):
- Camouflage Scarf (skills[0]): while Camouflaged her normal attacks deal TRUE
  damage and she carries True Damage +42.24%. Camouflage itself is a dodge (not
  damage), but its WINDOW is what gates the two bullets that are, so the status
  is modeled as a 5-second self buff carrying both.

  It arms from two triggers - her own burst, and every Full Charge she lands
  inside Full Burst (`per_shot_rules` mode "every_during_full_burst", N=1). The
  two windows overlap, so both use `refreshing_buff_rule` with ONE SHARED
  refresh group: it is a single status re-armed, not two that sum. Her rifle
  fires every ~1.4 sec against a 5-sec status, so once Full Burst opens the
  status holds through the window and 5 sec past it.
- AS Formation (skills[1]), continuous from battle start:
  - Absolute-squad allies Critical Rate +8.16%. "All allies from the same
    squad" is her in-fiction squad, which the engine's scopes cannot express -
    but its membership is six units and settled, so `member_subset_buff_rule`
    over `ABSOLUTE_SQUAD_SLUGS` resolves it exactly rather than approximating
    onto `squad` (which would hand every deck-mate a crit buff the game does
    not give them).
  - squad Charge Damage +41.81%, and self ATK +42.24%. Read per bullet: the
    ATK line says "Affects self", the Charge Damage line "all allies".
  - the LT Formation bonus, squad Projectile Explosion Damage +5.11% and True
    Damage +30.97%. LT Formation is Emma: Tactical Upgrade's own S2, which she
    issues to her targets - so the bonus is live exactly when Emma is in the
    deck (Fienn, 2026-08-08), gated with `deck_contains`. The True Damage half
    lands on her own Camouflaged normal attacks and on her burst round; the
    Projectile Explosion half needs an RL ally or a projectile-explosion skill
    to have anything to multiply.
- Explosive Round (skills[2], her burst, cd 20): swaps her weapon for ONE
  exploding round (Fienn, in-game 2026-08-08 - the text gives no duration and
  the answer is a single shot, not a window). A `weapon_mode_schedules` segment
  with `until_shots: 1`: 0.3 sec charge, 105.6% of final ATK, 300% full-charge
  multiplier, typed `true`. Being a real segment rather than a flat nuke is
  what lets the deck's ATK and Charge Damage buffers - including her own
  +41.81% - multiply it.
  Its rider, Damage Taken +27.87% for 10 sec on the target hit, is applied at
  her burst instead of at the round's own impact: the two are 0.3 sec apart
  (the segment's charge), and the engine has no hook on a segment shot landing.

Not modeled / deferred:
- Camouflage's actual effect, "prevents being targeted by single-target
  attacks", and its removal on taking a direct hit. The engine has no targeting
  or incoming-damage model, so the status never breaks here - which makes the
  windows above an upper bound in a fight where she is being shot at. In a solo
  raid the boss's attacks are not modeled at all, so nothing about this is
  decidable from within the sim.
"""
from app.skill_rules._helpers import (
    ABSOLUTE_SQUAD_SLUGS,
    buff_rule,
    member_subset_buff_rule,
    refreshing_buff_rule,
)
from app.squad_engine import deck_contains


SKILL_VALUE_MANIFESTS = {
    "eunhwa-tactical-upgrade": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_eunhwa_tactical_upgrade",
        "keys": {
            "camouflage_scarf": ("skills", 0),
            "as_formation": ("skills", 1),
            "explosive_round": ("skills", 2),
        },
    },
}


EMMA = "emma-tactical-upgrade"  # the LT Formation half of the pair

# Explosive Round's weapon profile is written into the skill PROSE, not into
# value slots - the data carries only the damage percent, the round count and
# the rider. These two are transcribed from that text.
EXPLOSIVE_ROUND_CHARGE_TIME = 0.3
EXPLOSIVE_ROUND_FULL_CHARGE_DAMAGE = 300.0

# One shared group for the Camouflage status, so her burst and her Full-Burst
# charges re-arm the SAME window instead of stacking two of them.
_CAMOUFLAGE_REFRESH_GROUP = "eunhwa-tu-camouflage"


def _camouflage_buffs(camouflage):
    duration = float(camouflage["description_value_01"])
    true_damage = float(camouflage["description_value_02"]) / 100
    return [
        # The type conversion is encoded in the stat name; the normal-attack
        # pass reads it at each shot time.
        ("normal_attacks_deal_true", 1.0, "self", duration),
        ("true_damage_up", true_damage, "self", duration),
    ]


def _is_absolute_squad(member, _context=None):
    return member.slug in ABSOLUTE_SQUAD_SLUGS


def build_camouflage_per_shot_rules(camouflage):
    """Camouflage re-armed by every Full Charge inside Full Burst. Counting only
    in-window shots is the point: outside Full Burst the same charge does not
    arm it at all."""
    return [
        (1, "every_during_full_burst", [
            refreshing_buff_rule(
                "per_shot", _camouflage_buffs(camouflage),
                refresh_group=_CAMOUFLAGE_REFRESH_GROUP,
            ),
        ]),
    ]


def build_explosive_round_weapon_mode_schedule(values):
    """Her burst's one exploding round, as a weapon-mode segment.

    Every term of the transformed weapon comes from the skill, none from
    `weapon_stats` - which is where a collectible's charge-damage 배율 is
    normally applied - so the 배율 has to be applied here or the segment loses
    it entirely. Fienn measured 2026-08-03 that it does reach a transform
    (docs/measurements/collectible-charge-damage-in-transform.md); Maxwell's
    Pierce Shot carries the same line for the same reason.
    """
    explosive = values["explosive_round"]
    profile = {
        "weapon": "SR",
        "damage_percent": float(explosive["description_value_01"]),
        "charge_damage_percent": (
            EXPLOSIVE_ROUND_FULL_CHARGE_DAMAGE
            * values.get("caster_charge_damage_multiplier", 1.0)),
        "charge_time": EXPLOSIVE_ROUND_CHARGE_TIME,
        "max_ammo": int(float(explosive["description_value_02"])),
        "damage_type": "true",
    }

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": 1, "profile": profile}
                for t in context.burst_times.get("eunhwa-tactical-upgrade", [])]

    return schedule


def build_eunhwa_tactical_upgrade_rules(values):
    camouflage = values["camouflage_scarf"]
    formation = values["as_formation"]
    explosive = values["explosive_round"]

    squad_crit_rate = float(formation["description_value_01"]) / 100
    charge_damage = float(formation["description_value_02"]) / 100
    projectile_explosion = float(formation["description_value_03"]) / 100
    true_damage = float(formation["description_value_04"]) / 100
    self_atk = float(formation["description_value_05"]) / 100

    damage_taken = float(explosive["description_value_03"]) / 100
    damage_taken_duration = float(explosive["description_value_04"])

    with_emma = deck_contains(EMMA)

    return [
        member_subset_buff_rule(
            "battle_start", _is_absolute_squad, [("crit_rate", squad_crit_rate, None)],
        ),
        buff_rule("battle_start", [
            ("charge_damage_bonus", charge_damage, "squad", None),
            ("atk_percent", self_atk, "self", None),
        ]),
        buff_rule(
            "battle_start",
            [
                ("projectile_explosion_damage_up", projectile_explosion, "squad", None),
                ("true_damage_up", true_damage, "squad", None),
            ],
            condition=with_emma,
        ),
        refreshing_buff_rule(
            "own_burst_activate", _camouflage_buffs(camouflage),
            refresh_group=_CAMOUFLAGE_REFRESH_GROUP,
        ),
        buff_rule("own_burst_activate", [
            ("damage_taken_up", damage_taken, "squad", damage_taken_duration),
        ]),
    ]
