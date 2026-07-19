# 유저 세션 북마크릿 로스터 동기화 구현 계획 (Phase 7 서브프로젝트 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유저가 자기 blablalink 세션으로 북마크릿을 눌러 로스터를 우리 사이트로 가져온다 — 우리는 어떤 자격증명도, 어떤 로스터도 저장하지 않는다.

**Architecture:** 북마크릿이 blablalink 페이지 컨텍스트에서 3개 API를 호출해 원시 payload를 얻고, `window.open` + `postMessage`로 우리 앱에 넘긴다. 앱은 그것을 무상태 백엔드 엔드포인트로 보내 조립된 `roster.json` 형태를 받아 기존 임포트 경로(`parseRosterJson` → `mergeCollectorDrafts` → `localStorage`)에 흘린다. 서버 저장 없음.

**Tech Stack:** FastAPI + Pydantic (백엔드), React + Vite + TypeScript + Vitest (프론트), pytest (백엔드 테스트).

설계: `docs/superpowers/specs/2026-07-19-roster-sync-bookmarklet-design.md`

## Global Constraints

- **프라이버시 (설계에서 못 박은 것, 위반 시 태스크 반려):** 원시 로스터를 어떤 형태로도 저장·로깅하지 않는다. `open_id`를 어떤 로그에도 남기지 않는다. 익명 클라이언트 ID를 로스터와 결합 저장하지 않는다.
- **북마크릿은 최대한 얇게.** 판단·조립·검증은 전부 서버로 미룬다. 로직을 바꾸면 전 유저가 북마크를 재설치해야 하므로 변경 빈도를 낮추는 것이 설계 요구사항이다.
- **blablalink origin은 `https://www.blablalink.com` 고정.** `nikke_area_id`는 `81` 고정 — 공유 URL 앞자리(예 `29080`)는 ShiftyPad 리전 id이지 이 값이 아니다.
- **테스트 실행:** 백엔드는 `backend/`에서 `python -m pytest` (이 머신에선 `~/anaconda3/python.exe -m pytest` — `C:\Python314`의 python엔 pytest가 없다). 프론트는 `frontend/`에서 `npm test`.
- **기존 패리티를 깨지 말 것.** 오버로드 77/77, 스탯 159/159 테스트는 이 작업 내내 통과해야 한다.
- 모바일은 비목표. 서버 저장·계정·소유권 증명도 비목표.

---

### Task 1: 백엔드 — 디렉토리 스냅샷 로더

`assemble_roster`는 디렉토리를 인자로 받는데, 지금은 테스트만 파일에서 읽고 앱 코드엔 로더가 없다. `stat_assembly.load_stat_tables`와 같은 패턴으로 추가한다.

**Files:**
- Modify: `backend/app/roster_assembly.py`
- Test: `backend/tests/test_roster_assembly.py`

**Interfaces:**
- Consumes: 없음
- Produces: `load_directory(path: Path = DIRECTORY) -> list[dict]`, 모듈 상수 `DIRECTORY: Path`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_roster_assembly.py` 끝에 추가:

```python
def test_load_directory_reads_the_committed_snapshot():
    """조립에 필요한 필드가 스냅샷에 실제로 있는지 — 신규 Nikke 갱신 누락을 잡는 가드."""
    from app.roster_assembly import load_directory

    directory = load_directory()
    assert len(directory) > 150
    ssr = [e for e in directory if e.get("original_rare") == "SSR"]
    assert len(ssr) > 150
    for key in ("name_en", "resource_id", "class", "corporation", "name_code"):
        assert all(e.get(key) not in (None, "") for e in directory), key
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && python -m pytest tests/test_roster_assembly.py::test_load_directory_reads_the_committed_snapshot -v`
Expected: FAIL — `ImportError: cannot import name 'load_directory'`

- [ ] **Step 3: 구현**

`backend/app/roster_assembly.py` 상단 import 아래에 추가:

```python
import json
from pathlib import Path

# The committed public directory snapshot: resource_id / name_code / class /
# corporation per unit. A Nikke released after this snapshot is absent, and
# assemble_roster skips it silently - refresh the snapshot when that happens
# (the sync endpoint's telemetry counts unknown name_codes for exactly this).
DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "tools" / "collect-blablalink" / "nikke-directory.json"
)


