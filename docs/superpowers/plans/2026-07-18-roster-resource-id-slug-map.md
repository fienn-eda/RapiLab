# resource_id 권위 맵 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** blablalink 수집기 `roster.json`을 `resource_id → 인코딩 slug` 권위 맵으로 해석해, 이름 alias 오매핑(Soline/Marciana/Rei 중복)을 없애고 로스터가 추천기까지 정확히 흘러가게 한다.

**Architecture:** roster.json 임포트 경로를 이름 파생(`resolveSlug`/`SLUG_ALIASES`)에서 분리한다. 신규 프론트 모듈 `resourceIdSlugMap.ts`가 인코딩된 유닛의 `resource_id → slug`를 하드코딩한 유일한 진실의 소스가 되고, `rosterImport.ts`가 그것으로 slug를 정한다. 맵 미스(미인코딩 owned 유닛)는 alias 없는 raw `deriveSlug`로 draft를 **유지**하며(백엔드가 추천에서 자연 제외), 애정 캐릭 등 보유 가시성을 지킨다. 백엔드 drift 테스트가 맵을 `ENCODED_SLUGS`와 대조해 오타·누락을 잡는다. ExiaInvasion 경로·백엔드 엔진·수집기는 무변경.

**Tech Stack:** React + Vite + TypeScript (frontend, vitest), Python + pytest (backend drift test).

## Global Constraints

- 범위: `frontend/src/lib` + 백엔드 drift 테스트 1개. ExiaInvasion 경로(`exiaImport.ts`)·엔진·수집기 무변경.
- `deriveSlug`는 `exiaImport.ts`에 그대로 두고 rosterImport가 그것만 import(이동/복제 금지 — DRY).
- 맵 slug 값은 백엔드 `ENCODED_SLUGS`의 부분집합이어야 한다(drift 테스트가 강제).
- 투자 의존 엔트리(Drake 101→signature, Julia 150→base)는 Fienn 현재 로스터 기준으로 고정하고 근거를 주석에 남긴다.
- 미인코딩 유닛은 draft에서 제외하지 않는다(성능 영향 0, 보유 가시성 보존).
- 기존 프론트 스위트(97)·`tsc -b` 그린 유지. 새 백엔드 테스트 green.

---

### Task 1: resource_id → slug 권위 맵 모듈

**Files:**
- Create: `frontend/src/lib/resourceIdSlugMap.ts`
- Test: `frontend/src/lib/resourceIdSlugMap.test.ts`

**Interfaces:**
- Consumes: (없음)
- Produces: `export const RESOURCE_ID_TO_SLUG: Record<number, string>` — 조회는 `RESOURCE_ID_TO_SLUG[resource_id]`로, 미인코딩/미보유 id는 `undefined`.

- [ ] **Step 1: 실패 테스트 작성**

`frontend/src/lib/resourceIdSlugMap.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { RESOURCE_ID_TO_SLUG } from './resourceIdSlugMap'

describe('RESOURCE_ID_TO_SLUG', () => {
  it('maps unambiguous units by resource_id', () => {
    expect(RESOURCE_ID_TO_SLUG[16]).toBe('rapi-red-hood')
    expect(RESOURCE_ID_TO_SLUG[74]).toBe('soline-frost-ticket')
    expect(RESOURCE_ID_TO_SLUG[322]).toBe('marciana-marine-study')
  })

  it('disambiguates the three "Rei" units by resource_id', () => {
    expect(RESOURCE_ID_TO_SLUG[831]).toBe('rei-ayanami') // 레이
    expect(RESOURCE_ID_TO_SLUG[834]).toBe('rei-ayanami-tentative-name')
    expect(RESOURCE_ID_TO_SLUG[392]).toBeUndefined() // 라이 — 별개 캐릭터, 미인코딩
  })

  it('excludes base units whose only encoded form is a variant', () => {
    expect(RESOURCE_ID_TO_SLUG[71]).toBeUndefined() // base Soline
    expect(RESOURCE_ID_TO_SLUG[321]).toBeUndefined() // base Marciana
  })

  it('resolves investment-fixed base/signature pairs', () => {
    expect(RESOURCE_ID_TO_SLUG[101]).toBe('drake-signature') // 애장품 보유
    expect(RESOURCE_ID_TO_SLUG[150]).toBe('julia') // 미육성
  })
})
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/lib/resourceIdSlugMap.test.ts`
Expected: FAIL — "Cannot find module './resourceIdSlugMap'"

