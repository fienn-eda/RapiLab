"""Mint (slug "mint"), a Burst-2 Iron RL supporter. Base skills (no signature
weapon).

Mint alternates between "Assigned Part: Singing" and "...: Dancing" - each use
of her burst (Let's Sing Together!) toggles it, starting at Dancing on her
first use ("if in Dancing, become Singing; if not in Dancing [including
never-assigned], become Dancing"). Modeled without a separate status flag by
reading `context.activation_count(caster_slug, "own_burst_activate") % 2 == 0`
- an even count means she's currently Singing (1st use -> Dancing/count 1 odd,
2nd -> Singing/count 2 even, ...). She is Burst 2, so her own burst always
fires before Burst Stage 3 is entered in the same cycle, and the parity is
already correct by the time Fantastic Performance's rule checks it.

Modeled (DPS-relevant):
- Let's Sing Together! (skills[2], her burst): toggles her Assigned Part (see
  above - no separate effect needed, just the parity read elsewhere); squad
  Attack Damage + Max Ammo % + Critical Damage, all 10 sec. No enemy nuke
  (buff-only burst).
- Fantastic Performance! (skills[1]): on entering Burst Stage 3 - the beat
  BEFORE the Burst 3 casts, so this reaches that cast's own burst damage
  (contrast Crown's "at the start of Full Burst", which lands after it) - IF
  she's currently Singing (the parity check) - squad Critical Rate + squad Pierce Damage,
  10 sec, plus squad Projectile Explosion Damage
  (`projectile_explosion_damage_up`) - consumed by every RL ally's normal
  attacks and any projectile_explosion-typed burst nuke (gap #4 damage-type
  wiring; see raid_simulator's normal_attack_type / _TYPE_BUCKETS).

Here I Go! (skills[0]) Singing branch is modeled via the per-shot trigger (see
`build_here_i_go_rules`): on every Full Charge attack (Mint is an RL, every shot
is a full charge), squad ATK % of Mint's ATK. The Singing gate is time-indexed
(`mint_singing_at`, evaluated with each shot's time), so it works BOTH solo -
reconstructing her per-cycle Dancing/Singing parity from her recorded burst
times - and paired with Prika, whose Encore pins Singing from a specific time
(see prika.py). Its Dancing branch is self HP regen (survivability), not modeled.
"""
from app.effects import Effect
from app.squad_engine import SkillRule, burst_stage_entered

SKILL_VALUE_MANIFESTS = {
    "mint": {
        "source": "dotgg",
        "test_module": "test_skill_rules_mint",
        "keys": {
            "here_i_go": ("skills", 0),
            "fantastic_performance": ("skills", 1),
            "lets_sing_together": ("skills", 2),
        },
    },
}

SINGING_STATUS = "singing"  # pinned by Prika's Encore (see prika.py)


def _singing_by_parity(count):
    # Mint alternates each burst - 1st use Dancing, 2nd Singing, ... - so an
    # even, NON-ZERO burst count is Singing. Before her first burst she is
    # unassigned (neither status), so count 0 is not Singing.
    return count > 0 and count % 2 == 0


FANTASTIC_BURST_STAGE = 3  # skill text: "when entering Burst Stage 3" (fixed, not a data slot)


def _mint_is_singing(context, caster_slug):
    # Live check (Skill 2 at Burst Stage 3 entry): activation_count is the running
    # burst count at this moment. Prika's Encore pin forces Singing regardless.
    return context.has_status(caster_slug, SINGING_STATUS) or _singing_by_parity(
        context.activation_count(caster_slug, "own_burst_activate")
    )


def _stage_three_while_singing(context, caster_slug):
    """Fantastic Performance's gate: the squad has just entered Burst Stage 3
    AND Mint is Singing.

    Burst Stage 3 is entered BEFORE the Burst 3 casts, so this buff reaches
    that cast's own burst damage - unlike a "at the start of Full Burst" bullet
    (Crown's One for All), which lands after it. Mint is Burst 2, so her own
    burst has already fired this cycle and the Singing parity read is settled.
    """
    return burst_stage_entered(FANTASTIC_BURST_STAGE)(context, caster_slug) and _mint_is_singing(
        context, caster_slug
    )


def mint_singing_at(context, caster_slug, time):
    # Time-indexed check for the per-shot pass, which runs AFTER the burst cycle
    # and evaluates against the final context (so activation_count is useless -
    # it's the whole-fight total). Singing at `time` if Prika's Encore pinned it
    # by then, else by parity over only the bursts at or before `time`.
    since = context.status_since(caster_slug, SINGING_STATUS)
    if since is not None and time >= since:
        return True
    n = sum(1 for t in context.burst_times.get(caster_slug, []) if t <= time)
    return _singing_by_parity(n)


def build_mint_rules(values):
    sing_together = values["lets_sing_together"]
    fantastic = values["fantastic_performance"]

    burst_attack_damage = float(sing_together["description_value_01"]) / 100
    burst_attack_damage_duration = float(sing_together["description_value_02"])
    burst_max_ammo = float(sing_together["description_value_03"]) / 100
    burst_max_ammo_duration = float(sing_together["description_value_04"])
    burst_crit_damage = float(sing_together["description_value_05"]) / 100
    burst_crit_damage_duration = float(sing_together["description_value_06"])

    singing_crit_rate = float(fantastic["description_value_01"]) / 100
    singing_crit_rate_duration = float(fantastic["description_value_02"])
    singing_projectile_explosion = float(fantastic["description_value_03"]) / 100
    singing_projectile_explosion_duration = float(fantastic["description_value_04"])
    singing_pierce = float(fantastic["description_value_05"]) / 100
    singing_pierce_duration = float(fantastic["description_value_06"])

    def apply_burst(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("max_ammo_percent", burst_max_ammo, "squad", burst_max_ammo_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect(
                "other_critical_damage_sources", burst_crit_damage, "squad",
                burst_crit_damage_duration, caster_slug,
            ),
            applied_at=time,
        )

    def apply_fantastic_performance(context, caster_slug, time, registry):
        registry.add(
            Effect("crit_rate", singing_crit_rate, "squad", singing_crit_rate_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect(
                "projectile_explosion_damage_up", singing_projectile_explosion, "squad",
                singing_projectile_explosion_duration, caster_slug,
            ),
            applied_at=time,
        )
        registry.add(
            Effect("pierce_damage_up", singing_pierce, "squad", singing_pierce_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="own_burst_activate", action=apply_burst),
        SkillRule(trigger="ally_burst_activate", action=apply_fantastic_performance,
                  condition=_stage_three_while_singing),
    ]


def build_here_i_go_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): while Singing, on
    every Full Charge attack (Mint is an RL, every shot is a full charge), squad
    ATK % of Mint's ATK for 3 sec. The Singing gate is time-indexed via
    `mint_singing_at` (inside the action, which receives the shot time), so it
    works BOTH solo (per-cycle Dancing/Singing parity) and paired with Prika (her
    Encore pins Singing). Refreshing buff - the game refreshes, not stacks, on
    each full charge. The Dancing branch is self HP regen (survivability),
    not modeled."""
    singing_atk = float(values["description_value_01"]) / 100 * values["caster_atk"]
    singing_atk_duration = float(values["description_value_02"])

    def apply(context, caster_slug, time, registry):
        if mint_singing_at(context, caster_slug, time):
            registry.add_refreshing(
                Effect("flat_atk", singing_atk, "squad", singing_atk_duration, caster_slug,
                       refresh_group="here_i_go_singing"),
                applied_at=time,
            )

    return [(1, "every", [SkillRule(trigger="per_shot", action=apply)])]
