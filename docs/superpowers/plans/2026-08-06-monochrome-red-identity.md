# 흑·회·백·적 시각 정체성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RapiLab의 UI 크롬을 검정·회색·흰색·빨강으로 바꾼다. 게임 데이터가 색으로 나르는 정보(속성·성급·애장품)는 그대로 둔다.

**Architecture:** 변경은 CSS 두 파일로 닫힌다. `index.css`의 `:root`가 팔레트의 유일한 출처이고, `App.css`는 그 토큰을 표면에 적용한다. 이 팔레트는 배경 3단이 서로 1.05/1.08 대비로 거의 평평해서 **깊이를 테두리가 전부 지탱한다** — 그래서 테두리 토큰을 역할별로 셋(`--rule`/`--border`/`--border-strong`)으로 나누고, 액센트도 「누르는 것(흰색)」과 「가리키는 것(빨강)」 둘로 쪼갠다.

**Tech Stack:** 순수 CSS 커스텀 프로퍼티. 검증은 `scripts/check_palette_contrast.py`(Python, 의존성 없음) + 라이브 브라우저 확인.

**설계 근거:** `docs/superpowers/specs/2026-08-06-monochrome-red-identity-design.md`

## Global Constraints

- 대비 임계: 본문/글자 **4.5:1**, 컨트롤임을 알려주는 경계 **3:1**. 판정 기준 바닥은 가장 밝은 `--surface-2` = `#1a1a1a`.
- 게임 데이터 색은 **손대지 않는다**: `--el-fire` `#dd3333` · `--el-water` `#3fa9f5` · `--el-wind` `#46c96b` · `--el-iron` `#f2b53b` · `--el-electric` `#d158f5` · `--star` `#ffc93c` · `--favorite-item` `#ff8a3d`.
- 레이아웃·글자 크기·여백·폰트는 **바꾸지 않는다**. (`--sp-*`, `--radius*`, `--sans`, `--mono`, `--measure`, `--filter-*` 전부 불변.)
- **TSX는 건드리지 않는다.** 하드코딩된 색상값이 하나도 없음을 확인했다.
- **밀도 제약**: 두꺼운 선(2px)과 밝은 `--border`는 **컨테이너에만**. **그리드 항목 크롬**(팔레트 칩 박스, 빈 초상화 자리, 칩 안의 작은 배지)은 `--rule`을 쓴다. 이 선을 넘으면 촘촘한 화면이 시끄러워진다.
  - **예외 (Fienn 판정, 2026-08-06)**: 상태 배지는 밝기 사다리를 유지한다 — `.pill--muted`는 `--rule`, `.pill--ok`는 `--border`, `.pill--warn`은 `--border-strong`. 제약의 의도는 70칩 격자였고, 경고는 색을 잃은 만큼 테두리로 말해야 한다. 세 배지가 서로 다른 토큰을 쓰는 것은 의도이며 결함이 아니다.
- 커밋 메시지는 저장소 관례를 따른다: 명령형 현재 시제, 무엇을/왜.
- **Vitest는 `css: false`라 이 변경을 단위 테스트로 잡지 못한다.** `npm test`가 초록인 것은 "TSX를 안 깨뜨렸다"는 뜻일 뿐이다. 각 태스크의 진짜 게이트는 대비 스크립트와 라이브 확인이다.

## File Structure

| 파일 | 책임 | 상태 |
|---|---|---|
| `frontend/src/index.css` | `:root` 토큰 — 팔레트의 유일한 출처 | 수정 |
| `frontend/src/App.css` | 토큰을 표면에 적용하는 규칙 | 수정 |
| `scripts/check_palette_contrast.py` | 대비 임계 자동 검증 | **이미 있음**(스펙과 함께 커밋됨) |
| `docs/decisions.md` · `docs/insights.md` | 결정과 재사용 가능한 교훈 | 마지막 태스크에서 추가 |

---

## 사전 준비 (모든 태스크 공통)

개발 서버를 띄워두면 저장할 때마다 화면이 갱신되어 각 태스크의 라이브 확인이 빨라진다.

