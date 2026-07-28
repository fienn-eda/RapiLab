# 고정 편성 평가 · 유니온 레이드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유저가 직접 짠 고정 편성 N개를 (덱마다 자기 보스로) 채점해 기대 딜량을 돌려주는 평가 전용 경로를 만들고, 그 위에 추천 탭 `평가` 모드와 유니온 레이드 탭을 얹는다.

**Architecture:** 새 딜 계산을 만들지 않는다. 기존 `deck_allocation._best_ordering_summary`(고정 5인의 티어 내 최적 순서를 골라 요약)를 public으로 승격하고, 신규 `app/deck_evaluation.py`가 덱마다 자기 보스로 그걸 호출해 합산한다. 탐색·배분·스왑이 전부 없다. 프론트는 새 엔드포인트 하나(`POST /api/evaluate-decks`)를 화면 둘이 공유한다.

**Tech Stack:** Python 3 · FastAPI · pydantic · pytest / React 19 · TypeScript · Vite · Vitest · @testing-library/react

## Global Constraints

설계 스펙 `docs/superpowers/specs/2026-07-28-fixed-deck-evaluation-design.md`(Status: 승인됨)의 결정을 그대로 따른다. 아래는 모든 태스크에 암묵적으로 적용된다.

- **새 엔진 표면 금지.** 계산 경로는 `evaluate_decks` → `best_ordering_summary` → `evaluate_deck` → `simulate_raid`로 기존 세 모드와 동일해야 한다. 딜을 계산하는 두 번째 코드 경로를 만들지 않는다.
- **보스 스키마는 갈라지지 않는다.** 백엔드는 기존 `BossProfileIn` pydantic 모델을, 프론트는 기존 `BossProfileField` 컴포넌트를 덱별 보스에도 **그대로 재사용**한다. 보스 필드를 어디서도 다시 선언하지 않는다.
- **편성 순서는 엔진이 고른다.** 유저는 소속만 정한다(`DraftEditor`의 기존 계약: "Slots are MEMBERSHIP ONLY"). 응답의 `deck` 배열이 엔진이 고른 순서다.
- **덱 간 중복 편성 불가.** 솔로 5덱과 유니온 3덱 모두 동일.
- **유니온 전투 시간 기본값 180초.**
- **UI 문구는 한글, 캐주얼-정중체**(`~해요`/`~돼요`). 프로젝트 기준은 `frontend/src/lib/bookmarklet.ts`. 격식체(`~됨`/`~습니다`) 금지 — 과거 리뷰가 세 번 잡아낸 결함이다.
- **CLAUDE.md 규칙:** 주석은 무엇을·왜만 쓴다. "예전엔 이랬다"/"이걸 바꿨다" 류의 변경 이력을 코드 주석에 쓰지 않는다.
- 백엔드 기준선 **1413 passed, 3 skipped** · 프론트 기준선 **350 passed**. 태스크마다 이 수치가 줄지 않아야 한다.

## 파일 구조

**신규 (백엔드)**
- `backend/app/engine_version.py` — 엔진 소스의 내용 해시. 책임: "지금 이 엔진이 어떤 버전인가" 하나.
- `backend/app/deck_evaluation.py` — 고정 편성 N개를 덱별 보스로 채점. 책임: 평가. 배분·탐색을 절대 하지 않는다.
- `backend/tests/test_engine_version.py`, `backend/tests/test_deck_evaluation.py`, `backend/tests/test_api_evaluate_decks.py`

**수정 (백엔드)**
- `backend/app/deck_allocation.py` — `_best_ordering_summary` → `best_ordering_summary` 승격(호출부 2곳)
- `backend/app/api.py` — 요청/응답 모델 + `POST /api/evaluate-decks` + `GET /api/engine-version` + 기존 두 응답에 `engine_version`

**신규 (프론트)**
- `frontend/src/types/evaluate.ts` — 평가 API 와이어 타입 + 유니온 상수
- `frontend/src/api/evaluateDecks.ts` — 타입드 클라이언트
- `frontend/src/api/engineVersion.ts` — `GET /api/engine-version` 클라이언트
- `frontend/src/hooks/useEvaluateDecks.ts`, `frontend/src/hooks/useEngineVersion.ts`
- `frontend/src/components/EvaluationResults.tsx` — 평가 결과 렌더 (두 화면 공용)
- `frontend/src/components/UnionRaidPanel.tsx` — 유니온 레이드 탭
- 각각의 `.test.ts(x)`

**수정 (프론트)**
- `frontend/src/components/DraftEditor.tsx` — `showLocks?: boolean` 추가
- `frontend/src/lib/inputHash.ts` — 해시에 `engineVersion` 포함
- `frontend/src/components/RecommendPanel.tsx` — 4번째 모드 `평가`
- `frontend/src/App.tsx` — 3번째 탭 `유니온 레이드`
- `frontend/src/types/recommend.ts` — 응답에 `engine_version`
- `frontend/README.md` · `docs/roadmap.md`

### 계획 중 발견한 스펙 갭 (Fienn 확인 필요, Task 2에 반영)

스펙은 "세 엔드포인트 응답에 `engine_version` 추가"라고만 했다. 그런데 프론트는 **요청을 보내기 전에** 캐시를 조회하므로 해시를 만들 시점에 버전을 이미 알고 있어야 한다 — 응답으로만 받으면 닭-달걀이다. 그래서 `GET /api/engine-version`을 하나 더 만든다(App 마운트 시 1회 조회, `useSupportedUnits`와 같은 패턴). 버전을 아직 모르는 동안에는 해시에 `null`이 들어가고, 버전이 도착하면 해시가 바뀌어 캐시가 **한 번** 미스한다 — 의도된 동작이며 대가는 재계산 한 번이다.

---

### Task 1: 엔진 버전 = 소스 내용 해시

**Files:**
- Create: `backend/app/engine_version.py`
- Test: `backend/tests/test_engine_version.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `hash_sources(root: pathlib.Path) -> str` — `root` 아래 모든 `.py`의 경로+바이트로 만든 SHA-256 앞 12자
  - `engine_version() -> str` — `hash_sources(backend/app)`, 프로세스당 1회 캐시

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_engine_version.py`:

```python
"""엔진 버전은 손으로 올리는 숫자가 아니라 소스의 내용 해시다 - 올리는 걸
잊어서 캐시가 조용히 낡는 실패 모드를 없애는 것이 이 모듈의 존재 이유다."""
from app.engine_version import engine_version, hash_sources


def test_same_sources_hash_the_same(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    assert hash_sources(tmp_path) == hash_sources(tmp_path)


def test_changed_source_changes_the_hash(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    before = hash_sources(tmp_path)
    (tmp_path / "a.py").write_text("x = 2\n")
    assert hash_sources(tmp_path) != before


def test_new_module_changes_the_hash(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    before = hash_sources(tmp_path)
    (tmp_path / "b.py").write_text("x = 1\n")
    assert hash_sources(tmp_path) != before


def test_renaming_a_module_changes_the_hash(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    before = hash_sources(tmp_path)
    (tmp_path / "a.py").rename(tmp_path / "c.py")
    assert hash_sources(tmp_path) != before


def test_nested_packages_are_included(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text("x = 1\n")
    before = hash_sources(tmp_path)
    (tmp_path / "pkg" / "m.py").write_text("x = 2\n")
    assert hash_sources(tmp_path) != before


def test_non_python_files_are_ignored(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    before = hash_sources(tmp_path)
    (tmp_path / "notes.txt").write_text("hello\n")
    assert hash_sources(tmp_path) == before


def test_engine_version_is_short_stable_and_hex():
    version = engine_version()
    assert len(version) == 12
    assert all(c in "0123456789abcdef" for c in version)
    assert version == engine_version()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_engine_version.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.engine_version'`

- [ ] **Step 3: 최소 구현**

`backend/app/engine_version.py`:

```python
"""이 엔진이 계산한 결과를 다른 엔진의 결과와 구별하는 문자열.

클라이언트는 결과를 입력 해시로 캐싱한다. 입력만으로는 부족하다 - 엔진이
바뀌면 같은 입력이 다른 답을 내는데, 캐시는 그걸 모르고 낡은 수치를 계속
보여준다. 버전을 해시에 섞으면 엔진이 바뀌는 순간 전 캐시가 미스가 된다.

값은 손으로 올리는 숫자가 아니라 소스의 내용 해시다: 올리는 걸 잊는 순간
이 모듈이 막으려던 실패가 그대로 재발하기 때문이다. 딜에 영향을 주는 모듈만
고르지 않고 `app/` 전체를 해시하는 이유도 같다 - 새 모듈을 목록에 넣는 걸
잊을 수 있다. API 문구만 고쳐도 버전이 바뀌어 재계산 한 번이 더 생기지만,
그 대가는 수 초이고 실패 방향이 안전한 쪽이다.
"""
import hashlib
from functools import lru_cache
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent

# 12자 = 48비트. 충돌하면 낡은 캐시를 한 번 더 보여주는 것이 전부이고,
# 이 값은 URL도 파일명도 아닌 캐시 키의 한 조각이라 이 정도면 충분하다.
_VERSION_LENGTH = 12


def hash_sources(root: Path) -> str:
    """`root` 아래 모든 `.py`의 상대 경로와 바이트를 이어 만든 다이제스트.

    경로도 해시에 넣는 이유: 내용이 같은 모듈의 이름만 바뀌어도 엔진은
    달라진 것이다(등록·임포트 경로가 바뀐다). 경로 정렬은 OS의 파일 순회
    순서에 기대지 않도록 POSIX 문자열 기준으로 한다.
    """
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py"),
                       key=lambda p: p.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:_VERSION_LENGTH]


@lru_cache(maxsize=1)
def engine_version() -> str:
    """이 프로세스가 돌리고 있는 엔진의 버전. 소스는 실행 중 바뀌지 않으므로
    한 번만 읽는다."""
    return hash_sources(_APP_DIR)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_engine_version.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/engine_version.py backend/tests/test_engine_version.py
git commit -m "Version the engine by hashing its own source"
```

