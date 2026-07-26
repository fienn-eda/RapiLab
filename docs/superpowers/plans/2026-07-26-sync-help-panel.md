# 동기화 도움말 패널 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `SyncRosterPanel` 제목 옆 "동기화 방법" 버튼이 공유 URL 획득부터 다계정
운용까지를 스크린샷과 함께 인라인으로 펼쳐 보인다.

**Architecture:** 안내 문안은 상태 없는 새 컴포넌트 `SyncHelp`에 담고, 펼침/접힘
state는 `SyncRosterPanel`이 소유한다. 내용은 조건부 렌더가 아니라 항상 렌더한 뒤
`hidden` 속성으로 감춰 `aria-controls`가 가리키는 요소가 항상 DOM에 있게 한다.
기본 펼침 여부는 `App`이 prop으로 정한다 — 활성 프로필이 없는 화면에서만 펼친다.

**Tech Stack:** React 19 + TypeScript, Vite, Vitest + @testing-library/react +
jest-dom, 순수 CSS(`src/App.css`, 다크 단일 테마 토큰).

## Global Constraints

- 설계 스펙: `docs/superpowers/specs/2026-07-26-sync-help-panel-design.md`. 문안은
  스펙의 "문안" 절을 **글자 그대로** 옮긴다(임의 의역 금지).
- 화면 문구는 전부 한글. 어미는 앱 전체 관례인 "-어요/-예요"체를 따른다.
- 이 저장소는 `main`/원격이 없다. 트렁크는 `wip/scaffolding`이고 병합은 로컬이다.
- 프론트 테스트 기준선(이 워크트리 실측): **38 files / 294 passed**. 이 플랜을
  끝내면 **299 passed**가 된다(Task 1에서 +3, Task 2에서 +2).
  스펙의 "297"은 App 배선 테스트 2건을 세지 않은 값이라 이 플랜이 갱신한다.
- CSS 클래스명은 기존 BEM 관례를 따른다(`sync__*`, 새 블록은 `sync-help__*`).
- `hidden` 속성은 클래스의 `display`에 덮인다. `display`를 주는 블록에는 반드시
  `[hidden] { display: none; }`을 함께 쓴다(`App.css`의 `.panel[hidden]` 선례,
  같은 파일 211행 주석).

---

### Task 1: 도움말 컴포넌트와 토글

**Files:**
- Create: `frontend/public/help/shiftypad-share-button.png`
- Create: `frontend/public/help/shiftypad-copy-link.png`
- Create: `frontend/src/components/SyncHelp.tsx`
- Modify: `frontend/src/components/SyncRosterPanel.tsx`
- Modify: `frontend/src/App.css`
- Test: `frontend/src/components/SyncRosterPanel.test.tsx`

**Interfaces:**
- Consumes: 없음(이 플랜의 첫 태스크).
- Produces:
  - `SyncHelp({ id, hidden }: { id: string; hidden: boolean }): JSX.Element`
  - `SyncRosterPanel`의 props에 `defaultHelpOpen?: boolean`(기본 `false`) 추가.
    기존 필수 prop `onImport`는 그대로다.
  - 토글 버튼의 접근 가능한 이름은 정확히 `동기화 방법`, 도움말 컨테이너의
    DOM id는 `sync-help`. Task 2의 테스트가 이 두 값에 의존한다.

- [ ] **Step 1: 스크린샷을 public/help/로 복사한다**

원본은 Fienn이 캡처한 파일이고 이름에 한글과 공백이 있어 URL에 부적합하므로
내용 서술형 이름으로 바꿔 복사한다. 두 파일 모두 크롭되어 닉네임·UID가 보이지
않는다(스펙 결정 5번).

```bash
cd frontend
mkdir -p public/help
cp "/c/Users/fienn/Pictures/Screenshots/스크린샷 2026-07-26 231606.png" \
   public/help/shiftypad-share-button.png
cp "/c/Users/fienn/Pictures/Screenshots/스크린샷 2026-07-26 231627.png" \
   public/help/shiftypad-copy-link.png
ls -la public/help
```

기대: 두 파일이 각각 약 33KB, 30KB로 존재.

- [ ] **Step 2: 실패 테스트 3건을 작성한다**

`frontend/src/components/SyncRosterPanel.test.tsx`의 `describe('SyncRosterPanel', ...)`
블록 **맨 끝**(마지막 `it` 다음, 닫는 `})` 앞)에 붙인다. 파일 상단의 import와
`vi.mock`은 이미 있으므로 건드리지 않는다.

