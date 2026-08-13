"""Queen (Makoto Nijima) (slug "queen-makoto-nijima"), a Burst-3 Fire SG attacker.
Values from ShiftyPad; effect text cross-read from lootandwaifus.

Her kit runs on two collab mechanics. **1 More** is the named buff her own
burst grants herself when a Wind Code enemy is present - i.e. exactly when this
Fire unit holds elemental advantage - so every "Activates when 1 More takes
effect" bullet is her own burst gated on `boss_is_element("Wind")` (the burst
bullet reads "Affects self", Fienn 2026-08-13). **Follow Up** is the buff
Yukiko Amagi hands her, so the bullet keyed to it answers YUKIKO's burst
instead. Against anything but a Wind Code boss, both go dark and she is left
with her burst nuke and her flat self-buffs.

Modeled (DPS-relevant):
- Persona: Johanna (skills[0]):
  - Nuke Boost, Elemental Advantage Attack Damage +13.59% on herself,
    continuous and "cannot be removed". `other_elemental_bonus`, gated on the
    boss being Wind Code the way every such bullet is (see Marciana).
  - ATK +50.28% for 15 sec on herself, armed at battle start and re-armed every
    Full Burst end. Ungated - the bullet names no enemy condition.
  - 548.99% of final ATK as DISTRIBUTED damage to all enemies when 1 More takes
    effect: an instant nuke on her own burst, Wind-gated.
  - the same 548.99% again when Follow Up takes effect. Yukiko passing it is
    what fires this, so it rides `ally_burst_activate` + `ally_bursted`, and
    carries the same Wind gate because Yukiko's Follow Up hangs off HER 1 More.
    `raid_simulator` drains instant-damage pulses after the ally trigger for
    this bullet (2026-08-13); before that a reacting nuke was banked until Full
    Burst opened and collected that window's bonus.
- Fist of Justice! (skills[1]):
  - Attack Damage +30% on herself from battle start, continuous.
  - Nuke Amp, a second Elemental Advantage Attack Damage +25.56% on her burst,
    ending at Full Burst end. Added open-ended and closed by
    `truncate_open_ended` NAMED to this bullet: Nuke Boost above is permanent
    and sits on the same stat, so an un-named close would delete it for the
    rest of the fight.
  - Distributed Damage +90.01% for 10 sec on entering Burst Stage 3. The STAGE,
    so `ally_burst_activate` + `burst_stage_entered(3)` - it also fires in the
    cycles another Burst 3 takes the slot.
  - Baton Pass: flat ATK worth 35.2% of her own ATK, permanent, capped at 3
    stacks (one per 1 More), to "all standard Burst 3 allies (except the skill
    user) in the Persona state". That audience is `PERSONA_STATE_SLUGS` filtered
    to burst tier 3, resolved live to a `slugs:` scope rather than approximated
    onto `squad` - today it means Yukiko and nobody else, and a deck without her
    gives the bullet no audience at all, which is what the game does.
- Mafreidyne (skills[2], her burst, cd 40): 1421.69% of final ATK as
  DISTRIBUTED damage (`_BURST_DAMAGE_TYPES`), so her own Distributed Damage
  buff above multiplies it. Plus 1 More itself, ATK +30.27% for 10 sec on
  herself, Wind-gated.

Not modeled / deferred:
- Defense Master (DEF +14.78%) and Rakukaja (DEF +17.95%). DEF is not a damage
  stat in this engine.
- The Persona - Johanna wrapper itself. It is a container for the two effects
  above, not an effect; nothing else in the game reads "is Queen in the Persona
  state" except the two collab bullets, which `PERSONA_STATE_SLUGS` answers by
  membership since each unit self-applies it at battle start and nothing grants
  or removes it.
"""
from app.effects import Effect
from app.skill_rules._helpers import (
    buff_rule,
    instant_nuke_pulse_rule,
    persona_state_allies,
)
from app.squad_engine import (
    SkillRule,
    all_conditions,
    ally_bursted,
    boss_is_element,
    burst_stage_entered,
)


