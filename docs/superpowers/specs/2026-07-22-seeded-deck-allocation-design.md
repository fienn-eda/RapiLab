# 시드 기반 5덱 최적화 — 설계 (Seeded Deck Allocation)

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

### 핵심 아이디어

zero-base 추천 대신, **유저의 초안(부분 편성)을 받아 빈 자리를 최적화**한다. 유저가
잘 키운 핵심 유닛(주로 B1/B2 버퍼, 또는 생존용 유닛)을 각 덱에 고정하면, 엔진은
훨씬 작은 탐색 공간에서 그에 궁합이 맞는 나머지(특히 B3 딜러)를 찾는다. 이는 각 덱의
승부처가 "B1/B2 버프에 잘 어울리는 B3 구성"이라는 도메인 사실과 정확히 맞고, 생존
문제도 자연스럽게 흡수한다(유저가 필요하면 방어 유닛을 직접 고정).

## 목표 / 비목표

**목표**
- 유저가 덱별로 고정 유닛을 지정하면, 그것을 포함하는 최선의 5덱 분배를 반환한다.
- 고정 유닛의 **버스트 순서는 엔진이 교정**한다(유저가 비효율적으로 배치해도 됨).
- 빈 자리는 **B1/B2/B3 전 티어를 고려**해 채운다(고정이 B3 하나뿐이어도 동작).
- 프론트에 초안 편성 UI(팔레트 + 5덱×5슬롯) + 캐릭터 초상화를 제공한다.

**비목표**
- 생존/피격/HP/힐을 시뮬레이션하지 않는다(순수 딜 최대화기 유지).
- 보스 기믹/페이즈 타임라인을 모델링하지 않는다.
- `gauge_charge_time` / `mode`를 노출하지 않는다(아래 근거 참조).

### `gauge_charge_time` / `mode`를 노출하지 않는 근거

`burst_cycle.py` 도크스트링대로, 이 엔진은 "게이지가 쿨다운보다 먼저 다 찬다"는
전제 하에 동작한다 — `gauge_charge_time`은 Full Burst 종료 후 다음 사이클까지의
**바닥값**으로만 남고, 실제 병목은 가장 늦게 도는 티어의 쿨다운(CDR)이다. "누수 없이
CDR로 사이클을 굴린다"가 이미 엔진의 기본 전제라 보스별 노출 실익이 없다. `mode`도
기본이 `"manual"`(0.1초 간격)이라 수동전투 가정과 일치한다. 둘 다 현재 기본값을
유지한다.

## 설계

### ① 백엔드 — "고정 유닛을 포함하는 최선의 덱" 프리미티브

핵심 신규 연산: **부분 덱 완성**. 고정 유닛 집합 `required`(각자 `burst_tier`를 가짐)와
남은 후보 풀 `pool`, `boss`가 주어지면, `required`를 **모두 포함**하는 최선의 유효 덱을
반환한다.

- 고정 유닛의 티어 카운트와 양립하는 **모든 `ALLOWED_SHAPES`**를 열거한다
  (`ALLOWED_SHAPES = ((1,1,3),(1,2,2),(2,1,2))`). 각 shape에 대해, `required`가 이미
  차지한 티어 슬롯을 뺀 나머지를 `pool`에서 티어별로 채운다.
  - 예: `required = {B3 하나}`. 양립 shape 전부 시도 → (1,1,3): +1 B1, +1 B2, +1 B3 /
    (1,2,2): +1 B1, +2 B2 / (2,1,2): +2 B1, +1 B2 + (필요 시 B3). 최선을 고른다.
- 이는 기존 `shape_combinations`(deck_search.py)에 "이 유닛들을 반드시 포함" 필터를
  건 형태다. 재사용은 `pool`이 이미 고정 유닛을 제외하고 있으므로 자연 보장된다.
- 완성 후 **버스트 순서 최적화**는 기존 경로(`_intra_tier_orderings` + seat rule,
  예: Modernia/Velvet을 티어 내 마지막에 앉힘)를 그대로 탄다 → 유저가 순서를
  잘못 넣어도 교정된다.

