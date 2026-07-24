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
  it('groups owned-and-supported units under B1/B2/B3, excluding unowned', () => {
    render(<UnitPalette {...base} onPick={() => {}} usedSlugs={[]} />)
    expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /crown/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /anne/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /noir/i })).not.toBeInTheDocument()
  })

  it('renders a placed (used) unit as disabled for placement', () => {
    render(<UnitPalette {...base} onPick={() => {}} usedSlugs={['crown']} />)
    expect(screen.getByRole('button', { name: /crown/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /liter/i })).not.toBeDisabled()
  })

  it('calls onPick when a free, included unit is clicked (draft mode)', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    render(<UnitPalette {...base} onPick={onPick} usedSlugs={[]} />)
    await user.click(screen.getByRole('button', { name: /liter/i }))
    expect(onPick).toHaveBeenCalledWith('liter')
  })

  it('shows a checked Use checkbox per included unit; unchecked when excluded', () => {
    render(<UnitPalette {...base} excludedSlugs={['liter']} />)
    expect(screen.getByRole('checkbox', { name: /use crown/i })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /use liter/i })).not.toBeChecked()
  })

  it('calls onToggleExclude when a Use checkbox is toggled', async () => {
    const user = userEvent.setup()
    const onToggleExclude = vi.fn()
    render(<UnitPalette {...base} onToggleExclude={onToggleExclude} />)
    await user.click(screen.getByRole('checkbox', { name: /use crown/i }))
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })

  it('disables the place button for an excluded unit (draft mode)', () => {
    render(<UnitPalette {...base} onPick={() => {}} usedSlugs={[]} excludedSlugs={['blanc']} />)
    expect(screen.getByRole('button', { name: /blanc/i })).toBeDisabled()
  })

  it('renders no place button when onPick is omitted (single/raid mode)', () => {
    render(<UnitPalette {...base} />)
    expect(screen.queryByRole('button', { name: /crown/i })).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /use crown/i })).toBeInTheDocument()
  })

  // The Use checkbox asks "will you field this one?", which a portrait alone
  // cannot answer - so each unit carries the investment the answer turns on.
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
