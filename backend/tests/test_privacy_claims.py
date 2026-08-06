"""화면 맨 아래 개인정보 안내가 하는 주장을 코드로 못박는다.

안내는 "앱이 스스로 보내는 요청은 시작할 때 GitHub에 새 버전이 있는지 묻는 것
하나뿐"이라고 말한다. 그 문장은 새 바깥 요청이 하나 생기는 순간 틀린 말이 되고,
문구는 코드와 함께 고쳐지지 않는다 - 실제로 이 저장소에서는 호스팅 시절에 쓴
"우리 백엔드가 보는 유일한 식별자" 주석이 백엔드가 유저 PC로 옮겨간 뒤에도
넉 달 가까이 그대로 남아 있었다.

그래서 URL을 하나씩 분류해 둔다. 배포되는 앱이 임포트하는 모듈에서 새 URL이
나오면 이 테스트가 깨지고, 고치려면 그것이 바깥으로 나가는 요청인지 아닌지를
사람이 답해야 한다.

모듈 그래프는 반드시 subprocess에서 재야 한다. `sys.modules`는 pytest 세션
전체가 공유하므로, 이 파일 안에서 그냥 읽으면 형제 테스트가 임포트해 둔
`app.blablalink_api`까지 "배포되는 앱의 모듈"로 세어 버린다.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

# (파일, URL) -> 이것이 바깥으로 나가는 요청이 아닌 이유. 하나만 예외다.
CLASSIFIED = {
    ("api.py", "http://127.0.0.1"): "CORS 허용 출처(들어오는 쪽). 이 PC 안이다.",
    ("api.py", "http://localhost:5173"): "CORS 허용 출처(들어오는 쪽). 개발 서버다.",
    ("api.py", "https://www.blablalink.com"):
        "CORS 허용 출처(들어오는 쪽). 북마크릿이 있는 페이지가 우리에게 보낸다.",
    ("damage_formula.py", "https://nikke.gg/damage-formula/"): "독스트링의 출처 표기.",
    ("desktop.py", "http://{HOST}:{port}"): "자기 자신. 백엔드가 떴는지 보는 주소다.",
    ("updater.py", "https://api.github.com/repos/fienn-eda/RapiLab/releases/latest"):
        "바깥으로 나가는 유일한 요청. 안내가 말하는 그 하나다.",
}

OUTBOUND = ("updater.py", "https://api.github.com/repos/fienn-eda/RapiLab/releases/latest")

# 배포되는 앱이 켜질 때 실제로 거치는 진입점 셋. 파일 목록을 짐작하지 않고
# 인터프리터가 임포트한 것을 그대로 읽는다 - 짐작한 목록은 모듈 하나가
# 추가되는 날 조용히 빗나가고, 그러면 아무것도 지키지 않으면서 통과한다.
_PROBE = """
import json, pathlib, re, sys
import app.api, app.desktop, app.updater

url = re.compile(r"https?://[^\\s\\"')]+")
urls, modules = set(), set()
for name, module in list(sys.modules.items()):
    if not name.startswith("app."):
        continue
    modules.add(name)
    path = getattr(module, "__file__", None)
    if path is None:
        continue
    source = pathlib.Path(path).read_text(encoding="utf-8")
    urls.update((pathlib.Path(path).name, m.group(0)) for m in url.finditer(source))

print(json.dumps({"urls": sorted(urls), "modules": sorted(modules)}))
"""


@pytest.fixture(scope="module")
def shipped():
    """배포되는 앱의 모듈 그래프와 그 안의 URL."""
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=BACKEND_DIR, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    return {
        "urls": {tuple(entry) for entry in payload["urls"]},
        "modules": set(payload["modules"]),
    }


def test_every_url_in_the_shipped_app_is_classified(shipped):
    unclassified = shipped["urls"] - set(CLASSIFIED)

    assert not unclassified, (
        "배포되는 앱에 분류되지 않은 URL이 있다. 바깥으로 나가는 요청이라면 "
        "개인정보 안내(frontend/src/lib/helpText.ts의 HELP.privacy)를 먼저 "
        f"고치고, 아니라면 이유와 함께 CLASSIFIED에 넣을 것: {sorted(unclassified)}"
    )


def test_the_github_release_check_is_the_only_outbound_request(shipped):
    assert OUTBOUND in shipped["urls"], (
        "업데이트 확인이 사라졌거나 주소가 바뀌었다. 안내의 「밖으로 나가는 것」이 "
        "그 요청 하나를 이름으로 가리키므로 함께 고쳐야 한다."
    )


@pytest.mark.parametrize("collector", ["app.blablalink_api", "app.dotgg_client"])
def test_roster_collectors_are_not_reachable_from_the_shipped_app(shipped, collector):
    """blablalink·dotgg 클라이언트는 테스트와 수집 스크립트의 것이다.

    안내는 blablalink 조회가 "앱이 아니라 당신의 브라우저"에서 일어난다고
    말한다. 배포되는 앱이 이 둘 중 하나라도 임포트하게 되면 그 문장이 틀린다.
    """
    assert collector not in shipped["modules"]
