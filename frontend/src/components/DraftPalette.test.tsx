import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DraftPalette } from './DraftPalette'
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

describe('DraftPalette', () => {
  it('groups owned-and-supported units under their B1/B2/B3 headers, excluding unowned units', () => {
    render(
      <DraftPalette
        ownedSlugs={['crown', 'liter', 'blanc']}
        supportedUnits={UNITS}
        usedSlugs={[]}
        onPick={() => {}}
      />,
    )

    expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()

    expect(screen.getByRole('button', { name: /crown/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /liter/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /blanc/i })).toBeInTheDocument()
    // owned but not supported, and supported but not owned -> excluded
    expect(screen.queryByRole('button', { name: /anne/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /noir/i })).not.toBeInTheDocument()
  })

  it('omits a tier header when no owned-and-supported unit falls in it', () => {
    render(
      <DraftPalette
        ownedSlugs={['crown']}
        supportedUnits={UNITS}
        usedSlugs={[]}
        onPick={() => {}}
      />,
    )
    expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'B2' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'B3' })).not.toBeInTheDocument()
  })

  it('renders an already-placed (used) unit as disabled', () => {
    render(
      <DraftPalette
        ownedSlugs={['crown', 'liter']}
        supportedUnits={UNITS}
        usedSlugs={['crown']}
        onPick={() => {}}
      />,
    )
    expect(screen.getByRole('button', { name: /crown/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /liter/i })).not.toBeDisabled()
  })

  it('calls onPick with the slug when a free unit is clicked', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    render(
      <DraftPalette
        ownedSlugs={['liter']}
        supportedUnits={UNITS}
        usedSlugs={[]}
        onPick={onPick}
      />,
    )
    await user.click(screen.getByRole('button', { name: /liter/i }))
    expect(onPick).toHaveBeenCalledWith('liter')
  })

  it('does not call onPick when a used unit is clicked', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    render(
      <DraftPalette
        ownedSlugs={['crown']}
        supportedUnits={UNITS}
        usedSlugs={['crown']}
        onPick={onPick}
      />,
    )
    await user.click(screen.getByRole('button', { name: /crown/i }))
    expect(onPick).not.toHaveBeenCalled()
  })
})
