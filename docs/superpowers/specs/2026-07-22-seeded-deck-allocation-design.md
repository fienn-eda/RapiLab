# 초안 기반 5덱 최적화 — 설계 (Draft-Based Deck Allocation)

- 날짜: 2026-07-22
- 상태: 설계 확정, 구현 계획 대기
- 관련: Phase 5(5덱 분배 최적화, 백엔드/프론트 완료) 위에 얹는 확장
- 선행 문서: `docs/superpowers/specs/2026-07-17-five-deck-allocation-design.md`

## 배경 / 동기

솔로 레이드는 **보스 1마리를 최대 5개 팀으로 상대**하고, 팀별 점수를 합산하며, 니케는
전체에서 한 번씩만 쓸 수 있다. 이는 현재 `allocate_decks`가 가정하는 "같은 보스,
재사용 없는 5덱 분배"와 정확히 일치한다(총합 = 덱별 독립 점수의 합).

시즌마다 최적 조합을 가르는 결정 요소를 진단한 결과:

| 시즌 특성 | 현재 상태 |
|---|---|
| 원소(Code) | ✅ `BossProfile.element` (원소우위 반영) |
| 부위파괴/코어 | ✅ `part_destructible` / `core_hittable` |
| 방어력·전투시간 | ✅ `enemy_def` / `fight_duration` |
| 생존/기믹 | ❌ 시뮬 안 됨 + 방어 유닛 강제 편성 수단 없음 |

생존 필요성은 **시즌 × 유저 육성 상태**에 따라 달라진다(고돌파 유저는 전용 힐러 없이
버티고, 라이트 유저는 필요). 따라서 엔진이 생존을 자동 판정하면 안 된다 — 판단은
유저 몫이다. 그런데 현재는 유저가 "이 시즌엔 방어 유닛 필요"라고 판단해도 그것을
추천기에 반영할 방법이 없다(순수 딜 최적해가 방어 유닛을 빼버린다).

## 핵심 아이디어 — "초안 + 잠금" 통합 모델

zero-base 추천 대신, **유저의 초안(부분 또는 완성 편성)을 받아 최적화**한다. 유저가 각
덱에 놓은 유닛은 두 상태를 가진다:

- **잠금(locked)**: 엔진이 반드시 그 덱에 유지 (생존 유닛 등 "이건 꼭"). 탐색을 제약해
  전역 최선과 **다른**, 유저가 수용 가능한 결과를 낸다 → 초안의 진짜 최적화 가치.
- **유연(flexible)**: 엔진이 유지·이동·교체 가능. 최적화의 **시작점(warm-start)**.

빈 슬롯은 엔진이 채운다. 이 하나로 세 시나리오가 커버된다.

### 세 시나리오

1. **부분 초안(시드 완성)** — 유저가 핵심 유닛(잘 키운 B1/B2, 또는 생존 유닛)을 몇 개
   고정하고 나머지는 비움. 엔진이 그에 궁합 맞는 나머지(특히 B3 딜러)를 훨씬 작은
   공간에서 찾아 채운다. 각 덱 승부처가 "B1/B2 버프에 어울리는 B3"라는 도메인 사실에
   부합. 생존도 흡수(유저가 방어 유닛을 직접 고정).
2. **완성 구성 개선** — 유저가 25칸을 전부 채워 제출(이미 전투를 마친 구성 등). 최적이
   아닐 수 있으니 **더 나은 대안**을 제시한다. 아래 "완성 구성 개선" 참조.
3. **zero-base** — 아무것도 안 놓음 → 지금과 동일한 전역 최적 분배.

### 정직한 한계: 완성 구성을 "전부 유연"으로 내면 추천 = 전역 최선

유저가 25칸을 **전부 유연**으로 제출하고 우리가 전역 최적화를 돌리면, **추천 결과는
아무것도 안 낸 유저와 동일한 전역 최선**이다 — 채우는 행위 자체는 추천을 바꾸지
못한다(Fienn 지적, 2026-07-22). 그래서 완성 구성 시나리오에서 25명 제출이 실제
가치를 가지려면, 다음 둘을 **함께** 제시한다:

- **내 25명 안에서의 최선 배치**(후보 풀 = 제출한 25명): 벤치를 안 끌어오고 유저가
  가진 유닛만으로의 최적 partition/그룹핑/순서. → 25명 제출이 갖는 최적화 의미.
- **벤치 포함 전역 최선**(후보 풀 = 전체 로스터): 여기에 더해 "벤치를 쓰면 +얼마"까지.

## 목표 / 비목표

