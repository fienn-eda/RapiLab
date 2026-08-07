# 레이드 회차 보스 가져오기 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 솔로/유니온 레이드 공지에서 읽은 이번 회차 보스를 카드로 띄우고, 카드를 고르면 약점 속성이 채워지도록 한다.

**Architecture:** 공지 이미지는 앱이 아니라 `/update-raid-bosses` 스킬이 읽어 `data/raid-rotations.json`에 적는다. 백엔드는 그 파일을 검증해 `GET /api/raid-rotations`로 내고, 프론트는 `BossProfileField` 안에 회차 보스 피커를 그린다. 카드를 고르면 **약점 속성만** 들어가고 나머지 필드는 기본값으로 초기화된다.

**Tech Stack:** Python 3 / FastAPI / pydantic v2 / pytest · React 18 / TypeScript / Vite / Vitest / Testing Library

**설계 문서:** `docs/superpowers/specs/2026-08-07-raid-boss-rotation-import-design.md`

## Global Constraints

- **기준선(2026-08-07 실측):** 백엔드 `1967 passed, 3 skipped` · 프론트 `579 passed (58 files)`. 각 태스크 끝에서 이보다 줄면 안 된다.
- **자동으로 채워지는 보스 필드는 약점 속성 하나뿐이다.** 거리·부위파괴·코어피격·2관통·속성저지·방어력·전투시간은 공지에서 유추해 채우지 않는다 (설계 D3).
- **어떤 값도 상속되지 않는다.** 회차를 넘어서도, 직전에 고른 보스에서도. 카드를 고르면 약점 외의 모든 필드는 기본값으로 돌아간다 (설계 D2).
- **`stated`의 내용은 앱이 해석하지 않는다.** 화면에 원문 그대로 렌더링만 한다.
- 주석은 무엇을/왜만 쓴다. "예전엔 이랬다"·"이번에 바꿨다"는 금지 (`.claude/CLAUDE.md`).
- 백엔드 테스트: `cd backend && python3 -m pytest`. 프론트: `cd frontend && npx vitest run`.
- 이 워크트리는 `python3`가 Anaconda 파이썬이다. `python`은 없다.

---

## File Structure

**백엔드**

| 파일 | 책임 |
|---|---|
| `data/raid-rotations.json` | 회차 데이터. 워크플로우가 쓰고 백엔드가 읽는다. |
| `backend/app/elements.py` | `ELEMENTS` 상수 추가 — 5속성 이름을 네 번째로 다시 쓰지 않기 위해. |
| `backend/app/raid_rotations.py` | 파일 로드 + 검증. |
| `backend/app/api.py` | 와이어 모델 3개 + `GET /api/raid-rotations`. |
| `backend/tests/test_raid_rotations.py` | 검증 규칙. |
| `backend/tests/test_api_raid_rotations.py` | 라우트가 파일 내용을 그대로 내는지. |

**프론트**

| 파일 | 책임 |
|---|---|
| `frontend/src/types/raidRotation.ts` | 와이어 타입 + `latestRotationFor`. |
| `frontend/src/api/raidRotations.ts` | 타입 붙은 fetch. |
| `frontend/src/hooks/useRaidRotations.ts` | 마운트 시 1회 조회. |
| `frontend/src/lib/elementIcon.ts` | 속성 아이콘 경로 — 피커와 `BossProfileField`가 같이 쓴다. |
| `frontend/src/components/RaidRotationPicker.tsx` | 보스 카드 목록. 상태 없음, 선택은 prop. |
| `frontend/src/components/BossProfileField.tsx` | 피커 합성 + 선택 시 초기화. |
| `frontend/src/components/RecommendPanel.tsx` | 솔로 회차 배선. |
| `frontend/src/components/UnionRaidPanel.tsx` | 유니온 회차 배선. |
| `frontend/src/App.tsx` | 훅 1회 호출 후 두 패널에 전달. |
| `frontend/src/App.css` | 피커 스타일. |

**워크플로우 / 문서**

| 파일 | 책임 |
|---|---|
| `.claude/skills/update-raid-bosses/SKILL.md` | 공지 URL → 데이터 파일 절차. |
| `docs/roadmap.md` | 착륙 기록. |

---

### Task 1: 회차 데이터 파일과 로더

**Files:**
- Create: `data/raid-rotations.json`
- Modify: `backend/app/elements.py` (파일 끝에 추가)
- Create: `backend/app/raid_rotations.py`
- Test: `backend/tests/test_raid_rotations.py`

**Interfaces:**
- Consumes: `app.paths.data_dir()` — `data/` 디렉터리 경로.
- Produces:
  - `app.elements.ELEMENTS: frozenset[str]` — 5속성 이름.
  - `app.raid_rotations.load_rotations(path: Path | None = None) -> dict` — 검증된 문서.
  - `app.raid_rotations.validate_rotations(doc: dict) -> dict` — 통과하면 `doc` 그대로, 아니면 `ValueError`.

- [ ] **Step 1: 회차 데이터 파일을 쓴다**

`data/raid-rotations.json` — 2026-08-07에 arca.live 한국어 공지 2건을 판독한 값이다.

```json
{
  "schema_version": 1,
  "rotations": [
    {
      "id": "solo-39",
      "raid": "solo",
      "title": "솔로 레이드 39시즌",
      "starts_at": "2026-07-16T12:00:00+09:00",
      "ends_at": "2026-07-23T04:59:00+09:00",
      "source_url": "https://arca.live/b/nikketgv/177017741",
      "source_locale": "ko",
      "read_on": "2026-08-07",
      "bosses": [
        {
          "name": "아일랜드 이터",
          "weakness": "Iron",
          "stated": {
            "보스 속성": "전격",
            "약점 속성": "철갑",
            "스쿼드 추천": "머신건 니케",
            "랩쳐 주요 공격": [
              "아일랜드 이터는 탄막 사격을 통해 전체 니케에게 강력한 피해를 입힙니다. 엄폐하여 공격을 방어하세요.",
              "슬러지 미사일은 다수의 미사일을 발사하여 니케에게 피해를 입힙니다. 발사체를 파괴하여 공격을 방어하세요.",
              "호밍 레이저는 단일 니케에게 강력한 관통 피해를 입힙니다. 저지 부위를 공격해 방어하세요."
            ]
          }
        }
      ]
    },
    {
      "id": "union-2026-07-31",
      "raid": "union",
      "title": "유니온 레이드 7/31",
      "starts_at": "2026-07-31T05:00:00+09:00",
      "ends_at": "2026-08-06T04:59:00+09:00",
      "source_url": "https://arca.live/b/nikketgv/177833660",
      "source_locale": "ko",
      "read_on": "2026-08-07",
      "bosses": [
        {
          "name": "선바스",
          "weakness": "Electric",
          "stated": {
            "등급": "로드 급",
            "약점": "전격",
            "거리": "근거리",
            "설명": [
              "머리에 불길한 꽃을 얹고 있는 지상형 랩쳐.",
              "꽃봉오리 가득 에너지를 모아 앞으로 쏘아댄다."
            ]
          }
        },
        {
          "name": "플레이트",
          "weakness": "Fire",
          "stated": {
            "등급": "로드 급",
            "약점": "작열",
            "거리": "원거리",
            "설명": [
              "에너지 실드를 겹겹이 두르고 있는 공중형 랩쳐.",
              "강한 공격보다는 많은 공격으로 실드를 부숴야 한다."
            ]
          }
        },
        {
          "name": "토커티브",
          "weakness": "Water",
          "stated": {
            "등급": "타이런트 급",
            "약점": "수냉",
            "거리": "원거리",
            "설명": [
              "인간과 같이 사고하고 인간의 말을 하는 랩쳐.",
              "존재 자체가 수수께끼인 개체로, 모든 것이 불명이다."
            ]
          }
        },
        {
          "name": "리빌드 핑거즈",
          "weakness": "Wind",
          "stated": {
            "등급": "로드 급",
            "약점": "풍압",
            "거리": "원거리",
            "설명": [
              "다수의 손가락과 같은 촉수를 지닌 랩쳐.",
              "방심하지 않고, 동족 포식을 하지 못하게만 저지한다면 이겨낼 수 있다."
            ]
          }
        },
        {
          "name": "마테리얼 H",
          "weakness": "Iron",
          "stated": {
            "등급": "타이런트 급",
            "약점": "철갑",
            "거리": "근거리",
            "설명": [
              "일종의 배양 시설.",
              "특수한 부품을 재료로 사용한다."
            ]
          }
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/tests/test_raid_rotations.py`:

