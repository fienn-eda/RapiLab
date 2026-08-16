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

- Blessings Upon You's "when MP is replenished" ally bullet: at every MP fill
  event, all Electric Code allies EXCEPT Maiden get Elemental Advantage Attack
  Damage +40.9% (element bonus group = other_elemental_bonus, gated on the
  boss actually being Water - the rei-ayanami/marciana precedent) and flat ATK
  = 20.9% of Maiden's ATK, 10 sec each, refreshing (resource_fill_triggered_
  buffs, gap #8). See build_blessings_fill_triggered_buffs.

- Meditation (skills[0]), 3rd bullet: self Max HP +6.34% of her own, 15 sec, on
  every 6th Full Charge, stacking up to 10 - a REFRESHING stack, so the cap
  really binds (see build_meditation_resources). It reaches damage through
  Blessings Upon You, which converts her LIVE Max HP into ATK - so the stack she
  grants herself is worth real output, not just survivability.
"""
from app.effects import Effect, ResourceBuff, ResourceSpec
from app.skill_rules._helpers import instant_nuke_pulse_rule
from app.squad_engine import SkillRule, boss_is_element


SKILL_VALUE_MANIFESTS = {
    "maiden-ice-rose": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_maiden_ice_rose",
        "keys": {
            "meditation": ("skills", 0),
            "blessings_upon_you": ("skills", 1),
            "diamond_dust": ("skills", 2),
        },
        "drop_tokens": {
            # Trigger wording ("Burst Stage 1", "MP is 0", "MP is above 1") and
            # both "maximum of 12" mentions - MP_CAP restated - are not slots.
            "meditation": [0, 1, 3, 4, 6],
            "blessings_upon_you": [8, 9],
            "diamond_dust": [0],
        },
    },
}


MP_CAP = 12  # skill text: "MP can be accumulated up to a maximum of 12" (fixed, not a data slot)
# Her Meditation stack, published because an ally reads it: Flora's Petunia
# raises the stack count of stackable buffs, and this is one (her MP is not).
MEDITATION = "meditation"
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


def build_blessings_fill_triggered_buffs(values):
    """Blessings Upon You, 1st bullet: when MP is replenished, all Electric
    Code allies EXCEPT Maiden get Elemental Advantage Attack Damage +40.9%
    (only meaningful vs a Water boss - other_elemental_bonus is gated on
    actual advantage) and flat ATK = 20.9% of Maiden's ATK, 10 sec each."""
    blessings = values["blessings_upon_you"]
    caster_atk = values["caster_atk"]
    elemental = float(blessings["description_value_01"]) / 100
    elemental_duration = float(blessings["description_value_02"])
    flat_atk = caster_atk * float(blessings["description_value_03"]) / 100
    atk_duration = float(blessings["description_value_04"])

    def electric_allies_except_owner(member, owner_slug):
        return member.element == "Electric" and member.slug != owner_slug

    return [
        {
            "resource": "mp",
            "member_filter": electric_allies_except_owner,
            "buffs": [("other_elemental_bonus", elemental, elemental_duration)],
            "condition": boss_is_element("Water"),
        },
        {
            "resource": "mp",
            "member_filter": electric_allies_except_owner,
            "buffs": [("flat_atk", flat_atk, atk_duration)],
        },
    ]


def build_blessings_upon_you_rules(values, caster_max_hp):
    blessings = values["blessings_upon_you"]
    self_elem_adv = float(blessings["description_value_05"]) / 100
    self_elem_adv_duration = float(blessings["description_value_06"])
    self_atk_pct_of_max_hp = float(blessings["description_value_07"]) / 100
    self_atk_duration = float(blessings["description_value_08"])

    def action(context, caster_slug, time, registry):
        # Applied at time + _POST_CAST_DELAY, not time itself - see the
        # module docstring's "when MP is used" note.
        applied_at = time + _POST_CAST_DELAY
        registry.add(
            Effect("other_elemental_bonus", self_elem_adv, "self", self_elem_adv_duration, caster_slug),
            applied_at=applied_at,
        )
        # Live Max HP (base + flat_max_hp buffs) rather than the static
        # character-info value - same conversion max_hp_scaled_atk_rule does,
        # inlined here because this bullet lands at the delayed instant.
        by_slug = {m.slug: m for m in context.members}
        target = {"slug": caster_slug, "element": by_slug[caster_slug].element}
        live_max_hp = context.live_max_hp(caster_max_hp, target, applied_at, registry)
        registry.add(
            Effect("flat_atk", live_max_hp * self_atk_pct_of_max_hp, "self", self_atk_duration, caster_slug),
            applied_at=applied_at,
        )

    return [SkillRule(trigger="own_burst_activate", action=action)]


def build_blessings_upon_you_per_shot_rules(values):
    nuke = float(values["blessings_upon_you"]["description_value_09"])
    return [(1, "every", [instant_nuke_pulse_rule("per_shot", nuke)])]


def build_meditation_resources(values, caster_max_hp):
    """Meditation's 3rd bullet: self Max HP +6.34% of her own for 15 sec, one
    stack per 6 Full Charges (every shot is one, on an RL), STACKS UP TO 10.

    It reaches damage through Blessings Upon You, which converts her LIVE Max HP
    into ATK. That conversion is an `own_burst_activate` rule inside the burst
    cycle while this stack is emitted by the resource pass afterwards, so seeing
    it takes simulate_raid's fixed-point loop, which hands the late `flat_max_hp`
    back as a shadow on the next pass (`SquadContext.live_max_hp`). Worth 5.23%
    of her damage in a Liter/Crown/Blanc/Helm deck (measured 2026-08-17).

    A REFRESHING stack (`lifetime_refreshes`): each new stack restarts the 15
    sec for the whole stack, so the count climbs to the cap as long as she lands
    a proc within 15 sec of the last (Fienn, range test 2026-08-17). It was
    previously modeled as independent 15-sec Effects with no cap at all, on the
    reasoning that ten stacks would need sixty charged shots inside ONE fixed
    15-sec window - which no RL cadence reaches. That reasoning was wrong: the
    window is not fixed, it is renewed by every proc. The plain timed rule holds
    her at about two stacks; the cap of 10 is real and it binds.
    """
    meditation = values["meditation"]
    threshold = int(float(meditation["description_value_03"]))
    per_stack = caster_max_hp * float(meditation["description_value_04"]) / 100
    duration = float(meditation["description_value_05"])
    cap = int(float(meditation["description_value_06"]))
    return [
        ResourceSpec(
            name=MEDITATION,
            fill=("per_shot_every", threshold),
            cap=cap,
            buffs=[ResourceBuff(
                stat="flat_max_hp", scope="self",
                value_fn=lambda count: per_stack * count,
                lifetime=duration, lifetime_refreshes=True,
            )],
            stackable_buff=True,
        )
    ]


def build_diamond_dust_dynamic_hit_count_nukes(values):
    dust = values["diamond_dust"]
    base_percent = float(dust["description_value_01"])
    max_hp_percent = float(dust["description_value_02"]) / 100
    return [{
        "resource": "mp", "base_percent": base_percent,
        "extra_flat_atk_percent_of_max_hp": max_hp_percent,
    }]
