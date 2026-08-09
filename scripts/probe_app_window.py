"""설치형 앱 창(WebView2) 안에서 UI 조작이 실제로 도는지 재고 보고한다.

**언제 쓰나:** 브라우저에서는 되는데 앱에서는 안 된다는 보고가 들어왔을 때.
배포물이 설치형 앱이라, 드래그·클립보드·파일처럼 호스트를 경유하는 UI는
`npm test`와 Chromium이 초록이어도 앱에서 깨질 수 있다. 실제로 그랬다:
WebView2는 `dragstart`만 내고 `dragover`/`drop`을 하나도 전달하지 않아,
드래그가 유일한 배치 수단이던 세 화면에서 편성이 아예 불가능했다
(`docs/insights.md` 「설치형 앱(WebView2)은 dragstart만 내고 끝난다」).

**무엇을 재나** — 미란다 계산기 화면에서 네 가지를 차례로 관측한다:
  1. HTML5 드래그: 팔레트 칩 → 빈 슬롯. 어떤 드래그 이벤트가 실제로 왔는지.
  2. 포인터 이벤트: 같은 동작에서 pointerdown/move/up이 오는지, elementFromPoint가
     대상을 짚는지 - 「드래그를 포인터로 다시 쓰면 되는가」의 답이다.
  3. 클릭 배치: 팔레트 칩을 눌러 자리에 앉는지.
  4. 클릭 제외: 덱 좌석의 얼굴을 눌러 빠지는지.

**함정 셋** (이걸 모르면 잘못된 초록을 본다):
  - 합성 드래그(`Input.dispatchDragEvent`, Playwright의 `dragTo`)는 **호스트를
    안 타서 WebView2에서도 성공한다.** 진짜 `Input.dispatchMouseEvent`로 눌림·
    이동·뗌을 보내야 드러난다. 이 스크립트가 그렇게 한다.
  - DevTools 웹소켓은 Origin 헤더가 붙으면 403으로 막는다 → `suppress_origin=True`.
  - 앱이 실행 중이면 PyInstaller가 exe를 못 덮는다. 그때는 `--url`로 개발 서버를
    같은 WebView2 창에 물려 고친 소스를 확인한다(다시 굽지 않아도 된다).

    python scripts/probe_app_window.py                        # 구운 앱을 잰다
    python scripts/probe_app_window.py --url http://localhost:5173/   # 개발 서버를 같은 창으로
    python scripts/probe_app_window.py --keep                  # 창을 남겨 직접 본다

아나콘다로 돌릴 것 - `websocket-client`가 거기 있다. 창을 띄우는 쪽만
Python 3.14를 쓴다(pywebview가 거기 있다). 새 인스턴스는 SYNC_PORTS의 다음 빈
포트를 잡으므로 이미 떠 있는 앱은 건드리지 않는다.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import websocket  # websocket-client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "dist", "RapiLab", "RapiLab.exe")
# pywebview가 설치된 인터프리터. 아나콘다에는 없다.
PYTHON_314 = r"C:\Python314\python.exe"


class Page:
    """CDP page connection - send() blocks until that id comes back."""

    def __init__(self, ws_url):
        # Origin 헤더가 붙으면 DevTools가 403으로 막는다 - 브라우저 플래그를 더
        # 늘리는 대신 헤더를 안 보낸다.
        self.ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
        self.next_id = 0

    def send(self, method, **params):
        self.next_id += 1
        msg_id = self.next_id
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            reply = json.loads(self.ws.recv())
            if reply.get("id") == msg_id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply.get("result", {})

    def js(self, expression):
        result = self.send(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(json.dumps(result["exceptionDetails"])[:400])
        return result["result"].get("value")

    def mouse(self, kind, x, y, buttons=0):
        self.send(
            "Input.dispatchMouseEvent",
            type=kind,
            x=float(x),
            y=float(y),
            button="left",
            buttons=buttons,
            clickCount=1 if kind in ("mousePressed", "mouseReleased") else 0,
        )


def wait_for_target(port, url_hint, timeout=90):
    """The page target for the app's own origin, once the window is up."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            raw = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2).read()
            for target in json.loads(raw):
                if target.get("type") == "page" and url_hint in target.get("url", ""):
                    return target
            last = f"no matching page target among {[t.get('url') for t in json.loads(raw)]}"
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last = repr(exc)
        time.sleep(1)
    sys.exit(f"ERROR: CDP endpoint never offered the app page ({last})")


