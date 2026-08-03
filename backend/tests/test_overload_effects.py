from app.effects import EffectRegistry
from app.models import OverloadOption
from app.overload_effects import overload_options_to_effects


def test_atk_up_overload_maps_to_atk_percent_effect():
    effects = overload_options_to_effects(
        [OverloadOption(name="공격력 증가", value=11.81)], source_slug="crown"
    )
    assert len(effects) == 1
    assert effects[0].stat == "atk_percent"
    assert round(effects[0].value, 4) == 0.1181
    assert effects[0].scope == "self"
    assert effects[0].duration is None


def test_superior_code_damage_maps_to_other_elemental_bonus():
    effects = overload_options_to_effects(
        [OverloadOption(name="우월코드 대미지 증가", value=88.61)], source_slug="anis-star"
    )
    assert effects[0].stat == "other_elemental_bonus"
    assert round(effects[0].value, 4) == 0.8861


def test_critical_damage_maps_to_other_critical_damage_sources():
    effects = overload_options_to_effects(
        [OverloadOption(name="크리티컬 대미지 증가", value=11.54)], source_slug="anis-star"
    )
    assert effects[0].stat == "other_critical_damage_sources"
    assert round(effects[0].value, 4) == 0.1154


def test_charge_damage_maps_to_charge_damage_bonus():
    effects = overload_options_to_effects(
        [OverloadOption(name="차지 대미지 증가", value=9.70)], source_slug="helm"
    )
    assert effects[0].stat == "charge_damage_bonus"
    assert round(effects[0].value, 4) == 0.097


def test_not_yet_consumed_stats_still_produce_named_effects():
    # crit rate / charge speed / max ammo aren't wired into damage_formula yet
    # (no attack-rate model), but we still capture them under a stable name
    # so nothing is silently dropped.
    effects = overload_options_to_effects(
        [
            OverloadOption(name="크리티컬 확률 증가", value=5.71),
            OverloadOption(name="차지 속도 증가", value=3.16),
            OverloadOption(name="최대 장탄 수 증가", value=48.39),
        ],
        source_slug="crown",
    )
    stats = {e.stat for e in effects}
    assert stats == {"crit_rate", "charge_speed_percent", "max_ammo_percent"}


def test_multiple_overload_options_all_convert():
    options = [
        OverloadOption(name="우월코드 대미지 증가", value=88.61),
        OverloadOption(name="공격력 증가", value=40.20),
        OverloadOption(name="최대 장탄 수 증가", value=48.39),
        OverloadOption(name="크리티컬 대미지 증가", value=11.54),
    ]
    effects = overload_options_to_effects(options, source_slug="anis-star")
    assert len(effects) == 4


def test_unknown_overload_name_raises():
    import pytest

    with pytest.raises(ValueError, match="unknown overload option"):
        overload_options_to_effects(
            [OverloadOption(name="존재하지않는옵션", value=1.0)], source_slug="anis-star"
        )


def test_converted_effects_plug_directly_into_effect_registry():
    effects = overload_options_to_effects(
        [
            OverloadOption(name="공격력 증가", value=40.20),
            OverloadOption(name="우월코드 대미지 증가", value=88.61),
        ],
        source_slug="anis-star",
    )
    registry = EffectRegistry()
    for effect in effects:
        registry.add(effect, applied_at=0.0)

    anis = {"slug": "anis-star", "element": "Electric"}
    assert round(registry.total_for("atk_percent", anis, now=123.0), 4) == 0.402
    assert round(registry.total_for("other_elemental_bonus", anis, now=123.0), 4) == 0.8861


def test_the_charge_speed_ceiling_is_a_top_roll_on_every_gear_slot():
    """The most charge speed overload alone can grant. Derived rather than
    written down: the roll ladder is in the committed stat tables and the
    grouping is `charge_speed_percent_from_lines`, so a re-fitted table moves
    this without an edit. Four slots at 6.09 sum to 24.36 and group to 24."""
    from app.overload_effects import max_charge_speed_percent
    from app.stat_assembly import load_stat_tables

    assert max_charge_speed_percent(load_stat_tables()) == 24.0
