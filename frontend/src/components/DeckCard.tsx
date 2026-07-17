// A single deck's slugs (in burst order) and damage breakdown. Shared by
// DeckResults (ranked #N alternatives) and RaidResults (allocation-order
// "Deck N" partitions) — only the label differs.

import type { DeckRecommendation } from '../types/recommend'
import { formatDamage } from './formatDamage'

interface DeckCardProps {
  label: string
  deck: DeckRecommendation
}

export function DeckCard({ label, deck }: DeckCardProps) {
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
          </li>
        ))}
      </ol>
      <div className="deck-results__breakdown">
        <span>Burst: {formatDamage(deck.burst_damage)}</span>
        <span>Normal: {formatDamage(deck.normal_attack_damage)}</span>
      </div>
    </li>
  )
}
