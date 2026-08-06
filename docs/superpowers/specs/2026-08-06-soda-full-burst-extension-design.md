# 소다: 트윙클링 바니의 풀 버스트 확장 — 설계

- 날짜: 2026-08-06
- 대상: `Beginner's Rewards`(skills[1]) **전체** — 풀 버스트 지속 확장(+2/+3초)과, 그
  확장 상태에 게이팅된 per-shot 넉(52.04% / 85.02%). 이 스킬은 지금 통째로 보류다
- 선행: `docs/measurements/soda-golden-chip-in-play.md`(Fienn 실측),
  `docs/superpowers/specs/2026-08-05-per-cycle-full-burst-length-design.md`(사이클별 FB 길이),
  `docs/roadmap.md`의 소다 항목

## 왜 지금인가

이 효과는 소다를 인코딩한 2026-07-12부터 보류였고, 사유가 두 번 바뀌었다.

1. **처음(2026-07-12):** 「캐스터별 풀 버스트 길이라는 개념이 엔진에 없다」 — 2026-08-05에
   `FULL_BURST_DURATION_DELTA`가 생기며 사실이 아니게 됐다.
2. **2026-08-06 오전:** 칩 소비를 감산으로 고친 뒤 재판단해 「순환이라 상수로 접을 수
   없다」로 남겼다. 근거는 시뮬 궤적이었는데, **그 궤적은 소다가 매 사이클 버스트하는
   운영의 것**이었다.

Fienn의 실측이 그 근거를 무너뜨렸다. 실전(B3가 셋인 덱, 소다는 격 사이클로 버스트)에서
풀 버스트는 **15초**이고 칩은 33~50에서 **순환**한다. 같은 로테이션에 +5초를 주입하면
시뮬이 그 궤적을 스택 단위로 재현하고(50→33→42→50→33), 엔진 그대로는 재현하지 못한다
(50→33→39→45→28→…로 고갈).

**대가**: 이 덱 총딜 4.429B → **4.841B (+9.3%)**. 소다 혼자가 아니라 덱 전원이 풀 버스트
창을 50% 더 갖기 때문이다. 그리고 이 +9.3%는 **확장만** 넣은 값이다 — 같은 스킬의 두
번째 불릿이 여기 얹힌다.

> **Superseded (2026-08-06 착륙 후 실측):** 넉까지 얹은 실제 값은
> 4.4288B → **5.0810B (+14.7%)**이다. 위 +9.3%는 착륙 전의 예측으로 남긴다 —
> 이 문서는 우리가 무엇을 예상했는지의 기록이다.
> 측정값은 `docs/measurements/soda-golden-chip-in-play.md`「해석 3」.

### 두 번째 불릿도 같은 스코프다

```
■ 풀 버스트 중 평타 시 발동. 십자선에 가장 가까운 적 1체.
  Stage 1: Time Extension I 상태  → 최종 ATK의 52.04%   (dv10)
  Stage 2: Time Extension II 상태 → 최종 ATK의 85.02%   (dv12)
```

소다의 평타 1발이 33% ATK인데 이 넉은 **85%** — 평타의 2.6배가 FB 중 매 발마다 추가로
꽂힌다. 그리고 게이트가 정확히 「Time Extension 상태」라 **확장을 모델링해야 비로소
도달 가능해진다**. 지금 docstring이 「확장이 없으니 이 넉도 unreachable」이라 적어둔
그 항목이고, 확장만 넣고 넉을 빼면 「확장은 모델됐는데 그것에 걸린 넉은 미모델」이라는
어중간한 상태로 남는다.

## 순환이 아니라 순차 의존이다

「순환」이라는 진단 자체가 반쯤 틀렸다. 원문은 `Activates when entering Burst Stage 3`
이므로 **사이클 k의 확장은 사이클 k에 진입하는 순간의 칩**으로 정해지고, 그 칩은
사이클 1..k−1의 샷이 만든 것이다. 사이클 k 자신의 샷은 아직 존재하지 않는다. 시간
순서로는 인과가 한 방향이다.

