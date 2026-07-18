"""Ground-truth tests for the solo-raid stat calculator.

Numbers here are measured, not invented: base curves come from the committed
public table snapshot, and the expected ATK is what the collector scraped off
ShiftyPad for Fienn's roster.
"""
import json
from pathlib import Path

import pytest

from app.stat_assembly import (
    affinity_atk,
    corporation_atk,
    equipment_atk,
    breakthrough_multiplier,
    base_atk,
    assemble_atk,
    load_stat_tables,
)

# Rapi: Red Hood - Attacker, grade 3 / core 6, measured 143,543 ATK at level 400.
RAPI_RED_HOOD_RAID400_ATK = 143543


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_base_atk_reads_the_class_curve(tables):
    # Independently reproduced from two different Attackers' stat files.
    assert base_atk(tables, "Attacker", 400) == 90318
    assert base_atk(tables, "Supporter", 400) == 75265
    assert base_atk(tables, "Defender", 400) == 60212


def test_base_atk_rejects_an_unknown_class(tables):
    with pytest.raises(KeyError):
        base_atk(tables, "Healer", 400)


def test_base_atk_is_one_indexed_by_level(tables):
    # Level 1 is the first entry, not the zeroth - an off-by-one here would be
    # invisible at level 400 but wrong everywhere.
    assert base_atk(tables, "Attacker", 1) == 600


@pytest.mark.parametrize(
    "grade, core, expected",
    [
        (0, 0, 1.00),
        (1, 0, 1.02),
        (2, 0, 1.04),
        (3, 0, 1.06),
        (3, 1, 1.06 * 1.02),
        (3, 6, 1.06 * 1.12),
    ],
)
def test_breakthrough_multiplier_is_multiplicative(grade, core, expected):
    # Verified against all 159 collected units: grade and core each contribute
    # 2% of base, and they MULTIPLY rather than add (grade 3 + core 1 measures
    # 1.0812, not 1.08).
    assert breakthrough_multiplier(grade, core) == pytest.approx(expected)


def test_assemble_atk_reproduces_a_measured_unit(tables):
    # The flat contribution of gear/cube/collectible/affinity is not yet derived,
    # so it is supplied here as the residual it is known to be. What this pins is
    # the part that IS derived: the base curve and the breakthrough multiplier.
    atk = assemble_atk(
        tables,
        character_class="Attacker",
        level=400,
        grade=3,
        core=6,
        extra_flat=35057.5,
    )
    assert atk == pytest.approx(RAPI_RED_HOOD_RAID400_ATK, abs=1.0)


def test_assemble_atk_without_extra_flat_undershoots_a_geared_unit(tables):
    # Guards against quietly treating the missing flat term as zero: a geared
    # unit must NOT come out right when it is omitted.
    atk = assemble_atk(tables, character_class="Attacker", level=400, grade=3, core=6)
    assert atk < RAPI_RED_HOOD_RAID400_ATK


# --- full-roster regression ---------------------------------------------------

FIXTURE = Path(__file__).parent / "fixtures" / "stat_ground_truth.json"


@pytest.fixture(scope="module")
def ground_truth():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["units"]


@pytest.fixture(scope="module")
def ground_truth_ranks():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["account_research"]


def test_ground_truth_spans_two_levels(ground_truth):
    # The whole point of the fixture: one level cannot separate a base-scaled
    # term from a flat one, so a single-level fixture would silently pass a
    # wrong formula.
    assert {u["level"] for u in ground_truth} == {1, 663}
    assert len(ground_truth) == 159


def test_breakthrough_multiplier_matches_every_measured_unit(tables, ground_truth):
    """Solve each unit's own multiplier from its two measurements and compare.

    For one unit, measured(L) = base[L]*m + flat with `flat` level-independent,
    so m = (measured(663) - measured(400)) / (base[663] - base[400]) - no
    knowledge of gear or affinity required.
    """
    checked, bad = 0, []
    for u in ground_truth:
        if u["level"] == 400:
            continue
        b400 = base_atk(tables, u["class"], 400)
        b_actual = base_atk(tables, u["class"], u["level"])
        if b_actual == b400:
            continue
        solved = (u["measured"]["actual_atk"] - u["measured"]["raid400_atk"]) / (b_actual - b400)
        predicted = breakthrough_multiplier(u["grade"], u["core"])
        checked += 1
        # Measurements are integers, so the solved ratio carries rounding noise.
        if abs(solved - predicted) > 1e-4:
            bad.append((u["name_en"], u["grade"], u["core"], round(solved, 6), round(predicted, 6)))
    assert checked >= 150, f"only {checked} units usable - fixture may have degraded"
    assert bad == [], f"units whose measured multiplier disagrees: {bad[:8]}"


