// Ranked deck recommendations returned by POST /api/recommend. Each deck
// lists its 5 slugs in burst order (B1 -> B2 -> B3), per the response contract.
//
// 미지원 슬러그는 여기서 말하지 않는다 - 니케 풀 탭이 이미 "보유 중이지만 아직
// 엔진 미지원 N기"로 같은 사실을 말하고, 결과 화면에서는 그것이 매번 뜨는
// 배경 소음이었다 (Fienn, 2026-08-11).

import type { DeckRecommendation } from '../types/recommend'
import { DeckCard, type UnitLookups } from './DeckCard'
import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'

interface DeckResultsProps extends UnitLookups {
  decks: DeckRecommendation[]
}

export function DeckResults({ decks, ...lookups }: DeckResultsProps) {
  if (decks.length === 0) {
    return <p className="empty__text"><HelpText>{HELP.results.emptyDecks}</HelpText></p>
  }

  return (
    <ol className="deck-results">
      {decks.map((deck, index) => (
        <DeckCard key={deck.deck.join('-')} label={`#${index + 1}`} deck={deck} {...lookups} />
      ))}
    </ol>
  )
}
