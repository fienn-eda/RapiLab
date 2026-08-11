# 유니온레이드 레벨보정 해제 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유니온 레이드 화면이 레벨 400으로 정규화된 스탯 대신 계정 싱크로 레벨로 조립한 실제 스탯으로 딜을 재게 한다.

**Architecture:** 싱크로 레벨(`outpost_info.synchro_level`)을 북마크릿부터 백엔드 조립기까지 날라, 조립기가 유닛마다 스탯 두 벌(`raid400` + `actual`)을 내게 한다. 어느 벌을 쓸지는 요청의 `stat_basis` 필드가 정하고, 유니온 탭만 `"actual"`을 보낸다. 실제 스탯이 없으면 폴백하지 않고 422로 거절한다.

**Tech Stack:** Python 3 / FastAPI / Pydantic / pytest (backend) · React + TypeScript + Vite / vitest (frontend)

## Global Constraints

- 설계 근거는 `docs/superpowers/specs/2026-08-11-union-raid-actual-stats-design.md`. 이 계획의 절 번호(§N)는 그 문서를 가리킨다.
- **백엔드 테스트는 반드시 `backend/`에서 돌린다.** 루트에서는 `No module named 'app'`으로 수집이 깨진다.
- 백엔드 python: `C:/Users/fienn/anaconda3/python.exe`.
- **프론트 의존성은 이 워크트리에 없다.** 처음 한 번 `npm --prefix frontend ci`.
- 프론트 테스트: `npm --prefix frontend test -- <경로>` (= `vitest run <경로>`).
- **`npm test`는 타입을 안 본다.** 프론트를 만진 태스크는 끝에 `npx --prefix frontend tsc -b --noEmit frontend`를 따로 돌린다(`--prefix`는 tsc 실행파일 위치, 맨 뒤 `frontend`는 tsconfig 경로다).
- 용어: **싱크로 레벨**은 게임의 싱크로 디바이스 레벨, **동기화**는 앱이 blablalink에서 로스터를 읽어오는 일. 코드와 문구에서 섞지 않는다.
- 주석은 무엇을·왜만 쓴다. "예전에는 이랬다"류 변경 이력을 코드에 남기지 않는다.
- 커밋 메시지는 한국어 한 줄, 무엇을 왜 바꿨는지.

## File Structure

| 파일 | 책임 | 태스크 |
|---|---|---|
| `backend/app/roster_assembly.py` | 유닛 하나를 임의 레벨로 조립하는 헬퍼 + `raid400`/`actual` 두 벌 출력 | 1 |
| `backend/tests/test_roster_assembly.py` | 조립기 동작(두 벌·싱크로 레벨 적용·없을 때) | 1 |
| `backend/tests/test_stat_model_at_any_level.py` (신규) | 모델이 임의 레벨에서 옳다는 픽스처 대조 | 2 |
| `backend/app/blablalink_api.py` | 서버 직접 fetch 경로에서 `synchro_level` 꺼내기 | 3 |
| `backend/app/api.py` | `AssembleRosterRequest` 필드 · `stat_basis` 필드 · 실제 스탯 없을 때 422 | 3, 5 |
| `backend/app/user_roster.py` | `base_stats`를 어느 벌로 만들지 고르기 | 5 |
| `frontend/src/lib/bookmarklet.ts` | 북마크릿 소스가 `synchro_level`을 싣는다 | 4 |
| `frontend/src/hooks/useBookmarkletImport.ts` | payload를 받아 그대로 넘긴다 | 4 |
| `frontend/src/api/assembleRoster.ts` | 요청 타입 | 4 |
| `frontend/src/types/evaluate.ts` | 유니온 요청 wire 타입 | 6 |
| `frontend/src/components/UnionRaidPanel.tsx` | `stat_basis` 전송 · 실제 스탯 없으면 제출 차단 | 6 |
| `frontend/src/lib/helpText.ts` | 차단 안내 문구 | 6 |

**태스크 순서:** 1 → 3 → 4 (배관) → 5 → 6. 2는 어디서든 독립적으로 할 수 있다.

**중간 상태에 대해:** 태스크 1이 끝나도 실제로는 `actual`이 만들어지지 않는다 — 태스크 3·4가 값을 날라주기 전까지 `synchro_level`이 도착하지 않기 때문이다. 태스크 1의 테스트는 raw에 직접 값을 넣어 검증하므로 그래도 독립적으로 초록이다. 태스크 5까지 끝나도 프론트는 여전히 400으로 동작한다(기본값이 `raid400`). 6에서 처음으로 화면이 바뀐다.

---

### Task 1: 조립기가 싱크로 레벨로 스탯 두 벌을 낸다

**Files:**
- Modify: `backend/app/roster_assembly.py` (`assemble_unit`, `assemble_roster`)
- Test: `backend/tests/test_roster_assembly.py`

**Interfaces:**
- Produces: `assemble_unit(tables, entry, owned, detail, research, assume_cube_level=None, synchro_level: int | None = None) -> dict` — 반환 dict에 `raid400`은 항상, `actual`은 `synchro_level`이 있을 때만.
- Produces: `assemble_roster`가 `raw["synchro_level"]`(옵셔널)을 읽는다. 시그니처는 그대로.

- [ ] **Step 1: 실패하는 테스트 세 개를 쓴다**

`backend/tests/test_roster_assembly.py` 끝에 추가. `test_fetch_then_assemble_end_to_end`가 쓰는 raw 모양을 그대로 빌려 쓴다.

