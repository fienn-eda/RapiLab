// Deck allocation returned by POST /api/recommend-raid: up to num_decks
// DISJOINT decks the player fields together in one raid — NOT ranked
// alternatives for a single deck slot (that's DeckResults). Each deck still
// lists its 5 slugs in burst order with the same total/burst/normal
// breakdown; this view additionally surfaces the combined total and who was
// left on the bench.

import type { DeckRecommendation } from '../types/recommend'
import { DeckCard, type UnitLookups } from './DeckCard'
import { ExcludedSlugsNote } from './ExcludedSlugsNote'
import { formatDamage } from './formatDamage'
import { nameFromSlug } from '../lib/unitName'

interface RaidResultsProps extends UnitLookups {
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  /** Submitted slugs the backend can't evaluate yet — shown as "not yet supported". */
  excludedSlugs?: string[]
  /** Usable units the allocation left out of every deck. */
  leftoverSlugs?: string[]
}

export function RaidResults({
  decks,
  combinedTotalDamage,
  excludedSlugs = [],
  leftoverSlugs = [],
  ...lookups
}: RaidResultsProps) {
  const nameFor = lookups.nameFor ?? nameFromSlug
  if (decks.length === 0) {
    return (
      <>
        <p className="empty__text">No raid decks allocated yet.</p>
        <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
      </>
    )
  }

  return (
    <>
      <p className="raid-results__note">
        Field all {decks.length} of these decks together — each Nikke is allocated to exactly
        one deck. This is a partition, not a ranked list of alternatives.
      </p>
      <p className="raid-results__combined">
        Combined total: <strong>{formatDamage(combinedTotalDamage)} dmg</strong>
      </p>
      <ol className="deck-results">
        {decks.map((deck, index) => (
          <DeckCard
            key={deck.deck.join('-')}
            label={`Deck ${index + 1}`}
            deck={deck}
            {...lookups}
          />
        ))}
      </ol>
      {leftoverSlugs.length > 0 && (
        <p className="raid-results__leftover">
          Bench (not allocated to a deck): {leftoverSlugs.map(nameFor).join(', ')}
        </p>
      )}
      <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
    </>
  )
}