**`allocate_decks`에 `seeds` 파라미터 추가**

```python
def allocate_decks(roster, boss, num_decks=5, seeds=None,
                   time_budget_sec=45.0, workers=None):
    ...
```

- `seeds`: 유저가 짠 덱별 고정 슬러그 리스트. `seeds=None`/빈 리스트면 **기존과 100%
  동일**(하위호환, 기존 테스트/경로 불변).
- 흐름: (1) 각 시드 덱을 위 프리미티브로 완성하고 고정+채운 유닛을 풀에서 제거 →
  (2) 남은 빈 덱(`num_decks - len(seeds)`)은 지금처럼 greedy peeling으로 채움 →
  (3) 스왑 언덕오르기(`_swap_pass`)에서 **고정 유닛은 잠금**(스왑 대상에서 제외).
- `_swap_pass`/`_try_pair_swaps`/`_try_leftover_swaps`에 좌석별 "locked" 마스크를
  추가한다(고정 유닛이 앉은 자리는 스왑 후보로 뽑지 않음). 채워진(엔진이 넣은)
  유닛은 잠기지 않으므로 스왑으로 계속 개선된다.

**불가능 초안 검증**(조용히 버리지 않고 명확한 에러)

- shape 불가: 한 시드 덱의 고정 티어 카운트가 어떤 `ALLOWED_SHAPES`로도 안 됨
  (예: 한 덱에 B1 3명 — 최대 2).
- 전역 고갈: 고정들이 특정 티어를 다 소진해 남은 덱을 유효 shape로 못 채움.
- 미지원/미보유 슬러그가 `seeds`에 포함.
- 같은 슬러그가 두 덱에 중복 고정.

각각 어떤 시드 덱/슬러그가 문제인지 식별 가능한 메시지로 422 반환. 흔한 케이스
(B3 하나, B1 하나 고정)는 항상 완성 가능하므로 정상 경로.

### ② API + 데이터

**`/api/recommend-raid`에 `seeds` 추가**

```python
class SeedDeck(BaseModel):
    slugs: list[str]           # 이 덱에 고정할 슬러그(순서 무의미, 소속만)

class RecommendRaidRequest(RecommendRequest):
    num_decks: int = Field(5, ge=1, le=5)
    seeds: list[SeedDeck] = []  # 빈 리스트 = 기존 zero-base
```

- `len(seeds) <= num_decks` 검증. 각 `SeedDeck.slugs`는 1~5개.
- 응답 `RecommendRaidResponse`는 그대로. 단 각 덱이 **어떤 유닛이 유저 고정이고
  어떤 게 엔진 채움인지** 구분할 수 있어야 한다 → `DeckRecommendation`에
  `pinned_slugs: list[str]`(그 덱에서 유저가 고정한 슬러그) 추가. 프론트가 이걸로
  고정/채움을 시각 구분한다.

**신규 `/api/supported-units`**

팔레트가 "엔진 지원 니케"를 티어별로 그리려면 slug→메타 맵이 필요하다.

```python
class SupportedUnit(BaseModel):
    slug: str
    name: str
    burst_tier: int            # 1 | 2 | 3
    nikke_class: str           # Attacker | Defender | Supporter
    element: str               # Fire | Water | Wind | Iron | Electric

@app.get("/api/supported-units")
def supported_units() -> list[SupportedUnit]: ...
```

- 소스: 엔진 registry(지원 슬러그) + `load_directory()`(이미 api.py에서 `_DIRECTORY`로
  로드, name/element 등 메타 보유). burst_tier는 로스터 스펙 조립 시 나오는 값과 동일
  소스를 사용한다. **여기서 정확한 필드 매핑은 구현 계획에서 확정**(directory 스키마
  확인 필요).

### ③ 프론트 — 초안 편성 UI + 초상화

- **팔레트**: 유저 보유 ∩ 엔진 지원 니케를 B1/B2/B3 그룹으로 표시. 유저 로스터
  (`useRoster`, localStorage)와 `/api/supported-units`를 교차한다.
