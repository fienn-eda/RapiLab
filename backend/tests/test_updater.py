"""업데이트 판단. 네트워크는 여기서 타지 않는다 - 논리만 본다."""
import pytest

from app import updater


@pytest.mark.parametrize("current,candidate,expected", [
    ("v1.0.0", "v1.0.1", True),
    ("v1.0.0", "v1.1.0", True),
    ("v1.0.0", "v2.0.0", True),
    ("v1.0.0", "v1.0.0", False),
    ("v1.0.1", "v1.0.0", False),      # 되돌아가지 않는다
    ("v1.10.0", "v1.9.0", False),     # 문자열 비교였다면 v1.9가 더 커 보인다
    ("v1.9.0", "v1.10.0", True),
])
def test_version_ordering(current, candidate, expected):
    assert updater.is_newer(current, candidate) is expected


def test_an_unparseable_tag_is_never_newer():
    # 태그 규칙을 벗어난 릴리스(nightly 등)로 유저를 옮기지 않는다.
    assert updater.is_newer("v1.0.0", "nightly") is False
    assert updater.is_newer("nightly", "v1.0.0") is False
    assert updater.is_newer("v1.0.0", "v1.0.0-rc1") is False


def test_no_current_version_means_no_update():
    # 개발 중 실행이거나 태그 없이 얼린 빌드다.
    assert updater.is_newer(None, "v1.0.0") is False


def test_the_releases_url_points_at_this_project():
    assert "fienn-eda/RapiLab" in updater.RELEASES_URL
