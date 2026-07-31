# 데스크톱 앱 패키징 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RapiLab을 Windows 설치형 앱으로 실행 가능하게 만든다 — pywebview 창 안에서 FastAPI가 프론트와 API를 같은 origin으로 서빙하고, PyInstaller로 얼린 뒤에도 데이터·버전·쓰기 경로가 전부 맞는다.

**Architecture:** 엔트리포인트가 uvicorn을 데몬 스레드로 띄우고 준비될 때까지 기다린 뒤 pywebview 창을 그 주소로 연다. 프론트는 코드 변경 없이 빌드 산출물을 FastAPI가 정적 서빙한다(전부 상대경로 `/api/*`라 Vite 프록시가 그대로 대체된다). 얼렸을 때 깨지는 것은 전부 **경로와 버전**이므로, 흩어진 `__file__` 기반 경로를 리졸버 하나로 모으고 엔진 버전을 빌드 시점에 주입한다.

**Tech Stack:** Python 3.14 · FastAPI · uvicorn · pywebview 6.2.1 (pythonnet 3.1.0 / WebView2) · PyInstaller 6.21.0 · React/Vite (기존)

## 검증된 전제 (2026-07-31 스모크)

격리 venv(Python 3.14.6)에서 `pywebview==6.2.1` · `pyinstaller==6.21.0` · `pythonnet==3.1.0`(cp314 wheel) 설치가 되고, **실제 창이 뜨고 `webview.start()`가 정상 반환**한다. 브레인스토밍이 남긴 유일한 미검증 가정이었고 깨졌다.

## Global Constraints

- **Windows 전용.** 코드서명 없이 시작한다(오픈소스 공개로 신뢰 보완).
- **껍데기는 pywebview 네이티브 창.** "로컬 서버 띄우고 브라우저 열기"는 Fienn이 기각했다.
- **프론트 소스는 건드리지 않는다** — 전부 상대경로 `/api/*`이므로 같은 origin 서빙이면 그대로 돈다. (동기화 경로 Task 8~9는 예외이며 그 이유가 Task 8에 적혀 있다.)
- **기존 개발 흐름을 깨지 않는다.** `uvicorn app.api:app --reload` + Vite :5173 조합은 계속 동작해야 한다(`docs/roadmap.md`의 로컬 개발 2서버 구성).
- **테스트는 `backend/`에서 돌린다.** 리포 루트에서 pytest하면 `No module named 'app'`으로 수집 실패한다.
- 현재 기준선: 백엔드 **1685 passed / 3 skipped** · 프론트 **453 passed**. 각 Task는 이 수를 줄이지 않는다.

## 범위 밖 (별도 계획)

**③ 배포채널 · ④ 자동업데이트 · ⑤ 공개준비.** ③이 원격 저장소를 요구하는데 이 리포에는 원격이 없다(계정 작업이라 Fienn의 몫). ④는 ③에 의존하고 **첫 릴리스에 반드시 포함**되어야 하므로, 원격이 생긴 뒤 ③+④를 한 계획으로 묶는다. 이 계획이 끝나면 "내 PC에서 앱으로 뜨고 동작한다"까지가 완성된다.

---

### Task 1: 경로 리졸버 — 얼려도 맞는 한 곳

**Files:**
- Create: `backend/app/paths.py`
- Modify: `backend/app/skill_values.py:18`, `backend/app/stat_assembly.py:55`, `backend/app/roster_assembly.py:20`, `backend/app/dotgg_client.py:12`
- Test: `backend/tests/test_paths.py`

**Interfaces:**
- Produces: `data_dir() -> Path` (읽기 전용 번들 데이터) · `writable_dir() -> Path` (캐시 등 쓰기)

`__file__` 상대 경로가 네 모듈에 흩어져 있고 전부 `parents[2] / "data"`를 가정한다. 얼리면 그 조상이 존재하지 않는다. 그리고 `dotgg_client`는 `data/cache/`에 **쓴다** — Program Files 아래는 쓰기 금지다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_paths.py
"""번들 데이터는 어디서 읽고, 쓰기는 어디로 가는가.

얼린 앱에서 깨지는 것은 코드가 아니라 경로다. sys.frozen / sys._MEIPASS는
PyInstaller가 런타임에 심는 값이라 여기서는 monkeypatch로 흉내낸다.
"""
from pathlib import Path

from app import paths


