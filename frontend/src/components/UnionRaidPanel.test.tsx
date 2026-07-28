import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnionRaidPanel } from './UnionRaidPanel'
import { DRAG_SLUG_TYPE } from './UnitPalette'
import type { UserNikkeState } from '../types/userNikkeState'
import type { SupportedUnit } from '../types/supportedUnit'

vi.mock('../api/evaluateDecks', () => ({
  evaluateDecks: vi.fn(),
}))

import { evaluateDecks } from '../api/evaluateDecks'

/** Seats `slug` in deck `deckNumber` (1-based) the way the UI does: by drop.
 * jsdom implements no drag, so hand the handler the slug a real drag would
 * have carried — same helper RecommendPanel.test.tsx uses. */
const dropOnDeck = (deckNumber: number, slug: string) => {
  const deck = screen.getByRole('heading', { name: new RegExp(`덱 ${deckNumber}`) })
  fireEvent.drop(deck.closest('div')!, {
    dataTransfer: {
      types: [DRAG_SLUG_TYPE],
      getData: (type: string) => (type === DRAG_SLUG_TYPE ? slug : ''),
    },
  })
}

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 200,
  hp: 1_000_000,
  atk: 85_000,
  def_: 12_000,
  skill_levels: { skill1: 10, skill2: 7, burst: 4 },
  overload_options: [],
})

// 15 units so the three battles' 5-seat decks can actually be filled without
// repeats — union raid's "all 15 seats different Nikkes" rule.
const roster: UserNikkeState[] = Array.from({ length: 15 }, (_, i) => nikke(`u${i}`))
const supportedUnits: SupportedUnit[] = Array.from({ length: 15 }, (_, i) => ({
  slug: `u${i}`,
  name: `U${i}`,
  burstTier: ((i % 3) + 1) as 1 | 2 | 3,
  element: 'Iron' as const,
}))

const portraitFor = () => null
const nameFor = (slug: string) => slug.toUpperCase()
const burstTierFor = (slug: string): 1 | 2 | 3 | null => {
  const i = Number(slug.slice(1))
  return Number.isNaN(i) ? null : (((i % 3) + 1) as 1 | 2 | 3)
}

const renderPanel = () =>
  render(
    <UnionRaidPanel
      roster={roster}
      supportedUnits={supportedUnits}
      portraitFor={portraitFor}
      nameFor={nameFor}
      burstTierFor={burstTierFor}
    />,
  )

beforeEach(() => {
  vi.mocked(evaluateDecks).mockReset()
})

afterEach(() => {
  vi.mocked(evaluateDecks).mockReset()
})