- [ ] **Step 3: 맵 모듈 작성**

`frontend/src/lib/resourceIdSlugMap.ts` (엔트리는 Fienn roster.json의 owned 유닛 × 백엔드 `ENCODED_SLUGS` 교차로 저술; resource_id는 blablalink canonical ID):

```typescript
// blablalink resource_id -> our encoded character_slug. Authoritative source for
// the collector (roster.json) import path — decoupled from name-derived aliasing so
// base/variant and same-name collisions resolve unambiguously. Values are a subset of
// the backend's ENCODED_SLUGS (enforced by backend test_resource_id_slug_map.py).
// Ids absent here are units we have not encoded (or not owned) -> excluded from
// recommendation, kept visible in the roster draft via raw deriveSlug.
//
// Investment-fixed entries (same resource_id, two encoded slugs — depends on whether
// the Favorite Item is owned; the collector does not capture that yet):
//   101 Drake -> drake-signature (Favorite Item owned, Fienn 2026-07-18)
//   150 Julia -> julia           (uninvested, no Favorite Item)
// The durable fix is SSR-favorite auto-detection (deferred; see the design spec).
export const RESOURCE_ID_TO_SLUG: Record<number, string> = {
  15: 'anis-sparkling-summer', // Anis: Sparkling Summer
  16: 'rapi-red-hood', // Rapi: Red Hood
  17: 'anis-star', // Anis: Star
  18: 'neon-vision-eye', // Neon: Vision Eye
  32: 'miranda', // Miranda
  43: 'd-killer-wife', // D: Killer Wife
  73: 'brid-silent-track', // Brid: Silent Track
  74: 'soline-frost-ticket', // Soline: Frost Ticket
  82: 'liter', // Liter
  100: 'laplace', // Laplace
  101: 'drake-signature', // Drake — Favorite Item owned (investment-fixed)
  150: 'julia', // Julia — uninvested (investment-fixed)
  170: 'privaty', // Privaty
  182: 'guillotine-winter-slayer', // Guillotine: Winter Slayer
  183: 'maiden-ice-rose', // Maiden: Ice Rose
  192: 'tove', // Tove
  194: 'ludmilla-winter-owner', // Ludmilla: Winter Owner
  223: 'nayuta', // Nayuta
  231: 'isabel', // Isabel
  234: 'dorothy-serendipity', // Dorothy: Serendipity
  260: 'modernia', // Modernia
  262: 'liberalio', // Liberalio
  270: 'blanc', // Blanc
  271: 'noir', // Noir
  272: 'rouge', // Rouge
  281: 'moran', // Moran
  283: 'rosanna-chic-ocean', // Rosanna: Chic Ocean
  284: 'sakura-bloom-in-summer', // Sakura: Bloom in Summer
  290: 'mana', // Mana
  314: 'soda-twinkling-bunny', // Soda: Twinkling Bunny
  315: 'ade-agent-bunny', // Ade: Agent Bunny
  316: 'velvet', // Velvet
  322: 'marciana-marine-study', // Marciana: Marine Study
  330: 'crown', // Crown
  352: 'helm', // Helm
  353: 'helm-aquamarine', // Helm: Aquamarine
  354: 'mast-romantic-maid', // Mast: Romantic Maid
  355: 'anchor-innocent-maid', // Anchor: Innocent Maid
  390: 'zwei', // Zwei
  391: 'ein', // Ein
  403: 'quency-escape-queen', // Quency: Escape Queen
  431: 'volume', // Volume
  511: 'cinderella', // Cinderella
  513: 'little-mermaid', // Little Mermaid
  514: 'grave', // Grave
  570: 'ark-ranger-black', // Ark Ranger Black
  581: 'arcana', // Arcana
  583: 'arcana-fortune-mate', // Arcana: Fortune Mate
  600: 'mint', // Mint
  601: 'prika', // Prika
  831: 'rei-ayanami', // Rei (레이)
  834: 'rei-ayanami-tentative-name', // Rei (Tentative Name)
  835: 'asuka-shikinami-langley-wille', // Asuka: WILLE
  840: 'ada-wong', // Ada
  851: 'raven', // Raven
  860: 'chisato-nishikigi', // Chisato
  861: 'takina-inoue', // Takina
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/lib/resourceIdSlugMap.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/resourceIdSlugMap.ts frontend/src/lib/resourceIdSlugMap.test.ts
git commit -m "feat: resource_id -> slug authoritative map for collector import"
```

