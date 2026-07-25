from fastapi.testclient import TestClient
from app.api import app
from app.skill_rules.registry import ENCODED_SLUGS, MODE_VARIANTS
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


def test_every_owned_slug_reaches_the_recommender():
    """The test above covers the ENGINE's vocabulary; this one covers the
    ROSTER's. A synced roster names the character the player owns, and for a
    MODE_VARIANTS character that is the base slug (`bready`), never the
    candidates the loader fans her out into. Listing only candidates made the
    frontend - which intersects the roster with this list - call three owned
    characters unsupported while the recommender was fielding them."""
    listed = {u["slug"] for u in supported_units()}
    missing = sorted(set(MODE_VARIANTS) - listed)
    assert not missing, f"ownable but invisible to the recommender: {missing}"


def test_a_mode_variant_character_is_listed_once_with_her_candidates():
    units = {u["slug"]: u for u in supported_units()}
    bready = units["bready"]
    assert bready["candidates"] == ["bready-lingering", "bready-recommended"]
    assert bready["name"] == "Bready"
    # Her candidates stay listed too: a result deck names THOSE, so the client
    # still has to be able to look one up for a portrait and a burst tier.
    assert {"bready-lingering", "bready-recommended"} <= set(units)


def test_a_base_slug_that_is_itself_a_candidate_carries_no_candidate_list():
    """rapi-red-hood is both the owned slug and an engine candidate, so she
    needs no merged entry - and must not get one, since a draft CAN seat her."""
    units = {u["slug"]: u for u in supported_units()}
    assert "candidates" not in units["rapi-red-hood"]
    assert units["rapi-red-hood"]["burst_tier"] == 3
    assert units["rapi-red-hood-b1"]["burst_tier"] == 1


def test_a_merged_entry_describes_candidates_that_actually_agree():
    """A merged entry takes its name/element/burst tier from the FIRST loadable
    candidate. That is only honest while a character's candidates agree, and
    burst tier is the one they could plausibly differ on (VARIANT_BURST_TIERS,
    as rapi-red-hood does). If a future MODE_VARIANTS base spans tiers AND is
    not a candidate itself, it cannot be drawn as one palette chip - fail here
    so that gets decided rather than silently mis-grouped."""
    units = {u["slug"]: u for u in supported_units()}
    for base, variants in MODE_VARIANTS.items():
        if base in variants:
            continue                      # listed on its own terms
        described = [units[v] for v in variants if v in units]
        for field in ("name", "element", "burst_tier"):
            values = {u[field] for u in described}
            assert len(values) == 1, f"{base} candidates disagree on {field}: {values}"


def test_supported_units_have_required_fields():
    units = supported_units()
    assert units, "expected a non-empty supported-unit list"
    for u in units:
        assert {"slug", "name", "burst_tier", "element"} <= set(u)
        assert set(u) <= {"slug", "name", "burst_tier", "element", "candidates"}
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
    by_slug = {u["slug"]: u for u in body}
    # `candidates` survives serialization where it matters, and is null (not
    # absent) elsewhere - the TS mirror treats both as "one candidate".
    assert by_slug["bready"]["candidates"] == ["bready-lingering",
                                              "bready-recommended"]
    assert by_slug["crown"]["candidates"] is None