```python
def _rapi_raw(**extra):
    """The end-to-end test's payload, reusable. Rapi: Red Hood at lv 1 - low
    enough that a synchro level of 668 cannot be confused with her own level."""
    raw = {
        "owned": [{"name_code": 5129, "lv": 1, "core": 6, "grade": 3}],
        "character_details": [{"name_code": 5129, "grade": 3, "core": 6,
                               "attractive_lv": 40, "harmony_cube_lv": 0,
                               "favorite_item_tid": 0, "favorite_item_lv": 0,
                               "skill1_lv": 10, "skill2_lv": 10, "ulti_skill_lv": 10}],
        "recycle_room_researches": [
            {"tid": 1001, "lv": 170}, {"tid": 1101, "lv": 190}, {"tid": 1201, "lv": 150},
        ],
    }
    raw.update(extra)
    return raw


def test_synchro_level_produces_a_second_stat_set(tables):
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    units, _ = assemble_roster(tables, directory, _rapi_raw(synchro_level=668))

    u = units[0]
    assert set(u["actual"]) == {"hp", "atk", "def"}
    assert u["actual"]["def"] == 0
    # The union stats are the SAME unit at a higher level, so they must exceed
    # the level-400 set rather than merely differ from it.
    assert u["actual"]["atk"] > u["raid400"]["atk"]
    assert u["actual"]["hp"] > u["raid400"]["hp"]


def test_the_synchro_level_overrides_the_units_own_level(tables):
    """A Nikke left out of the synchro device sits at lv 1, but fights union
    content at the synchro level - the player swaps her in (design §1). So her
    `actual` must be built from 668, not from the 1 the roster reports."""
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    units, _ = assemble_roster(tables, directory, _rapi_raw(synchro_level=668))
    at_synchro = units[0]["actual"]["atk"]

    # Same account, same unit, but now the device level is 400: the two must
    # differ, which is only true if the level argument is what drives it.
    units_400, _ = assemble_roster(tables, directory, _rapi_raw(synchro_level=400))
    assert units_400[0]["actual"]["atk"] == units_400[0]["raid400"]["atk"]
    assert at_synchro > units_400[0]["actual"]["atk"]


def test_without_a_synchro_level_no_actual_stats_are_invented(tables):
    """An old bookmarklet sends no synchro level. The sync must still work -
    raid400 is level-independent of it - and simply carry no `actual`."""
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    units, _ = assemble_roster(tables, directory, _rapi_raw())

    assert "actual" not in units[0]
    assert units[0]["raid400"]["atk"] > 0
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_roster_assembly.py -k synchro -v`
Expected: 3 FAILED — `KeyError: 'actual'` (앞 둘), 세 번째는 `assert "actual" not in units[0]`이 통과해 **PASS**할 수 있다. 세 번째가 지금 초록인 것은 정상이다: 기능이 없어서 통과하는 가드이므로, Step 5에서 구현을 넣은 뒤 **`synchro_level` 전달을 일부러 끊어** 빨개지는지 확인한다.

- [ ] **Step 3: 레벨을 받는 헬퍼를 뽑는다**

`roster_assembly.py`에서 `_gear_hp` 아래, `assemble_unit` 위에 추가:

```python
def _stats_at_level(tables, inp: dict, research: dict, level: int) -> dict:
    """One unit's ATK/HP at `level`, in the wire shape.

    Solo raid normalizes every account to 400; union raid fights at the
    account's synchro level. Those two are the only callers, and the level is
    the only thing that differs between them.
    """
    atk = sa.assemble_atk(tables, character_class=inp["class"], level=level,
                          grade=inp["grade"], core=inp["core"],
                          affinity_flat=sa.affinity_atk(
                              tables, inp["class"], inp["attractive_lv"]),
                          research_flat=sa.corporation_atk(
                              tables, inp["corporation"], research),
                          extra_flat=_gear_atk(tables, inp))
    hp = sa.assemble_hp(tables, character_class=inp["class"], level=level,
                        grade=inp["grade"], core=inp["core"],
                        affinity_flat_hp=sa.affinity_hp(
                            tables, inp["class"], inp["attractive_lv"]),
                        research_flat_hp=sa.research_hp(
                            tables, inp["class"], research),
                        extra_flat_hp=_gear_hp(tables, inp))
    # DEF is not modelled - no caller reads it (stat_assembly's module docstring).
    return {"hp": round(hp), "atk": round(atk), "def": 0}
```

- [ ] **Step 4: `assemble_unit`이 헬퍼를 두 번 쓰게 한다**

`assemble_unit`의 시그니처에 `synchro_level`을 더하고, 본문 앞머리의 `atk = ...` / `hp = ...` 두 블록을 지운다. `return` 문을 아래처럼 바꾼다 — `raid400` 값의 출처만 헬퍼로 옮기고 나머지 키는 그대로다.

```python
def assemble_unit(tables, entry: dict, owned: dict, detail: dict, research: dict,
                  assume_cube_level: int | None = None,
                  synchro_level: int | None = None) -> dict:
    inp = extract_inputs(entry, owned, detail, assume_cube_level)
    unit = {
        "name_en": inp["name_en"],
        "resource_id": inp["resource_id"],
        # Not consumed by the simulation - already folded into the stat sets -
        # but the UI shows them so the user can confirm their roster imported
        # correctly.
        "grade": inp["grade"],
        "core": inp["core"],
        # Ownership, not a stat: a dual-slot unit's Favorite Item swaps in a
        # different skill encoding ("-signature"), so the frontend needs to know
        # per user rather than consult a hand-maintained list. The stat effect
        # of the item is already folded into the stat sets above.
        "favorite_item": sa.owns_favorite_item(inp["favorite_item_tid"]),
        # The item's flat ATK/HP is already folded in; this is its SKILL, which
        # is a separate damage source the engine reads per unit
        # (collectible_effects). `favorite_item` above stays - it answers a
        # different question, namely which skill encoding to use.
        "collectible": {
            "tid": inp["favorite_item_tid"],
            "level": inp["favorite_item_lv"],
        },
        "raid400": _stats_at_level(tables, inp, research, 400),
        "skill_levels": {
            "skill1": inp["skill1_lv"],
            "skill2": inp["skill2_lv"],
            "burst": inp["ulti_skill_lv"],
        },
        "overload": assemble_overload(tables, detail),
    }
    # Union raid has no level normalization, so it needs the same unit at the
    # account's synchro level. Absent when the sync did not carry that level -
    # inventing one would be a silent 24% distortion (design §5).
    if synchro_level is not None:
        unit["actual"] = _stats_at_level(tables, inp, research, synchro_level)
    return unit
```

- [ ] **Step 5: `assemble_roster`가 raw에서 싱크로 레벨을 읽어 넘긴다**

`assemble_roster` 본문에서 `research = ...` 줄 다음에 추가하고, `assemble_unit` 호출에 인자를 더한다:

```python
    # The account's synchro device level, when the sync carried it. `or None`
    # also folds a 0 into "absent": level 0 is outside the stat table's 1..1200
    # and would raise rather than produce an honest number.
    synchro_level = raw.get("synchro_level") or None
```

```python
            units.append(assemble_unit(tables, entry, o, d, research,
                                       assume_cube_level, synchro_level))
```

