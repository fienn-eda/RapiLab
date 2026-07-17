// Parses the blablalink collector's roster.json into editable NikkeDrafts.
// raid400 (level 400, solo-raid baseline) stats go into hp/atk/def; actual
// (real-level) stats go into the actual* fields for future union-raid use.

import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'
import { resolveSlug } from './exiaImport'

interface RosterUnit {
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
  for (const u of data.units) {
    if (!u || !u.name_en || !u.raid400) {
      warnings.push('unit missing name_en/raid400')
      continue
    }
    drafts.push({
      ...makeEmptyDraft(),
      character_slug: resolveSlug(u.name_en),
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
  return { drafts, warnings }
}