---

### Task 2: 백엔드 drift 테스트 (맵 ⊆ ENCODED_SLUGS, 누락 감지)

**Files:**
- Create: `backend/tests/test_resource_id_slug_map.py`

**Interfaces:**
- Consumes: `frontend/src/lib/resourceIdSlugMap.ts` (정규식으로 파싱), `app.skill_rules.registry.ENCODED_SLUGS`
- Produces: (테스트 전용, 산출 인터페이스 없음)

**참고 — 왜 백엔드에 두는가:** `ENCODED_SLUGS`가 백엔드에 살아 있어 단일 소스로 대조 가능하고, 새 유닛을 인코딩(백엔드 작업)하면 즉시 "맵 엔트리 누락"이 이 테스트에서 잡힌다(재생성 규율 불필요). 맵 파일은 `  <id>: '<slug>',` 평면 포맷이라 정규식 파싱이 안전하다.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_resource_id_slug_map.py`:

```python
"""Drift guard for the frontend resource_id -> slug authoritative map.

Keeps the hand-authored map honest against the live ENCODED_SLUGS: every mapped
slug must be encoded (no typos / stale removals), and every encoded slug must have
a resource_id EXCEPT the known-unmapped set (investment-shadowed or not-owned).
"""
import re
from pathlib import Path

from app.skill_rules.registry import ENCODED_SLUGS

MAP_FILE = (
    Path(__file__).resolve().parents[2]
    / "frontend" / "src" / "lib" / "resourceIdSlugMap.ts"
)

# Encoded slugs deliberately absent from the map:
#   drake / julia-signature -> the same physical unit is assigned to the OTHER slug
#     of an investment-shadowed base/signature pair (101->drake-signature, 150->julia),
#     so only one of each pair carries the resource_id.
#   jill-valentine -> not in the roster the map was authored from (owner's resource_id
#     unknown locally); add its id when a Jill owner syncs. Recommendation-irrelevant
#     until then.
KNOWN_UNMAPPED = {"drake", "julia-signature", "jill-valentine"}


def _mapped_slugs() -> set[str]:
    text = MAP_FILE.read_text(encoding="utf-8")
    body = text.split("Record<number, string> = {", 1)[1]
    return set(re.findall(r"\d+:\s*'([a-z0-9-]+)'", body))


def test_every_mapped_slug_is_encoded():
    encoded = set(ENCODED_SLUGS)
    stray = _mapped_slugs() - encoded
    assert stray == set(), f"map slugs not in ENCODED_SLUGS (typo/stale): {stray}"


def test_every_encoded_slug_is_mapped_except_known():
    uncovered = set(ENCODED_SLUGS) - _mapped_slugs()
    assert uncovered == KNOWN_UNMAPPED, (
        "encoded slugs missing a resource_id entry changed; add the entry or update "
        f"KNOWN_UNMAPPED. diff={uncovered ^ KNOWN_UNMAPPED}"
    )
