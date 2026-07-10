"""Prika (slug "prika"), a Burst-2 Water SR supporter. Base skills - collected
from lootandwaifus.com (Prika is not on dotgg).

Prika's kit is built around a two-unit combo with Mint (Fienn's intended
rotation: Prika bursts FIRST to grant Performance, then Mint bursts repeatedly;
each Mint Sing Along re-triggers Prika's Encore, so Prika's buffs persist and
Mint stays permanently Singing without Prika bursting again).

Modeled (DPS-relevant):
- Get Ready for an Amazing Show! (skills[2], her burst, cd=40): squad Charge
  Damage, and Prika enters Performance status (the flag Encore gates on). The
  Charge Damage lasts 25 sec solo, but is applied as PERMANENT when Mint is in
  the deck: Encore extends Performance's duration every Mint burst, so in the
  intended rotation it never drops. (Re-adding it on each Encore would instead
  double-count during the overlap window, since same-stat effects sum.) Her
  Performance self HP-recovery bullet is survivability, not modeled.
- One More Song! (skills[1]) Encore: fires on Mint's burst while Prika is in
  Performance status - the `ally_burst_activate` cross-unit trigger. It grants
  squad Attack Damage for 10 sec and sets the Sing Along initiator's (Mint's)
  Singing status so Mint's Singing-only buffs stay on (see mint.py). The
  "Performance duration +21 sec" it also grants is what keeps the burst's Charge
  Damage alive - captured by that buff being permanent (above), not re-added here.
- Let's Get the Show Started! (skills[0]): on every Full Charge attack, squad
  Projectile Explosion Damage, Pierce Damage, and ATK % of Prika's ATK for 3 sec
  - via the per-shot trigger (`per_shot_rules`). Prika is an SR (charge weapon),
  so every shot is a full charge.

Not modeled:
- Encore's Performance-duration +21 sec and self Burst-cooldown +21 sec: rotation
  bookkeeping, not squad DPS. The Charge Damage refresh already captures the
  outcome (Performance is maintained while Mint keeps bursting).
- One More Song!'s Full-Burst self Max HP and Let's Get the Show Started!'s
  Performance-only self healing/Pierce: survivability.
- Standalone (no Mint) Encore never fires - which is correct: without Mint there
  is no Sing Along to trigger it. Prika solo is then just her burst Charge Damage
  plus her full-charge squad buffs.
"""
from app.effects import Effect
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule, all_conditions, ally_bursted, deck_contains, has_status

PERFORMANCE_STATUS = "performance"
SINGING_STATUS = "singing"  # set on Mint; read by mint.py's Singing gate
SING_ALONG_SOURCE = "mint"  # only Mint's burst grants Sing Along, which triggers Encore


def build_prika_rules(values):
    show = values["get_ready_for_an_amazing_show"]
    encore = values["one_more_song"]

    charge_damage = float(show["description_value_03"]) / 100
    charge_damage_duration = float(show["description_value_04"])
    encore_attack_damage = float(encore["description_value_04"]) / 100
    encore_attack_damage_duration = float(encore["description_value_05"])

    def apply_burst(context, caster_slug, time, registry):
        # With Mint present, Encore keeps extending Performance, so the Charge
        # Damage is maintained the whole fight - modeled as permanent. Solo, it
        # lasts its stated 25 sec.
        duration = None if deck_contains(SING_ALONG_SOURCE)(context, caster_slug) else charge_damage_duration
        registry.add(
            Effect("charge_damage_bonus", charge_damage, "squad", duration, caster_slug),
            applied_at=time,
        )
        context.set_status(caster_slug, PERFORMANCE_STATUS)

    def apply_encore(context, caster_slug, time, registry):
        registry.add(
            Effect(
                "attack_damage_up", encore_attack_damage, "squad",
                encore_attack_damage_duration, caster_slug,
            ),
            applied_at=time,
        )
        # Effect 1: the Sing Along initiator (Mint) gains Singing, continuously.
        context.set_status(context.last_burst_slug, SINGING_STATUS)

    return [
        SkillRule(trigger="own_burst_activate", action=apply_burst),
        SkillRule(
            trigger="ally_burst_activate",
            condition=all_conditions(ally_bursted(SING_ALONG_SOURCE), has_status(PERFORMANCE_STATUS)),
            action=apply_encore,
        ),
    ]


def build_lets_get_show_started_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): on every Full
    Charge attack (Prika is an SR, every shot is a full charge), squad Projectile
    Explosion Damage, Pierce Damage, and ATK % of Prika's ATK, each for 3 sec.
    The Performance-only self healing/Pierce is survivability, not modeled."""
    projectile_explosion = float(values["description_value_01"]) / 100
    projectile_explosion_duration = float(values["description_value_02"])
    pierce = float(values["description_value_03"]) / 100
    pierce_duration = float(values["description_value_04"])
    ally_atk = float(values["description_value_05"]) / 100 * values["caster_atk"]
    ally_atk_duration = float(values["description_value_06"])

    return [(1, "every", [buff_rule("per_shot", [
        ("projectile_explosion_damage_up", projectile_explosion, "squad", projectile_explosion_duration),
        ("pierce_damage_up", pierce, "squad", pierce_duration),
        ("flat_atk", ally_atk, "squad", ally_atk_duration),
    ])])]
