"""임포트되는 서드파티가 requirements에 다 있는가.

"내 PC에서는 되던데"를 잡는 테스트다. numpy가 빠져 있는 것을 이 방식으로 찾았다
(2026-07-31): `cascade`와 `surrogate`가 쓰는데 선언되지 않았고, Fienn PC에 깔려
있어 아무도 모르고 있었다. 패키징은 그 차이를 즉시 드러낸다.
"""
import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
STDLIB = set(sys.stdlib_module_names)
LOCAL = {"app", "tests"}

# 임포트 이름과 배포 이름이 다른 것들.
IMPORT_TO_PACKAGE = {"webview": "pywebview", "clr": "pythonnet"}

# pythonnet이 CLR에서 노출하는 이름들 - pip에는 없고 `clr.AddReference`가 만든다.
# 셸이 WebView2 이벤트를 다루려면 `Microsoft.Web.WebView2.Core`를 임포트해야
# 하는데, 여기 없으면 그것이 "선언되지 않은 서드파티"로 보인다.
CLR_NAMESPACES = {"Microsoft", "System"}

# 데스크톱 앱으로 띄울 때만 임포트되는 모듈. 서버로 돌릴 때는 지나가지 않으므로
# requirements.txt가 아니라 requirements-app.txt가 책임진다.
APP_ONLY = {"desktop.py"}


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def _declared(requirements: Path) -> set[str]:
    declared = set()
    for line in requirements.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-r"):
            continue
        # "uvicorn[standard]", "numpy>=2.0", "pydantic==2.7" -> 이름만
        name = line.split("[")[0].split("==")[0].split(">=")[0].split("<")[0]
        declared.add(name.strip().lower())
    return declared


def _third_party(paths) -> set[str]:
    imported = set()
    for path in paths:
        imported |= _top_level_imports(path)
    return {IMPORT_TO_PACKAGE.get(name, name) for name in imported
            if name not in STDLIB and name not in LOCAL
            and name not in CLR_NAMESPACES}


def test_every_third_party_import_in_the_server_is_declared():
    server_modules = [p for p in (BACKEND / "app").rglob("*.py") if p.name not in APP_ONLY]
    undeclared = _third_party(server_modules) - _declared(BACKEND / "requirements.txt")
    assert not undeclared, f"imported but not declared: {sorted(undeclared)}"


def test_the_desktop_shell_is_covered_by_the_app_requirements():
    # 셸만 쓰는 것(pywebview)이 서버 목록에 들어가면, 서버로 배포할 때 GUI
    # 스택을 끌고 간다. 그래서 별도 파일이 있고, 이 테스트가 그 경계를 지킨다.
    declared = _declared(BACKEND / "requirements.txt") | _declared(
        BACKEND / "requirements-app.txt")
    undeclared = _third_party([BACKEND / "app" / "desktop.py"]) - declared
    assert not undeclared, f"imported by the shell but not declared: {sorted(undeclared)}"


def test_the_app_requirements_build_on_the_server_ones():
    # 앱 전용 파일이 서버 목록을 다시 적으면 둘이 갈라진다.
    text = (BACKEND / "requirements-app.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in text


def test_the_packaging_stack_is_declared_for_the_app():
    declared = _declared(BACKEND / "requirements-app.txt")
    assert {"pywebview", "pyinstaller"} <= declared
