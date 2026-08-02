"""무기변형 프로파일이 소장품에 닿는지를, 유닛 목록 없이 지킨다.

프로파일의 `charge_damage_percent`가 0이 아니면 그 값은 둘 중 하나여야 한다:
`caster_weapon_stats`에서 온 값(그 경로는 `user_roster`가 소장품 배율을 이미 곱해
둔다)이거나, `caster_charge_damage_multiplier`를 소비한 값이거나. 둘 다에 무반응인
프로파일은 변형 중 소장품을 통째로 잃는다 - maxwell과 red-hood가 정확히 그
상태였고, Fienn의 2026-08-03 사격장 판독이 그것이 틀렸음을 확정했다
(`docs/measurements/collectible-charge-damage-in-transform.md`).

손으로 유지하는 「걸리는 유닛」 목록 대신 행동 불변식을 쓰는 이유는, 목록은 새
유닛이 등록될 때 조용히 낡기 때문이다(`docs/insights.md`의 힐 제공자 목록 전례).
"""
from types import SimpleNamespace

import pytest

from app.collectible_effects import COLLECTIBLE_SKILL_STATS
from app.skill_rules.registry import (_WEAPON_MODE_SCHEDULE_BUILDERS,
                                      get_skill_value_manifest,
                                      get_weapon_mode_schedules)
from app.skill_values import assemble_skill_values, load_character_data
from app.stat_assembly import load_stat_tables

MAX_LEVELS = {"skill1": 10, "skill2": 10, "burst": 10}

BASE_WEAPON = {"weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
               "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}

TRANSFORM_SLUGS = sorted(_WEAPON_MODE_SCHEDULE_BUILDERS)


def _weapons_whose_collectible_scales_charge_damage():
    """소장품이 차지 대미지 배율을 주는 무기군. 손으로 적지 않고 커밋된 소장품
    테이블과 매핑에서 유도하므로, 매핑이 바뀌면 이 테스트의 적용 범위도 따라온다."""
    weapons = set()
    for record in load_stat_tables()["collectibles"].values():
        for group in record["collection_skill_group_data"]:
            mapping = COLLECTIBLE_SKILL_STATS.get(group["group_id"]) or ()
            if any(slot and slot[0] == "charge_damage_percent" for slot in mapping):
                weapons.add(record["weapon_type"])
    return frozenset(weapons)


CHARGE_DAMAGE_WEAPONS = _weapons_whose_collectible_scales_charge_damage()


class _AnyContext:
    """스케줄이 무엇을 조회하든 답을 주는 문맥. 이 테스트는 프로파일의 수치만
    보므로 타임라인의 내용은 상관없다."""

    def __init__(self, slug):
        self.burst_times = {slug: [20.0]}
        self.full_burst_windows = [(20.0, 30.0)]
        self.shot_times = {}
        self.shot_ammo_rounds = {}

    def __getattr__(self, name):
        return lambda *args, **kwargs: 0.0


def _transform_charge_damage(slug, manifest, weapon_charge, multiplier):
    values = {
        **assemble_skill_values(slug, manifest, MAX_LEVELS),
        "caster_atk": 300_000.0,
        "caster_def": 3_000.0,
        "caster_max_hp": 1_000_000.0,
        "caster_weapon_stats": {**BASE_WEAPON, "charge_damage_percent": weapon_charge},
        "caster_charge_damage_multiplier": multiplier,
    }
    segments = get_weapon_mode_schedules(slug, values)(_AnyContext(slug), 180.0)
    if not segments:
        return None
    return segments[0]["profile"].get("charge_damage_percent")


@pytest.mark.parametrize("slug", TRANSFORM_SLUGS)
def test_a_transform_profile_with_charge_damage_is_reachable_by_the_collectible(slug):
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        pytest.skip(f"{slug} has no skill-value manifest to assemble from")

    data = load_character_data(manifest["source"], manifest.get("data_slug", slug))
    if data["weapon"] not in CHARGE_DAMAGE_WEAPONS:
        return  # 이 무기군의 소장품은 차지 대미지를 올리지 않는다

    baseline = _transform_charge_damage(slug, manifest, 250.0, 1.0)
    if not baseline:
        return  # 차지 대미지가 없는 프로파일에는 배율이 곱할 대상이 없다

    moved_by_weapon = _transform_charge_damage(slug, manifest, 500.0, 1.0) != baseline
    moved_by_multiplier = _transform_charge_damage(slug, manifest, 250.0, 2.0) != baseline

    assert moved_by_weapon or moved_by_multiplier, (
        f"{slug}의 변형 프로파일 charge_damage_percent가 weapon_stats에도 "
        f"caster_charge_damage_multiplier에도 반응하지 않는다 - 그 유닛은 "
        f"변형 중 소장품의 차지대미지 배율을 잃는다")
