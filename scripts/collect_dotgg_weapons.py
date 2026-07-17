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
        # Inert for magazine weapons (raid_simulator gates charge_damage_percent
        # behind is_charge_weapon), but "100%" is dotgg's own "no charge
        # multiplier" convention - and unlike "0%" it can't turn into a x0
        # damage factor if the gate ever changes.
        stub["chargeTime"] = 0
        stub["chargeDamage"] = "100%"
    stub["_todo"] = todo
    return stub


def collect(lw_dir, dotgg_dir, manifests, fetch_list, fetch_char,
            stub_slugs=(), dry_run=False):
    """Fetch dotgg weapon-stat files for every lootandwaifus-collected unit
    the roster loader can't currently find, writing them under dotgg's own
    slug (the loader matches on the url field, not the filename). Per-unit
    failures are recorded and don't stop the run."""
    results = {"fetched": [], "alias_needed": [], "not_on_dotgg": [],
               "stubbed": [], "errors": []}
    lw_files = {p.stem.removeprefix("char_"): p
                for p in sorted(Path(lw_dir).glob("char_*.json"))}
    wanted = wanted_dotgg_urls(lw_files, manifests)
    existing = existing_dotgg_urls(dotgg_dir)
    missing = {slug: url for slug, url in wanted.items() if url not in existing}
    if not missing:
        return results
    try:
        characters = fetch_list()
    except Exception as exc:
        results["errors"].append(("<character list>", str(exc)))
        return results
    for lw_slug, wanted_url in sorted(missing.items()):
        lw_data = json.loads(lw_files[lw_slug].read_text(encoding="utf-8"))
        entry, how = resolve_dotgg_entry(wanted_url, lw_data.get("name"), characters)
        if entry is None:
            results["not_on_dotgg"].append(lw_slug)
            if lw_slug in stub_slugs and not dry_run:
                stub_path = Path(dotgg_dir) / f"char_{wanted_url}.json"
                stub_path.write_text(
                    json.dumps(make_stub(lw_data, wanted_url),
                               ensure_ascii=False, indent=1),
                    encoding="utf-8")
                results["stubbed"].append(lw_slug)
            continue
        if entry["url"] != wanted_url:
            # The loader looks up wanted_url; this unit's manifest (current
            # or future) needs a dotgg_slug alias pointing at entry["url"].
            results["alias_needed"].append((lw_slug, entry["url"]))
            if entry["url"] in existing:
                continue
        if not dry_run:
            try:
                data = fetch_char(entry["url"])
            except Exception as exc:
                results["errors"].append((lw_slug, str(exc)))
                continue
            out_path = Path(dotgg_dir) / f"char_{entry['url']}.json"
            out_path.write_text(json.dumps(data, ensure_ascii=False),
                                encoding="utf-8")
        results["fetched"].append((lw_slug, entry["url"], how))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch missing dotgg weapon-stat files for "
                    "lootandwaifus-collected units.")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be fetched/stubbed, write nothing")
    parser.add_argument("--stub", nargs="+", default=(), metavar="SLUG",
                        help="write a manual-entry template for these "
                             "lootandwaifus slugs when dotgg doesn't have them")
    args = parser.parse_args(argv)

    from app.dotgg_client import fetch_character, fetch_character_list
    from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest

    manifests = {}
    for slug in sorted(ENCODED_SLUGS):
        manifest = get_skill_value_manifest(slug)
        if manifest is not None:
            manifests[slug] = manifest

    lw_slugs = {p.stem.removeprefix("char_")
                for p in LW_DIR.glob("char_*.json")}
    unknown = sorted(set(args.stub) - lw_slugs)
    if unknown:
        parser.error(f"--stub slugs without a lootandwaifus file: {unknown}")

    results = collect(LW_DIR, DOTGG_DIR, manifests,
                      fetch_character_list, fetch_character,
                      stub_slugs=tuple(args.stub), dry_run=args.dry_run)

    label = "would fetch" if args.dry_run else "fetched"
    for lw_slug, url, how in results["fetched"]:
        print(f"{label}: {lw_slug} -> char_{url}.json (matched by {how})")
    for lw_slug, url in results["alias_needed"]:
        print(f"ALIAS NEEDED: {lw_slug} -> manifest needs dotgg_slug: \"{url}\"")
    for lw_slug in results["not_on_dotgg"]:
        hint = "" if lw_slug in results["stubbed"] else f" (--stub {lw_slug} for a manual template)"
        print(f"NOT ON DOTGG: {lw_slug}{hint}")
    for lw_slug in results["stubbed"]:
        print(f"stubbed: {lw_slug} - fill its _todo fields, then delete _todo")
    for lw_slug, message in results["errors"]:
        print(f"ERROR: {lw_slug}: {message}")
    if not any(results.values()):
        print("nothing missing - every lootandwaifus unit has dotgg weapon stats")
    return 1 if results["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