SKILL_VALUE_MANIFESTS = {
    "queen-makoto-nijima": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_queen_makoto_nijima",
        "keys": {
            "persona_johanna": ("skills", 0),
            "fist_of_justice": ("skills", 1),
            "mafreidyne": ("skills", 2),
        },
    },
}

# Fire's advantage target, so "if a Wind Code enemy is present" is the same
# condition as "if she holds elemental advantage".
ADVANTAGE_TARGET = "Wind"
# The partner whose Follow Up arms her second nuke. Named rather than derived:
# it is the only bullet in the game that grants Follow Up, and a wrong guess
# here would silently fire her nuke off some unrelated unit's burst.
FOLLOW_UP_SOURCE = "yukiko-amagi"
# Names Nuke Amp's Effects so closing them at Full Burst end leaves Nuke Boost -
# the same stat, same source, but permanent - standing.
NUKE_AMP_GROUP = "fist_of_justice_nuke_amp"


def mafreidyne_burst_percent(values):
    return float(values["mafreidyne"]["description_value_01"])


def build_queen_makoto_nijima_rules(values):
    johanna = values["persona_johanna"]
    justice = values["fist_of_justice"]
    mafreidyne = values["mafreidyne"]
    caster_atk = values["caster_atk"]

    nuke_boost = float(johanna["description_value_01"]) / 100
    one_more_nuke = float(johanna["description_value_03"])
    follow_up_nuke = float(johanna["description_value_04"])
    self_atk = float(johanna["description_value_05"]) / 100
    self_atk_duration = float(johanna["description_value_06"])

    nuke_amp = float(justice["description_value_01"]) / 100
    distributed = float(justice["description_value_03"]) / 100
    distributed_duration = float(justice["description_value_04"])
    persona_tier = int(float(justice["description_value_05"]))
    baton_pass = float(justice["description_value_06"]) / 100 * caster_atk
    baton_pass_stacks = int(float(justice["description_value_07"]))
    attack_damage = float(justice["description_value_09"]) / 100

    one_more_atk = float(mafreidyne["description_value_02"]) / 100
    one_more_atk_duration = float(mafreidyne["description_value_03"])

    has_advantage = boss_is_element(ADVANTAGE_TARGET)

    def apply_nuke_amp(context, caster_slug, time, registry):
        registry.add(
            Effect("other_elemental_bonus", nuke_amp, "self", None, caster_slug,
                   refresh_group=NUKE_AMP_GROUP),
            applied_at=time,
        )

    def end_nuke_amp(context, caster_slug, time, registry):
        registry.truncate_open_ended("other_elemental_bonus", caster_slug, time,
                                     refresh_group=NUKE_AMP_GROUP)

    def apply_baton_pass(context, caster_slug, time, registry):
        # One stack per 1 More, i.e. per burst of hers, and the text caps it at
        # three. Her own burst count is what activation_count returns here.
        if context.activation_count(caster_slug, "own_burst_activate") > baton_pass_stacks:
            return
        slugs = persona_state_allies(context, caster_slug, persona_tier)
        if not slugs:
            return
        registry.add(
            Effect("flat_atk", baton_pass, "slugs:" + ",".join(slugs), None, caster_slug),
            applied_at=time,
        )

    return [
        buff_rule("battle_start", [
            ("other_elemental_bonus", nuke_boost, "self", None),
            ("attack_damage_up", attack_damage, "self", None),
        ], condition=has_advantage),
        buff_rule("battle_start", [
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
        instant_nuke_pulse_rule(
            "ally_burst_activate", follow_up_nuke,
            condition=all_conditions(ally_bursted(FOLLOW_UP_SOURCE), has_advantage),
            damage_type="distributed",
        ),
        SkillRule(trigger="own_burst_activate", action=apply_nuke_amp),
        SkillRule(trigger="full_burst_end", action=end_nuke_amp),
        buff_rule("ally_burst_activate", [
            ("distributed_damage_up", distributed, "self", distributed_duration),
        ], condition=burst_stage_entered(persona_tier)),
        SkillRule(trigger="own_burst_activate", action=apply_baton_pass,
                  condition=has_advantage),
    ]