순환처럼 보이는 것은 **구현 구조** 때문이다. `simulate_raid`는 `simulate_burst_cycle`을
통째로 먼저 돌려 모든 FB 창을 확정한 뒤에 샷을 생성한다(샷 생성이 재장전·장탄 버프를
읽어야 해서 그 순서가 강제된다 — `docs/decisions.md` 2026-07-12 「자원 채움을 버스트
사이클 앞으로 옮기는 안」기각 참고). 그래서 사이클 단위 인터리브가 아니라 **패스 단위
반복**으로 같은 답에 도달한다.

## 확정된 결정

| 질문 | 결정 | 근거 |
|---|---|---|
| 칩 조건을 따라가나, 상수로 접나 | **사이클별로 따라간다** | 두 운영이 모두 실재한다 — 격번(칩 순환)과 매 사이클(칩 고갈). 상수는 후자를 과대평가한다 |
| 순환을 어디서 끊나 | **수렴까지 반복**(상한 4패스) | 사이클 단위 인터리브는 엔진 핵심 경로 재구조화라 모든 덱의 숫자가 움직일 위험이 있다 |
| Beginner's Rewards가 칩을 읽는 시점 | **소다 버스트의 17 소비 전** | 같은 순간의 ATK 게이트(≥30)가 이미 `use_pre_reset`으로 소비 전을 읽는다 — 두 스킬이 같은 값을 봐야 일관된다 |
| 조건을 어디에 두나 | **오버라이드 테이블**(A안) | `burst_cycle`은 순수 스케줄러로 남는다. 자원 머신 이중 구현을 피한다 |

## 아키텍처

```
simulate_raid(deck, **kwargs)                  ← 얇은 래퍼 (새 역할)
  overrides = None
  for _ in range(MAX_FULL_BURST_PASSES):       # 4
      result, resolved = _simulate_raid_once(deck, **kwargs, fb_overrides=overrides)
      if resolved == overrides:
          break                                 # 고정점
      overrides = resolved
  return result

_simulate_raid_once(...)                        ← 지금의 simulate_raid 본문, rename
  simulate_burst_cycle(deck, ..., full_burst_duration_overrides=fb_overrides)
      사이클 k 길이 = max(MIN_FULL_BURST_DURATION,
                          FULL_BURST_DURATION
                          + tier3_member["full_burst_duration_delta"]   # 기존: 이사벨·모더니아
                          + fb_overrides.get(k, 0.0))                    # 신규: 소다
  … 샷 생성 → 자원 fill/reset resolution (전부 기존 그대로) …
  resolved = _resolve_conditional_fb_deltas(context, events, conditional_full_burst_deltas)
  return result, resolved
```

`_simulate_raid_once`가 `(result, resolved)` 튜플을 반환하는 것은 **context를 밖으로
노출하지 않기 위해서**다. 래퍼는 칩이 뭔지 알 필요 없이 딕셔너리 두 개만 비교한다.
그리고 래퍼는 인자 30개를 다시 나열하지 않는다 — 실제로 읽어야 하는 `deck`만 명시하고
나머지는 `**kwargs`로 위임한다.

### 엔진은 레지스트리를 모른다

`raid_simulator.py`는 `skill_rules.registry`를 임포트하지 않고 `burst_cycle.py`는
아무것도 임포트하지 않는다. 그래서 조건부 델타 스펙은 레지스트리에서 직접 읽지 않고
**`resource_specs`·`resource_gated_buffs`와 똑같이 인자로 전달**한다:

```
simulate_raid(..., conditional_full_burst_deltas={
    "soda-twinkling-bunny": {"resource": "chip", "cap": 50, "tiers": [(10, 2.0), (20, 5.0)]},
})
```

조립은 `roster.assemble_simulation_inputs`가 한다 — 다른 스펙 딕셔너리를 만드는 자리와
같다. **member dict에는 아무것도 추가하지 않는다**(기존 `full_burst_duration_delta`는
`burst_cycle`이 읽어야 해서 member에 있지만, 조건부 쪽은 `burst_cycle`이 아니라
resolution 뒤의 해석기가 읽는다).

### `_resolve_conditional_fb_deltas`

```
for cycle_index, tier3_time in enumerate(각 사이클의 tier-3 발동 시각):
    total = 0.0
    for slug, spec in conditional_full_burst_deltas.items():
        count = context.resource_count(slug, spec["resource"],
                                       tier3_time - EPSILON, spec["cap"])
        total += 그 count가 통과하는 가장 높은 tier의 값   # 없으면 0
    if total: resolved[cycle_index] = total
```

