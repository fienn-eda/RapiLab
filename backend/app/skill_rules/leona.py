"""Leona (slug "leona"), a Burst-2 Water SG supporter.
Values from ShiftyPad; effect text cross-read from lootandwaifus.

Modeled (DPS-relevant):
- Thunderous Roar (skills[0]): every 5 of her own normal attacks, squad
  Critical Rate +2.62% per stack, capped at 5. A `ResourceSpec` named "roar",
  filled `("per_shot_every", 5)`.

  Its lifetime is the judgment call. "Stacks up to 5 time(s) and lasts for
  5 sec" is ONE counter whose life every trigger refreshes back to 5 sec (the
  Raven ruling, Fienn 2026-07-17) - NOT five independent 5-second stacks. Her
  own cadence decides whether the difference shows: her shotgun fires 9 rounds
  at 0.667 sec apart and reloads in 1.5, so the gap between fills alternates
  3.33 / 4.98 sec and never reaches 5. The counter therefore never lapses, and
  a permanent accumulation reproduces that exactly. Per-stack expiry would pin
  her at 2 stacks for the entire fight and quietly close Lion's Heart's
  max-stack gate forever.
- Courageous Look (skills[1]): on Full Burst enter, squad Hit Rate +20.28% for
  10 sec. Hit Rate narrows a normal attack's bullet spread against the boss's
  core, and pays out on any encounter that sets a core diameter - which is
  where her shotgun allies collect, SG having the widest spread of any weapon.
- Lion's Heart (skills[2], her burst, cd 20): squad Critical Damage +34.64% for
  10 sec, plus - gated on Roar sitting at its 5-stack cap - Critical Rate
  +21.32% for 10 sec on shotgun allies. The gate is a `resource_gated_buffs`
  spec reading the count at her own burst time; the shotgun-only audience is
  its `member_filter`, resolved against the live squad rather than approximated
  onto `squad`. Roar reaches the cap about 19 sec in and holds it, so from the
  second cycle on this bullet is live every time.
- Courageous Look's "Number of pellets ▲ 5" on the 2 highest-ATK shotgun
  allies. Pellet count moves NO damage directly - the shot's total is split
  across more pellets (measured on Arcana: Fortune Mate, 2026-08-03) - but it
  is a real input to Dorothy: Serendipity's Flash counter, which counts pellets
  rather than shots, and Flash's procs DO move damage. So the targeting is
  encoded as the text has it, shotguns AND top-2, via
  `highest_atk_buff_rule(..., member_filter=_is_shotgun)`; `top_atk_slugs`
  gained the filter for exactly this pair (2026-08-08). Approximating it onto
  every shotgun ally would speed up a Flash counter the game never touched in
  any deck holding three shotguns.

  She competes for her own two slots (`include_caster=True`): the bullet says
  only "the 2 ally unit(s) with shotguns who have the highest final ATK", with
  no "except caster" clause, and such a bullet includes the caster whenever she
  meets its conditions - which she does, being a shotgun (Fienn, 2026-08-08;
  the same ruling Maxwell's Straight Shot got on 2026-07-19). The clause IS
  spelled out when it applies, in Miranda's, Mana's and Soda's text.

Not modeled / deferred:
- Thunderous Roar's second bullet, "after 15 normal attacks, all allies with
  shotguns: Maximum Effective Range ▲ 20% for 10 sec". This widens the weapon's
  own range band. Since 2026-07-31 the effective-range bonus is decided by the
  encounter (`BossProfile.effective_range_band` picks which weapon classes
  collect the measured +0.30); it is not a registry stat and no skill can move
  it. Encoding it anywhere would be inert or, worse, wrong.
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import (
    buff_rule,
    highest_atk_buff_rule,
    linear_resource_buff,
)
from app.skill_rules.dorothy_serendipity import PELLET_COUNT_BONUS


SKILL_VALUE_MANIFESTS = {
    "leona": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_leona",
        "keys": {
            "thunderous_roar": ("skills", 0),
            "courageous_look": ("skills", 1),
            "lions_heart": ("skills", 2),
        },
    },
}


SHOTGUN = "SG"
# "Activates after 5 normal attacks" - the fill cadence, read from the slot but
# named here because the tests reason about it directly.
ROAR_SHOT_COUNT = 5


def _is_shotgun(member, _owner_slug=None):
    return member.weapon == SHOTGUN


def build_leona_resources(values):
    roar = values["thunderous_roar"]
    return [
        ResourceSpec(
            name="roar",
            fill=("per_shot_every", int(float(roar["description_value_01"]))),
            cap=int(float(roar["description_value_03"])),
            buffs=[
                # lifetime=None: one refreshed counter, not per-stack expiry -
                # see the module docstring for why her cadence settles it.
                linear_resource_buff(
                    "crit_rate", float(roar["description_value_02"]) / 100, "squad", lifetime=None
                ),
            ],
        )
    ]


def build_lions_heart_resource_gated_buffs(values):
    """Lion's Heart's shotgun bullet, gated on Roar at max stacks."""
    roar = values["thunderous_roar"]
    heart = values["lions_heart"]
    cap = int(float(roar["description_value_03"]))
    return [{
        "resource": "roar", "cap": cap,
        "gate_fn": lambda count, cap=cap: count >= cap,
        "stat": "crit_rate",
        "value": float(heart["description_value_03"]) / 100,
        "member_filter": _is_shotgun,
        "duration": float(heart["description_value_04"]),
    }]


def build_leona_rules(values):
    look = values["courageous_look"]
    heart = values["lions_heart"]

    hit_rate = float(look["description_value_01"]) / 100
    hit_rate_duration = float(look["description_value_02"])
    pellet_targets = int(float(look["description_value_03"]))
    pellets = float(look["description_value_04"])
    pellet_duration = float(look["description_value_05"])
    crit_damage = float(heart["description_value_01"]) / 100
    crit_damage_duration = float(heart["description_value_02"])

    return [
        buff_rule("full_burst_enter", [("hit_rate", hit_rate, "squad", hit_rate_duration)]),
        highest_atk_buff_rule(
            "full_burst_enter", pellet_targets,
            [(PELLET_COUNT_BONUS, pellets, pellet_duration)],
            member_filter=_is_shotgun, include_caster=True,
        ),
        buff_rule("own_burst_activate", [
            ("other_critical_damage_sources", crit_damage, "squad", crit_damage_duration),
        ]),
    ]