```tsx
  it('도움말은 기본으로 접혀 있다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.getByText(/복사한 URL을 아래 칸에 붙여넣어요/)).not.toBeVisible()
  })

  it('동기화 방법 버튼을 누르면 도움말이 펼쳐진다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} />)
    const toggle = screen.getByRole('button', { name: '동기화 방법' })

    fireEvent.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/복사한 URL을 아래 칸에 붙여넣어요/)).toBeVisible()
    // 라벨 없는 아이콘 두 개를 지목하는 것이 이 도움말의 존재 이유다.
    expect(screen.getByAltText(/공유 아이콘/)).toBeVisible()
    expect(screen.getByAltText(/링크 복사하기/)).toBeVisible()
  })

  it('defaultHelpOpen이면 처음부터 펼쳐져 있다', () => {
    render(<SyncRosterPanel onImport={vi.fn()} defaultHelpOpen />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(screen.getByText(/계정마다 북마크가 따로 필요해요/)).toBeVisible()
  })
```

`toBeVisible()`은 jest-dom이 요소와 그 조상의 `hidden` 속성을 함께 본다. jsdom은
CSS를 적용하지 않으므로, 이 단언이 실제로 검사하는 것은 `hidden` 속성이다 —
그래서 감추기를 CSS가 아니라 속성으로 하는 것이 테스트 가능성 면에서도 맞다.

- [ ] **Step 3: 실패를 확인한다**

```bash
cd frontend && npm test -- --run src/components/SyncRosterPanel.test.tsx
```

기대: 새 3건이 FAIL — `Unable to find an accessible element with the role
"button" and name "동기화 방법"`. 기존 7건은 PASS.

- [ ] **Step 4: SyncHelp.tsx를 만든다**

```tsx
// blablalink 동기화 안내: 공유 URL을 어디서 얻는지부터 계정이 여러 개일 때까지.
// 펼침/접힘은 SyncRosterPanel이 소유하고 여기는 문안만 담는다.
//
// 1~2단계에 스크린샷이 붙는 이유: blablalink의 공유 아이콘과 "링크 복사하기"는
// 둘 다 라벨이 없어, 글만으로는 나란히 있는 방패/물음표 아이콘과 구별해 지목할
// 방법이 없다.

interface SyncHelpProps {
  /** 토글 버튼의 aria-controls가 가리키는 id. */
  id: string
  hidden: boolean
}

export function SyncHelp({ id, hidden }: SyncHelpProps) {
  return (
    <div className="sync-help" id={id} hidden={hidden}>
      <ol className="sync-help__steps">
        <li>
          blablalink <strong>SHIFTYPAD</strong> 페이지 우측 상단의 공유 아이콘을
          눌러요.
          <img
            className="sync-help__shot"
            src="/help/shiftypad-share-button.png"
            alt="SHIFTYPAD 페이지 우측 상단, 방패와 물음표 아이콘 오른쪽에 있는 공유 아이콘"
          />
        </li>
        <li>
          <strong>링크 복사하기</strong>를 눌러 URL을 복사해요.
          <img
            className="sync-help__shot"
            src="/help/shiftypad-copy-link.png"
            alt="공유하기 창에서 Facebook·Twitter·Naver·whatsApp 오른쪽에 있는 링크 복사하기 버튼"
          />
        </li>
        <li>복사한 URL을 아래 칸에 붙여넣어요.</li>
        <li>
          나타나는 <strong>니케 로스터 동기화</strong> 링크를 브라우저 북마크 바로
          드래그해요. 북마크 바가 안 보이면 Ctrl+Shift+B로 켤 수 있어요.
        </li>
        <li>
          blablalink에 로그인한 상태에서 그 북마크를 눌러요. 로스터가 새 탭에서
          열려요.
        </li>
      </ol>

      <h3 className="sync-help__heading">다시 동기화할 때</h3>
      <p className="sync-help__text">
        북마크만 다시 누르면 돼요. 공유 URL을 또 붙여넣을 필요는 없어요.
      </p>

      <h3 className="sync-help__heading">계정이 여러 개일 때</h3>
      <p className="sync-help__text">
        계정마다 북마크가 따로 필요해요 — 북마크릿에는 그 계정의 ID가 들어 있어요.
      </p>
      <ol className="sync-help__steps">
        <li>
          추가할 계정의 SHIFTYPAD에서 공유 URL을 복사해 위 1~4단계를 다시 해요.
        </li>
        <li>
          이름이 다 똑같이 "니케 로스터 동기화"라서, 북마크 이름을 계정 이름으로
          바꿔두면 헷갈리지 않아요.
        </li>
        <li>
          <strong>그 계정으로 blablalink에 로그인한 상태에서</strong> 해당 북마크를
          눌러요.
        </li>
      </ol>
      <p className="sync-help__text">
        동기화한 계정은 위쪽 <strong>계정</strong> 드롭다운에서 전환해요. 계정별
        로스터와 추천 결과는 섞이지 않아요.
      </p>
    </div>
  )
}
```

