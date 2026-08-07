# 수렴 실패에 소리를 붙인다 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 풀 버스트 확장의 고정점 루프가 상한에 걸렸을 때, 지금은 아무도 안 읽는
`full_burst_passes["converged"]` 대신 파이썬 `warnings`로 알려 스크립트·테스트가
수정 없이 알아채게 한다.

**Architecture:** 신호는 `simulate_raid`가 상한을 다 쓰고 루프를 빠져나오는 한
지점에서만 나간다. `warnings.warn`이라 소비자가 아무것도 안 해도 닿고,
`backend/pytest.ini`의 `filterwarnings = error` 덕에 테스트 스위트 전체가 수정
0줄로 소비자가 된다. API 응답도 프론트도 건드리지 않는다.

**Tech Stack:** Python 3.14.6 / pytest 9.1.1 / 표준 라이브러리 `warnings`·`inspect`

**기준선 (2026-08-08 실측, `cd backend && python -m pytest -q`):** 2079 passed / 0 failed / 34.6초.
`rootdir`가 `backend`이고 `configfile: pytest.ini`라 `filterwarnings = error`가
실제로 걸린 상태의 숫자다. **반드시 `backend/`에서 돌릴 것** — 저장소 루트에서
돌리면 `ModuleNotFoundError: No module named 'app'`로 수집이 중단된다(설정 파일
자체는 루트에서도 잡힌다; 깨지는 것은 `sys.path`다).

설계문서: `docs/superpowers/specs/2026-08-08-full-burst-convergence-visibility-design.md`
브랜치: `wip/full-burst-convergence-warning` (설계 커밋 `b47f20f5`가 이미 올라가 있다)

## Global Constraints

- **경고 메시지에 덱 슬러그를 싣지 않는다.** 파이썬 기본 필터가 (텍스트,
  카테고리, 위치)로 중복을 접으므로 덱마다 다른 텍스트를 내면 스윕 한 번이
  수만 줄이 된다. 싣는 것은 상한값과 `fight_duration`뿐.
- **`full_burst_passes`는 결과 dict에 그대로 둔다.** 기존 테스트 두 개가 읽고
  있고(`test_interaction_soda_full_burst_extension.py:151,165`) 「몇 패스
  돌았나」를 묻는 유일한 창구다. 없애는 작업이 아니라 소리를 붙이는 작업이다.
- **안 만드는 것**: API 응답 필드, 프론트 배너, `deck_search`의 질의 헬퍼,
  예외 던지기, `fight_duration` 상한 검증. 전부 설계문서 §6에서 명시적으로
  제외했다.
- **주석·docstring은 한국어로, 「무엇을·왜」만.** 「예전엔 이랬다」를 쓰지 않는다.
- 커밋은 태스크마다 한 번씩.

## File Structure

| 파일 | 책임 | 변경 |
|---|---|---|
| `backend/app/raid_simulator.py` | 경고 카테고리 정의 + 수렴 실패 지점에서 발신 | 수정 (`import` 2줄, 클래스 1개, `simulate_raid` 안 ~12줄) |
| `backend/tests/test_interaction_soda_full_burst_extension.py` | 경고가 나는지 / 안 나는지 / 상한 마진이 유지되는지 | 수정 (import 3줄, 테스트 3개 추가) |
| `docs/roadmap.md` | 미완 항목을 닫고 측정 결과를 남긴다 | 수정 (~10줄) |

새 파일은 없다. 경고는 그것을 아는 유일한 모듈에 두는 것이 맞고, 테스트는 이미
그 픽스처를 가진 파일에 두는 것이 맞다.

---

### Task 1: 수렴 실패가 경고를 낸다

**Files:**
- Modify: `backend/app/raid_simulator.py` (import 블록 103행 위, `MAX_FULL_BURST_PASSES` 근처 512-531행, `simulate_raid` 595-606행)
- Test: `backend/tests/test_interaction_soda_full_burst_extension.py`

