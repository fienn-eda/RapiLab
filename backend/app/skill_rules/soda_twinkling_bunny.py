"""Soda: Twinkling Bunny (slug "soda-twinkling-bunny"), a Burst-3 Iron
Shotgun attacker. Base skills. PARTIAL - see below.

First consumer of the reset-capable resource primitive (a resource SET to a
fixed value rather than incremented - see effects.ResourceSpec.resets) and of
resource_gated_buffs (a burst-fired buff gated on a resource's count at the
burst's own time - see raid_simulator's `resource_gated_buffs` param).

Modeled (DPS-relevant): a "chip" resource (Golden Chip), capped at 50.
- Lucky Golden Chip (skills[0]) starts it at 50 (the cap) from battle start,
  and fills it +1 every 3 normal attacks DURING FULL BURST
  (`per_shot_every_during_full_burst`) - it IS her Critical Damage stack:
  +1.32% Critical Damage per stack, continuous.
- Onward, Soda! (skills[2], her burst): deals 628.7% of final ATK as damage,
  then resets Golden Chip to 17 (`resets`, trigger "own_burst") - consuming
  whatever it had built up. Additionally, if she had at least 30 stacks right
  BEFORE that reset (`resource_gated_buffs`, `use_pre_reset`), grants self
  ATK +65.25% for 15 sec.

Not modeled / deferred:
- Lucky Golden Chip's co-fired buff ("after 3 normal attacks during Full
  Burst, affects self and the 1 ally with the highest final ATK: Attack
  Damage +10.51% for 2 sec") needs an FB-window-gated PER-SHOT TRIGGER (like
  `per_shot_rules`, but counting only in-Full-Burst shots) - a related but
  distinct gap from the FB-gated RESOURCE FILL built for Golden Chip itself
  (`per_shot_rules` has no Full-Burst-window filter). Approximating it as a
  plain "every 3 shots" would be a real overcount, not a minor one: SG fires
  1.5/s, so "every 3 shots" is every 2 sec - exactly the buff's own duration,
  making it read as PERMANENT if fired outside Full Burst too, instead of only
  active during her ~10-sec Full Burst window each cycle. Deferred rather than
  approximated.
- Beginner's Rewards (skills[1]) entirely: both bullets depend on a per-unit
  Full Burst Duration extension (+2s/+3s gated on Golden Chip stacks), which
  has no engine concept (Full Burst duration is a single global constant, not
  adjustable per-caster) - and the bullet's own per-shot nuke is itself gated
  on that same extension state, so it's unreachable too.
- Onward, Soda!'s Hit Rate +38.91%/15s (gated on pre-reset stacks >=20) is
  inert - Hit Rate isn't a stat the engine consumes.
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import linear_resource_buff


def onward_soda_burst_percent(values):
    return float(values["onward_soda"]["description_value_02"])


def build_golden_chip_resources(values):
    chip = values["lucky_golden_chip"]
    soda = values["onward_soda"]

    initial_stacks = int(float(chip["description_value_01"]))
    crit_damage_per_stack = float(chip["description_value_03"]) / 100
    cap = int(float(chip["description_value_04"]))
    post_burst_value = int(float(soda["description_value_01"]))

    return [
        ResourceSpec(
            name="chip",
            fill=("per_shot_every_during_full_burst", 3),
            cap=cap,
            buffs=[linear_resource_buff("other_critical_damage_sources", crit_damage_per_stack, "self")],
            resets=[
                {"trigger": "battle_start", "value": initial_stacks},
                {"trigger": "own_burst", "value": post_burst_value},
            ],
        )
    ]


def build_onward_soda_resource_gated_buffs(values):
    soda = values["onward_soda"]
    cap = int(float(values["lucky_golden_chip"]["description_value_04"]))
    atk_gate = float(soda["description_value_06"])
    atk_value = float(soda["description_value_07"]) / 100
    atk_duration = float(soda["description_value_08"])

    return [{
        "resource": "chip", "cap": cap, "use_pre_reset": True,
        "gate_fn": lambda count, gate=atk_gate: count >= gate,
        "stat": "atk_percent", "value": atk_value, "scope": "self", "duration": atk_duration,
    }]
