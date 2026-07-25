"""The Korean display-name table (`app/display_names.py`) and how
`supported_units()` prefers it.

The table is hand-authored and deliberately allowed to be INCOMPLETE - an
unfilled slug falls back to the source data's English name, so filling it is
incremental and never a regression. These tests therefore check the table's
internal consistency and the lookup's precedence, never its coverage.
"""
import app.supported_units as su
from app.display_names import DISPLAY_NAMES
from app.supported_units import supported_units


def test_every_table_key_is_a_slug_the_catalog_lists():
    """A typo'd key is silently dead weight - it would never match a slug, so
    the name it carries would never show and nobody would notice."""
    listed = {u["slug"] for u in supported_units()}
    strangers = sorted(set(DISPLAY_NAMES) - listed)
    assert not strangers, f"display names for slugs the catalog does not list: {strangers}"


def test_filled_names_are_unique():
    """The whole point of the table is to end the 17 colliding names. Two
    slugs sharing a filled name means a mode variant went in undistinguished -
    e.g. both Bready candidates typed as plain '브레디'."""
    seen = {}
    collisions = {}
    for slug, name in DISPLAY_NAMES.items():
        if not name:
            continue
        if name in seen:
            collisions.setdefault(name, [seen[name]]).append(slug)
        seen[name] = slug
    assert not collisions, f"one name on several slugs: {collisions}"


def test_the_catalog_prefers_the_table_over_the_source_name(monkeypatch):
    monkeypatch.setattr(su, "DISPLAY_NAMES", {"crown": "크라운"})
    units = {u["slug"]: u for u in supported_units()}
    assert units["crown"]["name"] == "크라운"


def test_an_unfilled_entry_falls_back_to_the_source_name(monkeypatch):
    """An empty string is "not translated yet", not a name - filling the table
    one unit at a time must never blank a label."""
    monkeypatch.setattr(su, "DISPLAY_NAMES", {"crown": ""})
    units = {u["slug"]: u for u in supported_units()}
    assert units["crown"]["name"] == "Crown"


def test_a_mode_variant_takes_its_own_name_not_the_bases(monkeypatch):
    """The merged owned entry copies its first candidate's metadata, so a
    naive implementation would hand the base's name to the candidate too (or
    vice versa) and re-create the collision the table exists to remove."""
    monkeypatch.setattr(su, "DISPLAY_NAMES", {
        "bready": "브레디",
        "bready-lingering": "브레디 (잔류)",
        "bready-recommended": "브레디 (권장)",
    })
    units = {u["slug"]: u for u in supported_units()}
    assert units["bready"]["name"] == "브레디"
    assert units["bready-lingering"]["name"] == "브레디 (잔류)"
    assert units["bready-recommended"]["name"] == "브레디 (권장)"
