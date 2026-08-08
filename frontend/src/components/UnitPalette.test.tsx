import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnitPalette } from './UnitPalette'
import type { SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'

vi.mock('../hooks/usePortraitManifest', () => ({
  usePortraitManifest: () => ({ portraitFor: () => null }),
}))

const UNITS: SupportedUnit[] = [
  { slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' },
  { slug: 'anne', name: 'Anne', burstTier: 1, element: 'Fire' },
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
  { slug: 'blanc', name: 'Blanc', burstTier: 3, element: 'Wind' },
  { slug: 'noir', name: 'Noir', burstTier: 3, element: 'Electric' },
]

const owned = (
  slug: string,
  investment: Partial<Pick<UserNikkeState, 'skill_levels' | 'overload_options'>> = {},
): UserNikkeState => ({
  character_slug: slug,
  level: 400,
  hp: 1,
  atk: 1,
  def_: 1,
  skill_levels: { skill1: 10, skill2: 10, burst: 10 },
  overload_options: [],
  ...investment,
})

const base = {
  roster: [owned('crown'), owned('liter'), owned('blanc')],
  supportedUnits: UNITS,
  excludedSlugs: [],
  onToggleExclude: () => {},
}

const renderPalette = (overrides: Partial<Parameters<typeof UnitPalette>[0]> = {}) =>
  render(<UnitPalette {...base} {...overrides} />)

describe('UnitPalette', () => {
  const unitButton = (name: RegExp) => screen.getByRole('button', { name })

  it('groups owned-and-supported units under B1/B2/B3, excluding unowned', () => {
    render(<UnitPalette {...base} draggable usedSlugs={[]} />)
    expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()
    expect(unitButton(/crown/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /anne/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /noir/i })).not.toBeInTheDocument()
  })

  // The chip is a portrait and its skill pips; the name, tier and element it
  // used to print are on the hover card, and the button carries the name for
  // anyone not looking at pixels.
  it('names each unit through its button rather than visible chip text', () => {
    render(<UnitPalette {...base} />)
    expect(unitButton(/crown 사용/i)).toBeInTheDocument()
    expect(unitButton(/liter 사용/i)).toBeInTheDocument()
    // Element renders as its Korean label in the chip's meta line, not the raw name.
    expect(screen.getByText(/B1 · 철갑/)).toBeInTheDocument()
  })

  it('reports pool membership as the pressed state of the portrait toggle', () => {
    render(<UnitPalette {...base} excludedSlugs={['liter']} />)
    expect(unitButton(/crown 사용/i)).toHaveAttribute('aria-pressed', 'true')
    expect(unitButton(/liter 사용/i)).toHaveAttribute('aria-pressed', 'false')
  })

  it('toggles a unit out of the pool when its portrait is clicked', async () => {
    const user = userEvent.setup()
    const onToggleExclude = vi.fn()
    render(<UnitPalette {...base} onToggleExclude={onToggleExclude} />)
    await user.click(unitButton(/crown 사용/i))
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })

  it('only lets an included, unseated unit be dragged in draft mode', () => {
    render(<UnitPalette {...base} draggable usedSlugs={['crown']} excludedSlugs={['blanc']} />)
    expect(unitButton(/liter 사용/i)).toHaveAttribute('draggable', 'true')
    // Already in a deck, so there is nothing left to seat.
    expect(unitButton(/crown 사용/i)).toHaveAttribute('draggable', 'false')
    // Out of the pool entirely.
    expect(unitButton(/blanc 사용/i)).toHaveAttribute('draggable', 'false')
  })

  it('drags nothing outside draft mode', () => {
    render(<UnitPalette {...base} />)
    expect(unitButton(/liter 사용/i)).toHaveAttribute('draggable', 'false')
  })

  // Clicking a portrait asks "will you field this one?", which the portrait
  // alone cannot answer - so skill levels sit on the chip, and the hover card
  // carries the unit's identity and what it rolled.
  it("shows each unit's skill levels and named overload rolls", () => {
    render(
      <UnitPalette
        {...base}
        roster={[
          owned('crown', {
            skill_levels: { skill1: 10, skill2: 4, burst: 7 },
            overload_options: [
              { name: '공격력 증가', value: 40.91 },
              { name: '우월코드 대미지 증가', value: 99.82 },
            ],
          }),
        ]}
      />,
    )
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    // Named and valued, never merely counted: "공 40.91%" and a revive chance
    // are both one line but not remotely the same decision. Names are
    // abbreviated to the forms used at the table.
    // Scoped to the overload line itself: the filter toolbar's sort <select>
    // offers the same abbreviations as option text.
    expect(screen.getByText('공', { selector: '.overload__name' })).toBeInTheDocument()
    expect(screen.getByText('40.91%')).toBeInTheDocument()
    expect(screen.getByText('우코', { selector: '.overload__name' })).toBeInTheDocument()
    expect(screen.getByText('99.82%')).toBeInTheDocument()
  })

  it('says so when a unit rolled no overload at all', () => {
    render(<UnitPalette {...base} roster={[owned('crown')]} />)
    expect(screen.getByText('오버로드 없음')).toBeInTheDocument()
  })

  // Five rows top to bottom - breakthrough, core, S1, S2, B - so the column
  // lines up across every chip in the grid.
  describe('the stat column beside the portrait', () => {
    const chip = (investment: { grade?: number; core?: number }) =>
      render(
        <UnitPalette
          {...base}
          roster={[owned('crown', { skill_levels: { skill1: 10, skill2: 4, burst: 7 } })]}
          investmentFor={() => investment}
        />,
      )

    it('leads with breakthrough and core, then the three skill levels', () => {
      const { container } = chip({ grade: 2, core: 4 })
      const cells = [...container.querySelectorAll('.palette__stats > li')]
      expect(cells.map((cell) => cell.textContent)).toEqual([
        '★★☆',
        '+4',
        'S110',
        'S24',
        'B7',
      ])
    })

    it('keeps breakthrough and core in cells of their own', () => {
      const { container } = chip({ grade: 3, core: 2 })
      expect(container.querySelectorAll('.palette__stat--grade')).toHaveLength(1)
      expect(container.querySelectorAll('.palette__stat--core')).toHaveLength(1)
    })

    // A dash, not "+0" or an empty cell: the row still has to hold its place
    // in the column, and there is nothing to report in it.
    it('dashes an uncored unit rather than claiming a zero', () => {
      const { container } = chip({ grade: 3, core: 0 })
      expect(container.querySelector('.palette__stat--core')).toHaveTextContent('—')
    })

    it('dashes breakthrough when the unit carries no grade at all', () => {
      const { container } = chip({})
      expect(container.querySelector('.palette__stat--grade')).toHaveTextContent('—')
    })
  })

  describe('the filter toolbar', () => {
    const filtered = () =>
      render(
        <UnitPalette
          {...base}
          roster={[
            owned('crown', { overload_options: [{ name: '공격력 증가', value: 10 }] }),
            owned('liter', { overload_options: [{ name: '공격력 증가', value: 50 }] }),
            owned('blanc'),
          ]}
        />,
      )

    it('hides the units a name search does not match', async () => {
      const user = userEvent.setup()
      filtered()
      await user.type(screen.getByLabelText('이름 검색'), 'cro')
      expect(unitButton(/crown 사용/i)).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /liter 사용/i })).not.toBeInTheDocument()
    })

    it('drops a burst heading once its last unit is filtered away', async () => {
      const user = userEvent.setup()
      filtered()
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B2' })).not.toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B3' })).not.toBeInTheDocument()
    })

    // Sorting reorders inside each burst group; it never merges them, because
    // a deck is always built tier by tier.
    it('sorts within a burst group without dissolving the groups', async () => {
      const user = userEvent.setup()
      render(
        <UnitPalette
          {...base}
          roster={[
            owned('crown', { overload_options: [{ name: '공격력 증가', value: 10 }] }),
            owned('anne', { overload_options: [{ name: '공격력 증가', value: 90 }] }),
            owned('liter'),
          ]}
        />,
      )
      await user.selectOptions(screen.getByLabelText('정렬'), '공')
      await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')

      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
      const b1 = screen.getByRole('heading', { name: 'B1' }).closest('section')!
      const names = [...b1.querySelectorAll('.palette__name')].map((n) => n.textContent)
      expect(names).toEqual(['Anne', 'Crown'])
    })

    // The load-bearing invariant: the filter narrows the view, and the pool is
    // a separate decision the user made per unit.
    it('keeps a hidden unit excluded, and hands it back on clearing the filter', async () => {
      const user = userEvent.setup()
      render(<UnitPalette {...base} excludedSlugs={['liter']} />)
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.queryByRole('button', { name: /liter 사용/i })).not.toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: '필터 해제' }))
      expect(unitButton(/liter 사용/i)).toHaveAttribute('aria-pressed', 'false')
    })

    it('counts against the units it draws, not the whole roster', async () => {
      const user = userEvent.setup()
      filtered()
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.getByText('3기 중 1기 표시 중')).toBeInTheDocument()
    })

    // A bordered toolbar with nothing to filter reads as a bug, not a feature.
    it('does not draw the filter toolbar when the roster owns no supported unit', () => {
      render(<UnitPalette {...base} roster={[]} />)
      expect(screen.queryByLabelText('이름 검색')).not.toBeInTheDocument()
    })
  })
})

describe('without onToggleExclude', () => {
  it('draws the chip as a plain drag source rather than a toggle', () => {
    // 이 화면(미란다 계산기)에는 탐색이 없어 후보 풀이라는 개념이 없다.
    // 켤 수는 있는데 아무 일도 안 일어나는 컨트롤을 남기지 않는다.
    renderPalette({ onToggleExclude: undefined, excludedSlugs: undefined })
    const chip = screen.getByRole('button', { name: 'Crown' })
    expect(chip).not.toHaveAttribute('aria-pressed')
  })

  it('still toggles when the handler is given', () => {
    const onToggleExclude = vi.fn()
    renderPalette({ onToggleExclude })
    const chip = screen.getByRole('button', { name: /Crown 사용/ })
    expect(chip).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(chip)
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })
})