```python
"""회차 데이터 파일의 검증 규칙.

파일이 깨졌을 때 조용히 빈 목록이 되면 화면에 피커가 안 그려질 뿐이라 아무도
모른다. 그래서 로드가 터지는 편을 택했고, 아래 테스트들이 어떤 깨짐이 터지는지를
못박는다.
"""
import json

import pytest

from app.elements import ELEMENTS
from app.raid_rotations import load_rotations, validate_rotations


def a_rotation(**overrides):
    doc = {
        "id": "solo-1", "raid": "solo", "title": "솔로 레이드 1시즌",
        "starts_at": "2026-01-01T12:00:00+09:00",
        "ends_at": "2026-01-08T04:59:00+09:00",
        "source_url": "https://example.test/1", "source_locale": "ko",
        "read_on": "2026-01-01",
        "bosses": [{"name": "보스", "weakness": "Iron", "stated": {}}],
    }
    doc.update(overrides)
    return doc


def a_doc(*rotations):
    return {"schema_version": 1, "rotations": list(rotations)}


def test_elements_are_the_five_the_wheel_knows():
    assert ELEMENTS == {"Fire", "Water", "Wind", "Iron", "Electric"}


def test_a_valid_document_comes_back_unchanged():
    doc = a_doc(a_rotation())
    assert validate_rotations(doc) is doc


def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError, match="solo-1"):
        validate_rotations(a_doc(a_rotation(), a_rotation()))


def test_an_unknown_raid_kind_is_rejected():
    with pytest.raises(ValueError, match="ultra"):
        validate_rotations(a_doc(a_rotation(raid="ultra")))


def test_an_unknown_weakness_is_rejected():
    boss = [{"name": "보스", "weakness": "Poison", "stated": {}}]
    with pytest.raises(ValueError, match="Poison"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_boss_with_no_weakness_is_allowed():
    # 무속성 보스가 나오면 약점 칸이 비어야 한다 - 5속성 중 하나를 억지로 고르면
    # 그 순간 없는 약점특효가 붙는다.
    boss = [{"name": "보스", "weakness": None, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_an_unparseable_time_is_rejected():
    with pytest.raises(ValueError, match="7/23"):
        validate_rotations(a_doc(a_rotation(ends_at="7/23 4:59")))


def test_a_rotation_that_ends_before_it_starts_is_rejected():
    with pytest.raises(ValueError, match="solo-1"):
        validate_rotations(a_doc(a_rotation(
            starts_at="2026-01-08T12:00:00+09:00",
            ends_at="2026-01-01T04:59:00+09:00")))


def test_a_missing_start_is_allowed():
    # 본문 텍스트만으로 들어오는 경로에서는 종료 시각만 적혀 있을 수 있다.
    assert validate_rotations(a_doc(a_rotation(starts_at=None)))


def test_the_shipped_file_loads():
    doc = load_rotations()
    assert doc["schema_version"] == 1
    assert {r["id"] for r in doc["rotations"]} >= {"solo-39", "union-2026-07-31"}


def test_the_shipped_union_rotation_has_one_boss_per_element():
    doc = load_rotations()
    union = next(r for r in doc["rotations"] if r["id"] == "union-2026-07-31")
    assert {b["weakness"] for b in union["bosses"]} == ELEMENTS


def test_the_shipped_file_is_the_one_the_app_bundles(tmp_path):
    # 로더의 기본 경로가 paths.data_dir()이어야 얼린 앱에서도 같은 파일을 읽는다.
    from app.paths import data_dir
    assert json.loads((data_dir() / "raid-rotations.json").read_text(encoding="utf-8"))
```

- [ ] **Step 3: 테스트를 돌려 실패를 확인한다**

Run: `cd backend && python3 -m pytest tests/test_raid_rotations.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.raid_rotations'`, 그리고 `ImportError: cannot import name 'ELEMENTS'`

- [ ] **Step 4: `ELEMENTS`를 추가한다**

`backend/app/elements.py` 파일 끝에:

```python
# 5속성의 이름. 순환에서 유도한다 - 목록을 따로 적으면 순환이 바뀌는 날 둘이
# 어긋나고, 어긋난 쪽이 검증에 쓰이면 없는 속성이 통과한다.
ELEMENTS = frozenset(_STRONG_AGAINST)
```

- [ ] **Step 5: 로더를 쓴다**

`backend/app/raid_rotations.py`:

```python
"""이번 회차 레이드 보스. `/update-raid-bosses` 스킬이 공지를 읽어 적고, 보스
설정 화면의 카드 피커가 읽는다.

기계가 읽는 필드는 보스마다 `weakness` 하나뿐이다. 거리·부위파괴 같은 것은
공지가 명시하지 않으므로 `stated`에 원문 그대로 들어가고 앱은 해석하지 않는다
(docs/superpowers/specs/2026-08-07-raid-boss-rotation-import-design.md D3).

파일의 키는 보스 이름이 아니라 (회차, 보스)다. 같은 보스가 시즌마다 다른 속성을
달고 나오므로, 지난 시즌 기록이 이번 시즌 보스에 얹힐 수 있는 구조를 아예 만들지
않는다 (같은 문서 D2).
"""
import json
from datetime import datetime
from pathlib import Path

from app.elements import ELEMENTS
from app.paths import data_dir

RAID_KINDS = frozenset({"solo", "union"})


def _parse_time(value, where):
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{where}: 시각을 읽을 수 없다 - {value!r}") from exc


def validate_rotations(doc):
    """검사를 통과하면 `doc`을 그대로 돌려준다.

    깨진 파일에 대해 빈 목록을 내지 않고 터뜨리는 이유: 회차 데이터가 조용히
    비면 화면에서는 피커가 없는 것과 구별되지 않는다.
    """
    seen = set()
    for rotation in doc["rotations"]:
        rid = rotation["id"]
        if rid in seen:
            raise ValueError(f"회차 id가 중복이다: {rid!r}")
        seen.add(rid)
        if rotation["raid"] not in RAID_KINDS:
            raise ValueError(f"{rid}: 알 수 없는 raid {rotation['raid']!r}")
        starts = _parse_time(rotation.get("starts_at"), rid)
        ends = _parse_time(rotation["ends_at"], rid)
        if starts is not None and starts >= ends:
            raise ValueError(f"{rid}: starts_at이 ends_at보다 늦거나 같다")
        for boss in rotation["bosses"]:
            weakness = boss["weakness"]
            if weakness is not None and weakness not in ELEMENTS:
                raise ValueError(
                    f"{rid}/{boss['name']}: 알 수 없는 약점 {weakness!r}")
    return doc


def load_rotations(path: Path | None = None):
    """번들된 회차 파일을 읽어 검증한다."""
    path = data_dir() / "raid-rotations.json" if path is None else path
    return validate_rotations(json.loads(path.read_text(encoding="utf-8")))
```

- [ ] **Step 6: 테스트를 돌려 통과를 확인한다**

Run: `cd backend && python3 -m pytest tests/test_raid_rotations.py -v`
Expected: PASS (13 tests)

- [ ] **Step 7: 전체 스위트를 돌린다**

Run: `cd backend && python3 -m pytest -q`
Expected: `1980 passed, 3 skipped` (기준선 1967 + 이번 13)

- [ ] **Step 8: 커밋**

