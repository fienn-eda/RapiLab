# 솔로 레이드 설정 영역 재배치 — 설계

날짜: 2026-08-20 · Fienn 요청

## 무엇을 만드나

솔로 레이드 탭의 설정 영역(`.recommend-form__setup`)을 다시 짠다. 네 가지다.

1. **배치** — 좌 컬럼에 「보스 설정」과 「모드」를 세로로 쌓고, 우 컬럼 전체를
   새 「시즌 가이드」 카드가 받는다.
2. **보스 설정 기본 접힘** — 솔로 탭에서만. 회차 카드까지 포함해 통째로 접는다.
3. **시즌 가이드** — 보스 설정에서 파생된 키워드 뱃지 줄 + Fienn이 직접 쓰는
   문장. 문장은 localStorage에 남는다.
4. **버튼형 컨트롤** — 기믹 체크박스 5개와 모드 라디오 4개를 토글 칩으로.

## 왜

지금 배치는 좌(보스 설정, 세로로 길다) · 우(모드, 짧다)라 오른쪽 아래가 빈다.
보스 설정은 시즌마다 한 번 채우고 나면 거의 안 건드리는데도 화면에서 제일 큰
자리를 늘 차지하고 있고, 정작 플레이 중에 반복해서 보고 싶은 것 — 이 보스의
기믹이 무엇이고 무엇을 챙겨야 하는가 — 은 앱 어디에도 없다.

접어서 생긴 자리를 가이드가 받으면 두 문제가 같이 풀린다.

## 지금 있는 것과 무엇이 다른가

- `BossProfileField`에는 **이미 접기가 있다**(`collapsed` 상태 + `aria-expanded`
  머리 버튼). 기본값이 펼침일 뿐이다. 오류가 있으면 강제로 펼치는 규칙
  (`hasErrors`)도 이미 있다.
- 버튼형 칩도 **이미 두 벌 있다** — `.element-picker`(약점)와
  `.rotation-picker`(회차 보스). 진짜 `<input>`을 `.visually-hidden`으로 숨기고
  라벨을 `:has(input:checked)`로 칠하는 방식이라, 화살표 이동과 화면 낭독기의
  그룹 읽기를 잃지 않는다. 기믹·모드도 같은 패턴을 쓴다.
- 키워드 뱃지의 규칙도 **이미 있다** — `BossSummary.tsx`가 결과 화면에서
  「코어 피격 · 2관통 · 부위파괴 · 잡몹 생성 · 속성저지 필수」를 그린다. 새로
  만들지 않고 공유한다.

즉 이 설계가 새로 만드는 것은 **가이드 카드와 그 저장소** 하나뿐이고, 나머지는
있는 것의 기본값과 배치를 바꾼다.

## 설계

### A. 배치 — `RecommendPanel.tsx` · `App.css`

`.recommend-form__setup`을 그대로 2컬럼 그리드로 두되 폭 배분을 바꾼다.

```
grid-template-columns: minmax(260px, 22rem) minmax(0, 1fr);
```

좌 컬럼은 새 래퍼 `.recommend-form__controls`(flex column, gap `--sp-4`)로
`<BossProfileField>`와 모드 `<fieldset>`을 감싼다. 우 컬럼은 `<SeasonGuideCard>`
하나다. `align-items: start`는 유지 — 가이드가 길어도 좌 컬럼 카드들이 늘어나지
않는다.

900px 이하에서 1컬럼으로 떨어지는 기존 미디어쿼리는 그대로 둔다.

`.recommend-form__setup` 위의 주석은 「모드 컬럼은 내용만큼만 차지한다」고 적혀
있는데 이 변경으로 사실이 아니게 된다. 새 배치가 무엇을 가르는지 — 왼쪽은 내가
고르는 것, 오른쪽은 내가 읽는 것 — 로 다시 쓴다.

### B. 기본 접힘 — `BossProfileField.tsx`

`collapsed` 초기값을 새 prop `defaultCollapsed`(기본 `false`)로 받고, 솔로
탭(`RecommendPanel`)에서만 `true`로 넘긴다.

