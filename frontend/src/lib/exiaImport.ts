// Parses an ExiaInvasion export (blablalink roster JSON) into editable NikkeDrafts.
// Only the fields the export carries are mapped; ATK/HP/DEF and cube stay manual.
// The cookie/game_uid fields in the export are credentials and are never read.

import type { OverloadRow } from '../types/nikkeDraft'

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
