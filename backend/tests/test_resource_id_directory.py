"""Proves each mapped resource_id really names the unit its slug claims.

test_resource_id_slug_map.py checks that mapped slugs are *encoded*, which cannot
catch a wrong-but-valid id: swapping Soline's base (71) for her Frost Ticket
variant (74) leaves every slug encoded and silently feeds one unit's stats to the
other. This guard closes that hole by checking the map against a committed
snapshot of the public nikke directory (refresh with
`node collect.js --directory` in tools/collect-blablalink).
"""
import json
import re
from pathlib import Path

from tests.test_resource_id_slug_map import MAP_FILE, _map_text

SNAPSHOT = (
    Path(__file__).resolve().parents[2]
    / "tools" / "collect-blablalink" / "nikke-directory.json"
)

# Collab units whose ShiftyPad name is the character's short form while our slug
# spells out the full name. Each is pinned to the exact name it may differ from,
# so the exemption cannot drift into hiding a genuine mis-mapping.
SLUG_NAME_EXCEPTIONS = {
    831: "Rei",
    834: "Rei (Tentative Name)",
    835: "Asuka: WILLE",
    840: "Ada",
    860: "Chisato",
    861: "Takina",
}


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _mapped_entries() -> dict[int, str]:
    body = _map_text().split("Record<number, string> = {", 1)[1].split("\n}", 1)[0]
    return {int(i): slug for i, slug in re.findall(r"(\d+):\s*'([a-z0-9-]+)'", body)}


def _directory() -> dict[int, str]:
    assert SNAPSHOT.exists(), (
        f"{SNAPSHOT} is missing; refresh it with `node collect.js --directory` in "
        "tools/collect-blablalink (needs Chrome on --remote-debugging-port=9222)."
    )
    entries = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return {e["resource_id"]: e["name_en"] for e in entries}


def test_every_mapped_resource_id_exists_in_the_directory():
    unknown = set(_mapped_entries()) - set(_directory())
    assert unknown == set(), (
        f"resource_ids in {MAP_FILE.name} that no nikke has: {sorted(unknown)}. "
        "Either the id is wrong or the snapshot predates the unit's release."
    )


def test_each_mapped_slug_names_its_directory_unit():
    directory = _directory()
    mismatched = {}
    for resource_id, slug in _mapped_entries().items():
        name = directory.get(resource_id)
        if name is None:
            continue  # reported by the existence test above
        expected = SLUG_NAME_EXCEPTIONS.get(resource_id)
        if expected is not None:
            if name != expected:
                mismatched[resource_id] = (slug, name, f"exempted as {expected!r}")
            continue
        if _normalise(slug) != _normalise(name):
            mismatched[resource_id] = (slug, name, "slug != directory name")
    assert mismatched == {}, (
        "mapped slugs that do not name their resource_id's unit "
        f"(id: slug, directory name, why): {mismatched}"
    )


def test_exceptions_are_all_still_mapped():
    stale = set(SLUG_NAME_EXCEPTIONS) - set(_mapped_entries())
    assert stale == set(), (
        f"SLUG_NAME_EXCEPTIONS entries for unmapped resource_ids: {sorted(stale)}; "
        "drop them so the exemption list cannot silently outlive its map entries."
    )
