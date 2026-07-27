"""EVE (slug "eve"), a Burst-3 Iron AR attacker (burst cd 40s, base skills
only - no signature/Treasure weapon in the collected data).

Her damage outside the burst hangs off Unstable Energy, which triggers "after
landing 44 critical hit(s) with normal attacks". That counter is why she sat
deferred: the engine never rolls crit per hit (every hit's damage is scaled by
the expected crit factor), so there is no "this shot crit" event to count -
the same structural limit that permanently deferred Julia's signature
Crescendo/Marcato. Fienn's ruling (2026-07-20) reopened it with a condition:
an expected-value conversion is reasonable, but ONLY if the deck's crit-rate
buffs count. So the trigger is not folded into a fixed shot threshold at build
time (44 / 0.75 = 59 shots, which would silently ignore every ally crit
buffer); it rides the new `every_n_critical_hits` per-shot mode, which
accumulates the unit's LIVE crit rate shot by shot and fires whenever the
running total crosses 44. A deck with Miranda or Zwei in it therefore procs
Unstable Energy genuinely more often.

Modeled (DPS-relevant):
- Impact-Type Exospine (skills[0]) battle-start self Critical Rate +60%,
  permanent. This is also what makes her own baseline crit rate 75% (engine
  base 15%), i.e. ~59 shots per proc before any ally buffs.
- Unstable Energy (skills[0]): 240% of final ATK, 3 sequential hits, every 44
  expected crits. Emitted as 3 separate pulses at the same instant, not one
  720% hit, so enemy DEF is subtracted per hit like every other multi-hit nuke.
  Fired off her own shots, so the Full Burst bonus follows whichever of them
  land inside a window.
- Unstable Energy's rider: "when Unstable Energy hits an Electric Code target",
  Damage Taken +10% for 10 sec - gated on an Electric boss (engine gap #5
  convention, as with Brid / Helm: Aquamarine / Marciana).
- Eagle Eye-Type Exospine (skills[1]) battle-start self: flat ATK = 50% of her
  own ATK, and Max Ammunition Capacity +25%, both permanent. Max Ammo is a real
  DPS term here, not bookkeeping - it feeds shot generation (fewer reloads).
- Counter Chain (skills[2], her burst): 457.14% of final ATK, 6 sequential hits
  (`_BURST_HIT_COUNTS`).
- Exospine Mk2 (the burst's 10-sec self state) has two clauses, both modeled by
  deriving the scale from the skill's own slots rather than hardcoding a x2:
  Unstable Energy's per-hit multiplier is "scaled by 100%" (240% -> 480%) for
  procs landing inside the window, and Eagle Eye's ATK multiplier likewise
  (50% -> 100% of her own ATK). The latter is applied as an ADDITIONAL flat-ATK
  grant for 10 sec on top of the permanent battle-start one, which sums to the
  100% the Mk2 state describes. Fienn confirmed this reading from the Korean
  skill text (2026-07-20): the English "Damage multiplier of Eagle Eye-Type
  Exospine" is really skill 2's ATK buff, which Mk2 raises to 100%.

Not modeled / deferred:
- Eagle Eye's "when landing 10 normal attack(s) on an Electric Code target,
  Reloads 3 round(s)". Ammo/reload manipulation: the firing timeline is
  generated before per-shot rules run and rules explicitly must not change shot
  generation, so this is the same class of gap as Milk: Blooming Bunny's forced
  reload (engine-gaps #11). It would shorten reload downtime, so this encoding
  is a floor for her.
- Skill 1's "Previous effects trigger repeatedly" line carries no count or
  condition in the collected text (the `escalating_buff_rule` phrasing normally
  reads "Once/Twice/Three times, previous effects trigger repeatedly"). Left
  unmodeled rather than guessed at a stack count.
- "Affects random enemy units" targeting - a raid sim is a single boss, so
  every hit lands on the only target.

Numbers sourced from data/lootandwaifus/char_eve.json.
"""
from app.effects import Effect, Pulse
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "eve": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_eve",
        "keys": {
            "impact_exospine": ("skills", 0),
            "eagle_eye_exospine": ("skills", 1),
            "counter_chain": ("skills", 2),
        },
        # "Exospine Mk2" / "Impact-Type Exospine Mk2" / "Eagle Eye-Type Exospine
        # Mk2" - the "2" in each Mk2 is a name, not a skill value, and lands
        # between the real numbers.
        "drop_tokens": {"counter_chain": [2, 4, 6]},
    },
}