describe('UnionRaidPanel', () => {
  it('기본으로 전투 3회분의 보스 설정을 그린다', () => {
    renderPanel()
    expect(screen.getAllByRole('group', { name: /전투/ })).toHaveLength(3)
  })

  it('전투마다 보스 속성을 따로 고를 수 있다', async () => {
    renderPanel()
    const groups = screen.getAllByRole('group', { name: /전투/ })
    await userEvent.selectOptions(within(groups[0]).getByLabelText(/속성/), 'Iron')
    await userEvent.selectOptions(within(groups[1]).getByLabelText(/속성/), 'Water')
    expect(within(groups[0]).getByLabelText(/속성/)).toHaveValue('Iron')
    expect(within(groups[1]).getByLabelText(/속성/)).toHaveValue('Water')
  })

  it('전투 시간 기본값은 180초다', () => {
    renderPanel()
    const groups = screen.getAllByRole('group', { name: /전투/ })
    expect(within(groups[0]).getByLabelText(/전투 시간/)).toHaveValue(180)
  })

  it('15칸을 다 채우기 전에는 제출을 막는다', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
  })

  it('잠금 토글을 그리지 않는다', async () => {
    renderPanel()
    await screen.findByRole('button', { name: /u0 사용/i }) // palette rendered
    dropOnDeck(1, 'u0')
    expect(screen.getByRole('button', { name: '덱 1에서 U0 제거' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /고정/ })).not.toBeInTheDocument()
  })

  it('전투 수를 줄이면 뒤 전투의 보스 설정과 편성이 사라지고, 다시 늘리면 빈 값이 붙는다', async () => {
    const user = userEvent.setup()
    renderPanel()
    dropOnDeck(3, 'u10')
    expect(screen.getByRole('button', { name: '덱 3에서 U10 제거' })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('전투 수'), '1')
    expect(screen.getAllByRole('group', { name: /전투/ })).toHaveLength(1)

    await user.selectOptions(screen.getByLabelText('전투 수'), '3')
    expect(screen.getAllByRole('group', { name: /전투/ })).toHaveLength(3)
    // A fresh, empty battle 3 - shrinking and re-growing does not restore the
    // seat it lost.
    expect(screen.queryByRole('button', { name: '덱 3에서 U10 제거' })).not.toBeInTheDocument()
  })

  it('편성 15칸을 다 채우고 제출하면 전투마다 자기 몫의 보스와 5명을 evaluate-decks에 보낸다', async () => {
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0 },
        { deck: ['u5', 'u6', 'u7', 'u8', 'u9'], total_damage: 20, burst_damage: 12, normal_attack_damage: 8, skill_damage: 0 },
        { deck: ['u10', 'u11', 'u12', 'u13', 'u14'], total_damage: 30, burst_damage: 18, normal_attack_damage: 12, skill_damage: 0 },
      ],
      combined_total_damage: 60,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    renderPanel()
    const groups = screen.getAllByRole('group', { name: /전투/ })
    await user.selectOptions(within(groups[0]).getByLabelText(/속성/), 'Iron')
    await user.selectOptions(within(groups[1]).getByLabelText(/속성/), 'Water')
    await user.selectOptions(within(groups[2]).getByLabelText(/속성/), 'Wind')

    for (let deck = 0; deck < 3; deck += 1) {
      for (let seat = 0; seat < 5; seat += 1) {
        dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
      }
    }

    const submit = screen.getByRole('button', { name: /인카운터/ })
    expect(submit).toBeEnabled()
    await user.click(submit)

    expect(evaluateDecks).toHaveBeenCalledWith(
      {
        roster,
        decks: [
          {
            units: ['u0', 'u1', 'u2', 'u3', 'u4'],
            boss: expect.objectContaining({ element: 'Iron' }),
          },
          {
            units: ['u5', 'u6', 'u7', 'u8', 'u9'],
            boss: expect.objectContaining({ element: 'Water' }),
          },
          {
            units: ['u10', 'u11', 'u12', 'u13', 'u14'],
            boss: expect.objectContaining({ element: 'Wind' }),
          },
        ],
      },
      expect.any(AbortSignal),
    )
    expect(await screen.findByText('총합:', { exact: false })).toBeInTheDocument()
  })

  it('결과가 나온 뒤 보스 속성을 바꿔도 카드 표시는 제출 당시 속성 그대로다', async () => {
    // A result's damage was computed against the SUBMITTED boss. Reading the
    // live form field for its label instead would relabel a finished card out
    // from under numbers it wasn't scored against - the exact bug Task 10
    // shipped and had to fix for the evaluate mode this panel mirrors.
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0 },
      ],
      combined_total_damage: 10,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    renderPanel()
    await user.selectOptions(screen.getByLabelText('전투 수'), '1')
    for (const slug of ['u0', 'u1', 'u2', 'u3', 'u4']) dropOnDeck(1, slug)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(await screen.findByText('1번 덱 · 무속성')).toBeInTheDocument()

    const groups = screen.getAllByRole('group', { name: /전투/ })
    await user.selectOptions(within(groups[0]).getByLabelText(/속성/), 'Fire')

    expect(screen.getByText('1번 덱 · 무속성')).toBeInTheDocument()
    expect(screen.queryByText('1번 덱 · 작열')).not.toBeInTheDocument()
  })

  it('배치된 유닛을 제외하면 편성에서 빠지고, 다시 채워 제출하면 제출 로스터에도 포함되지 않는다', async () => {
    // "Exclude" must mean the same thing here as in the recommend tab's
    // palette: out of the deck AND out of the scored roster, not greyed out
    // while still seated and counted at full weight.
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u1', 'u2', 'u3', 'u4', 'u5'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0 },
      ],
      combined_total_damage: 10,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    renderPanel()
    await user.selectOptions(screen.getByLabelText('전투 수'), '1')
    await screen.findByRole('button', { name: /u0 사용/i }) // palette rendered
    for (const slug of ['u0', 'u1', 'u2', 'u3', 'u4']) dropOnDeck(1, slug)

    // Exclude the seated u0 - unseats it and greys it out.
    await user.click(screen.getByRole('button', { name: /u0 사용/i }))
    expect(screen.queryByRole('button', { name: '덱 1에서 U0 제거' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /u0 사용/i })).toHaveAttribute('aria-pressed', 'false')

    // Refill the emptied seat with a different unit so the deck is complete
    // again, then submit.
    dropOnDeck(1, 'u5')
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(evaluateDecks).toHaveBeenCalledWith(
      expect.objectContaining({
        roster: roster.filter((n) => n.character_slug !== 'u0'),
        decks: [{ units: ['u1', 'u2', 'u3', 'u4', 'u5'], boss: expect.anything() }],
      }),
      expect.any(AbortSignal),
    )
  })

  it('보스 필드가 하나라도 유효하지 않으면 15칸을 다 채워도 제출을 막는다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 사용/i }) // palette rendered
    for (let deck = 0; deck < 3; deck += 1) {
      for (let seat = 0; seat < 5; seat += 1) {
        dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
      }
    }
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeEnabled()

    const groups = screen.getAllByRole('group', { name: /전투/ })
    const fightDuration = within(groups[1]).getByLabelText(/전투 시간/)
    await user.clear(fightDuration)
    await user.type(fightDuration, '0')

    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
  })

  it('실행 버튼이 덱 컬럼 안에 있어 편성과 함께 화면에 남는다', async () => {
    renderPanel()

    expect(
      screen.getByRole('button', { name: /인카운터/ }).closest('.draft-layout__decks'),
    ).not.toBeNull()
  })
})
