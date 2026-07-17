# dotgg 무기 스탯 공백 해소 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** lootandwaifus로만 수집된 유닛의 dotgg 무기 스탯 파일을 재사용 스크립트로 채우고, dotgg에 없는 신규 유닛(2026-05 이후)은 수동 입력 스텁으로 메운다. 엔진/로더 코드 변경 없음.

**Architecture:** `scripts/collect_dotgg_weapons.py` 단일 스크립트. 순수 함수(누락 판정·슬러그 해석·스텁 생성)와 주입식 오케스트레이션 `collect()`(fetch 함수를 인자로 받아 테스트에서 fake 사용)로 나눈다. dotgg 파일은 파일명이 아니라 **파일 내 `url` 필드**로 색인되므로(`skill_values.py:_dotgg_path_for`) 커버리지 판정도 url 집합으로 한다.

**Tech Stack:** Python 표준 라이브러리 + 기존 `app.dotgg_client`(requests) 재사용. 테스트는 pytest.

**스펙:** `docs/superpowers/specs/2026-07-17-dotgg-weapon-stats-design.md`

## Global Constraints

- 테스트 실행은 `backend/` 디렉토리에서 `python3 -m pytest ...` (`python3` = anaconda, pytest 8.4.2 보유. `python`(C:\Python314)에는 pytest 없음).
- `backend/pytest.ini`가 `filterwarnings = error` — 경고 하나라도 새면 실패. 테스트 출력은 프리스틴해야 함.
- 스크립트 스타일은 `scripts/lootandwaifus_html_to_json.py`를 따른다: 모듈 docstring에 목적/When to use/Usage, argparse, 유닛별 오류 보고 후 계속 진행, 실행 요약 출력. 코드·주석·출력은 영어.
- 커밋 메시지는 기존 스타일(`feat:`/`docs:`/`test:` prefix, 소문자 요약).
- `git add -A` 금지 — 파일을 명시해서 add.
- 작업 위치: worktree `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\dotgg-weapon-stats-gap` (브랜치 `worktree-dotgg-weapon-stats-gap`).

**도메인 배경 (구현자가 알아야 할 것):**
- 로더 체인: `user_roster.load_nikke_spec` → manifest(`get_skill_value_manifest(slug)`)의 `dotgg_slug`(없으면 `data_slug`, 없으면 slug)로 `load_character_data("dotgg", …)` 호출 → `_dotgg_path_for`가 `data/dotgg/char_*.json`들의 내부 `url` 필드로 색인해 찾음. `_weapon_stats`는 6필드(`weapon`, `maxAmmo`, `damage`, `reloadTime`, `chargeTime`, `chargeDamage`)가 **모두 존재**해야 dict를 반환, 하나라도 없으면 None(→ 유닛 제외). 값이 빈 문자열이면 존재 검사는 통과하고 `int("")`에서 죽으므로 **스텁은 미입력 필드를 생략**해야 한다.
- 매니페스트는 각 `backend/app/skill_rules/<unit>.py`의 `SKILL_VALUE_MANIFESTS`에 콜로케이트, `registry.get_skill_value_manifest(slug)`로 병합 조회. 전체 목록은 `ENCODED_SLUGS`를 돌며 얻는다. registry import는 pydantic 불필요(순수 stdlib).
- dotgg API는 2026-05경 갱신 중단. 구 유닛은 여전히 응답함(scarlet-black-shadow의 `chargeTime: 0.3` 라이브 확인, 2026-07-17). 신규 유닛 4종은 어떤 이름으로도 없음: `ark-ranger-black`, `cinderella-crystal-wave`, `marciana-marine-study`, `prika`.
- 이름 매칭은 **정확 일치(대소문자만 무시)**여야 한다. 부분 일치를 쓰면 `cinderella-crystal-wave`가 base `Cinderella`에, `marciana-marine-study`가 base `Marciana`에 잘못 매칭된다(다른 유닛!).
- 스텁 생성은 `--stub <slug>...` 명시 지정 유닛만. 자동 생성하면 별칭 문제 유닛(예: asuka-shikinami-langley-wille ↔ dotgg `asuka-wille`, 이름 표기도 다름)에 잘못된 스텁이 생긴다.

---

### Task 1: 순수 헬퍼 함수 (누락 판정 · 슬러그 해석 · 스텁 생성)

**Files:**
- Create: `scripts/collect_dotgg_weapons.py`
- Test: `backend/tests/test_collect_dotgg_weapons.py`

**Interfaces:**
- Produces (Task 2가 사용):
  - `wanted_dotgg_urls(lw_slugs, manifests) -> dict[str, str]` — lw 슬러그 → 로더가 조회할 dotgg url
  - `existing_dotgg_urls(dotgg_dir) -> set[str]` — 로컬 dotgg 파일들의 내부 `url` 집합
  - `resolve_dotgg_entry(wanted_url, lw_name, characters) -> (dict | None, str | None)` — how는 `"slug"` | `"name"` | None
  - `make_stub(lw_data, wanted_url) -> dict` — 수동 입력 템플릿
  - 상수 `CHARGE_WEAPONS`, `MANUAL_FIELDS_CHARGE`, `MANUAL_FIELDS_MAGAZINE`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_collect_dotgg_weapons.py` 생성:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (backend/에서): `python3 -m pytest tests/test_collect_dotgg_weapons.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'collect_dotgg_weapons'`

- [ ] **Step 3: 최소 구현**

`scripts/collect_dotgg_weapons.py` 생성:

```python
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
        stub["chargeTime"] = 0
        stub["chargeDamage"] = "0%"
    stub["_todo"] = todo
    return stub
