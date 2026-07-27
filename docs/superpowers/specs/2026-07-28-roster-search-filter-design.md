# 니케 검색 · 정렬 · 필터 — 설계

- Date: 2026-07-28
- Status: 승인됨 (Fienn)
- 관련: `docs/roadmap.md`("UI 크롬 한글화 스펙 리뷰 중 나온 백로그 2건" 중
  첫 번째 항목 — "니케 검색/정렬/필터 기능")

## 배경

로스터가 커지면 유닛을 눈으로 훑어 찾게 된다. 실측 로스터는 보유 159기 ·
엔진 지원 70기 규모이고, 두 화면 모두 그 전량을 한 번에 그린다.

- **로스터 탭**(`RosterGrid`) — 지원 70기를 **평평한 카드 그리드** 하나로
  그린다. 그룹도, 검색도, 정렬도 없다. 미지원 89기는 접힌 `<details>`.
- **추천 탭**(`UnitPalette`) — 이미 B1/B2/B3 섹션으로 묶여 있지만, 섹션 안은
  `supportedUnits`가 오는 순서 그대로다. 검색·정렬·필터가 없다.

찾는 방식이 "스크롤하며 초상화 알아보기"뿐이라, 특정 유닛을 집으려면 70개
칩을 훑어야 하고 "우월코드 오버로드가 제일 높은 애가 누구지" 같은 질문에는
답할 방법이 아예 없다.

Fienn이 밝힌 용도는 두 가지다: **육성이 잘 된 유닛을 빨리 찾기**, 그리고
**필요한 유닛을 빨리 찾기**.

## 결정

### 1. 필터 축은 속성 · 버스트 단계 두 개뿐

Fienn 지정. 애장품 보유 여부와 돌파/코어 투자도는 후보에 올랐다가 제외됐다 —
둘 다 이미 타일 위에 배지로 보이고, 오버로드 정렬이 "육성이 잘 된 유닛 찾기"를
이미 충족한다.

속성 5종(작열·수냉·풍압·철갑·전격)과 버스트 3종(B1·B2·B3)은 각각 다중 선택이며,
**아무것도 안 고른 상태 = 전부 표시**다. "전체" 항목을 따로 두지 않는다.

### 2. 검색은 이름 부분일치만

Fienn 지정. 초성 검색(`ㅎㄹ` → `홍련`)은 자모 분해 유틸과 그 테스트가 따로
필요해 기각. 슬러그 검색(`red-hood`)도 기각 — 슬러그는 식별자지 유저가 읽는
이름이 아니다.

부분일치는 대소문자를 무시하고 앞뒤 공백을 버린다. 한글 조합 중인 입력
(`홍ㄹ`)은 단순 `includes`로도 자연스럽게 아무것도 안 맞다가 완성되면 맞는다 —
별도 처리 없음.

### 3. 정렬은 이름(가나다순) + 오버로드 옵션 7종, 양방향

Fienn 지정. 오버로드 정렬은 **옵션 종류를 하나 고른 뒤 그 값으로 줄 세우는**
방식이다(우코 · 공 · 장탄 · 차속 · 크댐 · 크확 · 차댐).

- 값은 blablalink가 이미 **4부위 합산**해서 주는 수치를 그대로 쓴다.
- 그 옵션을 안 굴린 유닛은 **0**으로 취급한다. 합산 기여가 실제로 0이므로
  사실 그대로이고, 내림차순에서는 자연히 뒤로, 오름차순에서는 앞으로 간다.
  "안 굴림"을 특별 취급해 항상 뒤로 보내는 안은 기각했다 — 오름차순의 용도가
  바로 "덜 키운 유닛 찾기"인데 그 답을 숨기게 된다.
- 동점은 **이름으로 깬다**. 그래야 같은 필터에서 두 번 렌더해도 순서가 같다.
- 옵션 이름의 축약(`우월코드 대미지 증가` → `우코`)은 기존
  `InvestmentSummary.abbreviateOverload`를 재사용한다. 라벨을 두 벌 만들면
  갈라진다.

### 4. 정렬을 걸어도 B1/B2/B3 그룹은 유지된다

Fienn 지정. 정렬은 **각 그룹 안에서만** 일어난다. 덱은 항상 버스트 단계별로
구성하므로 그룹이 사라지면 "이 정렬 결과로 덱을 짤 수 있나"를 읽을 수 없다.

같은 이유로 **로스터 탭에도 B1/B2/B3 분류를 새로 넣는다**(Fienn 요청). 두 화면이
같은 골격을 갖게 되어, 추천 탭에서 본 배치를 로스터 탭에서 다시 찾을 수 있다.

### 5. 필터는 시야만 바꾼다 — 탐색 풀은 건드리지 않는다

**이 스펙에서 가장 중요한 결정.** 추천 탭의 팔레트는 지금 *의도적으로* 전체
로스터를 그린다(`docs/insights.md`, "Client-side pool reduction" 항목): 제외된
유닛을 숨겨버리면 다시 포함시킬 컨트롤이 사라지기 때문이다.

