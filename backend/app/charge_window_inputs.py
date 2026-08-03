"""Turns a roster entry into the calculator's WindowInputs.

Everything except one skill-text value is read from the loaders the recommender
already uses, so a re-measured charge time, a re-timed motion delay or a
re-synced overload roll moves the calculator with no edit here. The exception -
Asura's magazine grant - is read through the function her own unit module
exposes, which her rule builder calls too. Calm Depths' cut is not read at all:
its rule is fired through the engine and whatever it grants is what the
calculator applies, because WHO receives it is itself part of the rule.
"""
from dataclasses import dataclass

from app.charge_window import WindowInputs, aggregate_charge_speed
from app.cube_effects import assumed_cube_effects
from app.effects import EffectRegistry
from app.overload_effects import NAME_TO_STAT
from app.roster import assemble_simulation_inputs
from app.skill_rules.registry import get_charge_motion_delay
from app.skill_rules.scarlet_black_shadow import full_burst_max_ammo_percent
from app.skill_values import DATA_DIR
from app.squad_engine import SquadContext, SquadMember, fire_trigger
from app.user_roster import load_nikke_spec

SCARLET_SLUG = "scarlet-black-shadow"
LIBERALIO_SLUG = "liberalio"
NEON_SLUG = "neon-vision-eye"

# The units this calculator answers for: every one is a charge weapon whose kit
# fires something on each Full Charge, which is what makes "how many shots"
# equal "how much damage" for them.
CALCULATOR_SLUGS = (SCARLET_SLUG, LIBERALIO_SLUG, NEON_SLUG)


@dataclass(frozen=True)
class Overrides:
    """What the user typed over the synced roster. None means "use the roster".

    The roster snapshot goes stale the moment gear changes, and for this screen
    that is the normal state rather than an error - Fienn's own measured runs
    already used a bigger magazine than his last sync recorded.
    """
    charge_speed_lines: list[float] | None
    max_ammo_percent: float | None
    reload_speed_percent: float | None


def _overload_lines(spec, stat):
    """The roster's rolled values for one stat, in percent.

    A synced option carries the per-gear rolls it was summed from, and those are
    what charge speed rounds over. Without them the total is the only roll the
    caller can see - which is exactly as much as that roster knows.
    """
    lines = []
    for option in spec.overload_options:
        if NAME_TO_STAT.get(option.name) != stat:
            continue
        rolls = getattr(option, "lines", None)
        lines.extend([line.value for line in rolls] if rolls else [option.value])
    return lines


def charge_speed_rolls_known(spec) -> bool:
    """Whether the individual charge-speed rolls are known, or only their total.

    The rounding is per roll, so a total several roll combinations could have
    produced leaves the frame count uncertain by one - the UI says so rather
    than presenting an estimate as a reading.
    """
    for option in spec.overload_options:
        if NAME_TO_STAT.get(option.name) == "charge_speed_percent":
            return bool(getattr(option, "lines", None))
    return True  # no charge-speed overload at all: nothing to be unsure about


def _overload_total(spec, stat):
    return sum(_overload_lines(spec, stat)) / 100


def _cube_reload_speed(slug):
    for effect in assumed_cube_effects(slug):
        if effect.stat == "reload_speed_percent":
            return effect.value
    return 0.0


def _self_max_ammo_percent(spec):
    """Magazine grants the unit gives ITSELF inside the window. Only Scarlet has
    one; Liberalio and Neon fight the window on their base magazine."""
    if spec.slug == SCARLET_SLUG:
        return full_burst_max_ammo_percent(spec.skill_values)
    return 0.0


def calm_depths_cut_for(spec, companion) -> float:
    """The seconds Calm Depths actually hands THIS unit - asked of the engine.

    Which Burst 3 wins the grant is a ranking on FINAL ATK at Full Burst entry,
    not on the roster's base ATK: Calm Depths hands Liberalio herself +160% at
    that moment, and the subject's own burst is live in the window it is being
    measured in. A comparison rebuilt here would be a second copy of the rule
    the deck search already owns, and it would answer differently - Fienn's own
    roster has Scarlet out-BASING her while she out-finals Scarlet, which is
    what his 0.7323 -> 0.5424 sec measurement records.

    So the two units are assembled and their triggers fired the way the
    simulator fires them, and whoever the rule picks is who the calculator
    buffs. Her Strange Currents immunity rides along for free: when she wins her
    own grant it lands nowhere.
    """
    engine = assemble_simulation_inputs([spec, companion])
    context = SquadContext(
        [SquadMember(member["slug"], burst_tier=member["burst_tier"],
                     element=member["element"])
         for member in engine["deck"]],
        base_atk={slug: stats["atk"] for slug, stats in engine["base_stats"].items()},
    )
    registry = EffectRegistry()
    rules = engine["rules_by_slug"]
    fire_trigger("battle_start", rules, context, registry, time=0.0)
    # Her burst only ever raises her ATK, which is the direction that can COST
    # her the grant - so leaving it out would be an over-estimate, not a
    # conservative one.
    fire_trigger("own_burst_activate", {spec.slug: rules.get(spec.slug, [])},
                 context, registry, time=0.0)
    fire_trigger("full_burst_enter", rules, context, registry, time=0.0)
    return registry.total_for("charge_time_reduction_sec",
                              {"slug": spec.slug, "element": spec.element}, now=0.0)


def build_inputs(state, with_liberalio, overrides, liberalio_state=None,
                 data_dir=DATA_DIR):
    if state.character_slug not in CALCULATOR_SLUGS:
        raise ValueError(
            f"{state.character_slug} is not covered by the charge-window calculator")
    spec = load_nikke_spec(state, data_dir)
    if spec is None:
        raise ValueError(f"{state.character_slug} could not be loaded from local data")
    weapon = spec.weapon_stats

    # Both paths aggregate through the same function, so the per-roll rounding
    # rule lives in `aggregate_charge_speed` and nowhere else.
    lines = (_overload_lines(spec, "charge_speed_percent")
             if overrides.charge_speed_lines is None else overrides.charge_speed_lines)
    charge_speed = aggregate_charge_speed(lines)

    ammo_percent = (_overload_total(spec, "max_ammo_percent")
                    if overrides.max_ammo_percent is None else overrides.max_ammo_percent)
    reload_speed = (_cube_reload_speed(spec.slug)
                    if overrides.reload_speed_percent is None
                    else overrides.reload_speed_percent)

    # Strange Currents grants Liberalio immunity to external charge-speed
    # effects, so she can never receive her own grant - the toggle is refused
    # rather than hidden, because the API is callable without the UI.
    #
    # Her grant is built from HER skill levels and collectible, so a roster
    # without her cannot produce one. The window is still worth answering
    # un-buffed, so the cut is dropped and the caller says so.
    cut = 0.0
    if with_liberalio and spec.slug != LIBERALIO_SLUG and liberalio_state is not None:
        companion = load_nikke_spec(liberalio_state, data_dir,
                                    slug_override=LIBERALIO_SLUG)
        if companion is not None:
            cut = calm_depths_cut_for(spec, companion)

    total_ammo_percent = ammo_percent + _self_max_ammo_percent(spec)
    return WindowInputs(
        charge_time=weapon["charge_time"],
        motion_delay=get_charge_motion_delay(spec.slug),
        max_ammo=max(1, round(weapon["max_ammo"] * (1 + total_ammo_percent))),
        reload_time=weapon["reload_time"],
        charge_speed_percent=charge_speed,
        charge_time_reduction_sec=cut,
        reload_speed_percent=reload_speed,
    )
