import { describe, it, expect } from 'vitest'
import {
  bossProfileToDraft,
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from './bossProfileDraft'

describe('validateBossProfileDraft', () => {
  it('accepts the defaults (non-elemental, DEF 0, 180s, no part destruction)', () => {
    const { errors, value } = validateBossProfileDraft(makeDefaultBossProfileDraft())
    expect(errors).toEqual({})
    expect(value).toEqual({
      element: null,
      core_hittable: false,
      pierce_hits_body_behind_core: false,
      enemy_def: 0,
      fight_duration: 180,
      part_destructible: false,
      part_destruction_times: [],
      spawns_adds: false,
      core_diameter_px: null,
      effective_range_band: null,
      elemental_interrupt_required: false,
    })
  })

  it('accepts an elemental, core-hittable, part-destructible boss with a custom DEF and duration', () => {
    const draft: BossProfileDraft = {
      element: 'Fire',
      boss_name: null,
      core_hittable: true,
      pierce_hits_body_behind_core: false,
      enemy_def: '15000',
      fight_duration: '90',
      part_destructible: true,
      part_destruction_times: '',
      spawns_adds: false,
      core_diameter_px: '',
      effective_range_band: null,
      elemental_interrupt_required: false,
    }
    expect(validateBossProfileDraft(draft).value).toEqual({
      element: 'Fire',
      core_hittable: true,
      pierce_hits_body_behind_core: false,
      enemy_def: 15000,
      fight_duration: 90,
      part_destructible: true,
      part_destruction_times: [],
      spawns_adds: false,
      core_diameter_px: null,
      effective_range_band: null,
      elemental_interrupt_required: false,
    })
  })

  it('rejects a negative enemy_def', () => {
    const draft = { ...makeDefaultBossProfileDraft(), enemy_def: '-1' }
    const { errors, value } = validateBossProfileDraft(draft)
    expect(errors.enemy_def).toBe('0 이상이어야 해요')
    expect(value).toBeUndefined()
  })

  it('rejects a zero or negative fight_duration', () => {
    expect(
      validateBossProfileDraft({ ...makeDefaultBossProfileDraft(), fight_duration: '0' })
        .errors.fight_duration,
    ).toBe('0보다 커야 해요')
    expect(
      validateBossProfileDraft({ ...makeDefaultBossProfileDraft(), fight_duration: '-5' })
        .errors.fight_duration,
    ).toBe('0 이상이어야 해요')
  })

  it('rejects non-numeric fields', () => {
    const draft = { ...makeDefaultBossProfileDraft(), enemy_def: 'abc' }
    expect(validateBossProfileDraft(draft).errors.enemy_def).toBe('숫자를 입력하세요')
  })

  it('rejects empty fields as required', () => {
    const draft = { ...makeDefaultBossProfileDraft(), fight_duration: '' }
    expect(validateBossProfileDraft(draft).errors.fight_duration).toBe('필수 입력이에요')
  })
})

describe('bossProfileToDraft', () => {
  it('round-trips through validate -> toDraft -> validate to an equal BossProfile', () => {
    const draft: BossProfileDraft = {
      element: 'Fire',
      boss_name: null,
      core_hittable: true,
      pierce_hits_body_behind_core: false,
      enemy_def: '15000',
      fight_duration: '90',
      part_destructible: true,
      part_destruction_times: '',
      spawns_adds: false,
      core_diameter_px: '33.33',
      effective_range_band: null,
      elemental_interrupt_required: false,
    }
    const { value: boss } = validateBossProfileDraft(draft)
    const restoredDraft = bossProfileToDraft(boss!)
    const { value: restoredBoss } = validateBossProfileDraft(restoredDraft)
    expect(restoredBoss).toEqual(boss)
  })

  it('round-trips the defaults', () => {
    const { value: boss } = validateBossProfileDraft(makeDefaultBossProfileDraft())
    const { value: restoredBoss } = validateBossProfileDraft(bossProfileToDraft(boss!))
    expect(restoredBoss).toEqual(boss)
  })

  it('2관통 플래그가 draft와 BossProfile 사이를 왕복한다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), pierce_hits_body_behind_core: true }
    const { value } = validateBossProfileDraft(draft)

    expect(value?.pierce_hits_body_behind_core).toBe(true)
    expect(bossProfileToDraft(value!).pierce_hits_body_behind_core).toBe(true)
  })
})

describe('makeDefaultBossProfileDraft', () => {
  it('defaults enemy_def to 0 when no default is given', () => {
    expect(makeDefaultBossProfileDraft().enemy_def).toBe('0')
  })

  it('takes the caller-supplied enemy_def', () => {
    expect(makeDefaultBossProfileDraft('31784').enemy_def).toBe('31784')
  })

  it('leaves every other field at its default when given one', () => {
    const withDef = makeDefaultBossProfileDraft('31784')
    expect({ ...withDef, enemy_def: '0' }).toEqual(makeDefaultBossProfileDraft())
  })
})

