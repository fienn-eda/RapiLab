# 미란다 계산기 — 누가 파워업!과 웨이크업!을 받는가

날짜: 2026-08-08

미란다의 두 대상형 버프는 **최종 공격력 순위**로 대상을 정한다. 순위는 그 순간
살아 있는 ATK 버프까지 반영한 값이라, 로스터의 공격력만 보고는 답을 알 수 없다.
계산기 탭에 덱 5인을 편성하면 누가 무엇을 받는지 초상화 옆 뱃지로 답한다.

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

### 1.3 검증이 밝힌 사실 하나

**파워업!은 자기 힘만으로 웨이크업!3의 대상을 바꾸지 못한다.** 상위 N명을 같은
비율로 올리므로 그들 사이의 순서도, 3위와의 격차 방향도 뒤집히지 않는다.

대상이 사이클마다 갈리는 진짜 원인은 셋이다 — ① 같은 순간 뒤이어 터지는 B2/B3
버스트의 대상형 ATK 버프, ② 덱 순서상 미란다보다 앞선 아군의 `full_burst_enter`
ATK 버프(`fire_trigger`가 `rules_by_slug` 순서로 돈다), ③ 지난 창에서 넘어와
아직 살아 있는 버프. 계산기가 존재할 이유가 이 셋이다.

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
집합만으로는 두 불릿을 구분할 수 없고(둘 다 같은 랭킹을 쓴다), `n`으로 나누는
것은 값이 바뀌면 조용히 깨진다. 그래서 자기가 줄 스탯 이름을 넘기는 두 곳만
기록된다:

- `_helpers.highest_atk_buff_rule` (`_helpers.py:136`) → 파워업!
- `_helpers._resolve_scope`의 `("top_atk", n)` 분기 (`_helpers.py:126`) → 웨이크업!3

`grant_stats`를 안 넘기는 다른 호출자(맥스웰·레오나·나가·마나·소다)는 오늘과
동일하게 아무것도 기록하지 않는다.

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
  "notes": [str, ...],
}
```

**문장은 백엔드가 만들지 않는다.** 표시 이름을 아는 쪽은 프론트다(`nameFor`).
`notes`는 유닛 이름이 안 들어가는 전제/한계만 담는다.

## 5. API — `POST /api/miranda-targets`

`ChargeWindowRequest`(`api.py:231`)와 같은 모양: 로스터를 통째로 받고 슬러그로
가리킨다.

```python
class MirandaTargetsRequest(BaseModel):
    roster: list[UserNikkeState]
    units: list[str]          # 5명
```

보스는 **무속성·180초 고정**이다(Fienn, 2026-08-08 — 폼 없음). `BossProfileIn()`의
기본값을 그대로 쓰고 상수로 한 번만 적는다. 그 전제가 답을 바꿀 수 있다는 사실은
`notes`에 항상 실린다 — 보스 속성에 걸린 ATK 버프(`boss_is_element` 조건)를 가진
유닛이 덱에 있으면 실제 레이드와 순위가 다를 수 있다.

422 네 가지:

| 조건 | 메시지 |
|---|---|
| `len(units) != 5` | 덱은 5명이어야 한다 |
| 미란다 부재 | 미란다(또는 애장품 미란다)가 덱에 없다 |
| 미지원/로스터에 없는 슬러그 | 그 슬러그를 쓸 수 없다 |
| `InfeasibleDeck` | 성립하는 버스트 순서가 없다 (`_evaluate_decks_sync`의 문구 재사용) |

`_reject_unknown_overload_options`는 평가 경로와 같이 태운다.

## 6. 프론트

### 6.1 계산기 탭 개편

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

### 6.2 `MirandaCalculatorPanel.tsx`

편성은 **유니온 탭과 같은 컴포넌트**다(`UnionRaidPanel.tsx:269-291`):

```
<div className="draft-layout">
  <UnitPalette ... />
  <DraftEditor numDecks={1} showLocks={false} ... />
