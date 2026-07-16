"""Gap #9: the "first_bullet" per-shot mode (fires on the round that OPENS
each magazine, including t=0 - "at the start of battle and upon reloading to
Max Ammunition"), the RoundGrant second-pass refactor it needs (a grant
recorded BY a per-shot rule must still cover that unit's next N shots), and
the normal_attack_damage_multiplier phase-2 term (a Final ATK modifier on the
user's normal attacks only)."""
from app.effects import Effect
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, round_buff_rule


def _deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Fire", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Fire", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]


def _ar_weapon(max_ammo=12):
    return {"weapon": "AR", "damage_percent": 10.0, "max_ammo": max_ammo,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 100.0}


def _run(attacker_rules=(), per_shot_rules=None, periodic_nukes=None,
         burst_damage_percents=None, fight_duration=3.5, max_ammo=12):
    deck = _deck()
    return simulate_raid(
        deck=deck,
        rules_by_slug={"buffer": [], "midtier": [], "attacker": list(attacker_rules)},
        burst_damage_percents=burst_damage_percents or {},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo)},
        per_shot_rules=per_shot_rules or {},
        periodic_nukes=periodic_nukes or {},
    )


def test_first_bullet_mode_fires_exactly_at_magazine_opening_shots():
    # AR 12/s, 12 ammo, 1s reload: magazines open at t=0.0 and t=2.0.
    per_shot = {"attacker": [(None, "first_bullet", [instant_nuke_pulse_rule("per_shot", 100.0)])]}
    result = _run(per_shot_rules=per_shot)
    nukes = [e["time"] for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert nukes == [0.0, 2.0]


def test_first_bullet_round_grant_covers_the_next_shots_of_the_same_unit():
    # Ordering regression for the RoundGrant second pass: a grant recorded BY
    # a per-shot rule (here at each magazine's first bullet) must convert into
    # an Effect covering that unit's next 9 shots - under the old code grants
    # were converted before the unit's own per-shot rules ran, so this grant
    # never landed.
    per_shot = {"attacker": [(None, "first_bullet", [
        round_buff_rule("per_shot", [("normal_attack_damage_multiplier", 0.30, "self")], shots=9)
    ])]}
    baseline = _run()
    boosted = _run(per_shot_rules=per_shot)
    base_shots = [(e["time"], e["damage"]) for e in baseline["damage_log"] if e["source"] == "normal_attack"]
    boost_shots = [(e["time"], e["damage"]) for e in boosted["damage_log"] if e["source"] == "normal_attack"]
    assert [t for t, _ in base_shots] == [t for t, _ in boost_shots]
    # magazines open at 0.0 and 2.0; shots 1-9 of each magazine are 1.30x,
    # shots 10-12 are not.
    per_magazine_index = {}
    for (t, base_damage), (_, boost_damage) in zip(base_shots, boost_shots):
        magazine = 0 if t < 2.0 else 1
        idx = per_magazine_index[magazine] = per_magazine_index.get(magazine, 0) + 1
        expected = base_damage * 1.30 if idx <= 9 else base_damage
        assert round(boost_damage, 6) == round(expected, 6), (t, idx)


def test_normal_attack_damage_multiplier_scales_only_normal_attacks():
    # A permanent multiplier raises every normal-attack entry by exactly 1.30x
    # and leaves burst / periodic entries untouched.
    rules = [buff_rule("battle_start", [("normal_attack_damage_multiplier", 0.30, "self", None)])]
    kwargs = dict(
        burst_damage_percents={"attacker": 100.0},
        periodic_nukes={"attacker": {"cooldown": 1.0, "percent": 50.0}},
        fight_duration=6.0,
    )
    baseline = _run(**kwargs)
    boosted = _run(attacker_rules=rules, **kwargs)

    def by_source(result, source):
        return [(e["time"], e["damage"]) for e in result["damage_log"] if e["source"] == source]

    base_normals, boost_normals = by_source(baseline, "normal_attack"), by_source(boosted, "normal_attack")
    assert base_normals and len(base_normals) == len(boost_normals)
    for (t, base_damage), (_, boost_damage) in zip(base_normals, boost_normals):
        assert round(boost_damage, 6) == round(base_damage * 1.30, 6), t
    assert by_source(baseline, "burst") == by_source(boosted, "burst")
    assert by_source(baseline, "periodic") == by_source(boosted, "periodic")
