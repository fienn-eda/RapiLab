# 결과 화면 정리와 결과 보관 — 설계

날짜: 2026-08-06 · 상태: 승인됨 (Fienn)

Fienn이 다섯 가지를 요청했다. 앞의 넷은 화면을 읽기 쉽게 만드는 작은 변경이고,
다섯째(결과 보관)가 이 문서 분량의 절반을 차지한다.

1. 솔로 레이드 보스 방어력 기본값을 31784로
2. 방어력·전투 시간을 폼에서 숨김 — 거의 바꿀 일이 없는 값이다
3. 결과 덱 카드가 창 폭만큼 넓어진다. 좁히고, 한 행에 여러 덱을 놓는다
4. 결과에 그 결과가 어떤 보스를 상대로 나온 것인지 함께 표시
5. 결과를 이름 붙여 보관. 솔로와 유니온의 보관물은 섞이지 않는다

---

## 1. 솔로 보스 방어력 기본값

`makeDefaultBossProfileDraft()`는 솔로 탭(`RecommendPanel`)과 유니온 탭
(`UnionRaidPanel`)이 공유한다. 유니온 보스의 방어력은 솔로와 다른 값이라,
공유 기본값을 31784로 바꾸면 유니온 쪽이 조용히 틀린 숫자로 계산된다.

**결정**: 기본 방어력을 선택 인자로 받는다. 인자가 없으면 지금과 같은 `'0'`.

```ts
export const makeDefaultBossProfileDraft = (enemyDef = '0'): BossProfileDraft => ({ … })
```

솔로 탭만 상수를 넘긴다. 상수는 `RecommendPanel`이 소유하고, 어디서 온 숫자인지를
주석으로 남긴다. 유니온용 값을 알게 되면 같은 자리에 한 줄 더 놓으면 된다.

`resizeDraft`가 유니온에서 새 전투를 append할 때 부르는 무인자 호출은 그대로
`'0'`을 받는다 — 유니온의 기본값이 바뀌지 않는다는 뜻이고, 의도한 바다.

## 2. "기타 설정" 접이식

`BossProfileField` 맨 아래의 방어력·전투 시간 두 `NumberField`를 `<details>`로 감싼다.
`<summary>`는 라벨과 **현재 값 요약**을 함께 낸다:

> ▸ 기타 설정 — 방어력 31,784 · 180초

접힌 채로도 무슨 값으로 계산되는지 보이게 하려는 것이다. 값이 바뀌면 요약도 바뀐다.

**열림 조건**: `errors.enemy_def`나 `errors.fight_duration`이 있으면 `open`을 강제한다.
접힌 상자 안에 제출을 막는 오류가 숨는 상태를 만들지 않는다. `open` 속성을 제어값으로
쓰지 않고 `open={hasError || undefined}`처럼 "오류가 있을 때만 참"으로 두면, 유저가
직접 펼친 상태는 유저가 계속 쥔다.

이 변경은 두 탭에 동시에 적용된다 — 같은 컴포넌트다. 유니온에서도 이 두 값은
거의 손대지 않으므로 그대로 두는 것이 맞다.

## 3. 결과 카드 다열 그리드

원인은 한 줄이다. `.deck-results`가 `flex-direction: column`이고, 부모
(`.app__main > .card`)가 `width: 100%`, `.app`이 창 폭을 그대로 쓴다. 그래서 덱
카드 하나가 창 폭 전부를 먹고, 얼굴 5개(64px씩 ≈ 370px)만 채운 뒤 오른쪽은 빈다.

**변경**:

```css
.deck-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--sp-3);
}
```

340px은 얼굴 5개가 한 줄에 들어가는 최소 폭이다. 창이 좁으면 `auto-fill`이 1열로
되돌린다 — 별도 미디어 쿼리가 필요 없다.

`DeckResults` · `RaidResults` · `DraftResults` · `EvaluationResults`가 모두 이 클래스를
쓰므로 한 곳만 고치면 네 화면이 같이 바뀐다. `DraftResults`가 카드 밑에 붙이는
diff 줄(`+/-`)은 카드 안에 있으므로 함께 따라간다.

## 4. 결과에 보스 설정 표시

새 컴포넌트 `BossSummary`. `BossProfile` 하나를 받아 한 줄의 배지로 그린다:

> 약점 화염 · 원거리(SR) · 코어 피격 · 2관통 · 부위파괴 · 속성저지 필수 · 방어력 31,784 · 180초

- 약점 속성은 항상(없으면 "약점 없음"), 적정거리는 설정됐을 때만
- 기믹 넷은 **켜진 것만** 나온다. 꺼진 기믹을 "부위파괴 없음"처럼 쓰면 줄이 길어지기만 한다
- 방어력·전투 시간은 폼에서 숨겼기 때문에 여기 남는다. 숨긴 값일수록 결과에
  적혀 있어야 나중에 이 결과가 무슨 조건이었는지 알 수 있다
- 속성 이름은 기존 `bossElementLabel`과 같은 규칙을 쓴다: 화면은 보스 본인 속성이
  아니라 **약점**으로 말한다

