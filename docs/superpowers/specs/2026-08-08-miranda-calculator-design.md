# 미란다 계산기 — 누가 파워업!과 웨이크업!을 받는가

날짜: 2026-08-08

미란다의 두 대상형 버프는 **최종 공격력 순위**로 대상을 정한다. 순위는 그 순간
살아 있는 ATK 버프까지 반영한 값이라, 로스터의 공격력만 보고는 답을 알 수 없다.
계산기 탭에 덱 5인을 편성하면 누가 무엇을 받는지 초상화 옆 뱃지로 답하고,
못 받는 니케에게는 **받으려면 오버로드 공격력이 얼마나 필요한지**까지 답한다.

## 1. 검증 — 시전/효과 타이밍은 정확하다

작업 전제로 요구된 검증이다. 결론: **현행 인코딩은 맞다. 엔진 수정 없음.**

### 1.1 원문 대 인코딩

`data/dotgg/char_miranda.json`의 원문(스킬 10레벨):

| | 기본 `miranda` | 애장품 `miranda-signature` |
|---|---|---|
| 파워업!(버스트, 쿨 20초) | 최종공격력 상위 **1명** · ATK +40.4%, 크댐 +56.23%, 각 10초 | 상위 **2명**, 값 동일 |
| 웨이크업! 1번불릿 | 전체 아군 크댐 +32.99%, 10초 | 동일 |
| 웨이크업! 2번불릿 | **없음** | 자신 크확 +30.1% / 공격데미지 +23.7%, 각 10초 |
| 웨이크업! 3번불릿 | **없음** | 최종공격력 상위 **1명** · 크확 +85.42%, **1발(round)** |

두 대상형 불릿 모두 원문이 `(except caster; including the caster if there are
not enough allies)`이고, `miranda.py`는 `highest_atk_buff_rule` /
`_resolve_scope`의 기본값(`include_caster=False`)으로 그 뜻을 그대로 쓴다
(`squad_engine.py:202` docstring). 덱은 항상 5인이므로 후보가 4명이라 **미란다
본인은 실제 덱에서 절대 자기 버프를 받지 않는다.**

웨이크업!은 기본 배열에서 1번불릿에서 끝난다(슬롯 03~09가 아예 없음). 즉
**애장품이 없으면 금색 뱃지는 존재할 수 없고 은색도 1명뿐이다.**

### 1.2 런타임 타이밍

5인 덱(미란다 B1 · b2 · 캐리 3인 B3, 60초)으로 `top_atk_slugs`를 감싸 측정한
결과:

| 사이클 | 파워업! 판정 | 웨이크업!3 판정 | 판정 시점 랭킹 |
|---|---|---|---|
| 1 | t=5.000000 | t=5.000001 | 90000/80000/70000 → **126360/112320**/70000 |
| 2 | t=25.000000 | t=25.000001 | 동일 |
| 3 | t=45.000000 | t=45.000001 | 동일 |

- 파워업!은 `own_burst_activate` = **B1 시전 순간**에 판정한다. 그 시점 랭킹에는
  같은 순간 뒤이어 터지는 B2/B3의 버스트 효과가 아직 없다 — `burst_cycle.py`의
  티어 루프가 `on_tier_fire`를 1→2→3 순서로 부르므로, auto 모드에서 세 티어의
  시각이 같아도 **순서는 보존된다**(`burst_cycle.py:191-212`).
- 웨이크업!3은 `full_burst_enter` = **풀버스트 진입 순간**에 판정한다. 이 시각은
  `tier3_fire_time + FULL_BURST_OPEN_DELAY`(1e-6)이고, 그래서 랭킹이 같은
  사이클 파워업!의 ATK +40.4%를 **반영한다**(90000 → 126360 = ×1.404).
  이 1e-6 간격이 창을 연 시전과 창 안의 효과를 갈라놓는 장치다
  (`burst_cycle.py:61-69`).
- 매 사이클 재판정된다. 시전자는 후보에서 빠진다.

### 1.3 「최종 공격력」이 세는 항

Fienn이 물은 것: 이 용어는 발동 시점 스킬 버프와 오버로드 공격력을 포함하는
개념인데 맞게 적용되는가. **맞다.** 랭킹이 세는 값은 판정 순간 기준

```
final(u) = base_atk(u) × (1 + Σ atk_percent(u)) + Σ flat_atk(u)
```

표시 공격력이 다섯 다 100,000이고 `ada-wong`만 오버로드 「공격력 증가 +12%」를
가진 실제 로스터 덱으로 확인:

