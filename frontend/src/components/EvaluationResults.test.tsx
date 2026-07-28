import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvaluationResults } from './EvaluationResults'

const DECKS = [
  { deck: ['liter', 'blanc', 'crown', 'modernia', 'privaty'],
    total_damage: 100, burst_damage: 60, normal_attack_damage: 30, skill_damage: 10 },
  { deck: ['rouge', 'volume', 'mint', 'grave', 'noir'],
    total_damage: 50, burst_damage: 30, normal_attack_damage: 15, skill_damage: 5 },
]

const renderResults = (overrides = {}) =>
  render(<EvaluationResults
    decks={DECKS}
    combinedTotalDamage={150}
    excludedSlugs={[]}
    bossElements={['Iron', 'Water']}
    nameFor={(slug) => slug}
    {...overrides} />)

describe('EvaluationResults', () => {
  it('덱마다 카드를 그리고 합계를 보여준다', () => {
    renderResults()
    // The composed label ("N번 덱 · 속성") is this component's own output,
    // not DeckCard's internal markup — counting matches of it proves one
    // card per deck without coupling to a CSS class this component doesn't own.
    expect(screen.getAllByText(/\d번 덱 · /)).toHaveLength(2)
    expect(screen.getByText(/150/)).toBeTruthy()
  })

  it('덱마다 자기 보스 속성을 표시한다 (자리와 짝이 맞다)', () => {
    // Exact composed text, not a substring match, so this fails if the
    // element/deck pairing is transposed, reversed, or off-by-one.
    renderResults()
    expect(screen.getByText('1번 덱 · 철갑')).toBeTruthy()
    expect(screen.getByText('2번 덱 · 수냉')).toBeTruthy()
  })

  it('엔진이 고른 순서를 안내한다', () => {
    renderResults()
    expect(screen.getByText(/순서/)).toBeTruthy()
  })

  it('지원하지 않는 슬러그가 있으면 알려준다', () => {
    // ExcludedSlugsNote humanizes the slug (nameFromSlug), the same as
    // RaidResults.test.tsx's "Some Slug" expectation for "some-slug" — so the
    // rendered text is "Not A Nikke", not the raw slug.
    renderResults({ excludedSlugs: ['not-a-nikke'] })
    expect(screen.getByText(/Not A Nikke/)).toBeTruthy()
  })
})
