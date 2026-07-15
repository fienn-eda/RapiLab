"""Velvet (slug "velvet"), a Burst-2 Wind SR supporter. Collected from
lootandwaifus.com. Designed as an off-burst sub-DPS (per lootandwaifus's own
notes) whose kit is almost entirely self-focused and gated on mechanics the
engine can't represent yet.

Modeled (DPS-relevant):
- Perfect Execution (skills[2], her burst, cd=20): self Attack Damage ▲34.52%
  for 10 sec. No burst nuke (buff-only burst; the weapon-transformation part
  of the same bullet is deferred, see below).
- Bullets of Love (skills[1]) - her real squad support, gated on Full Burst
  (gap #7's `every_during_full_burst`; see `build_bullets_of_love_per_shot_rules`):
  - On each Full-Charge shot during Full Burst (SR: every shot is a full charge,
    so N=1 in-window): squad flat ATK = 25.2% of her own ATK and squad Charge
    Damage +100.8%, both for 3 sec (refreshing). Charge Damage is squad-scoped
    per the Prika precedent (the engine applies charge_damage_bonus squad-wide;
    charge-weapon allies are the real beneficiaries).
  - After 50 normal attacks during Full Burst: self Attack Damage +15.03% for
    5 sec and a 400.92%-of-final-ATK nuke ("as additional damage", so
    full_burst_bonus_eligible - and it always lands inside Full Burst).
  The "ammo pouch" the skill spends from (6000 rounds, refilled to full at
  battle start and every Burst Stage 2) far exceeds per-cycle spend, so it never
  depletes and is treated as a non-constraint (not modeled as a resource).

Not modeled / deferred:
- Perfect Execution's own weapon-transformation damage (7% of final ATK per
  shot for 10 sec) - no weapon-transformation support (same gap as Nayuta's
  Memory Incineration).
- Sticky Fingers (skills[0])'s Full-Charge self ATK/Attack Damage buff (+30.5%
  each, 3 sec) fires "while NOT in Full Burst" - needs a not-in-Full-Burst
  per-shot window filter (the complement of gap #7's FB-window mode), which
  isn't built. Self-scoped on a supporter, low DPS weight. Its enemy-ammo-steal
  and ammo-pouch fill are non-damage.
"""
from app.effects import Effect
from app.skill_rules._helpers import instant_nuke_pulse_rule, refreshing_buff_rule
from app.squad_engine import SkillRule

BULLETS_OF_LOVE_NUKE_SHOT_COUNT = 50  # "after landing 50 normal attacks during Full Burst"


def build_velvet_rules(values):
    execution = values["perfect_execution"]

    self_attack_damage = float(execution["description_value_03"]) / 100
    self_attack_damage_duration = float(execution["description_value_04"])

    def apply_burst(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="own_burst_activate", action=apply_burst)]


def build_bullets_of_love_per_shot_rules(values):
    """gap #7 (`every_during_full_burst`): her two Full-Burst-gated bullets. The
    Full-Charge squad buff fires on every in-Full-Burst shot (N=1, SR = every
    shot is a full charge); the 50-normal bullet fires a self buff + nuke."""
    bullets = values["bullets_of_love"]
    caster_atk = values["caster_atk"]
    squad_atk = float(bullets["description_value_02"]) / 100 * caster_atk
    squad_atk_duration = float(bullets["description_value_03"])
    charge_damage = float(bullets["description_value_04"]) / 100
    charge_damage_duration = float(bullets["description_value_05"])
    self_attack_damage = float(bullets["description_value_08"]) / 100
    self_attack_damage_duration = float(bullets["description_value_09"])
    nuke_percent = float(bullets["description_value_10"])

    return [
        (1, "every_during_full_burst", [
            refreshing_buff_rule("per_shot", [
                ("flat_atk", squad_atk, "squad", squad_atk_duration),
                ("charge_damage_bonus", charge_damage, "squad", charge_damage_duration),
            ]),
        ]),
        (BULLETS_OF_LOVE_NUKE_SHOT_COUNT, "every_during_full_burst", [
            refreshing_buff_rule("per_shot", [
                ("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration),
            ]),
            instant_nuke_pulse_rule("per_shot", nuke_percent, full_burst_bonus_eligible=True),
        ]),
    ]