- [ ] **Step 5: SyncRosterPanel에 토글을 붙인다**

세 군데를 고친다.

(a) import에 `SyncHelp`를 더한다. 기존 import 줄들 다음에 놓는다:

```tsx
import { SyncHelp } from './SyncHelp'
```

(b) props 인터페이스에 `defaultHelpOpen`을 더한다:

```tsx
interface SyncRosterPanelProps {
  onImport: (args: {
    openId: string
    nickname: string
    roster: NikkeDraft[]
  }) => void
  /** 활성 프로필이 없는 화면에서는 도움말이 펼쳐진 채로 시작한다 - 아직 아무것도
   * 동기화하지 못한 유저가 토글을 "발견"할 필요가 없어야 한다. */
  defaultHelpOpen?: boolean
}
```

시그니처와 첫 state를 이렇게 바꾼다:

```tsx
export function SyncRosterPanel({ onImport, defaultHelpOpen = false }: SyncRosterPanelProps) {
  const [helpOpen, setHelpOpen] = useState(defaultHelpOpen)
  const [openId, setOpenId] = useState<string | null>(null)
```

(c) `return`의 `<h2>` 한 줄을 제목 행 + 도움말로 교체한다. 바꾸기 전:

```tsx
      <h2 className="sync__title">blablalink에서 동기화</h2>
```

바꾼 뒤:

```tsx
      <div className="sync__header">
        <h2 className="sync__title">blablalink에서 동기화</h2>
        <button
          type="button"
          className="sync__help-toggle"
          aria-expanded={helpOpen}
          aria-controls="sync-help"
          onClick={() => setHelpOpen((open) => !open)}
        >
          동기화 방법
        </button>
      </div>
      <SyncHelp id="sync-help" hidden={!helpOpen} />
```

- [ ] **Step 6: CSS를 추가한다**

`frontend/src/App.css`의 기존 `.sync__hint` 규칙 **바로 다음**에 붙인다(싱크
관련 규칙끼리 모아 두기 위해).

```css
/* 제목과 도움말 토글을 한 줄에. 도움말 본문은 이 행이 아니라 패널 아래로
   전체 폭으로 펼쳐진다. */
.sync__header {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
}

.sync__help-toggle {
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  font-size: 13px;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
}

.sync__help-toggle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.sync-help {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  max-width: 480px;
  padding: var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-2);
  font-size: 13px;
  color: var(--text-muted);
}

/* 위 클래스의 `display`가 `hidden` 속성의 UA 규칙을 이기므로, .panel[hidden]과
   같은 이유로 감추기를 여기서 다시 말해야 한다. */
.sync-help[hidden] {
  display: none;
}

.sync-help__steps {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin: 0;
  padding-left: var(--sp-4);
}

.sync-help__heading {
  margin: var(--sp-2) 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.sync-help__text {
  margin: 0;
}

.sync-help__shot {
  display: block;
  max-width: 100%;
  margin-top: var(--sp-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
```

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

```bash
cd frontend && npm test -- --run src/components/SyncRosterPanel.test.tsx
```

기대: 10 passed (기존 7 + 신규 3).

- [ ] **Step 8: 커밋**

```bash
git add frontend/public/help frontend/src/components/SyncHelp.tsx \
        frontend/src/components/SyncRosterPanel.tsx \
        frontend/src/components/SyncRosterPanel.test.tsx frontend/src/App.css
git commit -m "Add an inline sync help panel behind a '동기화 방법' toggle

The share URL a sync starts from is reached through two unlabelled icons, so
prose alone cannot point at them - the two captures do. The body is always
rendered and hidden by attribute rather than conditionally mounted, so the
toggle's aria-controls always resolves."
```