**목표**
- 유저가 덱별로 유닛을 놓으면(잠금/유연/빈칸), 그것을 반영한 최선의 분배를 반환한다.
- 잠금 유닛의 **버스트 순서는 엔진이 교정**한다(유저가 비효율적으로 배치해도 됨).
- 빈 자리는 **B1/B2/B3 전 티어를 고려**해 채운다(고정이 B3 하나뿐이어도 동작).
- 완성 구성 제출 시 **baseline(내 구성 점수) → 내 25명 최선 → 벤치 포함 최선**의 3단
  진단 + 덱별 diff를 제공한다. 추천은 **절대 유저 구성보다 나쁘지 않다**.
- 프론트에 초안 편성 UI(팔레트 + 5덱×5슬롯) + 캐릭터 초상화를 제공한다.

**비목표**
- 생존/피격/HP/힐을 시뮬레이션하지 않는다(순수 딜 최대화기 유지).
- 보스 기믹/페이즈 타임라인을 모델링하지 않는다.
- 버스트 좌우 순서를 입력받지 않는다(소속만; 순서는 엔진이 배정·점수화).
- `gauge_charge_time` / `mode`를 노출하지 않는다(아래 근거 참조).

### `gauge_charge_time` / `mode`를 노출하지 않는 근거

`burst_cycle.py` 도크스트링대로, 이 엔진은 "게이지가 쿨다운보다 먼저 다 찬다"는
전제 하에 동작한다 — `gauge_charge_time`은 Full Burst 종료 후 다음 사이클까지의
**바닥값**으로만 남고, 실제 병목은 가장 늦게 도는 티어의 쿨다운(CDR)이다. "누수 없이
CDR로 사이클을 굴린다"가 이미 엔진의 기본 전제라 보스별 노출 실익이 없다. `mode`도
기본이 `"manual"`(0.1초 간격)이라 수동전투 가정과 일치한다. 둘 다 현재 기본값을
유지한다.

## 설계

### ① 백엔드 — 완성 프리미티브 + 제약 최적화

**A. "고정 유닛을 포함하는 최선의 덱" 완성 프리미티브**

고정 유닛 집합 `required`(각자 `burst_tier`)와 후보 풀 `pool`, `boss`가 주어지면,
`required`를 **모두 포함**하는 최선의 유효 덱을 반환한다.

- 고정 유닛의 티어 카운트와 양립하는 **모든 `ALLOWED_SHAPES`**를 열거
  (`ALLOWED_SHAPES = ((1,1,3),(1,2,2),(2,1,2))`). 각 shape에서 `required`가 차지한
  티어 슬롯을 뺀 나머지를 `pool`에서 티어별로 채운다.
  - 예: `required = {B3 하나}`. 양립 shape 전부 시도 → (1,1,3): +1 B1,+1 B2,+1 B3 /
    (1,2,2): +1 B1,+2 B2 / (2,1,2): +2 B1,+1 B2. 최선을 고른다.
- 기존 `shape_combinations`(deck_search.py)에 "이 유닛들을 반드시 포함" 필터를 건 형태.
- 완성 후 **버스트 순서 최적화**는 기존 경로(`_intra_tier_orderings` + seat rule,
  예: Modernia/Velvet을 티어 내 마지막에 앉힘)를 그대로 탄다 → 유저가 순서를 잘못
  넣어도 교정.

**B. 제약 최적화 함수 `optimize(pool, draft, boss, num_decks)`**

`draft` = 덱별 배치(각 유닛 잠금/유연). 동작:

- 잠금 유닛은 그 덱에 고정하고 위 완성 프리미티브로 각 덱을 완성(빈칸 채움).
- 덜 채워진 덱이 있으면 기존 greedy peeling으로 나머지 빈 덱을 `pool`에서 채움.
- **스왑 언덕오르기**(`_swap_pass`)를 돌리되 **잠금 유닛이 앉은 좌석은 잠금 마스크**로
  스왑 대상에서 제외. 유연/채움 유닛은 계속 개선됨(벤치=`pool`−사용분과도 스왑).
- `draft`가 비면 기존 `allocate_decks`와 **100% 동일**(하위호환, 기존 경로 불변).

`_swap_pass`/`_try_pair_swaps`/`_try_leftover_swaps`에 좌석별 locked 마스크를 추가한다.

**C. "유저 구성보다 나쁘지 않음" 보장 (완성 구성 개선)**

warm-start 스왑은 **같은 티어끼리만** 스왑 → 벤치 유닛 교체는 되지만 **덱 shape는
유저가 짠 채로 고정**된다. 유저의 shape 선택이 비최적이면 shape를 전부 탐색하는
from-scratch 경로가 필요하다. 그래서 완성 구성에 대해서는:

