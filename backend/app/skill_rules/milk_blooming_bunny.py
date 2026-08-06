"""Milk: Blooming Bunny (slug "milk-blooming-bunny"), a Burst-3 Iron SR
attacker (burst cd 40s, base skills only).

Her kit is a two-state loop, and it was the last unit blocked by
engine-gaps #11 ("forced reload / ammo removal state machine"). That gap turned
out to be much smaller than recorded once the loop was pinned down:

- Embarrassment only ENTERS "when not in the Embarrassment state", and Fienn's
  ruling (2026-07-20) is that only her burst's Overconfident immunity clears
  it. So the state is entered exactly ONCE per own burst, not re-triggered on
  every full charge - the ammo dump and forced reload are a single bounded
  event per burst, not a per-shot loop.
- "Removes 100% of ammo" + "Forced Reload" is what a weapon-mode SEGMENT
  boundary already does: `_base_shot_records` restarts each stretch with a
  fresh magazine at the stretch's start (the post-transform resume semantic).
  A segment covering exactly the forced reload, firing no shots of its own,
  therefore models "magazine discarded here, reloading, fresh magazine after".
- "Reload speed is fixed at a 50% reduction" is 3s against her 2s base in game
  (Fienn), which is what `attack_rate.reload_time_with_speed`'s negative branch
  now returns. Her forced-reload window length is derived through it rather
  than hardcoded.

Timeline per own burst at `bt` (all derived from slots / her weapon, not
hardcoded): Overconfident immunity covers `bt .. bt + 10`; she then spends one
full charge plus the 0.5s hold that arms the trigger, so Embarrassment enters at
`bt + 11.5` and its forced reload runs to `bt + 14.5`. The state itself then
holds until her next burst.

Modeled (DPS-relevant):
- Embarrassment entry (skills[0]): 290% of final ATK as Distributed Damage to
  all enemies, once per entry (`scheduled_nukes`, typed "distributed" so the
  `distributed_damage_up` bucket applies).
- Embarrassment entry: self ATK +118.7% for 40 sec, and Outburst's (skills[1])
  "Pierce Damage +64.7% continuously while in Embarrassment status" for as long
  as the state lasts - both via `burst_anchored_buffs`, the latter with
  `UNTIL_NEXT_OWN_BURST` since that is literally what ends the state. Note the
  ATK buff's fixed 40s is SHORTER than her typical re-burst gap, so it lapses
  before the state does; that is what the skill text says, not an approximation.
- The forced reload itself: a zero-shot `weapon_mode_schedules` segment over
  `[entry, entry + forced reload]`. The segment profile uses an explicit
  `rate_of_fire` slow enough that no shot fits, because explicit-rate profiles
  deliberately take NO cadence buffs - a charge-time profile would shrink under
  an ally's Charge Speed buff and could leak a phantom shot into the window.
- Embarrassment Explosion (skills[2], her burst): self Pierce Damage +117.64%
  and ATK +220%, both 10 sec. The burst itself deals no direct damage.
- Outburst's Overconfident clause: 447.7% of final ATK as Distributed Damage
  "every 2 sec" while the 10-sec Overconfident status is up - 5 ticks per burst,
  at `bt + 2 .. bt + 10` (the status starts at the burst, so the first tick is
  one full interval in).

- "Gain Pierce for 6 sec" on every full charge (skills[0]): the `has_pierce`
  property, which is what lets her two "Pierce Damage +X%" clauses pay out at
  all. She is an SR, so every shot IS a full charge and 6 sec is far longer
  than her cadence - the window never lapses, so it is granted permanently from
  battle start rather than re-applied per shot.

Not modeled / deferred:
- Distributed Damage's "all enemies" split: a raid sim is a single boss, so
  every instance lands whole on the only target (existing convention).
- The player choice not to arm Embarrassment before a cycle she will burst in
  (Fienn: it is better not to trigger it then) is implicit in the schedule -
  the state is only ever entered after her own burst, which is the same thing.

Numbers sourced from data/lootandwaifus/char_milk-blooming-bunny.json;
weapon stats from data/dotgg/char_milk-blooming-bunny.json.
"""
from app.attack_rate import reload_time_with_speed
from app.raid_simulator import UNTIL_NEXT_OWN_BURST
from app.skill_rules._helpers import buff_rule

SKILL_VALUE_MANIFESTS = {
    "milk-blooming-bunny": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_milk_blooming_bunny",
        "keys": {
            "embarrassment_suppression": ("skills", 0),
            "outburst": ("skills", 1),
            "embarrassment_explosion": ("skills", 2),
        },
        # "Effect 1:" .. "Effect 5:" are clause labels, not skill values, and
        # they interleave with the real numbers.
        "drop_tokens": {"embarrassment_suppression": [2, 4, 6, 9, 10]},
    },
}

OVERCONFIDENT_TICKS = 5  # 10-sec status, one Distributed tick every 2 sec


