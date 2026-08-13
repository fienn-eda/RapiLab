"""Yukiko Amagi (slug "yukiko-amagi"), a Burst-3 Fire MG attacker.
Values from ShiftyPad; effect text cross-read from lootandwaifus.

Same two collab mechanics as her partner (see `queen_makoto_nijima`): **1 More**
is what her own burst grants herself when a Wind Code enemy is present - the
bullet reads "Affects self" - so every "when 1 More takes effect" bullet is her
own burst gated on `boss_is_element("Wind")`. She is the source of **Follow Up**,
which is why Queen holds a bullet keyed to it; nothing hands one to Yukiko, so
she has no cross-unit trigger of her own.

Modeled (DPS-relevant):
- Persona: Konohana Sakuya (skills[0]):
  - ATK +65.37% for 15 sec on herself, at battle start and every Full Burst end.
  - 400.31% of final ATK as DISTRIBUTED damage to all enemies when 1 More takes
    effect, i.e. an instant nuke on her own Wind-gated burst.
- Scarlet Flower (skills[1]):
  - Attack Damage +55.31% on herself from battle start, continuous.
  - Fire Amp, Distributed Damage +90.01% on herself from her burst until Full
    Burst ends. Open-ended and closed by `truncate_open_ended` named to this
    bullet, the shape Queen's Nuke Amp needs and this one keeps for symmetry.
  - Elemental Advantage Attack Damage +48.15% for 10 sec on entering Burst
    Stage 3 - the STAGE, so `ally_burst_activate` + `burst_stage_entered(3)`,
    firing in the cycles another Burst 3 takes the slot too.
  - Follow Up: flat ATK worth 80.25% of her own ATK for 25 sec to "all standard
    Burst 3 allies (except the skill user) in the Persona state", resolved live
    via `persona_state_allies` rather than approximated onto `squad`. Today that
    is Queen and nobody else.
- Maragidyne (skills[2], her burst, cd 40): 1258.79% of final ATK as DISTRIBUTED
  damage (`_BURST_DAMAGE_TYPES`), which her own Fire Amp multiplies. Plus 1 More
  itself, ATK +45.33% for 10 sec on herself.

Not modeled / deferred:
- Media and Mediarama, the two heals (5.7% of her final Max HP to every ally,
  every 3 sec - the first from battle start, the second only while her burst
  window is up). The engine models no ally HP, so the AMOUNT is not a damage
  quantity; the OCCURRENCE is, which is why she is in `HEAL_PROVIDER_SLUGS` so a
  deck-mate whose bullet arms on any ally healing (Crown) sees her. Note the
  provider scan cross-check reads lootandwaifus/dotgg text, and her page was
  collected on 2026-08-13 for exactly that reason - without it she would sit in
  `unreadable_slugs` and the list would be a hand claim nothing verifies.
- Scarlet Protection (Damage taken from Water Code enemies -17.95%). Damage
  taken by an ally is not modeled; the sim never damages the squad.
"""
from app.effects import Effect
from app.skill_rules._helpers import (
    buff_rule,
    instant_nuke_pulse_rule,
    persona_state_allies,
)
from app.squad_engine import SkillRule, boss_is_element, burst_stage_entered


SKILL_VALUE_MANIFESTS = {
    "yukiko-amagi": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_yukiko_amagi",
        "keys": {
            "persona_konohana_sakuya": ("skills", 0),
            "scarlet_flower": ("skills", 1),
            "maragidyne": ("skills", 2),
        },
    },
}

# Fire's advantage target, so "if a Wind Code enemy is present" is the same
# condition as "if she holds elemental advantage".
ADVANTAGE_TARGET = "Wind"
# Names Fire Amp's Effect so its close at Full Burst end can never reach another
# continuous bullet of hers on the same stat - the trap Queen's two Elemental
# Advantage bullets sprang.
FIRE_AMP_GROUP = "scarlet_flower_fire_amp"


def maragidyne_burst_percent(values):
    return float(values["maragidyne"]["description_value_01"])


def build_yukiko_amagi_rules(values):
    sakuya = values["persona_konohana_sakuya"]
    scarlet = values["scarlet_flower"]
    maragidyne = values["maragidyne"]
    caster_atk = values["caster_atk"]

    one_more_nuke = float(sakuya["description_value_03"])
    self_atk = float(sakuya["description_value_04"]) / 100
    self_atk_duration = float(sakuya["description_value_05"])

    fire_amp = float(scarlet["description_value_03"]) / 100
    elemental = float(scarlet["description_value_05"]) / 100
    elemental_duration = float(scarlet["description_value_06"])
    persona_tier = int(float(scarlet["description_value_07"]))
    follow_up = float(scarlet["description_value_08"]) / 100 * caster_atk
    follow_up_duration = float(scarlet["description_value_09"])
    attack_damage = float(scarlet["description_value_10"]) / 100

    one_more_atk = float(maragidyne["description_value_02"]) / 100
    one_more_atk_duration = float(maragidyne["description_value_03"])

    has_advantage = boss_is_element(ADVANTAGE_TARGET)

    def apply_fire_amp(context, caster_slug, time, registry):
        registry.add(
            Effect("distributed_damage_up", fire_amp, "self", None, caster_slug,
                   refresh_group=FIRE_AMP_GROUP),
            applied_at=time,
        )

    def end_fire_amp(context, caster_slug, time, registry):
        registry.truncate_open_ended("distributed_damage_up", caster_slug, time,
                                     refresh_group=FIRE_AMP_GROUP)

    def apply_follow_up(context, caster_slug, time, registry):
        slugs = persona_state_allies(context, caster_slug, persona_tier)
        if not slugs:
            return
        registry.add(
            Effect("flat_atk", follow_up, "slugs:" + ",".join(slugs),
                   follow_up_duration, caster_slug),
            applied_at=time,
        )

    return [
        buff_rule("battle_start", [
            ("attack_damage_up", attack_damage, "self", None),
            ("atk_percent", self_atk, "self", self_atk_duration),
        ]),
        buff_rule("full_burst_end", [
            ("atk_percent", self_atk, "self", self_atk_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("atk_percent", one_more_atk, "self", one_more_atk_duration),
        ], condition=has_advantage),
        instant_nuke_pulse_rule("own_burst_activate", one_more_nuke,
                                condition=has_advantage, damage_type="distributed"),
        SkillRule(trigger="own_burst_activate", action=apply_fire_amp),
        SkillRule(trigger="full_burst_end", action=end_fire_amp),
        buff_rule("ally_burst_activate", [
            ("other_elemental_bonus", elemental, "self", elemental_duration),
        ], condition=burst_stage_entered(persona_tier)),
        SkillRule(trigger="own_burst_activate", action=apply_follow_up,
                  condition=has_advantage),
    ]