def test_data_dir_is_the_repo_data_when_not_frozen():
    assert paths.data_dir().name == "data"
    assert (paths.data_dir() / "nikke-stat-tables").is_dir()


def test_data_dir_follows_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.data_dir() == tmp_path / "data"


def test_writable_dir_is_not_inside_the_bundle_when_frozen(monkeypatch, tmp_path):
    # Program Files 아래는 쓰기 금지라, 얼렸을 때의 쓰기 경로가 번들 안이면 안 된다.
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    writable = paths.writable_dir()
    assert tmp_path not in writable.parents
    assert writable.parts[-1] == "RapiLab"
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_paths.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.paths'`

- [ ] **Step 3: 리졸버를 만든다**

```python
# backend/app/paths.py
"""번들 데이터와 쓰기 가능 디렉터리가 어디인지 아는 유일한 곳.

얼리기 전에는 `__file__`에서 리포 루트를 거슬러 올라가면 되지만, PyInstaller가
얼리면 그 조상이 존재하지 않는다. 네 모듈이 각자 `parents[2] / "data"`를 하고
있었고 그 넷은 전부 같은 날 같은 방식으로 틀린다 - 그래서 한 곳으로 모은다.

쓰기 경로가 따로 있는 이유: 설치형 앱은 Program Files 아래에 놓이고 거기는
쓰기 금지다. `dotgg_client`가 캐시를 데이터 디렉터리에 쓰고 있었다.
"""
import os
import sys
from pathlib import Path

_APP_NAME = "RapiLab"


def _frozen() -> bool:
    return getattr(sys, "frozen", False)


def data_dir() -> Path:
    """읽기 전용 번들 데이터(`data/`). 얼린 뒤에는 PyInstaller가 풀어놓은 곳."""
    if _frozen():
        return Path(sys._MEIPASS) / "data"
    return Path(__file__).resolve().parents[2] / "data"


def writable_dir() -> Path:
    """앱이 쓸 수 있는 사용자별 디렉터리. 없으면 만든다.

    얼리지 않았을 때도 %LOCALAPPDATA%를 쓴다 - 개발 중에만 리포 안에 쓰면
    "내 PC에서는 되던데"가 정확히 이 경로에서 나온다.
    """
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    path = Path(base) / _APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_paths.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: 네 모듈을 리졸버로 돌린다**

`skill_values.py:18` → `DATA_DIR = data_dir()`
`stat_assembly.py:55` → `data_dir() / "nikke-stat-tables" / "tables.json"`
`roster_assembly.py:20` → `data_dir()`로 대체
`dotgg_client.py:12` → `DEFAULT_CACHE_DIR = writable_dir() / "cache"`

각 파일 상단에 `from app.paths import data_dir` (또는 `writable_dir`)을 추가하고, 기존 `Path(__file__)...` 표현식을 지운다.

- [ ] **Step 6: 전체 스위트로 회귀가 없음을 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: 1688 passed / 3 skipped (기존 1685 + 신규 3)

- [ ] **Step 7: 커밋**

```bash
git add backend/app/paths.py backend/tests/test_paths.py backend/app/skill_values.py \
        backend/app/stat_assembly.py backend/app/roster_assembly.py backend/app/dotgg_client.py
git commit -m "Ask one module where the data is, so freezing moves one answer"
```

---

### Task 2: engine_version — 얼리면 조용히 틀리는 것을 소리나게

**Files:**
- Modify: `backend/app/engine_version.py`
- Test: `backend/tests/test_engine_version.py` (기존 파일이 있으면 추가, 없으면 생성)

**Interfaces:**
- Consumes: Task 1의 `paths` (frozen 판별)
- Produces: `engine_version() -> str` (동작 불변) · `_VERSION_FILE` (빌드가 심는 파일 이름)

지금은 `app/` 아래 `.py`를 전부 해시한다. 얼리면 그 경로에 소스가 없어 **예외가 아니라 빈 다이제스트**가 나온다 — 프론트 결과 캐시가 낡은 채로 산다. 이 계획에서 가장 위험한 항목이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_engine_version.py 에 추가
def test_frozen_without_a_stamped_version_raises_rather_than_returning_a_hash(
        monkeypatch, tmp_path):
    """소스가 없는 채로 해시하면 '빈 입력의 sha256'이 나온다. 그것은 유효해
    보이는 문자열이라 캐시를 조용히 낡게 만든다 - 조용한 오답보다 시끄러운
    실패가 낫다."""
    from app import engine_version as ev
    ev.engine_version.cache_clear()
    monkeypatch.setattr(ev.sys, "frozen", True, raising=False)
    monkeypatch.setattr(ev.sys, "_MEIPASS", str(tmp_path), raising=False)
    with pytest.raises(RuntimeError, match="stamped"):
        ev.engine_version()
    ev.engine_version.cache_clear()


def test_frozen_reads_the_stamped_version(monkeypatch, tmp_path):
    from app import engine_version as ev
    ev.engine_version.cache_clear()
    (tmp_path / ev._VERSION_FILE).write_text("abc123def456", encoding="utf-8")
    monkeypatch.setattr(ev.sys, "frozen", True, raising=False)
    monkeypatch.setattr(ev.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert ev.engine_version() == "abc123def456"
    ev.engine_version.cache_clear()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_engine_version.py -q`
