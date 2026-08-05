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
  /** false일 때만 경고한다 — 없으면(옛 저장 결과) 아무 말도 하지 않는다. */
  swapConverged?: boolean
}

export function RaidResults({
  decks,
  combinedTotalDamage,
  excludedSlugs = [],
  leftoverSlugs = [],
  swapConverged,
  ...lookups
}: RaidResultsProps) {
  const nameFor = lookups.nameFor ?? nameFromSlug
  if (decks.length === 0) {
    return (
      <>
        <p className="empty__text">아직 배분된 레이드 덱이 없어요.</p>
        <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
      </>
    )
  }

  return (
    <>
      <p className="raid-results__note">
        이 {decks.length}개 덱을 모두 함께 편성하세요 — 각 니케는 정확히 하나의 덱에만
        배정돼요. 이것은 순위별 대안이 아니라 하나의 분할이에요.
      </p>
      {swapConverged === false && (
        <p className="raid-results__note" role="status">
          탐색이 상한에 걸려 끝까지 가지 못했어요. 더 나은 배분이 남아 있을 수 있어요.
        </p>
      )}
      <p className="raid-results__combined">
        총합: <strong>{formatDamage(combinedTotalDamage)} 딜</strong>
      </p>
      <ol className="deck-results">
        {decks.map((deck, index) => (
          <DeckCard
            key={deck.deck.join('-')}
            label={`덱 ${index + 1}`}
            deck={deck}
            {...lookups}
          />
        ))}
      </ol>
      {leftoverSlugs.length > 0 && (
        <p className="raid-results__leftover">
          벤치 (덱에 배정되지 않음): {leftoverSlugs.map(nameFor).join(', ')}
        </p>
      )}
      <ExcludedSlugsNote excludedSlugs={excludedSlugs} />
    </>
  )
}
