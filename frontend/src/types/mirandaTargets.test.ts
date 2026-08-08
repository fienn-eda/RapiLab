import { describe, expect, it } from 'vitest'
import { mapMirandaTargetsResult } from './mirandaTargets'
import type { MirandaTargetsResultWire } from './mirandaTargets'

const WIRE: MirandaTargetsResultWire = {
  seats: [
    { slug: 'miranda-signature', burst_tier: 1 },
    { slug: 'crown', burst_tier: 2 },
    { slug: 'ada-wong', burst_tier: 3 },
  ],
  miranda_slug: 'miranda-signature',
  has_favorite_item: true,
  cycles: [
    { index: 1, powering_up: ['ada-wong', 'crown'], wake_up_crit_rate: ['ada-wong'] },
  ],
  overload_thresholds: [
    { slug: 'crown', current_percent: 8, kind: 'gain', threshold_percent: 11.47 },
    { slug: 'ada-wong', current_percent: 12, kind: 'keep', threshold_percent: 0 },
  ],
  overload_atk_cap_percent: 58.52,
  notes: ['무속성 보스·180초 전투를 가정해 계산했어요.'],
}

describe('mapMirandaTargetsResult', () => {
  it('renames every wire field to camelCase', () => {
    const result = mapMirandaTargetsResult(WIRE)
    expect(result.seats).toEqual([
      { slug: 'miranda-signature', burstTier: 1 },
      { slug: 'crown', burstTier: 2 },
      { slug: 'ada-wong', burstTier: 3 },
    ])
    expect(result.mirandaSlug).toBe('miranda-signature')
    expect(result.hasFavoriteItem).toBe(true)
    expect(result.cycles).toEqual([
      { index: 1, poweringUp: ['ada-wong', 'crown'], wakeUpCritRate: ['ada-wong'] },
    ])
    expect(result.overloadAtkCapPercent).toBe(58.52)
    expect(result.notes).toEqual(WIRE.notes)
  })

  it('keeps a null threshold as null rather than dropping it', () => {
    // null은 「상한 안에 답이 없다」는 뜻을 지닌 값이지 누락이 아니다.
    const wire = {
      ...WIRE,
      overload_thresholds: [
        { slug: 'isabel', current_percent: 0, kind: 'gain' as const, threshold_percent: null },
      ],
    }
    expect(mapMirandaTargetsResult(wire).overloadThresholds).toEqual([
      { slug: 'isabel', currentPercent: 0, kind: 'gain', thresholdPercent: null },
    ])
  })
})
