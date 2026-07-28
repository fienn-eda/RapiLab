// Renders a fixed set of user-built decks the engine only scored — it chose
// each deck's seat order (which unit bursts first), never its membership.
// Shared by the recommend tab's evaluate mode and the union raid tab, whose
// only difference is that each deck can name its own boss element (union
// raid's three battles each pick one).

import type { DeckRecommendation, BossElement } from '../types/recommend'
import { DeckCard, type UnitLookups } from './DeckCard'
import { ExcludedSlugsNote } from './ExcludedSlugsNote'
import { formatDamage } from './formatDamage'
import { elementLabel } from '../lib/elementName'

const bossElementLabel = (element: BossElement): string =>
  element === null ? '무속성' : elementLabel(element)

interface EvaluationResultsProps extends UnitLookups {
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  /** Submitted slugs the backend can't evaluate yet — shown as "not yet supported". */
  excludedSlugs?: string[]
  /** One boss element per deck (union raid's three battles each pick their own). */
  bossElements: BossElement[]
}

export function EvaluationResults({
  decks,
  combinedTotalDamage,
  excludedSlugs = [],
  bossElements,
  ...lookups
}: EvaluationResultsProps) {
  return (
    <>
      <p className="evaluation-results__combined">
        총합: <strong>{formatDamage(combinedTotalDamage)} 딜</strong>
      </p>
      <ol className="deck-results">
        {decks.map((deck, index) => (
          <DeckCard
            key={deck.deck.join('-')}
            label={`${index + 1}번 덱 · ${bossElementLabel(bossElements[index])}`}
            deck={deck}
            {...lookups}
          />
        ))}
      </ol>
      <p className="evaluation-results__ordering-note">
        자리 순서는 엔진이 기대 딜량이 가장 높게 나오도록 고른 거예요. 인게임에서도 이 순서로
        배치해요.
      </p>
      <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
    </>
  )
}
