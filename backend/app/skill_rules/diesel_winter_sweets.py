"""Diesel: Winter Sweets (slugs "diesel-winter-sweets-intro" /
"diesel-winter-sweets-highlight"), a Burst-3 Fire RL attacker (Elysion, burst
cd 40s, no signature weapon - base skills only).

She locks into one of two mutually exclusive states at the FIRST Full Burst
of the fight and keeps it until the fight ends (Fienn, 2026-07-19):
  - **Intro** - she burst into that Full Burst. Sustained Damage +60.19%.
  - **Highlight** - she did NOT burst into it. Sustained Damage +235.03%,
    nearly four times as much.
Everything else in her kit is identical between the two, so the state is
worth roughly a 4x multiplier on her headline buff and decides how she is
played: holding her burst through the opening cycle locks Highlight, and her
40s cooldown then settles her onto even-numbered cycles - which matches
Fienn's play experience that even-cycle bursting is clearly stronger.

Because the state is decided by BURST SCHEDULING, which this engine actually
simulates, the two states cannot be two static slugs the way Bready's Tastes
are: a Highlight slug that still burst in cycle 1 would collect Highlight's
buff on top of a burst it never took. So `diesel-winter-sweets-highlight`
carries a `burst_delay` of `{"skip_cycles": 1}` (see burst_cycle), which
genuinely holds her out of the opening cycle; a tier-mate covers it, and
ALLOWED_SHAPES guarantees a second Burst 3 exists. The two slugs are wired
through `MODE_VARIANTS` so the search fields whichever scores higher and
never both.

Modeled (DPS-relevant):
- Ah Ah, Mic Test (skills[0]): the locked state's Critical Damage +20.28%,
  applied at Full Burst entry (where the state is actually entered) and
  refreshing, so it is one permanent instance rather than one per cycle.
  Plus the state's Sustained Damage buff for 10 sec on every Full Burst
  entry - 60.19% (Intro) or 235.03% (Highlight).
- I'm Gonna Sing Now! (skills[1]) Full Charge stacks: Sustained Damage
  +318.14% for 3 sec, stacking to 2. Every RL shot is a full charge, so this
  is a `("per_shot_every", 1)` ResourceSpec with cap 2 and a 3s stack
  lifetime - her 1s charge time holds both stacks inside a magazine and
  drops them across the 2s reload, which the cap and lifetime express
  exactly.
- I'm Gonna Sing Now! Full Burst DoT: 63.33% of final ATK every 1 sec for 9
  sec on Full Burst entry, as a `scheduled_nukes` schedule anchored on
  `context.full_burst_windows` (it fires on ANY Full Burst, not only her own
  burst, so the burst-anchored DoT machinery does not fit).
- La La La (skills[2], her burst): Damage Taken +25.09% for 10 sec, plus a
  9-tick 1s DoT. The all-enemy tick (18.43%) and the stage-target tick
  (181.2%) are summed to 199.63% - a raid is a single boss, so it is always
  the stage target and takes both.
- The part-destruction Sustained Damage +68.04% for 15 sec: timed when the
  encounter knows the times, bracketed when it does not.
  - `BossProfile.part_destruction_times` declared (2026-08-20): the
    `part_destroyed` trigger opens the skill's own 15s window at each time.
    Fienn's solo-40 reading (1 · 61 · 126 s) is 45s of a 180s fight, which is
    -2.91% on the deck total against the untimed reading below.
  - destructible but untimed: applied permanently from battle start, on the
    reading that parts are destroyed often enough for the 15s window to read as
    continuous. That is the more generous half of the original bracket, and the
    declared times exist to replace it.
  - not destructible: absent.

- Noise Pollution (La La La, Highlight only): Hit Rate -100% for 1 sec on all
  allies EXCEPT herself, on her burst. This is Highlight's price, and it is a
  real one for a squad of shotguns - a 250px spread doubles to 477px, which on
  a 50px core cuts an ally's core-hit share from 4.0% to 1.1% for that second.
  It is gated on the boss having NO destructible part, because the same skill
  gives allies Mute (immunity to Noise Pollution, up to 3 stacks) "when an ally
  or self destroys an enemy's part": on a part-destructible boss the squad
  restocks Mute repeatedly and the penalty simply never lands, while her burst
  spends only one stack per use. That is the same "parts are destroyed
  repeatedly through a raid" reading her Sustained bracket below already uses,
  applied to the other side of the flag (Fienn, 2026-08-07).

Not modeled / deferred:
- Mute stack bookkeeping itself: a real counter with a source, a cap and a
  spend, standing in here as a boss-profile branch. Two things that branch
  cannot see are a fight where parts exist but are destroyed too rarely to keep
  Mute up, and the very start of a fight before the first part falls.

Numbers sourced from data/lootandwaifus/char_diesel-winter-sweets.json.
"""
from app.effects import Effect, ResourceSpec
from app.skill_rules._helpers import buff_rule, linear_resource_buff, refreshing_buff_rule
from app.squad_engine import (
    SkillRule,
    boss_part_destruction_untimed,
    boss_part_indestructible,
)

_MANIFEST_KEYS = {
    "mic_test": ("skills", 0),
    "sing_now": ("skills", 1),
    "la_la_la": ("skills", 2),
}

SKILL_VALUE_MANIFESTS = {
    "diesel-winter-sweets-intro": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_diesel_winter_sweets",
        "data_slug": "diesel-winter-sweets",
        "keys": _MANIFEST_KEYS,
    },
    "diesel-winter-sweets-highlight": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_diesel_winter_sweets",
        "data_slug": "diesel-winter-sweets",
        "keys": _MANIFEST_KEYS,
    },
}