---

### Task 2: 세 엔드포인트에 `engine_version` 노출 + `GET /api/engine-version`

**Files:**
- Modify: `backend/app/api.py` (`RecommendResponse`, `RecommendRaidResponse`, 두 `_*_sync` 반환부, 새 라우트)
- Modify: `frontend/src/types/recommend.ts` (응답 타입에 `engine_version`)
- Test: `backend/tests/test_engine_version_endpoint.py`

**Interfaces:**
- Consumes: Task 1의 `engine_version() -> str`
- Produces:
  - `GET /api/engine-version` → `{"engine_version": "<12자>"}`
  - `RecommendResponse.engine_version: str` · `RecommendRaidResponse.engine_version: str`
  - TS: `RecommendResponse.engine_version: string` · `RecommendRaidResponse.engine_version: string`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_engine_version_endpoint.py`:

```python
"""엔진 버전은 결과 캐시의 무효화 축이다. 클라이언트는 요청을 보내기 전에
캐시를 조회하므로 GET으로도 받을 수 있어야 하고, 응답에 실린 값과 같아야
한다 - 두 값이 어긋나면 캐시가 영원히 미스하거나 영원히 낡는다."""
from fastapi.testclient import TestClient

from app.api import app
from app.engine_version import engine_version

client = TestClient(app)


def test_engine_version_endpoint_returns_the_running_version():
    response = client.get("/api/engine-version")
    assert response.status_code == 200
    assert response.json() == {"engine_version": engine_version()}


def test_recommend_reports_the_same_version_as_the_endpoint():
    roster = [{"character_slug": s} for s in
              ("liter", "blanc", "crown", "modernia", "privaty")]
    response = client.post("/api/recommend",
                           json={"roster": roster, "boss": {}, "top_n": 1})
    assert response.status_code == 200
    assert response.json()["engine_version"] == engine_version()


def test_recommend_raid_reports_the_same_version_as_the_endpoint():
    roster = [{"character_slug": s} for s in
              ("liter", "blanc", "crown", "modernia", "privaty")]
    response = client.post("/api/recommend-raid",
                           json={"roster": roster, "boss": {}, "num_decks": 1})
    assert response.status_code == 200
    assert response.json()["engine_version"] == engine_version()
```

주의: 위 5개 슬러그는 `/api/supported-units`가 실제로 내주는 로더블 유닛이어야 한다. 먼저 `cd backend && python -c "from app.supported_units import supported_units as s; print([u['slug'] for u in s()][:20])"`로 확인하고, B1·B2·B3가 모두 들어간 5명으로 고른다(그렇지 않으면 422 "no feasible deck"이 난다). 기존 `backend/tests/test_api_recommend_raid_draft.py`가 쓰는 로스터 픽스처를 그대로 빌려도 된다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_engine_version_endpoint.py -v`
Expected: FAIL — `GET /api/engine-version`이 404, 응답에 `engine_version` 키 없음

- [ ] **Step 3: 최소 구현**

`backend/app/api.py`:

임포트에 추가:

```python
from app.engine_version import engine_version
```

`RecommendResponse`에 필드 추가:

```python
class RecommendResponse(BaseModel):
    decks: list[DeckRecommendation]
    excluded_slugs: list[str]
    # 클라이언트가 결과를 입력 해시로 캐싱한다. 어떤 엔진이 낸 답인지 같이
    # 실어주지 않으면 엔진을 고친 뒤에도 낡은 수치가 캐시에서 계속 나온다.
    engine_version: str
```

`RecommendRaidResponse`에도 같은 필드를 추가(주석은 반복하지 말고 `engine_version: str`만).

`_recommend_sync`의 `return RecommendResponse(...)`에 `engine_version=engine_version()` 추가.
`_recommend_raid_sync`의 `return RecommendRaidResponse(...)`에도 `engine_version=engine_version()` 추가.

새 라우트를 `supported_units_route` 옆에 추가:

```python
@app.get("/api/engine-version")
def engine_version_route() -> dict[str, str]:
    """클라이언트는 요청을 보내기 전에 결과 캐시를 조회하므로, 버전을 응답으로만
    받으면 조회 시점에 알 수가 없다. 그래서 GET으로도 낸다."""
    return {"engine_version": engine_version()}
```

`frontend/src/types/recommend.ts`의 `RecommendResponse`와 `RecommendRaidResponse`에 각각 추가:

```typescript
  // 이 결과를 낸 엔진의 버전 — 결과 캐시의 무효화 축(lib/inputHash.ts).
  engine_version: string
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_engine_version_endpoint.py -v`
Expected: PASS (3 tests)

Run: `cd backend && python -m pytest -q`
Expected: 기준선(1413 passed, 3 skipped)보다 줄지 않고, 신규 테스트만큼 늘어난다

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 클린

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api.py backend/tests/test_engine_version_endpoint.py frontend/src/types/recommend.ts
git commit -m "Report the engine version on every recommendation surface"
```

---

### Task 3: `best_ordering_summary` public 승격

**Files:**
- Modify: `backend/app/deck_allocation.py:171`, `:381`, `:391`

**Interfaces:**
- Consumes: 없음
- Produces: `deck_allocation.best_ordering_summary(units, boss, pool=None) -> dict` — 기존 `_best_ordering_summary`와 동작 동일. 반환 dict는 `_summarize`의 계약(`deck`(정렬된 슬러그) · `total_damage` · `burst_damage` · `normal_attack_damage` · `skill_damage` · `result`).

- [ ] **Step 1: 기존 테스트가 그린인지 먼저 확인한다**

Run: `cd backend && python -m pytest tests/test_deck_allocation.py tests/test_recommend_from_draft.py -q`
Expected: PASS — 이 태스크는 순수 이름 변경이므로 시작점이 그린이어야 의미가 있다

- [ ] **Step 2: 이름을 바꾼다**

`backend/app/deck_allocation.py`에서 정의(391행)와 호출부 2곳(171행, 381행)의 `_best_ordering_summary`를 `best_ordering_summary`로 바꾼다. 함수 본문·독스트링·주석은 손대지 않는다.

Run: `cd backend && grep -rn "_best_ordering_summary" backend/ ; true`
Expected: 아무것도 안 나온다 (밑줄 붙은 이름이 남아 있지 않다)

- [ ] **Step 3: 테스트가 여전히 그린인지 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: Task 2 직후와 정확히 같은 수치 (순수 이름 변경이므로 단 하나도 달라지면 안 된다)

- [ ] **Step 4: 커밋**

```bash
git add backend/app/deck_allocation.py
git commit -m "Make the fixed-deck scorer part of the module's public surface"
```

---

### Task 4: `evaluate_decks` — 덱별 보스로 고정 편성 채점

**Files:**
- Create: `backend/app/deck_evaluation.py`
- Test: `backend/tests/test_deck_evaluation.py`

**Interfaces:**
- Consumes: Task 3의 `deck_allocation.best_ordering_summary` · `deck_allocation._seed_choices` · `deck_search._intra_tier_orderings`
- Produces:
  - `class InfeasibleDeck(ValueError)` — 속성 `deck_index: int`
  - `evaluate_decks(decks, bosses, alternatives=None) -> dict`
    - `decks: list[list[spec]]` (각 5명) · `bosses: list[BossProfile]` (같은 길이)
    - 반환 `{"decks": [<best_ordering_summary 반환 dict>, ...], "combined_total_damage": float}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_deck_evaluation.py`:

```python
"""고정 편성 평가: 탐색도 배분도 없이, 덱마다 자기 보스로 채점하고 합산한다.
덱끼리 상호작용이 없다는 것이 합산의 근거이므로, 덱별 보스가 서로에게 새지
않는다는 것이 여기서 가장 중요한 성질이다. 시뮬은 스텁 - 실제 시뮬은 API
엔드투엔드 테스트에서 돈다."""
import pytest

import app.deck_allocation as da
import app.deck_search as ds
from app.deck_evaluation import InfeasibleDeck, evaluate_decks
from app.deck_search import BossProfile
from tests.test_deck_allocation import roster_of


def patch_boss_aware_scorer(monkeypatch, scorer):
    """`scorer(slugs, boss) -> float`. best_ordering_summary는 evaluate_deck을
    직접(da 바인딩) 그리고 _score_batch를 통해(ds 바인딩) 모두 부르므로 둘 다
    패치한다 - tests/test_deck_allocation.py의 patch_scorer와 같은 이유."""
    def fake_evaluate(ordered_deck, boss):
        return {"total_damage": scorer({u.slug for u in ordered_deck}, boss),
                "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", fake_evaluate)
    monkeypatch.setattr(da, "evaluate_deck", fake_evaluate)


def _deck(roster, *slugs):
    by_slug = {u.slug: u for u in roster}
    return [by_slug[s] for s in slugs]


def _two_decks():
    roster = roster_of({
        "t1a": 1, "t2a": 2, "t3a1": 3, "t3a2": 3, "t3a3": 3,
        "t1b": 1, "t2b": 2, "t3b1": 3, "t3b2": 3, "t3b3": 3,
    })
    return roster, [_deck(roster, "t1a", "t2a", "t3a1", "t3a2", "t3a3"),
                    _deck(roster, "t1b", "t2b", "t3b1", "t3b2", "t3b3")]


