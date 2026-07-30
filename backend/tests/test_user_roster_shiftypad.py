"""shiftypad-source loading: weapon, skill values and meta come from the
normalized data/shiftypad/<slug>.json, not dotgg."""
import json
from pathlib import Path

from app.models import UserNikkeState
from app.shiftypad_normalize import normalize_shiftypad
from app.skill_values import assemble_skill_values, load_character_data
from app.user_roster import load_nikke_spec

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


def test_weapon_source_lets_a_lootandwaifus_slug_take_shiftypad_weapon_stats(monkeypatch):
    """A Favorite Item slug reads its dollskills from lootandwaifus while taking
    weapon stats from the BASE unit's normalized ShiftyPad file. Such a unit has
    no dotgg file at all, and dotgg can no longer be collected from."""
    manifest = {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "sugar",
        "keys": {"black_typhoon": ("dollskills", 0)},
    }
    monkeypatch.setattr("app.user_roster.ENCODED_SLUGS", {"sugar-signature"})
    monkeypatch.setattr("app.user_roster.get_skill_value_manifest", lambda slug: manifest)

    spec = load_nikke_spec(UserNikkeState(
        character_slug="sugar-signature", level=200, hp=1_000_000.0, atk=60_000.0,
        def_=3_000.0, skill_levels={"skill1": 10, "skill2": 10, "burst": 10},
    ))

    assert spec is not None
    # weapon stats from data/shiftypad/sugar.json, except reload_time: Sugar is
    # a clip shotgun, so the file's 0.67 sec buys three of her nine rounds and
    # the magazine costs three of them (registry.CLIP_RELOAD_SPLITS).
    assert spec.weapon_stats == {
        "weapon": "SG", "damage_percent": 231.6, "max_ammo": 9,
        "reload_time": 0.67 * 3, "charge_time": 0.0, "charge_damage_percent": 100.0,
    }
    # meta still prefers the lootandwaifus file
    assert (spec.burst_tier, spec.element, spec.burst_cooldown) == (3, "Iron", 40.0)
    # and the skill values came from dollskills, not skills: only the Favorite
    # Item text carries the intact-cover Attack Damage bullet.
    assert spec.skill_values["black_typhoon"]["description_value_06"] == "19.98"