`assemble_roster`의 docstring 끝에 한 줄 덧붙인다:

```
    `raw["synchro_level"]`이 있으면 유닛마다 그 레벨의 `actual` 스탯이 함께 나온다.
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_roster_assembly.py -v`
Expected: 새 테스트 3개 PASS, 기존 테스트 전부 PASS (기존 `test_fetch_then_assemble_end_to_end`의 raw에는 `synchro_level`이 없어 키 집합 단언이 그대로 맞는다).

- [ ] **Step 7: 세 번째 가드가 진짜로 재는지 확인한다**

Step 5에서 넣은 `synchro_level` 인자를 잠시 지우고(`assemble_unit(... , assume_cube_level)`) 다시 돌린다.
Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_roster_assembly.py -k synchro -v`
Expected: 앞 두 테스트가 FAIL. 확인했으면 인자를 되돌리고 다시 돌려 전부 PASS.

- [ ] **Step 8: 백엔드 전체를 돌린다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest -q`
Expected: 실패 0.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/roster_assembly.py backend/tests/test_roster_assembly.py
git commit -m "조립기가 싱크로 레벨의 스탯도 낸다 - 유니온은 레벨 400으로 안 싸운다"
```

---

### Task 2: 모델이 임의 레벨에서 옳다는 것을 픽스처로 고정한다

스펙 §3. 새 코드는 없다 — 이 태스크는 **이미 참인 사실에 가드를 건다**. 그 사실 위에 태스크 1이 서 있다.

**Files:**
- Create: `backend/tests/test_stat_model_at_any_level.py`

**Interfaces:**
- Consumes: `stat_assembly`의 `assemble_atk` / `assemble_hp` / `affinity_atk` / `affinity_hp` / `corporation_atk` / `research_hp` / `load_stat_tables`, `roster_assembly._gear_atk` / `_gear_hp`.

**왜 새 파일인가:** 이 테스트는 두 모듈에 걸친다 — 모델은 `stat_assembly`인데 장비 합산은 `roster_assembly._gear_atk`이 갖고 있다. `test_stat_assembly.py`는 `roster_assembly`를 들여오지 않고, `test_roster_assembly.py`는 수집기 스크랩 대조 파일이다. 장비 합산을 테스트 안에서 다시 구현하는 선택지는 **버린다** — 이 저장소에서 자체 구현한 계산은 에러 없이 틀린 숫자를 세 번 냈다. 모듈에게 물어본다.

**기존 테스트와 겹치지 않는다:** `test_stat_assembly.py`의 `test_flat_model_reproduces_every_ungeared_unit`은 **장비 없는 유닛만, 레벨 400, ATK만** 본다. 이 테스트는 **159유닛 전부, 각자의 레벨, ATK와 HP**다.

- [ ] **Step 1: 픽스처가 무엇을 담고 있는지 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -c "import json,pathlib; d=json.loads(pathlib.Path('tests/fixtures/stat_ground_truth.json').read_text(encoding='utf-8')); print(sorted(d['units'][0]['measured'])); print(sorted({u['level'] for u in d['units']}))"`
Expected: `['actual_atk', 'actual_hp', 'raid400_atk', 'raid400_hp']`와 `[1, 668]`. 400레벨 값과 실제 레벨 값이 **둘 다 스크랩**이라는 것이 이 테스트가 순환논법이 아닌 이유다(`scripts/build_stat_ground_truth.py` docstring: "both scraped").

- [ ] **Step 2: 테스트 파일을 만든다**

```python
"""스탯 모델은 솔로레이드의 400레벨 밖에서도 맞는다.

유니온의 모든 수치가 이 위에 선다: 싱크로 레벨로 조립하는 것은 같은 모델에
`level`만 다르게 넣는 것이다. 픽스처의 `actual_*`는 ShiftyPad가 각 니케의 실제
레벨(1 또는 668)로 계산해 화면에 띄운 값을 스크랩한 것이라, 이 대조는 우리
자신이 아니라 게임을 상대로 한다.
"""
import json
from pathlib import Path

import pytest

from app.roster_assembly import _gear_atk, _gear_hp
from app.stat_assembly import (affinity_atk, affinity_hp, assemble_atk,
                               assemble_hp, corporation_atk, load_stat_tables,
                               research_hp)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "stat_ground_truth.json"


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


@pytest.fixture(scope="module")
def fixture_data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_the_fixture_still_carries_levels_other_than_400(fixture_data):
    """이것이 깨지면 아래 테스트는 아무것도 재지 않는다 - 모든 유닛이 400이면
    "임의 레벨에서 맞는다"를 400 하나로 확인하는 셈이 된다."""
    assert {u["level"] for u in fixture_data["units"]} - {400}


def test_the_model_reproduces_the_scraped_stats_at_each_units_own_level(
        tables, fixture_data):
    ranks = fixture_data["account_research"]
    off = []
    for u in fixture_data["units"]:
        atk = assemble_atk(
            tables, character_class=u["class"], level=u["level"],
            grade=u["grade"], core=u["core"],
            affinity_flat=affinity_atk(tables, u["class"], u["attractive_lv"]),
            research_flat=corporation_atk(tables, u["corporation"], ranks),
            extra_flat=_gear_atk(tables, u))
        hp = assemble_hp(
            tables, character_class=u["class"], level=u["level"],
            grade=u["grade"], core=u["core"],
            affinity_flat_hp=affinity_hp(tables, u["class"], u["attractive_lv"]),
            research_flat_hp=research_hp(tables, u["class"], ranks),
            extra_flat_hp=_gear_hp(tables, u))
        if abs(round(atk) - u["measured"]["actual_atk"]) > 1:
            off.append((u["name_en"], "atk", round(atk), u["measured"]["actual_atk"]))
        if abs(round(hp) - u["measured"]["actual_hp"]) > 1:
            off.append((u["name_en"], "hp", round(hp), u["measured"]["actual_hp"]))
    assert off == [], f"units the model misses at their own level: {off[:8]}"
```

