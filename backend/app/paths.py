"""번들 데이터와 쓰기 가능 디렉터리가 어디인지 아는 유일한 곳.

얼리기 전에는 `__file__`에서 리포 루트를 거슬러 올라가면 되지만, PyInstaller가
얼리면 그 조상이 존재하지 않는다. 네 모듈이 각자 `parents[2] / "data"`를 하고
있었고 그 넷은 전부 같은 날 같은 방식으로 틀린다 - 그래서 한 곳으로 모은다.
판별을 여기 하나만 두는 것이 이 모듈의 요점이므로, 프론트 번들 경로도 같이
산다(같은 `sys.frozen` 질문이다).

쓰기 경로가 따로 있는 이유: 설치형 앱은 Program Files 아래에 놓이고 거기는
쓰기 금지다. `dotgg_client`가 캐시를 데이터 디렉터리에 쓰고 있었다.
"""
import os
import sys
from pathlib import Path

APP_NAME = "RapiLab"

# 리포 루트. 이 파일이 backend/app/paths.py이므로 두 단계 위다.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_root() -> Path:
    """읽기 전용 자원의 뿌리. 얼린 뒤에는 PyInstaller가 풀어놓은 곳, 아니면 리포 루트.

    아래 셋이 전부 이것 위에 앉는 이유는 단순히 짧아서가 아니라, 번들에 무엇을
    넣어야 하는지가 여기 모여 있어야 spec 파일과 어긋나지 않기 때문이다.
    """
    return Path(sys._MEIPASS) if _frozen() else _REPO_ROOT


def data_dir() -> Path:
    """읽기 전용 번들 데이터(`data/`)."""
    return bundle_root() / "data"


def directory_snapshot() -> Path:
    """공개 니케 디렉터리 스냅샷. `data/` 밖(`tools/`)에 있어 따로 이름을 갖는다."""
    return bundle_root() / "tools" / "collect-blablalink" / "nikke-directory.json"


def frontend_dist() -> Path:
    """빌드된 프론트가 있는 곳. 없을 수도 있다 - 개발 중에는 Vite가 :5173에서
    서빙하고 이 디렉터리는 비어 있는 것이 정상이다."""
    return bundle_root() / "frontend" if _frozen() else _REPO_ROOT / "frontend" / "dist"


def writable_dir() -> Path:
    """앱이 쓸 수 있는 사용자별 디렉터리. 없으면 만든다.

    얼리지 않았을 때도 %LOCALAPPDATA%를 쓴다 - 개발 중에만 리포 안에 쓰면
    "내 PC에서는 되던데"가 정확히 이 경로에서 나온다.
    """
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
