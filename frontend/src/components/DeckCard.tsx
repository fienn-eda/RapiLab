// A single deck's units (in burst order) and damage breakdown. Shared by
// DeckResults (ranked #N alternatives), RaidResults (allocation-order
// "Deck N" partitions), and DraftResults (draft tiers) — only the label,
// and DraftResults' optional pinned/diff annotations, differ.
//
// The deck is drawn as a row of faces, the same language the palette and the
// draft slots use: a recommendation is only useful once you can tell who is
// in it, and a column of slugs made the answer the least legible screen in
// the app.

import type { DeckRecommendation } from '../types/recommend'
import { nameFromSlug } from '../lib/unitName'
import { formatDamage } from './formatDamage'

/** How a result view turns a slug into something a player can recognise.
 * Threaded down from RecommendPanel, which owns both sources. */
export interface UnitLookups {
  /** Defaults leave a deck readable without a portrait manifest or the
   * supported-unit list, which is also what the unit tests render against. */
  portraitFor?: (slug: string) => string | null
  nameFor?: (slug: string) => string
}

interface DeckCardProps extends UnitLookups {
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
  portraitFor = () => null,
  nameFor = nameFromSlug,
}: DeckCardProps) {
  return (
    <li className="deck-results__item">
      <div className="deck-results__header">
        <span className="deck-results__rank">{label}</span>
        <span className="deck-results__total">
          {formatDamage(deck.total_damage)} 총딜
        </span>
      </div>
      <ol className="deck-results__units">
        {deck.deck.map((slug, slot) => {
          const portrait = portraitFor(slug)
          const name = nameFor(slug)
          return (
            <li key={`${slug}-${slot}`} className="deck-results__unit">
              <span className="deck-results__figure">
                {portrait ? (
                  <img className="deck-results__portrait" src={portrait} alt="" />
                ) : (
                  <span className="deck-results__portrait deck-results__portrait--missing" />
                )}
                {pinnedSlugs.includes(slug) && (
                  <span className="deck-results__pin" title="고정해서 여기 유지돼요">
                    <span aria-hidden="true">📌</span>
                    <span className="visually-hidden">고정됨</span>
                  </span>
                )}
              </span>
              <span className="deck-results__unit-name">{name}</span>
            </li>
          )
        })}
      </ol>
      <div className="deck-results__breakdown">
        <span>버스트: {formatDamage(deck.burst_damage)}</span>
        <span>평타: {formatDamage(deck.normal_attack_damage)}</span>
      </div>
      {(addedSlugs.length > 0 || removedSlugs.length > 0) && (
        <div className="deck-results__diff">
          {addedSlugs.length > 0 && (
            <span className="deck-results__diff-added">
              + {addedSlugs.map(nameFor).join(', ')}
            </span>
          )}
          {removedSlugs.length > 0 && (
            <span className="deck-results__diff-removed">
              - {removedSlugs.map(nameFor).join(', ')}
            </span>
          )}
        </div>
      )}
    </li>
  )
}