**Interfaces:**
- Consumes: `raid_simulator.MAX_FULL_BURST_PASSES` (모듈 전역 int, 현재 32),
  `raid_simulator._simulate_raid_once` (7번째 위치 파라미터가 `fight_duration`),
  테스트 파일의 `_run(deck, fight_duration)` / `_alternating_deck()`
- Produces: `raid_simulator.FullBurstConvergenceWarning` (`UserWarning` 하위
  클래스) — Task 2가 이름으로 참조하지는 않지만 같은 파일에서 조용함을 전제한다

- [ ] **Step 1: 실패 테스트를 쓴다**

`backend/tests/test_interaction_soda_full_burst_extension.py` 상단 import를
바꾼다. 현재 36행이 `from app.raid_simulator import simulate_raid` 한 줄인데,
monkeypatch가 모듈 객체를 필요로 하므로 모듈째 들여온다.

```python
import warnings

import pytest

from app import raid_simulator
from app.raid_simulator import simulate_raid
```

(`import warnings` / `import pytest`는 파일 맨 위, 기존 `from app...` 줄들보다
앞에 둔다.)

파일 맨 끝에 테스트 두 개를 붙인다.

```python
def test_a_run_that_hits_the_pass_cap_says_so_out_loud(monkeypatch):
    """상한에 걸린 답은 고정점이 아니다 - 마지막 패스가 낸 답일 뿐이다. 그 사실이
    `full_burst_passes`에만 있으면 아무도 못 본다(그 플래그를 읽는 하류가 없었다).
    경고로도 나와야 `filterwarnings = error`인 이 스위트와 `scripts/`의 소비자들이
    수정 없이 알아챈다.

    상한 1을 쓰는 이유: 이 픽스처는 200초에서 3패스가 필요하다는 것이 바로 위
    테스트에 못박혀 있으므로, 1은 반드시 수렴 실패다."""
    monkeypatch.setattr(raid_simulator, "MAX_FULL_BURST_PASSES", 1)
    with pytest.warns(raid_simulator.FullBurstConvergenceWarning) as caught:
        result = _run(_alternating_deck(), fight_duration=200.0)
    assert result["full_burst_passes"] == {"passes": 1, "converged": False}
    # 경고와 플래그가 같은 사실을 말하는지, 그리고 메시지만으로 재현이 되는지 -
    # 덱을 싣지 않는 대신 길이는 실려야 한다.
    assert "fight_duration=200.0" in str(caught[0].message)


def test_a_converging_run_stays_silent():
    """확장이 있다고 경고하는 게 아니라 수렴 못 했을 때만 경고한다. 이게 틀리면
    `filterwarnings = error` 아래에서 이 파일의 다른 테스트가 전부 깨진다."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _run(_alternating_deck(), fight_duration=200.0)
    assert [w for w in caught
            if issubclass(w.category, raid_simulator.FullBurstConvergenceWarning)] == []
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && python -m pytest tests/test_interaction_soda_full_burst_extension.py -v
```

기대: `test_a_run_that_hits_the_pass_cap_says_so_out_loud`가
`AttributeError: module 'app.raid_simulator' has no attribute 'FullBurstConvergenceWarning'`로
실패. `test_a_converging_run_stays_silent`도 같은 이유로 실패.
나머지 3개는 통과.

- [ ] **Step 3: 경고 카테고리를 만든다**

`backend/app/raid_simulator.py`의 import 블록 맨 앞(현재 103행 `from app.accuracy ...`
바로 위)에 표준 라이브러리 import를 넣는다.

```python
import inspect
import warnings

from app.accuracy import WEAPON_SPREAD_DIAMETER, core_hit_rate
```

`MAX_FULL_BURST_PASSES = 32`(531행) **바로 아래**에 클래스를 붙인다.