```bash
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

백엔드 `:8000`, 프론트 `:5173`. 확인은 항상 **http://localhost:5173/** 에서 한다.

---

### Task 1: 팔레트 토큰을 교체한다

이 태스크만 끝나도 앱은 흑·회·백·적이 된다(상태색은 아직 초록/호박이 남아 있다).

**Files:**
- Modify: `frontend/src/index.css:33-53` (배경/테두리/글자/액센트/상태색 블록)
- Modify: `frontend/src/index.css:55-58` (속성 색 주석 — 보라를 언급하고 있어 거짓이 된다)
- Modify: `frontend/src/index.css:71` (`--shadow`)

**Interfaces:**
- Produces: `--bg` `--surface` `--surface-2` `--rule` `--border` `--border-strong` `--text` `--text-muted` `--primary` `--primary-contrast` `--primary-hover` `--accent` `--accent-contrast` `--accent-soft` `--shadow`
- Produces(제거): `--accent-hover`는 Task 2에서 `.btn--primary:hover`를 옮긴 뒤 고아가 되므로 **Task 2에서** 지운다. 이 태스크에서는 남겨둔다(지금 지우면 앱이 깨진다).

- [ ] **Step 1: 대비 스크립트를 먼저 돌려 기준선을 본다**

Run: `python scripts/check_palette_contrast.py`

Expected: 표가 출력되고 `border`·`border-strong` 행이 `ok`. 이 스크립트는 이미 목표 팔레트 값을 담고 있으므로, 여기서 나오는 숫자가 곧 우리가 맞춰야 할 값이다.

- [ ] **Step 2: 배경·테두리·글자 블록을 교체한다**

`frontend/src/index.css`의 33-42행(주석 포함)을 아래로 바꾼다:

```css
  /* One near-black ground with two barely-lighter steps. The ladder is almost
     flat - 1.05 and 1.08 between steps - so the borders below carry the
     structure rather than the fills. */
  --bg: #0a0a0a;
  --surface: #111111;
  --surface-2: #1a1a1a;

  /* Three lines, three jobs. A divider that merely separates content may sit
     below the 3:1 floor; a line that is what tells you something IS a control
     may not. Ratios are against --surface-2, the lightest ground any of them
     is drawn on: 1.28 / 3.03 / 5.04. --border clears its floor by 0.03, so
     re-run scripts/check_palette_contrast.py if it or --surface-2 moves. */
  --rule: #2e2e2e;
  --border: #666666;
  --border-strong: #8a8a8a;

  /* Not pure white on pure black. That pairing maxes contrast at 21:1 but
     haloes, and this screen is read for minutes at a time. */
  --text: #f2f2f2;
  --text-muted: #9e9e9e;
```

- [ ] **Step 3: 액센트 블록을 교체한다**

44-47행을 아래로 바꾼다. `--accent-hover`는 Task 2까지 살려둔다:

```css
  /* White is what you press; red is what the app is pointing at - the active
     tab, a selected chip, a focus ring, an error. Keeping red rare is what
     lets it mean "look here" when it does appear.
     The contrast token is near-black, not white: white on this red is 3.80,
     which fails; near-black is 5.21. */
  --primary: #f2f2f2;
  --primary-contrast: #0a0a0a;
  --primary-hover: #ffffff;

  --accent: #ff2233;
  --accent-hover: #ff4757;
  --accent-contrast: #0a0a0a;
  --accent-soft: rgba(255, 34, 51, 0.18);
```

- [ ] **Step 4: 속성 색 주석에서 사라진 보라를 걷어낸다**

55-58행의 주석을 아래로 바꾼다. 나머지 다섯 줄(`--el-*` 값)은 **그대로 둔다**:

```css
  /* Element identity, so a portrait can state its element without a label.
     This is the one place colour carries game data, and it is why the chrome
     around it is monochrome: against a grey ground these read louder, not
     weaker. Fire is a deep red (Fienn, 2026-07-28) so it does not read as
     Iron's gold on a dark surface. */
```

- [ ] **Step 5: 그림자를 끈다**

71행을 바꾼다:

```css
  /* Nothing: a dark shadow on a near-black ground does no work. The two
     popovers that need to float (.help-tip__bubble, .palette__details) are
     separated by an opaque background and a --border-strong edge instead. */
  --shadow: none;