SEED_PROFILE = """
(() => {
  const unit = (slug) => ({
    id: slug, character_slug: slug, level: '200', hp: '1000000', atk: '85000', def_: '12000',
    actualHp: '', actualAtk: '', actualDef: '',
    skill_levels: { skill1: '10', skill2: '7', burst: '4' }, overload_options: [],
  })
  const slugs = ['miranda-signature','crown','liter','blanc','noir','dorothy','red-hood','privaty','anis-star']
  localStorage.setItem('nikke-profiles', JSON.stringify({
    activeKey: 'probe:81',
    profiles: { 'probe:81': {
      openId: 'probe', area: 81, nickname: 'DnD Probe', roster: slugs.map(unit),
      results: {}, lastResultHash: null, lastInputs: null, savedRuns: [],
    }},
  }))
  return 'seeded'
})()
"""

OPEN_MIRANDA = """
(() => {
  const byText = (root, text) =>
    [...root.querySelectorAll('button,[role=tab]')].find((e) => e.textContent.trim() === text)
  const tab = byText(document, '계산기')
  if (!tab) return 'no calculator tab'
  tab.click()
  const panel = document.querySelector('#panel-calculator')
  const sub = byText(panel, '미란다 계산기')
  if (!sub) return 'no miranda subtab'
  sub.click()
  return 'opened'
})()
"""

INSTALL_PROBE = """
(() => {
  window.__dnd = []
  const rec = (e) => window.__dnd.push({
    type: e.type,
    target: (e.target.tagName || '?').toLowerCase() + '.' + String(e.target.className || '').split(' ')[0],
    types: e.dataTransfer ? [...e.dataTransfer.types] : null,
  })
  for (const t of ['dragstart','dragenter','dragover','drop','dragend'])
    document.addEventListener(t, rec, false)
  return 'probe installed'
})()
"""

BOXES = """
(() => {
  const panel = document.querySelector('#panel-calculator')
  if (!panel) return { error: 'no calculator panel' }
  const chip = panel.querySelector('.palette__face[draggable="true"]')
  const open = panel.querySelector('.draft-editor__slot--open')
  if (!chip || !open) return { error: 'chip=' + !!chip + ' open=' + !!open }
  chip.scrollIntoView({ block: 'center' })
  const c = chip.getBoundingClientRect(), o = open.getBoundingClientRect()
  return {
    label: chip.getAttribute('aria-label'),
    chip: { x: c.x + c.width / 2, y: c.y + c.height / 2 },
    open: { x: o.x + o.width / 2, y: o.y + o.height / 2 },
    openOnScreen: o.top >= 0 && o.bottom <= innerHeight,
    chipOnScreen: c.top >= 0 && c.bottom <= innerHeight,
  }
})()
"""

READ_RESULT = """
(() => {
  const panel = document.querySelector('#panel-calculator')
  const compact = []
  for (const e of (window.__dnd || [])) {
    const last = compact[compact.length - 1]
    if (last && last.type === e.type && last.target === e.target) { last.n++; continue }
    compact.push({ ...e, n: 1 })
  }
  return {
    seated: [...panel.querySelectorAll('.draft-editor__slot-portrait')].map((i) => i.getAttribute('alt') || i.textContent),
    open: panel.querySelectorAll('.draft-editor__slot--open').length,
    events: compact,
  }
})()
"""


