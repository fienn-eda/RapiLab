"""Anis: Star (slug "anis-star"), a Burst-1 Electric RL Defender.

Modeled (DPS-relevant):
- Starfall (skills[0]): the formation-branch buffs (alone -> My Own Star self
  ATK + squad burst-cooldown reduction; with a Burst-1 ally -> Everyone's Star)
  and its full-charge additional damage (120.13% of final ATK on every Full
  Charge -> a per-shot nuke, since an RL's every shot is a full charge; see
  `build_starfall_full_charge_nuke_rules`). Also the squad Burst Gauge filling
  speed (+6% at lv10, `grant_gauge_fill_speed`), which feeds
  `burst_gauge.fill_times` rather than the damage formula.
- Stardust (skills[1]): squad ATK % of caster's ATK while My Own Star; squad
  Projectile Explosion Damage (the skill says "self + allies with lower DEF";
  she's a Defender so ~everyone qualifies -> squad approx); squad Attack Damage.
- Star Anis (burst): self Attack Damage while My Own Star; Shooting Stars, the
  summoned auto-attack that ticks 40.01% of final ATK every 0.25 sec for 10 sec
  off each of her bursts (40 ticks per cycle, see
  `build_shooting_stars_scheduled_nukes`); and the window's fixed 0.7-sec
  charge time (see `build_star_anis_burst_rules`).

Her damage splits 48% normal attacks / 38% Shooting Stars / 15% Starfall in the
recorded deck (measured 2026-07-28). Count instances and you will rank her
sources wrong - 600 ticks against 201 shots is not 3:1 in damage, because one
tick's coefficient is 40.01% against a shot's 167.76%.

Shooting Stars IS `full_burst_bonus_eligible`. It carries no "as additional
damage" phrase at all - it is a summon that attacks - and the phrase was only
ever a proxy for WHEN the damage is computed (Fienn, 2026-07-26). Her burst
opens Full Burst 0.2 sec later while the first tick lands 0.25 sec after it,
so every tick is computed inside the window (Fienn, 2026-07-27). Its 0.25-sec
attack interval is written into the skill TEXT rather than a numbered value
slot (it does not scale with skill level), so it is a module constant.

The window's "Charge time is fixed at 0.7 sec" is modeled as an equivalent
self Charge Speed buff, derived by inverting `attack_rate.charge_time_with_speed`
against her weapon's own base charge time (so it stays pinned to the 0.7-sec
TARGET and survives changes to that formula), rather than a `weapon_mode_schedules` segment, because segments never
reload: a 10-sec segment would fire ~14 uninterrupted shots when her 6-round
magazine really only manages ~11 around a reload. Two consequences of that
choice are documented rather than hidden: charge speed is sampled once per
MAGAZINE (see attack_rate), so a magazine already in flight when the burst
lands keeps the slower cadence and one starting late keeps the faster one past
the window's end - measured on the GAUGE axis for the first time on 2026-08-22
(Fienn's deck-1 range reading): the engine fires her at 0.77-sec intervals in
the gauge-charging window where her base charge is 1.00 sec, so it OVER-credits
her there. That is the opposite sign from this approximation's damage cost, and
it is why closing it makes the computed fill time worse before better - see
`docs/measurements/burst-gauge-fill.md` (F2) and `docs/engine-gaps.md`; and
modeling a "fixed at" as a buff means an ally's Charge
Speed buff stacks on top and pushes below 0.7 sec, where in game the fixed
value would not move - an over-estimate confined to decks that buff charge
speed. The engine DOES have a per-unit buff-immunity primitive
(`EffectRegistry.set_external_stat_immunity`, which Liberalio's Strange Currents
uses to refuse everyone else's charge speed), but it is permanent once set,
and hers must cover only her burst window - so it cannot be reused here as-is.

Star Anis also grants the squad Max HP +15.02% of her own while in Everyone's
Star - modeled, because `flat_max_hp` feeds every "ATK ▲ X% of Max HP"
conversion in the deck (Maiden, Cinderella, Maxwell, Laplace: Ultimate Hero).

Not modeled: the Everyone's Star "Re-enters Burst / Stage" branch (no
multi-stage burst re-entry); the burst's Explosion Radius (inert) and DEF, and
her heals (survival).

She reads 0.946x of her recorded raid damage, up from 0.627x over four
corrections. Everything below is the audit trail, kept because the WAY the last
one hid is the reusable part.

Verified and not worth re-checking: her Projectile Explosion Damage +92.03%
reaches her own shots (all 201 of her normal attacks carry damage_type
"projectile_explosion"), the burst's 0.7-sec charge fix shows up as 128 of her
~180 shot intervals, her cooldown reduction applies to herself (20 - 7.48 =
12.52 sec, matching her 15 bursts), and her 88.61% Superior Code overload is
correctly discarded because Electric holds no advantage over an Iron boss.

Two readings of Shooting Stars, one confirmed and one reversed (Fienn,
2026-07-28):

- Shooting Stars fires ONE star every 0.25 sec, measured in game. The 40-tick
  stream is right; "generates starS" is flavour. (Had it been N streams her
  damage would scale nearly linearly in N - 2 gives 0.778x, 3 gives 0.929x -
  which is why it was worth measuring.)
- ~~Shooting Stars does NOT take Projectile Explosion Damage.~~ **REVERSED
  2026-07-28.** The tooltip scoping ("로켓 런쳐의 폭발과 부착형 발사체의 폭발")
  was read as excluding a summon, and the burst's own "Explosion Radius +100%"
  additional effect - which only means something for damage that explodes - was
  filed as inert alongside it. Fienn's range footage settles it directly: a tick
  and a normal attack, both non-crit core hits in one window, differ by exactly
  their bare coefficients, so the tick is in the same buckets. The ticks also
  collect the CORE bonus, against the blanket "scheduled ticks never core" rule.
  Together: 0.739x -> 0.946x (core alone 0.823x, the type alone 0.818x).

Her per-hit damage is EXACT. Ten range-test readings (solo, target DEF 100,
crit/non-crit x core/non-core x before/after her own burst) reproduce from a
single anchor within 0.002%, which is the game's integer display rounding:
the normal attack's 0.613 x 2.73675, Starfall's 1.2013 with NO charge
multiplier, a tick's 0.4001, core exactly +1.0, crit 0.5 + her 11.54% overload,
and her burst's +35.2% Attack Damage as the ONLY thing that changes across it.
That last point doubles as proof the solo test never entered Full Burst (no
+0.5, no Stardust buffs), which is also why it cannot test the Projectile
Explosion question - Stardust's +92.03% is Full-Burst-gated.

★ HOW THE LAST -0.358B HID, because the shape recurs. An audit on 2026-07-28
decomposed her three sources against each other inside one window and reported
"nothing unaccounted for": normal attack 4,293,059.88 for 61.3 x 2.73675, a star
tick 443,724.05 for 40.01, Starfall 973,376.55 for 120.13, with the gaps being
"exactly the three modifiers that differ - star tick vs normal = core 1.5388 x
the projectile-explosion bucket 1.4994". That sentence IS the bug, written down
as a result. The audit checked that the sim's own numbers were internally
consistent with the sim's own assumptions, and a source-vs-source ratio can only
ever do that. Whether the tick SHOULD have been missing core and projectile
explosion is a question about the game, and no amount of internal arithmetic
reaches it. A solo range test could not reach it either - solo never enters Full
Burst, so Stardust's Full-Burst-gated +92.03% is absent and the pair carries no
projectile-explosion factor to compare.
  What settled it: the same two instances measured IN A DECK, IN a Full Burst
window (Fienn's footage, above). Their ratio came out as the bare coefficient
ratio, which says every modifier cancels - the tick is in her normal attack's
state exactly. **A ratio between two of the engine's own outputs verifies
consistency; only a ratio against the GAME verifies truth.**

Still under-modeled, small and named: her shot intervals read 128 at 0.70 sec
against 50 at 1.00, i.e. 71.9% at the burst-fixed cadence where her burst covers
79.9% of the fight. That is the once-per-MAGAZINE charge-speed sampling this
module already documents, worth about +5% of her normal attack and Starfall -
roughly +0.038B against the -0.074B that remains.

Her element is NOT costing her anything: `elements.py` returns 1.0 for a
disadvantaged attacker, not a penalty (Iron beats Electric, and NIKKE has no
reverse malus).

She is an RL, so she can NEVER collect the Effective Range Bonus at any distance
(Fienn, 2026-07-28 - the rule lives in the encoding skill's
references/damage-formula-reference.md). That is what makes her range footage
read a major bucket of exactly 1.000000 before her burst and 1.500000 inside
Full Burst, with no +0.30 term to account for, and it is why she is a good unit
to measure the other terms against. When gap #16 wires the bonus, she must stay
excluded.
"""
from app.effects import Effect, Pulse
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule
from app.squad_engine import SkillRule, has_status, no_other_burst_tier_allies, not_condition

