import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DeckResults } from './DeckResults'
import type { DeckRecommendation } from '../types/recommend'
import { HELP } from '../lib/helpText'

describe('DeckResults', () => {
  it('shows an empty message when there are no decks', () => {
    render(<DeckResults decks={[]} />)
    expect(screen.getByText(HELP.results.emptyDecks)).toBeInTheDocument()
  })

  it('renders each deck ranked, with its units in order and its total damage', () => {
    const decks: DeckRecommendation[] = [
      {
        deck: ['red-hood', 'liter', 'blanc', 'noir', 'anne'],
        total_damage: 5_000_000,
        burst_damage: 3_000_000,
        normal_attack_damage: 1_200_000,
        skill_damage: 800_000, hold_burst_slugs: [],
      },
      {
        deck: ['mast', 'privaty', 'drake', 'grave', 'crown'],
        total_damage: 4_000_000,
        burst_damage: 2_500_000,
        normal_attack_damage: 1_500_000,
        skill_damage: 0, hold_burst_slugs: [],
      },
    ]
    render(<DeckResults decks={decks} />)

    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('5,000,000 총딜')).toBeInTheDocument()
    // The per-source split rides along on the response but is deliberately
    // not drawn - the card answers "what is this deck worth", nothing else.
    expect(screen.queryByText(/^(버스트|평타|스킬):/)).not.toBeInTheDocument()

    // Names, not slugs: a deck is only a recommendation once you can tell
    // who is in it.
    const firstDeckUnits = screen.getAllByText(/Red Hood|Liter|Blanc|Noir|Anne/)
    expect(firstDeckUnits.map((el) => el.textContent)).toEqual([
      'Red Hood',
      'Liter',
      'Blanc',
      'Noir',
      'Anne',
    ])
  })

  it('lists excluded slugs as not yet supported when there are any', () => {
    render(<DeckResults decks={[]} excludedSlugs={['some-slug', 'other-slug']} />)
    expect(
      screen.getByText(HELP.results.excludedUnsupported('Some Slug, Other Slug')),
    ).toBeInTheDocument()
  })

  it('renders no excluded line when nothing was excluded', () => {
    render(<DeckResults decks={[]} excludedSlugs={[]} />)
    expect(screen.queryByText(/아직 미지원/)).not.toBeInTheDocument()
  })
})
