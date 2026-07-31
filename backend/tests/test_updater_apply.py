"""받은 것을 풀고 교체 스크립트를 만든다. 실제 교체는 앱이 죽은 뒤 헬퍼가 한다."""
import zipfile

from app import updater


def _release_zip(tmp_path, top="RapiLab"):
    """릴리스 자산과 같은 모양 - 앱 폴더 하나를 통째로 담은 zip."""
    src = tmp_path / "src" / top
    (src / "_internal").mkdir(parents=True, exist_ok=True)
    (src / "RapiLab.exe").write_text("new exe", encoding="utf-8")
    (src / "_internal" / "data.txt").write_text("payload", encoding="utf-8")
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in src.rglob("*"):
            zf.write(path, path.relative_to(src.parent))
    return archive


def test_staging_unpacks_the_app_folder(tmp_path):
    staged = updater.stage_update(_release_zip(tmp_path), tmp_path / "work")
    assert staged is not None
    assert (staged / "RapiLab.exe").is_file()
    assert (staged / "_internal" / "data.txt").is_file()


def test_a_zip_without_the_exe_is_rejected(tmp_path):
    # 엉뚱한 자산을 풀어놓고 교체하면 설치본이 사라진다. exe가 없으면 우리 앱이 아니다.
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("readme.txt", "nothing here")
    assert updater.stage_update(archive, tmp_path / "work") is None


def test_a_corrupt_zip_is_rejected(tmp_path):
    archive = tmp_path / "broken.zip"
    archive.write_bytes(b"not a zip at all")
    assert updater.stage_update(archive, tmp_path / "work") is None


def test_staging_twice_does_not_mix_the_two(tmp_path):
    # 앞선 시도가 남긴 파일이 섞이면 무엇을 설치하는지 알 수 없게 된다.
    work = tmp_path / "work"
    updater.stage_update(_release_zip(tmp_path), work)
    (work / "RapiLab" / "leftover.txt").write_text("stale", encoding="utf-8")
    staged = updater.stage_update(_release_zip(tmp_path), work)
    assert staged is not None
    assert not (staged / "leftover.txt").exists()


def test_the_swap_script_waits_before_replacing(tmp_path):
    script = updater.write_swap_script(
        tmp_path / "staged", tmp_path / "install", "RapiLab.exe")
    body = script.read_text(encoding="utf-8")
    # 실행 중인 exe는 잠겨 있다 - 기다리지 않는 스크립트는 반드시 실패한다.
    assert "timeout" in body.lower()
    assert str(tmp_path / "install") in body
    assert "RapiLab.exe" in body