```bash
git add data/raid-rotations.json backend/app/elements.py backend/app/raid_rotations.py backend/tests/test_raid_rotations.py
git commit -m "회차 보스 데이터 파일과 로더

공지에서 읽은 값을 (회차, 보스) 키로 담는다. 기계가 읽는 필드는 weakness
하나뿐이고 나머지는 stated에 원문으로 들어간다."
```

---

### Task 2: `GET /api/raid-rotations`

**Files:**
- Modify: `backend/app/api.py` (import 블록, 모델 정의부, `/api/supported-units` 라우트 아래)
- Test: `backend/tests/test_api_raid_rotations.py`

**Interfaces:**
- Consumes: `app.raid_rotations.load_rotations()` (Task 1).
- Produces: `GET /api/raid-rotations` → `{"schema_version": int, "rotations": [...]}`. 프론트 `types/raidRotation.ts`가 이 모양을 그대로 미러한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_api_raid_rotations.py`:

```python
"""GET /api/raid-rotations - 회차 보스 카드가 읽는 표면."""
from fastapi.testclient import TestClient

from app.api import app
from app.raid_rotations import load_rotations

client = TestClient(app)


def get():
    response = client.get("/api/raid-rotations")
    assert response.status_code == 200
    return response.json()


def test_the_route_serves_the_file_as_is():
    # 서버가 회차를 골라 자르지 않는다. 어느 회차를 보여줄지는 화면의 판단이고,
    # 서버가 미리 자르면 과거 회차를 보려는 다음 요구에서 양쪽을 고쳐야 한다.
    assert get() == load_rotations()


def test_every_boss_carries_a_weakness_field():
    for rotation in get()["rotations"]:
        for boss in rotation["bosses"]:
            assert "weakness" in boss


def test_stated_survives_the_wire_untouched():
    # stated는 자유 형식이라 pydantic이 조용히 떨어뜨리기 쉬운 자리다. 공지 원문이
    # 화면까지 그대로 가는지가 이 기능의 요점이므로 값으로 확인한다.
    solo = next(r for r in get()["rotations"] if r["id"] == "solo-39")
    stated = solo["bosses"][0]["stated"]
    assert stated["스쿼드 추천"] == "머신건 니케"
    assert len(stated["랩쳐 주요 공격"]) == 3


def test_a_union_rotation_carries_all_five_bosses():
    union = next(r for r in get()["rotations"] if r["id"] == "union-2026-07-31")
    assert len(union["bosses"]) == 5
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd backend && python3 -m pytest tests/test_api_raid_rotations.py -v`
Expected: FAIL — `assert 404 == 200`

- [ ] **Step 3: 모델과 라우트를 더한다**

`backend/app/api.py`의 import 블록에 (`from app.paths import frontend_dist` 근처, 알파벳 순서 유지):

```python
from app.raid_rotations import load_rotations
```

`BossProfileIn` 정의 아래에 모델 셋:

```python
class RotationBoss(BaseModel):
    """공지가 적은 보스 하나.

    `weakness`만 앱이 해석한다 - 화면이 이 값으로 보스 속성을 역산해 채운다.
    `stated`는 공지 원문이고 렌더링만 된다. 자유 형식인 이유는 솔로 공지와
    유니온 공지가 서로 다른 항목을 적기 때문이다(솔로: 보스 속성·스쿼드 추천·공격
    패턴 / 유니온: 등급·거리).
    """
    name: str
    weakness: Literal["Fire", "Water", "Wind", "Iron", "Electric"] | None = None
    stated: dict[str, str | list[str]] = {}


class RaidRotation(BaseModel):
    id: str
    raid: Literal["solo", "union"]
    title: str
    # 공지 본문이 종료 시각만 적는 경우가 있어 시작은 비어 있을 수 있다.
    starts_at: str | None = None
    ends_at: str
    source_url: str
    # `name`이 한국 서버 표기인지 영문명인지. 읽는 쪽이 알아야 한다.
    source_locale: Literal["ko", "en"]
    read_on: str
    bosses: list[RotationBoss]


class RaidRotationsResponse(BaseModel):
    schema_version: int
    rotations: list[RaidRotation]
```

`supported_units_route` 아래에 라우트:

```python
@app.get("/api/raid-rotations", response_model=RaidRotationsResponse)
def raid_rotations_route() -> RaidRotationsResponse:
    """공지에서 읽어둔 회차 보스 전부. 어느 회차를 노출할지는 화면이 정한다."""
    return RaidRotationsResponse(**load_rotations())
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd backend && python3 -m pytest tests/test_api_raid_rotations.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 전체 스위트를 돌린다**

Run: `cd backend && python3 -m pytest -q`
Expected: `1984 passed, 3 skipped`

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api.py backend/tests/test_api_raid_rotations.py
git commit -m "GET /api/raid-rotations

회차 파일을 자르지 않고 그대로 낸다 - 어느 회차를 보여줄지는 화면의 판단이다."
```

---

### Task 3: 프론트 타입 · API 클라이언트 · 훅

**Files:**
- Create: `frontend/src/types/raidRotation.ts`
- Create: `frontend/src/api/raidRotations.ts`
- Create: `frontend/src/hooks/useRaidRotations.ts`
- Test: `frontend/src/types/raidRotation.test.ts`
- Test: `frontend/src/hooks/useRaidRotations.test.ts`

**Interfaces:**
- Consumes: `GET /api/raid-rotations` (Task 2), `api/recommendApiError.ts`의 `RecommendApiError`, `types/supportedUnit.ts`의 `NikkeElement`.
- Produces:
  - `types/raidRotation.ts`: `RaidKind`, `RotationBoss`, `RaidRotation`, `RaidRotationsWire`, `latestRotationFor(rotations: RaidRotation[], raid: RaidKind): RaidRotation | null`
  - `api/raidRotations.ts`: `getRaidRotations(): Promise<RaidRotation[]>`
  - `hooks/useRaidRotations.ts`: `useRaidRotations(): { rotations: RaidRotation[]; loading: boolean }`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/types/raidRotation.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { latestRotationFor, type RaidRotation } from './raidRotation'

const rotation = (id: string, raid: 'solo' | 'union', endsAt: string): RaidRotation => ({
  id,
  raid,
  title: id,
  starts_at: null,
  ends_at: endsAt,
  source_url: 'https://example.test',
  source_locale: 'ko',
  read_on: '2026-01-01',
  bosses: [],
})

describe('latestRotationFor', () => {
  it('같은 레이드 중 가장 늦게 끝나는 회차를 고른다', () => {
    const rotations = [
      rotation('solo-38', 'solo', '2026-07-09T04:59:00+09:00'),
      rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00'),
    ]
    expect(latestRotationFor(rotations, 'solo')?.id).toBe('solo-39')
  })

  it('배열 순서가 아니라 종료 시각으로 고른다', () => {
    // 과거 회차를 뒤늦게 채워 넣으면 배열 끝이 최신이 아니게 된다.
    const rotations = [
      rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00'),
      rotation('solo-37', 'solo', '2026-06-25T04:59:00+09:00'),
    ]
    expect(latestRotationFor(rotations, 'solo')?.id).toBe('solo-39')
  })

  it('다른 레이드의 회차는 보지 않는다', () => {
    const rotations = [
      rotation('union-1', 'union', '2026-12-31T04:59:00+09:00'),
      rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00'),
    ]
    expect(latestRotationFor(rotations, 'solo')?.id).toBe('solo-39')
  })

  it('그 레이드의 회차가 없으면 null이다', () => {
    expect(latestRotationFor([rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00')], 'union'))
      .toBeNull()
  })
})
```

`frontend/src/hooks/useRaidRotations.test.ts`:

