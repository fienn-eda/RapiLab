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

Step 2 precedent check - "Activates when entering Burst Stage 3" (Shades of
White's self ATK +73.92%/10s, skills[1], not her burst skill): the same
phrase appears verbatim in cinderella.py's Flawless Glass (skills[0]) and
ein.py's Feather Standby (skills[0]), both self-scoped and both modeled as
`own_burst_activate` with the reasoning "she IS the Burst-3 slot, so that
instant is her own burst activation" (ein.py). rei_ayanami.py's Attack
Support uses the SAME phrase but is modeled as `full_burst_enter` instead -
its buff scope is squad-wide (all Fire Code allies), not self, so it has to
fire on ANY unit's Burst Stage 3 entry, not just Rei's own. Snow White: Heavy
Arms's B3-entry buff is self-scoped like Cinderella's/Ein's, so it follows
their precedent: `own_burst_activate`. (nayuta.py's "stage3" naming, also
turned up by the grep, is an unrelated internal resource-tier mechanic - her
own 30-stack Memory Absorption counter - not the Burst-Stage-3 cascade, so
it isn't a real precedent for this trigger despite the name collision.)
Approximation implication: this buff only fires on cycles where she actually
casts her own burst - since her Burst Skill is fixed at position 3 (a game
attribute, not a deck-configurable seat), that's every cycle she reaches
Full Burst, same as any other own_burst_activate bullet in this kit.

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
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule

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
        buff_rule("own_burst_activate", [
            ("attack_damage_up", float(burst["description_value_01"]) / 100, "self",
             float(burst["description_value_02"])),
            # Shades of White's "entering Burst Stage 3" self ATK - see the
            # Step 2 precedent note in the module docstring.
            ("atk_percent", float(shades["description_value_08"]) / 100, "self",
             float(shades["description_value_09"])),
        ]),
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
    return [
        (1, "every", [charge_window_buffs]),
        (1, "every_outside_segment",
         [instant_nuke_pulse_rule("per_shot", all_hit + base_ammo * seq_hit)]),
        (1, "every_during_segment",
         [instant_nuke_pulse_rule("per_shot",
                                  all_hit + boosted_ammo * seq_hit * (1 + seq_up))]),
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
