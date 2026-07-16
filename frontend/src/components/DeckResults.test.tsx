import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DeckResults } from './DeckResults'
import type { DeckRecommendation } from '../types/recommend'

describe('DeckResults', () => {
  it('shows an empty message when there are no decks', () => {
    render(<DeckResults decks={[]} />)
    expect(screen.getByText('No decks recommended yet.')).toBeInTheDocument()
  })

  it('renders each deck ranked, with its slugs in order and a damage breakdown', () => {
    const decks: DeckRecommendation[] = [
      {
        deck: ['red-hood', 'liter', 'blanc', 'noir', 'anne'],
        total_damage: 5_000_000,
        burst_damage: 3_000_000,
        normal_attack_damage: 2_000_000,
      },
      {
        deck: ['mast', 'privaty', 'drake', 'grave', 'crown'],
        total_damage: 4_000_000,
        burst_damage: 2_500_000,
        normal_attack_damage: 1_500_000,
      },
    ]
    render(<DeckResults decks={decks} />)

    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('5,000,000 total dmg')).toBeInTheDocument()
    expect(screen.getByText('Burst: 3,000,000')).toBeInTheDocument()
    expect(screen.getByText('Normal: 2,000,000')).toBeInTheDocument()

    const firstDeckSlugs = screen.getAllByText(/red-hood|liter|blanc|noir|anne/)
    expect(firstDeckSlugs).toHaveLength(5)
    expect(firstDeckSlugs.map((el) => el.textContent)).toEqual([
      'red-hood',
      'liter',
      'blanc',
      'noir',
      'anne',
    ])
  })
})
