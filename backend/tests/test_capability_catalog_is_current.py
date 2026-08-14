"""The engine capability catalog must list every resource fill kind and reset
trigger the engine actually implements.

The catalog (`.claude/skills/nikke-skill-encoding/references/
engine-capabilities.md`) is what an encoding session consults to answer "can the
engine express this?" - a module's own deferral note is only a claim about the
engine on the day it was written. That division of labour only works while the
catalog is complete.

It was not. Until 2026-08-14 the catalog described 7 of 13 fill kinds and never
mentioned that a resource can have several fill sources at once, and a five-slug
"Pattern B (time-decaying gauge / multi-source stacks)" gap stayed open for
capabilities that were, four slugs out of five, already built. This test is the
part of that fix that survives.

Adding a fill kind or reset trigger therefore means documenting it. The check is
by NAME, so it catches a new branch nobody wrote up; it cannot judge whether the
prose is any good.
"""
import re
from pathlib import Path

import pytest

from app import raid_simulator

CATALOG = (Path(__file__).resolve().parents[2] / ".claude" / "skills"
           / "nikke-skill-encoding" / "references" / "engine-capabilities.md")

# Dispatched before `_resource_fill_times` is reached, so it carries no
# `kind ==` branch for the scan below to find.
SEPARATELY_RESOLVED_FILL_KINDS = {"squad_burst_cycle_conditional"}


def _source():
    return Path(raid_simulator.__file__).read_text(encoding="utf-8")


def _catalog():
    if not CATALOG.exists():  # pragma: no cover - only in a partial checkout
        pytest.skip(f"capability catalog not present at {CATALOG}")
    return CATALOG.read_text(encoding="utf-8")


def _documents(catalog, name):
    """Whether the catalog names this kind AS A KIND.

    Matching the bare word is not enough: the first new fill kind added after
    this test landed was `computed`, an ordinary English word that already
    appeared in the prose, so a substring check passed while the kind itself was
    undocumented. Every kind in the catalog is written in its literal spec form
    - `("per_shot_every", N)` - so the double quotes are what distinguish a
    documented kind from an accidental word match."""
    return f'"{name}"' in catalog


def test_every_resource_fill_kind_is_in_the_catalog():
    kinds = set(re.findall(r'kind == "([a-z_]+)"', _source()))
    kinds |= SEPARATELY_RESOLVED_FILL_KINDS
    # Guard the scan itself: a refactor that renames the dispatch variable would
    # otherwise leave this test passing over an empty set.
    assert len(kinds) >= 13, f"fill-kind scan found only {sorted(kinds)}"

    catalog = _catalog()
    undocumented = sorted(k for k in kinds if not _documents(catalog, k))
    assert not undocumented, (
        "these ResourceSpec fill kinds exist in raid_simulator but are absent "
        f"from the capability catalog: {undocumented}. Add them to "
        f"{CATALOG.name} - an encoding session reads that file to decide "
        "whether a mechanic is representable, and a kind missing from it reads "
        "as a capability the engine does not have."
    )


def test_every_resource_reset_trigger_is_in_the_catalog():
    triggers = set(re.findall(r'reset_spec\["trigger"\] == "([a-z_]+)"', _source()))
    assert len(triggers) >= 4, f"reset-trigger scan found only {sorted(triggers)}"

    catalog = _catalog()
    undocumented = sorted(t for t in triggers if not _documents(catalog, t))
    assert not undocumented, (
        "these ResourceSpec reset triggers exist in raid_simulator but are "
        f"absent from the capability catalog: {undocumented}."
    )


def test_catalog_records_that_fills_can_have_several_sources():
    """The one capability whose absence from the catalog is known to have cost
    real time: `fill` also takes a list of (spec, amount) pairs."""
    catalog = _catalog()
    assert "_fill_sources" in catalog
    assert "MORE THAN ONE fill source" in catalog
