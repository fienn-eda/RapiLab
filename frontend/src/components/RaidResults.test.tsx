import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RaidResults } from './RaidResults'
import type { DeckRecommendation } from '../types/recommend'
import { HELP } from '../lib/helpText'

describe('RaidResults', () => {
  it('shows an empty message when there are no decks', () => {
    render(<RaidResults decks={[]} combinedTotalDamage={0} />)
    expect(screen.getByText(HELP.results.emptyRaid)).toBeInTheDocument()
  })

  it('renders each deck in allocation order, labeled Deck N (not ranked)', () => {
    const decks: DeckRecommendation[] = [
      {
        deck: ['red-hood', 'liter', 'blanc', 'noir', 'anne'],
        total_damage: 5_000_000,
        burst_damage: 3_000_000,
        normal_attack_damage: 2_000_000,
        skill_damage: 0, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], seating: {},
      },
      {
        deck: ['mast', 'privaty', 'drake', 'grave', 'crown'],
        total_damage: 4_000_000,
        burst_damage: 2_500_000,
        normal_attack_damage: 1_500_000,
        skill_damage: 0, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], seating: {},
      },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={9_000_000} />)

    expect(screen.getByText('덱 1')).toBeInTheDocument()
    expect(screen.getByText('덱 2')).toBeInTheDocument()
    expect(screen.queryByText('#1')).not.toBeInTheDocument()
    expect(screen.getByText('5,000,000 총딜')).toBeInTheDocument()
  })

  it('shows the combined total prominently', () => {
    const decks: DeckRecommendation[] = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], seating: {} },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={100} />)
    expect(screen.getByText('100 딜')).toBeInTheDocument()
  })

  it('lists leftover slugs as bench when there are any', () => {
    const decks: DeckRecommendation[] = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], seating: {} },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={100} leftoverSlugs={['f', 'g']} />)
    expect(screen.getByText(HELP.results.bench('F, G'))).toBeInTheDocument()
  })

  it('renders no bench line when nothing is leftover', () => {
    const decks: DeckRecommendation[] = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], seating: {} },
    ]
    render(<RaidResults decks={decks} combinedTotalDamage={100} leftoverSlugs={[]} />)
    expect(screen.queryByText(/벤치/)).not.toBeInTheDocument()
  })

  // 위 DeckResults와 같은 이유로 여기서도 말하지 않는다.
  it('미지원 안내를 결과에 끼워 넣지 않는다', () => {
    render(<RaidResults decks={[]} combinedTotalDamage={0} />)
    expect(screen.queryByText(/미지원/)).not.toBeInTheDocument()
  })

  it('탐색이 잘렸을 때만 경고한다', () => {
    const decks: DeckRecommendation[] = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], seating: {} },
    ]
    const { rerender } = render(
      <RaidResults decks={decks} combinedTotalDamage={100} swapConverged={false} />,
    )
    expect(screen.getByText(HELP.results.swapCutoff)).toBeInTheDocument()

    rerender(<RaidResults decks={decks} combinedTotalDamage={100} swapConverged={true} />)
    expect(screen.queryByText(HELP.results.swapCutoff)).not.toBeInTheDocument()

    rerender(<RaidResults decks={decks} combinedTotalDamage={100} />)
    expect(screen.queryByText(HELP.results.swapCutoff)).not.toBeInTheDocument()
  })
})