```ts
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useRaidRotations } from './useRaidRotations'

const wire = {
  schema_version: 1,
  rotations: [
    {
      id: 'solo-39',
      raid: 'solo',
      title: '솔로 레이드 39시즌',
      starts_at: null,
      ends_at: '2026-07-23T04:59:00+09:00',
      source_url: 'https://example.test',
      source_locale: 'ko',
      read_on: '2026-08-07',
      bosses: [{ name: '아일랜드 이터', weakness: 'Iron', stated: {} }],
    },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useRaidRotations', () => {
  it('회차 목록을 실어 온다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => wire,
    }))
    const { result } = renderHook(() => useRaidRotations())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.rotations.map((r) => r.id)).toEqual(['solo-39'])
  })

  it('실패하면 빈 목록으로 끝난다', async () => {
    // 회차 데이터가 없으면 피커가 안 그려질 뿐이고 보스 설정은 손으로 다 된다.
    // 배너를 띄울 만한 실패가 아니다.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const { result } = renderHook(() => useRaidRotations())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.rotations).toEqual([])
  })
})
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/types/raidRotation.test.ts src/hooks/useRaidRotations.test.ts`
Expected: FAIL — `Failed to resolve import "./raidRotation"` / `"./useRaidRotations"`

- [ ] **Step 3: 타입과 최신 회차 선택을 쓴다**

`frontend/src/types/raidRotation.ts`:

```ts
// TS mirror of GET /api/raid-rotations (backend/app/api.py RaidRotationsResponse).
// types/recommend.ts와 같은 이유로 snake_case를 그대로 둔다 — 파이썬 쪽이 진실의
// 원천이고, 이름을 바꾸면 두 파일을 대조할 수 없다.
//
// `stated`는 공지 원문이다. 앱은 해석하지 않고 렌더링만 한다.

import type { NikkeElement } from './supportedUnit'

export type RaidKind = 'solo' | 'union'

export interface RotationBoss {
  name: string
  /** 공지가 적은 약점. 무속성 보스는 null. */
  weakness: NikkeElement | null
  /** 공지 원문. 항목은 솔로/유니온이 다르므로 자유 형식이다. */
  stated: Record<string, string | string[]>
}

export interface RaidRotation {
  id: string
  raid: RaidKind
  title: string
  starts_at: string | null
  ends_at: string
  source_url: string
  source_locale: 'ko' | 'en'
  read_on: string
  bosses: RotationBoss[]
}

export interface RaidRotationsWire {
  schema_version: number
  rotations: RaidRotation[]
}

/** 이 레이드의 최신 회차. 없으면 null.
 *
 * `ends_at`이 가장 늦은 회차로 정한다. 배열 순서나 `read_on`으로 고르면 과거
 * 회차를 뒤늦게 채워 넣는 날 뒤집힌다. 문자열 비교가 아니라 파싱해서 비교하는
 * 이유는 오프셋이 다른 회차가 섞일 수 있어서다. */
export const latestRotationFor = (
  rotations: RaidRotation[],
  raid: RaidKind,
): RaidRotation | null =>
  rotations
    .filter((r) => r.raid === raid)
    .reduce<RaidRotation | null>(
      (best, r) =>
        best === null || Date.parse(r.ends_at) > Date.parse(best.ends_at) ? r : best,
      null,
    )
```

- [ ] **Step 4: API 클라이언트를 쓴다**

`frontend/src/api/raidRotations.ts`:

```ts
// Typed client for GET /api/raid-rotations. 회차 보스 카드 피커가 쓴다.
// 와이어가 이미 프론트가 쓰는 모양이라 supportedUnits.ts와 달리 매핑 함수가 없다.

import type { RaidRotation, RaidRotationsWire } from '../types/raidRotation'
import { RecommendApiError } from './recommendApiError'

export const getRaidRotations = async (): Promise<RaidRotation[]> => {
  const response = await fetch('/api/raid-rotations')
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  const wire = (await response.json()) as RaidRotationsWire
  return wire.rotations
}
```

- [ ] **Step 5: 훅을 쓴다**

`frontend/src/hooks/useRaidRotations.ts`:

```ts
// 회차 보스 목록을 마운트 시 1회 조회한다. useSupportedUnits와 같은 모양이지만
// 에러 상태가 없다 — 회차 데이터가 없으면 피커가 안 그려질 뿐이고 보스 설정은
// 손으로 전부 되므로, 배너를 띄울 실패가 아니다.

import { useEffect, useState } from 'react'
import { getRaidRotations } from '../api/raidRotations'
import type { RaidRotation } from '../types/raidRotation'

export interface RaidRotationsState {
  rotations: RaidRotation[]
  loading: boolean
}

export const useRaidRotations = (): RaidRotationsState => {
  const [rotations, setRotations] = useState<RaidRotation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getRaidRotations()
      .then((result) => {
        if (!cancelled) setRotations(result)
      })
      .catch(() => {
        if (!cancelled) setRotations([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { rotations, loading }
}
```

- [ ] **Step 6: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/types/raidRotation.test.ts src/hooks/useRaidRotations.test.ts`
Expected: PASS (6 tests)

- [ ] **Step 7: 타입 체크와 전체 스위트**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: tsc 오류 없음 · `585 passed (60 files)`

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/types/raidRotation.ts frontend/src/types/raidRotation.test.ts frontend/src/api/raidRotations.ts frontend/src/hooks/useRaidRotations.ts frontend/src/hooks/useRaidRotations.test.ts
git commit -m "회차 보스 타입·클라이언트·훅

최신 회차는 ends_at으로 고른다 - 배열 순서는 과거 회차를 뒤늦게 넣으면 뒤집힌다."
```

---

### Task 4: 보스 카드 피커 컴포넌트

**Files:**
- Create: `frontend/src/lib/elementIcon.ts`
- Modify: `frontend/src/components/BossProfileField.tsx:28-34` (`WEAKNESS_ICON` 상수를 `lib/elementIcon.ts`로 옮기고 import)
- Create: `frontend/src/components/RaidRotationPicker.tsx`
- Test: `frontend/src/components/RaidRotationPicker.test.tsx`

**Interfaces:**
- Consumes: `types/raidRotation.ts`의 `RaidRotation`·`RotationBoss` (Task 3), `lib/elementName.ts`의 `elementLabel`.
- Produces:
  - `lib/elementIcon.ts`: `WEAKNESS_ICON: Record<NikkeElement, string>`
  - `components/RaidRotationPicker.tsx`: `RaidRotationPicker({ rotation, selectedName, onPick })` — 상태 없는 표시 컴포넌트.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/RaidRotationPicker.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { RaidRotation } from '../types/raidRotation'
import { RaidRotationPicker } from './RaidRotationPicker'

const rotation: RaidRotation = {
  id: 'union-2026-07-31',
  raid: 'union',
  title: '유니온 레이드 7/31',
  starts_at: '2026-07-31T05:00:00+09:00',
  ends_at: '2026-08-06T04:59:00+09:00',
  source_url: 'https://arca.live/b/nikketgv/177833660',
  source_locale: 'ko',
  read_on: '2026-08-07',
  bosses: [
    {
      name: '선바스',
      weakness: 'Electric',
      stated: { 등급: '로드 급', 거리: '근거리', 설명: ['머리에 꽃을 얹은 랩쳐.'] },
    },
    { name: '토커티브', weakness: 'Water', stated: { 등급: '타이런트 급' } },
  ],
}

describe('RaidRotationPicker', () => {
  it('회차의 보스를 전부 그린다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /선바스/ })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /토커티브/ })).toBeInTheDocument()
  })

  it('공지 원문을 해석하지 않고 그대로 보여준다', () => {
    // 「거리: 근거리」는 우리 적정거리 밴드로 번역되지 않는다 - 화면에 원문으로
    // 남아 있어야 Fienn이 보고 직접 판단할 수 있다.
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getByText('거리')).toBeInTheDocument()
    expect(screen.getByText('근거리')).toBeInTheDocument()
  })

  it('여러 줄짜리 항목도 전부 보여준다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getByText('머리에 꽃을 얹은 랩쳐.')).toBeInTheDocument()
  })

  it('고른 보스를 콜백으로 넘긴다', async () => {
    const onPick = vi.fn()
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={onPick} />)
    await userEvent.click(screen.getByRole('radio', { name: /토커티브/ }))
    expect(onPick).toHaveBeenCalledWith(rotation.bosses[1])
  })

  it('선택된 보스만 체크되어 있다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName="선바스" onPick={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /선바스/ })).toBeChecked()
    expect(screen.getByRole('radio', { name: /토커티브/ })).not.toBeChecked()
  })
})
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/RaidRotationPicker.test.tsx`
Expected: FAIL — `Failed to resolve import "./RaidRotationPicker"`

- [ ] **Step 3: 아이콘 맵을 옮긴다**

`frontend/src/lib/elementIcon.ts` 생성:

```ts
// 속성 아이콘 경로. blablalink의 코드 아이콘을 scripts/download_element_icons.py로
// 받아둔 것이다. 보스 설정의 약점 선택과 회차 보스 카드가 같이 쓴다.

