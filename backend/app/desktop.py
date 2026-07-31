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

`guard_webview()`가 있는 이유: 화면을 그리는 WebView2는 우리 프로세스가 아니라
따로 사는 프로세스 무리다. 그것이 죽으면 창은 남고 내용만 사라지는데, 우리는
멀쩡히 살아 있으므로 아무 신호도 남지 않는다 - 유저에게는 검은 화면이다.

실행:
    python -m app.desktop          # 개발 중 (frontend/dist가 있어야 화면이 나온다)
    RapiLab.exe                    # 얼린 뒤
    RapiLab.exe --debug            # 창에서 우클릭 -> 개발자 도구
    RapiLab.exe --selftest         # 창 없이 번들 점검
"""
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HOST = "127.0.0.1"
WINDOW_TITLE = "RapiLab"
STARTUP_TIMEOUT = 20.0

# WebView2의 브라우저 프로세스가 죽어도 이 프로세스는 멀쩡히 살아 있다 - 창은
# 남고 내용만 사라지므로 유저에게는 "원인이 없는 검은 화면"이고, 종료 코드에도
# 로그에도 아무것도 남지 않는다. 오버레이 훅 소프트웨어(RivaTuner Statistics
# Server 등)가 주입되면 이 기계에서 실측 40% 확률로 그렇게 됐다.
#
# 막을 수는 없다 - 주입은 우리 코드가 돌기 전에 일어나고, 브라우저 인자로도
# 못 비킨다(--disable-gpu는 오히려 나빴다). 그래서 알아채고 다시 띄운다.
# 주입은 프로세스마다 새로 굴리므로 새 프로세스가 곧 새 기회다.
WEBVIEW_ATTEMPT_ENV = "RAPILAB_WEBVIEW_ATTEMPT"

# 4번이면 위 확률에서 2.6%가 남는다. 무한이 아닌 이유는 아래 _restart_or_give_up
# 참조 - 못 뜨는 앱보다 안 꺼지는 앱이 나쁘다.
WEBVIEW_ATTEMPTS = 4

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


def _relaunch_command() -> list[str]:
    """이 앱을 다시 띄우는 명령. 인자는 그대로 물려준다.

    얼린 뒤에는 `sys.executable`이 RapiLab.exe 자신이지만 개발 중에는 python
    이라, 그것만 띄우면 앱 대신 REPL이 뜬다.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]
    return [sys.executable, "-m", "app.desktop", *sys.argv[1:]]


def _report_dead_webview() -> None:
    """화면을 못 띄웠다는 것을 창 없이 알린다.

    HTML로 알릴 수 없다 - 알릴 대상이 방금 죽은 그 WebView2다. 배포 빌드는
    콘솔도 없으므로 남는 길은 OS 대화상자뿐이다.
    """
    import ctypes

    ctypes.windll.user32.MessageBoxW(
        None,
        "화면을 여러 번 띄우지 못했습니다.\n\n"
        "MSI Afterburner / RivaTuner Statistics Server 같은 오버레이 프로그램이 "
        "켜져 있으면 화면을 그리는 구성요소가 강제로 종료됩니다.\n\n"
        "오버레이를 끄거나, RTSS에서 msedgewebview2.exe 프로필의 application "
        "detection level을 None으로 두고 다시 실행해 주세요.",
        WINDOW_TITLE,
        0x10,  # MB_ICONERROR
    )