| | 파워업! 판정(t=2.4) | 웨이크업!3 판정(t=2.6) |
|---|---|---|
| ada-wong | **112,000** (오버로드 +12%) | **192,400** (오버로드 + 파워업 +40.4% + 자버프 +40%) |
| crown | 100,000 | 140,400 (파워업 +40.4%) |
| cinderella | 100,000 | 113,550 (**평탄 공격력 +13,550**) |
| miranda-signature / isabel | 100,000 | 100,000 |

| 항 | 경로 | 확인 |
|---|---|---|
| 표시 공격력(레벨400·돌파·장비·큐브·소장품) | `base_atk` = `state.atk` | ✅ |
| 오버로드 「공격력 증가」 | 영구 `atk_percent` 자기 효과 | ✅ 나머지 넷이 동점이라 오직 이 힘으로 1순위 |
| 발동 시점 살아 있는 스킬 ATK% 버프 | `atk_percent` | ✅ |
| 평탄 공격력 버프 | `flat_atk` | ✅ |

오버로드가 표시 공격력에 이미 접혀 있지 않고 엔진이 따로 얹는다는 것은
`overload_effects.py` 도입부에 Fienn 확인으로 적혀 있다.

**맞게 빠지는 항**도 확인했다. ATK 관련 이름을 전수(`atk_percent` /
`flat_atk` / `caster_atk` / `extra_flat_atk*` / `electric_power_atk`)로 훑은 결과:

- 「공격 데미지 증가」(`attack_damage_up`)는 공격력이 아니라 데미지 배율이라 최종
  공격력에 안 들어가는 것이 맞다. 우월코드·크확·크댐도 같다.
- `extra_flat_atk_percent_of_max_hp`는 메이든: 아이스 로즈의 다이아몬드 더스트
  **자기 공식 안의 항**이라 레지스트리를 우회한다(`maiden_ice_rose.py:43`).
  게임에서도 그녀의 공격력 스탯을 올리는 값이 아니다. 그녀의 진짜 아군 평탄 ATK
  버프는 별도로 `flat_atk`로 들어간다.
- `electric_power_atk`는 라플라스의 `refresh_group` 이름이지 스탯이 아니다.

**랭킹이 놓치는 ATK 항은 없다.**

### 1.4 검증이 밝힌 사실 둘

**파워업!은 자기 힘만으로 웨이크업!3의 대상을 바꾸지 못한다.** 상위 N명을 같은
비율로 올리므로 그들 사이의 순서도, 3위와의 격차 방향도 뒤집히지 않는다.

대상이 사이클마다 갈리는 진짜 원인은 셋이다 — ① 같은 순간 뒤이어 터지는 B2/B3
버스트의 대상형 ATK 버프, ② 덱 순서상 미란다보다 앞선 아군의 `full_burst_enter`
ATK 버프(`fire_trigger`가 `rules_by_slug` 순서로 돈다), ③ 지난 창에서 넘어와
아직 살아 있는 버프.

**두 불릿은 성격이 다르다.** 파워업! 판정 시점(B1 시전)에는 오버로드와 영구
자버프 말고 켜진 것이 거의 없어 대상이 사이클마다 잘 안 바뀐다. 웨이크업!3은 그
사이클 버스트가 다 들어간 뒤라 변동이 크다 — 위 덱에서 ada-wong의 `atk_percent`가
1사이클 +0.924에서 2사이클 +0.524로 움직였다.

**동점은 좌석 순서로 갈린다**(안정 정렬). 위 실측에서 넷이 완전 동점이라 crown이
덱 순서만으로 2번 슬롯을 먹었다. 실제 로스터에서 정확한 동점은 드물지만 간발의
차는 흔하고, 그때 답이 얼마나 아슬아슬한지는 §5의 임계값이 답한다.

## 2. 왜 시뮬레이션을 돌리는가

랭킹을 계산기가 자체 구현하는 안은 기각한다. 같은 실수가 이 저장소에서 이미 세
번 났다(`docs/insights.md` — 「측정 스크립트는 모듈에 물어봐야 한다」). 로스터
공격력만으로 정적 정렬하는 안도 기각한다: 스쿼드 전체 ATK% 버프는 순위를 안
바꾸지만 대상형·자버프는 바꾸므로, **계산기가 필요한 바로 그 덱에서만 틀린다.**

엔진이 이미 정확히 이 랭킹을 하고 있으므로, 그 결과를 기록해 읽는다.

