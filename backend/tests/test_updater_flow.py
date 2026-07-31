"""시작할 때 한 번 도는 전체 흐름. 네트워크와 프로세스는 주입해 논리만 본다."""
from app import updater


def test_no_update_when_not_frozen(monkeypatch):
    # 개발 중에 리포를 덮어쓰는 일은 절대 없어야 한다.
    monkeypatch.setattr(updater, "app_version", lambda: None)
    assert updater.update_if_available() is False


def test_no_update_when_already_latest(monkeypatch):
    monkeypatch.setattr(updater, "app_version", lambda: "v1.0.0")
    monkeypatch.setattr(updater, "latest_release", lambda **kw: {"tag_name": "v1.0.0"})
    assert updater.update_if_available() is False


def test_no_downgrade(monkeypatch):
    monkeypatch.setattr(updater, "app_version", lambda: "v1.2.0")
    monkeypatch.setattr(updater, "latest_release", lambda **kw: {"tag_name": "v1.1.0"})
    assert updater.update_if_available() is False


def test_network_failure_is_silent(monkeypatch):
    monkeypatch.setattr(updater, "app_version", lambda: "v1.0.0")
    monkeypatch.setattr(updater, "latest_release", lambda **kw: None)
    assert updater.update_if_available() is False


def test_a_failed_download_does_not_launch_the_swap(monkeypatch):
    # 받지도 못했는데 교체를 걸면 설치본이 빈 폴더로 덮인다.
    launched = []
    monkeypatch.setattr(updater, "app_version", lambda: "v1.0.0")
    monkeypatch.setattr(updater, "latest_release", lambda **kw: {"tag_name": "v1.1.0"})
    monkeypatch.setattr(updater, "download_asset", lambda *a, **kw: None)
    monkeypatch.setattr(updater, "_launch", lambda script: launched.append(script))
    assert updater.update_if_available() is False
    assert launched == []


def test_a_bad_archive_does_not_launch_the_swap(monkeypatch, tmp_path):
    launched = []
    monkeypatch.setattr(updater, "app_version", lambda: "v1.0.0")
    monkeypatch.setattr(updater, "latest_release", lambda **kw: {"tag_name": "v1.1.0"})
    monkeypatch.setattr(updater, "download_asset", lambda *a, **kw: tmp_path / "x.zip")
    monkeypatch.setattr(updater, "stage_update", lambda *a, **kw: None)
    monkeypatch.setattr(updater, "_launch", lambda script: launched.append(script))
    assert updater.update_if_available() is False
    assert launched == []


def test_a_good_update_launches_the_swap(monkeypatch, tmp_path):
    launched = []
    staged = tmp_path / "staged"
    staged.mkdir()
    monkeypatch.setattr(updater, "app_version", lambda: "v1.0.0")
    monkeypatch.setattr(updater, "latest_release", lambda **kw: {"tag_name": "v1.1.0"})
    monkeypatch.setattr(updater, "download_asset", lambda *a, **kw: tmp_path / "x.zip")
    monkeypatch.setattr(updater, "stage_update", lambda *a, **kw: staged)
    monkeypatch.setattr(updater, "install_dir", lambda: tmp_path / "install")
    monkeypatch.setattr(updater, "_launch", lambda script: launched.append(script))
    assert updater.update_if_available() is True
    assert len(launched) == 1
