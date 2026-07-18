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


def dotgg_level_values(level_dict):
    """Numeric values a dotgg level actually carries: "" slots are unused and
    a literal "0" is dotgg's unused-slot filler too (e.g. Scarlet: Black
    Shadow Skill 2 value_04) - never a patched stat."""
    return [v for v in level_dict.values() if v not in ("", "0")]


def level_missing(level_dict, lw_text):
    """dotgg slot values (raw strings) with no matching numeric token left in
    the lootandwaifus level text. Multiset semantics: each match consumes its
    token, so duplicate values need duplicate tokens. Extra tokens are fine
    (trigger phrases, "1/2/3 times")."""
    available = Counter(float(t) for t in NUMBER.findall(lw_text))
    missing = []
    for value in dotgg_level_values(level_dict):
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
        dotgg_levels = dotgg_data[array][index]["levels"]
        lw_levels = lw_skills[index]["levels"]
        if len(dotgg_levels) != len(lw_levels):
            warnings.append(
                f"{key}: level count mismatch (dotgg {len(dotgg_levels)}, "
                f"lootandwaifus {len(lw_levels)})")
        findings = []
        for i in range(min(len(dotgg_levels), len(lw_levels))):
            missing = level_missing(dotgg_levels[i], lw_levels[i])
            if missing:
                findings.append((i + 1, missing))
        if findings:
            drift[key] = findings
    return drift, warnings