```

- [ ] **Step 6: 대비를 재검증한다**

Run: `python scripts/check_palette_contrast.py`

Expected: 모든 행이 `ok`. 특히 `border` 행의 `surface-2` 열이 **3.03 ok**, `accent` 행이 **4.58 ok**.

- [ ] **Step 7: TSX가 안 깨졌는지 확인한다**

Run: `cd frontend && npm test`
Expected: `Test Files 54 passed (54)`, `Tests 524 passed (524)`

- [ ] **Step 8: 라이브로 토큰이 실제 적용됐는지 확인한다**

http://localhost:5173/ 을 열고 브라우저 콘솔에서:

```js
const s = getComputedStyle(document.documentElement)
console.table({
  bg: s.getPropertyValue('--bg').trim(),
  border: s.getPropertyValue('--border').trim(),
  rule: s.getPropertyValue('--rule').trim(),
  accent: s.getPropertyValue('--accent').trim(),
  primary: s.getPropertyValue('--primary').trim(),
  shadow: s.getPropertyValue('--shadow').trim(),
  elFire: s.getPropertyValue('--el-fire').trim(),
})
```

Expected: `bg: #0a0a0a`, `border: #666666`, `rule: #2e2e2e`, `accent: #ff2233`, `primary: #f2f2f2`, `shadow: none`, `elFire: #dd3333`(불변).

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/index.css
git commit -m "Swap the palette to black, grey, white and red

The ladder of three grounds is now almost flat, so the border tokens split
into three roles and carry the structure the fills used to. Element, star and
favourite-item colours are untouched: colour on screen means the game is
stating a fact."
```

---

### Task 2: 주요 버튼을 흰색으로 — 액센트를 쪼갠다

**Files:**
- Modify: `frontend/src/App.css:843-851` (`.btn--primary`, `.btn--primary:hover`)
- Modify: `frontend/src/index.css` (`--accent-hover` 제거)

**Interfaces:**
- Consumes: Task 1의 `--primary` `--primary-contrast` `--primary-hover`
- Produces: 없음(이후 태스크는 이 규칙에 의존하지 않는다)

- [ ] **Step 1: 현재 상태를 눈으로 확인한다**

http://localhost:5173/ → 솔로 레이드 탭. **「인카운터!」 버튼이 빨간 면**이어야 한다(Task 1 직후 상태). 이것이 우리가 바꾸려는 것이다.

- [ ] **Step 2: `.btn--primary`를 흰 면으로 바꾼다**

`frontend/src/App.css` 843-851행을 아래로 바꾼다:

```css
/* White, not red. Red is reserved for what the app is pointing at; the button
   you are meant to press is the brightest thing on the page instead. */
.btn--primary {
  background: var(--primary);
  color: var(--primary-contrast);
  border-color: var(--primary);
  font-weight: 600;
}

.btn--primary:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}
```

`font-weight: 600`은 새로 넣는 것이 아니라 **이미 이 규칙에 있던 선언**이다. 교체하면서 떨어뜨리면 안 된다 — 글자 굵기는 이 개편의 범위 밖이다.

- [ ] **Step 3: 고아가 된 `--accent-hover`를 지운다**

`frontend/src/index.css`에서 `--accent-hover: #ff4757;` 줄을 삭제한다.

- [ ] **Step 4: 정말 아무도 안 쓰는지 확인한다**

Run: `grep -rn "accent-hover" frontend/src`
Expected: 출력 없음. 하나라도 나오면 지우지 말고 그 사용처를 먼저 처리한다.

- [ ] **Step 5: 라이브 확인**

솔로 레이드 탭에서 브라우저 콘솔:

```js
const b = document.querySelector('.btn--primary')
const cs = getComputedStyle(b)
console.log(cs.backgroundColor, cs.color)
```

Expected: `rgb(242, 242, 242) rgb(10, 10, 10)` — 흰 면에 근검정 글자.

- [ ] **Step 6: 회귀 확인**

Run: `cd frontend && npm test`
Expected: `Tests 524 passed (524)`

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/App.css frontend/src/index.css
git commit -m "Give the primary button white, and free red for emphasis

