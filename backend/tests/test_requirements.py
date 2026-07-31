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


def test_every_third_party_import_in_app_is_declared():
    imported = set()
    for path in (BACKEND / "app").rglob("*.py"):
        imported |= _top_level_imports(path)
    third_party = {name for name in imported if name not in STDLIB and name not in LOCAL}
    undeclared = third_party - _declared(BACKEND / "requirements.txt")
    assert not undeclared, f"imported but not declared: {sorted(undeclared)}"


def test_the_app_requirements_build_on_the_server_ones():
    # 앱 전용 파일이 서버 목록을 다시 적으면 둘이 갈라진다.
    text = (BACKEND / "requirements-app.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in text


def test_the_packaging_stack_is_declared_for_the_app():
    declared = _declared(BACKEND / "requirements-app.txt")
    assert {"pywebview", "pyinstaller"} <= declared
