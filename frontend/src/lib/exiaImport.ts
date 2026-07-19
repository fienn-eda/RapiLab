// Parses an ExiaInvasion export (blablalink roster JSON) into editable NikkeDrafts.
// Only the fields the export carries are mapped; ATK/HP/DEF and cube stay manual.
// The cookie/game_uid fields in the export are credentials and are never read.

import type { NikkeDraft, OverloadRow } from '../types/nikkeDraft'

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
        actualHp: '',
        actualAtk: '',
        actualDef: '',
        skill_levels: {
          skill1: String(character.skill1_level ?? ''),
          skill2: String(character.skill2_level ?? ''),
          burst: String(character.skill_burst_level ?? ''),
        },
        overload_options: rows,
        hasCube: false,
        pve_cube: { name: '', level: '' },
        cubeKnown: false, // the ExiaInvasion export doesn't carry cube data
      })
    }
  }

  return { drafts, warnings }
}
