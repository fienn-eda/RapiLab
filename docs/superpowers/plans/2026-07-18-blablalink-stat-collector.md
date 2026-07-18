# blablalink/ShiftyPad 스탯 수집기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **상태 (2026-07-18 확인):** Task 1–6 **전부 구현 완료**되어 출하됨 — 체크박스가 비어
> 있던 것은 진행 중 문서를 갱신하지 않았기 때문이며, 미구현을 뜻하지 않았다(코드로 대조
> 확인: `capture.js`/`parse.js`(9 테스트)/`collect.js`, `models.py`의 `actual_*`,
> `nikkeDraft.ts`의 `actualAtk`, `ImportRosterButton`의 `'units' in raw` 분기).
> **남은 것은 Post-implementation의 추천 정확도 E2E 1건뿐**(§442) — 400레벨 스탯이 추천
> 결과를 실제로 바꾸는지의 확인으로, `scripts/verify_raid400_correction.py`가 수행한다.

**Goal:** 로그인된 blablalink 세션에서 ShiftyPad을 스크랩해 유닛별 정확 스탯(실제레벨 + 솔로레이드 400레벨)·오버로드·스킬·큐브를 수집하는 헬퍼를 만들고, 그 결과를 앱 로스터로 임포트한다. 솔로레이드 추천이 400레벨 스탯을 쓰도록 교정한다.

**Architecture:** Node/Playwright 수집기가 CDP로 Fienn의 로그인 Chrome에 붙어 유닛별 `?nikke=<resource_id>` 페이지를 스크랩(레벨 400 세팅 + 메인패널 + Equipment Effects + Skill/Cube/Collection 탭) → `roster.json` 출력. 파서는 순수 함수로 분리해 캡처된 HTML 픽스처에 대해 jsdom으로 TDD. 백엔드는 `actual_*` 스탯 필드를 추가하고 `hp/atk/def`를 400레벨 의미로 재정의(엔진 무변경). 프론트는 roster.json을 NikkeDraft로 매핑해 Phase A 병합 setter로 임포트.

**Tech Stack:** Node + playwright-core(CDP) + jsdom(파서 테스트) / Python FastAPI(백엔드) / React+TS+Vitest(프론트).

## Global Constraints

- 설계·결정: `docs/superpowers/specs/2026-07-18-blablalink-stat-collector-design.md`.
- **자격증명 저장 금지.** 세션은 Fienn 브라우저(CDP). 수집기는 쿠키를 읽어 API 폴백 호출에만 쓰고 파일로 저장하지 않는다. **캡처 픽스처는 정제**(계정 식별자·쿠키·전투력 등 제거/더미).
- **추측 금지(CLAUDE.md).** 라이브 셀렉터/DOM 구조는 Task 1 스파이크에서 실물로 확정한 뒤 코딩. 확정 전 파서 코드를 지어내지 않는다.
- **폴백은 언제나 수동/Phase A 파일임포트.** ShiftyPad 실패 시 앱은 수동 폼으로 degrade.
- 오버로드 draft `name`은 백엔드 `overload_effects.py` 한글 7종과 정확히 일치.
- `hp/atk/def` = **솔로레이드 400레벨** 값. `actual_*` = 실제레벨(유니온레이드 후속용, 저장만).
- 프론트 테스트는 `frontend/`에서 `npm test`. 백엔드는 `python3 -m pytest -q`(출력 pristine).
- 기존 코드 스타일 준수(프론트 2-space·세미콜론 없음·화살표; 백엔드 기존 관례).

---

## File Structure

- `tools/collect-blablalink/` (신규) — Node 수집기.
  - `package.json`, `capture.js`(스파이크 산출·재사용), `collect.js`(오케스트레이션), `parse.js`(순수 파서), `parse.test.js`(jsdom TDD), `__fixtures__/*.html`.
