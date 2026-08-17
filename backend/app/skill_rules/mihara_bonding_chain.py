"""Mihara: Bonding Chain (slug "mihara-bonding-chain"), a Burst-3 Fire MG
attacker (Missilis, burst cd 40s, no signature weapon - base skills only).

Two chained counters drive her whole kit. Restraint Chains (cap 10) are
banked on her, then spent WHOLE - every chain fires one attack at once
(Fienn's in-game confirmation, 2026-07-19: "한꺼번에 발동") - and each attack
plants one stack of Ensnaring Chains (cap 20) on the target. Ensnaring
Chains is a per-stack sustained DoT that her burst then reads and detonates.

Restraint Chains is NOT modeled as a resource: in a solo-boss raid it is
always exactly full (10) at every discharge, so the discharge SCHEDULE is
all that matters and the count itself carries no information. Of the three
discharge triggers the skill lists, only two can ever find a full bank in a
raid, and they are the modeled ones:
  - battle start ("적이 전장에 진입 후" - the enemy entering the field), paired
    with the battle-start charge, and
  - the end of each Full Burst she burst in ("풀 버스트 타임 종료 후"), paired
    with the charge that happens "when Full Burst ends if this unit has just
    used her Burst Skill" (fill kind `on_full_burst_end_after_own_burst`).
The third trigger, entering Burst Stage 3, then always finds an empty bank
(the chains were spent at the previous Full Burst's end), so it is a no-op
here rather than a separate discharge.

This reproduces Fienn's in-game reading (2026-07-19) that Ensnaring Chains
sits at its 20 cap when she bursts. Measured end-to-end in the deck shape
she is actually played in - a (1,1,3) whose Burst 1/2 cooldowns are short
enough (Liter 20s + Crown 20s, ~17s cycles) that the Burst 3 slot rotates:
she bursts at t=1.0 / 34.7 / 68.3 / 102.0 / 135.6 / 169.3 and holds exactly
20 stacks at every one of them except the first (t=1.0 holds 10, the
battle-start discharge alone - nothing has had time to accumulate yet).
The loop that sustains it: her burst wipes the stacks 10s later, the
discharge just past that same Full Burst's end re-plants 10, and Tighten
Up's normal-attack trickle (+1 per 40 normals during Full Burst, roughly
+15 over a 10s window at MG fire rate) tops it off to the cap during the
intervening Full Bursts she does not burst in.

The count only falls short of the cap when nothing intervenes: in a deck
where she is the sole bursting Burst 3 and fires EVERY cycle, no Full Burst
passes without her burst wiping it, so she sits at 10. That shape needs a
Burst 2 slower than her own cooldown (e.g. Blanc at 60s) to arise at all.

Modeled (DPS-relevant):
- Body Contact (skills[0]) chain attacks: 50.06% of final ATK per chain,
  10 chains fired at the same instant per discharge (`scheduled_nukes`,
  the discharge schedule above).
- Body Contact's Ensnaring Chains: a `ResourceSpec` (cap 20) fed by three
  sources - +10 per chain discharge (one per attack landed), and +1 per 40
  normal attacks during Full Burst from Tighten Up. Its DoT is a whole-fight
  `scheduled_nukes` tick, 25.08% of final ATK every 1 sec PER STACK, via the
  spec's `resource_gate`; typed "sustained" so it scales with Sustained
  Damage buffs (including her own, below).
- Tighten Up (skills[1]) Burst Stage 3 entry: Sustained Damage +59.98% for
  10 sec, self-scoped. Fired on `full_burst_enter` - Fienn's ruling
  (2026-07-19) is that ANY Burst 3 ally entering Burst Stage 3 triggers it,
  not only her own burst.
- Bonding Pain (her burst, skills[2]): Dragging Chain, 50.05% of final ATK
  every 1 sec for 10 sec, each tick "mirroring the stack count of Ensnaring
  Chains" - a `resource_scaled_nukes` DoT whose ticks each re-read the count
  at their own time. "Cancels Ensnaring Chains after the effect is
  triggered" is the paired `own_burst_delayed` reset to 0 at burst + 10s, so
  all ten ticks read the pre-cancel stacks and the counter rebuilds after.

Not modeled / deferred:
- Tighten Up's "when the skill user is incapacitated, Ensnaring Chains
  stacks +20": the sim has no incapacitation model, and a raid run where
  Mihara dies is not the case being optimized.
- Tighten Up's "when an enemy is neutralized, Restraint Chain +1": a raid
  boss is never neutralized, so this never fires (and Restraint Chains is
  not a modeled counter anyway - see above).
- The chain attacks' "random enemy units" targeting: a solo-boss raid has
  one target, so every chain lands on it regardless.

Numbers sourced from data/lootandwaifus/char_mihara-bonding-chain.json.
"""
from app.effects import Effect, ResourceSpec
from app.raid_simulator import AFTER_WINDOW_EPSILON
from app.squad_engine import SkillRule, burst_stage_entered

