"""번들 데이터는 어디서 읽고, 쓰기는 어디로 가는가.

얼린 앱에서 깨지는 것은 코드가 아니라 경로다. `sys.frozen`과 `sys._MEIPASS`는
PyInstaller가 런타임에 심는 값이라 여기서는 monkeypatch로 흉내낸다.
"""
from app import paths


def test_data_dir_is_the_repo_data_when_not_frozen():
    assert paths.data_dir().name == "data"
    assert (paths.data_dir() / "nikke-stat-tables").is_dir()


def test_data_dir_follows_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.data_dir() == tmp_path / "data"


def test_frontend_dist_follows_meipass_when_frozen(monkeypatch, tmp_path):
    # 프론트 번들도 같은 판별을 쓴다 - 판별이 두 곳에 생기면 이 모듈이 없애려던
    # 문제가 그대로 돌아온다.
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.frontend_dist() == tmp_path / "frontend"


def test_frontend_dist_is_the_vite_output_when_not_frozen():
    assert paths.frontend_dist().parts[-2:] == ("frontend", "dist")


def test_writable_dir_is_not_inside_the_bundle_when_frozen(monkeypatch, tmp_path):
    # Program Files 아래는 쓰기 금지라, 얼렸을 때의 쓰기 경로가 번들 안이면 안 된다.
    # 번들과 쓰기 위치를 서로의 부모가 아닌 곳에 둬야 이 주장이 의미를 갖는다.
    bundle = tmp_path / "bundle"
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    writable = paths.writable_dir()
    assert bundle not in writable.parents
    assert writable != paths.data_dir()
    assert writable.name == "RapiLab"


def test_writable_dir_exists_after_the_call(monkeypatch, tmp_path):
    # 호출자가 mkdir을 기억할 필요가 없어야 한다 - dotgg_client가 캐시를 쓰기
    # 직전에 부르는 자리다.
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    assert paths.writable_dir().is_dir()
