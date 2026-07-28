# 정체성 그룹과 후보 팬아웃의 분리 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `MODE_VARIANTS`가 겸하던 두 질문을 분리해, 애장품(`-signature`) 13쌍이 "같은 캐릭터"로는 묶이되 엔진의 후보 팬아웃에는 절대 들어가지 않게 한다.

**Architecture:** `registry.character_map()`을 신설한다 — 매니페스트의 `data_slug`로 인코딩 슬러그를 묶어 `슬러그 → 소유 캐릭터`를 파생하며, 빌드가 2개 이상인 캐릭터의 슬러그만 담는다. `deck_search`가 `MODE_VARIANTS` 대신 이 맵을 쓰고, `variant_base`/`_no_variant_clash`/`_VARIANT_GROUP`은 `character_of`/`_no_character_clash`/`_CHARACTER_OF`로 개명한다. `MODE_VARIANTS` 자체는 내용 변경 없이 팬아웃 전용으로 남는다.

**Tech Stack:** Python 3 · pytest · FastAPI (백엔드 전용, 프론트 변경 없음)

**Spec:** `docs/superpowers/specs/2026-07-28-identity-vs-candidate-fanout-design.md`

## Global Constraints

- 작업 디렉터리는 워크트리 `.claude/worktrees/identity-vs-fanout`, 브랜치 `worktree-identity-vs-fanout`. 트렁크는 `wip/scaffolding`이며 원격은 없다.
- pytest는 `backend/`에서 실행한다: `cd backend && python -m pytest`.
- **기준선: 백엔드 1519 passed / 3 skipped** (트렁크 `8a1ed2c`에서 실측, 2026-07-28). 이 계획이 추가하는 테스트만큼만 늘어야 하고, 기존 테스트는 하나도 깨지면 안 된다.
- 프론트엔드(`frontend/`)는 이 작업에서 **건드리지 않는다.**
- `MODE_VARIANTS`의 **내용(entries)은 바꾸지 않는다.** 독스트링만 정정한다.
- `VARIANT_BURST_TIERS`와 `SOLE_TIER1_SLUGS`는 이름도 내용도 **그대로 둔다** — 진짜 모드 변형 개념이다.
- 주석은 WHAT/WHY만 쓴다. "예전엔 이랬다"류 변경 이력은 코드 주석에 쓰지 않는다.
- 커밋 메시지는 영문, 본문은 왜 그렇게 했는지를 적는다.

---

### Task 1: `registry.character_map()` + drift 방어 테스트

**Files:**
- Modify: `backend/app/skill_rules/registry.py` (파일 끝, `get_skill_value_manifest` 뒤)
- Test: `backend/tests/test_character_map.py` (신규)

**Interfaces:**
- Produces: `app.skill_rules.registry.character_map() -> dict[str, str]` — 슬러그를 그 슬러그가 속한 소유 캐릭터로 보낸다. **빌드가 2개 이상인 캐릭터의 슬러그만** 담기므로, 솔로 캐릭터는 키가 없다(호출자가 `.get(slug, slug)`로 처리). 결과는 캐시되어 매번 같은 dict 객체를 돌려준다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_character_map.py`를 새로 만든다:

```python
"""Drift guard for the identity table (registry.character_map()).

Identity is derived from each manifest's `data_slug`, a field whose stated job
is naming the data source. That field already names the character every build
is collected from, which is why the derivation works - but it means a
data-sourcing change could redraw identity silently. These tests pin the
grouping so it cannot.
"""
from collections import defaultdict

from app.skill_rules.registry import (ENCODED_SLUGS, MODE_VARIANTS,
                                      character_map, get_skill_value_manifest)


def _groups():
    """slug -> [slugs], grouped the way character_map() is derived."""
    by_character = defaultdict(list)
    for slug in ENCODED_SLUGS:
        manifest = get_skill_value_manifest(slug) or {}
        by_character[manifest.get("data_slug", slug)].append(slug)
    return {c: slugs for c, slugs in by_character.items() if len(slugs) > 1}


def test_the_table_holds_exactly_the_multi_build_characters():
    groups = _groups()
    expected = {slug: character
                for character, slugs in groups.items() for slug in slugs}
    assert character_map() == expected
    # A solo character is deliberately absent: `.get(slug, slug)` already names
    # her, and keeping the table small keeps the seat-exclusion check cheap.
    assert "crown" not in character_map()


