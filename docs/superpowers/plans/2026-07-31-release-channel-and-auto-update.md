# 배포채널 + 자동업데이트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 태그를 밀면 GitHub Actions가 앱을 빌드해 Release에 올리고, 설치된 앱이 시작할 때 그것을 받아 스스로 교체·재시작한다.

**Architecture:** 릴리스 태그가 곧 앱 버전이다 — 빌드가 태그를 번들에 심고, 앱은 그것과 GitHub의 최신 릴리스를 비교한다. Windows는 실행 중인 exe를 덮어쓸 수 없으므로 교체는 앱 밖에서 한다: 앱이 새 버전을 임시 폴더에 풀고 헬퍼 스크립트를 띄운 뒤 스스로 종료하면, 헬퍼가 프로세스가 사라지기를 기다렸다가 폴더를 바꿔치고 앱을 다시 실행한다.

**Tech Stack:** GitHub Actions (windows-latest) · PyInstaller · urllib (GitHub REST) · Windows 배치 헬퍼

## Global Constraints

- **저장소:** `https://github.com/fienn-eda/RapiLab` (public). 릴리스 조회는 인증 없이 한다 — 비인증 REST는 시간당 60회이고, 앱은 시작할 때 1회만 부른다.
- **얼리지 않은 실행에서는 업데이트를 하지 않는다.** 개발 중에 리포를 덮어쓰면 안 된다.
- **업데이트 실패는 조용히 넘어간다.** 네트워크가 없거나 GitHub이 죽어도 앱은 현재 버전으로 뜬다 — 업데이트는 부가 기능이지 실행 조건이 아니다.
- **전체 교체.** 델타·패치 없음(결정 5번). 자산은 `dist/RapiLab/` 폴더 전체를 담은 zip 하나.
- 기준선: 백엔드 **1723 passed / 3 skipped** · 프론트 **452 passed**. 각 Task는 이 수를 줄이지 않는다.
- 테스트는 `backend/`에서 돌린다.

## 범위 밖

**⑤ 공개 준비**(스토어 페이지·홍보·개인정보 처리방침 문구). 이 계획이 끝나면 "태그를 밀면 유저에게 도달하고, 유저는 켜기만 하면 최신이 된다"까지가 완성된다.

---

### Task 1: 앱 버전 — 릴리스 태그를 번들에 심는다

**Files:**
- Create: `backend/app/app_version.py`
- Modify: `scripts/build_app.py`, `packaging/rapilab.spec`, `.gitignore`
- Test: `backend/tests/test_app_version.py`

**Interfaces:**
- Produces: `app_version() -> str | None` (얼리지 않았으면 None) · `VERSION_FILE`

`engine_version`은 소스 해시라 **순서를 비교할 수 없다** — 업데이트 판단에는 태그가 필요하다. 둘은 목적이 다르므로 따로 둔다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_app_version.py
"""릴리스 태그. engine_version(소스 해시)과 달리 순서를 비교할 수 있어야 한다.

얼리지 않은 실행에는 태그가 없다 - 개발 중인 코드는 어떤 릴리스도 아니다.
그때 None을 돌려주는 것이 업데이트를 건너뛰게 하는 장치다.
"""
from app import app_version as av


def test_unfrozen_has_no_release_version(monkeypatch):
    monkeypatch.setattr(av.sys, "frozen", False, raising=False)
    av.app_version.cache_clear()
    assert av.app_version() is None
    av.app_version.cache_clear()


def test_frozen_reads_the_stamped_tag(monkeypatch, tmp_path):
    (tmp_path / av.VERSION_FILE).write_text("v1.2.3\n", encoding="utf-8")
    monkeypatch.setattr(av.sys, "frozen", True, raising=False)
    monkeypatch.setattr(av.sys, "_MEIPASS", str(tmp_path), raising=False)
    av.app_version.cache_clear()
    assert av.app_version() == "v1.2.3"
    av.app_version.cache_clear()


def test_a_frozen_build_without_a_tag_is_not_an_error(monkeypatch, tmp_path):
    """태그 없이 얼린 빌드(로컬 실험)는 업데이트만 못 할 뿐 멀쩡히 돌아야 한다.

    engine_version과 다른 점이다: 그쪽은 없으면 캐시가 조용히 낡으므로 거부하지만,
    태그가 없으면 최악이 '업데이트를 안 한다'이고 그건 조용해도 된다.
    """
    monkeypatch.setattr(av.sys, "frozen", True, raising=False)
    monkeypatch.setattr(av.sys, "_MEIPASS", str(tmp_path), raising=False)
    av.app_version.cache_clear()
    assert av.app_version() is None
    av.app_version.cache_clear()