- `backend/app/models.py` (수정) — `actual_hp/actual_atk/actual_def` 옵셔널 필드.
- `backend/tests/test_models.py` (수정) — 필드 검증.
- `frontend/src/types/userNikkeState.ts`·`nikkeDraft.ts` (수정) — TS 미러 + draft 필드.
- `frontend/src/lib/rosterImport.ts`·`.test.ts` (신규) — roster.json → NikkeDraft.
- `frontend/src/components/ImportRosterButton.tsx` (수정) — roster.json 업로드 분기.

---

### Task 1: 스크랩 레시피 확정 + 픽스처 캡처 (라이브 스파이크)

> 라이브 SPA 리버싱이라 사전 코드가 아니라 **실물 확정 + 산출물**로 정의한다. Fienn의 로그인
> Chrome(원격 디버깅 9222)이 필요. `tools/collect-blablalink/`에서 playwright-core 사용.

**Files:**
- Create: `tools/collect-blablalink/package.json`, `capture.js`, `__fixtures__/`, `RECIPE.md`

**Produces (다음 태스크가 의존):**
- 유닛 2~3명(가급적 Attacker/Supporter/Defender 각 1 + 애장품 보유 1)의 **정제된 HTML 픽스처**:
  메인패널(레벨 400 세팅 상태) + Equipment Effects + Skill/Cube/Collection 탭 각각.
  파일명 규약: `__fixtures__/<slug>.<surface>.html` (surface = main|skill|cube|collection).
- `RECIPE.md`: 확정된 스크랩 절차 — (a) 레벨을 정확히 400으로 세팅하는 방법(버튼/현재레벨 판별),
  (b) Skill/Cube/Collection 탭을 여는 셀렉터, (c) 보유 유닛 목록 취득 방법(ShiftyPad 리스트 vs
  raw API `GetUserCharacters`), (d) resource_id 획득. 각 항목에 실제 셀렉터/단계 기록.

- [x] **Step 1: 워크스페이스 + CDP 접속 확인**

`tools/collect-blablalink/package.json` 생성 후 `npm i playwright-core`. `capture.js`로
`chromium.connectOverCDP('http://localhost:9222')` 접속, `/shiftyspad/nikke?nikke=<rid>` 이동 확인.

- [x] **Step 2: 레벨 400 세팅 확정**

메인패널이 `실제값 + (슬라이더가 400일 때)델타` 구조임은 확인됨(Rapi: ATK 418862/−275319→143543).
레벨 컨트롤은 커스텀 버튼(`-263/-10/-1/+1/+10`, `input[type=range]` 아님). **현재 레벨을 읽고 400까지
정확히 이동하는 절차**를 실물로 확정(synchro=663이면 `-263` 1회지만 일반화 필요). RECIPE.md에 기록.

- [x] **Step 3: 탭 스크랩 확정**

Cube/Collection 탭은 `page.getByText('Cube'/'Collection', {exact:true})` 클릭으로 전환 확인됨.
Skill 탭은 "not visible" 이슈 → 보이는 탭 컨트롤 셀렉터를 실물로 확정(예: 특정 클래스/역할 속성).
실패 시 스킬레벨은 raw API 폴백으로 결정하고 RECIPE.md에 명시.

- [x] **Step 4: 보유 유닛 목록 확정**

ShiftyPad 리스트 뷰(`from=list`)에서 보유 유닛+resource_id를 긁을 수 있는지 확인. 안 되면 raw API
`GetUserCharacters`(name_code) + 디렉토리(name_code→resource_id) 폴백. RECIPE.md에 확정.

- [x] **Step 5: 픽스처 캡처 + 정제**

확정된 절차로 2~3 유닛의 각 surface HTML을 `page.content()`로 저장. **정제:** `game_uid`·`cookie`·
계정명·전투력 등 식별자를 더미로 치환(스크립트화). 픽스처에 자격증명이 없음을 grep으로 검증.

- [x] **Step 6: 커밋**

