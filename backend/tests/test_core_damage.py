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