`EPSILON`은 `1e-6`을 쓴다(`resource_count`가 `fill_time > time`을 배제하는 부동소수
비교라, 이 폭이면 같은 순간의 리셋만 벗어나고 직전 fill은 그대로 센다).
이것이 **소비 전 판정**이다: 소다의 버스트 리셋은 정확히 `tier3_time`에 기록되므로
그 직전 값이 진입 시점의 칩이다. 소다가 그 사이클의 B3가 아니면 애초에 소비가 없어
같은 식이 그대로 맞다.

사이클별 tier-3 발동 시각은 `events`의 `{"type": "burst", "tier": 3}` 항목을 시간순으로
읽는다 — `full_burst_start`가 아니라 **버스트 발동 시각**이어야 한다(둘은
`FULL_BURST_OPEN_DELAY`만큼 떨어져 있고, 원문의 판정 시점은 전자다).

### per-shot 넉이 단계를 아는 법

넉 자체는 새 엔진 수단이 필요 없다 — `per_shot_rules`의 `every_during_full_burst`
모드(threshold 1 = 창 안 모든 샷)에서 action이 `instant_damage_percent` 펄스를 넣으면
엔진이 `per_shot_nuke`로 기록한다(Velvet의 `instant_nuke_pulse_rule`과 같은 경로).
다만 소다는 **퍼센트가 그 사이클의 단계에 달려 있어** 그 헬퍼를 그대로 못 쓰고 단계를
읽는 커스텀 action이 필요하다.

`SquadContext`에 창별 단계를 싣는다:

```
context.full_burst_extension_stages: list[(start, end, stage)]   # stage 0/1/2
context.full_burst_extension_stage(time) -> int
```

`_simulate_raid_once`가 FB 창을 만들 때 **자기가 받은 오버라이드에서** 채우므로, 같은
패스 안에서 창 길이와 넉 단계가 항상 일치한다. 패스 1은 오버라이드가 없어 단계가 0이고
넉도 0이다 — 확장과 같은 이유로 하한에서 출발한다.

델타(초)가 아니라 **단계 인덱스**를 싣는 것은 5.0초에서 「II단계」를 역추론하지 않기
위해서다. 값이 우연히 겹치면 조용히 틀린다.

## 컴포넌트

| 파일 | 변경 |
|---|---|
| `skill_rules/registry.py` | `_CONDITIONAL_FULL_BURST_DELTA_BUILDERS` 신설 + `get_conditional_full_burst_delta(slug, skill_values)`(다른 빌더 딕셔너리와 같은 모양) · 소다의 `_PER_SHOT_RULE_BUILDERS` 항목이 이미 있으므로 거기에 넉 rule을 합친다 |
| `roster.py` | `assemble_simulation_inputs`가 `conditional_full_burst_deltas` 딕셔너리를 조립해 `simulate_raid`에 넘긴다 — 다른 스펙 딕셔너리를 만드는 자리와 같다 |
| `burst_cycle.py` | `simulate_burst_cycle`에 `full_burst_duration_overrides=None`. 사이클 인덱스로 조회해 길이에 더하기만 한다 |
| `squad_engine.py` | `SquadContext`에 `full_burst_extension_stages` + `full_burst_extension_stage(time)` |
| `raid_simulator.py` | 본문 → `_simulate_raid_once`(rename, `(result, resolved)` 반환) · 새 `simulate_raid` 수렴 루프 · `_resolve_conditional_fb_deltas` 신설 · 새 인자 `conditional_full_burst_deltas` · 창 생성 시 단계를 context에 싣기 |
| `skill_rules/soda_twinkling_bunny.py` | `build_beginners_rewards_full_burst_delta(values)`(임계·초를 슬롯에서) · `build_beginners_rewards_per_shot_rules(values)`(단계 조건부 넉) · docstring에서 deferred → modeled 이동 |

### 값은 슬롯에서 읽는다

