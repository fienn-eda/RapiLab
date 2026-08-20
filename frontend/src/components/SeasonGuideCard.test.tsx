import { render, screen, within } from '@testing-library/react'
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

/** 회차 데이터가 가이드를 실어 온 모양. 이 값이 릴리즈 빌드에 담기는 쪽이다. */
const withBundledGuide = (guide: { at: number | null; text: string }[]): RaidRotation => ({
  ...solo40,
  bosses: [
    {
      name: '사치스러운 거미',
      weakness: 'Fire',
      range_band: 'mid',
      core_diameter_px: null,
      part_destruction_times: [1, 61, 126],
      spawns_adds: true,
      guide,
      stated: {},
    },
  ],
})

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

  it('쓴 이벤트가 남고, 보스를 바꾸면 다른 목록이 나온다', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<SeasonGuideCard rotation={solo40} boss={picked()} />)

    await user.click(screen.getByRole('button', { name: '이벤트 추가' }))
    await user.type(screen.getByPlaceholderText('이 시점에 무엇을 하나'), '알 먼저')
    expect(screen.getByDisplayValue('알 먼저')).toBeInTheDocument()

    rerender(<SeasonGuideCard rotation={solo40} boss={picked({ boss_name: '다른 보스' })} />)
    expect(screen.queryByDisplayValue('알 먼저')).not.toBeInTheDocument()

    rerender(<SeasonGuideCard rotation={solo40} boss={picked()} />)
    expect(screen.getByDisplayValue('알 먼저')).toBeInTheDocument()
  })

  it('회차 데이터의 가이드가 기본으로 깔린다 - 이게 릴리즈에 실리는 쪽이다', () => {
    render(
      <SeasonGuideCard
        rotation={withBundledGuide([{ at: 12, text: '탄막 — 엄폐' }])}
        boss={picked()}
      />,
    )
    expect(screen.getByDisplayValue('탄막 — 엄폐')).toBeInTheDocument()
  })

  it('앱에서 고치면 번들 값을 덮는다', async () => {
    const user = userEvent.setup()
    const rotation = withBundledGuide([{ at: 12, text: '탄막 — 엄폐' }])
    render(<SeasonGuideCard rotation={rotation} boss={picked()} />)

    await user.type(screen.getByDisplayValue('탄막 — 엄폐'), '로 넘긴다')
    expect(screen.getByDisplayValue('탄막 — 엄폐로 넘긴다')).toBeInTheDocument()
  })

  it('고친 적이 없으면 되돌리기가 없다', () => {
    render(
      <SeasonGuideCard
        rotation={withBundledGuide([{ at: 12, text: '탄막 — 엄폐' }])}
        boss={picked()}
      />,
    )
    expect(screen.queryByRole('button', { name: '기본값으로 되돌리기' })).not.toBeInTheDocument()
  })

  it('되돌리면 번들 값이 다시 보인다', async () => {
    const user = userEvent.setup()
    const rotation = withBundledGuide([{ at: 12, text: '탄막 — 엄폐' }])
    render(<SeasonGuideCard rotation={rotation} boss={picked()} />)

    await user.type(screen.getByDisplayValue('탄막 — 엄폐'), '!')
    await user.click(screen.getByRole('button', { name: '기본값으로 되돌리기' }))

    expect(screen.getByDisplayValue('탄막 — 엄폐')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '기본값으로 되돌리기' })).not.toBeInTheDocument()
  })

  // 번들 값이 없는 보스에서는 되돌릴 곳이 없다 - 버튼을 그리면 「빈 목록으로
  // 만들기」가 되어 이름과 다른 일을 한다.
  it('번들 가이드가 없으면 되돌리기가 안 나온다', async () => {
    const user = userEvent.setup()
    render(<SeasonGuideCard rotation={solo40} boss={picked()} />)

    await user.click(screen.getByRole('button', { name: '이벤트 추가' }))
    expect(screen.queryByRole('button', { name: '기본값으로 되돌리기' })).not.toBeInTheDocument()
  })

  it('부위파괴가 꺼져 있으면 파괴 행이 없다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: false, part_destruction_times: '1, 61' })}
      />,
    )
    expect(within(screen.getByRole('list')).queryByText('부위파괴')).not.toBeInTheDocument()
  })

  it('부위파괴가 켜져 있으면 파괴 행이 잔여시간으로 선다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, part_destruction_times: '1, 61, 126' })}
      />,
    )
    // 「부위파괴」는 뱃지 줄에도 있으므로 타임라인 목록으로 좁혀 센다.
    const timeline = within(screen.getByRole('list'))
    expect(timeline.getAllByText('부위파괴')).toHaveLength(3)
    expect(screen.getByText('2:59')).toBeInTheDocument()
    expect(screen.getByText('1:59')).toBeInTheDocument()
    expect(screen.getByText('0:54')).toBeInTheDocument()
  })

  // 편집 중인 반쪽짜리 입력이 0초짜리 행(= 3:00)을 만들면 안 된다.
  it('파괴 시각 칸이 편집 중이어도 빈 조각을 0초로 읽지 않는다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, part_destruction_times: '1, ' })}
      />,
    )
    expect(within(screen.getByRole('list')).getAllByText('부위파괴')).toHaveLength(1)
    expect(screen.getByText('2:59')).toBeInTheDocument()
  })

  // 전투 시간을 바꾸면 같은 경과 초가 다른 잔여시간이 된다 - 이벤트는 전투
  // 시작에 붙어 있고 시계만 길어진다.
  it('전투 시간을 바꾸면 파괴 행의 잔여시간이 따라 움직인다', () => {
    const { rerender } = render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, part_destruction_times: '60' })}
      />,
    )
    expect(screen.getByText('2:00')).toBeInTheDocument()

    rerender(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({
          part_destructible: true,
          part_destruction_times: '60',
          fight_duration: '200',
        })}
      />,
    )
    expect(screen.getByText('2:20')).toBeInTheDocument()
  })
})
