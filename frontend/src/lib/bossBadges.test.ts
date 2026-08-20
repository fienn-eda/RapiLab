import { describe, expect, it } from 'vitest'
import { gimmickBadges, type BossGimmickFlags } from './bossBadges'

const none: BossGimmickFlags = {
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  part_destructible: false,
  spawns_adds: false,
  elemental_interrupt_required: false,
}

describe('gimmickBadges', () => {
  it('꺼진 기믹은 적지 않는다', () => {
    expect(gimmickBadges(none)).toEqual([])
  })

  it('켜진 것만 적는다', () => {
    expect(gimmickBadges({ ...none, part_destructible: true })).toEqual(['부위파괴'])
  })

  it('순서가 고정이다 - 켜진 조합이 달라져도 자리를 바꾸지 않는다', () => {
    expect(
      gimmickBadges({
        core_hittable: true,
        pierce_hits_body_behind_core: true,
        part_destructible: true,
        spawns_adds: true,
        elemental_interrupt_required: true,
      }),
    ).toEqual(['코어 피격', '2관통', '부위파괴', '잡몹 생성', '속성저지 필수'])
  })
})
