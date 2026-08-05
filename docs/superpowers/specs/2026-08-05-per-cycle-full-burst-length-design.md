# 사이클별 풀 버스트 길이 + 시간을 아는 조건 — 설계

날짜: 2026-08-05

아르카나가 추천 상위권에 계속 노출된다는 Fienn 제보(2026-08-05)에서 출발했다. 원인은
탐색이 아니라 인코딩이다: 그녀의 조건부 불릿 셋이 **원문상 절대 만족될 수 없는 조건**을
항상 만족한 것으로 처리되고 있고, 그 조건을 열 수 있는 유일한 유닛(이사벨)의 효과는
엔진에 표현 수단이 없다. 두 문제는 한 몸이라 따로 고칠 수 없다.

## 배경 — 무엇이 어떻게 틀렸나

**아르카나의 조건.** 스킬 1 「Awakened Destiny」 1불릿(The Magician), 스킬 2
「Cycle of Destiny」 1·2불릿(Strength, Death)은 셋 다 이렇게 시작한다:

> ■ Activates when Full Burst ends. … **if self is in Wheel of Fortune status.**

「운명의 수레바퀴」는 그녀의 버스트 「Shackles of Destiny」가 전기 코드 아군(자신 포함)에게
거는 **10초**짜리 상태다. 그녀는 Burst 2이므로 시전 시각은 **버스트 스테이지 2**이고,
풀 버스트의 10초는 그 뒤의 **B3 시전이 끝나야** 시작한다. 따라서 표준 창에서 수레바퀴는
풀 버스트보다 항상 **먼저** 끝난다 — 조건은 구조적으로 만족 불가다.

**엔진의 인코딩.** `arcana.py`는 이 게이트를 `own_burst_fired_this_cycle()`로 읽었다.
그 조건은 `caster_slug in context.burst_used_this_cycle` 하나뿐이라 **시계가 없다**.
같은 실행에서 엔진 자신의 이펙트 레지스트리가 반박한다:

```
   fb_end     gate   wheel granted -> expires   really active?
    12.600   True      2.500 ->   12.500        False
```

**대가.** 실로스터로 조건부 불릿 셋만 껐다 켜서 잰 값:

| 덱 | 현재 | 게이트 정직 | 차이 |
|---|---:|---:|---:|
| 아니스:스타 · 아르카나 · 이사벨 · 크라운 · 신데렐라 | 6.93B | 5.37B | **+28.9%** |
| 아니스:스타 · 아르카나 · 크라운 · 신데렐라 · 네온:비전아이 | 8.42B | 6.73B | **+25.2%** |

대부분은 Death의 쿨감이 아니라 Magician(공댐 +180%)·Strength(자ATK 180% flat)가
**전기 B3 캐리**에게 주는 몫이다(신데렐라 +76.5%, 네온 +71.6%).

**여는 유일한 길.** 수집 데이터 전체에서 풀 버스트 길이를 바꾸는 유닛은 셋뿐이고,
**줄이는** 쪽은 이사벨 하나다.

| 유닛 | 원문 | 방향 |
|---|---|---|
| Isabel | Sonic Chaser: `Full Burst Time ▼ 5 sec.` | **−5초** |
| Modernia | New World: `Full Burst Duration ▲ 5 sec.` | +5초 |
| Soda: Twinkling Bunny | Beginner's Rewards: `Full Burst Duration▲ 2/3 sec.` | +2/+3초, 골든칩 게이팅 |

`burst_cycle.FULL_BURST_DURATION = 10.0`은 전역 상수다. 그래서 **이사벨을 낀 덱과 안 낀
덱의 타임라인이 완전히 동일**하고, 엔진에는 둘을 구별할 수단이 없다.

Fienn 확정(2026-08-05): **이사벨의 단축은 그녀가 버스트한 사이클에만 적용된다.**
B3가 둘인 덱에서 다른 B3가 사이클을 열면 그 사이클은 10초다. 즉 시너지는
「아르카나와 이사벨이 **같은 사이클에** 버스트하는 운영」에서만 나온다.

## 범위

이번에 넣는 것: **이사벨 · 모더니아**. 값이 고정 상수라 순환이 없다.

**소다는 제외** — 별건 티켓(커밋 `d89ebf3`, `docs/roadmap.md`). 두 가지 이유:

1. 그녀의 칩 소비가 별개의 버그다. 원문은 `Number of Golden Chip stacks ▼ 17 after the
   effect applied`(= 17만큼 감산)인데 인코딩은 **17로 세팅**한다. 이 차이가 그녀의
   크리댐(스택당 +1.32%, 최대 +66%)과 버스트 ATK 게이트(≥30)를 좌우한다.
