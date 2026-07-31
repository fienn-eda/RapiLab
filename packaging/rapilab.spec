# -*- mode: python ; coding: utf-8 -*-
"""RapiLab PyInstaller spec.

`python scripts/build_app.py`로 실행할 것 — 이 파일을 직접 돌리면 프론트 빌드와
엔진 버전 스탬프가 빠지고, 두 번째가 빠지면 앱이 시작하자마자 죽는다.

datas의 세 항목은 `backend/app/paths.py`의 `bundle_root()` 아래 배치와 정확히
짝을 이룬다. 한쪽만 고치면 얼린 앱에서만 파일을 못 찾는다.
"""
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "backend" / "app" / "desktop.py")],
    pathex=[str(ROOT / "backend")],
    datas=[
        # paths.data_dir()
        (str(ROOT / "data"), "data"),
        # paths.frontend_dist()
        (str(ROOT / "frontend" / "dist"), "frontend"),
        # paths.directory_snapshot()
        (str(ROOT / "tools" / "collect-blablalink" / "nikke-directory.json"),
         "tools/collect-blablalink"),
        # engine_version.VERSION_FILE - 번들 루트에 놓인다
        (str(ROOT / "packaging" / "engine_version.txt"), "."),
        # app_version.VERSION_FILE - 릴리스 태그. 비어 있을 수 있다.
        (str(ROOT / "packaging" / "app_version.txt"), "."),
    ],
    hiddenimports=[
        # uvicorn은 프로토콜/로깅 구현을 문자열로 늦게 임포트해서 정적 분석에
        # 걸리지 않는다.
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    excludes=["pytest", "httpx"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RapiLab",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="RapiLab")