def test_combined_total_is_the_sum_of_the_decks(monkeypatch):
    patch_boss_aware_scorer(monkeypatch, lambda slugs, boss: 10.0)
    _, decks = _two_decks()

    out = evaluate_decks(decks, [BossProfile(), BossProfile()])

    assert [d["total_damage"] for d in out["decks"]] == [10.0, 10.0]
    assert out["combined_total_damage"] == 20.0


def test_each_deck_is_scored_against_its_own_boss(monkeypatch):
    # 1번 덱만 Iron 보스, 2번 덱은 Water. 스코어러가 보스 속성으로 갈리므로
    # 보스가 덱을 가로질러 새면 두 값이 같아진다.
    patch_boss_aware_scorer(
        monkeypatch, lambda slugs, boss: 100.0 if boss.element == "Iron" else 1.0)
    _, decks = _two_decks()

    out = evaluate_decks(decks, [BossProfile(element="Iron"),
                                 BossProfile(element="Water")])

    assert [d["total_damage"] for d in out["decks"]] == [100.0, 1.0]
    assert out["combined_total_damage"] == 101.0


def test_returned_deck_is_the_best_intra_tier_ordering(monkeypatch):
    # 같은 5인이라도 t3a1이 t3a2보다 앞설 때만 높은 점수가 나오게 만든다.
    def score(slugs, boss):
        return 10.0

    def fake_evaluate(ordered_deck, boss):
        order = [u.slug for u in ordered_deck]
        bonus = 5.0 if order.index("t3a1") < order.index("t3a2") else 0.0
        return {"total_damage": 10.0 + bonus, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", fake_evaluate)
    monkeypatch.setattr(da, "evaluate_deck", fake_evaluate)
    roster, decks = _two_decks()

    out = evaluate_decks(decks[:1], [BossProfile()])

    deck = out["decks"][0]["deck"]
    assert deck.index("t3a1") < deck.index("t3a2")
    assert out["decks"][0]["total_damage"] == 15.0


def test_infeasible_deck_names_its_index(monkeypatch):
    patch_boss_aware_scorer(monkeypatch, lambda slugs, boss: 10.0)
    roster, decks = _two_decks()
    # 2번 덱을 전부 B3로 채우면 legal한 티어 배치가 없다.
    all_tier3 = roster_of({"x1": 3, "x2": 3, "x3": 3, "x4": 3, "x5": 3})

    with pytest.raises(InfeasibleDeck) as excinfo:
        evaluate_decks([decks[0], all_tier3],
                       [BossProfile(), BossProfile()])

    assert excinfo.value.deck_index == 1


def test_mode_variant_seat_is_scored_at_its_best_reading(monkeypatch):
    # 한 좌석이 두 후보(-mg / -snipe)를 갖는다. -snipe가 더 세므로 그쪽이 채택돼야
    # 한다 - baseline_total_damage가 쓰는 것과 같은 기준.
    patch_boss_aware_scorer(
        monkeypatch, lambda slugs, boss: 100.0 if "v-snipe" in slugs else 10.0)
    roster = roster_of({"t1a": 1, "t2a": 2, "t3a1": 3, "t3a2": 3,
                        "v-mg": 3, "v-snipe": 3})
    by_slug = {u.slug: u for u in roster}
    deck = [by_slug[s] for s in ("t1a", "t2a", "t3a1", "t3a2", "v-mg")]
    alternatives = {"v-mg": (by_slug["v-mg"], by_slug["v-snipe"])}

    out = evaluate_decks([deck], [BossProfile()], alternatives=alternatives)

    assert out["decks"][0]["total_damage"] == 100.0
    assert "v-snipe" in out["decks"][0]["deck"]


def test_deck_and_boss_counts_must_match():
    with pytest.raises(ValueError):
        evaluate_decks([[]], [BossProfile(), BossProfile()])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_deck_evaluation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.deck_evaluation'`

- [ ] **Step 3: 최소 구현**

`backend/app/deck_evaluation.py`:

```python
"""유저가 이미 짜놓은 고정 편성 N개를, 덱마다 자기 보스로 채점한다.

`deck_allocation`과의 차이는 방향이다. 저기는 로스터에서 덱을 만들어내고,
여기는 만들어진 덱을 채점만 한다 - 탐색도, 배분도, 스왑도 없다. 그래서
덱끼리 상호작용이 없고, 합계는 덱별 점수의 단순 합이며, 덱마다 보스가 달라도
그 성질이 그대로 성립한다(유니온 레이드가 그 경우다).

채점은 `deck_allocation.best_ordering_summary`에 위임한다. 딜을 계산하는 두
번째 경로를 만들지 않는 것이 이 모듈의 설계 제약이다 - 엔진을 고쳤을 때 평가
결과가 추천 결과와 어긋나면 유저가 두 수치 중 어느 쪽도 믿을 수 없게 된다.
"""
from app.deck_allocation import _seed_choices, best_ordering_summary
from app.deck_search import _intra_tier_orderings


class InfeasibleDeck(ValueError):
    """이 5인으로는 legal한 버스트 티어 배치가 하나도 없다. `deck_index`는
    호출자가 유저에게 몇 번째 덱인지 말해줄 수 있게 들고 있는 값이다."""

    def __init__(self, deck_index: int):
        super().__init__(f"deck {deck_index} has no feasible burst-tier ordering")
        self.deck_index = deck_index


def evaluate_decks(decks, bosses, alternatives=None):
    """`decks[i]`를 `bosses[i]`로 채점한 요약들과 그 합계.

    `alternatives`는 엔진이 여러 모드로 모델링하는 캐릭터(MODE_VARIANTS)의
    좌석을 위한 것이다. 어떤 모드로 도는지는 유저가 고르는 것이 아니므로
    모든 해석을 채점해 최선을 채택한다 - `recommend_from_draft`의
    `baseline_total_damage`가 쓰는 것과 같은 기준이라, 두 화면의 수치가 서로
    비교 가능하게 남는다.
    """
    if len(decks) != len(bosses):
        raise ValueError(f"got {len(decks)} decks but {len(bosses)} bosses")

    summaries = []
    for index, (deck, boss) in enumerate(zip(decks, bosses)):
        readings = _seed_choices(deck, alternatives)
        # 어떤 해석으로도 legal한 배치가 없을 때만 불가능한 덱이다. 좌석의
        # 모드는 티어를 바꿀 수 있으므로(VARIANT_BURST_TIERS) 해석마다 따로 본다.
        scored = [best_ordering_summary(reading, boss) for reading in readings
                  if next(_intra_tier_orderings(reading), None) is not None]
        if not scored:
            raise InfeasibleDeck(index)
        summaries.append(max(scored, key=lambda s: s["total_damage"]))

    return {"decks": summaries,
            "combined_total_damage": sum(s["total_damage"] for s in summaries)}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_deck_evaluation.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/deck_evaluation.py backend/tests/test_deck_evaluation.py
git commit -m "Score fixed decks, each against its own boss"
```

---

### Task 5: `POST /api/evaluate-decks`

**Files:**
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_api_evaluate_decks.py`

**Interfaces:**
- Consumes: Task 4의 `evaluate_decks` · `InfeasibleDeck`, Task 1의 `engine_version`
- Produces: `POST /api/evaluate-decks`. 요청 `{roster, decks:[{units:[slug×5], boss:BossProfileIn}]}` → 응답 `{decks:[DeckRecommendation], combined_total_damage, excluded_slugs, engine_version}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_api_evaluate_decks.py`:

```python
"""POST /api/evaluate-decks - 탐색 없는 평가 전용 경로. 실제 시뮬을 돌린다
(스텁 없음): 이 엔드포인트가 추천 경로와 같은 프리미티브를 쓴다는 주장은
스텁으로는 검증되지 않는다."""
from fastapi.testclient import TestClient

from app.api import app
from app.engine_version import engine_version

client = TestClient(app)

# B1/B2/B3를 모두 덮는 실제 로더블 유닛 5명. 확인:
#   python -c "from app.supported_units import supported_units as s; \
#              print(sorted((u['burst_tier'], u['slug']) for u in s()))"
DECK = ["liter", "blanc", "crown", "modernia", "privaty"]
ROSTER = [{"character_slug": s} for s in DECK]


def _request(decks, roster=None):
    return {"roster": roster if roster is not None else ROSTER, "decks": decks}


def test_evaluates_one_deck_and_reports_the_engine_version():
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": DECK, "boss": {}}]))

    assert response.status_code == 200
    body = response.json()
    assert len(body["decks"]) == 1
    deck = body["decks"][0]
    assert sorted(deck["deck"]) == sorted(DECK)
    assert deck["total_damage"] > 0
    # _summarize의 계약: 세 갈래가 총딜을 남김없이 덮는다.
    assert (deck["burst_damage"] + deck["normal_attack_damage"]
            + deck["skill_damage"]) == deck["total_damage"]
    assert body["combined_total_damage"] == deck["total_damage"]
    assert body["excluded_slugs"] == []
    assert body["engine_version"] == engine_version()


def test_matches_the_draft_baseline_for_the_same_deck_and_boss():
    """같은 편성·같은 보스라면 평가 경로와 추천 경로의 baseline은 같은
    프리미티브를 통과하므로 정확히 같은 값이어야 한다. 두 경로가 갈라지면
    이 테스트가 먼저 터진다."""
    boss = {"element": "Iron"}
    evaluated = client.post(
        "/api/evaluate-decks",
        json=_request([{"units": DECK, "boss": boss}])).json()
    drafted = client.post("/api/recommend-raid", json={
        "roster": ROSTER, "boss": boss, "num_decks": 1,
        "draft": [{"units": [{"slug": s} for s in DECK]}],
    }).json()

    assert evaluated["combined_total_damage"] == drafted["baseline_total_damage"]


def test_boss_element_changes_the_result():
    iron = client.post("/api/evaluate-decks",
                       json=_request([{"units": DECK, "boss": {"element": "Iron"}}])).json()
    none = client.post("/api/evaluate-decks",
                       json=_request([{"units": DECK, "boss": {}}])).json()

    assert iron["combined_total_damage"] != none["combined_total_damage"]


def test_rejects_an_empty_deck_list():
    response = client.post("/api/evaluate-decks", json=_request([]))
    assert response.status_code == 422


def test_rejects_a_deck_that_is_not_five_units():
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": DECK[:4], "boss": {}}]))
    assert response.status_code == 422
    assert "1번" in response.json()["detail"]


def test_rejects_a_slug_used_in_two_decks():
    roster = [{"character_slug": s} for s in DECK + ["rouge", "volume", "mint", "grave", "noir"]]
    second = ["liter", "rouge", "volume", "mint", "grave"]
    response = client.post("/api/evaluate-decks", json=_request(
        [{"units": DECK, "boss": {}}, {"units": second, "boss": {}}], roster=roster))

    assert response.status_code == 422
    assert "liter" in response.json()["detail"]


def test_rejects_a_slug_the_engine_cannot_use():
    response = client.post("/api/evaluate-decks", json=_request(
        [{"units": ["not-a-nikke"] + DECK[1:], "boss": {}}]))

    assert response.status_code == 422
    assert "not-a-nikke" in response.json()["detail"]


def test_rejects_a_deck_with_no_feasible_burst_ordering():
    """B1이 없는 5인은 legal한 배치가 없다."""
    b3_only = ["modernia", "privaty", "noir", "grave", "mint"]
    roster = [{"character_slug": s} for s in b3_only]
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": b3_only, "boss": {}}], roster=roster))

    assert response.status_code == 422
    assert "1번" in response.json()["detail"]
```

주의: `DECK`·`b3_only`·중복 테스트의 여분 슬러그는 **실제 로더블 유닛이어야** 하고 티어 구성이 주석대로여야 한다. 테스트를 쓰기 전에 위 주석의 `python -c` 명령으로 슬러그별 `burst_tier`를 출력해 확인하고, 맞지 않으면 그 목록에서 골라 교체한다. `b3_only`는 전원 B3여야 한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_api_evaluate_decks.py -v`
Expected: FAIL — 404 (라우트 없음)

- [ ] **Step 3: 최소 구현**

`backend/app/api.py`. 임포트에 추가:

```python
from app.deck_evaluation import InfeasibleDeck, evaluate_decks
```

모델을 `RecommendRaidResponse` 아래에 추가:

```python
class EvaluateDeckIn(BaseModel):
    """평가할 고정 편성 하나와 그 덱이 맞설 보스.

    보스가 덱 안에 있는 이유는 유니온 레이드다 - 3회 전투의 보스 속성을 유저가
    전투마다 고른다. 필드를 다시 선언하지 않고 BossProfileIn을 그대로 품어서,
    엔진이 보스 플래그를 늘려도 고칠 곳이 한 군데로 남는다."""
    units: list[str]
    boss: BossProfileIn


class EvaluateDecksRequest(BaseModel):
    roster: list[UserNikkeState]
    decks: list[EvaluateDeckIn]


class EvaluateDecksResponse(BaseModel):
    # pinned_slugs도 leftover_slugs도 없다: 잠금은 최적화의 개념이고, 안 고른
    # 유닛은 클라이언트가 이미 아는 것이라 배분 결과와 달리 알려줄 것이 없다.
    decks: list[DeckRecommendation]
    combined_total_damage: float
    excluded_slugs: list[str]
    engine_version: str
```

동기 핸들러를 `_recommend_raid_sync` 아래에 추가:

```python
def _evaluate_decks_sync(request: EvaluateDecksRequest, cancel) -> EvaluateDecksResponse:
    _reject_unknown_overload_options(request.roster)
    specs, excluded = load_roster(request.roster)
    if not request.decks:
        raise HTTPException(422, "평가할 덱이 없어요.")

    by_slug = {u.slug: u for u in specs}
    alternatives = {}
    for base, variants in MODE_VARIANTS.items():
        loadable = tuple(by_slug[v] for v in variants if v in by_slug)
        if base not in by_slug and loadable:
            alternatives[base] = loadable

    decks, bosses, requested = [], [], []
    for index, deck_in in enumerate(request.decks, start=1):
        if len(deck_in.units) != DECK_SIZE:
            raise HTTPException(
                422, f"{index}번 덱은 {len(deck_in.units)}명이에요. 덱마다 정확히 "
                     f"{DECK_SIZE}명이어야 해요.")
        seat = []
        for slug in deck_in.units:
            options = alternatives.get(slug)
            if options is None and slug not in by_slug:
                raise HTTPException(422, f"엔진이 쓸 수 없는 슬러그예요: {slug}")
            seat.append(options[0] if options else by_slug[slug])
            requested.append(slug)
        decks.append(seat)
        bosses.append(BossProfile(
            element=deck_in.boss.element,
            core_hittable=deck_in.boss.core_hittable,
            enemy_def=deck_in.boss.enemy_def,
            fight_duration=deck_in.boss.fight_duration,
            part_destructible=deck_in.boss.part_destructible,
        ))

    # 클라가 보낸 슬러그로 보고한다 - 해석된 대표 슬러그를 들이대면 유저가
    # 자기가 안 쓴 이름을 보게 된다.
    if len(requested) != len(set(requested)):
        dups = sorted({s for s in requested if requested.count(s) > 1})
        raise HTTPException(422, f"여러 덱에 겹쳐 들어간 니케가 있어요: {dups}")

    alternatives = {options[0].slug: options for options in alternatives.values()}
    try:
        out = evaluate_decks(decks, bosses, alternatives=alternatives)
    except InfeasibleDeck as e:
        raise HTTPException(
            422, f"{e.deck_index + 1}번 덱은 버스트 단계 조합이 성립하지 않아요 "
                 f"(1·2·3단계가 모두 필요해요).")

    return EvaluateDecksResponse(
        decks=[DeckRecommendation(
            deck=d["deck"], total_damage=d["total_damage"],
            burst_damage=d["burst_damage"],
            normal_attack_damage=d["normal_attack_damage"],
            skill_damage=d["skill_damage"]) for d in out["decks"]],
        combined_total_damage=out["combined_total_damage"],
        excluded_slugs=excluded,
        engine_version=engine_version(),
    )
```

`DECK_SIZE = 5`를 `DISCONNECT_POLL_SEC` 근처의 모듈 상수 옆에 둔다 (주석: `# 니케 한 덱은 5명 - 엔진의 고정 덱 크기.`).

라우트를 `recommend_raid` 아래에 추가:

```python
@app.post("/api/evaluate-decks", response_model=EvaluateDecksResponse)
async def evaluate_decks_route(
    request: EvaluateDecksRequest, http_request: Request
) -> EvaluateDecksResponse:
    return await _run_cancellable(http_request, _evaluate_decks_sync, request)
```

`cancel` 인자는 `_run_cancellable`의 계약이라 받되, 이 경로는 몇 초짜리라 SimPool을 만들지 않으므로 토큰에 붙일 풀이 없다. `_evaluate_decks_sync`의 시그니처에 `cancel`을 두고 쓰지 않는 것이 맞다 — 주석으로 이유를 남긴다:

```python
    # 평가는 탐색이 없어 수 초에 끝난다. SimPool을 만들지 않으므로 토큰에
    # 접을 풀도 없다 - 인자는 _run_cancellable의 계약을 맞추기 위한 것.
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_api_evaluate_decks.py -v`
Expected: PASS (8 tests)

Run: `cd backend && python -m pytest -q`
Expected: 기준선 대비 감소 없음

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api.py backend/tests/test_api_evaluate_decks.py
git commit -m "Add the fixed-deck evaluation endpoint"
```

---

### Task 6: 프론트 와이어 타입 + API 클라이언트 + 훅

**Files:**
- Create: `frontend/src/types/evaluate.ts`
- Create: `frontend/src/api/evaluateDecks.ts`, `frontend/src/api/engineVersion.ts`
- Create: `frontend/src/hooks/useEvaluateDecks.ts`, `frontend/src/hooks/useEvaluateDecks.test.ts`
- Create: `frontend/src/hooks/useEngineVersion.ts`, `frontend/src/hooks/useEngineVersion.test.ts`

**Interfaces:**
- Consumes: Task 5의 `POST /api/evaluate-decks`, Task 2의 `GET /api/engine-version`
- Produces:
  - `EvaluateDeckInput { units: string[]; boss: BossProfile }`
  - `EvaluateDecksRequest { roster: UserNikkeState[]; decks: EvaluateDeckInput[] }`
  - `EvaluateDecksResponse { decks: DeckRecommendation[]; combined_total_damage: number; excluded_slugs: string[]; engine_version: string }`
  - `UNION_RAID_NUM_DECKS = 3` · `DEFAULT_UNION_NUM_DECKS = 3` · `MIN_UNION_NUM_DECKS = 1`
  - `evaluateDecks(request, signal?) => Promise<EvaluateDecksResponse>`
  - `fetchEngineVersion(signal?) => Promise<string>`
  - `useEvaluateDecks(): { status, decks, combinedTotalDamage, excludedSlugs, error?, cancel, submit }`
  - `useEngineVersion(): string | null`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/hooks/useEvaluateDecks.test.ts` — 기존 `useRecommendRaid.test.ts`의 구조를 그대로 따른다(같은 모킹 방식, 같은 단언 스타일). 먼저 그 파일을 읽고 패턴을 맞출 것.

```typescript
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useEvaluateDecks } from './useEvaluateDecks'
import * as client from '../api/evaluateDecks'
import { RecommendApiError } from '../api/recommendApiError'
import type { EvaluateDecksRequest } from '../types/evaluate'

const REQUEST: EvaluateDecksRequest = {
  roster: [{ character_slug: 'liter' }],
  decks: [{
    units: ['liter', 'blanc', 'crown', 'modernia', 'privaty'],
    boss: { element: 'Iron', core_hittable: false, enemy_def: 0, fight_duration: 180, part_destructible: false },
  }],
}

const RESPONSE = {
  decks: [{ deck: ['liter', 'blanc', 'crown', 'modernia', 'privaty'],
            total_damage: 100, burst_damage: 60, normal_attack_damage: 30, skill_damage: 10 }],
  combined_total_damage: 100,
  excluded_slugs: [],
  engine_version: 'abcdef012345',
}

afterEach(() => vi.restoreAllMocks())

describe('useEvaluateDecks', () => {
  it('성공하면 덱과 합계를 노출한다', async () => {
    vi.spyOn(client, 'evaluateDecks').mockResolvedValue(RESPONSE)
    const { result } = renderHook(() => useEvaluateDecks())

    await act(async () => { await result.current.submit(REQUEST) })

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.combinedTotalDamage).toBe(100)
    expect(result.current.decks).toHaveLength(1)
    expect(result.current.excludedSlugs).toEqual([])
  })

  it('422의 detail을 에러 메시지로 드러낸다', async () => {
    vi.spyOn(client, 'evaluateDecks').mockRejectedValue(
      new RecommendApiError(422, { detail: '1번 덱은 4명이에요.' }))
    const { result } = renderHook(() => useEvaluateDecks())

    await act(async () => { await result.current.submit(REQUEST) })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toContain('1번 덱')
  })
})
```

`frontend/src/hooks/useEngineVersion.test.ts`:

```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useEngineVersion } from './useEngineVersion'
import * as client from '../api/engineVersion'

afterEach(() => vi.restoreAllMocks())

describe('useEngineVersion', () => {
  it('가져오기 전에는 null이고, 도착하면 버전을 준다', async () => {
    vi.spyOn(client, 'fetchEngineVersion').mockResolvedValue('abcdef012345')
    const { result } = renderHook(() => useEngineVersion())

    expect(result.current).toBeNull()
    await waitFor(() => expect(result.current).toBe('abcdef012345'))
  })

  it('가져오기가 실패해도 null로 남고 던지지 않는다', async () => {
    vi.spyOn(client, 'fetchEngineVersion').mockRejectedValue(new Error('offline'))
    const { result } = renderHook(() => useEngineVersion())

    await waitFor(() => expect(result.current).toBeNull())
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/hooks/useEvaluateDecks.test.ts src/hooks/useEngineVersion.test.ts`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 최소 구현**

`frontend/src/types/evaluate.ts`:

```typescript
// POST /api/evaluate-decks의 와이어 타입.
// SOURCE OF TRUTH: backend/app/api.py (EvaluateDecksRequest / EvaluateDecksResponse).
//
// /api/recommend-raid와의 차이는 방향이다. 저기는 엔진이 덱을 짜주고, 여기는
// 유저가 짠 덱을 채점만 한다 - 그래서 잠금도, 남은 유닛도, 대안 배치도 없다.
// 보스가 요청 하나에 하나가 아니라 덱마다 하나인 것도 여기뿐이다: 유니온
// 레이드는 3회 전투의 보스 속성을 유저가 전투마다 고른다.

import type { UserNikkeState } from './userNikkeState'
import type { BossProfile, DeckRecommendation } from './recommend'

export interface EvaluateDeckInput {
  units: string[] // 정확히 5개 슬러그. 소속만 — 자리 순서는 버스트 순서가 아니다.
  boss: BossProfile
}

export interface EvaluateDecksRequest {
  roster: UserNikkeState[]
  decks: EvaluateDeckInput[]
}

export interface EvaluateDecksResponse {
  // 각 덱의 `deck`은 엔진이 고른 최적 순서다 — 유저가 넣은 순서가 아니다.
  decks: DeckRecommendation[]
  combined_total_damage: number
  excluded_slugs: string[]
  engine_version: string
}

/** 유니온 레이드는 3회 전투다. 한 전투만 계산해보고 싶을 때를 위해 아래로 열어둔다. */
export const MIN_UNION_NUM_DECKS = 1
export const MAX_UNION_NUM_DECKS = 3
export const DEFAULT_UNION_NUM_DECKS = 3
```

`frontend/src/api/evaluateDecks.ts` — `api/recommendRaid.ts`를 그대로 본뜨되 URL과 타입만 바꾼다. 타임아웃은 마찬가지로 걸지 않는다(설정하지 않는다는 결정이 아니라, `signal`이 유저의 취소를 담당한다는 같은 계약이다).

```typescript
// POST /api/evaluate-decks의 타입드 클라이언트. api/recommendRaid.ts와 같은
// 계약을 따른다: 타임아웃 없음(마감을 걸면 잘 돌고 있는 실행을 끊는다),
// 호출자의 `signal`이 유저의 취소를 담당하고, 연결이 끊기면 서버도 멈춘다.
// 평가는 탐색이 없어 수 초에 끝나므로 대기 안내가 배분만큼 절실하지는 않다.

import type { EvaluateDecksRequest, EvaluateDecksResponse } from '../types/evaluate'
import { RecommendApiError } from './recommendApiError'

export const evaluateDecks = async (
  request: EvaluateDecksRequest,
  signal?: AbortSignal,
): Promise<EvaluateDecksResponse> => {
  const response = await fetch('/api/evaluate-decks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return (await response.json()) as EvaluateDecksResponse
}
```

`frontend/src/api/engineVersion.ts`:

```typescript
// GET /api/engine-version. 결과 캐시를 조회하는 시점(요청을 보내기 전)에
// 버전을 이미 알고 있어야 해서, 응답에 실려 오는 것과 별개로 이 GET이 있다.

export const fetchEngineVersion = async (signal?: AbortSignal): Promise<string> => {
  const response = await fetch('/api/engine-version', { signal })
  if (!response.ok) throw new Error(`engine-version failed: ${response.status}`)
  const body = (await response.json()) as { engine_version: string }
  return body.engine_version
}
```

`frontend/src/hooks/useEvaluateDecks.ts` — `useRecommendRaid.ts`를 본뜨되 상태는 셋(decks / combinedTotalDamage / excludedSlugs)뿐이다.

```typescript
// POST /api/evaluate-decks 제출의 요청/로딩/에러/결과 상태. useRecommendRaid와
// 같은 useAsyncRequestStatus 위에 서지만, 결과가 훨씬 얇다 - 평가에는 대안
// 배치도, 남은 유닛도, 잠금도 없다.

import { useCallback, useState } from 'react'
import { evaluateDecks } from '../api/evaluateDecks'
import type { DeckRecommendation } from '../types/recommend'
import type { EvaluateDecksRequest } from '../types/evaluate'
import { useAsyncRequestStatus, type RequestStatus } from './useAsyncRequestStatus'

export interface EvaluateDecksState {
  status: RequestStatus
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  excludedSlugs: string[]
  error?: string
  cancel: () => void
  submit: (request: EvaluateDecksRequest) => Promise<void>
}

const FALLBACK_ERROR_MESSAGE = '기대 딜량을 계산하지 못했어요.'

export const useEvaluateDecks = (): EvaluateDecksState => {
  const [decks, setDecks] = useState<DeckRecommendation[]>([])
  const [combinedTotalDamage, setCombinedTotalDamage] = useState(0)
  const [excludedSlugs, setExcludedSlugs] = useState<string[]>([])
  const { status, error, run, cancel } = useAsyncRequestStatus()

  const submit = useCallback(
    (request: EvaluateDecksRequest) =>
      run(
        (signal) => evaluateDecks(request, signal),
        (response) => {
          setDecks(response.decks)
          setCombinedTotalDamage(response.combined_total_damage)
          setExcludedSlugs(response.excluded_slugs)
        },
        FALLBACK_ERROR_MESSAGE,
      ),
    [run],
  )

  return { status, decks, combinedTotalDamage, excludedSlugs, error, cancel, submit }
}
```

주의: `useAsyncRequestStatus`의 `run` 시그니처를 먼저 읽고 정확히 맞춘다 (`useRecommendRaid.ts`가 쓰는 형태 그대로).

`frontend/src/hooks/useEngineVersion.ts`:

```typescript
// 지금 백엔드가 돌리는 엔진의 버전. 마운트 시 1회 가져오고, 실패하면 null로
// 남는다 - 버전을 모른다고 추천을 못 쓰게 만들 이유는 없다. null이면 캐시
// 키에 null이 들어가고, 버전이 도착한 뒤 한 번 미스한 다음부터 정상이다.

import { useEffect, useState } from 'react'
import { fetchEngineVersion } from '../api/engineVersion'

export const useEngineVersion = (): string | null => {
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchEngineVersion(controller.signal)
      .then(setVersion)
      .catch(() => {})
    return () => controller.abort()
  }, [])

  return version
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/hooks/useEvaluateDecks.test.ts src/hooks/useEngineVersion.test.ts`
Expected: PASS

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 클린

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/types/evaluate.ts frontend/src/api/evaluateDecks.ts frontend/src/api/engineVersion.ts frontend/src/hooks/useEvaluateDecks.ts frontend/src/hooks/useEvaluateDecks.test.ts frontend/src/hooks/useEngineVersion.ts frontend/src/hooks/useEngineVersion.test.ts
git commit -m "Add the evaluation client, its hook and the engine-version probe"
```

---

### Task 7: 결과 캐시 키에 엔진 버전을 섞는다

**Files:**
- Modify: `frontend/src/lib/inputHash.ts`
- Modify: `frontend/src/lib/inputHash.test.ts`
- Modify: `frontend/src/components/RecommendPanel.tsx` (호출부 + 새 prop)
- Modify: `frontend/src/App.tsx` (prop 전달)
- Modify: `frontend/src/components/RecommendPanel.test.tsx` (새 prop 반영)

**Interfaces:**
- Consumes: Task 6의 `useEngineVersion`
- Produces: `hashRecommendInputs(roster, boss, draft, numDecks, engineVersion: string | null) -> string` · `RecommendPanelProps.engineVersion: string | null`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/lib/inputHash.test.ts`에 추가 (기존 테스트는 인자가 하나 늘었으므로 전부 갱신해야 한다 — 먼저 파일을 읽고 기존 호출을 모두 새 시그니처로 고친 뒤 아래를 덧붙인다):

```typescript
  it('엔진 버전이 다르면 해시가 달라진다', () => {
    const a = hashRecommendInputs(ROSTER, BOSS, null, 5, 'aaaaaaaaaaaa')
    const b = hashRecommendInputs(ROSTER, BOSS, null, 5, 'bbbbbbbbbbbb')
    expect(a).not.toBe(b)
  })

  it('엔진 버전이 같으면 해시가 같다', () => {
    const a = hashRecommendInputs(ROSTER, BOSS, null, 5, 'aaaaaaaaaaaa')
    const b = hashRecommendInputs(ROSTER, BOSS, null, 5, 'aaaaaaaaaaaa')
    expect(a).toBe(b)
  })

  it('버전을 모르는 상태(null)도 자기들끼리는 일관된 키를 만든다', () => {
    const a = hashRecommendInputs(ROSTER, BOSS, null, 5, null)
    const b = hashRecommendInputs(ROSTER, BOSS, null, 5, null)
    expect(a).toBe(b)
    expect(a).not.toBe(hashRecommendInputs(ROSTER, BOSS, null, 5, 'aaaaaaaaaaaa'))
  })
```

`ROSTER`/`BOSS`는 그 파일에 이미 있는 픽스처 이름을 쓴다 — 없으면 기존 테스트가 쓰는 리터럴을 그대로 옮겨 상수로 만든다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/lib/inputHash.test.ts`
Expected: FAIL — 인자 개수 불일치 / 새 단언 실패

- [ ] **Step 3: 최소 구현**

`frontend/src/lib/inputHash.ts` 헤더 주석의 첫 문단을 다음으로 교체한다(엔진이 결정론적이라는 서술만으로는 캐시 무효화 근거가 되지 못한다는 점을 명시):

```typescript
// recommend-raid 요청의 결정론적 캐시 키. 엔진에 RNG가 없으므로 같은 로스터
// 투자 데이터·보스 프로필·드래프트·엔진 버전이면 언제나 같은 결과가 나온다 -
// 이 해시로 재계산을 건너뛴다. 엔진 버전이 키에 들어가는 것이 핵심이다:
// 입력만으로 만든 키는 엔진을 고친 뒤에도 낡은 수치를 캐시에서 내준다.
// 결과에 영향을 주지 않는 순서(로스터 배열 순서, 드래프트 덱 안의 좌석 순서)는
// 정규화해 일부러 충돌시키고, 객체 키 순서도 정규화해 구조가 같은 값은 언제나
// 같게 직렬화되게 한다.
```

시그니처와 본문:

```typescript
export const hashRecommendInputs = (
  roster: UserNikkeState[],
  boss: BossProfile,
  draft: Draft | null,
  numDecks: number,
  /** 백엔드에서 아직 못 받았으면 null. null끼리는 일관되므로 그 동안에도 캐시는
   * 동작하고, 버전이 도착하면 한 번 미스한 뒤 정상으로 돌아온다. */
  engineVersion: string | null,
): string => {
  const canonical = {
    roster: canonicalRoster(roster),
    boss: canonicalize(boss),
    draft: canonicalDraft(draft),
    numDecks,
    engineVersion,
  }
  return fnv1a(JSON.stringify(canonical))
}
```

`RecommendPanel.tsx`: props 인터페이스에 추가

```typescript
  /** 결과 캐시의 무효화 축 — lib/inputHash.ts. 아직 못 받았으면 null. */
  engineVersion: string | null
```

그리고 `hashRecommendInputs(effectiveRoster, bossProfile, draftForHash, numDecks)` 호출에 `, engineVersion`을 더한다.

`App.tsx`: `const engineVersion = useEngineVersion()`을 다른 훅들 옆에 두고 `<RecommendPanel ... engineVersion={engineVersion} />`로 넘긴다.

`RecommendPanel.test.tsx`: 렌더 헬퍼가 props를 조립하는 곳에 `engineVersion: null`(또는 고정 문자열)을 더한다. 파일을 먼저 읽고 헬퍼 한 곳만 고치면 되는지 확인한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run`
Expected: 기준선 350 passed 이상, 0 failed

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 클린

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/inputHash.ts frontend/src/lib/inputHash.test.ts frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/App.tsx
git commit -m "Key the result cache on the engine that produced it"
```

---

### Task 8: `DraftEditor`에 `showLocks` 옵션

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx`
- Modify: `frontend/src/components/DraftEditor.test.tsx`

**Interfaces:**
- Consumes: 없음
- Produces: `DraftEditorProps.showLocks?: boolean` (기본 `true`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/DraftEditor.test.tsx`에 추가. 잠금 버튼을 찾는 방식은 그 파일의 기존 테스트가 쓰는 셀렉터를 그대로 따른다(먼저 읽을 것 — `aria-pressed` 기반일 가능성이 높다).

```typescript
  it('showLocks가 false면 잠금 토글을 그리지 않는다', () => {
    renderEditor({ showLocks: false, value: draftWithOneUnit })
    expect(screen.queryByRole('button', { pressed: false })).toBeNull()
  })

  it('기본값에서는 잠금 토글이 그대로 있다', () => {
    renderEditor({ value: draftWithOneUnit })
    expect(screen.getByRole('button', { pressed: false })).toBeTruthy()
  })
```

`renderEditor`/`draftWithOneUnit`은 그 파일에 이미 있는 헬퍼/픽스처 이름으로 맞춘다. 잠금 버튼 외에 `pressed` 속성을 가진 버튼이 슬롯에 또 있으면 셀렉터를 `aria-label` 기반으로 좁힌다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/DraftEditor.test.tsx`
Expected: FAIL — `showLocks`가 무시되어 버튼이 여전히 그려진다

- [ ] **Step 3: 최소 구현**

`DraftEditorProps`에 추가:

```typescript
  /** 잠금은 최적화의 개념이라 편성을 채점만 하는 화면에는 고정할 것이 없다.
   * 기본은 켜짐 — 드래프트 모드가 원래 쓰던 동작이다. */
  showLocks?: boolean
```

컴포넌트 시그니처에서 `showLocks = true`로 기본값을 받고, 잠금 버튼을 그리는 JSX를 `{showLocks && ( ... )}`로 감싼다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/DraftEditor.test.tsx`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx
git commit -m "Let the draft editor hide locks where they mean nothing"
```

---

### Task 9: `EvaluationResults` — 평가 결과 렌더

**Files:**
- Create: `frontend/src/components/EvaluationResults.tsx`, `frontend/src/components/EvaluationResults.test.tsx`

**Interfaces:**
- Consumes: Task 6의 타입, 기존 `DeckCard` · `ExcludedSlugsNote` · `formatDamage`
- Produces: `<EvaluationResults decks={DeckRecommendation[]} combinedTotalDamage={number} excludedSlugs={string[]} bossElements={(BossElement)[]} nameFor={(slug:string)=>string} />`

`bossElements`는 덱별 보스 속성 배열이다(유니온에서 덱마다 다르므로 카드 제목에 붙인다). 추천 탭 평가 모드는 전 덱 같은 값을 넘긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/EvaluationResults.test.tsx`. 먼저 `RaidResults.test.tsx`를 읽고 같은 렌더/단언 스타일을 쓴다.

```typescript
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvaluationResults } from './EvaluationResults'

const DECKS = [
  { deck: ['liter', 'blanc', 'crown', 'modernia', 'privaty'],
    total_damage: 100, burst_damage: 60, normal_attack_damage: 30, skill_damage: 10 },
  { deck: ['rouge', 'volume', 'mint', 'grave', 'noir'],
    total_damage: 50, burst_damage: 30, normal_attack_damage: 15, skill_damage: 5 },
]

const renderResults = (overrides = {}) =>
  render(<EvaluationResults
    decks={DECKS}
    combinedTotalDamage={150}
    excludedSlugs={[]}
    bossElements={['Iron', 'Water']}
    nameFor={(slug) => slug}
    {...overrides} />)

describe('EvaluationResults', () => {
  it('덱마다 카드를 그리고 합계를 보여준다', () => {
    renderResults()
    expect(screen.getAllByRole('article')).toHaveLength(2)
    expect(screen.getByText(/150/)).toBeTruthy()
  })

  it('덱마다 자기 보스 속성을 표시한다', () => {
    renderResults()
    expect(screen.getByText(/철갑/)).toBeTruthy()
    expect(screen.getByText(/수냉/)).toBeTruthy()
  })

  it('엔진이 고른 순서를 안내한다', () => {
    renderResults()
    expect(screen.getByText(/순서/)).toBeTruthy()
  })

  it('지원하지 않는 슬러그가 있으면 알려준다', () => {
    renderResults({ excludedSlugs: ['not-a-nikke'] })
    expect(screen.getByText(/not-a-nikke/)).toBeTruthy()
  })
})
```

`getAllByRole('article')`은 `DeckCard`가 실제로 무슨 role을 갖는지 확인한 뒤 맞춘다 — `DeckCard.tsx`를 먼저 읽고, article이 아니면 그 파일이 쓰는 셀렉터로 바꾼다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/EvaluationResults.test.tsx`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 최소 구현**

`frontend/src/components/EvaluationResults.tsx`. `RaidResults.tsx`의 구조(합계 헤더 + 덱 카드 목록 + 제외 슬러그 노트)를 따르되, 대안 배치·남은 유닛·잠금 표시는 없다. 속성 라벨은 반드시 기존 `lib/elementName.ts`의 `elementLabel()`을 쓴다(작열/수냉/풍압/철갑/전격).

각 덱 카드 제목은 `{index + 1}번 덱 · {elementLabel(element)}` 형태로, 카드 아래에 안내 한 줄:

```tsx
<p className="evaluation-results__ordering-note">
  자리 순서는 엔진이 기대 딜량이 가장 높게 나오도록 고른 거예요. 인게임에서도 이 순서로 배치해요.
</p>
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/EvaluationResults.test.tsx`
Expected: PASS

Run: `cd frontend && npx tsc -b --noEmit`
Expected: 클린

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/EvaluationResults.tsx frontend/src/components/EvaluationResults.test.tsx
git commit -m "Render an evaluated set of decks with the order the engine chose"
```

---

### Task 10: 추천 탭 `평가` 모드

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx`
- Modify: `frontend/src/components/RecommendPanel.test.tsx`

**Interfaces:**
- Consumes: Task 6의 `useEvaluateDecks`, Task 8의 `showLocks`, Task 9의 `EvaluationResults`
- Produces: `RecommendMode`에 `'evaluate'` 추가

**설계 메모(구현자에게):** 평가 모드 결과는 **캐시하지 않는다.** 수 초면 끝나서 캐시 이득이 없고, `StoredResult`(배분 결과 모양)를 건드리지 않아도 되기 때문이다. 그래서 `getCached`/`onResult`/`raidResultMode`/`displayMode` 경로에 평가 모드를 끼워 넣지 말고, `useEvaluateDecks`의 자체 상태만 읽어 렌더한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`RecommendPanel.test.tsx`에 추가:

```typescript
  it('평가 모드는 25칸을 다 채우기 전에는 제출을 막는다', async () => {
    renderPanel({ roster: fullRoster })
    await userEvent.click(screen.getByRole('radio', { name: /평가/ }))
    expect(screen.getByRole('button', { name: /계산/ })).toBeDisabled()
  })

  it('평가 모드에서는 잠금 토글이 없다', async () => {
    renderPanel({ roster: fullRoster })
    await userEvent.click(screen.getByRole('radio', { name: /평가/ }))
    expect(screen.queryByRole('button', { pressed: false })).toBeNull()
  })

  it('다른 모드로 바꾸면 평가 결과가 새어 보이지 않는다', async () => {
    // 평가 성공 상태를 만든 뒤 '단일 덱'으로 전환하면 결과가 사라져야 한다.
    // 기존 raidResultMode 가드가 지키는 것과 같은 계약이다.
  })
```

세 번째 테스트는 이 파일의 기존 "모드 전환 시 결과 격리" 테스트를 그대로 본떠서 완성한다 — 그 테스트가 결과를 어떻게 주입하는지(훅 모킹인지 fetch 모킹인지) 먼저 읽고 같은 방식을 쓴다. **주석만 남긴 채로 커밋하지 않는다.**

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx`
Expected: FAIL — `평가` 라디오가 없다

- [ ] **Step 3: 최소 구현**

`RecommendMode` 타입에 `'evaluate'`를 더한다. 모드 스위치에 네 번째 라디오(라벨 `평가`)를 기존 셋과 같은 마크업으로 추가한다.

`const evaluation = useEvaluateDecks()`를 `single`/`raid` 옆에 둔다.

- 편성기: `mode === 'evaluate'`일 때 `<DraftEditor ... showLocks={false} />`를 그린다(드래프트 모드가 쓰는 것과 같은 `draftValue`/`setDraftValue` 상태를 공유해도 된다 — 두 모드가 동시에 보이지 않는다).
- `numDecks` 셀렉터는 드래프트/배분 모드와 똑같이 보인다.
- 제출 버튼: `mode === 'evaluate'`이면 라벨은 `기대 딜량 계산`, 활성 조건은 **선택한 덱이 전부 5명**일 때만. 판정은 `draftValue.decks.slice(0, numDecks).every((seats) => seats.length === MAX_DRAFT_SEATS_PER_DECK)`.
- 제출 시: 캐시 경로를 타지 않고 곧장

```tsx
evaluation.submit({
  roster: effectiveRoster,
  decks: draftValue.decks.slice(0, numDecks).map((seats) => ({
    units: seats.map((seat) => seat.slug),
    boss: bossProfile,
  })),
})
```

- 결과: `{mode === 'evaluate' && evaluation.status === 'success' && (<EvaluationResults decks={evaluation.decks} combinedTotalDamage={evaluation.combinedTotalDamage} excludedSlugs={evaluation.excludedSlugs} bossElements={evaluation.decks.map(() => bossProfile.element)} nameFor={nameFor} />)}`
- 로딩/에러: 기존 모드들과 같은 자리에서 `mode === 'evaluate' && evaluation.status === 'loading' | 'error'`로 분기. 로딩 문구는 `기대 딜량 계산 중이에요 — 몇 초면 끝나요.`
- 모드를 바꿀 때 평가 결과가 새지 않도록, 모드 라디오 `onChange`에서 `evaluation.cancel()`을 부르고, 렌더 조건이 `mode === 'evaluate'`로 이미 게이팅돼 있는지 확인한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run`
Expected: 0 failed

Run: `cd frontend && npx tsc -b --noEmit && npm run build`
Expected: 클린

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "Add the evaluate mode to the recommend tab"
```

---

### Task 11: 유니온 레이드 탭

**Files:**
- Create: `frontend/src/components/UnionRaidPanel.tsx`, `frontend/src/components/UnionRaidPanel.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Task 6·8·9의 전부, 기존 `BossProfileField` · `UnitPalette` · `DraftEditor`
- Produces: `<UnionRaidPanel roster={UserNikkeState[]} supportedUnits={SupportedUnit[]} portraitFor nameFor burstTierFor />` · `App`의 `Tab`에 `'union'` 추가

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/UnionRaidPanel.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { UnionRaidPanel } from './UnionRaidPanel'

describe('UnionRaidPanel', () => {
  it('기본으로 전투 3회분의 보스 설정을 그린다', () => {
    renderPanel()
    expect(screen.getAllByRole('group', { name: /전투/ })).toHaveLength(3)
  })

  it('전투마다 보스 속성을 따로 고를 수 있다', async () => {
    renderPanel()
    const groups = screen.getAllByRole('group', { name: /전투/ })
    await userEvent.selectOptions(within(groups[0]).getByLabelText(/속성/), 'Iron')
    await userEvent.selectOptions(within(groups[1]).getByLabelText(/속성/), 'Water')
    expect(within(groups[0]).getByLabelText(/속성/)).toHaveValue('Iron')
    expect(within(groups[1]).getByLabelText(/속성/)).toHaveValue('Water')
  })

  it('전투 시간 기본값은 180초다', () => {
    renderPanel()
    const groups = screen.getAllByRole('group', { name: /전투/ })
    expect(within(groups[0]).getByLabelText(/전투 시간/)).toHaveValue(180)
  })

  it('15칸을 다 채우기 전에는 제출을 막는다', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: /계산/ })).toBeDisabled()
  })

  it('잠금 토글을 그리지 않는다', () => {
    renderPanel()
    expect(screen.queryByRole('button', { pressed: false })).toBeNull()
  })
})
```

`renderPanel` 헬퍼와 픽스처(로스터 15명 이상 + `supportedUnits`)는 `RecommendPanel.test.tsx`가 쓰는 것을 본떠 이 파일 안에 만든다. `within`은 `@testing-library/react`에서 임포트한다. `BossProfileField`가 실제로 `role="group"`과 접근 가능한 이름을 갖는지 먼저 확인하고, 아니면 `<fieldset><legend>{n}번 전투</legend>`로 감싸서 이름을 만든다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/UnionRaidPanel.test.tsx`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 최소 구현**