```

- [ ] **Step 2: 테스트 통과 확인** (맵은 Task 1에서 이미 존재)

Run: `cd backend && python -m pytest tests/test_resource_id_slug_map.py -v`
Expected: PASS (2 tests). 실패 시 diff를 보고 맵 엔트리 또는 `KNOWN_UNMAPPED`를 교정.

- [ ] **Step 3: 커밋**

```bash
git add backend/tests/test_resource_id_slug_map.py
git commit -m "test: drift guard for resource_id slug map vs ENCODED_SLUGS"
```

---

### Task 3: rosterImport를 맵 기반으로 배선 (미인코딩 유닛 유지 + 집계 경고)

**Files:**
- Modify: `frontend/src/lib/rosterImport.ts`
- Test: `frontend/src/lib/rosterImport.test.ts` (케이스 추가)

**Interfaces:**
- Consumes: `RESOURCE_ID_TO_SLUG` (Task 1), `deriveSlug` (기존 `exiaImport.ts` export)
- Produces: `parseRosterJson(raw)` — 반환 형태 불변 `{ drafts: NikkeDraft[]; warnings: string[] }`. 맵 히트→권위 slug, 미스→raw 파생 slug(draft 유지) + `warnings`에 미지원 유닛 집계 1건.

- [ ] **Step 1: 실패 테스트 추가**

`frontend/src/lib/rosterImport.test.ts`에 케이스 추가(기존 3개는 유지 — Rapi 16→map hit, Neon: Blue Ocean은 resource_id 없음→deriveSlug로 여전히 'neon-blue-ocean'):

```typescript
  it('resolves encoded units by resource_id, not name', () => {
    const { drafts } = parseRosterJson({
      units: [
        { resource_id: 831, name_en: 'Rei', raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 101, name_en: 'Drake', raid400: { hp: 1, atk: 1, def: 1 } },
      ],
    })
    expect(drafts.map((d) => d.character_slug)).toEqual([
      'rei-ayanami',
      'drake-signature',
    ])
  })

  it('keeps unencoded owned units (raw slug) and warns in aggregate', () => {
    const { drafts, warnings } = parseRosterJson({
      units: [
        { resource_id: 71, name_en: 'Soline', raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 392, name_en: 'Rei', raid400: { hp: 1, atk: 1, def: 1 } },
      ],
    })
    // kept as drafts with raw-derived slugs (backend excludes them from search)
    expect(drafts.map((d) => d.character_slug)).toEqual(['soline', 'rei'])
    // one aggregate warning naming them
    expect(warnings).toHaveLength(1)
    expect(warnings[0]).toContain('Soline')
    expect(warnings[0]).toContain('Rei')
  })
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/lib/rosterImport.test.ts`
Expected: FAIL — 새 두 케이스가 실패(현재 코드는 `resolveSlug`로 71→'soline-frost-ticket' 오매핑, 집계 경고 없음)

- [ ] **Step 3: rosterImport 구현 변경**

`frontend/src/lib/rosterImport.ts`를 다음으로 교체:

```typescript
// Parses the blablalink collector's roster.json into editable NikkeDrafts.
// raid400 (level 400, solo-raid baseline) stats go into hp/atk/def; actual
// (real-level) stats go into the actual* fields for future union-raid use.
// Slug is resolved by resource_id (authoritative map); unencoded owned units are
// kept with a raw-derived slug (the backend excludes them from recommendation).

import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'
import { deriveSlug } from './exiaImport'
import { RESOURCE_ID_TO_SLUG } from './resourceIdSlugMap'

interface RosterUnit {
  resource_id?: number
  name_en: string
  raid400: { hp: number; atk: number; def: number }
  actual?: { hp: number; atk: number; def: number }
  overload?: { name: string; value: number }[]
  skill_levels?: { skill1: number; skill2: number; burst: number }
  pve_cube?: { name: string; level: number } | null
}
interface RosterJson {
  synchroLevel?: number
  units?: RosterUnit[]
}