```bash
git add tools/collect-blablalink/package.json tools/collect-blablalink/capture.js tools/collect-blablalink/RECIPE.md tools/collect-blablalink/__fixtures__
git commit -m "feat: blablalink scrape recipe + sanitized ShiftyPad fixtures"
```

---

### Task 2: 파서 (픽스처 기반 TDD)

캡처된 HTML을 파싱하는 순수 함수. jsdom으로 픽스처에 대해 테스트. 아래 파싱 로직은 라이브
프로브로 검증된 것(메인패널/오버로드). 탭 파싱은 Task 1 RECIPE의 확정 구조를 따른다.

**Files:**
- Create: `tools/collect-blablalink/parse.js`, `tools/collect-blablalink/parse.test.js`
- Uses: `__fixtures__/*.html`(Task 1), `jsdom`(dev dep)

**Interfaces / Produces:**
- `parseMainStats(doc): { actual:{hp,atk,def}, raid400:{hp,atk,def} }`
- `parseOverload(doc): { name:string, value:number }[]` (한글 7종, 미매핑 드롭)
- `parseCube(doc): { name:string, level:number } | null`
- `parseSkills(doc): { skill1:number, skill2:number, burst:number }` (Skill surface, 폴백 시 별도)

- [x] **Step 1: 실패 테스트 (메인 스탯)**

`tools/collect-blablalink/parse.test.js`:
```js
const fs = require('fs')
const path = require('path')
const { JSDOM } = require('jsdom')
const { parseMainStats, parseOverload } = require('./parse')

const doc = (slug, surface) =>
  new JSDOM(fs.readFileSync(path.join(__dirname, '__fixtures__', `${slug}.${surface}.html`), 'utf8')).window.document

test('parseMainStats returns actual and level-400 stats', () => {
  const r = parseMainStats(doc('rapi-red-hood', 'main'))
  expect(r.actual.atk).toBe(418862)
  expect(r.raid400.atk).toBe(143543) // actual + delta
  expect(r.raid400.hp).toBe(3532402)
  expect(r.raid400.def).toBe(20986)
})

test('parseOverload maps English labels to the Korean stat names, summed', () => {
  const rows = parseOverload(doc('rapi-red-hood', 'main'))
  expect(rows).toContainEqual({ name: '공격력 증가', value: 42.32 })
  expect(rows).toContainEqual({ name: '우월코드 대미지 증가', value: 87.21 })
})
```

- [x] **Step 2: 실패 확인**

Run: `cd tools/collect-blablalink && npx jest parse.test.js` (또는 `node --test`)
Expected: FAIL — `parse` 모듈/함수 없음. (테스트 러너는 Task 1에서 `npm i -D jest` 또는 node:test로 확정.)

- [x] **Step 3: 구현 (검증된 파싱 로직)**

