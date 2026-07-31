"""릴리스 태그. engine_version(소스 해시)과 달리 순서를 비교할 수 있어야 한다.

얼리지 않은 실행에는 태그가 없다 - 개발 중인 코드는 어떤 릴리스도 아니다.
그때 None을 돌려주는 것이 업데이트를 건너뛰게 하는 장치다.
"""
from app import app_version as av


def test_unfrozen_has_no_release_version(monkeypatch):
    monkeypatch.setattr(av.sys, "frozen", False, raising=False)
    av.app_version.cache_clear()
    try:
        assert av.app_version() is None
    finally:
        av.app_version.cache_clear()


def test_frozen_reads_the_stamped_tag(monkeypatch, tmp_path):
    (tmp_path / av.VERSION_FILE).write_text("v1.2.3\n", encoding="utf-8")
    monkeypatch.setattr(av.sys, "frozen", True, raising=False)
    monkeypatch.setattr(av.sys, "_MEIPASS", str(tmp_path), raising=False)
    av.app_version.cache_clear()
    try:
        assert av.app_version() == "v1.2.3"
    finally:
        av.app_version.cache_clear()


def test_a_frozen_build_without_a_tag_is_not_an_error(monkeypatch, tmp_path):
    """태그 없이 얼린 빌드(로컬 실험)는 업데이트만 못 할 뿐 멀쩡히 돌아야 한다.

    engine_version과 다른 점이다: 그쪽은 없으면 캐시가 조용히 낡으므로 거부하지만,
    태그가 없으면 최악이 '업데이트를 안 한다'이고 그건 조용해도 된다.
    """
    monkeypatch.setattr(av.sys, "frozen", True, raising=False)
    monkeypatch.setattr(av.sys, "_MEIPASS", str(tmp_path), raising=False)
    av.app_version.cache_clear()
    try:
        assert av.app_version() is None
    finally:
        av.app_version.cache_clear()
