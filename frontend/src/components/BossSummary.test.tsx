import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BossSummary } from './BossSummary'
import type { BossProfile } from '../types/recommend'

const boss = (overrides: Partial<BossProfile> = {}): BossProfile => ({
  element: null,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: 31784,
  fight_duration: 180,
  part_destructible: false,
  effective_range_band: null,
  elemental_interrupt_required: false,
  ...overrides,
})

describe('BossSummary', () => {
  it('보스 본인 속성이 아니라 약점으로 말한다', () => {
    // 작열('Fire') 보스는 수냉이 약점이다.
    render(<BossSummary boss={boss({ element: 'Fire' })} />)

    expect(screen.getByText(/약점 수냉/)).toBeInTheDocument()
  })

  it('약점이 없으면 없다고 말한다', () => {
    render(<BossSummary boss={boss()} />)

    expect(screen.getByText(/약점 없음/)).toBeInTheDocument()
  })

  it('꺼진 기믹은 아예 그리지 않는다', () => {
    render(<BossSummary boss={boss()} />)

    expect(screen.queryByText(/코어 피격/)).not.toBeInTheDocument()
    expect(screen.queryByText(/2관통/)).not.toBeInTheDocument()
    expect(screen.queryByText(/부위파괴/)).not.toBeInTheDocument()
    expect(screen.queryByText(/속성저지/)).not.toBeInTheDocument()
  })

  it('켜진 기믹은 전부 적는다', () => {
    render(
      <BossSummary
        boss={boss({
          core_hittable: true,
          pierce_hits_body_behind_core: true,
          part_destructible: true,
          elemental_interrupt_required: true,
        })}
      />,
    )

    expect(screen.getByText('코어 피격')).toBeInTheDocument()
    expect(screen.getByText('2관통')).toBeInTheDocument()
    expect(screen.getByText('부위파괴')).toBeInTheDocument()
    expect(screen.getByText('속성저지 필수')).toBeInTheDocument()
  })

  it('적정거리는 정해졌을 때만 적는다', () => {
    const { rerender } = render(<BossSummary boss={boss()} />)
    expect(screen.queryByText(/거리/)).not.toBeInTheDocument()

    rerender(<BossSummary boss={boss({ effective_range_band: 'far' })} />)
    expect(screen.getByText('원거리')).toBeInTheDocument()
  })

  // 보스 폼이 이 둘을 접어 두므로, 결과에 남는 유일한 자리가 여기다.
  it('접혀 있는 두 숫자를 언제나 싣는다', () => {
    render(<BossSummary boss={boss()} />)

    expect(screen.getByText('방어력 31,784')).toBeInTheDocument()
    expect(screen.getByText('180초')).toBeInTheDocument()
  })
})
