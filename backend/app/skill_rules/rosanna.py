"""Rosanna (slug "rosanna"), a Burst-1 Electric MG Attacker. NOT the same unit as
`rosanna-chic-ocean` (Water SG, Burst 3), which is separately encoded.

Her kit is thin in engine terms: one self crit buff on a shot counter, and a
burst that carries essentially all of her damage.

Modeled (DPS-relevant):
- On the Lam (skills[0]): self Critical Rate +19.34% for 3 sec every 120 normal
  attacks (`per_shot_rules`' "every" mode). 120 MG shots take 2.0 sec, inside
  the 3 sec duration, and the bullet names no stack count - so each
  re-application refreshes the live grant rather than adding to it.
- Vendetta (skills[2], her burst, cd 40): 1310.4% of final ATK, plus the
  Concealment rider's 561.6% folded in - see below. A raid boss is one target,
  so the "affects 2 unit(s)" targeting lands as a single hit.

The Concealment rider (Fienn, 2026-07-24): Vendetta deals an extra 561.6% "if
the skill user is in the Concealment state". Concealment comes from battle start
(5 sec) and from On the Lam every 120 normal attacks (10 sec). At the engine's
MG rate of 60 shots/sec a 120-shot counter completes in 2.0 sec of fire - about
2.7 sec of wall clock once reloads are counted - so a 10 sec Concealment is
re-granted roughly four times over before it could lapse. It is permanently up
from t≈2s, so the rider is folded into the burst percent rather than gated.
The skill's "removed upon taking a direct hit" clause does not change this: the
sim models no incoming damage, and even in game the state is restored within
seconds.

Not modeled / deferred:
- Frenzy (skills[1]): ATK +22.61%, up to 10 stacks for 30 sec, triggered "when a
  Nikke is incapacitated". The sim never downs an ally, so the trigger can never
  fire. Her Favorite Item build adds a second, shot-counted source for the same
  buff, which IS encoded there.
- The Burst Gauge fill (36.54%) - gauge charge time is a fixed sim input.
- Concealment's own effect (untargetable) and the "removes 5 buff(s) from the 2
  highest-ATK enemies, once per battle" bullet - neither is a damage concept the
  engine represents (there is no enemy-buff model at all).
"""
from app.skill_rules._helpers import refreshing_buff_rule


SKILL_VALUE_MANIFESTS = {
    "rosanna": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_rosanna",
        "keys": {
            "on_the_lam": ("skills", 0),
            "capo_dei_capi": ("skills", 1),
            "vendetta": ("skills", 2),
        },
    },
}


def vendetta_burst_percent(values):
    """Assalto plus the always-on Concealment rider (see the module docstring)."""
    vendetta = values["vendetta"]
    return float(vendetta["description_value_02"]) + float(vendetta["description_value_03"])


def build_rosanna_base_rules(values):
    # Everything else in skills[0]/skills[1] is deferred (see the docstring), so
    # she registers no trigger-driven buffs - her shot-counted crit buff lives in
    # build_rosanna_base_per_shot_rules and her damage in the burst percent.
    return []


def build_rosanna_base_per_shot_rules(values):
    lam = values["on_the_lam"]
    shots = int(float(lam["description_value_01"]))
    crit_rate = float(lam["description_value_03"]) / 100
    crit_duration = float(lam["description_value_04"])
    return [(shots, "every", [
        refreshing_buff_rule("per_shot", [("crit_rate", crit_rate, "self", crit_duration)]),
    ])]