임계(10/20)와 초(2/3), 넉 퍼센트(52.04/85.02)를 상수로 박지 않는다 — 다른 인코딩과 같은
규칙이고 스킬 레벨이 바뀌어도 따라간다. 덤프해 둔 자연 번호는 `dv03`=10, `dv04`=2,
`dv06`=20, `dv07`=3, `dv10`=52.04, `dv12`=85.02이다(`dv01`=3은 "Burst Stage **3**",
`dv02`/`dv05`는 "Stage 1/2"의 번호 — insights.md의 「슬롯 손번호는 트리거 문구 속
숫자까지 센다」 그대로다). `SKILL_VALUE_MANIFESTS`에 `beginners_rewards` 키를 추가해야
하므로 `test_skill_value_assembly.py` 하네스를 통과시키는 일이 딸려 온다(필요하면
`drop_tokens`, **픽스처나 하네스는 고치지 않는다**).

`tiers`를 `[(10, 2.0), (20, 5.0)]`로 두는 것은 원문이
`Each subsequent effect triggers all effects before it`이라 20+ 이면 2+3이 함께 걸리기
때문이다 — 슬롯에서 읽은 2와 3을 **빌더가 누적해** 값에 미리 반영하고, 소비 지점에서
다시 더하지 않는다.

## 넉도 누적이다 (Fienn 확정, 2026-08-06)

`Each subsequent effect triggers all effects before it`이 이 스킬의 두 불릿 모두에
붙어 있다. 확장 쪽은 누적이 **실측으로 확인**됐고(Fienn의 15초 = 10 + 2 + 3), 넉 쪽도
**같게 읽는 것이 맞다고 Fienn이 확인했다** — Ext II 상태의 한 발은
**52.04 + 85.02 = 137.06%**이고 Ext I 상태는 52.04%다.

빌더가 슬롯에서 읽은 두 값을 누적해 `[(1, 0.5204), (2, 1.3706)]` 형태로 만들고, 소비
지점(per-shot action)에서 다시 더하지 않는다 — 확장의 `tiers`와 같은 규칙이다.

## 불변식 — 소다가 없는 덱은 결과도 비용도 바뀌지 않는다

이 설계에서 가장 중요한 성질이다. 조건부 델타를 가진 유닛이 덱에 없으면
`_resolve_conditional_fb_deltas`가 빈 딕셔너리를 돌려주고, 첫 패스에서
`resolved == overrides`(둘 다 비어 있음)가 성립해 **정확히 1패스**로 끝난다.
`simulate_burst_cycle`은 빈 테이블에서 0을 더한다.

깨지면 전 덱의 숫자가 움직인다. 그래서 테스트로 못박고, 골든 테스트와 캘리브레이션이
이 불변식의 두 번째 방어선이 된다.

## 엣지 케이스

| 상황 | 처리 |
|---|---|
| **수렴 실패** | 상한 4패스에서 멈추고 마지막 결과를 쓴다. 결정적이라 탐색 재현성(2026-08-05)은 유지된다. `result["full_burst_passes"]`에 패스 수와 수렴 여부를 남겨 **조용히 넘어가지 않게** 한다 — 단, 이 키를 넣기 전에 `result` 딕셔너리를 통째로 비교하는 테스트가 있는지 먼저 확인한다(없어 보이지만 확인하고 넣는다) |
| **소다가 있으면 최소 2패스** | 패스 1은 확장 없이(FB 10초) 돌아 칩 궤적을 얻고 패스 2가 그것을 적용한다. 첫 사이클은 전투 시작 칩이 50이라 실제로는 항상 +5초인데 패스 1에서는 10초다 — 정상이고, 그래서 **하한에서 시작해 위로** 간다 |
| **사이클 수가 패스마다 다름** | FB가 길어지면 사이클이 줄 수 있어 테이블 키 개수가 달라진다. 딕셔너리 동등 비교라 그대로 처리된다 |
| **이사벨과 겹침** | 합산 후 `MIN_FULL_BURST_DURATION`(0.0)으로 클램프. −5 + 5 = 0 → 10초. 둘은 다른 조건(자기 버스트 vs 덱 보유)이라 겹쳐 걸리는 것이 원문대로다 |
| **칩 자원 없이 조건부 델타만** | 실제로 생기지 않는 조합이지만 자원이 없으면 델타 0으로 방어한다 |

