// Editable form state for one Nikke, plus the validation that turns a draft
// into a valid UserNikkeState. Numeric fields are held as strings so inputs can
// be cleared/partial while typing; validation parses and range-checks them
// against CONSTRAINTS (mirrored from backend/app/models.py).

import {
  CONSTRAINTS,
  type OverloadOption,
  type UserNikkeState,
} from './userNikkeState'

export interface OverloadRow {
  id: string
  name: string
  value: string
}

export interface NikkeDraft {
  id: string
  character_slug: string
  // Breakthrough / core enhancement, display only. Optional because a
  // manually created draft has no import to take them from; absent must not
  // be read as zero.
  grade?: number
  core?: number
  // Whether the player has this unit's Favorite Item equipped, display only.
  // The promoted slug cannot stand in for it: only 13 units have a distinct
  // "-signature" encoding, so everyone else keeps a plain slug whether or not
  // the item is equipped. Optional for the same reason grade is - absent means
  // "the import never said", which is not the same as false.
  favorite_item?: boolean
  level: string
  hp: string
  atk: string
  def_: string
  actualHp: string
  actualAtk: string
  actualDef: string
  skill_levels: { skill1: string; skill2: string; burst: string }
  overload_options: OverloadRow[]
}

export interface NikkeDraftErrors {
  character_slug?: string
  level?: string
  hp?: string
  atk?: string
  def_?: string
  skill_levels?: { skill1?: string; skill2?: string; burst?: string }
  overload_options?: Record<string, { name?: string; value?: string }>
}

const newId = (): string => crypto.randomUUID()

export const makeEmptyDraft = (): NikkeDraft => ({
  id: newId(),
  character_slug: '',
  level: '',
  hp: '',
  atk: '',
  def_: '',
  actualHp: '',
  actualAtk: '',
  actualDef: '',
  skill_levels: { skill1: '', skill2: '', burst: '' },
  overload_options: [],
})

interface ParsedNumber {
  error?: string
  value?: number
}

const parseIntField = (
  raw: string,
  bounds: { min: number; max?: number },
): ParsedNumber => {
  const trimmed = raw.trim()
  if (trimmed === '') return { error: 'Required' }
  if (!/^-?\d+$/.test(trimmed)) return { error: 'Must be a whole number' }
  const value = Number(trimmed)
  if (value < bounds.min) return { error: `Must be ≥ ${bounds.min}` }
  if (bounds.max !== undefined && value > bounds.max)
    return { error: `Must be ≤ ${bounds.max}` }
  return { value }
}

const parseFloatField = (
  raw: string,
  bounds: { min: number },
): ParsedNumber => {
  const trimmed = raw.trim()
  if (trimmed === '') return { error: 'Required' }
  const value = Number(trimmed)
  if (!Number.isFinite(value)) return { error: 'Must be a number' }
  if (value < bounds.min) return { error: `Must be ≥ ${bounds.min}` }
  return { value }
}

export interface ValidationResult {
  errors: NikkeDraftErrors
  value?: UserNikkeState
}

/**
 * Validate a draft against the UserNikkeState constraints. Returns field-level
 * errors and, only when the whole draft is valid, the parsed UserNikkeState.
 */
export const validateDraft = (draft: NikkeDraft): ValidationResult => {
  const errors: NikkeDraftErrors = {}

  if (draft.character_slug.trim() === '') errors.character_slug = 'Required'

  const level = parseIntField(draft.level, CONSTRAINTS.level)
  if (level.error) errors.level = level.error

  const hp = parseFloatField(draft.hp, CONSTRAINTS.hp)
  if (hp.error) errors.hp = hp.error

  const atk = parseFloatField(draft.atk, CONSTRAINTS.atk)
  if (atk.error) errors.atk = atk.error

  const def_ = parseFloatField(draft.def_, CONSTRAINTS.def_)
  if (def_.error) errors.def_ = def_.error

  const skill1 = parseIntField(draft.skill_levels.skill1, CONSTRAINTS.skill)
  const skill2 = parseIntField(draft.skill_levels.skill2, CONSTRAINTS.skill)
  const burst = parseIntField(draft.skill_levels.burst, CONSTRAINTS.skill)
  const skillErrors = {
    ...(skill1.error ? { skill1: skill1.error } : {}),
    ...(skill2.error ? { skill2: skill2.error } : {}),
    ...(burst.error ? { burst: burst.error } : {}),
  }
  if (Object.keys(skillErrors).length > 0) errors.skill_levels = skillErrors

  const overloadOptions: OverloadOption[] = []
  const overloadErrors: Record<string, { name?: string; value?: string }> = {}
  for (const row of draft.overload_options) {
    const rowErrors: { name?: string; value?: string } = {}
    const name = row.name.trim()
    if (name === '') rowErrors.name = 'Required'
    const parsedValue = parseFloatField(row.value, { min: -Infinity })
    if (parsedValue.error) rowErrors.value = parsedValue.error
    if (Object.keys(rowErrors).length > 0) {
      overloadErrors[row.id] = rowErrors
    } else {
      overloadOptions.push({ name, value: parsedValue.value! })
    }
  }
  if (Object.keys(overloadErrors).length > 0)
    errors.overload_options = overloadErrors

  if (Object.keys(errors).length > 0) return { errors }

  const value: UserNikkeState = {
    character_slug: draft.character_slug.trim(),
    level: level.value!,
    hp: hp.value!,
    atk: atk.value!,
    def_: def_.value!,
    skill_levels: {
      skill1: skill1.value!,
      skill2: skill2.value!,
      burst: burst.value!,
    },
    overload_options: overloadOptions,
  }

  for (const [key, raw] of [
    ['actual_hp', draft.actualHp],
    ['actual_atk', draft.actualAtk],
    ['actual_def', draft.actualDef],
  ] as const) {
    const t = raw.trim()
    if (t !== '' && /^\d+(\.\d+)?$/.test(t)) value[key] = Number(t)
  }

  return { errors, value }
}

/** The subset of drafts that are complete and valid, parsed into UserNikkeState. */
export const getValidRoster = (drafts: NikkeDraft[]): UserNikkeState[] =>
  drafts
    .map((draft) => validateDraft(draft).value)
    .filter((value): value is UserNikkeState => value != null)
