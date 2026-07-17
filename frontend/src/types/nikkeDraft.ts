// Editable form state for one Nikke, plus the validation that turns a draft
// into a valid UserNikkeState. Numeric fields are held as strings so inputs can
// be cleared/partial while typing; validation parses and range-checks them
// against CONSTRAINTS (mirrored from backend/app/models.py).

import {
  CONSTRAINTS,
  type OverloadOption,
  type PveCube,
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
  level: string
  core_level: string
  hp: string
  atk: string
  def_: string
  actualHp: string
  actualAtk: string
  actualDef: string
  skill_levels: { skill1: string; skill2: string; burst: string }
  overload_options: OverloadRow[]
  hasCube: boolean
  pve_cube: { name: string; level: string }
}

export interface NikkeDraftErrors {
  character_slug?: string
  level?: string
  core_level?: string
  hp?: string
  atk?: string
  def_?: string
  skill_levels?: { skill1?: string; skill2?: string; burst?: string }
  overload_options?: Record<string, { name?: string; value?: string }>
  pve_cube?: { name?: string; level?: string }
}

const newId = (): string => crypto.randomUUID()

export const makeOverloadRow = (): OverloadRow => ({
  id: newId(),
  name: '',
  value: '',
})

export const makeEmptyDraft = (): NikkeDraft => ({
  id: newId(),
  character_slug: '',
  level: '',
  core_level: '',
  hp: '',
  atk: '',
  def_: '',
  actualHp: '',
  actualAtk: '',
  actualDef: '',
  skill_levels: { skill1: '', skill2: '', burst: '' },
  overload_options: [],
  hasCube: false,
  pve_cube: { name: '', level: '' },
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

  const coreLevel = parseIntField(draft.core_level, CONSTRAINTS.core_level)
  if (coreLevel.error) errors.core_level = coreLevel.error

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

  let pveCube: PveCube | null = null
  if (draft.hasCube) {
    const cubeErrors: { name?: string; level?: string } = {}
    const cubeName = draft.pve_cube.name.trim()
    if (cubeName === '') cubeErrors.name = 'Required'
    const cubeLevel = parseIntField(draft.pve_cube.level, CONSTRAINTS.cubeLevel)
    if (cubeLevel.error) cubeErrors.level = cubeLevel.error
    if (Object.keys(cubeErrors).length > 0) {
      errors.pve_cube = cubeErrors
    } else {
      pveCube = { name: cubeName, level: cubeLevel.value! }
    }
  }

  if (Object.keys(errors).length > 0) return { errors }

  const value: UserNikkeState = {
    character_slug: draft.character_slug.trim(),
    level: level.value!,
    core_level: coreLevel.value!,
    hp: hp.value!,
    atk: atk.value!,
    def_: def_.value!,
    skill_levels: {
      skill1: skill1.value!,
      skill2: skill2.value!,
      burst: burst.value!,
    },
    overload_options: overloadOptions,
    pve_cube: pveCube,
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

/**
 * Merge collector roster.json drafts into the current roster by
 * character_slug. Unlike mergeRosterDrafts (which preserves manually-entered
 * stats/cube because the ExiaInvasion export lacks them), the collector's
 * roster.json is authoritative for stats, so an existing unit's stats, cube,
 * and actual-level stats are overwritten too. core_level is NOT overwritten
 * (the collector does not capture it — the displayed stats already bake in
 * the real grade/core).
 */
export const mergeCollectorDrafts = (
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
        hp: inc.hp,
        atk: inc.atk,
        def_: inc.def_,
        actualHp: inc.actualHp,
        actualAtk: inc.actualAtk,
        actualDef: inc.actualDef,
        skill_levels: inc.skill_levels,
        overload_options: inc.overload_options,
        hasCube: inc.hasCube,
        pve_cube: inc.pve_cube,
      }
      updated += 1
    }
  }

  return { drafts: next, added, updated }
}
