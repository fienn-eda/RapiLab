"""Turns raw character skill-level data into the `description_value_NN` slot
dicts the skill_rules builders consume.

lootandwaifus stores each level as raw text; encoders hand-numbered its numeric
tokens left-to-right when transcribing fixtures, so the extractor reproduces
exactly that convention. Some encoders skipped non-value numbers (trigger
phrases like "Burst stage 3"); those units carry a per-unit `drop_tokens`
override in their SKILL_VALUE_MANIFESTS, added only where the assembly
verification harness fails (see test_skill_value_assembly.py) — never
speculatively. dotgg levels are already native slot dicts and pass through.
"""
import json
import re
from pathlib import Path

_NUMBER = re.compile(r"\d+(?:\.\d+)?")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_SKILL_INDEX_TO_LEVEL_KEY = {0: "skill1", 1: "skill2", 2: "burst"}

_dotgg_url_index: dict = {}


def _dotgg_path_for(data_slug, data_dir):
    """dotgg filenames use dotgg's own slug (char_drake-nikke.json for "drake"),
    so files are indexed once by their "url" field, never located by filename."""
    dotgg_dir = Path(data_dir) / "dotgg"
    if dotgg_dir not in _dotgg_url_index:
        index = {}
        for path in sorted(dotgg_dir.glob("char_*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            index[data.get("url")] = path
        _dotgg_url_index[dotgg_dir] = index
    path = _dotgg_url_index[dotgg_dir].get(data_slug)
    if path is None:
        raise FileNotFoundError(f"no dotgg data file with url {data_slug!r}")
    return path


def load_character_data(source, data_slug, data_dir=DATA_DIR):
    if source == "dotgg":
        path = _dotgg_path_for(data_slug, data_dir)
    elif source == "shiftypad":
        path = Path(data_dir) / "shiftypad" / f"{data_slug}.json"
    else:
        path = Path(data_dir) / "lootandwaifus" / f"char_{data_slug}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def assemble_skill_values(slug, manifest, skill_levels, data_dir=DATA_DIR):
    data = load_character_data(manifest["source"], manifest.get("data_slug", slug), data_dir)
    values = {}
    for key, (array, index) in manifest["keys"].items():
        level = skill_levels[_SKILL_INDEX_TO_LEVEL_KEY[index]]
        raw_level = data[array][index]["levels"][level - 1]
        drop = manifest.get("drop_tokens", {}).get(key, ())
        if manifest["source"] in ("dotgg", "shiftypad"):
            values[key] = dotgg_slots(raw_level, drop)
        else:
            values[key] = extract_lootandwaifus_slots(raw_level, drop)
    return values


def extract_lootandwaifus_slots(level_text, drop_tokens=()):
    dropped = set(drop_tokens)
    tokens = [t for i, t in enumerate(_NUMBER.findall(level_text)) if i not in dropped]
    return {f"description_value_{i + 1:02d}": token for i, token in enumerate(tokens)}


def dotgg_slots(level_dict, drop_tokens=()):
    """Native slot passthrough (minus empty slots). Some encoders renumbered
    dotgg's native slots when transcribing (skipping threshold/count slots the
    builders don't read), so drop_tokens applies here too: drop the given
    0-based non-empty slots and renumber the rest sequentially. Without drops,
    native slot keys are preserved untouched."""
    if not drop_tokens:
        return {key: value for key, value in level_dict.items() if value != ""}
    dropped = set(drop_tokens)
    tokens = [v for v in level_dict.values() if v != ""]
    kept = [t for i, t in enumerate(tokens) if i not in dropped]
    return {f"description_value_{i + 1:02d}": token for i, token in enumerate(kept)}