2. 올바른 의미로 읽으면 그녀의 확장은 **순환**이다. 실측(180초, 덱
   `anis-star,arcana,crown,cinderella,soda-twinkling-bunny`):

   ```
   리셋 해석(현재): 50→17, 이후 매 버스트 26~27로 평평   → 항상 +5s (상수)
   감산 해석(원문): 50→43→35→28→20→13→9                → t=141 임계 20 이탈, t=166 임계 10 이탈
   ```

   확장을 모델링하면 FB가 길어져 FB 중 사격이 늘고 칩이 덜 줄어 이탈 시점이 밀린다 —
   **답이 자기 입력으로 되돌아온다.** 끊는 방법은 고정점 반복(`evaluate_deck` 2~3회 —
   탐색 벽시계 여유가 3.4초뿐이라 위험)과 스케줄러 안에서 칩 궤적 재구현(자원 머신
   이중 구현)뿐이고 둘 다 대가가 크다. **칩을 먼저 고쳐야 어느 쪽이 필요한지 데이터로
   답할 수 있다.**

---

## A. 엔진 프리미티브

### A.1 사이클별 풀 버스트 길이

값이 스킬 데이터 슬롯이 아니라 설명문에 박힌 리터럴이므로 registry의 상수 맵에 적는다
(그레이브의 "10 sec" 선례, `VARIANT_BURST_TIERS`와 같은 형태).

```python
# app/skill_rules/registry.py
#
# 자기 버스트가 풀 버스트 창 자체의 길이를 바꾸는 Burst 3. 값이 스킬 슬롯이 아니라
# 설명문에 박힌 리터럴이라 여기 적는다.
FULL_BURST_DURATION_DELTA: dict[str, float] = {
    "isabel": -5.0,     # Sonic Chaser: "Full Burst Time ▼ 5 sec."
    "modernia": 5.0,    # New World:    "Full Burst Duration ▲ 5 sec."
}


def get_full_burst_duration_delta(slug: str) -> float:
    return FULL_BURST_DURATION_DELTA.get(slug, 0.0)
```

배선은 `burst_delay` · `self_stun`과 같은 경로다 — 「유닛의 버스트 스케줄을 바꾸는
사실」이 이미 다니는 길이다.

```
registry.get_full_burst_duration_delta(slug)
    ↓
roster.assemble_simulation_inputs → member["full_burst_duration_delta"]   (0이면 안 싣는다)
    ↓
burst_cycle.simulate_burst_cycle
```

`burst_cycle`은 지금 `tier3_fire_time`만 붙잡는데, **그 사이클의 티어 3을 실제로 쏜
멤버**도 같이 붙잡아 창 길이를 잰다:

```python
full_burst_end = full_burst_start + max(
    0.0, FULL_BURST_DURATION + tier3_member.get("full_burst_duration_delta", 0.0))
```

`max(0.0, ...)`는 방어다. 현재 데이터로는 최소 5초라 걸리지 않지만, 길이가 음수인 창은
아래의 모든 `start <= t < end` 검사를 **조용히** 뒤집는다.

**아래로는 손댈 곳이 없다.** FB 보너스(`in_full_burst`) · `during_full_burst` per-shot
모드 · 자원 리셋 · `resource_gated_buffs`의 `at:"full_burst_end"`가 전부
`full_burst_windows`(구간 리스트)를 읽지 길이 상수를 읽지 않는다. 사이클 간격도
`time = full_burst_end`라 자동으로 따라온다.

### A.2 시간을 아는 조건

조건 팩토리는 `(context, caster_slug)`만 받아서 「상태가 아직 살아 있는가」를 답할 수
없다. `SkillRule`에 선택적 술어를 하나 더 둔다.

```python
# app/squad_engine.py
@dataclass
class SkillRule:
    trigger: str
    action: Callable[[SquadContext, str, float, EffectRegistry], None]
    condition: Callable[[SquadContext, str], bool] = field(default=_always_true)
    # 상태의 남은 시간처럼 트리거의 시각을 봐야만 답할 수 있는 게이트. 시각은 언제나
    # 호출자가 넘긴다 - 컨텍스트에 찍어두고 나중에 읽는 방식은 낡은 값을 에러 없이
    # 반환하고, 이 저장소는 그 실패를 이미 두 번 겪었다(docs/insights.md의
    # "per-shot/periodic 조건은 라이브가 아니라 최종 컨텍스트를 본다").
    time_condition: Callable[[SquadContext, str, float], bool] = field(default=_always_true_at)
```

호출 지점은 셋이고 **전부 이미 자기 시각을 들고 있다.** 셋 다 넘긴다:

