"""POST /api/charge-window - the FB shot-count calculator's surface."""
import pytest
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)

MAXED = {"skill1": 10, "skill2": 10, "burst": 10}


def a_unit(slug, overloads=()):
    """An overload entry is (name, value) for a roster that only kept the total,
    or (name, value, [rolls]) for one synced after the rolls were carried."""
    options = []
    for entry in overloads:
        name, value = entry[0], entry[1]
        option = {"name": name, "value": value}
        if len(entry) > 2:
            option["lines"] = [{"slot": "head", "value": roll} for roll in entry[2]]
        options.append(option)
    return {
        "character_slug": slug, "level": 200, "hp": 1_000_000, "atk": 100_000,
        "def_": 10_000, "skill_levels": MAXED, "overload_options": options,
    }


def post(slug, roster, with_liberalio=False, overrides=None, cube=None):
    body = {"slug": slug, "roster": roster, "with_liberalio": with_liberalio,
            "overrides": overrides or {}}
    if cube is not None:
        body["cube"] = cube
    return client.post("/api/charge-window", json=body)


def test_scarlet_with_liberalio_reports_the_measured_cadence():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    response = post("scarlet-black-shadow", roster, with_liberalio=True)
    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == pytest.approx(0.5389, abs=1 / 180)
    assert body["magazine"] == 22
    assert body["current"]["high_shots"] == 19


def test_the_threshold_ladder_comes_back_ordered_and_deduplicated():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    percents = [round(t["charge_speed_percent"] * 100, 2) for t in body["thresholds"]]
    assert percents[:4] == [0.0, 5.56, 11.11, 16.67]
    assert percents == sorted(percents)


def test_a_reload_inside_the_window_is_reported_as_a_note():
    # Base magazine plus Asura only: 14 rounds empty at 7.42 sec.
    roster = [a_unit("scarlet-black-shadow"), a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert any("재장전" in note for note in body["notes"])


def test_a_magazine_that_costs_shots_says_which_axis_is_the_limit():
    """Fienn's synced Scarlet holds 18 rounds and reads 18 shots at every step
    through 22.22%. The ladder is right and looks broken, because nothing on it
    says the magazine - not the charge speed - is what is capping the count."""
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 44.28)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert body["magazine"] == 18
    assert body["current"]["high_shots"] == 18
    assert any("최대장탄" in note for note in body["notes"])


def test_a_tactical_bear_takes_the_magazine_cap_off_the_same_gear():
    """Same 18 rounds, other cube: the rounds it hands back mid-magazine push
    the reload past the window, so the count is the cadence's own 19 again."""
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 44.28)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True,
                cube="tactical_bear").json()
    assert body["magazine"] == 18
    assert body["current"]["high_shots"] == 19
    assert not any("최대장탄" in note for note in body["notes"])
    assert not any("재장전" in note for note in body["notes"])


def test_a_cube_the_project_has_no_table_for_is_refused():
    roster = [a_unit("scarlet-black-shadow"), a_unit("liberalio")]
    assert post("scarlet-black-shadow", roster, cube="bastion").status_code == 422


def test_a_magazine_the_cadence_cannot_empty_gets_no_such_note():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert not any("최대장탄" in note for note in body["notes"])


def test_a_roomy_magazine_produces_no_reload_note():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert not any("재장전" in note for note in body["notes"])


def test_liberalio_taking_her_own_buff_is_reported():
    # The grant goes to the lowest-final-ATK Burst 3 ally and does NOT exclude
    # her, so a Scarlet whose burst lifts her past Liberalio means Liberalio
    # keeps it.
    scarlet = a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])
    liberalio = a_unit("liberalio")
    liberalio["atk"] = 50_000  # 130,000 final against Scarlet's 215,120
    body = post("scarlet-black-shadow", [scarlet, liberalio], with_liberalio=True).json()
    assert any("리버렐리오" in note for note in body["notes"])