## 3. 엔진 계측 — opt-in

`SquadContext`에 `target_grants: list | None`(기본 `None` = 기록 안 함)을 둔다.
`top_atk_slugs`에 `grant_stats: tuple[str, ...] | None = None`을 추가하고, 값이
있고 로그가 붙어 있을 때만 한 건을 남긴다:

```python
{"caster": caster_slug, "time": time, "stats": [...], "targets": [...]}
```

기록은 `top_atk_slugs`가 하지만 **무슨 불릿인지는 호출자가 선언한다.** 대상
집합만으로는 미란다의 두 불릿을 구분할 수 없고(둘 다 같은 랭킹을 쓴다), `n`으로
나누는 것은 값이 바뀌면 조용히 깨진다. 그래서 두 룰 빌더가 자기 `buffs`의 스탯
이름을 무조건 `grant_stats`로 넘긴다:

- `_helpers.highest_atk_buff_rule` (`_helpers.py:136`) → 파워업!
- `_helpers._resolve_scope`의 `("top_atk", n)` 분기, `round_buff_rule`이 호출
  (`_helpers.py:126`) → 웨이크업!3

**두 헬퍼는 미란다 전용이 아니라 공유 헬퍼다** — `highest_atk_buff_rule`은
맥스웰(스트레이트샷)·레오나(펠릿)·나가(우정의 지원)의 top-N 불릿도 만든다.
`grant_stats`가 무조건 넘어가므로 top-N 대상형 버프는 전부 자기 스탯을 선언해
기록되고, 로그를 읽는 쪽이 시전자(caster)로 걸러 자기가 찾는 것만 골라낸다
(§4.1의 `miranda_target_report`가 `caster in MIRANDA_SLUGS`로 그렇게 한다).

`_simulate_raid_once`는 `collect_target_grants: bool = False`를 받아 컨텍스트에
빈 리스트를 달고, 결과 dict에 `"target_grants"`를 싣는다(`raid_simulator.py:739`,
`:1841`). `simulate_raid` 래퍼는 마지막 패스의 `result`를 그대로 돌려주므로
(`raid_simulator.py:601-616`) 풀버스트 확장 고정점 반복이 있는 덱에서도 **수렴한
패스의 기록**이 나온다. `deck_search.evaluate_deck`(`deck_search.py:440`)이
플래그를 그대로 통과시킨다.

**기본이 off이므로 탐색 핫패스의 할당은 1비트도 늘지 않는다.**

랭킹 숫자는 기록하지 않는다. 화면에 안 쓰기로 했고(Fienn, 2026-08-08), 필요해지면
`top_atk_slugs`가 이미 계산 중인 값이라 한 줄이다.

## 4. `backend/app/miranda_targets.py`

```python
MIRANDA_SLUGS = ("miranda", "miranda-signature")

def miranda_target_report(deck_specs, boss, alternatives=None) -> dict
```

두 단계다.

1. `deck_evaluation.evaluate_decks([deck_specs], [boss], alternatives)`로 **좌석
   순서를 정한다.** 유니온 탭이 쓰는 것과 같은 함수라, 계산기가 보여주는 배치가
   유니온 탭이 채점하는 배치와 어긋날 수 없다. 선택 로직을 복제하지 않는 것이
   요점이다(`deck_evaluation.py` 모듈 docstring의 설계 제약과 같은 이유).
2. 그 순서(`summary["deck"]`)로 `evaluate_deck(ordered, boss,
   collect_target_grants=True)`를 **한 번 더** 돌려 기록을 얻는다.

같은 덱을 한 번 더 도는 비용은 `best_ordering_summary`가 이미 좌석 순열마다 도는
것에 비하면 미미하고, 그 대가로 일반 경로에 플래그가 새지 않는다.

### 4.1 어느 불릿인지 가려내기

기록 중에서 `caster`가 `MIRANDA_SLUGS`인 것만 본 뒤, `stats`로 나눈다:

| `stats`에 든 것 | 불릿 |
|---|---|
| `atk_percent` | 파워업!(버스트) |
| `crit_rate` | 웨이크업! 3번불릿 |

기록되는 것은 top-N 대상형 룰 둘뿐이므로 이 구분에 겹침이 없다. 미란다의 다른
불릿들이 같은 스탯을 주긴 하지만 — 애장품 헬스업!의 자신 ATK(`refreshing_buff_rule`),
웨이크업! 2번불릿의 자신 크확(`buff_rule`) — **둘 다 top-N 룰이 아니라서 애초에
기록되지 않는다.** 이 사실이 이 표를 성립시키므로 테스트로 못박는다.