```

- [ ] **Step 4: 테스트 통과 확인**

Run (backend/에서): `python3 -m pytest tests/test_collect_dotgg_weapons.py -v`
Expected: 9 passed

- [ ] **Step 5: 커밋**

```bash
git add scripts/collect_dotgg_weapons.py backend/tests/test_collect_dotgg_weapons.py
git commit -m "feat: pure helpers for dotgg weapon-stat collection (coverage, resolution, stubs)"
```

---

### Task 2: collect() 오케스트레이션 + CLI

**Files:**
- Modify: `scripts/collect_dotgg_weapons.py` (Task 1 파일에 추가)
- Test: `backend/tests/test_collect_dotgg_weapons.py` (추가)

**Interfaces:**
- Consumes: Task 1의 순수 함수 전부.
- Produces:
  - `collect(lw_dir, dotgg_dir, manifests, fetch_list, fetch_char, stub_slugs=(), dry_run=False) -> dict` — 키: `"fetched"` (lw_slug, url, how) 리스트, `"alias_needed"` (lw_slug, url), `"not_on_dotgg"` lw_slug 리스트, `"stubbed"` lw_slug 리스트, `"errors"` (lw_slug, message).
  - `main(argv=None) -> int` — 오류 있으면 1.
  - `alias_needed` 의미: 해석된 dotgg url이 로더가 찾을 url(wanted)과 다름 → 해당 유닛이 인코딩될 때 manifest에 `dotgg_slug: "<url>"` 필요.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_collect_dotgg_weapons.py`에 추가:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (backend/에서): `python3 -m pytest tests/test_collect_dotgg_weapons.py -v`
Expected: Task 1의 9개는 PASS, 새 7개는 FAIL — `AttributeError: module 'collect_dotgg_weapons' has no attribute 'collect'`

- [ ] **Step 3: 구현**

`scripts/collect_dotgg_weapons.py`의 `make_stub` 아래에 추가:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run (backend/에서): `python3 -m pytest tests/test_collect_dotgg_weapons.py -v`
Expected: 16 passed

- [ ] **Step 5: 전체 스위트 회귀 확인**

Run (backend/에서): `python3 -m pytest -q`
Expected: 전부 PASS (기존 스위트에 영향 없음)

- [ ] **Step 6: 커밋**

```bash
git add scripts/collect_dotgg_weapons.py backend/tests/test_collect_dotgg_weapons.py
git commit -m "feat: collect_dotgg_weapons script - fetch missing dotgg weapon stats, stub dotgg-absent units"
```

---

### Task 3: 실제 수집 실행 + 산출물 반영

**Files:**
- Create: `data/dotgg/char_*.json` (스크립트 산출물 — 수집분 + 스텁 4개)

**Interfaces:**
- Consumes: Task 2의 CLI.

**주의:** `data/dotgg/`·`data/lootandwaifus/`는 `.gitignore`에 있음 — git 밖
로컬 데이터 자산이라 **커밋 불가/불필요**. 워크트리에는 메인 체크아웃에서
복사해 둔 사본이 있고, 스크립트 산출물은 브랜치 머지와 별개로 마지막에
메인 체크아웃 `data/dotgg/`로 복사해 전달한다.

- [ ] **Step 1: dry-run으로 대상 확인**

Run (저장소 루트에서): `python3 scripts/collect_dotgg_weapons.py --dry-run`
Expected: `would fetch:` 줄들에 scarlet-black-shadow, bready, red-hood, snow-white 등이 나오고, `NOT ON DOTGG:`에 ark-ranger-black · cinderella-crystal-wave · marciana-marine-study · prika (+ 별칭 미해결 유닛이 있으면 그것도), ERROR 없음.

- [ ] **Step 2: 실제 수집 + 스텁 생성**

Run (저장소 루트에서):
```bash
python3 scripts/collect_dotgg_weapons.py --stub ark-ranger-black cinderella-crystal-wave marciana-marine-study prika
```
Expected: exit 0, dry-run에서 예고된 유닛들이 `fetched:`로, 4유닛이 `stubbed:`로 출력.

- [ ] **Step 3: 산출물 검증**

Run (저장소 루트에서):
```bash
python3 -c "import json; d=json.load(open('data/dotgg/char_scarlet-black-shadow.json', encoding='utf-8')); print(d['chargeTime'], d['maxAmmo'], d['reloadTime'])"
```
Expected: `0.3 9 2` (라이브 확인값과 일치)