import type { NikkeElement } from '../types/supportedUnit'

export const WEAKNESS_ICON: Record<NikkeElement, string> = {
  Fire: '/elements/fire.png',
  Water: '/elements/water.png',
  Wind: '/elements/wind.png',
  Iron: '/elements/iron.png',
  Electric: '/elements/electric.png',
}
```

`frontend/src/components/BossProfileField.tsx`에서 25-34행의 주석과 `WEAKNESS_ICON` 정의를 지우고, import 블록에 추가:

```ts
import { WEAKNESS_ICON } from '../lib/elementIcon'
```

화면에 그리는 것이 보스 본인 속성이 아니라 약점이라는 25-27행 주석은 `WEAKNESS_CHOICES` 위로 옮겨 남긴다:

```ts
// 화면에 그리는 것은 보스 본인 속성이 아니라 그 보스를 이기는 속성이다 — 플레이어가
// 편성할 때 보는 값이 그쪽이기 때문.
const WEAKNESS_CHOICES: NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']
```

- [ ] **Step 4: 피커를 쓴다**

`frontend/src/components/RaidRotationPicker.tsx`:

```tsx
// 이번 회차 보스 카드. 고르면 약점 속성만 보스 설정에 들어가고, 공지가 명시하지
// 않은 것(거리·저지 부위·스쿼드 추천)은 원문 그대로 카드에 남는다 — 우리 플래그로
// 번역하면 틀렸을 때 값 검증을 전부 통과하고 조용히 초록으로 남기 때문이다.

import { useId } from 'react'
import { WEAKNESS_ICON } from '../lib/elementIcon'
import { elementLabel } from '../lib/elementName'
import type { RaidRotation, RotationBoss } from '../types/raidRotation'

interface RaidRotationPickerProps {
  rotation: RaidRotation
  /** 지금 골라져 있는 보스 이름. 아무것도 안 고른 상태는 null. */
  selectedName: string | null
  onPick: (boss: RotationBoss) => void
}

export function RaidRotationPicker({
  rotation,
  selectedName,
  onPick,
}: RaidRotationPickerProps) {
  const groupId = useId()

  return (
    <div className="field">
      <span className="field__label" id={`${groupId}-label`}>
        {rotation.title} 보스
      </span>
      {/* 진짜 라디오를 시각적으로만 숨긴다 — 약점 선택과 같은 이유로, div/button으로
          만들면 화살표 이동과 화면 낭독기의 그룹 읽기를 둘 다 잃는다. */}
      <div
        className="rotation-picker"
        role="radiogroup"
        aria-labelledby={`${groupId}-label`}
      >
        {rotation.bosses.map((boss) => (
          <label key={boss.name} className="rotation-picker__option">
            <input
              type="radio"
              className="visually-hidden"
              name={groupId}
              checked={selectedName === boss.name}
              onChange={() => onPick(boss)}
            />
            <span className="rotation-picker__head">
              {boss.weakness && (
                <img
                  className="rotation-picker__icon"
                  src={WEAKNESS_ICON[boss.weakness]}
                  alt={elementLabel(boss.weakness)}
                />
              )}
              <span className="rotation-picker__name">{boss.name}</span>
            </span>
            <dl className="rotation-picker__stated">
              {Object.entries(boss.stated).map(([key, value]) => (
                <div className="rotation-picker__stated-row" key={key}>
                  <dt>{key}</dt>
                  <dd>
                    {Array.isArray(value)
                      ? value.map((line) => <span key={line}>{line}</span>)
                      : value}
                  </dd>
                </div>
              ))}
            </dl>
          </label>
        ))}
      </div>
      <p className="group__hint">
        공지 원문이에요. 약점 속성만 자동으로 채워지고, 나머지는 직접 확인해서 체크하세요.
      </p>
    </div>
  )
}
```

- [ ] **Step 5: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/RaidRotationPicker.test.tsx src/components/BossProfileField.test.tsx`
Expected: PASS — 피커 5개 + 기존 `BossProfileField` 테스트 전부

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/elementIcon.ts frontend/src/components/RaidRotationPicker.tsx frontend/src/components/RaidRotationPicker.test.tsx frontend/src/components/BossProfileField.tsx
git commit -m "회차 보스 카드 피커

공지 원문을 해석하지 않고 그대로 렌더링한다. 속성 아이콘 맵은 약점 선택과
공유하므로 lib/elementIcon.ts로 옮겼다."
```

---

### Task 5: `BossProfileField` 합성 — 고르면 나머지는 초기화

이 계획에서 가장 중요한 태스크다. 설계 D2("어떤 값도 상속되지 않는다")가 실제로 지켜지는 곳이 여기 하나뿐이다.

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx` (props 인터페이스, 컴포넌트 본문 상단, 반환 JSX 맨 앞)
- Test: `frontend/src/components/BossProfileField.test.tsx` (파일 끝에 describe 추가)

**Interfaces:**
- Consumes: `RaidRotationPicker` (Task 4), `types/raidRotation.ts`의 `RaidRotation`·`RotationBoss` (Task 3), `lib/elementAdvantage.ts`의 `bossElementFor`, `types/bossProfileDraft.ts`의 `makeDefaultBossProfileDraft`.
- Produces: `BossProfileFieldProps`에 `rotation?: RaidRotation | null`과 `defaultEnemyDef?: string` 추가. Task 6의 두 패널이 이 둘을 넘긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/BossProfileField.test.tsx` 파일 끝에 추가. 파일 상단 import에 `RaidRotation` 타입을 더한다.

```tsx
const rotation: RaidRotation = {
  id: 'union-2026-07-31',
  raid: 'union',
  title: '유니온 레이드 7/31',
  starts_at: '2026-07-31T05:00:00+09:00',
  ends_at: '2026-08-06T04:59:00+09:00',
  source_url: 'https://arca.live/b/nikketgv/177833660',
  source_locale: 'ko',
  read_on: '2026-08-07',
  bosses: [
    { name: '선바스', weakness: 'Electric', stated: { 거리: '근거리' } },
    { name: '토커티브', weakness: 'Water', stated: { 거리: '원거리' } },
  ],
}

