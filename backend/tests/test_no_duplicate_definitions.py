"""Every top-level definition in the engine is defined exactly once.

A duplicate is invisible at runtime - Python simply keeps the last one - so a
merge that concatenates two revisions of a region instead of replacing it
leaves the file importable, the tests green, and one of the two copies silently
dead. That happened in `skill_rules/_helpers.py`: three helpers were defined
twice, and the surviving `instant_nuke_pulse_rule` was the copy carrying the
docstring its own commit had set out to replace, while the copy with the new
docstring carried a body belonging to a different helper.
"""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"


def _duplicate_definitions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = [node.name for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef))]
    return sorted({name for name in names if names.count(name) > 1})


def test_no_module_defines_the_same_name_twice():
    offenders = {str(path.relative_to(APP)): duplicates
                 for path in sorted(APP.rglob("*.py"))
                 if (duplicates := _duplicate_definitions(path))}
    assert offenders == {}