**유니온 탭은 펼친 채로 둔다.** 유니온은 전투 수만큼 보스 카드가 서고 매 전투마다
다른 보스를 고르므로, 접으면 실행할 때마다 다섯 번 펼쳐야 한다 — 솔로에서
이득인 것이 유니온에서는 손해다.

접힘의 범위는 지금과 같다: 머리 버튼만 남고 `showBody` 아래 전부가 사라진다.
**회차 보스 카드도 함께 접힌다**(Fienn 지정, 2026-08-20). 접힌 머리는
`bossHeading`이 만들며 약점 아이콘 + 보스 이름이다.

`hasErrors`일 때 강제로 펼치는 규칙은 그대로 — 기본이 접힘이 되면 이 규칙이
없을 때 「이유 없이 계산이 안 되는 화면」이 되기 쉬우므로 오히려 더 중요해진다.

### C. 토글 칩 — `components/fields/ToggleChip.tsx`

`.element-picker__option`이 쓰는 패턴을 한 컴포넌트로 뽑는다.

```tsx
<ToggleChip type="checkbox" checked={…} onChange={…} help={<HelpTip …/>}>
  코어 타격 가능
</ToggleChip>
```

구조는 `<div class="chip-toggle">` 안에 `<label>`(숨은 input + 텍스트)과 선택적
help 노드가 나란히 선다. **help를 `<label>` 밖에 두는 것이 요점이다** — 라벨
안에서는 아무 클릭이나 컨트롤을 토글하므로, 설명을 열려던 클릭이 보스 설정을
바꾼다(기존 `.checkbox-row` 주석이 지적한 그대로).

칠하기는 `.chip-toggle:has(input:checked)` — 테두리를 `--accent`로, 배경을
`--surface`로. 포커스는 `:has(input:focus-visible)`로 아웃라인.

소비처 둘:

- **기믹 5개** (`BossProfileField`) — `type="checkbox"`, `.chip-row`에 flex-wrap.
  `.checkbox-row` 다섯 덩어리가 사라진다.

전환 후 `.checkbox` · `.checkbox-row` · `.radio` 세 클래스는 **아무도 쓰지
않는다**(실측: `.checkbox`/`.checkbox-row`는 `BossProfileField.tsx`에만,
`.radio`는 `RecommendPanel.tsx`의 모드 라디오 넷에만 있다). `App.css`에서 같이
지운다 — 쓰이지 않는 클래스를 남기면 다음 세션이 그것을 살아 있는 패턴으로 읽는다.
`.field__label-row`는 `.checkbox-row`와 규칙을 공유하고 있으니 선택자에서 한쪽만
떼어낸다.
- **모드 4개** (`RecommendPanel`) — `type="radio"`, 이름 공유. 지금 각 모드에
  붙은 문장형 힌트(`HELP.recommendMode.*`)는 칩에 안 들어가므로 **선택된 모드의
  힌트만** 칩 줄 아래 한 줄로 내린다. 네 문장이 한 문장이 되어 세로가 줄고,
  「지금 무엇을 하려는가」에 대한 답은 그대로 남는다.

약점 칩과 회차 카드는 이미 버튼형이라 건드리지 않는다.

### D. 키워드 뱃지 — `lib/bossBadges.ts`

`BossSummary.tsx`의 기믹 목록 만드는 부분을 순수 함수로 뽑아 둘이 공유한다.

```ts
export interface BossGimmickFlags {
  core_hittable: boolean
  pierce_hits_body_behind_core: boolean
  part_destructible: boolean
  spawns_adds: boolean
  elemental_interrupt_required: boolean
}
export const gimmickBadges = (boss: BossGimmickFlags): string[] => …
```

인터페이스를 플래그만으로 좁히는 이유: 결과 화면은 `BossProfile`을 보고 가이드
카드는 폼 상태인 `BossProfileDraft`를 보는데, 둘 다 구조적으로 이 다섯 필드를
만족한다. 넓게 잡으면 한쪽이 못 부른다.