POINTER_PROBE = """
(() => {
  window.__ptr = { down: 0, move: 0, up: 0, overSlot: 0, upTarget: null }
  const slot = document.querySelector('#panel-calculator .draft-editor__slot--open')
  addEventListener('pointerdown', () => window.__ptr.down++, true)
  addEventListener('pointermove', (e) => {
    window.__ptr.move++
    // 놓을 자리를 좌표로 찾을 수 있는가 - 포인터 드래그는 이걸로 히트테스트한다
    const el = document.elementFromPoint(e.clientX, e.clientY)
    if (el && el.closest('.draft-editor__slot--open')) window.__ptr.overSlot++
  }, true)
  addEventListener('pointerup', (e) => {
    window.__ptr.up++
    const el = document.elementFromPoint(e.clientX, e.clientY)
    window.__ptr.upTarget = el ? (el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]) : null
  }, true)
  return 'pointer probe installed, slot found=' + !!slot
})()
"""

READ_POINTER = "(() => window.__ptr)()"

SEAT_BUTTON_BOX = """
(() => {
  const panel = document.querySelector('#panel-calculator')
  // 칩 자체가 배치 컨트롤이다(앉은 칩은 disabled).
  const seat = panel && panel.querySelector('.palette__face:not([disabled])')
  if (!seat) return { error: 'no seatable .palette__face on screen' }
  seat.scrollIntoView({ block: 'center' })
  const r = seat.getBoundingClientRect()
  return { label: seat.getAttribute('aria-label'), x: r.x + r.width / 2, y: r.y + r.height / 2 }
})()
"""

GRIP_BOX = """
(() => {
  const panel = document.querySelector('#panel-calculator')
  // 고정 좌석(미란다)은 div라 버튼이 아니다 - 뺄 수 있는 좌석만 고른다.
  const grip = panel && panel.querySelector('button.draft-editor__slot-grip')
  if (!grip) return { error: 'no removable seat on screen' }
  grip.scrollIntoView({ block: 'center' })
  const r = grip.getBoundingClientRect()
  return { label: grip.getAttribute('aria-label'), x: r.x + r.width / 2, y: r.y + r.height / 2 }
})()
"""

