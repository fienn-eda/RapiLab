"""주어진 URL을 RapiLab과 같은 창(pywebview + WebView2)으로 띄운다.

언제 쓰나: 설치형 앱에서만 나는 UI 문제를 고칠 때. dist를 다시 굽지 않고도
같은 호스트에서 최신 소스를 볼 수 있다 - 앱이 실행 중이면 PyInstaller가
exe를 덮어쓰지 못하므로 이 경로가 유일할 때가 있다.

보통은 직접 부르지 않는다 - `scripts/probe_app_window.py --url ...` 이 이 파일을
띄운다. 손으로 볼 때만 아래처럼 쓴다. Python 3.14로 돌릴 것(pywebview가 거기
있다 - 아나콘다에는 없다):

    C:\\Python314\\python.exe scripts/webview_host.py http://localhost:5173/
"""
import sys

import webview

if len(sys.argv) < 2:
    sys.exit("usage: webview_host.py <url>")

# 앱과 같은 크기 - 레이아웃이 폭에 따라 갈리므로(900px에서 1단으로 접힌다)
# 여기서 다르면 다른 화면을 보게 된다.
webview.create_window("RapiLab (dev host)", sys.argv[1], width=1280, height=860)
webview.start()