def test_every_mode_variant_candidate_maps_to_its_base():
    # The fan-out table's own groups are a subset of identity: the candidates a
    # base fans out to are builds of that base's character.
    encoded = set(ENCODED_SLUGS)
    for base, variants in MODE_VARIANTS.items():
        for variant in variants:
            if variant in encoded:
                assert character_map()[variant] == base


def test_every_favorite_item_build_maps_to_its_base_character():
    encoded = set(ENCODED_SLUGS)
    pairs = {s: f"{s}-signature" for s in encoded if f"{s}-signature" in encoded}
    assert len(pairs) == 13, (
        "expected 13 encoded base/-signature pairs; a new Favorite Item build "
        f"landed or one was removed - got {sorted(pairs)}"
    )
    for base, signature in pairs.items():
        assert character_map()[signature] == base
        assert character_map()[base] == base


def test_the_grouping_is_the_expected_seventeen_characters():
    # The whole table, pinned. A change here is either a new multi-build unit
    # (update this list) or a data_slug that drifted away from naming the
    # character (fix the manifest).
    assert sorted(_groups()) == [
        "bready", "cinderella-crystal-wave", "diesel-winter-sweets", "drake",
        "flora", "helm", "julia", "laplace", "miranda", "moran", "phantom",
        "privaty", "rapi-red-hood", "rosanna", "sugar", "tove", "zwei",
    ]
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_character_map.py -v`
Expected: 4개 전부 FAIL — `ImportError: cannot import name 'character_map'`

- [ ] **Step 3: 최소 구현을 넣는다**

`backend/app/skill_rules/registry.py`의 **맨 끝**(`get_skill_value_manifest` 정의 뒤)에 추가한다:

```python
_character_map_cache = None


def character_map():
    """Slug -> the one OWNED CHARACTER whose build it is, for every slug whose
    character has more than one encoded build.

    This is the IDENTITY table: it answers "may these two hold a seat at the
    same time", and the answer is no for two builds of one character, since the
    player owns her once. A character with a single build is absent because
    `.get(slug, slug)` already names her.

    It is NOT MODE_VARIANTS, which answers the separate question of what the
    engine may CHOOSE between. A Favorite Item build belongs here and must never
    be fanned out: owning the item is a fact about the player, not a choice the
    search gets to make for them.

    Identity comes from the manifest's `data_slug`, which already names the
    character a build's data is collected from; test_character_map pins the
    grouping so a data-sourcing change cannot redraw it silently.
    """
    global _character_map_cache
    if _character_map_cache is None:
        by_character = defaultdict(list)
        for slug in ENCODED_SLUGS:
            manifest = get_skill_value_manifest(slug) or {}
            by_character[manifest.get("data_slug", slug)].append(slug)
        _character_map_cache = {
            slug: character
            for character, slugs in by_character.items() if len(slugs) > 1
            for slug in slugs
        }
    return _character_map_cache
```

`defaultdict`가 아직 임포트되어 있지 않으면, `registry.py` 아래쪽의 `import importlib` / `import pkgutil` 블록 옆에 `from collections import defaultdict`를 추가한다.

**주의:** 이 함수는 반드시 지연 생성이어야 한다. `get_skill_value_manifest`가 `pkgutil`로 패키지 전체를 스캔하므로, 모듈 임포트 시점에 호출하면 `registry` 자신이 스캔 대상이 된다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_character_map.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/tests/test_character_map.py
git commit -m "Add character_map(), the identity table MODE_VARIANTS was standing in for"
```

---

### Task 2: `deck_search`를 새 맵으로 바꾸고 `variant` 이름을 `character`로 개명

**Files:**
- Modify: `backend/app/deck_search.py:26-53` (임포트·맵·두 함수) + 주석 12곳
- Modify: `backend/app/deck_allocation.py:19` (임포트) + 사용처 15곳 + 주석
- Modify: `backend/app/surrogate.py:15,99`
- Modify: `backend/app/skill_rules/bready.py:19` (주석 한 줄)
- Modify: `scripts/measure_thin_draft.py:29,61,62`
- Test: `backend/tests/test_deck_search.py` (monkeypatch 이름 11곳 + 신규 테스트 2개)

**Interfaces:**
- Consumes: `registry.character_map()` (Task 1)
- Produces: `deck_search.character_of(slug) -> str` · `deck_search._no_character_clash(units) -> bool` · 모듈 상수 `deck_search._CHARACTER_OF`(테스트가 monkeypatch하는 지점)

- [ ] **Step 1: 실패하는 회귀 테스트를 쓴다**

`backend/tests/test_deck_search.py`에 추가한다(`test_mode_variants_never_share_a_deck` 바로 아래):