```

- [ ] **Step 2: 실패 확인** — `cd backend && python -m pytest tests/test_app_version.py -q` → `No module named 'app.app_version'`

- [ ] **Step 3: 구현**

```python
# backend/app/app_version.py
"""이 빌드가 어느 릴리스인가.

`engine_version`과 따로 있는 이유: 그쪽은 소스의 내용 해시라 "달라졌다"만
말할 수 있고 "더 새롭다"를 말하지 못한다. 업데이트는 순서 비교가 필요하므로
릴리스 태그를 따로 심는다.

없을 수 있다 - 개발 중 실행이거나, 태그 없이 로컬에서 얼린 빌드다. 그때는
업데이트를 건너뛴다.
"""
import sys
from functools import lru_cache
from pathlib import Path

VERSION_FILE = "app_version.txt"


@lru_cache(maxsize=1)
def app_version() -> str | None:
    if not getattr(sys, "frozen", False):
        return None
    stamped = Path(sys._MEIPASS) / VERSION_FILE
    if not stamped.is_file():
        return None
    return stamped.read_text(encoding="utf-8").strip() or None
```

- [ ] **Step 4: 통과 확인**

- [ ] **Step 5: 빌드가 태그를 심게 한다**

`scripts/build_app.py`에 `--version` 인자를 추가하고, `stamp_version()` 옆에서
`packaging/app_version.txt`를 쓴다(값이 없으면 빈 파일). `rapilab.spec`의
`datas`에 그 파일을 번들 루트로 추가한다. `.gitignore`에
`packaging/app_version.txt`를 넣는다 — 빌드 산출물이다.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/app_version.py backend/tests/test_app_version.py \
        scripts/build_app.py packaging/rapilab.spec .gitignore
git commit -m "Stamp the release tag so the app can tell newer from different"
```

---

### Task 2: 최신 릴리스 조회와 비교

**Files:**
- Create: `backend/app/updater.py`
- Test: `backend/tests/test_updater.py`

**Interfaces:**
- Consumes: Task 1의 `app_version()`
- Produces: `latest_release(timeout) -> dict | None` · `is_newer(current, candidate) -> bool` · `RELEASES_URL`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_updater.py
"""업데이트 판단. 네트워크는 여기서 타지 않는다 - 응답을 주입해 논리만 본다."""
import pytest

from app import updater


@pytest.mark.parametrize("current,candidate,expected", [
    ("v1.0.0", "v1.0.1", True),
    ("v1.0.0", "v1.1.0", True),
    ("v1.0.0", "v2.0.0", True),
    ("v1.0.0", "v1.0.0", False),
    ("v1.0.1", "v1.0.0", False),      # 되돌아가지 않는다
    ("v1.10.0", "v1.9.0", False),     # 문자열 비교였다면 틀린다
    ("v1.9.0", "v1.10.0", True),
])
def test_version_ordering(current, candidate, expected):
    assert updater.is_newer(current, candidate) is expected


def test_an_unparseable_tag_is_never_newer():
    # 태그 규칙을 벗어난 릴리스로 유저를 옮기지 않는다.
    assert updater.is_newer("v1.0.0", "nightly") is False
    assert updater.is_newer("nightly", "v1.0.0") is False


def test_no_current_version_means_no_update():
    # 개발 중 실행이거나 태그 없이 얼린 빌드다.
    assert updater.is_newer(None, "v1.0.0") is False
```

- [ ] **Step 2: 실패 확인**

- [ ] **Step 3: 구현**

```python
# backend/app/updater.py
"""새 릴리스가 있으면 받아서 스스로 교체한다.

Windows는 실행 중인 exe를 덮어쓸 수 없다. 그래서 교체는 앱 밖에서 한다 -
앱은 새 버전을 임시 폴더에 풀고 헬퍼를 띄운 뒤 종료하고, 헬퍼가 프로세스가
사라지기를 기다렸다가 폴더를 바꿔치고 다시 실행한다.

실패는 전부 조용하다. 네트워크가 없어도 앱은 떠야 한다.
"""
import json
import re
import urllib.request

RELEASES_URL = "https://api.github.com/repos/fienn-eda/RapiLab/releases/latest"

# `v1.2.3`만 릴리스로 친다. 그 밖의 태그(nightly 등)로 유저를 옮기지 않는다.
_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def _parts(tag: str | None):
    match = _TAG.match(tag or "")
    return tuple(int(g) for g in match.groups()) if match else None


