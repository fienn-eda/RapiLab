# 보스 설정 — 약점 속성 · 속성저지 · 코어 2관통 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보스 설정 폼이 약점 속성을 아이콘으로 받고, 속성저지 기믹을 덱 탐색 제약으로
반영하며, 코어와 본체가 별개인 보스에서 관통 유닛의 탄이 두 번 들어가게 한다.

**Architecture:** 세 항목은 서로 독립적이다. (A) 약점 ↔ 보스 본인 속성 변환은 **UI
경계에서만** 일어나고 와이어의 `element`는 보스 본인 속성 그대로다. (B) 속성저지는 덱
**생성 시점**의 술어로 들어가며, 5덱 배분은 peel 배분 + 힐클라임 가드로 "채울 수 있는
덱까지만" 만족시킨다. (C) 코어 2관통은 phase 2 damage_log에서 인스턴스를 하나 더 낳는
것으로 끝난다.

**Tech Stack:** Python 3 / FastAPI / pytest (backend), React 19 + TypeScript + Vite /
Vitest + Testing Library (frontend).

**설계 문서:** `docs/superpowers/specs/2026-08-03-boss-weakness-and-gimmick-fields-design.md`

## Global Constraints

- **트렁크는 `wip/scaffolding`이다.** `main` 브랜치도 원격도 없다. 이 작업은
  `wip/boss-weakness-and-gimmicks` 브랜치에서 진행한다(이미 생성됨).
- **백엔드 테스트:** 리포 루트에서 `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`.
  PowerShell이면 `cd backend; $env:PYTHONIOENCODING='utf-8'; python -m pytest tests/ -q`.
  `PYTHONIOENCODING`이 없으면 콘솔이 cp949라 한글 이름에서 터진다.
- **프론트 테스트:** `cd frontend && npm test` (vitest run).
- **기준선:** 착수 시점 백엔드 **1810 passed / 3 skipped**, 프론트 **467 passed**.
  떨어지면 회귀다. (초판에 적힌 1788은 낡은 숫자였다 — Task 5의 구현자가 stash로 실측해
  1810을 확인했다. 각 Task는 자기 앞의 Task들이 더한 테스트만큼 올라간 값을 기대할 것.)
- **캘리브레이션 불변.** 세 항목 전부 기본값이 off/기존 동작이라, 기록 덱 5개의 합계
  **1.077x**가 움직이면 그 자체가 회귀다. Task 13에서 확인한다.
- **와이어의 `BossProfile.element`는 끝까지 보스 본인 속성이다.** 약점으로 바꾸지 않는다.
- **엔진 속성 이름은 `Fire`/`Water`/`Wind`/`Iron`/`Electric`.** blablalink의
  `electronic`은 다운로드 스크립트 한 곳에서만 등장한다.
- **한글 UI 문구는 한국 서버 공식 표기를 쓴다:** 작열 · 수냉 · 풍압 · 철갑 · 전격
  (`frontend/src/lib/elementName.ts`가 이미 그 표를 갖고 있다).
- **커밋은 작업 단위로 자주.** pre-commit 훅을 절대 건너뛰지 않는다.

---

## File Structure

### 생성

| 파일 | 책임 |
| --- | --- |
| `scripts/download_element_icons.py` | 5개 속성 아이콘을 `frontend/public/elements/`로 받는다 |
| `frontend/public/elements/{fire,water,wind,iron,electric}.png` | 아이콘 자산 |
| `frontend/src/lib/elementAdvantage.ts` | 약점 ↔ 보스 본인 속성 변환 (엔진 순환의 TS 거울) |
| `frontend/src/lib/elementAdvantage.test.ts` | 위의 왕복 테스트 |
| `backend/tests/test_core_pierce_hits_body.py` | 코어 2관통 엔진 동작 |
| `backend/tests/test_elemental_interrupt_constraint.py` | 속성저지 술어 + 탐색 제약 |

### 수정

| 파일 | 무엇이 바뀌나 |
| --- | --- |
| `backend/app/elements.py` | `weakness_of()` 신설 — 순환의 역방향 |
| `backend/app/raid_simulator.py` | `pierce_hits_body_behind_core` 파라미터 + phase 2 인스턴스 분기 |
| `backend/app/deck_search.py` | `BossProfile` 두 필드 · `deck_breaks_gimmick` · 생성기 `deck_filter` · 풀 보강 |
| `backend/app/deck_allocation.py` | peel 배분 필터 + 힐클라임 가드 |
| `backend/app/api.py` | `BossProfileIn` 두 필드 |
| `backend/tests/test_api_boss_profile.py` | `evaluate_deck`이 보스 필드를 흘리지 않는다는 테스트 |
| `frontend/src/types/recommend.ts` | `BossProfile` 두 필드 |
| `frontend/src/types/bossProfileDraft.ts` | draft 두 필드 + 검증 통과 |
| `frontend/src/components/BossProfileField.tsx` | 아이콘 라디오 그룹 · 새 체크박스 2개 · `showElementalInterrupt` prop |
| `frontend/src/components/EvaluationResults.tsx` | 덱 라벨을 약점 표기로 |
| `frontend/src/components/DeckCard.tsx` | `UnitLookups.gimmickUnmetFor` + ⚠ 배지 |
| `frontend/src/components/RecommendPanel.tsx` | `gimmickUnmetFor` 계산·전달 |
| `frontend/src/components/UnionRaidPanel.tsx` | 체크박스 숨김 prop 전달 |
| `frontend/src/lib/helpText.ts` | 새 항목 두 개의 설명 |
| `frontend/src/App.css` | 아이콘 라디오 그룹 · ⚠ 배지 스타일 |
| `docs/roadmap.md` · `docs/insights.md` · `docs/decisions.md` | 착륙 기록 |

---

# Phase A — 약점 속성 아이콘

## Task 1: 속성 아이콘 다운로드 스크립트

**Files:**
- Create: `scripts/download_element_icons.py`
- Create (스크립트 산출물): `frontend/public/elements/{fire,water,wind,iron,electric}.png`

**Interfaces:**
- Produces: `/elements/<element>.png` — 프론트가 절대경로로 읽는 5개 자산.
  파일명은 소문자 엔진 속성명(`electric`, `electronic`이 아니다).

- [ ] **Step 1: 스크립트를 쓴다**

`scripts/download_element_icons.py`:

```python
#!/usr/bin/env python
"""Download the five element (code) icons the boss form draws.

WHY
    The boss form picks the boss's WEAKNESS by icon rather than by a dropdown,
    so the app needs the five code icons on disk. RapiLab ships as an installed
    WebView2 app, so hotlinking blablalink's CDN would leave the picker blank
    offline (and break outright if the CDN path rotates) - the same reason
    scripts/download_portraits.py exists.

WHEN TO USE
    - One-shot to populate frontend/public/elements/.
    - Again only if blablalink changes the asset paths below.

WHAT IT DOES
    Downloads five PNGs into frontend/public/elements/, named by the ENGINE's
    element names. blablalink calls the electric code "electronic"; that spelling
    is confined to this file's URL table, exactly as backend/app/shiftypad_normalize.py
    confines it on the data side.

    Idempotent: skips files already on disk unless --force is given.

USAGE
    python scripts/download_element_icons.py
    python scripts/download_element_icons.py --force
    python scripts/download_element_icons.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "frontend" / "public" / "elements"

BASE_URL = ("https://www.blablalink.com/assets/nikke/version/default"
            "/shiftysassets/images")

# engine element name -> blablalink's icon basename. "electronic" is
# blablalink's spelling of the engine's "Electric" and lives only here.
ICONS = {
    "fire": "icon-code-fire.png",
    "water": "icon-code-water.png",
    "wind": "icon-code-wind.png",
    "iron": "icon-code-iron.png",
    "electric": "icon-code-electronic.png",
}


def download(url: str, dest: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "RapiLab/element-icons"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; download nothing")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fetched = skipped = 0
    failed: list[str] = []
    for element, basename in sorted(ICONS.items()):
        dest = OUT_DIR / f"{element}.png"
        url = f"{BASE_URL}/{basename}"
        if dest.exists() and not args.force:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  would fetch {url} -> {dest.relative_to(REPO)}")
            continue
        try:
            n = download(url, dest)
            print(f"  fetched {dest.name} ({n:,} bytes)")
            fetched += 1
            time.sleep(0.2)  # be polite to the CDN
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{dest.name}: {exc}")
            print(f"  FAILED {url}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"dry-run: would fetch {len(ICONS) - skipped}, skip {skipped} existing")
        return 0
    print(f"done: fetched {fetched}, skipped {skipped}, failed {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: dry-run으로 URL을 확인한다**

Run: `python scripts/download_element_icons.py --dry-run`
Expected: 5줄의 `would fetch https://www.blablalink.com/.../icon-code-*.png -> frontend/public/elements/*.png`

- [ ] **Step 3: 실제로 받는다**

Run: `python scripts/download_element_icons.py`
Expected: `done: fetched 5, skipped 0, failed 0`

- [ ] **Step 4: 5개 파일이 생겼는지 확인한다**

Run: `ls frontend/public/elements/`
Expected: `electric.png  fire.png  iron.png  water.png  wind.png`

받은 파일이 0바이트이거나 HTML이면(CDN이 에러 페이지를 200으로 주는 경우) 여기서 멈추고
Fienn에게 알린다. 확인: 각 파일이 1KB 이상이고 `file` 또는 헤더가 PNG여야 한다.

- [ ] **Step 5: 커밋**

```bash
git add scripts/download_element_icons.py frontend/public/elements/
git commit -m "Download the five code icons the boss weakness picker draws"
```

---

## Task 2: 약점 ↔ 보스 본인 속성 변환

**Files:**
- Create: `frontend/src/lib/elementAdvantage.ts`
- Test: `frontend/src/lib/elementAdvantage.test.ts`

**Interfaces:**
- Consumes: `NikkeElement` from `../types/supportedUnit`
- Produces:
  - `bossElementFor(weakness: NikkeElement): NikkeElement` — 이 약점을 가진 보스의 본인 속성
  - `weaknessFor(boss: NikkeElement): NikkeElement` — 이 보스를 이기는 속성
  - 둘은 서로의 역함수. Task 3·4가 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/lib/elementAdvantage.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { bossElementFor, weaknessFor } from './elementAdvantage'
import type { NikkeElement } from '../types/supportedUnit'

const ALL: NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']