`frontend/src/components/UnionRaidPanel.tsx`:

```tsx
// 유니온 레이드: 5속성 보스 중 골라 3회 전투하고, 한 번 출전한 니케는 다음
// 전투에 못 나온다. 그래서 화면은 "보스 설정 + 5인 편성"을 전투 수만큼 세운
// 것이고, 편성 규칙은 솔로 5덱과 같다(전원이 서로 달라야 한다).
//
// 추천 탭과 달리 여기엔 최적화가 없다 - 엔진은 유저가 짠 편성을 채점만 한다.
// 잠금이 없는 것도(고정할 최적화가 없다), 결과를 캐시하지 않는 것도(수 초면
// 끝난다) 같은 이유다.
```

구성:
- 상태: `numBattles`(기본 `DEFAULT_UNION_NUM_DECKS`), `bosses: BossProfileDraft[]`(전투 수만큼), `draftValue: Draft`
- 보스는 전투마다 `<fieldset>`로 감싼 `BossProfileField` 하나. **필드를 새로 선언하지 않는다** — 기존 컴포넌트를 그대로 쓴다. 기본값은 `makeDefaultBossProfileDraft()`이며 전투 시간 180은 거기서 온다(값이 다르면 그 팩토리를 확인해 180으로 맞춘다).
- `numBattles`를 줄이면 뒤쪽 보스 설정과 덱이 사라지고, 늘리면 빈 값이 붙는다.
- 팔레트(`UnitPalette`) + `<DraftEditor numDecks={numBattles} showLocks={false} />`
- 제출 버튼(`기대 딜량 계산`)은 선택한 전투 수만큼의 덱이 **전부 5명**일 때만 활성.
- 제출: `useEvaluateDecks().submit({ roster, decks: draftValue.decks.slice(0, numBattles).map((seats, i) => ({ units: seats.map(s => s.slug), boss: toBossProfile(bosses[i]) })) })`
  — `toBossProfile`은 `RecommendPanel`이 `BossProfileDraft`를 와이어 `BossProfile`로 바꿀 때 쓰는 기존 변환을 **그대로 재사용**한다. 그 변환이 `RecommendPanel` 안에 인라인돼 있으면 `types/bossProfileDraft.ts` 옆으로 추출해 양쪽이 같은 함수를 쓰게 한다(복제 금지).