- [ ] **Step 3: 통과하는지 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_stat_model_at_any_level.py -v`
Expected: 2 PASSED. (구현이 이미 있으므로 처음부터 초록인 것이 맞다 — 이 태스크는 새 기능이 아니라 이미 참인 사실에 거는 가드다.)

- [ ] **Step 4: 가드가 무엇을 잡는지 확인한다**

두 번째 테스트의 `level=u["level"]` 두 곳을 잠시 `level=400`으로 바꾸고 다시 돌린다.
Expected: FAIL — 레벨 668 유닛 135기가 크게 어긋난다. 확인했으면 되돌린다.

이 단계를 건너뛰면 이 테스트가 실제로 무엇을 재는지 아무도 모른다.

- [ ] **Step 5: 커밋**

```bash
git add backend/tests/test_stat_model_at_any_level.py
git commit -m "스탯 모델이 400레벨 밖에서도 맞는다는 것을 픽스처로 고정한다"
```

---

### Task 3: 싱크로 레벨 배관 — 백엔드

**Files:**
- Modify: `backend/app/blablalink_api.py` (`fetch_roster`)
- Modify: `backend/app/api.py` (`AssembleRosterRequest`)
- Test: `backend/tests/test_blablalink_api.py`, `backend/tests/test_assemble_roster_api.py`

**Interfaces:**
- Produces: `fetch_roster`의 반환 dict에 `"synchro_level": int | None` 키가 늘어난다.
- Produces: `AssembleRosterRequest.synchro_level: int | None = None` — `model_dump()`를 타고 `assemble_roster`의 `raw`로 들어가 태스크 1이 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_blablalink_api.py`의 `FakeCaller` 응답에 `synchro_level`을 넣고 단언을 더한다. 기존 `test_fetch_roster_makes_three_calls_and_bundles_them`의 `GetUserProfileOutpostInfo` 줄을 아래로 바꾸고, 그 테스트 끝에 단언 한 줄을 더한다:

```python
        "GetUserProfileOutpostInfo": {"outpost_info": {
            "recycle_room_researches": [{"tid": 1201, "lv": 170}],
            "synchro_level": 668,
        }},
```

```python
    assert out["synchro_level"] == 668
```

그리고 같은 파일에 새 테스트:

```python
def test_fetch_roster_tolerates_an_outpost_without_a_synchro_level():
    """Only Fienn's account was ever observed - another account's outpost may
    be shaped differently, and a missing synchro level must degrade to "no
    union stats" rather than break the sync."""
    caller = FakeCaller({
        "GetUserCharacters": {"characters": [{"name_code": 5001, "lv": 400, "core": 3, "grade": 3}]},
        "GetUserCharacterDetails": {"character_details": [{"name_code": 5001}]},
        "GetUserProfileOutpostInfo": {"outpost_info": {}},
    })
    out = fetch_roster(caller, "OPENID", area=81)

    assert out["synchro_level"] is None
    assert out["recycle_room_researches"] == []
```

`backend/tests/test_assemble_roster_api.py`에는 엔드포인트가 값을 실제로 쓰는지 보는 테스트를 더한다. **`client`는 fixture가 아니라 모듈 최상단의 `client = TestClient(app)` 변수다** — 인자로 받지 않는다. 헬퍼 `_pilgrim(character_class)`와 `_bare_detail(name_code, **over)`도 그 파일에 이미 있다.

```python
def test_assemble_roster_carries_the_synchro_level_into_actual_stats():
    unit = _pilgrim("Attacker")
    payload = {
        "owned": [{"name_code": unit["name_code"], "lv": 1}],
        "character_details": [_bare_detail(unit["name_code"], core=0)],
        "recycle_room_researches": [],
    }
    without = client.post("/api/assemble-roster", json=payload).json()["units"][0]
    with_level = client.post(
        "/api/assemble-roster", json={**payload, "synchro_level": 668},
    ).json()["units"][0]

    # No synchro level -> no union stats, and the sync still succeeds.
    assert "actual" not in without
    # With one -> the same unit at 668, which must beat her level-400 numbers.
    assert with_level["actual"]["atk"] > with_level["raid400"]["atk"]
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_blablalink_api.py tests/test_assemble_roster_api.py -v`
Expected: `KeyError: 'synchro_level'`과 `KeyError: 'actual'`로 FAIL.

- [ ] **Step 3: `fetch_roster`가 값을 꺼내게 한다**

`blablalink_api.py`의 `return` 블록을 바꾼다. `outpost_info`를 두 번 파지 않도록 먼저 꺼낸다:

```python
    info = outpost.get("outpost_info") or {}
    return {
        "owned": owned,
        "character_details": detail.get("character_details", []),
        "recycle_room_researches": info.get("recycle_room_researches") or [],
        # The account's synchro device level - what every Nikke fights union
        # content at. `outpost_battle_level` sits next to it and is NOT this.
        "synchro_level": info.get("synchro_level"),
    }
```

- [ ] **Step 4: 요청 모델에 필드를 더한다**

`api.py`의 `AssembleRosterRequest`:

```python
class AssembleRosterRequest(BaseModel):
    """The three raw blablalink payloads the bookmarklet collects, verbatim."""
    owned: list[dict]
    character_details: list[dict]
    recycle_room_researches: list[dict]
    # Optional because an already-installed bookmarklet does not send it: a
    # bookmarklet is frozen at install time, so requiring this would break
    # every existing user's sync. Absent means the roster carries no union
    # stats, which the union tab reports rather than papers over.
    synchro_level: int | None = None
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_blablalink_api.py tests/test_assemble_roster_api.py -v`
Expected: 전부 PASS.

- [ ] **Step 6: 백엔드 전체를 돌린다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest -q`
Expected: 실패 0.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/blablalink_api.py backend/app/api.py backend/tests/test_blablalink_api.py backend/tests/test_assemble_roster_api.py
git commit -m "싱크로 레벨을 outpost_info에서 꺼내 조립기까지 나른다"
```

---

### Task 4: 싱크로 레벨 배관 — 프론트 (북마크릿 포함)

**Files:**
- Modify: `frontend/src/lib/bookmarklet.ts` (`collectSource`의 `servers.push`)
- Modify: `frontend/src/hooks/useBookmarkletImport.ts` (`ServerPayload`, `importServer`)
- Modify: `frontend/src/api/assembleRoster.ts` (`RawRosterPayload`)
- Test: `frontend/src/lib/bookmarklet.test.ts`, `frontend/src/hooks/useBookmarkletImport.test.ts`

**Interfaces:**
- Consumes: 태스크 3의 `AssembleRosterRequest.synchro_level`.
- Produces: 북마크릿 payload의 `servers[]` 원소에 `synchro_level?: number`.