SKILL_VALUE_MANIFESTS = {
    "anis-star": {
        "source": "dotgg",
        "test_module": "test_skill_rules_anis_star",
        "keys": {
            "starfall": ("skills", 0),
            "stardust": ("skills", 1),
            "star_anis": ("skills", 2),
        },
        "fixtures": {"starfall": "LEVEL_10_VALUES"},
        "drop_tokens": {
            # Kept: Shooting Stars damage 40.01 + its 10s window (which the
            # burst's other effects share), the My Own Star Attack Damage pair
            # (35.2 / 10s), the Everyone's Star Max HP pair (15.02 / 10s - it
            # feeds every Max-HP-scaled ATK conversion in the deck), and the
            # fixed 0.7s charge time. Dropped: the inert Explosion Radius 100
            # and DEF 55.01.
            "star_anis": [2, 3],
        },
    },
}


def build_starfall_rules(values: dict) -> list[SkillRule]:
    own_burst_tier = int(values["description_value_01"])
    my_own_star_atk = float(values["description_value_02"]) / 100
    cooldown_reduction_sec = float(values["description_value_03"])
    gauge_fill_speed = float(values["description_value_05"]) / 100

    def grant_gauge_fill_speed(context, caster_slug, time, registry):
        # 스쿼드 전체의 타격당 게이지 에너지에 곱해진다(burst_gauge.fill_times).
        if context.has_status(caster_slug, "Starfall Gauge Buff Granted"):
            return
        context.set_status(caster_slug, "Starfall Gauge Buff Granted")
        registry.add(
            Effect(
                stat="burst_gauge_fill_speed_percent",
                value=gauge_fill_speed,
                scope="squad",
                duration=None,
                source_slug=caster_slug,
            ),
            applied_at=time,
        )

    def alone_branch(context, caster_slug, time, registry):
        context.clear_status(caster_slug, "Everyone's Star")
        if not context.has_status(caster_slug, "My Own Star"):
            context.set_status(caster_slug, "My Own Star")
            registry.add(
                Effect(
                    stat="atk_percent",
                    value=my_own_star_atk,
                    scope="self",
                    duration=None,
                    source_slug=caster_slug,
                ),
                applied_at=time,
            )
        registry.add_pulse(
            Pulse(
                stat="burst_cooldown_reduction_sec",
                value=cooldown_reduction_sec,
                scope="squad",
                source_slug=caster_slug,
            )
        )

    def with_ally_branch(context, caster_slug, time, registry):
        context.clear_status(caster_slug, "My Own Star")
        context.set_status(caster_slug, "Everyone's Star")

    alone = no_other_burst_tier_allies(own_burst_tier)
    with_ally = not_condition(alone)

    return [
        SkillRule(trigger="battle_start", action=grant_gauge_fill_speed),
        SkillRule(trigger="battle_start", condition=alone, action=alone_branch),
        SkillRule(trigger="battle_start", condition=with_ally, action=with_ally_branch),
        SkillRule(trigger="full_burst_end", condition=alone, action=alone_branch),
        SkillRule(trigger="full_burst_end", condition=with_ally, action=with_ally_branch),
    ]