describe('BossProfileField 회차 보스 피커', () => {
  it('회차가 없으면 피커를 그리지 않는다', () => {
    render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={vi.fn()} />)
    expect(screen.queryByRole('radio', { name: /선바스/ })).not.toBeInTheDocument()
  })

  it('보스를 고르면 약점에서 역산한 보스 속성이 들어간다', async () => {
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={onChange}
        rotation={rotation}
      />,
    )
    await userEvent.click(screen.getByRole('radio', { name: /선바스/ }))
    // 약점 전격 -> 전격이 이기는 속성이 보스 본인 속성이다.
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ element: bossElementFor('Electric') }),
    )
  })

  it('보스를 고르면 손으로 켜둔 다른 필드가 전부 초기화된다', async () => {
    // 설계 D2. 이게 없으면 화면에는 「토커티브」라고 적혀 있는데 계산은 직전 보스
    // 가정(코어 피격 가능 · 부위파괴 · 방어력)으로 돈다.
    const onChange = vi.fn()
    const dirty = {
      ...makeDefaultBossProfileDraft(),
      core_hittable: true,
      pierce_hits_body_behind_core: true,
      part_destructible: true,
      elemental_interrupt_required: true,
      effective_range_band: 'far' as const,
      enemy_def: '99999',
      fight_duration: '240',
    }
    render(<BossProfileField value={dirty} onChange={onChange} rotation={rotation} />)
    await userEvent.click(screen.getByRole('radio', { name: /토커티브/ }))
    expect(onChange).toHaveBeenCalledWith({
      ...makeDefaultBossProfileDraft(),
      element: bossElementFor('Water'),
    })
  })

  it('초기화되는 방어력은 호출부가 준 기본값이다', async () => {
    // 솔로와 유니온 보스는 방어력이 달라서 공유 기본값 하나로는 한쪽이 틀린다 —
    // makeDefaultBossProfileDraft가 인자를 받는 것과 같은 이유다.
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft('31784')}
        onChange={onChange}
        rotation={rotation}
        defaultEnemyDef="31784"
      />,
    )
    await userEvent.click(screen.getByRole('radio', { name: /선바스/ }))
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ enemy_def: '31784' }),
    )
  })

  it('약점을 손으로 바꾸면 카드 선택이 풀린다', async () => {
    // 카드는 「이 보스로 계산 중」이라고 말한다. 속성이 그 보스와 달라진 뒤에도
    // 체크가 남아 있으면 화면이 거짓말을 한다.
    const Harness = () => {
      const [draft, setDraft] = useState(makeDefaultBossProfileDraft())
      return <BossProfileField value={draft} onChange={setDraft} rotation={rotation} />
    }
    render(<Harness />)
    await userEvent.click(screen.getByRole('radio', { name: /선바스/ }))
    expect(screen.getByRole('radio', { name: /선바스/ })).toBeChecked()

    await userEvent.click(screen.getByRole('radio', { name: '작열' }))
    expect(screen.getByRole('radio', { name: /선바스/ })).not.toBeChecked()
  })
})
```

테스트 파일 상단에 필요한 import를 더한다:

```tsx
import { useState } from 'react'
import { bossElementFor } from '../lib/elementAdvantage'
import type { RaidRotation } from '../types/raidRotation'
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx`
Expected: FAIL — `rotation` prop이 타입에 없다는 tsc 오류, 그리고 「선바스」 라디오를 못 찾음

- [ ] **Step 3: props에 두 항목을 더한다**

`frontend/src/components/BossProfileField.tsx`의 `BossProfileFieldProps`에:

```ts
  /** 이번 회차 보스 목록. 없으면 카드 피커를 그리지 않는다. */
  rotation?: RaidRotation | null
  /** 카드를 골랐을 때 방어력이 되돌아갈 값. 솔로 보스와 유니온 보스는 방어력이
   *  달라 공유 기본값 하나로는 한쪽이 틀린 값으로 계산된다 —
   *  makeDefaultBossProfileDraft가 인자를 받는 것과 같은 이유다. */
  defaultEnemyDef?: string
```

시그니처와 import:

```tsx
import { bossElementFor } from '../lib/elementAdvantage'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'
import type { RaidRotation, RotationBoss } from '../types/raidRotation'
import { RaidRotationPicker } from './RaidRotationPicker'
```

```tsx
export function BossProfileField({
  value,
  errors,
  onChange,
  showElementalInterrupt = true,
  rotation = null,
  defaultEnemyDef = '0',
}: BossProfileFieldProps) {
```

- [ ] **Step 4: 선택 처리와 렌더링을 더한다**

`const rangeBandId = useId()` 아래에:

```tsx
  // 어느 보스 카드를 눌렀는지. 이름으로 들고 있는 이유는 같은 약점을 가진 보스가
  // 한 회차에 둘 나올 수 있어서다 — 속성만으로는 어느 쪽인지 못 가른다.
  const [pickedName, setPickedName] = useState<string | null>(null)

  // 카드는 「이 보스로 계산 중」이라고 말한다. 그래서 약점이 그 보스와 달라진
  // 순간(사용자가 아이콘을 직접 눌렀을 때) 체크를 놓아야 한다.
  const picked = rotation?.bosses.find((boss) => boss.name === pickedName) ?? null
  const selectedName =
    picked && picked.weakness !== null && bossElementFor(picked.weakness) === value.element
      ? picked.name
      : null

  // 공지가 명시한 약점만 얹고 나머지는 전부 기본값으로 돌린다. 직전 보스의 설정이
  // 남으면 화면에는 새 보스 이름이 적혀 있는데 계산은 옛 보스 가정으로 돈다.
  const pickRotationBoss = (boss: RotationBoss) => {
    setPickedName(boss.name)
    onChange({
      ...makeDefaultBossProfileDraft(defaultEnemyDef),
      element: boss.weakness === null ? null : bossElementFor(boss.weakness),
    })
  }
```

`useState`를 react import에 더한다:

```tsx
import { useId, useState } from 'react'
```

`<legend className="group__legend">보스 설정</legend>` 바로 아래에:

```tsx
      {rotation && (
        <RaidRotationPicker
          rotation={rotation}
          selectedName={selectedName}
          onPick={pickRotationBoss}
        />
      )}
```

- [ ] **Step 5: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx`
Expected: PASS — 기존 테스트 전부 + 새 5개

- [ ] **Step 6: 초기화가 정말 걸리는지 깨뜨려 확인한다**

`pickRotationBoss`의 `...makeDefaultBossProfileDraft(defaultEnemyDef),`를 `...value,`로 잠시 바꾼다.

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx`
Expected: FAIL — "보스를 고르면 손으로 켜둔 다른 필드가 전부 초기화된다"가 깨져야 한다.

깨지는 것을 확인한 뒤 되돌린다. 테스트가 잡는다고 적은 것은 실제로 깨보고 확인한다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/BossProfileField.tsx frontend/src/components/BossProfileField.test.tsx
git commit -m "카드를 고르면 약점만 들어가고 나머지는 초기화된다

같은 보스가 시즌마다 다른 속성으로 나오므로 어떤 값도 상속되지 않아야 한다.
직전에 고른 보스의 설정이 남는 것도 같은 실패다."
```

---

### Task 6: 두 패널 배선과 스타일

**Files:**
- Modify: `frontend/src/App.tsx:13` (import), `:64` 근처 (훅 호출), `:193` `<RecommendPanel>`, `:231` `<UnionRaidPanel>`
- Modify: `frontend/src/components/RecommendPanel.tsx` (props, `:694` 렌더)
- Modify: `frontend/src/components/UnionRaidPanel.tsx` (props, `:205` 렌더)
- Modify: `frontend/src/App.css` (`.element-picker` 블록 뒤, 793행 근처)
- Test: `frontend/src/App.test.tsx` (describe 추가)

**Interfaces:**
- Consumes: `useRaidRotations` · `latestRotationFor` (Task 3), `BossProfileField`의 `rotation`·`defaultEnemyDef` props (Task 5).
- Produces: `RecommendPanelProps`와 `UnionRaidPanelProps`에 `rotations: RaidRotation[]` 추가.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/App.test.tsx`는 `fetch`가 아니라 **API 모듈을 목킹**한다. 회차도 같은
방식으로 붙인다.

파일 상단 `vi.mock` 블록에 (13-15행의 `supportedUnits` 목 옆에):

```tsx
vi.mock('./api/raidRotations', () => ({
  getRaidRotations: vi.fn(),
}))
```

import 블록(18행 근처)에:

```tsx
import { getRaidRotations } from './api/raidRotations'
import type { RaidRotation } from './types/raidRotation'
```

`beforeEach`(43-46행)와 `afterEach`(48-51행)에 한 줄씩. 나머지 테스트는 회차를
기대하지 않으므로 기본은 빈 목록이다:

```tsx
  vi.mocked(getRaidRotations).mockResolvedValue([])
```

```tsx
  vi.mocked(getRaidRotations).mockReset()
```

그리고 테스트 본문. `hidden` 패널은 접근성 트리에서 빠지므로(99-127행의 기존
테스트가 그 성질에 기대고 있다) 탭을 전환하며 검사한다:

```tsx
  const ROTATIONS: RaidRotation[] = [
    {
      id: 'solo-39',
      raid: 'solo',
      title: '솔로 레이드 39시즌',
      starts_at: '2026-07-16T12:00:00+09:00',
      ends_at: '2026-07-23T04:59:00+09:00',
      source_url: 'https://arca.live/b/nikketgv/177017741',
      source_locale: 'ko',
      read_on: '2026-08-07',
      bosses: [{ name: '아일랜드 이터', weakness: 'Iron', stated: {} }],
    },
    {
      id: 'union-2026-07-31',
      raid: 'union',
      title: '유니온 레이드 7/31',
      starts_at: '2026-07-31T05:00:00+09:00',
      ends_at: '2026-08-06T04:59:00+09:00',
      source_url: 'https://arca.live/b/nikketgv/177833660',
      source_locale: 'ko',
      read_on: '2026-08-07',
      bosses: [{ name: '선바스', weakness: 'Electric', stated: {} }],
    },
  ]

  it('탭마다 그 레이드의 회차 보스만 뜬다', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    vi.mocked(getRaidRotations).mockResolvedValue([...ROTATIONS])
    seedProfiles({
      activeKey: ACCT_A,
      profiles: {
        [ACCT_A]: {
          openId: 'acct-a',
          area: 81,
          nickname: '본계',
          roster: [validDraft()],
          results: {},
          lastResultHash: null,
          lastInputs: null,
          savedRuns: [],
        },
      },
    })

    render(<App />)

    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))
    expect(await screen.findByRole('radio', { name: /아일랜드 이터/ })).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: /선바스/ })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '유니온 레이드' }))
    expect(screen.getByRole('radio', { name: /선바스/ })).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: /아일랜드 이터/ })).not.toBeInTheDocument()
  })
