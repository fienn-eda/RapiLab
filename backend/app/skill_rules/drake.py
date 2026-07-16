"""Drake (slug "drake") and her signature-weapon build (slug "drake-signature"),
a Burst-3 Fire SG attacker. Collected from api.dotgg.gg. The two builds are
separate deck candidates (dual-slug, like julia/julia-signature); the signature
build has higher numbers and an extra shotgun-ally buff plus a second Thunderbolt
trigger.

Modeled (DPS-relevant):
- Overcharge (skills[0], on entering Full Burst): all allies ATK +11.85% for 10
  sec (squad). Signature adds, for all Shotgun allies (squad approx - no
  weapon-type scope), ATK +63.88% and Max Ammunition +50.14% for 10 sec.
- Thunderbolt (skills[1]): after every 10 normal attacks, a 98.55%-of-final-ATK
  nuke (gap #1 `every`). Signature adds a second trigger: after every 5 normal
  attacks, a 201.6% nuke. "3 / 1 enemies with lowest HP" collapses to the single
  raid boss. "As damage" (not "additional"), so NOT Full-Burst-Bonus eligible.
- Drake Special (skills[2], her burst): burst nuke (base 1254%, signature 3009.6%
  of final ATK) plus self Max Ammunition +72.18% for 10 sec. Signature also
  grants self Attack Damage +31.68% for 10 sec.

Not modeled / deferred:
- Overcharge's Hit Rate buff (+11.85% base / +20.09% signature) - Hit Rate is not
  consumed by the engine (like Attack Speed), so it's inert.
- The shotgun-ally ("all allies with a Shotgun") scope is approximated as squad,
  over-applying the +63.88% ATK / +50.14% Max Ammo to non-shotgun allies (small,
  per the documented weapon-type-scope approximation).
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

SKILL_VALUE_MANIFESTS = {
    "drake": {
        "source": "dotgg",
        "test_module": "test_skill_rules_drake",
        "keys": {
            "overcharge": ("skills", 0),
            "thunderbolt": ("skills", 1),
            "drake_special": ("skills", 2),
        },
    },
    "drake-signature": {
        "source": "dotgg",
        "data_slug": "drake",
        "test_module": "test_skill_rules_drake",
        "keys": {
            "overcharge": ("dollskills", 0),
            "thunderbolt": ("dollskills", 1),
            "drake_special": ("dollskills", 2),
        },
        "fixtures": {
            "overcharge": "OVERCHARGE_SIG",
            "thunderbolt": "THUNDERBOLT_SIG",
            "drake_special": "DRAKE_SPECIAL_SIG",
        },
    },
}


def drake_special_burst_percent(values):
    return float(values["drake_special"]["description_value_01"])


def drake_signature_burst_percent(values):
    return float(values["drake_special"]["description_value_01"])


def build_drake_rules(values):
    overcharge = values["overcharge"]
    drake_special = values["drake_special"]

    squad_atk = float(overcharge["description_value_03"]) / 100
    squad_atk_duration = float(overcharge["description_value_04"])
    self_max_ammo = float(drake_special["description_value_02"]) / 100
    self_max_ammo_duration = float(drake_special["description_value_03"])

    return [
        buff_rule("full_burst_enter", [("atk_percent", squad_atk, "squad", squad_atk_duration)]),
        buff_rule("own_burst_activate", [("max_ammo_percent", self_max_ammo, "self", self_max_ammo_duration)]),
    ]


def build_drake_signature_rules(values):
    overcharge = values["overcharge"]
    drake_special = values["drake_special"]

    squad_atk = float(overcharge["description_value_03"]) / 100
    squad_atk_duration = float(overcharge["description_value_04"])
    sg_atk = float(overcharge["description_value_05"]) / 100
    sg_atk_duration = float(overcharge["description_value_06"])
    sg_max_ammo = float(overcharge["description_value_07"]) / 100
    sg_max_ammo_duration = float(overcharge["description_value_08"])
    self_max_ammo = float(drake_special["description_value_02"]) / 100
    self_max_ammo_duration = float(drake_special["description_value_03"])
    self_attack_damage = float(drake_special["description_value_04"]) / 100
    self_attack_damage_duration = float(drake_special["description_value_05"])

    return [
        buff_rule("full_burst_enter", [
            ("atk_percent", squad_atk, "squad", squad_atk_duration),
            ("atk_percent", sg_atk, "squad", sg_atk_duration),                # SG allies, squad approx
            ("max_ammo_percent", sg_max_ammo, "squad", sg_max_ammo_duration),  # SG allies, squad approx
        ]),
        buff_rule("own_burst_activate", [
            ("max_ammo_percent", self_max_ammo, "self", self_max_ammo_duration),
            ("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration),
        ]),
    ]


def build_thunderbolt_per_shot_rules(values):
    """gap #1: a 98.55% nuke every 10 normal attacks."""
    thunderbolt = values["thunderbolt"]
    threshold = int(float(thunderbolt["description_value_01"]))
    nuke_percent = float(thunderbolt["description_value_03"])
    return [(threshold, "every", [instant_nuke_pulse_rule("per_shot", nuke_percent)])]


def build_thunderbolt_signature_per_shot_rules(values):
    """gap #1: the base 98.55%/10-normals nuke plus the signature's second
    trigger, a 201.6% nuke every 5 normal attacks."""
    thunderbolt = values["thunderbolt"]
    threshold_1 = int(float(thunderbolt["description_value_01"]))
    nuke_1 = float(thunderbolt["description_value_03"])
    threshold_2 = int(float(thunderbolt["description_value_04"]))
    nuke_2 = float(thunderbolt["description_value_06"])
    return [
        (threshold_1, "every", [instant_nuke_pulse_rule("per_shot", nuke_1)]),
        (threshold_2, "every", [instant_nuke_pulse_rule("per_shot", nuke_2)]),
    ]
