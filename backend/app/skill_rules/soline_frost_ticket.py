"""Soline: Frost Ticket (slug "soline-frost-ticket"), a Burst-1 SG supporter.
Base skills (no signature).

Modeled (DPS-relevant):
- I'll Check Your Ticket! (skills[0]): squad burst-cooldown reduction on Full
  Burst enter.

Everything else she does (ticket-based Max HP grants, HP-threshold heals, her
burst's squad heal) is survivability with no effect on damage output, so it
isn't modeled. Her value to a raid deck is purely as a burst-rotation enabler.
"""
from app.skill_rules._helpers import cdr_pulse_rule

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
    return [cdr_pulse_rule("full_burst_enter", cdr_sec)]
