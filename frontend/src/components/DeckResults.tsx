// Ranked deck recommendations returned by POST /api/recommend. Each deck
// lists its 5 slugs in burst order (B1 -> B2 -> B3), per the response contract.

import type { DeckRecommendation } from '../types/recommend'

interface DeckResultsProps {
  decks: DeckRecommendation[]
  /** Submitted slugs the backend can't evaluate yet — shown as "not yet supported". */
  excludedSlugs?: string[]
}

const formatDamage = (value: number): string => Math.round(value).toLocaleString()

export function DeckResults({ decks, excludedSlugs = [] }: DeckResultsProps) {
  const excludedNote = excludedSlugs.length > 0 && (
    <p className="deck-results__excluded">
      Not yet supported (excluded from search): {excludedSlugs.join(', ')}
    </p>
  )

  if (decks.length === 0) {
    return (
      <>
        <p className="empty__text">No decks recommended yet.</p>
        {excludedNote}
      </>
    )
  }

  return (
    <>
    <ol className="deck-results">
      {decks.map((deck, index) => (
        <li key={deck.deck.join('-')} className="deck-results__item">
          <div className="deck-results__header">
            <span className="deck-results__rank">#{index + 1}</span>
            <span className="deck-results__total">
              {formatDamage(deck.total_damage)} total dmg
            </span>
          </div>
          <ol className="deck-results__slugs">
            {deck.deck.map((slug, slot) => (
              <li key={`${slug}-${slot}`} className="deck-results__slug">
                {slug}
              </li>
            ))}
          </ol>
          <div className="deck-results__breakdown">
            <span>Burst: {formatDamage(deck.burst_damage)}</span>
            <span>Normal: {formatDamage(deck.normal_attack_damage)}</span>
          </div>
        </li>
      ))}
    </ol>
    {excludedNote}
    </>
  )
}
