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
    cube_atk,
    collectible_atk,
    owns_favorite_item,
    breakthrough_multiplier,
    base_atk,
    core_flat_atk,
    assemble_atk,
    load_stat_tables,
)

# Rapi: Red Hood - Attacker, grade 3 / core 6, measured 143,543 ATK at level 400.
RAPI_RED_HOOD_RAID400_ATK = 143543
# The committed public directory snapshot; the ground truth is keyed by name, and
# resource_id is what the calculator identifies a unit by.
DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "tools" / "collect-blablalink" / "nikke-directory.json"
)


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
    # Rapi: Red Hood's gear/cube/collectible/affinity contribution, supplied as
    # the residual it is measured to be. What this pins is the part that IS
    # derived: the base curve, the breakthrough multiplier and the core flat.
    atk = assemble_atk(
        tables,
        character_class="Attacker",
        level=400,
        grade=3,
        core=6,
        corporation_sub_type="OVERSPEC",
        extra_flat=35460,
    )
    assert atk == pytest.approx(RAPI_RED_HOOD_RAID400_ATK, abs=1.0)


def test_assemble_atk_without_extra_flat_undershoots_a_geared_unit(tables):
    # Guards against quietly treating the missing flat term as zero: a geared
    # unit must NOT come out right when it is omitted.
    atk = assemble_atk(
        tables, character_class="Attacker", level=400, grade=3, core=6,
        corporation_sub_type="OVERSPEC",
    )
    assert atk < RAPI_RED_HOOD_RAID400_ATK


# --- per-core flat ------------------------------------------------------------


def test_core_flat_atk_defaults_to_the_class_value():
    assert core_flat_atk("Attacker") == pytest.approx(118.95)
    assert core_flat_atk("Supporter") == pytest.approx(113.29)
    assert core_flat_atk("Defender") == pytest.approx(107.87)


def test_pilgrims_get_more_atk_per_core(tables):
    # Scarlet and the other four Pilgrim Attackers all measure ~143 per core
    # against the 118.95 every other SSR Attacker measures.
    assert core_flat_atk("Attacker", corporation="PILGRIM") == pytest.approx(142.90)
    assert core_flat_atk("Defender", corporation="PILGRIM") == pytest.approx(127.22)
    assert core_flat_atk("Attacker", corporation="ELYSION") == pytest.approx(118.95)


def test_overspec_units_sit_between_their_class_and_a_pilgrim():
    # Rapi: Red Hood and the other two awakened Counters carry the game's own
    # corporation_sub_type: OVERSPEC and measure 132.95 as ELYSION Attackers.
    assert core_flat_atk("Attacker", corporation_sub_type="OVERSPEC") == pytest.approx(132.95)
    assert core_flat_atk("Defender", corporation_sub_type="OVERSPEC") == pytest.approx(116.79)
    # Every Pilgrim is OVERSPEC too, and worth more than a Counter.
    assert core_flat_atk(
        "Attacker", corporation="PILGRIM", corporation_sub_type="OVERSPEC"
    ) == pytest.approx(142.90)


def test_a_units_own_measured_core_flat_wins_over_every_rule():
    # Vesti is a plain ELYSION Attacker by every field we can read, yet measures
    # 94.22 rather than the class's 118.95.
    assert core_flat_atk("Attacker", resource_id=91) == pytest.approx(94.22)
    assert core_flat_atk("Attacker", corporation="ELYSION") == pytest.approx(118.95)


def test_core_flat_atk_rejects_an_unknown_class():
    with pytest.raises(KeyError):
        core_flat_atk("Healer")


def test_an_unmeasured_pilgrim_class_refuses_to_guess():
    # No Pilgrim Supporter in the ground truth has a core, so its per-core flat
    # is unknown. Answering with the class value would be wrong by ~14 per core.
    with pytest.raises(KeyError):
        core_flat_atk("Supporter", corporation="PILGRIM")


def test_a_coreless_unit_needs_no_identity(tables):
    # A unit with no cores never reaches the per-core flat, so an un-measured
    # Pilgrim Supporter still assembles as long as it has no cores.
    assert assemble_atk(
        tables, character_class="Supporter", level=400, grade=3, core=0,
        corporation="PILGRIM",
    ) > 0


# --- full-roster regression ---------------------------------------------------

FIXTURE = Path(__file__).parent / "fixtures" / "stat_ground_truth.json"


@pytest.fixture(scope="module")
def ground_truth():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["units"]


@pytest.fixture(scope="module")
def ground_truth_ranks():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["account_research"]


@pytest.fixture(scope="module")
def identity():
    """name -> the snapshot fields that select a unit's per-core flat."""
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    return {
        e["name_en"]: {
            "resource_id": e["resource_id"],
            "corporation_sub_type": e.get("corporation_sub_type"),
        }
        for e in directory
    }


def test_the_snapshot_carries_the_overspec_field(identity):
    """A snapshot refreshed without `--deep` would drop corporation_sub_type.

    Nothing else would fail: every OVERSPEC unit would quietly fall back to its
    class value and read ~14-24 ATK per core low. So assert the field is there
    and that it still marks the units it is known to mark.
    """
    overspec = {n for n, e in identity.items() if e["corporation_sub_type"] == "OVERSPEC"}
    assert {"Rapi: Red Hood", "Anis: Star", "Neon: Vision Eye"} <= overspec
    # Every Pilgrim measured is OVERSPEC, which is why corporation alone settles
    # a Pilgrim in core_flat_atk.
    assert {"Scarlet", "Modernia", "Red Hood", "Noah", "Crown", "Cinderella"} <= overspec


