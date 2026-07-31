"""RapiLab 데스크톱 앱을 빌드한다.

언제 쓰나: 릴리스를 만들 때, 그리고 패키징에 영향을 주는 것을 고친 뒤 —
`app/paths.py`가 아는 경로, 의존성, 프론트.

왜 스크립트인가: 세 단계가 순서대로여야 하고 그중 하나는 잊으면 조용하지 않게
실패한다. 프론트를 빌드하고 → 엔진 버전을 번들에 적고 → 얼린다. 버전 스탬프를
빼먹으면 얼린 앱이 시작하자마자 RuntimeError로 죽는다(`engine_version`이 그렇게
만들어져 있다 — 빈 해시를 조용히 내놓느니 죽는 쪽이다). 손으로 하면 매번 잊는다.

    python scripts/build_app.py                  # 전체
    python scripts/build_app.py --skip-frontend  # frontend/dist를 재사용

산출물은 `dist/RapiLab/RapiLab.exe`.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.engine_version import VERSION_FILE, hash_sources  # noqa: E402

PACKAGING = ROOT / "packaging"


def _run(command, cwd=None):
    print(f"$ {' '.join(str(c) for c in command)}")
    subprocess.run(command, cwd=cwd, check=True,
                   shell=isinstance(command[0], str) and command[0] == "npm")


def build_frontend():
    _run(["npm", "run", "build"], cwd=ROOT / "frontend")
    index = ROOT / "frontend" / "dist" / "index.html"
    if not index.is_file():
        sys.exit(f"ERROR: frontend build produced no {index}")


def stamp_version() -> str:
    """번들에 들어갈 엔진 버전을 적는다.

    얼린 앱에는 `.py`가 없어 런타임에 계산할 수 없다. 여기서 소스를 해시해
    파일로 넣어두면 `engine_version()`이 그것을 읽는다.
    """
    PACKAGING.mkdir(exist_ok=True)
    version = hash_sources(ROOT / "backend" / "app")
    (PACKAGING / VERSION_FILE).write_text(version, encoding="utf-8")
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-frontend", action="store_true",
                        help="frontend/dist를 다시 만들지 않고 그대로 쓴다")
    parser.add_argument("--clean", action="store_true",
                        help="build/ 와 dist/ 를 먼저 지운다")
    args = parser.parse_args()

    if args.clean:
        for path in (ROOT / "build", ROOT / "dist"):
            shutil.rmtree(path, ignore_errors=True)

    if args.skip_frontend:
        if not (ROOT / "frontend" / "dist" / "index.html").is_file():
            sys.exit("ERROR: --skip-frontend 인데 frontend/dist가 비어 있다")
    else:
        build_frontend()

    version = stamp_version()
    print(f"stamped engine version {version}")

    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath",
          str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
          str(PACKAGING / "rapilab.spec")])

    exe = ROOT / "dist" / "RapiLab" / "RapiLab.exe"
    print(f"\nbuilt {exe}" if exe.is_file() else f"\nWARNING: {exe} not found")


if __name__ == "__main__":
    main()