필터는 유닛을 화면에서 숨기므로 같은 함정을 다시 열 수 있다. 그래서:

- 필터·검색·정렬은 `excludedSlugs`, `effectiveRoster`, `hashRecommendInputs`,
  `poolTotal`/`poolIncluded`, 요청 payload 중 **무엇도 바꾸지 않는다**.
- 필터로 숨겨진 유닛은 여전히 탐색 풀에 있다. 숨겨진 채 제외된 유닛도
  제외 상태를 그대로 유지한다.
- 숨김이 무언의 상태가 되지 않도록, 필터가 걸려 있으면 툴바가
  `70기 중 12기 표시 중`을 보여주고 **필터 해제** 버튼을 함께 낸다.
- `<summary>`의 `N/M 탐색 풀에 포함됨` 줄은 **전체 로스터 기준 그대로** 둔다.
  필터에 따라 이 숫자가 움직이면 "필터가 풀을 바꾼다"고 읽히기 때문이다.

이 불변식은 문서가 아니라 **회귀 테스트로 고정한다**: 필터를 건 뒤 제출하면
요청 roster가 필터 전과 동일해야 한다.

### 6. 엔진 미지원 목록에는 툴바가 걸리지 않는다

미지원 유닛은 `supportedUnits`에 없으므로 **속성도 버스트 단계도 알 수 없다**.
셋 중 검색만 적용하는 반쪽 동작은 "왜 속성 필터가 여기만 안 듣지"를 만든다.
접힌 `<details>` 목록을 지금 모양 그대로 전량 유지한다.

### 7. 상태는 컴포넌트가 소유한다 — 탭별 독립, 새로고침하면 초기화

Fienn 지정. `RosterGrid`와 `UnitPalette`가 각자 `useState`로 필터 상태를 갖는다.
localStorage 저장은 기각 — "저장된 필터 탓에 유닛이 사라진 것처럼 보이는"
사고가 가장 잦은 방식이다.

부수 결과 하나: 추천 탭의 모드 전환(단일/레이드 ↔ 드래프트)은 팔레트 인스턴스를
바꾸므로 **필터가 초기화된다**. 프롭 드릴링을 피한 대가이고, 모드 전환은 드물다.

### 8. 작열 속성색을 `#dd3333`으로

Fienn 지정 (rgb 221,51,51). 지금 `--el-fire: #f0603c`는 주황에 가까워 철갑
(`--el-iron: #f2b53b`, 금색)과 어두운 화면에서 헷갈린다.

이 토큰을 읽는 곳은 `.roster-card`의 `border-top`과 `.palette__item`의
`border-left` 둘뿐이므로, **토큰 한 줄 수정으로 양쪽이 함께 바뀐다**.

## 범위

### 포함

- `lib/unitFilter.ts` — 필터·정렬 순수 로직 + 상태 타입.
- `components/UnitFilterBar.tsx` — 두 탭이 공유하는 controlled 툴바.
- `RosterGrid` — B1/B2/B3 분할 + 툴바 배선.
- `UnitPalette` — 툴바 배선 (그룹은 이미 있음).
- `--el-fire` 토큰 변경.
- 위 전부의 테스트, 특히 5번의 payload 불변 회귀 테스트.

### 제외

- 초성 검색, 슬러그 검색.
- 애장품 · 돌파/코어 필터.
- 필터 상태 저장(localStorage / URL 쿼리).
- 미지원 유닛 목록의 검색·정렬·필터.
- 사이드바 탭 재구성(로드맵 백로그의 나머지 한 건, 별도 스펙).
- 결과 화면(`DeckResults`/`RaidResults`/`DraftResults`)과 드래프트 덱 슬롯 —
  거기는 이미 5기 이하라 찾을 게 없다.

## 구조

### `lib/unitFilter.ts`

```ts
export type OverloadKey = '우코' | '공' | '장탄' | '차속' | '크댐' | '크확' | '차댐'
export type SortKey = 'name' | OverloadKey

export interface UnitFilterState {
  /** 이름 부분일치. 빈 문자열 = 조건 없음. */
  query: string
  /** 빈 배열 = 전부 표시. */
  elements: NikkeElement[]
  /** 빈 배열 = 전부 표시. */
  burstTiers: BurstTier[]
  sortKey: SortKey
  sortDir: 'asc' | 'desc'
}

/** 기본 상태. 정렬 기본값이 '이름 · 오름차순'이라는 것은 곧 **필터를 아무것도
 *  안 걸어도 두 그리드가 가나다순으로 그려진다**는 뜻이다 — 지금의 "백엔드가
 *  준 순서"는 유저에게 아무 의미가 없으므로 의도한 변경이다. */
export const EMPTY_FILTER: UnitFilterState = {
  query: '',
  elements: [],
  burstTiers: [],
  sortKey: 'name',
  sortDir: 'asc',
}

/** 필터가 걸려 있는지 — 툴바의 "필터 해제" 노출과 "N기 중 M기" 표시를 가른다.
 *  정렬은 무엇도 숨기지 않으므로 여기 포함되지 않는다. */
export function isFiltering(state: UnitFilterState): boolean

/** 필터·정렬이 유닛에서 읽는 것 전부. 저장 모양(NikkeDraft의 문자열 값 /
 *  UserNikkeState의 숫자 값)이 뭐든 호출부가 이걸로 환원해 넘긴다. */
export interface UnitFacets {
  name: string
  element: NikkeElement
  burstTier: BurstTier
  overload: { name: string; value: number | string }[]
}

export function filterAndSort<T>(
  items: T[],
  facets: (item: T) => UnitFacets,
  state: UnitFilterState,
): T[]
```