def load_directory(path: Path = DIRECTORY) -> list[dict]:
    """The directory snapshot assemble_roster joins owned units against."""
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && python -m pytest tests/test_roster_assembly.py -v`
Expected: PASS (기존 2개 + 신규 1개)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/roster_assembly.py backend/tests/test_roster_assembly.py
git commit -m "feat: load the committed directory snapshot from app code"
```

---

### Task 2: 백엔드 — `POST /api/assemble-roster`

원시 3 payload를 받아 조립된 `roster.json` 형태를 돌려주는 무상태 엔드포인트.

**Files:**
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_assemble_roster_api.py` (신규)

**Interfaces:**
- Consumes: `roster_assembly.load_directory`, `roster_assembly.assemble_roster`, `roster_assembly.to_roster_json`, `stat_assembly.load_stat_tables`
- Produces: `POST /api/assemble-roster`. 요청 본문 `{"owned": [...], "character_details": [...], "recycle_room_researches": [...]}`, 응답 `{"units": [...]}`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_assemble_roster_api.py` 신규 생성:

```python
"""The bookmarklet sync endpoint: raw blablalink payloads in, assembled roster out.

Assembly correctness is already covered by the 77/77 overload and 159/159 stat
parity suites; these tests cover the HTTP contract and the statelessness the
privacy posture depends on.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app

ROOT = Path(__file__).resolve().parents[2]
DETAILS = ROOT / "tools" / "collect-blablalink" / "details.json"

client = TestClient(app)


def test_assembles_a_real_payload_into_roster_units():
    if not DETAILS.exists():
        pytest.skip("local collector dumps not synced")
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    response = client.post("/api/assemble-roster", json={
        "owned": raw["owned"],
        "character_details": raw["character_details"],
        "recycle_room_researches": raw["recycle_room_researches"],
    })
    assert response.status_code == 200
    units = response.json()["units"]
    assert len(units) > 100
    first = units[0]
    assert first["raid400"]["atk"] > 0
    assert first["raid400"]["hp"] > 0
    assert "skill_levels" in first and "overload" in first


def test_an_account_with_no_research_rows_still_assembles():
    """멀티유저 전제조건: 미연구 계정도 크래시 없이 조립된다."""
    response = client.post("/api/assemble-roster", json={
        "owned": [], "character_details": [], "recycle_room_researches": [],
    })
    assert response.status_code == 200
    assert response.json() == {"units": []}


def test_a_missing_field_is_a_422_not_a_500():
    response = client.post("/api/assemble-roster", json={"owned": []})
    assert response.status_code == 422
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && python -m pytest tests/test_assemble_roster_api.py -v`
Expected: FAIL — 404 (라우트 없음)

- [ ] **Step 3: 구현**

`backend/app/api.py`의 import 블록에 추가:

```python
from app.roster_assembly import assemble_roster, load_directory, to_roster_json
from app.stat_assembly import load_stat_tables
```

모델 정의부(`RecommendRaidResponse` 아래)에 추가:

```python
class AssembleRosterRequest(BaseModel):
    """The three raw blablalink payloads the bookmarklet collects, verbatim."""
    owned: list[dict]
    character_details: list[dict]
    recycle_room_researches: list[dict]
```

`app = FastAPI(...)` 아래에 참조 데이터 로딩(프로세스당 1회) 추가:

```python
# Reference tables are read-only and identical for every request, so load once.
_STAT_TABLES = load_stat_tables()
_DIRECTORY = load_directory()
```

라우트 추가(파일 끝):

```python
@app.post("/api/assemble-roster")
def assemble_roster_endpoint(request: AssembleRosterRequest) -> dict:
    """Assemble a bookmarklet-collected roster. Stateless: the request body is
    never persisted - see the privacy posture in the sub-project 4 spec."""
    units = assemble_roster(_STAT_TABLES, _DIRECTORY, request.model_dump())
    return to_roster_json(units)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && python -m pytest tests/test_assemble_roster_api.py -v`
Expected: PASS (3개)

- [ ] **Step 5: 전체 스위트 확인**

Run: `cd backend && python -m pytest -q`
Expected: 기존 812 + 신규 4 = 816 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api.py backend/tests/test_assemble_roster_api.py
git commit -m "feat: stateless POST /api/assemble-roster for bookmarklet sync"
```

---

### Task 3: 백엔드 — 집계 텔레메트리

제품 개선용 집계만 남긴다. DB는 도입하지 않는다(모델 A) — 요청당 구조화된 로그 한 줄이면 나중에 로그 집계로 셀 수 있고, 그게 지금 필요한 전부다.

**Files:**
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_assemble_roster_api.py`

