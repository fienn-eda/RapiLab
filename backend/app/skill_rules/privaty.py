"""Privaty (slug "privaty") and her Favorite Item build (slug
"privaty-signature"), from api.dotgg.gg.

The two builds are separate deck candidates (dual-slot); which one a user fights
with comes from their roster's per-unit `favorite_item` flag.

The Favorite Item adds a whole 4th effect to EX Magazine (Attack Damage up) that
the base skill lacks entirely, replaces LD Assault's Stunned rider with a
Designated-Target one and adds a Damage Taken debuff, and takes AK Missile's
burst 457.87% -> 1407.64%.

Base modeled: EX Magazine's three squad effects (ATK, Reload Speed, and the
Max Ammo REDUCTION - her own downside, encoded rather than quietly dropped), LD
Assault's 85.79% last-bullet nuke, and the 457.87% burst.

Base deferred: LD Assault's "1089% if the target is Stunned". Raid bosses cannot
be stunned (Fienn, 2026-07-24), so the rider never fires in the content this
recommender simulates - and AK Missile's own 3-sec stun is inert for the same
reason. Encoding either would credit damage that cannot happen.

Unlike Crown's "X% of caster's ATK", EX Magazine's ATK bonus is a plain
"ATK UP X%" buff on the target's own ATK, so it maps directly to
atk_percent rather than needing a caster-stat snapshot.

"LD Assault" (skills[1]) fires "when the last bullet hits the target" -
modeled via `per_shot_rules`' `"last_bullet"` mode (gap #1's residual
variant, built 2026-07-12): every last bullet applies a squad Damage Taken
debuff on the target and deals 256.17% of final ATK as additional damage
(both fired off her own shots, so both take the Full Burst bonus on whichever
land inside a window), PLUS, if the
target is currently in "Designated Target" status, an ADDITIONAL 1687% hit
stacked on top (two separate pulses that instant, not either/or - the skill
text's second bullet is a bonus layered on the first, not a replacement).
"Designated Target" is the status Privaty's own AK Missile burst applies to
its target for a fixed duration (`ak_missile`'s own description_value_04,
10 sec at max level) - modeled as a live time-window check against
`context.burst_times[caster_slug]` at the shot's own time, since this
engine has no built-in TIMED status primitive (`has_status`/`clear_status`
are boolean-only, no auto-expiry) and the window (10s) doesn't line up with
any existing per-cycle shortcut like `own_burst_fired_this_cycle()`
(Privaty's burst cooldown is 40s, so the window is a real fraction of the
cycle, not "the whole cycle until reset"). AK Missile's own Designated
Target ATK-down debuff on the enemy isn't modeled (reduces the BOSS's own
attack, a survivability stat this engine's damage formula never reads).

**Unconfirmed assumption (uses the engine's DEFAULT behavior, not an
in-game-verified fact - unlike Maiden's self-buff timing, which WAS
confirmed):** the Damage Taken debuff is added with plain `registry.add`
(not `add_refreshing`) and applied at the same instant as its own triggering
hit. Under this engine's default same-instant-inclusive semantics, that
means (a) a last bullet's own damage already reflects the debuff IT just
applied, and (b) two last bullets within the debuff's 10s window STACK
(additive squad debuff) rather than refresh. Neither has been checked
against real gameplay - flag for in-game verification if it matters.

AK Missile's own "Deals X% of final ATK as Burst Skill damage" and its
Designated-Target follow-up effects use ak_missile_burst_percent() instead
of a SkillRule, same pattern as Helm's Aegis Cannon.
"""
from app.effects import Effect, Pulse
from app.squad_engine import SkillRule

# Privaty runs with her signature weapon completed (Fienn confirmed), so the
# manifest reads the dollskills arrays, not the base skills.
SKILL_VALUE_MANIFESTS = {
    "privaty": {
        "source": "dotgg",
        "test_module": "test_skill_rules_privaty",
        "keys": {
            "ex_magazine": ("skills", 0),
            "ld_assault": ("skills", 1),
            "ak_missile": ("skills", 2),
        },
        "fixtures": {
            "ex_magazine": "EX_MAGAZINE_BASE",
            "ld_assault": "LD_ASSAULT_BASE",
            "ak_missile": "AK_MISSILE_BASE",
        },
    },
    "privaty-signature": {
        "source": "dotgg",
        "data_slug": "privaty",
        "test_module": "test_skill_rules_privaty",
        "keys": {
            "ex_magazine": ("dollskills", 0),
            "ld_assault": ("dollskills", 1),
            "ak_missile": ("dollskills", 2),
        },
        "fixtures": {
            "ex_magazine": "EX_MAGAZINE_VALUES",
            "ld_assault": "LD_ASSAULT_VALUES",
            "ak_missile": "AK_MISSILE_VALUES",
        },
    },
}


