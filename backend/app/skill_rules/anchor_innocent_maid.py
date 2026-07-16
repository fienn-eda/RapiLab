"""Anchor: Innocent Maid (slug "anchor-innocent-maid"), a Burst-2 Water RL
supporter. Base skills (no signature weapon).

Modeled (DPS-relevant):
- Starfish (Shaped) Omurice (skills[0]): escalating on Full Burst enter -
  Once: Potency of HP (survivability, not modeled); Twice: squad Distributed
  Damage ▲ (a real DPS synergy buff for Distributed-Damage dealers such as
  Scarlet: Black Shadow - see references/special-mechanics.md); Three times:
  debuff stack count ▼1, which is what lets Mast: Romantic Maid hold her Drunken
  stacks at 3 (handled on Mast's side via deck_contains, not emitted here).
- Sea Anemone (Shaped) Pasta (skills[1]): escalating on Full Burst end -
  Once: Hit Rate (accuracy, not modeled); Twice: squad ATK % of caster's ATK;
  Three times: squad Reloading Speed.
- Seaside Stroll (skills[2], her burst): squad ATK % of caster's ATK on her
  own burst (the storage/heal parts are survivability, not modeled).

The Distributed Damage buff uses `distributed_damage_up`, which raid_simulator
does not consume yet (and would need per-unit gating so only Distributed-Damage
units benefit) - so it is currently inert, but encoded faithfully so it starts
counting once a Distributed-Damage dealer is encoded and the stat is wired.

Anchor also heals (Starfish + Seaside Stroll); healing is tracked separately
(has-heal flag), not as a damage effect.
"""
from app.skill_rules._helpers import buff_rule, escalating_buff_rule

SKILL_VALUE_MANIFESTS = {
    "anchor-innocent-maid": {
        "source": "dotgg",
        "test_module": "test_skill_rules_anchor",
        "keys": {
            "starfish_omurice": ("skills", 0),
            "sea_anemone_pasta": ("skills", 1),
            "seaside_stroll": ("skills", 2),
        },
    },
}


def build_anchor_rules(values):
    starfish = values["starfish_omurice"]
    pasta = values["sea_anemone_pasta"]
    stroll = values["seaside_stroll"]
    caster_atk = values["caster_atk"]

    starfish_distributed = float(starfish["description_value_03"]) / 100
    starfish_distributed_duration = float(starfish["description_value_04"])
    pasta_atk = float(pasta["description_value_03"]) / 100 * caster_atk
    pasta_atk_duration = float(pasta["description_value_04"])
    pasta_reload = float(pasta["description_value_05"]) / 100
    pasta_reload_duration = float(pasta["description_value_06"])
    stroll_atk = float(stroll["description_value_04"]) / 100 * caster_atk
    stroll_atk_duration = float(stroll["description_value_05"])

    return [
        escalating_buff_rule("full_burst_enter", [
            [],  # Once: Potency of HP - survivability, not modeled
            # Twice: Distributed Damage ▲ (currently inert; see module docstring)
            [("distributed_damage_up", starfish_distributed, "squad", starfish_distributed_duration)],
            [],  # Three times: debuff stack ▼1 - enables Mast's stacks (handled in Mast)
        ]),
        escalating_buff_rule("full_burst_end", [
            [],  # Once: Hit Rate - accuracy, not modeled
            [("flat_atk", pasta_atk, "squad", pasta_atk_duration)],           # Twice
            [("reload_speed_percent", pasta_reload, "squad", pasta_reload_duration)],  # Three times
        ]),
        buff_rule("own_burst_activate", [
            ("flat_atk", stroll_atk, "squad", stroll_atk_duration),
        ]),
    ]
