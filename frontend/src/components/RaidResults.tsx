// Deck allocation returned by POST /api/recommend-raid: up to num_decks
// DISJOINT decks the player fields together in one raid — NOT ranked
// alternatives for a single deck slot (that's DeckResults). Each deck still
// lists its 5 slugs in burst order with the same total/burst/normal
// breakdown; this view additionally surfaces the combined total and who was
// left on the bench.

import type { DeckRecommendation } from '../types/recommend'
import { BenchNote } from './BenchNote'
import { DeckCard, type UnitLookups } from './DeckCard'
import { formatDamage } from './formatDamage'
import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'
import { nameFromSlug } from '../lib/unitName'
import { SwapConvergenceNote } from './SwapConvergenceNote'

interface RaidResultsProps extends UnitLookups {
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  /** Usable units the allocation left out of every deck. */
  leftoverSlugs?: string[]
  /** false일 때만 경고한다 — 없으면(옛 저장 결과) 아무 말도 하지 않는다. */
  swapConverged?: boolean
}

export function RaidResults({
  decks,
  combinedTotalDamage,
  leftoverSlugs = [],
  swapConverged,
  ...lookups
}: RaidResultsProps) {
  const nameFor = lookups.nameFor ?? nameFromSlug
  if (decks.length === 0) {
    return (
      <>
        <p className="empty__text"><HelpText>{HELP.results.emptyRaid}</HelpText></p>
      </>
    )
  }

  return (
    <>
      <p className="raid-results__note">
        <HelpText>{HELP.results.raidSplit(decks.length)}</HelpText>
      </p>
      <SwapConvergenceNote swapConverged={swapConverged} />
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
      <BenchNote leftoverSlugs={leftoverSlugs} nameFor={nameFor} />
    </>
  )
}
