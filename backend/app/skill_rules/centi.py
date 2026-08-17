"""Centi (slug "centi") and her Favorite Item (애장품) build (slug
"centi-signature"), an Iron Burst-2 Rocket Launcher Defender. The two builds are
separate deck candidates (dual-slug, like drake/drake-signature). Base skill
values and the weapon come from ShiftyPad; the Favorite Item's skill text is
lootandwaifus `dollskills`, the only source that carries it.

The Favorite Item is what makes her a deck candidate at all: it hangs a squad ATK
buff and an Iron-Code elemental buff off Skill 2's cycle, which the base build
spends entirely on a shield.

Modeled (DPS-relevant), base build:
- Start Construction (burst, cd 20): 145.46% of final ATK as burst damage, and
  enemy DEF -14.54% for 10 sec. The debuff is squad-scoped so every attacker
  shares it. "The 5 enemy units with the lowest remaining HP" collapses to the
  single raid boss.

Modeled (DPS-relevant), Favorite Item build - everything above, unchanged (the
item leaves her burst alone, so both builds share `build_centi_rules`), plus:
- Field Discussion (dollskills[1], cd 9): all allies ATK +4.6% of her own ATK
  PER STACK, stacking up to 10. Her headline contribution.
- Maintain Fortification (dollskills[0]): all Iron Code allies (herself included)
  Elemental Advantage Attack Damage +5.69% per stack, up to 10, fired by that
  same Skill 2 activation. Advantage-gated by the damage formula, so it pays
  out only against an Electric Code boss.
- Both counts come from one `ResourceSpec` filled on her Skill 2 cycle - see
  `build_field_discussion_resources` for why the caps really do bind.
- Maintain Fortification's Full Charge cooldown cut (9.16% of Skill 2's cooldown
  per full charge) decides both buffs' uptime, so it is modeled as a shortened
  periodic cooldown - see `field_discussion_effective_cooldown`.

She is a clip launcher: her 6-round magazine comes back two rounds at a time, so
the gap after it empties is three 0.5-sec loads rather than one
(registry.CLIP_RELOAD_SPLITS). Her cadence - and the cooldown cut derived from
it - accounts for that.

Both stack caps bind: the 5.96-sec cycle keeps restarting the 8- and 10-sec
timers the stacks share, so the counts climb to 10 and hold (Fienn confirmed in
game, 2026-08-17). This file used to say the opposite - "at most 2 of the 10
stacks are ever live" - which was per-stack-expiry arithmetic.

Not modeled / deferred:
- The shared shield (6.38% of final Max HP in the base build, 7% with the item),
  Stockpile's stored healing, and the item burst's 30.2% squad heal. The engine
  has no damage consumer for survivability.
- In the base build the Full Charge cooldown cut has nothing to accelerate -
  Skill 2 only raises a shield there - so it changes no damage and is left out.
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import buff_rule, linear_resource_buff

# Seconds she waits between a charged shot and the next charge: 22 frames,
# measured by Fienn (2026-07-30). Written as a frame count because that is the
# grid the measurement resolved, matching Bready's entry in the registry.
CHARGE_MOTION_DELAY = 22 / 60

# Field Discussion's listed cooldown, before the Full Charge cut.
FIELD_DISCUSSION_COOLDOWN = 9.0

SKILL_VALUE_MANIFESTS = {
    "centi": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_centi",
        "keys": {
            "start_construction": ("skills", 2),
        },
    },
    "centi-signature": {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "centi",
        "test_module": "test_skill_rules_centi_signature",
        "keys": {
            "maintain_fortification": ("dollskills", 0),
            "field_discussion": ("dollskills", 1),
            "start_construction": ("dollskills", 2),
        },
    },
}


def start_construction_burst_percent(values):
    return float(values["start_construction"]["description_value_02"])


def build_centi_rules(values):
    """Her burst, identical in both builds."""
    construction = values["start_construction"]
    def_down = float(construction["description_value_03"]) / 100
    def_down_duration = float(construction["description_value_04"])
    return [
        buff_rule("own_burst_activate", [
            ("enemy_def_percent", -def_down, "squad", def_down_duration),
        ]),
    ]


def _average_shot_interval(weapon_stats):
    """Seconds between her charged shots, averaged across a magazine: the charge
    plus her measured post-shot pause, with the reload spread over the rounds it
    buys. `reload_time` is the whole refill, so her three clip loads are already
    in it (see registry.CLIP_RELOAD_SPLITS) - 1.6167 sec, matching Fienn."""
    per_shot = weapon_stats["charge_time"] + CHARGE_MOTION_DELAY
    return per_shot + weapon_stats["reload_time"] / weapon_stats["max_ammo"]


def field_discussion_effective_cooldown(values):
    """How often Skill 2 really comes up. Every Full Charge hit takes 9.16% of
    its cooldown off, so the timer runs down at one second per second PLUS one
    such cut per shot.

    Read off her BASE cadence: a deck's charge-speed or Max Ammunition buffs
    would land more shots inside the window and shorten this further, which a
    static value cannot follow.
    """
    cut = float(values["maintain_fortification"]["description_value_02"]) / 100
    cut_per_second = FIELD_DISCUSSION_COOLDOWN * cut / _average_shot_interval(
        values["caster_weapon_stats"])
    return FIELD_DISCUSSION_COOLDOWN / (1 + cut_per_second)


def build_field_discussion_resources(values):
    """Skill 2's activation carries both Favorite Item buffs, and both are
    stacking ones: "stacks up to 10 times and lasts for 8 sec" (squad ATK) and
    "...for 10 sec" (Iron-Code Elemental Advantage Attack Damage). One counter
    drives both, filled every `field_discussion_effective_cooldown`.

    Each stack restarts the ONE timer the stack shares (the Raven ruling, Fienn
    2026-07-17; Maiden: Ice Rose's range test 2026-08-17), and Fienn confirmed
    2026-08-17 that this counter reaches its cap in game. Her cycle is 5.96 sec
    against 8- and 10-sec stacks, so no gap can break the chain and the count
    climbs to 10 and stays there. A permanent accumulation reproduces that
    exactly - Leona's Roar is encoded the same way for the same reason. Read as
    10 independent timers, the cycle instead held at most 2 stacks, which is
    what these buffs used to be worth: the correction is **her +55.76% / the
    deck +48.94%** (`scripts/measure_buffrule_stack_refresh.py`).

    The cap is the ONLY thing that can bind here, so it is read from the skill
    data rather than assumed - a shorter cycle (a deck's charge-speed buffs)
    only tightens the chain, never breaks it.

    ONE counter drives both because the two bullets fire on the same event and
    neither can lapse; their stated durations differ (8 vs 10 sec) and would
    need a counter each the moment a cycle longer than 8 sec could arise. The
    two caps are checked against each other rather than assumed equal, so that
    day announces itself here.
    """
    discussion = values["field_discussion"]
    fortification = values["maintain_fortification"]
    squad_atk = float(discussion["description_value_03"]) / 100 * values["caster_atk"]
    elemental = float(fortification["description_value_04"]) / 100
    cap = int(float(discussion["description_value_04"]))
    elemental_cap = int(float(fortification["description_value_05"]))
    if cap != elemental_cap:
        raise ValueError(
            f"Centi's two Skill-2 buffs no longer share a stack cap "
            f"({cap} vs {elemental_cap}); they need a resource each"
        )
    return [ResourceSpec(
        name="field_discussion",
        fill=("periodic", field_discussion_effective_cooldown(values)),
        cap=cap,
        buffs=[
            linear_resource_buff("flat_atk", squad_atk, "squad"),
            linear_resource_buff("other_elemental_bonus", elemental, "element:Iron"),
        ],
    )]
