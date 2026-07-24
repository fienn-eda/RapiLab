"""Rosanna's Favorite Item (애장품) build, slug "rosanna-signature" - a SEPARATE
roster entry from base Rosanna (slug "rosanna"), per the dual-slot convention
(2026-07-12). NOT related to `rosanna-chic-ocean`, a different unit entirely.

The Favorite Item's value is that it gives her kit triggers the engine can
actually fire: a permanent elemental buff, a shot-counted Frenzy source (the
base build's only Frenzy trigger is an ally being downed, which never happens),
and a boss-element-gated damage-taken debuff for the whole squad.

Weapon stats come from base Rosanna's ShiftyPad file via the manifest's
`weapon_source`, since ShiftyPad exposes no dollskills and dotgg is dead.

Modeled (DPS-relevant):
- On the Lam (dollskills[0]): self Elemental Advantage Attack Damage +20%,
  permanent. The text gates it on "when the stage target appears", which a raid
  always satisfies (the documented always-on-in-raid convention). Note this is
  advantage-GATED: it only pays out when she already holds elemental advantage
  over the boss.
- On the Lam (dollskills[0]): self Critical Rate +19.34% for 3 sec every 120
  normal attacks, as in the base build.
- Capo dei Capi (dollskills[1]): Frenzy, self ATK +22.61% for 30 sec, every 500
  normal attacks on the stage target. At the engine's MG rate (60 shots/sec, 300
  rounds, 1.67s reload) 500 shots take ~11.1 sec of wall clock, so about 2-3
  instances overlap at steady state. The engine produces that real count; the
  skill text's 10-stack cap is NOT reachable from this source alone (it assumes
  the ally-incapacitation source too), so no cap is imposed here.
- Vendetta (dollskills[2], her burst, cd 40): 1310.4% plus the always-on
  Concealment rider's 561.6%, identical to the base build - see `rosanna.py`
  for why the rider is folded in rather than gated.
- Vendetta (dollskills[2]): Damage Taken +29% for 30 sec when the boss is Water
  Code, via `boss_is_element("Water")`. Modeled as squad scope because a
  damage-taken debuff sits on the enemy and every attacker benefits.

Not modeled / deferred:
- Frenzy's original "when a Nikke is incapacitated" trigger, and the Favorite
  Item's 400% nuke on that same trigger - the sim never downs an ally.
- The Burst Gauge fill (36.54%) - gauge charge time is a fixed sim input.
- Concealment's untargetability and the enemy buff-strip - no engine concept.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import boss_is_element


SKILL_VALUE_MANIFESTS = {
    "rosanna-signature": {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "rosanna",
        "test_module": "test_skill_rules_rosanna_signature",
        "keys": {
            "on_the_lam": ("dollskills", 0),
            "capo_dei_capi": ("dollskills", 1),
            "vendetta": ("dollskills", 2),
        },
    },
}


def vendetta_signature_burst_percent(values):
    vendetta = values["vendetta"]
    return float(vendetta["description_value_02"]) + float(vendetta["description_value_03"])


def build_rosanna_signature_rules(values):
    lam = values["on_the_lam"]
    vendetta = values["vendetta"]
    elemental = float(lam["description_value_08"]) / 100
    damage_taken = float(vendetta["description_value_04"]) / 100
    damage_taken_duration = float(vendetta["description_value_05"])
    return [
        buff_rule("battle_start", [
            ("other_elemental_bonus", elemental, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("damage_taken_up", damage_taken, "squad", damage_taken_duration),
        ], condition=boss_is_element("Water")),
    ]


def build_rosanna_signature_per_shot_rules(values):
    lam = values["on_the_lam"]
    capo = values["capo_dei_capi"]
    crit_shots = int(float(lam["description_value_01"]))
    crit_rate = float(lam["description_value_03"]) / 100
    crit_duration = float(lam["description_value_04"])
    frenzy_shots = int(float(capo["description_value_08"]))
    frenzy_atk = float(capo["description_value_09"]) / 100
    frenzy_duration = float(capo["description_value_11"])
    return [
        (crit_shots, "every", [
            buff_rule("per_shot", [("crit_rate", crit_rate, "self", crit_duration)]),
        ]),
        (frenzy_shots, "every", [
            buff_rule("per_shot", [("atk_percent", frenzy_atk, "self", frenzy_duration)]),
        ]),
    ]