One accent token was doing two jobs - the thing you press and the thing being
pointed at. Splitting them is what makes a restrained red possible: it now
appears only where the app is drawing the eye."
```

---

### Task 3: 상태색을 무채색+빨강으로 흡수한다

상태색은 게임 데이터가 아니라 앱이 하는 말이므로 팔레트 안으로 들어온다. 사용처는 14개 선택자, 17줄이다.

**Files:**
- Modify: `frontend/src/App.css` — 630, 635, 875-876, 899, 1016-1017, 1021-1022, 1134, 1143, 1561, 1751, 1755행
- Modify: `frontend/src/index.css` — `--ok` `--ok-soft` `--warn` `--warn-soft` `--danger` 제거

**Interfaces:**
- Consumes: Task 1의 `--accent` `--accent-soft` `--text` `--text-muted` `--border`
- Produces: 없음

- [ ] **Step 1: 오류·위험을 빨강으로 옮긴다**

아래 다섯 곳에서 `var(--danger)` → `var(--accent)`:

- `App.css:630` `.field--invalid .field__input` → `border-color: var(--accent);`
- `App.css:635` `.field__error` → `color: var(--accent);`
- `App.css:876` `.btn--icon:hover` → `color: var(--accent);`
- `App.css:899` `.sync__error` → `color: var(--accent);`
- `App.css:1755` `.deck-results__diff-removed` → `color: var(--accent);`

- [ ] **Step 2: 정상·증가를 흰색으로 옮긴다**

- `App.css:1751` `.deck-results__diff-added` → `color: var(--text);`
- `App.css:1016-1017` `.pill--ok` → 아래로 교체:

```css
.pill--ok {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border);
}
```

- [ ] **Step 3: 경고를 보조 글자 + 테두리로 옮긴다**

- `App.css:1021-1022` `.pill--warn` → 아래로 교체:

```css
/* A warning is not an error. It reads as quieter text inside a stated edge,
   which leaves red to mean something is actually wrong. */
.pill--warn {
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-strong);
}
```

- `App.css:1134` `.deck-results__warning` → `color: var(--text-muted);`
- `App.css:1143` `.deck-results__hold` → `color: var(--text-muted);`
- `App.css:1561` `.draft-editor__deck-warning` → `color: var(--text-muted);`
- `App.css:875` `.btn--icon:hover` → `background: var(--accent-soft);`

- [ ] **Step 4: 죽은 토큰을 지운다**

`frontend/src/index.css`에서 아래 다섯 줄을 삭제한다:

```css
  --ok: #4ade80;
  --ok-soft: rgba(74, 222, 128, 0.14);
  --warn: #fbbf24;
  --warn-soft: rgba(251, 191, 36, 0.16);
  --danger: #f87171;
```

- [ ] **Step 5: 남은 참조가 없는지 확인한다**

Run: `grep -rn "var(--ok\|var(--warn\|var(--danger" frontend/src`
Expected: 출력 없음. 하나라도 남으면 그 줄을 먼저 위 규칙대로 옮긴다.

- [ ] **Step 6: 화면에 초록·호박이 남아 있지 않은지 라이브로 확인한다**

http://localhost:5173/ 에서 브라우저 콘솔:

```js
// Every painted colour on the page, minus the ones game data is allowed to use.
const allowed = new Set(['rgb(221, 51, 51)','rgb(63, 169, 245)','rgb(70, 201, 107)',
                         'rgb(242, 181, 59)','rgb(209, 88, 245)','rgb(255, 201, 60)',
                         'rgb(255, 138, 61)'])
const odd = new Set()
for (const el of document.querySelectorAll('*')) {
  const cs = getComputedStyle(el)
  for (const p of ['color','backgroundColor','borderTopColor','borderLeftColor']) {
    const v = cs[p]
    if (!v.startsWith('rgb')) continue
    const [r,g,b] = v.match(/\d+/g).map(Number)
    const grey = Math.max(r,g,b) - Math.min(r,g,b) < 12
    const red = r > g && r > b
    if (!grey && !red && !allowed.has(v)) odd.add(`${v}  ${el.className || el.tagName}`)
  }
}
console.log([...odd].join('\n') || 'clean: only greys, reds and game-data colours')
```

Expected: `clean: ...` 또는 초상화 이미지 관련 항목만. 초록/호박 계열이 UI 요소에 남아 있으면 그 선택자를 이 태스크에서 마저 옮긴다.

- [ ] **Step 7: 회귀 확인 후 커밋**

Run: `cd frontend && npm test` → `Tests 524 passed (524)`

```bash
git add frontend/src/App.css frontend/src/index.css
git commit -m "Fold the status colours into the monochrome and the red

