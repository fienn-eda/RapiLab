from fastapi.testclient import TestClient
from app.api import app
from app.supported_units import supported_units


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