- `warm` = `optimize(pool, draft=유저구성, ...)` — 유저 구성에서 출발 → **≥ baseline** 보장.
- `scratch` = `optimize(pool, draft=∅, ...)`(= 기존 from-scratch) — 모든 shape 탐색.
- 결과 = `max(warm, scratch)`. ⇒ shape 너머도 탐색하면서 **≥ 유저 구성** 동시 보장.

(부분 초안 시나리오는 잠금 자체가 목적이라 `warm`만; baseline 보호 불필요.)

**D. 완성 구성 개선의 3단 산출**

`draft`가 완성(모든 덱 5칸, 총 `num_decks×5`)일 때:

- `baseline` = 유저 구성 그대로의 점수(엔진 최선 순서로 각 덱 채점).
- `within_draft` = `max(warm, scratch)` with **pool = 제출한 유닛만**. ⇒ ≥ baseline.
- `recommended` = `max(warm, scratch)` with **pool = 전체 로스터**. ⇒ ≥ within_draft ≥ baseline.

세 값은 **단조 증가**(전체 로스터 ⊇ 제출 유닛 ⊇ baseline partition)라 "내 구성 →
내 유닛 재배치(+Δ1) → 벤치 포함(+Δ2)"로 자연스럽게 제시된다.

**불가능 초안 검증**(조용히 버리지 않고 식별 가능한 422)

- shape 불가: 한 덱의 잠금 티어 카운트가 어떤 `ALLOWED_SHAPES`로도 안 됨(예: B1 3명).
- 전역 고갈: 잠금들이 특정 티어를 다 소진해 남은 덱을 유효 shape로 못 채움.
- 미지원/미보유 슬러그 포함 / 같은 슬러그가 두 덱에 중복 배치.

### ② API + 데이터

**`/api/recommend-raid` 입력에 `draft` 추가**

```python
class DraftUnit(BaseModel):
    slug: str
    locked: bool = False        # true=반드시 이 덱 유지, false=warm-start 힌트

class DraftDeck(BaseModel):
    units: list[DraftUnit]      # 0..5, 순서 무의미(소속만)

class RecommendRaidRequest(RecommendRequest):
    num_decks: int = Field(5, ge=1, le=5)
    draft: list[DraftDeck] = [] # 빈 리스트 = zero-base
```

- `len(draft) <= num_decks` 검증. 한 유닛은 draft 전체에서 최대 1회.

**응답 — 하위호환 유지 + 진단 필드 추가(additive)**

```python
class DeckRecommendation(BaseModel):
    deck: list[str]
    total_damage: float
    burst_damage: float
    normal_attack_damage: float
    pinned_slugs: list[str] = []          # 그 덱에서 유저가 잠근 슬러그

class DraftAllocation(BaseModel):
    decks: list[DeckRecommendation]
    combined_total_damage: float
    leftover_slugs: list[str]

class RecommendRaidResponse(BaseModel):
    decks: list[DeckRecommendation]        # = recommended(전역 최선). 기존 shape 유지
    combined_total_damage: float           # 기존
    excluded_slugs: list[str]              # 기존
    leftover_slugs: list[str]              # 기존
    within_draft: DraftAllocation | None = None       # 완성 구성일 때만
    baseline_total_damage: float | None = None        # 완성 구성일 때만
```

기존 소비자(레이드 모드 UI/mock)는 top-level `decks`/`combined_total_damage` 그대로
동작. 새 필드는 완성 구성 제출 시에만 채워진다.

**신규 `GET /api/supported-units`** (팔레트용)

```python
class SupportedUnit(BaseModel):
    slug: str
    name: str
    burst_tier: int            # 1 | 2 | 3
    nikke_class: str           # Attacker | Defender | Supporter
    element: str               # Fire | Water | Wind | Iron | Electric
```

- 소스: 엔진 registry(지원 슬러그) + `load_directory()`(api.py `_DIRECTORY`, name/element
  등 메타). burst_tier는 로스터 스펙 조립과 동일 소스. **정확한 필드 매핑은 구현
  계획에서 확정**(directory 스키마 확인 필요).

### ③ 프론트 — 초안 편성 UI + 초상화

- **팔레트**: 유저 보유 ∩ 엔진 지원 니케를 B1/B2/B3 그룹으로. 유저 로스터
  (`useRoster`, localStorage) × `/api/supported-units`.