`tools/collect-blablalink/parse.js`:
```js
// Pure parsers over a ShiftyPad nikke-page Document. No network, no Playwright.

const num = (s) => parseInt(String(s).replace(/[^0-9-]/g, ''), 10)

// Main stat panel: each of POWER/HP/ATK/DEF shows "<actual> \n <negative delta to selected level>".
// With the level slider at 400, level-400 value = actual + delta.
const parseMainStats = (doc) => {
  const els = [...doc.querySelectorAll('*')]
  const lvEl = els.find((e) => e.children.length === 0 && /^LV\s*\d+/i.test((e.textContent || '').trim()))
  let box = lvEl
  for (let i = 0; i < 8 && box && box.parentElement; i++) {
    box = box.parentElement
    if (/POWER|HP|ATK|DEF/i.test(box.textContent) && box.textContent.length < 600) break
  }
  const lines = (box.textContent || '').split('\n').map((s) => s.trim()).filter(Boolean)
  const out = { actual: {}, raid400: {} }
  const key = { HP: 'hp', ATK: 'atk', DEF: 'def' }
  for (let i = 0; i < lines.length; i++) {
    const k = key[lines[i].toUpperCase()]
    if (!k) continue
    const actual = /^[0-9,]+$/.test(lines[i + 1] || '') ? num(lines[i + 1]) : null
    const delta = /^-[0-9,]+$/.test(lines[i + 2] || '') ? num(lines[i + 2]) : 0
    if (actual !== null) { out.actual[k] = actual; out.raid400[k] = actual + delta }
  }
  return out
}

const OVERLOAD_LABEL_TO_NAME = {
  'Increase ATK': '공격력 증가',
  'Increase Element Damage Dealt': '우월코드 대미지 증가',
  'Increase Critical Damage': '크리티컬 대미지 증가',
  'Increase Critical Rate': '크리티컬 확률 증가',
  'Increase Charge Damage': '차지 대미지 증가',
  'Increase Charge Speed': '차지 속도 증가',
  'Increase Max Ammunition Capacity': '최대 장탄 수 증가',
}

// "Equipment Effects" section: pairs of (English label, "NN.NN%"). Already summed across 4 pieces.
const parseOverload = (doc) => {
  const text = doc.body.textContent || ''
  const start = text.indexOf('Equipment Effects')
  const region = start >= 0 ? text.slice(start, start + 400) : text
  const rows = []
  const re = /(Increase [A-Za-z ]+?)\s*([0-9]+(?:\.[0-9]+)?)%/g
  let m
  while ((m = re.exec(region))) {
    const name = OVERLOAD_LABEL_TO_NAME[m[1].trim()]
    if (name) rows.push({ name, value: parseFloat(m[2]) })
  }
  return rows
}

module.exports = { parseMainStats, parseOverload }
```
(파싱 로직은 라이브 프로브 `mainstats.js`/full-text 덤프로 검증됨. `parseCube`/`parseSkills`는
Task 1 RECIPE의 확정 탭 구조에 맞춰 같은 파일에 추가 — 픽스처가 그 구조를 담으므로 TDD로 작성.)

- [x] **Step 4: 통과 확인** — `npx jest parse.test.js` PASS.

- [x] **Step 5: 커밋**
```bash
git add tools/collect-blablalink/parse.js tools/collect-blablalink/parse.test.js
git commit -m "feat: ShiftyPad HTML parsers (stats both levels, overload)"
```

---

### Task 3: 수집기 오케스트레이션

CDP 접속 → 보유목록 → 유닛 순회(이동·레벨400·탭) → 파서 호출 → `roster.json`. 라이브 조작이라
파서(Task 2)와 분리하고, 오케스트레이션은 스모크(로그·개수)로 검증.

**Files:**
- Create: `tools/collect-blablalink/collect.js`
- Uses: `parse.js`(Task 2), Task 1 RECIPE(레벨400·탭·목록 절차)

**Produces:** `roster.json` — `{ synchroLevel, units: [{ resource_id, name_en, slug, raid400:{hp,atk,def}, actual:{hp,atk,def}, overload:[{name,value}], skill_levels:{skill1,skill2,burst}, pve_cube:{name,level}|null }] }`

- [x] **Step 1: 구현** — `collect.js`: connectOverCDP → 보유목록(RECIPE) → 각 유닛 이동 →
  레벨400 세팅(RECIPE) → surface별 `page.content()` → `parse.*` → 누적. `--dry-run`(1유닛),
  `--out roster.json`, 진행 로그, 유닛 단위 try/catch(1명 실패가 전체를 안 죽임), resource_id→slug는
  Phase A `resolveSlug`(name_en) 재사용(모듈 공유 또는 복제 — Task 5에서 확정).
- [x] **Step 2: 스모크 실행** — Fienn 세션에 대해 `node collect.js --dry-run`. 1유닛 roster.json이
  raid400/actual/overload/skills/cube를 담는지 육안 + `parse.test` 픽스처와 형태 일치 확인.
- [x] **Step 3: 커밋**
```bash
git add tools/collect-blablalink/collect.js
git commit -m "feat: blablalink collector orchestration -> roster.json"
```

---

