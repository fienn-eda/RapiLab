import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { SeasonGuideCard } from './SeasonGuideCard'
import { guideTitle } from '../lib/bossLabel'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'
import type { BossProfileDraft } from '../types/bossProfileDraft'
import type { RaidRotation } from '../types/raidRotation'

const solo40: RaidRotation = {
  id: 'solo-40',
  raid: 'solo',
  title: '솔로 레이드 40시즌',
  starts_at: '2026-08-20T12:00:00+09:00',
  ends_at: '2026-08-27T04:59:00+09:00',
  source_url: 'https://example.test',
  source_locale: 'ko',
  read_on: '2026-08-20',
  bosses: [],
}

/** 40시즌 「사치스러운 거미」를 고른 상태. 공지의 약점이 Fire라 보스 본인
 *  속성은 Wind다(bossElementFor). */
const picked = (over: Partial<BossProfileDraft> = {}): BossProfileDraft => ({
  ...makeDefaultBossProfileDraft('31784'),
  element: 'Wind',
  boss_name: '사치스러운 거미',
  ...over,
})

beforeEach(() => {
  localStorage.clear()
})

describe('guideTitle', () => {
  it('회차만 뽑는다 - 이 카드는 솔로 탭 안에만 선다', () => {
    expect(guideTitle(solo40)).toBe('40시즌 가이드')
  })

  it('형식이 다르면 제목을 통째로 쓴다', () => {
    expect(guideTitle({ ...solo40, title: '유니온 레이드 7/31' })).toBe(
      '유니온 레이드 7/31 가이드',
    )
  })

  it('회차가 없으면 폴백', () => {
    expect(guideTitle(null)).toBe('보스 가이드')
  })
})

describe('SeasonGuideCard', () => {
  it('약점과 켜진 기믹을 뱃지로 그린다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, spawns_adds: true })}
      />,
    )

    expect(screen.getByText('작열 약점')).toBeInTheDocument()
    expect(screen.getByText('부위파괴')).toBeInTheDocument()
    expect(screen.getByText('잡몹 생성')).toBeInTheDocument()
    expect(screen.queryByText('코어 피격')).not.toBeInTheDocument()
  })

  it('속성을 안 고른 보스는 약점 없음으로 적는다', () => {
    render(<SeasonGuideCard rotation={solo40} boss={makeDefaultBossProfileDraft('31784')} />)
    expect(screen.getByText('약점 없음')).toBeInTheDocument()
  })

  it('적정거리를 고른 보스만 거리 뱃지를 갖는다', () => {
    const { rerender } = render(
      <SeasonGuideCard rotation={solo40} boss={picked({ effective_range_band: 'mid' })} />,
    )
    expect(screen.getByText('중거리')).toBeInTheDocument()

    rerender(<SeasonGuideCard rotation={solo40} boss={picked()} />)
    expect(screen.queryByText('중거리')).not.toBeInTheDocument()
  })

  it('보스를 안 골랐으면 무엇을 할지 적는다', () => {
    render(<SeasonGuideCard rotation={solo40} boss={makeDefaultBossProfileDraft('31784')} />)

    expect(screen.getByText('위에서 이번 회차 보스를 고르세요.')).toBeInTheDocument()
    expect(screen.queryByLabelText('가이드 내용')).not.toBeInTheDocument()
  })

  it('회차 자체가 없어도 뱃지는 그린다 - 보스 설정이 접혀 있어 볼 곳이 여기다', () => {
    render(<SeasonGuideCard rotation={null} boss={picked({ spawns_adds: true })} />)
    expect(screen.getByText('잡몹 생성')).toBeInTheDocument()
    expect(screen.queryByLabelText('가이드 내용')).not.toBeInTheDocument()
  })

  it('쓴 글이 남고, 보스를 바꾸면 다른 글이 나온다', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<SeasonGuideCard rotation={solo40} boss={picked()} />)

    await user.type(screen.getByLabelText('가이드 내용'), '알 먼저')
    expect(screen.getByLabelText('가이드 내용')).toHaveValue('알 먼저')

    rerender(<SeasonGuideCard rotation={solo40} boss={picked({ boss_name: '다른 보스' })} />)
    expect(screen.getByLabelText('가이드 내용')).toHaveValue('')

    rerender(<SeasonGuideCard rotation={solo40} boss={picked()} />)
    expect(screen.getByLabelText('가이드 내용')).toHaveValue('알 먼저')
  })

  it('부위파괴가 꺼져 있으면 파괴 시각을 그리지 않는다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: false, part_destruction_times: '1, 61' })}
      />,
    )
    expect(screen.queryByText(/파괴 1/)).not.toBeInTheDocument()
  })

  it('부위파괴가 켜져 있으면 파괴 시각을 그린다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, part_destruction_times: '1, 61, 126' })}
      />,
    )
    expect(screen.getByText('파괴 1 · 61 · 126초')).toBeInTheDocument()
  })

  // 편집 중인 반쪽짜리 입력이 0초짜리 눈금을 만들면 안 된다.
  it('파괴 시각 칸이 편집 중이어도 빈 조각을 0초로 읽지 않는다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, part_destruction_times: '1, ' })}
      />,
    )
    expect(screen.getByText('파괴 1초')).toBeInTheDocument()
  })
})
