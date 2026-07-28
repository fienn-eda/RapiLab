# RapiLab UI 개편 — 네이밍 정리와 제출 버튼 상시 노출

날짜: 2026-07-28

## 목적

두 가지를 고친다.

1. **네이밍**: 앱 이름을 RapiLab으로 세우고, 화면의 용어를 플레이어가 게임에서
   쓰는 말("재장전 큐브", "솔로 레이드", "니케 풀")로 맞춘다. 모드 이름은
   구현 방식("드래프트 기반 최적화")이 아니라 결과("빈자리만 최적화")로 부른다.
2. **제출 버튼 도달성**: 어떤 모드에서든 스크롤 위치와 무관하게 실행 버튼이
   화면에 남아 있게 한다. 지금은 팔레트 70여 개 칩을 지나 내려가면 버튼이
   화면 밖으로 사라진다.

## 범위 밖

- 백엔드/엔진: 손대지 않는다.
- 에러 문구 안의 "덱 추천"(`api/recommendApiError.ts`,
  `hooks/useAsyncRequestStatus.ts`): 앱 이름이 아니라 동작 설명이므로 유지.
- `lib/rosterImport.ts`의 `Resilience Cube`: blablalink API가 주는 데이터
  값이지 화면 문구가 아니다. 유지.
- 취소 버튼의 백엔드 중단 경로: 이미 구현돼 있고 이번 작업과 무관.

## 1. 텍스트 변경

| 파일 | 현재 | 변경 후 |
|---|---|---|
| `frontend/index.html` `<title>` | `NIKKE Deck Builder` | `RapiLab` |
| `App.tsx` `.app__title` | `NIKKE 덱 빌더` | `RapiLab` |
| `App.tsx` `.app__note` | `모든 니케가 Resilience 큐브 Lv.15를 착용한 것으로 계산합니다.` | `모든 니케가 재장전 큐브 15레벨을 착용한 것으로 계산합니다.` |
| `App.tsx` `TABS` | `로스터` | `니케 풀` |
| `App.tsx` `TABS` | `추천` | `솔로 레이드` |
| `RecommendPanel.tsx` `aria-label` / `.card__title` | `덱 추천` | `솔로 레이드` |

`TABS`의 `id`(`'roster' | 'recommend' | 'union'`)와 `panel-*`/`tab-*` DOM id는
바꾸지 않는다. 라벨만 바뀌며, 탭 id는 패널을 가리키는 내부 키다.

### 모드 이름과 힌트

`RecommendPanel`의 `RecommendMode` 유니온 값(`'single' | 'raid' | 'draft' |
'evaluate'`)은 그대로 둔다 — `StoredInputs.mode`로 프로필에 저장돼 있어서
바꾸면 기존 사용자의 저장된 결과가 복원되지 않는다. 화면 라벨만 바꾼다.

| 모드 | 이름 | 힌트 |
|---|---|---|
| `single` | 단일 덱 | 기대 딜량이 높은 개별 덱을 찾아줘요 |
| `raid` | 전부 최적화 | 설정한 덱 개수만큼 최적화해요 |
| `draft` | 빈자리만 최적화 | 직접 편성한 니케들을 기반으로 나머지 자리를 최적화해요 |
| `evaluate` | 기대 딜량 계산 | 직접 짠 덱의 기대 딜량만 빠르게 계산해요, 최적화는 하지 않아요 |

`evaluate`의 힌트는 현행 유지다.

### 제출 버튼 라벨

유휴 상태는 네 모드와 유니온 레이드 모두 **`인카운터!`** 하나로 통일한다.

실행 중 라벨은 모드별로 유지한다(`추천 중…` / `배분 중…` / `최적화 중…` /
`계산 중…`). 버튼이 진행 상태를 알려주는 유일한 자리이므로, 실행 중에도
`인카운터!`로 두면 눌렸는지 알 수 없다.

`submitLabel`은 지금 4중 삼항으로 유휴/실행 두 축을 한꺼번에 표현한다. 유휴가
한 문자열로 합쳐지므로 `active.status === 'loading' ? <모드별 진행 라벨> :
'인카운터!'` 형태로 납작해진다.