| 위치 | 시각 |
|---|---|
| `squad_engine.py::fire_trigger` | `time` |
| `raid_simulator.py` periodic 패스 | `tick` |
| `raid_simulator.py` per-shot 패스 | `shot_time` |

`_helpers.member_subset_buff_rule`에도 `time_condition=`을 `condition=` 옆에 대칭으로
뚫는다(내부에서 `_rule`에 그대로 넘긴다).

아르카나가 쓸 조건 팩토리:

```python
def own_burst_status_active(seconds: float):
    """자기 버스트가 자신에게 건 상태가 아직 살아 있는가.

    부여 시점은 그 버스트를 쓴 시각이므로 별도 상태 기록이 필요 없다 -
    `SquadContext.burst_times[caster][-1] + seconds > now`. 한 번도 버스트하지
    않았으면 거짓.

    `own_burst_fired_this_cycle()`가 답할 수 없는 질문이다: 그쪽은 시계가 없어서
    부여 이후 `seconds`가 지났는지 구별하지 못한다. 풀 버스트 창 하나를 사이에 둔
    `full_burst_end` 게이트에서는 그 차이가 전부다.
    """
```

### A.3 실제 창 길이를 알아야 하는 버프

`on_full_burst_enter` 훅이 지금 시작 시각만 넘긴다. 종료 시각도 같이 넘기도록
`full_burst_end` 계산을 훅 호출 **위로** 올린다. `raid_simulator`가 그것을
`context.current_full_burst_end`에 세우고, 원문이 `continuously`(= 풀 버스트가 끝날
때까지)인 두 버프가 `end - time`으로 지속시간을 잡는다:

- `dorothy_serendipity.py` — Radiant Wings의 풀 버스트 중 자ATK +75.24%
- `arcana_fortune_mate.py` — Making Memories의 자크리율 +20.09% · 공댐 +29.99%

지금까지는 FB가 항상 10초라 `FULL_BURST_DURATION` 상수가 맞았고, **이 변경이 그 전제를
깬다.** 그래서 범위 안이다.

---

## B. 인코딩

### B.1 아르카나

세 룰의 `condition=own_burst_fired_this_cycle()`을
`time_condition=own_burst_status_active(wheel_duration)`으로 **교체**한다(추가가 아니다).

- `apply_cycle_death` (Death)
- Magician의 `member_subset_buff_rule`
- Strength의 `member_subset_buff_rule`

**둘을 AND로 묶지 않는 이유:** 원문은 「자신이 운명의 수레바퀴 상태라면」이지 「이번
사이클에 버스트했다면」이 아니다. AND로 묶으면 원문보다 **엄격**해진다 — FB 5초
사이클(간격 7.6초 = 5 + 게이지 2.4 + 티어갭 0.2)에서는 이전 사이클의 수레바퀴가 다음
사이클 FB 종료까지 살아남는 배치가 현재 게이지 상수에서 **2.7초 차이로** 비껴가 있다.
여유가 그것뿐인 전제를 조건에 심을 이유가 없다.

`wheel_duration`은 모듈이 이미 `shackles["description_value_02"]`에서 읽고 있다 —
**새 상수를 박지 않는다.**

`own_burst_fired_this_cycle()` 자체는 남는다. 그레이브(상태가 **끝날** 때 발동하므로
`full_burst_end`가 옳은 시각) · 아스카 · 마나 · 신데렐라:크리스탈웨이브 · 마르시아나가
계속 쓰고, 그쪽은 전부 옳은 용법이다.

### B.2 이사벨 · 모더니아

registry 맵 항목 + 독스트링을 「보류」에서 「모델됨」으로. `encoded-nikkes.md`의 두
행도 함께.

### B.3 파급

| 유닛 | 바뀌는 것 |
|---|---|
| 이사벨 | FB 5초 — 사이클이 짧아져 버스트 횟수↑, 대신 FB 보너스 구간↓ |
| 모더니아 | FB 15초 — 반대 방향 |
| 도로시: 세렌디피티 | Radiant Wings 자ATK가 실제 창 길이만큼 |
| 아르카나: 포츈 메이트 | Making Memories 크리율·공댐이 실제 창 길이만큼 |
| 아르카나 | 조건부 불릿 셋이 이사벨 동반 사이클에만 |

---

## C. 테스트

**상수를 못박는 단언은 총합이 아니라 산술로 실패해야 한다.** 전례: `gauge_charge_time`을
5.0이라는 명백히 틀린 값으로 바꿔도 그때 새로 쓴 2개 말고는 **1871개 중 아무것도 깨지지
않았다.** 총합을 보는 테스트는 상수 하나의 변화에 둔감하다.

