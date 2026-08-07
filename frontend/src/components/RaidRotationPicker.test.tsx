import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { RaidRotation } from '../types/raidRotation'
import { RaidRotationPicker } from './RaidRotationPicker'

const rotation: RaidRotation = {
  id: 'union-2026-07-31',
  raid: 'union',
  title: '유니온 레이드 7/31',
  starts_at: '2026-07-31T05:00:00+09:00',
  ends_at: '2026-08-06T04:59:00+09:00',
  source_url: 'https://arca.live/b/nikketgv/177833660',
  source_locale: 'ko',
  read_on: '2026-08-07',
  bosses: [
    {
      name: '선바스',
      weakness: 'Electric',
      stated: { 등급: '로드 급', 거리: '근거리', 설명: ['머리에 꽃을 얹은 랩쳐.'] },
    },
    { name: '토커티브', weakness: 'Water', stated: { 등급: '타이런트 급' } },
  ],
}

describe('RaidRotationPicker', () => {
  it('회차의 보스를 전부 그린다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /선바스/ })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /토커티브/ })).toBeInTheDocument()
  })

  it('공지 원문을 해석하지 않고 그대로 보여준다', () => {
    // 「거리: 근거리」는 우리 적정거리 밴드로 번역되지 않는다 - 화면에 원문으로
    // 남아 있어야 Fienn이 보고 직접 판단할 수 있다.
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getByText('거리')).toBeInTheDocument()
    expect(screen.getByText('근거리')).toBeInTheDocument()
  })

  it('여러 줄짜리 항목도 전부 보여준다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getByText('머리에 꽃을 얹은 랩쳐.')).toBeInTheDocument()
  })

  it('고른 보스를 콜백으로 넘긴다', async () => {
    const onPick = vi.fn()
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={onPick} />)
    await userEvent.click(screen.getByRole('radio', { name: /토커티브/ }))
    expect(onPick).toHaveBeenCalledWith(rotation.bosses[1])
  })

  it('선택된 보스만 체크되어 있다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName="선바스" onPick={vi.fn()} />)
    expect(screen.getByRole('radio', { name: /선바스/ })).toBeChecked()
    expect(screen.getByRole('radio', { name: /토커티브/ })).not.toBeChecked()
  })
})
