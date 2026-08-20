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
      range_band: 'near',
      core_diameter_px: null,
      part_destruction_times: [],
      stated: { 등급: '로드 급', 거리: '근거리', 설명: ['머리에 꽃을 얹은 랩쳐.'] },
    },
    {
      name: '토커티브',
      weakness: 'Water',
      range_band: 'far',
      core_diameter_px: null,
      part_destruction_times: [],
      stated: { 등급: '타이런트 급' },
    },
  ],
}

describe('RaidRotationPicker', () => {
  it('회차의 보스를 전부 그린다', () => {
    // 이름을 정확 일치로 찾는 것이 카드에 문단이 섞이지 않았다는 증거이기도 하다 —
    // 라벨 안에 공지 원문이 들어가면 접근성 이름이 길어져 여기서 먼저 깨진다.
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getByRole('radio', { name: '전격선바스' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '수냉토커티브' })).toBeInTheDocument()
  })

  it('카드에는 이름과 약점 아이콘만 나온다', () => {
    // 공지 원문은 `stated`에 기록으로 남지만 화면에는 안 나온다 - 5장이 각자
    // 두어 문단을 달고 있으면 정작 만지려는 보스 설정이 화면 밖으로 밀린다.
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.queryByText('거리')).not.toBeInTheDocument()
    expect(screen.queryByText('근거리')).not.toBeInTheDocument()
    expect(screen.queryByText('머리에 꽃을 얹은 랩쳐.')).not.toBeInTheDocument()
    expect(screen.queryByText('로드 급')).not.toBeInTheDocument()
  })

  it('고른 보스를 콜백으로 넘긴다', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={onPick} />)
    await user.click(screen.getByRole('radio', { name: '수냉토커티브' }))
    expect(onPick).toHaveBeenCalledWith(rotation.bosses[1])
  })

  it('선택된 보스만 체크되어 있다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName="선바스" onPick={vi.fn()} />)
    expect(screen.getByRole('radio', { name: '전격선바스' })).toBeChecked()
    expect(screen.getByRole('radio', { name: '수냉토커티브' })).not.toBeChecked()
  })

  it('카드는 보스 수만큼만 그려진다', () => {
    render(<RaidRotationPicker rotation={rotation} selectedName={null} onPick={vi.fn()} />)
    expect(screen.getAllByRole('radio')).toHaveLength(rotation.bosses.length)
  })
})
