from app import roster
from app.effects import Effect
from app.models import OverloadOption, UserNikkeState
from app.raid_simulator import simulate_raid
from app.roster import NikkeSpec, assemble_simulation_inputs
from app.user_roster import load_roster


def helm_spec(overload_options=None):
    return NikkeSpec(
        slug="helm",
        burst_tier=3,
        burst_cooldown=40.0,
        element="Water",
        weapon="SR",
        base_stats={"atk": 398398, "def": 52659, "max_hp": 9198954},
        skill_values={
            "frontline_command": {"description_value_01": "14.64", "description_value_02": "5"},
            "fire_away": {"description_value_01": "3.08", "description_value_02": "27.87", "description_value_03": "10", "description_value_04": "178.98"},
            "aegis_cannon": {"description_value_01": "8236.8", "description_value_04": "158.4", "description_value_05": "10"},
        },
        weapon_stats={
            "weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        },
        overload_options=overload_options or [],
    )


def anis_star_spec():
    return NikkeSpec(
        slug="anis-star",
        burst_tier=1,
        burst_cooldown=20.0,
        element="Electric",
        weapon="RL",
        base_stats={"atk": 260890, "def": 69656, "max_hp": 10720232},
        skill_values={
            "starfall": {
                "description_value_01": "1", "description_value_02": "40.01",
                "description_value_03": "7.48", "description_value_04": "120.13", "description_value_05": "6",
            },
            "stardust": {
                "description_value_01": "35.01", "description_value_02": "10", "description_value_03": "1.26",
                "description_value_04": "92.03", "description_value_05": "10", "description_value_06": "34",
                "description_value_07": "10",
            },
            "star_anis": {
                "description_value_01": "40.01", "description_value_02": "10",
                "description_value_03": "35.2", "description_value_04": "10",
                "description_value_05": "15.02", "description_value_06": "10",
                "description_value_07": "0.7",
            },
        },
        weapon_stats={
            "weapon": "RL", "damage_percent": 61.3, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        },
    )


def rapi_red_hood_spec():
    return NikkeSpec(
        slug="rapi-red-hood",
        burst_tier=3,
        burst_cooldown=40.0,
        element="Fire",
        weapon="MG",
        base_stats={"atk": 300000, "def": 60000, "max_hp": 10000000},
        skill_values={
            "battlefield_assessment": {
                "description_value_01": "1", "description_value_02": "1",
                "description_value_03": "1", "description_value_04": "7.48",
                "description_value_05": "8.02", "description_value_06": "10",
                "description_value_07": "95.04", "description_value_08": "10",
                "description_value_09": "48", "description_value_10": "10",
            },
            "attachable_projectiles": {
                "description_value_01": "150.72", "description_value_02": "100.6",
                "description_value_03": "120", "description_value_04": "88.11",
                "description_value_05": "88.11",
            },
            "power_of_inheritance": {
                "description_value_08": "339.98",
                "description_value_11": "421.2", "description_value_12": "10",
                "description_value_14": "60", "description_value_15": "10",
            },
        },
        weapon_stats={
            "weapon": "MG", "damage_percent": 20.0, "max_ammo": 300,
            "reload_time": 2.0, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    )


def takina_spec():
    return NikkeSpec(
        slug="takina-inoue",
        burst_tier=2,
        burst_cooldown=20.0,
        element="Iron",
        weapon="SR",
        base_stats={"atk": 280000, "def": 60000, "max_hp": 10000000},
        skill_values={
            "combat_support": {
                "description_value_01": "80.04", "description_value_02": "5",
                "description_value_03": "35.05", "description_value_04": "15",
            },
            "battlefield_control": {
                "description_value_01": "10.09", "description_value_02": "5",
                "description_value_03": "140.49", "description_value_04": "10",
            },
            "suppression_initiated": {
                "description_value_01": "200.64", "description_value_02": "10",
                "description_value_03": "6.04", "description_value_04": "5",
            },
        },
        weapon_stats={
            "weapon": "SR", "damage_percent": 69.0, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        },
    )


def crown_spec():
    return NikkeSpec(
        slug="crown",
        burst_tier=2,
        burst_cooldown=20.0,
        element="Iron",
        weapon="MG",
        base_stats={"atk": 281952, "def": 66196, "max_hp": 11621606},
        skill_values={
            "one_for_all": {
                "description_value_01": "64.51", "description_value_02": "15", "description_value_03": "44.35",
                "description_value_04": "15", "description_value_05": "37.44", "description_value_06": "15",
                "description_value_07": "44.35", "description_value_08": "15",
            },
            "royal_attire": {
                "description_value_01": "43", "description_value_02": "4.06",
                "description_value_03": "20", "description_value_04": "5",
                "description_value_05": "5", "description_value_06": "5.23",
                "description_value_07": "20.99", "description_value_08": "7",
            },
            "last_kingdom": {
                "description_value_01": "36.24", "description_value_02": "15",
                "description_value_03": "10.45", "description_value_04": "15",
            },
        },
        weapon_stats={
            "weapon": "MG", "damage_percent": 5.57, "max_ammo": 300,
            "reload_time": 2.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )


def minimal_feasible_deck(helm_overload=None):
    return [anis_star_spec(), crown_spec(), helm_spec(helm_overload)]


def helm_aquamarine_spec():
    return NikkeSpec(
        slug="helm-aquamarine",
        burst_tier=2,
        burst_cooldown=20.0,
        element="Iron",
        weapon="AR",
        base_stats={"atk": 300000, "def": 50000, "max_hp": 9000000},
        skill_values={
            "admire_accompaniment": {
                "description_value_01": "131.34", "description_value_02": "1.82",
                "description_value_03": "2.2", "description_value_04": "2.6",
            },
            "aegis_cannon_overload": {"description_value_01": "164.83"},
            "aegis_cannon_suppression_fire": {
                "description_value_01": "105.58", "description_value_02": "5.64",
                "description_value_03": "5", "description_value_04": "5",
            },
        },
        weapon_stats={
            "weapon": "AR", "damage_percent": 13.65, "max_ammo": 60,
            "reload_time": 2.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )


def _real_specs(slugs):
    states = [UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }) for slug in slugs]
    specs, excluded = load_roster(states)
    assert not excluded, excluded
    return specs


def _anti_at_field_sources(inputs):
    (spec,) = [s for s in inputs["resource_specs"]["asuka-shikinami-langley-wille"]
               if s.name == "anti_at_field"]
    return spec.fill if isinstance(spec.fill, list) else [(spec.fill, 1)]


def test_rei_adds_a_fill_source_to_asukas_anti_at_field_only_when_fielded():
    """"Anti A.T. Field stacks ▲ 10" is REI's bullet writing into ASUKA's
    resource. The numbers are Rei's, so they are declared in her module and
    merged here - the fill source only exists when both are actually fielded,
    which is what the game does.

    The cap stays Asuka's: `resource_count` clamps the merged total, so the
    contribution can never push the count past the 30 her skill states."""
    alone = _anti_at_field_sources(
        assemble_simulation_inputs(_real_specs(["asuka-shikinami-langley-wille"])))
    assert len(alone) == 1, "her own fill only"

    both = _anti_at_field_sources(assemble_simulation_inputs(
        _real_specs(["asuka-shikinami-langley-wille", "rei-ayanami-tentative-name"])))
    contributed = [(fill, amount) for fill, amount in both if fill != alone[0][0]]
    assert len(contributed) == 1
    (fill, amount) = contributed[0]
    assert amount == 10
    assert fill[0] == "per_shot_every_during_own_status_window_by_ally"
    assert fill[1] == 18                                  # her own threshold
    assert fill[3] == "rei-ayanami-tentative-name"        # whose shots feed it


def test_assemble_produces_deck_entries_with_scheduler_fields():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    deck = inputs["deck"]
    assert [m["slug"] for m in deck] == ["anis-star", "crown", "helm"]
    helm = next(m for m in deck if m["slug"] == "helm")
    assert helm["burst_tier"] == 3
    assert helm["element"] == "Water"
    assert helm["cooldown"] == 40.0


def test_assemble_applies_a_permanent_self_burst_cooldown_cut_to_the_scheduler():
    # Moran's Favorite Item cuts her OWN burst cooldown continuously, so the
    # scheduler must see the reduced number rather than her nominal 40 sec.
    spec = NikkeSpec(
        slug="moran-signature",
        burst_tier=1,
        burst_cooldown=40.0,
        element="Electric",
        weapon="AR",
        base_stats={"atk": 100000, "def": 50000, "max_hp": 5000000},
        skill_values={
            "bring_it_on": {"description_value_01": "3.51", "description_value_02": "47.18",
                            "description_value_03": "5", "description_value_04": "20"},
            "leave_it_to_me": {"description_value_10": "7.48"},
            "fair_and_square": {"description_value_01": "14.7", "description_value_04": "10",
                                "description_value_09": "42.57", "description_value_10": "10"},
        },
        weapon_stats={
            "weapon": "AR", "damage_percent": 13.65, "max_ammo": 60,
            "reload_time": 1.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )
    member = assemble_simulation_inputs([spec])["deck"][0]
    assert member["cooldown"] == 20.0


def test_burst_damage_percents_only_includes_nikkes_with_a_burst_nuke():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    # helm has a nuke (Aegis Cannon 8236.8%); anis-star and crown are buff bursts
    assert inputs["burst_damage_percents"] == {"helm": 8236.8}


def test_burst_damage_types_tags_projectile_explosion_nukes():
    # Attack-typed burst nukes are omitted (default); only overrides are listed.
    assert assemble_simulation_inputs(minimal_feasible_deck())["burst_damage_types"] == {}
    inputs = assemble_simulation_inputs([rapi_red_hood_spec()])
    assert inputs["burst_damage_types"] == {"rapi-red-hood": "projectile_explosion"}


def test_base_stats_and_weapon_stats_are_keyed_by_slug():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    assert inputs["base_stats"]["helm"]["atk"] == 398398
    assert inputs["weapon_stats"]["helm"]["weapon"] == "SR"


def test_assembled_inputs_run_through_simulate_raid():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    result = simulate_raid(
        **inputs, enemy_def=0, gauge_charge_time=2.0, fight_duration=60.0, mode="manual",
    )
    assert result["total_damage"] > 0
    assert any(e["source"] == "burst" for e in result["damage_log"])
    assert any(e["source"] == "normal_attack" for e in result["damage_log"])


def test_overload_atk_up_increases_total_damage():
    without = assemble_simulation_inputs(minimal_feasible_deck())
    with_ov = assemble_simulation_inputs(
        minimal_feasible_deck(helm_overload=[OverloadOption(name="공격력 증가", value=40.20)])
    )
    kwargs = dict(enemy_def=0, gauge_charge_time=2.0, fight_duration=60.0, mode="manual")
    dmg_without = simulate_raid(**without, **kwargs)["total_damage"]
    dmg_with = simulate_raid(**with_ov, **kwargs)["total_damage"]
    assert dmg_with > dmg_without


def test_periodic_nukes_only_includes_nikkes_with_one():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    assert inputs["periodic_nukes"] == {}

    inputs_with_aqua = assemble_simulation_inputs([anis_star_spec(), helm_aquamarine_spec()])
    assert inputs_with_aqua["periodic_nukes"] == {
        "helm-aquamarine": {"cooldown": 4.0, "percent": 105.58}
    }


def test_periodic_rules_only_includes_nikkes_with_one():
    assert assemble_simulation_inputs(minimal_feasible_deck())["periodic_rules"] == {}

    inputs = assemble_simulation_inputs([takina_spec()])
    assert set(inputs["periodic_rules"]) == {"takina-inoue"}
    cooldown, rules = inputs["periodic_rules"]["takina-inoue"][0]
    assert cooldown == 15.0
    assert all(r.trigger == "periodic" for r in rules)


def test_periodic_rules_flow_through_simulate_raid():
    inputs = assemble_simulation_inputs([takina_spec()])
    result = simulate_raid(
        **inputs, enemy_def=0, gauge_charge_time=2.0, fight_duration=40.0, mode="manual",
    )
    assert result["total_damage"] > 0


def test_periodic_nukes_flow_through_simulate_raid():
    inputs = assemble_simulation_inputs([anis_star_spec(), helm_aquamarine_spec()])
    result = simulate_raid(
        **inputs, enemy_def=0, gauge_charge_time=2.0, fight_duration=20.0, mode="manual",
    )
    periodic_hits = [e for e in result["damage_log"] if e["source"] == "periodic"]
    assert len(periodic_hits) > 0
    assert all(e["slug"] == "helm-aquamarine" for e in periodic_hits)


def test_cube_reload_speed_effect_moves_damage_through_the_reload_path(monkeypatch):
    # The assumed cube's other_elemental_bonus is inert here (boss_element
    # defaults to None, and that stat is gated on elemental advantage), so
    # this isolates reload_speed_percent - the only cube term with an
    # end-to-end path through normal-attack reload cadence - by swapping
    # assumed_cube_effects for a reload-only stub vs an empty one.
    kwargs = dict(enemy_def=0, gauge_charge_time=2.0, fight_duration=60.0, mode="manual")

    monkeypatch.setattr(roster, "assumed_cube_effects", lambda slug, cube: [])
    dmg_without = simulate_raid(
        **assemble_simulation_inputs(minimal_feasible_deck()), **kwargs
    )["total_damage"]

    monkeypatch.setattr(
        roster,
        "assumed_cube_effects",
        lambda slug, cube: [Effect("reload_speed_percent", 0.2969, "self", None, slug)],
    )
    dmg_with = simulate_raid(
        **assemble_simulation_inputs(minimal_feasible_deck()), **kwargs
    )["total_damage"]

    assert dmg_with > dmg_without
    # Golden pin. Re-baselined 2026-08-05 (latest): the battle-start
    # burst-cooldown-reduction pulse Anis: Star's Starfall grants
    # (skill_rules/anis_star.py's alone_branch, registered on BOTH
    # battle_start and full_burst_end) is no longer banked into cycle 1's own
    # reduction - raid_simulator.on_battle_start now drains it there, since
    # nothing has bursted yet for it to reduce (Fienn, in-game, 2026-08-05).
    # She is in minimal_feasible_deck, so her own rotation is what moved:
    # cycle 1's cooldowns are no longer double-reduced, and the rotation
    # starts marginally slower. Both absolutes fell - 744,964,664 ->
    # 694,864,568 without the cube, 792,975,565 -> 742,128,726 with it. The
    # reload saving's DELTA fell too (48,010,901 -> 47,264,159 - the slower
    # rotation shifts which shots land inside/outside Full Burst windows for
    # the buffed run), but LESS than the base did, so the same saving now
    # buys a marginally larger share of a marginally smaller pie: the RATIO
    # rose 1.0644 -> 1.0680.
    #
    # Re-baselined 2026-07-31: the reload model went affine
    # (`file * (1 - s) + 0.148`), which is exactly this path. The cube's 29.69%
    # now takes 29.69% off the SCALED part instead of dividing the whole reload,
    # so the buff's delta grows: 35,136,487 -> 48,010,901, and the RATIO rises
    # 1.047400 -> 1.064400. Unlike the two entries below, this one IS the reload
    # path moving rather than the base being diluted around it - which is
    # exactly what this pin's split into ratio + delta exists to show.
    #
    # Re-baselined 2026-07-28: Anis: Star's Shooting Stars
    # collect the core hit bonus and carry projectile_explosion damage, both
    # settled by Fienn's range footage. Her ticks are a fixed 40 per cycle that
    # no reload buff buys more of, so this only grows the BASE: 711.0M -> 741.3M
    # and 746.2M -> 776.4M, with the reload DELTA byte-identical at 35,136,487.
    # The RATIO therefore falls 1.049415 -> 1.047400 for the same reason it rose
    # in the 07-27 entry below - dilution, not a change in the reload path.
    #
    # NOTE for the next re-baseline: the "29.24M" delta quoted in the 07-27
    # entry was already stale before this change (measured here at 35,136,487
    # both before and after). Re-measure the delta rather than trusting the
    # last comment's figure - that is what makes this pin worth keeping.
    #
    # Re-baselined 2026-07-27: Full Burst now opens a beat
    # AFTER the tier-3 cast, so a Burst 3's own burst nuke no longer collects
    # any full_burst_enter buff (burst_cycle.FULL_BURST_OPEN_DELAY). Both
    # absolutes fell 902.0M -> 666.9M and 872.8M -> 637.7M, but the reload
    # DELTA is untouched at 29.24M - only burst damage moved - so the RATIO
    # rose 1.0335 -> 1.0458 purely because the base shrank.
    #
    # Re-baselined 2026-07-26: "Damage to Parts ▲ X%" no longer
    # rides the general Damage-Up bucket (it raises damage dealt to PARTS, and
    # this engine models one boss with none - Fienn, 2026-07-26). Helm's Fire
    # Re-baselined 2026-07-27: Anis: Star's Shooting Stars became
    # full_burst_bonus_eligible - her burst opens Full Burst 0.2 sec before the
    # first tick lands, so every tick is computed inside the window. Absolutes
    # rose 876.1M -> 902.0M and 846.9M -> 872.8M. The RATIO fell 1.0345 ->
    # 1.0335: the stars are a fixed 40 ticks per cycle, so a reload buff buys
    # no more of them, and growing them dilutes the share of damage that a
    # reload saving can move.
    #
    # Away grants it squad-wide, so both absolutes fell: 888.6M -> 876.1M and
    # 859.1M -> 846.9M. The RATIO barely moved (1.0343 -> 1.0345) because the
    # term was a flat multiplier on both sides of the comparison.
    #
    # Re-baselined 2026-07-24 before that: "helm" now means the Nikke WITHOUT
    # her Favorite Item (the build is chosen from the user's roster, and the
    # Favorite Item lives at "helm-signature"), which drops her 178.98%
    # full-charge nuke and shrinks her burst 8236.8% -> 1237.5%. Absolutes moved
    # 1124M -> 859M. The RATIO fell (1.0369 -> 1.0343) for a real reason rather
    # than noise: the full-charge nuke fired once per shot, so it was pure
    # leverage on the extra shots a reload buff buys; without it the same reload
    # saving converts to less damage.
    #
    # Re-baselined 2026-07-21 before that: the completeness batch changed all
    # three units in this deck and restored Crown's Last Kingdom via
    # Effect.refresh_group (680M -> 1124M, ratio 1.0224 -> 1.0369, because charge
    # speed began shortening the charge instead of dividing it).
    # Re-baselined 2026-07-28: normal attacks now collect the Full Burst bonus
    # (measured; see raid_simulator's normal-attack record call). Absolutes rose
    # 637.7M -> 722.3M without the cube and 666.9M -> 759.4M with it, and the
    # RATIO rose 1.0458 -> 1.0514 for the same reason this test exists: a reload
    # saving buys extra shots, and those shots are worth more now that the ones
    # landing inside a window carry +0.5 in the major modifier.
    #
    # Re-baselined 2026-07-28 again: Helm: Aquamarine's Admire Accompaniment
    # per-shot nuke ("every 30 normal attacks, deals 131.34% of final ATK as
    # ADDITIONAL damage") now collects the bonus too. Absolutes rose 722.3M ->
    # 741.7M and 759.4M -> 780.9M, and the RATIO rose 1.0514 -> 1.0529 by the
    # same mechanism as the entry above: the nuke fires off a shot COUNT, so
    # the extra shots a reload saving buys carry it, and each is now worth more.
    #
    # Re-baselined 2026-07-28 once more: Helm now carries the 0.4 sec charge
    # motion delay Fienn timed (attack_rate.CHARGE_MOTION_DELAY_SECONDS), so
    # each of her shots occupies 1.4 sec rather than 1.0. The RATIO FELL
    # 1.0529 -> 1.0494, which is the point of the delay: a reload saving buys
    # the same seconds back, but seconds are worth fewer shots now.
    #
    # Re-baselined 2026-08-07: Frontline Command's "Critical Rate of normal
    # attack" moved to the normal_attack_crit_rate bucket, so it stops reaching
    # anything that is not a normal attack. RATIO 1.0680 -> 1.0678, DELTA
    # 47,264,159 -> 46,818,986. The delta moving is not a reload regression: the
    # shots this cube buys also drive Admire Accompaniment's per-shot NUKE, and
    # a nuke is not a normal attack, so each extra shot is now worth slightly
    # less than it was. A reload-path regression would move the delta with the
    # nuke's own value unchanged.
    #
    # Re-baselined again the same day: a machine gun now spins up at the head of
    # every magazine (attack_rate.MG_SPINUP, measured). RATIO 1.0678 -> 1.0527,
    # DELTA 46,818,986 -> 34,754,490. This deck's MG fires fewer rounds per
    # magazine-and-reload cycle, so the seconds a reload saving buys are worth
    # fewer shots - the same mechanism the charge motion delay produced when it
    # landed, and the reason this assertion is split from the delta below.
    # Re-baselined 2026-08-14: the machine gun's warm-up is a measured CURVE
    # rather than one flat reduced rate, so a magazine's 48 ramp rounds sit
    # where they were read - rounds 0-2 take 56 of the ramp's 137 frames. The
    # ramp's total and the magazine's length are unchanged, so this is not the
    # reload path moving: the saving still buys the same seconds, but every
    # ramp round except the last one now lands later inside its own magazine,
    # which shifts which shots fall inside Full Burst and which fit before the
    # fight ends. RATIO 1.0527 -> 1.0524, DELTA 34,754,490 -> 34,564,302 (the
    # absolutes are 660,172,350 without the cube and 694,736,653 with it).
    # Re-baselined again the same day: a machine gun's heating now SURVIVES a
    # short reload, and the reload also ends 12.5 frames before the next round
    # (both measured). This is the reload path moving, which is what the pin is
    # for: the cube's 29.69% no longer buys only seconds, it buys a magazine
    # that opens part way up the ramp. The two runs move in OPPOSITE directions
    # - without the cube the post-reload pause is a pure cost (660,172,350 ->
    # 655,848,890) while with it the retention more than pays for the pause
    # (694,736,653 -> 702,322,805). RATIO 1.0524 -> 1.0709, DELTA 34,564,302 ->
    # 46,473,915.
    assert round(dmg_with / dmg_without, 4) == 1.0709
    # Pin the DELTA too, not just the ratio: the ratio moves whenever anything
    # in this deck's damage moves, but a reload-speed change is the only thing
    # that may move the delta. Splitting them is what stops a re-baseline from
    # quietly absorbing a real regression in the reload path.
    assert round(dmg_with - dmg_without, 0) == 46_473_915.0


def test_weapon_mode_schedules_key_exists_in_assembled_inputs():
    inputs = assemble_simulation_inputs(minimal_feasible_deck())
    assert "weapon_mode_schedules" in inputs
    assert inputs["weapon_mode_schedules"] == {}


def test_assemble_puts_the_full_burst_delta_on_the_member_only_when_nonzero():
    # Real data files (via load_roster) rather than a hand-built NikkeSpec:
    # isabel's -5.0 comes from registry.FULL_BURST_DURATION_DELTA keyed by her
    # slug, so the roster-loading path has to be the one under test.
    states = [
        UserNikkeState(
            character_slug=slug, level=200,
            hp=1_000_000.0, atk=60_000.0, def_=3_000.0,
            skill_levels={"skill1": 10, "skill2": 10, "burst": 10},
        )
        for slug in ("liter", "arcana", "isabel")
    ]
    specs, _excluded = load_roster(states)
    inputs = assemble_simulation_inputs(specs)
    by_slug = {m["slug"]: m for m in inputs["deck"]}

    assert by_slug["isabel"]["full_burst_duration_delta"] == -5.0
    assert "full_burst_duration_delta" not in by_slug["arcana"]


def test_assemble_wires_sodas_conditional_full_burst_delta():
    """조건부 FB 델타는 member가 아니라 별도 딕셔너리로 나간다 - burst_cycle이
    아니라 resolution 뒤의 해석기가 읽기 때문."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in ("liter", "crown", "soda-twinkling-bunny")
    ]
    specs, excluded = load_roster(states)
    assert not excluded
    inputs = assemble_simulation_inputs(specs)

    deltas = inputs["conditional_full_burst_deltas"]
    assert set(deltas) == {"soda-twinkling-bunny"}
    assert deltas["soda-twinkling-bunny"]["resource"] == "chip"
    assert deltas["soda-twinkling-bunny"]["tiers"] == [(10.0, 2.0), (20.0, 5.0)]
    # member에는 아무것도 안 붙는다
    soda_member = next(m for m in inputs["deck"] if m["slug"] == "soda-twinkling-bunny")
    assert "conditional_full_burst_delta" not in soda_member


def test_assemble_leaves_conditional_deltas_empty_without_such_a_unit():
    """소다 없는 덱은 빈 딕셔너리 - 이게 '1패스로 끝난다'의 출발점이다."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in ("liter", "crown", "modernia")
    ]
    specs, _ = load_roster(states)
    assert assemble_simulation_inputs(specs)["conditional_full_burst_deltas"] == {}


def test_assemble_wires_sodas_gated_nuke_alongside_her_cofired_buff():
    """registry.PER_SHOT_RULE_BUILDERS의 소다 항목은
    build_lucky_golden_chip_per_shot_rules(sv) + build_beginners_rewards_per_shot_rules(sv)
    두 항을 더한 것 - 후자(넉, threshold 1)가 빠져도 이 항목을 직접 부르는
    단위 테스트는 하나도 안 깨진다. assemble_simulation_inputs를 거쳐야
    레지스트리 배선 자체가 검증된다 (test_assemble_puts_the_full_burst_delta_
    on_the_member_only_when_nonzero가 FULL_BURST_DURATION_DELTA를 지키는 것과
    같은 자리)."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in ("liter", "crown", "soda-twinkling-bunny")
    ]
    specs, excluded = load_roster(states)
    assert not excluded
    inputs = assemble_simulation_inputs(specs)

    rules = inputs["per_shot_rules"]["soda-twinkling-bunny"]
    modes = {(threshold, mode) for threshold, mode, _skill_rules in rules}
    # 넉(Beginner's Rewards) - threshold 1, 확장 창 안 매 평타.
    assert (1, "every_during_full_burst") in modes
    # 골든칩 공동발동 버프(Lucky Golden Chip) - threshold 3.
    assert (3, "every_during_full_burst") in modes