# Highlight is entered by NOT bursting into the first Full Burst, so the
# scheduler must genuinely hold her back for it (see the module docstring).
HIGHLIGHT_BURST_DELAY = {"skip_cycles": 1}


def _f(values, key, slot):
    return float(values[key][f"description_value_{slot:02d}"])


def _shared_rules(values):
    """Everything identical between the two states: her burst's Damage Taken
    debuff and the part-destruction Sustained bracket."""
    return [
        buff_rule("own_burst_activate", [
            ("damage_taken_up", _f(values, "la_la_la", 1) / 100, "squad",
             _f(values, "la_la_la", 2)),
        ]),
        # 파괴 시각을 모르는 인카운터: 15초 창이 자주 다시 열려 연속으로 읽힌다는
        # 근사라 지속시간이 없다(영구). 시각이 선언되면 이 근사는 꺼지고 아래 규칙이
        # 시각마다 원문 그대로의 15초 창을 연다.
        buff_rule(
            "battle_start",
            [("sustained_damage_up", _f(values, "sing_now", 2) / 100, "self", None)],
            condition=boss_part_destruction_untimed(),
        ),
        buff_rule(
            "part_destroyed",
            [("sustained_damage_up", _f(values, "sing_now", 2) / 100, "self",
              _f(values, "sing_now", 3))],
        ),
    ]


def _state_rules(values, crit_slot, sustained_slot):
    """The locked state: its permanent Critical Damage and its per-Full-Burst
    Sustained Damage buff. Both hang off Full Burst entry, which is where the
    state is entered; the Critical Damage one refreshes so the permanent
    effect stays a single instance across cycles."""
    return [
        refreshing_buff_rule("full_burst_enter", [
            ("other_critical_damage_sources", _f(values, "mic_test", crit_slot) / 100, "self", None),
        ]),
        buff_rule("full_burst_enter", [
            ("sustained_damage_up", _f(values, "mic_test", sustained_slot) / 100, "self",
             _f(values, "mic_test", sustained_slot + 1)),
        ]),
    ]


def _noise_pollution_rule(values):
    """Highlight's price: on her burst, every ally BUT her loses all Hit Rate
    for a second. Gated on the boss having no destructible part - see the
    module docstring for why that flag stands in for the Mute counter."""
    hit_rate = _f(values, "la_la_la", 9) / 100
    duration = _f(values, "la_la_la", 10)

    def apply_noise_pollution(context, caster_slug, time, registry):
        # "Affects all allies (except self)" - resolved live to a slugs: scope,
        # the shape Brid: Silent Track's Full Throttle established. A squad
        # scope would blind Diesel herself, whose RL never cared either way.
        allies = [m.slug for m in context.members if m.slug != caster_slug]
        if not allies:
            return
        registry.add(
            Effect("hit_rate", -hit_rate, "slugs:" + ",".join(allies),
                   duration, caster_slug),
            applied_at=time,
        )

    rule = SkillRule(trigger="own_burst_activate", action=apply_noise_pollution)
    rule.condition = boss_part_indestructible()
    return rule


def build_diesel_intro_rules(values):
    # Intro never enters Highlight status, so Noise Pollution cannot fire for
    # her at all - the bullet is gated on the state, not on the burst.
    return _state_rules(values, crit_slot=1, sustained_slot=3) + _shared_rules(values)


def build_diesel_highlight_rules(values):
    return (_state_rules(values, crit_slot=2, sustained_slot=5)
            + _shared_rules(values)
            + [_noise_pollution_rule(values)])


def build_diesel_resource_specs(values):
    """Full Charge stacks: every RL shot is a full charge, so +1 per shot,
    capped at 2.

    "Sustained Damage ▲ 318.14% for 3 sec. Stacks up to 2 times" is ONE clock
    the pair shares, restarted by every shot (the Raven ruling), so the pair
    survives the gap between her charged shots and falls off together 3 sec
    after the last one - not one stack at a time."""
    return [
        ResourceSpec(
            name="full_charge_encore",
            fill=("per_shot_every", 1),
            cap=_f(values, "sing_now", 6),
            buffs=[
                linear_resource_buff(
                    "sustained_damage_up",
                    _f(values, "sing_now", 4) / 100,
                    "self",
                )
            ],
            lifetime=_f(values, "sing_now", 5),
            lifetime_refreshes=True,
        )
    ]


def build_diesel_full_burst_dot(values):
    """"Deals 63.33% of final ATK as sustained damage every 1 sec for 9 sec"
    on entering Full Burst - ANY Full Burst, so it anchors on the fight's
    Full Burst windows rather than her own burst times."""
    tick_interval = _f(values, "sing_now", 8)
    tick_count = int(_f(values, "sing_now", 9))

    def schedule(context, fight_duration):
        times = []
        for start, _end in context.full_burst_windows:
            times.extend(start + tick_interval * i for i in range(tick_count))
        return times

    return [{
        "schedule": schedule,
        "percent": _f(values, "sing_now", 7),
        "damage_type": "sustained",
    }]


def build_diesel_burst_dot(values):
    """Her burst's DoT. The all-enemy tick and the stage-target tick both land
    on a raid's single boss, so they are summed into one tick value."""
    percent = _f(values, "la_la_la", 3) + _f(values, "la_la_la", 6)
    return [{
        "base_percent": percent,
        "tick_count": int(_f(values, "la_la_la", 5)),
        "tick_interval": _f(values, "la_la_la", 4),
        "damage_type": "sustained",
        "resolves_after_cast": True,
    }]
