"""Audit counted per-shot rules whose timed buffs stack instead of refreshing.

WHY: a `("every", N)` per-shot rule that grants a multi-second buff re-fires
long before the buff expires, so `buff_rule` sums the overlaps into a total the
game never shows. NIKKE marks the buffs that really do stack with an explicit
"Stacks up to N times" clause; a bullet without one refreshes, and must be
encoded with `refreshing_buff_rule`. Phantom's Thief's Vision was encoded the
stacking way and read self ATK +511% instead of +85.12%, which put her at #2 of
93 slugs in the damage sweep.

The audit cannot read the skill TEXT, so it reports every rule that stacks and
by how much - the encoder still has to open the description and decide whether
that stacking is the one the bullet asks for. Overlap factors near the bullet's
stated cap are usually intended; an uncapped ramp usually is not.

WHEN TO RUN: after encoding a Nikke with per-shot rules, and before shipping a
change to `_helpers.buff_rule` / `refreshing_buff_rule`.

Exit code is 1 when any rule stacks, so it reads as a checklist rather than a
gate - several stacking rules are correct.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.attack_rate import generate_shot_times
from app.effects import EffectRegistry
from app.skill_rules import registry as skill_registry
from app.skill_values import assemble_skill_values, load_weapon_data
from app.squad_engine import SquadContext, SquadMember, fire_trigger
from app.user_roster import _weapon_stats

# The stats a per-shot buff can grant that damage actually reads. Anything the
# damage formula ignores would be noise in this report.
DAMAGE_STATS = (
    "atk_percent", "flat_atk", "attack_damage_up", "crit_rate",
    "other_critical_damage_sources", "other_core_damage_sources",
    "distributed_damage_up", "sustained_damage_up", "true_damage_up",
    "pierce_damage_up", "damage_taken_up", "charge_damage_bonus",
    "attack_speed_percent", "charge_speed_percent", "enemy_def_percent",
)
MAX_SKILL_LEVELS = {"skill1": 10, "skill2": 10, "burst": 10}
FIGHT_DURATION = 180.0
# How many procs to walk. Long enough for the slowest counter here (Rosanna's
# 500th shot) to reach its steady state.
PROCS = 12


def _shot_times(slug, manifest):
    weapon = load_weapon_data(manifest, manifest.get("data_slug", slug))
    return weapon, generate_shot_times(
        weapon["weapon"], weapon["maxAmmo"], weapon["reloadTime"],
        weapon["chargeTime"], FIGHT_DURATION,
    )


def _with_caster_stats(values, weapon):
    """The caster base stats `roster` injects for skills that scale off them.

    Their magnitudes only set the SIZE of a grant, never whether re-applying it
    stacks, so a fixed stand-in roster answers this audit's question for every
    unit at once.
    """
    return {
        **values,
        "caster_atk": 60000.0,
        "caster_def": 5000.0,
        "caster_max_hp": 100000.0,
        "caster_weapon_stats": _weapon_stats(weapon),
        "caster_charge_damage_multiplier": 1.0,
    }


def _live_totals(registry, who, time):
    return {stat: registry.total_for(stat, who, time) for stat in DAMAGE_STATS}


def _audit_rule(slug, weapon, shot_times, every, rules):
    """Peak live total across `PROCS` procs vs. what one proc alone grants."""
    procs = [shot_times[i] for i in range(every - 1, len(shot_times), every)][:PROCS]
    if len(procs) < 2:
        return None, "fewer than 2 procs in a 180s fight"
    context = SquadContext([
        SquadMember(slug, burst_tier=3, element="Water", weapon=weapon["weapon"]),
    ])
    who = {"slug": slug, "element": "Water"}

    alone = EffectRegistry()
    fire_trigger("per_shot", {slug: rules}, context, alone, procs[0])
    single = {s: v for s, v in _live_totals(alone, who, procs[0]).items() if v}

    repeated = EffectRegistry()
    peak = dict.fromkeys(single, 0.0)
    for time in procs:
        fire_trigger("per_shot", {slug: rules}, context, repeated, time)
        for stat, value in _live_totals(repeated, who, time).items():
            if stat in peak:
                peak[stat] = max(peak[stat], value)

    gap = procs[1] - procs[0]
    overlaps = {
        stat: (single[stat], peak[stat])
        for stat in single
        if peak[stat] > single[stat] * 1.001
    }
    return (gap, overlaps), None


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--slug", help="audit one slug instead of every encoded unit")
    args = parser.parse_args()

    slugs = sorted(skill_registry._PER_SHOT_RULE_BUILDERS)
    if args.slug:
        if args.slug not in slugs:
            parser.error(f"{args.slug} has no per-shot rules "
                         f"(encoded units with them: {', '.join(slugs)})")
        slugs = [args.slug]

    stacking, skipped = [], []
    for slug in slugs:
        try:
            manifest = skill_registry.get_skill_value_manifest(slug)
            values = assemble_skill_values(slug, manifest, MAX_SKILL_LEVELS)
            weapon, shot_times = _shot_times(slug, manifest)
            spec = skill_registry._PER_SHOT_RULE_BUILDERS[slug](
                _with_caster_stats(values, weapon))
        except Exception as error:
            skipped.append((slug, f"{type(error).__name__}: {error}"))
            continue
        for item in spec:
            if not (isinstance(item, tuple) and len(item) == 3 and item[1] == "every"):
                continue
            every, _mode, rules = item
            try:
                result, reason = _audit_rule(slug, weapon, shot_times, every, rules)
            except Exception as error:
                skipped.append((f"{slug} every {every}", f"{type(error).__name__}: {error}"))
                continue
            if result is None:
                skipped.append((f"{slug} every {every}", reason))
                continue
            gap, overlaps = result
            if overlaps:
                stacking.append((slug, every, gap, overlaps))

    print(f"audited {len(slugs)} slug(s) with per-shot rules\n")
    if stacking:
        print("STACKING - confirm each against the bullet's own text:")
        for slug, every, gap, overlaps in stacking:
            print(f"  {slug}  every {every} shots (a proc every {gap:.2f}s)")
            for stat, (one, peak) in sorted(overlaps.items()):
                print(f"      {stat}: one proc {one:.4f} -> peak {peak:.4f}  (x{peak / one:.2f})")
    else:
        print("no counted per-shot rule stacks its timed buffs")
    if skipped:
        print("\nNOT AUDITED - these are unanswered, not clean:")
        for what, reason in skipped:
            print(f"  {what}: {reason}")
    return 1 if stacking else 0


if __name__ == "__main__":
    sys.exit(main())