**배치**:

- **솔로**: 결과 목록 바로 위에 한 줄. 네 모드가 각자의 제출 시점 스냅샷을 쓴다 —
  `single` → `singleBoss`, `raid`/`draft` → `displayBoss`, `evaluate` → `evaluateBoss`.
  라이브 폼 상태(`draft`)를 읽으면 안 된다. 결과가 나온 뒤 폼을 만지면 숫자는 옛
  보스인데 설명만 새 보스가 되어 거짓말을 한다. 이 세 스냅샷은 이미 있고,
  gimmick 배지가 이미 같은 이유로 그것들을 쓰고 있다.
- **유니온**: 각 덱 카드 안. 전투마다 보스가 다르므로 카드 밖에 몰아 쓸 수 없다.

**타입 변경**: `EvaluationResults`의 `bossElements: BossElement[]`를
`bosses: BossProfile[]`로 넓힌다. 라벨에 쓰던 element는 `bosses[i].element`로 얻는다.
`DeckCard`에는 `boss?: BossProfile`를 추가하고, 넘어왔을 때만 카드 안에 `BossSummary`를
그린다. 솔로의 evaluate 모드는 지금 `evaluation.decks.map(() => evaluateBoss)`로
같은 보스를 복제해 넘기고 있는데, 그 자리에는 `bosses`만 넘기고 `DeckCard`에는
넘기지 않는다 — 솔로는 상단 한 줄로 이미 말했다.

## 5. 결과 보관

### 저장 위치

`Profile`에 필드 하나를 더한다.

```ts
export interface SavedRun {
  id: string            // `${savedAt}-${같은 ms의 순번}` — 아래 참조
  name: string          // 유저가 붙인 이름
  savedAt: number       // epoch ms
  tab: 'solo' | 'union' // 두 탭을 섞이지 않게 하는 것은 이 필드 하나다
  view: SoloRunView | UnionRunView
}

export interface Profile {
  …
  savedRuns: SavedRun[]
}
```

프로필 안에 두는 이유: 결과는 그 로스터에 대한 답이라, 계정·서버가 다르면 의미가
다르다. 프로필별 분리는 저장소가 이미 하고 있는 일이고, 프로필을 지우면 그 보관물도
함께 사라지는 것이 옳다.

**`results` 캐시와 다른 점**: `upsertProfile`은 로스터가 바뀌면 `results`를 비운다
(그 캐시는 "다시 계산할 필요 없다"는 주장이므로 로스터가 바뀌면 거짓이 된다).
`savedRuns`는 **비우지 않는다**. 유저가 이름을 붙여 명시적으로 보관한 것을 말없이
지우는 저장소는 신뢰할 수 없다. 보관물은 "그때 그 로스터로 나온 답"이라는 기록이지
현재 로스터에 대한 주장이 아니다.

기존 프로필에는 이 필드가 없다. **`migrate`에서 채운다** — 그 함수는 이미 프로필을
항목 단위로 돌며 `area`를 채우고 있고, 거기서 `savedRuns: profile.savedRuns ?? []`를
같이 채우면 그 뒤의 코드는 이 필드를 옵셔널로 다루지 않아도 된다. `Profile` 타입에서는
필수 필드다. 읽는 곳마다 `?? []`를 흩뿌리면 한 곳을 빠뜨렸을 때만 터진다.

**id 생성**: `${savedAt}-${그 ms에 이미 있는 개수}`. `crypto.randomUUID()`는 이
프로젝트의 jsdom 테스트 환경에서 있다고 확신할 수 없고, 확인하러 가는 값어치가 없다.
이 규칙은 결정적이라 테스트가 id를 예측할 수 있다는 이점도 있다.

### 저장하는 것

그릴 수 있어야 하고, 폼을 되돌릴 수 있어야 한다. 로스터 자체는 담지 않는다 —
결과에 나오는 슬러그는 결과 안에 있고, 이름·초상화는 전역 조회다.

```ts
interface SoloRunBase {
  boss: BossProfile
  numDecks: number
  excludedSlugs: string[]
}

type SoloRunView =
  | (SoloRunBase & { mode: 'single'; decks: DeckRecommendation[] })
  | (SoloRunBase & {
      mode: 'raid'
      decks: RaidDeck[]
      combinedTotalDamage: number
      leftoverSlugs: string[]
      swapConverged?: boolean
    })
  | (SoloRunBase & {
      mode: 'draft'
      decks: RaidDeck[]
      combinedTotalDamage: number
      leftoverSlugs: string[]
      withinDraft: DraftAllocation | null
      baselineTotalDamage: number | null
      swapConverged?: boolean
      draft: Draft | null
    })
  | (SoloRunBase & {
      mode: 'evaluate'
      decks: DeckRecommendation[]
      combinedTotalDamage: number
      draft: Draft
    })

interface UnionRunView {
  numBattles: number
  bosses: BossProfile[]
  draft: Draft
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  excludedSlugs: string[]
}
```

