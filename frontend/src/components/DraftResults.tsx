// Draft-based raid results (frontend/README.md "Draft-based raid
// recommendation" / "UI scope — draft editor"). For a COMPLETE draft (the
// backend returns non-null within_draft/baseline_total_damage), renders the
// three ascending tiers the monotone guarantee promises:
//   your draft (baseline) <= best within your draft (+delta1) <= recommended,
//   bench-inclusive (+delta2)
// with a per-deck diff against the submitted draft and pinned_slugs badges
// on the recommended tier. Otherwise (no draft, or a partial one) falls back
// to the plain RaidResults/DeckCard view — same shape /api/recommend-raid
// always returned before drafts existed.

import type { Draft, DraftSeat } from '../types/draft'
import type { DraftAllocation, RaidDeck } from '../types/recommend'
import { DeckCard } from './DeckCard'
import { ExcludedSlugsNote } from './ExcludedSlugsNote'
import { formatDamage } from './formatDamage'
import { RaidResults } from './RaidResults'

interface DraftResultsProps {
  decks: RaidDeck[]
  combinedTotalDamage: number
  excludedSlugs?: string[]
  leftoverSlugs?: string[]
  withinDraft?: DraftAllocation | null
  baselineTotalDamage?: number | null
  /** The draft as submitted, for the per-deck diff. Diffs are omitted without it. */
  submittedDraft?: Draft
}

const diffAgainstSubmitted = (
  recommendedSlugs: string[],
  submitted?: DraftSeat[],
): { added: string[]; removed: string[] } => {
  if (!submitted) return { added: [], removed: [] }
  const submittedSlugs = submitted.map((seat) => seat.slug)
  return {
    added: recommendedSlugs.filter((slug) => !submittedSlugs.includes(slug)),
    removed: submittedSlugs.filter((slug) => !recommendedSlugs.includes(slug)),
  }
}

/** Pairs each result deck with the submitted-draft deck it overlaps most.
 * Deck INDEX alignment between a recommend_from_draft result and the
 * submitted draft is not guaranteed: recommended/within_draft can come from
 * either the warm-start pass (seeded in submitted order) or a from-scratch
 * pass (backend/app/deck_allocation.py's `_better(scratch, warm)`), whose
 * deck order has no relation to the submitted draft at all. Matching by
 * slug overlap instead means a mere relabeling (same groupings, different
 * deck slots) diffs as empty, and only a genuine swap shows up. Greedy:
 * each result deck (in order) claims the highest-overlap still-unclaimed
 * submitted deck; ties go to the lowest submitted-deck index. */
export const matchDecksToSubmitted = (
  resultDecks: { deck: string[] }[],
  submittedDecks: DraftSeat[][],
): (DraftSeat[] | undefined)[] => {
  const claimed = new Set<number>()
  return resultDecks.map((resultDeck) => {
    const resultSlugs = new Set(resultDeck.deck)
    let bestIndex = -1
    let bestOverlap = -1
    submittedDecks.forEach((seats, index) => {
      if (claimed.has(index)) return
      const overlap = seats.filter((seat) => resultSlugs.has(seat.slug)).length
      if (overlap > bestOverlap) {
        bestOverlap = overlap
        bestIndex = index
      }
    })
    if (bestIndex === -1) return undefined
    claimed.add(bestIndex)
    return submittedDecks[bestIndex]
  })
}

export function DraftResults({
  decks,
  combinedTotalDamage,
  excludedSlugs = [],
  leftoverSlugs = [],
  withinDraft = null,
  baselineTotalDamage = null,
  submittedDraft,
}: DraftResultsProps) {
  if (withinDraft == null || baselineTotalDamage == null) {
    return (
      <RaidResults
        decks={decks}
        combinedTotalDamage={combinedTotalDamage}
        excludedSlugs={excludedSlugs}
        leftoverSlugs={leftoverSlugs}
      />
    )
  }

  const delta1 = withinDraft.combined_total_damage - baselineTotalDamage
  const delta2 = combinedTotalDamage - withinDraft.combined_total_damage

  const submittedDecks = submittedDraft?.decks ?? []
  const withinDraftMatches = matchDecksToSubmitted(withinDraft.decks, submittedDecks)
  const recommendedMatches = matchDecksToSubmitted(decks, submittedDecks)

  return (
    <div className="draft-results">
      <p className="raid-results__note">
        Three ascending tiers: your submitted draft, the best allocation using
        only your drafted units, and the bench-inclusive recommendation.
      </p>

      <section className="draft-results__tier" aria-label="Your draft">
        <h3 className="draft-results__tier-title">Your draft</h3>
        <p className="draft-results__tier-total">{formatDamage(baselineTotalDamage)} dmg</p>
      </section>

      <section className="draft-results__tier" aria-label="Best within your draft">
        <h3 className="draft-results__tier-title">
          Best within your draft (+{formatDamage(delta1)})
        </h3>
        <p className="draft-results__tier-total">
          {formatDamage(withinDraft.combined_total_damage)} dmg
        </p>
        <ol className="deck-results">
          {withinDraft.decks.map((deck, index) => {
            const { added, removed } = diffAgainstSubmitted(
              deck.deck,
              withinDraftMatches[index],
            )
            return (
              <DeckCard
                key={`within-draft-${index}`}
                label={`Deck ${index + 1}`}
                deck={deck}
                addedSlugs={added}
                removedSlugs={removed}
              />
            )
          })}
        </ol>
      </section>

      <section className="draft-results__tier" aria-label="Recommended">
        <h3 className="draft-results__tier-title">
          Recommended, bench-inclusive (+{formatDamage(delta2)})
        </h3>
        <p className="draft-results__tier-total">{formatDamage(combinedTotalDamage)} dmg</p>
        <ol className="deck-results">
          {decks.map((deck, index) => {
            const { added, removed } = diffAgainstSubmitted(
              deck.deck,
              recommendedMatches[index],
            )
            return (
              <DeckCard
                key={`recommended-${index}`}
                label={`Deck ${index + 1}`}
                deck={deck}
                pinnedSlugs={deck.pinned_slugs}
                addedSlugs={added}
                removedSlugs={removed}
              />
            )
          })}
        </ol>
      </section>

      {leftoverSlugs.length > 0 && (
        <p className="raid-results__leftover">
          Bench (not allocated to a deck): {leftoverSlugs.join(', ')}
        </p>
      )}
      <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
    </div>
  )
}
