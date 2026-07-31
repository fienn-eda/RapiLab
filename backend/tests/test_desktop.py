"""실행셸에서 GUI가 아닌 부분 - 포트 선택, 준비 대기, WebView2 복구.

창 자체는 여기서 열지 않는다: 테스트가 사람의 화면을 뺏고, 창이 뜨는지는
2026-07-31 스모크(격리 venv, Python 3.14.6)에서 이미 확인했다. 여기서 고정하는
것은 창을 열기 **전에** 서버가 실제로 응답하는지 기다리는 부분이다 - 그것이
없으면 빈 창이 뜨고, 그 증상은 "앱이 안 켜진다"로 보고된다.
"""
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app import desktop


def test_pick_port_returns_a_port_that_is_actually_free():
    port = desktop.pick_port()
    with socket.socket() as probe:
        probe.bind((desktop.HOST, port))  # 비어 있지 않으면 OSError


def test_pick_port_only_returns_ports_the_bookmarklet_knows_about():
    # 북마클릿은 목록에 없는 주소로는 보낼 수 없다 - OS가 고른 임의 포트를
    # 쓰면 동기화가 앱을 못 찾는다.
    assert desktop.pick_port() in desktop.SYNC_PORTS


def test_pick_port_steps_past_one_that_is_taken():
    # 하나로 고정하지 않는 이유 - 그 포트가 쓰이고 있으면 앱이 아예 못 뜬다.
    first = desktop.SYNC_PORTS[0]
    with socket.socket() as taken:
        taken.bind((desktop.HOST, first))
        taken.listen(1)
        assert desktop.pick_port() != first
        assert desktop.pick_port() in desktop.SYNC_PORTS


def test_pick_port_says_so_when_every_candidate_is_taken(monkeypatch):
    monkeypatch.setattr(desktop, "_is_free", lambda port: False)
    try:
        desktop.pick_port()
    except RuntimeError as exc:
        assert "already be running" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_wait_until_serving_gives_up_instead_of_hanging():
    # 아무도 듣지 않는 포트. 영원히 창을 안 여는 것보다 실패를 보고해야 한다.
    assert desktop.wait_until_serving(f"http://{desktop.HOST}:9", timeout=0.5) is False


