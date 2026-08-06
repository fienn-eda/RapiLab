// Editable form state for the boss profile, plus the validation that turns a
// draft into a BossProfile. Numeric fields are held as strings so inputs can
// be cleared/partial while typing, same pattern as nikkeDraft.ts.

import type { BossElement, BossProfile, BossRangeBand } from './recommend'

export interface BossProfileDraft {
  element: BossElement
  core_hittable: boolean
  pierce_hits_body_behind_core: boolean
  enemy_def: string
  fight_duration: string
  part_destructible: boolean
  effective_range_band: BossRangeBand
  elemental_interrupt_required: boolean
}

/** 기본 방어력은 호출부가 정한다 — 솔로 레이드와 유니온 레이드 보스는 방어력이
 * 다르므로, 공유 기본값 하나로는 한쪽이 틀린 값으로 계산된다. */
export const makeDefaultBossProfileDraft = (enemyDef = '0'): BossProfileDraft => ({
  element: null,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: enemyDef,
  fight_duration: '180',
  part_destructible: false,
  effective_range_band: null,
  elemental_interrupt_required: false,
})

export interface BossProfileDraftErrors {
  enemy_def?: string
  fight_duration?: string
}

export interface BossProfileValidationResult {
  errors: BossProfileDraftErrors
  value?: BossProfile
}

/** Inverse of validateBossProfileDraft's numeric parse - turns a stored/restored
 * BossProfile back into editable form state (numbers as strings). Used to
 * repopulate the boss form from a profile's lastInputs. */
export const bossProfileToDraft = (boss: BossProfile): BossProfileDraft => ({
  element: boss.element,
  core_hittable: boss.core_hittable,
  // 이 필드가 생기기 전에 저장된 프로필은 undefined라, 그대로 두면 체크박스가
  // 비제어 컴포넌트가 된다.
  pierce_hits_body_behind_core: boss.pierce_hits_body_behind_core ?? false,
  enemy_def: String(boss.enemy_def),
  fight_duration: String(boss.fight_duration),
  part_destructible: boss.part_destructible,
  // A profile saved before this field existed has it undefined, which would
  // otherwise reach the select as an uncontrolled value.
  effective_range_band: boss.effective_range_band ?? null,
  // 이 필드가 생기기 전에 저장된 프로필은 undefined라, 그대로 두면 체크박스가
  // 비제어 컴포넌트가 된다.
  elemental_interrupt_required: boss.elemental_interrupt_required ?? false,
})

interface ParsedNumber {
  error?: string
  value?: number
}

const parseFloatField = (raw: string, bounds: { min: number }): ParsedNumber => {
  const trimmed = raw.trim()
  if (trimmed === '') return { error: '필수 입력이에요' }
  const value = Number(trimmed)
  if (!Number.isFinite(value)) return { error: '숫자를 입력하세요' }
  if (value < bounds.min) return { error: `${bounds.min} 이상이어야 해요` }
  return { value }
}

/**
 * Validate a boss profile draft. Returns field-level errors and, only when
 * the whole draft is valid, the parsed BossProfile.
 */
export const validateBossProfileDraft = (
  draft: BossProfileDraft,
): BossProfileValidationResult => {
  const errors: BossProfileDraftErrors = {}

  const enemyDef = parseFloatField(draft.enemy_def, { min: 0 })
  if (enemyDef.error) errors.enemy_def = enemyDef.error

  const fightDuration = parseFloatField(draft.fight_duration, { min: 0 })
  if (fightDuration.error) errors.fight_duration = fightDuration.error
  else if (fightDuration.value === 0) errors.fight_duration = '0보다 커야 해요'

  if (Object.keys(errors).length > 0) return { errors }

  const value: BossProfile = {
    element: draft.element,
    core_hittable: draft.core_hittable,
    pierce_hits_body_behind_core: draft.pierce_hits_body_behind_core,
    enemy_def: enemyDef.value!,
    fight_duration: fightDuration.value!,
    part_destructible: draft.part_destructible,
    effective_range_band: draft.effective_range_band,
    elemental_interrupt_required: draft.elemental_interrupt_required,
  }
  return { errors, value }
}