def is_newer(current: str | None, candidate: str | None) -> bool:
    now, new = _parts(current), _parts(candidate)
    return bool(now and new and new > now)


def latest_release(timeout: float = 5.0) -> dict | None:
    """GitHub의 최신 릴리스. 실패하면 None."""
    try:
        request = urllib.request.Request(
            RELEASES_URL, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return None
```

- [ ] **Step 4: 통과 확인 후 커밋**

```bash
git add backend/app/updater.py backend/tests/test_updater.py
git commit -m "Compare release tags by number, not by string"
```

---

### Task 3: 내려받고, 교체를 예약한다

**Files:**
- Modify: `backend/app/updater.py`
- Test: `backend/tests/test_updater_apply.py`

**Interfaces:**
- Produces: `download_asset(release, dest) -> Path | None` · `stage_update(zip_path, work) -> Path | None` · `write_swap_script(staged, install_dir, exe) -> Path`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_updater_apply.py
"""받은 것을 풀고, 교체 스크립트를 만든다. 실제 교체는 앱이 죽은 뒤 헬퍼가 한다."""
import zipfile

from app import updater


def _zip_with(tmp_path, name="RapiLab"):
    src = tmp_path / "src" / name
    (src / "_internal").mkdir(parents=True)
    (src / "RapiLab.exe").write_text("new exe", encoding="utf-8")
    (src / "_internal" / "data.txt").write_text("payload", encoding="utf-8")
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in src.rglob("*"):
            zf.write(path, path.relative_to(src.parent))
    return archive


def test_staging_unpacks_the_app_folder(tmp_path):
    staged = updater.stage_update(_zip_with(tmp_path), tmp_path / "work")
    assert staged is not None
    assert (staged / "RapiLab.exe").is_file()
    assert (staged / "_internal" / "data.txt").is_file()


def test_a_zip_without_the_exe_is_rejected(tmp_path):
    # 엉뚱한 자산을 풀어놓고 교체하면 앱이 사라진다.
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("readme.txt", "nothing here")
    assert updater.stage_update(archive, tmp_path / "work") is None


def test_the_swap_script_waits_for_the_app_to_exit(tmp_path):
    script = updater.write_swap_script(
        tmp_path / "staged", tmp_path / "install", "RapiLab.exe")
    body = script.read_text(encoding="utf-8")
    # 실행 중인 exe는 덮어쓸 수 없다 - 기다리지 않는 스크립트는 반드시 실패한다.
    assert "timeout" in body.lower() or "ping" in body.lower()
    assert "RapiLab.exe" in body
    assert str(tmp_path / "install") in body
```

- [ ] **Step 2: 실패 확인**

- [ ] **Step 3: 구현** — `updater.py`에 추가

```python
import os
import shutil
import zipfile
from pathlib import Path


def download_asset(release: dict, dest: Path, timeout: float = 300.0) -> Path | None:
    """릴리스의 zip 자산을 받는다. 자산이 없거나 실패하면 None."""
    asset = next((a for a in release.get("assets", [])
                  if a.get("name", "").endswith(".zip")), None)
    if not asset:
        return None
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(asset["browser_download_url"], timeout=timeout) as r:
            dest.write_bytes(r.read())
        return dest
    except Exception:
        return None


def stage_update(archive: Path, work: Path) -> Path | None:
    """zip을 풀고, 앱 폴더로 보이는지 확인한 뒤 그 경로를 돌려준다.

    확인이 있는 이유: 엉뚱한 자산을 풀어 교체하면 설치본이 사라진다. exe가
    보이지 않으면 그것은 우리 앱이 아니다.
    """
    try:
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(work)
    except Exception:
        return None
    for candidate in [work, *(p for p in work.iterdir() if p.is_dir())]:
        if (candidate / "RapiLab.exe").is_file():
            return candidate
    return None


def write_swap_script(staged: Path, install_dir: Path, exe_name: str) -> Path:
    """앱이 죽은 뒤 폴더를 바꿔치고 다시 띄우는 배치.

    앱 자신이 할 수 없는 일이라 밖으로 내보낸다. `timeout`으로 잠깐 기다리는
    이유는 프로세스가 완전히 사라지기 전에는 exe가 잠겨 있기 때문이고,
    robocopy를 쓰는 이유는 열려 있던 파일 몇 개에 실패해도 나머지를 계속
    옮기기 때문이다.
    """
    script = staged.parent / "swap.bat"
    script.write_text(
        "@echo off\r\n"
        "timeout /t 3 /nobreak >nul\r\n"
        f'robocopy "{staged}" "{install_dir}" /MIR /NFL /NDL /NJH /NJS >nul\r\n'
        f'start "" "{install_dir / exe_name}"\r\n',
        encoding="utf-8")
    return script
```

- [ ] **Step 4: 통과 확인 후 커밋**

---

### Task 4: 셸에 배선 — 시작할 때 받고 즉시 재시작

**Files:**
- Modify: `backend/app/desktop.py`, `backend/app/updater.py`
- Test: `backend/tests/test_updater_flow.py`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# backend/tests/test_updater_flow.py
"""시작할 때 한 번 도는 전체 흐름. 네트워크와 프로세스는 주입해 가른다."""
from app import updater


def test_no_update_when_not_frozen(monkeypatch):
    # 개발 중에 리포를 덮어쓰는 일은 없어야 한다.
    monkeypatch.setattr(updater, "app_version", lambda: None)
    assert updater.update_if_available() is False


def test_no_update_when_already_latest(monkeypatch):
    monkeypatch.setattr(updater, "app_version", lambda: "v1.0.0")
    monkeypatch.setattr(updater, "latest_release", lambda **k: {"tag_name": "v1.0.0"})
    assert updater.update_if_available() is False


def test_network_failure_is_silent(monkeypatch):
    monkeypatch.setattr(updater, "app_version", lambda: "v1.0.0")
    monkeypatch.setattr(updater, "latest_release", lambda **k: None)
    assert updater.update_if_available() is False
```

- [ ] **Step 2: 실패 확인**

- [ ] **Step 3: `updater.update_if_available()` 구현**

얼렸고, 태그가 있고, 최신이 더 새로울 때만 받는다. 받고 풀고 스크립트를 만든
뒤 `subprocess.Popen`으로 띄우고 True를 돌려준다. 나머지는 전부 False.

- [ ] **Step 4: `desktop.main()`에 배선**

창을 만들기 **전에** 부른다. True면 헬퍼가 이미 떴으므로 `raise SystemExit(0)`으로
앱을 비운다 — 3초 뒤 헬퍼가 교체하고 다시 띄운다.

- [ ] **Step 5: 통과 확인 후 커밋**

---

### Task 5: GitHub Actions — 태그를 밀면 릴리스가 나온다

**Files:**
- Create: `.github/workflows/release.yml`
- Test: 수동 — 태그를 밀어 워크플로가 자산을 붙이는지 본다

- [ ] **Step 1: 워크플로를 쓴다**

```yaml
# .github/workflows/release.yml
name: release

on:
  push:
    tags: ['v*.*.*']

permissions:
  contents: write   # 릴리스를 만들고 자산을 올리는 데 필요하다

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install frontend deps
        run: npm ci
        working-directory: frontend
      - name: Install app deps
        run: pip install -r backend/requirements-app.txt
      - name: Build
        run: python scripts/build_app.py --version ${{ github.ref_name }}
      - name: Package
        run: Compress-Archive -Path dist/RapiLab -DestinationPath RapiLab-${{ github.ref_name }}.zip
      - name: Smoke the built app
        run: dist/RapiLab/RapiLab.exe --selftest
      - uses: softprops/action-gh-release@v2
        with:
          files: RapiLab-${{ github.ref_name }}.zip
          generate_release_notes: true
```

- [ ] **Step 2: 커밋하고 밀어본다**

첫 실행은 러너에서 PyInstaller가 도는지, `--selftest`가 통과하는지를 본다.
실패하면 로그를 읽고 이 파일만 고친다 — 앱 코드는 이미 검증돼 있다.

- [ ] **Step 3: `v0.1.0` 태그를 밀어 첫 릴리스를 만든다**

---

### Task 6: 자동업데이트를 실제로 확인한다

- [ ] **Step 1:** `v0.1.0` 자산을 받아 설치하고 실행한다(업데이트 없음 → 그냥 뜬다).
- [ ] **Step 2:** `v0.1.1` 태그를 밀어 릴리스를 만든다.
- [ ] **Step 3:** 설치된 `v0.1.0`을 실행한다. 창이 잠깐 떴다 닫히고, 몇 초 뒤 다시 뜨며, 그 버전이 `v0.1.1`이어야 한다.
- [ ] **Step 4:** 오프라인 상태에서 실행해 앱이 그대로 뜨는지 본다(업데이트 실패는 조용하다).

## 실행 순서

Task 1 → 2 → 3 → 4는 순서대로 의존한다. Task 5는 1에만 의존하므로 병행 가능하지만,
**Task 6은 5가 끝나고 릴리스가 두 개 있어야** 할 수 있다.