### `test_burst_cycle.py`

- 티어 3을 쏜 멤버의 델타가 창 길이를 정한다 — 창 == 5.0 / 15.0을 직접 단언
- B3가 둘일 때 **사이클마다** 그 사이클을 연 쪽을 따른다
- 사이클 간격이 그만큼 바뀐다
- 기본값보다 더 음수인 델타는 음수 창이 아니라 0 길이가 된다
- `on_full_burst_enter` 훅이 종료 시각을 함께 받는다 (기존 훅 테스트 갱신)

### `test_squad_engine.py`

- `time_condition` 기본값은 통과하고, 거짓이면 액션이 돌지 않는다
- `own_burst_status_active`: 만료 전 참 · 만료 후 거짓 · **한 번도 안 터졌으면 거짓**
- **호출 지점 셋 전부가 존중한다.** periodic·per-shot을 빼먹으면 조용히 썩는 자리라
  이것이 핵심 테스트다

### `test_skill_rules_arcana.py`

낡은 전제를 못박은 테스트 둘
(`test_cycle_of_destiny_death_bullet_requires_arcana_burst_this_cycle`,
`test_magician_and_strength_require_bursted_target_and_wheel_of_fortune`)을 고친다.
새 단언: 버스트 후 10.1초에 FB 종료 → 발동 안 함 / 5.1초 → 발동 / 미버스트 → 발동 안 함.

### 신규 `test_interaction_arcana_isabel.py`

이 수정의 요점을 실제로 못박는 유일한 테스트: 아르카나와 이사벨이 같은 사이클에 터지는
덱에서는 세 불릿이 꽂히고, FB를 안 줄이는 B3로 바꾸면 안 꽂힌다.

### 뮤테이션 확인

「테스트가 잡는다고 적은 것은 실제로 깨보고 확인할 것」. 두 가지를 되돌려 각각 테스트가
정말 깨지는지 본다:

1. `FULL_BURST_DURATION_DELTA["isabel"]`를 0.0으로
2. 아르카나의 게이트를 `own_burst_fired_this_cycle()`로

---

## D. 검증 기준

1. 전체 스위트 초록 — 기준선 **백엔드 1874 passed / 3 skipped**(2026-08-05 실행 확인)
2. **캘리브레이션 불변.** 기록 덱 5개(`RECORD_ROTATIONS`)에 이사벨·모더니아·아르카나·
   소다가 하나도 없으므로 `measure_record_calibration.py`가 **combined 1.078x over 25
   units · within ±15%: 17/25** 그대로 나와야 한다(2026-08-05 실행 확인). 움직였다면
   어딘가로 샌 것이다. 이 변경의 가장 날카로운 안전망이다 — 이 설계는 덱 **추천**만
   바꾸고 기록 대조는 건드리지 않아야 한다.
3. 검토 때 쓴 두 덱 — 네온 덱은 세 불릿을 통째로 잃고, 이사벨 덱은 둘이 같은 사이클에
   터지는 좌석 순서에서만 얻는다. 탐색이 이사벨을 신데렐라 왼쪽으로 옮기는지 확인
   (현재 최적 좌석 순서는 아르카나를 신데렐라와, 이사벨을 크라운과 짝지어 둘이 **한
   번도 같은 사이클에 안 터진다**)
4. **제보된 증상** — 고정 로스터로 배분을 전후 비교해, 이사벨 없는 아르카나가 상위에서
   내려오는지

---

## E. 이 설계가 가르지 못하는 것

- **소다의 FB 확장** — 별건 티켓. 그녀의 칩 소비 의미가 먼저 정해져야 한다.
- **FB 단축이 실제로 이득인지** — 엔진은 이제 답을 내놓지만, 「FB 보너스 구간을 잃는
  대신 사이클을 더 돈다」는 교환을 **실기록으로 대조한 적이 없다.** 이사벨이 들어간
  기록이 없다. 게이트는 옳아지지만 이사벨 덱의 절대 수치는 여전히 미검증이다.
- **Magician의 스킬 2 쿨감 −75%** — 아군 스킬 쿨다운이 시뮬되지 않는다. 계속 보류.
- **경계 판정** — 게임이 FB 마지막 틱에서 조건을 보는지 한 프레임 뒤에 보는지. 5초 창
  에서는 여유가 4.9초라 답이 바뀌지 않지만, 9.9초짜리 단축 유닛이 나오면 이 모델이
  갈라진다.
- **아르카나의 대상 조건** — 「previously cast their Burst Skill」을 「이번 사이클에」로
  읽은 것은 기존 결정(`docs/decisions.md`, gap #3)이고 이 설계는 건드리지 않는다.