```bash
python3 -c "import json; d=json.load(open('data/dotgg/char_prika.json', encoding='utf-8')); print(d['source'], d['_todo'])"
```
Expected: `manual ['maxAmmo', 'damage', 'reloadTime']`

- [ ] **Step 4: 전체 스위트 확인**

Run (backend/에서): `python3 -m pytest -q`
Expected: 전부 PASS. (스텁이 url 색인에 들어가도 `_weapon_stats` 필드 검사로 해당 유닛은 여전히 제외 — 실패하면 원인 규명 후 수정.)

- [ ] **Step 5: 산출물 확인 (커밋 없음 — data/는 gitignore)**

```bash
git status --short   # data/ 산출물이 untracked/ignored로 남고 추적 파일 변경이 없는지 확인
ls data/dotgg | wc -l   # 파일 수 증가 확인 (53 + 수집분 + 스텁 4)
```

메인 체크아웃 반영은 브랜치 마무리 단계에서 새 `char_*.json`들을
`C:\Users\fienn\Desktop\NikkeDeckBuilder\data\dotgg\`로 복사해서 수행.

---

### Task 4: collect-nikke 워크플로 갱신

**Files:**
- Modify: `.claude/commands/collect-nikke.md`

**Interfaces:** 없음 (문서/지침).

- [ ] **Step 1: 커맨드 지침에 무기 스탯 확보 단계 추가**

`.claude/commands/collect-nikke.md` 끝(현재 마지막 줄 "Confirm the saved file retains all skill levels, not just the max.")에 다음 단락 추가:

```markdown

After saving a lootandwaifus collection, also secure the unit's dotgg
weapon stats (the engine reads maxAmmo/damage/reloadTime/chargeTime/
chargeDamage from data/dotgg/, and lootandwaifus only has the weapon TYPE):
run `python3 scripts/collect_dotgg_weapons.py`. If it reports the unit as
NOT ON DOTGG (dotgg stopped updating around 2026-05), rerun with
`--stub <slug>` and report that Fienn must fill the stub's `_todo` fields
(then delete `_todo`); include the stub path in your report. If it reports
ALIAS NEEDED, note that the unit's manifest needs that `dotgg_slug` when it
gets encoded.
```

- [ ] **Step 2: 커밋**

```bash
git add .claude/commands/collect-nikke.md
git commit -m "docs: collect-nikke also secures dotgg weapon stats (script + manual stub path)"
```

---

### Task 5: 프로젝트 문서 갱신

**Files:**
- Modify: `docs/roadmap.md`

**Interfaces:** 없음.

- [ ] **Step 1: roadmap Phase 6 잔여 문구 갱신**

`docs/roadmap.md`의 Phase 6 항목(297–304행 부근)에서 마지막 문장

```
marciana(스킨판 weapon 스탯
  없음)·ark-ranger-black·prika(dotgg 부재)는 보류.
```

를 다음으로 교체:

```
marciana-marine-study·ark-ranger-black·prika·cinderella-crystal-wave(dotgg
  부재, 2026-05 갱신 중단)는 `scripts/collect_dotgg_weapons.py --stub`으로
  수동 스텁 생성됨 — Fienn이 `_todo` 필드(무기 스탯 3~5개)를 채우면 로더블.
```

그리고 같은 Phase 6 리스트에 항목 추가:

```
- dotgg 무기 스탯 수집 자동화 ✅ (2026-07-17): `scripts/collect_dotgg_weapons.py`
  — lootandwaifus 유닛 대비 누락 dotgg 파일 스캔·수집(슬러그→이름 정확 매칭),
  dotgg 부재 유닛은 `--stub`으로 수동 입력 템플릿. collect-nikke 워크플로에 편입.
```

- [ ] **Step 2: 커밋**

```bash
git add docs/roadmap.md
git commit -m "docs: roadmap - dotgg weapon-stat collection script + manual stub path"
```

- [ ] **Step 3: /document 위임 (메인 세션에서)**

docs-keeper에 기록 위임 — decisions.md: "dotgg 갱신 중단(2026-05) 대응으로 신규 유닛 무기 스탯은 수동 입력 파일(`source: manual`, dotgg 스키마)로 채우기로 결정 (대안이던 제3소스 스크레이핑은 YAGNI 보류)"; insights.md: "dotgg 파일은 파일명이 아니라 내부 url 필드로 색인됨 / 수동 스텁은 미입력 필드를 생략해야 함(빈 문자열이면 `int('')` 크래시)".

---

## Self-Review 결과

- **스펙 커버리지:** 스크립트(스캔·해석·수집·스텁) = Task 1–3, 수동 파일 규약 = Task 1(`make_stub`)+3, collect-nikke 갱신 = Task 4, 문서 = Task 5, 오류 처리(유닛별 보고·계속 진행) = Task 2, 테스트(순수 함수 + fake fetcher) = Task 1–2. 완료 기준 3건 = Task 3. 갭 없음.
- **플레이스홀더:** 없음 (모든 코드/명령/예상 출력 명시).
- **타입 일관성:** `collect()` 결과 키·튜플 형태가 테스트와 구현에서 일치, `make_stub(lw_data, wanted_url)` 시그니처 일치 확인.