Green, amber and a second red were the app talking, not the game. Errors and
losses take the one red; gains take white; a warning takes quieter text inside
a stated edge, so red keeps meaning something is wrong."
```

---

### Task 4: 선의 역할을 나눈다 — `--rule` 배선과 컨테이너 두께

`--border`가 `#2c2937`에서 `#666666`으로 크게 밝아졌으므로, 지금 그것을 쓰는 22곳 중 **칸막이와 개별 항목 크롬은 `--rule`로 내려야 한다.** 안 하면 촘촘한 화면이 시끄러워진다 — 이것이 이 방향이 성립하기 위한 조건이다.

**Files:**
- Modify: `frontend/src/App.css` — 아래 표의 행들

**Interfaces:**
- Consumes: Task 1의 `--rule` `--border` `--border-strong`
- Produces: 없음

- [ ] **Step 1: 순수 칸막이를 `--rule`로 내린다**

`var(--border)` → `var(--rule)`:

| 행 | 선택자 | 속성 |
|---|---|---|
| 63 | `.app__footer` | `border-top` |
| 293 | `.roster__unsupported` | `border-top` |
| 399 | `.tabs` | `border-bottom` |
| 1727 | `.draft-results__tier` | `border-top` |

- [ ] **Step 2: 개별 항목 크롬을 `--rule`로 내린다**

`var(--border)` → `var(--rule)`:

| 행 | 선택자 | 왜 |
|---|---|---|
| 467 | `.skills__pip` | 칩 안의 작은 배지 |
| 562 | `.roster-card__portrait--missing` | 빈 자리 표시 |
| 1028 | `.pill--muted` | 데이터 배지 |
| 1181 | `.deck-results__portrait--missing` | 빈 자리 표시 |
| 1311 | `.palette__item` | **박스**만. 1315행의 `border-left: 3px solid var(--element, var(--border))` 속성 띠는 그대로 둔다 |

`.palette__item`이 핵심이다. 팔레트는 한 화면에 70칩 이상이 깔리는 곳이라, 여기 박스가 밝아지면 격자가 웅성거린다. 정체성은 왼쪽 3px 속성 띠가 이미 지고 있다.

- [ ] **Step 3: 컨테이너 넷을 2px로 올린다**

아래 네 곳의 `border: 1px solid var(--border)` → `border: 2px solid var(--border)`:

| 행 | 선택자 |
|---|---|
| 133 | `.unit-filter` |
| 316 | `.card` |
| 724 | `.group` |
| 1528 | `.draft-editor__deck` |

나머지 `--border` 사용처(`.unit-filter__search` 155, `.unit-filter__select` 171, `.unit-filter__chip` 193, `.sync-help` 964, `.sync-help__shot` 1001, `.deck-results__item` 1106, `.draft-editor__slot` 1583)는 **1px 그대로 두고 `--border`를 유지한다** — 컨트롤임을 알려주는 선이라 3:1이 필요하지만 두꺼울 필요는 없다.

- [ ] **Step 4: 옛 팔레트의 파란 잔재를 지운다**

`App.css:1780` `.charge-ladder__row--current`의 폴백이 옛 팔레트의 파랑이다:

```css
  background: var(--accent-soft, rgba(120, 170, 255, 0.14));
```

`--accent-soft`는 항상 정의되어 있으므로 폴백은 죽은 값이고, 하필 이 팔레트에 없는 색이다:

```css
  background: var(--accent-soft);
```

같은 부류가 하나 더 있다. `.charge-ladder__table td`의 행 구분선이다:

```css
  border-bottom: 1px solid var(--border, #3a3a3a);
```