```python
def test_a_favorite_item_build_is_the_same_character_as_its_base():
    # The Favorite Item is equipment on one owned unit, so her base and
    # -signature encodings are two builds of one character and cannot both hold
    # a seat. They are NOT candidates the engine may choose between - owning the
    # item is settled before the search runs.
    from app import deck_search

    assert deck_search.character_of("miranda-signature") == "miranda"
    assert deck_search.character_of("miranda") == "miranda"
    assert not deck_search._no_character_clash(
        [FakeUnit("miranda", 1), FakeUnit("miranda-signature", 1)])


def test_a_slug_with_no_sibling_build_is_its_own_character():
    from app import deck_search

    assert deck_search.character_of("crown") == "crown"
    assert deck_search._no_character_clash([FakeUnit("crown", 2), FakeUnit("blanc", 1)])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_deck_search.py -k "favorite_item_build or no_sibling_build" -v`
Expected: FAIL — `AttributeError: module 'app.deck_search' has no attribute 'character_of'`

- [ ] **Step 3: `deck_search.py:26-53`을 교체한다**

기존 임포트 줄 `from app.skill_rules.registry import MODE_VARIANTS`와 그 아래 `_VARIANT_GROUP` / `variant_base` / `_no_variant_clash` 블록을 통째로 다음으로 바꾼다:

```python
from app.skill_rules.registry import character_map

# candidate slug -> the owned character it is a build of, for the seat-exclusion
# check below. Absent slugs are their own character.
_CHARACTER_OF = character_map()


def character_of(slug):
    """The single OWNED CHARACTER a candidate slug stands for - a mode variant
    and a Favorite Item build alike map to the character they are a build of,
    and every other slug is its own character.

    Anything that must not spend one owned character twice keys on this rather
    than on the slug: a deck's seats (`_no_character_clash` below) and, because
    the player fields all of a raid's decks at once, the whole allocation
    (deck_allocation's peel, bench and hill-climb).
    """
    return _CHARACTER_OF.get(slug, slug)


def _no_character_clash(units):
    seen = set()
    for unit in units:
        character = _CHARACTER_OF.get(unit.slug)
        if character is not None:
            if character in seen:
                return False
            seen.add(character)
    return True
```

`deck_search.py`는 이제 `MODE_VARIANTS`를 전혀 쓰지 않는다 — 남은 등장은 전부 주석이며 Step 5에서 정리한다.

- [ ] **Step 4: 식별자를 기계적으로 치환한다**

```bash
sed -i 's/_VARIANT_GROUP/_CHARACTER_OF/g; s/\bvariant_base\b/character_of/g; s/_no_variant_clash/_no_character_clash/g' \
  backend/app/deck_search.py backend/app/deck_allocation.py backend/app/surrogate.py \
  backend/tests/test_deck_search.py scripts/measure_thin_draft.py
```

치환이 남김없이 됐는지 확인한다 — 출력이 비어야 한다:

```bash
grep -rn "_VARIANT_GROUP\|variant_base\|_no_variant_clash" backend/app backend/tests scripts --include=*.py
```

- [ ] **Step 5: 주석 문구를 정리한다**

sed는 식별자만 바꾼다. 남은 `MODE_VARIANTS` **주석** 문구를 손으로 손질한다. 규칙은 하나다: **정체성을 말하는 자리면 "sibling build"/"the same character"로 바꾸고, 팬아웃(엔진의 선택)을 말하는 자리면 `MODE_VARIANTS`를 그대로 둔다.**

`backend/app/deck_search.py` — **전부 정체성**이므로 12곳 모두 바꾼다. `MODE_VARIANTS sibling` → `sibling build`, `MODE_VARIANTS base` → `character`, `cross-tier MODE_VARIANTS sibling` → `cross-tier sibling build`. `VARIANT_BURST_TIERS`를 가리키는 부분은 그대로 둔다(그건 실제로 모드 변형 얘기다). 대상 줄: 205, 346, 390, 412, 415, 452, 463, 495, 514, 540, 576, 646.

`backend/app/deck_allocation.py` — **갈린다.**
- 정체성이라 바꿀 곳: 4행(모듈 독스트링의 `MODE_VARIANTS candidates still holds at most one seat` → `sibling builds still hold at most one seat`), 37행, 83행. 4행의 `(see deck_search's \`variant_base\`)`는 `(see deck_search's \`character_of\`)`로 이미 sed가 바꿨다.
- **그대로 둘 곳**: 44행(`_seed_choices`의 "여러 모드로 모델링 — 엔진이 고른다"), 189행, 230행, 321행. 이 넷은 진짜로 팬아웃/`alternatives` 얘기다.

