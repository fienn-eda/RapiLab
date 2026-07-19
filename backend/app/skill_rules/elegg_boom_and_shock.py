"""Elegg: Boom and Shock (slug "elegg-boom-and-shock"), a Burst-3 Water MG
attacker (Missilis, burst cd 40s, no signature weapon - base skills only).

Her whole kit hangs off one named resource, Ghosts (cap 13): a possession
window recurs every 6s and captures 1 ghost once the squad lands 100
cumulative hits inside it, ghost count drives two continuous Water-Code
squad buffs, and her burst spends ghosts for a hit count that branches at
the cap.

Modeled (DPS-relevant):
- Hello Ghost (skills[0]) ghost capture: modeled as a plain
  `("periodic", 6.0)` resource fill, cap 13. The skill's real gate is "100
  hits in total, cumulative across all allies" per 6s window; Fienn's ruling
  (2026-07-19) is that Elegg alone always clears it - she is an MG firing at
  60 rounds/sec, so 100 squad hits inside 6 seconds is never the binding
  constraint. Encoding the squad-wide hit counter (as Little Mermaid's
  Bubble Barrage does) would add machinery for a condition that is always
  true, so the fill is deterministic instead. Documented as an approximation
  because a hypothetical all-SR/RL deck could in principle miss it.
- Hello Ghost's ghost-count buffs, both `element:Water` scope (she is Water,
  so they include her) and both continuous (`lifetime=None`), emitted as
  threshold `ResourceBuff`s off the ghost count:
    1+ ghosts: flat ATK = 16.2% of Elegg's own base ATK.
    4+ ghosts: Elemental Advantage Attack Damage +35%.
- Ghostbuster (skills[1]) burst self-buff: ATK +40% for 10 sec on
  `own_burst_activate`.
- Ghostbuster's overflow nuke: "when a ghost is captured while at maximum
  ghost capacity", 1100% of final ATK to all enemies. With a deterministic
  fill this is exactly "every 6s tick that lands while the count is already
  13", so it's a `scheduled_nukes` schedule that reads the resolved ghost
  count at each tick (resources resolve before scheduled nukes in
  `simulate_raid`, so the count is populated by then).
- 13 Ghosts (her burst, skills[2]): 800% of final ATK per hit, fired as a
  `dynamic_hit_count_nukes` spec whose `hit_count_fn` branches on the ghost
  count - 13 sequential hits at the 13 cap, 6 hits below it - paired with an
  `own_burst` reset whose `value_fn` spends 9 at the cap and 6 below it,
  floored at 1 ("Maintains at least 1 ghost"). Both engine fields were added
  for this unit; the burst carries no separate `burst_damage_percents` entry
  because this nuke IS the burst's damage.

Not modeled / deferred:
- The 6s Possession debuff itself and "1 random enemy" targeting: a raid sim
  is a single boss, so possession is always on the only target and carries no
  damage term of its own.
- "Required hit count: 100" as a real counter - see the approximation above.
- "Elemental Advantage Attack Damage" maps to other_elemental_bonus, which the
  engine adds on top of the elemental multiplier unconditionally - correct only
  when the wielder has elemental advantage (the intended Water-vs-Fire-boss
  raid setup); a neutral/disadvantaged boss would overcount it (existing
  convention, see guillotine_winter_slayer / anis_sparkling_summer).

Numbers sourced from data/lootandwaifus/char_elegg-boom-and-shock.json.
"""
from app.effects import Effect, ResourceBuff, ResourceSpec
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "elegg-boom-and-shock": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_elegg_boom_and_shock",
        "keys": {
            "hello_ghost": ("skills", 0),
            "ghostbuster": ("skills", 1),
            "thirteen_ghosts": ("skills", 2),
        },
    },
}

GHOSTS = "ghosts"


def _f(values, key, slot):
    return float(values[key][f"description_value_{slot:02d}"])


def ghost_cap(values):
    return _f(values, "hello_ghost", 6)


def _capture_interval(values):
    return _f(values, "hello_ghost", 7)


