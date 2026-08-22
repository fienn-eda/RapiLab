import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DraftResults, matchDecksToSubmitted } from './DraftResults'
import type { DraftAllocation, RaidDeck } from '../types/recommend'
import type { Draft } from '../types/draft'
import { HELP } from '../lib/helpText'

const recommendedDecks: RaidDeck[] = [
  {
    deck: ['a', 'b', 'c', 'd', 'z'],
    total_damage: 130,
    burst_damage: 80,
    normal_attack_damage: 50,
    skill_damage: 0, hold_burst_slugs: [], hold_fire_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {},
    pinned_slugs: ['a'],
  },
]

const withinDraft: DraftAllocation = {
  decks: [
    { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 110, burst_damage: 70, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [], hold_fire_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {}, pinned_slugs: [] },
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
    expect(screen.getByText('내 드래프트')).toBeInTheDocument()
    expect(screen.getByText('100 딜')).toBeInTheDocument()

    // Tier 2: best within the drafted units only (+delta1 = 10)
    expect(screen.getByText(/드래프트 내 최선/)).toHaveTextContent('+10')
    expect(screen.getByText('110 딜')).toBeInTheDocument()

    // Tier 3: bench-inclusive recommendation (+delta2 = 20)
    expect(screen.getByText(/추천\s*\(/)).toHaveTextContent('+20')
    expect(screen.getByText('130 딜')).toBeInTheDocument()

    // Per-deck diff vs the submitted draft: recommended swapped 'e' for 'z'
    expect(screen.getByText(/\+ Z/)).toBeInTheDocument()
    expect(screen.getByText(/- E/)).toBeInTheDocument()

    // pinned_slugs badge on the recommended tier
    expect(screen.getByText('고정됨')).toBeInTheDocument()
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

    expect(screen.queryByText('내 드래프트')).not.toBeInTheDocument()
    expect(screen.queryByText(/드래프트 내 최선/)).not.toBeInTheDocument()
    expect(screen.getByText('덱 1')).toBeInTheDocument()
    expect(screen.getByText('130 딜')).toBeInTheDocument()
    expect(screen.getByText(HELP.results.bench('Bench Unit'))).toBeInTheDocument()
  })

  // The backend's recommended tier can come from a from-scratch pass whose
  // deck order has nothing to do with the submitted draft's deck order
  // (recommend_from_draft picks _better(scratch, warm); scratch's decks
  // aren't seeded in draft order at all). The diff MUST match by slug
  // overlap, not array index, or a mere relabeling reads as "everyone swapped".
  const twoDeckSubmittedDraft: Draft = {
    decks: [
      ['a', 'b', 'c', 'd', 'e'].map((slug) => ({ slug, locked: false })),
      ['f', 'g', 'h', 'i', 'j'].map((slug) => ({ slug, locked: false })),
    ],
  }

  it('shows an empty per-deck diff when the result is a permutation of the submitted decks (content-matched, not index-matched)', () => {
    const permutedRecommended: RaidDeck[] = [
      { deck: ['f', 'g', 'h', 'i', 'j'], total_damage: 60, burst_damage: 40, normal_attack_damage: 20, skill_damage: 0, hold_burst_slugs: [], hold_fire_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {}, pinned_slugs: [] },
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 70, burst_damage: 45, normal_attack_damage: 25, skill_damage: 0, hold_burst_slugs: [], hold_fire_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {}, pinned_slugs: [] },
    ]
    render(
      <DraftResults
        decks={permutedRecommended}
        combinedTotalDamage={130}
        withinDraft={{ decks: permutedRecommended, combined_total_damage: 130, leftover_slugs: [] }}
        baselineTotalDamage={120}
        submittedDraft={twoDeckSubmittedDraft}
      />,
    )
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^-/)).not.toBeInTheDocument()
  })

  it('shows exactly one add/remove pair when a permuted result has one real unit swap', () => {
    const permutedWithOneSwap: RaidDeck[] = [
      { deck: ['f', 'g', 'h', 'i', 'j'], total_damage: 60, burst_damage: 40, normal_attack_damage: 20, skill_damage: 0, hold_burst_slugs: [], hold_fire_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {}, pinned_slugs: [] },
      { deck: ['a', 'b', 'c', 'd', 'z'], total_damage: 70, burst_damage: 45, normal_attack_damage: 25, skill_damage: 0, hold_burst_slugs: [], hold_fire_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {}, pinned_slugs: [] },
    ]
    render(
      <DraftResults
        decks={permutedWithOneSwap}
        combinedTotalDamage={130}
        withinDraft={{ decks: permutedWithOneSwap, combined_total_damage: 130, leftover_slugs: [] }}
        baselineTotalDamage={120}
        submittedDraft={twoDeckSubmittedDraft}
      />,
    )
    // Only the swapped deck's diff appears, and only for the swapped unit.
    const added = screen.getAllByText(/^\+/)
    const removed = screen.getAllByText(/^-/)
    expect(added).toHaveLength(2) // one in the within-draft tier, one in the recommended tier
    expect(removed).toHaveLength(2)
    added.forEach((el) => expect(el).toHaveTextContent('+ Z'))
    removed.forEach((el) => expect(el).toHaveTextContent('- E'))
  })

  it('shows no diff when a drafted character comes back as the mode the engine chose', () => {
    // The player drafts `bready`; the engine settles on `bready-lingering`. Raw
    // slug comparison reads that as "dropped one unit, added another" - and the
    // deck matching, which pairs by slug overlap, could also fail to pair the
    // deck at all. Both compare through ownedSlugFor instead.
    const ownedSlugFor = (slug: string) =>
      slug.startsWith('bready') ? 'bready' : slug
    const resolvedDecks: RaidDeck[] = [
      { deck: ['bready-lingering', 'b', 'c', 'd', 'e'], total_damage: 70, burst_damage: 45, normal_attack_damage: 25, skill_damage: 0, hold_burst_slugs: [], hold_fire_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {}, pinned_slugs: ['bready-lingering'] },
    ]
    const drafted: Draft = {
      decks: [
        [
          { slug: 'bready', locked: true },
          { slug: 'b', locked: false },
          { slug: 'c', locked: false },
          { slug: 'd', locked: false },
          { slug: 'e', locked: false },
        ],
      ],
    }
    render(
      <DraftResults
        decks={resolvedDecks}
        combinedTotalDamage={70}
        withinDraft={{ decks: resolvedDecks, combined_total_damage: 70, leftover_slugs: [] }}
        baselineTotalDamage={65}
        submittedDraft={drafted}
        ownedSlugFor={ownedSlugFor}
      />,
    )
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^-/)).not.toBeInTheDocument()
  })

  it('탐색이 잘렸을 때만 경고한다 (complete-draft, three-tier branch)', () => {
    const { rerender } = render(
      <DraftResults
        decks={recommendedDecks}
        combinedTotalDamage={130}
        withinDraft={withinDraft}
        baselineTotalDamage={100}
        submittedDraft={submittedDraft}
        swapConverged={false}
      />,
    )
    expect(screen.getByText(HELP.results.swapCutoff)).toBeInTheDocument()

    rerender(
      <DraftResults
        decks={recommendedDecks}
        combinedTotalDamage={130}
        withinDraft={withinDraft}
        baselineTotalDamage={100}
        submittedDraft={submittedDraft}
        swapConverged={true}
      />,
    )
    expect(screen.queryByText(HELP.results.swapCutoff)).not.toBeInTheDocument()

    rerender(
      <DraftResults
        decks={recommendedDecks}
        combinedTotalDamage={130}
        withinDraft={withinDraft}
        baselineTotalDamage={100}
        submittedDraft={submittedDraft}
      />,
    )
    expect(screen.queryByText(HELP.results.swapCutoff)).not.toBeInTheDocument()
  })
})

