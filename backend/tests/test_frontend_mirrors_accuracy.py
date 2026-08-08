"""프론트의 코어 명중률 미러가 엔진과 같은 숫자를 쓰는지.

`frontend/src/lib/coreHitRate.ts`는 `app.accuracy`의 상수를 옮겨 적는다 —
보스 폼이 코어 지름 옆에 무기별 명중률을 즉시 보여주기 위해서고, 타이핑마다
왕복하지 않으려는 선택이다(`lib/elementAdvantage.ts`가 `app.elements`를
미러링하는 것과 같은 관례).

원소 상성과 다른 점이 하나 있다: 그쪽은 바뀌지 않는 게임 규칙 다섯 줄이지만,
탄착군 지름은 수집 데이터(`shot_detail.start_accuracy_circle_scale`)에서
파생돼 실제로 바뀐 적이 있다(MG의 start/end). 표류하면 화면이 조용히 틀린
비율을 적으므로 여기서 대조한다.

`scripts/audit_weapon_accuracy_scales.py`는 파이썬 표를 **데이터**와 대조하고,
이 테스트는 TS 표를 **파이썬 표**와 대조한다 - 사슬의 서로 다른 고리다.
"""
import re
from pathlib import Path

from app.accuracy import WEAPON_SPREAD_DIAMETER, ZERO_SPREAD_HIT_RATE

MIRROR = (Path(__file__).resolve().parents[2]
          / "frontend" / "src" / "lib" / "coreHitRate.ts")


def _mirror_source():
    assert MIRROR.exists(), f"미러 파일이 없다: {MIRROR}"
    return MIRROR.read_text(encoding="utf-8")


def test_the_mirror_uses_the_same_zero_spread_hit_rate():
    source = _mirror_source()
    match = re.search(r"ZERO_SPREAD_HIT_RATE\s*=\s*([\d.]+)", source)
    assert match, "미러에서 ZERO_SPREAD_HIT_RATE를 못 찾았다"
    assert float(match.group(1)) == ZERO_SPREAD_HIT_RATE


def test_the_mirror_uses_the_same_spread_diameters():
    source = _mirror_source()
    body = re.search(
        r"WEAPON_SPREAD_DIAMETER[^=]*=\s*\{(.*?)\}", source, re.DOTALL)
    assert body, "미러에서 WEAPON_SPREAD_DIAMETER를 못 찾았다"
    mirrored = {weapon: float(value)
                for weapon, value in re.findall(r"(\w+):\s*([\d.]+)", body.group(1))}
    assert mirrored == WEAPON_SPREAD_DIAMETER