def test_every_measured_unit_is_in_the_directory(ground_truth, identity):
    # The join below is only sound if it is total - a missed name would silently
    # fall back to the class default and hide a per-unit core flat.
    missing = sorted({u["name_en"] for u in ground_truth} - set(identity))
    assert missing == []


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


def test_flat_model_reproduces_every_ungeared_unit(
    tables, ground_truth, ground_truth_ranks, identity
):
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
            corporation=u["corporation"],
            **identity[u["name_en"]],
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
    assert exact >= 22, f"only {exact} ungeared units reproduce exactly"
    assert deviating == [], deviating


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


def test_equipment_of_the_units_own_corporation_is_worth_30_percent_more(tables):
    # Observed in game: the T9 Attacker torso (tid 3210901) reads 588 ATK in the
    # table but 764 on an ELYSION unit wearing the ELYSION-made piece, and
    # 588 * 1.3 = 764.4. Generic gear (type 0) and another corporation's gear
    # get nothing.
    torso_t9 = 3210901
    assert equipment_atk(tables, torso_t9, 0) == 588
    assert (
        equipment_atk(tables, torso_t9, 0, equip_corporation_type=1, unit_corporation="ELYSION")
        == 764
    )
    assert (
        equipment_atk(tables, torso_t9, 0, equip_corporation_type=0, unit_corporation="ELYSION")
        == 588
    )
    assert (
        equipment_atk(tables, torso_t9, 0, equip_corporation_type=2, unit_corporation="ELYSION")
        == 588
    )


def test_gear_only_units_reproduce_exactly(
    tables, ground_truth, ground_truth_ranks, identity
):
    """End-to-end over every unit with gear but no cube or collectible."""
    exact, off = 0, []
    for u in ground_truth:
        if u["harmony_cube_lv"] or u["favorite_item_lv"]:
            continue
        flat = (
            affinity_atk(tables, u["class"], u["attractive_lv"])
            + corporation_atk(tables, u["corporation"], ground_truth_ranks)
            + sum(
                equipment_atk(
                    tables,
                    x["tid"],
                    x["lv"],
                    equip_corporation_type=x["corporation_type"],
                    unit_corporation=u["corporation"],
                )
                for x in u["equip"]
            )
        )
        predicted = assemble_atk(
            tables, character_class=u["class"], level=400,
            grade=u["grade"], core=u["core"], corporation=u["corporation"],
            **identity[u["name_en"]], extra_flat=flat,
        )
        delta = u["measured"]["raid400_atk"] - predicted
        exact += abs(delta) < 1.0
        if abs(delta) >= 1.0:
            off.append((u["name_en"], round(delta, 1)))
    assert exact >= 74, f"regression: only {exact} exact (was 74)"
    assert off == [], off


# --- cube and collectible -----------------------------------------------------


def test_cube_atk_reads_the_level_curve(tables):
    assert cube_atk(tables, 0) == 0
    assert cube_atk(tables, 6) == 790
    assert cube_atk(tables, 15) == 2780


def test_collectible_atk_is_indexed_by_level(tables):
    ordinary = 100202
    assert collectible_atk(tables, ordinary, 1) == 3370
    assert collectible_atk(tables, ordinary, 5) == 4821
    assert collectible_atk(tables, ordinary, 15) == 9688


def test_an_unequipped_collectible_contributes_nothing(tables):
    assert collectible_atk(tables, 0, 0) == 0
    # A tid with level 0 is an empty slot: the curve has an entry at index 0
    # (3,029) but such units measure no contribution.
    assert collectible_atk(tables, 100202, 0) == 0


def test_a_favorite_item_is_priced_at_the_curve_maximum(tables):
    # Exia, Laplace, Miranda and Zwei each hold a favorite item at level 2 and
    # each contributes 9,688 - the top of the curve, not its level-2 entry.
    favorite = 200201
    assert collectible_atk(tables, favorite, 2) == 9688
    assert owns_favorite_item(favorite)
    assert not owns_favorite_item(100202)


def test_full_model_reproduces_the_whole_roster(
    tables, ground_truth, ground_truth_ranks, identity
):
    """Every term together, over all 159 collected units."""
    exact, off = 0, []
    for u in ground_truth:
        flat = (
            affinity_atk(tables, u["class"], u["attractive_lv"])
            + corporation_atk(tables, u["corporation"], ground_truth_ranks)
            + sum(
                equipment_atk(
                    tables, x["tid"], x["lv"],
                    equip_corporation_type=x["corporation_type"],
                    unit_corporation=u["corporation"],
                )
                for x in u["equip"]
            )
            + cube_atk(tables, u["harmony_cube_lv"])
            + collectible_atk(tables, u["favorite_item_tid"], u["favorite_item_lv"])
        )
        predicted = assemble_atk(
            tables, character_class=u["class"], level=400,
            grade=u["grade"], core=u["core"], corporation=u["corporation"],
            **identity[u["name_en"]], extra_flat=flat,
        )
        delta = u["measured"]["raid400_atk"] - predicted
        exact += abs(delta) < 1.0
        if abs(delta) >= 1.0:
            off.append((u["name_en"], round(delta, 1)))
    assert off == [], off
    assert exact == 159, f"regression: only {exact}/159 exact"
