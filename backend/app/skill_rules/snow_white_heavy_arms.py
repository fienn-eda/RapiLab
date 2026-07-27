"""Snow White: Heavy Arms (slug "snow-white-heavy-arms"), a Burst-3 Water SR
attacker - the charge-loop kit the weapon-transform design's verification
pass had deferred as possibly needing a new state machine. It doesn't: every
full charge fires Auto Fire (41.9% all-enemy hit + 105.59% x loaded-ammo
sequential hits, ALL landing on the single raid boss - Fienn 2026-07-19), and
Seven Dwarves Fully Active is a weapon-mode segment (2 shots at 3.2s charge,
+528% charge damage folded into the profile's charge_damage_percent so deck
charge buffs still stack on top) whose empowered Auto Fire rides the
every_during_segment per-shot mode - the outside/during split (Task 8) makes
double-counting structurally impossible.

Lock-on/ammo accrual is deterministic: 0.2s ticks during charge reach the
5-round cap within the 1.2s base charge (6 ticks) and the 15-round boosted cap
within 3.2s (16 ticks), so loaded ammo is a constant per mode.

The lock-on "Damage Taken up 4.2% for 4s" tick is approximated as a permanent
squad-scope debuff (charging uptime is ~100%, 4s duration >> 0.2s tick -
Fienn, 2026-07-19).

"Activates when entering Burst Stage 3" (Shades of White's self ATK
+73.92%/10s, skills[1], not her burst skill) is about the STAGE, not about
her: it fires in every cycle a Burst 3 takes the slot, including the cycles an
ALLIED Burst 3 takes. Hence `ally_burst_activate` + `burst_stage_entered(3)`
rather than `own_burst_activate`, which would silently drop those cycles - in
a deck where she alternates the B3 seat with another Burst 3 (e.g. Cinderella)
that is half of them. Scope is irrelevant to this choice: a self-scoped buff
on a stage event is still a stage event, it just lands on one unit. Her burst
skill's OWN buff (Fully Active, skills[2]) is a different instant and stays on
`own_burst_activate` - the two bullets were wired to one rule until 2026-07-27
and had to be split. See docs/insights.md for the general trigger rule and the
five units it corrected.

Modeled (DPS-relevant):
- Seven Dwarves V+VI (skills[0]): battle-start squad Damage Taken +4.2%
  (permanent approximation, see above). Auto Fire per-shot pulses (see below).
- Shades of White (skills[1]): charge-window refreshing self ATK +46.84%/5s
  and Damage to Parts +62.64%/5s (fires every shot - the 1.2s/3.2s charge
  cadence never lets the 5s window lapse); self ATK +73.92%/10s on entering
  Burst Stage 3 (own_burst_activate, see precedent note above); Fully-Active-
  only Charge Damage +528%/1 round and Sequential attack damage +158.4%/1
  round, folded into the Fully Active segment profile and the boosted Auto
  Fire pulse respectively (both are always-on for a Fully Active shot, so
  "1 round" collapses to "every Fully Active shot").
- Seven Dwarves Fully Active (skills[2], her burst, cd 40): self Attack
  Damage +84.48%/10s (own_burst_activate) plus the weapon-mode segment: 2
  shots at a fixed 3.2s charge, folding the caster's own 250% base full-
  charge damage with Shades of White's +528% Fully Active bonus into one
  778% charge_damage_percent (weapon_mode_schedules).
- Auto Fire (per-shot, riding every full charge): 41.9% all-enemy-hit +
  (loaded ammo x 105.59%) sequential hit, ALL landing on the boss. Outside
  a Fully Active segment: 5 loaded ammo, plain. Inside one: 15 loaded ammo x
  (1 + 158.4% Sequential attack damage) - `every_during_segment` /
  `every_outside_segment` (Task 8) keep these mutually exclusive per shot.

Deferred: DEF up 42.24% (defensive, inert), Pierce (convention, same as
Red Hood/Snow White's Pierce bullets - no engine representation), the 41.9%
destructible-projectile sweep (no destructible projectiles modeled), Lock-On
multi-target bookkeeping (single raid boss collapses "up to 5/10 targets" to
one target, same as every other multi-target Lock-On kit in this engine).

RANGE-TESTED AND CORRECTED (Fienn, 2026-07-28 - Rapi + Crown + her, non-core
normal attacks). Everything about Auto Fire's SHAPE was already right and is now
sourced rather than assumed:

- Five sequential hits outside Fully Active, fifteen inside - counted in game.
- One Auto Fire hit reads 2.52005x the 41.9% all-enemy sweep, against a bare
  coefficient ratio of 105.59 / 41.9 = 2.52005. Exact.
- The sweep reads 0.22175x her normal attack outside the segment and 0.07570x
  inside it, against 0.419 / (0.6904 x 2.73675) = 0.22176 and
  0.419 / (0.6904 x 8.01675) = 0.07570 - which also confirms the Fully Active
  profile's 273.675 + 528 charge damage, collectible included.
- Crit reads 1.586x outside a Full Burst window and 1.39067x inside one, i.e.
  (1 + 0.5 + 0.086) and (1.5 + 0.5 + 0.086) / 1.5 - her 8.6% crit-damage
  overload, and an independent re-confirmation of the Full Burst bonus.

What was WRONG was "Sequential attack damage 158.4%". It was folded into the
volley's coefficient as x2.584; the measurement puts the Fully Active hit at
4.26515x the sweep where the bare coefficients give 2.52005x, so the bullet is
worth 1.69249x - and 1 + 1.584 / (1 + 1.2874) = 1.69249 against the engine's own
live Damage-Up bucket at that instant. It is an ADDITIVE bucket term, not a
coefficient multiplier, and the engine was over-counting her Fully Active Auto
Fire by 2.584 / 1.69249 = 1.527x. She read 1.424x of her record; she now reads
1.152x.

Hence the split below: the sweep is not a sequential attack and keeps the plain
type, while the volley carries damage_type "sequential" so the type-gated
`sequential_attack_damage_up` reaches it and nothing else.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule
from app.squad_engine import burst_stage_entered

SHADES_BURST_STAGE = 3  # skill text: "when entering Burst Stage 3" (fixed, not a data slot)

SKILL_VALUE_MANIFESTS = {
    "snow-white-heavy-arms": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_snow_white_heavy_arms",
        "keys": {
            "seven_dwarves": ("skills", 0),
            "shades_of_white": ("skills", 1),
            "fully_active": ("skills", 2),
        },
    },
}


def build_snow_white_heavy_arms_rules(values):
    dwarves = values["seven_dwarves"]
    shades = values["shades_of_white"]
    burst = values["fully_active"]
    return [
        buff_rule("battle_start", [
            ("damage_taken_up", float(dwarves["description_value_07"]) / 100, "squad", None),
        ]),
        # Fully Active is her OWN burst skill's buff, so it rides her own cast.
        buff_rule("own_burst_activate", [
            ("attack_damage_up", float(burst["description_value_01"]) / 100, "self",
             float(burst["description_value_02"])),
        ]),
        # Shades of White's self ATK says "when entering Burst Stage 3" - the
        # STAGE, so it also fires in cycles an allied Burst 3 takes the slot,
        # and it lands one beat before that cast settles.
        buff_rule("ally_burst_activate", [
            ("atk_percent", float(shades["description_value_08"]) / 100, "self",
             float(shades["description_value_09"])),
        ], condition=burst_stage_entered(SHADES_BURST_STAGE)),
    ]


def build_seven_dwarves_per_shot_rules(values):
    dwarves = values["seven_dwarves"]
    shades = values["shades_of_white"]
    burst = values["fully_active"]
    all_hit = float(dwarves["description_value_10"])
    seq_hit = float(dwarves["description_value_12"])
    base_ammo = int(float(dwarves["description_value_05"]))
    boosted_ammo = base_ammo + int(float(burst["description_value_09"]))
    seq_up = float(shades["description_value_12"]) / 100
    charge_window_buffs = refreshing_buff_rule("per_shot", [
        ("atk_percent", float(shades["description_value_03"]) / 100, "self",
         float(shades["description_value_04"])),
        ("damage_to_parts_up", float(shades["description_value_05"]) / 100, "self",
         float(shades["description_value_06"])),
        # "Gains Pierce for 5 sec" from the same Full-Charge bullet: her
        # charge is fixed at 1.2 sec, so refreshing per shot holds it open.
        ("has_pierce", 1.0, "self", float(shades["description_value_04"])),
    ])
    # Fully Active's "Sequential attack damage 158.4%" lands in the shared
    # Damage-Up bucket, so the sequential volley is emitted as its own
    # type-gated pulse instead of being folded into the coefficient. The
    # all-enemy 41.9% sweep is NOT a sequential attack and stays plain, which
    # is why the two split here rather than riding one pulse.
    # "for 1 round(s)" on a shot that must cover its OWN Auto Fire (Fienn's
    # reading shows the granting charge's volley already carries it), so this
    # cannot be a round grant - those cover the NEXT shots. Bounded by her base
    # charge time instead: the base cadence resumes exactly one base charge
    # after the segment's last shot, and the effect window is half-open, so the
    # first post-segment shot lands precisely on the expiry and is excluded.
    # Segment shots are 3.2 sec apart, so each simply re-grants it.
    base_charge = float(values["caster_weapon_stats"]["charge_time"])
    sequential_up = refreshing_buff_rule("per_shot", [
        ("sequential_attack_damage_up", seq_up, "self", base_charge),
    ])
    return [
        (1, "every", [charge_window_buffs]),
        (1, "every_outside_segment",
         [instant_nuke_pulse_rule("per_shot", all_hit),
          instant_nuke_pulse_rule("per_shot", base_ammo * seq_hit,
                                  damage_type="sequential")]),
        (1, "every_during_segment",
         [sequential_up,
          instant_nuke_pulse_rule("per_shot", all_hit),
          instant_nuke_pulse_rule("per_shot", boosted_ammo * seq_hit,
                                  damage_type="sequential")]),
    ]


def build_fully_active_weapon_mode_schedule(values):
    shades = values["shades_of_white"]
    burst = values["fully_active"]
    weapon = values["caster_weapon_stats"]
    profile = {
        "weapon": weapon["weapon"],
        "damage_percent": weapon["damage_percent"],
        "charge_damage_percent": weapon["charge_damage_percent"]
        + float(shades["description_value_10"]),
        "charge_time": float(burst["description_value_05"]),
    }
    uses = int(float(burst["description_value_03"]))

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": uses, "profile": profile}
                for t in context.burst_times.get("snow-white-heavy-arms", [])]

    return schedule