export const parseRosterJson = (
  raw: unknown,
): { drafts: NikkeDraft[]; warnings: string[] } => {
  const data = raw as RosterJson
  if (!data || typeof data !== 'object' || !Array.isArray(data.units)) {
    throw new Error('Not a collector roster: missing "units".')
  }
  const drafts: NikkeDraft[] = []
  const warnings: string[] = []
  const unsupported: string[] = []
  for (const u of data.units) {
    if (!u || !u.name_en || !u.raid400) {
      warnings.push('unit missing name_en/raid400')
      continue
    }
    const mapped =
      u.resource_id !== undefined ? RESOURCE_ID_TO_SLUG[u.resource_id] : undefined
    const slug = mapped ?? deriveSlug(u.name_en)
    if (mapped === undefined) unsupported.push(u.name_en)
    drafts.push({
      ...makeEmptyDraft(),
      character_slug: slug,
      level: '400',
      core_level: '0',
      hp: String(u.raid400.hp),
      atk: String(u.raid400.atk),
      def_: String(u.raid400.def),
      actualHp: u.actual ? String(u.actual.hp) : '',
      actualAtk: u.actual ? String(u.actual.atk) : '',
      actualDef: u.actual ? String(u.actual.def) : '',
      skill_levels: {
        skill1: String(u.skill_levels?.skill1 ?? ''),
        skill2: String(u.skill_levels?.skill2 ?? ''),
        burst: String(u.skill_levels?.burst ?? ''),
      },
      overload_options: (u.overload ?? []).map((o) => ({
        id: crypto.randomUUID(),
        name: o.name,
        value: String(o.value),
      })),
      hasCube: !!u.pve_cube,
      pve_cube: u.pve_cube
        ? { name: u.pve_cube.name, level: String(u.pve_cube.level) }
        : { name: '', level: '' },
    })
  }
  if (unsupported.length > 0) {
    warnings.push(
      `${unsupported.length} owned units not yet supported (excluded from ` +
        `recommendation): ${unsupported.join(', ')}`,
    )
  }
  return { drafts, warnings }
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/lib/rosterImport.test.ts`
Expected: PASS (기존 3 + 신규 2 = 5 tests). 기존 "handles an uninvested unit"의 Neon: Blue Ocean은 resource_id가 없어 deriveSlug로 'neon-blue-ocean' 유지 → 통과.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/rosterImport.ts frontend/src/lib/rosterImport.test.ts
git commit -m "feat: resolve collector roster by resource_id; keep unencoded units visible"
```

---

### Task 4: 전체 스위트 검증 (프론트 + 타입 + 백엔드)

**Files:** (없음 — 검증 전용)

- [ ] **Step 1: 프론트 전체 테스트**

Run: `cd frontend && npm test`
Expected: PASS — 기존 97 + 신규(맵 4 + rosterImport 2) 모두 green.

- [ ] **Step 2: 타입 체크**

Run: `cd frontend && npx tsc -b`
Expected: 에러 없음(클린). `resource_id?` 옵셔널·`RESOURCE_ID_TO_SLUG` 인덱싱 타입 정상.

- [ ] **Step 3: 백엔드 drift 테스트 재확인**

Run: `cd backend && python -m pytest tests/test_resource_id_slug_map.py -v`
Expected: PASS (2 tests).

- [ ] **Step 4: 정합 커밋 (변경 없으면 생략)**

```bash
git add -A
git commit -m "chore: verify resource_id map wiring — full suite green" || echo "nothing to commit"
```

---

## 남은 후속(이 계획 밖 — 스펙의 Deferred 참고)
- **SSR-애장품 자동판정**: drake/julia 투자 의존을 실제 신호로 대체(수집기 Collection 탭 캡처 + `favorite_rare` 판독). 라이브 검증 필요.
- **jill-valentine resource_id**: Jill 보유 유저가 sync하거나 디렉토리 재정찰 시 맵에 추가(그때 `KNOWN_UNMAPPED`에서 제거).
- **must-include(핀) 추천** + **OOB(edenpj식) 몇-클릭 sync**: 별도 Phase 7 작업(로드맵 참고).