READ_SEATS = """
(() => {
  const panel = document.querySelector('#panel-calculator')
  return {
    open: panel.querySelectorAll('.draft-editor__slot--open').length,
    // img 인지 이름 폴백인지 갈라 본다 - alt와 textContent를 한 칸에 담으면
    // 「초상화가 안 나온다」가 「났다」로 보인다.
    slots: [...panel.querySelectorAll('.draft-editor__slot')].map((s) => {
      const img = s.querySelector('img.draft-editor__slot-portrait')
      const missing = s.querySelector('.draft-editor__slot-portrait--missing')
      return {
        kind: s.classList.contains('draft-editor__slot--open') ? 'open'
              : img ? 'img' : missing ? 'name-fallback' : 'neither',
        src: img ? img.getAttribute('src') : null,
        loaded: img ? (img.complete && img.naturalWidth > 0) : null,
        text: missing ? missing.textContent : (img ? img.getAttribute('alt') : null),
      }
    }),
  }
})()
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=9223, help="WebView2 원격 디버깅 포트")
    parser.add_argument("--keep", action="store_true", help="확인용으로 창을 남긴다")
    parser.add_argument("--url", default="",
                        help="dist/RapiLab.exe 대신 이 URL을 같은 WebView2 창으로 띄운다 - "
                             "앱이 실행 중이면 PyInstaller가 exe를 못 덮으므로 "
                             "고친 소스를 같은 호스트에서 보려면 이 길뿐이다")
    args = parser.parse_args()

    env = dict(os.environ)
    env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"--remote-debugging-port={args.port}"
    if args.url:
        host = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webview_host.py")
        command = [PYTHON_314, host, args.url]
    else:
        if not os.path.isfile(APP):
            sys.exit(f"ERROR: {APP} 가 없다 - 먼저 scripts/build_app.py 를 돌릴 것")
        command = [APP]
    print(f"$ {' '.join(command)} (--remote-debugging-port={args.port})")
    proc = subprocess.Popen(command, env=env)

    try:
        target = wait_for_target(args.port, "5173" if args.url else "127.0.0.1:41")
        print(f"attached: {target['url']}")
        page = Page(target["webSocketDebuggerUrl"])
        page.send("Runtime.enable")
        page.send("Page.enable")

        print(page.js(SEED_PROFILE))
        page.send("Page.reload")
        time.sleep(4)

        print(page.js(OPEN_MIRANDA))
        time.sleep(1)
        print(page.js(INSTALL_PROBE))

        boxes = page.js(BOXES)
        if boxes.get("error"):
            sys.exit(f"ERROR: 화면을 못 찾았다 - {boxes['error']}")
        print(f"drag {boxes['label']}: {boxes['chip']} -> {boxes['open']} "
              f"(chip on screen={boxes['chipOnScreen']}, slot on screen={boxes['openOnScreen']})")

        src, dst = boxes["chip"], boxes["open"]
        # 진짜 마우스 입력. 임계값을 넘기려면 눌린 채로 여러 번 움직여야 한다.
        page.mouse("mouseMoved", src["x"], src["y"])
        page.mouse("mousePressed", src["x"], src["y"], buttons=1)
        steps = 25
        for i in range(1, steps + 1):
            page.mouse(
                "mouseMoved",
                src["x"] + (dst["x"] - src["x"]) * i / steps,
                src["y"] + (dst["y"] - src["y"]) * i / steps,
                buttons=1,
            )
            time.sleep(0.02)
        page.mouse("mouseReleased", dst["x"], dst["y"], buttons=0)
        time.sleep(1.5)

        result = page.js(READ_RESULT)

        # 2번째 관측: HTML5 DnD가 죽어 있어도 포인터 이벤트는 오는가. 이 답이
        # 「드래그를 포인터 이벤트로 다시 쓰면 되는가」를 가른다.
        page.js(POINTER_PROBE)
        page.mouse("mouseMoved", src["x"], src["y"])
        page.mouse("mousePressed", src["x"], src["y"], buttons=1)
        for i in range(1, steps + 1):
            page.mouse(
                "mouseMoved",
                src["x"] + (dst["x"] - src["x"]) * i / steps,
                src["y"] + (dst["y"] - src["y"]) * i / steps,
                buttons=1,
            )
            time.sleep(0.02)
        page.mouse("mouseReleased", dst["x"], dst["y"], buttons=0)
        time.sleep(0.5)
        pointer = page.js(READ_POINTER)

        # 3번째 관측: 고친 경로. 팔레트의 + 를 진짜 마우스로 눌러 자리에
        # 앉는지 본다 - jsdom 초록은 이 창에 대해 아무 말도 하지 않는다.
        seat_box = page.js(SEAT_BUTTON_BOX)
        clicked = {"found": bool(seat_box) and not seat_box.get("error")}
        if clicked["found"]:
            page.mouse("mouseMoved", seat_box["x"], seat_box["y"])
            page.mouse("mousePressed", seat_box["x"], seat_box["y"], buttons=1)
            page.mouse("mouseReleased", seat_box["x"], seat_box["y"], buttons=0)
            time.sleep(1)
            clicked.update(page.js(READ_SEATS))
            clicked["label"] = seat_box["label"]
        else:
            clicked["why"] = seat_box.get("error") if seat_box else "no box"

        # 4번째 관측: 덱 안 초상화를 누르면 편성에서 빠지는가.
        removed = {}
        if clicked.get("found"):
            box = page.js(GRIP_BOX)
            if box and not box.get("error"):
                page.mouse("mouseMoved", box["x"], box["y"])
                page.mouse("mousePressed", box["x"], box["y"], buttons=1)
                page.mouse("mouseReleased", box["x"], box["y"], buttons=0)
                time.sleep(1)
                removed = {"label": box["label"], **page.js(READ_SEATS)}
            else:
                removed = {"why": (box or {}).get("error", "no box")}

        print("\n=== RESULT (json) ===")
        print(json.dumps({"html5_dnd": result, "pointer_events": pointer,
                          "click_to_seat": clicked, "click_to_remove": removed},
                         ensure_ascii=False, indent=1))
    finally:
        if args.keep:
            print(f"\n창을 남긴다 (PID {proc.pid}) - 직접 확인 후 닫을 것")
        else:
            proc.terminate()
            print(f"\n띄운 인스턴스 종료 (PID {proc.pid})")


if __name__ == "__main__":
    main()
