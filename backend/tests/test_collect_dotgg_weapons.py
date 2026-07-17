"""Tests for scripts/collect_dotgg_weapons.py - coverage detection, dotgg
slug/name resolution, manual-stub shape, and collect() orchestration with
fake fetchers (no network). The script lives outside backend/, so its
directory is added to sys.path here."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import collect_dotgg_weapons as cdw

from app.user_roster import _weapon_stats


CHARACTERS = [
    {"name": "Scarlet: Black Shadow", "url": "scarlet-black-shadow"},
    {"name": "Privaty", "url": "privaty"},
]


def test_wanted_urls_default_to_the_lootandwaifus_slug():
    assert cdw.wanted_dotgg_urls(["mint"], {}) == {"mint": "mint"}


def test_wanted_urls_apply_the_manifest_dotgg_slug_alias():
    manifests = {"ada-wong": {"source": "lootandwaifus", "dotgg_slug": "ada"}}
    assert cdw.wanted_dotgg_urls(["ada-wong"], manifests) == {"ada-wong": "ada"}


def test_existing_urls_read_the_url_field_not_the_filename(tmp_path):
    (tmp_path / "char_drake-nikke.json").write_text(
        json.dumps({"name": "Drake", "url": "drake"}), encoding="utf-8"
    )
    assert cdw.existing_dotgg_urls(tmp_path) == {"drake"}


def test_resolve_prefers_exact_slug_match():
    entry, how = cdw.resolve_dotgg_entry("scarlet-black-shadow", "anything", CHARACTERS)
    assert entry["url"] == "scarlet-black-shadow"
    assert how == "slug"


def test_resolve_falls_back_to_case_insensitive_exact_name_match():
    entry, how = cdw.resolve_dotgg_entry("privaty-nikke", "PRIVATY", CHARACTERS)
    assert entry["url"] == "privaty"
    assert how == "name"


def test_resolve_never_partial_matches_names():
    # "Cinderella: Crystal Wave" must NOT match base "Cinderella" - different unit.
    characters = [{"name": "Cinderella", "url": "cinderella"}]
    entry, how = cdw.resolve_dotgg_entry(
        "cinderella-crystal-wave", "Cinderella: Crystal Wave", characters
    )
    assert entry is None
    assert how is None


def test_stub_for_charge_weapon_lists_all_five_manual_fields():
    lw = {"name": "Ark Ranger Black", "url": "ark-ranger-black", "weapon": "SR"}
    stub = cdw.make_stub(lw, "ark-ranger-black")
    assert stub["url"] == "ark-ranger-black"
    assert stub["source"] == "manual"
    assert stub["weapon"] == "SR"
    assert stub["_todo"] == ["maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage"]
    assert "chargeTime" not in stub


def test_stub_for_magazine_weapon_prefills_the_charge_fields():
    lw = {"name": "Prika", "url": "prika", "weapon": "MG"}
    stub = cdw.make_stub(lw, "prika")
    assert stub["chargeTime"] == 0
    assert stub["chargeDamage"] == "0%"
    assert stub["_todo"] == ["maxAmmo", "damage", "reloadTime"]


def test_unfilled_stub_is_rejected_by_the_weapon_stats_loader():
    stub = cdw.make_stub({"name": "Prika", "url": "prika", "weapon": "MG"}, "prika")
    assert _weapon_stats(stub) is None