표의 행 사이를 가르는 선이므로 `--rule`이 맞고, 폴백은 여기서도 죽은 값이다:

```css
  border-bottom: 1px solid var(--rule);
```

**이 지점은 최초 조사가 놓쳤다.** `var(--border)`를 정확 일치로 셌기 때문에 폴백이 붙은 `var(--border, …)` 형태가 빠졌다. 앞으로 토큰 사용처를 셀 때는 `var\(--border\b` 처럼 폴백까지 걸리는 패턴을 쓸 것.

- [ ] **Step 5: 밀도를 라이브로 확인한다 — 이 방향의 알려진 실패 지점**

http://localhost:5173/ → 솔로 레이드 탭 → 아래로 스크롤해 **「사용할 유닛」 팔레트**(70칩 이상)를 화면에 채운다.

봐야 할 것: 칩 격자가 **선의 그물처럼 보이지 않아야** 한다. 눈에 먼저 들어오는 것은 초상화와 왼쪽 속성 띠여야 하고, 칩 박스 선은 배경에 가까워야 한다.

콘솔로도 확인:

```js
const chip = document.querySelector('[role=tabpanel]:not([hidden]) .palette__item')
const cs = getComputedStyle(chip)
console.log('box:', cs.borderTopColor, '| element stripe:', cs.borderLeftColor)
```

Expected: box는 `rgb(46, 46, 46)`(`--rule`), stripe는 그 유닛의 속성 색(예: `rgb(221, 51, 51)`).

- [ ] **Step 6: 회귀 확인 후 커밋**

Run: `cd frontend && npm test` → `Tests 524 passed (524)`
Run: `cd frontend && npm run build` → 성공

```bash
git add frontend/src/App.css
git commit -m "Split the lines by what they do, now that they carry the depth

With the grounds almost flat, a bright border is the only thing saying where a
control is - so the lines that merely divide content, and the chrome on the
seventy-odd palette chips, drop to the dimmer rule token. Containers go to 2px.
Getting this boundary wrong is what would make a dense screen noisy."
```

---

### Task 5: 전면 확인과 기록

**Files:**
- Create: `docs/decisions.md` 최상단 항목
- Create: `docs/insights.md` 최상단 항목

**Interfaces:**
- Consumes: Task 1-4의 결과
- Produces: 없음

- [ ] **Step 1: 다섯 탭 × 두 폭을 전부 본다**

http://localhost:5173/ 에서 **니케 풀 · 솔로 레이드 · 유니온 레이드 · 계산기 · 동기화** 다섯 탭을, 창 폭 **1440px**와 **760px** 양쪽에서 확인한다.

각 화면에서:
- 초록·호박·보라가 UI 요소에 남아 있지 않다
- 속성 색·성급 금색·애장품 주황은 그대로 있다
- 어느 화면도 가로 스크롤이 생기지 않는다

```js
console.log('h-overflow:', document.documentElement.scrollWidth > document.documentElement.clientWidth)
```

Expected: `h-overflow: false`

- [ ] **Step 2: 팝오버 둘이 내용 위에서 분리돼 보이는지 확인한다**

그림자를 껐으므로 이 둘은 이제 테두리만으로 떠 있어야 한다.

- 계산기 탭의 `?` 아이콘에 마우스를 올려 **도움말 말풍선**(`.help-tip__bubble`)을 띄운다
- 솔로 레이드 탭 팔레트의 칩에 마우스를 올려 **유닛 상세**(`.palette__details`)를 띄운다

둘 다 뒤 내용과 확실히 갈려 보여야 한다. 안 그러면 해당 선택자의 테두리를 `--border-strong`으로 올린다.

- [ ] **Step 3: 대비를 마지막으로 재검증한다**

Run: `python scripts/check_palette_contrast.py`
Expected: 모든 행 `ok`

- [ ] **Step 4: 전체 스위트**

Run: `cd frontend && npm test` → `Tests 524 passed (524)`
Run: `cd frontend && npm run build` → 성공
Run: `cd backend && python -m pytest -q` → `1912 passed, 3 skipped`

(백엔드는 이 변경과 무관하지만, 저장소 관례상 커밋 전 기준선을 확인한다.)

