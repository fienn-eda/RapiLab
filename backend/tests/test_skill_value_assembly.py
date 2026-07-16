"""Assembly verification harness: for EVERY encoded unit that declares a
SKILL_VALUE_MANIFESTS entry, assemble max-level skill_values from the local
data files and compare each slot against the values the unit's own test
fixtures assert (the fixtures are ground truth - hand-transcribed during
encoding, and every builder is tested against them). A mismatch is fixed by a
drop_tokens override in that unit's manifest, NEVER by loosening this
comparison. New encodings must declare a manifest and pass this too (see the
nikke-skill-encoding skill workflow)."""
import importlib.util
from pathlib import Path

import pytest

from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest
from app.skill_values import assemble_skill_values

MAX_LEVELS = {"skill1": 10, "skill2": 10, "burst": 10}

MANIFEST_SLUGS = [slug for slug in ENCODED_SLUGS if get_skill_value_manifest(slug)]


def _load_test_module(name):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_at_least_the_pilots_have_manifests():
    assert {"drake", "drake-signature", "rei-ayanami"} <= set(MANIFEST_SLUGS)


@pytest.mark.parametrize("slug", MANIFEST_SLUGS)
def test_assembled_max_level_values_match_fixtures(slug):
    manifest = get_skill_value_manifest(slug)
    values = assemble_skill_values(slug, manifest, MAX_LEVELS)
    fixtures_module = _load_test_module(manifest["test_module"])
    for key in manifest["keys"]:
        fixture_name = manifest.get("fixtures", {}).get(key, key.upper())
        fixture = getattr(fixtures_module, fixture_name)
        parsed = values[key]
        for slot, expected in fixture.items():
            assert slot in parsed, f"{slug}.{key}: parser produced no {slot} (got {sorted(parsed)})"
            assert float(parsed[slot]) == pytest.approx(float(expected)), (
                f"{slug}.{key}.{slot}: parsed {parsed[slot]!r} != fixture {expected!r}"
            )
