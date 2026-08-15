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
import type { OverloadLine } from '../types/userNikkeState'
import { deriveSlug } from './exiaImport'
import { resolveSlugForUnit } from './resourceIdSlugMap'
import { HELP } from './helpText'

interface RosterUnit {
  resource_id?: number
  name_en: string
  grade?: number
  core?: number
  // Whether this unit's collectible slot holds a Favorite Item. Absent on a
  // collector scrape and on rosters predating the field; see resolveSlugForUnit
  // for what answers in that case.
  favorite_item?: boolean
  // The equipped collectible (소장품). Its weapon-group skill is a damage
  // source the backend reads per unit; absent on rosters predating the field.
  collectible?: { tid: number; level: number }
  raid400: { hp: number; atk: number; def: number }
  actual?: { hp: number; atk: number; def: number }
  // The roll shape is the shared one rather than a restatement of it: the sync
  // carries an option row and a roll level per line, and a local copy that
  // listed only slot and value would read as though it did not.
  overload?: { name: string; value: number; lines?: OverloadLine[] }[]
  skill_levels?: { skill1: number; skill2: number; burst: number }
}
interface RosterJson {
  synchroLevel?: number
  units?: RosterUnit[]
  /** Units the backend had to drop because no honest level-400 stat exists for
   * them (a cored PILGRIM Supporter's per-core flat was never measured). Absent
   * from a collector scrape, which never assembled stats in the first place. */
  unmeasured?: { name_en: string; reason: string }[]
}

export const parseRosterJson = (
  raw: unknown,
): { drafts: NikkeDraft[]; warnings: string[] } => {
  const data = raw as RosterJson
  if (!data || typeof data !== 'object' || !Array.isArray(data.units)) {
    throw new Error('수집기 로스터 형식이 아니에요: "units" 필드가 없어요.')
  }
  const drafts: NikkeDraft[] = []
  const warnings: string[] = []
  const unsupported: string[] = []
  for (const u of data.units) {
    if (!u || !u.name_en || !u.raid400) {
      warnings.push(HELP.roster.importMalformedUnit)
      continue
    }
    const mapped = resolveSlugForUnit(u.resource_id, u.favorite_item)
    if (mapped === undefined) unsupported.push(u.name_en)
    drafts.push({
      ...makeEmptyDraft(),
      character_slug: mapped ?? deriveSlug(u.name_en),
      grade: u.grade,
      core: u.core,
      favorite_item: u.favorite_item,
      collectible_tid: u.collectible?.tid,
      collectible_level: u.collectible?.level,
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
        ...(o.lines?.length ? { lines: o.lines } : {}),
      })),
    })
  }
  if (unsupported.length > 0) {
    warnings.push(HELP.roster.importUnsupported(unsupported.length, unsupported.join(', ')))
  }
  // A dropped unit is worth a louder line than an unsupported one: it IS
  // encoded and would be fielded, and the only reason it is missing is a hole in
  // the measured data that a different account happens to expose.
  if (data.unmeasured && data.unmeasured.length > 0) {
    warnings.push(
      HELP.roster.importUnmeasured(
        data.unmeasured.length,
        data.unmeasured.map((u) => `${u.name_en} (${u.reason})`).join('; '),
      ),
    )
  }
  return { drafts, warnings }
}