Expected: FAIL — 첫 테스트가 `RuntimeError` 대신 문자열을 받는다

- [ ] **Step 3: 구현한다**

```python
# engine_version.py — import 부에 sys 추가, 아래를 교체
import sys

# 빌드가 소스 해시를 적어 번들에 넣는 파일. 얼린 앱에는 .py 소스가 없으므로
# 런타임에 다시 계산할 방법이 없고, 계산을 시도하면 '아무것도 해시하지 않은'
# 값이 조용히 나온다.
_VERSION_FILE = "engine_version.txt"


@lru_cache(maxsize=1)
def engine_version() -> str:
    """이 프로세스가 돌리고 있는 엔진의 버전."""
    if getattr(sys, "frozen", False):
        stamped = Path(sys._MEIPASS) / _VERSION_FILE
        if not stamped.is_file():
            raise RuntimeError(
                f"frozen build has no stamped {_VERSION_FILE} - the build step "
                "must write hash_sources() into the bundle")
        return stamped.read_text(encoding="utf-8").strip()
    return hash_sources(_APP_DIR)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_engine_version.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/engine_version.py backend/tests/test_engine_version.py
git commit -m "Refuse to guess the engine version instead of hashing nothing"
```

---

### Task 3: 런타임 의존성을 실제와 맞춘다

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/requirements-app.txt`
- Test: `backend/tests/test_requirements.py`

`requirements.txt`에 **numpy가 없다** — `cascade.py`와 `surrogate.py`가 쓴다. Fienn PC에 깔려 있어 안 터질 뿐이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_requirements.py
"""임포트되는 서드파티가 requirements에 다 있는가.

"내 PC에서는 되던데"를 잡는 테스트다. numpy가 빠져 있는 것을 이 방식으로
찾았다(2026-07-31).
"""
import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
STDLIB = set(sys.stdlib_module_names)
LOCAL = {"app", "tests"}


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_every_third_party_import_in_app_is_declared():
    declared = {
        line.split("[")[0].split("==")[0].split(">=")[0].strip().lower()
        for line in (BACKEND / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    imported = set()
    for path in (BACKEND / "app").rglob("*.py"):
        imported |= _top_level_imports(path)
    third_party = {n for n in imported if n not in STDLIB and n not in LOCAL}
    assert third_party <= declared, f"undeclared: {sorted(third_party - declared)}"
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_requirements.py -q`
Expected: FAIL — `undeclared: ['numpy']`

- [ ] **Step 3: requirements를 고친다**

`backend/requirements.txt`에 `numpy` 한 줄 추가(알파벳 순 위치).

`backend/requirements-app.txt` 신설:

```
# 데스크톱 앱으로 패키징할 때만 필요한 것. 서버 실행에는 쓰이지 않는다.
-r requirements.txt
pywebview
pyinstaller
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_requirements.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/requirements.txt backend/requirements-app.txt backend/tests/test_requirements.py
git commit -m "Declare numpy, and let a test say so next time"
```

---

### Task 4: 프론트 정적 서빙 — 같은 origin

