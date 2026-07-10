"""Mint (slug "mint"), a Burst-2 Iron RL supporter. Base skills (no signature
weapon).

Mint alternates between "Assigned Part: Singing" and "...: Dancing" - each use
of her burst (Let's Sing Together!) toggles it, starting at Dancing on her
first use ("if in Dancing, become Singing; if not in Dancing [including
never-assigned], become Dancing"). Modeled without a separate status flag by
reading `context.activation_count(caster_slug, "own_burst_activate") % 2 == 0`
- an even count means she's currently Singing (1st use -> Dancing/count 1 odd,
2nd -> Singing/count 2 even, ...). Her own burst always fires before
full_burst_enter in the same cycle, so the parity is already correct by the
time Fantastic Performance's full_burst_enter rule checks it.

Modeled (DPS-relevant):
- Let's Sing Together! (skills[2], her burst): toggles her Assigned Part (see
  above - no separate effect needed, just the parity read elsewhere); squad
  Attack Damage + Max Ammo % + Critical Damage, all 10 sec. No enemy nuke
  (buff-only burst).
- Fantastic Performance! (skills[1]): on Full Burst enter, IF she's currently
  Singing (the parity check) - squad Critical Rate + squad Pierce Damage,
  10 sec, plus squad Projectile Explosion Damage
  (`projectile_explosion_damage_up`), encoded faithfully but currently INERT -
  raid_simulator doesn't consume that stat yet (see engine-capabilities.md's
  unwired-buckets list). This is one of her two headline Singing-branch buffs,
  so it's worth wiring if Mint (or another Nikke leaning on it) matters for a
  real deck evaluation.

Not modeled: Here I Go! (skills[0]) entirely - both its bullets ("on Full
Charge attack, while Singing: squad ATK; while Dancing: self HP regen") need
an "own full-charge-shot" trigger that doesn't exist (normal-attack shots are
generated in a separate pass in raid_simulator, not routed through
fire_trigger). The Singing branch (squad ATK % of caster's ATK) is real DPS
value and would need this trigger to model - flag to Fienn if Mint's
evaluation looks too thin, since this is likely a meaningful chunk of her kit.
"""
from app.effects import Effect
from app.squad_engine import SkillRule


def _mint_is_singing(context, caster_slug):
    return context.activation_count(caster_slug, "own_burst_activate") % 2 == 0


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
        SkillRule(trigger="full_burst_enter", action=apply_fantastic_performance, condition=_mint_is_singing),
    ]