- 결과: `<EvaluationResults ... bossElements={bosses.slice(0, numBattles).map(b => b.element)} />`

`App.tsx`:
- `type Tab = 'roster' | 'recommend' | 'union'`
- `TABS`에 `{ id: 'union', label: '유니온 레이드' }` 추가
- 기존 두 패널과 같은 방식(`hidden` 토글, 언마운트 금지 — 진행 중인 요청이 버려지지 않게)으로 세 번째 `tabpanel`을 붙인다.

`App.test.tsx`: 탭이 셋 렌더되고 `유니온 레이드`를 누르면 그 패널이 보이는지 확인하는 테스트를 기존 탭 테스트를 본떠 추가한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run`
Expected: 0 failed

Run: `cd frontend && npx tsc -b --noEmit && npm run build`
Expected: 클린

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "Add the union raid tab"
```

---

### Task 12: 라이브 엔드투엔드 확인 + 실측

**Files:**
- 없음 (측정만)

**Interfaces:**
- Consumes: Task 1–11 전부

- [ ] **Step 1: 백엔드를 띄운다**

Run: `cd backend && python -m uvicorn app.api:app --port 8000`
(별도 셸에서) Run: `cd frontend && npm run dev`

메모: 로컬 개발은 서버 두 개다. Vite(:5173)가 `/api/*`를 FastAPI(:8000)로 프록시하므로 백엔드를 안 띄우면 ECONNREFUSED가 난다.

