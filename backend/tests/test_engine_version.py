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


def test_frozen_without_a_stamped_version_raises_rather_than_returning_a_hash(
        monkeypatch, tmp_path):
    """소스가 없는 채로 해시하면 '빈 입력의 sha256'이 나온다.

    그것은 유효해 보이는 12자 문자열이라 아무도 알아채지 못하고, 프론트의
    결과 캐시는 엔진이 바뀌어도 낡은 수치를 계속 내놓는다 - 이 모듈이 막으려던
    바로 그 실패다. 조용한 오답보다 시끄러운 실패가 낫다.
    """
    import pytest

    from app import engine_version as ev

    ev.engine_version.cache_clear()
    monkeypatch.setattr(ev.sys, "frozen", True, raising=False)
    monkeypatch.setattr(ev.sys, "_MEIPASS", str(tmp_path), raising=False)
    try:
        with pytest.raises(RuntimeError, match="stamped"):
            ev.engine_version()
    finally:
        ev.engine_version.cache_clear()


def test_frozen_reads_the_stamped_version(monkeypatch, tmp_path):
    from app import engine_version as ev

    ev.engine_version.cache_clear()
    (tmp_path / ev.VERSION_FILE).write_text("abc123def456\n", encoding="utf-8")
    monkeypatch.setattr(ev.sys, "frozen", True, raising=False)
    monkeypatch.setattr(ev.sys, "_MEIPASS", str(tmp_path), raising=False)
    try:
        assert ev.engine_version() == "abc123def456"
    finally:
        ev.engine_version.cache_clear()


def test_unfrozen_still_hashes_the_sources(monkeypatch):
    # 개발 중 동작은 바뀌지 않아야 한다 - 스탬프는 얼린 빌드에만 있다.
    from app import engine_version as ev

    ev.engine_version.cache_clear()
    monkeypatch.setattr(ev.sys, "frozen", False, raising=False)
    try:
        assert ev.engine_version() == ev.hash_sources(ev._APP_DIR)
    finally:
        ev.engine_version.cache_clear()
