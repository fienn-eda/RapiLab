"""RapiLab 데스크톱 실행셸.

uvicorn을 데몬 스레드로 띄우고, 실제로 응답할 때까지 기다린 뒤, pywebview 창을
그 주소로 연다. 기다리는 단계가 핵심이다 - 바로 열면 서버가 준비되기 전에 창이
로드를 시도해 빈 화면이 뜨고, 그 증상은 "앱이 안 켜진다"로 보고된다.

`freeze_support()`가 맨 앞에 있는 이유: Windows의 프로세스 풀은 spawn이라 자식이
이 모듈을 다시 임포트한다. 얼린 앱에서 그것은 exe를 다시 실행하는 것이고, 방어가
없으면 앱이 자기 자신을 무한히 띄운다. `sim_pool`이 ProcessPoolExecutor를 쓰므로
가정이 아니라 실제로 지나가는 경로다.

포트를 OS에게 고르게 하는 이유: 고정 포트는 이미 쓰이고 있을 수 있고, 그때 앱은
켜지지 않는다. 대신 북마클릿은 주소를 미리 알 수 없게 되는데, 그 문제는 동기화
경로(계획의 Task 7)에서 다룬다.

실행:
    python -m app.desktop          # 개발 중 (frontend/dist가 있어야 화면이 나온다)
    RapiLab.exe                    # 얼린 뒤
"""
import multiprocessing
import socket
import threading
import time
import urllib.error
import urllib.request

HOST = "127.0.0.1"
WINDOW_TITLE = "RapiLab"
STARTUP_TIMEOUT = 20.0


def pick_port() -> int:
    """비어 있는 포트 하나. 0번에 바인드해 OS에게 고르게 하고 곧바로 놓아준다."""
    with socket.socket() as probe:
        probe.bind((HOST, 0))
        return probe.getsockname()[1]


def wait_until_serving(url: str, timeout: float = STARTUP_TIMEOUT) -> bool:
    """`url`이 응답하기 시작하면 True, 시간이 다하면 False.

    HTTP 상태는 보지 않는다 - 404도 "서버가 살아서 대답했다"는 뜻이고, 프론트
    번들 없이 API만 띄운 개발 상태의 루트가 정확히 그 모양이다.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            # 소켓을 닫지 않으면 ResourceWarning이 뜬다. HTTPError도 응답
            # 객체이므로 같이 닫는다.
            with urllib.request.urlopen(url, timeout=0.5):
                return True
        except urllib.error.HTTPError as exc:
            exc.close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


def _serve(port: int) -> None:
    # 임포트를 함수 안에 두는 이유: 이 모듈은 테스트가 GUI/서버 스택 없이
    # 임포트하고, 얼린 앱에서는 시작 시간이 짧을수록 좋다.
    import uvicorn

    from app.api import build_app

    uvicorn.run(build_app(), host=HOST, port=port, log_level="warning")


def main() -> None:
    multiprocessing.freeze_support()
    import webview

    port = pick_port()
    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    url = f"http://{HOST}:{port}"
    if not wait_until_serving(url):
        raise RuntimeError(
            f"backend did not answer on {url} within {STARTUP_TIMEOUT:.0f}s")
    webview.create_window(WINDOW_TITLE, url, width=1280, height=860)
    webview.start()


if __name__ == "__main__":
    main()