def build_starfall_full_charge_nuke_rules(values: dict):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): Starfall deals
    additional damage (`description_value_04`% of final ATK) on every Full Charge
    attack - an RL's every shot is a full charge, so it fires each shot."""
    nuke_percent = float(values["description_value_04"])
    return [(1, "every", [instant_nuke_pulse_rule("per_shot", nuke_percent)])]


def build_stardust_rules(values: dict) -> list[SkillRule]:
    my_own_star_atk = float(values["description_value_01"]) / 100 * values["caster_atk"]
    my_own_star_atk_duration = float(values["description_value_02"])
    projectile_explosion = float(values["description_value_04"]) / 100
    projectile_explosion_duration = float(values["description_value_05"])
    attack_damage = float(values["description_value_06"]) / 100
    attack_damage_duration = float(values["description_value_07"])

    def apply_my_own_star_atk(context, caster_slug, time, registry):
        registry.add(
            Effect("flat_atk", my_own_star_atk, "squad", my_own_star_atk_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(
            trigger="full_burst_enter",
            condition=has_status("My Own Star"),
            action=apply_my_own_star_atk,
        ),
        buff_rule("full_burst_enter", [
            ("projectile_explosion_damage_up", projectile_explosion, "squad", projectile_explosion_duration),
            ("attack_damage_up", attack_damage, "squad", attack_damage_duration),
        ]),
    ]


SLUG = "anis-star"

# "Attack Interval: 0.25 sec" is prose in the skill description, not a numbered
# value slot, so it does not scale with skill level.
SHOOTING_STARS_INTERVAL = 0.25


def build_shooting_stars_scheduled_nukes(values: dict):
    """Shooting Stars: summoned stars that auto-attack for `description_value_01`%
    of final ATK every 0.25 sec across the burst's `description_value_02`-sec
    window. Anchored to her own burst times (a `scheduled_nukes` schedule, the
    Milk/Raven precedent) rather than the Full Burst window - the stars are
    summoned BY the burst, and as a Burst 1 she fires before Full Burst opens.

    Every tick is `full_burst_bonus_eligible`: the bonus is decided by WHEN a
    damage instance is computed, not by any text phrase (Fienn, 2026-07-26),
    and a summon's ticks are computed strictly after the cast by construction.
    Her burst opens Full Burst 0.2 sec later (B1 -> B2 -> B3) while the first
    tick lands 0.25 sec after it, so every tick falls inside the window - and
    the engine still tests each tick's own time, so this stays exact rather
    than an approximation (Fienn, 2026-07-27).

    A tick is ALSO `core_eligible` and typed `projectile_explosion`, because a
    star is a shooter, not a status effect. Fienn's range footage settles both
    at once: one non-crit core-hit tick reads 1,786,809 against a non-crit
    core-hit normal attack's 7,492,265, a ratio of 4.193098, while the bare
    coefficients give (61.3% x 273.675%) / 40.01% = 4.193021 - the same to
    0.0018%. Every modifier cancels between the pair, so the tick sits in
    exactly the state her own shot does: the core bonus AND the
    projectile-explosion bucket her Stardust was filling inside that window.
    Two earlier readings of the same skill were wrong in the same direction:
    "scheduled ticks never collect core" was applied as a blanket rule, and the
    burst's "Explosion Radius +100%" additional effect - which only makes sense
    for something that explodes - was dismissed as inert."""
    percent = float(values["description_value_01"])
    duration = float(values["description_value_02"])
    ticks = int(round(duration / SHOOTING_STARS_INTERVAL))

    def schedule(context, fight_duration):
        times = []
        for burst_time in context.burst_times.get(SLUG, []):
            times.extend(
                burst_time + SHOOTING_STARS_INTERVAL * k
                for k in range(1, ticks + 1)
                if burst_time + SHOOTING_STARS_INTERVAL * k < fight_duration
            )
        return times

    return [{"schedule": schedule, "percent": percent, "core_eligible": True,
             "damage_type": "projectile_explosion"}]


def build_star_anis_burst_rules(values: dict) -> list[SkillRule]:
    self_attack_damage = float(values["description_value_03"]) / 100
    self_attack_damage_duration = float(values["description_value_04"])
    window_duration = float(values["description_value_02"])
    squad_max_hp = values["caster_max_hp"] * float(values["description_value_05"]) / 100
    squad_max_hp_duration = float(values["description_value_06"])
    fixed_charge_time = float(values["description_value_07"])
    base_charge_time = float(values["caster_weapon_stats"]["charge_time"])
    # "Charge time is fixed at 0.7 sec" as the charge-speed buff that produces
    # that cadence on her own weapon - see the module docstring for why this is
    # a buff and not a weapon-mode segment, and what it costs. Inverts
    # `attack_rate.charge_time_with_speed` (which SHORTENS by the percent), so
    # it stays anchored to the 0.7-sec target rather than to a raw percent.
    charge_speed = 1 - fixed_charge_time / base_charge_time

    def apply_self_attack_damage(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    def apply_fixed_charge_time(context, caster_slug, time, registry):
        registry.add(
            Effect("charge_speed_percent", charge_speed, "self", window_duration, caster_slug),
            applied_at=time,
        )

    def apply_squad_max_hp(context, caster_slug, time, registry):
        registry.add(
            Effect("flat_max_hp", squad_max_hp, "squad", squad_max_hp_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(
            trigger="own_burst_activate",
            condition=has_status("My Own Star"),
            action=apply_self_attack_damage,
        ),
        SkillRule(
            trigger="own_burst_activate",
            condition=has_status("Everyone's Star"),
            action=apply_squad_max_hp,
        ),
        SkillRule(trigger="own_burst_activate", action=apply_fixed_charge_time),
    ]