```

이 테스트는 `describe('App', ...)` 안, `SUPPORTED` 상수를 볼 수 있는 자리에 넣는다
(129행의 유니온 탭 테스트 옆).

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: FAIL — 「아일랜드 이터」 라디오를 못 찾음

- [ ] **Step 3: App에서 한 번 조회해 두 패널에 넘긴다**

`frontend/src/App.tsx` import 블록:

```ts
import { useRaidRotations } from './hooks/useRaidRotations'
```

`const supportedUnits = useSupportedUnits()` 아래:

```ts
  // 두 탭 패널이 동시에 마운트되므로 훅을 패널마다 부르면 같은 파일을 두 번
  // 받는다. 한 번 받아 내려보낸다.
  const raidRotations = useRaidRotations()
```

`<RecommendPanel>`과 `<UnionRaidPanel>`에 각각 prop 추가:

```tsx
                rotations={raidRotations.rotations}
```

- [ ] **Step 4: RecommendPanel을 배선한다**

`frontend/src/components/RecommendPanel.tsx` — props 인터페이스에:

```ts
  /** 공지에서 읽어둔 회차 전체. 이 탭은 솔로 레이드 회차만 쓴다.
   *  선택적인 이유는 이 컴포넌트를 직접 렌더하는 테스트가 51곳이기 때문이다 —
   *  전부 고치면 그 소음에 실제 변경이 묻힌다. 배선을 빠뜨리면 App 테스트의
   *  "탭마다 그 레이드의 회차 보스만 뜬다"가 잡는다. */
  rotations?: RaidRotation[]
```

구조 분해에서 기본값을 준다:

```tsx
  rotations = [],
```

import:

```ts
import { latestRotationFor, type RaidRotation } from '../types/raidRotation'
```

구조 분해에 `rotations`를 더하고, 694행의 렌더를:

```tsx
          <BossProfileField
            value={draft}
            errors={touched ? errors : {}}
            onChange={setDraft}
            rotation={latestRotationFor(rotations, 'solo')}
            defaultEnemyDef={SOLO_RAID_DEFAULT_ENEMY_DEF}
          />
```

- [ ] **Step 5: UnionRaidPanel을 배선한다**

`frontend/src/components/UnionRaidPanel.tsx` — props 인터페이스에. RecommendPanel과
같은 이유로 선택적이다(이쪽 테스트는 `renderPanel` 헬퍼 하나지만, 두 패널의 prop
모양이 다르면 App에서 배선할 때 한쪽만 틀리기 쉽다):

```ts
  /** 공지에서 읽어둔 회차 전체. 이 탭은 유니온 레이드 회차만 쓴다. */
  rotations?: RaidRotation[]
```

import:

```ts
import { latestRotationFor, type RaidRotation } from '../types/raidRotation'
```

구조 분해에 `rotations = [],`를 더하고, 컴포넌트 본문에서 한 번만 고른다 (전투 수만큼
다시 계산하지 않기 위해):

```tsx
  const unionRotation = useMemo(() => latestRotationFor(rotations, 'union'), [rotations])
```

205행의 렌더에 두 줄 추가:

```tsx
              <BossProfileField
                value={bosses[i]}
                errors={touched ? validated[i].errors : {}}
                onChange={(next) =>
                  setBosses((current) => current.map((boss, idx) => (idx === i ? next : boss)))
                }
                rotation={unionRotation}
                // 이 탭은 유저가 짠 편성을 채점만 해서 탐색이 없다 - 제약이 걸 곳이 없다.
                showElementalInterrupt={false}
              />
```

`defaultEnemyDef`는 넘기지 않는다 — 이 탭은 `makeDefaultBossProfileDraft()`를
인자 없이 쓰므로 기본값 `'0'`이 맞다.

- [ ] **Step 6: 스타일을 더한다**

`frontend/src/App.css`의 `.element-picker__option[data-element='Electric']` 블록 뒤에:

```css
/* 회차 보스 카드. 카드마다 공지 원문이 붙어 높이가 제각각이므로 flex가 아니라
   그리드로 놓는다 — 5장이 들쭉날쭉하면 어느 것이 골라졌는지 읽기 어렵다. */
.rotation-picker {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--sp-2);
}

.rotation-picker__option {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  cursor: pointer;
}

.rotation-picker__option:has(input:checked) {
  border-color: var(--accent);
  background: var(--surface);
}