def _serve_ok():
    class Ok(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer((desktop.HOST, 0), Ok)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_wait_until_serving_sees_a_live_server():
    server = _serve_ok()
    try:
        url = f"http://{desktop.HOST}:{server.server_port}"
        assert desktop.wait_until_serving(url, timeout=5.0) is True
    finally:
        # shutdown()은 serve_forever 루프만 멈춘다. 리스닝 소켓은 server_close()가
        # 닫고, 안 닫으면 ResourceWarning이 테스트를 깨뜨린다.
        server.shutdown()
        server.server_close()


def test_a_404_still_counts_as_serving():
    """응답이 오면 서버는 살아 있다.

    루트가 404를 내는 구성(프론트 번들 없이 API만 띄운 개발 상태)에서 이걸
    실패로 읽으면, 창은 멀쩡히 뜰 수 있는데 셸이 20초를 기다리다 죽는다.
    """
    class NotFound(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(404)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer((desktop.HOST, 0), NotFound)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://{desktop.HOST}:{server.server_port}"
        assert desktop.wait_until_serving(url, timeout=5.0) is True
    finally:
        # shutdown()은 serve_forever 루프만 멈춘다. 리스닝 소켓은 server_close()가
        # 닫고, 안 닫으면 ResourceWarning이 테스트를 깨뜨린다.
        server.shutdown()
        server.server_close()


class _Exited(Exception):
    """`os._exit` 자리. 진짜를 부르면 테스트 실행기가 통째로 사라진다."""

    def __init__(self, code: int):
        self.code = code


@pytest.fixture
def restart_probe(monkeypatch):
    """재시작 경로를 관찰한다 - 무엇을 띄웠고 어떤 코드로 나갔는지."""
    spawned = []
    monkeypatch.setattr(desktop.subprocess, "Popen",
                        lambda command, **kwargs: spawned.append((command, kwargs)))
    monkeypatch.setattr(desktop.os, "_exit",
                        lambda code: (_ for _ in ()).throw(_Exited(code)))
    monkeypatch.delenv(desktop.WEBVIEW_ATTEMPT_ENV, raising=False)
    return spawned


def test_relaunch_runs_the_exe_itself_when_frozen(monkeypatch):
    # 얼린 뒤 sys.executable은 RapiLab.exe다. 인자를 물려줘야 --debug로 띄운
    # 앱이 재시작 뒤에도 --debug로 뜬다.
    monkeypatch.setattr(desktop.sys, "frozen", True, raising=False)
    monkeypatch.setattr(desktop.sys, "executable", r"C:\RapiLab\RapiLab.exe")
    monkeypatch.setattr(desktop.sys, "argv", ["RapiLab.exe", "--debug"])
    assert desktop._relaunch_command() == [r"C:\RapiLab\RapiLab.exe", "--debug"]


def test_relaunch_runs_the_module_when_not_frozen(monkeypatch):
    # 개발 중에는 sys.executable이 python이라 그것만 띄우면 REPL이 뜬다.
    monkeypatch.delattr(desktop.sys, "frozen", raising=False)
    monkeypatch.setattr(desktop.sys, "executable", r"C:\python.exe")
    monkeypatch.setattr(desktop.sys, "argv", ["-m", "--debug"])
    assert desktop._relaunch_command()[:3] == [r"C:\python.exe", "-m", "app.desktop"]


def test_a_dead_webview_gets_another_try(monkeypatch, restart_probe):
    monkeypatch.setattr(desktop, "_relaunch_command", lambda: ["RapiLab.exe"])
    with pytest.raises(_Exited) as exit_info:
        desktop._restart_or_give_up()
    assert exit_info.value.code == 0
    command, kwargs = restart_probe[0]
    assert command == ["RapiLab.exe"]
    assert kwargs["env"][desktop.WEBVIEW_ATTEMPT_ENV] == "2"


def test_the_new_process_keeps_the_rest_of_the_environment(monkeypatch, restart_probe):
    # 환경을 통째로 갈아끼우면 PATH도 사라진다 - 그러면 재시작한 앱은 아예 못 뜬다.
    monkeypatch.setattr(desktop, "_relaunch_command", lambda: ["RapiLab.exe"])
    monkeypatch.setenv("RAPILAB_TEST_MARKER", "kept")
    with pytest.raises(_Exited):
        desktop._restart_or_give_up()
    assert restart_probe[0][1]["env"]["RAPILAB_TEST_MARKER"] == "kept"


def test_it_stops_retrying_and_says_why(monkeypatch, restart_probe):
    """무한 재시작은 검은 화면보다 나쁘다 - 유저가 앱을 끌 수조차 없다."""
    told = []
    monkeypatch.setattr(desktop, "_report_dead_webview", lambda: told.append(True))
    monkeypatch.setenv(desktop.WEBVIEW_ATTEMPT_ENV, str(desktop.WEBVIEW_ATTEMPTS))
    with pytest.raises(_Exited) as exit_info:
        desktop._restart_or_give_up()
    assert exit_info.value.code == 1
    assert told == [True]
    assert restart_probe == []


def test_a_garbled_attempt_count_does_not_break_the_recovery(monkeypatch, restart_probe):
    # 이 경로는 이미 무언가 잘못된 상태에서 도는 곳이다. 여기서 예외가 나면
    # 남는 것은 아무 설명 없는 빈 창이다.
    monkeypatch.setattr(desktop, "_relaunch_command", lambda: ["RapiLab.exe"])
    monkeypatch.setenv(desktop.WEBVIEW_ATTEMPT_ENV, "일곱")
    with pytest.raises(_Exited) as exit_info:
        desktop._restart_or_give_up()
    assert exit_info.value.code == 0


def test_the_guard_gives_up_quietly_when_pywebview_is_missing():
    """감시를 못 걸어도 앱은 떠야 한다 - 감시는 부가 기능이지 실행 조건이 아니다.

    이 테스트 환경에는 pywebview가 없다. 그래서 여기서 통과한다는 것은 곧
    임포트 실패가 앱을 죽이지 않는다는 뜻이다.
    """
    desktop.guard_webview()