### 4.2 사이클로 묶기

`events`(`burst_cycle`의 이벤트 로그)의 `full_burst_end` 시각이 경계다. 사이클
k는 `(직전 full_burst_end, 이번 full_burst_end]`이고 1부터 센다. 기록은 발동
순서대로 쌓이므로 시각으로 버킷팅하면 된다.

미란다가 그 사이클에 버스트하지 않았으면(B1이 둘인 덱) 그 사이클의
`powering_up`은 빈 배열이다. **웨이크업!은 미란다의 버스트와 무관하게 매
풀버스트마다 발동한다** — `full_burst_enter`는 전원의 룰에 발화하므로 그 사이클도
`wake_up_crit_rate`는 채워진다.

`full_burst_missed`가 있으면(창이 한 번도 안 열리는 배치) `cycles`는 빈 배열이고
`notes`가 그 사실을 적는다.

### 4.3 반환

```python
{
  "seats": [{"slug": ..., "burst_tier": 1|2|3}, ...],   # 좌석 순서
  "miranda_slug": "miranda" | "miranda-signature",
  "has_favorite_item": bool,
  "cycles": [{"index": 1, "powering_up": [slug...],
              "wake_up_crit_rate": [slug...]}, ...],
  "overload_thresholds": [...],      # §5
  "overload_atk_cap_percent": 58.52, # §5.3
  "notes": [str, ...],
}
```

**문장은 백엔드가 만들지 않는다.** 표시 이름을 아는 쪽은 프론트다(`nameFor`).
`notes`는 유닛 이름이 안 들어가는 전제/한계만 담는다.

## 5. 오버로드 임계값 — 얼마나 더 필요한가 / 얼마나 버티는가

`[미란다, a, b, c, d]`에서 유저는 a가 웨이크업!3을 받길 원하는데 b가 받고 있다.
그럼 **a에게 오버로드 공격력이 얼마나 더 필요한가.** 받고 있는 쪽에게는 반대로
**얼마나 떨어져도 유지되는가.**

파워업!(은색)에는 이 값을 내지 않는다(Fienn, 2026-08-08). 상위 2명이고 판정
시점에 켜진 버프가 거의 없어 경쟁이 헐거운 쪽이다.

### 5.1 닫힌형을 쓰지 않는 이유

`(b의 최종공격력 − a의 최종공격력) / a의 표시공격력`은 **필요치를 과대평가한다.**
a의 오버로드가 오르면 파워업!(B1 시전) 판정도 같이 움직여, a가 파워업! 상위 N에
새로 들어가면 그 자리에서 +40.4%를 얻고 밀려난 쪽은 그만큼 잃는다. 계단이 정확히
이 질문이 흥미로운 지점에 서 있다.

그래서 실제로 돌려서 답한다. `evaluate_deck` 1회가 **0.107초**(5인·180초,
2026-08-08 측정)라 12번 돌려도 1.3초다. 근사할 이유가 없다.

### 5.2 단조성 — 이진탐색이 건전한 근거

a의 최종 공격력을 올렸을 때 **경쟁자가 ATK 이득을 보는 경로**가 있으면 술어가
단조가 아니고 이진탐색이 최소값을 놓친다. 저장소에서 ATK 순위를 읽는 곳은
`top_atk_slugs`(상위)와 `lowest_atk_slugs`(하위) 둘인데, 후자의 유일한 소비처는
리버렐리오이고 주는 것은 `charge_time_reduction_sec`이다(`liberalio.py:174`).
**ATK를 순위로 나눠주는 규칙이 없다.**

남는 2차 경로 하나는 적어 둔다: 리버렐리오의 차지 단축이 사격 시각을 옮기면 발수로
켜지는 ATK% 버프가 판정 순간에 살아 있는지가 달라질 수 있다. 그래서 **탐색은
단조를 가정하되, 보고하는 값은 반드시 시뮬로 재확인한 값이다** — 답이 틀릴 수는
없고, 드물게 최소가 아닐 수는 있다.

### 5.3 무엇을 재는가

경계는 **「전 사이클에서 받는가」**다. 웨이크업!3 대상은 사이클마다 바뀔 수 있으니
가장 빡센 사이클이 값을 정한다. 이 정의라야 뱃지의 `n/T` 표기와 한 문장으로
이어진다.

