"""Bready (slugs "bready-lingering" / "bready-recommended"), a Burst-3 Water
SR attacker (burst cd 40s, no signature weapon - base skills only).

Bready has two mutually exclusive states, and they change what most of her
kit does:
  - **Lingering Taste** - entered by receiving a buff that increases
    SUSTAINED damage. Her Full Charges then plant Aftertaste, a sustained
    DoT, and her burst amplifies it.
  - **Recommended Taste** - entered by receiving a buff that increases
    DISTRIBUTED damage while not already in Lingering Taste. Her Full
    Charges then deal distributed damage and buff her own Attack Damage,
    and her burst gives raw ATK instead.
Each cancels the other, so exactly one is live at a time.

Which state she runs in is decided by her DECK, not by the player - and the
engine has no "I received a buff of kind X" trigger to detect it. So the two
states are encoded as two static slugs wired through `MODE_VARIANTS`, the
same shape Cinderella: Crystal Wave's MG/Snipe modes use: the roster fans
Bready out into both candidates, `_no_character_clash` stops a deck fielding
both, and the search picks whichever scores higher. Fienn's ruling
(2026-07-19) is that both must exist rather than hardcoding today's meta:
she is paired with distributed-damage buffers now only because the available
sustained-damage buffers are weak, and a strong one shipping later flips it.

**Caveat this leaves open:** the search can pick `bready-recommended` in a
deck whose buffers are all sustained-damage (or vice versa), which in game
would put her in the other state. Nothing in the engine ties the choice to
the deck's actual buff kinds, so the mode is an assertion by the caller, not
a derivation. Read a recommended Bready deck as "field her this way IF your
buffs put her in this state".

Modeled (DPS-relevant), both modes:
- Lonely Gourmet (skills[0]) on entering Full Burst: self ATK +70.01% for
  10 sec.
- Lonely Gourmet's Taste state itself: Charge Speed -20% for 50 sec, a real
  self DEBUFF now that charge speed feeds the firing cadence (see red-hood's
  Phase-S re-verification). Identical in both states, so it is not what
  distinguishes them. Applied at battle start and refreshed - the state is
  entered as soon as the deck's buffs land and "cannot be removed".

Lingering mode only:
- Favorite Candy (skills[1]): every 3rd Full Charge puts Damage Taken +10.2%
  for 5 sec on the target and plants Aftertaste, 150.04% of final ATK as
  sustained damage every 1 sec for 5 sec.
- New Flavor (her burst, skills[2]): self Attack Damage +60.19% for 10 sec,
  plus "Aftertaste Effect +349.8% for 10 sec". There is no per-named-effect
  amplifier stat, but Aftertaste is her ONLY sustained-typed damage source,
  so a SELF-scoped `sustained_damage_up` +349.8% is exactly equivalent
  within her kit - it can reach nothing else she deals. Documented here
  because that equivalence breaks if she is ever given a second sustained
  damage source.

Recommended mode only:
- Favorite Candy (skills[1]): every Full Charge gives self Attack Damage
  +60.01% for 5 sec and deals 265.07% of final ATK as distributed damage to
  all enemies (typed "distributed" so it scales with `distributed_damage_up`
  - see special-mechanics.md, distributed damage is an offensive bucket).
- New Flavor (her burst, skills[2]): self Attack Damage +60.19% for 10 sec
  and self ATK +70.09% for 10 sec.

She is an SR, so every shot is a Full Charge (N=1 in `per_shot_rules`, the
Velvet convention).

Not modeled / deferred:
- Detecting which Taste the deck actually induces - see the caveat above.
- Neither burst has a nuke ("Deals X%" appears only in Favorite Candy), so
  the registry burst percent is None for both modes.

Numbers sourced from data/lootandwaifus/char_bready.json.
"""
from app.skill_rules._helpers import (
    buff_rule,
    instant_nuke_pulse_rule,
    refreshing_buff_rule,
)

_MANIFEST_KEYS = {
    "lonely_gourmet": ("skills", 0),
    "favorite_candy": ("skills", 1),
    "new_flavor": ("skills", 2),
}
SKILL_VALUE_MANIFESTS = {
    "bready-lingering": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_bready",
        "data_slug": "bready",
        "keys": _MANIFEST_KEYS,
    },
    "bready-recommended": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_bready",
        "data_slug": "bready",
        "keys": _MANIFEST_KEYS,
    },
}


