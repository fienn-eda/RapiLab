# 덱 편성 조작 2차 — 설계

날짜: 2026-08-11 · Fienn의 사용 보고 5건

## 무엇을 고치나

Fienn이 앱을 쓰면서 적어 준 다섯 가지다. 넷은 조작(표적이 좁거나 없다), 하나는
버그다.

1. 팔레트로 덱을 채울 때 활성 덱이 자동으로 넘어가지 않는다 — 15명을 누르면
   덱 3개가 차야 하는데, 5명째 이후로는 조용히 아무 일도 안 일어난다.
2. 든 니케를 다른 덱으로 옮길 때 **가장 왼쪽 빈자리 하나만** 눌리고, 그 표적은
   `+` 글자 크기다.
3. 활성 덱을 고르는 표적이 덱 **이름 글자**뿐이다.
4. 이름 검색이 한글 완성형 부분일치뿐이다 — 초성도 영문도 안 된다.
5. 미란다 계산기에서 앉은 니케를 누른 뒤 팔레트 니케를 눌러도 교환이 안 된다.

## 진단

### 5번은 배선 누락이다

`MirandaCalculatorPanel`이 `DraftEditor`에 `onHeldSlugChange`를 안 넘긴다. 그래서
좌석을 눌러 「들어도」 패널은 그 사실을 모르고, 팔레트 클릭은 그냥
`placeUnit(current, 0, slug)`을 부른다. 덱은 이미 5/5라 `placeUnit`이 no-op으로
거절하고, 화면에는 아무 표시도 남지 않는다.

솔로 탭(`RecommendPanel`)과 유니온 탭(`UnionRaidPanel`)에는 이 배선과 `replaceUnit`
분기가 둘 다 있다. 미란다 패널만 빠졌다.

### 2·3번은 같은 원인이다 — 표적이 컨트롤 글리프뿐

`DraftEditor`에서 덱을 향한 클릭을 받는 곳이 두 군데뿐이다: 덱 제목의 텍스트
버튼(활성 덱 선택)과, 든 것이 있을 때만 버튼이 되는 **첫 번째** 빈자리의 `+`
글자. 덱 테두리 안의 나머지 면적은 전부 죽어 있다.

첫 빈자리만 버튼인 것은 접근성 결정이었다 — 다섯 개를 다 노출하면 스크린리더가
덱마다 "+"를 다섯 번 읽는다. 그 결정은 유효하고, 이 설계는 그걸 유지한다.

### 4번은 2026-07-28 스펙이 명시적으로 기각한 것이다

`docs/superpowers/specs/2026-07-28-roster-search-filter-design.md` §2, "Fienn 지정":
초성 검색은 「자모 분해 유틸과 그 테스트가 따로 필요해」 기각, 슬러그 검색은
「슬러그는 식별자지 유저가 읽는 이름이 아니다」로 기각. **이 설계는 그 결정을
뒤집는다** (Fienn, 2026-08-11).

뒤집는 근거: 슬러그가 곧 케밥케이스 영문명이라는 것이 이미 백엔드 테스트로
고정돼 있다. `backend/tests/test_resource_id_directory.py:61-78`이
`_normalise(slug) != _normalise(name_en)`이면 스위트를 빨갛게 만든다(예외는
콜라보 약칭 7건). 즉 「슬러그는 이름이 아니다」는 식별자로서는 맞지만, 검색
건초더미로서는 영문명과 같은 문자열이다. 백엔드에 `name_en`을 새로 내보낼
필요가 없다.

## 설계

### A. `firstDeckWithRoom` — 팔레트가 향하는 덱 (1번)

`frontend/src/types/draft.ts`에 순수 함수 하나를 새로 만든다.

```ts
/** `from`부터 앞으로, 끝까지 가면 처음으로 되돌아 훑어 빈자리가 있는 첫 덱.
 * 전부 찼으면 null. `numDecks` 밖은 보지 않고, decks 배열에 아직 없는 자리는
 * 건너뛴다 - 없는 덱에 앉히면 placeUnit이 조용히 거절해서, 활성 덱만 옮기고
 * 아무도 안 앉는 상태가 된다. */
export const firstDeckWithRoom = (
  draft: Draft, from: number, numDecks: number,
): number | null
```

두 패널(`RecommendPanel`, `UnionRaidPanel`)의 `onSeat`이 이걸 **두 번** 쓴다.

```ts
onSeat={(slug) => {
  if (heldSlug) { /* 기존 replaceUnit 분기 그대로 */ }
  const target = firstDeckWithRoom(draftValue, seatDeck, numDecks)
  if (target === null) return
  const next = placeUnit(draftValue, target, slug)
  setDraftValue(next)
  setActiveDeck(firstDeckWithRoom(next, target, numDecks) ?? target)
}}
```

- **어디에 앉나** — 활성 덱에 자리가 있으면 거기, 없으면 다음 빈 덱. 이것 하나로
  「꽉 찬 덱을 직접 골라 두고 팔레트를 눌렀는데 조용히 아무 일도 안 남」이
  같이 풀린다.
