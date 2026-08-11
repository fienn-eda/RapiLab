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

  // 미지원 슬러그는 결과 화면에서 말하지 않는다 - 니케 풀 탭이 이미 같은
  // 사실을 말하고, 여기서는 매번 뜨는 배경 소음이었다(Fienn, 2026-08-11).
  it('미지원 안내를 결과에 끼워 넣지 않는다', () => {
    render(<DeckResults decks={[]} />)
    expect(screen.queryByText(/미지원/)).not.toBeInTheDocument()
  })
})
