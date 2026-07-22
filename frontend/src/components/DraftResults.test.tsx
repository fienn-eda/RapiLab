import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DraftResults } from './DraftResults'
import type { DraftAllocation, RaidDeck } from '../types/recommend'
import type { Draft } from '../types/draft'

const recommendedDecks: RaidDeck[] = [
  {
    deck: ['a', 'b', 'c', 'd', 'z'],
    total_damage: 130,
    burst_damage: 80,
    normal_attack_damage: 50,
    pinned_slugs: ['a'],
  },
]

const withinDraft: DraftAllocation = {
  decks: [
    { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 110, burst_damage: 70, normal_attack_damage: 40, pinned_slugs: [] },
  ],
  combined_total_damage: 110,
  leftover_slugs: [],
}

const submittedDraft: Draft = {
  decks: [
    ['a', 'b', 'c', 'd', 'e'].map((slug) => ({ slug, locked: slug === 'a' })),
  ],
}

describe('DraftResults', () => {
  it('renders the three ascending tiers, a per-deck diff, and pinned badges for a complete draft', () => {
    render(
      <DraftResults
        decks={recommendedDecks}
        combinedTotalDamage={130}
        withinDraft={withinDraft}
        baselineTotalDamage={100}
        submittedDraft={submittedDraft}
      />,
    )

    // Tier 1: baseline (the submitted draft, scored as-is)
    expect(screen.getByText('Your draft')).toBeInTheDocument()
    expect(screen.getByText('100 dmg')).toBeInTheDocument()

    // Tier 2: best within the drafted units only (+delta1 = 10)
    expect(screen.getByText(/Best within your draft/)).toHaveTextContent('+10')
    expect(screen.getByText('110 dmg')).toBeInTheDocument()

    // Tier 3: bench-inclusive recommendation (+delta2 = 20)
    expect(screen.getByText(/Recommended/)).toHaveTextContent('+20')
    expect(screen.getByText('130 dmg')).toBeInTheDocument()

    // Per-deck diff vs the submitted draft: recommended swapped 'e' for 'z'
    expect(screen.getByText(/\+ z/)).toBeInTheDocument()
    expect(screen.getByText(/- e/)).toBeInTheDocument()

    // pinned_slugs badge on the recommended tier
    expect(screen.getByText('pinned')).toBeInTheDocument()
  })

  it('renders the single recommended allocation when within_draft/baseline_total_damage are null', () => {
    render(
      <DraftResults
        decks={recommendedDecks}
        combinedTotalDamage={130}
        withinDraft={null}
        baselineTotalDamage={null}
        leftoverSlugs={['bench-unit']}
      />,
    )

    expect(screen.queryByText('Your draft')).not.toBeInTheDocument()
    expect(screen.queryByText(/Best within your draft/)).not.toBeInTheDocument()
    expect(screen.getByText('Deck 1')).toBeInTheDocument()
    expect(screen.getByText('130 dmg')).toBeInTheDocument()
    expect(screen.getByText('Bench (not allocated to a deck): bench-unit')).toBeInTheDocument()
  })
})
