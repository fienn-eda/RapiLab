import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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
    expect(unitButton(/use crown/i)).toBeInTheDocument()
    expect(unitButton(/use liter/i)).toBeInTheDocument()
  })

  it('reports pool membership as the pressed state of the portrait toggle', () => {
    render(<UnitPalette {...base} excludedSlugs={['liter']} />)
    expect(unitButton(/use crown/i)).toHaveAttribute('aria-pressed', 'true')
    expect(unitButton(/use liter/i)).toHaveAttribute('aria-pressed', 'false')
  })

  it('toggles a unit out of the pool when its portrait is clicked', async () => {
    const user = userEvent.setup()
    const onToggleExclude = vi.fn()
    render(<UnitPalette {...base} onToggleExclude={onToggleExclude} />)
    await user.click(unitButton(/use crown/i))
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })

  it('only lets an included, unseated unit be dragged in draft mode', () => {
    render(<UnitPalette {...base} draggable usedSlugs={['crown']} excludedSlugs={['blanc']} />)
    expect(unitButton(/use liter/i)).toHaveAttribute('draggable', 'true')
    // Already in a deck, so there is nothing left to seat.
    expect(unitButton(/use crown/i)).toHaveAttribute('draggable', 'false')
    // Out of the pool entirely.
    expect(unitButton(/use blanc/i)).toHaveAttribute('draggable', 'false')
  })

  it('drags nothing outside draft mode', () => {
    render(<UnitPalette {...base} />)
    expect(unitButton(/use liter/i)).toHaveAttribute('draggable', 'false')
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
    expect(screen.getByText('공')).toBeInTheDocument()
    expect(screen.getByText('40.91%')).toBeInTheDocument()
    expect(screen.getByText('우코')).toBeInTheDocument()
    expect(screen.getByText('99.82%')).toBeInTheDocument()
  })

  it('says so when a unit rolled no overload at all', () => {
    render(<UnitPalette {...base} roster={[owned('crown')]} />)
    expect(screen.getByText('No overload')).toBeInTheDocument()
  })
})
