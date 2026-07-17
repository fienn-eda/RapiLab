# ExiaInvasion 로스터 임포터 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ExiaInvasion이 export한 blablalink 로스터 JSON을 읽어, 오버로드·스킬·돌파·레벨을 채운 `NikkeDraft`로 매핑하고 슬러그별 병합으로 로스터에 임포트하는 프론트엔드 UI를 만든다.

**Architecture:** 순수 파서(`lib/exiaImport.ts`)가 export JSON → `NikkeDraft[]` + warnings로 변환한다. 병합 로직은 순수 함수(`types/nikkeDraft.ts`의 `mergeRosterDrafts`)로 분리해 단위 테스트한다. `useRoster`는 이 병합을 감싸는 `importDrafts` setter를 노출하고, 새 `ImportRosterButton` 컴포넌트가 파일 입력 → 파싱 → 병합 → 요약을 잇는다. ATK/HP/DEF/큐브는 임포트하지 않고 수동 필드로 남긴다.

**Tech Stack:** React + TypeScript + Vite, Vitest + @testing-library/react. 백엔드 변경 없음.

## Global Constraints

- 설계 근거·결정 로그: `docs/superpowers/specs/2026-07-18-exia-roster-importer-design.md`.
- **`cookie`·`game_uid`는 절대 읽지도 저장하지도 않는다.** 파서는 매핑에 필요한 필드만 접근.
- 테스트는 네트워크·토큰 불요, 실제 계정 데이터 파일 커밋 금지. 테스트 입력은 **인라인 합성 픽스처**(실제 구조를 모사하되 자격증명 없음)로 만든다.
- 오버로드 draft `name`은 백엔드 `overload_effects.py`의 `NAME_TO_STAT` 한글 키와 **정확히 일치**해야 한다.
- 숫자 필드는 `NikkeDraft`에서 문자열로 보관(빈칸 허용). 임포터도 문자열로 채운다.
- 테스트 실행은 `frontend/`에서: 단일 파일 `npm test -- <경로>`, 전체 `npm test`.
- 기존 코드 스타일(2-space, 세미콜론 없음, 화살표 함수, `type`/`interface` 관례) 준수.

---

## File Structure

- `frontend/src/lib/exiaImport.ts` (신규) — 순수 파서: `resolveSlug`, `aggregateOverload`, `parseExiaExport`, 관련 타입.
- `frontend/src/lib/exiaImport.test.ts` (신규) — 위 테스트.
- `frontend/src/types/nikkeDraft.ts` (수정) — `mergeRosterDrafts` 순수 병합 함수 추가.
- `frontend/src/types/nikkeDraft.test.ts` (수정) — 병합 테스트 추가.
- `frontend/src/hooks/useRoster.ts` (수정) — `importDrafts` setter 추가.
- `frontend/src/hooks/useRoster.test.ts` (수정) — `importDrafts` 테스트 추가.
- `frontend/src/components/ImportRosterButton.tsx` (신규) — 파일 입력 → 파싱 → 병합 → 요약 UI.
- `frontend/src/components/ImportRosterButton.test.tsx` (신규) — 컴포넌트 테스트.
- `frontend/src/App.tsx` (수정) — `importDrafts`를 `ImportRosterButton`에 배선.

---

### Task 1: 슬러그 해석 (`resolveSlug`)

**Files:**
- Create: `frontend/src/lib/exiaImport.ts`
- Test: `frontend/src/lib/exiaImport.test.ts`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `deriveSlug(nameEn: string): string`
  - `resolveSlug(nameEn: string): string`

- [ ] **Step 1: Write the failing test**

