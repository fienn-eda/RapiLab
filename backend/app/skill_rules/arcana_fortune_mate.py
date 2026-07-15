"""Arcana: Fortune Mate (slug "arcana-fortune-mate"), a Burst-2 Fire SG
attacker. Base skills (no signature weapon).

Modeled (DPS-relevant):
- Radiant Youth (skills[2], her burst): grants herself "Making Memories" -
  Critical Rate + Attack Damage, continuous until Full Burst ends (Keepsake
  Album removes it there) - approximated as lasting the Full Burst window
  (`FULL_BURST_DURATION`). Plus the burst nuke, 554.4% of final ATK
  (`radiant_youth_burst_percent`). Also sets the `making_memories` status that
  gates the Precious Moments ramp below.
- Memories and Moments (skills[1]) two mechanics:
  - On using her Burst Skill, an Attack Damage buff to "all shotgun-wielding
    allies (except self)" - the engine has no weapon-type scope, so approximated
    as squad (Phase C gap #3 candidate). Fortune Mate herself also picks up the
    buff she wasn't meant to receive - a small self-only overstatement.
  - Precious Moments: at the 6th normal attack landed while in Making Memories,
    self ATK +2.49% (continuous, stacks up to 3). The 6th normal is reliably
    reached exactly once per Full Burst (SG fires far more than 6 shots in the
    10s window, and the phase effect does not re-stack within one Making
    Memories), so the increment is modeled once per Full Burst on
    `full_burst_enter` (an exact per-cycle equivalence, NOT a normal-count
    approximation onto the wrong trigger). This ALSO keeps the stack count in
    the burst-cycle pass, where Keepsake Album can read it - a per-shot count
    would be built in a later pass and be invisible to Keepsake's full_burst_end
    read. Stacks persist across cycles (Keepsake removes only Making Memories and
    Snapshots, not Precious Moments), ramping 1 -> 2 -> 3 over three cycles. The
    stack count is tracked with `record_activation("precious_moments")`.
- Keepsake Album (skills[0]): when Full Burst ends, all shotgun-wielding allies
  (squad approx) gain flat ATK = 13% of the caster's ATK PER Precious Moments
  stack, for 15 sec. Reads the live stack count, so it ramps with Precious
  Moments (13% -> 26% -> 39% of caster ATK over three cycles). Clears the
  `making_memories` status so the next cycle's burst re-arms it.

Not modeled / deferred:
- Happy Memories (Memories and Moments' 4th-normal effect): "Number of pellets
  +1, stacks up to 3" - the engine has no per-pellet SG damage concept, so a
  pellet-count buff can't be represented. This is a real part of her SG DPS.
- Snapshots of Youth (Keepsake Album, triggered by Happy Memories): Normal
  Attack Damage Multiplier +10% (stacks up to 3) - Normal Attack Damage
  Multiplier is a deferred stat (see damage-formula-reference.md).
- Memories and Moments' 2nd/4th-normal reload phases (reload/pellet) - reload
  isn't DPS-modeled and pellets are deferred as above.
"""
from app.burst_cycle import FULL_BURST_DURATION
from app.effects import Effect
from app.squad_engine import SkillRule, has_status

MAKING_MEMORIES_STATUS = "making_memories"
PRECIOUS_MOMENTS_COUNTER = "precious_moments"


def radiant_youth_burst_percent(values):
    return float(values["radiant_youth"]["description_value_04"])


def build_fortune_mate_rules(values):
    radiant_youth = values["radiant_youth"]
    memories = values["memories_and_moments"]
    keepsake = values["keepsake_album"]
    caster_atk = values["caster_atk"]

    crit_rate = float(radiant_youth["description_value_01"]) / 100
    attack_damage = float(radiant_youth["description_value_03"]) / 100
    ally_attack_damage = float(memories["description_value_06"]) / 100
    ally_attack_damage_duration = float(memories["description_value_07"])
    precious_moments_atk = float(memories["description_value_04"]) / 100
    precious_moments_cap = int(float(memories["description_value_05"]))
    keepsake_atk_per_stack = float(keepsake["description_value_01"]) / 100 * caster_atk
    keepsake_duration = float(keepsake["description_value_02"])

    def apply_radiant_youth(context, caster_slug, time, registry):
        context.set_status(caster_slug, MAKING_MEMORIES_STATUS, time)
        registry.add(
            Effect("crit_rate", crit_rate, "self", FULL_BURST_DURATION, caster_slug), applied_at=time
        )
        registry.add(
            Effect("attack_damage_up", attack_damage, "self", FULL_BURST_DURATION, caster_slug),
            applied_at=time,
        )

    def apply_squad_attack_damage(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", ally_attack_damage, "squad", ally_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    def gain_precious_moments(context, caster_slug, time, registry):
        if context.activation_count(caster_slug, PRECIOUS_MOMENTS_COUNTER) >= precious_moments_cap:
            return
        context.record_activation(caster_slug, PRECIOUS_MOMENTS_COUNTER)
        registry.add(Effect("atk_percent", precious_moments_atk, "self", None, caster_slug), applied_at=time)

    def apply_keepsake_album(context, caster_slug, time, registry):
        context.clear_status(caster_slug, MAKING_MEMORIES_STATUS)
        stacks = context.activation_count(caster_slug, PRECIOUS_MOMENTS_COUNTER)
        if stacks == 0:
            return
        registry.add(
            Effect("flat_atk", keepsake_atk_per_stack * stacks, "squad", keepsake_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="own_burst_activate", action=apply_radiant_youth),
        SkillRule(trigger="own_burst_activate", action=apply_squad_attack_damage),
        SkillRule(trigger="full_burst_enter", action=gain_precious_moments,
                  condition=has_status(MAKING_MEMORIES_STATUS)),
        SkillRule(trigger="full_burst_end", action=apply_keepsake_album),
    ]