- [ ] **Step 1: 의존성을 깐다 (이 워크트리에서 처음 한 번)**

Run: `npm --prefix frontend ci`

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`frontend/src/lib/bookmarklet.test.ts`에 추가:

```ts
  it('싱크로 레벨을 outpost_info에서 꺼내 싣는다', () => {
    // 유니온은 레벨 보정이 없어 이 값이 곧 전투 레벨이다. 옆에 있는
    // outpost_battle_level은 다른 값이므로 이름을 정확히 고정한다.
    expect(source).toContain('synchro_level')
    expect(source).not.toContain('outpost_battle_level')
  })
```

`frontend/src/hooks/useBookmarkletImport.test.ts`에 추가 — 이 파일이 이미 쓰는 렌더/목 방식을 그대로 따르되, `assembleRoster`가 받은 인자를 확인한다:

```ts
  it('서버 payload의 synchro_level을 조립 요청에 실어 보낸다', async () => {
    // 이 값이 없으면 백엔드가 실제 레벨 스탯을 만들 수 없고, 유니온 탭이 막힌다.
    // 훅은 값을 해석하지 않고 나르기만 한다.
    ...  // 이 파일의 기존 테스트가 쓰는 셋업을 그대로 쓰고, servers[0]에
         // synchro_level: 668을 넣은 뒤 assembleRoster 목의 첫 인자를 본다
    expect(vi.mocked(assembleRoster).mock.calls[0][0]).toMatchObject({ synchro_level: 668 })
  })
```

**주의:** 이 파일의 기존 테스트를 먼저 읽고 셋업(목 대상, 인박스 payload 모양, 렌더 헬퍼)을 그대로 재사용한다. 새 셋업을 발명하지 않는다.

- [ ] **Step 3: 실패를 확인한다**

Run: `npm --prefix frontend test -- src/lib/bookmarklet.test.ts src/hooks/useBookmarkletImport.test.ts`
Expected: 두 새 테스트 FAIL.

- [ ] **Step 4: 북마크릿 소스가 값을 싣게 한다**

`bookmarklet.ts`의 `servers.push({...})` 한 줄에서 `recycle_room_researches:` 뒤에 더한다:

```js
,synchro_level:(outpost.outpost_info||{}).synchro_level
```

- [ ] **Step 5: 훅이 값을 나르게 한다**

`useBookmarkletImport.ts`의 `ServerPayload`에 필드를 더한다:

```ts
  /** 계정의 싱크로 디바이스 레벨. 옛 북마크릿에는 없는 필드다 - 없으면 백엔드가
   *  실제 레벨 스탯을 만들지 않고, 유니온 탭이 그 사실을 알린다. */
  synchro_level?: number
```

`importServer`의 `assembleRoster({...})` 호출에 한 줄 더한다:

```ts
        synchro_level: server.synchro_level,
```

`isServerPayload`는 **건드리지 않는다** — 이 필드를 검사하면 옛 북마크릿 payload가 통째로 거절된다. `nickname_error`가 같은 이유로 검사에서 빠져 있다.

- [ ] **Step 6: 요청 타입에 필드를 더한다**

`api/assembleRoster.ts`의 `RawRosterPayload`:

```ts
  /** 계정의 싱크로 디바이스 레벨. 백엔드가 이 레벨로 유니온용 스탯을 조립한다. */
  synchro_level?: number
```

- [ ] **Step 7: 통과를 확인한다**

Run: `npm --prefix frontend test -- src/lib/bookmarklet.test.ts src/hooks/useBookmarkletImport.test.ts`
Expected: 전부 PASS.

- [ ] **Step 8: 타입체크**

Run: `npx --prefix frontend tsc -b --noEmit frontend`
Expected: 오류 0.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/lib/bookmarklet.ts frontend/src/lib/bookmarklet.test.ts frontend/src/hooks/useBookmarkletImport.ts frontend/src/hooks/useBookmarkletImport.test.ts frontend/src/api/assembleRoster.ts
git commit -m "북마크릿이 싱크로 레벨을 함께 보낸다 - 옛 북마크릿은 그대로 동작한다"
```

---

### Task 5: 요청이 어느 스탯으로 잴지 말한다

**Files:**
- Modify: `backend/app/user_roster.py` (`load_nikke_spec`, `load_roster`)
- Modify: `backend/app/api.py` (`RecommendRequest`, `EvaluateDecksRequest`, 세 `_*_sync`)
- Test: `backend/tests/test_user_roster.py`(없으면 생성), `backend/tests/test_api_stat_basis.py`(생성)

**Interfaces:**
- Produces: `load_roster(states, data_dir=DATA_DIR, stat_basis: str = "raid400")`, `load_nikke_spec(state, data_dir=DATA_DIR, slug_override=None, stat_basis: str = "raid400")`.
- Produces: `RecommendRequest.stat_basis` / `EvaluateDecksRequest.stat_basis`, 타입 `Literal["raid400", "actual"]`, 기본 `"raid400"`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_api_stat_basis.py`를 새로 만든다. `client`는 `test_assemble_roster_api.py`와 같은 방식(모듈 최상단 변수)으로 만든다.

```python
"""stat_basis: 어느 스탯 벌로 딜을 잴지 요청이 정한다 (설계 §4, §5)."""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def _unit(slug, **extra):
    """A minimal valid UserNikkeState body for `slug`, level-400 stats only."""
    state = {
        "character_slug": slug, "level": 400,
        "hp": 1_000_000, "atk": 100_000, "def_": 0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        "overload_options": [],
    }
    state.update(extra)
    return state


def test_actual_basis_is_rejected_when_a_unit_has_no_real_level_stats():
    """400 값으로 폴백하면 유닛 간 상대 ATK가 최대 24% 뒤틀린다(설계 §5).
    그래서 근사하지 않고 거절한다."""
    response = client.post("/api/evaluate-decks", json={
        "roster": [_unit("drake")],
        "decks": [],
        "stat_basis": "actual",
    })

    assert response.status_code == 422
    assert "drake" in response.json()["detail"]


def test_the_rejection_names_only_the_units_that_are_missing():
    response = client.post("/api/evaluate-decks", json={
        "roster": [_unit("drake", actual_atk=300_000, actual_hp=3_000_000),
                   _unit("blanc")],
        "decks": [],
        "stat_basis": "actual",
    })

    detail = response.json()["detail"]
    assert "blanc" in detail and "drake" not in detail


def test_the_default_basis_does_not_require_real_level_stats():
    """`actual`이 없는 로스터는 지금 되는 곳에서 계속 돼야 한다 - 이 필드의
    기본값이 곧 현행 동작이다."""
    response = client.post("/api/evaluate-decks", json={
        "roster": [_unit("drake")],
        "decks": [],
    })

    # 덱이 비어 어차피 422지만, 그 이유가 스탯이 아니라 덱이어야 한다.
    assert "실제 레벨" not in response.json()["detail"]
```