### Task 4: 백엔드 모델 — 실제레벨 스탯 필드

`hp/atk/def`는 **솔로레이드 400레벨** 의미(엔진 무변경). 유니온레이드용 실제레벨을 옵셔널 추가.

**Files:**
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_models.py`

**Interfaces:** `UserNikkeState`에 `actual_hp: float|None`, `actual_atk: float|None`, `actual_def: float|None`(기본 None, `ge=0`).

- [x] **Step 1: 실패 테스트**

`backend/tests/test_models.py`에 추가:
```python
def test_user_nikke_state_accepts_actual_level_stats():
    s = UserNikkeState(
        character_slug="rapi-red-hood", level=400, core_level=0,
        hp=3532402, atk=143543, def_=20986,
        actual_hp=9727100, actual_atk=418862, actual_def=55537,
        skill_levels=SkillLevels(skill1=10, skill2=10, burst=10),
        overload_options=[], pve_cube=None,
    )
    assert s.actual_atk == 418862

def test_actual_level_stats_default_to_none():
    s = UserNikkeState(
        character_slug="liter", level=400, core_level=0,
        hp=1, atk=1, def_=1,
        skill_levels=SkillLevels(skill1=1, skill2=1, burst=1),
        overload_options=[], pve_cube=None,
    )
    assert s.actual_atk is None
```
(기존 `SkillLevels`/`UserNikkeState` import 재사용 — 파일 상단 확인.)

- [x] **Step 2: 실패 확인** — `python3 -m pytest backend/tests/test_models.py -q` FAIL(`actual_atk` 미정의).

- [x] **Step 3: 구현** — `backend/app/models.py`의 `UserNikkeState`에 필드 추가(기존 `def_` 근처):
```python
    actual_hp: float | None = Field(default=None, ge=0)
    actual_atk: float | None = Field(default=None, ge=0)
    actual_def: float | None = Field(default=None, ge=0)
```

- [x] **Step 4: 통과 확인** — `python3 -m pytest backend/tests/test_models.py -q` PASS(기존 모델 테스트 포함).

- [x] **Step 5: 커밋**
```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: UserNikkeState optional actual-level stats (union raid)"
```

---

### Task 5: 프론트 타입 + roster.json 임포터

roster.json을 `NikkeDraft[]`로 매핑하고 Phase A `mergeRosterDrafts`로 병합. `hp/atk/def`←raid400.

**Files:**
- Modify: `frontend/src/types/userNikkeState.ts`, `frontend/src/types/nikkeDraft.ts`
- Create: `frontend/src/lib/rosterImport.ts`, `frontend/src/lib/rosterImport.test.ts`

**Interfaces:**
- `UserNikkeState`(TS)·`NikkeDraft`에 `actualHp/actualAtk/actualDef`(문자열, draft) 추가(백엔드 미러).
- `parseRosterJson(raw: unknown): { drafts: NikkeDraft[]; warnings: string[] }`.

- [x] **Step 1: 실패 테스트**

`frontend/src/lib/rosterImport.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { parseRosterJson } from './rosterImport'

const sample = () => ({
  synchroLevel: 663,
  units: [
    {
      resource_id: 16, name_en: 'Rapi: Red Hood', slug: 'rapi-red-hood',
      raid400: { hp: 3532402, atk: 143543, def: 20986 },
      actual: { hp: 9727100, atk: 418862, def: 55537 },
      overload: [{ name: '공격력 증가', value: 42.32 }],
      skill_levels: { skill1: 10, skill2: 10, burst: 10 },
      pve_cube: { name: 'Resilience Cube', level: 15 },
    },
  ],
})

