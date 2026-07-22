"""shiftypad-source loading: weapon, skill values and meta come from the
normalized data/shiftypad/<slug>.json, not dotgg."""
import json
from pathlib import Path

from app.shiftypad_normalize import normalize_shiftypad
from app.skill_values import assemble_skill_values, load_character_data

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"


def _write_normalized(data_dir, slug):
    bundle = json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))
    out = data_dir / "shiftypad"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{slug}.json").write_text(
        json.dumps(normalize_shiftypad(bundle)), encoding="utf-8"
    )


def test_load_character_data_reads_shiftypad_dir(tmp_path):
    _write_normalized(tmp_path, "rapi-red-hood")
    data = load_character_data("shiftypad", "rapi-red-hood", tmp_path)
    assert data["weapon"] == "MG"
    assert data["skills"][0]["levels"][0]["description_value_02"] == "5.34"


def test_assemble_skill_values_treats_shiftypad_as_native_slots(tmp_path):
    _write_normalized(tmp_path, "rapi-red-hood")
    manifest = {
        "source": "shiftypad",
        "keys": {"battlefield_assessment": ("skills", 0)},
    }
    levels = {"skill1": 1, "skill2": 1, "burst": 1}
    values = assemble_skill_values("rapi-red-hood", manifest, levels, tmp_path)
    # native-slot passthrough, same as dotgg
    assert values["battlefield_assessment"]["description_value_02"] == "5.34"
