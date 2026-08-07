"""이번 회차 레이드 보스. `/update-raid-bosses` 스킬이 공지를 읽어 적고, 보스
설정 화면의 카드 피커가 읽는다.

기계가 읽는 필드는 보스마다 `weakness` 하나뿐이다. 거리·부위파괴 같은 것은
공지가 명시하지 않으므로 `stated`에 원문 그대로 들어가고 앱은 해석하지 않는다
(docs/superpowers/specs/2026-08-07-raid-boss-rotation-import-design.md D3).

파일의 키는 보스 이름이 아니라 (회차, 보스)다. 같은 보스가 시즌마다 다른 속성을
달고 나오므로, 지난 시즌 기록이 이번 시즌 보스에 얹힐 수 있는 구조를 아예 만들지
않는다 (같은 문서 D2).
"""
import json
from datetime import datetime
from pathlib import Path

from app.elements import ELEMENTS
from app.paths import data_dir

RAID_KINDS = frozenset({"solo", "union"})


def _parse_time(value, where):
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{where}: 시각을 읽을 수 없다 - {value!r}") from exc


def validate_rotations(doc):
    """검사를 통과하면 `doc`을 그대로 돌려준다.

    깨진 파일에 대해 빈 목록을 내지 않고 예외를 던지는 이유: 런타임에서는
    이 예외도 결국 프런트(`useRaidRotations`)가 빈 목록으로 삼켜 화면은
    똑같이 조용하다. 예외가 실제로 잡히는 자리는 `test_the_shipped_file_loads`
    등 이 파일을 로드해 보는 테스트다 — 깨진 파일이 사용자에게 닿기 전에
    거기서 걸린다.
    """
    seen = set()
    for rotation in doc["rotations"]:
        rid = rotation["id"]
        if rid in seen:
            raise ValueError(f"회차 id가 중복이다: {rid!r}")
        seen.add(rid)
        if rotation["raid"] not in RAID_KINDS:
            raise ValueError(f"{rid}: 알 수 없는 raid {rotation['raid']!r}")
        starts = _parse_time(rotation.get("starts_at"), rid)
        ends = _parse_time(rotation["ends_at"], rid)
        if starts is not None and starts >= ends:
            raise ValueError(f"{rid}: starts_at이 ends_at보다 늦거나 같다")
        if not rotation["bosses"]:
            raise ValueError(f"{rid}: bosses가 비어 있다")
        for boss in rotation["bosses"]:
            weakness = boss["weakness"]
            if weakness not in ELEMENTS:
                raise ValueError(
                    f"{rid}/{boss['name']}: 알 수 없는 약점 {weakness!r}")
    return doc


def load_rotations(path: Path | None = None):
    """번들된 회차 파일을 읽어 검증한다."""
    path = data_dir() / "raid-rotations.json" if path is None else path
    return validate_rotations(json.loads(path.read_text(encoding="utf-8")))
