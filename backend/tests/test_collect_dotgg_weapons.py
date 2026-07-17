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
    assert stub["chargeDamage"] == "100%"
    assert stub["_todo"] == ["maxAmmo", "damage", "reloadTime"]


def test_unfilled_stub_is_rejected_by_the_weapon_stats_loader():
    stub = cdw.make_stub({"name": "Prika", "url": "prika", "weapon": "MG"}, "prika")
    assert _weapon_stats(stub) is None


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _data_dirs(tmp_path):
    lw_dir = tmp_path / "lootandwaifus"
    dotgg_dir = tmp_path / "dotgg"
    lw_dir.mkdir()
    dotgg_dir.mkdir()
    return lw_dir, dotgg_dir


def test_collect_fetches_missing_units_and_skips_covered_ones(tmp_path):
    lw_dir, dotgg_dir = _data_dirs(tmp_path)
    _write(lw_dir / "char_scarlet-black-shadow.json",
           {"name": "Scarlet: Black Shadow", "url": "scarlet-black-shadow", "weapon": "RL"})
    _write(lw_dir / "char_mint.json", {"name": "Mint", "url": "mint", "weapon": "SR"})
    _write(dotgg_dir / "char_mint.json",
           {"name": "Mint", "url": "mint", "weapon": "SR", "chargeTime": 1})
    calls = []

    def fetch_char(slug):
        calls.append(slug)
        return {"name": "Scarlet: Black Shadow", "url": slug, "weapon": "RL", "chargeTime": 0.3}

    results = cdw.collect(lw_dir, dotgg_dir, {}, lambda: CHARACTERS, fetch_char)
    assert calls == ["scarlet-black-shadow"]
    saved = json.loads(
        (dotgg_dir / "char_scarlet-black-shadow.json").read_text(encoding="utf-8"))
    assert saved["chargeTime"] == 0.3
    assert results["fetched"] == [("scarlet-black-shadow", "scarlet-black-shadow", "slug")]
    assert results["errors"] == []


def test_collect_never_calls_the_api_when_nothing_is_missing(tmp_path):
    lw_dir, dotgg_dir = _data_dirs(tmp_path)
    _write(lw_dir / "char_mint.json", {"name": "Mint", "url": "mint", "weapon": "SR"})
    _write(dotgg_dir / "char_mint.json", {"name": "Mint", "url": "mint"})

    def explode():
        raise AssertionError("character list fetched with nothing missing")

    results = cdw.collect(lw_dir, dotgg_dir, {}, explode, explode)
    assert results["fetched"] == []


def test_collect_reports_alias_without_refetch_when_local_file_exists(tmp_path):
    # privaty-nikke (lw slug) resolves by name to dotgg "privaty", whose file
    # is already local under its own url - no fetch, just a manifest hint.
    lw_dir, dotgg_dir = _data_dirs(tmp_path)
    _write(lw_dir / "char_privaty-nikke.json",
           {"name": "Privaty", "url": "privaty-nikke", "weapon": "AR"})
    _write(dotgg_dir / "char_privaty.json", {"name": "Privaty", "url": "privaty"})

    def fetch_char(slug):
        raise AssertionError("refetched an already-local file")

    results = cdw.collect(lw_dir, dotgg_dir, {}, lambda: CHARACTERS, fetch_char)
    assert results["alias_needed"] == [("privaty-nikke", "privaty")]
    assert results["fetched"] == []


def test_collect_marks_name_resolved_fetches_as_alias_needed(tmp_path):
    lw_dir, dotgg_dir = _data_dirs(tmp_path)
    _write(lw_dir / "char_privaty-nikke.json",
           {"name": "Privaty", "url": "privaty-nikke", "weapon": "AR"})

    def fetch_char(slug):
        return {"name": "Privaty", "url": slug, "weapon": "AR"}

    results = cdw.collect(lw_dir, dotgg_dir, {}, lambda: CHARACTERS, fetch_char)
    assert results["fetched"] == [("privaty-nikke", "privaty", "name")]
    assert results["alias_needed"] == [("privaty-nikke", "privaty")]
    assert (dotgg_dir / "char_privaty.json").exists()


def test_collect_stubs_only_the_requested_slugs(tmp_path):
    lw_dir, dotgg_dir = _data_dirs(tmp_path)
    _write(lw_dir / "char_prika.json", {"name": "Prika", "url": "prika", "weapon": "MG"})
    _write(lw_dir / "char_ark-ranger-black.json",
           {"name": "Ark Ranger Black", "url": "ark-ranger-black", "weapon": "SR"})

    results = cdw.collect(lw_dir, dotgg_dir, {}, lambda: [], lambda s: {},
                          stub_slugs=("prika",))
    assert sorted(results["not_on_dotgg"]) == ["ark-ranger-black", "prika"]
    assert results["stubbed"] == ["prika"]
    stub = json.loads((dotgg_dir / "char_prika.json").read_text(encoding="utf-8"))
    assert stub["source"] == "manual"
    assert not (dotgg_dir / "char_ark-ranger-black.json").exists()


def test_collect_records_the_error_and_continues_after_a_failed_fetch(tmp_path):
    lw_dir, dotgg_dir = _data_dirs(tmp_path)
    _write(lw_dir / "char_privaty-nikke.json",
           {"name": "Privaty", "url": "privaty-nikke", "weapon": "AR"})
    _write(lw_dir / "char_scarlet-black-shadow.json",
           {"name": "Scarlet: Black Shadow", "url": "scarlet-black-shadow", "weapon": "RL"})

    def fetch_char(slug):
        if slug == "privaty":
            raise RuntimeError("boom")
        return {"name": "Scarlet: Black Shadow", "url": slug, "weapon": "RL"}

    results = cdw.collect(lw_dir, dotgg_dir, {}, lambda: CHARACTERS, fetch_char)
    assert [slug for slug, _ in results["errors"]] == ["privaty-nikke"]
    assert results["fetched"] == [("scarlet-black-shadow", "scarlet-black-shadow", "slug")]


def test_collect_dry_run_writes_nothing(tmp_path):
    lw_dir, dotgg_dir = _data_dirs(tmp_path)
    _write(lw_dir / "char_scarlet-black-shadow.json",
           {"name": "Scarlet: Black Shadow", "url": "scarlet-black-shadow", "weapon": "RL"})
    _write(lw_dir / "char_prika.json", {"name": "Prika", "url": "prika", "weapon": "MG"})

    def fetch_char(slug):
        raise AssertionError("dry run must not fetch character data")

    results = cdw.collect(lw_dir, dotgg_dir, {}, lambda: CHARACTERS, fetch_char,
                          stub_slugs=("prika",), dry_run=True)
    assert results["fetched"] == [("scarlet-black-shadow", "scarlet-black-shadow", "slug")]
    assert results["stubbed"] == []
    assert list(dotgg_dir.iterdir()) == []