.rotation-picker__option:has(input:focus-visible) {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.rotation-picker__head {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
}

.rotation-picker__icon {
  width: 20px;
  height: 20px;
}

.rotation-picker__name {
  font-weight: 600;
}

/* 공지 원문은 참고 자료지 입력값이 아니다 — 카드에서 시선을 덜 끌게 둔다. */
.rotation-picker__stated {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
}

.rotation-picker__stated-row {
  display: flex;
  gap: var(--sp-1);
}

.rotation-picker__stated-row dt::after {
  content: ':';
}

.rotation-picker__stated-row dd {
  margin: 0;
  display: flex;
  flex-direction: column;
}
```

- [ ] **Step 7: 테스트와 타입 체크**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: tsc 오류 없음 · `596 passed (61 files)`
(기준선 579 + Task 3의 6 + Task 4의 5 + Task 5의 5 + 이번 1)

- [ ] **Step 8: 앱을 띄워 눈으로 본다**

Vitest는 `css: false`라 스타일은 단위 테스트로 검증되지 않는다. 두 서버를 띄운다:

```bash
cd backend && python3 -m uvicorn app.api:app --port 8000
```

```bash
cd frontend && npm run dev
```

`http://localhost:5173`에서 확인할 것:

- 유니온 탭 1~3번 전투 각각에 보스 카드 5장이 뜨는가
- 카드를 누르면 아래 약점 아이콘이 같이 바뀌는가
- 코어 피격 가능을 체크한 뒤 다른 카드를 누르면 체크가 풀리는가
- 카드 안의 공지 원문이 넘치지 않고 읽히는가
- 솔로 탭에는 「아일랜드 이터」 한 장만 뜨는가

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/App.css frontend/src/components/RecommendPanel.tsx frontend/src/components/UnionRaidPanel.tsx
git commit -m "회차 보스 피커를 두 탭에 배선

회차 조회는 App에서 한 번만 한다 - 두 탭 패널이 동시에 마운트되므로 패널마다
부르면 같은 파일을 두 번 받는다."
```

---

### Task 7: `/update-raid-bosses` 스킬과 문서

**Files:**
- Create: `.claude/skills/update-raid-bosses/SKILL.md`
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: `data/raid-rotations.json`의 스키마 (Task 1).
- Produces: 사람이 실행하는 절차. 코드가 소비하지 않는다.

- [ ] **Step 1: 스킬을 쓴다**

`.claude/skills/update-raid-bosses/SKILL.md`:

````markdown
---
name: update-raid-bosses
description: 솔로/유니온 레이드 공지에서 이번 회차 보스를 읽어 data/raid-rotations.json에 반영한다. Fienn이 공지 URL(또는 공지 이미지 URL)을 줄 때 쓴다.
---

# 레이드 회차 보스 갱신

공지의 보스 정보는 **전부 이미지 안에** 있다. 그래서 판독은 앱이 아니라 여기서
한다 — 앱에는 OCR이 들어가지 않는다.

## 인자

공지 글 URL 또는 공지 이미지 URL. 둘 다 받는다: 호스트 셀렉터가 안 먹거나 새
사이트가 나와도 이미지 주소만 주면 우회된다.

## 1. 본문 이미지 찾기

글 URL이면 브라우저(Playwright MCP)로 열어 **본문 컨테이너 안의** 이미지만
가져온다. 페이지 전체에서 `img`를 긁으면 사이드바·추천글·댓글 스크린샷이 섞인다.

| 호스트 | 본문 컨테이너 |
|---|---|
| `blablalink.com` | `.ql-editor` |
| `arca.live` | `.fr-view.article-content` |

두 호스트 모두 본문 이미지는 **정확히 1장**이다. 2장 이상이 나오면 컨테이너를
잘못 잡은 것이다.

본문 텍스트도 같이 뽑는다 — 보스 이름과 기간이 거기 있을 수 있다.

## 2. 판독

이미지를 받아 읽는다. 세로로 긴 이미지는 4~5조각으로 잘라야 글자가 보인다.

```bash
python3 -c "
from PIL import Image
im = Image.open('post.png'); W, H = im.size
for i in range(5):
    im.crop((0, H*i//5, W, H*(i+1)//5)).save(f'slice_{i}.png')
"
```

읽을 것:

- **유니온 레이드** — 보스마다 이름 · 등급(로드 급/타이런트 급) · 약점 · 거리 · 설명
- **솔로 레이드** — 이름 · 보스 속성 · 약점 속성 · 스쿼드 추천 · 랩쳐 주요 공격 · 기간

속성 이름 대응:

| 공지 | 엔진 |
|---|---|
| 작열 / Fire | `Fire` |
| 수냉 / Water | `Water` |
| 풍압 / Wind | `Wind` |
| 철갑 / Iron | `Iron` |
| 전격 / Electric | `Electric` |

**대조:** 솔로 공지는 보스 속성과 약점을 나란히 적는다.
`backend/app/elements.py`의 `weakness_of(보스속성)`이 공지의 약점과 같은지
확인하고, 어긋나면 멈추고 Fienn에게 보고한다.

## 3. Fienn 확인 — 유일한 중단점

판독 결과를 표로 보여주고 확인받는다. 승인 전에는 파일을 고치지 않는다.

## 4. 파일 반영

`data/raid-rotations.json`의 `rotations`에 추가한다. 같은 `id`가 이미 있으면 교체.

- `id` — 솔로는 `solo-<시즌번호>`, 유니온은 `union-<시작일>`(유니온 공지에는 시즌
  번호가 없다)
- `weakness` — **기계가 읽는 유일한 필드.** 공지의 약점을 엔진 어휘로.
- `stated` — 공지 원문 그대로. 거리·스쿼드 추천·저지 부위 같은 것은 **여기까지만**
  간다. 우리 플래그로 번역하지 않는다.
- `source_url` — 글 주소. **이미지 URL은 적지 않는다** — arca 이미지는 서명 URL이라
  약 10시간 뒤 만료된다.
- `source_locale` — 한국어 공지면 `ko`. 한국어판이 1순위다: CHATTERBOX의 한국 서버
  공식 이름은 「토커티브」이고, 영어판을 음차하면 없는 이름이 만들어진다.

## 5. 검증하고 커밋

```bash
cd backend && python3 -m pytest tests/test_raid_rotations.py tests/test_api_raid_rotations.py -v
```

`test_the_shipped_file_loads`가 새 회차를 포함해 통과해야 한다. 그 다음 커밋.

## 번역하지 않는 것

공지가 **그 단어로 적지 않은 것**은 채우지 않는다. 아래 셋은 그럴듯하지만 근거가
없다:

- 「거리: 근거리/원거리」 → `effective_range_band` — 우리 밴드는 3단계인데 공지에서
  관측된 값은 둘뿐이다.
- 「스쿼드 추천: 머신건 니케」 → `mid` — MG 추천이 거리 때문인지 알 수 없다.
- 「저지 부위」 → `part_destructible` — 이 플래그는 보스의 사실이 아니라 파츠파괴
  의존 유닛의 상한/하한 모델 선택이다.

틀린 매핑은 값 검증을 전부 통과하고 조용히 초록으로 남는다.
````

- [ ] **Step 2: 스킬이 실제로 돌아가는지 확인한다**

새 세션에서 `/update-raid-bosses https://arca.live/b/nikketgv/177833660`을 실행해,
이미 들어 있는 `union-2026-07-31`과 같은 값이 나오는지 본다. 값이 다르면 스킬
문서의 판독 지시가 부족한 것이다.

- [ ] **Step 3: roadmap을 갱신한다**

`docs/roadmap.md`의 진행 상황 목록에 한 줄 더한다. 205행 근처의 "5속성 보스
프리셋(보스별 부위파괴/코어피격 특성 데이터 미확보)"이 이 작업과 이웃하므로 그
근처가 자리다.

```markdown
- **레이드 회차 보스 가져오기 착륙**(2026-08-07): 솔로/유니온 공지에서 읽은 이번
  회차 보스를 보스 설정 위에 카드로 띄운다. 판독은 `/update-raid-bosses` 스킬이
  하고 앱에는 OCR이 없다. **자동으로 채워지는 것은 약점 속성 하나**이고, 거리·
  스쿼드 추천·저지 부위는 공지 원문으로만 카드에 남는다(설계 D3 — 우리 플래그와
  같은 분류인지 미확인). 위 "5속성 보스 프리셋"의 미확보 항목(보스별 부위파괴/
  코어피격)은 **여전히 미확보다** — 공지가 그 둘을 주지 않는다.
  스펙: `docs/superpowers/specs/2026-08-07-raid-boss-rotation-import-design.md`,
  플랜: `docs/superpowers/plans/2026-08-07-raid-boss-rotation-import.md`.
```

기준선 숫자를 적어둔 줄이 있으면 다음 Step에서 나온 실제 값으로 갱신한다.

- [ ] **Step 4: 전체 스위트를 다시 돌린다**

Run: `cd backend && python3 -m pytest -q`
Expected: `1984 passed, 3 skipped`

Run: `cd frontend && npx vitest run`
Expected: `596 passed (61 files)`

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/update-raid-bosses/SKILL.md docs/roadmap.md
git commit -m "회차 보스 갱신 스킬

공지 URL을 주면 이미지를 읽어 data/raid-rotations.json에 반영한다. 공지가 그
단어로 적지 않은 것은 채우지 않는다는 규칙을 문서에 못박았다."
```

---

## 태스크 의존 관계

```
Task 1 (데이터+로더)
  └─ Task 2 (API)
       └─ Task 3 (타입·클라이언트·훅)
            ├─ Task 4 (피커 컴포넌트)
            │    └─ Task 5 (BossProfileField 합성)   ← D2가 지켜지는 곳
            │         └─ Task 6 (패널 배선·CSS)
            └─ Task 7 (스킬·문서) — Task 1 이후 언제든
```

Task 7은 Task 1의 스키마만 알면 되므로 병렬로 진행할 수 있다. 나머지는 순차다.
