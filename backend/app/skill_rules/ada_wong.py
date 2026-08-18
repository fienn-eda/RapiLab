"""Ada Wong (slug "ada-wong"), a Burst-3 Electric RL attacker. Collected from
lootandwaifus (2026-07-16 file).

Modeled (DPS-relevant):
- Covert Support (skills[0], on entering Full Burst): all Burst 3 allies who
  previously used their Burst Skill (member-subset scope, gap #3) get flat ATK
  = 60% of caster's ATK and True Damage ^ 50%, 10 sec. Ada herself matches
  once her burst fired.
- Flash Grenade (skills[1]): during Full Burst, every 2 sec, 420% of final ATK
  as True Damage (periodic_nukes during_full_burst, gap #6; true-typed so
  true_damage_up applies and enemy DEF is ignored). Her burst's "activation
  time condition v 1 sec for 10 sec" makes FB windows opened by HER OWN burst
  tick at 1s instead (own_burst_interval, Fienn 2026-07-16).
- Secret Agent (skills[2], her burst): self ATK ^ 40% and True Damage ^ 42%
  for 10 sec, plus Special Modification for 1 round. Buff-only burst (no burst
  nuke percent).
- Special Modification, BOTH halves, as a one-shot weapon-mode segment
  (2026-08-18). Fienn's 2026-07-16 ruling ("Charge Speed v 300%" = charge time
  x(1+3.0), model both halves) had hit the engine's magazine-boundary trap:
  charge speed is evaluated once per magazine start, so a 1-round
  charge_speed_percent Effect granted mid-magazine covers no boundary and the
  slowdown NEVER lands (still true - see
  test_one_round_charge_speed_grant_is_inert_mid_magazine). The pair was
  therefore folded into a NET charge_damage_bonus, +15.0 scaled down by the x4
  unpaid time cost (15/4 - 1 = +2.75) - which paid that time in FEWER SHOTS
  rather than in a longer charge. A SEGMENT has no such trap: it STATES its own
  charge time, so the slow shot is declared rather than sampled, and
  `until_shots: 1` is exactly "for 1 round(s)" - her second shot onward is the
  plain RL again (Fienn, 2026-08-18). 4.0 sec charge (1.0 x 4), 1750% Charge
  Damage (250% + 1500%). A deck Charge Speed buff still shortens it, because a
  `charge_time` profile honours live cadence buffs by contract.

  Residual: a segment boundary hands back a FRESH magazine, so she is credited
  one extra round per burst cycle that the real Special Modification spends out
  of the six she had. Small, and in her favour; the alternative understated the
  whole bullet instead.

Not modeled / deferred:
- Covert Support's HP recovery (survival, not DPS).
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule


SKILL_VALUE_MANIFESTS = {
    "ada-wong": {
        "source": "lootandwaifus",
        "dotgg_slug": "ada",
        "test_module": "test_skill_rules_ada_wong",
        "keys": {
            "covert_support": ("skills", 0),
            "flash_grenade": ("skills", 1),
            "secret_agent": ("skills", 2),
        },
        "drop_tokens": {
            "covert_support": [0],
            "secret_agent": [5, 7],
        },
    },
}


def build_ada_wong_rules(values):
    covert = values["covert_support"]
    secret = values["secret_agent"]
    caster_atk = values["caster_atk"]

    covert_flat_atk = caster_atk * float(covert["description_value_01"]) / 100
    covert_atk_duration = float(covert["description_value_02"])
    covert_true = float(covert["description_value_03"]) / 100
    covert_true_duration = float(covert["description_value_04"])
    self_atk = float(secret["description_value_01"]) / 100
    self_atk_duration = float(secret["description_value_02"])
    self_true = float(secret["description_value_03"]) / 100
    self_true_duration = float(secret["description_value_04"])
    def bursted_b3(member, context):
        return member.burst_tier == 3 and member.slug in context.burst_used_this_cycle

    return [
        member_subset_buff_rule("full_burst_enter", bursted_b3, [
            ("flat_atk", covert_flat_atk, covert_atk_duration),
            ("true_damage_up", covert_true, covert_true_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("atk_percent", self_atk, "self", self_atk_duration),
            ("true_damage_up", self_true, "self", self_true_duration),
        ]),
        # Special Modification is the segment below, not a round buff: it has to
        # change the charge TIME as well as the damage.
    ]


def build_special_modification_weapon_mode_schedule(values):
    """Secret Agent's Special Modification: her FIRST normal attack after the
    burst charges x4 as long and carries the full Charge Damage bonus; from the
    second shot on she is a plain RL again (Fienn, in-game 2026-08-18).

    `until_shots` is what makes "for 1 round(s)" exact, and a segment STATES its
    own charge time instead of sampling `charge_speed_percent` at a magazine
    boundary - the trap that had forced the old net-damage approximation (see
    the module docstring)."""
    secret = values["secret_agent"]
    weapon = values["caster_weapon_stats"]
    rounds = int(float(secret["description_value_05"]))                  # 1 round
    charge_time_cost = 1 + float(secret["description_value_06"]) / 100   # x4 charge time
    charge_damage = float(secret["description_value_07"])                # +1500%
    profile = {
        "weapon": weapon["weapon"],
        "damage_percent": weapon["damage_percent"],
        "charge_time": weapon["charge_time"] * charge_time_cost,
        # Charge Damage is one additive group, so the skill's bonus joins her
        # weapon's own full-charge multiplier rather than replacing it.
        "charge_damage_percent": weapon["charge_damage_percent"] + charge_damage,
    }

    def schedule(context, fight_duration):
        return [{"start": burst_time, "until_shots": rounds, "profile": profile}
                for burst_time in context.burst_times.get("ada-wong", [])
                if burst_time < fight_duration]

    return schedule


def build_flash_grenade_periodic_nuke(values):
    grenade = values["flash_grenade"]
    return {
        "cooldown": float(grenade["description_value_01"]),
        "percent": float(grenade["description_value_02"]),
        "damage_type": "true",
        "during_full_burst": True,
        "own_burst_interval": (
            float(grenade["description_value_03"]),   # 1 sec
            float(grenade["description_value_04"]),   # for 10 sec
        ),
    }