- **5덱 × 5슬롯 편성기**: 각 덱은 최대 5유닛의 **소속(집합)** — 슬롯 위치는 버스트
  순서가 아니다(순서는 결과에서 엔진이 배정). 클릭/드래그로 배치, 한 유닛은 최대
  한 덱(재사용 금지 클라단 강제).
- **"빈 자리 최적화" 버튼**: 현재 초안을 `seeds`로 POST → 완성된 덱 렌더. 기존
  `RaidResults.tsx`를 재사용하되 `pinned_slugs`로 **유저 고정 vs 엔진 채움**을 시각
  구분(예: 고정은 테두리/배지).
- **검증 피드백**: 백엔드 422(불가능 초안)를 유저가 이해할 수 있는 문구로 표시.
- 기존 레이드 모드(zero-base)는 유지 — 시드가 비면 같은 화면이 그대로 동작.

### 초상화 — 소싱 발견 게이트

레포에 캐릭터 초상화가 없다(있는 이미지는 `capturedimages/` 스탯 캡처뿐). 따라서
초상화 작업의 **1단계는 소싱 발견**이다. 절대 URL을 지어내지 않는다.

1. slug로 안정적으로 매핑되는 초상화 소스가 실제로 있는지 검증한다. 후보:
   수집 파이프라인이 이미 받는 dotgg/lootandwaifus 데이터의 이미지 필드,
   또는 blablalink CDN(Phase B에서 스탯 테이블 소비에 이미 사용).
2. 있으면: 로컬에 내려받아 프론트에서 서빙한다(핫링크는 깨질 수 있어 지양).
   slug→파일 매핑을 커밋한다. 다운로드 스크립트에 이름·문서 부여.
3. 없으면: **이름+티어+클래스색 칩으로 폴백**하고 초상화는 별도 백로그로 남긴다.

이 게이트의 결과가 UI의 카드 표현을 정한다. 프론트 편성기 로직은 초상화 유무와
무관하게 동작하도록 설계한다(칩/초상화는 표현 레이어).

## 데이터 계약 요약

- `POST /api/recommend-raid` 요청에 `seeds: [{slugs: [...]}, ...]` 추가(옵셔널).
- 응답 `DeckRecommendation`에 `pinned_slugs: [...]` 추가.
- `GET /api/supported-units` → `[{slug, name, burst_tier, nikke_class, element}]`.
- 계약 상세는 `frontend/README.md`에 기록(프론트 병렬 착수의 단일 출처).

## 테스트

- 백엔드 프리미티브: 고정 유닛이 결과 덱에 항상 포함 / 순서가 교정됨
  (Modernia/Velvet 왼쪽 입력 → 오른쪽 착석) / 빈 자리가 전 티어에서 채워짐
  (B3 하나 고정 → 유효 shape 완성) / `seeds=[]`가 기존 결과와 비트 동일.
- 불가능 초안: B1 3명·전역 고갈·미지원 슬러그·중복 고정 각각 422 + 식별 메시지.
- API: `seeds` 왕복 + `pinned_slugs` 정확성 + `/api/supported-units` 스키마.
- 프론트: 팔레트 그룹핑 / 재사용 금지 / 고정·채움 구분 렌더 / 422 표시(Vitest).

## 병렬화 / 시퀀싱

세 조각으로 분해되며 옆 세션에 넘기기 좋다.

1. **초상화 소싱+다운로드** — 완전 독립. 즉시 병렬 착수 가능(발견 게이트부터).
2. **백엔드 시드 할당 + API** — 임계경로. 데이터 계약(`frontend/README.md`)을 정의.
3. **프론트 편성기 UI** — API 계약 초안이 나오면 mock 클라이언트로 병렬 착수 가능
   (프로젝트에 기존 mock 패턴 있음: `recommendRaidClient.mock.ts`).

## 열린 항목 / 후속

- `/api/supported-units`의 directory 스키마 → 정확한 name/class/element/burst_tier
  필드 매핑은 구현 계획에서 확정.
- 초상화 소싱 결과에 따라 카드 표현 확정.
- 성능: 시드가 탐색 공간을 줄이므로 zero-base보다 빠를 것으로 예상(측정으로 확인).
