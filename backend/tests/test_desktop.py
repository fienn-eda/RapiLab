"""실행셸에서 GUI가 아닌 부분 - 포트 선택과 준비 대기.

창 자체는 여기서 열지 않는다: 테스트가 사람의 화면을 뺏고, 창이 뜨는지는
2026-07-31 스모크(격리 venv, Python 3.14.6)에서 이미 확인했다. 여기서 고정하는
것은 창을 열기 **전에** 서버가 실제로 응답하는지 기다리는 부분이다 - 그것이
없으면 빈 창이 뜨고, 그 증상은 "앱이 안 켜진다"로 보고된다.
"""
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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