**Files:**
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_static_serving.py`

**Interfaces:**
- Consumes: Task 1의 `paths`
- Produces: `/` 및 SPA 라우트가 `frontend/dist/index.html`을 반환

프론트가 전부 상대경로 `/api/*`를 쓰므로, 같은 origin에서 정적 서빙하면 Vite 프록시를 그대로 대체한다. **dist가 없을 때(개발 중)는 마운트하지 않는다** — 개발 2서버 구성을 깨지 않기 위해서다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_static_serving.py
"""빌드된 프론트가 있으면 API와 같은 origin에서 서빙된다.

앱에서는 Vite 프록시가 없으므로 이것이 프론트가 API에 닿는 유일한 방법이다.
dist가 없는 개발 환경에서는 마운트하지 않아야 한다 - 그때는 :5173이 서빙한다.
"""
from fastapi.testclient import TestClient

from app import api


def test_api_routes_still_answer_when_a_bundle_is_mounted(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<!doctype html>ok", encoding="utf-8")
    monkeypatch.setattr(api, "frontend_dist", lambda: tmp_path)
    app = api.build_app()
    client = TestClient(app)
    assert client.get("/api/supported-units").status_code == 200


def test_a_client_route_falls_back_to_index_html(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<!doctype html>ok", encoding="utf-8")
    monkeypatch.setattr(api, "frontend_dist", lambda: tmp_path)
    client = TestClient(api.build_app())
    response = client.get("/some/client/route")
    assert response.status_code == 200
    assert "<!doctype html>" in response.text


def test_no_bundle_means_no_mount(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "frontend_dist", lambda: tmp_path / "absent")
    client = TestClient(api.build_app())
    assert client.get("/some/client/route").status_code == 404
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_static_serving.py -q`
Expected: FAIL — `AttributeError: module 'app.api' has no attribute 'frontend_dist'`

- [ ] **Step 3: 구현한다**

`api.py` 하단(모든 라우트 정의 뒤)에 추가하고, 모듈 끝의 `app`은 `build_app()`이 만들도록 바꾼다.

`frontend_dist()`는 **Task 1의 `paths.py`에 둔다** — frozen 판별이 두 곳에 생기면 Task 1이 없앤 문제가 그대로 돌아온다. `paths.py`에 추가:

```python
def frontend_dist() -> Path:
    """빌드된 프론트가 있는 곳. 얼린 앱에서는 번들 안, 개발 중에는 리포 안."""
    if _frozen():
        return Path(sys._MEIPASS) / "frontend"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"
```

`api.py`는 그것을 재수출해 테스트가 한 곳만 monkeypatch하면 되게 한다:

```python
from app.paths import frontend_dist


def build_app() -> FastAPI:
    """라우트가 전부 붙은 app에 프론트 번들을 (있으면) 얹는다.

    마운트는 마지막이어야 한다 - `/`에 걸린 StaticFiles는 그 아래 모든 경로를
    가져가므로, `/api/*`보다 먼저 붙으면 API가 전부 404가 된다.
    """
    dist = frontend_dist()
    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
```

`from fastapi.staticfiles import StaticFiles`와 `from app.paths import frontend_dist`를 임포트에 추가한다. 모듈 끝에서 `app = build_app()`이 되도록 바꾸되, **기존 `app` 객체를 새로 만들지 말고** 데코레이터가 이미 라우트를 붙여 놓은 그 객체에 마운트만 얹는다.

> **주의:** `StaticFiles(html=True)`는 없는 경로에 404를 낸다. SPA 라우트 폴백이 필요하면 `StaticFiles`를 감싼 커스텀 클래스로 `index.html`을 돌려주게 하고, 그 동작을 위 두 번째 테스트가 고정한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_static_serving.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: 개발 구성이 안 깨졌는지 확인한다**

Run: `cd backend && python -m pytest -q`
Expected: 기존 전부 통과 — `/api/*` 라우트를 잡아먹지 않았는지가 핵심

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api.py backend/tests/test_static_serving.py
git commit -m "Serve the built frontend from the API's own origin"
```

---

### Task 5: 실행셸 — 창 하나와 그 안의 서버

**Files:**
- Create: `backend/app/desktop.py`
- Test: `backend/tests/test_desktop.py`

**Interfaces:**
- Consumes: Task 4의 `build_app()`
- Produces: `pick_port() -> int` · `wait_until_serving(url, timeout) -> bool` · `main() -> None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_desktop.py
"""실행셸에서 GUI가 아닌 부분 - 포트 선택과 준비 대기.

창 자체는 여기서 열지 않는다(테스트가 사람의 화면을 뺏는다). 열리는지는
2026-07-31 스모크에서 확인했고, 여기서 고정하는 것은 창을 열기 '전에'
서버가 실제로 응답하는지 기다리는 부분이다 - 그것이 없으면 빈 창이 뜬다.
"""
import socket

from app import desktop


def test_pick_port_returns_a_port_that_is_actually_free():
    port = desktop.pick_port()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))  # 비어 있지 않으면 OSError


def test_wait_until_serving_gives_up_instead_of_hanging():
    # 아무도 듣지 않는 포트. 창을 영원히 안 여는 것보다 실패를 보고해야 한다.
    assert desktop.wait_until_serving("http://127.0.0.1:9", timeout=0.5) is False


def test_wait_until_serving_sees_a_live_server():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Ok(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Ok)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        assert desktop.wait_until_serving(url, timeout=5.0) is True
    finally:
        server.shutdown()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && python -m pytest tests/test_desktop.py -q`
Expected: FAIL — `No module named 'app.desktop'`

- [ ] **Step 3: 구현한다**

```python
# backend/app/desktop.py
"""RapiLab 데스크톱 실행셸.

uvicorn을 데몬 스레드로 띄우고, 실제로 응답할 때까지 기다린 뒤, pywebview
창을 그 주소로 연다. 기다리는 단계가 핵심이다 - 바로 열면 서버가 준비되기
전에 창이 로드를 시도해 빈 화면이 뜬다.

`freeze_support()`가 맨 위에 있는 이유: Windows의 프로세스 풀은 spawn이라
자식이 이 모듈을 다시 임포트한다. 얼린 앱에서 그것은 exe를 다시 실행하는
것이고, 방어가 없으면 앱이 자기 자신을 무한히 띄운다. `sim_pool`이
ProcessPoolExecutor를 쓰므로 가정이 아니라 실제 경로다.
"""
import multiprocessing
import socket
import threading
import time
import urllib.error
import urllib.request

HOST = "127.0.0.1"


def pick_port() -> int:
    """비어 있는 포트 하나. 0번 바인드로 OS에게 고르게 하고 곧바로 놓아준다."""
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def wait_until_serving(url: str, timeout: float = 20.0) -> bool:
    """`url`이 응답하기 시작하면 True, 시간이 다하면 False."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return True
        except urllib.error.HTTPError:
            return True  # 응답은 했다 - 404여도 서버는 살아 있다
        except OSError:
            time.sleep(0.1)
    return False


def _serve(port: int) -> None:
    import uvicorn

    from app.api import build_app

    uvicorn.run(build_app(), host=HOST, port=port, log_level="warning")


def main() -> None:
    multiprocessing.freeze_support()
    import webview

    port = pick_port()
    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    url = f"http://{HOST}:{port}"
    if not wait_until_serving(url):
        raise RuntimeError(f"backend did not start on {url}")
    webview.create_window("RapiLab", url, width=1280, height=860)
    webview.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && python -m pytest tests/test_desktop.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: 얼리지 않은 상태로 실제 실행해 본다**

```bash
cd frontend && npm run build
cd ../backend && python -m app.desktop
```
Expected: 네이티브 창이 뜨고 RapiLab UI가 보인다. 니케 풀 탭이 데이터를 읽는지 확인하고 창을 닫는다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/desktop.py backend/tests/test_desktop.py
git commit -m "Open the window only once the server answers"
```

---

### Task 6: PyInstaller 빌드

**Files:**
- Create: `scripts/build_app.py`, `packaging/rapilab.spec`
- Test: 수동 — 빌드 산출물 실행

**Interfaces:**
- Consumes: Task 2의 `hash_sources`/`_VERSION_FILE`, Task 5의 `main()`

- [ ] **Step 1: 빌드 스크립트를 쓴다**

```python
# scripts/build_app.py
"""RapiLab 데스크톱 앱을 빌드한다.

언제 쓰나: 릴리스를 만들 때, 그리고 패키징에 영향을 주는 코드를 고친 뒤
(경로·버전·의존성). 왜 스크립트인가: 세 단계(프론트 빌드 → 버전 스탬프 →
PyInstaller)가 순서대로여야 하고, 버전 스탬프를 빼먹으면 얼린 앱이 시작하자마자
RuntimeError로 죽는다 - 그 실패는 시끄럽지만, 손으로 하면 매번 잊는다.

    python scripts/build_app.py            # 전체 빌드
    python scripts/build_app.py --skip-frontend   # 프론트 dist를 재사용
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.engine_version import _VERSION_FILE, hash_sources  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-frontend", action="store_true",
                        help="frontend/dist를 다시 만들지 않고 그대로 쓴다")
    args = parser.parse_args()

    if not args.skip_frontend:
        subprocess.run(["npm", "run", "build"], cwd=ROOT / "frontend",
                       check=True, shell=True)

    stamp = ROOT / "packaging" / _VERSION_FILE
    stamp.parent.mkdir(exist_ok=True)
    stamp.write_text(hash_sources(ROOT / "backend" / "app"), encoding="utf-8")
    print(f"stamped engine version {stamp.read_text().strip()}")

    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                    str(ROOT / "packaging" / "rapilab.spec")], check=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: spec 파일을 쓴다**

```python
# packaging/rapilab.spec
# PyInstaller spec. `python scripts/build_app.py`로 실행할 것 - 이 파일을 직접
# 돌리면 프론트 빌드와 버전 스탬프가 빠진다.
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "backend" / "app" / "desktop.py")],
    pathex=[str(ROOT / "backend")],
    datas=[
        (str(ROOT / "data"), "data"),
        (str(ROOT / "frontend" / "dist"), "frontend"),
        (str(ROOT / "packaging" / "engine_version.txt"), "."),
    ],
    hiddenimports=["uvicorn.logging", "uvicorn.protocols", "uvicorn.lifespan"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="RapiLab",
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="RapiLab")
```

- [ ] **Step 3: 빌드한다**

Run: `python scripts/build_app.py`
Expected: `dist/RapiLab/RapiLab.exe` 생성

- [ ] **Step 4: 얼린 앱을 실행한다**

Run: `dist/RapiLab/RapiLab.exe`
Expected: 창이 뜨고 UI가 보인다. **확인할 것 셋** — ① 니케 풀에 유닛이 보인다(데이터 경로) ② 추천을 한 번 돌린다(프로세스 풀이 자기를 다시 띄우지 않는다) ③ 결과가 나온다(엔진 버전 스탬프가 읽힌다).

- [ ] **Step 5: 커밋**

```bash
git add scripts/build_app.py packaging/rapilab.spec
git commit -m "Build the app in the order that cannot be done by hand"
```

---

### Task 7: 북마클릿을 로컬 API로 — 설계 확인이 선행

**Files:**
- Modify: `frontend/src/lib/bookmarklet.ts`, `backend/app/api.py` (CORS)
- Test: `frontend/src/lib/bookmarklet.test.ts`

**⚠ 이 Task는 착수 전에 라이브 확인이 필요하다.** 북마클릿은 `https://www.blablalink.com` 페이지에서 돌고, 거기서 `http://127.0.0.1:PORT`로 POST한다. 브라우저의 혼합 콘텐츠 정책이 loopback을 예외로 두는지 **이 프로젝트에서 확인된 바 없다**. 확인 방법: blablalink에 로그인한 탭의 콘솔에서

```js
fetch('http://127.0.0.1:8000/api/supported-units').then(r => console.log(r.status))
```

를 실행해 200이 오는지 본다(백엔드를 8000에 띄워두고). 막히면 이 Task의 접근을 바꿔야 하므로, **막히는지부터 확인한 뒤 나머지 단계를 설계한다.**

또한 Task 5가 포트를 OS에게 고르게 하므로 북마클릿이 주소를 모른다. 확인이 끝나면 **고정 포트로 되돌리거나**(충돌 시 대안 필요) 북마클릿이 후보 포트를 훑는 방식 중 하나를 골라야 하고, 그 선택은 위 확인 결과에 달려 있다.

- [ ] **Step 1: 혼합 콘텐츠 확인 (Fienn)** — 위 스니펫 실행, 결과 기록
- [ ] **Step 2: 결과에 따라 이 Task의 나머지 단계를 설계한다**

---

## 실행 순서

Task 1 → 2 → 3은 서로 독립이라 순서가 자유롭고, Task 4는 1에, 5는 4에, 6은 2·5에 의존한다. Task 7은 Step 1의 확인 결과가 나오기 전까지 착수하지 않는다.

Task 6까지 끝나면 **얼린 앱이 뜨고 추천이 돈다**. 로스터는 그때까지 수동 입력으로만 채울 수 있고, 동기화는 Task 7이 연다.