---

### Task 2: App 배선과 기존 힌트 어미 통일

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/SyncRosterPanel.tsx`
- Test: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Task 1의 `SyncRosterPanel`의 `defaultHelpOpen?: boolean` prop과
  접근 가능한 이름이 `동기화 방법`인 토글 버튼.
- Produces: 없음(마지막 태스크).

- [ ] **Step 1: 실패 테스트 2건을 작성한다**

`frontend/src/App.test.tsx`의 `describe('App', ...)` 블록 맨 끝에 붙인다.
`seedProfiles`와 `beforeEach`의 `localStorage.clear()`는 이미 파일에 있다.

```tsx
  it('활성 프로필이 없는 화면에서는 동기화 도움말이 펼쳐져 있다', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('이미 동기화한 계정이 있으면 로스터 탭의 도움말은 접혀 있다', () => {
    seedProfiles({
      activeOpenId: 'open-1',
      profiles: {
        'open-1': {
          openId: 'open-1',
          nickname: 'Fienn',
          roster: [],
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
      },
    })
    render(<App />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npm test -- --run src/App.test.tsx
```

기대: 첫 번째 신규 테스트가 FAIL(`aria-expanded`가 `"false"`로 나옴). 두 번째는
이미 PASS일 수 있다 — 그래도 회귀 가드로 남긴다(스펙 결정 4번의 나머지 절반이다).

- [ ] **Step 3: App.tsx에서 프로필 없는 화면에만 prop을 넘긴다**

`frontend/src/App.tsx`에서 `activeProfile === null` 분기의 한 줄을 바꾼다.
바꾸기 전:

```tsx
          <SyncRosterPanel onImport={upsertProfile} />
```

바꾼 뒤:

```tsx
          <SyncRosterPanel onImport={upsertProfile} defaultHelpOpen />
```

**주의:** `SyncRosterPanel`은 이 파일에 두 번 나온다. 고칠 것은 `activeProfile
=== null`의 `<main className="app__main">` 안에 있는 쪽이고, 로스터 탭
(`id="panel-roster"`) 안의 것은 **그대로 둔다**.

- [ ] **Step 4: 기존 힌트의 어미를 맞춘다**

`frontend/src/components/SyncRosterPanel.tsx`의 `sync__hint` 문단이 혼자
"-하세요"체다. 도움말과 앱 나머지의 "-어요"체로 맞춘다. 바꾸기 전:

```tsx
            이 링크를 북마크 바로 드래그한 다음, blablalink에 로그인한 상태에서
            클릭하세요. 로스터가 새 탭에서 열리므로, 이 탭은 새로고침해야
            갱신돼요.
```

바꾼 뒤:

```tsx
            이 링크를 북마크 바로 드래그한 다음, blablalink에 로그인한 상태에서
            눌러요. 로스터가 새 탭에서 열리므로, 이 탭은 새로고침해야 갱신돼요.
```

이 힌트는 도움말과 중복되지만 **남긴다** — 도움말은 접혀 있을 수 있고, 이
문장은 북마크릿 링크가 바로 옆에 있는 순간에만 의미가 있다(스펙 "범위" 절).

- [ ] **Step 5: 전체 스위트와 타입체크를 돌린다**

```bash
cd frontend && npm test -- --run && npx tsc -b
```

기대: **299 passed / 38 files**, `tsc -b`는 출력 없이 종료(클린).

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx \
        frontend/src/components/SyncRosterPanel.tsx
git commit -m "Open the sync help by default where nothing is synced yet

The panel renders on two screens. On the one reached with no active profile
the user has not managed a sync at all, so the help should not have to be
discovered; in the roster tab of someone already synced it stays folded."
```

---

## 남은 확인 (구현 후, 사람이 한다)

- [ ] `npm run dev` + 백엔드(`uvicorn`)를 띄우고 브라우저에서 종단 확인:
      프로필이 없는 첫 화면에서 도움말이 펼쳐져 있는지, 스크린샷 2장이 실제로
      뜨는지(경로 오타는 테스트가 못 잡는다 — jsdom은 이미지를 불러오지 않는다),
      로스터 탭에서는 접혀 있는지, 좁은 화면에서 가로 스크롤이 생기지 않는지.
- [ ] `docs/roadmap.md`의 백로그 3건 항목에서 "Sync from blablalink 옆 도움말
      버튼"을 완료로 옮기고 기준선(299)을 기록한다.
