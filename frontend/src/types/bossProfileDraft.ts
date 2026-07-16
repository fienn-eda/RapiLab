// Editable form state for the boss profile, plus the validation that turns a
// draft into a BossProfile. Numeric fields are held as strings so inputs can
// be cleared/partial while typing, same pattern as nikkeDraft.ts.

import type { BossElement, BossProfile } from './recommend'

export interface BossProfileDraft {
  element: BossElement
  core_hittable: boolean
  enemy_def: string
  fight_duration: string
}

export const makeDefaultBossProfileDraft = (): BossProfileDraft => ({
  element: null,
  core_hittable: false,
  enemy_def: '0',
  fight_duration: '180',
})

export interface BossProfileDraftErrors {
  enemy_def?: string
  fight_duration?: string
}

export interface BossProfileValidationResult {
  errors: BossProfileDraftErrors
  value?: BossProfile
}

interface ParsedNumber {
  error?: string
  value?: number
}

const parseFloatField = (raw: string, bounds: { min: number }): ParsedNumber => {
  const trimmed = raw.trim()
  if (trimmed === '') return { error: 'Required' }
  const value = Number(trimmed)
  if (!Number.isFinite(value)) return { error: 'Must be a number' }
  if (value < bounds.min) return { error: `Must be ≥ ${bounds.min}` }
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
  else if (fightDuration.value === 0) errors.fight_duration = 'Must be > 0'

  if (Object.keys(errors).length > 0) return { errors }

  const value: BossProfile = {
    element: draft.element,
    core_hittable: draft.core_hittable,
    enemy_def: enemyDef.value!,
    fight_duration: fightDuration.value!,
  }
  return { errors, value }
}