ELECTRIC = "Electric"  # the rider only fires against an Electric Code target

# "Attacks sequentially for 6 time(s)" - 6 at every skill level, so it is a
# constant here rather than a slot read (`get_burst_hit_count` takes no skill
# values), matching the Cinderella / Sakura hit-count precedent.
COUNTER_CHAIN_HIT_COUNT = 6


def _f(values, key, slot):
    return float(values[key][f"description_value_{slot:02d}"])


def counter_chain_burst_percent(values):
    return _f(values, "counter_chain", 1)


def _mk2_scale(values, slot):
    """Mk2's "scaled by 100%" clauses, as a multiplier on the base value."""
    return _f(values, "counter_chain", slot) / 100


def build_eve_rules(values):
    """Both Exospines' permanent battle-start self buffs, plus the Mk2 half of
    Eagle Eye that rides her burst. Unstable Energy is a per-shot rule (see
    `build_unstable_energy_per_shot_rules`) and Counter Chain's nuke is a plain
    burst percent, so neither is here."""
    caster_atk = values["caster_atk"]
    eagle_eye_atk = _f(values, "eagle_eye_exospine", 1) / 100 * caster_atk
    mk2_duration = _f(values, "counter_chain", 3)

    return [
        buff_rule("battle_start", [
            ("crit_rate", _f(values, "impact_exospine", 1) / 100, "self", None),
            ("flat_atk", eagle_eye_atk, "self", None),
            ("max_ammo_percent", _f(values, "eagle_eye_exospine", 2) / 100, "self", None),
        ]),
        # Mk2 raises Eagle Eye's ATK multiplier from 50% to 100% of her own ATK
        # for the window; the battle-start grant already supplies the first 50%.
        buff_rule("own_burst_activate", [
            ("flat_atk", eagle_eye_atk * _mk2_scale(values, 5), "self", mk2_duration),
        ]),
    ]


def build_unstable_energy_per_shot_rules(values):
    """Unstable Energy, on the new `every_n_critical_hits` mode: every 44
    EXPECTED critical hits (the engine's crit model has no per-hit roll - see
    the module docstring), 240% of final ATK in 3 sequential hits, doubled
    inside her burst's Exospine Mk2 window. The Electric-Code rider rides the
    same proc, so it shares one action rather than a second trigger entry."""
    crit_threshold = _f(values, "impact_exospine", 2)
    percent = _f(values, "impact_exospine", 3)
    hits = int(_f(values, "impact_exospine", 4))
    damage_taken = _f(values, "impact_exospine", 5) / 100
    debuff_duration = _f(values, "impact_exospine", 6)
    mk2_percent = percent * (1 + _mk2_scale(values, 4))
    mk2_duration = _f(values, "counter_chain", 3)

    def action(context, caster_slug, time, registry):
        in_mk2 = any(
            bt <= time < bt + mk2_duration
            for bt in context.burst_times.get(caster_slug, [])
        )
        hit_percent = mk2_percent if in_mk2 else percent
        for _ in range(hits):
            registry.add_pulse(
                Pulse("instant_damage_percent", hit_percent, "self", caster_slug)
            )
        if context.boss_element == ELECTRIC:
            registry.add(
                Effect("damage_taken_up", damage_taken, "squad", debuff_duration, caster_slug),
                applied_at=time,
            )

    return [(crit_threshold, "every_n_critical_hits", [
        SkillRule(trigger="per_shot", action=action),
    ])]