```python


class FullBurstConvergenceWarning(UserWarning):
    """고정점 루프가 상한을 다 쓰고도 자기 입력을 재생산하지 못했다.

    이 경고가 붙은 결과의 `total_damage`는 고정점이 아니다 - 마지막 패스가 낸
    답일 뿐이라 창 길이가 실제와 다르고, 다른 덱과 비교할 수 있는 숫자가 아니다.

    전용 클래스인 이유는 둘이다: `pytest.warns`가 다른 경고와 헷갈리지 않고
    이것만 겨눌 수 있고, 언젠가 누가 이것만 골라 끄고 싶어질 때 축이 있다.
    `UserWarning` 하위라 파이썬 기본 필터에서 안 무시된다.
    """
```

- [ ] **Step 4: 수렴 실패 지점에서 경고를 낸다**

`simulate_raid`(595-606행)의 루프 뒤 두 줄을 이렇게 바꾼다.

```python
    result["full_burst_passes"] = {"passes": MAX_FULL_BURST_PASSES, "converged": False}
    # `converged: False`만으로는 아무도 못 본다 - 이 플래그를 읽는 하류가 없다.
    # 질의 헬퍼를 하나 더 만들어도 `scripts/`의 소비자 16개 중 2개만 부르는
    # `deck_search.never_full_bursts`의 전철을 밟는다. 경고는 소비자가 아무것도
    # 안 해도 닿고, `backend/pytest.ini`의 `filterwarnings = error` 아래에서는
    # 테스트 실패가 된다.
    #
    # 덱을 메시지에 안 싣는 것은 의도다: 파이썬 기본 필터가 (텍스트, 카테고리,
    # 위치)로 중복을 접으므로 덱마다 다른 텍스트를 내면 스윕 한 번이 수만 줄이
    # 된다. `fight_duration`은 요청당 사실상 하나라 접힌 채로도 재현에 쓸 수
    # 있고, 애초에 패스 수를 정하는 축이다.
    bound = inspect.signature(_simulate_raid_once).bind_partial(*args, **kwargs)
    warnings.warn(
        f"풀 버스트 확장이 {MAX_FULL_BURST_PASSES} 패스 안에 수렴하지 않았다 "
        f"(fight_duration={bound.arguments.get('fight_duration', '?')}) - "
        f"이 결과의 total_damage는 고정점이 아니다.",
        FullBurstConvergenceWarning,
        stacklevel=2,
    )
    return result
```

`stacklevel=2`는 경고가 `raid_simulator.py`가 아니라 **부른 쪽** 줄을 가리키게
한다. `bind_partial`을 쓰는 이유는 `simulate_raid(*args, **kwargs)`가 인자를
그대로 넘기므로 `fight_duration`이 위치·키워드 둘 다로 올 수 있어서다. 차가운
경로라 `inspect` 비용은 문제가 되지 않는다.

- [ ] **Step 5: 통과를 확인한다**

```bash
cd backend && python -m pytest tests/test_interaction_soda_full_burst_extension.py -v
```

기대: 5개 전부 PASS.

- [ ] **Step 6: 스위트 전체를 돌려 회귀가 없는지 본다**

```bash
cd backend && python -m pytest -q
```

기대: 기준선(2079 passed / 0 failed)에 새 테스트 2개가 더해진 **2081 passed**.
경고가 `filterwarnings = error`에 걸려 깨지는 테스트가 하나라도 있으면, 그것은
그 덱이 실제로 수렴하지 않는다는 뜻이므로 **회귀가 아니라 발견**이다 — 계획을
멈추고 그 덱을 보고할 것.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/raid_simulator.py backend/tests/test_interaction_soda_full_burst_extension.py
git commit -F - <<'EOF'
수렴 실패가 조용히 나가지 않는다 — 고정점 상한에 경고를 붙인다

