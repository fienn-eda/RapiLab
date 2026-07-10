"""Velvet (slug "velvet"), a Burst-2 Wind SR supporter. Collected from
lootandwaifus.com. Designed as an off-burst sub-DPS (per lootandwaifus's own
notes) whose kit is almost entirely self-focused and gated on mechanics the
engine can't represent yet.

Modeled (DPS-relevant):
- Perfect Execution (skills[2], her burst, cd=20): self Attack Damage ▲34.52%
  for 10 sec. No burst nuke (buff-only burst; the weapon-transformation part
  of the same bullet is deferred, see below).

Not modeled - all deferred bullets are self-scoped (she does not buff the
squad anywhere in her kit):
- Perfect Execution's own weapon-transformation damage (7% of final ATK per
  shot for 10 sec) - no weapon-transformation support (same gap as Nayuta's
  Memory Incineration).
- Sticky Fingers (skills[0]) entirely - an "ammo pouch" resource mechanic (not
  modeled: removing enemy ammo, filling/spending her own pouch) gating a self
  ATK/Attack Damage buff on her own full-charge-shot while not in Full Burst -
  the same missing "own full-charge-shot" trigger seen on Mint/Prika.
- Bullets of Love (skills[1]) entirely - both bullets need triggers that don't
  exist (own full-charge-shot during Full Burst; 50 normal attacks during Full
  Burst), gating a squad ATK/Charge Damage buff and a sizeable self nuke
  (400.92% of final ATK at max level) - likely a meaningful chunk of her real
  DPS, worth flagging even though it's the already-catalogued gap, not a new
  one.
"""
from app.effects import Effect
from app.squad_engine import SkillRule


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
