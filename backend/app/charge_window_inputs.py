"""Turns a roster entry into the calculator's WindowInputs.

Everything except two skill-text values is read from the loaders the recommender
already uses, so a re-measured charge time, a re-timed motion delay or a
re-synced overload roll moves the calculator with no edit here. The two
exceptions - Asura's magazine grant and Calm Depths' caster-based cut - are read
through the functions their own unit modules expose, which the rule builders
call too.
"""
from dataclasses import dataclass

from app.charge_window import WindowInputs, aggregate_charge_speed
from app.cube_effects import assumed_cube_effects
from app.overload_effects import NAME_TO_STAT
from app.skill_rules.liberalio import calm_depths_charge_cut_seconds
from app.skill_rules.registry import get_charge_motion_delay
from app.skill_rules.scarlet_black_shadow import full_burst_max_ammo_percent
from app.skill_values import DATA_DIR
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


def _overload_total(spec, stat):
    return sum(option.value for option in spec.overload_options
               if NAME_TO_STAT.get(option.name) == stat) / 100


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


def build_inputs(state, with_liberalio, overrides, liberalio_state=None,
                 data_dir=DATA_DIR):
    if state.character_slug not in CALCULATOR_SLUGS:
        raise ValueError(
            f"{state.character_slug} is not covered by the charge-window calculator")
    spec = load_nikke_spec(state, data_dir)
    if spec is None:
        raise ValueError(f"{state.character_slug} could not be loaded from local data")
    weapon = spec.weapon_stats

    if overrides.charge_speed_lines is None:
        charge_speed = _overload_total(spec, "charge_speed_percent")
    else:
        charge_speed = aggregate_charge_speed(
            overrides.charge_speed_lines, weapon["charge_time"])

    ammo_percent = (_overload_total(spec, "max_ammo_percent")
                    if overrides.max_ammo_percent is None else overrides.max_ammo_percent)
    reload_speed = (_cube_reload_speed(spec.slug)
                    if overrides.reload_speed_percent is None
                    else overrides.reload_speed_percent)

    # Strange Currents grants Liberalio immunity to external charge-speed
    # effects, so she can never receive her own grant - the toggle is refused
    # rather than hidden, because the API is callable without the UI.
    cut = 0.0
    if with_liberalio and spec.slug != LIBERALIO_SLUG:
        companion = load_nikke_spec(liberalio_state or state, data_dir,
                                    slug_override=LIBERALIO_SLUG)
        if companion is not None:
            cut = calm_depths_charge_cut_seconds(
                companion.skill_values, companion.weapon_stats)

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
