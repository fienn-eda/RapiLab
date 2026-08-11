from app import user_roster
from app.models import OverloadOption, UserNikkeState
from app.roster import assemble_simulation_inputs
from app.user_roster import load_nikke_spec, load_roster


def _state(slug, **overrides):
    payload = {
        "character_slug": slug,
        "level": 200,
        "hp": 1_000_000.0,
        "atk": 60_000.0,
        "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }
    payload.update(overrides)
    return UserNikkeState(**payload)


def test_loads_drake_end_to_end_from_real_data_files():
    spec = load_nikke_spec(_state("drake"))
    assert spec is not None
    assert spec.burst_tier == 3
    assert spec.element == "Fire"
    assert spec.weapon == "SG"
    assert spec.burst_cooldown == 40.0
    assert spec.base_stats == {"atk": 60_000.0, "def": 3_000.0, "max_hp": 1_000_000.0}
    # weapon stats from data/dotgg/char_drake-nikke.json ("damage": "214.3%", maxAmmo 9, ...)
    # reload_time is the file's 0.5 sec x 3, because Drake is a clip shotgun:
    # she loads three of her nine rounds at a time (registry.CLIP_RELOAD_SPLITS).
    assert spec.weapon_stats == {
        "weapon": "SG", "damage_percent": 214.3, "max_ammo": 9,
        "reload_time": 1.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
    }
    # skill values assembled at max level (DRAKE_SPECIAL fixture ground truth)
    assert float(spec.skill_values["drake_special"]["description_value_01"]) == 1254.0


def test_skill_levels_flow_into_assembled_values():
    lv1 = load_nikke_spec(_state("drake", skill_levels={"skill1": 10, "skill2": 10, "burst": 1}))
    lv10 = load_nikke_spec(_state("drake"))
    assert float(lv1.skill_values["drake_special"]["description_value_01"]) < float(
        lv10.skill_values["drake_special"]["description_value_01"]
    )


def test_overload_options_pass_through():
    # overload_options stay OverloadOption models: roster._passive_effects hands
    # them to overload_options_to_effects, which reads .name/.value attributes.
    spec = load_nikke_spec(_state(
        "drake",
        overload_options=[{"name": "공격력 증가", "value": 10.0}],
    ))
    assert spec.overload_options == [OverloadOption(name="공격력 증가", value=10.0)]
    # the assembled spec must survive roster assembly (every unit also gets
    # the assumed harmony cube's effects - see cube_effects.assumed_cube_effects)
    assemble_simulation_inputs([spec])


def test_dotgg_slug_manifest_key_bridges_source_slug_mismatch():
    # ada-wong's lootandwaifus slug is "ada-wong" but dotgg's url is "ada"
    # (dotgg shortens collab names); the manifest's dotgg_slug key points the
    # weapon-stats lookup at the right file while skill values stay on the
    # lootandwaifus slug.
    spec = load_nikke_spec(_state("ada-wong"))
    assert spec is not None
    assert spec.burst_tier == 3
    assert spec.element == "Electric"
    assert spec.weapon_stats["weapon"] == "RL"
    assert spec.weapon_stats["max_ammo"] == 6


def test_unloadable_units_are_excluded_not_errors():
    assert load_nikke_spec(_state("totally-unknown")) is None          # not encoded
    # every encoded unit now carries a manifest (KNOWN_MANIFEST_EXCEPTIONS is
    # empty) - privaty, the last holdout used here, loads.
    assert load_nikke_spec(_state("privaty")) is not None


def test_load_roster_partitions_specs_and_excluded():
    specs, excluded = load_roster([_state("drake"), _state("totally-unknown"), _state("privaty")])
    assert [s.slug for s in specs] == ["drake", "privaty"]
    assert excluded == ["totally-unknown"]


def test_load_roster_fans_out_mode_variants(monkeypatch):
    # drake/drake-signature is a real encoded pair (normally reached via the
    # -signature dual-slot mechanism); reused here only as a stand-in slug pair
    # to prove the MODE_VARIANTS fan-out mechanism, monkeypatched empty in prod.
    monkeypatch.setattr(user_roster, "MODE_VARIANTS", {"drake": ("drake", "drake-signature")})
    monkeypatch.setattr(user_roster, "VARIANT_BURST_TIERS", {"drake-signature": 1})
    specs, excluded = load_roster([_state("drake"), _state("privaty")])
    assert [s.slug for s in specs] == ["drake", "drake-signature", "privaty"]
    assert excluded == []
    drake_base, drake_sig, privaty_spec = specs
    assert drake_base.burst_tier == 3  # no VARIANT_BURST_TIERS entry - actual meta burst
    assert drake_sig.burst_tier == 1  # override applied
    # a unit with no MODE_VARIANTS entry fans out to itself only, unaffected
    assert privaty_spec == load_nikke_spec(_state("privaty"))


def test_load_nikke_spec_slug_override_applies_weapon_profile_override(monkeypatch):
    sentinel = {
        "weapon": "RL", "damage_percent": 1.0, "max_ammo": 1,
        "reload_time": 1.0, "charge_time": 1.0, "charge_damage_percent": 1.0,
    }
    monkeypatch.setattr(user_roster, "get_weapon_profile_override",
                        lambda slug, sv, weapon_stats=None: sentinel)
    spec = load_nikke_spec(_state("drake"), slug_override="drake-signature")
    assert spec.slug == "drake-signature"
    assert spec.weapon_stats == sentinel


def test_a_favorite_item_pair_is_not_fanned_out():
    # Identity and candidate fan-out are different questions. miranda and
    # miranda-signature are one character, but the roster loader must NOT turn
    # one owned Miranda into both: whether the player owns the item is settled
    # data, so offering the -signature encoding would hand them an item's
    # effects they may not have.
    specs, excluded = load_roster([_state("miranda")])
    assert [s.slug for s in specs] == ["miranda"]
    assert excluded == []
    signature_only, _ = load_roster([_state("miranda-signature")])
    assert [s.slug for s in signature_only] == ["miranda-signature"]


def test_a_clip_weapon_carries_the_time_to_refill_the_whole_magazine():
    # Centi loads two of her six rounds at a time, three times, so the gap after
    # her magazine empties is 3 x the 0.5 sec in the data file.
    spec = load_nikke_spec(_state("centi"))
    assert spec.weapon_stats["reload_time"] == 1.5


def test_an_ordinary_weapon_keeps_the_file_reload():
    spec = load_nikke_spec(_state("liter"))
    assert spec.weapon_stats["reload_time"] == 1.5  # SMG, one load


def test_grave_reloads_her_magazine_in_two_loads():
    spec = load_nikke_spec(_state("grave"))
    assert spec.weapon_stats["reload_time"] == 2.0


def test_actual_basis_builds_specs_from_the_real_level_stats():
    """유니온은 싱크로 레벨로 싸우므로 다른 스탯 벌을 쓴다. 두 기준이 같은 값을
    내면 스위치는 죽은 코드이므로, 다름 자체를 잰다."""
    state = _state("drake", actual_atk=300_000.0, actual_hp=9_000_000.0)

    specs_400, _ = load_roster([state])
    specs_actual, _ = load_roster([state], stat_basis="actual")

    assert specs_400[0].base_stats == {"atk": 60_000.0, "def": 3_000.0,
                                       "max_hp": 1_000_000.0}
    # DEF가 0인 이유는 스탯 모델이 DEF를 내지 않아 동기화된 로스터의 유니온
    # 쪽에는 애초에 값이 없기 때문이다.
    assert specs_actual[0].base_stats == {"atk": 300_000.0, "def": 0.0,
                                          "max_hp": 9_000_000.0}