- **5덱 × 5슬롯 편성기**: 각 덱은 최대 5유닛 **소속(집합)** — 슬롯 위치는 버스트 순서가
  아님(순서는 결과에서 엔진 배정). 클릭/드래그 배치, 유닛당 최대 1덱(재사용 금지
  클라단 강제). 각 배치 유닛에 **잠금 토글**(자물쇠).
- **"최적화" 버튼**: 초안을 `draft`로 POST → 결과 렌더.
  - 부분/zero-base: 추천 덱을 `RaidResults.tsx` 재사용해 렌더, `pinned_slugs`로
    잠금/채움 시각 구분.
  - 완성 구성: **3단 비교** 렌더 — baseline → within_draft(+Δ1) → recommended(+Δ2),
    각 단계 덱별 diff(무엇이 바뀌었나).
- **검증 피드백**: 백엔드 422(불가능 초안)를 이해 가능한 문구로 표시.
- 기존 레이드 모드(zero-base)는 유지 — draft가 비면 같은 화면이 그대로 동작.

### 초상화 — 소싱 발견 게이트

레포에 캐릭터 초상화가 없다(있는 이미지는 `capturedimages/` 스탯 캡처뿐). **1단계는
소싱 발견**. 절대 URL을 지어내지 않는다.

1. slug로 안정 매핑되는 초상화 소스가 실제 있는지 검증. 후보: 수집 파이프라인이 이미
   받는 dotgg/lootandwaifus 데이터의 이미지 필드, 또는 blablalink CDN(Phase B에서
   스탯 테이블 소비에 이미 사용).
2. 있으면: 로컬 다운로드(핫링크 금지 — 깨질 수 있음), slug→파일 매핑 커밋, 다운로드
   스크립트에 이름·문서 부여.
3. 없으면: **이름+티어+클래스색 칩으로 폴백**, 초상화는 별도 백로그.

편성기 로직은 초상화 유무와 무관하게 동작(칩/초상화는 표현 레이어).

## 데이터 계약 요약

- `POST /api/recommend-raid` 요청에 `draft: [{units:[{slug,locked}]}, ...]` 추가(옵셔널).
- 응답: `DeckRecommendation.pinned_slugs` 추가 + `within_draft`/`baseline_total_damage`
  (완성 구성일 때만) 추가. top-level 기존 필드 불변.
- `GET /api/supported-units` → `[{slug, name, burst_tier, nikke_class, element}]`.
- 계약 상세는 `frontend/README.md`에 기록(프론트 병렬 착수의 단일 출처).

## 테스트

- 완성 프리미티브: 잠금 유닛이 결과 덱에 항상 포함 / 순서 교정(Modernia/Velvet 왼쪽
  입력 → 오른쪽 착석) / 빈 자리가 전 티어에서 채워짐(B3 하나 고정 → 유효 shape) /
  `draft=∅`가 기존 결과와 비트 동일.
- 완성 구성 개선: `baseline ≤ within_draft ≤ recommended` 단조성 / recommended가 절대
  baseline보다 안 나쁨 / within_draft가 벤치를 안 씀(pool=제출 유닛) / recommended가
  벤치 유닛을 끌어와 개선하는 케이스.
- 불가능 초안: B1 3명·전역 고갈·미지원 슬러그·중복 배치 각각 422 + 식별 메시지.
- API: `draft` 왕복 + `pinned_slugs` 정확성 + 완성 구성 응답 필드 + `/api/supported-units`.
- 프론트: 팔레트 그룹핑 / 재사용 금지 / 잠금 토글 / 3단 비교 렌더 / 422 표시(Vitest).

## 병렬화 / 시퀀싱

세 조각으로 분해되며 옆 세션에 넘기기 좋다.

1. **초상화 소싱+다운로드** — 완전 독립. 즉시 병렬 착수 가능(발견 게이트부터).
2. **백엔드 완성 프리미티브 + `optimize` + API** — 임계경로. 데이터 계약
   (`frontend/README.md`) 정의.
3. **프론트 편성기 UI** — API 계약 초안이 나오면 mock 클라이언트로 병렬 착수 가능
   (기존 mock 패턴: `recommendRaidClient.mock.ts`).

## 열린 항목 / 후속

- `/api/supported-units`의 directory 스키마 → name/class/element/burst_tier 필드 매핑은
  구현 계획에서 확정.
- 초상화 소싱 결과에 따라 카드 표현 확정.
- 성능: 완성 구성 개선은 within_draft(작은 풀)+recommended(전체 로스터 from-scratch)
  두 탐색 → 후자가 비용 지배. zero-base와 같은 수준으로 예상, 측정으로 확인.
