import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnitPalette } from './UnitPalette'
import type { SupportedUnit } from '../types/supportedUnit'

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

const base = {
  ownedSlugs: ['crown', 'liter', 'blanc'],
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
})
