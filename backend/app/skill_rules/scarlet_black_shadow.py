"""Scarlet: Black Shadow (slug "scarlet-black-shadow"), a Burst-3 Wind RL
attacker (Pilgrim, burst cd 40s, no signature weapon - base skills only).
First consumer of `per_shot_rules`' "sequence" mode (gap #10): her whole kit
revolves around a full-charge counter whose requirement table her burst
rewrites for 10 seconds.

Modeled (DPS-relevant):
- Fleetly Fading Breakthrough (skills[0]): one running full-charge counter
  (RL: every shot is a full charge) walks the staged table 3/6/9 - 3rd shot
  deals 283.03% of final ATK as damage to the 1 lowest-final-DEF enemy (= the
  solo raid boss), 6th deals 565% as Distributed Damage, 9th deals 848.03% as
  Distributed Damage, then the cycle restarts ("Only one effect is triggered
  at a time"). Vs the single raid boss all three stages land fully on the
  boss; the Distributed stages are typed "distributed" so squad
  distributed_damage_up buffs (e.g. Anchor's) apply.
- Fleetly Fading Strike (skills[2], her burst, buff-only - burst percent is
  None): self ATK +115.12% and Charge Damage +169.63% for 10 sec, and
  "Changes Full Charge attack count required for Skill 1 to 1/2/3 for 10 sec"
  - the sequence spec's own-burst-window requirement override. The running
  count and stage carry over across the window boundary (Fienn 2026-07-18).
- Fleetly Fading: Asura (skills[1]): on Full Burst entry, self Max
  Ammunition Capacity +60% for 10 sec - max_ammo_percent is consumed live by
  shot generation (magazine size / reload cadence), and FB-entry effects are
  registered before the weapon pass, so her own magazines really grow.
- Asura's "Reload 100% of the magazine(s)" on Full Burst entry: a zero-length
  `weapon_mode_schedules` segment at each Full Burst start. A segment boundary
  is the engine's "discard the magazine, resume with a fresh one", and a
  segment of zero length fires nothing and consumes no time, which is exactly
  an INSTANT full reload. The trigger is ANY Full Burst entry (the skill says
  "when entering Full Burst", not her own burst), so it reads
  `context.full_burst_windows`, not `burst_times`. This drives the sequence
  counter hard: as an RL every shot is a full charge, so magazines she would
  have spent reloading through instead keep the counter moving.

Not modeled / deferred:
- Asura's PARTIAL reload at skill levels below 7 ("Reload 30%/60% of the
  magazine(s)"). The segment boundary is an all-or-nothing fresh magazine, so
  the segment is only emitted when the slot reads 100.

Charge-weapon note: the base weapon's first shot of a stretch lands one charge
time after the stretch starts, so a reset at T drops whatever charge was in
progress and her next shot is at T + charge_time. In game she would keep that
progress, so every modeled shot time is at or after its real one - the
encoding stays a floor.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

SKILL_VALUE_MANIFESTS = {
    "scarlet-black-shadow": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_scarlet_black_shadow",
        "keys": {
            "fleetly_fading_breakthrough": ("skills", 0),
            "fleetly_fading_asura": ("skills", 1),
            "fleetly_fading_strike": ("skills", 2),
        },
        "drop_tokens": {
            # "required for Skill 1 to 1 time/2 times/..." - the "1" naming
            # Skill 1 is a numeric token but not a value slot.
            "fleetly_fading_strike": [0],
        },
    },
}

# "Three times / Six times / Nine times" - written out in the skill text, not
# numeric description slots.
BREAKTHROUGH_BASE_REQUIREMENTS = (3, 6, 9)


def full_burst_max_ammo_percent(values):
    """Fleetly Fading: Asura's Max Ammunition Capacity grant, as a ratio.

    Shared with charge_window_inputs: her magazine size decides whether a reload
    lands inside the Full Burst window, so the calculator needs the same number
    the rule below applies."""
    return float(values["fleetly_fading_asura"]["description_value_01"]) / 100


def build_scarlet_black_shadow_rules(values):
    strike = values["fleetly_fading_strike"]
    self_atk = float(strike["description_value_05"]) / 100
    self_atk_duration = float(strike["description_value_06"])
    charge_damage = float(strike["description_value_07"]) / 100
    charge_damage_duration = float(strike["description_value_08"])
    asura = values["fleetly_fading_asura"]
    max_ammo = full_burst_max_ammo_percent(values)
    max_ammo_duration = float(asura["description_value_02"])
    return [
        buff_rule("own_burst_activate", [
            ("atk_percent", self_atk, "self", self_atk_duration),
            ("charge_damage_bonus", charge_damage, "self", charge_damage_duration),
        ]),
        buff_rule("full_burst_enter", [
            ("max_ammo_percent", max_ammo, "self", max_ammo_duration),
        ]),
    ]


FULL_MAGAZINE_RELOAD_PERCENT = 100.0


def build_scarlet_weapon_mode_schedule(values):
    """Asura's instant "Reload 100% of the magazine(s)" on entering Full Burst,
    as a zero-length segment at each Full Burst start: no shots, no elapsed
    time, and the base weapon resumes there with a fresh magazine."""
    asura = values["fleetly_fading_asura"]
    reload_percent = float(asura["description_value_03"])
    weapon = values["caster_weapon_stats"]["weapon"]

    def schedule(context, fight_duration):
        if reload_percent < FULL_MAGAZINE_RELOAD_PERCENT:
            return []
        return [
            {
                "start": start,
                "end": start,
                "profile": {"weapon": weapon, "damage_percent": 0.0, "rate_of_fire": 1.0},
            }
            for start, _end in context.full_burst_windows
            if start < fight_duration
        ]

    return schedule


def build_breakthrough_per_shot_rules(values):
    """gap #10 ("sequence" mode): the staged 3/6/9 full-charge nukes, with the
    burst's 1/2/3 requirement override inside her own 10s burst window."""
    breakthrough = values["fleetly_fading_breakthrough"]
    strike = values["fleetly_fading_strike"]
    stage_percents = [
        float(breakthrough["description_value_02"]),
        float(breakthrough["description_value_03"]),
        float(breakthrough["description_value_04"]),
    ]
    override_requirements = [
        int(strike["description_value_01"]),
        int(strike["description_value_02"]),
        int(strike["description_value_03"]),
    ]
    window_duration = float(strike["description_value_04"])
    spec = {
        "requirements": list(BREAKTHROUGH_BASE_REQUIREMENTS),
        "own_burst_window": (window_duration, override_requirements),
    }
    # Every stage is computed at its own SHOT's time, not at a cast, so the
    # Full Burst window test decides per hit - the timing fact the "as
    # additional damage" phrase is only a proxy for (Fienn, 2026-07-26). Her
    # burst rewrites the requirement table, so most stages land inside Full
    # Burst and collect the bonus; the ones outside it still do not.
    stage_rules = [
        [instant_nuke_pulse_rule("per_shot", stage_percents[0])],
        [instant_nuke_pulse_rule("per_shot", stage_percents[1],
                                 damage_type="distributed")],
        [instant_nuke_pulse_rule("per_shot", stage_percents[2],
                                 damage_type="distributed")],
    ]
    return [(spec, "sequence", stage_rules)]


# Fienn's in-game measurements, two independent readings that agree:
#   2026-07-20, 60fps over a Full Burst window: 14 hits in 9.52 sec, evenly
#     spaced - one shot every 0.7323 sec.
#   2026-07-28, timing the fire-to-charge gap directly: pauses of 0.44 / 0.42 /
#     0.44 / 0.42 / 0.43 sec, with charge-completion to charge-completion at
#     0.74 / 0.73 / 0.73 / 0.73.
#
# The second splits the first. 0.7325 - 0.43 = 0.3025, which is the 0.30 sec
# charge time her collected data always said - so the data file was right and
# the missing piece was the pause after the shot, the melee animation of a
# "Rocket Launcher" who actually swings a sword. She therefore carries a plain
# charge_time and a motion delay (registry.TIMED_CHARGE_MOTION_DELAY) rather
# than a weapon profile that overwrote charge_time with the whole interval.
#
# The split is what makes charge-speed buffs behave: they shorten the 0.30 and
# leave the 0.43 alone. She is played with Liberalio precisely for that buff,
# and under the old model the buff was applied to the entire 0.73.

