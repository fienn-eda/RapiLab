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
  normal attacks, as in the base build. Unlike Frenzy below, that bullet names
  no stack count, so it refreshes rather than stacks.
- Capo dei Capi (dollskills[1]): Frenzy, self ATK +22.61% per stack, one stack
  per 500 normal attacks on the stage target, capped at 10 - a `ResourceSpec`,
  see `build_frenzy_resources`. Her 500 shots take ~15 sec of wall clock
  against a 30-sec stack, and that duration is one shared timer every stack
  restarts, so the chain never breaks and she climbs to the cap. Reading it as
  10 independent 30-sec timers instead pinned her at the 2-3 instances that
  happen to overlap, which is what this bullet used to hold - worth
  **her +55.85% / the deck +20.90%** on a DEF-8000 boss
  (`scripts/measure_buffrule_stack_refresh.py`).
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
from app.effects import ResourceSpec
from app.skill_rules._helpers import buff_rule, linear_resource_buff, refreshing_buff_rule
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
    crit_shots = int(float(lam["description_value_01"]))
    crit_rate = float(lam["description_value_03"]) / 100
    crit_duration = float(lam["description_value_04"])
    return [
        (crit_shots, "every", [
            refreshing_buff_rule("per_shot",
                                 [("crit_rate", crit_rate, "self", crit_duration)]),
        ]),
    ]


def build_frenzy_resources(values):
    """Frenzy: "ATK +22.61%. Stacks up to 10 times and lasts for 30 sec", one
    stack per 500 normal attacks.

    The 30 sec is ONE timer the whole stack shares, restarted by every new
    stack (the Raven ruling, Fienn 2026-07-17; Maiden: Ice Rose's range test
    2026-08-17), and Fienn confirmed 2026-08-17 that this counter does reach
    its cap in game. Her 500 shots take ~15 sec of wall clock, so no gap comes
    close to 30 - the chain never breaks, and the count simply climbs to the
    cap and stays. A permanent accumulation reproduces that exactly, which is
    how Leona's Roar is encoded for the same reason; per-stack expiry would
    instead settle at the 2-3 overlapping instances this bullet used to hold.
    """
    capo = values["capo_dei_capi"]
    return [ResourceSpec(
        name="frenzy",
        fill=("per_shot_every", int(float(capo["description_value_08"]))),
        cap=int(float(capo["description_value_10"])),
        buffs=[linear_resource_buff(
            "atk_percent", float(capo["description_value_09"]) / 100, "self")],
    )]
