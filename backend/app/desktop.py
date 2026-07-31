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
import sys
import threading
import time
import urllib.error
import urllib.request

HOST = "127.0.0.1"
WINDOW_TITLE = "RapiLab"
STARTUP_TIMEOUT = 20.0

# 로스터 동기화 북마클릿이 이 앱을 찾아야 하므로 포트는 **알려진 후보** 중에서
# 고른다. OS에게 맡기면(0번 바인드) 주소를 미리 알 수 없어 북마클릿이 어디로
# 보낼지 모르고, 하나로 고정하면 그 포트가 이미 쓰이고 있을 때 앱이 아예 뜨지
# 않는다. 그래서 몇 개를 순서대로 시도한다.
#
# 이 목록은 `frontend/src/lib/bookmarklet.ts`의 같은 목록과 짝이다 - 한쪽만
# 고치면 동기화가 조용히 안 된다. 값은 등록된 서비스가 없는 대역에서 골랐다.
SYNC_PORTS = (41573, 41574, 41575, 41576)


def _is_free(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind((HOST, port))
            return True
        except OSError:
            return False


def pick_port() -> int:
    """북마클릿이 찾을 수 있는 포트 중 비어 있는 첫 번째."""
    for port in SYNC_PORTS:
        if _is_free(port):
            return port
    raise RuntimeError(
        f"none of the sync ports {SYNC_PORTS} are free - another copy of "
        "RapiLab may already be running")


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


def selftest() -> int:
    """창을 열지 않고 얼린 빌드가 성한지 확인한다. 성공하면 0.

    이것이 있는 이유: 얼린 앱은 포트를 OS에게 받으므로 밖에서 접근할 방법이
    없고, 그러면 릴리스를 사람이 눌러보는 것 외에 검증할 길이 없다. 여기서
    보는 넷은 전부 "얼렸을 때만" 깨질 수 있는 것들이다.

        RapiLab.exe --selftest

    결과를 파일에도 쓴다: 배포용 exe는 windowed 부트로더라 콘솔이 없고, 그러면
    stdout이 갈 곳이 없어 종료 코드 말고는 아무것도 안 남는다.
    """
    import json
    import urllib.request

    from app.engine_version import engine_version
    from app.paths import writable_dir

    lines: list[str] = []

    def report(message: str) -> None:
        print(message)
        lines.append(message)

    def finish(code: int) -> int:
        (writable_dir() / "selftest.log").write_text(
            "\n".join(lines) + f"\nexit: {code}\n", encoding="utf-8")
        return code

    port = pick_port()
    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    url = f"http://{HOST}:{port}"
    if not wait_until_serving(url):
        report(f"FAIL: backend did not answer on {url}")
        return finish(1)

    # ① 엔진 버전 - 얼린 빌드는 스탬프를 읽어야 하고, 없으면 여기서 죽는다.
    report(f"engine version: {engine_version()}")

    # ② 번들 데이터 - 경로가 어긋나면 유닛이 0개로 조용히 나온다.
    # 이 엔드포인트는 리스트를 그대로 낸다(response_model=list[SupportedUnit]).
    with urllib.request.urlopen(f"{url}/api/supported-units") as response:
        units = json.load(response)
    report(f"supported units: {len(units)}")
    if not units:
        report("FAIL: no units - data path is wrong inside the bundle")
        return finish(1)

    # ③ 프론트 번들 - 없으면 창이 빈 화면으로 뜬다.
    with urllib.request.urlopen(url) as response:
        served_index = "<div id=\"root\"" in response.read().decode("utf-8", "replace")
    report(f"serves the app shell: {served_index}")
    if not served_index:
        return finish(1)

    # ④ 프로세스 풀 - freeze_support()가 없으면 워커가 exe를 다시 실행해서
    # 앱이 자기 자신을 무한히 띄운다. 실제로 하나 돌려봐야 알 수 있다.
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=1) as pool:
        if pool.submit(abs, -7).result(timeout=60) != 7:
            report("FAIL: process pool returned the wrong answer")
            return finish(1)
    report("process pool: ok")
    return finish(0)


def main() -> None:
    multiprocessing.freeze_support()
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(selftest())

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