- **활성 표시는 어디로** — 앉힌 **직후** 상태로 다시 훑는다. 그래서 5명째가
  덱 1을 채우는 순간 테두리가 덱 2로 옮겨가, 다음 클릭이 어디로 갈지 눈에
  보인다. 여섯 번째 클릭을 기다리지 않는다.

`setState` 갱신자 안에서 `setActiveDeck`을 부르지 않는다 — 갱신자는 순수해야
하고 StrictMode가 두 번 부른다. 클릭 하나는 한 번의 배치라 클로저의
`draftValue`를 그대로 읽는 것이 옳다.

드래그 드롭과 `+` 버튼 경로는 건드리지 않는다. 그쪽은 유저가 덱을 **명시적으로**
지목한 것이라 활성 덱 개념이 끼어들 자리가 없다.

### B. 덱 몸통이 표적이다 (2번 + 3번)

`.draft-editor__deck` div에 껍데기 `onClick`을 단다.

```ts
onClick={() => {
  if (heldSlug !== null) {
    const next = moveUnit(value, deckIndex, heldSlug)
    // moveUnit은 꽉 찬 덱과 「이미 그 덱」을 거절하며 같은 객체를 돌려준다.
    // 거절당했는데 든 것을 내려놓으면 유닛이 조용히 사라진 것처럼 보인다.
    if (next === value) return
    onChange(next)
    setHeld(null)
    onActiveDeckChange?.(deckIndex)
    return
  }
  if (picksDeck) onActiveDeckChange(deckIndex)
}}
```

**든 것이 있으면 이동, 없으면 선택.** 이동한 덱은 활성 덱이 된다(Fienn 지정) —
방금 만진 덱이 다음 팔레트 클릭도 받는다.

껍데기는 덱 테두리 안 전체를 덮으므로, **안쪽 컨트롤은 전부
`stopPropagation`**해야 한다. 안 그러면 두 번 처리된다 — 특히 좌석 버튼은
자기 핸들러에서 `setHeld(null)`을 부르지만 껍데기가 읽는 `heldSlug`는 같은 배치
안이라 아직 옛 값이라서, 교환하고 나서 또 이동하려 든다.

- `draft-editor__slot-grip` (좌석 집기/제거/교환)
- `draft-editor__slot-lock` (잠금 토글)
- `draft-editor__deck-pick` (덱 이름 토글)
- `draft-editor__slot-plus` (첫 빈자리 `+`)

`+` 버튼은 지금 하는 일을 그대로 한다. 껍데기와 같은 동작이지만 남긴다 —
그것이 **키보드로 닿는 유일한 놓기 경로**이고, 접근성 트리 노출을 덱마다
하나로 한정한 기존 결정이 거기 걸려 있다.

**껍데기는 접근성 트리에 넣지 않는다.** `role="button"`도 `tabIndex`도 안 붙인다:
덱 div는 다른 버튼들을 품고 있어서, 탭 정지점이 되면 안쪽 버튼들과 겹쳐 오히려
나빠진다. 껍데기가 주는 두 동작(선택·놓기)은 각각 진짜 버튼이 이미 갖고 있다 —
껍데기는 마우스 편의일 뿐이다.

고정 좌석(미란다)은 `<div>`라 클릭이 껍데기로 올라간다. 미란다 화면은 덱이
하나뿐이라 `moveUnit`이 같은 덱으로 거절 → 아무 일도 안 일어난다. 안전하다.

CSS는 누를 수 있을 때만 `cursor: pointer`를 준다. Vitest는 `css: false`라 이건
테스트가 못 재므로, 앱을 띄워서 눈으로 확인한다.

### C. 초성 + 영문 검색 (4번)

새 파일 `frontend/src/lib/koreanSearch.ts`:

```ts
/** 문자열에서 한글 음절의 초성만 뽑아 잇는다. 음절이 아닌 글자(공백·`:`·
 * 괄호·영숫자)는 버린다 - "홍련: 흑영"이 "ㅎㄹㅎㅇ"가 되어야 "ㅎㄹ"로도
 * "ㅎㄹㅎㅇ"로도 맞는다. */
export const toChosung = (text: string): string

/** 질의가 초성만으로 이뤄졌는가. 완성형이 섞이면("홍ㄹ") 초성 대조는 틀린
 * 답을 내므로 그때는 쓰지 않는다. */
export const isChosungQuery = (text: string): boolean
```

`lib/unitFilter.ts`의 이름 대조가 세 갈래가 된다:

```ts
// 1. 지금 그대로 - 한글 완성형 부분일치
if (facets.name.toLowerCase().includes(query)) return true
// 2. 영문: 슬러그가 곧 케밥케이스 영문명이다. 비영숫자를 지워 대조하므로
//    "ada wong"과 "ada-wong"이 같은 것을 가리킨다.
//    q !== '' 가드가 필수다: 한글 질의는 영숫자만 남기면 빈 문자열이 되고,
//    빈 문자열은 모든 슬러그에 includes로 맞아 전부 통과시킨다.
const q = alphanumericOnly(query)
if (q !== '' && alphanumericOnly(facets.slug).includes(q)) return true
// 3. 초성
if (isChosungQuery(query) && toChosung(facets.name).includes(query)) return true
```