유닛 u의 오버로드 공격력 총합을 x, `all(u, x)` = 「x일 때 u가 전 사이클
웨이크업!3을 받는다」라 하면:

| 지금 상태 | 종류 | 답 |
|---|---|---|
| `all(u, 현재)` 거짓 | `gain` | `all`이 참이 되는 최소 x. 상한에서도 거짓이면 없음 |
| `all(u, 현재)` 참 | `keep` | `all`이 참으로 남는 최소 x — 이 값 밑으로 내려가면 놓친다 |

상한은 `overload_decode`의 테이블이 정한다 — 부위당 최고 굴림 14.63% × 4부위 =
**58.52%**. 숫자를 상수로 적지 않고 `max_atk_percent(tables)`를
`overload_effects.py`에 둔다 — `max_charge_speed_percent`가 바로 옆에서 같은 일을
하고 있고, 둘 다 `NAME_TO_STAT`으로 효과 타입을 찾는다. 테이블이 재적합되면 값이
따라간다.

미란다 자신은 대상이 될 수 없으므로(§1.1) 목록에서 빠진다. 애장품 없는
미란다(`miranda`)면 웨이크업!3이 스킬에 없으므로 **목록 전체가 비어 있다.**

### 5.4 탐색

- **선검사 1회.** `gain`은 상한에서, `keep`은 0에서 돌린다. `gain`이 상한에서도
  거짓이면 「오버로드만으로는 불가능」으로 끝. `keep`이 0에서도 참이면 「0이어도
  유지」로 끝. 둘 다 시뮬 1회.
- **이진탐색 ~12회.** 구간이 0.01%p보다 좁아지면 멈춘다 — 블라블라링크가
  오버로드를 소수 둘째 자리로 보여주므로 그보다 가늘 이유가 없다.
  **보고하는 값은 언제나 실제로 돌려서 참으로 확인된 쪽 끝**이다(`gain`은 위쪽,
  `keep`은 아래쪽). 반올림으로 「1%p 모자란데 된다고 적힌」 값이 나올 수 없다.
- 유닛당 최대 13회 × 4명 = 52회 ≈ **5.6초**. 기준 계산까지 7초 안쪽이라 「이
  니케로 계산」 같은 선택 UI가 필요 없다.

### 5.5 무엇을 고정하는가

- **좌석 순서**를 기준 계산에서 고정한다. x마다 `evaluate_decks`를 다시 부르면
  배치가 바뀌어 다른 덱의 답이 된다.
- **한 유닛만** 움직인다. 둘을 동시에 올리는 경우는 풀지 않는다.
- 스펙 교체는 `dataclasses.replace(spec, overload_options=[...])`로 「공격력 증가」
  라인 하나만 바꾼다(`NikkeSpec`은 dataclass다, `roster.py:48`). ATK는
  `granted_percent`가 표시값을 그대로 쓰므로(`lines`는 차지속도 전용) 값 하나면
  충분하다.

## 6. API — `POST /api/miranda-targets`

`ChargeWindowRequest`(`api.py:231`)와 같은 모양: 로스터를 통째로 받고 슬러그로
가리킨다.

```python
class MirandaTargetsRequest(BaseModel):
    roster: list[UserNikkeState]
    units: list[str]          # 5명

class MirandaCycle(BaseModel):
    index: int
    powering_up: list[str]
    wake_up_crit_rate: list[str]

class MirandaOverloadThreshold(BaseModel):
    slug: str
    current_percent: float
    kind: Literal["gain", "keep"]
    # gain: 이 값 이상이면 전 사이클 받는다 (상한 안에 답이 없으면 None)
    # keep: 이 값 밑으로 내려가면 놓친다 (0.0이면 오버로드 없이도 유지)
    threshold_percent: float | None
```

보스는 **무속성·180초 고정**이다(Fienn, 2026-08-08 — 폼 없음). `BossProfileIn()`의
기본값을 그대로 쓰고 상수로 한 번만 적는다. 그 전제가 답을 바꿀 수 있다는 사실은
`notes`에 항상 실린다 — 보스 속성에 걸린 ATK 버프(`boss_is_element` 조건)를 가진
유닛이 덱에 있으면 실제 레이드와 순위가 다를 수 있다.

422 네 가지:

| 조건 | 메시지 |
|---|---|
| `len(units) != 5` | 덱은 5명이어야 한다 |
| 미란다 부재 | 미란다(또는 애장품 미란다)가 덱에 없다 — 화면에서는 좌석이 고정이라 닿지 않는 가드다(§7.2). API는 화면 밖에서도 불릴 수 있으므로 남긴다 |
| 미지원/로스터에 없는 슬러그 | 그 슬러그를 쓸 수 없다 |
| `InfeasibleDeck` | 성립하는 버스트 순서가 없다 (`_evaluate_decks_sync`의 문구 재사용) |

`_reject_unknown_overload_options`는 평가 경로와 같이 태운다.

## 7. 프론트

### 7.1 계산기 탭 개편

`App.tsx:261-276`의 패널이 `ChargeWindowPanel`을 직접 품고 있는 자리를
`CalculatorPanel`로 바꾼다. `CalculatorPanel`은 서브탭 목록 하나를 들고 있고,
계산기를 늘리는 일이 배열에 항목 하나 넣는 일이 된다.

```
차속 + 타수 계산기 | 미란다 계산기
```

**둘 다 마운트한 채 `hidden`으로 감춘다** — 메인 탭이 이미 그렇고(`App.tsx:171-174`),
차지 계산기의 입력값이 서브탭을 오갈 때 날아가지 않는다.

서브탭 접근성은 메인 탭과 같은 관용구(`role="tablist"` / `role="tab"` /
`aria-controls` / `aria-selected`)를 쓴다.

### 7.2 `MirandaCalculatorPanel.tsx`

편성은 **유니온 탭과 같은 컴포넌트**다(`UnionRaidPanel.tsx:269-291`):

```
<div className="draft-layout">
  <UnitPalette ... />
  <DraftEditor numDecks={1} showLocks={false} fixedSlugs={[mirandaSlug]} ... />
</div>
```

같은 컴포넌트라 드래그·초상화·티어 뱃지 동작이 자동으로 일치한다. 잠금이 없는
이유도 같다 — 고정할 최적화가 없다.

**미란다는 처음부터 앉아 있고, 유저는 남은 네 자리만 채운다**(Fienn, 2026-08-08).

초기값은 `placeUnit(makeEmptyDraft(1), 0, mirandaSlug)`이다. `mirandaSlug`는
로스터에 있는 쪽 — 애장품을 보유하면 임포트가 이미 `miranda-signature`로
승격해 두었으므로(§8) 그것을, 아니면 `miranda`를 쓴다. 패널은 `App.tsx`가
이미 쓰는 대로 `key={activeKey}`로 마운트되므로, 계정을 바꾸면 새 로스터로
다시 앉는다.

**「맨 왼쪽」에는 만들 장치가 없다.** `DraftEditor`가 좌석을 저장 순서가 아니라
버스트 티어 순으로 그리고(`inTierOrder`, `DraftEditor.tsx:205-208`), 미란다는
B1이라 언제나 첫 칸이다. 같은 B1이 하나 더 들어와도 JS의 정렬이 안정적이라 먼저
앉은 미란다가 앞에 남는다.

필요한 것은 **고정** 하나다. `DraftEditor`에 `fixedSlugs?: string[]`(기본
`[]` = 오늘 동작)을 더해 세 가지를 막는다:

1. × 제거 버튼을 그리지 않는다
2. 그립이 `draggable`이 아니다 (끌어내서 뺄 수 없다)
3. 그 좌석으로의 **스왑 드롭을 무시**한다 — 스왑은 점유자를 밀어내므로 ①②만
   막으면 뒷문이 열린 채다

**로스터에 미란다가 없으면** 편성을 시작할 수 없다. 빈 덱을 그려 두고 백엔드의
422를 기다리는 대신, 패널이 안내만 띄운다 — 이 화면에서 유저가 할 수 있는 일이
없기 때문이다.

**팔레트의 「제외」는 이 화면에서 아무 일도 하지 않는다.** 제외가 하는 일은 탐색
후보 풀에서 빼는 것인데 여기엔 탐색이 없고, 제출되는 것은 배치된 다섯뿐이다
(로스터 전체는 스탯 때문에 실리지만 나머지는 안 읽힌다). 그래서
`UnitPalette`의 `excludedSlugs`/`onToggleExclude`를 **옵셔널로 바꾸고**,
`onToggleExclude`가 없으면 토글을 그리지 않는다. 켤 수는 있는데 아무 일도
안 일어나는 컨트롤을 남기지 않는다는 것은 이 저장소가 이미 세운 규칙이다
(`BossProfileField.tsx:47-49`). 기존 두 호출자는 계속 넘기므로 동작이 그대로다.