**켜진 것만 나온다** — 꺼진 기믹까지 적으면 줄만 길어지고, 없는 것은 화면에
없는 것으로 읽힌다(`BossSummary`의 기존 규칙 그대로).

가이드 카드는 여기에 약점 속성과 적정거리를 자기 자리에서 더한다. 보스 설정이
접혀 있으면 적정거리를 볼 곳이 여기밖에 없기 때문이다.

**스타일: 흰 테두리 + 투명 바탕**(Fienn 지정, 2026-08-20). 흰색으로 *채우지*
않는 이유는 이 앱의 팔레트 규칙이다 — `index.css`에 `--primary`(#f2f2f2)는
「누르는 것」, `--accent`는 「앱이 가리키는 것」으로 못박혀 있다. 같은 변경에서
바로 옆 기믹이 진짜 버튼형 칩이 되므로, 흰색으로 채운 뱃지는 눌러보게 된다.
테두리는 새 색을 만들지 않고 `--text`를 쓴다.

### E. 시즌 가이드 — `components/SeasonGuideCard.tsx` · `hooks/useBossGuides.ts`

**제목.** `rotation.title`에서 `/(\d+시즌)/`을 뽑아 `40시즌 가이드`로 쓴다.
못 뽑으면 `{rotation.title} 가이드`, 회차 자체가 없으면 `보스 가이드`.
「솔로 레이드」를 떼는 것이 안전한 이유는 이 카드가 솔로 탭 안에만 서기
때문이다.

**뱃지 줄.** 약점 속성(또는 「약점 없음」) → 적정거리(있을 때) → `gimmickBadges`.

**문장.** 테두리 없는 `<textarea>`. 읽을 때는 카드 본문처럼 보이고 클릭하면
그 자리에서 고쳐진다 — 보기/편집 모드를 나누지 않는 이유는 그 토글이 무엇을
벌어 주는지가 없기 때문이다. `aria-label`을 붙이고 빈 값에는 placeholder로
무엇을 적는 자리인지 알린다.

**저장.** `useBossGuides` 훅. localStorage 키 `nikke-boss-guides`,
모양은 `{ guides: Record<string, string> }`, 항목 키는 `${rotation.id}::${boss_name}`.

- (회차, 보스)로 키를 잡는 것은 `data/raid-rotations.json`의 키와 같은 규칙이다
  (decisions.md 2026-08-07). 같은 보스가 다음 시즌에 다른 속성으로 나오면 가이드도
  다른 칸이다. 지난 시즌 글은 지워지지 않고 그 키에 남는다.
- 읽기·쓰기가 막힌 브라우저(사생활 모드)에서도 동작해야 한다 — 실패하면 메모리에만
  두고 조용히 계속한다. `App.tsx`의 사이드바 접힘 상태가 쓰는 것과 같은 방어다.

**회차 보스를 안 골랐을 때**(`rotation === null` 또는 `boss_name === null`)는
뱃지만 그리고 텍스트 자리에 안내 문구를 둔다. 저장할 키가 없는데 입력을 받으면
쓴 글이 조용히 사라진다.

## 무엇을 안 만드나

- **보스 이미지** — 2단계(Fienn 지정). 정적 에셋 자체는 이미 되는 길이 있다
  (`frontend/public/portraits/` + `manifest.json`, `elements/`). 다만 공지
  이미지 URL은 서명 URL이라 약 10시간이면 만료되므로(decisions.md 2026-08-07)
  링크가 아니라 받아서 커밋하는 방식이어야 하고, 그러면 회차 데이터의 스키마
  확장(백엔드 모델 · 로더 · `/update-raid-bosses` 스킬 · 테스트)이 따라온다.
  1단계에서는 **빈 상자도 그리지 않는다** — 깨진 것으로 읽힌다. 2단계에서 이미지가
  생기면 카드가 자연히 자리를 만든다.
- **유니온 탭의 가이드 카드** — 요청 범위 밖.
- **가이드의 git 영속화** — localStorage만. 회차 데이터에 `guide` 필드를 두는
  길은 「앱 안에서 직접 입력」과 맞지 않아 기각했다(Fienn, 2026-08-20).

## 테스트

새 파일마다 한 벌:

- `ToggleChip` — 체크/라디오가 실제 input으로 렌더되는지, help 클릭이 토글하지
  **않는지**(이게 이 구조의 존재 이유다).
- `bossBadges` — 켜진 것만 나오는지, 순서가 고정인지.
- `useBossGuides` — (회차, 보스)별로 칸이 갈리는지, localStorage가 막혀도
  던지지 않는지.
- `SeasonGuideCard` — 제목 추출 세 갈래, 보스 미선택 시 안내 문구, 입력이 저장되고
  보스를 바꾸면 다른 글이 나오는지.

기존 테스트가 깨지는 범위는 **세어 봤다**. 접힘이 솔로에서만 기본이고
`defaultCollapsed`의 기본값이 `false`이므로, `BossProfileField.test.tsx`(939줄)는
자기가 그 prop을 안 넘겨 **깨지지 않는다**. `App.test.tsx`도 보스 필드를 만지지
않는다(일치 0건). 실제로 깨지는 것은 `RecommendPanel.test.tsx`의 **11곳**
(104 · 325 · 326 · 355 · 386 · 1059 · 1065 · 1728 · 1732 · 1733행)뿐이고, 전부
`getByLabelText`라 **칩 전환 자체로는 안 깨진다** — `ToggleChip`은 input을 label
안에 두므로 접근 가능 이름이 그대로다. 깨지는 원인은 접힘 하나다.

「펼치고 시작」 헬퍼를 하나 두고 그 여덟 테스트에서 부른다. 테스트마다 펼치는
코드를 복사하지 않는 이유는 다음에 접힘 규칙이 또 바뀔 때 같은 수정을 여러 번
하게 되기 때문이다.

`BossProfileField.test.tsx`에는 새 테스트가 하나 붙는다 — `defaultCollapsed`를
넘기면 회차 카드까지 접히는지.

## 분량

- 신규(`ToggleChip` · `bossBadges` · `useBossGuides` · `SeasonGuideCard`) — 약 250줄
- CSS — 약 120줄 (죽는 `.checkbox`/`.checkbox-row`/`.radio` 삭제 포함)
- 기존 수정(`RecommendPanel` · `BossProfileField` · `BossSummary`) — 약 150줄
- 신규 테스트 — 약 250줄
- 기존 테스트 수정 — 약 40줄 (헬퍼 + 호출부 8곳)

합계 약 750~850줄.

## 열려 있는 위험
- **뱃지 테두리 대비.** `--text`(#f2f2f2)를 테두리로 쓰므로 새 색은 없다.
  `scripts/check_palette_contrast.py`는 팔레트 토큰을 검사하는 것이라 이 변경으로
  다시 돌릴 필요는 없지만, 칩과 뱃지가 한 줄에 섞여 서므로 **둘이 서로 다른
  것으로 읽히는지**는 앱을 띄워 눈으로 확인해야 한다(`docs/insights.md`의
  「CSS 변경은 앱을 띄워야 보인다」 — Vitest는 `css: false`다).
- **접힌 채로 잘못된 값이 계산에 쓰이는 경우.** 오류는 강제 펼침이 잡지만,
  오류가 아닌 「직전 시즌 값이 남은」 상태는 못 잡는다. 회차 카드를 고르면 나머지
  필드가 기본값으로 돌아가는 기존 규칙(decisions.md 2026-08-07)이 그 방어인데,
  카드가 접힘 뒤로 들어가면 그 규칙을 쓸 기회가 줄어든다. 뱃지 줄이 접힌 상태의
  값을 늘 비추는 것이 이 위험에 대한 답이다 — 뱃지가 실제 계산 입력에서
  파생되므로 어긋날 수 없다.