def _f(values, key, slot):
    return float(values[key][f"description_value_{slot:02d}"])


def _shared_rules(values):
    """Lonely Gourmet: the Full Burst ATK buff and the Taste state's own
    Charge Speed penalty, identical in both modes."""
    return [
        buff_rule("full_burst_enter", [
            ("atk_percent", _f(values, "lonely_gourmet", 1) / 100, "self",
             _f(values, "lonely_gourmet", 2)),
        ]),
        buff_rule("battle_start", [
            ("charge_speed_percent", -_f(values, "lonely_gourmet", 3) / 100, "self",
             _f(values, "lonely_gourmet", 4)),
        ]),
    ]


def build_bready_lingering_rules(values):
    return _shared_rules(values) + [
        buff_rule("own_burst_activate", [
            ("attack_damage_up", _f(values, "new_flavor", 1) / 100, "self",
             _f(values, "new_flavor", 2)),
            # "Aftertaste Effect +349.8%" - self-scoped sustained_damage_up is
            # exact here because Aftertaste is her only sustained damage.
            ("sustained_damage_up", _f(values, "new_flavor", 3) / 100, "self",
             _f(values, "new_flavor", 4)),
        ]),
    ]


def build_bready_recommended_rules(values):
    return _shared_rules(values) + [
        buff_rule("own_burst_activate", [
            ("attack_damage_up", _f(values, "new_flavor", 1) / 100, "self",
             _f(values, "new_flavor", 2)),
            ("atk_percent", _f(values, "new_flavor", 5) / 100, "self",
             _f(values, "new_flavor", 6)),
        ]),
    ]


def build_lingering_per_shot_rules(values):
    """Every 3rd Full Charge marks the target with Damage Taken. The Aftertaste
    DoT it plants alongside is scheduled separately (see
    build_aftertaste_scheduled_nukes) because a per-shot pulse lands as one
    instant hit and Aftertaste ticks over 5 seconds."""
    return [(
        int(_f(values, "favorite_candy", 1)),
        "every",
        [refreshing_buff_rule("per_shot", [
            ("damage_taken_up", _f(values, "favorite_candy", 2) / 100, "squad",
             _f(values, "favorite_candy", 3)),
        ])],
    )]


def build_aftertaste_scheduled_nukes(values, slug="bready-lingering"):
    """Aftertaste: planted on every 3rd Full Charge, then 150.04% of final ATK
    as sustained damage every 1 sec for 5 sec. Scheduled off her own shot
    timeline (the Raven Shock Wave shape) so the ticks land at their real
    times and pick up whatever buffs are live at each one.

    A re-plant while Aftertaste is still running REFRESHES its window rather
    than running a second copy - the skill text carries no stack count, unlike
    the effects that do (cf. Diesel's "Stacks up to 2 times"). Modeled as the
    union of the [plant, plant+5s) windows, ticking every second while active.
    """
    plant_every = int(_f(values, "favorite_candy", 1))
    interval = _f(values, "favorite_candy", 5)
    duration = _f(values, "favorite_candy", 6)

    def schedule(context, fight_duration):
        shots = context.shot_times.get(slug, [])
        plants = [t for i, t in enumerate(shots) if (i + 1) % plant_every == 0]
        ticks = []
        window_start = window_end = None
        for plant in sorted(plants):
            if window_end is None or plant > window_end:
                if window_start is not None:
                    ticks.extend(_ticks_in(window_start, window_end, interval, fight_duration))
                window_start = plant
            window_end = plant + duration
        if window_start is not None:
            ticks.extend(_ticks_in(window_start, window_end, interval, fight_duration))
        return ticks

    return [{
        "percent": _f(values, "favorite_candy", 4),
        "schedule": schedule,
        "damage_type": "sustained",
    }]


def _ticks_in(start, end, interval, fight_duration):
    tick = start + interval
    while tick <= end and tick < fight_duration:
        yield tick
        tick += interval


def build_recommended_per_shot_rules(values):
    """Every Full Charge (she is an SR, so every shot): self Attack Damage,
    plus a distributed-damage hit on all enemies."""
    return [(
        1,
        "every",
        [
            refreshing_buff_rule("per_shot", [
                ("attack_damage_up", _f(values, "favorite_candy", 7) / 100, "self",
                 _f(values, "favorite_candy", 8)),
            ]),
            instant_nuke_pulse_rule("per_shot", _f(values, "favorite_candy", 9),
                                    damage_type="distributed"),
        ],
    )]