def _f(values, key, slot):
    return float(values[key][f"description_value_{slot:02d}"])


def _forced_reload_seconds(values):
    """The forced reload's length: her weapon's own reload time under the
    "fixed at a 50% reduction" clause, through the engine's two-directional
    reload-speed formula (2s base -> 3s, matching Fienn's in-game reading)."""
    reload_time = values["caster_weapon_stats"]["reload_time"]
    reduction = _f(values, "embarrassment_suppression", 5) / 100
    return reload_time_with_speed(reload_time, -reduction)


def embarrassment_entry_offset(values):
    """Seconds after her own burst that Embarrassment is entered: the burst's
    Overconfident immunity has to lapse first, then she needs one full charge
    and the 0.5s hold that arms the trigger."""
    immunity = _f(values, "embarrassment_explosion", 1)
    charge_time = values["caster_weapon_stats"]["charge_time"]
    hold = _f(values, "embarrassment_suppression", 2)
    return immunity + charge_time + hold


def build_milk_rules(values):
    """Embarrassment Explosion, her burst: Overconfident's two self buffs. The
    burst deals no direct damage - its Distributed ticks are scheduled nukes."""
    return [
        buff_rule("own_burst_activate", [
            ("pierce_damage_up", _f(values, "embarrassment_explosion", 2) / 100, "self",
             _f(values, "embarrassment_explosion", 3)),
            ("atk_percent", _f(values, "embarrassment_explosion", 4) / 100, "self",
             _f(values, "embarrassment_explosion", 5)),
        ]),
        # Embarrassment Suppression: "Gain Pierce for 6 sec" on every Full
        # Charge. Her every shot IS a full charge, so the window never lapses
        # - permanent from battle start is the same outcome, and it is what
        # makes the Pierce Damage above (and Bunny allies' buffs) count.
        buff_rule("battle_start", [("has_pierce", 1.0, "self", None)]),
    ]


def build_milk_burst_anchored_buffs(values):
    """The Embarrassment state's two buffs, both landing at the entry offset:
    ATK for its own fixed 40 sec, and Outburst's Pierce Damage for as long as
    the state itself lasts (i.e. until her next burst clears it)."""
    offset = embarrassment_entry_offset(values)
    return [
        {
            "offset": offset,
            "stat": "atk_percent",
            "value": _f(values, "embarrassment_suppression", 7) / 100,
            "scope": "self",
            "duration": _f(values, "embarrassment_suppression", 8),
        },
        {
            "offset": offset,
            "stat": "pierce_damage_up",
            "value": _f(values, "outburst", 1) / 100,
            "scope": "self",
            "duration": UNTIL_NEXT_OWN_BURST,
        },
    ]


def build_milk_weapon_mode_schedule(values):
    """The forced reload, as a segment that fires nothing: entering the segment
    discards whatever is left in her magazine and the base weapon resumes with a
    fresh one when it ends. `rate_of_fire` (not `charge_time`) so the empty
    window cannot be shrunk by an ally's Charge Speed buff into leaking a shot."""
    offset = embarrassment_entry_offset(values)
    reload_seconds = _forced_reload_seconds(values)
    weapon = values["caster_weapon_stats"]["weapon"]

    def schedule(context, fight_duration):
        segments = []
        for burst_time in context.burst_times.get("milk-blooming-bunny", []):
            start = burst_time + offset
            if start >= fight_duration:
                continue
            segments.append({
                "start": start,
                "end": min(start + reload_seconds, fight_duration),
                "profile": {
                    "weapon": weapon,
                    "damage_percent": 0.0,
                    "rate_of_fire": 1.0 / (reload_seconds * 2),
                },
            })
        return segments

    return schedule


def build_milk_scheduled_nukes(values):
    """Two Distributed Damage sources: one 290% hit at each Embarrassment entry,
    and Overconfident's 447.7% every 2 sec across her burst's 10-sec status."""
    entry_offset = embarrassment_entry_offset(values)
    tick_interval = _f(values, "outburst", 2)

    def entry_schedule(context, fight_duration):
        return [
            bt + entry_offset
            for bt in context.burst_times.get("milk-blooming-bunny", [])
            if bt + entry_offset < fight_duration
        ]

    def overconfident_schedule(context, fight_duration):
        times = []
        for bt in context.burst_times.get("milk-blooming-bunny", []):
            times.extend(
                bt + tick_interval * k
                for k in range(1, OVERCONFIDENT_TICKS + 1)
                if bt + tick_interval * k < fight_duration
            )
        return times

    return [
        {
            "schedule": entry_schedule,
            "percent": _f(values, "embarrassment_suppression", 3),
            "damage_type": "distributed",
        },
        {
            "schedule": overconfident_schedule,
            "percent": _f(values, "outburst", 3),
            "damage_type": "distributed",
        },
    ]
