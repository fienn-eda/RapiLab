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
  for 10 sec, plus Special Modification for 1 round. Fienn's 2026-07-16 ruling
  ("Charge Speed v 300%" = charge time x(1+3.0), model both halves) hit the
  engine's magazine-boundary trap: charge speed is evaluated once per magazine
  start, so a 1-round charge_speed_percent Effect granted mid-magazine covers
  no boundary and the slowdown NEVER lands (verified in
  test_one_round_charge_speed_grant_is_inert_mid_magazine) - the raw pair
  would credit +1500% Charge Damage without paying the x4 charge time. Per
  the ruling's documented fallback, the pair is applied as a NET 1-round
  charge_damage_bonus instead: +15.0 scaled down by the x4 unpaid time cost,
  15/4 - 1 = +2.75 net. Buff-only burst (no burst nuke percent).

Not modeled / deferred:
- Covert Support's HP recovery (survival, not DPS).
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule, round_buff_rule


SKILL_VALUE_MANIFESTS = {
    "ada-wong": {
        "source": "lootandwaifus",
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
    special_mod_rounds = int(float(secret["description_value_05"]))      # 1 round
    charge_time_cost = 1 + float(secret["description_value_06"]) / 100   # x4 charge time
    charge_damage = float(secret["description_value_07"]) / 100          # +15.0 nominal
    # Net approximation (see module docstring): the slowdown can't land within
    # a 1-round window, so fold its time cost into the damage bonus instead -
    # the nominal bonus divided by the x4 time cost, minus the round's own
    # baseline (Fienn's documented fallback: 15/4 - 1 = +2.75).
    net_charge_damage = charge_damage / charge_time_cost - 1             # = +2.75

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
        round_buff_rule("own_burst_activate", [
            ("charge_damage_bonus", net_charge_damage, "self"),
        ], shots=special_mod_rounds),
    ]


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