- [ ] **Step 5: `docs/decisions.md` 최상단에 결정을 기록한다**

`# Decisions` 헤더 블록 바로 다음, 기존 첫 항목(`## 스왑 예산을…`) **위에** 아래를 삽입한다. 구현 중 실제와 달라진 것이 있으면 그 부분만 고쳐 쓴다.

```markdown
## 앱의 색을 흑·회·백·적으로 — 색은 게임의 것, 무채색과 빨강은 앱의 것

- Date: 2026-08-06
- Context: 보라(`#a78bfa`) 액센트에 맞춰 튜닝된 다크 테마라 개성이 약했다.
  그런데 이 앱에서 색은 장식이 아니다 — 속성 5종은 초상화 테두리로, 돌파는
  금색 별로, 애장품은 주황 하트로 **정보를 나르고 있었다**. 무채색화가
  정보를 지우는 문제부터 풀어야 했다.
- Decision (Fienn, 2026-08-06): **지배 규칙을 세웠다 — 화면에 색이 있으면
  그건 게임이 말하는 사실이고, 흑·회·백·적은 앱 자신의 목소리다.** 그래서
  속성·성급·애장품 색은 한 픽셀도 안 건드리고, 상태색(초록·호박·빨강)은
  앱이 하는 말이므로 팔레트 안으로 흡수했다. 방향은 실제 앱에 세 후보를
  입혀 비교한 뒤 **C·하드 컨트라스트**로 골랐다.
- Why 액센트를 쪼갰나: 기존 `--accent` 하나가 「누를 수 있는 것」과 「여기를
  봐」를 겸하며 35곳을 맡고 있었다. 흰 주요 버튼과 절제된 빨강을 동시에
  가지려면 쪼개는 것 외에 방법이 없다 — `--primary`(흰색)는 누르는 것,
  `--accent`(빨강)는 앱이 가리키는 것. 실제로 `--primary`로 옮겨야 했던
  것은 35곳 중 3줄뿐이었다.
- 받아들인 절충: **「활성」과 「오류」가 같은 빨강을 쓴다.** 색조로는 안
  갈리고 그것이 무엇인지(탭 밑줄이냐 오류 문구냐)가 가른다. 빨강을 오류에만
  남기면 화면에서 빨강이 거의 사라져 정체성이 안 남는다.
- **밀도 제약은 미감이 아니라 이 방향의 성립 조건이다.** 배경 3단이 서로
  1.05/1.08 대비로 평평해져 깊이를 테두리가 전부 지탱하는데, 그래서 밝아진
  `--border`를 70칩짜리 팔레트 격자에 그대로 쓰면 화면이 선의 그물이 된다.
  선을 셋으로 나눠(`--rule`/`--border`/`--border-strong`) 칸막이와 개별 항목
  크롬은 어두운 쪽에 두었다.
- Alternatives considered: **(a) 속성도 무채색화하고 아이콘 배지로** — 촘촘한
  그리드에 요소가 하나 더 얹혀 훑는 속도가 떨어진다. **(b) 속성을 빨강 단계로
  환원** — 5단계 빨강은 서로 헷갈려 사실상 정보를 잃는다. **(c) 빨강을 주역으로**
  — 흔해져 위험 신호와 구분이 안 된다. **(d) A·잉크 / B·그래파이트** — 실제
  화면 비교 후 미채택. **(e) 팔레트만 교체** — 회색 사다리가 보라를 전제로
  맞춰져 있어 단조해진다.
- Consequences: 변경은 CSS 두 파일로 닫혔다(TSX에 하드코딩된 색이 없었다).
  죽은 토큰 6개(`--ok` `--ok-soft` `--warn` `--warn-soft` `--danger`
  `--accent-hover`)를 지웠다. `scripts/check_palette_contrast.py`가 남아
  임계를 지킨다 — **`--border` `#666666`은 3.03으로 문턱 3.0 바로 위라**,
  이 값이나 `--surface-2`를 만지면 반드시 다시 돌려야 한다. 프론트 524 ·
  백엔드 1912/3 불변(CSS는 스위트가 보지 못한다).
```

- [ ] **Step 6: `docs/insights.md` 최상단에 교훈을 기록한다**

`# Insights` 헤더 블록 바로 다음, 기존 첫 항목 **위에** 아래를 삽입한다.

