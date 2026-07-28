"""Drift guard for the identity table (registry.character_map()).

Identity is derived from each manifest's `data_slug`, a field whose stated job
is naming the data source. That field already names the character every build
is collected from, which is why the derivation works - but it means a
data-sourcing change could redraw identity silently. These tests pin the
grouping so it cannot.
"""
from collections import defaultdict

from app.skill_rules.registry import (ENCODED_SLUGS, MODE_VARIANTS,
                                      character_map, get_skill_value_manifest)


def _groups():
    """character -> [slugs], grouped the way character_map() is derived."""
    by_character = defaultdict(list)
    for slug in ENCODED_SLUGS:
        manifest = get_skill_value_manifest(slug) or {}
        by_character[manifest.get("data_slug", slug)].append(slug)
    return {c: slugs for c, slugs in by_character.items() if len(slugs) > 1}


def test_the_table_holds_exactly_the_multi_build_characters():
    groups = _groups()
    expected = {slug: character
                for character, slugs in groups.items() for slug in slugs}
    assert character_map() == expected
    # A solo character is deliberately absent: `.get(slug, slug)` already names
    # her, and keeping the table small keeps the seat-exclusion check cheap.
    assert "crown" not in character_map()


def test_every_mode_variant_candidate_maps_to_its_base():
    # The fan-out table's own groups are a subset of identity: the candidates a
    # base fans out to are builds of that base's character.
    encoded = set(ENCODED_SLUGS)
    for base, variants in MODE_VARIANTS.items():
        for variant in variants:
            if variant in encoded:
                assert character_map()[variant] == base


def test_every_favorite_item_build_maps_to_its_base_character():
    encoded = set(ENCODED_SLUGS)
    pairs = {s: f"{s}-signature" for s in encoded if f"{s}-signature" in encoded}
    assert len(pairs) == 13, (
        "expected 13 encoded base/-signature pairs; a new Favorite Item build "
        f"landed or one was removed - got {sorted(pairs)}"
    )
    for base, signature in pairs.items():
        assert character_map()[signature] == base
        assert character_map()[base] == base


def test_the_grouping_is_the_expected_seventeen_characters():
    # The whole table, pinned. A change here is either a new multi-build unit
    # (update this list) or a data_slug that drifted away from naming the
    # character (fix the manifest).
    assert sorted(_groups()) == [
        "bready", "cinderella-crystal-wave", "diesel-winter-sweets", "drake",
        "flora", "helm", "julia", "laplace", "miranda", "moran", "phantom",
        "privaty", "rapi-red-hood", "rosanna", "sugar", "tove", "zwei",
    ]