`backend/app/skill_rules/bready.py:19` — 문장이 `MODE_VARIANTS`로 팬아웃된다는 얘기이므로 `MODE_VARIANTS`는 남기고, sed가 바꾼 `_no_character_clash`만 그대로 둔다.

`backend/tests/test_deck_search.py` — 주석 속 `_no_variant_clash`는 sed가 처리했다. `MODE_VARIANTS pair`(93행 부근)는 실제로 rapi의 모드 쌍을 가리키므로 남긴다.

- [ ] **Step 6: 테스트를 돌린다**

Run: `cd backend && python -m pytest tests/test_deck_search.py tests/test_deck_allocation.py tests/test_surrogate.py -v`
Expected: 전부 PASS (신규 2개 포함)

- [ ] **Step 7: 스크립트가 아직 임포트되는지 확인한다**

Run: `cd backend && python -c "import sys; sys.path.insert(0, '../scripts'); import ast; ast.parse(open('../scripts/measure_thin_draft.py').read())" && python -m pytest tests/ -q 2>&1 | tail -3`
Expected: 파싱 성공 + 전체 스위트가 기준선 + 신규 6개(Task 1의 4 + Task 2의 2)로 통과

- [ ] **Step 8: 커밋**

```bash
git add backend/app/deck_search.py backend/app/deck_allocation.py backend/app/surrogate.py \
  backend/app/skill_rules/bready.py backend/tests/test_deck_search.py scripts/measure_thin_draft.py
git commit -m "Key seat exclusion on character identity, not on mode variants"
```

---

### Task 3: 애장품 쌍이 후보 팬아웃으로 새지 않음을 못박는다

정체성 표를 넓혔으니, 반대쪽이 넓어지지 않았음을 테스트로 고정한다. 이 테스트들이 이 작업의 안전장치다 — 애장품이 없는 유저에게 엔진이 `-signature` 인코딩을 골라주는 일을 막는다.

**Files:**
- Modify: `backend/app/skill_rules/registry.py:605-616` (`MODE_VARIANTS` 독스트링만)
- Test: `backend/tests/test_user_roster.py` (신규 1개)
- Test: `backend/tests/test_supported_units.py` (신규 1개)
- Test: `backend/tests/test_api_recommend_raid_draft.py` (신규 1개 — `_variant_alternatives`의 호출자를 다루는 파일이다)

**Interfaces:**
- Consumes: Task 1의 `character_map()`, Task 2의 `character_of`

- [ ] **Step 1: 실패할 수 있는 세 테스트를 쓴다**

`backend/tests/test_user_roster.py` 끝에 추가:

```python
def test_a_favorite_item_pair_is_not_fanned_out():
    # Identity and candidate fan-out are different questions. miranda and
    # miranda-signature are one character, but the roster loader must NOT turn
    # one owned Miranda into both: whether the player owns the item is settled
    # data, so offering the -signature encoding would hand them an item's
    # effects they may not have.
    specs, excluded = load_roster([_state("miranda")])
    assert [s.slug for s in specs] == ["miranda"]
    assert excluded == []
    signature_only, _ = load_roster([_state("miranda-signature")])
    assert [s.slug for s in signature_only] == ["miranda-signature"]
```

`backend/tests/test_supported_units.py` 끝에 추가:

```python
def test_a_favorite_item_base_carries_no_candidate_list():
    """`candidates` means "the engine picks among these". A Favorite Item build
    is not a choice the engine makes, so miranda must not advertise her
    -signature encoding as one - even though the two are the same character."""
    units = {u["slug"]: u for u in supported_units()}
    assert "candidates" not in units["miranda"]
    assert "candidates" not in units["miranda-signature"]
```

`backend/tests/test_api_recommend_raid_draft.py` 끝에 추가:

```python
def test_variant_alternatives_omits_favorite_item_pairs():
    # A drafted seat naming `miranda` is a concrete spec, not an ambiguous one:
    # there is no mode for the engine to settle. Only a base the roster loader
    # fans out (a MODE_VARIANTS base) travels with alternatives.
    from app.api import _variant_alternatives
    from app.user_roster import load_roster
    from tests.test_user_roster import _state

    specs, _ = load_roster([_state("miranda"), _state("miranda-signature"),
                            _state("bready")])
    _by_slug, alternatives = _variant_alternatives(specs)
    assert "miranda" not in alternatives
    assert set(alternatives) == {"bready"}
```

