// Editable form state for the boss profile, plus the validation that turns a
// draft into a BossProfile. Numeric fields are held as strings so inputs can
// be cleared/partial while typing, same pattern as nikkeDraft.ts.

import type { BossElement, BossProfile, BossRangeBand } from './recommend'

export interface BossProfileDraft {
  element: BossElement
  /** 회차에서 고른 보스 이름. 표시 전용이라 BossProfile(wire)에는 가지 않는다.
   * 속성이 손으로 바뀌면 null로 돌아간다 - 이름이 가리키던 보스가 아니게 된다. */
  boss_name: string | null
  core_hittable: boolean
  pierce_hits_body_behind_core: boolean
  enemy_def: string
  fight_duration: string
  part_destructible: boolean
  /** 잡몹이 주기적으로 생성되는 보스. 홀드 파이어 택틱을 탐색에서 지운다. */
  spawns_adds: boolean
  /** 파츠가 깨지는 시각을 쉼표로 구분한 초. 빈 문자열 = 관측 안 함. */
  part_destruction_times: string
  /** 빈 문자열 = 안 쟀다. 필수가 아니라서 다른 숫자 칸과 파싱 규칙이 다르다. */
  core_diameter_px: string
  effective_range_band: BossRangeBand
  elemental_interrupt_required: boolean
}

/** 기본 방어력은 호출부가 정한다 — 솔로 레이드와 유니온 레이드 보스는 방어력이
 * 다르므로, 공유 기본값 하나로는 한쪽이 틀린 값으로 계산된다. */
export const makeDefaultBossProfileDraft = (enemyDef = '0'): BossProfileDraft => ({
  element: null,
  boss_name: null,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: enemyDef,
  fight_duration: '180',
  part_destructible: false,
  spawns_adds: false,
  part_destruction_times: '',
  core_diameter_px: '',
  effective_range_band: null,
  elemental_interrupt_required: false,
})

export interface BossProfileDraftErrors {
  enemy_def?: string
  fight_duration?: string
  core_diameter_px?: string
  part_destruction_times?: string
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
  // wire에는 이름이 없다. 복원한 폼은 약점 이름으로 자기를 부른다.
  boss_name: null,
  core_hittable: boss.core_hittable,
  // 이 필드가 생기기 전에 저장된 프로필은 undefined라, 그대로 두면 체크박스가
  // 비제어 컴포넌트가 된다.
  pierce_hits_body_behind_core: boss.pierce_hits_body_behind_core ?? false,
  enemy_def: String(boss.enemy_def),
  fight_duration: String(boss.fight_duration),
  part_destructible: boss.part_destructible,
  // 이 필드가 생기기 전에 저장된 프로필은 undefined라, 그대로 두면 체크박스가
  // 비제어 컴포넌트가 된다.
  spawns_adds: boss.spawns_adds ?? false,
  // 이 필드가 생기기 전에 저장된 프로필은 undefined라, 빈 칸으로 돌아간다.
  part_destruction_times: (boss.part_destruction_times ?? []).join(', '),
  // 이 필드가 생기기 전에 저장된 프로필은 undefined이고, null은 「안 쟀다」다.
  // 둘 다 빈 칸으로 돌아간다.
  core_diameter_px: boss.core_diameter_px == null ? '' : String(boss.core_diameter_px),
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

/** 안 재도 되는 양수 칸. 빈 칸은 오류가 아니라 `null`이다 — `parseFloatField`는
 * 빈 값을 「필수 입력」 오류로 보므로 재사용할 수 없다. */
const parseOptionalPositive = (raw: string): ParsedNumber => {
  const trimmed = raw.trim()
  if (trimmed === '') return {}
  const value = Number(trimmed)
  if (!Number.isFinite(value)) return { error: '숫자를 입력하세요' }
  if (value <= 0) return { error: '0보다 커야 해요' }
  return { value }
}

interface ParsedTimes {
  error?: string
  value: number[]
}

/** 쉼표로 구분된 초. 빈 칸은 오류가 아니라 「관측 안 함」이라 빈 목록이다.
 * 0은 허용한다 - 전투 시작과 동시에 깨지는 파츠가 있을 수 있고, 엔진에도 t=0은
 * 유효한 시각이다(battle_start가 거기 있다). */
const parseDestructionTimes = (raw: string): ParsedTimes => {
  const tokens = raw.split(',').map((token) => token.trim()).filter((token) => token !== '')
  const value: number[] = []
  for (const token of tokens) {
    const time = Number(token)
    if (!Number.isFinite(time)) return { error: '초를 쉼표로 구분해 적으세요', value: [] }
    if (time < 0) return { error: '0 이상이어야 해요', value: [] }
    value.push(time)
  }
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

  const coreDiameter = parseOptionalPositive(draft.core_diameter_px)
  if (coreDiameter.error) errors.core_diameter_px = coreDiameter.error

  const destructionTimes = parseDestructionTimes(draft.part_destruction_times)
  if (destructionTimes.error) errors.part_destruction_times = destructionTimes.error

  if (Object.keys(errors).length > 0) return { errors }

  const value: BossProfile = {
    element: draft.element,
    core_hittable: draft.core_hittable,
    pierce_hits_body_behind_core: draft.pierce_hits_body_behind_core,
    enemy_def: enemyDef.value!,
    fight_duration: fightDuration.value!,
    part_destructible: draft.part_destructible,
    spawns_adds: draft.spawns_adds,
    part_destruction_times: destructionTimes.value,
    core_diameter_px: coreDiameter.value ?? null,
    effective_range_band: draft.effective_range_band,
    elemental_interrupt_required: draft.elemental_interrupt_required,
  }
  return { errors, value }
}