`SoloRunView`는 `mode`로 갈리는 판별 유니온이다. 넷을 한 타입으로 합치는 쪽이
처음에는 단순해 보이지만 **타입이 통과하지 않는다**: `RaidDeck`은
`DeckRecommendation`에 `pinned_slugs: string[]`를 **필수로** 더한 것이고,
`DraftResults`는 `decks: RaidDeck[]`를 요구한다. 합집합 하나로 두면 `decks`가
넓은 쪽(`DeckRecommendation[]`)이 되어 `DraftResults`에 넘길 수 없다.

쪼갠 값은 그 이상이다. 렌더 쪽은 어차피 `mode`로 네 갈래로 갈리고 있으므로,
판별 유니온은 그 분기 안에서 필드를 좁혀 준다 — `single`에는 존재하지도 않는
`withinDraft`를 `null`로 채워 넣을 일이 없어진다.

### UI

**저장**: 버튼은 결과 맨 위 줄의 오른쪽 끝에 놓는다. 솔로는 ④에서 새로 생기는
`BossSummary` 줄이 그 자리고, 유니온은 `총합: …` 줄(`evaluation-results__combined`)이다.
둘 다 결과 블록의 첫 줄이라 "이 결과를 저장한다"가 무엇을 가리키는지 분명하다.

누르면 이름 입력 줄이 열린다. 기본값은 `화염 · 전부 최적화 · 08-06`처럼
`약점 · 모드 이름 · MM-DD`이고(유니온은 `유니온 · 08-06`), 그대로 확인해도 되고
고쳐도 된다. 이미 저장된 결과를 다시 저장하는 것은 막지 않는다 — 같은 조건을 다른
이름으로 남기고 싶을 수 있다.

**목록**: 결과 아래에 접이식 `저장한 결과 (N)` 섹션. 각 탭은 자기 `tab` 값만 필터해
보여준다. 이것이 "솔로와 유니온이 섞이지 않는다"의 전부다.

**열기**: 항목을 클릭하면 그 자리에서 아코디언처럼 펼쳐져 **읽기 모드**로 결과를
그린다. 지금 화면에 떠 있는 계산 결과는 건드리지 않는다. 펼친 항목 위 배너에:

- `이 설정으로 폼 채우기` — 여기서 비로소 폼이 바뀐다. 보스 설정·모드·덱 수·편성을
  저장 당시로 되돌린다. 결과는 되돌리지 않는다(폼을 채운 뒤 다시 돌리는 것이 목적이다)
- `이름 바꾸기`
- `삭제` — 확인 후

**상한**: 프로필당 50개. 넘으면 저장을 **거부하고 안내**한다. `results` 캐시는
오래된 것을 조용히 밀어내지만(재계산하면 그만이다), 보관물은 그러면 안 된다.

### 순수 함수

`types/profile.ts`에 `results` 캐시와 같은 자리에 둔다.

```ts
export const SAVED_RUNS_CAP = 50
export const saveRun    = (state, key, run: SavedRun): ProfilesState
export const renameRun  = (state, key, id: string, name: string): ProfilesState
export const deleteRun  = (state, key, id: string): ProfilesState
export const runsForTab = (profile: Profile, tab: 'solo' | 'union'): SavedRun[]
```

`saveRun`은 상한을 넘으면 **상태를 그대로 돌려준다**. 호출부가 거부를 감지할 수
있도록 훅 쪽에서 `boolean`을 반환한다.

---

## 테스트

- `bossProfileDraft`: 인자 없는 기본값이 여전히 `'0'`, 인자를 준 기본값이 그 값
- `BossProfileField`: 기타 설정이 기본으로 접혀 있음 / 오류가 있으면 펼쳐짐 /
  요약에 현재 값이 보임
- `BossSummary`: 꺼진 기믹이 안 나옴 · 약점 없음 · 적정거리 없음 각각
- `EvaluationResults` · `DeckCard`: 유니온에서 카드마다 보스가 나옴,
  솔로에서는 안 나옴
- `profile.ts`: `saveRun`/`renameRun`/`deleteRun`/`runsForTab`, 상한 거부,
  **로스터 변경이 `savedRuns`를 지우지 않음**(이것이 핵심 회귀 테스트다)
- `SavedRunList`: 탭 필터가 다른 탭 항목을 안 보여줌, 펼치기, 폼 채우기 콜백
- `RecommendPanel` / `UnionRaidPanel`: 저장 → 목록에 나타남 → 열기 → 폼 채우기

CSS는 Vitest가 `css: false`라 단위 테스트로 검증할 수 없다(`docs/insights.md`).
③의 그리드는 앱을 띄워 눈으로 확인한다.

기준선은 이 작업을 시작한 시점의 프론트엔드 **54파일 524 테스트 통과**다.
백엔드는 이번 변경이 닿지 않는다.

## 하지 않는 것

- 파일 내보내기(JSON/이미지) — 요청 범위 밖이다
- 자동 히스토리 — 유저가 고른 것만 남는다
- 보관물끼리의 비교 화면 — 필요해지면 그때
- 유니온 결과의 해시 캐시 — 유니온은 수 초면 끝나므로 캐시할 이유가 없고,
  이번 변경도 그 판단을 바꾸지 않는다
