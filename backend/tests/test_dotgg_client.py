import json

import pytest

from app import dotgg_client


def test_fetch_character_list_returns_known_character(tmp_path):
    characters = dotgg_client.fetch_character_list(cache_dir=tmp_path)

    names = {c["name"] for c in characters}
    assert "Anis" in names
    assert len(characters) > 100


def test_fetch_character_list_writes_cache_file(tmp_path):
    dotgg_client.fetch_character_list(cache_dir=tmp_path)

    cache_file = tmp_path / "characters.json"
    assert cache_file.exists()
    cached = json.loads(cache_file.read_text(encoding="utf-8"))
    assert any(c["name"] == "Anis" for c in cached)


def test_fetch_character_list_second_call_uses_cache(tmp_path, monkeypatch):
    dotgg_client.fetch_character_list(cache_dir=tmp_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not hit network when cache is warm")

    monkeypatch.setattr(dotgg_client.requests, "get", fail_if_called)

    characters = dotgg_client.fetch_character_list(cache_dir=tmp_path)
    assert any(c["name"] == "Anis" for c in characters)


def test_fetch_character_returns_skill_level_data(tmp_path):
    anis = dotgg_client.fetch_character("anis", cache_dir=tmp_path)

    assert anis["name"] == "Anis"
    assert anis["class"] == "Defender"
    assert anis["element"] == "Iron"
    assert len(anis["skills"]) >= 1
    first_skill = anis["skills"][0]
    assert len(first_skill["levels"]) >= 1


def test_fetch_character_writes_per_slug_cache_file(tmp_path):
    dotgg_client.fetch_character("anis", cache_dir=tmp_path)

    cache_file = tmp_path / "character_anis.json"
    assert cache_file.exists()


def test_fetch_character_unknown_slug_raises(tmp_path):
    with pytest.raises(dotgg_client.DotggApiError):
        dotgg_client.fetch_character("this-character-does-not-exist", cache_dir=tmp_path)
