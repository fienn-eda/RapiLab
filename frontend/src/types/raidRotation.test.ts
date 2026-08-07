import { describe, expect, it } from 'vitest'
import { latestRotationFor, type RaidRotation } from './raidRotation'

const rotation = (id: string, raid: 'solo' | 'union', endsAt: string): RaidRotation => ({
  id,
  raid,
  title: id,
  starts_at: null,
  ends_at: endsAt,
  source_url: 'https://example.test',
  source_locale: 'ko',
  read_on: '2026-01-01',
  bosses: [],
})

describe('latestRotationFor', () => {
  it('같은 레이드 중 가장 늦게 끝나는 회차를 고른다', () => {
    const rotations = [
      rotation('solo-38', 'solo', '2026-07-09T04:59:00+09:00'),
      rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00'),
    ]
    expect(latestRotationFor(rotations, 'solo')?.id).toBe('solo-39')
  })

  it('배열 순서가 아니라 종료 시각으로 고른다', () => {
    // 과거 회차를 뒤늦게 채워 넣으면 배열 끝이 최신이 아니게 된다.
    const rotations = [
      rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00'),
      rotation('solo-37', 'solo', '2026-06-25T04:59:00+09:00'),
    ]
    expect(latestRotationFor(rotations, 'solo')?.id).toBe('solo-39')
  })

  it('다른 레이드의 회차는 보지 않는다', () => {
    const rotations = [
      rotation('union-1', 'union', '2026-12-31T04:59:00+09:00'),
      rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00'),
    ]
    expect(latestRotationFor(rotations, 'solo')?.id).toBe('solo-39')
  })

  it('그 레이드의 회차가 없으면 null이다', () => {
    expect(latestRotationFor([rotation('solo-39', 'solo', '2026-07-23T04:59:00+09:00')], 'union'))
      .toBeNull()
  })
})
