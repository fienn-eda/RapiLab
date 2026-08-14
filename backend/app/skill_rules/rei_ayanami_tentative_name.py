"""Rei Ayanami (Tentative Name) (slug "rei-ayanami-tentative-name"), a Burst-3
Wind AR attacker. A DISTINCT unit from Rei Ayanami (`rei-ayanami`, a Fire MG) -
not a signature variant. Base skills (no signature/Treasure). Collected from
lootandwaifus.com.

Modeled (DPS-relevant):
- Attack State (skills[2], her burst): self Attack Damage +35.9% and self flat
  ATK = 63.36% of the caster's ATK, both for 10 sec, plus the burst nuke, 990.2%
  of final ATK (`attack_state_burst_percent`). Attack State itself lasts 10 sec
  from her burst - the window the per-shot nuke below is gated to.
- Maintenance and Resupply (skills[1]): on entering Full Burst, all allies gain
  flat ATK = 11.61% of the caster's ATK for 10 sec (squad scope).
- Maintenance and Resupply's second bullet: on Full Burst entry, allies holding
  a Machine Gun who have already used their Burst Skill get MG heating up speed
  +100% for 13 sec - halving the 2.28-sec warm-up every one of their magazines
  pays (docs/measurements/mg-spinup.md).
- Annihilation Support (skills[0]) Attack-State clause: every 7 normal attacks
  while in Attack State (her own 10s burst window, gap #7's
  `every_during_own_status_window`), a 286.37%-of-final-ATK nuke. "As additional
  damage", so Full-Burst-Bonus eligible (and it lands inside her burst's Full
  Burst). See `build_annihilation_support_per_shot_rules`.

Not modeled / deferred:
- Annihilation Support's main payload (skills[0]): "after 18 normal attacks
  against a target in Anti A.T. Field status, deal 590.64% as additional damage
  (+10 Anti A.T. Field stacks)". Anti A.T. Field is a target/boss status applied
  by other Evangelion-collab units - a cross-unit target-status the engine
  doesn't model. This is her signature collab-synergy damage.
- Annihilation Support's Full-Burst clause for "allies in Annihilation State"
  (units-affected +1, attack range +500%, ATK +17.6% of caster ATK) - gated on
  the Annihilation State ally status, also cross-unit and unmodeled.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, member_subset_buff_rule


SKILL_VALUE_MANIFESTS = {
    "rei-ayanami-tentative-name": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rei_ayanami_tentative_name",
        "keys": {
            "annihilation_support": ("skills", 0),
            "maintenance_and_resupply": ("skills", 1),
            "attack_state": ("skills", 2),
        },
    },
}


ATTACK_STATE_WINDOW = 10.0  # Attack State (skills[2]) lasts 10 sec from her burst


def attack_state_burst_percent(values):
    return float(values["attack_state"]["description_value_05"])


def build_rei_tentative_rules(values):
    maintenance = values["maintenance_and_resupply"]
    attack_state = values["attack_state"]
    caster_atk = values["caster_atk"]

    self_attack_damage = float(attack_state["description_value_01"]) / 100
    self_attack_damage_duration = float(attack_state["description_value_02"])
    self_atk = float(attack_state["description_value_03"]) / 100 * caster_atk
    self_atk_duration = float(attack_state["description_value_04"])
    squad_atk = float(maintenance["description_value_03"]) / 100 * caster_atk
    squad_atk_duration = float(maintenance["description_value_04"])
    heating_speed = float(maintenance["description_value_01"]) / 100
    heating_duration = float(maintenance["description_value_02"])

    return [
        buff_rule("own_burst_activate", [
            ("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration),
            ("flat_atk", self_atk, "self", self_atk_duration),
        ]),
        buff_rule("full_burst_enter", [("flat_atk", squad_atk, "squad", squad_atk_duration)]),
        # "Affects all allies with a Machine Gun who have used their Burst
        # Skills" - the narrow subset Effect.scope can't express, resolved live
        # so the "already burst" half is read at the trigger's own moment.
        member_subset_buff_rule(
            "full_burst_enter",
            lambda member, context: (
                member.weapon == "MG"
                and member.slug in context.burst_used_this_cycle),
            [("mg_heating_speed_percent", heating_speed, heating_duration)],
        ),
    ]


def build_annihilation_support_per_shot_rules(values):
    """gap #7: every 7 normal attacks while in Attack State (her own 10s burst
    window) a 286.37%-of-final-ATK "additional damage" nuke. The Anti A.T. Field
    payload on the same skill is deferred (cross-unit target status)."""
    annihilation = values["annihilation_support"]
    threshold = int(float(annihilation["description_value_04"]))
    nuke_percent = float(annihilation["description_value_05"])
    return [(
        (threshold, ATTACK_STATE_WINDOW),
        "every_during_own_status_window",
        [instant_nuke_pulse_rule("per_shot", nuke_percent)],
    )]
