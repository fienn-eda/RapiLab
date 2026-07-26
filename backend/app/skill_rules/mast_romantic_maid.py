"""Mast: Romantic Maid (slug "mast-romantic-maid"), a Burst-2 Water MG
supporter. Base skills (no signature weapon).

Mast stacks "Drunken" (up to 3) - one stack each burst cycle (on entering Burst
stage 1). Two of her buffs scale with the current stack count, and the stack
count itself is deck-dependent:

- With Anchor: Innocent Maid in the deck, Anchor's Starfish Omurice reduces a
  debuff stack each cycle, so Mast never triggers the max-stack Hangover stun
  and holds 3 stacks (stacks(cycle) = min(cycle, 3)).
- Solo, reaching 3 stacks at Full Burst end stuns her and clears the stacks, so
  she cycles 1 -> 2 -> 3 -> 1 (stacks(cycle) = ((cycle-1) % 3) + 1).

Modeled per burst cycle via SquadContext.activation_count + deck_contains.

Modeled (DPS-relevant):
- A Pirate's Heart (skills[0]): while Drunken, squad Critical Rate + ATK % of
  caster's ATK - FLAT (not stack-scaled), active continuously. Approximated as
  applied once from cycle 1 and kept for the fight (she is Drunken almost the
  whole time; the brief solo post-stun gap is ignored).
- A Pirate's Spirit (skills[1]): on entering full burst (Burst stage 3) while
  Drunken, squad Distributed Damage ▲ and Reloading Speed ▲, both per-stack *
  stacks, for 10s. The Distributed Damage half is offensive - it multiplies
  allies' Distributed damage instances (Scarlet: Black Shadow's 6th/9th
  stages) - and was missing until 2026-07-27.
- A Pirate's Romance (skills[2], her burst): squad Critical Damage + Attack
  Damage (flat, 10s), plus ATK ▲ per-stack * stacks of caster's ATK for 10s.

The stack count is derived from Burst-Stage-1 entries, not from Mast's own
activations: the stack is a squad-cycle event, and she does not burst every
cycle when another Burst 2 shares the slot.
"""
from app.effects import Effect
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "mast-romantic-maid": {
        "source": "dotgg",
        "test_module": "test_skill_rules_mast",
        "keys": {
            "pirates_heart": ("skills", 0),
            "pirates_spirit": ("skills", 1),
            "pirates_romance": ("skills", 2),
        },
    },
}

ANCHOR_SLUG = "anchor-innocent-maid"
MAX_DRUNKEN_STACKS = 3


def _drunken_stacks(context, time):
    """Stacks held at `time`. Drunken is gained "when entering Burst stage 1",
    which is a SQUAD event - it happens every cycle whoever takes the slot, and
    whether or not Mast bursts that cycle. Counting her own activations of some
    trigger instead silently undercounts every cycle she sits out: in Fienn's
    deck 1 she alternates the Burst-2 slot with Anchor, so her burst fired on
    cycles 2/4/6/... while reading stack counts 1/2/3/... - one short until the
    cap hid it."""
    cycle = sum(
        1
        for member in context.members
        if member.burst_tier == 1
        for t in context.burst_times.get(member.slug, ())
        if t <= time
    )
    anchor_present = any(m.slug == ANCHOR_SLUG for m in context.members)
    if anchor_present:
        return min(cycle, MAX_DRUNKEN_STACKS)
    return ((cycle - 1) % MAX_DRUNKEN_STACKS) + 1 if cycle else 0


def build_mast_rules(values):
    heart = values["pirates_heart"]
    spirit = values["pirates_spirit"]
    romance = values["pirates_romance"]
    caster_atk = values["caster_atk"]

    drunken_crit_rate = float(heart["description_value_03"]) / 100
    drunken_atk = float(heart["description_value_04"]) / 100 * caster_atk

    spirit_distributed_per_stack = float(spirit["description_value_01"]) / 100
    spirit_distributed_duration = float(spirit["description_value_02"])
    spirit_reload_per_stack = float(spirit["description_value_03"]) / 100
    spirit_reload_duration = float(spirit["description_value_04"])

    romance_crit_damage = float(romance["description_value_01"]) / 100
    romance_crit_damage_duration = float(romance["description_value_02"])
    romance_attack_damage = float(romance["description_value_03"]) / 100
    romance_attack_damage_duration = float(romance["description_value_04"])
    romance_atk_per_stack = float(romance["description_value_05"]) / 100
    romance_atk_duration = float(romance["description_value_06"])

    def apply_drunken_continuous(context, caster_slug, time, registry):
        if context.activation_count(caster_slug, "full_burst_enter") != 1:
            return
        registry.add(Effect("crit_rate", drunken_crit_rate, "squad", None, caster_slug), applied_at=time)
        registry.add(Effect("flat_atk", drunken_atk, "squad", None, caster_slug), applied_at=time)

    def apply_spirit(context, caster_slug, time, registry):
        stacks = _drunken_stacks(context, time)
        # "Distributed Damage - 15.03% x number of Drunken stacks" is an
        # OFFENSIVE buff on the Distributed damage type, not survivability -
        # and in Fienn's deck 1 it lands on Scarlet: Black Shadow, who deals
        # two of her three staged effects as Distributed Damage.
        registry.add(
            Effect("distributed_damage_up", spirit_distributed_per_stack * stacks, "squad",
                   spirit_distributed_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("reload_speed_percent", spirit_reload_per_stack * stacks, "squad",
                   spirit_reload_duration, caster_slug),
            applied_at=time,
        )

    def apply_romance_burst(context, caster_slug, time, registry):
        registry.add(
            Effect("other_critical_damage_sources", romance_crit_damage, "squad",
                   romance_crit_damage_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("attack_damage_up", romance_attack_damage, "squad",
                   romance_attack_damage_duration, caster_slug),
            applied_at=time,
        )
        stacks = _drunken_stacks(context, time)
        registry.add(
            Effect("flat_atk", romance_atk_per_stack * stacks * caster_atk, "squad",
                   romance_atk_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="full_burst_enter", action=apply_drunken_continuous),
        SkillRule(trigger="full_burst_enter", action=apply_spirit),
        SkillRule(trigger="own_burst_activate", action=apply_romance_burst),
    ]