full_burst_passes의 converged: False를 읽는 하류가 없어 고정점이 아닌 답이
평범한 damage 숫자로 나가고 있었다. 질의 헬퍼 대신 warnings를 쓴 것은
scripts/의 소비자 16개 중 never_full_bursts를 부르는 것이 2개뿐이기 때문이고,
backend/pytest.ini가 filterwarnings = error라 스위트 전체가 수정 0줄로
소비자가 된다.
EOF
```

---

### Task 2: 상한 32의 실제 마진을 테스트로 못박고 기록을 갱신한다

Task 1이 만든 경고가 **오늘 울릴 수 있는 것인지**를 확정한다. 설계문서 §5의
확인 항목이다. 2026-08-08 측정(격번 픽스처, `full_burst_passes`를 직접 읽음):

| 길이 | 패스 | 소요 |
|---|---|---|
| 200초 | 3 | 0.02s |
| 700초 | **8** | 0.39s |
| 1800초 | 8 | 1.76s |
| 3600초 | 8 | 5.93s |
| 7200초 | **8** | 22.25s |

평탄부는 8에서 확정이고 게임 최대(180초)의 40배에서도 안 올라간다. 상한 32는
4배 마진이다. 700초가 이미 평탄부이면서 0.39초라 스위트에 넣을 수 있다.

**Files:**
- Modify: `backend/tests/test_interaction_soda_full_burst_extension.py` (맨 끝)
- Modify: `backend/app/raid_simulator.py` (516-519행 주석)
- Modify: `docs/roadmap.md` (1272-1281행)

**Interfaces:**
- Consumes: Task 1이 만든 `FullBurstConvergenceWarning`이 이 길이에서 **안**
  난다는 것(이 테스트가 경고를 내면 `filterwarnings = error`에 걸려 실패한다 —
  그 자체가 유효한 단언이다)

- [ ] **Step 1: 평탄부를 못박는 테스트를 쓴다**

`backend/tests/test_interaction_soda_full_burst_extension.py` 맨 끝에 붙인다.

```python
def test_the_pass_count_plateaus_far_below_the_cap():
    """패스 수는 전투 길이를 따라 오르다 8에서 멈춘다 - 상한 32는 4배 마진이다.

    지키는 주장은 「상한은 품질 노브가 아니라 폭주 방지 장치」다. 평탄부가
    올라가기 시작하면 여기서 걸린다.

    700초를 고른 이유: 평탄부의 시작이면서 0.4초에 끝난다. 더 긴 길이는 사이클
    수를 따라 급히 비싸져(3600초 5.9초 · 7200초 22초) 스위트에 못 넣는다 -
    2026-08-08에 7200초까지 손으로 재서 8을 확인했다(게임 최대 180초의 40배).
    """
    result = _run(_alternating_deck(), fight_duration=700.0)
    assert result["full_burst_passes"] == {"passes": 8, "converged": True}
```

- [ ] **Step 2: 통과를 확인한다**

```bash
cd backend && python -m pytest tests/test_interaction_soda_full_burst_extension.py -v
```

기대: 6개 전부 PASS, 파일 전체가 1초 안에 끝난다. 이 테스트가 경고 때문에
실패하면 Task 1의 조건이 틀린 것이므로 멈추고 보고할 것.

- [ ] **Step 3: 상한 주석에 측정 결과를 반영한다**

`backend/app/raid_simulator.py` 516-519행의 문단 끝 문장을 바꾼다.

바꿀 대상:
```
# 사이클씩 앞으로 번진다. 격 사이클 덱을 길이별로 쓸면 3패스(200초) / 5(400초) /
# 7(600초) / 8(700초 이후 평평)이다.
```

바꾼 뒤:
```
# 사이클씩 앞으로 번진다. 격 사이클 덱을 길이별로 쓸면 3패스(200초) / 5(400초) /
# 7(600초) / 8(700초 이후 평평)이고, 7200초 - 게임 최대의 40배 - 까지 재도 8이다
# (2026-08-08). 그러므로 32는 이 확장에 대해 4배 마진이고, 여기 걸리려면 진동해서
# 수렴하지 않는 조합이어야 한다. 걸리면 조용하지 않다:
# `FullBurstConvergenceWarning`을 낸다.
```

- [ ] **Step 4: roadmap의 미완 항목을 닫는다**

`docs/roadmap.md` 1279-1281행의 `- [ ]` 항목을 `- [x]`로 바꾸고 결과를 적는다.

바꿀 대상:
```
- [ ] `full_burst_passes`의 `converged: False`를 읽는 하류가 없다 — 수렴 실패가 조용히
      damage 숫자로 나간다. 상한 32면 실질적으로 안 걸리지만, 걸렸을 때 보이게 할 곳이
      필요하다(API 응답 또는 로그).