**Interfaces:**
- Consumes: Task 2의 엔드포인트
- Produces: 없음(로그만). 헤더 `X-Client-Id`를 선택적으로 읽는다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_assemble_roster_api.py`에 추가:

```python
import logging


def test_telemetry_logs_aggregates_but_never_the_roster_or_open_id(caplog):
    """프라이버시 규율: 집계 수치만, 원시 데이터·식별자는 절대 안 남는다."""
    payload = {
        "owned": [{"name_code": 5001, "lv": 400, "core": 3, "grade": 3}],
        "character_details": [{"name_code": 5001, "grade": 3, "core": 3}],
        "recycle_room_researches": [],
    }
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/assemble-roster", json=payload,
            headers={"X-Client-Id": "anon-abc"},
        )
    assert response.status_code == 200
    text = caplog.text
    assert "roster_sync" in text
    assert "anon-abc" in text          # 익명 id는 남는다
    assert "5001" not in text          # 원시 유닛 데이터는 안 남는다
    assert "intl_open_id" not in text  # open_id는 애초에 서버로 오지도 않는다
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && python -m pytest tests/test_assemble_roster_api.py::test_telemetry_logs_aggregates_but_never_the_roster_or_open_id -v`
Expected: FAIL — `assert "roster_sync" in text` 실패

- [ ] **Step 3: 구현**

`backend/app/api.py` 상단에 추가:

```python
import logging

logger = logging.getLogger(__name__)
```

라우트를 아래로 교체:

```python
@app.post("/api/assemble-roster")
def assemble_roster_endpoint(
    request: AssembleRosterRequest,
    x_client_id: str | None = Header(default=None),
) -> dict:
    """Assemble a bookmarklet-collected roster. Stateless: the request body is
    never persisted - see the privacy posture in the sub-project 4 spec."""
    units = assemble_roster(_STAT_TABLES, _DIRECTORY, request.model_dump())
    known = {e["name_code"] for e in _DIRECTORY}
    # Aggregates only. Counting unknown name_codes is how we learn the
    # directory snapshot has gone stale against a newly released Nikke.
    logger.info(
        "roster_sync client=%s owned=%d assembled=%d unknown_name_codes=%d",
        x_client_id or "none",
        len(request.owned),
        len(units),
        sum(1 for o in request.owned if o.get("name_code") not in known),
    )
    return to_roster_json(units)
```

`fastapi` import에 `Header`를 추가:

```python
from fastapi import FastAPI, Header, HTTPException
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && python -m pytest tests/test_assemble_roster_api.py -v`
Expected: PASS (4개)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api.py backend/tests/test_assemble_roster_api.py
git commit -m "feat: aggregate-only telemetry on the sync endpoint"
```

---

### Task 4: 프론트 — 공유 URL 파서

**Files:**
- Create: `frontend/src/lib/shareUrl.ts`
- Test: `frontend/src/lib/shareUrl.test.ts`

**Interfaces:**
- Produces: `parseShareUrl(url: string): string` — `intl_open_id`를 반환, 실패 시 `Error` throw

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/lib/shareUrl.test.ts`:

```typescript
import { describe, expect, it } from 'vitest'
import { parseShareUrl } from './shareUrl'

// uid는 "<shiftypad_region_id>-<intl_open_id>"의 base64. 앞자리는 ShiftyPad
// 리전 id이지 API의 nikke_area_id(81 고정)가 아니다.
const uid = btoa('29080-1234567890123456789')