def test_affinity_does_not_enter_the_multiplier(tables, ground_truth):
    """Units sharing (grade, core) must solve to the same multiplier regardless
    of affinity - this is what rules affinity out of the percentage term."""
    groups: dict[tuple[int, int], set[int]] = {}
    for u in ground_truth:
        if u["level"] == 400:
            continue
        b400 = base_atk(tables, u["class"], 400)
        b_actual = base_atk(tables, u["class"], u["level"])
        if b_actual == b400:
            continue
        solved = (u["measured"]["actual_atk"] - u["measured"]["raid400_atk"]) / (b_actual - b400)
        groups.setdefault((u["grade"], u["core"]), set()).add(u["attractive_lv"])
        assert abs(solved - breakthrough_multiplier(u["grade"], u["core"])) <= 1e-4
    # The claim is only meaningful if some group actually varies in affinity.
    assert any(len(v) > 1 for v in groups.values()), "no (grade,core) group varied in affinity"


# --- flat term: affinity + corporation research --------------------------------


def test_affinity_atk_is_flat_not_a_percentage(tables):
    # The in-game popup shows 2340 ATK at affinity rank 40 for an Attacker -
    # the table cell verbatim. Reading it as 23.4% is the misreading this pins.
    assert affinity_atk(tables, "Attacker", 40) == 2340
    assert affinity_atk(tables, "Supporter", 30) == 1367
    assert affinity_atk(tables, "Defender", 40) == 1560
    assert affinity_atk(tables, "Attacker", 1) == 0


def test_corporation_atk_is_per_rank(tables, ground_truth_ranks):
    # Popup: 엘리시온 RANK 170 -> 4,250 ATK, i.e. 25 per rank rather than 25 total.
    assert corporation_atk(tables, "ELYSION", ground_truth_ranks) == 4250
    assert corporation_atk(tables, "PILGRIM", ground_truth_ranks) == 4750


def test_flat_model_reproduces_every_ungeared_unit(tables, ground_truth, ground_truth_ranks):
    """With no gear/cube/collectible, measured ATK must fall out of the model.

    These units isolate the terms derived so far, so an error in affinity or
    corporation cannot hide behind an unmodelled gear contribution.
    """
    exact, deviating = 0, []
    for u in ground_truth:
        if u["favorite_item_lv"] or u["harmony_cube_lv"] or max(e["tier"] for e in u["equip"]):
            continue
        predicted = assemble_atk(
            tables,
            character_class=u["class"],
            level=400,
            grade=u["grade"],
            core=u["core"],
            extra_flat=(
                affinity_atk(tables, u["class"], u["attractive_lv"])
                + corporation_atk(tables, u["corporation"], ground_truth_ranks)
            ),
        )
        delta = u["measured"]["raid400_atk"] - predicted
        if abs(delta) < 1.0:
            exact += 1
        else:
            deviating.append((u["name_en"], round(delta, 1)))
    assert exact >= 20, f"only {exact} ungeared units reproduce exactly"
    # Three Attackers at affinity 30 come out 0.08-0.52% low and the cause is not
    # yet known. Pinned by name so the list cannot quietly grow.
    assert sorted(n for n, _ in deviating) == ["Brid", "Julia", "Trony"], deviating
    assert all(abs(d) < 600 for _, d in deviating), deviating


# --- equipment ----------------------------------------------------------------

ATTACKER_HEAD_T10 = 3111001  # 공격력 6014 at LV.00 on the in-game level-up screen
DEFENDER_ARM_T10 = 3321001  # Module_C, 공격력 2551 / 방어력 800 on screen


def test_equipment_atk_matches_the_in_game_level_up_screen(tables):
    # capturedimages/equip-stats-attacker-head-lv{0,5}.png
    assert equipment_atk(tables, ATTACKER_HEAD_T10, 0) == 6014
    assert equipment_atk(tables, ATTACKER_HEAD_T10, 5) == 6014 + 3007
    # A level in the middle, cross-checked against Asuka's measured residual.
    assert equipment_atk(tables, ATTACKER_HEAD_T10, 3) == 6014 + 1804


def test_equipment_atk_rounds_halves_to_even(tables):
    # capturedimages/equip-stats-defender-arm-lv5.png: 2551 -> +1276, and
    # 2551 * 0.5 = 1275.5 lands on the even 1276 rather than truncating to 1275.
    assert equipment_atk(tables, DEFENDER_ARM_T10, 0) == 2551
    assert equipment_atk(tables, DEFENDER_ARM_T10, 5) == 2551 + 1276


def test_equipment_atk_is_zero_for_an_unequipped_slot(tables):
    assert equipment_atk(tables, 0, 0) == 0
