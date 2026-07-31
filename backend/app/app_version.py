"""이 빌드가 어느 릴리스인가.

`engine_version`과 따로 있는 이유: 그쪽은 소스의 내용 해시라 "달라졌다"만 말할
수 있고 "더 새롭다"를 말하지 못한다. 업데이트는 순서 비교가 필요하므로 릴리스
태그를 따로 심는다. 둘은 목적이 다르니 하나로 합치려 들지 말 것 - 캐시 무효화는
내용이 달라졌는지만 알면 되고, 업데이트는 방향을 알아야 한다.

없을 수 있다 - 개발 중 실행이거나, 태그 없이 로컬에서 얼린 빌드다. 그때는
업데이트를 건너뛴다. `engine_version`이 스탬프가 없으면 거부하는 것과 다른데,
거기서는 값이 없으면 캐시가 조용히 낡지만 여기서는 최악이 "업데이트를 안 한다"
이고 그것은 조용해도 되는 실패이기 때문이다.
"""
import sys
from functools import lru_cache
from pathlib import Path

VERSION_FILE = "app_version.txt"


@lru_cache(maxsize=1)
def app_version() -> str | None:
    """이 빌드의 릴리스 태그(`v1.2.3`), 릴리스 빌드가 아니면 None."""
    if not getattr(sys, "frozen", False):
        return None
    stamped = Path(sys._MEIPASS) / VERSION_FILE
    if not stamped.is_file():
        return None
    return stamped.read_text(encoding="utf-8").strip() or None