`facets` 접근자를 받는 제네릭이라, 두 호출부가 자기 데이터 모양을 그대로 들고
있으면서 같은 규칙을 쓴다. 데이터 모양을 통일하는 리팩터는 지금 목표에 비해
과하다(YAGNI).

`BurstTier` 타입과 `BURST_TIERS` 상수는 `types/supportedUnit.ts`로 올려
`UnitPalette`의 지역 상수와 새 코드가 같은 것을 쓰게 한다.

### `components/UnitFilterBar.tsx`

Controlled. `value: UnitFilterState`, `onChange`, 그리고 표시 개수 두 개
(`shown`, `total`)를 받는다. 스스로는 상태를 갖지 않는다.

```
[ 이름 검색…            ]  정렬 [이름 ▾] [↓]
속성  작열 수냉 풍압 철갑 전격        ← 토글 칩, 다중 선택
단계  B1  B2  B3                      ← 토글 칩, 다중 선택
70기 중 12기 표시 중   [필터 해제]     ← isFiltering()일 때만
```

- 검색은 `<input type="search">`.
- 토글 칩은 `<button aria-pressed>` — 팔레트 초상화 토글이 이미 쓰는 패턴.
- 정렬 방향은 `aria-pressed` 토글 버튼 하나(내림/오름).
- 0건이면 그리드 자리에 "조건에 맞는 니케가 없어요."

### 배선

- `RosterGrid`: 지원 유닛을 `BURST_TIERS`로 분할 → 각 그룹에
  `filterAndSort` → `<h3>B1</h3>` + 카드 그리드. 빈 그룹은 그리지 않는다.
  미지원 `<details>`는 그대로.
- `UnitPalette`: 기존 그룹 루프 안에 `filterAndSort`를 끼우고 툴바를 위에 얹는다.

## 테스트

기준선: 프론트 **301 passed / 38 files** (2026-07-28 트렁크 `29c65ff`에서 실측).

- `lib/unitFilter.test.ts` — 빈 필터는 항등(순서 포함), 이름 부분일치(대소문자·
  공백), 속성/단계 다중 선택, 두 축의 교집합, 가나다 정렬, 오버로드 정렬
  내림/오름, 안 굴린 유닛 = 0, 동점의 이름 tie-break, `isFiltering`.
- `UnitFilterBar.test.tsx` — 칩 토글이 `onChange`를 올바른 상태로 부름, 필터
  없을 때 "필터 해제"가 없음, `isFiltering`일 때 개수 줄이 뜸, 해제 버튼이
  `EMPTY_FILTER`를 냄.
- `RosterGrid.test.tsx` (추가) — B1/B2/B3 헤딩이 뜸, 비어 있는 단계는 헤딩도
  없음, 속성 필터가 카드를 숨김, **미지원 목록은 필터와 무관하게 전량 유지**.
- `UnitPalette.test.tsx` (추가) — 필터가 칩을 숨김, 숨겨진 유닛의 제외 상태가
  보존됨(필터 해제하면 제외된 채로 다시 나타남), 0건 안내.
- `RecommendPanel.test.tsx` (추가) — **회귀**: 필터를 건 뒤 제출해도 요청
  payload의 roster가 필터 전과 동일하고, `N/M 탐색 풀에 포함됨` 숫자가
  안 움직인다.

작열 색상 변경은 토큰 한 줄이라 테스트 대상이 아니다 — Vitest는 `css: false`라
CSS 값을 못 읽는다(`docs/insights.md`). 실제 브라우저에서 눈으로 확인한다.

## 남은 확인 (구현 후, 사람이 한다)

- 툴바가 두 화면에서 세로 공간을 얼마나 먹는지. 추천 탭 팔레트는 이미
  `<details>` 안에 있어 여유가 적다. **재현 하네스가 아니라 실제 앱에서 잰다**
  (`docs/insights.md`의 788px vs 937px 사건).
- `#dd3333`이 어두운 표면에서 `--danger: #f87171`와 헷갈리지 않는지. 둘이
  나란히 놓이는 자리는 없지만 확인할 가치가 있다.
