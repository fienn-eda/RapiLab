"""Maiden: Ice Rose (slug "maiden-ice-rose"), a Burst-3 Electric Rocket
Launcher defender. Base skills. PARTIAL - see below.

First consumer of the squad-burst-cycle-conditional resource fill mode (a
resource whose fill depends on GLOBAL burst-cycle events AND its own running
value - see raid_simulator's `_resolve_squad_burst_cycle_resource`) and of
dynamic_hit_count_nukes (a burst nuke whose HIT COUNT, not just its percent,
is itself a resource's value).

Modeled (DPS-relevant): an "mp" resource, capped at 12.
- Meditation (skills[0]) fills it: +1 if MP is currently 0, whenever ANY squad
  member's Burst Stage 1 fires; +1 if MP is currently >=1, on entering Full
  Burst. When Maiden is the SOLE Burst-3 unit in the deck, the SECOND rule can
  never actually fire: the engine's burst1 -> burst2 -> burst3 -> full-burst-
  enter sequencing (confirmed strict, Fienn 2026-07-12) means her OWN burst
  (which drains MP to 0) always completes before Full Burst formally "enters"
  - so by the time that check runs, MP is already back to 0, and Diamond
  Dust's hit count is exactly 1 per cycle (from the tier-1 rule alone). This
  is scoped to solo tier-3 play, not a universal property of the fill logic:
  sharing the Burst-3 slot with ANOTHER Burst-3 unit (e.g. a deck fielding
  both Maiden and Asuka Shikinami Langley: Wille) breaks the invariant on any
  cycle where the OTHER unit completes tier-3 instead of Maiden - her own
  reset doesn't fire that cycle, so MP can climb past 1 before her next own
  burst reads it, making the second rule genuinely contribute (verified in
  `test_interaction_asuka_maiden_shared_burst_tier.py`, which is why the rule
  stays modeled rather than being treated as dead code).
- Blessings Upon You (skills[1]): "when MP is used" (i.e. on her own burst,
  which always drains SOME amount of MP even when that amount is 0) grants
  self Elemental Advantage Attack Damage +31.68% and ATK +3.2% of her own
  final Max HP, both for 10 sec. Separately, every Full-Charge shot (RL is
  always full-charge) deals an extra 547.62%-of-final-ATK hit.
  **Confirmed in-game (Fienn, 2026-07-12): this self-buff does NOT apply to
  Diamond Dust's own damage**, even though both fire from the same burst -
  Diamond Dust's damage is computed at cast time, and a buff the cast itself
  grants doesn't retroactively affect it, only subsequent damage. Modeled by
  applying the buff `_POST_CAST_DELAY` seconds after the burst fires (an
  amount far below any real shot interval, so every OTHER consumer of the
  buff is unaffected) rather than at the exact cast instant.
- Diamond Dust (skills[2], her burst): deals 1372.8% of (10% of her final Max
  HP + her ATK) per hit, hitting once per point of MP she had right before
  this same burst drained it - i.e. always once per cycle here (see above).
  The 10%-Max-HP term is inherent to Diamond Dust's own formula (folded in via
  `extra_flat_atk_percent_of_max_hp`, bypassing the registry entirely), so it
  is unaffected by the self-buff timing question above.

Not modeled / deferred:
- Blessings Upon You's "when MP is replenished" ally buff (Elemental
  Advantage Attack Damage +40.9% and ATK +20.9% of caster ATK, both for 10
  sec, to all OTHER Electric Code allies) needs a buff granted to OTHER
  units triggered by a resource FILL event - a different capability from
  `resource_gated_buffs` (which is the resource OWNER's own burst-time gate,
  not a squad-wide fill-triggered buff). Not built; a secondary supporting
  buff, not her headline mechanic.
- Meditation's "Max HP +6.34% for 15 sec, stacks up to 10, on every 6th
  Full-Charge attack" - Max HP isn't a stat the engine's damage formula
  consumes; survivability, not DPS.
"""
from app.effects import Effect, ResourceSpec
from app.skill_rules._helpers import instant_nuke_pulse_rule
from app.squad_engine import SkillRule

MP_CAP = 12  # skill text: "MP can be accumulated up to a maximum of 12" (fixed, not a data slot)
# How long after her own burst fires the "MP is used" self-buff becomes
# active - strictly greater than 0 so it doesn't retroactively boost that
# same burst's own Diamond Dust damage (confirmed in-game, Fienn 2026-07-12),
# but far below any real shot interval so every later consumer (per-shot
# nuke, normal attacks) sees it exactly as if it started at burst_time.
_POST_CAST_DELAY = 1e-6


def _squad_tier1_fire(event):
    return event["type"] == "burst" and event["tier"] == 1


def _full_burst_enter(event):
    return event["type"] == "full_burst_start"


def build_mp_resources(values):
    return [
        ResourceSpec(
            name="mp",
            fill=("squad_burst_cycle_conditional", [
                (_squad_tier1_fire, lambda count: count == 0, 1),
                (_full_burst_enter, lambda count: count >= 1, 1),
            ]),
            cap=MP_CAP,
            buffs=[],
            resets=[{"trigger": "own_burst", "value": 0}],
        )
    ]


def build_blessings_upon_you_rules(values, caster_max_hp):
    blessings = values["blessings_upon_you"]
    self_elem_adv = float(blessings["description_value_05"]) / 100
    self_elem_adv_duration = float(blessings["description_value_06"])
    self_atk_from_max_hp = caster_max_hp * float(blessings["description_value_07"]) / 100
    self_atk_duration = float(blessings["description_value_08"])

    def action(context, caster_slug, time, registry):
        # Applied at time + _POST_CAST_DELAY, not time itself - see the
        # module docstring's "when MP is used" note.
        applied_at = time + _POST_CAST_DELAY
        registry.add(
            Effect("other_elemental_bonus", self_elem_adv, "self", self_elem_adv_duration, caster_slug),
            applied_at=applied_at,
        )
        registry.add(
            Effect("flat_atk", self_atk_from_max_hp, "self", self_atk_duration, caster_slug),
            applied_at=applied_at,
        )

    return [SkillRule(trigger="own_burst_activate", action=action)]


def build_blessings_upon_you_per_shot_rules(values):
    nuke = float(values["blessings_upon_you"]["description_value_09"])
    return [(1, "every", [instant_nuke_pulse_rule("per_shot", nuke)])]


def build_diamond_dust_dynamic_hit_count_nukes(values):
    dust = values["diamond_dust"]
    base_percent = float(dust["description_value_01"])
    max_hp_percent = float(dust["description_value_02"]) / 100
    return [{
        "resource": "mp", "base_percent": base_percent,
        "extra_flat_atk_percent_of_max_hp": max_hp_percent,
    }]