def test_the_buff_liberalio_keeps_is_left_out_of_the_ladder_too():
    """The note and the numbers are one judgement: seconds she never hands over
    must not be in the interval the ladder is built from."""
    scarlet = a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])
    liberalio = a_unit("liberalio")
    liberalio["atk"] = 50_000
    kept = post("scarlet-black-shadow", [scarlet, liberalio], with_liberalio=True).json()
    solo = post("scarlet-black-shadow", [scarlet, liberalio]).json()
    assert kept["interval"] == pytest.approx(solo["interval"])


def test_out_basing_liberalio_does_not_mean_she_keeps_the_buff():
    """Fienn's roster shape: Scarlet out-BASES her, yet Calm Depths' +160% on
    herself at Full Burst entry puts her final ATK above Scarlet's, so the cut
    lands on Scarlet - as his own measurement shows. Ranking on the roster's
    base ATK reports the opposite."""
    scarlet = a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])
    liberalio = a_unit("liberalio")
    liberalio["atk"] = 90_000  # 234,000 final against Scarlet's 215,120
    body = post("scarlet-black-shadow", [scarlet, liberalio], with_liberalio=True).json()
    assert not any("그녀 자신에게" in note for note in body["notes"])


def test_asking_for_an_absent_liberalio_says_so_and_drops_the_buff():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    with_her = post("scarlet-black-shadow",
                    roster + [a_unit("liberalio")], with_liberalio=True).json()
    without_her = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert without_her["interval"] > with_her["interval"]
    assert any("로스터에 없어" in note for note in without_her["notes"])


def test_a_roster_that_only_kept_the_total_says_the_answer_is_an_estimate():
    """Charge speed rounds per roll, so a total several roll combinations could
    have produced does not pin the frame count - and the reader is told rather
    than shown an estimate that looks like a reading."""
    roster = [a_unit("scarlet-black-shadow",
                     [("최대 장탄 수 증가", 85.37), ("차지 속도 증가", 7.20)])]
    body = post("scarlet-black-shadow", roster).json()
    assert any("합계에서 추정" in note for note in body["notes"])


def test_a_roster_carrying_the_rolls_gets_no_estimate_note():
    roster = [a_unit("scarlet-black-shadow",
                     [("최대 장탄 수 증가", 85.37),
                      ("차지 속도 증가", 7.20, [2.57, 4.63])])]
    body = post("scarlet-black-shadow", roster).json()
    assert not any("합계에서 추정" in note for note in body["notes"])


def test_typed_rolls_are_rolls_so_they_get_no_estimate_note():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    body = post("scarlet-black-shadow", roster,
                overrides={"charge_speed_lines": [2.57, 4.63]}).json()
    assert not any("합계에서 추정" in note for note in body["notes"])


def test_a_unit_with_no_charge_speed_overload_has_nothing_to_be_unsure_about():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    body = post("scarlet-black-shadow", roster).json()
    assert not any("합계에서 추정" in note for note in body["notes"])


def test_the_rolls_a_total_hides_actually_change_the_answer():
    """2.57 + 4.63 and 2.28 + 4.92 both display 7.20% and grant 8 and 7. This is
    what the estimate note is warning about, so it has to be real."""
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    high = post("scarlet-black-shadow", roster,
                overrides={"charge_speed_lines": [2.57, 4.63]}).json()
    low = post("scarlet-black-shadow", roster,
               overrides={"charge_speed_lines": [2.28, 4.92]}).json()
    assert high["charge_speed_percent"] == pytest.approx(0.08)
    assert low["charge_speed_percent"] == pytest.approx(0.07)


def test_an_unsupported_slug_is_a_422():
    assert post("liter", [a_unit("liter")]).status_code == 422


def test_a_slug_missing_from_the_roster_is_a_422():
    assert post("neon-vision-eye", [a_unit("liberalio")]).status_code == 422