요청 상태는 `ChargeWindowPanel`처럼 `useState` 세 개(`result`/`error`/`busy`)로
둔다. 전용 훅을 만들 이유가 없다: 취소도, 캐시도, 프로필 저장도 없다. 다만 최대
7초가 걸리므로 진행 문구를 띄운다(유니온 탭의 `recommend-form__progress` 관용구).

### 7.3 `MirandaTargets.tsx` — 뱃지

`cycles`를 유닛별로 접는다. 총 사이클 수 `T`, 어떤 유닛이 받은 사이클 수 `n`:

| 조건 | 표시 |
|---|---|
| `wake_up_crit_rate`에 든 사이클 ≥ 1 | 금색 `[크확]` |
| `powering_up`에 든 사이클 ≥ 1 | 은색 `[공격력]` `[크댐]` |
| `n < T` | 뱃지 뒤에 `n/T` |

`T`는 `cycles.length`(전체 풀버스트 횟수)다. 웨이크업!은 매 사이클 발동하므로
`[크확]`의 분모로 곧바로 맞지만, 파워업!은 미란다가 그 사이클에 버스트했을
때만이라 **`3/5`가 「밀렸다」가 아니라 「미란다가 3번만 쐈다」일 수 있다.** 그
둘을 화면에서 가른다: `powering_up`이 빈 사이클(=그녀가 못 쏜 사이클)이 있으면
목록 아래에 따로 적는다.

대상이 사이클마다 다르면 목록 아래에 한 줄씩:
- `⚠ 2·4사이클에는 도로시 대신 리타가 파워업!을 받아요`
- `⚠ 미란다는 5사이클 중 3번만 버스트해요 (같은 1티어에 니케가 둘이에요)`

### 7.4 임계값 표시

`overload_thresholds`를 유닛 줄에 붙인다.

| `kind` / 값 | 문구 |
|---|---|
| `gain`, 값 있음 | `오버로드 공격력 8.00% → 11.47% 필요 (+3.47%p)` |
| `gain`, `null` | `오버로드 공격력을 상한(58.52%)까지 올려도 못 받아요` |
| `keep`, 값 > 0 | `오버로드 공격력이 5.90% 밑으로 내려가면 놓쳐요 (지금 8.00%, 여유 2.10%p)` |
| `keep`, 값 = 0 | `오버로드 공격력이 없어도 유지돼요` |

상한 숫자는 응답의 `overload_atk_cap_percent`에서 읽는다. 프론트에 박아 두면
테이블이 재적합될 때 조용히 낡는다.

### 7.5 파일

| 파일 | 내용 |
|---|---|
| `frontend/src/components/CalculatorPanel.tsx` | 서브탭 |
| `frontend/src/components/MirandaCalculatorPanel.tsx` | 편성 + 실행 |
| `frontend/src/components/MirandaTargets.tsx` | 초상화 + 뱃지 + 임계값 |
| `frontend/src/api/mirandaTargets.ts` | POST |
| `frontend/src/types/mirandaTargets.ts` | wire 타입 |
| `frontend/src/components/DraftEditor.tsx` | `fixedSlugs` prop (기본 `[]`) |
| `frontend/src/components/UnitPalette.tsx` | 제외 두 prop을 옵셔널로 |
| `frontend/src/App.tsx` | 패널 한 줄 교체 |
| `frontend/src/App.css` | 금/은 뱃지, 서브탭, 고정 좌석 |

wire 타입의 필드는 **옵셔널로 두지 않는다** — 옵셔널이면 타입이 배선 누락을
못 잡는다(`docs/insights.md`, 2026-08-07). `threshold_percent`의 `null`은
「상한 안에 답이 없다」는 뜻을 지닌 값이지 누락이 아니므로 유니온으로 적는다.

## 8. 애장품

로스터 임포트가 애장품 보유 시 이미 `-signature`로 승격한다
(`frontend/src/lib/resourceIdSlugMap.ts:137`). 그래서 계산기는 아무것도 묻지 않고
덱에 든 슬러그가 답이다.

`miranda`(애장품 없음)면 `notes`에 적는다 — 웨이크업! 3번불릿이 스킬 자체에
없어서 금색 뱃지가 안 뜨는 것이지 계산기가 못 찾은 것이 아니다. 이 구분을 안
적으면 화면이 고장난 것으로 읽힌다. 임계값 목록도 이때는 비어 있다(§5.3).

「애장품이 있었다면」을 가정해 보는 기능은 넣지 않는다(YAGNI).

## 9. 이 작업이 바꾸지 않는 것

