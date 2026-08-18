"""Zwei (slug "zwei") and her Favorite Item build (slug "zwei-signature"), a
Burst-1 SG supporter. Collected from lootandwaifus.

The two builds are separate deck candidates (dual-slot); which one a user fights
with comes from their roster's per-unit `favorite_item` flag.

Base modeled (DPS-relevant): the Full-Burst squad Pierce (1 round + 10 sec), the
Full-Burst squad Crit Rate (18.63% for 5 sec - the Favorite Item doubles that
window to 10 sec), her burst's squad Pierce, and the same weapon transform with a
1.5-sec charge (the Favorite Item shortens it to 1.2 sec).

Base has NO per-shot rules and NO resource: the stacking Pierce and the "Pierce
Attacks 101" crit-rate stack are text only the Favorite Item adds.

**Slot numbering differs between the two arrays** and that is the trap here.
lootandwaifus values are numbered left-to-right over the rendered text, and the
Favorite Item's Overcharge Formula mentions the status NAME "Pierce Attacks 101"
- so the literal 101 consumes slot 05 and pushes the squad Pierce/duration to
slots 06/07, where the base build has them at 05/06. A shared builder reading
fixed indices would silently read the wrong numbers, which is why the base has
its own.

Favorite Item modeled (DPS-relevant):
- Pierce Equation (dollskills[0]): on Full Burst enter, squad Pierce Damage up
  for 1 round (a bullet-count grant - each ally's next shot) plus a separate
  squad Pierce Damage up for 10 sec.
- Pierce Equation's second bullet: on EACH of her normal attacks during Full
  Burst, squad Pierce Damage up "for 1 round" - another bullet-count grant, fired
  through the Full-Burst-window-gated per-shot trigger (`per_shot_rules` mode
  "every_during_full_burst"), stacking up to the skill's 3-stack cap per ally
  (round_buff_rule's `cap`, read from the skill's own cap slot).
- Frame Analysis (dollskills[1]): on Full Burst enter, squad Crit Rate up.
- Frame Analysis's second bullet: on EACH of her normal attacks "while in Pierce
  Attacks 101 status", squad Crit Rate up, 5 sec per stack, capped at 3. "Pierce
  Attacks 101" is the NAME Overcharge Formula gives the all-ally buff it grants
  for 10 sec, so the gate is a 10-sec window anchored on her own burst - a capped
  resource filled by `per_shot_every_during_own_status_window`, whose window
  duration is read from Overcharge Formula's own duration slot.
- Overcharge Formula (dollskills[2], her burst): squad Pierce Damage up, plus
  her self weapon transform - see build_overcharge_weapon_mode_schedule.

Not modeled / deferred:
- Frame Analysis's Cover HP recovery (survival, no DPS effect).
- Frame Analysis's Cover HP recovery is the only DPS-irrelevant bullet left.
Note pierce is treated as general damage-up (see raid_simulator).
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import buff_rule, linear_resource_buff, round_buff_rule

SKILL_VALUE_MANIFESTS = {
    "zwei": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst1_batch2",
        "keys": {
            "pierce_equation": ("skills", 0),
            "frame_analysis": ("skills", 1),
            "overcharge_formula": ("skills", 2),
        },
        "fixtures": {
            "pierce_equation": "ZWEI_BASE_PIERCE_EQUATION",
            "frame_analysis": "ZWEI_BASE_FRAME_ANALYSIS",
            "overcharge_formula": "ZWEI_BASE_OVERCHARGE_FORMULA",
        },
    },
    "zwei-signature": {
        "source": "lootandwaifus",
        "data_slug": "zwei",
        "test_module": "test_skill_rules_burst1_batch2",
        "keys": {
            "pierce_equation": ("dollskills", 0),
            "frame_analysis": ("dollskills", 1),
            "overcharge_formula": ("dollskills", 2),
        },
        "fixtures": {
            "pierce_equation": "ZWEI_SIG_PIERCE_EQUATION",
            "frame_analysis": "ZWEI_SIG_FRAME_ANALYSIS",
            "overcharge_formula": "ZWEI_SIG_OVERCHARGE_FORMULA",
        },
    },
}


def build_zwei_base_rules(values):
    """Zwei without her Favorite Item. Overcharge Formula's squad Pierce sits at
    slots 05/06 here, not 06/07 - see the module docstring on slot numbering."""
    pierce = values["pierce_equation"]
    frame = values["frame_analysis"]
    overcharge = values["overcharge_formula"]
    round_pierce = float(pierce["description_value_01"]) / 100
    round_pierce_rounds = int(float(pierce["description_value_02"]))
    fb_pierce = float(pierce["description_value_03"]) / 100
    fb_pierce_duration = float(pierce["description_value_04"])
    fb_crit_rate = float(frame["description_value_03"]) / 100
    fb_crit_rate_duration = float(frame["description_value_04"])
    burst_pierce = float(overcharge["description_value_05"]) / 100
    burst_pierce_duration = float(overcharge["description_value_06"])

    return [
        buff_rule("full_burst_enter", [
            ("pierce_damage_up", fb_pierce, "squad", fb_pierce_duration),
            ("crit_rate", fb_crit_rate, "squad", fb_crit_rate_duration),
        ]),
        round_buff_rule("full_burst_enter",
                        [("pierce_damage_up", round_pierce, "squad")],
                        shots=round_pierce_rounds),
        buff_rule("own_burst_activate", [
            ("pierce_damage_up", burst_pierce, "squad", burst_pierce_duration),
        ]),
        # Overcharge Formula's "Additional Effect: Pierce" - the transform is
        # one charged shot, so the property covers exactly that round. Her
        # squad Pierce Damage buffs credit only allies who have Pierce too.
        round_buff_rule("own_burst_activate", [("has_pierce", 1.0, "self")], shots=1),
    ]


def build_zwei_rules(values):
    pierce = values["pierce_equation"]
    frame = values["frame_analysis"]
    overcharge = values["overcharge_formula"]
    round_pierce = float(pierce["description_value_01"]) / 100
    round_pierce_rounds = int(pierce["description_value_02"])
    fb_pierce = float(pierce["description_value_03"]) / 100
    fb_pierce_duration = float(pierce["description_value_04"])
    fb_crit_rate = float(frame["description_value_03"]) / 100
    fb_crit_rate_duration = float(frame["description_value_04"])
    burst_pierce = float(overcharge["description_value_06"]) / 100
    burst_pierce_duration = float(overcharge["description_value_07"])

    return [
        buff_rule("full_burst_enter", [
            ("pierce_damage_up", fb_pierce, "squad", fb_pierce_duration),
            ("crit_rate", fb_crit_rate, "squad", fb_crit_rate_duration),
        ]),
        # Pierce for 1 round: each ally's next shot (bullet-count grant).
        round_buff_rule("full_burst_enter",
                        [("pierce_damage_up", round_pierce, "squad")],
                        shots=round_pierce_rounds),
        buff_rule("own_burst_activate", [
            ("pierce_damage_up", burst_pierce, "squad", burst_pierce_duration),
        ]),
        # Overcharge Formula's "Additional Effect: Pierce" - the transform is
        # one charged shot, so the property covers exactly that round. Her
        # squad Pierce Damage buffs credit only allies who have Pierce too.
        round_buff_rule("own_burst_activate", [("has_pierce", 1.0, "self")], shots=1),
    ]


def build_pierce_equation_per_shot_rules(values):
    """Pierce Equation's second bullet: every normal attack DURING FULL BURST
    grants the squad Pierce Damage for 1 round (each ally's next shot), stacking
    up to slot 06 times per ally."""
    pierce = values["pierce_equation"]
    stack_pierce = float(pierce["description_value_05"]) / 100
    stack_cap = int(float(pierce["description_value_06"]))
    stack_rounds = int(float(pierce["description_value_07"]))

    return [(1, "every_during_full_burst", [
        round_buff_rule("per_shot", [("pierce_damage_up", stack_pierce, "squad")],
                        shots=stack_rounds, cap=stack_cap, from_own_shot=True),
    ])]


def build_frame_analysis_resources(values):
    """Frame Analysis's second bullet: a capped Crit Rate stack, one per normal
    attack she lands while Pierce Attacks 101 (her burst's 10-sec all-ally buff)
    is up, the stack living 5 sec.

    Those 5 sec are ONE clock every new stack restarts (`lifetime_refreshes`,
    the Raven ruling). Her SG fills the cap inside the window under either
    reading; what the shared clock changes is the TAIL - all three stacks fall
    off together 5 sec after her last shot in the window instead of decaying one
    at a time. The buff is squad-scoped, so that tail alone is worth +1.70% to
    the deck (`scripts/audit_stack_lifetime_refresh.py`).

    A stacking BUFF in the game's sense, so Flora's Petunia raises its count -
    confirmed in the range (Fienn, 2026-08-17): the count climbs while Zwei
    fires nothing herself, which only Flora's shots can explain."""
    frame = values["frame_analysis"]
    crit_rate_per_stack = float(frame["description_value_06"]) / 100
    cap = int(float(frame["description_value_08"]))
    stack_lifetime = float(frame["description_value_07"])
    status_duration = float(values["overcharge_formula"]["description_value_07"])

    return [
        ResourceSpec(
            name="pierce_attacks_101",
            fill=("per_shot_every_during_own_status_window", 1, status_duration),
            cap=cap,
            buffs=[linear_resource_buff("crit_rate", crit_rate_per_stack, "squad")],
            lifetime=stack_lifetime,
            lifetime_refreshes=True,
            stackable_buff=True,
        )
    ]


def build_overcharge_weapon_mode_schedule(values, slug="zwei"):
    """Overcharge Formula's self weapon transform: a charged Pierce shot at 50.69%
    of final ATK, 300% of that on Full Charge. The charge is 1.5 sec on the base
    build and 1.2 sec with the Favorite Item; both read slot 01.

    `slug` keys the burst schedule, so the signature build anchors on its own
    burst times rather than the base slug's (the laplace-signature precedent).

    "Max Ammunition Capacity: 1" is what bounds the window - the transformed
    weapon holds one round, so the transform is ONE shot per burst, not a
    duration (which the skill text indeed never states). That is the same shape,
    and the same text shape, as Maxwell's Pierce Shot, encoded the same way.

    The charge time goes in as `charge_time`, not `rate_of_fire`: unlike
    Nayuta's "Charge time: Fixed at 1.8 sec", nothing here pins the value, so an
    ally's Charge Speed buff should move it.

    `always_core_hit`: the transformed shot lands on the core in play (Fienn,
    in game, 2026-08-15). It has to be DECLARED because spread is looked up from
    the BASE weapon, and hers is a Shotgun - 250 units against a 48.89 core is a
    core hit rate of 0.038, so the approximation was costing this shot nearly
    all of its core bonus. Zwei is the widest-spread case in the table; the same
    reading settles Snow White (AR base) and, negatively, Grave and
    Jill: Valentine, whose transforms Fienn checked and found NOT core-locked.
    """
    overcharge = values["overcharge_formula"]
    profile = {
        "weapon": "SR",
        "damage_percent": float(overcharge["description_value_02"]),
        "charge_damage_percent": float(overcharge["description_value_03"]),
        "charge_time": float(overcharge["description_value_01"]),
        "always_core_hit": True,
    }

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": 1, "profile": profile}
                for t in context.burst_times.get(slug, [])]

    return schedule