def build_elegg_burst_delay(values):
    """13 Ghosts hits 13 times at the ghost cap and only 6 below it, so she is
    played by bursting AT the cap every time rather than the instant her
    cooldown allows (Fienn, 2026-07-19: twice over a fight, once the stacks
    are up). With the deterministic fill both halves of that fall out of the
    same two values: the first cap is reached at `cap * capture interval`
    (78s), and each later one takes `spend at cap * capture interval` (54s)
    to refill - longer than her 40s cooldown, which is why her effective
    cadence is the refill, not the cooldown."""
    interval = _capture_interval(values)
    spend_at_cap = _f(values, "thirteen_ghosts", 9)
    return {
        "not_before": ghost_cap(values) * interval,
        "min_interval": spend_at_cap * interval,
    }


def build_elegg_ghost_resources(values):
    """Ghosts: +1 every capture interval (see module docstring for why the
    100-hit requirement is treated as always met), capped, spent by her burst.
    The two ghost-count buffs are threshold steps, not linear ramps."""
    cap = ghost_cap(values)
    caster_atk = values["caster_atk"]
    atk_threshold = _f(values, "hello_ghost", 8)
    atk_percent_of_caster = _f(values, "hello_ghost", 9) / 100
    elem_threshold = _f(values, "hello_ghost", 10)
    elem_bonus = _f(values, "hello_ghost", 11) / 100

    return [
        ResourceSpec(
            name=GHOSTS,
            fill=("periodic", _capture_interval(values)),
            cap=cap,
            buffs=[
                ResourceBuff(
                    stat="flat_atk", scope="element:Water",
                    value_fn=lambda count: caster_atk * atk_percent_of_caster if count >= atk_threshold else 0.0,
                ),
                ResourceBuff(
                    stat="other_elemental_bonus", scope="element:Water",
                    value_fn=lambda count: elem_bonus if count >= elem_threshold else 0.0,
                ),
            ],
            resets=[{"trigger": "own_burst", "value_fn": _make_ghost_spend(values)}],
        )
    ]


def _make_ghost_spend(values):
    """"Number of ghosts v 6. Maintains at least 1 ghost" below the cap, but
    v 9 at the cap - the spend reads the count it is spending."""
    cap = ghost_cap(values)
    spend_below_cap = _f(values, "thirteen_ghosts", 4)
    floor = _f(values, "thirteen_ghosts", 5)
    spend_at_cap = _f(values, "thirteen_ghosts", 9)

    def spend(pre_value):
        cost = spend_at_cap if pre_value >= cap else spend_below_cap
        return max(floor, pre_value - cost)

    return spend


def build_thirteen_ghosts_dynamic_hit_count_nukes(values):
    """Her burst: 800% per hit, 13 hits at the ghost cap and 6 below it."""
    cap = ghost_cap(values)
    hits_below_cap = _f(values, "thirteen_ghosts", 3)
    hits_at_cap = _f(values, "thirteen_ghosts", 8)

    return [{
        "resource": GHOSTS,
        "base_percent": _f(values, "thirteen_ghosts", 2),
        "hit_count_fn": lambda count: hits_at_cap if count >= cap else hits_below_cap,
    }]


def build_ghostbuster_scheduled_nukes(values, slug="elegg-boom-and-shock"):
    """The overflow nuke: a capture landing while already at the ghost cap.
    Reads the resolved ghost count just before each capture tick, so a burst
    that spent ghosts earlier correctly suppresses the overflow until the
    count climbs back to the cap."""
    cap = ghost_cap(values)
    interval = _capture_interval(values)

    def schedule(context, fight_duration):
        times = []
        tick = interval
        while tick < fight_duration:
            # The count strictly BEFORE this capture: at the cap already means
            # this capture overflows.
            if context.resource_count(slug, GHOSTS, tick - 1e-6, cap) >= cap:
                times.append(tick)
            tick += interval
        return times

    return [{"percent": _f(values, "ghostbuster", 3), "schedule": schedule}]


def build_elegg_boom_and_shock_rules(values):
    """Ghostbuster's burst self-buff. Everything else in her kit rides the
    ghost resource (see the resource/nuke builders above)."""
    def grant_burst_atk(context, caster_slug, time, registry):
        registry.add(
            Effect("atk_percent", _f(values, "ghostbuster", 1) / 100, "self",
                   _f(values, "ghostbuster", 2), caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="own_burst_activate", action=grant_burst_atk)]
