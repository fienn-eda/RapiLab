"""Anis: Star (slug "anis-star"), a Burst-1 Electric RL Defender.

Modeled (DPS-relevant):
- Starfall (skills[0]): the formation-branch buffs (alone -> My Own Star self
  ATK + squad burst-cooldown reduction; with a Burst-1 ally -> Everyone's Star)
  and its full-charge additional damage (120.13% of final ATK on every Full
  Charge -> a per-shot nuke, since an RL's every shot is a full charge; see
  `build_starfall_full_charge_nuke_rules`).
- Stardust (skills[1]): squad ATK % of caster's ATK while My Own Star; squad
  Projectile Explosion Damage (the skill says "self + allies with lower DEF";
  she's a Defender so ~everyone qualifies -> squad approx); squad Attack Damage.
- Star Anis (burst): self Attack Damage while My Own Star; Shooting Stars, the
  summoned auto-attack that ticks 40.01% of final ATK every 0.25 sec for 10 sec
  off each of her bursts (40 ticks per cycle - by far her largest damage source,
  see `build_shooting_stars_scheduled_nukes`); and the window's fixed 0.7-sec
  charge time (see `build_star_anis_burst_rules`).

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
the window's end; and modeling a "fixed at" as a buff means an ally's Charge
Speed buff stacks on top and pushes below 0.7 sec, where in game the fixed
value would not move - an over-estimate confined to decks that buff charge
speed (the engine has no per-unit buff-immunity primitive; Liberalio needs the
same one).

Not modeled: Starfall's Burst Gauge filling speed (inert stat) and the
Everyone's Star "Re-enters Burst / Stage" branch (no multi-stage burst
re-entry); the burst's Explosion Radius (inert) and DEF, and all heal / Max HP
(survival).

She reads 0.627x of her recorded raid damage - the LOWEST ratio of all 25
measured units - and needs +59% to reach it, which is a different order of miss
from the rest of her deck (+20% / +9% / +7% / -15%). An audit on 2026-07-27
found the modelled parts right: her Projectile Explosion Damage +92.03% does
reach her own shots (all 201 of her normal attacks carry damage_type
"projectile_explosion"), the burst's 0.7-sec charge fix shows up as 128 of her
~180 shot intervals, her cooldown reduction applies to herself (20 - 7.48 =
12.52 sec, matching her 15 bursts), and her 88.61% Superior Code overload is
correctly discarded because Electric holds no advantage over an Iron boss.

Both readings that could have explained it are now settled AGAINST changing
anything here (Fienn, 2026-07-28):

- Shooting Stars fires ONE star every 0.25 sec, measured in game. The 40-tick
  stream is right; "generates starS" is flavour. (Had it been N streams her
  damage would scale nearly linearly in N - 2 gives 0.778x, 3 gives 0.929x -
  which is why it was worth measuring.)
- Shooting Stars does NOT take Projectile Explosion Damage. The in-game tooltip
  scopes that stat to "로켓 런쳐의 폭발과 부착형 발사체의 폭발" - a rocket
  launcher's own explosion and an attached projectile's - and a summon's
  auto-attack is neither. Her RL NORMAL attacks are in scope and already carry
  the type. Typing the ticks projectile_explosion would add +0.108B (her 0.627x
  -> 0.706x, deck1 0.867x -> 0.876x); that damage would be fictional.

Her per-hit damage is EXACT. Ten range-test readings (solo, target DEF 100,
crit/non-crit x core/non-core x before/after her own burst) reproduce from a
single anchor within 0.002%, which is the game's integer display rounding:
the normal attack's 0.613 x 2.73675, Starfall's 1.2013 with NO charge
multiplier, a tick's 0.4001, core exactly +1.0, crit 0.5 + her 11.54% overload,
and her burst's +35.2% Attack Damage as the ONLY thing that changes across it.
That last point doubles as proof the solo test never entered Full Burst (no
+0.5, no Stardust buffs), which is also why it cannot test the Projectile
Explosion question - Stardust's +92.03% is Full-Burst-gated.

So her 0.627x sits entirely ABOVE the per-hit layer, in counts, uptime or deck
context - the same signature Ade: Agent Bunny showed. Do not look for it in the
coefficients again.
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
            # (35.2 / 10s), and the fixed 0.7s charge time. Dropped: the inert
            # Explosion Radius 100, DEF 55.01, and the Everyone's Star Max HP
            # pair (15.02 / 10s) - all survivability or unconsumed stats.
            "star_anis": [2, 3, 6, 7],
        },
    },
}


def build_starfall_rules(values: dict) -> list[SkillRule]:
    own_burst_tier = int(values["description_value_01"])
    my_own_star_atk = float(values["description_value_02"]) / 100
    cooldown_reduction_sec = float(values["description_value_03"])
    gauge_fill_speed = float(values["description_value_05"]) / 100

    def grant_gauge_fill_speed(context, caster_slug, time, registry):
        # INERT BY DESIGN. Nothing reads `burst_gauge_fill_speed_percent`: the
        # cycle takes its gauge time from BossProfile.gauge_charge_time, a fixed
        # input no buff can move (see docs/engine-gaps.md, "Burst Gauge fill
        # speed - 구현 안 함"). Registered anyway so it starts counting the day
        # the cycle reads the registry, but do not expect it to move damage.
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
    than an approximation (Fienn, 2026-07-27)."""
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

    return [{"schedule": schedule, "percent": percent,
             "full_burst_bonus_eligible": True}]


def build_star_anis_burst_rules(values: dict) -> list[SkillRule]:
    self_attack_damage = float(values["description_value_03"]) / 100
    self_attack_damage_duration = float(values["description_value_04"])
    window_duration = float(values["description_value_02"])
    fixed_charge_time = float(values["description_value_05"])
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

    return [
        SkillRule(
            trigger="own_burst_activate",
            condition=has_status("My Own Star"),
            action=apply_self_attack_damage,
        ),
        SkillRule(trigger="own_burst_activate", action=apply_fixed_charge_time),
    ]