describe('core diameter', () => {
  it('빈 칸은 오류가 아니라 null이다 — 안 잰 보스가 기본이다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), core_diameter_px: '' }
    const { errors, value } = validateBossProfileDraft(draft)

    expect(errors.core_diameter_px).toBeUndefined()
    expect(value!.core_diameter_px).toBeNull()
  })

  it('양수는 숫자로 통과한다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), core_diameter_px: '33.33' }

    expect(validateBossProfileDraft(draft).value!.core_diameter_px).toBe(33.33)
  })

  it('0과 음수는 거부한다 — 0은 「코어 없음」이 아니다', () => {
    // 코어가 없다는 것은 core_hittable이 표현한다. 여기 0이 들어오면 값을
    // 못 읽고 자리만 채운 것이다.
    for (const raw of ['0', '-1']) {
      const draft = { ...makeDefaultBossProfileDraft(), core_diameter_px: raw }
      expect(validateBossProfileDraft(draft).errors.core_diameter_px).toBeDefined()
    }
  })

  it('왕복해도 값이 남는다', () => {
    const draft = {
      ...makeDefaultBossProfileDraft(),
      core_hittable: true,
      core_diameter_px: '58.67',
    }
    const { value: boss } = validateBossProfileDraft(draft)
    const restored = validateBossProfileDraft(bossProfileToDraft(boss!))

    // 값을 따로 단언하는 것은 의도다: toEqual만 두면 양쪽 다 필드가 없을 때도
    // 통과해, 이 필드가 왕복에서 빠져도 초록으로 남는다.
    expect(restored.value!.core_diameter_px).toBe(58.67)
    expect(restored.value).toEqual(boss)
  })

  it('이 필드가 없던 시절 저장된 프로필도 복원된다', () => {
    const old = { ...validateBossProfileDraft(makeDefaultBossProfileDraft()).value! }
    delete (old as { core_diameter_px?: unknown }).core_diameter_px

    expect(bossProfileToDraft(old).core_diameter_px).toBe('')
  })
})

describe('파츠 파괴 시각', () => {
  it('쉼표로 구분된 초를 목록으로 읽는다', () => {
    const draft: BossProfileDraft = {
      ...makeDefaultBossProfileDraft(),
      part_destructible: true,
      part_destruction_times: '1, 61, 126',
    }
    expect(validateBossProfileDraft(draft).value!.part_destruction_times)
      .toEqual([1, 61, 126])
  })

  it('빈 칸은 「관측 안 함」이라 빈 목록이다', () => {
    const { value } = validateBossProfileDraft(makeDefaultBossProfileDraft())
    expect(value!.part_destruction_times).toEqual([])
  })

  it('숫자가 아닌 시각은 거부한다', () => {
    const draft = {
      ...makeDefaultBossProfileDraft(),
      part_destruction_times: '1, 나중에',
    }
    const { errors, value } = validateBossProfileDraft(draft)

    expect(errors.part_destruction_times).toBeTruthy()
    expect(value).toBeUndefined()
  })

  it('음수 시각은 거부한다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), part_destruction_times: '-1' }
    expect(validateBossProfileDraft(draft).errors.part_destruction_times).toBeTruthy()
  })

  it('폼으로 왕복해도 시각이 살아남는다', () => {
    const draft: BossProfileDraft = {
      ...makeDefaultBossProfileDraft(),
      part_destructible: true,
      part_destruction_times: '1, 61, 126',
    }
    const { value: boss } = validateBossProfileDraft(draft)
    const restored = validateBossProfileDraft(bossProfileToDraft(boss!))

    // 값을 따로 단언하는 것은 코어 지름과 같은 이유다 - toEqual만 두면 양쪽 다
    // 필드가 없을 때도 통과한다.
    expect(restored.value!.part_destruction_times).toEqual([1, 61, 126])
    expect(restored.value).toEqual(boss)
  })

  it('이 필드가 없던 시절 저장된 프로필도 복원된다', () => {
    const old = { ...validateBossProfileDraft(makeDefaultBossProfileDraft()).value! }
    delete (old as { part_destruction_times?: unknown }).part_destruction_times

    expect(bossProfileToDraft(old).part_destruction_times).toBe('')
  })
})

describe('잡몹 생성', () => {
  it('기본값은 꺼짐이다', () => {
    expect(validateBossProfileDraft(makeDefaultBossProfileDraft()).value!.spawns_adds)
      .toBe(false)
  })

  it('켜면 요청까지 실려 간다', () => {
    const draft = { ...makeDefaultBossProfileDraft(), spawns_adds: true }
    expect(validateBossProfileDraft(draft).value!.spawns_adds).toBe(true)
  })

  it('이 필드가 없던 시절 저장된 프로필도 복원된다', () => {
    const old = { ...validateBossProfileDraft(makeDefaultBossProfileDraft()).value! }
    delete (old as { spawns_adds?: unknown }).spawns_adds

    expect(bossProfileToDraft(old).spawns_adds).toBe(false)
  })
})