`UnitFacets`에 `slug: string`이 는다. 두 호출부(`UnitPalette`, `RosterGrid`)가
이미 슬러그를 쥐고 있으므로 한 줄씩이다.

검색 입력의 placeholder를 「니케 이름」에서 초성·영문도 된다고 말하도록 고친다 —
안 적으면 아무도 안 쓴다.

**알면서 받아들이는 한계**: 콜라보 7종은 슬러그가 풀네임이라 ShiftyPad 약칭
(`Ada`)으로는 안 맞고 `ada wong`으로 맞는다. 엔진이 만든 접미사
(`-signature`·`-lingering`)는 영문이 아니지만 `bready`로 치면 어차피 걸린다.
둘 다 백엔드가 `name_en`을 내보내야 풀리는데, 그 값어치가 아직 없다.

### D. 미란다 교환 (5번)

솔로·유니온 패널과 똑같은 모양을 넣는다: `heldSlug` 상태, `onSeat`의
`replaceUnit` 분기, `DraftEditor`에 `onHeldSlugChange={setHeldSlug}`.
덱이 하나라 `firstDeckWithRoom`은 쓰지 않는다.

## 검증

TDD로 간다. 각 항목마다 「구현을 어떻게 망가뜨리면 이게 빨개지나」에 답이 있다.

**`types/draft.test.ts` — `firstDeckWithRoom`**
- 활성 덱에 자리가 있으면 그 덱 / 꽉 차면 다음 덱 / 뒤가 다 차면 앞으로 되돌아감
- 전부 차면 null · `numDecks` 밖은 안 본다 · decks 배열에 없는 자리는 건너뛴다

**`DraftEditor.test.tsx` — 껍데기**
- 몸통을 누르면 활성 덱이 바뀐다(아무것도 안 들었을 때)
- 들고 다른 덱의 **두 번째** 빈자리를 눌러도 옮긴다 ← 2번의 회귀 테스트
- 들고 몸통을 눌러 옮기면 그 덱이 활성 덱이 된다
- **꽉 찬 덱 몸통을 누르면 계속 들고 있다** — `onChange`도 `onHeldSlugChange(null)`도
  안 온다 ← `next === value` 가드를 떼면 빨개진다
- 좌석/잠금/덱이름/`+`를 눌렀을 때 껍데기가 겹쳐 처리하지 않는다 —
  `stopPropagation`을 하나씩 떼면 하나씩 빨개진다
- 덱이 하나면 몸통 클릭이 `onActiveDeckChange`를 안 부른다

**`koreanSearch.test.ts`**
- `toChosung`: 홍련→ㅎㄹ · 된소리(빨강→ㅃㄱ) · 겹받침이 초성을 안 흐린다 ·
  비한글 제거("홍련: 흑영"→ㅎㄹㅎㅇ) · 빈 문자열
- `isChosungQuery`: `ㅎㄹ` true · `홍ㄹ` false · `crown` false · 빈 문자열 false

**`unitFilter.test.ts`**
- `ㅎㄹ`→홍련 · `crown`→크라운 · `ada wong`→`ada-wong` · 대소문자 무시
- **회귀: 초성 질의가 슬러그 분기로 새어 전부 통과하지 않는다** ← `q !== ''`
  가드를 떼면 빨개진다
- 기존 완성형 부분일치가 그대로다

**`RecommendPanel.test.tsx` · `UnionRaidPanel.test.tsx`**
- 팔레트를 다섯 번 눌러 덱 1을 채우면 여섯 번째는 덱 2에 앉는다
- 다섯 번째 직후 활성 표시가 이미 덱 2다 ← 「채워진 뒤 다시 훑기」를 빼면 빨개진다

**`MirandaCalculatorPanel.test.tsx`**
- 앉은 니케를 누르고 팔레트 니케를 누르면 교환된다 ← 5번의 회귀 테스트
- 미란다 자리는 그 경로로도 안 바뀐다

**앱에서 눈으로** — CSS(`cursor`)와 WebView2 클릭 전달은 Vitest가 못 잰다.
기존에 드래그가 앱에서만 죽어 있던 전례가 있으므로, 다섯 항목 전부 패키징된
앱에서 한 번씩 눌러 확인한다.

## 안 하는 것

- 백엔드 `name_en` 필드 — 슬러그로 충분하다.
- 드래그 드롭 경로 손보기 — 앱에서 어차피 안 되고, 이 다섯 건과 무관하다.
- 덱 껍데기의 키보드 접근 — 두 동작 다 이미 진짜 버튼이 있다.
- 검색 상태 저장, 초성 + 완성형 혼합 질의(`홍ㄹ`) 처리.