describe('parseRosterJson', () => {
  it('maps a unit: raid-400 into hp/atk/def, actual into actual_*, overload/skills/cube', () => {
    const { drafts } = parseRosterJson(sample())
    const d = drafts[0]
    expect(d.character_slug).toBe('rapi-red-hood')
    expect(d.atk).toBe('143543')      // solo raid = level 400
    expect(d.actualAtk).toBe('418862') // union raid = actual level
    expect(d.skill_levels).toEqual({ skill1: '10', skill2: '10', burst: '10' })
    expect(d.overload_options[0]).toMatchObject({ name: '공격력 증가', value: '42.32' })
    expect(d.hasCube).toBe(true)
    expect(d.pve_cube).toEqual({ name: 'Resilience Cube', level: '15' })
  })

  it('throws on non-roster input', () => {
    expect(() => parseRosterJson({})).toThrow(/units/)
  })
})
```

- [x] **Step 2: 실패 확인** — `cd frontend && npm test -- src/lib/rosterImport.test.ts` FAIL.

- [x] **Step 3: 구현**

`frontend/src/types/nikkeDraft.ts`의 `NikkeDraft`에 `actualHp: string; actualAtk: string; actualDef: string` 추가 + `makeEmptyDraft`에 `actualHp:'',actualAtk:'',actualDef:''` + `validateDraft`에서 빈 문자열이면 `actual_*`를 넣지 않음(옵셔널). `userNikkeState.ts`에 `actual_hp?/actual_atk?/actual_def?: number` 미러.

`frontend/src/lib/rosterImport.ts`:
```ts
import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'

interface RosterUnit {
  slug: string
  raid400: { hp: number; atk: number; def: number }
  actual?: { hp: number; atk: number; def: number }
  overload?: { name: string; value: number }[]
  skill_levels?: { skill1: number; skill2: number; burst: number }
  pve_cube?: { name: string; level: number } | null
}
interface RosterJson { synchroLevel?: number; units?: RosterUnit[] }

export const parseRosterJson = (raw: unknown): { drafts: NikkeDraft[]; warnings: string[] } => {
  const data = raw as RosterJson
  if (!data || typeof data !== 'object' || !Array.isArray(data.units)) {
    throw new Error('Not a collector roster: missing "units".')
  }
  const drafts: NikkeDraft[] = []
  const warnings: string[] = []
  for (const u of data.units) {
    if (!u || !u.slug) { warnings.push('unit missing slug'); continue }
    const base = makeEmptyDraft()
    drafts.push({
      ...base,
      character_slug: u.slug,
      level: '400',
      hp: String(u.raid400.hp), atk: String(u.raid400.atk), def_: String(u.raid400.def),
      actualHp: u.actual ? String(u.actual.hp) : '',
      actualAtk: u.actual ? String(u.actual.atk) : '',
      actualDef: u.actual ? String(u.actual.def) : '',
      skill_levels: {
        skill1: String(u.skill_levels?.skill1 ?? ''),
        skill2: String(u.skill_levels?.skill2 ?? ''),
        burst: String(u.skill_levels?.burst ?? ''),
      },
      overload_options: (u.overload ?? []).map((o) => ({ id: crypto.randomUUID(), name: o.name, value: String(o.value) })),
      hasCube: !!u.pve_cube,
      pve_cube: u.pve_cube ? { name: u.pve_cube.name, level: String(u.pve_cube.level) } : { name: '', level: '' },
    })
  }
  return { drafts, warnings }
}
```

- [x] **Step 4: 통과 확인** — `npm test -- src/lib/rosterImport.test.ts` + 기존 draft/roster 테스트 그린.

- [x] **Step 5: 커밋**
```bash
git add frontend/src/types/nikkeDraft.ts frontend/src/types/userNikkeState.ts frontend/src/lib/rosterImport.ts frontend/src/lib/rosterImport.test.ts
git commit -m "feat: roster.json importer (raid-400 stats + actual-level fields)"
```

---

### Task 6: 임포트 UI 배선 + 전체 검증

`ImportRosterButton`이 파일 형식을 감지: `elements` 있으면 ExiaInvasion(Phase A), `units` 있으면 collector roster.json.

**Files:**
- Modify: `frontend/src/components/ImportRosterButton.tsx`
- Test: `frontend/src/components/ImportRosterButton.test.tsx`

- [x] **Step 1: 실패 테스트** — collector roster.json 업로드 시 `onImport`가 `character_slug='rapi-red-hood'`·`atk='143543'` draft로 호출되는지. (기존 ExiaInvasion 케이스는 유지.)
```tsx
it('imports a collector roster.json (units) with raid-400 stats', async () => {
  const onImport = vi.fn((_d: NikkeDraft[]) => ({ added: 1, updated: 0 }))
  render(<ImportRosterButton onImport={onImport} />)
  const json = JSON.stringify({ synchroLevel: 663, units: [{ slug: 'rapi-red-hood', raid400: { hp: 1, atk: 143543, def: 1 } }] })
  await userEvent.upload(screen.getByLabelText(/import/i), new File([json], 'roster.json', { type: 'application/json' }))
  await waitFor(() => expect(onImport).toHaveBeenCalled())
  expect(onImport.mock.calls[0][0][0].atk).toBe('143543')
})
```

- [x] **Step 2: 실패 확인** — `npm test -- src/components/ImportRosterButton.test.tsx` FAIL.

- [x] **Step 3: 구현** — `handleChange`에서 `JSON.parse` 후 형식 분기:
```ts
    const parsed = 'units' in (raw as object)
      ? parseRosterJson(raw)          // collector
      : parseExiaExport(raw)          // ExiaInvasion (Phase A)
    const { added, updated } = onImport(parsed.drafts)