describe('elementAdvantage', () => {
  it('수냉이 약점인 보스는 작열이다', () => {
    expect(bossElementFor('Water')).toBe('Fire')
    expect(weaknessFor('Fire')).toBe('Water')
  })

  it('두 함수는 서로의 역함수다', () => {
    for (const element of ALL) {
      expect(weaknessFor(bossElementFor(element))).toBe(element)
      expect(bossElementFor(weaknessFor(element))).toBe(element)
    }
  })

  it('엔진의 순환을 그대로 담는다', () => {
    // backend/app/elements.py: Water > Fire > Wind > Iron > Electric > Water
    expect(ALL.map(bossElementFor)).toEqual(['Wind', 'Fire', 'Iron', 'Electric', 'Water'])
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd frontend && npx vitest run src/lib/elementAdvantage.test.ts`
Expected: FAIL — `Failed to resolve import "./elementAdvantage"`

- [ ] **Step 3: 최소 구현을 쓴다**

`frontend/src/lib/elementAdvantage.ts`:

```ts
// 약점 속성 ↔ 보스 본인 속성. 화면은 약점으로 말하고, 와이어는 보스 본인 속성을
// 실어 나른다 — boss_is_element 조건부 스킬(브리드의 풍압코드 피해량 증가)이
// 후자를 읽기 때문이다. 변환은 이 파일 하나를 통해서만 일어난다.
//
// SOURCE OF TRUTH: backend/app/elements.py
//   Water > Fire > Wind > Iron > Electric > Water

import type { NikkeElement } from '../types/supportedUnit'

/** 공격 속성 -> 그 속성이 이기는 속성. */
const STRONG_AGAINST: Record<NikkeElement, NikkeElement> = {
  Water: 'Fire',
  Fire: 'Wind',
  Wind: 'Iron',
  Iron: 'Electric',
  Electric: 'Water',
}

const WEAK_TO = Object.fromEntries(
  Object.entries(STRONG_AGAINST).map(([attacker, beaten]) => [beaten, attacker]),
) as Record<NikkeElement, NikkeElement>

/** 이 속성이 약점인 보스의 본인 속성. 'Water'(수냉 약점) -> 'Fire'(작열 보스) */
export const bossElementFor = (weakness: NikkeElement): NikkeElement =>
  STRONG_AGAINST[weakness]

/** 이 보스를 이기는 속성. 'Fire'(작열 보스) -> 'Water'(수냉이 약점) */
export const weaknessFor = (boss: NikkeElement): NikkeElement => WEAK_TO[boss]
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd frontend && npx vitest run src/lib/elementAdvantage.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/elementAdvantage.ts frontend/src/lib/elementAdvantage.test.ts
git commit -m "Convert between a boss's weakness and its own element"
```

---

## Task 3: 보스 폼의 아이콘 라디오 그룹

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx:42-64` (속성 `<select>` 블록)
- Modify: `frontend/src/App.css` (Fields 절 끝, `.field-row--overload` 뒤)
- Test: `frontend/src/components/BossProfileField.test.tsx`

**Interfaces:**
- Consumes: `bossElementFor` / `weaknessFor` (Task 2), `/elements/<element>.png` (Task 1)
- Produces: `BossProfileDraft.element`는 여전히 **보스 본인 속성**. 폼의 계약은 안 바뀐다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/BossProfileField.test.tsx`에 아래 `describe`를 파일 끝에 덧붙인다:

```tsx
describe('BossProfileField 약점 속성 선택', () => {
  it('약점 아이콘을 고르면 보스 본인 속성이 draft로 간다', async () => {
    // 화면은 약점으로 말하고 와이어는 보스 본인 속성을 나른다. 수냉이 약점이면
    // 보스는 작열이다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('수냉'))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ element: 'Fire' }))
  })

  it('저장된 보스 속성이 대응하는 약점 아이콘을 선택 상태로 그린다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('수냉')).toBeChecked()
    expect(screen.getByLabelText('작열')).not.toBeChecked()
  })

  it('약점 없음이 null로 왕복한다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire' }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('약점 없음'))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ element: null }))
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx`
Expected: FAIL — `Unable to find a label with the text of: 수냉` (아직 `<select>`다)

- [ ] **Step 3: 라디오 그룹을 구현한다**

`BossProfileField.tsx`의 import에 추가:

```tsx
import { bossElementFor, weaknessFor } from '../lib/elementAdvantage'
import type { NikkeElement } from '../types/supportedUnit'
```

`RANGE_BAND_LABEL` 아래에 추가:

```tsx
// 화면에 그리는 것은 보스 본인 속성이 아니라 그 보스를 이기는 속성이다 — 플레이어가
// 편성할 때 보는 값이 그쪽이기 때문. 아이콘은 blablalink의 코드 아이콘을
// scripts/download_element_icons.py로 받아둔 것이다.
const WEAKNESS_ICON: Record<NikkeElement, string> = {
  Fire: '/elements/fire.png',
  Water: '/elements/water.png',
  Wind: '/elements/wind.png',
  Iron: '/elements/iron.png',
  Electric: '/elements/electric.png',
}

const WEAKNESS_CHOICES: NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']
```

`elementId`를 쓰던 블록(42~64행)을 통째로 교체:

```tsx
      <div className="field">
        <span className="field__label" id={`${elementId}-label`}>
          보스 약점 속성
        </span>
        {/* 진짜 라디오를 시각적으로만 숨긴다. div/button으로 만들면 화살표 이동과
            화면 낭독기의 그룹 읽기를 둘 다 잃는다. */}
        <div className="element-picker" role="radiogroup" aria-labelledby={`${elementId}-label`}>
          {WEAKNESS_CHOICES.map((weakness) => {
            const bossElement = bossElementFor(weakness)
            return (
              <label
                key={weakness}
                className="element-picker__option"
                data-element={weakness}
              >
                <input
                  type="radio"
                  className="visually-hidden"
                  name={elementId}
                  checked={value.element === bossElement}
                  onChange={() => onChange({ ...value, element: bossElement })}
                />
                <img className="element-picker__icon" src={WEAKNESS_ICON[weakness]} alt="" />
                <span className="element-picker__name">{elementLabel(weakness)}</span>
              </label>
            )
          })}
          <label className="element-picker__option element-picker__option--none">
            <input
              type="radio"
              className="visually-hidden"
              name={elementId}
              checked={value.element === null}
              onChange={() => onChange({ ...value, element: null })}
            />
            <span className="element-picker__name">약점 없음</span>
          </label>
        </div>
      </div>
```

`weaknessFor`는 이 컴포넌트에서 안 쓰이므로 import에서 뺀다(Task 4가 쓴다). 더는 쓰이지
않는 `BOSS_ELEMENTS` / `BossElement` import도 정리한다 — `oxlint`가 잡는다.

- [ ] **Step 4: CSS를 넣는다**

`frontend/src/App.css`의 `.field-row--overload .field:first-child { ... }` 블록 바로 뒤에
추가:

```css
/* Element picker ---------------------------------------------------------- */

/* 보스의 약점을 코드 아이콘으로 고른다. 라디오 자체는 .visually-hidden으로 숨고,
   선택 표시는 라벨이 :has()로 그린다 — 아이콘이 곧 히트 영역이라 라벨을 그대로
   버튼처럼 쓸 수 있다. */
.element-picker {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.element-picker__option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-1);
  padding: var(--sp-2);
  min-width: 56px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  cursor: pointer;
}

.element-picker__option:has(input:checked) {
  border-color: var(--element, var(--accent));
  background: var(--surface);
}