- [ ] **Step 2: 돌려서 상태를 확인한다**

Run: `cd backend && python -m pytest tests/test_user_roster.py tests/test_supported_units.py -k "favorite_item" -v`
Expected: PASS. **여기서 통과하는 것이 정상이다** — Task 1·2가 팬아웃을 건드리지 않았음을 증명하는 회귀 테스트이기 때문이다. 하나라도 FAIL하면 Task 1이나 2가 팬아웃을 오염시킨 것이므로 멈추고 원인을 찾는다.

- [ ] **Step 3: `MODE_VARIANTS` 독스트링을 정정한다**

`backend/app/skill_rules/registry.py`의 `MODE_VARIANTS` 위 주석(605-610행)을 다음으로 바꾼다. 표의 **내용은 건드리지 않는다**:

```python
# One owned character who yields MULTIPLE deck candidates (Fienn, 2026-07-18/19):
# a pre-battle mode choice (Cinderella: Crystal Wave MG/Snipe) or a formation
# role choice (Rapi: Red Hood B3/B1). The tuple lists every candidate slug the
# roster loader fans the one owned state out to (include the base slug itself
# when it stays a candidate).
#
# This is the FAN-OUT table - what the engine may choose between - and only
# that. It is not the identity table: "may these two hold a seat at once" is
# `character_map()`, which also covers the Favorite Item builds. A build the
# player either owns or does not own is settled data, never a candidate, so it
# belongs there and must never be added here.
```

- [ ] **Step 4: 전체 스위트를 돌린다**

Run: `cd backend && python -m pytest -q 2>&1 | tail -3`
Expected: 기준선 1519 + 신규 9 = **1528 passed / 3 skipped**

- [ ] **Step 5: 커밋**

```bash
git add backend/app/skill_rules/registry.py backend/tests/test_user_roster.py \
  backend/tests/test_supported_units.py backend/tests/test_api_recommend_raid_draft.py
git commit -m "Pin that Favorite Item builds never enter the candidate fan-out"
```

---

### Task 4: 분배가 애장품 쌍을 두 덱에 앉히지 않는지 확인한다

**Files:**
- Test: `backend/tests/test_deck_allocation.py` (신규 1개)

**Interfaces:**
- Consumes: Task 2의 `character_of` (deck_allocation이 이미 쓰고 있다)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_deck_allocation.py`의 `test_peeling_never_spends_one_character_on_two_decks` 바로 아래에 추가한다:

```python
def test_peeling_never_spends_a_favorite_item_character_on_two_decks(monkeypatch):
    """A Favorite Item build and its base are the same owned unit, so the five
    raid decks - fielded simultaneously - can seat her only once. A roster
    holding both encodings (a hand-edited roster.json) must not buy two seats."""
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
        "miranda": 3, "miranda-signature": 3,
    })

    def score(slugs):
        if slugs == {"a1", "a2", "a3", "a4", "miranda"}:
            return 100.0
        if slugs == {"b1", "b2", "b3", "b4", "miranda-signature"}:
            return 90.0
        return 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=2, time_budget_sec=0.0)

    seated = [slug for d in out["decks"] for slug in d["deck"]]
    assert "miranda" in seated                       # the 100-point deck still wins
    assert "miranda-signature" not in seated
    # She is fielded, so her other build is not a benched unit either.
    assert "miranda-signature" not in out["leftover_slugs"]
```

- [ ] **Step 2: 돌린다**

Run: `cd backend && python -m pytest tests/test_deck_allocation.py -k favorite_item -v`
Expected: PASS (Task 2의 수정 덕분). **FAIL이면 Task 2가 `deck_allocation` 경로를 다 덮지 못한 것이다** — `character_of`가 `deck_allocation`의 peel/bench/hill-climb 세 곳에 전부 걸렸는지 확인한다.

- [ ] **Step 3: 이 테스트가 진짜로 결함을 잡는지 확인한다**

통과하는 테스트는 그것만으로는 아무것도 증명하지 않는다. 정체성 표를 **수정 이전 상태**(`MODE_VARIANTS`에서만 파생)로 되돌렸을 때 이 테스트가 실패해야 한다.

임시 파일 `backend/tests/test_mutation_check_tmp.py`를 만든다:

```python
"""Throwaway: proves the Favorite Item allocation test actually bites."""
import app.deck_allocation as da
import app.deck_search as ds
from app.deck_search import BossProfile
from app.skill_rules.registry import MODE_VARIANTS
from tests.test_deck_allocation import patch_scorer, roster_of


