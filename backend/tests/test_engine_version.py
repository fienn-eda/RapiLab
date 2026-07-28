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
