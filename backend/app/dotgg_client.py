"""Client for the public api.dotgg.gg NIKKE data API (no auth required).

Responses are cached to disk as plain JSON so we don't hammer a third-party
API that isn't officially documented for this kind of use.
"""
import json
from pathlib import Path

import requests

from app.paths import writable_dir

BASE_URL = "https://api.dotgg.gg/nikke"
# 캐시는 번들이 아니라 사용자 디렉터리로 간다 - 설치 위치는 쓰기 금지일 수 있다.
DEFAULT_CACHE_DIR = writable_dir() / "cache"


class DotggApiError(Exception):
    pass


def _cache_path(cache_dir: Path, filename: str) -> Path:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / filename


def _get_json(url: str) -> dict:
    response = requests.get(url, timeout=10)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise DotggApiError(f"{url} -> {response.status_code}: {response.text}") from exc
    return response.json()


def fetch_character_list(cache_dir: Path = DEFAULT_CACHE_DIR) -> list[dict]:
    cache_file = _cache_path(cache_dir, "characters.json")
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    data = _get_json(f"{BASE_URL}/characters")
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def fetch_character(slug: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> dict:
    cache_file = _cache_path(cache_dir, f"character_{slug}.json")
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    data = _get_json(f"{BASE_URL}/character/{slug}")
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data
