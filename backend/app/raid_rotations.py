"""이번 회차 레이드 보스. `/update-raid-bosses` 스킬이 공지를 읽어 적고, 보스
설정 화면의 카드 피커가 읽는다.

기계가 읽는 필드는 보스마다 다섯이고, 출처가 둘로 갈린다.

**공지에서 오는 둘** — `weakness`와 `range_band`. 공지가 그 단어로 적은 것을 판독
시점에 스킬이 엔진 어휘로 옮겨 적으므로, 앱이 `stated`의 산문을 파싱하는 일은 없다.

**관측에서 오는 셋** — 공지에 없고 그 보스와 싸워 봐야 아는 값이라 3단계에서
사람에게 받는다. `core_diameter_px`는 화면에서 잰 길이를 엔진 단위로 환산한 값이고
(docs/measurements/accuracy-circle-and-core-px.md), `part_destruction_times`는 파츠가
실제로 깨지는 초, `spawns_adds`는 잡몹이 주기적으로 나오는가다. 마지막 것은 딜
계산에 안 들어가고 홀드 파이어 택틱을 탐색 후보에서 지우는 데만 쓰인다.

나머지(저지 부위·스쿼드 추천 등)는 대응이 확인되지 않아 `stated`에 원문 그대로만
남는다 (docs/superpowers/specs/2026-08-07-raid-boss-rotation-import-design.md D3).

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

# 공지의 「거리」를 옮겨 담는 값. `BossProfile.effective_range_band`와 같은 어휘라
# 화면이 그대로 얹는다. 유니온 공지만 이 항목을 적고 솔로 공지는 적지 않으므로
# None이 허용된다 — 그때는 보스 설정의 적정거리가 「모름」으로 남는다.
RANGE_BANDS = frozenset({"near", "mid", "far"})


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
            band = boss["range_band"]
            if band is not None and band not in RANGE_BANDS:
                raise ValueError(
                    f"{rid}/{boss['name']}: 알 수 없는 거리 {band!r}")
            # 대괄호가 아니라 .get인 것은 의도다: 코어는 재야만 존재하는 값이라
            # 공지가 반드시 답을 주는 weakness/range_band와 성격이 다르다.
            # 번들 파일에 키가 빠지는 것은 라우트가 파일과 완전히 같은지 보는
            # test_the_route_serves_the_file_as_is가 막는다.
            core = boss.get("core_diameter_px")
            if core is not None and not (isinstance(core, (int, float)) and core > 0):
                raise ValueError(
                    f"{rid}/{boss['name']}: 코어 지름은 양수여야 한다 {core!r}")
            # 코어 지름과 같은 이유로 .get이다 - 관측해야만 존재한다.
            for moment in boss.get("part_destruction_times") or []:
                # bool은 int의 하위형이라 따로 막는다: True가 시각 1.0으로 통과하면
                # 판독이 「파괴된다」를 시각 자리에 적은 것이 조용히 살아남는다.
                if isinstance(moment, bool) or not isinstance(moment, (int, float)) \
                        or moment < 0:
                    raise ValueError(
                        f"{rid}/{boss['name']}: 파괴 시각은 0 이상의 수여야 한다 "
                        f"{moment!r}")
            adds = boss.get("spawns_adds")
            if adds is not None and not isinstance(adds, bool):
                raise ValueError(
                    f"{rid}/{boss['name']}: 잡몹 생성은 예/아니오여야 한다 {adds!r}")
            # 가이드도 코어 지름과 같은 계열이라 .get이다 - 공지가 아니라 그 보스와
            # 싸워 본 사람이 적는 값이라 없을 수 있다. 엔진은 이 값을 읽지 않고
            # 화면에만 뜨지만, 깨진 채로 번들에 실리면 가이드 칸이 통째로 빈다.
            guide = boss.get("guide")
            if guide is not None:
                if not isinstance(guide, list):
                    raise ValueError(
                        f"{rid}/{boss['name']}: 가이드는 목록이어야 한다 {guide!r}")
                for entry in guide:
                    if not isinstance(entry, dict):
                        raise ValueError(
                            f"{rid}/{boss['name']}: 가이드 항목은 객체여야 한다 "
                            f"{entry!r}")
                    at = entry.get("at")
                    # None은 시각에 매이지 않는 「상시」 항목이다. bool을 따로 막는
                    # 것은 파괴 시각과 같은 이유다 - True가 시각 1로 통과하면
                    # 「일어난다」를 시각 자리에 적은 것이 조용히 살아남는다.
                    if at is not None and (
                        isinstance(at, bool)
                        or not isinstance(at, (int, float))
                        or at < 0
                    ):
                        raise ValueError(
                            f"{rid}/{boss['name']}: 가이드 시각은 0 이상의 수이거나 "
                            f"비어 있어야 한다 {at!r}")
                    text = entry.get("text")
                    if not isinstance(text, str):
                        raise ValueError(
                            f"{rid}/{boss['name']}: 가이드 항목에 설명이 없다 "
                            f"{entry!r}")
    return doc


def load_rotations(path: Path | None = None):
    """번들된 회차 파일을 읽어 검증한다."""
    path = data_dir() / "raid-rotations.json" if path is None else path
    return validate_rotations(json.loads(path.read_text(encoding="utf-8")))
