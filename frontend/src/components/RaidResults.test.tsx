import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RaidResults } from './RaidResults'
import type { DeckRecommendation } from '../types/recommend'

describe('RaidResults', () => {
  it('shows an empty message when there are no decks', () => {
    render(<RaidResults decks={[]} combinedTotalDamage={0} />)
    expect(screen.getByText('No raid decks allocated yet.')).toBeInTheDocument()
  })

  it('renders each deck in allocation order, labeled Deck N (not ranked)', () => {
    const decks: DeckRecommendation[] = [
      {
        deck: ['red-hood', 'liter', 'blanc', 'noir', 'anne'],
        total_damage: 5_000_000,
        burst_damage: 3_000_000,
        normal_attack_damage: 2_000_000,
        skill_damage: 0,
      },
      {
        deck: ['mast', 'privaty', 'drake', 'grave', 'crown'],
        total_damage: 4_000_000,
        burst_damage: 2_500_000,
        normal_attack_damage: 1_500_000,
        skill_damage: 0,
      },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={9_000_000} />)

    expect(screen.getByText('Deck 1')).toBeInTheDocument()
    expect(screen.getByText('Deck 2')).toBeInTheDocument()
    expect(screen.queryByText('#1')).not.toBeInTheDocument()
    expect(screen.getByText('5,000,000 total dmg')).toBeInTheDocument()
    expect(screen.getByText('Burst: 3,000,000')).toBeInTheDocument()
    expect(screen.getByText('Normal: 2,000,000')).toBeInTheDocument()
  })

  it('shows the combined total prominently', () => {
    const decks: DeckRecommendation[] = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0 },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={100} />)
    expect(screen.getByText('100 dmg')).toBeInTheDocument()
  })

  it('lists leftover slugs as bench when there are any', () => {
    const decks: DeckRecommendation[] = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0 },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={100} leftoverSlugs={['f', 'g']} />)
    expect(screen.getByText('Bench (not allocated to a deck): F, G')).toBeInTheDocument()
  })

  it('renders no bench line when nothing is leftover', () => {
    const decks: DeckRecommendation[] = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0 },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={100} leftoverSlugs={[]} />)
    expect(screen.queryByText(/Bench/)).not.toBeInTheDocument()
  })

  it('lists excluded slugs as not yet supported when there are any', () => {
    render(<RaidResults decks={[]} combinedTotalDamage={0} excludedSlugs={['some-slug']} />)
    expect(
      screen.getByText('Not yet supported (excluded from search): Some Slug'),
    ).toBeInTheDocument()
  })
})