```markdown
## 어두운 팔레트를 눈으로 고르면 틀린다 — 특히 테두리가 깊이를 질 때

- 확립: 2026-08-06. 흑·회·백·적 개편에서 **눈으로는 멀쩡했던 값 셋이 계산에서
  떨어졌다**: 후보 `--border: #3a3a3a`는 1.74로 컴포넌트 경계에 필요한 3:1에
  한참 못 미쳤고, 빨강 면 위 흰 글자는 3.80으로 실격이었으며(근검정은 5.21로
  통과), 스펙에 어림으로 적은 3.22/4.7은 실제로 3.03/5.04였다.
- **대비 숫자는 기준 바닥을 밝히지 않으면 무의미하다.** 같은 회색이 `--bg`
  위에서 3.45, `--surface-2` 위에서 3.03이다. 판정은 **그 색이 놓이는 가장
  밝은 바닥**으로 해야 한다.
- **배경 사다리가 평평해지면 테두리 토큰이 민감해진다.** 이 팔레트는 배경
  3단이 서로 1.05/1.08이라 깊이를 선이 전부 지탱한다. 그 상태에서는 선을
  역할별로 갈라야 한다 — 그것이 없으면 컨트롤임을 알 수 없는 선(3:1 필수)과
  그냥 칸막이(면제)가 같은 값을 쓰게 되고, 촘촘한 화면이 웅성거린다.
- **How to apply:** `scripts/check_palette_contrast.py`를 돌린다. 장식용
  구분선은 임계 0으로 등록해 **숫자는 보이되 통과한 척은 안 하게** 해두었다.
- 방향 자체는 말로 고르면 안 된다. 세 후보를 **실제 앱에 입혀** 스크린샷을
  비교했는데, 로스터 탭에서는 화면 대부분이 초상화라 A와 C가 구분되지 않았다
  — 팔레트 판단은 **크롬이 화면을 차지하는 화면**에서 해야 한다.
```

- [ ] **Step 7: 커밋**

```bash
git add docs/decisions.md docs/insights.md
git commit -m "docs: record the monochrome-red identity and what picking it taught

The rule that decides future colour questions, the accent split, and the three
contrast defects that eyeballing would have shipped."
```

---

## Self-Review

**스펙 커버리지**

| 스펙 항목 | 태스크 |
|---|---|
| 지배 규칙 | Task 5 Step 5 (기록), Task 1-4 전반에 반영 |
| 불변 — 게임의 목소리 | Global Constraints, Task 1 Step 4, Task 3 Step 6, Task 5 Step 1 |
| 팔레트 토큰 표 | Task 1 Step 2-3 |
| 순백/순흑을 쓰지 않는 이유 | Task 1 Step 2 (`--text` 주석) |
| `--rule` 분리 이유 | Task 1 Step 2, Task 4 |
| 액센트 쪼개기 | Task 1 Step 3, Task 2 |
| 상태색 흡수 | Task 3 |
| 표면 처리 — 그림자 | Task 1 Step 5, Task 5 Step 2 |
| 표면 처리 — 선 두께 | Task 4 Step 3 |
| 표면 처리 — 개별 항목 크롬 | Task 4 Step 2 |
| 밀도 제약 (실측 근거) | Task 4 Step 5 |
| 범위 | Global Constraints |
| 검증 3종 | Task 1/3/4/5의 확인 단계 |

빠진 항목 없음.

**남은 위험 (스펙과 동일, 실행 중 주의)**

- `--border` `#666666`은 3.03으로 문턱 바로 위다. 이 값이나 `--surface-2`를 만지면 즉시 대비 스크립트를 다시 돌린다.
- 스펙의 「상태 표현」 중 포커스·선택·호버는 Task 1의 토큰 교체만으로 자동으로 따라온다(기존 규칙이 `--accent`/`--accent-soft`를 이미 쓰고 있다). Task 5 Step 1에서 눈으로 확인한다.
- 화면 확인은 이 저장소의 로스터 하나로만 한다. 애장품·오버로드가 드문 로스터에서는 인상이 다를 수 있다.