- [ ] **Step 2: 실제 로스터로 평가 시간을 잰다**

Run:

```bash
cd backend && python -c "
import time, json
from fastapi.testclient import TestClient
from app.api import app
from app.supported_units import supported_units

client = TestClient(app)
units = supported_units()
by_tier = {t: [u['slug'] for u in units if u['burst_tier'] == t] for t in (1, 2, 3)}
decks = [[by_tier[1][i], by_tier[2][i], by_tier[3][3*i], by_tier[3][3*i+1], by_tier[3][3*i+2]]
         for i in range(3)]
roster = [{'character_slug': s} for deck in decks for s in deck]
body = {'roster': roster,
        'decks': [{'units': d, 'boss': {'element': e}}
                  for d, e in zip(decks, ['Iron', 'Water', 'Fire'])]}
start = time.perf_counter()
r = client.post('/api/evaluate-decks', json=body)
print(r.status_code, f'{time.perf_counter() - start:.2f}s')
print(json.dumps({k: v for k, v in r.json().items() if k != 'decks'}, indent=2))
"
```

Expected: 200, **수 초**. 20초를 넘으면 스펙의 "직렬로 시작" 판단이 틀린 것이므로 수치를 기록하고 Fienn에게 보고한다(보스별로 묶어 SimPool을 태우는 것이 후속 레버).