describe('matchDecksToSubmitted', () => {
  it('matches by greatest slug overlap, not by index', () => {
    const resultDecks = [{ deck: ['f', 'g', 'h', 'i', 'j'] }, { deck: ['a', 'b', 'c', 'd', 'z'] }]
    const submittedDecks = [
      ['a', 'b', 'c', 'd', 'e'].map((slug) => ({ slug, locked: false })),
      ['f', 'g', 'h', 'i', 'j'].map((slug) => ({ slug, locked: false })),
    ]
    const matches = matchDecksToSubmitted(resultDecks, submittedDecks)
    expect(matches[0]).toBe(submittedDecks[1]) // result[0] overlaps deck 1 (f,g,h,i,j) fully
    expect(matches[1]).toBe(submittedDecks[0]) // result[1] overlaps deck 0 (a,b,c,d,e) 4/5
  })

  it('breaks ties by lowest submitted-deck index', () => {
    const resultDecks = [{ deck: ['x', 'y', 'z', 'w', 'v'] }]
    const submittedDecks = [
      [{ slug: 'x', locked: false }],
      [{ slug: 'x', locked: false }],
    ]
    const matches = matchDecksToSubmitted(resultDecks, submittedDecks)
    expect(matches[0]).toBe(submittedDecks[0])
  })

  it('never matches the same submitted deck to two result decks', () => {
    const resultDecks = [{ deck: ['a'] }, { deck: ['a', 'b'] }]
    const submittedDecks = [[{ slug: 'a', locked: false }, { slug: 'b', locked: false }]]
    const matches = matchDecksToSubmitted(resultDecks, submittedDecks)
    // Only one result deck can claim the single submitted deck; the other gets undefined.
    expect(matches.filter((m) => m === submittedDecks[0])).toHaveLength(1)
  })
})