def test_it_fails_when_identity_covers_only_mode_variants(monkeypatch):
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {v: b for b, vs in MODE_VARIANTS.items() for v in vs})
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
        "miranda": 3, "miranda-signature": 3,
    })

    def score(slugs):
        if slugs == {"a1", "a2", "a3", "a4", "miranda"}:
            return 100.0
        if slugs == {"b1", "b2", "b3", "b4", "miranda-signature"}:
            return 90.0
        return 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=2, time_budget_sec=0.0)
    seated = [slug for d in out["decks"] for slug in d["deck"]]
    assert "miranda-signature" not in seated
```

Run: `cd backend && python -m pytest tests/test_mutation_check_tmp.py -q`
Expected: **FAIL** — `assert 'miranda-signature' not in seated`. 이게 통과해버리면 테스트가 아무것도 안 잡고 있다는 뜻이니 멈추고 원인을 찾는다.

확인했으면 지운다: `rm backend/tests/test_mutation_check_tmp.py`

- [ ] **Step 4: 임시 파일이 사라졌는지 확인하고 커밋한다**

```bash
git status --short
git add backend/tests/test_deck_allocation.py
git commit -m "Cover the raid allocation against seating one character twice"
```

`git status --short`에 `test_mutation_check_tmp.py`가 남아 있으면 안 된다.

---

### Task 5: 전체 회귀 · 라이브 검증 · 문서

**Files:**
- Modify: `docs/roadmap.md` (해당 To-Do 항목을 완료로)
- Modify: `docs/insights.md` · `docs/decisions.md` (`/document` 경유)

- [ ] **Step 1: 백엔드 전체 스위트**

Run: `cd backend && python -m pytest -q 2>&1 | tail -5`
Expected: **1529 passed / 3 skipped** (기준선 1519 + 신규 10). 숫자가 다르면 실제 값을 기록하고 차이를 설명한다.

- [ ] **Step 2: 실제 로스터로 네 모드 회귀**

`/verify` 스킬로 백엔드를 띄우고 네 경로를 전부 친다: `POST /api/recommend`(단일 덱) · `POST /api/recommend-raid`(전체 분배) · `POST /api/recommend-raid`(드래프트) · `POST /api/evaluate-decks`(고정 편성). 로스터는 실제 로스터 픽스처를 쓴다 — `supported-units`로 만든 로스터는 애장품 쌍이 둘 다 들어가 없는 버그를 보게 된다.

각 응답의 총딜을 이 브랜치 이전(`git stash` 또는 트렁크 체크아웃)과 비교한다. **네 모드 모두 값이 바뀌면 안 된다** — 새 맵은 기존 정의역 위에서 순수 확장이기 때문이다. 달라지면 멈추고 원인을 찾는다.

- [ ] **Step 3: 프론트 무변경 확인**

Run: `git diff --stat wip/scaffolding -- frontend/`
Expected: 출력 없음

- [ ] **Step 4: 로드맵 갱신**

`docs/roadmap.md`의 "정체성 그룹과 후보 팬아웃을 분리" To-Do를 `- [ ]`에서 `- [x]`로 바꾸고, 무엇을 했는지(두 테이블 분리 · `data_slug` 파생 · 개명 · 새 테스트 수 · 최종 기준선)를 항목 본문에 적는다. 기존 항목들의 서술 밀도를 맞춘다.

- [ ] **Step 5: 결정·통찰 기록**

`/document` 스킬로 docs-keeper에 넘긴다. 넘길 내용:
- **결정**: 정체성을 `data_slug` 그룹핑에서 파생하기로 한 것과 그 대안(손으로 쓴 표 · `-signature` 접미사 규칙), 그리고 이 선택이 지불하는 결합 비용과 그 방어선(drift 테스트).
- **통찰**: 한 테이블이 두 질문에 답하면, 새 항목을 "추가하는" 처방이 반대쪽에 조용한 결함을 만든다 — 애장품 쌍을 `MODE_VARIANTS`에 넣었으면 없는 아이템의 효과를 유저에게 줬을 것이다.

- [ ] **Step 6: 커밋**

```bash
git add docs/
git commit -m "Docs: record the identity/fan-out split and its drift guard"
```

- [ ] **Step 7: 트렁크로 머지**

`superpowers:finishing-a-development-branch` 스킬을 따른다. 트렁크는 `wip/scaffolding`, 원격은 없다.
