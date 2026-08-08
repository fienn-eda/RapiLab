"""유닛별 코어 대미지 배율 — 표가 수집 데이터와 맞는가.

`data/`는 gitignore라 101슬러그 전수 대조는 감사 스크립트
(`scripts/audit_core_damage_rate.py`)가 한다. 여기서는 추적되는 픽스처로
양쪽 방향을 박는다: 표에 있는 유닛은 그 값이 맞고, 표에 없는 유닛은 기본값이
맞다. 한쪽만 박으면 표가 통째로 비어도 절반은 통과한다.
"""
import json
from pathlib import Path

from app.core_damage import (
    CORE_DAMAGE_RATE,
    DEFAULT_CORE_DAMAGE_RATE,
    core_hit_bonus_for,
)
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"


def _collected_rate(slug):
    """이 유닛의 raw 번들이 적은 core_damage_rate."""
    bundle = json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))
    return bundle["detail"]["shot_detail"]["core_damage_rate"]


def test_the_table_carries_the_collected_rate_for_a_25000_unit():
    assert _collected_rate("miranda") == 25000
    assert CORE_DAMAGE_RATE["miranda"] == 25000


def test_a_unit_absent_from_the_table_is_20000_in_the_data():
    assert _collected_rate("julia") == DEFAULT_CORE_DAMAGE_RATE
    assert "julia" not in CORE_DAMAGE_RATE


def test_the_rate_converts_to_the_major_modifier_term():
    # 25000 = 250% = 1 + 1.5, 20000 = 200% = 1 + 1.0
    assert core_hit_bonus_for("miranda") == 1.5
    assert core_hit_bonus_for("julia") == 1.0


def test_an_unknown_slug_gets_the_default():
    assert core_hit_bonus_for("no-such-nikke") == 1.0


def test_the_favorite_item_build_shares_the_base_units_weapon_rate():
    # 애장품 빌드는 load_weapon_data가 base 유닛의 무기 파일을 읽으므로 같은
    # 무기이고, 따라서 같은 배율이다.
    assert CORE_DAMAGE_RATE["miranda-signature"] == CORE_DAMAGE_RATE["miranda"]


# --- 엔진이 실제로 그 값을 쓰는가 ---
#
# ATK 10000 x 발당 100%, 적 DEF 0, 크리 0%, 풀버스트 창이 열리기 전에 전투가
# 끝나므로 한 발의 major modifier는 코어 보너스 하나뿐이다. 그래서 한 발은 곧
# 10000 x (1 + 보너스)이고, 값으로 박을 수 있다.
_WEAPON = {"weapon": "AR", "damage_percent": 100.0, "max_ammo": 999,
           "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0}


def _first_shot(striker_slug, *, core_hittable=True):
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": striker_slug, "burst_tier": 3, "element": "Iron",
         "cooldown": 20.0, "weapon": "AR"},
    ]
    log = simulate_raid(
        deck,
        {"b1": [], "b2": [], striker_slug: []},
        burst_damage_percents={striker_slug: 100.0},
        base_stats={s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in deck},
        enemy_def=0,
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={striker_slug: _WEAPON},
        core_hittable=core_hittable,
    )["damage_log"]
    return next(e["damage"] for e in log if e["source"] == "normal_attack")


def test_a_25000_unit_hits_the_core_for_more_than_a_20000_unit():
    assert _first_shot("miranda") == 25000.0      # 10000 x (1 + 1.5)
    assert _first_shot("julia") == 20000.0        # 10000 x (1 + 1.0)


def test_the_higher_rate_needs_a_core_to_land_on():
    # 코어가 없는 보스에서는 아무도 보너스를 받지 않는다 - 2.5배 유닛도 마찬가지다.
    assert _first_shot("miranda", core_hittable=False) == 10000.0
    assert _first_shot("julia", core_hittable=False) == 10000.0


def test_the_body_hit_behind_the_core_is_untouched_by_the_higher_rate():
    """관통 유닛의 발은 코어를 뚫고 본체에 또 맞는다 - 그 본체 인스턴스는
    코어 보너스를 받지 않으므로 2.5배 유닛이라도 그대로 10000이다."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "miranda", "burst_tier": 3, "element": "Iron",
         "cooldown": 20.0, "weapon": "AR"},
    ]
    log = simulate_raid(
        deck,
        {"b1": [], "b2": [],
         "miranda": [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]},
        burst_damage_percents={"miranda": 100.0},
        base_stats={s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in deck},
        enemy_def=0,
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={"miranda": _WEAPON},
        core_hittable=True,
        pierce_hits_body_behind_core=True,
    )["damage_log"]
    shots = [e["damage"] for e in log if e["source"] == "normal_attack"]
    # core 10000 x (1 + 1.5), body 10000 x 1
    assert shots[:2] == [25000.0, 10000.0]


def _core_strike_damage(caster_slug):
    """caster_slug가 core_strike 스킬딜을 쏘는 버스트 한 발."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": caster_slug, "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    log = simulate_raid(
        deck,
        {s["slug"]: [] for s in deck},
        burst_damage_percents={caster_slug: 100.0},
        base_stats={s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in deck},
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        core_hittable=True,
        burst_damage_types={caster_slug: "core_strike"},
    )["damage_log"]
    return next(e["damage"] for e in log if e["source"] == "burst")


def test_core_strike_collects_the_casters_own_rate_not_just_normal_attacks():
    # core_strike는 스킬딜이지만 core_eligible이 인정하는 예외라 평타와 똑같이
    # 시전자의 배율을 받는다 - 보너스가 평타로만 좁혀지면 미란다 쪽이 20000으로
    # 떨어져 잡아낸다.
    assert _core_strike_damage("miranda") == 25000.0    # 10000 x (1 + 1.5)
    assert _core_strike_damage("julia") == 20000.0       # 10000 x (1 + 1.0)
