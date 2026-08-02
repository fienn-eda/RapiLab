"""Soline: Frost Ticket (slug "soline-frost-ticket"), a Burst-1 SG supporter.
Base skills (no signature).

Modeled (DPS-relevant):
- I'll Check Your Ticket! (skills[0]): squad burst-cooldown reduction on Full
  Burst enter, and the ticket grant - squad Max HP +10% of her own PER ticket,
  continuous. Tickets are issued at battle start and on each of her bursts,
  capped at 2, so the squad holds one until her first burst and the cap after.

  The only thing that spends a ticket is I'll Help You Board the Train!, which
  fires when someone in the squad drops below 15% HP; the sim never damages
  allies, so tickets are never consumed and the count only climbs.

  Max HP is not survivability bookkeeping here - `flat_max_hp` feeds every
  "ATK ▲ X% of Max HP" conversion in the deck (Maiden, Cinderella, Maxwell,
  Laplace: Ultimate Hero), so a deck holding one of those gains real damage
  from her tickets.

Not modeled:
- Her heals (HP-threshold and burst) and First Train Discount, whose whole
  function is to stop a heal from spending a ticket - with no heals fired there
  is nothing for it to suppress.
"""
from app.effects import Effect
from app.skill_rules._helpers import cdr_pulse_rule
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "soline-frost-ticket": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "check_ticket": ("skills", 0),
        },
    },
}


def build_soline_frost_ticket_rules(values):
    check = values["check_ticket"]
    cdr_sec = float(check["description_value_03"])
    per_ticket_max_hp = values["caster_max_hp"] * float(check["description_value_01"]) / 100
    ticket_cap = int(float(check["description_value_02"]))

    def issue_ticket(context, caster_slug, time, registry):
        """One ticket at battle start, one per own burst, up to the cap. Each is
        its own permanent effect, so the squad's total IS the ticket count."""
        issued = (context.activation_count(caster_slug, "battle_start")
                  + context.activation_count(caster_slug, "own_burst_activate"))
        if issued > ticket_cap:
            return
        registry.add(
            Effect("flat_max_hp", per_ticket_max_hp, "squad", None, caster_slug),
            applied_at=time,
        )

    return [
        cdr_pulse_rule("full_burst_enter", cdr_sec),
        SkillRule(trigger="battle_start", action=issue_ticket),
        SkillRule(trigger="own_burst_activate", action=issue_ticket),
    ]
