"""POST /api/charge-window - the FB shot-count calculator's surface."""
import pytest
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)

MAXED = {"skill1": 10, "skill2": 10, "burst": 10}


def a_unit(slug, overloads=()):
    return {
        "character_slug": slug, "level": 200, "hp": 1_000_000, "atk": 100_000,
        "def_": 10_000, "skill_levels": MAXED,
        "overload_options": [{"name": n, "value": v} for n, v in overloads],
    }


def post(slug, roster, with_liberalio=False, overrides=None):
    return client.post("/api/charge-window", json={
        "slug": slug, "roster": roster, "with_liberalio": with_liberalio,
        "overrides": overrides or {},
    })


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


def test_a_roomy_magazine_produces_no_reload_note():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)]),
              a_unit("liberalio")]
    body = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert not any("재장전" in note for note in body["notes"])


def test_liberalio_taking_her_own_buff_is_reported():
    # The grant goes to the lowest-ATK Burst 3 ally and does NOT exclude her, so
    # a Scarlet with more ATK means Liberalio keeps it.
    scarlet = a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])
    liberalio = a_unit("liberalio")
    liberalio["atk"] = 50_000  # lower than Scarlet's 100,000
    body = post("scarlet-black-shadow", [scarlet, liberalio], with_liberalio=True).json()
    assert any("리버렐리오" in note for note in body["notes"])


def test_asking_for_an_absent_liberalio_says_so_and_drops_the_buff():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    with_her = post("scarlet-black-shadow",
                    roster + [a_unit("liberalio")], with_liberalio=True).json()
    without_her = post("scarlet-black-shadow", roster, with_liberalio=True).json()
    assert without_her["interval"] > with_her["interval"]
    assert any("로스터에 없어" in note for note in without_her["notes"])


def test_lines_the_two_aggregation_rules_split_on_are_reported():
    # 5.51% raw buys no frame of an 18-frame charge; rounded to 6% it buys one.
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    body = post("scarlet-black-shadow", roster,
                overrides={"charge_speed_lines": [5.51]}).json()
    assert any("집계 규칙" in note for note in body["notes"])


def test_lines_the_two_rules_agree_on_get_no_note():
    roster = [a_unit("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])]
    body = post("scarlet-black-shadow", roster,
                overrides={"charge_speed_lines": [4.33, 4.33]}).json()
    assert not any("집계 규칙" in note for note in body["notes"])


def test_the_synced_roster_gets_no_aggregation_note():
    # blablalink reports overload options already summed across gear, so the
    # per-slot decomposition the comparison needs simply is not there.
    roster = [a_unit("scarlet-black-shadow",
                     [("최대 장탄 수 증가", 85.37), ("차지 속도 증가", 5.51)])]
    body = post("scarlet-black-shadow", roster).json()
    assert not any("집계 규칙" in note for note in body["notes"])


def test_an_unsupported_slug_is_a_422():
    assert post("liter", [a_unit("liter")]).status_code == 422


def test_a_slug_missing_from_the_roster_is_a_422():
    assert post("neon-vision-eye", [a_unit("liberalio")]).status_code == 422
