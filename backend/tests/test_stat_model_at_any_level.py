"""스탯 모델은 솔로레이드의 400레벨 밖에서도 맞는다.

유니온의 모든 수치가 이 위에 선다: 싱크로 레벨로 조립하는 것은 같은 모델에
`level`만 다르게 넣는 것이다. 픽스처의 `actual_*`는 ShiftyPad가 각 니케의 실제
레벨(1 또는 668)로 계산해 화면에 띄운 값을 스크랩한 것이라
(`scripts/build_stat_ground_truth.py`: "both scraped"), 이 대조는 우리 자신이
아니라 게임을 상대로 한다.

`test_stat_assembly.py`의 `test_flat_model_reproduces_every_ungeared_unit`과
겹치지 않는다 - 저쪽은 장비 없는 유닛만, 400레벨, ATK만 본다.
"""
import json
from pathlib import Path

import pytest

from app.roster_assembly import _gear_atk, _gear_hp
from app.stat_assembly import (affinity_atk, affinity_hp, assemble_atk,
                               assemble_hp, corporation_atk, load_stat_tables,
                               research_hp)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "stat_ground_truth.json"


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


@pytest.fixture(scope="module")
def fixture_data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_the_fixture_still_carries_levels_other_than_400(fixture_data):
    """이것이 깨지면 아래 테스트는 아무것도 재지 않는다 - 모든 유닛이 400이면
    "임의 레벨에서 맞는다"를 400 하나로 확인하는 셈이 된다."""
    assert {u["level"] for u in fixture_data["units"]} - {400}


def test_the_model_reproduces_the_scraped_stats_at_each_units_own_level(
        tables, fixture_data):
    ranks = fixture_data["account_research"]
    off = []
    for u in fixture_data["units"]:
        atk = assemble_atk(
            tables, character_class=u["class"], level=u["level"],
            grade=u["grade"], core=u["core"],
            affinity_flat=affinity_atk(tables, u["class"], u["attractive_lv"]),
            research_flat=corporation_atk(tables, u["corporation"], ranks),
            extra_flat=_gear_atk(tables, u))
        hp = assemble_hp(
            tables, character_class=u["class"], level=u["level"],
            grade=u["grade"], core=u["core"],
            affinity_flat_hp=affinity_hp(tables, u["class"], u["attractive_lv"]),
            research_flat_hp=research_hp(tables, u["class"], ranks),
            extra_flat_hp=_gear_hp(tables, u))
        if abs(round(atk) - u["measured"]["actual_atk"]) > 1:
            off.append((u["name_en"], "atk", round(atk), u["measured"]["actual_atk"]))
        if abs(round(hp) - u["measured"]["actual_hp"]) > 1:
            off.append((u["name_en"], "hp", round(hp), u["measured"]["actual_hp"]))
    assert off == [], f"units the model misses at their own level: {off[:8]}"
