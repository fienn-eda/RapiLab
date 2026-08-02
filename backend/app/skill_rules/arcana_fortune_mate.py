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
    allies (except self)" - exact scope via the gap #3 live member filter
    (2026-07-18; was a squad approximation that also over-applied to herself).
  - The normal-attack PHASE ROTATION, the kit's engine (see below).
- Keepsake Album (skills[0]): when Full Burst ends, all shotgun-wielding allies
  (exact SG member filter, self included) gain flat ATK = 13% of the caster's
  ATK PER Precious Moments stack, for 15 sec. Clears the `making_memories`
  status so the next cycle's burst re-arms it. Also grants Snapshots of Youth
  (Normal Attack Damage Multiplier +10%, cap 3) each time Happy Memories fires.

THE PHASE ROTATION (Fienn's in-game observation, 2026-07-28)
------------------------------------------------------------
"Effect varies according to the number of attacks. Only one effect is triggered
at a time." reads like three independent thresholds; it is one ROTATION. Every
2nd normal attack landed while in Making Memories fires exactly ONE of three
effects, in order, and the cycle repeats:

    2 reload | 4 Happy Memories | 6 Precious Moments | 8 reload | 10 HM | 12 PM | ...

Fienn counted this to the 18th normal and confirmed the decisive negative: at
the 12th, Happy Memories and the reload do NOT fire - only Precious Moments.
The counter restarts when Making Memories is removed (skill text), i.e. every
Full Burst. So each effect is one (first, period) pair on a period-6 rotation,
which is what `per_shot_rules`' `cycle_in_own_status_window` mode expresses;
the older `every_during_own_status_window` would drag the phase across windows.

HOW FAR THE ROTATION GETS IS DECK-DEPENDENT, which is why none of this is
folded into a per-cycle constant. Her SG fires ~14 shots in a 10 sec window
unaided (Happy Memories 2, Precious Moments 2), but Fienn measured 22 with
Tove's attack speed in the squad - which caps BOTH at 3 inside a single window.
An "N stacks per Full Burst" approximation would have been wrong by 2x in one
direction or the other depending on who else is seated.

RANGE-TESTED (Fienn, 2026-07-28 - Tove + her + Dorothy: Serendipity + Drake
(favorite item) + Solin: Frost Ticket, non-crit per-pellet readings)
--------------------------------------------------------------------
Reading CONSECUTIVE pairs isolates one stack gain at a time, cancelling ATK and
every deck buff:

- Precious Moments is exactly what the data slot says. The three PM steps read
  1.009247 / 1.009164 / 1.009080, and ATK +2.49% into one additive bucket
  reproduces all three from a single fitted bucket total, to 0.007%.
- Snapshots of Youth lands at 0.0913573 per stack, not 0.1, because her SG
  COLLECTIBLE already holds 9.46% of the same "일반 공격 대미지 배율" bucket:
  0.1 / 1.0946 = 0.0913576. The readings pick her collectible rung out of the
  ladder's four - 4.73/6.30/7.88/9.46 predict 0.0955/0.0941/0.0927/0.0914 and
  only the last is within reading precision.
- Happy Memories' pellet does NOT add shot damage. The pellet count (10/11/12/13,
  counted off the boss's bullet holes) and the per-pellet value are measured
  INDEPENDENTLY, so their product - the shot total - carries no assumption: it
  grows 9.13573% per stack, which is Snapshots' marginal contribution alone.
  Pellets multiplying damage would put it at 20.05% (1.1 x 1.0914 - 1). The same
  shot total is split across more pellets, so pellet count buys hit consistency
  and core coverage, not damage - which is why the engine having no per-pellet
  model costs nothing here.

E2E on the squad Fienn measured in (Tove + her + Dorothy: Serendipity + Drake
(favorite item) + Soline: Frost Ticket, real synced roster): she goes 0.978B ->
1.093B (+11.7%), and her three SG allies gain 0.5-0.8% each from Keepsake Album
now reading the live count instead of one stack per cycle. Deck total +2.40%.

Not modeled / deferred:
- The rotation's reload phase ("Reloads 6 rounds" every 6th normal): the shot
  timeline is fixed before per-shot rules run, so no rule can hand a magazine
  rounds back (same wall as Milk's forced reload and EVE's Eagle Eye, gap #11).
  It matters here - the refill is what keeps her firing without a reload gap
  inside the window - so her shot count is a FLOOR.
- Happy Memories' pellet count itself: it moves no damage (see above), and the
  engine has no per-pellet shotgun model to hang hit-consistency on.
"""
from app.burst_cycle import FULL_BURST_DURATION
from app.effects import Effect, ResourceSpec
from app.skill_rules._helpers import linear_resource_buff, refreshing_buff_rule
from app.squad_engine import SkillRule, has_status

SKILL_VALUE_MANIFESTS = {
    "arcana-fortune-mate": {
        "source": "dotgg",
        "test_module": "test_skill_rules_arcana_fortune_mate",
        "keys": {
            "keepsake_album": ("skills", 0),
            "memories_and_moments": ("skills", 1),
            "radiant_youth": ("skills", 2),
        },
    },
}

MAKING_MEMORIES_STATUS = "making_memories"
PRECIOUS_MOMENTS_RESOURCE = "precious_moments"
SNAPSHOTS_RESOURCE = "snapshots_of_youth"

# The rotation: one effect per 2nd normal attack, three effects in order, so
# each lands every 6th normal starting at its own step. The reload phase (step
# 2) has no engine representation - see the docstring's deferred note.
ROTATION_PERIOD = 6
HAPPY_MEMORIES_FIRST = 4
PRECIOUS_MOMENTS_FIRST = 6


def radiant_youth_burst_percent(values):
    return float(values["radiant_youth"]["description_value_04"])


def build_fortune_mate_rules(values):
    radiant_youth = values["radiant_youth"]
    memories = values["memories_and_moments"]

    crit_rate = float(radiant_youth["description_value_01"]) / 100
    attack_damage = float(radiant_youth["description_value_03"]) / 100
    ally_attack_damage = float(memories["description_value_06"]) / 100
    ally_attack_damage_duration = float(memories["description_value_07"])

    def apply_radiant_youth(context, caster_slug, time, registry):
        context.set_status(caster_slug, MAKING_MEMORIES_STATUS, time)
        registry.add(
            Effect("crit_rate", crit_rate, "self", FULL_BURST_DURATION, caster_slug), applied_at=time
        )
        registry.add(
            Effect("attack_damage_up", attack_damage, "self", FULL_BURST_DURATION, caster_slug),
            applied_at=time,
        )

    def apply_sg_ally_attack_damage(context, caster_slug, time, registry):
        # "all shotgun-wielding allies (except self)" - exact scope via the
        # gap #3 live member filter (was a squad approximation).
        slugs = [m.slug for m in context.members if m.weapon == "SG" and m.slug != caster_slug]
        if not slugs:
            return
        registry.add(
            Effect("attack_damage_up", ally_attack_damage, "slugs:" + ",".join(slugs),
                   ally_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    def clear_making_memories(context, caster_slug, time, registry):
        # Keepsake Album's third bullet. Its flat-ATK grant is NOT here: that
        # scales off a Precious Moments count only the shot loop can produce,
        # so it is resolved by `build_keepsake_album_resource_gated_buffs`.
        context.clear_status(caster_slug, MAKING_MEMORIES_STATUS)

    return [
        SkillRule(trigger="own_burst_activate", action=apply_radiant_youth),
        SkillRule(trigger="own_burst_activate", action=apply_sg_ally_attack_damage),
        SkillRule(trigger="full_burst_end", action=clear_making_memories),
    ]


def build_memories_and_moments_resources(values):
    """Both stack counters the rotation feeds. They differ in exactly one way -
    Precious Moments persists across cycles, Happy Memories is wiped when Full
    Burst ends - so only the latter carries a reset."""
    memories = values["memories_and_moments"]
    keepsake = values["keepsake_album"]
    return [
        ResourceSpec(
            name=PRECIOUS_MOMENTS_RESOURCE,
            fill=("per_shot_cycle_in_own_status_window",
                  PRECIOUS_MOMENTS_FIRST, ROTATION_PERIOD, FULL_BURST_DURATION),
            cap=int(float(memories["description_value_05"])),
            buffs=[linear_resource_buff(
                "atk_percent", float(memories["description_value_04"]) / 100, "self")],
        ),
        ResourceSpec(
            name=SNAPSHOTS_RESOURCE,
            # Snapshots of Youth is granted "when Happy Memories takes effect",
            # so it rides the Happy Memories rotation step 1:1 and shares its
            # cap. Full Burst's end removes it, hence the reset.
            fill=("per_shot_cycle_in_own_status_window",
                  HAPPY_MEMORIES_FIRST, ROTATION_PERIOD, FULL_BURST_DURATION),
            cap=int(float(keepsake["description_value_04"])),
            buffs=[linear_resource_buff(
                "normal_attack_damage_multiplier",
                float(keepsake["description_value_03"]) / 100, "self")],
            resets=[{"trigger": "full_burst_end", "value": 0}],
        ),
    ]


def build_keepsake_album_resource_gated_buffs(values):
    """"When Full Burst ends ... ATK 13% of the skill user's ATK x stack count
    of Precious Moments for 15 sec", to all shotgun-wielding allies (herself
    included). Read at full_burst_end rather than fired by a SkillRule there,
    because the burst-cycle walk runs before any shot exists and would always
    see an empty counter."""
    keepsake = values["keepsake_album"]
    memories = values["memories_and_moments"]
    return [{
        "resource": PRECIOUS_MOMENTS_RESOURCE,
        "cap": int(float(memories["description_value_05"])),
        "at": "full_burst_end",
        "stat": "flat_atk",
        "value_per_stack": float(keepsake["description_value_01"]) / 100 * values["caster_atk"],
        "member_filter": lambda member, caster_slug: member.weapon == "SG",
        "duration": float(keepsake["description_value_02"]),
    }]
