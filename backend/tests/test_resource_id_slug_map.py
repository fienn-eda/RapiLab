"""Drift guard for the frontend resource_id -> slug map and its signature layer.

Keeps the hand-authored frontend tables honest against the live ENCODED_SLUGS:
every mapped slug must be encoded, DUAL_SLOT_BASES must match the actual encoded
base/-signature pairs (so a newly encoded dual-slot unit cannot ship unhandled),
and every encoded slug must be reachable except a known, documented gap.
"""
import re
from pathlib import Path

from app.skill_rules.registry import ENCODED_SLUGS

MAP_FILE = (
    Path(__file__).resolve().parents[2]
    / "frontend" / "src" / "lib" / "resourceIdSlugMap.ts"
)

# Encoded slugs deliberately unreachable from the identity map:
#   jill-valentine -> not owned in the roster the map was authored from, so its
#     resource_id is unknown locally (never guessed). Add the entry when a Jill owner
#     syncs or a directory snapshot lands, then drop it from this set.
# NOTE: "-signature" slugs are intentionally absent from the identity map (they are
# reached by promotion via SIGNATURE_OWNED), so they are subtracted before comparing.
KNOWN_UNMAPPED = {"jill-valentine"}


def _map_text() -> str:
    return MAP_FILE.read_text(encoding="utf-8")


def _body_after(marker: str, end: str) -> str:
    """Text between `marker` and the next `end`, failing loudly if the marker moved."""
    text = _map_text()
    assert marker in text, (
        f"marker {marker!r} not found in {MAP_FILE}; this test parses that literal "
        "text — update the marker to match the file."
    )
    return text.split(marker, 1)[1].split(end, 1)[0]


def _mapped_slugs() -> set[str]:
    body = _body_after("Record<number, string> = {", "\n}")
    return set(re.findall(r"\d+:\s*'([a-z0-9-]+)'", body))


def _dual_slot_bases() -> set[str]:
    # Split on the full declaration: the bare name also appears in the file's header
    # comment, and splitting there would swallow the whole map.
    body = _body_after("DUAL_SLOT_BASES: ReadonlySet<string> = new Set([", "])")
    return set(re.findall(r"'([a-z0-9-]+)'", body))


def _encoded_dual_slot_bases() -> set[str]:
    encoded = set(ENCODED_SLUGS)
    return {s for s in encoded if f"{s}-signature" in encoded}


def test_every_mapped_slug_is_encoded():
    stray = _mapped_slugs() - set(ENCODED_SLUGS)
    assert stray == set(), f"map slugs not in ENCODED_SLUGS (typo/stale): {stray}"


def test_dual_slot_bases_match_encoded_pairs():
    declared, actual = _dual_slot_bases(), _encoded_dual_slot_bases()
    assert declared == actual, (
        "DUAL_SLOT_BASES is out of sync with encoded base/-signature pairs; "
        f"add/remove entries in resourceIdSlugMap.ts. diff={declared ^ actual}"
    )


def test_every_encoded_slug_is_reachable_except_known():
    signature_slugs = {f"{b}-signature" for b in _encoded_dual_slot_bases()}
    uncovered = set(ENCODED_SLUGS) - _mapped_slugs() - signature_slugs
    assert uncovered == KNOWN_UNMAPPED, (
        "encoded slugs missing a resource_id entry changed; add the entry or update "
        f"KNOWN_UNMAPPED. diff={uncovered ^ KNOWN_UNMAPPED}"
    )
