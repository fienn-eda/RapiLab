"""Prika (slug "prika"), a Burst-2 Water SR supporter. Base skills - not on
dotgg (too recent), collected from lootandwaifus.com.

Modeled (DPS-relevant):
- Get Ready for an Amazing Show! (skills[2], her burst, cd=40): squad Charge
  Damage for 25 sec. No enemy nuke (buff-only burst; her self HP-recovery
  bullet in the same skill is not modeled - survivability).

Not modeled - both are real engine gaps, not simplifications, and per
lootandwaifus's own strategy notes ("always used with Mint... she needs to
ALWAYS burst first, then you switch to bursting with Mint forever") these two
ARE most of her actual kit, so this encoding is intentionally thin - flag to
Fienn before trusting a Prika-inclusive deck evaluation:
- Let's Get the Show Started! (skills[0]) entirely - all three of its squad
  buffs (Projectile Explosion Damage, Pierce Damage, ATK % of caster's ATK)
  trigger "when performing a Full Charge attack" - the same missing "own
  full-charge-shot" trigger that also blocks Mint's Here I Go! (normal-attack
  shots are generated in a separate pass in raid_simulator, not routed through
  fire_trigger).
- One More Song! (skills[1])'s Encore Function bullet - activates "when Sing
  Along takes effect [Mint's burst buff bundle, see mint.py] while Prika is in
  Performance status [her own burst's buff window]". This needs a
  cross-character trigger: Prika's rule would have to fire off ANOTHER
  Nikke's (specifically Mint's) own_burst_activate, not her own - the engine's
  own_burst_activate dispatch is scoped to the firing slug's own rules only
  (see raid_simulator.on_tier_fire), so there's no way for Prika's rules to
  observe Mint bursting. This is a bigger architecture gap than the
  deck_contains-style conditions used elsewhere (e.g. Blanc/Rouge, Mast/
  Anchor), which only check static deck membership, not react to a specific
  ally's trigger firing. skills[1]'s other bullet (self Max HP) is
  survivability, not modeled regardless.
"""
from app.effects import Effect
from app.squad_engine import SkillRule


def build_prika_rules(values):
    show = values["get_ready_for_an_amazing_show"]

    charge_damage = float(show["description_value_03"]) / 100
    charge_damage_duration = float(show["description_value_04"])

    def apply_burst(context, caster_slug, time, registry):
        registry.add(
            Effect("charge_damage_bonus", charge_damage, "squad", charge_damage_duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="own_burst_activate", action=apply_burst)]
