"""Charge Damage buffs only reach a unit that is actually firing a charge shot.

"Charge Damage ▲ X%" multiplies a fully-charged shot. An SMG, MG, AR or SG has
no charge, so a squad-wide Charge Damage buff does nothing for its bearer
(Fienn, 2026-07-26) - and the engine was multiplying every allied normal attack
by it regardless. Velvet's +100.8% was roughly DOUBLING her SMG and MG
teammates' normal attacks in Fienn's recorded deck 2.

The exception is what makes this a window test rather than a weapon test:
Nayuta's burst transforms her normal attack into a charge attack for 10s
(`weapon_mode_schedules` with an SR profile), so the buff must reach her for
exactly that window and no longer.
"""
from app.raid_simulator import simulate_raid

RULES_BY_SLUG = {"buffer": [], "midtier": [], "attacker": []}


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats():
    return {s["slug"]: {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0}
            for s in make_deck()}


SMG = {"weapon": "SMG", "damage_percent": 10.0, "max_ammo": 300,
       "reload_time": 2.0, "charge_time": 0.0, "charge_damage_percent": 100.0}
SR = {"weapon": "SR", "damage_percent": 10.0, "max_ammo": 6,
      "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 100.0}


def _normal_damage(weapon_stats, charge_bonus, schedules=None):
    from app.effects import Effect
    from app.squad_engine import SkillRule

    def grant(context, caster_slug, time, registry):
        registry.add(Effect("charge_damage_bonus", charge_bonus, "squad", None,
                            caster_slug), applied_at=time)

    rules = dict(RULES_BY_SLUG)
    rules["buffer"] = [SkillRule(trigger="battle_start", action=grant)]
    result = simulate_raid(
        make_deck(), rules,
        burst_damage_percents={}, base_stats=make_base_stats(),
        enemy_def=0, gauge_charge_time=2.0, fight_duration=40.0, mode="manual",
        base_crit_rate=0.0,
        weapon_stats={s["slug"]: weapon_stats for s in make_deck()},
        weapon_mode_schedules=schedules or {},
    )
    return sum(e["damage"] for e in result["damage_log"]
               if e["slug"] == "attacker" and e["source"] == "normal_attack")


def test_a_charge_damage_buff_does_nothing_for_a_non_charge_weapon():
    assert _normal_damage(SMG, 1.008) == _normal_damage(SMG, 0.0)


def test_a_charge_damage_buff_still_reaches_a_charge_weapon():
    assert _normal_damage(SR, 1.008) > _normal_damage(SR, 0.0)


def test_a_weapon_transform_into_a_charge_mode_lets_the_buff_through():
    """Nayuta's case: an SMG whose burst turns her normal attack into a charge
    attack for a window. Inside it the buff must count."""
    def schedule(context, fight_duration):
        return [{"start": 5.0, "end": 15.0,
                 "profile": {"weapon": "SR", "damage_percent": 10.0,
                             "rate_of_fire": 1.0, "charge_damage_percent": 100.0}}]

    schedules = {"attacker": schedule}
    assert (_normal_damage(SMG, 1.008, schedules)
            > _normal_damage(SMG, 0.0, schedules))