</div>
```

같은 컴포넌트라 드래그·제외·초상화·티어 뱃지 동작이 자동으로 일치한다. 잠금이
없는 이유도 같다 — 고정할 최적화가 없다.

요청 상태는 `ChargeWindowPanel`처럼 `useState` 세 개(`result`/`error`/`busy`)로
둔다. 전용 훅을 만들 이유가 없다: 취소도, 캐시도, 프로필 저장도 없는 수 초짜리
요청이다.

### 6.3 `MirandaTargets.tsx` — 뱃지

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

미란다 본인은 뱃지 없이 목록에 남는다(§1.1 — 5인 덱에서 그녀는 후보가 아니다).

### 6.4 파일

| 파일 | 내용 |
|---|---|
| `frontend/src/components/CalculatorPanel.tsx` | 서브탭 |
| `frontend/src/components/MirandaCalculatorPanel.tsx` | 편성 + 실행 |
| `frontend/src/components/MirandaTargets.tsx` | 초상화 + 뱃지 |
| `frontend/src/api/mirandaTargets.ts` | POST |
| `frontend/src/types/mirandaTargets.ts` | wire 타입 |
| `frontend/src/App.tsx` | 패널 한 줄 교체 |
| `frontend/src/App.css` | 금/은 뱃지, 서브탭 |

wire 타입의 필드는 **옵셔널로 두지 않는다** — 옵셔널이면 타입이 배선 누락을
못 잡는다(`docs/insights.md`, 2026-08-07).

## 7. 애장품

로스터 임포트가 애장품 보유 시 이미 `-signature`로 승격한다
(`frontend/src/lib/resourceIdSlugMap.ts:137`). 그래서 계산기는 아무것도 묻지 않고
덱에 든 슬러그가 답이다.

`miranda`(애장품 없음)면 `notes`에 적는다 — 웨이크업! 3번불릿이 스킬 자체에
없어서 금색 뱃지가 안 뜨는 것이지 계산기가 못 찾은 것이 아니다. 이 구분을 안
적으면 화면이 고장난 것으로 읽힌다.

「애장품이 있었다면」을 가정해 보는 기능은 넣지 않는다(YAGNI).

## 8. 이 작업이 바꾸지 않는 것

- **딜 수치는 1비트도 안 움직인다.** 계측은 기본 off이고, 켜도 기록만 한다.
- 미란다의 인코딩은 그대로다(§1 — 맞다).
- 다른 top-N 유닛(맥스웰·레오나·나가·마나·소다)은 `grant_stats`를 안 넘기므로
  기록되지 않는다. 그들의 계산기가 필요해지면 인자 하나를 넘기면 된다.
- 차지 계산기의 동작·입력·결과는 그대로다. 바뀌는 것은 감싸는 서브탭뿐이다.

## 9. 테스트

**백엔드**

- `test_miranda_buff_timing.py`(신규) — §1.2를 회귀로 고정한다. 파워업!의 기록
  시각이 B1 버스트 이벤트 시각과 같고, 웨이크업!3의 기록 시각이 `full_burst_start`
  와 같으며, 후자의 대상이 파워업!의 ATK 버프가 실린 랭킹에서 나온다는 것
  (파워업!이 없으면 순위가 달라지도록 값을 잡아 확인).
- `test_raid_simulator.py` — `collect_target_grants` 기본값에서는 결과에
  `target_grants` 키가 없다(핫패스 무변경의 증거).
- `test_miranda_targets.py`(신규) — 애장품 없는 미란다는 `wake_up_crit_rate`가
  전 사이클 빈 배열이고 `powering_up`이 1명; 애장품이면 2명 + 1명. B1이 둘인
  덱에서 미란다가 못 쏜 사이클의 `powering_up`이 비고 `wake_up_crit_rate`는
  차 있는다. 미란다는 자기 대상이 되지 않는다.
- `test_api_miranda_targets.py`(신규) — 422 네 가지와 정상 응답 한 건.

**프론트**

- `CalculatorPanel.test.tsx` — 서브탭 전환, 감춰진 패널이 언마운트되지 않는다
  (차지 계산기 입력이 돌아와도 남아 있다).
- `MirandaTargets.test.tsx` — 금+은 / 은만 / 뱃지 없음 세 상태, `n/T` 표기,
  변동 문장, 애장품 없음 안내.
- `MirandaCalculatorPanel.test.tsx` — 5명 미만이면 실행 버튼 비활성, 미란다가
  없으면 안내, 실패 시 오류 표시.

## 규모

프로덕션 ~700줄(백엔드 ~330, 프론트 ~370), 테스트 ~380줄.