- [ ] **Step 3: 브라우저에서 두 화면을 확인한다**

`/verify` 스킬 또는 Playwright로: 추천 탭 `평가` 모드에서 25칸을 채워 제출 → 결과가 나오는지 · 유니온 탭에서 전투마다 보스 속성을 다르게 주고 15칸을 채워 제출 → 덱마다 다른 속성이 표시되는지.

- [ ] **Step 4: 전체 테스트를 다시 돌린다**

Run: `cd backend && python -m pytest -q`
Expected: 기준선 1413 + 신규분, 0 failed

Run: `cd frontend && npx vitest run`
Expected: 기준선 350 + 신규분, 0 failed

- [ ] **Step 5: 실측을 기록하고 커밋**

측정한 초수와 브라우저 확인 결과를 `docs/roadmap.md` 최상단 상태 항목에 적는다.

```bash
git add docs/roadmap.md
git commit -m "Record what the live evaluation run measured"
```

---

### Task 13: 문서 갱신

**Files:**
- Modify: `frontend/README.md` (데이터 계약)
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: 전부

- [ ] **Step 1: `frontend/README.md`에 계약을 적는다**

`### POST /api/recommend-raid ...` 섹션 뒤에 `### POST /api/evaluate-decks (고정 편성 평가 — 솔로 5덱 / 유니온 3덱)` 섹션을 추가한다. 그 파일의 기존 두 엔드포인트 섹션과 같은 형식(요청/응답 JSON 예시 + 의미 설명)을 쓴다. 반드시 담을 것:

- 보스가 덱마다 하나라는 것과 그 이유(유니온 레이드)
- `deck` 배열이 **엔진이 고른 순서**라는 것
- 422 다섯 가지
- `engine_version`이 결과 캐시의 무효화 축이라는 것과 `GET /api/engine-version`이 따로 있는 이유

`### UI scope — draft editor (built)` 뒤에 `### UI scope — 평가 모드 · 유니온 레이드 탭 (built)`을 추가하고, 평가 결과는 캐시하지 않는다는 결정과 이유를 적는다.

- [ ] **Step 2: `docs/roadmap.md`를 갱신한다**

최상단 상태 블록에 이번 작업 항목을 기존 항목들과 같은 형식으로 추가한다: 무엇이 착지했는지, 백엔드/프론트 테스트 수치, 스펙·플랜 경로, 실측 시간, 범위 밖으로 남긴 것(유니온 레이드 *추천*, 5속성 보스 프리셋).

- [ ] **Step 3: 커밋**

```bash
git add frontend/README.md docs/roadmap.md
git commit -m "Document the evaluation endpoint and the two screens on it"
```

- [ ] **Step 4: 결정·통찰 기록**

`/document` 명령(docs-keeper 서브에이전트)으로 다음을 넘긴다:
- **결정:** 평가 전용 경로를 별도 엔드포인트로 낸 이유(플래그 얹기·프론트 다중 호출을 기각한 근거)
- **결정:** 엔진 버전을 손으로 올리는 숫자가 아니라 `app/` 전체의 내용 해시로 만든 이유
- **통찰:** 입력만으로 만든 결과 캐시 키는 엔진이 바뀌면 조용히 낡는다 — 결정론은 한 버전 안에서만 참이다

---

## Self-Review

**1. 스펙 커버리지**

| 스펙 항목 | 태스크 |
|---|---|
| 접근 A(전용 엔드포인트) | 5 |
| 새 엔진 표면 금지 / 같은 프리미티브 | 3, 4 + 파리티 테스트(5) |
| 편성 순서는 엔진이 고르고 결과가 알려줌 | 4(테스트), 9(안내 문구) |
| 화면 둘 · 엔진 하나 | 10, 11 |
| 덱 수 1–5 / 1–3 | 10, 11 |
| 덱별 전체 보스 프로필 · 180초 | 11 |
| 잠금 토글 숨김 | 8, 10, 11 |
| 중복 편성 불가 | 8(기존 `placeUnit` 불변식) + 5(백엔드 422) |
| 보스 스키마 안 갈라짐 | 5(`BossProfileIn` 재사용), 11(`BossProfileField` 재사용) |
| 캐시에 엔진 버전 | 1, 2, 7 |
| API 형태·422 다섯 가지 | 5 |
| MODE_VARIANTS 최선 해석 | 4, 5 |
| 성능: 직렬로 시작 후 실측 | 4(풀 없음), 12 |
| 테스트 목록 전부 | 1, 2, 4, 5, 6, 8, 9, 10, 11 |
| 범위 밖 항목 | 13(문서에 명시) |

빠진 스펙 항목 없음.

**2. 플레이스홀더 스캔**

- Task 10의 세 번째 테스트가 본문 없이 주석만 있다 → 스텝 본문에 "주석만 남긴 채로 커밋하지 않는다"와 무엇을 본떠야 하는지를 명시해 해소.
- 기존 파일의 헬퍼 이름(`renderPanel`·`renderEditor`·`ROSTER`·`draftWithOneUnit`)에 의존하는 곳은 전부 "먼저 그 파일을 읽고 실제 이름에 맞춘다"를 붙였다.
- 슬러그 픽스처(`DECK`·`b3_only`)는 실제 로더블 여부를 확인하는 명령을 함께 적었다 — 추측한 슬러그를 그대로 쓰면 안 된다.

**3. 타입 일관성**

- `best_ordering_summary` — Task 3에서 승격, Task 4에서 소비. 이름 일치.
- `evaluate_decks(decks, bosses, alternatives=None)` — Task 4 정의, Task 5 호출. 인자 일치.
- `InfeasibleDeck.deck_index` — Task 4 정의, Task 5에서 `e.deck_index + 1`로 1-기반 표시. 일치.
- `hashRecommendInputs(..., engineVersion)` — Task 7에서 시그니처 변경, 같은 태스크 안에서 호출부·테스트 모두 갱신.
- `EvaluateDecksResponse.decks: DeckRecommendation[]` — Task 6 타입, Task 9 `EvaluationResults`의 prop 타입과 일치.
- `useEvaluateDecks()`의 반환 키(`decks`/`combinedTotalDamage`/`excludedSlugs`) — Task 6 정의, Task 10·11 소비. 일치.
- `showLocks` — Task 8 정의, Task 10·11 소비. 일치.
- `engine_version`(백) ↔ `engine_version`(TS 와이어) ↔ `engineVersion`(TS 로컬) — 와이어는 snake, 로컬은 camel로 프로젝트 관례와 일치.
