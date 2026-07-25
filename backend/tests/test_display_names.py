"""The Korean display-name table (`app/display_names.py`) and how
`supported_units()` prefers it.

The table is hand-authored and deliberately allowed to be INCOMPLETE - an
unfilled slug falls back to the source data's English name, so filling it is
incremental and never a regression. These tests therefore check the table's
internal consistency and the lookup's precedence, never its coverage.
"""
import app.supported_units as su
from app.display_names import DISPLAY_NAMES
from app.skill_rules.registry import MODE_VARIANTS
from app.supported_units import supported_units


def test_every_table_key_is_a_slug_the_catalog_lists():
    """A typo'd key is silently dead weight - it would never match a slug, so
    the name it carries would never show and nobody would notice."""
    listed = {u["slug"] for u in supported_units()}
    strangers = sorted(set(DISPLAY_NAMES) - listed)
    assert not strangers, f"display names for slugs the catalog does not list: {strangers}"


def test_a_characters_mode_candidates_are_named_apart():
    """A character the engine fans into several candidates has them ALL in the
    roster at once - measured: every MODE_VARIANTS base does - so two of them
    can land on the bench together. That is the "Bready, Bready" this table
    exists to end, and only distinct names end it."""
    for base, variants in MODE_VARIANTS.items():
        named = [(v, DISPLAY_NAMES.get(v)) for v in variants if DISPLAY_NAMES.get(v)]
        names = [n for _, n in named]
        assert len(names) == len(set(names)), \
            f"{base}'s candidates share a name: {named}"


def _owned_character(slug):
    """The one owned character a slug stands for - the mirror of the roster's
    own resolution. A MODE_VARIANTS candidate stands for its base, and a
    Favorite Item build stands for the unit that equips it."""
    for base, variants in MODE_VARIANTS.items():
        if slug in variants:
            return base
    return slug.removesuffix("-signature")


def test_two_different_characters_never_share_a_name():
    """Uniqueness is scoped to the character, NOT global. A base and its
    "-signature" build never appear together (the roster resolves to one or the
    other - measured: no roster holds both), so naming both '헬름' is right:
    the heart, not the name, says which build is in play. Two DIFFERENT
    characters sharing a name is still a typo worth catching."""
    by_name = {}
    for slug, name in DISPLAY_NAMES.items():
        if name:
            by_name.setdefault(name, []).append(slug)
    crossed = {
        name: slugs for name, slugs in by_name.items()
        if len({_owned_character(s) for s in slugs}) > 1
    }
    assert not crossed, f"one name across different characters: {crossed}"


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