def _restart_or_give_up() -> None:
    """죽은 WebView2를 새 프로세스로 갈음한다. 시도를 다 쓰면 알리고 끝낸다.

    되살리지 않고 새로 띄우는 이유: 브라우저 프로세스가 사라지면 그 WebView2
    인스턴스는 무효라 복구 대상이 아니다.

    횟수를 세는 이유: 이 기계에서 100% 죽는 조합이 있으면 무한 재시작이 되고,
    그때 유저는 앱을 끌 수조차 없다 - 검은 화면보다 나쁘다.

    `os._exit`인 이유: 여기는 이미 반쯤 무너진 UI 스레드의 이벤트 핸들러 안이다.
    정상 종료 경로를 타려다 그 스레드에 걸리면 아무 일도 일어나지 않는다.
    """
    try:
        attempt = int(os.environ.get(WEBVIEW_ATTEMPT_ENV, "1"))
    except ValueError:
        attempt = 1   # 이 경로에서 예외가 나면 남는 것은 설명 없는 빈 창이다
    if attempt >= WEBVIEW_ATTEMPTS:
        _report_dead_webview()
        os._exit(1)
    subprocess.Popen(
        _relaunch_command(),
        env={**os.environ, WEBVIEW_ATTEMPT_ENV: str(attempt + 1)},
        close_fds=True,
    )
    os._exit(0)


def guard_webview() -> None:
    """WebView2가 죽으면 앱을 다시 띄우도록 pywebview에 감시를 건다.

    pywebview 6.2.1은 `ProcessFailed`를 구독하지 않는다 - 브라우저 프로세스가
    사라져도 파이썬 쪽에는 아무 신호가 없고, 그래서 빈 창이 그대로 남는다.
    초기화 완료 콜백을 감싸서 거기서 직접 건다.

    실패는 조용하다. 감시는 부가 기능이지 실행 조건이 아니므로, 못 걸었다고
    앱이 안 뜨면 그것이 더 나쁜 고장이다.
    """
    try:
        # 순서가 있다: edgechromium이 WebView2 어셈블리를 CLR에 붙이므로
        # 아래 enum은 그 다음에야 임포트된다.
        from webview.platforms.edgechromium import EdgeChrome

        from Microsoft.Web.WebView2.Core import CoreWebView2ProcessFailedKind
    except Exception:
        return

    def on_process_failed(_sender, args) -> None:
        # 렌더러만 죽은 것은 WebView2가 스스로 다시 띄운다. 브라우저 프로세스가
        # 죽었을 때만 이 인스턴스가 못 쓰게 된다.
        if args.ProcessFailedKind == CoreWebView2ProcessFailedKind.BrowserProcessExited:
            _restart_or_give_up()

    original = EdgeChrome.on_webview_ready

    def on_webview_ready(self, sender, args) -> None:
        # 초기화가 실패하는 경우도 같은 원인에서 온다. 이때는 CoreWebView2가
        # 아예 없어서 아래 구독을 걸 수도 없다.
        if not args.IsSuccess:
            _restart_or_give_up()
            return
        original(self, sender, args)
        sender.CoreWebView2.ProcessFailed += on_process_failed

    EdgeChrome.on_webview_ready = on_webview_ready


def main() -> None:
    multiprocessing.freeze_support()
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(selftest())

    # 창을 만들기 전에 확인한다. 새 릴리스가 있으면 헬퍼가 이미 떴으므로
    # 여기서 앱을 비워야 교체가 가능하다 - 실행 중인 exe는 잠겨 있다.
    # 실패는 조용하고, 그때는 그냥 현재 버전으로 뜬다.
    from app.updater import update_if_available
    if update_if_available():
        raise SystemExit(0)

    import webview

    guard_webview()
    port = pick_port()
    threading.Thread(target=_serve, args=(port,), daemon=True).start()
    url = f"http://{HOST}:{port}"
    if not wait_until_serving(url):
        raise RuntimeError(
            f"backend did not answer on {url} within {STARTUP_TIMEOUT:.0f}s")
    webview.create_window(WINDOW_TITLE, url, width=1280, height=860)
    # `--debug`면 창에서 우클릭으로 개발자 도구가 열린다. 배포 빌드는 콘솔이
    # 없어서, 창 안에서 무슨 일이 났는지 볼 방법이 이것뿐이다 - 서버 로그는
    # 브라우저가 겪은 것을 알지 못한다.
    webview.start(debug="--debug" in sys.argv[1:])


if __name__ == "__main__":
    main()