```

바꾼 뒤:
```
- [x] **`converged: False`에 소리를 붙였다.** 읽는 하류가 없던 플래그 대신
      `FullBurstConvergenceWarning`을 낸다 — 소비자가 아무것도 안 해도 닿고,
      `backend/pytest.ini`가 `filterwarnings = error`라 **테스트 스위트 전체가
      수정 0줄로 소비자**가 된다. 질의 헬퍼를 안 만든 이유는 선례가 말해준다:
      `scripts/`에서 시뮬 결과를 소비하는 16개 중 `never_full_bursts`를 부르는
      것은 2개뿐이라, 헬퍼는 「읽는 하류가 없다」를 이름만 바꿔 재생산한다.
      수신자는 앱이 아니라 우리로 정했으므로(Fienn, 2026-08-08) API 응답 필드와
      프론트 배너는 만들지 않았다.
      **상한 32의 실제 마진도 같이 쟀다**: 격번 픽스처의 패스 수는 8에서
      평평하고 **7200초 — 게임 최대 180초의 40배 — 까지 안 올라간다**(200초 3 /
      700초 8 / 1800초 8 / 3600초 8 / 7200초 8). 즉 이 경고는 오늘 소다로는
      울릴 수 없고, 진동해서 수렴 안 하는 조합이 미래에 생겼을 때를 위한 것이다.
      700초 평탄부는 0.39초라 테스트로 못박았다.
```

- [ ] **Step 5: 스위트 전체를 돌린다**

```bash
cd backend && python -m pytest -q
```

기대: **2082 passed**.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/raid_simulator.py backend/tests/test_interaction_soda_full_burst_extension.py docs/roadmap.md
git commit -F - <<'EOF'
상한 32의 실제 마진을 못박는다 — 패스 수는 8에서 평평하다

격번 픽스처를 7200초(게임 최대의 40배)까지 재도 8패스다. 상한 32는 4배
마진이고, 새 경고는 진동해서 수렴하지 않는 조합에서만 울린다. 700초 평탄부는
0.39초라 테스트로 남겼고 - 3600초는 5.9초, 7200초는 22초라 스위트에 못 넣는다.
EOF
```

- [ ] **Step 7: 배운 것을 docs/에 남긴다**

`/document` 명령으로 docs-keeper에 넘긴다. 넘길 내용:

> **결정**: 수렴 실패를 알리는 채널로 API 응답 필드(`swap_converged` 선례)가
> 아니라 파이썬 `warnings`를 골랐다. 수신자가 앱 사용자가 아니라 숫자를
> 집계하는 우리(스크립트·측정·테스트)라고 판정했기 때문이고, 그 판정이 서면
> 나머지가 따라온다.
>
> **인사이트**: 「부르면 받는」 질의 헬퍼는 이 저장소에서 2/16 채택률이다
> (`never_full_bursts`). 신호를 놓치지 않게 하려면 소비자가 아무것도 안 해도
> 닿아야 한다. `backend/pytest.ini`의 `filterwarnings = error`는 그 목적에
> 이미 배치된 인프라다 — 경고 하나를 추가하면 2000개 테스트가 전부 검사기가
> 된다.
>
> **인사이트**: 경고 메시지에 가변 식별자(덱 슬러그)를 실으면 파이썬의 중복
> 접기가 무력화되어 스윕에서 수만 줄이 된다. 접히는 축(요청당 하나인 값)만
> 싣는다.

---

## 완료 조건

- `cd backend && python -m pytest -q` → 2082 passed, 0 failed, 출력에 경고 없음
- `git log --oneline wip/scaffolding..HEAD` → 설계 1 + 구현 2 = 3커밋
- `docs/roadmap.md`에 `- [ ] full_burst_passes의 converged: False` 항목이 남아
  있지 않다