- **딜 수치는 1비트도 안 움직인다.** 계측은 기본 off이고, 켜도 기록만 한다.
  임계값 탐색은 계산기 안에서만 스펙을 복제해 돌리며 로스터를 건드리지 않는다.
- 미란다의 인코딩은 그대로다(§1 — 맞다).
- 다른 top-N 유닛(맥스웰·레오나·나가)의 grant도 `highest_atk_buff_rule`을 통해
  로그가 붙어 있으면 함께 기록된다 — 오늘은 아무도 그 기록을 읽지 않는다. 탐색
  경로에서는 비용이 0이다: `target_grants`는 `miranda_target_report`(§4)만
  로그를 붙이고, 일반 탐색은 여전히 `None`이라 아무것도 안 쌓인다.
- 차지 계산기의 동작·입력·결과는 그대로다. 바뀌는 것은 감싸는 서브탭뿐이다.
- `DraftEditor`와 `UnitPalette`의 기존 두 호출자(추천 탭·유니온 탭)는 새 prop을
  안 넘기므로 오늘과 같이 동작한다. 두 변경 모두 기본값이 오늘의 동작이다.

## 10. 테스트

**백엔드**

- `test_miranda_buff_timing.py`(신규) — §1.2를 회귀로 고정한다. 파워업!의 기록
  시각이 B1 버스트 이벤트 시각과 같고, 웨이크업!3의 기록 시각이 `full_burst_start`
  와 같으며, 후자의 대상이 파워업!의 ATK 버프가 실린 랭킹에서 나온다는 것
  (파워업!이 없으면 순위가 달라지도록 값을 잡아 확인).
- `test_miranda_buff_timing.py` — §1.3을 고정한다. 표시 공격력이 같고 오버로드만
  다른 두 유닛에서 오버로드가 순위를 가른다.
- `test_raid_simulator.py` — `collect_target_grants` 기본값에서는 결과에
  `target_grants` 키가 없다(핫패스 무변경의 증거).
- `test_miranda_targets.py`(신규) — 애장품 없는 미란다는 `wake_up_crit_rate`가
  전 사이클 빈 배열이고 `powering_up`이 1명이며 임계값 목록이 비어 있다;
  애장품이면 2명 + 1명. B1이 둘인 덱에서 미란다가 못 쏜 사이클의 `powering_up`이
  비고 `wake_up_crit_rate`는 차 있는다. 미란다는 자기 대상이 되지 않는다.
- `test_miranda_overload_threshold.py`(신규) — **경계를 실제로 밟는다**:
  `gain` 임계값에서 돌리면 전 사이클 받고 한 눈금 아래에서는 못 받는다;
  `keep` 임계값 바로 아래에서는 놓친다. 상한에서도 못 받는 유닛은 `None`.
  오버로드 없이도 유지되는 유닛은 `keep` + `0.0`. 탐색 전후로 좌석 순서가 같다.
  `max_atk_percent`가 테이블에서 58.52를 낸다.
- `test_api_miranda_targets.py`(신규) — 422 네 가지와 정상 응답 한 건.

**프론트**

- `CalculatorPanel.test.tsx` — 서브탭 전환, 감춰진 패널이 언마운트되지 않는다
  (차지 계산기 입력이 돌아와도 남아 있다).
- `MirandaTargets.test.tsx` — 금+은 / 은만 / 뱃지 없음 세 상태, `n/T` 표기,
  변동 문장, 임계값 네 가지 문구, 애장품 없음 안내.
- `MirandaCalculatorPanel.test.tsx` — 미란다가 처음부터 첫 칸에 앉아 있고 남은
  네 자리가 비어 있다; 애장품을 보유하면 앉는 것이 `miranda-signature`다;
  로스터에 미란다가 없으면 편성 대신 안내가 나온다; 다섯이 안 차면 실행 버튼
  비활성; 진행 문구; 실패 시 오류 표시.
- `DraftEditor.test.tsx` — `fixedSlugs`의 좌석은 제거 버튼이 없고, 드래그
  소스가 아니며, **그 위로 스왑 드롭을 해도 밀려나지 않는다**(뒷문). 기본값
  `[]`에서는 오늘 동작 그대로다.
- `UnitPalette.test.tsx` — `onToggleExclude` 없이 렌더하면 제외 토글이 없고,
  넘기면 오늘 동작 그대로다.

## 규모

프로덕션 ~920줄(백엔드 ~450, 프론트 ~470), 테스트 ~560줄.
