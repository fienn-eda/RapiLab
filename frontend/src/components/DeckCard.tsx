// A single deck's slugs (in burst order) and damage breakdown. Shared by
// DeckResults (ranked #N alternatives), RaidResults (allocation-order
// "Deck N" partitions), and DraftResults (draft tiers) — only the label,
// and DraftResults' optional pinned/diff annotations, differ.

import type { DeckRecommendation } from '../types/recommend'
import { formatDamage } from './formatDamage'

interface DeckCardProps {
  label: string
  deck: DeckRecommendation
  /** Locked draft slugs the engine kept in this deck (RaidDeck.pinned_slugs). */
  pinnedSlugs?: string[]
  /** Slugs in this deck the submitted draft didn't have (DraftResults diff). */
  addedSlugs?: string[]
  /** Slugs the submitted draft had that this deck doesn't (DraftResults diff). */
  removedSlugs?: string[]
}

export function DeckCard({
  label,
  deck,
  pinnedSlugs = [],
  addedSlugs = [],
  removedSlugs = [],
}: DeckCardProps) {
  return (
    <li className="deck-results__item">
      <div className="deck-results__header">
        <span className="deck-results__rank">{label}</span>
        <span className="deck-results__total">
          {formatDamage(deck.total_damage)} total dmg
        </span>
      </div>
      <ol className="deck-results__slugs">
        {deck.deck.map((slug, slot) => (
          <li key={`${slug}-${slot}`} className="deck-results__slug">
            {slug}
            {pinnedSlugs.includes(slug) && (
              <span className="pill pill--ok deck-results__pin">pinned</span>
            )}
          </li>
        ))}
      </ol>
      <div className="deck-results__breakdown">
        <span>Burst: {formatDamage(deck.burst_damage)}</span>
        <span>Normal: {formatDamage(deck.normal_attack_damage)}</span>
      </div>
      {(addedSlugs.length > 0 || removedSlugs.length > 0) && (
        <div className="deck-results__diff">
          {addedSlugs.length > 0 && (
            <span className="deck-results__diff-added">+ {addedSlugs.join(', ')}</span>
          )}
          {removedSlugs.length > 0 && (
            <span className="deck-results__diff-removed">- {removedSlugs.join(', ')}</span>
          )}
        </div>
      )}
    </li>
  )
}