### 진행 안내 문구

`recommend-form__progress`의 모드 이름도 새 이름을 따른다.

- `레이드 덱 배분 중` → `전부 최적화 중`
- `드래프트 최적화 중` → `빈자리만 최적화 중`

## 2. 제출 버튼 배치

`.recommend-form__actions` 블록(제출 버튼 + 실행 중에만 나타나는 취소 버튼 +
`rosterTooSmall` 경고)을 모드에 따라 두 자리 중 하나에 놓는다. 블록 자체는
`RecommendPanel` 안에서 JSX 변수로 한 번만 정의해 중복을 만들지 않는다.

### 솔로 레이드 탭 — `single` / `raid`

우측에 덱 컬럼이 없는 모드다. 액션 블록을 `<form>`의 마지막 자식으로 옮기고
화면 하단에 고정한다.

```css
.recommend-form__actions--sticky {
  position: sticky;
  bottom: 0;
  width: 100%;
}
```

`.recommend-form`이 `align-items: flex-start`라 `width: 100%`가 없으면 바가
내용 폭으로 줄어 배경이 카드를 가로지르지 못한다. 아래 콘텐츠가 비쳐 보이지
않도록 배경색·상단 보더·좌우 음의 여백(카드 패딩만큼 넓혀 카드 폭을 채움)을
준다. 팔레트의 오버로드 팝오버보다 위에 오도록 `z-index`를 맞춘다.

sticky를 깨는 `overflow` 조상은 없다(`overflow-y: auto`는 `.sync-help`뿐).

### 솔로 레이드 탭 — `draft` / `evaluate`

같은 액션 블록을 `.draft-layout__decks` 안, `DraftEditor` 아래에 렌더한다.
이 컬럼은 이미 `position: sticky; top: var(--sp-4)`이므로 덱1~5와 함께 따라
붙는다. 추가 CSS가 필요 없다.

### 유니온 레이드 탭

`UnionRaidPanel`의 액션 블록을 `.draft-layout__decks` 안 `DraftEditor` 아래로
옮긴다. 여기엔 취소 버튼도 `rosterTooSmall` 경고도 없으므로
`RecommendPanel`과 공유할 컴포넌트를 만들지 않는다 — 두 곳의 내용물이 다르고,
공유하면 조건부 props만 늘어난다.

## 알려진 제약

1. **하단 고정 바는 `<form>` 안에서만 붙는다.** 결과 컴포넌트
   (`DeckResults`/`RaidResults`)는 폼 바깥, `<section class="card">`의 형제로
   렌더된다. 결과를 읽으며 스크롤하면 바는 사라진다. 결과를 보는 중에는 재실행
   버튼이 필요하지 않다고 보고 이 범위로 둔다.
2. **모바일(≤900px)에서는 덱 컬럼 sticky가 꺼져 있다**(`App.css`의 미디어
   쿼리). `draft`/`evaluate`/유니온의 버튼은 그 폭에서 덱 아래로 그냥 흐른다.
   하단 고정 바(`single`/`raid`)는 폭과 무관하게 동작한다.

## 테스트

기존 프론트 테스트가 바뀌는 문자열을 상당수 물고 있다(`RecommendPanel.test.tsx`
가 가장 많고, `App.test.tsx`가 그다음). 이들은 새 라벨로 갱신한다 — 커버리지를
줄이지 않고 같은 것을 새 이름으로 확인한다.

새로 추가하는 검증:

- `single`/`raid` 모드에서 액션 블록이 `--sticky` 배치로 렌더되고,
  `draft`/`evaluate`에서는 덱 컬럼(`.draft-layout__decks`) 안에 있을 것.
- 유니온 레이드의 제출 버튼이 덱 컬럼 안에 있을 것.
- 모드를 바꾸면 버튼 라벨이 `인카운터!`로 유지되고, 실행 중에만 모드별
  진행 라벨로 바뀔 것.

두 탭 패널이 동시에 마운트돼 있으므로 DOM 조회는 패널 단위로 스코프한다.