**슬러그에 대해:** `drake`와 `blanc`은 둘 다 `ENCODED_SLUGS`에 있다(확인함). 거절 검사 자체는 `request.roster`를 그대로 훑으므로 인코딩 여부와 무관하고, 세 번째 테스트도 덱이 비어 있어서 422가 되는 것이라 무관하다 — 읽는 사람이 "인코딩 안 된 슬러그라 걸린 것 아닌가"를 의심하지 않도록 실재하는 슬러그를 쓸 뿐이다.

`backend/tests/test_user_roster.py`에 분기가 실제로 다른 값을 만드는지 보는 테스트를 더한다. 이 파일에는 이미 `_state(slug, **overrides)` 헬퍼가 있다(기본 `atk=60_000.0`, `hp=1_000_000.0`, `def_=3_000.0`).

```python
def test_actual_basis_builds_specs_from_the_real_level_stats():
    """두 기준이 같은 값을 내면 스위치는 죽은 코드다 - 그래서 다름을 잰다."""
    state = _state("drake", actual_atk=300_000.0, actual_hp=9_000_000.0)

    specs_400, _ = load_roster([state])
    specs_actual, _ = load_roster([state], stat_basis="actual")

    assert specs_400[0].base_stats == {"atk": 60_000.0, "def": 3_000.0,
                                       "max_hp": 1_000_000.0}
    # DEF는 0이다: 스탯 모델이 DEF를 내지 않아 동기화된 로스터의 유니온 쪽에는
    # 애초에 값이 없다(설계 §5).
    assert specs_actual[0].base_stats == {"atk": 300_000.0, "def": 0.0,
                                          "max_hp": 9_000_000.0}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_api_stat_basis.py tests/test_user_roster.py -v`
Expected: `TypeError: load_roster() got an unexpected keyword argument 'stat_basis'`, 그리고 422 대신 다른 이유의 응답.

- [ ] **Step 3: `user_roster`가 기준을 받게 한다**

`load_nikke_spec`의 시그니처와 `NikkeSpec(...)`의 `base_stats=` 인자를 바꾼다:

```python
def load_nikke_spec(
    state: UserNikkeState, data_dir: Path = DATA_DIR, slug_override: str | None = None,
    stat_basis: str = "raid400",
) -> NikkeSpec | None:
```

```python
        base_stats=_base_stats(state, stat_basis),
```

그리고 `load_nikke_spec` 위에 헬퍼를 둔다:

```python
def _base_stats(state: UserNikkeState, stat_basis: str) -> dict:
    """Which of the roster's two stat sets this fight is scored with.

    Solo raid normalizes every account to character level 400; union raid has
    no level correction and is fought at the account's synchro level. The
    caller's content decides, so it travels as an argument rather than being
    inferred here. DEF is 0 on the union side for the same reason it is 0 in
    the synced roster - the stat model does not produce one.
    """
    if stat_basis == "actual":
        return {"atk": state.actual_atk, "def": 0.0, "max_hp": state.actual_hp}
    return {"atk": state.atk, "def": state.def_, "max_hp": state.hp}
```

`load_roster`도 기준을 받아 그대로 넘긴다:

```python
def load_roster(states: list[UserNikkeState], data_dir: Path = DATA_DIR,
                stat_basis: str = "raid400"):
    specs, excluded, seen = [], [], set()
    for state in states:
        slugs = MODE_VARIANTS.get(state.character_slug) or (state.character_slug,)
        loaded = [s for s in (load_nikke_spec(state, data_dir, slug_override=slug,
                                              stat_basis=stat_basis)
                              for slug in slugs) if s is not None]
```

- [ ] **Step 4: 요청 모델에 필드를 더한다**

`api.py`의 `RecommendRequest`와 `EvaluateDecksRequest` 양쪽에 같은 줄을 넣는다. `RecommendRaidRequest`는 `RecommendRequest`를 상속하므로 자동으로 딸려온다.

```python
    # 어느 스탯 벌로 잴지. 엔드포인트로 가르지 않는 이유는 /api/recommend-raid가
    # 이름과 달리 솔로 탭의 5덱 배분이기 때문이다 - 컨텐츠와 엔드포인트가 이미
    # 어긋나 있어, 거기 정책을 걸면 유니온 추천이 생기는 날 조용히 틀린다.
    stat_basis: Literal["raid400", "actual"] = "raid400"
```

`Literal`은 이 파일이 이미 `from typing import Literal`로 들여온다.

- [ ] **Step 5: 거절 함수를 만들고 세 곳에서 부른다**

`api.py`의 `_reject_unknown_overload_options` 옆에 둔다:

```python
def _reject_missing_actual_stats(roster: list[UserNikkeState]) -> None:
    """유니온은 싱크로 레벨로 싸우므로 실제 레벨 스탯 없이는 잴 수가 없다.

    400레벨 값으로 대신 재면 유닛 간 상대 ATK가 최대 24% 뒤틀린다(설계 §5) -
    레벨은 base 커브에만 들어가고 장비·큐브·소장품은 레벨과 무관하게 더해지기
    때문이다. 그래서 근사하지 않고 거절한다.
    """
    missing = sorted({s.character_slug for s in roster
                      if s.actual_atk is None or s.actual_hp is None})
    if missing:
        raise HTTPException(
            422,
            "실제 레벨 스탯이 없는 니케가 있어요. 북마크릿을 다시 설치하고 "
            f"로스터를 다시 동기화해 주세요: {', '.join(missing)}",
        )
```

`_recommend_sync`, `_recommend_raid_sync`, `_evaluate_decks_sync` 셋 모두에서 `_reject_unknown_overload_options(request.roster)` 바로 다음 줄에 넣고, `load_roster` 호출에 기준을 넘긴다:

```python
    if request.stat_basis == "actual":
        _reject_missing_actual_stats(request.roster)
    specs, excluded = load_roster(request.roster, stat_basis=request.stat_basis)
```

`_miranda_targets_sync`의 `load_roster(request.roster)`는 **그대로 둔다** — 계산기 탭은 400 기준이다(설계 §8).

- [ ] **Step 6: 통과를 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest tests/test_api_stat_basis.py tests/test_user_roster.py -v`
Expected: 전부 PASS.

- [ ] **Step 7: 기본값이 회귀가 아닌지 전체로 확인한다**

Run: `cd backend && C:/Users/fienn/anaconda3/python.exe -m pytest -q`
Expected: 실패 0. 기존 요청은 `stat_basis`를 안 보내므로 전부 `raid400`으로 떨어져 지금과 같은 수를 낸다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/user_roster.py backend/app/api.py backend/tests/test_api_stat_basis.py backend/tests/test_user_roster.py
git commit -m "요청이 어느 스탯 벌로 잴지 말한다 - 없으면 근사하지 않고 거절한다"
```

---

### Task 6: 유니온 탭이 실제 스탯으로 재고, 없으면 막는다

**Files:**
- Modify: `frontend/src/types/evaluate.ts` (`EvaluateDecksRequest`)
- Modify: `frontend/src/components/UnionRaidPanel.tsx` (`canSubmit`, 안내 렌더)
- Modify: `frontend/src/lib/helpText.ts`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Consumes: 태스크 5의 `stat_basis`.
- Produces: 유니온 요청 본문에 `stat_basis: 'actual'`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`UnionRaidPanel.test.tsx`에 추가. 이 파일의 기존 헬퍼(`nikke(slug)`, `dropOnDeck`, 렌더 셋업)를 그대로 쓴다. `nikke()`가 만드는 상태에는 `actual_*`가 없으므로, **있는 경우를 만들려면 스프레드로 덧붙인다.**

```ts
  it('실제 레벨 스탯이 없으면 제출을 막고 북마크릿 재설치를 안내한다', async () => {
    // 유니온은 싱크로 레벨로 싸운다. 400레벨 값으로 대신 재면 유닛 간 상대
    // ATK가 최대 24% 뒤틀린다 - 그래서 계산을 아예 하지 않는다.
    ...  // 기존 테스트와 같은 방식으로 덱을 채우고 보스를 유효하게 만든 뒤
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
    expect(screen.getByText(/북마크릿/)).toBeInTheDocument()
  })

  it('실제 레벨 스탯이 있으면 막지 않고 stat_basis를 실어 보낸다', async () => {
    // 가드가 늘 막는 것이 아님을 고정한다 - 이게 없으면 "항상 disabled"인
    // 구현도 위 테스트를 통과한다.
    ...  // roster의 각 유닛에 actual_atk / actual_hp를 넣어 렌더
    await userEvent.click(screen.getByRole('button', { name: /인카운터/ }))
    expect(vi.mocked(evaluateDecks).mock.calls[0][0]).toMatchObject({ stat_basis: 'actual' })
  })
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- src/components/UnionRaidPanel.test.tsx`
Expected: 첫 테스트는 버튼이 활성이라 FAIL, 둘째는 `stat_basis` 없음으로 FAIL.

- [ ] **Step 3: 문구를 넣는다**

`helpText.ts`의 `sync` 블록에 더한다. 바로 위 `bookmarkletNoAccount`가 같은 성격(북마크릿 재설치 안내)이라 톤을 맞춘다.

```ts
    /** 유니온 탭이 계산을 막을 때. 동기화만 다시 해서는 안 풀린다 - 옛 북마크릿은
     *  싱크로 레벨을 보내지 않으므로 재설치가 먼저다. */
    unionNeedsActualStats:
      '유니온 레이드는 싱크로 레벨로 싸워요. 지금 로스터에는 그 레벨의 스탯이 없어서 계산할 수 없어요. "동기화 방법"을 열어 북마크릿을 다시 설치한 뒤, 로스터를 다시 동기화해 주세요.',
```

- [ ] **Step 4: wire 타입에 필드를 더한다**

`types/evaluate.ts`의 `EvaluateDecksRequest`:

```ts
export interface EvaluateDecksRequest {
  roster: UserNikkeState[]
  decks: EvaluateDeckInput[]
  /** 유니온은 레벨 보정이 없어 싱크로 레벨로 싸운다. 이 요청은 유니온 탭만
   *  쓰므로 리터럴로 고정한다 - 실수로 솔로 기준을 보낼 자리를 만들지 않는다. */
  stat_basis: 'actual'
}
```

- [ ] **Step 5: 패널이 막고 보낸다**

`UnionRaidPanel.tsx`에서 `effectiveRoster`(현재 160행 근처) **다음에** 판정을 두고, `canSubmit`에 더한다. `canSubmit`이 `effectiveRoster`보다 위에 있으므로 **`canSubmit` 정의를 `effectiveRoster` 아래로 옮긴다**.

```tsx
  // 유니온은 싱크로 레벨로 싸우므로 실제 레벨 스탯이 있어야 잴 수 있다. DEF는
  // 보지 않는다 - 스탯 모델이 DEF를 내지 않아 "없음"과 0을 구분할 수 없다.
  const missingActualStats = useMemo(
    () => effectiveRoster.some((n) => n.actual_atk == null || n.actual_hp == null),
    [effectiveRoster],
  )

  const canSubmit =
    decksFull && allBossesValid && !missingActualStats && evaluation.status !== 'loading'
```

`handleSubmit`의 `evaluation.submit({...})`에 한 줄:

```tsx
      stat_basis: 'actual',
```

제출 버튼이 있는 `recommend-form__actions` 안, 버튼 위에 안내를 렌더한다:

```tsx
                {missingActualStats && <HelpText>{HELP.sync.unionNeedsActualStats}</HelpText>}
```

- [ ] **Step 6: 통과를 확인한다**

Run: `npm --prefix frontend test -- src/components/UnionRaidPanel.test.tsx`
Expected: 전부 PASS.

- [ ] **Step 7: 가드를 떼서 무엇을 재는지 확인한다**

`canSubmit`에서 `!missingActualStats`를 잠시 지우고 다시 돌린다.
Expected: 첫 테스트 FAIL. 확인했으면 되돌린다.

- [ ] **Step 8: 프론트 전체 + 타입 + lint**

