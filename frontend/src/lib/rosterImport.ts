// Parses the blablalink collector's roster.json into editable NikkeDrafts.
// raid400 (level 400, solo-raid baseline) stats go into hp/atk/def; actual
// (real-level) stats go into the actual* fields for future union-raid use.
// Slug comes from the resource_id identity map, promoted to the "-signature"
// encoding when the unit's own `favorite_item` flag says the Favorite Item is
// owned; unencoded owned units are kept with a raw-derived slug
// (the backend excludes them from recommendation but they stay visible in the roster).
// A unit with no resource_id at all (stale or hand-edited roster.json — the collector
// always emits one) takes that same path: raw slug, reported as unsupported.

import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'
import { deriveSlug } from './exiaImport'
import { resolveSlugForUnit } from './resourceIdSlugMap'

interface RosterUnit {
  resource_id?: number
  name_en: string
  grade?: number
  core?: number
  // Whether this unit's collectible slot holds a Favorite Item. Absent on a
  // collector scrape and on rosters predating the field; see resolveSlugForUnit
  // for what answers in that case.
  favorite_item?: boolean
  raid400: { hp: number; atk: number; def: number }
  actual?: { hp: number; atk: number; def: number }
  overload?: { name: string; value: number }[]
  skill_levels?: { skill1: number; skill2: number; burst: number }
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
    const mapped = resolveSlugForUnit(u.resource_id, u.favorite_item)
    if (mapped === undefined) unsupported.push(u.name_en)
    drafts.push({
      ...makeEmptyDraft(),
      character_slug: mapped ?? deriveSlug(u.name_en),
      grade: u.grade,
      core: u.core,
      level: '400',
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
