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


def test_supported_units_endpoint():
    client = TestClient(app)
    resp = client.get("/api/supported-units")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list) and body
    assert {"slug", "name", "burst_tier", "element"} <= set(body[0])