### 수렴은 보장이 아니라 기대다

「FB가 길수록 칩이 많다 → 델타가 크거나 같다」는 대체로 성립하지만 엄밀하지 않다.
FB가 길어지면 사이클 간격도 늘어 같은 전투 길이에 들어가는 **버스트 횟수가 줄 수
있고**, 그러면 소비 총량도 바뀌어 특정 사이클의 진입 칩이 내려갈 수 있다. 단조성을
증명하지 않고 상한을 안전장치로 둔다. 실제 수렴 패스 수는 측정해서 기록한다.

## 테스트

- **단위** — tier 표 생성(칩 9→0, 10→+2, 20→+5, 50→+5) · `simulate_burst_cycle`이
  사이클별 오버라이드를 더한다 · 기존 `full_burst_duration_delta`와 합산된다 ·
  `full_burst_extension_stage(time)`이 창 안/밖과 창별 단계를 맞게 답한다
- **판정 시점(뮤테이션)** — 진입 칩 28인 사이클에서 `t−ε`을 `t`로 바꾸면 +5초가 +2초로
  바뀌는 테스트. 소비 전/후를 실제로 가르는지 **깨봐서** 확인한다
- **불변식** — 소다 없는 덱이 정확히 1패스로 끝나고 결과가 동일하다
- **넉** — 단계 0인 창에서는 넉이 하나도 안 나오고, 단계 1/2인 창에서는 창 안 샷 수만큼
  나오며 퍼센트가 단계를 따른다 · 창 밖 샷은 넉을 안 만든다
- **통합 둘** — 두 운영이 모두 나와야 한다:
  - 격번 로테이션 → FB 15초, 칩이 33~50에서 순환 (Fienn 실측 재현)
  - 매 사이클 버스트 → 단계가 실제로 떨어진다
- **회귀** — 이사벨·모더니아의 사이클별 FB 길이가 그대로다

## 검증과 파급

- 기준선 **1913 passed / 3 skipped**에서 시작해 신규 테스트만큼 늘어난다
- **캘리브레이션 1.078x·17/25 불변이어야 한다** — 기록 덱 5개에 소다가 없다. 움직이면
  불변식이 깨진 것이다
- **골든 테스트도 초록이어야 한다.** 깨지면 버그 신호이지 재기준화 대상이 아니다
- `scripts/bench_evaluate_deck.py`로 소다 덱 시뮬 비용(현재 44.4ms), 그리고 실제 탐색
  대기시간을 잰다
- `scripts/measure_golden_chip.py`로 두 덱의 궤적을 다시 찍어 실측과 대조한다
- 덱 추천 순위 변화를 확인한다 — 소다는 지금 그 덱에서 18.8%를 내고, 확장이 붙으면
  올라갈 가능성이 크다

## 이 설계가 다루지 않는 것

- **창당 fill이 실측 8인데 시뮬 9~10인 15% 차이.** 확장을 넣으면 창이 길어져 절대
  오차는 커지지만 궤적의 결론은 바뀌지 않는다. 소다는 9발 장탄에 클립 3분할 재장전이라
  재장전 모델에 민감하다 — 별건으로 남긴다.
- **칩이 20 아래로 내려간 구간의 실측.** Fienn은 격번으로만 플레이해 그 구간에 들어간
  적이 없다. 시뮬은 FB가 12초(=10+2)로 줄어든다고 말하지만 대조가 없다.
- **다른 유닛으로의 일반화.** 수집 데이터 전체에서 풀 버스트 길이를 바꾸는 유닛은
  셋뿐이고(이사벨·모더니아·소다) 조건부는 소다 하나다. 메커니즘은 일반적인 모양으로
  두되 소비자를 늘리려 하지 않는다.
- **넉의 타격 대상.** 원문은 「십자선에 가장 가까운 적 1체」인데 이 시뮬레이터는 단일
  보스를 때린다 — 다른 모든 넉과 같은 취급이고 이 스킬만의 문제가 아니다.
- **넉이 풀 버스트 보너스를 받는지.** `per_shot_nuke`는 샷 시각에 계산되므로 창 안에
  있고, 엔진의 기존 판정을 그대로 따른다. 이 설계가 새로 정하는 것이 아니다.