describe('parseShareUrl', () => {
  it('대시 뒤 open_id만 취한다', () => {
    expect(parseShareUrl(`https://www.blablalink.com/shiftyspad?uid=${uid}`))
      .toBe('1234567890123456789')
  })

  it('open_id를 직접 붙여넣어도 받는다', () => {
    expect(parseShareUrl('1234567890123456789')).toBe('1234567890123456789')
  })

  it('uid가 없으면 거부한다', () => {
    expect(() => parseShareUrl('https://www.blablalink.com/shiftyspad'))
      .toThrow(/share URL/i)
  })

  it('디코드 결과가 예상 형태가 아니면 거부한다', () => {
    expect(() => parseShareUrl(`https://www.blablalink.com/shiftyspad?uid=${btoa('junk')}`))
      .toThrow(/share URL/i)
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm test -- shareUrl`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/lib/shareUrl.ts`:

```typescript
// ShiftyPad의 공개 공유 URL에서 intl_open_id를 뽑는다. uid는
// "<shiftypad_region_id>-<intl_open_id>"의 base64이고, 앞자리 리전 id는
// API가 받는 nikke_area_id(81 고정)와 무관하므로 버린다.

const OPEN_ID = /^\d{6,}$/

export const parseShareUrl = (input: string): string => {
  const trimmed = input.trim()
  if (OPEN_ID.test(trimmed)) return trimmed

  const uid = (() => {
    try {
      return new URL(trimmed).searchParams.get('uid')
    } catch {
      return null
    }
  })()
  if (!uid) throw new Error('Not a ShiftyPad share URL: no uid parameter.')

  let decoded: string
  try {
    decoded = atob(uid)
  } catch {
    throw new Error('Not a ShiftyPad share URL: uid is not base64.')
  }
  const openId = decoded.split('-').at(-1) ?? ''
  if (!OPEN_ID.test(openId)) {
    throw new Error('Not a ShiftyPad share URL: no open id inside uid.')
  }
  return openId
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm test -- shareUrl`
Expected: PASS (4개)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/shareUrl.ts frontend/src/lib/shareUrl.test.ts
git commit -m "feat: parse the ShiftyPad share URL into an open id"
```

---

### Task 5: 프론트 — 익명 클라이언트 ID

**Files:**
- Create: `frontend/src/lib/clientId.ts`
- Test: `frontend/src/lib/clientId.test.ts`

**Interfaces:**
- Produces: `getClientId(): string`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/lib/clientId.test.ts`:

```typescript
import { beforeEach, describe, expect, it } from 'vitest'
import { getClientId } from './clientId'

beforeEach(() => localStorage.clear())

describe('getClientId', () => {
  it('한 번 만들면 계속 같은 값을 준다', () => {
    expect(getClientId()).toBe(getClientId())
  })

  it('저장소를 비우면 새 값을 만든다', () => {
    const first = getClientId()
    localStorage.clear()
    expect(getClientId()).not.toBe(first)
  })

  it('게임 계정과 무관한 임의 값이다', () => {
    expect(getClientId()).toMatch(/^[0-9a-f-]{36}$/)
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm test -- clientId`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/lib/clientId.ts`:

```typescript
// 제품 개선용 익명 식별자. 게임 계정·open_id·로스터와 무관하며, 우리 백엔드로
// 가는 요청에만 실린다 (blablalink 호출에는 절대 싣지 않는다).

const STORAGE_KEY = 'nikke-client-id'

export const getClientId = (): string => {
  const existing = localStorage.getItem(STORAGE_KEY)
  if (existing) return existing
  const id = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, id)
  return id
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm test -- clientId`
Expected: PASS (3개)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/clientId.ts frontend/src/lib/clientId.test.ts
git commit -m "feat: anonymous client id for product analytics"
```

---

### Task 6: 프론트 — 조립 API 클라이언트

**Files:**
- Create: `frontend/src/api/assembleRoster.ts`
- Test: `frontend/src/api/assembleRoster.test.ts`

**Interfaces:**
- Consumes: `getClientId` (Task 5)
- Produces: `assembleRoster(payload: RawRosterPayload): Promise<unknown>`, `export interface RawRosterPayload { owned: unknown[]; character_details: unknown[]; recycle_room_researches: unknown[] }`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/api/assembleRoster.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from 'vitest'
import { assembleRoster } from './assembleRoster'

const payload = { owned: [], character_details: [], recycle_room_researches: [] }

afterEach(() => vi.restoreAllMocks())

describe('assembleRoster', () => {
  it('익명 id 헤더를 붙여 POST한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ units: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await assembleRoster(payload)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/assemble-roster')
    expect(init.method).toBe('POST')
    expect(init.headers['X-Client-Id']).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('실패 응답은 에러로 올린다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422 }))
    await expect(assembleRoster(payload)).rejects.toThrow(/422/)
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm test -- assembleRoster`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/api/assembleRoster.ts`:

```typescript
// 북마크릿이 모은 원시 payload를 백엔드에 조립시킨다. 백엔드는 이 본문을
// 저장하지 않는다 (무상태) - 서브프로젝트 4 스펙의 프라이버시 규율.

import { getClientId } from '../lib/clientId'

export interface RawRosterPayload {
  owned: unknown[]
  character_details: unknown[]
  recycle_room_researches: unknown[]
}

export const assembleRoster = async (
  payload: RawRosterPayload,
): Promise<unknown> => {
  const response = await fetch('/api/assemble-roster', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Client-Id': getClientId(),
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error(`assemble-roster failed: ${response.status}`)
  }
  return await response.json()
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm test -- assembleRoster`
Expected: PASS (2개)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/api/assembleRoster.ts frontend/src/api/assembleRoster.test.ts
git commit -m "feat: client for the stateless assemble-roster endpoint"
```

---

### Task 7: 프론트 — 북마크릿 생성기

북마크릿 본문을 만드는 순수 함수. **얇게 유지하는 것이 요구사항**이므로, 하는 일은 3콜 + postMessage뿐이다.

**Files:**
- Create: `frontend/src/lib/bookmarklet.ts`
- Test: `frontend/src/lib/bookmarklet.test.ts`

**Interfaces:**
- Produces: `buildBookmarklet(openId: string, appOrigin: string): string`, 상수 `BLABLALINK_ORIGIN = 'https://www.blablalink.com'`, `READY_MESSAGE = 'nikke-sync-ready'`, `PAYLOAD_MESSAGE = 'nikke-sync-payload'`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/lib/bookmarklet.test.ts`:

```typescript
import { describe, expect, it } from 'vitest'
import {
  BLABLALINK_ORIGIN,
  PAYLOAD_MESSAGE,
  buildBookmarklet,
} from './bookmarklet'

const code = buildBookmarklet('1234567890123456789', 'https://deck.example')
// 본문은 encodeURIComponent로 감싸여 있어 "://" 같은 문자가 %3A%2F%2F로 바뀐다.
// 따라서 내용 단언은 반드시 디코드한 소스에 대해 한다.
const source = decodeURIComponent(code.replace(/^javascript:/, ''))

describe('buildBookmarklet', () => {
  it('javascript: URL로 나온다', () => {
    expect(code.startsWith('javascript:')).toBe(true)
  })

  it('open_id와 앱 origin이 박힌다', () => {
    expect(source).toContain('1234567890123456789')
    expect(source).toContain('https://deck.example')
  })

  it('세 엔드포인트를 모두 부른다', () => {
    for (const ep of [
      'GetUserCharacters',
      'GetUserCharacterDetails',
      'GetUserProfileOutpostInfo',
    ]) {
      expect(source).toContain(ep)
    }
  })

  it('area 81과 blablalink origin 가드를 포함한다', () => {
    expect(source).toContain('nikke_area_id:81')
    expect(source).toContain(BLABLALINK_ORIGIN)
    expect(source).toContain(PAYLOAD_MESSAGE)
  })

  it('자격증명을 담지 않는다', () => {
    expect(source).not.toMatch(/password|token|cookie=/i)
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm test -- bookmarklet`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/lib/bookmarklet.ts`:

```typescript
// 유저의 blablalink 세션으로 3개 API를 호출해 원시 payload를 우리 앱에 넘기는
// 북마크릿. blablalink 페이지 컨텍스트에서 도는 것이 전제다 - 거기서만
// credentials:'include' fetch가 CORS를 통과한다(2026-07-19 실측).
//
// 외부 스크립트 로딩은 blablalink CSP의 script-src에 막힐 공산이 커서 로직이
// 인라인으로 강제되고, 따라서 이 코드를 바꾸면 전 유저가 북마크를 다시 깔아야
// 한다. 판단·조립·검증은 전부 서버로 미루고 여기는 얇게 유지할 것.

export const BLABLALINK_ORIGIN = 'https://www.blablalink.com'
export const READY_MESSAGE = 'nikke-sync-ready'
export const PAYLOAD_MESSAGE = 'nikke-sync-payload'

export const buildBookmarklet = (openId: string, appOrigin: string): string => {
  const source = `(async()=>{
if(location.origin!=='${BLABLALINK_ORIGIN}'){alert('blablalink 페이지에서 눌러주세요.');return}
const call=async(ep,body)=>{
 const r=await fetch('https://api.blablalink.com/api/game/proxy/Game/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'include'});
 const j=await r.json();
 if(j.code!==0)throw new Error(ep+':'+j.code);
 return j.data};
const base={intl_open_id:'${openId}',nikke_area_id:81};
try{
 const owned=(await call('GetUserCharacters',{...base})).characters||[];
 const detail=await call('GetUserCharacterDetails',{...base,name_codes:owned.map(c=>c.name_code)});
 const outpost=await call('GetUserProfileOutpostInfo',{...base});
 const payload={owned:owned,character_details:detail.character_details||[],recycle_room_researches:((outpost.outpost_info||{}).recycle_room_researches)||[]};
 const w=window.open('${appOrigin}');
 if(!w){alert('팝업이 차단됐어요. 차단을 해제하고 다시 눌러주세요.');return}
 window.addEventListener('message',e=>{
  if(e.origin==='${appOrigin}'&&e.data&&e.data.type==='${READY_MESSAGE}'){
   w.postMessage({type:'${PAYLOAD_MESSAGE}',payload:payload},'${appOrigin}')}})
}catch(err){
 const m=String(err);
 alert(m.indexOf('300001')>=0?'blablalink 로그인이 필요해요.':(m.indexOf('1303005')>=0||m.indexOf(':1')>=0)?'공유 URL을 다시 확인해주세요.':'가져오기 실패: '+m)}
})()`
  return 'javascript:' + encodeURIComponent(source)
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm test -- bookmarklet`
Expected: PASS (5개)

> 참고: `encodeURIComponent`는 `://`를 `%3A%2F%2F`로 바꾸므로 **인코딩된 문자열에 대한 origin 단언은 반드시 실패한다**(실측 확인). 위 테스트가 디코드한 `source`에 대해 단언하는 이유다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/bookmarklet.ts frontend/src/lib/bookmarklet.test.ts
git commit -m "feat: generate the personalised sync bookmarklet"
```

---

### Task 8: 프론트 — postMessage 수신 훅

**Files:**
- Create: `frontend/src/hooks/useBookmarkletImport.ts`
- Test: `frontend/src/hooks/useBookmarkletImport.test.ts`

**Interfaces:**
- Consumes: `BLABLALINK_ORIGIN`/`READY_MESSAGE`/`PAYLOAD_MESSAGE` (Task 7), `assembleRoster` (Task 6), `parseRosterJson` (`../lib/rosterImport`)
- Produces: `useBookmarkletImport(onRoster: (raw: unknown) => void): { status: 'idle' | 'importing' | 'done' | 'error'; error: string | null }`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/hooks/useBookmarkletImport.test.ts`:

```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useBookmarkletImport } from './useBookmarkletImport'
import { BLABLALINK_ORIGIN, PAYLOAD_MESSAGE } from '../lib/bookmarklet'
import { assembleRoster } from '../api/assembleRoster'

// 이 코드베이스의 모킹 관례는 vi.mock + vi.mocked다 (RecommendPanel.test.tsx 참고).
// ESM 명명 export는 vi.spyOn으로 가로챌 수 없다.
vi.mock('../api/assembleRoster', () => ({
  assembleRoster: vi.fn(),
}))

const EMPTY = { owned: [], character_details: [], recycle_room_researches: [] }

const post = (origin: string, data: unknown) =>
  window.dispatchEvent(new MessageEvent('message', { origin, data }))

beforeEach(() => vi.mocked(assembleRoster).mockReset())

describe('useBookmarkletImport', () => {
  it('blablalink에서 온 payload를 조립해 넘긴다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))

    post(BLABLALINK_ORIGIN, { type: PAYLOAD_MESSAGE, payload: EMPTY })

    await waitFor(() => expect(onRoster).toHaveBeenCalledWith({ units: [] }))
  })

  it('다른 출처의 메시지는 무시한다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))

    post('https://evil.example', { type: PAYLOAD_MESSAGE, payload: EMPTY })

    await new Promise((r) => setTimeout(r, 10))
    expect(assembleRoster).not.toHaveBeenCalled()
    expect(onRoster).not.toHaveBeenCalled()
  })

  it('조립 실패는 error 상태로 드러난다', async () => {
    vi.mocked(assembleRoster).mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useBookmarkletImport(vi.fn()))

    post(BLABLALINK_ORIGIN, { type: PAYLOAD_MESSAGE, payload: EMPTY })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toContain('boom')
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm test -- useBookmarkletImport`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/hooks/useBookmarkletImport.ts`:

```typescript
// 북마크릿이 window.open으로 연 우리 페이지에서 원시 payload를 받는다.
// 마운트 시 opener에게 ready를 알리고, blablalink 출처의 payload 메시지만
// 받아들여 백엔드 조립을 거쳐 onRoster로 넘긴다.

import { useCallback, useEffect, useState } from 'react'
import { assembleRoster, type RawRosterPayload } from '../api/assembleRoster'
import {
  BLABLALINK_ORIGIN,
  PAYLOAD_MESSAGE,
  READY_MESSAGE,
} from '../lib/bookmarklet'

type Status = 'idle' | 'importing' | 'done' | 'error'

export const useBookmarkletImport = (onRoster: (raw: unknown) => void) => {
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)

  const handle = useCallback(
    async (payload: RawRosterPayload) => {
      setStatus('importing')
      setError(null)
      try {
        onRoster(await assembleRoster(payload))
        setStatus('done')
      } catch (e) {
        setError(String(e))
        setStatus('error')
      }
    },
    [onRoster],
  )

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      if (event.origin !== BLABLALINK_ORIGIN) return
      const data = event.data as { type?: string; payload?: RawRosterPayload }
      if (data?.type !== PAYLOAD_MESSAGE || !data.payload) return
      void handle(data.payload)
    }
    window.addEventListener('message', listener)
    // 북마크릿은 이 창이 뜬 뒤에야 payload를 보낼 수 있으므로 준비됐음을 알린다.
    window.opener?.postMessage({ type: READY_MESSAGE }, BLABLALINK_ORIGIN)
    return () => window.removeEventListener('message', listener)
  }, [handle])

  return { status, error }
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm test -- useBookmarkletImport`
Expected: PASS (3개)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/hooks/useBookmarkletImport.ts frontend/src/hooks/useBookmarkletImport.test.ts
git commit -m "feat: receive the bookmarklet payload over postMessage"
```

---

### Task 9: 프론트 — 동기화 패널 UI + 앱 배선

**Files:**
- Create: `frontend/src/components/SyncRosterPanel.tsx`
- Test: `frontend/src/components/SyncRosterPanel.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `parseShareUrl` (Task 4), `buildBookmarklet` (Task 7), `useBookmarkletImport` (Task 8), `parseRosterJson`, `importDrafts` (기존 `useRoster`)
- Produces: `<SyncRosterPanel onImport={...} />`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/components/SyncRosterPanel.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SyncRosterPanel } from './SyncRosterPanel'

const uid = btoa('29080-1234567890123456789')
const shareUrl = `https://www.blablalink.com/shiftyspad?uid=${uid}`

describe('SyncRosterPanel', () => {
  it('공유 URL을 넣으면 북마크릿 링크가 나온다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/share url/i), {
      target: { value: shareUrl },
    })
    const link = screen.getByRole('link', { name: /roster/i })
    expect(link.getAttribute('href')).toContain('javascript:')
    expect(link.getAttribute('href')).toContain('1234567890123456789')
  })

  it('잘못된 URL은 에러를 보여주고 링크를 만들지 않는다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/share url/i), {
      target: { value: 'https://example.com' },
    })
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.queryByRole('link', { name: /roster/i })).toBeNull()
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm test -- SyncRosterPanel`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/components/SyncRosterPanel.tsx`:

```tsx
// blablalink 동기화 안내: 공유 URL -> 개인화 북마크릿 링크 -> (유저가 blablalink에서
// 클릭) -> postMessage 수신 -> 로스터 병합. 자격증명은 어디에도 저장하지 않는다.

import { useState } from 'react'
import { parseShareUrl } from '../lib/shareUrl'
import { buildBookmarklet } from '../lib/bookmarklet'
import { useBookmarkletImport } from '../hooks/useBookmarkletImport'
import { parseRosterJson } from '../lib/rosterImport'
import type { NikkeDraft } from '../types/nikkeDraft'

interface SyncRosterPanelProps {
  onImport: (
    drafts: NikkeDraft[],
    source: 'exia' | 'collector',
  ) => { added: number; updated: number }
}

export function SyncRosterPanel({ onImport }: SyncRosterPanelProps) {
  const [openId, setOpenId] = useState<string | null>(null)
  const [urlError, setUrlError] = useState<string | null>(null)
  const [summary, setSummary] = useState<string | null>(null)

  const { status, error } = useBookmarkletImport((raw) => {
    const { drafts } = parseRosterJson(raw)
    const { added, updated } = onImport(drafts, 'collector')
    setSummary(`${added} added, ${updated} updated`)
  })

  const handleUrl = (value: string) => {
    if (!value.trim()) {
      setOpenId(null)
      setUrlError(null)
      return
    }
    try {
      setOpenId(parseShareUrl(value))
      setUrlError(null)
    } catch (e) {
      setOpenId(null)
      setUrlError(String(e))
    }
  }

  return (
    <section className="sync">
      <h2>Sync from blablalink</h2>
      <label htmlFor="share-url">ShiftyPad share URL</label>
      <input
        id="share-url"
        type="text"
        onChange={(e) => handleUrl(e.target.value)}
        placeholder="https://www.blablalink.com/shiftyspad?uid=..."
      />
      {urlError && <p role="alert">{urlError}</p>}
      {openId && (
        <>
          <p>
            아래 링크를 북마크바로 드래그한 뒤, blablalink에 로그인한 상태에서
            눌러주세요.
          </p>
          <a href={buildBookmarklet(openId, window.location.origin)}>
            Sync NIKKE roster
          </a>
        </>
      )}
      {status === 'importing' && <p>가져오는 중…</p>}
      {summary && <p>{summary}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
```

`frontend/src/App.tsx` 수정 — import 추가:

```tsx
import { SyncRosterPanel } from './components/SyncRosterPanel'
```

`<ImportRosterButton onImport={importDrafts} />` 바로 아래에 추가:

```tsx
        <SyncRosterPanel onImport={importDrafts} />
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm test`
Expected: 전체 PASS (기존 112 + 신규 19 = 131)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/SyncRosterPanel.tsx frontend/src/components/SyncRosterPanel.test.tsx frontend/src/App.tsx
git commit -m "feat: blablalink sync panel wired into the app"
```

---

### Task 10: 수동 스모크 + 문서

북마크릿은 브라우저 밖에서 테스트할 수 없으므로(설계상 알려진 한계) 실계정 1회 검증이 필수다.

**Files:**
- Modify: `docs/roadmap.md`, `docs/superpowers/specs/2026-07-19-roster-sync-bookmarklet-design.md`
- Modify: `frontend/README.md`

- [ ] **Step 1: 백엔드 기동**

```bash
cd backend && python -m uvicorn app.api:app --reload
```

- [ ] **Step 2: 프론트 기동**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: 실계정 스모크**

1. 앱에서 Fienn의 ShiftyPad 공유 URL 입력 → 북마크릿 링크가 나오는지 확인
2. 링크를 북마크바로 드래그
3. `https://www.blablalink.com/shiftyspad/nikke?nikke=16` 열기 (로그인 상태)
4. 북마크 클릭
5. 새 탭이 열리고 로스터가 병합되는지 확인

기대: 159 내외의 유닛이 들어오고 ATK/HP가 채워짐. **팝업 차단 동작을 여기서 확인한다**(스펙의 미확인 항목).

- [ ] **Step 4: 결과를 스펙에 기록**

스펙의 "위험과 남은 미지수" 표에서 팝업 차단 행을 실측 결과로 갱신하고, 문서 상단 상태를 "구현 완료"로 바꾼다.

- [ ] **Step 5: 로드맵 갱신**

`docs/roadmap.md`의 Phase 7 항목에 서브프로젝트 4 완료와 **서브프로젝트 3(소유권 증명) 불필요로 소멸**을 반영한다.

- [ ] **Step 6: 커밋**

```bash
git add docs/roadmap.md docs/superpowers/specs/2026-07-19-roster-sync-bookmarklet-design.md frontend/README.md
git commit -m "docs: bookmarklet sync verified end to end"
```

---

## 남은 수동 항목 (이 계획 범위 밖)

- **개인정보 처리방침 문서** — 공개 배포 전 필요(스펙에 명시, 법률 검토는 범위 밖).
- **디렉토리 스냅샷 갱신 루틴** — 신규 Nikke 출시 시. Task 3의 `unknown_name_codes` 카운터가 신호를 준다.
- **배포 인프라** — 현재 리모트·배포 없음. 모델 A는 정적 호스팅 + 기존 API로 충분.
