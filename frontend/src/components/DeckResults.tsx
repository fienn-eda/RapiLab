// Ranked deck recommendations returned by POST /api/recommend. Each deck
// lists its 5 slugs in burst order (B1 -> B2 -> B3), per the response contract.

import type { DeckRecommendation } from '../types/recommend'
import { DeckCard, type UnitLookups } from './DeckCard'
import { ExcludedSlugsNote } from './ExcludedSlugsNote'

interface DeckResultsProps extends UnitLookups {
  decks: DeckRecommendation[]
  /** Submitted slugs the backend can't evaluate yet — shown as "not yet supported". */
  excludedSlugs?: string[]
}

export function DeckResults({ decks, excludedSlugs = [], ...lookups }: DeckResultsProps) {
  if (decks.length === 0) {
    return (
      <>
        <p className="empty__text">No decks recommended yet.</p>
        <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
      </>
    )
  }

  return (
    <>
      <ol className="deck-results">
        {decks.map((deck, index) => (
          <DeckCard key={deck.deck.join('-')} label={`#${index + 1}`} deck={deck} {...lookups} />
        ))}
      </ol>
      <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
    </>
  )
}
