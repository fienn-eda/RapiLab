"""이 엔진이 계산한 결과를 다른 엔진의 결과와 구별하는 문자열.

클라이언트는 결과를 입력 해시로 캐싱한다. 입력만으로는 부족하다 - 엔진이
바뀌면 같은 입력이 다른 답을 내는데, 캐시는 그걸 모르고 낡은 수치를 계속
보여준다. 버전을 해시에 섞으면 엔진이 바뀌는 순간 전 캐시가 미스가 된다.

값은 손으로 올리는 숫자가 아니라 소스의 내용 해시다: 올리는 걸 잊는 순간
이 모듈이 막으려던 실패가 그대로 재발하기 때문이다. 딜에 영향을 주는 모듈만
고르지 않고 `app/` 전체를 해시하는 이유도 같다 - 새 모듈을 목록에 넣는 걸
잊을 수 있다. API 문구만 고쳐도 버전이 바뀌어 재계산 한 번이 더 생기지만,
그 대가는 수 초이고 실패 방향이 안전한 쪽이다.
"""
import hashlib
import sys
from functools import lru_cache
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent

# 빌드가 소스 해시를 적어 번들에 넣는 파일.
#
# 얼린 앱에는 `.py` 소스가 없다. 그런데 없는 것을 해시하는 것은 예외가 아니라
# **빈 입력의 sha256**이고, 그것은 다른 것과 구별되지 않는 12자 문자열이라
# 아무도 알아채지 못한다 - 이 모듈이 막으려던 "캐시가 조용히 낡는다"가 정확히
# 그 모양으로 되돌아온다. 그래서 얼린 빌드는 계산하지 않고 읽으며, 읽을 것이
# 없으면 시작을 거부한다.
VERSION_FILE = "engine_version.txt"

# 12자 = 48비트. 충돌하면 낡은 캐시를 한 번 더 보여주는 것이 전부이고,
# 이 값은 URL도 파일명도 아닌 캐시 키의 한 조각이라 이 정도면 충분하다.
_VERSION_LENGTH = 12


def hash_sources(root: Path) -> str:
    """`root` 아래 모든 `.py`의 상대 경로와 바이트를 이어 만든 다이제스트.

    경로도 해시에 넣는 이유: 내용이 같은 모듈의 이름만 바뀌어도 엔진은
    달라진 것이다(등록·임포트 경로가 바뀐다). 경로 정렬은 OS의 파일 순회
    순서에 기대지 않도록 POSIX 문자열 기준으로 한다.
    """
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py"),
                       key=lambda p: p.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:_VERSION_LENGTH]


@lru_cache(maxsize=1)
def engine_version() -> str:
    """이 프로세스가 돌리고 있는 엔진의 버전. 소스는 실행 중 바뀌지 않으므로
    한 번만 읽는다."""
    if getattr(sys, "frozen", False):
        stamped = Path(sys._MEIPASS) / VERSION_FILE
        if not stamped.is_file():
            raise RuntimeError(
                f"frozen build has no stamped {VERSION_FILE} - the build step "
                "must write hash_sources() into the bundle. Use "
                "scripts/build_app.py, which does it in the required order.")
        return stamped.read_text(encoding="utf-8").strip()
    return hash_sources(_APP_DIR)