`frontend/src/lib/exiaImport.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { deriveSlug, resolveSlug } from './exiaImport'

describe('deriveSlug', () => {
  it('kebab-cases a plain name', () => {
    expect(deriveSlug('Zwei')).toBe('zwei')
  })

  it('drops colons and parentheses', () => {
    expect(deriveSlug('Maiden: Ice Rose')).toBe('maiden-ice-rose')
    expect(deriveSlug('Rei (Tentative Name)')).toBe('rei-tentative-name')
    expect(deriveSlug('Asuka: WILLE')).toBe('asuka-wille')
  })
})

describe('resolveSlug', () => {
  it('passes an already-correct derived slug through', () => {
    expect(resolveSlug('Zwei')).toBe('zwei')
    expect(resolveSlug('Maiden: Ice Rose')).toBe('maiden-ice-rose')
  })

  it('applies the alias table for short in-game names', () => {
    expect(resolveSlug('Ada')).toBe('ada-wong')
    expect(resolveSlug('Jill')).toBe('jill-valentine')
    expect(resolveSlug('Rei')).toBe('rei-ayanami')
    expect(resolveSlug('Rei (Tentative Name)')).toBe('rei-ayanami-tentative-name')
    expect(resolveSlug('Asuka: WILLE')).toBe('asuka-shikinami-langley-wille')
    expect(resolveSlug('Soline')).toBe('soline-frost-ticket')
    expect(resolveSlug('Marciana')).toBe('marciana-marine-study')
    expect(resolveSlug('Takina')).toBe('takina-inoue')
    expect(resolveSlug('Chisato')).toBe('chisato-nishikigi')
  })

  it('leaves an unencoded unit as its derived slug (excluded downstream)', () => {
    expect(resolveSlug('Naga')).toBe('naga')
    expect(resolveSlug('Red Hood')).toBe('red-hood')
    expect(resolveSlug('Cinderella: Crystal Wave')).toBe('cinderella-crystal-wave')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- src/lib/exiaImport.test.ts`
Expected: FAIL — `exiaImport` module / exports not found.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/lib/exiaImport.ts`:
```ts
// Parses an ExiaInvasion export (blablalink roster JSON) into editable NikkeDrafts.
// Only the fields the export carries are mapped; ATK/HP/DEF and cube stay manual.
// The cookie/game_uid fields in the export are credentials and are never read.

// name_en (short in-game name) -> our character_slug, for the cases where the
// kebab-cased name does not already match our slug. Derived-slug keyed.
const SLUG_ALIASES: Record<string, string> = {
  rei: 'rei-ayanami',
  'rei-tentative-name': 'rei-ayanami-tentative-name',
  ada: 'ada-wong',
  jill: 'jill-valentine',
  'asuka-wille': 'asuka-shikinami-langley-wille',
  soline: 'soline-frost-ticket',
  marciana: 'marciana-marine-study',
  takina: 'takina-inoue',
  chisato: 'chisato-nishikigi',
}

export const deriveSlug = (nameEn: string): string =>
  nameEn
    .toLowerCase()
    .replace(/[()]/g, '')
    .replace(/:/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/ /g, '-')

