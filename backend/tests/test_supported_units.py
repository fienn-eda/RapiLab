from fastapi.testclient import TestClient
from app.api import app
from app.skill_rules.registry import ENCODED_SLUGS
from app.supported_units import supported_units


def test_every_encoded_slug_reaches_the_recommender():
    """An encoded unit the recommender cannot see is encoding work thrown away,
    and `supported_units` drops one SILENTLY (a bare `continue` on any load
    error) - it has now done so twice, for four units each time. The test below
    lists the first four by name; this one needs no list, so the next manifest
    key that only one of the two loaders learns about fails here instead of
    going unnoticed until someone counts."""
    missing = sorted(set(ENCODED_SLUGS) - {u["slug"] for u in supported_units()})
    assert not missing, f"encoded but invisible to the recommender: {missing}"


def test_supported_units_have_required_fields():
    units = supported_units()
    assert units, "expected a non-empty supported-unit list"
    for u in units:
        assert set(u) == {"slug", "name", "burst_tier", "element"}
        assert u["burst_tier"] in (1, 2, 3)
    slugs = {u["slug"] for u in units}
    assert "crown" in slugs   # a known encoded B1


def test_supported_units_includes_manifest_data_slug_and_dotgg_only_units():
    # Regression: these 4 were silently dropped when data-slug resolution
    # only consulted MODE_VARIANTS. julia-signature/drake-signature/
    # laplace-signature carry a data_slug override in their OWN skill-value
    # manifest (not MODE_VARIANTS); privaty has no lootandwaifus file at all
    # and must fall back to its dotgg weapon-data source for meta, exactly
    # as user_roster.load_nikke_spec does.
    slugs = {u["slug"] for u in supported_units()}
    assert {"privaty", "julia-signature", "drake-signature", "laplace-signature"} <= slugs


def test_supported_units_endpoint():
    client = TestClient(app)
    resp = client.get("/api/supported-units")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list) and body
    assert {"slug", "name", "burst_tier", "element"} <= set(body[0])