```
(import 추가: `import { parseRosterJson } from '../lib/rosterImport'`.)

- [x] **Step 4: 전체 검증** — `cd frontend && npm test`(전 스위트) + `npm run build`(tsc -b + vite) 클린. 백엔드 `python3 -m pytest -q` 그린.

- [x] **Step 5: 커밋**
```bash
git add frontend/src/components/ImportRosterButton.tsx frontend/src/components/ImportRosterButton.test.tsx
git commit -m "feat: import collector roster.json alongside ExiaInvasion export"
```

---

## Post-implementation

- [x] 실 세션으로 `collect.js` 전 유닛 수집 → 앱 임포트 → `POST /api/recommend`(솔로) 결과가 400레벨
      스탯 기준인지 E2E 확인. 663 대비 순위 변화 관측(정확도 교정 검증).
      → **완료 (2026-07-18)**, `scripts/verify_raid400_correction.py`로 수행.
      159유닛(인코딩 매핑 57 → 사용가능 53)을 400레벨/실제레벨 두 기준으로 각각 랭킹:
      **top-1 덱은 동일**하나 **top-5 구성이 달라짐**(400: maiden-ice-rose 진입 /
      실제레벨: dorothy-serendipity·ludmilla-winter-owner 진입). 절대 데미지는
      **2.91배 부풀림** — decisions.md가 예측한 2.9배와 일치. 즉 교정은 헤드라인 추천이
      아니라 **대안 순위와 절대 수치**를 바꿨다.
- [x] `docs/roadmap.md` Phase 7/B 상태 갱신.
- [x] `/document`로 결정/작업 문서화.

---

## Notes / 미해결(구현 중 확정)

- **Task 1 산출(RECIPE)이 Task 2~3의 셀렉터/절차를 확정한다.** 파서의 `parseCube`/`parseSkills`,
  레벨-400 세팅, 보유목록, Skill 탭 셀렉터는 픽스처 확정 후 코드화(지금 지어내지 않음).
- **오버로드 영문 라벨 7종 중 3종(크리댐·차지댐·차지속도)은 미관측** — 크리댐/차지 보유 유닛 픽스처로
  라벨 문자열 확정 후 `OVERLOAD_LABEL_TO_NAME` 교정.
- **유니온레이드 추천 로직은 범위 밖**(actual_* 저장만). 솔로레이드(400) 경로만 배선.
- **`level` 필드**: collector import는 400 고정. `core_level`은 inert이므로 생략(0).
