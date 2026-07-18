"""Detect balance-patch drift for dotgg-source skill-value manifests.

api.dotgg.gg stopped updating around 2026-05, but some encoded units still
read their runtime skill values from data/dotgg/*.json (manifest source
"dotgg"). When such a unit is balance-patched, the dotgg file keeps loading
without error and the simulation silently uses pre-patch numbers (proven on
Scarlet: Black Shadow, 2026-07 - see docs/insights.md). This script compares
every dotgg-source manifest's consumed skills, all levels, against
lootandwaifus data and reports which units drifted - those are the
migration candidates to source "lootandwaifus".

By default each target unit's lootandwaifus page is re-fetched first (browser
User-Agent curl, per the data-sources reference) so the comparison is against
the live site; the HTML and regenerated JSON land in data/lootandwaifus/ as a
useful side effect. --offline compares whatever is on disk.

Usage:
    python scripts/check_skill_value_drift.py               # fetch + compare all
    python scripts/check_skill_value_drift.py --offline     # local files only
    python scripts/check_skill_value_drift.py --slug mint   # one manifest

Output: one OK/DRIFT line per manifest (DRIFT details indented), WARN lines
for anything unverifiable, then a summary. Exit 1 if any DRIFT, else 0.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from lootandwaifus_html_to_json import parse_html

LW_DIR = ROOT / "data" / "lootandwaifus"
# Same numeric-token regex the engine's extractor uses (skill_values.py).
NUMBER = re.compile(r"\d+(?:\.\d+)?")
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def referenced_slots(skill):
    """Slot names the skill's description template actually interpolates
    (e.g. {"description_value_01", "description_value_02"}), parsed from its
    "description" string. Returns None when there is no description or it
    has no {description_value_NN} placeholders, meaning the caller should
    fall back to comparing all non-filler slots - some dotgg levels carry
    leftover slots the description never renders (brid-silent-track "Full
    Throttle" description_value_04 duplicates the real duration slot), and
    those must not be compared against the rendered lootandwaifus text."""
    matches = re.findall(r"\{(description_value_\d+)\}",
                          skill.get("description") or "")
    return frozenset(matches) if matches else None


def dotgg_level_values(level_dict, referenced=None):
    """Numeric values a dotgg level actually carries: "" slots are unused and
    a literal "0" is dotgg's unused-slot filler too (e.g. Scarlet: Black
    Shadow Skill 2 value_04) - never a patched stat. When referenced is
    given, only slots in that set are considered (see referenced_slots)."""
    items = level_dict.items()
    if referenced is not None:
        items = ((k, v) for k, v in items if k in referenced)
    return [v for _, v in items if v not in ("", "0")]


def level_missing(level_dict, lw_text, referenced=None):
    """dotgg slot values (raw strings) with no matching numeric token left in
    the lootandwaifus level text. Multiset semantics: each match consumes its
    token, so duplicate values need duplicate tokens. Extra tokens are fine
    (trigger phrases, "1/2/3 times"). referenced restricts which dotgg slots
    are compared - see dotgg_level_values."""
    available = Counter(float(t) for t in NUMBER.findall(lw_text))
    missing = []
    for value in dotgg_level_values(level_dict, referenced):
        number = float(value)
        if available[number] > 0:
            available[number] -= 1
        else:
            missing.append(value)
    return missing


def compare_unit(dotgg_data, lw_data, keys):
    """Compare every manifest-consumed (array, index) skill across all levels
    both sides have. Returns (drift, warnings): drift maps manifest key ->
    [(level_number_1based, [missing raw strings])]; warnings are strings for
    anything that couldn't be verified (missing array, level-count skew)."""
    drift = {}
    warnings = []
    for key, (array, index) in sorted(keys.items()):
        lw_skills = lw_data.get(array)
        if not lw_skills or index >= len(lw_skills):
            warnings.append(f"{key}: lootandwaifus data has no {array}[{index}]")
            continue
        skill = dotgg_data[array][index]
        dotgg_levels = skill["levels"]
        lw_levels = lw_skills[index]["levels"]
        referenced = referenced_slots(skill)
        if len(dotgg_levels) != len(lw_levels):
            warnings.append(
                f"{key}: level count mismatch (dotgg {len(dotgg_levels)}, "
                f"lootandwaifus {len(lw_levels)})")
        findings = []
        for i in range(min(len(dotgg_levels), len(lw_levels))):
            missing = level_missing(dotgg_levels[i], lw_levels[i], referenced)
            if missing:
                findings.append((i + 1, missing))
        if findings:
            drift[key] = findings
    return drift, warnings


