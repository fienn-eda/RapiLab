"""Dorothy: Serendipity (slug "dorothy-serendipity"), a Burst-3 Water SG
attacker. Base skills. Collected from lootandwaifus.com. Her kit is built around
a pellet counter: her shotgun's pellets accumulate toward a threshold that arms
her own Hit Rate, and that Hit Rate is large enough to collapse an SG's spread
onto the boss's core.

Modeled (DPS-relevant):
- Flash (skills[0]): every 80 pellets that hit the target, self Hit Rate
  +98.18%, Attack Damage +72% and the Pierce property, all for 3 round(s).
  Encoded as a `per_shot_rules` "accumulate" rule - pellets, not shots, because
  a shot is worth 10 pellets normally, 15 while her burst's "+5" is up, and
  1 (+5) for the 3 rounds this bullet fixes the count at 1. That variation is
  load-bearing: she fires 58% of her shots inside her own burst window, so the
  cycle runs 7.9 shots rather than the 11 a flat 10 pellets would give.
  +98.18% alone puts her 250px spread at 26.9px - inside a 50px core - so those
  3 shots hit the core outright against her idle 4%.
- Radiant Wings (skills[1]): self Pierce Damage +55.08% continuously (from battle
  start, permanent). During Full Burst, self ATK +75.24% and self Hit Rate
  +40.68% - modeled as full_burst_enter buffs lasting until the open Full Burst
  window closes (falls back to `FULL_BURST_DURATION` for a context without a
  burst cycle). Stacked on Flash the two reach 138.86%, past the 110%
  singularity where an SG's spread is a point.
- False Salvation (skills[2], her burst): self Attack Speed +65% and self ATK
  +88.12%, both for 15 sec. Attack Speed feeds the Phase S shot-cadence model, so
  her shotgun fires ~65% more often for those 15 sec. Her burst has no nuke.
  Its "Number of pellets +5" is encoded too, but only as an input to Flash's
  counter (see `pellet_count_bonus` below) - pellet COUNT moves no damage.

Not modeled / deferred:
- Flash's second bullet, "when hitting the target with 160 pellets: expands
  Pierce range by 200%". The engine's only channel from Pierce to damage is
  `pierce_hits_body_behind_core`, a BOOLEAN that is already on the moment she
  holds Pierce, so a range multiplier has nothing to multiply - how many extra
  instances a wider pierce would produce is not something this engine counts.
  The wiring is open, though: a second "accumulate" rule at 160 rides the
  subtract-not-reset threshold onto every second Flash, which is what Fienn
  confirmed happens in-game (2026-08-07).

Assumption this encoding rests on:
- "80 pellets that HIT the target" is treated as 80 pellets FIRED - i.e. every
  pellet connects (gap #21's `p_조준` = 1.0). Fienn's ruling (2026-08-07): a raid
  boss fills the screen and an SG fires point-blank, so the 250px spread lands
  inside its body. On a small-bodied boss, or an operation aiming at parts, the
  cycle would be longer and she is overrated here.
"""
from app.effects import Effect
from app.skill_rules._helpers import (
    buff_rule,
    full_burst_window_length,
    round_buff_rule,
)
from app.squad_engine import SkillRule


SKILL_VALUE_MANIFESTS = {
    "dorothy-serendipity": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_dorothy_serendipity",
        "keys": {
            "flash": ("skills", 0),
            "radiant_wings": ("skills", 1),
            "false_salvation": ("skills", 2),
        },
    },
}

# Pellets a shotgun shot fires (`shot_detail.shot_count`; 10 across every
# collected SG, Zwei alone at 5). It is the counter's unit, not a damage term -
# the same shot total is split across more pellets, measured on Arcana: Fortune
# Mate's Happy Memories (2026-08-03).
SHOTGUN_PELLETS_PER_SHOT = 10.0

# The stat carrying "Number of pellets ▲ N" into the counter. Deliberately
# absent from raid_simulator's `_BUNDLE_STATS`: pellet count buys hit
# consistency and counter speed, never damage.
PELLET_COUNT_BONUS = "pellet_count_bonus"


def _target(context, slug):
    member = next((m for m in context.members if m.slug == slug), None)
    return {"slug": slug, "element": member.element if member else None}


def build_flash_per_shot_rules(values):
    """Flash's 80-pellet bullet as an "accumulate" per-shot rule.

    The increment callback is handed `shots_since_fire` rather than reading the
    registry for its own proc, because a round grant does not become an Effect
    until the pass after every unit's shot loop (gap #9) - this counter runs
    before it.
    """
    flash = values["flash"]
    threshold = float(flash["description_value_01"])
    shots = int(float(flash["description_value_02"]))
    hit_rate = float(flash["description_value_03"]) / 100
    attack_damage = float(flash["description_value_05"]) / 100
    fixed_pellets = float(flash["description_value_07"])

    def pellets_this_shot(context, slug, time, registry, shots_since_fire):
        locked = shots_since_fire is not None and shots_since_fire < shots
        base = fixed_pellets if locked else SHOTGUN_PELLETS_PER_SHOT
        # The burst's +5 adds to the fixed 1 rather than being overridden by it
        # (Fienn, in-game 2026-08-07).
        return base + registry.total_for(PELLET_COUNT_BONUS, _target(context, slug), now=time)

    return [
        ((threshold, pellets_this_shot), "accumulate", [
            round_buff_rule("per_shot", [
                ("hit_rate", hit_rate, "self"),
                ("attack_damage_up", attack_damage, "self"),
                ("has_pierce", 1.0, "self"),
            ], shots=shots, from_own_shot=True),
        ]),
    ]


def build_dorothy_serendipity_rules(values):
    radiant_wings = values["radiant_wings"]
    false_salvation = values["false_salvation"]

    self_pierce = float(radiant_wings["description_value_01"]) / 100
    fb_atk = float(radiant_wings["description_value_02"]) / 100
    fb_hit_rate = float(radiant_wings["description_value_03"]) / 100
    attack_speed = float(false_salvation["description_value_01"]) / 100
    attack_speed_duration = float(false_salvation["description_value_02"])
    burst_atk = float(false_salvation["description_value_03"]) / 100
    burst_atk_duration = float(false_salvation["description_value_04"])
    pellet_bonus = float(false_salvation["description_value_05"])
    pellet_bonus_duration = float(false_salvation["description_value_06"])

    def apply_full_burst_buffs(context, caster_slug, time, registry):
        window = full_burst_window_length(context, time)
        registry.add(
            Effect("atk_percent", fb_atk, "self", window, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("hit_rate", fb_hit_rate, "self", window, caster_slug),
            applied_at=time,
        )

    return [
        buff_rule("battle_start", [
            ("pierce_damage_up", self_pierce, "self", None),
        ]),
        SkillRule(trigger="full_burst_enter", action=apply_full_burst_buffs),
        buff_rule("own_burst_activate", [
            ("atk_percent", burst_atk, "self", burst_atk_duration),
            ("attack_speed_percent", attack_speed, "self", attack_speed_duration),
            (PELLET_COUNT_BONUS, pellet_bonus, "self", pellet_bonus_duration),
        ]),
    ]
