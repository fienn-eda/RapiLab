"""The engine capability catalog must name every fill kind, reset trigger, and
burst-gauge fill trigger the engine actually implements.

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

Adding one therefore means documenting it. **What is scanned**, three things:

- `ResourceSpec` fill kinds - `kind == "..."` in `raid_simulator.py`.
- `ResourceSpec` reset triggers - `reset_spec["trigger"] == "..."` there too.
- `burst_gauge.fill_times`'s `bonus_fills` trigger kinds - the keys its
  dispatcher splits on. **Added 2026-08-22, after a real escape:**
  `every_own_full_charge` was built, wired and shipped with the catalog
  untouched and this file stayed green, because the scan read one file
  (`raid_simulator.py`) and that trigger lives in `burst_gauge.py`.

**What is still NOT caught** - the rule remains partly yours (CLAUDE.md says so):

- Stats, triggers and spec-dict keys are not scanned at all.
- Whether the prose is any good, or even in the right section. The check is by
  NAME: `_documents` only asks whether the quoted name appears ANYWHERE in the
  catalog. A one-word mention passes. Worse, the mention need not be prose the
  scan put there - the `every_own_full_charge` write-up quotes the name in its
  literal spec form, so widening the scan would NOT retroactively have caught
  that escape once the catalog was fixed by hand. This guard raises the floor;
  it does not replace reading the catalog when you build a capability.
"""
import re
from pathlib import Path

import pytest

from app import burst_gauge, raid_simulator

CATALOG = (Path(__file__).resolve().parents[2] / ".claude" / "skills"
           / "nikke-skill-encoding" / "references" / "engine-capabilities.md")

# Dispatched before `_resource_fill_times` is reached, so it carries no
# `kind ==` branch for the scan below to find.
SEPARATELY_RESOLVED_FILL_KINDS = {"squad_burst_cycle_conditional"}


def _source():
    return Path(raid_simulator.__file__).read_text(encoding="utf-8")


def _burst_gauge_source():
    return Path(burst_gauge.__file__).read_text(encoding="utf-8")


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


def test_every_burst_gauge_fill_trigger_is_in_the_catalog():
    """The squad burst gauge has its own fill triggers, in its own module.

    `burst_gauge.fill_times`'s `bonus_fills` takes a list of specs where the KEY
    an element carries names its trigger kind, and `fill_times` splits the list
    on those keys. They are a capability an encoding session has to be able to
    look up, exactly like a `ResourceSpec` fill kind - and until 2026-08-22 they
    were outside every scan here, which is how `every_own_full_charge` shipped
    with the catalog untouched and this file green.
    """
    triggers = set(re.findall(r'for f in bonus_fills if "([a-z_]+)" in f',
                              _burst_gauge_source()))
    # Guard the scan itself: this reads one comprehension shape, so a refactor
    # that dispatches differently must come here rather than silently scanning
    # nothing - the same trap the fill-kind scan defends against.
    assert len(triggers) >= 2, f"bonus-fill trigger scan found only {sorted(triggers)}"

    catalog = _catalog()
    undocumented = sorted(t for t in triggers if not _documents(catalog, t))
    assert not undocumented, (
        "these burst_gauge bonus_fill triggers exist in the engine but are "
        f"absent from the capability catalog: {undocumented}. Add them to "
        f"{CATALOG.name} - a trigger missing from it reads as a capability the "
        "engine does not have, and the next session records it as a gap."
    )


def test_catalog_records_that_fills_can_have_several_sources():
    """The one capability whose absence from the catalog is known to have cost
    real time: `fill` also takes a list of (spec, amount) pairs."""
    catalog = _catalog()
    assert "_fill_sources" in catalog
    assert "MORE THAN ONE fill source" in catalog