def refresh_lw(slugs, lw_dir, fetch_html):
    """Re-fetch + re-parse lootandwaifus pages for the given slugs, writing
    char_<slug>.html and char_<slug>.json into lw_dir (same layout the
    collect workflow uses). A failed slug becomes a warning and is skipped -
    its stale local files, if any, are left untouched. Returns warnings."""
    lw_dir = Path(lw_dir)
    warnings = []
    for slug in sorted(set(slugs)):
        try:
            raw = fetch_html(slug)
        except Exception as exc:
            warnings.append(f"{slug}: fetch failed: {exc}")
            continue
        data, parse_warnings = parse_html(raw, slug)
        warnings.extend(f"{slug}: {w}" for w in parse_warnings)
        (lw_dir / f"char_{slug}.html").write_text(raw, encoding="utf-8")
        (lw_dir / f"char_{slug}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return warnings


def run_check(manifests, lw_dir, data_dir, fetch_html=None):
    """Compare each dotgg-source manifest against lootandwaifus data.
    manifests: {slug: manifest}, pre-filtered to source == "dotgg".
    data_dir: the data ROOT (contains dotgg/). If fetch_html is given, the
    target lootandwaifus pages are refreshed first. Returns
    ({slug: {"status", "drift", "warnings"}}, refresh_warnings)."""
    from app.skill_values import load_character_data

    lw_dir = Path(lw_dir)
    refresh_warnings = []
    if fetch_html is not None:
        slugs = {m.get("data_slug", slug) for slug, m in manifests.items()}
        refresh_warnings = refresh_lw(slugs, lw_dir, fetch_html)

    results = {}
    for slug, manifest in sorted(manifests.items()):
        data_slug = manifest.get("data_slug", slug)
        lw_path = lw_dir / f"char_{data_slug}.json"
        if not lw_path.exists():
            results[slug] = {"status": "WARN", "drift": {}, "warnings": [
                f"no lootandwaifus JSON (char_{data_slug}.json)"]}
            continue
        dotgg_data = load_character_data("dotgg", data_slug, data_dir)
        lw_data = json.loads(lw_path.read_text(encoding="utf-8"))
        drift, warnings = compare_unit(dotgg_data, lw_data, manifest["keys"])
        status = "DRIFT" if drift else ("WARN" if warnings else "OK")
        results[slug] = {"status": status, "drift": drift,
                         "warnings": warnings}
    return results, refresh_warnings


def curl_fetch(slug):
    """Fetch a character page with the browser-UA curl convention the
    data-sources reference documents (lootandwaifus 403s non-browser UAs)."""
    url = f"https://lootandwaifus.com/character/{slug}-nikke/"
    result = subprocess.run(
        ["curl", "-s", "-L", "--fail", "--max-time", "60", "-A", USER_AGENT,
         url],
        capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(
            f"curl exit {result.returncode} for {url}: {result.stderr.strip()}")
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true",
                        help="skip re-fetching; compare local files only")
    parser.add_argument("--slug", help="check a single manifest slug")
    args = parser.parse_args(argv)

    from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest

    manifests = {}
    for slug in sorted(ENCODED_SLUGS):
        manifest = get_skill_value_manifest(slug)
        if manifest is not None and manifest["source"] == "dotgg":
            manifests[slug] = manifest
    if args.slug:
        if args.slug not in manifests:
            parser.error(f"{args.slug!r} is not a dotgg-source manifest slug; "
                         f"candidates: {', '.join(sorted(manifests))}")
        manifests = {args.slug: manifests[args.slug]}

    results, refresh_warnings = run_check(
        manifests, LW_DIR, ROOT / "data",
        fetch_html=None if args.offline else curl_fetch)

    for message in refresh_warnings:
        print(f"WARN {message}")
    counts = Counter(r["status"] for r in results.values())
    for slug, result in sorted(results.items()):
        print(f"{result['status']} {slug}")
        for key, findings in sorted(result["drift"].items()):
            for level, missing in findings:
                print(f"  {key} Lv{level}: dotgg {', '.join(missing)} "
                      f"not in lootandwaifus")
        for message in result["warnings"]:
            print(f"  WARN {message}")
    print(f"\n{counts['OK']} OK, {counts['DRIFT']} DRIFT, {counts['WARN']} "
          f"WARN of {len(results)} dotgg-source manifest(s)")
    return 1 if counts["DRIFT"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