Run: `npm --prefix frontend test`
Expected: 실패 0.

Run: `npx --prefix frontend tsc -b --noEmit frontend`
Expected: 오류 0.

Run: `npm --prefix frontend run lint`
Expected: exit 0.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/types/evaluate.ts frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx frontend/src/lib/helpText.ts
git commit -m "유니온 탭이 싱크로 레벨 스탯으로 잰다 - 없으면 막고 북마크릿 재설치를 안내한다"
```

---

### Task 7: 실제 앱에서 확인하고 문서를 갱신한다

브라우저 렌더에서 한 번 보지 않으면 이 저장소는 여러 번 데었다(jsdom 초록이 앱에 대해 아무 말도 하지 않는다).

**Files:**
- Modify: `docs/roadmap.md` (To-Do 항목 체크)
- Modify: `docs/encoded-nikkes.md` — **해당 없음**, 건드리지 않는다

- [ ] **Step 1: 백엔드와 프론트를 띄운다**

`/run` 스킬이나 프로젝트의 `dev.ps1`을 쓴다. 포트 8000에 Fienn의 `--reload` 개발 백엔드가 이미 떠 있을 수 있다 — 그러면 그것을 그대로 쓰고 **죽이지 않는다**.

- [ ] **Step 2: 막히는 쪽을 본다**

동기화하지 않은(또는 옛 북마크릿으로 동기화한) 로스터로 유니온 탭에 들어가 덱을 채우고 보스를 고른다.
Expected: 「인카운터!」가 비활성이고 북마크릿 재설치 안내가 보인다.

- [ ] **Step 3: 통하는 쪽을 본다**

북마크릿을 다시 설치하고 동기화한 뒤 같은 편성을 제출한다.
Expected: 결과가 나오고, **딜 수치가 이전보다 약 3배**다(설계 §9, 중앙값 3.15배).

- [ ] **Step 4: 솔로 탭이 안 변했는지 본다**

같은 로스터로 솔로 탭에서 추천을 한 번 돌린다.
Expected: 수치가 이 작업 전과 같다. 솔로는 400 기준 그대로다.

- [ ] **Step 5: 로드맵을 갱신한다**

`docs/roadmap.md`의 To-Do에 이 작업 항목을 추가하고 체크한다. 2026-08-10 스펙이 "범위 밖으로 남긴다"고 적은 9번째 항목이 이것이므로, 그 문장을 찾아 **이 작업으로 닫혔다는 것을 한 줄로 잇는다**.

- [ ] **Step 6: 커밋**

```bash
git add docs/roadmap.md
git commit -m "로드맵: 유니온 실제 스탯 착륙"
```

---

## Self-Review

**스펙 커버리지**

| 스펙 절 | 태스크 |
|---|---|
| §1 전투 레벨 = 싱크로 레벨 | 1 (조립), 3 (값의 출처) |
| §2 스탯 두 벌 | 1 |
| §2.5 배관 다섯 곳 | 3 (백엔드 둘), 4 (프론트 셋) |
| §3 검증 둘로 나누기 | 1 (규칙), 2 (모델) |
| §4 `stat_basis` | 5 |
| §5 없으면 거절 | 5 (백엔드 422), 6 (프론트 차단·문구) |
| §6 프론트에서 바뀌는 곳 | 4, 6 |
| §7 테스트 목록 | 1, 2, 3, 4, 5, 6에 분산 |
| §8 범위 밖 | 5 Step 5가 미란다 경로를 그대로 두는 것으로 지킨다 |
| §9 사용자에게 보이는 변화 | 7 |

**타입 일관성**

- `synchro_level` — 백엔드 `int | None`, 프론트 `number | undefined`. 이름은 다섯 곳 모두 snake_case `synchro_level`(wire 이름이라 프론트에서도 그대로).
- `stat_basis` — 백엔드 `Literal["raid400", "actual"]`, 프론트 유니온 요청은 리터럴 `'actual'`.
- `actual` — 조립기 출력 키(`raid400`과 나란히), 프론트 `RosterUnit.actual`(이미 존재), wire `actual_hp`/`actual_atk`/`actual_def`(이미 존재).
- 태스크 1이 만드는 `_stats_at_level`은 태스크 2의 테스트가 부르지 않는다(그 테스트는 `stat_assembly`를 직접 부른다) — 의도된 것이다. 모델 검증이 조립기 구현을 거치면 조립기 버그가 모델 검증을 통과시킬 수 있다.

**계획을 쓰며 확인한 것 (추측이 아니다)**

- `test_stat_assembly.py`는 `from app.stat_assembly import (...)`로 심볼을 직접 들여온다 — `sa.` 접두사가 아니다. fixture는 `tables` / `ground_truth` / `ground_truth_ranks` / `identity`.
- `test_assemble_roster_api.py`의 `client`는 **fixture가 아니라 모듈 최상단 변수**다.
- `test_user_roster.py`의 헬퍼는 `_state(slug, **overrides)`이고 기본 스탯은 `atk=60_000.0` / `hp=1_000_000.0` / `def_=3_000.0`, 쓰는 슬러그는 `drake`.
- `drake`·`blanc`은 `ENCODED_SLUGS`에 있고 `anis`·`rapi`는 없다.
- `api.py`는 `from typing import Literal`을 이미 들여온다.
- `UnionRaidPanel.tsx`는 `HelpText`를 이미 들여온다. `canSubmit`은 147행, `effectiveRoster`는 160행 — 태스크 6에서 순서를 바꾼다.
- `UserNikkeState`(프론트)에는 `actual_hp?` / `actual_atk?` / `actual_def?`가 이미 선언돼 있다.
- `test_roster_assembly.py`의 parity 테스트는 `raid400`만 비교하므로 `actual` 추가로 깨지지 않는다.

**남은 위험**

- 태스크 4·6의 프론트 테스트 스니펫은 각 파일의 **기존 셋업을 재사용하라**고 지시하며 일부를 `...`로 남겼다. 이 저장소에서 계획 결함은 거의 전부 "계획이 발명한 셀렉터·픽스처"에서 나왔으므로, 그 자리는 파일을 열어 맞추는 편이 낫다. 무엇을 확인해야 하는지는 각 스니펫에 주석으로 적었다.
- 실기록 캘리브레이션(1.060x·18/25)이 유니온 실제 스탯에서 유효한지는 이 계획이 답하지 않는다(설계 §8).
