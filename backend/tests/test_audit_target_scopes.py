"""`scripts/audit_target_scopes.py`의 문구 탐지가 무엇을 잡는지 못박는다.

이 감사는 「좁은 타게팅 문구」를 사람 앞에 늘어놓는 체크리스트다. 그러니 놓치는
문구가 있으면 조용히 실패한다 - 목록에 안 뜨는 줄은 검토된 적이 없는데도 검토된
것처럼 보인다. 실제로 플로라 애장품의 좌석 결함이 그렇게 넘어갔다: 그 불릿은
「adjacent」도 「both sides」도 안 적고 **상태 이름**으로 대상을 가리킨다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_target_scopes import POSITIONAL  # noqa: E402

DIRECT = "■ Activates when assigned to the back row in battle. Affects self and 2 allies on both sides."
VIA_STATE = "■ Activates when entering Burst Stage 2. Affects all allies in the Peace of Mind state."
GRANTS_STATE = "■ Activates at the start of battle as long as this unit is alive. Affects self and both adjacent allies."
SQUAD = "■ Affects all allies."


def test_the_direct_wording_is_flagged():
    assert POSITIONAL.search(DIRECT)


def test_a_state_granted_to_the_sides_is_flagged_where_it_is_granted():
    assert POSITIONAL.search(GRANTS_STATE)


def test_paying_a_state_is_flagged_too():
    # 좌석형 상태를 지급하는 줄만 잡고 그 상태를 **소비하는** 줄을 놓치면, 실제로
    # 딜을 움직이는 불릿이 목록에 안 뜬다 (플로라의 ATK +45.12%가 그랬다).
    assert POSITIONAL.search(VIA_STATE)


def test_a_plain_squad_line_is_not_flagged():
    assert not POSITIONAL.search(SQUAD)


def test_the_state_pattern_does_not_swallow_every_state_line():
    # "in the <X> state"는 좌석과 무관한 상태에도 쓰인다 - 대상 절이 아니라
    # 발동 조건이면 잡으면 안 된다.
    assert not POSITIONAL.search("■ Activates when in Sword Coin status. Affects all allies.")
    assert not POSITIONAL.search("■ Activates when the caster is in the Burst state.")