export const resolveSlug = (nameEn: string): string => {
  const derived = deriveSlug(nameEn)
  return SLUG_ALIASES[derived] ?? derived
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/exiaImport.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/exiaImport.ts frontend/src/lib/exiaImport.test.ts
git commit -m "feat: ExiaInvasion importer slug resolution"
```

---

### Task 2: 오버로드 합산·매핑 (`aggregateOverload`)

**Files:**
- Modify: `frontend/src/lib/exiaImport.ts`
- Test: `frontend/src/lib/exiaImport.test.ts`

**Interfaces:**
- Consumes: `OverloadRow` from `../types/nikkeDraft`
- Produces:
  - `interface ExiaOverloadLine { function_type: string; function_value: number; level: number }`
  - `aggregateOverload(equipments: Record<string, ExiaOverloadLine[]>): { rows: OverloadRow[]; droppedTypes: string[] }`

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/lib/exiaImport.test.ts`:
```ts
import { aggregateOverload } from './exiaImport'

describe('aggregateOverload', () => {
  it('sums a function_type across the 4 gear pieces and maps to the Korean stat name', () => {
    const { rows } = aggregateOverload({
      '0': [{ function_type: 'IncElementDmg', function_value: 23.56, level: 11 }],
      '1': [{ function_type: 'IncElementDmg', function_value: 19.35, level: 8 }],
      '2': [{ function_type: 'StatAtk', function_value: 10.0, level: 4 }],
      '3': [],
    })
    expect(rows).toEqual([
      { id: expect.any(String), name: '우월코드 대미지 증가', value: '42.91' },
      { id: expect.any(String), name: '공격력 증가', value: '10' },
    ])
  })

  it('maps all seven known function types', () => {
    const { rows } = aggregateOverload({
      '0': [
        { function_type: 'StatAtk', function_value: 1, level: 1 },
        { function_type: 'IncElementDmg', function_value: 1, level: 1 },
        { function_type: 'StatCriticalDamage', function_value: 1, level: 1 },
        { function_type: 'StatCritical', function_value: 1, level: 1 },
        { function_type: 'StatChargeDamage', function_value: 1, level: 1 },
        { function_type: 'StatChargeTime', function_value: 1, level: 1 },
        { function_type: 'StatAmmoLoad', function_value: 1, level: 1 },
      ],
      '1': [],
      '2': [],
      '3': [],
    })
    expect(rows.map((r) => r.name)).toEqual([
      '공격력 증가',
      '우월코드 대미지 증가',
      '크리티컬 대미지 증가',
      '크리티컬 확률 증가',
      '차지 대미지 증가',
      '차지 속도 증가',
      '최대 장탄 수 증가',
    ])
  })

  it('drops unmapped function types (def, accuracy) and reports them', () => {
    const { rows, droppedTypes } = aggregateOverload({
      '0': [
        { function_type: 'StatDef', function_value: 5, level: 2 },
        { function_type: 'StatAccuracyCircle', function_value: 2.3, level: 1 },
        { function_type: 'StatAtk', function_value: 7, level: 3 },
      ],
      '1': [],
      '2': [],
      '3': [],
    })
    expect(rows).toEqual([
      { id: expect.any(String), name: '공격력 증가', value: '7' },
    ])
    expect(droppedTypes).toEqual(['StatDef', 'StatAccuracyCircle'])
  })

  it('returns nothing for empty equipments', () => {
    expect(aggregateOverload({})).toEqual({ rows: [], droppedTypes: [] })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/exiaImport.test.ts`
Expected: FAIL — `aggregateOverload` not exported.

- [ ] **Step 3: Write minimal implementation**

Add to `frontend/src/lib/exiaImport.ts` (add the `OverloadRow` import at the top):
```ts
import type { OverloadRow } from '../types/nikkeDraft'

export interface ExiaOverloadLine {
  function_type: string
  function_value: number
  level: number
}

// English overload stat key (function_type) -> the Korean name overload_effects.py
// maps. Only these seven have an engine consumer; anything else is dropped.
const FUNCTION_TYPE_TO_NAME: Record<string, string> = {
  StatAtk: '공격력 증가',
  IncElementDmg: '우월코드 대미지 증가',
  StatCriticalDamage: '크리티컬 대미지 증가',
  StatCritical: '크리티컬 확률 증가',
  StatChargeDamage: '차지 대미지 증가',
  StatChargeTime: '차지 속도 증가',
  StatAmmoLoad: '최대 장탄 수 증가',
}

export const aggregateOverload = (
  equipments: Record<string, ExiaOverloadLine[]>,
): { rows: OverloadRow[]; droppedTypes: string[] } => {
  const sums = new Map<string, number>()
  for (let slot = 0; slot < 4; slot++) {
    for (const line of equipments[String(slot)] ?? []) {
      sums.set(
        line.function_type,
        (sums.get(line.function_type) ?? 0) + line.function_value,
      )
    }
  }

  const rows: OverloadRow[] = []
  const droppedTypes: string[] = []
  for (const [type, sum] of sums) {
    const name = FUNCTION_TYPE_TO_NAME[type]
    if (name === undefined) {
      droppedTypes.push(type)
      continue
    }
    rows.push({
      id: crypto.randomUUID(),
      name,
      value: String(Math.round(sum * 100) / 100),
    })
  }
  return { rows, droppedTypes }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/exiaImport.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/exiaImport.ts frontend/src/lib/exiaImport.test.ts
git commit -m "feat: ExiaInvasion importer overload aggregation and mapping"
```

---

### Task 3: 최상위 파서 (`parseExiaExport`)

**Files:**
- Modify: `frontend/src/lib/exiaImport.ts`
- Test: `frontend/src/lib/exiaImport.test.ts`

**Interfaces:**
- Consumes: `resolveSlug`, `aggregateOverload` (Task 1–2); `NikkeDraft` from `../types/nikkeDraft`.
- Produces:
  - `type ImportWarning = { kind: 'dropped-overload'; nameEn: string; slug: string; droppedTypes: string[] } | { kind: 'skipped-character'; nameEn: string; reason: string }`
  - `interface ExiaImportResult { drafts: NikkeDraft[]; warnings: ImportWarning[] }`
  - `parseExiaExport(raw: unknown): ExiaImportResult` (throws `Error` on non-export input)

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/lib/exiaImport.test.ts`:
```ts
import { parseExiaExport } from './exiaImport'

const sampleExport = () => ({
  name: 'TESTER',
  game_uid: 'SHOULD-NOT-BE-READ',
  synchroLevel: 663,
  cookie: 'game_login_game=SECRET; token=SECRET',
  elements: {
    Electronic: [
      {
        name_en: 'Maiden: Ice Rose',
        skill1_level: 10,
        skill2_level: 9,
        skill_burst_level: 8,
        item_level: 15,
        item_rare: 'SR',
        limit_break: { grade: 3, core: 2 },
        equipments: {
          '0': [
            { function_type: 'IncElementDmg', function_value: 23.56, level: 11 },
            { function_type: 'StatDef', function_value: 5, level: 1 },
          ],
          '1': [{ function_type: 'IncElementDmg', function_value: 19.35, level: 8 }],
          '2': [],
          '3': [],
        },
      },
      {
        name_en: 'Ada',
        skill1_level: 1,
        skill2_level: 1,
        skill_burst_level: 1,
        limit_break: { grade: 0, core: 0 },
        equipments: { '0': [], '1': [], '2': [], '3': [] },
      },
    ],
    Iron: [
      {
        name_en: 'Naga',
        skill1_level: 5,
        skill2_level: 5,
        skill_burst_level: 5,
        limit_break: { grade: null, core: null },
        equipments: { '0': [], '1': [], '2': [], '3': [] },
      },
    ],
    Utility: [],
  },
})

describe('parseExiaExport', () => {
  it('maps a character: slug, synchro level, skills, core, overload — leaving stats/cube manual', () => {
    const { drafts } = parseExiaExport(sampleExport())
    const maiden = drafts.find((d) => d.character_slug === 'maiden-ice-rose')!
    expect(maiden.level).toBe('663')
    expect(maiden.core_level).toBe('2')
    expect(maiden.skill_levels).toEqual({ skill1: '10', skill2: '9', burst: '8' })
    expect(maiden.overload_options).toEqual([
      { id: expect.any(String), name: '우월코드 대미지 증가', value: '42.91' },
    ])
    expect(maiden.hp).toBe('')
    expect(maiden.atk).toBe('')
    expect(maiden.def_).toBe('')
    expect(maiden.hasCube).toBe(false)
    expect(maiden.pve_cube).toEqual({ name: '', level: '' })
  })

  it('applies the slug alias and keeps unencoded units by their derived slug', () => {
    const { drafts } = parseExiaExport(sampleExport())
    expect(drafts.map((d) => d.character_slug).sort()).toEqual([
      'ada-wong',
      'maiden-ice-rose',
      'naga',
    ])
  })

  it('maps a null limit_break to core_level 0', () => {
    const { drafts } = parseExiaExport(sampleExport())
    expect(drafts.find((d) => d.character_slug === 'naga')!.core_level).toBe('0')
  })

  it('reports dropped overload types as a warning', () => {
    const { warnings } = parseExiaExport(sampleExport())
    expect(warnings).toEqual([
      {
        kind: 'dropped-overload',
        nameEn: 'Maiden: Ice Rose',
        slug: 'maiden-ice-rose',
        droppedTypes: ['StatDef'],
      },
    ])
  })

  it('never surfaces cookie or game_uid anywhere in the result', () => {
    const result = parseExiaExport(sampleExport())
    const serialized = JSON.stringify(result)
    expect(serialized).not.toContain('SECRET')
    expect(serialized).not.toContain('SHOULD-NOT-BE-READ')
  })

  it('throws on input that is not an export', () => {
    expect(() => parseExiaExport(null)).toThrow(/elements/)
    expect(() => parseExiaExport({})).toThrow(/elements/)
    expect(() => parseExiaExport({ elements: 'nope' })).toThrow(/elements/)
  })

  it('skips a character with no name_en and reports it', () => {
    const bad = sampleExport()
    // @ts-expect-error deliberately malformed
    bad.elements.Electronic.push({ skill1_level: 1 })
    const { drafts, warnings } = parseExiaExport(bad)
    expect(drafts).toHaveLength(3)
    expect(warnings).toContainEqual(
      expect.objectContaining({ kind: 'skipped-character' }),
    )
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/exiaImport.test.ts`
Expected: FAIL — `parseExiaExport` not exported.

- [ ] **Step 3: Write minimal implementation**

Add to `frontend/src/lib/exiaImport.ts` (extend the `NikkeDraft` import):
```ts
import type { NikkeDraft, OverloadRow } from '../types/nikkeDraft'

interface ExiaCharacter {
  name_en?: string
  skill1_level?: number
  skill2_level?: number
  skill_burst_level?: number
  limit_break?: { grade: number | null; core: number | null } | null
  equipments?: Record<string, ExiaOverloadLine[]>
}

interface ExiaExport {
  synchroLevel?: number
  elements?: Record<string, ExiaCharacter[]>
}

export type ImportWarning =
  | { kind: 'dropped-overload'; nameEn: string; slug: string; droppedTypes: string[] }
  | { kind: 'skipped-character'; nameEn: string; reason: string }

export interface ExiaImportResult {
  drafts: NikkeDraft[]
  warnings: ImportWarning[]
}

export const parseExiaExport = (raw: unknown): ExiaImportResult => {
  const data = raw as ExiaExport | null
  if (
    !data ||
    typeof data !== 'object' ||
    typeof data.elements !== 'object' ||
    data.elements === null
  ) {
    throw new Error('Not an ExiaInvasion export: missing "elements".')
  }

  const level = String(data.synchroLevel ?? '')
  const drafts: NikkeDraft[] = []
  const warnings: ImportWarning[] = []

  for (const characters of Object.values(data.elements)) {
    if (!Array.isArray(characters)) continue
    for (const character of characters) {
      const nameEn = character?.name_en
      if (!nameEn) {
        warnings.push({
          kind: 'skipped-character',
          nameEn: String(nameEn),
          reason: 'missing name_en',
        })
        continue
      }

      const slug = resolveSlug(nameEn)
      const { rows, droppedTypes } = aggregateOverload(character.equipments ?? {})
      if (droppedTypes.length > 0) {
        warnings.push({ kind: 'dropped-overload', nameEn, slug, droppedTypes })
      }

      drafts.push({
        id: crypto.randomUUID(),
        character_slug: slug,
        level,
        core_level: String(character.limit_break?.core ?? 0),
        hp: '',
        atk: '',
        def_: '',
        skill_levels: {
          skill1: String(character.skill1_level ?? ''),
          skill2: String(character.skill2_level ?? ''),
          burst: String(character.skill_burst_level ?? ''),
        },
        overload_options: rows,
        hasCube: false,
        pve_cube: { name: '', level: '' },
      })
    }
  }

  return { drafts, warnings }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/exiaImport.test.ts`
Expected: PASS (all Task 1–3 cases).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/exiaImport.ts frontend/src/lib/exiaImport.test.ts
git commit -m "feat: parse ExiaInvasion export into NikkeDrafts"
```

---

### Task 4: 순수 병합 함수 (`mergeRosterDrafts`)

**Files:**
- Modify: `frontend/src/types/nikkeDraft.ts`
- Test: `frontend/src/types/nikkeDraft.test.ts`

**Interfaces:**
- Consumes: `NikkeDraft` (existing).
- Produces:
  - `interface RosterMergeResult { drafts: NikkeDraft[]; added: number; updated: number }`
  - `mergeRosterDrafts(current: NikkeDraft[], incoming: NikkeDraft[]): RosterMergeResult`
  - 병합 규칙: 같은 `character_slug`면 `level`·`core_level`·`skill_levels`·`overload_options`만 덮어쓰고 `id`·`hp`·`atk`·`def_`·`hasCube`·`pve_cube`는 보존. 없으면 추가. `incoming`에 없는 기존 항목은 무변경.

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/types/nikkeDraft.test.ts`:
```ts
import { makeEmptyDraft, mergeRosterDrafts } from './nikkeDraft'

const draft = (over: Partial<ReturnType<typeof makeEmptyDraft>>) => ({
  ...makeEmptyDraft(),
  ...over,
})

describe('mergeRosterDrafts', () => {
  it('overwrites import fields on a matching slug but preserves manual fields and id', () => {
    const existing = draft({
      character_slug: 'rapi-red-hood',
      atk: '60000',
      hp: '120000',
      def_: '3000',
      hasCube: true,
      pve_cube: { name: 'Bastion Cube', level: '7' },
      skill_levels: { skill1: '1', skill2: '1', burst: '1' },
      level: '200',
      core_level: '0',
    })
    const incoming = draft({
      character_slug: 'rapi-red-hood',
      atk: '',
      hp: '',
      skill_levels: { skill1: '10', skill2: '10', burst: '10' },
      level: '663',
      core_level: '5',
      overload_options: [{ id: 'x', name: '공격력 증가', value: '12' }],
    })

    const { drafts, added, updated } = mergeRosterDrafts([existing], [incoming])

    expect(added).toBe(0)
    expect(updated).toBe(1)
    expect(drafts).toHaveLength(1)
    const merged = drafts[0]
    expect(merged.id).toBe(existing.id)
    expect(merged.atk).toBe('60000')
    expect(merged.hp).toBe('120000')
    expect(merged.def_).toBe('3000')
    expect(merged.hasCube).toBe(true)
    expect(merged.pve_cube).toEqual({ name: 'Bastion Cube', level: '7' })
    expect(merged.level).toBe('663')
    expect(merged.core_level).toBe('5')
    expect(merged.skill_levels).toEqual({ skill1: '10', skill2: '10', burst: '10' })
    expect(merged.overload_options).toEqual([
      { id: 'x', name: '공격력 증가', value: '12' },
    ])
  })

  it('adds a new slug', () => {
    const existing = draft({ character_slug: 'liter' })
    const incoming = draft({ character_slug: 'crown' })
    const { drafts, added, updated } = mergeRosterDrafts([existing], [incoming])
    expect(added).toBe(1)
    expect(updated).toBe(0)
    expect(drafts.map((d) => d.character_slug)).toEqual(['liter', 'crown'])
  })

  it('leaves an existing draft untouched when the import does not include it', () => {
    const kept = draft({ character_slug: 'liter', atk: '999' })
    const incoming = draft({ character_slug: 'crown' })
    const { drafts } = mergeRosterDrafts([kept], [incoming])
    expect(drafts.find((d) => d.character_slug === 'liter')).toEqual(kept)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/types/nikkeDraft.test.ts`
Expected: FAIL — `mergeRosterDrafts` not exported.

- [ ] **Step 3: Write minimal implementation**

Append to `frontend/src/types/nikkeDraft.ts`:
```ts
export interface RosterMergeResult {
  drafts: NikkeDraft[]
  added: number
  updated: number
}

/**
 * Merge imported drafts into the current roster by character_slug. For a slug
 * already present, overwrite only the import-sourced fields (level, core_level,
 * skill_levels, overload_options) and keep the manual ones (id, hp, atk, def_,
 * hasCube, pve_cube). New slugs are appended; current drafts absent from the
 * import are left untouched.
 */
export const mergeRosterDrafts = (
  current: NikkeDraft[],
  incoming: NikkeDraft[],
): RosterMergeResult => {
  const next = current.map((d) => ({ ...d }))
  const indexBySlug = new Map(next.map((d, i) => [d.character_slug, i]))
  let added = 0
  let updated = 0

  for (const inc of incoming) {
    const idx = indexBySlug.get(inc.character_slug)
    if (idx === undefined) {
      next.push(inc)
      indexBySlug.set(inc.character_slug, next.length - 1)
      added += 1
    } else {
      next[idx] = {
        ...next[idx],
        level: inc.level,
        core_level: inc.core_level,
        skill_levels: inc.skill_levels,
        overload_options: inc.overload_options,
      }
      updated += 1
    }
  }

  return { drafts: next, added, updated }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/types/nikkeDraft.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/nikkeDraft.ts frontend/src/types/nikkeDraft.test.ts
git commit -m "feat: slug-by-slug roster merge preserving manual fields"
```

---

### Task 5: `useRoster.importDrafts` setter

**Files:**
- Modify: `frontend/src/hooks/useRoster.ts`
- Test: `frontend/src/hooks/useRoster.test.ts`

**Interfaces:**
- Consumes: `mergeRosterDrafts` (Task 4).
- Produces: `Roster.importDrafts(incoming: NikkeDraft[]): { added: number; updated: number }` — 병합 결과를 상태에 반영하고 요약 카운트를 반환. localStorage 미러링은 기존 `useEffect`가 처리.

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/hooks/useRoster.test.ts` (inside the existing `describe('useRoster', ...)` block; `act`/`renderHook` are already imported):
```ts
  it('imports drafts, preserving manual fields on a matching slug and persisting', () => {
    const first = renderHook(() => useRoster())
    act(() => first.result.current.addNikke())
    act(() =>
      first.result.current.updateNikke(first.result.current.drafts[0].id, {
        ...first.result.current.drafts[0],
        character_slug: 'rapi-red-hood',
        atk: '60000',
        skill_levels: { skill1: '1', skill2: '1', burst: '1' },
      }),
    )

    let summary = { added: -1, updated: -1 }
    act(() => {
      summary = first.result.current.importDrafts([
        {
          ...first.result.current.drafts[0],
          id: 'ignored-incoming-id',
          atk: '',
          skill_levels: { skill1: '10', skill2: '10', burst: '10' },
        },
        {
          ...first.result.current.drafts[0],
          id: 'new-one',
          character_slug: 'crown',
        },
      ])
    })

    expect(summary).toEqual({ added: 1, updated: 1 })
    const rapi = first.result.current.drafts.find(
      (d) => d.character_slug === 'rapi-red-hood',
    )!
    expect(rapi.atk).toBe('60000') // manual field preserved
    expect(rapi.skill_levels.skill1).toBe('10') // import field overwritten
    first.unmount()

    // persisted across a reload
    const second = renderHook(() => useRoster())
    expect(
      second.result.current.drafts.map((d) => d.character_slug).sort(),
    ).toEqual(['crown', 'rapi-red-hood'])
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/hooks/useRoster.test.ts`
Expected: FAIL — `importDrafts` is not a function.

- [ ] **Step 3: Write minimal implementation**

Modify `frontend/src/hooks/useRoster.ts`:

1. Update the imports line:
```ts
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  makeEmptyDraft,
  mergeRosterDrafts,
  type NikkeDraft,
} from '../types/nikkeDraft'
```

2. Add `importDrafts` to the `Roster` interface:
```ts
export interface Roster {
  drafts: NikkeDraft[]
  addNikke: () => void
  updateNikke: (id: string, next: NikkeDraft) => void
  removeNikke: (id: string) => void
  importDrafts: (incoming: NikkeDraft[]) => { added: number; updated: number }
}
```

3. Inside `useRoster`, after the existing persistence `useEffect`, add a ref mirror and the setter, then include `importDrafts` in the returned object:
```ts
  const draftsRef = useRef(drafts)
  useEffect(() => {
    draftsRef.current = drafts
  }, [drafts])

  const importDrafts = useCallback((incoming: NikkeDraft[]) => {
    const result = mergeRosterDrafts(draftsRef.current, incoming)
    setDrafts(result.drafts)
    return { added: result.added, updated: result.updated }
  }, [])
```
```ts
  return { drafts, addNikke, updateNikke, removeNikke, importDrafts }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/hooks/useRoster.test.ts`
Expected: PASS (new case + the three existing cases).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useRoster.ts frontend/src/hooks/useRoster.test.ts
git commit -m "feat: useRoster.importDrafts merge setter"
```

---

### Task 6: 임포트 UI (`ImportRosterButton`) + App 배선

**Files:**
- Create: `frontend/src/components/ImportRosterButton.tsx`
- Test: `frontend/src/components/ImportRosterButton.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `parseExiaExport`, `ImportWarning` (Task 3); `Roster.importDrafts` (Task 5).
- Produces: `<ImportRosterButton onImport={(drafts) => { added; updated }} />` — 파일 선택 시 JSON 파싱→파싱 실패는 사용자 에러, 성공 시 `onImport` 호출 후 요약 문구 표시.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/ImportRosterButton.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ImportRosterButton } from './ImportRosterButton'

const exportJson = () =>
  JSON.stringify({
    synchroLevel: 663,
    elements: {
      Electronic: [
        {
          name_en: 'Ada',
          skill1_level: 10,
          skill2_level: 10,
          skill_burst_level: 10,
          limit_break: { grade: 0, core: 0 },
          equipments: { '0': [], '1': [], '2': [], '3': [] },
        },
      ],
    },
  })

const file = (contents: string) =>
  new File([contents], 'FIENN.json', { type: 'application/json' })

describe('ImportRosterButton', () => {
  it('parses the chosen file, calls onImport, and shows a summary', async () => {
    const onImport = vi.fn(() => ({ added: 1, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)

    await userEvent.upload(
      screen.getByLabelText(/import from exiainvasion/i),
      file(exportJson()),
    )

    await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1))
    expect(onImport.mock.calls[0][0][0].character_slug).toBe('ada-wong')
    expect(await screen.findByText(/1 added/i)).toBeInTheDocument()
  })

  it('shows an error and does not call onImport when the file is not JSON', async () => {
    const onImport = vi.fn(() => ({ added: 0, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)

    await userEvent.upload(
      screen.getByLabelText(/import from exiainvasion/i),
      file('{ not json'),
    )

    expect(await screen.findByText(/could not read/i)).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('shows an error when the JSON is not an export', async () => {
    const onImport = vi.fn(() => ({ added: 0, updated: 0 }))
    render(<ImportRosterButton onImport={onImport} />)

    await userEvent.upload(
      screen.getByLabelText(/import from exiainvasion/i),
      file('{"foo": 1}'),
    )

    expect(await screen.findByText(/elements/i)).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/components/ImportRosterButton.test.tsx`
Expected: FAIL — component module not found.

Note: `@testing-library/user-event`, `@testing-library/react`, and jest-dom matchers (`toBeInTheDocument`, via `src/test/setup.ts`) are already configured — same setup `NikkeCard.test.tsx` uses. No install needed.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/ImportRosterButton.tsx`:
```tsx
// Imports an ExiaInvasion export file into the roster: read file -> parse ->
// merge (via onImport) -> show a summary. Parse/format failures surface as a
// user-facing error rather than crashing. ATK/HP/DEF and cube stay manual.

import { useState } from 'react'
import {
  parseExiaExport,
  type ImportWarning,
} from '../lib/exiaImport'
import type { NikkeDraft } from '../types/nikkeDraft'

interface ImportRosterButtonProps {
  onImport: (drafts: NikkeDraft[]) => { added: number; updated: number }
}

const summarise = (
  added: number,
  updated: number,
  warnings: ImportWarning[],
): string => {
  const parts = [`${added} added`, `${updated} updated`]
  const dropped = warnings.filter((w) => w.kind === 'dropped-overload').length
  if (dropped > 0) parts.push(`${dropped} had unsupported overload lines dropped`)
  const skipped = warnings.filter((w) => w.kind === 'skipped-character').length
  if (skipped > 0) parts.push(`${skipped} skipped`)
  return parts.join(', ')
}

export function ImportRosterButton({ onImport }: ImportRosterButtonProps) {
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0]
    event.target.value = '' // allow re-importing the same file
    if (!file) return

    setError(null)
    setMessage(null)

    let raw: unknown
    try {
      raw = JSON.parse(await file.text())
    } catch {
      setError('Could not read the file as JSON.')
      return
    }

    try {
      const { drafts, warnings } = parseExiaExport(raw)
      const { added, updated } = onImport(drafts)
      setMessage(summarise(added, updated, warnings))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed.')
    }
  }

  return (
    <div className="import">
      <label className="btn btn--ghost">
        Import from ExiaInvasion
        <input
          type="file"
          accept="application/json,.json"
          className="import__input"
          aria-label="Import from ExiaInvasion"
          onChange={handleChange}
        />
      </label>
      {message && <p className="import__message">{message}</p>}
      {error && (
        <p className="import__error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/components/ImportRosterButton.test.tsx`
Expected: PASS.

- [ ] **Step 5: Wire into App and verify the whole suite + build**

Modify `frontend/src/App.tsx`:

1. Add the import:
```ts
import { ImportRosterButton } from './components/ImportRosterButton'
```

2. Pull `importDrafts` from the hook:
```ts
  const { drafts, addNikke, updateNikke, removeNikke, importDrafts } =
    useRoster()
```

3. Render the button at the top of `<main>`, before the empty/roster branch:
```tsx
      <main className="app__main">
        <ImportRosterButton onImport={importDrafts} />

        {drafts.length === 0 ? (
```
(leave the rest of `<main>` unchanged)

Run the full suite and the type-checked build (from `frontend/`):
`npm test`
Expected: PASS (all files).
`npm run build`
Expected: `tsc -b` clean + vite build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ImportRosterButton.tsx frontend/src/components/ImportRosterButton.test.tsx frontend/src/App.tsx
git commit -m "feat: ExiaInvasion roster import UI wired into the app"
```

---

## Post-implementation

- [ ] `docs/roadmap.md` Phase 7 섹션에 Phase A 완료를 반영(To-Do 체크).
- [ ] 실제 `data/FIENN.json`로 수동 E2E: 앱 실행 → 파일 임포트 → 로스터에 유닛이 채워지고 ATK 공란인지, 재임포트가 손입력 ATK를 보존하는지 확인. (실제 파일은 커밋하지 않음.)

---

## Notes / spec 대비 정제

- **미매칭 슬러그 경고 (spec §6/§11):** 파서는 어떤 슬러그가 인코딩됐는지 모른다(레지스트리는 백엔드 지식). 따라서 "미매칭 슬러그"를 파스 시점에 경고하지 않고, 기존 `excluded_slugs` 흐름(추천 호출 후 `ExcludedSlugsNote`)이 미로더블 유닛을 보고한다. 파서 warnings는 **드롭된 오버로드·스킵된 캐릭터**만 담는다. 프론트에 전체 인코딩 슬러그 목록을 번들하는 건 유지비가 커 YAGNI로 배제.
- **픽스처 (spec §12/§13):** 정제·축소한 실제 파일 대신 **인라인 합성 픽스처**를 쓴다 — 자격증명이 원천적으로 없고 테스트 가독성이 높다. 구조는 spec §3의 실측 스키마를 모사한다.
- **`level`/`core_level`은 inert**(딜 미반영). 값 자체보다 임포트 흐름이 검증 대상.
