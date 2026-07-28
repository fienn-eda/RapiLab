"""POST /api/recommend-raid with an optional `draft`: resolves drafted slugs
to specs, calls recommend_from_draft, and returns three-tier results
(top-level `recommended` fields unchanged + additive `within_draft` /
`baseline_total_damage`). See docs/superpowers/specs (Task 5) and
app.deck_allocation.recommend_from_draft."""
from fastapi.testclient import TestClient

from app.api import app
from tests.test_api_recommend import BOSS, FEASIBLE, _nikke

client = TestClient(app)


def test_draft_omitted_is_backward_compatible():
    roster = [_nikke(slug) for slug in FEASIBLE]
    body = {"roster": roster, "boss": BOSS, "num_decks": 1}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["within_draft"] is None
    assert data["baseline_total_damage"] is None
    assert "decks" in data and "combined_total_damage" in data


def test_locked_draft_unit_appears_pinned():
    roster = [_nikke(slug) for slug in FEASIBLE]
    lock_slug = FEASIBLE[0]
    body = {"roster": roster, "boss": BOSS, "num_decks": 1,
            "draft": [{"units": [{"slug": lock_slug, "locked": True}]}]}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 200
    decks = resp.json()["decks"]
    assert any(lock_slug in d["pinned_slugs"] for d in decks)


def test_draft_referencing_unusable_slug_is_422():
    roster = [_nikke(slug) for slug in FEASIBLE]
    body = {"roster": roster, "boss": BOSS, "num_decks": 1,
            "draft": [{"units": [{"slug": "totally-unknown", "locked": True}]}]}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 422


def test_draft_placing_same_slug_in_two_decks_is_422():
    roster = [_nikke(slug) for slug in FEASIBLE]
    dup_slug = FEASIBLE[0]
    body = {"roster": roster, "boss": BOSS, "num_decks": 2,
            "draft": [{"units": [{"slug": dup_slug}]},
                      {"units": [{"slug": dup_slug}]}]}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 422
    assert dup_slug in resp.json()["detail"]


def test_draft_longer_than_num_decks_is_422():
    roster = [_nikke(slug) for slug in FEASIBLE]
    body = {"roster": roster, "boss": BOSS, "num_decks": 1,
            "draft": [{"units": [{"slug": FEASIBLE[0]}]},
                      {"units": [{"slug": FEASIBLE[1]}]}]}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 422


def test_variant_alternatives_omits_favorite_item_pairs():
    # A drafted seat naming `miranda` is a concrete spec, not an ambiguous one:
    # there is no mode for the engine to settle. Only a base the roster loader
    # fans out (a MODE_VARIANTS base) travels with alternatives.
    from app.api import _variant_alternatives
    from app.user_roster import load_roster
    from tests.test_user_roster import _state

    specs, _ = load_roster([_state("miranda"), _state("miranda-signature"),
                            _state("bready")])
    _by_slug, alternatives = _variant_alternatives(specs)
    assert "miranda" not in alternatives
    assert set(alternatives) == {"bready"}
