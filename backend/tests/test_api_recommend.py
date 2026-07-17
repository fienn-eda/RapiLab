from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def _nikke(slug, burst_tier_hint_atk=60_000.0):
    return {
        "character_slug": slug,
        "level": 200,
        "core_level": 0,
        "hp": 1_000_000.0,
        "atk": burst_tier_hint_atk,
        "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }


BOSS = {"element": "Water", "core_hittable": False, "enemy_def": 0,
        "fight_duration": 180, "part_destructible": False}

# Five loadable slugs covering burst tiers 1/2/3 (after Task 6's first
# backfill batch): tier 1: little-mermaid, tier 2: arcana/grave, tier 3:
# drake/modernia.
FEASIBLE = ["little-mermaid", "arcana", "grave", "drake", "modernia"]


def test_feasible_roster_returns_ranked_decks_and_exclusions():
    roster = [_nikke(slug) for slug in FEASIBLE] + [_nikke("totally-unknown")]
    response = client.post("/api/recommend", json={"roster": roster, "boss": BOSS, "top_n": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["excluded_slugs"] == ["totally-unknown"]
    assert 1 <= len(body["decks"]) <= 3
    totals = [d["total_damage"] for d in body["decks"]]
    assert totals == sorted(totals, reverse=True)
    first = body["decks"][0]
    assert set(first) == {"deck", "total_damage", "burst_damage", "normal_attack_damage"}
    assert len(first["deck"]) == 5


def test_infeasible_after_exclusion_is_422_naming_exclusions():
    response = client.post(
        "/api/recommend",
        json={"roster": [_nikke("totally-unknown")] * 5, "boss": BOSS},
    )
    assert response.status_code == 422
    assert "totally-unknown" in str(response.json()["detail"])


def test_malformed_body_is_422():
    response = client.post("/api/recommend", json={"roster": "nope", "boss": BOSS})
    assert response.status_code == 422


def test_unknown_overload_option_name_is_422_naming_bad_and_valid_names():
    roster = [_nikke(slug) for slug in FEASIBLE]
    roster[0]["overload_options"] = [{"name": "made-up-option", "value": 10.0}]
    response = client.post("/api/recommend", json={"roster": roster, "boss": BOSS})
    assert response.status_code == 422
    detail = str(response.json()["detail"])
    assert "made-up-option" in detail
    # the valid names come from the engine's NAME_TO_STAT, surfaced to the client
    assert "공격력 증가" in detail


def test_recommend_raid_partitions_roster_and_reports_leftovers():
    roster = [_nikke(slug) for slug in FEASIBLE] + [_nikke("totally-unknown")]
    response = client.post("/api/recommend-raid", json={"roster": roster, "boss": BOSS})
    assert response.status_code == 200
    body = response.json()
    assert body["excluded_slugs"] == ["totally-unknown"]
    assert len(body["decks"]) == 1                      # 5 loadable units -> 1 deck
    deck = body["decks"][0]
    assert set(deck) == {"deck", "total_damage", "burst_damage", "normal_attack_damage"}
    assert sorted(deck["deck"]) == sorted(FEASIBLE)
    assert body["leftover_slugs"] == []
    assert body["combined_total_damage"] == deck["total_damage"]


def test_recommend_raid_infeasible_is_422_naming_exclusions():
    response = client.post(
        "/api/recommend-raid",
        json={"roster": [_nikke("totally-unknown")] * 5, "boss": BOSS},
    )
    assert response.status_code == 422
    assert "totally-unknown" in str(response.json()["detail"])