.element-picker__option:has(input:focus-visible) {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.element-picker__icon {
  width: 28px;
  height: 28px;
}

.element-picker__name {
  font-size: 12px;
  color: var(--text-muted);
}

.element-picker__option:has(input:checked) .element-picker__name {
  color: var(--text);
}

/* "약점 없음"에는 아이콘이 없으므로 아이콘 자리만큼 높이를 맞춘다. */
.element-picker__option--none {
  justify-content: center;
}

.element-picker__option[data-element='Fire'] {
  --element: var(--el-fire);
}
.element-picker__option[data-element='Water'] {
  --element: var(--el-water);
}
.element-picker__option[data-element='Wind'] {
  --element: var(--el-wind);
}
.element-picker__option[data-element='Iron'] {
  --element: var(--el-iron);
}
.element-picker__option[data-element='Electric'] {
  --element: var(--el-electric);
}
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx`
Expected: PASS (기존 3개 + 새 3개 = 6 tests)

- [ ] **Step 6: 프론트 전체 테스트 + 린트**

Run: `cd frontend && npm test && npm run lint && npm run build`
Expected: 467 passed 이상, 린트/타입 에러 없음. `<select>`를 참조하던 다른 테스트가
깨지면 고친다(`RecommendPanel.test.tsx` / `UnionRaidPanel.test.tsx`에서
`getByLabelText('보스 속성')` 류를 쓰고 있으면 아이콘 라벨로 바꾼다).

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/BossProfileField.tsx frontend/src/components/BossProfileField.test.tsx frontend/src/App.css
git commit -m "Pick the boss's weakness by code icon instead of naming the boss's element"
```

---

## Task 4: 결과 카드 라벨을 약점 표기로

**Files:**
- Modify: `frontend/src/components/EvaluationResults.tsx:13-14, 41`
- Test: `frontend/src/components/EvaluationResults.test.tsx` (없으면 생성)

**Interfaces:**
- Consumes: `weaknessFor` (Task 2)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/EvaluationResults.test.tsx`에 추가(파일이 없으면 아래 전체로 생성):

```tsx
// 화면 전체가 약점으로 말하는데 결과 카드만 보스 본인 속성으로 말하면 읽는 사람이
// 머릿속에서 순환을 한 번 더 돌려야 한다.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvaluationResults } from './EvaluationResults'

const DECK = {
  deck: ['a', 'b', 'c', 'd', 'e'],
  total_damage: 1000,
  burst_damage: 500,
  normal_attack_damage: 400,
  skill_damage: 100,
}

describe('EvaluationResults 덱 라벨', () => {
  it('보스 본인 속성이 아니라 약점 속성으로 라벨한다', () => {
    render(
      <EvaluationResults decks={[DECK]} combinedTotalDamage={1000} bossElements={['Fire']} />,
    )

    expect(screen.getByText('1번 덱 · 약점 수냉')).toBeInTheDocument()
  })

  it('무속성 보스는 그대로 무속성이다', () => {
    render(
      <EvaluationResults decks={[DECK]} combinedTotalDamage={1000} bossElements={[null]} />,
    )

    expect(screen.getByText('1번 덱 · 무속성')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/EvaluationResults.test.tsx`
Expected: FAIL — 첫 테스트가 `1번 덱 · 작열`을 그리고 있어 텍스트를 못 찾는다

- [ ] **Step 3: 라벨을 바꾼다**

`EvaluationResults.tsx`:

```tsx
import { weaknessFor } from '../lib/elementAdvantage'

// 보스의 본인 속성이 아니라 약점을 이름 붙인다 — 보스 폼이 받는 것이 약점이므로,
// 결과가 본인 속성으로 말하면 두 화면이 다른 언어를 쓰게 된다.
const bossElementLabel = (element: BossElement): string =>
  element === null ? '무속성' : `약점 ${elementLabel(weaknessFor(element))}`
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/EvaluationResults.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: 프론트 전체 테스트**

Run: `cd frontend && npm test`
Expected: 전부 통과. `UnionRaidPanel.test.tsx`가 `작열` 라벨을 기대하고 있으면 고친다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/EvaluationResults.tsx frontend/src/components/EvaluationResults.test.tsx
git commit -m "Label a scored deck by the boss's weakness, matching the form"
```

---

# Phase C — 상시 코어 2관통

## Task 5: 엔진 — 관통 통상공격이 본체까지 때린다

**Files:**
- Modify: `backend/app/raid_simulator.py` (`simulate_raid` 시그니처 ~478행, phase 2 damage_log ~1442행)
- Test: `backend/tests/test_core_pierce_hits_body.py` (신규)

**Interfaces:**
- Produces: `simulate_raid(..., pierce_hits_body_behind_core=False)` — Task 6이 배선한다.
  기본값 False라 기존 호출자는 전부 불변.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_core_pierce_hits_body.py`:

```python
"""A boss whose core is a separate object from its body: a Pierce holder's shot
passes through the core and lands on the body behind it, so one normal attack
produces TWO damage instances.

The body hit is the same instance minus the core bonus (Fienn, 2026-08-03), so
with no other major modifiers the pair reads (1 + 1.0) + 1 = 3.0 against the core
hit's 2.0. The numbers below are pinned rather than expressed as "1.5x": that
ratio is only true while CORE_HIT_BONUS is 1.0, and a test that hides the
constant would keep passing if the constant moved.

A unit without Pierce can still hit the core, but nothing is behind it for her.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

DECK = [
    {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    {"slug": "striker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0, "weapon": "AR"},
]
BASE_STATS = {s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in DECK}
# 100% of ATK per shot with no reload, so one normal attack's damage IS the bucket.
WEAPON = {"weapon": "AR", "damage_percent": 100.0, "max_ammo": 999,
          "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0}

HOLDS_PIERCE = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]


def _log(striker_rules, *, core_hittable=True, two_pierce=True, per_shot_rules=None):
    return simulate_raid(
        DECK,
        {"b1": [], "b2": [], "striker": striker_rules},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        # The fight ends before any Full Burst window opens, so the core bonus is
        # the only major modifier in play.
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={"striker": WEAPON},
        core_hittable=core_hittable,
        pierce_hits_body_behind_core=two_pierce,
        per_shot_rules=per_shot_rules,
    )["damage_log"]


def _shots(log):
    return [e["damage"] for e in log if e["source"] == "normal_attack"]


def test_a_pierce_holders_shot_lands_on_the_core_and_the_body():
    log = _log(HOLDS_PIERCE)
    off = _log(HOLDS_PIERCE, two_pierce=False)

    assert len(_shots(log)) == 2 * len(_shots(off))
    # core 10000 x (1 + 1.0), body 10000 x 1
    assert _shots(log)[:2] == [20000.0, 10000.0]
    assert sum(_shots(log)) == 1.5 * sum(_shots(off))


def test_a_unit_without_pierce_is_untouched():
    assert _shots(_log([])) == _shots(_log([], two_pierce=False))


def test_a_pierce_holders_skill_damage_still_lands_once():
    # Pierce is a property of NORMAL ATTACKS. A per-shot nuke fired by the same
    # unit at the same instant has nothing behind the core to hit.
    nuke = {"striker": [(1, "every", [instant_nuke_pulse_rule("per_shot", 100.0)])]}
    log = _log(HOLDS_PIERCE, per_shot_rules=nuke)
    off = _log(HOLDS_PIERCE, two_pierce=False, per_shot_rules=nuke)

    pulses = [e["damage"] for e in log if e["source"] == "per_shot_nuke"]
    assert pulses == [e["damage"] for e in off if e["source"] == "per_shot_nuke"]


def test_the_flag_does_nothing_when_the_core_cannot_be_hit():
    # There is no 2-pierce without a core to pierce, so the flag has to be inert
    # rather than silently doubling body damage.
    assert _shots(_log(HOLDS_PIERCE, core_hittable=False)) == _shots(
        _log(HOLDS_PIERCE, core_hittable=False, two_pierce=False))


def test_only_the_shots_inside_the_pierce_window_land_twice():
    # Pierce for 0.5 sec: the early shots pass through, the later ones still hit
    # the core but have nothing behind it to reach.
    lapsed = [buff_rule("battle_start", [("has_pierce", 1.0, "self", 0.5)])]
    shots = _shots(_log(lapsed))

    assert shots[:2] == [20000.0, 10000.0]   # first shot: core, then body
    assert shots[-1] == 20000.0              # window lapsed: core only
    assert len(shots) > len(_shots(_log(lapsed, two_pierce=False)))


def test_a_weapon_transform_shot_lands_twice_too():
    """A transform segment fires through the SAME shot loop and is recorded as
    "normal_attack", so it needs no special casing - this pins that it really is
    so (design C.5). It matters because the units that hold Pierce and the units
    that transform are largely the same list: Maxwell and Snow White gain Pierce
    for exactly the one charged shot their transform is, and Red Hood holds it
    continuously, so on this boss her transform shots AND her base-weapon shots
    both land twice.
    """
    def schedule(context, fight_duration):
        return [{"start": 0.0, "end": 1.5,
                 "profile": {"weapon": "SR", "damage_percent": 500.0,
                             "charge_time": 0.0, "charge_damage_percent": 100.0}}]

    def run(two_pierce):
        return simulate_raid(
            DECK,
            {"b1": [], "b2": [], "striker": HOLDS_PIERCE},
            burst_damage_percents={"striker": 100.0},
            base_stats=BASE_STATS, enemy_def=0, gauge_charge_time=30.0,
            fight_duration=1.5, base_crit_rate=0.0,
            weapon_stats={"striker": WEAPON},
            weapon_mode_schedules={"striker": schedule},
            core_hittable=True,
            pierce_hits_body_behind_core=two_pierce,
        )["damage_log"]

    on, off = _shots(run(True)), _shots(run(False))

    assert off, "fixture broken: the transform window produced no normal attacks"
    assert len(on) == 2 * len(off)
    assert sum(on) == 1.5 * sum(off)
    # the transform's own shot: core 10000 x 5.0 x (1 + 1.0), body without the bonus
    assert 100000.0 in on and 50000.0 in on
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_core_pierce_hits_body.py -q`
Expected: FAIL — `simulate_raid() got an unexpected keyword argument 'pierce_hits_body_behind_core'`

- [ ] **Step 3: 시그니처에 파라미터를 더한다**

`raid_simulator.py`의 `simulate_raid` 시그니처에서 `part_destructible=False,` 바로 뒤에:

```python
    # A boss that keeps its core as a separate object from its body: a Pierce
    # holder's shot passes through the core and lands on the body behind it, so
    # one normal attack produces two instances (Fienn, 2026-08-03). Read together
    # with `core_hittable` below - there is no 2-pierce without a core to pierce,
    # so a caller that sets this without core_hittable gets nothing.
    pierce_hits_body_behind_core=False,
```

- [ ] **Step 4: phase 2의 damage_log를 고친다**

`raid_simulator.py`의 `damage_log = [...]` 리스트 컴프리헨션(현재 1442~1464행)을 통째로
아래로 교체한다:

```python
    def _entries(ev):
        """One damage entry per event - or TWO when a Pierce holder's normal
        attack strikes a core the boss keeps as a separate object from its body.
        The shot passes through the core and lands on the body behind it, and the
        body hit is the same instance minus the core bonus (Fienn, 2026-08-03).

        `hits_core` already folds in `core_hittable`, so the second instance
        cannot appear in a fight with no hittable core.
        """
        is_normal_attack = ev["source"] == "normal_attack"
        percent = _normal_attack_percent(ev) if is_normal_attack else _resolve_percent(ev)
        hits_core = core_hittable and (
            core_eligible(ev["source"], ev["damage_type"])
            if ev["core_eligible_override"] is None
            else ev["core_eligible_override"]
        )

        def instance(on_core):
            return {
                "slug": ev["slug"],
                "time": ev["time"],
                "damage": _damage_instance(
                    ev["slug"], percent, ev["time"],
                    damage_type=ev["damage_type"],
                    extra_charge_bonus=ev["extra_charge_bonus"],
                    extra_flat_atk=ev["extra_flat_atk"],
                    hits_core=on_core,
                    on_charge_weapon=ev["on_charge_weapon"],
                    is_normal_attack=is_normal_attack,
                ),
                "source": ev["source"],
                "damage_type": ev["damage_type"],
            }

        pierces = (
            pierce_hits_body_behind_core
            and hits_core
            and is_normal_attack
            and _stat_bundle(ev["slug"], ev["time"])["has_pierce"] > 0
        )
        # The body hit keeps `source` = "normal_attack", so a caller's
        # burst/normal/skill split (deck_search._summarize) still adds up.
        return [instance(True), instance(False)] if pierces else [instance(hits_core)]

    damage_log = [entry for ev in damage_events for entry in _entries(ev)]
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_core_pierce_hits_body.py -q`
Expected: PASS (6 tests)

- [ ] **Step 6: 백엔드 전체 테스트**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: 1788 passed / 3 skipped 이상. 기본값이 False라 한 건도 안 움직여야 한다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/raid_simulator.py backend/tests/test_core_pierce_hits_body.py
git commit -m "Land a pierce holder's shot on the body behind a separate core"
```

---

## Task 6: 보스 프로필 → 엔진 배선 (그리고 흘리지 않는다는 보증)

**Files:**
- Modify: `backend/app/deck_search.py` (`BossProfile` ~132행, `evaluate_deck` ~264행)
- Modify: `backend/app/api.py:49-60` (`BossProfileIn`)
- Test: `backend/tests/test_api_boss_profile.py`

**Interfaces:**
- Consumes: `simulate_raid(..., pierce_hits_body_behind_core=...)` (Task 5)
- Produces: `BossProfile.pierce_hits_body_behind_core: bool = False`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_api_boss_profile.py` 끝에 덧붙인다:

```python
def test_the_pierce_flag_a_caller_sends_is_the_flag_the_engine_gets():
    assert boss_profile(BossProfileIn(
        pierce_hits_body_behind_core=True)).pierce_hits_body_behind_core is True


def test_evaluate_deck_forwards_every_boss_field_the_simulator_accepts(monkeypatch):
    """The API's spread fixed one listing trap; this is the same trap one layer
    down. `evaluate_deck` hands simulate_raid its boss kwargs by NAME, so a new
    BossProfile field reaches the wire, reaches the engine's dataclass, and then
    silently stops - exactly how `effective_range_band` was lost on 2026-07-31.
    """
    import inspect

    from app import deck_search

    # BossProfile field -> simulate_raid parameter, where the two differ.
    ALIASES = {"element": "boss_element"}

    captured = {}

    def fake_simulate_raid(**kwargs):
        captured.update(kwargs)
        return {"total_damage": 0.0, "damage_log": [], "events": []}

    monkeypatch.setattr(deck_search, "assemble_simulation_inputs", lambda deck: {})
    monkeypatch.setattr(deck_search, "simulate_raid", fake_simulate_raid)
    deck_search.evaluate_deck([], deck_search.BossProfile())

    sim_params = set(inspect.signature(simulate_raid).parameters)
    expected = {ALIASES.get(f.name, f.name)
                for f in dataclasses.fields(deck_search.BossProfile)} & sim_params

    assert expected <= set(captured), (
        f"evaluate_deck drops boss fields the simulator accepts: "
        f"{sorted(expected - set(captured))}")
```

파일 상단 import에 추가:

```python
from app.raid_simulator import simulate_raid
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_api_boss_profile.py -q`
Expected: FAIL — 첫 테스트가 `BossProfileIn`에 없는 필드로 터지고, 두 번째는
`evaluate_deck drops boss fields the simulator accepts: ['pierce_hits_body_behind_core']`

- [ ] **Step 3: 세 곳을 배선한다**

`deck_search.py`의 `BossProfile`에서 `effective_range_band: str | None = None` 뒤에:

```python
    # This boss keeps its core as a separate object from its body, so a Pierce
    # holder's shot passes through the core and hits the body behind it - one
    # normal attack, two instances. Depends on `core_hittable`: there is nothing
    # to pierce through without a hittable core, and raid_simulator reads the two
    # together rather than trusting the caller not to send the contradiction.
    pierce_hits_body_behind_core: bool = False
```

`evaluate_deck`의 `simulate_raid(...)` 호출에 추가:

```python
        pierce_hits_body_behind_core=boss.pierce_hits_body_behind_core,
```

`api.py`의 `BossProfileIn`에서 `effective_range_band` 뒤에:

```python
    # See BossProfile.pierce_hits_body_behind_core - only meaningful together
    # with core_hittable.
    pierce_hits_body_behind_core: bool = False
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_api_boss_profile.py -q`
Expected: PASS

- [ ] **Step 5: 백엔드 전체 테스트**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: 기준선 유지

- [ ] **Step 6: 커밋**

```bash
git add backend/app/deck_search.py backend/app/api.py backend/tests/test_api_boss_profile.py
git commit -m "Carry the core-pierce flag from the wire to the simulator, and pin that it arrives"
```

---

## Task 7: 코어 2관통 체크박스

**Files:**
- Modify: `frontend/src/types/recommend.ts:23-37`
- Modify: `frontend/src/types/bossProfileDraft.ts`
- Modify: `frontend/src/components/BossProfileField.tsx` (코어 피격 가능 체크박스 뒤)
- Modify: `frontend/src/lib/helpText.ts:33-37`
- Test: `frontend/src/components/BossProfileField.test.tsx`, `frontend/src/types/bossProfileDraft.test.ts`

**Interfaces:**
- Produces: `BossProfileDraft.pierce_hits_body_behind_core: boolean`,
  `BossProfile.pierce_hits_body_behind_core: boolean`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/BossProfileField.test.tsx`에 추가:

```tsx
describe('BossProfileField 코어 2관통', () => {
  it('2관통을 켜면 코어 피격 가능도 함께 켜진다', async () => {
    // 코어를 못 때리면 뚫고 지나갈 것이 없다. 모순 상태를 만들 수 없게 한다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('상시 코어 2관통'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: true, pierce_hits_body_behind_core: true }),
    )
  })

  it('코어 피격 가능을 끄면 2관통도 꺼진다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{
          ...makeDefaultBossProfileDraft(),
          core_hittable: true,
          pierce_hits_body_behind_core: true,
        }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('코어 피격 가능'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: false, pierce_hits_body_behind_core: false }),
    )
  })
})
```

`frontend/src/types/bossProfileDraft.test.ts`에 추가:

```ts
it('2관통 플래그가 draft와 BossProfile 사이를 왕복한다', () => {
  const draft = { ...makeDefaultBossProfileDraft(), pierce_hits_body_behind_core: true }
  const { value } = validateBossProfileDraft(draft)

  expect(value?.pierce_hits_body_behind_core).toBe(true)
  expect(bossProfileToDraft(value!).pierce_hits_body_behind_core).toBe(true)
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx src/types/bossProfileDraft.test.ts`
Expected: FAIL — 라벨을 못 찾고, `pierce_hits_body_behind_core`가 `undefined`

- [ ] **Step 3: 타입과 draft를 넓힌다**

`frontend/src/types/recommend.ts`의 `BossProfile`에 추가:

```ts
  pierce_hits_body_behind_core: boolean // default false — 코어와 본체가 별개 객체인
  // 보스. 관통 특화 니케의 탄이 코어를 뚫고 뒤의 본체까지 때려 통상공격 1발이 두 번
  // 들어간다. core_hittable에 의존한다 — 뚫고 지나갈 코어가 없으면 성립하지 않는다.
```

`frontend/src/types/bossProfileDraft.ts`:

```ts
export interface BossProfileDraft {
  element: BossElement
  core_hittable: boolean
  pierce_hits_body_behind_core: boolean
  enemy_def: string
  fight_duration: string
  part_destructible: boolean
  effective_range_band: BossRangeBand
}
```

`makeDefaultBossProfileDraft`에 `pierce_hits_body_behind_core: false,`,
`bossProfileToDraft`에 아래를 추가한다:

```ts
  // 이 필드가 생기기 전에 저장된 프로필은 undefined라, 그대로 두면 체크박스가
  // 비제어 컴포넌트가 된다.
  pierce_hits_body_behind_core: boss.pierce_hits_body_behind_core ?? false,
```

`validateBossProfileDraft`의 `const value: BossProfile = {` 안에도
`pierce_hits_body_behind_core: draft.pierce_hits_body_behind_core,`를 넣는다.

- [ ] **Step 4: 체크박스를 그린다**

`BossProfileField.tsx`의 「코어 피격 가능」 `checkbox-row`를 교체하고 그 뒤에 새 행을 넣는다:

```tsx
      <div className="checkbox-row">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={value.core_hittable}
            onChange={(event) =>
              onChange({
                ...value,
                core_hittable: event.target.checked,
                // 코어를 못 때리면 뚫고 지나갈 것도 없다. 엔진도 두 값을 같이 읽지만,
                // 폼에서 모순 상태를 아예 만들지 않는 편이 화면이 정직하다.
                pierce_hits_body_behind_core:
                  event.target.checked && value.pierce_hits_body_behind_core,
              })
            }
          />
          코어 피격 가능
        </label>
        <HelpTip label="코어 피격 가능">
          <HelpText>{HELP.boss.coreHittable}</HelpText>
        </HelpTip>
      </div>

      <div className="checkbox-row">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={value.pierce_hits_body_behind_core}
            onChange={(event) =>
              onChange({
                ...value,
                pierce_hits_body_behind_core: event.target.checked,
                core_hittable: event.target.checked || value.core_hittable,
              })
            }
          />
          상시 코어 2관통
        </label>
        <HelpTip label="상시 코어 2관통">
          <HelpText>{HELP.boss.corePierce}</HelpText>
        </HelpTip>
      </div>
```

`frontend/src/lib/helpText.ts`의 `boss` 객체에 추가:

```ts
    corePierce:
      '코어와 본체가 **별개 객체**로 만들어진 보스예요. 관통 특화 니케의 탄은 코어를 뚫고 뒤의 본체까지 때려서, 평타 한 발이 두 번 들어가요. 관통이 없는 니케는 코어는 때려도 본체는 못 때려요. 코어 피격 가능이 함께 켜져요.',
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx src/types/bossProfileDraft.test.ts`
Expected: PASS

- [ ] **Step 6: 프론트 전체 테스트 + 빌드**

Run: `cd frontend && npm test && npm run lint && npm run build`
Expected: 전부 통과. `makeDefaultBossProfileDraft()`를 안 쓰고 draft 리터럴을 직접 만드는
테스트가 있으면 새 필드를 더해준다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/types frontend/src/components/BossProfileField.tsx frontend/src/components/BossProfileField.test.tsx frontend/src/lib/helpText.ts
git commit -m "Offer the core-pierce boss setting, tied to core hittability"
```

---

# Phase B — 속성저지 필수

## Task 8: 약점 술어와 보스 필드

**Files:**
- Modify: `backend/app/elements.py`
- Modify: `backend/app/deck_search.py` (`BossProfile`, 새 함수)
- Modify: `backend/app/api.py` (`BossProfileIn`)
- Test: `backend/tests/test_elemental_interrupt_constraint.py` (신규)

**Interfaces:**
- Produces:
  - `elements.weakness_of(boss_element: str) -> str` — 보스를 이기는 속성
  - `deck_search.deck_breaks_gimmick(units, boss) -> bool`
  - `deck_search.weakness_holders(units, boss) -> int` — Task 10이 쓴다
  - `BossProfile.elemental_interrupt_required: bool = False`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_elemental_interrupt_constraint.py`:

```python
"""속성저지 기믹: 파훼하려면 약점 속성 니케가 덱에 최소 1기 있어야 한다.

지금까지 덱 합법성 술어는 전부 유닛만 봤다(_no_character_clash 등). 이것은 보스에
의존하는 첫 제약이므로, 술어 자체와 그것이 탐색에 어떻게 들어가는지를 따로 고정한다.
"""
from dataclasses import dataclass

from app.deck_search import BossProfile, deck_breaks_gimmick, weakness_holders
from app.elements import weakness_of


@dataclass(frozen=True)
class Unit:
    """탐색이 유닛에게 묻는 것만 갖는 스텁. `base_stats`/`weapon_stats`는
    prune_candidate_pool의 `_prior`가 읽는 두 값이고(뒤의 Task들이 그 경로를 탄다),
    `backend/tests/test_deck_allocation.py`의 Unit이 같은 이유로 같은 모양이다."""
    slug: str
    burst_tier: int
    element: str
    base_stats: dict = None
    weapon_stats: dict = None

    def __post_init__(self):
        if self.base_stats is None:
            object.__setattr__(self, "base_stats", {"atk": 1000.0})
        if self.weapon_stats is None:
            object.__setattr__(self, "weapon_stats", {"damage_percent": 1.0})


def _deck(*elements):
    return [Unit(f"u{i}", 1 + i % 3, e) for i, e in enumerate(elements)]


def test_the_weakness_of_a_fire_boss_is_water():
    # elements.py: Water > Fire > Wind > Iron > Electric > Water
    assert weakness_of("Fire") == "Water"
    assert weakness_of("Water") == "Electric"


def test_every_element_has_exactly_one_weakness_and_it_round_trips():
    from app.elements import _STRONG_AGAINST

    for attacker, beaten in _STRONG_AGAINST.items():
        assert weakness_of(beaten) == attacker


def test_a_boss_with_no_gimmick_admits_any_deck():
    boss = BossProfile(element="Fire")
    assert deck_breaks_gimmick(_deck("Fire", "Fire", "Fire", "Fire", "Fire"), boss)


def test_an_element_less_boss_admits_any_deck_even_with_the_gimmick_on():
    # No element means no weakness, so demanding one would make every roster
    # infeasible rather than expressing a real requirement.
    boss = BossProfile(element=None, elemental_interrupt_required=True)
    assert deck_breaks_gimmick(_deck("Fire", "Fire", "Fire", "Fire", "Fire"), boss)


def test_the_gimmick_needs_one_unit_of_the_weakness_element():
    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    assert not deck_breaks_gimmick(_deck("Fire", "Wind", "Iron", "Electric", "Fire"), boss)
    assert deck_breaks_gimmick(_deck("Fire", "Wind", "Iron", "Electric", "Water"), boss)


def test_weakness_holders_counts_only_when_the_gimmick_is_on():
    units = _deck("Water", "Water", "Fire", "Fire", "Fire")
    assert weakness_holders(units, BossProfile(element="Fire")) == 0
    assert weakness_holders(
        units, BossProfile(element="Fire", elemental_interrupt_required=True)) == 2
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py -q`
Expected: FAIL — `ImportError: cannot import name 'weakness_of'`

- [ ] **Step 3: 구현한다**

`backend/app/elements.py` 끝에:

```python
# beaten element -> the attacker that beats it. Derived from _STRONG_AGAINST
# rather than written out, so the two can never disagree.
_WEAK_TO = {beaten: attacker for attacker, beaten in _STRONG_AGAINST.items()}


def weakness_of(boss_element: str) -> str:
    """The attacker element that holds advantage over `boss_element`.

    The boss's "weakness" in the UI's language: the element a player fields to
    break an elemental-interrupt gimmick.
    """
    if boss_element not in _WEAK_TO:
        raise KeyError(f"unknown element: {boss_element!r}")
    return _WEAK_TO[boss_element]
```

`backend/app/deck_search.py` — import에 추가:

```python
from app.elements import weakness_of
```

`BossProfile`의 `pierce_hits_body_behind_core` 뒤에:

```python
    # The boss gates a gimmick on an elemental interrupt: breaking it needs at
    # least one Nikke holding elemental advantage, so a deck without one cannot
    # clear the phase however much damage it does. Unlike every other deck
    # legality rule in this module, this one depends on the BOSS - see
    # deck_breaks_gimmick.
    elemental_interrupt_required: bool = False
```

`_buffer_seat_valid` 아래에:

```python
def weakness_holders(units, boss: BossProfile):
    """How many of `units` hold elemental advantage over this boss - 0 whenever
    the gimmick is off or the boss has no element, so callers need no second
    guard before budgeting them across decks."""
    if not boss.elemental_interrupt_required or boss.element is None:
        return 0
    weakness = weakness_of(boss.element)
    return sum(1 for u in units if u.element == weakness)


def deck_breaks_gimmick(units, boss: BossProfile):
    """Whether these units can break the boss's elemental-interrupt gimmick.

    Vacuously true when the boss has no gimmick, and ALSO when it has no element:
    an element-less boss has no weakness, so no deck could ever satisfy the
    requirement and enforcing it would make every roster infeasible rather than
    expressing anything real.
    """
    if not boss.elemental_interrupt_required or boss.element is None:
        return True
    weakness = weakness_of(boss.element)
    return any(u.element == weakness for u in units)
```

`backend/app/api.py`의 `BossProfileIn`에 추가:

```python
    # See BossProfile.elemental_interrupt_required. Inert on an element-less boss.
    elemental_interrupt_required: bool = False
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py tests/test_api_boss_profile.py -q`
Expected: PASS

- [ ] **Step 5: 백엔드 전체 테스트**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: 기준선 유지 (필드가 붙기만 하고 아무도 안 읽는다)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/elements.py backend/app/deck_search.py backend/app/api.py backend/tests/test_elemental_interrupt_constraint.py
git commit -m "Name a boss's weakness element and whether a deck can break its interrupt"
```

---

## Task 9: 탐색 생성기에 제약을 심는다

**Files:**
- Modify: `backend/app/deck_search.py` — `shape_combinations` · `_shape_completions` ·
  `feasible_orderings` · `_orderings_within_budget` · `completions_fit_budget` ·
  `search_best_decks` · `best_completions` · `find_best_decks`
- Test: `backend/tests/test_elemental_interrupt_constraint.py`

**Interfaces:**
- Consumes: `deck_breaks_gimmick` (Task 8)
- Produces:
  - 생성기 3종에 optional `deck_filter` 인자
  - `search_best_decks(..., deck_filter=None)` · `best_completions(..., deck_filter=None)`
  - `_ensure_weakness_in_pool(cut, roster, boss)` — Task 10은 안 쓰지만 여기서 필요

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_elemental_interrupt_constraint.py` 끝에 덧붙인다:

```python
def test_shape_combinations_drops_decks_that_cannot_break_the_gimmick():
    from app.deck_search import shape_combinations

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    roster = [Unit("b1", 1, "Fire"), Unit("b2", 2, "Fire"),
              Unit("c1", 3, "Fire"), Unit("c2", 3, "Fire"), Unit("c3", 3, "Water")]

    unfiltered = list(shape_combinations(roster))
    filtered = list(shape_combinations(roster, lambda d: deck_breaks_gimmick(d, boss)))

    assert unfiltered      # the roster does form (1,1,3) decks
    assert all(any(u.element == "Water" for u in deck) for deck in filtered)
    assert len(filtered) < len(unfiltered)


def test_shape_completions_drops_them_too():
    from app.deck_search import _shape_completions

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    required = [Unit("b1", 1, "Fire")]
    candidates = [Unit("b2", 2, "Fire"), Unit("c1", 3, "Fire"),
                  Unit("c2", 3, "Fire"), Unit("c3", 3, "Water")]

    filtered = list(_shape_completions(required, candidates,
                                       lambda d: deck_breaks_gimmick(d, boss)))

    assert filtered
    assert all(any(u.element == "Water" for u in deck) for deck in filtered)


def test_a_pruned_pool_is_topped_back_up_with_the_weakness_element():
    """prune_candidate_pool ranks by marginal contribution and knows nothing
    about the gimmick, so its cut can hold no weakness unit at all - and then the
    constrained search has nothing to return. Widen the pool rather than fall
    back to an exhaustive walk over the full roster (millions of orderings)."""
    from app.deck_search import _ensure_weakness_in_pool

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    cut = [Unit("b1", 1, "Fire"), Unit("b2", 2, "Fire"), Unit("c1", 3, "Fire")]
    roster = cut + [Unit("w1", 1, "Water"), Unit("w3", 3, "Water")]

    topped = _ensure_weakness_in_pool(cut, roster, boss)

    assert any(u.element == "Water" for u in topped)
    assert set(cut) <= set(topped)


def test_a_pool_that_already_holds_the_weakness_is_left_alone():
    from app.deck_search import _ensure_weakness_in_pool

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    cut = [Unit("b1", 1, "Water"), Unit("b2", 2, "Fire")]

    assert _ensure_weakness_in_pool(cut, cut, boss) is cut
```

`Unit` 스텁은 Task 8이 이미 최종 형태로 정의했으므로 손대지 않는다.

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py -q`
Expected: FAIL — `shape_combinations() takes 1 positional argument but 2 were given`

- [ ] **Step 3: 생성기 3종에 필터를 넣는다**

`deck_search.py`의 `shape_combinations`:

```python
def shape_combinations(roster, deck_filter=None):
    """Canonical tier-ordered 5-unit combinations, restricted to the shapes
    real play uses. Pure combinatorics on `.burst_tier` (like
    feasible_orderings); intra-tier order is the input order.

    `deck_filter` is an optional extra legality predicate on the finished deck.
    It exists for a rule this module had none of until now: one that depends on
    the BOSS rather than only on the units (deck_breaks_gimmick). Filtering here
    rather than after the search is deliberate - a search that converges on decks
    the rule forbids and is corrected afterwards loses an unpredictable amount.
    """
    by_tier = {1: [], 2: [], 3: []}
    for unit in roster:
        if unit.burst_tier in by_tier:
            by_tier[unit.burst_tier].append(unit)
    for n1, n2, n3 in ALLOWED_SHAPES:
        for c1 in combinations(by_tier[1], n1):
            for c2 in combinations(by_tier[2], n2):
                for c3 in combinations(by_tier[3], n3):
                    deck = list(c1) + list(c2) + list(c3)
                    if (_no_character_clash(deck) and _tier1_seating_valid(deck)
                            and (deck_filter is None or deck_filter(deck))):
                        yield deck
```

`_shape_completions(required, candidates, deck_filter=None)` — 마지막 `if`를 같은 모양으로:

```python
                    if (_no_character_clash(deck) and _tier1_seating_valid(deck)
                            and (deck_filter is None or deck_filter(deck))):
                        yield deck
```

`feasible_orderings(roster, deck_filter=None)` — `continue` 조건에 더한다:

```python
        if (infeasible or not all(by_tier[t] for t in (1, 2, 3))
                or not _no_character_clash(combo) or not _tier1_seating_valid(combo)
                or (deck_filter is not None and not deck_filter(combo))):
            continue
```

`find_best_decks(roster, boss, top_n=5)`도 함께 배선한다 — API는 안 쓰지만 두 경로가
합법성에 대해 다른 답을 내면 안 된다(`deck_is_valid`의 docstring과 같은 이유):

```python
def find_best_decks(roster, boss: BossProfile, top_n=5):
    deck_filter = _gimmick_filter(boss)
    scored = [
        _summarize(ordered, evaluate_deck(ordered, boss))
        for ordered in feasible_orderings(roster, deck_filter)
    ]
    ...
```

- [ ] **Step 4: 필터 생성기와 풀 보강을 넣는다**

`deck_breaks_gimmick` 아래에:

```python
def _gimmick_filter(boss: BossProfile):
    """The boss's gimmick as a deck predicate, or None when there is none to
    apply. None (rather than a predicate that always returns True) is what lets
    every generator below skip the call entirely on the common path."""
    if not boss.elemental_interrupt_required or boss.element is None:
        return None
    return lambda units: deck_breaks_gimmick(units, boss)


def _ensure_weakness_in_pool(cut, roster, boss: BossProfile):
    """Guarantee the cut pool can still form a deck that breaks the gimmick.

    prune_candidate_pool ranks by marginal contribution and knows nothing about
    the boss, so its cut can hold no unit of the weakness element - and then the
    constrained search has nothing at all to return. Top the pool back up with
    the best weakness unit at each tier instead. This is the same move
    _reference_deck makes when its picks come up short: widen the pool rather
    than return nothing, and never fall back to an exhaustive walk over the full
    roster (millions of orderings on a real one).
    """
    if not boss.elemental_interrupt_required or boss.element is None:
        return cut
    weakness = weakness_of(boss.element)
    if any(u.element == weakness for u in cut):
        return cut
    in_cut = {u.slug for u in cut}
    added = []
    for tier in (1, 2, 3):
        pick = max((u for u in roster
                    if u.burst_tier == tier and u.element == weakness
                    and u.slug not in in_cut),
                   key=_prior, default=None)
        if pick is not None:
            added.append(pick)
    return list(cut) + added
```

`_prior`는 파일 뒤쪽에 정의돼 있지만 호출 시점에만 필요하므로 순서는 문제없다.

- [ ] **Step 5: 두 탐색 진입점을 배선한다**

`_orderings_within_budget(roster, sim_budget, deck_filter=None)`:

```python
def _orderings_within_budget(roster, sim_budget, deck_filter=None):
    """_bounded_orderings over every deck `roster` can form (no draft to honor)."""
    return _bounded_orderings(shape_combinations(roster, deck_filter), sim_budget)
```

`completions_fit_budget(required, candidates, sim_budget=SEARCH_SIM_BUDGET, deck_filter=None)`:

```python
    return _bounded_orderings(_shape_completions(required, candidates, deck_filter),
                              sim_budget) is not None
```

`search_best_decks`에 `deck_filter=None`을 더하고 본문 앞부분을 교체:

```python
    candidates = list(roster)
    if deck_filter is None:
        deck_filter = _gimmick_filter(boss)
    orderings = _orderings_within_budget(candidates, sim_budget, deck_filter)
    if orderings is None:
        combos = cascade.shortlist(roster, boss, pool) if cascade is not None else None
        if combos is not None and deck_filter is not None:
            # The cascade ranks by predicted damage and knows nothing about the
            # gimmick, so its shortlist can be entirely decks the filter rejects.
            # Falling through to the pruned path is the same two-step this
            # function already takes when the cascade declines outright.
            combos = [c for c in combos if deck_filter(c)] or None
        if combos is None:
            cut = prune_candidate_pool(roster, boss, pool)
            combos = shape_combinations(_ensure_weakness_in_pool(cut, roster, boss),
                                        deck_filter)
        orderings = _all_intra_tier_orderings(combos)
```

`best_completions`에 `deck_filter=None`을 더하고 본문을 교체:

```python
    if deck_filter is None:
        deck_filter = _gimmick_filter(boss)
    orderings = _bounded_orderings(_shape_completions(required, candidates, deck_filter),
                                   sim_budget)
    if orderings is None:
        combos = (cascade.shortlist_completions(required, candidates, boss, pool)
                  if cascade is not None else None)
        if combos is not None and deck_filter is not None:
            combos = [c for c in combos if deck_filter(c)] or None
        if combos is None:
            cut = prune_candidate_pool(candidates, boss, pool)
            combos = _shape_completions(required,
                                        _ensure_weakness_in_pool(cut, candidates, boss),
                                        deck_filter)
        orderings = _all_intra_tier_orderings(combos)
        if not orderings:
            orderings = _all_intra_tier_orderings(
                _shape_completions(required, candidates, deck_filter))
```

`best_completions`의 기존 fallback 주석은 그대로 둔다 — 이유가 바뀌지 않았고, 이제
필터가 만든 공백도 같은 경로로 메워진다.

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py -q`
Expected: PASS

- [ ] **Step 7: 단일 덱 탐색의 종단 동작을 고정한다**

같은 테스트 파일에 추가:

```python
# 작열 보스의 약점. 이 파일 전체가 이 한 쌍으로 말한다.
WEAKNESS = "Water"
GIMMICK_BOSS = BossProfile(element="Fire", elemental_interrupt_required=True)


def _roster(n_weakness):
    """10 units - two decks' worth - of which the first `n_weakness` are the
    weakness element and the rest are the boss's own.

    Tiers 3/2/5 (B1/B2/B3) put every ordering under SEARCH_SIM_BUDGET (720 of
    1200), so the search enumerates rather than pruning: this file is about the
    constraint, not about the cut. The weakness units land at tier 1 first, so
    n=2 gives two B1s that CAN sit in different decks - which is what makes the
    budget cap in Task 10 a real test rather than a tautology.
    """
    tiers = [1, 1, 1, 2, 2, 3, 3, 3, 3, 3]
    return [Unit(f"u{i}", t, WEAKNESS if i < n_weakness else "Fire")
            for i, t in enumerate(tiers)]


def test_a_single_deck_search_returns_a_deck_that_breaks_the_gimmick(monkeypatch):
    """종단 확인 — 술어가 아니라 search_best_decks의 반환값을 본다."""
    from app.deck_search import search_best_decks
    from tests.test_deck_allocation import patch_scorer

    roster = _roster(2)
    by_slug = {u.slug: u for u in roster}
    # 약점 유닛이 없는 덱을 더 높게 친다 - 제약이 없으면 그쪽이 뽑힌다.
    patch_scorer(monkeypatch,
                 lambda slugs: 10.0 if any(by_slug[s].element == WEAKNESS for s in slugs)
                 else 100.0)

    result = search_best_decks(roster, GIMMICK_BOSS, top_n=1)

    assert any(by_slug[s].element == WEAKNESS for s in result[0]["deck"])


def test_a_roster_with_no_weakness_unit_still_gets_a_recommendation(monkeypatch):
    # 제약을 못 지키는 로스터에 대해 추천을 거부하지 않는다 - UI가 경고를 단다.
    from app.deck_search import search_best_decks
    from tests.test_deck_allocation import patch_scorer

    patch_scorer(monkeypatch, lambda slugs: 1.0)

    assert search_best_decks(_roster(0), GIMMICK_BOSS, top_n=1)
```

> **왜 스텁 로스터인가.** `patch_scorer`(`tests/test_deck_allocation.py`)가
> `evaluate_deck`을 `deck_search`와 `deck_allocation` 양쪽 모듈 바인딩에서 갈아치우므로
> 시뮬레이션이 아예 안 돈다. 실제 스펙 15기를 손으로 만드는 것보다 빠르고, 무엇보다
> **점수를 우리가 정하므로** "제약이 없으면 다른 답이 나온다"를 단언할 수 있다 —
> 실제 시뮬레이션으로는 그 대비를 만들 수 없다.

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py -q`
Expected: PASS

- [ ] **Step 8: 백엔드 전체 테스트**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: 기준선 유지. 제약이 꺼져 있으면 `_gimmick_filter`가 None이라 모든 경로가
이전과 글자 그대로 같아야 한다.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/deck_search.py backend/tests/test_elemental_interrupt_constraint.py
git commit -m "Filter decks that cannot break the boss's interrupt at generation time"
```

---

## Task 10: 5덱 배분 — 약점유닛 배분과 힐클라임 가드

**Files:**
- Modify: `backend/app/deck_allocation.py` — `allocate_decks` (seed 루프 · peel 루프),
  `_swap_pass`, `_try_swaps`
- Test: `backend/tests/test_elemental_interrupt_constraint.py`

**Interfaces:**
- Consumes: `weakness_holders` · `deck_breaks_gimmick` · `weakness_of` (Task 8),
  `search_best_decks(..., deck_filter=)` · `best_completions(..., deck_filter=)` (Task 9)
- Produces: 없음 (내부 동작)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_elemental_interrupt_constraint.py` 끝에:

```python
def _satisfied(alloc, roster):
    by_slug = {u.slug: u for u in roster}
    return sum(1 for d in alloc["decks"]
               if any(by_slug[s].element == WEAKNESS for s in d["deck"]))


def _stacking_scorer(monkeypatch):
    """Reward putting BOTH weakness units in one deck.

    Without the peel's per-deck cap the greedy peel takes that bait and deck 2
    gets nothing - which is exactly the starvation the cap exists to prevent. A
    scorer that is indifferent would make these tests pass for the wrong reason.
    """
    from tests.test_deck_allocation import patch_scorer
    patch_scorer(monkeypatch, lambda slugs: 100.0 if {"u0", "u1"} <= slugs else 10.0)


def test_the_peel_spreads_the_weakness_units_across_the_decks(monkeypatch):
    """설계 B.2. 약점유닛 2기 / 2덱이면 2덱 다 만족한다 - 점수가 몰아넣기를 부추겨도."""
    from app.deck_allocation import allocate_decks

    _stacking_scorer(monkeypatch)
    roster = _roster(2)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=0.0)

    assert len(alloc["decks"]) == 2
    assert _satisfied(alloc, roster) == 2


def test_a_thin_roster_satisfies_as_many_decks_as_it_can_and_no_fewer(monkeypatch):
    """약점유닛 1기 / 2덱이면 정확히 1덱. 0덱(제약을 놓침)도 2덱(없는 유닛)도 아니다."""
    from app.deck_allocation import allocate_decks
    from tests.test_deck_allocation import patch_scorer

    patch_scorer(monkeypatch, lambda slugs: 1.0)
    roster = _roster(1)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=0.0)

    assert _satisfied(alloc, roster) == 1


def test_a_roster_with_no_weakness_unit_still_allocates(monkeypatch):
    from app.deck_allocation import allocate_decks
    from tests.test_deck_allocation import patch_scorer

    patch_scorer(monkeypatch, lambda slugs: 1.0)
    roster = _roster(0)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=0.0)

    assert len(alloc["decks"]) == 2
    assert _satisfied(alloc, roster) == 0


def test_the_climb_will_not_stack_the_weakness_units_back_together(monkeypatch):
    """가드의 첫 번째 갈래. 몰아넣기가 100 + 10 = 110점이고 흩뿌리기는 10 + 10 = 20점
    이므로, 가드가 없으면 힐클라임이 peel의 배분을 즉시 되돌린다."""
    from app.deck_allocation import allocate_decks

    _stacking_scorer(monkeypatch)
    roster = _roster(2)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=30.0)

    assert _satisfied(alloc, roster) == 2


def test_the_swap_floor_never_exceeds_what_we_already_hold():
    """가드의 두 번째 갈래. K에 못 미치는 상태에서는 하한도 K가 아니라 현재값이다 -
    K를 그대로 쓰면 모든 스왑이 거부되어 클라임이 통째로 죽는다."""
    from app.deck_allocation import _gimmick_floor, _satisfied_count

    decks = [[Unit("a", 1, WEAKNESS)], [Unit("b", 1, "Fire")]]

    assert _satisfied_count(decks, GIMMICK_BOSS) == 1
    assert _gimmick_floor(decks, GIMMICK_BOSS, 2) == 1   # K=2지만 지금은 1
    assert _gimmick_floor(decks, GIMMICK_BOSS, 1) == 1
    assert _satisfied_count(decks, BossProfile(element="Fire")) == 0   # 기믹 없음
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py -q -k "gimmick or thin or climb or allocates"`
Expected: FAIL — `cannot import name '_satisfied_count'`, 그리고 얇은 로스터 케이스가
2가 아닌 값을 낸다

- [ ] **Step 3: peel 배분 필터를 넣는다**

`deck_allocation.py`의 import에 추가:

```python
from app.deck_search import (..., deck_breaks_gimmick, weakness_holders)
from app.elements import weakness_of
```

`_seed_choices` 아래에:

```python
def _gimmick_budget(available, boss, decks_left):
    """The gimmick constraint for ONE deck about to be built, budgeting the
    weakness units across the decks still to build. None when there is nothing to
    enforce (gimmick off, element-less boss, or no weakness unit left at all).

    A deck must hold at least one weakness unit and at most
    `max(1, w - decks_left + 1)` of them. The CAP is what keeps the greedy peel
    from starving later decks: without it, deck 1 can take two of three weakness
    units and deck 3 gets none, which drops the satisfied count below the
    min(M, N) the design promises.

    On a real roster the cap never binds - 60-80 units carry 12-16 of any one
    element, so it sits at 8 or more and a 5-unit deck cannot reach it. It bites
    only on thin rosters, which is exactly where the starvation happens.
    """
    w = weakness_holders(available, boss)
    if w == 0:
        return None
    weakness = weakness_of(boss.element)
    cap = max(1, w - decks_left + 1)

    def ok(units):
        held = sum(1 for u in units if u.element == weakness)
        return 1 <= held <= cap

    return ok


def _satisfied_count(decks, boss):
    """How many of these decks can break the boss's gimmick. 0 whenever there is
    no gimmick, which makes the swap guard below inert on the common path."""
    if not boss.elemental_interrupt_required or boss.element is None:
        return 0
    return sum(1 for deck in decks if deck_breaks_gimmick(deck, boss))


def _gimmick_floor(decks, boss, target):
    """The number of gimmick-breaking decks a swap may not take us below.

    The `min` is the whole point. Once the peel reached `target` (= min(M, N)),
    the count may not drop below it. If it came up short - a roster too thin to
    fill every deck - the rule is only "do not make it worse". Using `target`
    itself as the floor would reject every swap in that second case and kill the
    climb outright.
    """
    return min(target, _satisfied_count(decks, boss))
```

`allocate_decks`의 seed 루프에서 `found = max(...)` 부분을 교체:

```python
            # The seat budget counts the seed's own weakness units as available:
            # a drafted deck that already holds one needs no second.
            gimmick = _gimmick_budget(list(readings[0]) + remaining, boss,
                                      num_decks - len(decks))

            def complete(deck_filter):
                return max(
                    (c for reading in readings
                     for c in best_completions(reading, remaining, boss, top_n=1,
                                               pool=pool, cascade=cascade,
                                               deck_filter=deck_filter)),
                    key=lambda c: c["total_damage"], default=None)

            found = complete(gimmick)
            if found is None and gimmick is not None:
                # The draft cannot break the gimmick - the player filled the seats
                # with units that lack the weakness element. Solve it unconstrained
                # rather than refuse a deck they can field; the UI flags it instead
                # (design B.2 / B.6).
                found = complete(None)
```

`allocate_decks`의 free-deck peel 루프에서 `found = search_best_decks(...)`를 교체:

```python
            gimmick = _gimmick_budget(remaining, boss, num_decks - len(decks))
            found = search_best_decks(remaining, boss, top_n=1, pool=pool,
                                      cascade=cascade, deck_filter=gimmick)
            if not found and gimmick is not None:
                # No legal deck in the remaining pool holds a weakness unit within
                # the budget. Take the best unconstrained deck rather than stop
                # short of num_decks - the design's "as many decks as we can".
                found = search_best_decks(remaining, boss, top_n=1, pool=pool,
                                          cascade=cascade)
            if not found:
                break
```

- [ ] **Step 4: 힐클라임 가드를 넣는다**

`_swap_pass`에서 `scores = _score_batch(decks, boss, pool)` 앞에:

```python
    # K = min(M, N): the most decks this roster could ever satisfy. The climb may
    # move weakness units between decks freely; what it may not do is lower the
    # number of decks that hold one.
    gimmick_target = min(
        weakness_holders([u for deck in decks for u in deck] + list(leftovers), boss),
        len(decks))
```

그리고 `_try_swaps` 호출 두 곳에 `gimmick_target`을 넘긴다.

`_try_swaps` 시그니처에 `gimmick_target=0`을 더하고, `admissible` 앞에:

```python
    def gimmick_ok(a, k):
        """The swap must not lower how many decks can break the gimmick below
        `_gimmick_floor` - read live off `decks`, so an accepted swap that RAISED
        the count raises the floor with it."""
        if gimmick_target == 0:
            return True
        floor = _gimmick_floor(decks, boss, gimmick_target)
        trial = list(decks)
        deck_i = list(decks[i])
        deck_i[a] = partner[k]
        trial[i] = deck_i
        if j is not None:
            deck_j = list(partner)
            deck_j[k] = decks[i][a]
            trial[j] = deck_j
        return _satisfied_count(trial, boss) >= floor
```

`admissible`에 조건을 더한다:

```python
    def admissible(a, k):
        return ((seated is None or character_of(partner[k].slug) not in seated)
                and _swap_is_fieldable(decks[i], a, partner, k, j is not None)
                and gimmick_ok(a, k))
```

`gimmick_ok`가 라이브 `decks`를 읽으므로, 스왑이 수락된 뒤 꼬리를 다시 거르는 기존
`candidates = candidates[:start] + [... if admissible(...)]` 재필터가 그대로 가드에도
적용된다 — 별도 처리가 필요 없다.

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py -q`
Expected: PASS

- [ ] **Step 6: 제약이 꺼졌을 때 배분이 글자 그대로 예전과 같은지 확인한다**

같은 파일에 추가:

```python
def test_an_allocation_without_the_gimmick_is_byte_for_byte_the_old_one(monkeypatch):
    """제약이 꺼져 있으면 _gimmick_budget이 None, gimmick_target이 0이라 peel도
    클라임도 이전 코드와 같은 경로를 탄다. 배분 결과가 달라지면 회귀다."""
    from app.deck_allocation import allocate_decks

    _stacking_scorer(monkeypatch)
    roster = _roster(2)

    off = allocate_decks(roster, BossProfile(element="Fire"), num_decks=2,
                         time_budget_sec=30.0)

    # 기믹이 없으면 점수를 그대로 따라가 두 약점유닛이 한 덱에 몰린다.
    assert _satisfied(off, roster) == 1
    assert sum(d["total_damage"] for d in off["decks"]) == 110.0
```

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_elemental_interrupt_constraint.py -q`
Expected: PASS — 이 테스트가 실패하면 제약이 꺼진 경로에까지 새 코드가 샜다는 뜻이다.

- [ ] **Step 7: 백엔드 전체 테스트**

Run: `cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q`
Expected: 기준선 유지. `test_deck_allocation.py`가 `_try_swaps`를 직접 호출하고 있으면
새 기본 인자(`gimmick_target=0`) 덕에 그대로 통과해야 한다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/deck_allocation.py backend/tests/test_elemental_interrupt_constraint.py
git commit -m "Spread the weakness units across an allocation and hold that spread through the climb"
```

---

## Task 11: 속성저지 체크박스 (추천 탭 전용)

**Files:**
- Modify: `frontend/src/types/recommend.ts`
- Modify: `frontend/src/types/bossProfileDraft.ts`
- Modify: `frontend/src/components/BossProfileField.tsx`
- Modify: `frontend/src/components/UnionRaidPanel.tsx` (두 곳의 `<BossProfileField>`)
- Modify: `frontend/src/lib/helpText.ts`
- Test: `frontend/src/components/BossProfileField.test.tsx`,
  `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Produces: `BossProfileField`의 새 prop `showElementalInterrupt?: boolean` (기본 true)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`BossProfileField.test.tsx`에 추가:

```tsx
describe('BossProfileField 속성저지', () => {
  it('기본으로 속성저지 체크박스를 그린다', async () => {
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('속성저지 필수'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ elemental_interrupt_required: true }),
    )
  })

  it('showElementalInterrupt=false면 그리지 않는다', () => {
    // 유니온레이드 탭은 탐색이 없어 제약이 걸 곳이 없다.
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={vi.fn()}
        showElementalInterrupt={false}
      />,
    )

    expect(screen.queryByLabelText('속성저지 필수')).not.toBeInTheDocument()
  })
})
```

`UnionRaidPanel.test.tsx`에 추가:

```tsx
it('유니온레이드 탭에는 속성저지 체크박스가 없다', () => {
  // 이 탭은 유저가 짠 편성을 채점만 하므로 탐색 제약이 걸 곳이 없다.
  renderPanel()   // 이 파일이 이미 쓰는 렌더 헬퍼

  expect(screen.queryByLabelText('속성저지 필수')).not.toBeInTheDocument()
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx src/components/UnionRaidPanel.test.tsx`
Expected: FAIL — `속성저지 필수` 라벨이 없다

- [ ] **Step 3: 타입과 draft를 넓힌다**

`recommend.ts`의 `BossProfile`에:

```ts
  elemental_interrupt_required: boolean // default false — 기믹 파훼에 약점 속성 니케가
  // 덱당 최소 1기 필요하다. 무속성 보스에서는 무시된다(약점이 없으므로 어떤 덱도
  // 만족시킬 수 없고, 강제하면 모든 로스터가 불능이 된다).
```

`bossProfileDraft.ts`의 `BossProfileDraft`에 `elemental_interrupt_required: boolean`,
`makeDefaultBossProfileDraft`에 `elemental_interrupt_required: false,`,
`bossProfileToDraft`에 `elemental_interrupt_required: boss.elemental_interrupt_required ?? false,`,
`validateBossProfileDraft`의 `value`에
`elemental_interrupt_required: draft.elemental_interrupt_required,`를 더한다.

- [ ] **Step 4: 체크박스와 prop을 넣는다**

`BossProfileField.tsx`의 props에 추가:

```tsx
interface BossProfileFieldProps {
  value: BossProfileDraft
  errors?: BossProfileDraftErrors
  onChange: (value: BossProfileDraft) => void
  /** 속성저지 필수를 그릴지. 유니온레이드 탭은 탐색이 없어 제약이 걸 곳이 없으므로
   * 항목 자체를 감춘다 - 켤 수는 있는데 아무 일도 안 일어나는 것이 더 나쁘다. */
  showElementalInterrupt?: boolean
}
```

구조분해에 `showElementalInterrupt = true`를 더하고, 「부위파괴 기믹」 행 뒤에:

```tsx
      {showElementalInterrupt && (
        <div className="checkbox-row">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={value.elemental_interrupt_required}
              onChange={(event) =>
                onChange({ ...value, elemental_interrupt_required: event.target.checked })
              }
            />
            속성저지 필수
          </label>
          <HelpTip label="속성저지 필수">
            <HelpText>{HELP.boss.elementalInterrupt}</HelpText>
          </HelpTip>
        </div>
      )}
```

`helpText.ts`의 `boss`에:

```ts
    elementalInterrupt:
      '기믹을 파훼하려면 **약점 속성 니케가 덱마다 최소 1기** 필요해요. 켜면 추천이 그 조건을 지키는 편성만 내놔요. 약점 속성 니케가 덱 수보다 적으면 채울 수 있는 덱까지만 지키고, 나머지 덱에는 파훼 불가 표시가 붙어요. 무속성 보스에서는 무시돼요.',
```

`UnionRaidPanel.tsx`의 `<BossProfileField ... />` 호출에 `showElementalInterrupt={false}`를
더한다.

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx src/components/UnionRaidPanel.test.tsx src/types/bossProfileDraft.test.ts`
Expected: PASS

- [ ] **Step 6: 프론트 전체 테스트 + 빌드**

Run: `cd frontend && npm test && npm run lint && npm run build`
Expected: 전부 통과

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/types frontend/src/components frontend/src/lib/helpText.ts
git commit -m "Offer the elemental-interrupt requirement on the tabs that actually search"
```

---

## Task 12: 파훼 불가 덱에 경고 배지

**Files:**
- Modify: `frontend/src/components/DeckCard.tsx` (`UnitLookups`, 카드 헤더)
- Modify: `frontend/src/components/RecommendPanel.tsx` (lookups 구성부)
- Modify: `frontend/src/App.css`
- Test: `frontend/src/components/DeckCard.test.tsx` (없으면 생성)

**Interfaces:**
- Consumes: `weaknessFor` (Task 2), `SupportedUnit.element`
- Produces: `UnitLookups.gimmickUnmetFor?: (deckSlugs: string[]) => boolean` —
  `DeckResults` · `RaidResults` · `DraftResults` · `EvaluationResults`가 이미
  `{...lookups}`를 `DeckCard`로 그대로 흘리므로, 네 화면 전부가 한 번에 얻는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/DeckCard.test.tsx`에 추가(없으면 생성):

```tsx
// 파훼 불가 배지는 API가 아니라 화면이 판정한다 - supported-units가 슬러그별 속성을
// 주므로 응답에 필드를 더할 이유가 없다.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DeckCard } from './DeckCard'

const DECK = {
  deck: ['a', 'b', 'c', 'd', 'e'],
  total_damage: 1000,
  burst_damage: 500,
  normal_attack_damage: 400,
  skill_damage: 100,
}

describe('DeckCard 속성저지 배지', () => {
  it('파훼 불가 덱에 경고를 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} gimmickUnmetFor={() => true} />)

    expect(screen.getByText('속성저지 파훼 불가')).toBeInTheDocument()
  })

  it('파훼 가능한 덱에는 아무것도 안 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} gimmickUnmetFor={() => false} />)

    expect(screen.queryByText('속성저지 파훼 불가')).not.toBeInTheDocument()
  })

  it('판정자가 없으면 아무것도 안 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} />)

    expect(screen.queryByText('속성저지 파훼 불가')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/DeckCard.test.tsx`
Expected: FAIL — `속성저지 파훼 불가` 텍스트가 없다

- [ ] **Step 3: DeckCard를 넓힌다**

`DeckCard.tsx`의 `UnitLookups`에:

```ts
  /** 이 덱이 보스의 속성저지 기믹을 파훼할 수 없는지. 판정은 화면이 한다 —
   * supported-units가 슬러그별 속성을 주므로 응답에 필드를 더할 이유가 없다.
   * 없으면(제약이 꺼졌거나 판정할 보스가 없으면) 배지도 없다. */
  gimmickUnmetFor?: (deckSlugs: string[]) => boolean
```

구조분해에 `gimmickUnmetFor`를 더하고, 헤더의 `deck-results__total` 뒤에:

```tsx
        {gimmickUnmetFor?.(deck.deck) && (
          <span className="deck-results__warning">
            <span aria-hidden="true">⚠</span> 속성저지 파훼 불가
          </span>
        )}
```

`App.css`에:

```css
/* 파훼 불가 표시는 덱을 부정하지 않는다 - 대미지는 그대로 유효하고, 기믹만 못
   깬다. 그래서 danger가 아니라 경고 색이다. */
.deck-results__warning {
  font-size: 12px;
  color: var(--warning, var(--danger));
  white-space: nowrap;
}
```

> `--warning` 토큰이 `App.css`에 없으면 `var(--danger)` 폴백이 쓰인다. 토큰 목록을
> `grep -n "^  --" frontend/src/App.css`로 확인하고, 있으면 폴백을 지운다.

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/DeckCard.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: RecommendPanel이 판정자를 만든다**

`RecommendPanel.tsx`에서 `submittedBoss`(제출 시점에 고정된 보스)와
`supportedUnits`를 이미 갖고 있다. 결과를 그리는 lookups에 아래를 더한다:

```tsx
  // 제출 시점의 보스로 판정한다 - 화면의 라이브 보스 필드를 읽으면, 결과가 그대로인데
  // 플레이어가 체크박스를 만지는 순간 배지가 붙었다 떨어졌다 한다(evaluatedBossElement가
  // 존재하는 것과 같은 이유).
  const gimmickUnmetFor = useMemo(() => {
    const boss = evaluatedBoss
    if (!boss?.elemental_interrupt_required || boss.element === null) return undefined
    const weakness = weaknessFor(boss.element)
    const elementOf = new Map(supportedUnits.map((u) => [u.slug, u.element]))
    return (deckSlugs: string[]) => !deckSlugs.some((s) => elementOf.get(s) === weakness)
  }, [evaluatedBoss, supportedUnits])
```

`evaluatedBossElement`(현재 `BossElement` 하나만 붙잡는 상태)를 `evaluatedBoss`
(`BossProfile | null`)로 넓히고, `setEvaluatedBossElement(bossProfile.element)`를
`setEvaluatedBoss(bossProfile)`로 바꾼다. `EvaluationResults`에 넘기던
`bossElements={evaluation.decks.map(() => evaluatedBossElement)}`는
`evaluation.decks.map(() => evaluatedBoss?.element ?? null)`이 된다.

그런 다음 결과 컴포넌트 네 곳에 `gimmickUnmetFor={gimmickUnmetFor}`를 넘긴다
(`DeckResults` · `RaidResults` · `DraftResults` · `EvaluationResults` — 전부
`UnitLookups`를 확장하고 있으므로 prop 이름만 맞추면 된다).

- [ ] **Step 6: 프론트 전체 테스트 + 빌드**

Run: `cd frontend && npm test && npm run lint && npm run build`
Expected: 전부 통과

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components frontend/src/App.css
git commit -m "Flag a recommended deck that cannot break the boss's elemental interrupt"
```

---

## Task 13: 종단 검증과 문서

**Files:**
- Modify: `docs/roadmap.md`
- Modify: `docs/insights.md` · `docs/decisions.md` (`/document` 경유)

- [ ] **Step 1: 백엔드·프론트 전체 테스트**

Run:
```bash
cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
cd ../frontend && npm test && npm run lint && npm run build
```
Expected: 백엔드 1788+ passed / 3 skipped, 프론트 467+ passed. **출력이 깨끗해야 한다** —
예상된 에러 로그도 테스트가 잡아야 한다.

- [ ] **Step 2: 캘리브레이션이 안 움직였는지 확인한다**

Run: `python scripts/measure_record_calibration.py`
Expected: 합계 **1.077x** 그대로. 세 항목 전부 기본값이 off이므로 한 자리도 움직이면
안 된다. 움직였으면 여기서 멈추고 원인을 찾는다 — 회귀다.

- [ ] **Step 3: 앱을 실제로 띄워 눈으로 본다**

`/run` 스킬(또는 `docs`의 실행 절차)로 앱을 띄우고 확인한다:
- 보스 설정에 아이콘 6개가 뜨고, 클릭하면 선택 테두리가 속성 색으로 바뀐다
- 「상시 코어 2관통」을 켜면 「코어 피격 가능」도 함께 켜진다
- 「속성저지 필수」를 켜고 추천을 돌리면 모든 덱에 약점 속성 유닛이 있다
- 유니온레이드 탭에는 「속성저지 필수」가 없다

**CSS는 단위 테스트로 검증되지 않는다** (Vitest가 `css: false`). 이 단계를 건너뛰면
아이콘 배치가 깨진 채로 착륙한다.

- [ ] **Step 4: `docs/roadmap.md`를 갱신한다**

To-Do 체크리스트에서 이 작업에 해당하는 항목을 체크하거나, 없으면 완료 항목으로 추가한다.
남은 후속 하나를 To-Do에 새로 적는다:

```markdown
- [ ] 코어 2관통 보스에서 실기록 대조 — 켠 상태의 캘리브레이션이 없다
      (`docs/superpowers/specs/2026-08-03-boss-weakness-and-gimmick-fields-design.md`
      「이 설계가 가르지 못하는 것」)
```

- [ ] **Step 5: 결정과 인사이트를 기록한다**

`/document`를 호출해 docs-keeper에게 아래를 넘긴다:

- **결정 1**: 약점 ↔ 보스 본인 속성 변환을 UI 경계에 가둔다. 대안은 와이어를 약점으로
  바꾸는 것이었고, `boss_is_element` 조건부 스킬이 보스 본인 속성을 읽는다는 점과 저장된
  프로필 마이그레이션 비용 때문에 기각했다.
- **결정 2**: 속성저지를 사후 보수가 아니라 **덱 생성 시점**의 술어로 넣는다. 사후 보수는
  탐색이 제약을 어기는 방향으로 수렴한 뒤라 손실 폭을 예측할 수 없다.
- **결정 3**: 약점유닛이 모자라면 채울 수 있는 덱까지만 만족시키고 경고한다. 추천을
  거부하지 않는다.
- **인사이트 1**: 덱 합법성이 지금까지 유닛만 보는 술어였고, 보스 의존 제약은 이것이
  처음이다. 생성기 3종 · 풀 pruning · cascade shortlist · 힐클라임까지 전부 손대야 한다.
- **인사이트 2**: `evaluate_deck`이 `simulate_raid`에 보스 필드를 **이름으로 나열해서**
  넘기고 있었다 — `api.boss_profile`이 2026-07-31에 `effective_range_band`를 흘린 것과
  같은 함정이 한 층 아래 그대로 있었고, 이제 테스트가 막는다.
- **인사이트 3**: 힐클라임 가드의 하한은 `K`가 아니라 `min(K, 현재값)`이어야 한다.
  `K`를 그대로 쓰면 `K`에 못 미치는 상태에서 모든 스왑이 거부되어 클라임이 통째로 죽는다.

- [ ] **Step 6: 브랜치를 트렁크에 병합한다**

```bash
git checkout wip/scaffolding
git merge --no-ff wip/boss-weakness-and-gimmicks
```

병합 후 백엔드·프론트 전체 테스트를 한 번 더 돌린다.

- [ ] **Step 7: 커밋**

```bash
git add docs/
git commit -m "Record the boss weakness/interrupt/core-pierce work in the knowledge base"
```

---

## 자체 리뷰 결과

계획을 스펙과 대조한 결과 아래 두 가지를 계획에 반영했다.

1. **스펙 B.6의 "전수 탐색 fallback"을 풀 보강으로 바꿨다.** 스펙은 pruning이 약점유닛을
   다 잘라냈을 때 전수 탐색으로 되돌리라고 썼는데, 78유닛 로스터의 전수 탐색은 수백만
   ordering이라 단일 덱 탐색에서 감당이 안 된다. `_ensure_weakness_in_pool`이 잘린 풀에
   티어별 최고 약점유닛을 되채워 넣는 쪽이 같은 보장을 훨씬 싸게 준다. `_reference_deck`이
   이미 쓰는 "짧게 내지 말고 넓혀라" 패턴이다. `best_completions`의 기존 fallback은
   그대로 남는다.
2. **`evaluate_deck`의 나열 함정에 대한 테스트를 Task 6에 추가했다.** 스펙에는 없었지만,
   `api.py`의 스프레드가 막은 것과 같은 종류의 구멍이 한 층 아래 남아 있었다.
3. **탐색·배분 테스트를 실제 시뮬레이션이 아니라 스텁 로스터 + `patch_scorer`로 잡았다.**
   `tests/test_deck_allocation.py`가 이미 쓰는 방식이다. 이유는 속도가 아니라 **대비를
   만들 수 있다는 것**: 점수를 우리가 정하므로 "제약이 없으면 다른 답이 나온다"를 단언할
   수 있고, 실제 시뮬레이션으로는 그 대비가 안 만들어진다. peel 배분 테스트가
   "몰아넣기가 더 높은 점수"인 시나리오를 쓰는 것이 그래서다 — 무차별 점수였다면 상한이
   없어도 테스트가 통과했을 것이다.

스펙의 나머지 항목(A.1~A.5, B.1~B.8, C.1~C.5, 테스트 절 전부)은 각각 대응하는 Task가 있다.

### 스펙 대비 커버리지

| 스펙 | Task |
| --- | --- |
| A.1 와이어 불변 | 2 (변환 모듈), 3 (draft가 보스 본인 속성을 담는다) |
| A.2 아이콘 자산 | 1 |
| A.3 변환 모듈 | 2 |
| A.4 폼 | 3 |
| A.5 결과 표시 | 4 |
| B.1 의미 · B.5 술어 | 8 |
| B.2 채울 수 있는 덱까지 | 10 (peel 배분 + 얇은 로스터 테스트) |
| B.3 적용 범위 | 9 (단일·드래프트), 10 (5덱), 11 (유니온 미노출) |
| B.4 와이어 | 8 (백엔드), 11 (프론트) |
| B.6 생성 시점 필터 + fallback 둘 | 9 |
| B.7 peel 배분 · 힐클라임 가드 | 10 |
| B.8 경고 배지, API 변경 없음 | 12 |
| C.1 대미지 모델 · C.3 엔진 | 5 |
| C.2 와이어 + core_hittable 의존 | 6 (백엔드), 7 (프론트 토글) |
| C.4 자동 배제 | 5 (스킬딜 · core_hittable off 테스트) |
| C.5 무기변형 포함 | 5 (`test_a_weapon_transform_shot_lands_twice_too`) |
| 테스트 절 전체 | 각 Task의 Step 1 |
| 캘리브레이션 불변 | 13 Step 2 |
