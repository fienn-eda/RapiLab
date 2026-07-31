"""새 릴리스가 있으면 받아서 스스로 교체한다.

Windows는 실행 중인 exe를 덮어쓸 수 없다. 그래서 교체는 앱 밖에서 한다 - 앱은
새 버전을 임시 폴더에 풀고 헬퍼 배치를 띄운 뒤 종료하고, 헬퍼가 프로세스가
사라지기를 기다렸다가 설치 폴더를 바꿔치고 앱을 다시 실행한다.

**실패는 전부 조용하다.** 네트워크가 없어도, GitHub이 죽어도, 자산이 이상해도
앱은 현재 버전으로 떠야 한다 - 업데이트는 부가 기능이지 실행 조건이 아니다.
그래서 이 모듈의 함수들은 예외를 던지는 대신 None/False를 돌려준다.
"""
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from app.app_version import app_version
from app.paths import writable_dir

RELEASES_URL = "https://api.github.com/repos/fienn-eda/RapiLab/releases/latest"

# 이 이름이 보여야 우리 앱의 폴더로 인정한다 - 교체 전 유일한 안전장치다.
EXE_NAME = "RapiLab.exe"

# `v1.2.3`만 릴리스로 친다. 그 밖의 태그(nightly, v1.0.0-rc1 등)는 비교 대상이
# 아니다 - 정식 릴리스가 아닌 것으로 유저를 옮기지 않는다.
_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def _parts(tag: str | None) -> tuple[int, ...] | None:
    match = _TAG.match(tag or "")
    return tuple(int(group) for group in match.groups()) if match else None


def is_newer(current: str | None, candidate: str | None) -> bool:
    """`candidate`가 `current`보다 새 릴리스인가.

    숫자로 비교한다: 문자열 비교였다면 v1.9.0이 v1.10.0보다 커 보인다.
    어느 한쪽이라도 태그 규칙 밖이면 False - 모르는 것으로는 옮기지 않는다.
    """
    now, new = _parts(current), _parts(candidate)
    return bool(now and new and new > now)


def latest_release(timeout: float = 5.0) -> dict | None:
    """GitHub의 최신 릴리스 정보. 실패하면 None.

    인증하지 않는다. 공개 저장소이고 앱은 시작할 때 한 번만 부르므로,
    비인증 한도(시간당 60회)로 충분하다.
    """
    try:
        request = urllib.request.Request(
            RELEASES_URL, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return None


def download_asset(release: dict, dest: Path, timeout: float = 300.0) -> Path | None:
    """릴리스의 zip 자산을 `dest`로 받는다. 자산이 없거나 실패하면 None.

    95MB쯤 되므로 타임아웃이 넉넉하다. 느린 회선에서 시작이 오래 걸리는 것보다
    받다 마는 편이 나쁘다 - 받다 만 zip은 아래 stage_update가 걸러낸다.
    """
    asset = next((a for a in release.get("assets", [])
                  if a.get("name", "").endswith(".zip")), None)
    if not asset or not asset.get("browser_download_url"):
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

    확인이 있는 이유: 이 경로의 결과가 곧 설치 폴더를 통째로 덮어쓴다. 엉뚱한
    자산이나 깨진 zip을 그대로 밀면 유저의 설치본이 사라진다. exe가 보이지
    않으면 그것은 우리 앱이 아니므로 교체하지 않는다.

    작업 폴더는 매번 비운다 - 앞선 시도가 남긴 파일이 섞이면 무엇을 설치하는
    중인지 알 수 없게 된다.
    """
    try:
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(work)
    except Exception:
        return None
    # zip이 폴더를 한 겹 싸고 있을 수도, 바로 파일을 담고 있을 수도 있다.
    for candidate in [work, *(p for p in work.iterdir() if p.is_dir())]:
        if (candidate / EXE_NAME).is_file():
            return candidate
    return None


def write_swap_script(staged: Path, install_dir: Path, exe_name: str) -> Path:
    """앱이 죽은 뒤 설치 폴더를 바꿔치고 다시 띄우는 배치.

    앱 자신이 할 수 없는 일이라 밖으로 내보낸다. 기다리는 이유는 프로세스가
    완전히 사라지기 전에는 exe가 잠겨 있기 때문이고, robocopy를 쓰는 이유는
    /MIR로 폴더를 정확히 일치시키면서 - 지워진 파일까지 반영하면서 - 몇 개가
    잠겨 있어도 나머지를 계속 옮기기 때문이다.
    """
    script = staged.parent / "swap.bat"
    script.write_text(
        "@echo off\r\n"
        "timeout /t 3 /nobreak >nul\r\n"
        f'robocopy "{staged}" "{install_dir}" /MIR /NFL /NDL /NJH /NJS >nul\r\n'
        f'start "" "{install_dir / exe_name}"\r\n',
        encoding="utf-8")
    return script


def install_dir() -> Path:
    """설치 폴더 - 얼린 앱의 exe가 놓인 곳.

    `sys._MEIPASS`(번들이 풀린 임시 폴더)가 아니라 `sys.executable`의 부모다.
    둘을 헷갈리면 교체가 임시 폴더로 가고 설치본은 그대로 남는다.
    """
    return Path(sys.executable).resolve().parent


def _launch(script: Path) -> None:
    """헬퍼를 앱과 분리해 띄운다. 앱이 죽어도 살아남아야 교체를 마칠 수 있다."""
    subprocess.Popen(
        ["cmd", "/c", str(script)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0),
        close_fds=True,
    )


def update_if_available() -> bool:
    """새 릴리스가 있으면 받아서 교체를 예약한다. True면 앱은 즉시 종료해야 한다.

    어느 단계에서 실패하든 False이고 앱은 하던 대로 뜬다. 특히 받지 못했거나
    푼 것이 앱 폴더로 보이지 않으면 교체를 걸지 않는다 - 그대로 밀면 유저의
    설치본이 사라진다.
    """
    current = app_version()
    if current is None:
        return False   # 개발 중 실행이거나 태그 없는 빌드
    release = latest_release()
    if not release or not is_newer(current, release.get("tag_name")):
        return False

    work = writable_dir() / "update"
    archive = download_asset(release, work / "release.zip")
    if archive is None:
        return False
    staged = stage_update(archive, work / "unpacked")
    if staged is None:
        return False

    try:
        _launch(write_swap_script(staged, install_dir(), EXE_NAME))
    except Exception:
        return False
    return True