SKILL_VALUE_MANIFESTS = {
    "mihara-bonding-chain": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_mihara_bonding_chain",
        "keys": {
            "body_contact": ("skills", 0),
            "tighten_up": ("skills", 1),
            "bonding_pain": ("skills", 2),
        },
    },
}

ENSNARING_CHAINS = "ensnaring_chains"


def _f(values, key, slot):
    return float(values[key][f"description_value_{slot:02d}"])


def restraint_chain_cap(values):
    return _f(values, "body_contact", 2)


def ensnaring_cap(values):
    return _f(values, "body_contact", 9)


def _discharge_schedule(context, fight_duration, slug):
    """When the banked Restraint Chains are spent whole - battle start, then
    the end of each Full Burst she burst in. Mirrors the resource fill sources
    below so the attacks and the stacks they plant land together."""
    times = [0.0]
    for burst_time in context.burst_times.get(slug, []):
        end = next(
            (e for s, e in context.full_burst_windows if s <= burst_time <= e), None
        )
        if end is not None and end + AFTER_WINDOW_EPSILON not in times:
            times.append(end + AFTER_WINDOW_EPSILON)
    return sorted(t for t in times if t < fight_duration)


def build_ensnaring_chain_resources(values):
    """Ensnaring Chains: +1 stack per chain attack landed (so +10 per whole
    discharge) and +1 per 40 normal attacks during Full Burst, capped, wiped
    10s after her own burst by Bonding Pain."""
    chains_per_discharge = restraint_chain_cap(values)
    normals_per_stack = _f(values, "tighten_up", 1)
    stacks_per_trickle = _f(values, "tighten_up", 2)
    dragging_chain_duration = _f(values, "bonding_pain", 3)

    return [
        ResourceSpec(
            name=ENSNARING_CHAINS,
            cap=ensnaring_cap(values),
            buffs=[],
            fill=[
                (("at_battle_start",), chains_per_discharge),
                (("on_full_burst_end_after_own_burst",), chains_per_discharge),
                (("per_shot_every_during_full_burst", normals_per_stack), stacks_per_trickle),
            ],
            resets=[{
                "trigger": "own_burst_delayed",
                "delay": dragging_chain_duration,
                "value": 0.0,
            }],
        )
    ]


def build_mihara_scheduled_nukes(values, slug="mihara-bonding-chain"):
    """The chain attacks (one per chain, all at once per discharge) and the
    Ensnaring Chains DoT (every second, all fight, scaled per stack)."""
    chains_per_discharge = int(restraint_chain_cap(values))
    chain_attack_percent = _f(values, "body_contact", 5)
    dot_percent = _f(values, "body_contact", 7)
    dot_interval = _f(values, "body_contact", 8)
    cap = ensnaring_cap(values)

    def chain_attacks(context, fight_duration):
        times = []
        for discharge in _discharge_schedule(context, fight_duration, slug):
            times.extend([discharge] * chains_per_discharge)
        return times

    def ensnaring_ticks(context, fight_duration):
        tick = dot_interval
        times = []
        while tick < fight_duration:
            times.append(tick)
            tick += dot_interval
        return times

    return [
        {"percent": chain_attack_percent, "schedule": chain_attacks},
        {
            "percent": dot_percent,
            "schedule": ensnaring_ticks,
            "damage_type": "sustained",
            "resource_gate": (ENSNARING_CHAINS, cap, lambda count: count),
        },
    ]


def build_dragging_chain_resource_scaled_nukes(values):
    """Bonding Pain: 50.05% every 1 sec for 10 sec, each tick mirroring the
    live Ensnaring Chains stack count."""
    duration = _f(values, "bonding_pain", 3)
    interval = _f(values, "bonding_pain", 2)

    return [{
        "resource": ENSNARING_CHAINS,
        "cap": ensnaring_cap(values),
        "base_percent": _f(values, "bonding_pain", 1),
        "scale_fn": lambda count: count,
        "tick_count": int(duration / interval),
        "tick_interval": interval,
        "damage_type": "sustained",
    }]


TIGHTEN_UP_BURST_STAGE = 3  # skill text: "when entering Burst Stage 3" (fixed, not a data slot)


def build_mihara_bonding_chain_rules(values):
    """Tighten Up's Burst Stage 3 self-buff (any Burst 3 ally entering the
    stage, per Fienn 2026-07-19).

    The stage is entered BEFORE that Burst 3 casts, so this reaches the cast's
    own damage - including hers when she is the one bursting. `full_burst_enter`
    used to stand in for it, which was equivalent only while the two instants
    shared a timestamp (see burst_cycle.FULL_BURST_OPEN_DELAY).
    """
    def grant_sustained_damage(context, caster_slug, time, registry):
        registry.add(
            Effect("sustained_damage_up", _f(values, "tighten_up", 7) / 100, "self",
                   _f(values, "tighten_up", 8), caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="ally_burst_activate", action=grant_sustained_damage,
                      condition=burst_stage_entered(TIGHTEN_UP_BURST_STAGE))]