def build_ex_magazine_base_rules(values: dict) -> list[SkillRule]:
    """EX Magazine without the Favorite Item: the same three squad effects, but
    the array stops at slot 06 - the Attack Damage step (slots 07/08) is text the
    Favorite Item adds, so the shared builder's reads would KeyError here."""
    atk_up = float(values["description_value_01"]) / 100
    atk_duration = float(values["description_value_02"])
    reload_speed_up = float(values["description_value_03"]) / 100
    reload_duration = float(values["description_value_04"])
    max_ammo_reduction = float(values["description_value_05"]) / 100
    ammo_duration = float(values["description_value_06"])

    def action(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", atk_up, "squad", atk_duration, caster_slug), applied_at=time)
        registry.add(
            Effect("reload_speed_percent", reload_speed_up, "squad", reload_duration, caster_slug),
            applied_at=time,
        )
        # Her own downside, and it is squad-wide: encode the cost, not just the buff.
        registry.add(
            Effect("max_ammo_percent", -max_ammo_reduction, "squad", ammo_duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="full_burst_enter", action=action)]


def build_ld_assault_base_per_shot_rules(values: dict) -> list:
    """LD Assault without the Favorite Item: one last-bullet nuke.

    The skill's second bullet ("1089% if the target is Stunned") is DEFERRED, not
    approximated: raid bosses cannot be stunned (Fienn, 2026-07-24), so the rider
    never fires in the content this recommender simulates. Her own AK Missile stun
    is inert for the same reason. The Favorite Item replaces that bullet with a
    Designated-Target gate, which DOES fire - see build_ld_assault_per_shot_rules.
    """
    base_percent = float(values["ld_assault"]["description_value_01"])

    def action(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("instant_damage_percent", base_percent, "self", caster_slug))

    return [(None, "last_bullet", [SkillRule(trigger="per_shot", action=action)])]


def build_ex_magazine_rules(values: dict) -> list[SkillRule]:
    atk_up = float(values["description_value_01"]) / 100
    atk_duration = float(values["description_value_02"])
    reload_speed_up = float(values["description_value_03"]) / 100
    reload_duration = float(values["description_value_04"])
    max_ammo_reduction = float(values["description_value_05"]) / 100
    ammo_duration = float(values["description_value_06"])
    attack_damage_up = float(values["description_value_07"]) / 100
    attack_damage_duration = float(values["description_value_08"])

    def action(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", atk_up, "squad", atk_duration, caster_slug), applied_at=time)
        registry.add(
            Effect("reload_speed_percent", reload_speed_up, "squad", reload_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("max_ammo_percent", -max_ammo_reduction, "squad", ammo_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect(
                "attack_damage_up", attack_damage_up, "squad", attack_damage_duration, caster_slug
            ),
            applied_at=time,
        )

    return [SkillRule(trigger="full_burst_enter", action=action)]


def build_ak_missile_rules(values: dict) -> list[SkillRule]:
    other_elemental_bonus = float(values["description_value_05"]) / 100
    duration = float(values["description_value_06"])

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("other_elemental_bonus", other_elemental_bonus, "self", duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="own_burst_activate", action=action)]


def ak_missile_burst_percent(values: dict) -> float:
    return float(values["description_value_01"])


_LD_ASSAULT_DAMAGE_TAKEN = "ld_assault_damage_taken"


def build_ld_assault_per_shot_rules(values: dict) -> list:
    assault = values["ld_assault"]
    base_percent = float(assault["description_value_01"])
    designated_percent = float(assault["description_value_02"])
    damage_taken = float(assault["description_value_03"]) / 100
    debuff_duration = float(assault["description_value_04"])
    designated_duration = float(values["ak_missile"]["description_value_04"])

    def action(context, caster_slug, time, registry):
        # Refreshes, not stacks: the text carries no "stacks up to" (Fienn,
        # 2026-07-26). It matters far beyond Privaty - Damage Taken is an enemy
        # debuff every ally multiplies by, so stacking it lifted her whole
        # squad, and against Fienn's recorded deck 2 that showed as Nayuta
        # 1.10x, Little Mermaid 1.13x and Velvet 1.15x.
        registry.add_refreshing(
            Effect("damage_taken_up", damage_taken, "squad", debuff_duration, caster_slug,
                   refresh_group=_LD_ASSAULT_DAMAGE_TAKEN),
            applied_at=time,
        )
        registry.add_pulse(Pulse("instant_damage_percent", base_percent, "self", caster_slug))
        designated = any(
            bt <= time < bt + designated_duration for bt in context.burst_times.get(caster_slug, [])
        )
        if designated:
            registry.add_pulse(Pulse("instant_damage_percent", designated_percent, "self", caster_slug))

    return [(None, "last_bullet", [SkillRule(trigger="per_shot", action=action)])]
