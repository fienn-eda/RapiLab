"""Collects dotgg weapon-stat files for units that only have lootandwaifus data.

The engine reads per-unit weapon stats (weapon, maxAmmo, damage, reloadTime,
chargeTime, chargeDamage) from data/dotgg/char_*.json; lootandwaifus pages
only carry the weapon TYPE. Units collected from lootandwaifus alone are
therefore excluded from roster loading until their dotgg file exists. dotgg
indexes by the `url` field INSIDE each file (see skill_values._dotgg_path_for),
so coverage is judged on that field, never the filename.

dotgg stopped updating around 2026-05: units released after that are not on
the API at all. For those, pass --stub <slug> to write a manual-entry
template - fill the fields listed in its `_todo` key with values Fienn
confirmed (in-game / namu.wiki), then delete `_todo`. Unfilled stubs are
harmless: the loader's field check keeps the unit excluded.

When to use: after collecting a new unit from lootandwaifus (/collect-nikke),
or whenever roster loading reports units excluded for missing weapon stats.
Re-runnable and idempotent - covered units are skipped.

Usage:
    python3 scripts/collect_dotgg_weapons.py                # fetch every missing unit
    python3 scripts/collect_dotgg_weapons.py --dry-run      # report only, write nothing
    python3 scripts/collect_dotgg_weapons.py --stub prika   # also write manual template(s)
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

LW_DIR = REPO_ROOT / "data" / "lootandwaifus"
DOTGG_DIR = REPO_ROOT / "data" / "dotgg"

CHARGE_WEAPONS = ("RL", "SR")
MANUAL_FIELDS_CHARGE = ["maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage"]
MANUAL_FIELDS_MAGAZINE = ["maxAmmo", "damage", "reloadTime"]


def wanted_dotgg_urls(lw_slugs, manifests):
    """lootandwaifus slug -> the url the roster loader will look up in the
    dotgg url index (a manifest's dotgg_slug alias wins; default is the
    lootandwaifus slug itself, which is also the data_slug default)."""
    alias = {}
    for slug, manifest in manifests.items():
        data_slug = manifest.get("data_slug", slug)
        alias[data_slug] = manifest.get("dotgg_slug", data_slug)
    return {slug: alias.get(slug, slug) for slug in lw_slugs}


def existing_dotgg_urls(dotgg_dir):
    urls = set()
    for path in sorted(Path(dotgg_dir).glob("char_*.json")):
        urls.add(json.loads(path.read_text(encoding="utf-8")).get("url"))
    return urls


def resolve_dotgg_entry(wanted_url, lw_name, characters):
    """Find the dotgg character-list entry for a unit: exact slug match first,
    then exact case-insensitive name match. Never partial-matches - a skin
    unit ("Cinderella: Crystal Wave") must not resolve to its base unit."""
    for entry in characters:
        if entry.get("url") == wanted_url:
            return entry, "slug"
    name = (lw_name or "").lower()
    for entry in characters:
        if entry.get("name", "").lower() == name:
            return entry, "name"
    return None, None


def make_stub(lw_data, wanted_url):
    """Manual-entry template for a unit dotgg doesn't have. Unfilled fields
    are OMITTED (not empty strings) so _weapon_stats keeps excluding the unit
    instead of crashing on int("")."""
    stub = {
        "name": lw_data.get("name"),
        "url": wanted_url,
        "source": "manual",
        "weapon": lw_data.get("weapon"),
    }
    if lw_data.get("weapon") in CHARGE_WEAPONS:
        todo = list(MANUAL_FIELDS_CHARGE)
    else:
        todo = list(MANUAL_FIELDS_MAGAZINE)
        stub["chargeTime"] = 0
        stub["chargeDamage"] = "0%"
    stub["_todo"] = todo
    return stub
