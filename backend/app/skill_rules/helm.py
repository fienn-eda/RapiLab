"""Helm (slug "helm") and her Favorite Item build (slug "helm-signature"), a
Burst-3 Water SR attacker. Collected from api.dotgg.gg.

The two builds are separate deck candidates (dual-slot, like drake/julia), and
which one a user fights with comes from their roster's per-unit `favorite_item`
flag - never assumed here. Slots 01-03 carry the same meaning in both arrays, so
the shared builders below take either set; the Favorite Item's extra effects
read slots the base array does not have, and their builders are signature-only.

What the Favorite Item changes (it is not a numbers-only upgrade):
- Aegis Cannon's burst goes 1237.5% -> 8236.8% (6.7x).
- Fire Away's Full-Burst Attack Damage goes 11.85% -> 27.87%, and it GAINS a
  178.98% full-charge nuke the base skill has no text for at all.
- Aegis Cannon GAINS a self Charge Damage Multiplier rider. The base array's
  slots 04/05 are 30/30 and mean something else entirely, so
  build_aegis_cannon_rules must never be handed base values.

"Aegis Cannon" (skills[2]/dollskills[2], her burst skill) is mostly a pure
damage instance - use aegis_cannon_burst_percent() for the "X% of final ATK"
figure raid_simulator needs; the damage-proportional heal-over-time isn't
modeled since it doesn't affect DPS output.

"Frontline Command" fires "when the last bullet hits the target" - modeled
via `per_shot_rules`' `"last_bullet"` mode (gap #1's residual variant, built
2026-07-12) as a REFRESHING squad Crit Rate buff (SR's small magazine can
empty faster than the buff's own 5s window, so repeated last-bullet hits
must refresh, not stack - see the Prika/Mint per-shot-refresh precedent).

Signature only - "Fire Away" also deals 178.98% of final ATK on every Full
Charge hit - a DIFFERENT trigger from last-bullet, and since every shot on a
charge weapon is a full charge it is `per_shot_rules`' plain "every 1" mode (see
`build_fire_away_per_shot_rules`), which means it collects the Full Burst bonus
on whichever of her shots land inside a window.

Signature only - "Aegis Cannon" additionally grants herself Charge Damage
Multiplier +158.4% for 10 ROUNDS - a bullet-count duration, not seconds, so it
uses `round_buff_rule(shots=10)` (the Zwei/Miranda precedent).

Frontline Command's crit rate reads "Critical Rate of normal attack", so it
rides the `normal_attack_crit_rate` bucket. As plain `crit_rate` it used to
raise every burst nuke in the squad along with the normal attacks it names.

Signature only - "Frontline Command" also fills the squad's Burst Gauge by
14.31% on every Full Charge attack, via `build_frontline_command_gauge_fills`
and `burst_gauge.fill_times`'s `every_own_full_charge` trigger. Her SR fires a
full charge roughly every 1.4 sec, so this is one seventh of the gauge on a
fast cadence - the base build has no such bullet.

Not modeled / deferred (both builds): Frontline Command's full-charge Max-HP
recovery (survivability, not a damage concept) and Aegis Cannon's
damage-proportional heal-over-time.
"""
from app.effects import Effect
from app.skill_rules._helpers import (
    instant_nuke_pulse_rule,
    refreshing_buff_rule,
    round_buff_rule,
)
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "helm": {
        "source": "dotgg",
        "test_module": "test_skill_rules_helm",
        "keys": {
            "frontline_command": ("skills", 0),
            "fire_away": ("skills", 1),
            "aegis_cannon": ("skills", 2),
        },
        "fixtures": {
            "frontline_command": "FRONTLINE_COMMAND_VALUES",
            "fire_away": "FIRE_AWAY_VALUES",
            "aegis_cannon": "AEGIS_CANNON_VALUES",
        },
    },
    "helm-signature": {
        "source": "dotgg",
        "data_slug": "helm",
        "test_module": "test_skill_rules_helm",
        "keys": {
            "frontline_command": ("dollskills", 0),
            "fire_away": ("dollskills", 1),
            "aegis_cannon": ("dollskills", 2),
        },
        "fixtures": {
            "frontline_command": "FRONTLINE_COMMAND_SIG",
            "fire_away": "FIRE_AWAY_SIG",
            "aegis_cannon": "AEGIS_CANNON_SIG",
        },
    },
}


def build_frontline_command_per_shot_rules(values: dict) -> list:
    crit_rate_up = float(values["description_value_01"]) / 100
    duration = float(values["description_value_02"])
    return [(None, "last_bullet", [
        # "Critical Rate of normal attack" - the normal-attack-only bucket, so
        # it no longer inflates the squad's burst nukes as plain crit_rate did.
        refreshing_buff_rule("per_shot",
                             [("normal_attack_crit_rate", crit_rate_up, "squad", duration)])
    ])]


def build_frontline_command_gauge_fills(values: dict, slug: str) -> list[dict]:
    """Frontline Command's "Activates when attacking with Full Charge ... Fills
    Burst Gauge by X%" - the squad's gauge, once per full-charge shot SHE fires.

    Favorite Item only: the base array's Frontline Command text stops after the
    crit-rate line and has no gauge bullet at all, so the slug is passed in
    rather than assumed - the fill is keyed to the seat whose shots trigger it
    (`burst_gauge.fill_times`'s `every_own_full_charge`).
    """
    return [{"every_own_full_charge": slug,
             "fraction": float(values["description_value_04"]) / 100}]


def build_fire_away_rules(values: dict) -> list[SkillRule]:
    # "저지 부위 공격 대미지" = Damage to Interruption Parts: the zone a gimmick
    # makes you hit, NOT a destructible part. See test_parts_vs_interruption_parts.
    interruption_parts_up = float(values["description_value_01"]) / 100
    attack_damage_up = float(values["description_value_02"]) / 100
    attack_damage_duration = float(values["description_value_03"])

    def grant_damage_to_parts(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "Fire Away Granted"):
            return
        context.set_status(caster_slug, "Fire Away Granted")
        registry.add(
            Effect("damage_to_interruption_parts_up", interruption_parts_up,
                   "squad", None, caster_slug),
            applied_at=time,
        )

    def grant_attack_damage_up(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", attack_damage_up, "squad", attack_damage_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="battle_start", action=grant_damage_to_parts),
        SkillRule(trigger="full_burst_enter", action=grant_attack_damage_up),
    ]


def build_fire_away_per_shot_rules(values: dict) -> list:
    """Fire Away's "on Full Charge hit" bonus: every SR shot is a full charge,
    so this is the plain "every 1" per-shot mode."""
    nuke_percent = float(values["description_value_04"])
    return [(1, "every", [
        instant_nuke_pulse_rule("per_shot", nuke_percent)
    ])]


def build_aegis_cannon_rules(values: dict) -> list[SkillRule]:
    """Aegis Cannon's self Charge Damage Multiplier. "for N round(s)" is a
    bullet-count duration - her next `shots` normal attacks - not seconds."""
    charge_damage = float(values["description_value_04"]) / 100
    rounds = int(float(values["description_value_05"]))
    return [
        round_buff_rule(
            "own_burst_activate",
            [("charge_damage_bonus", charge_damage, "self")],
            shots=rounds,
        )
    ]


def aegis_cannon_burst_percent(values: dict) -> float:
    return float(values["description_value_01"])
