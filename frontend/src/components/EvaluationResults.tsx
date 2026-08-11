// Renders a fixed set of user-built decks the engine only scored — it chose
// each deck's seat order (which unit bursts first), never its membership.
// Shared by the recommend tab's evaluate mode and the union raid tab, whose
// only difference is that each deck can name its own boss element (union
// raid's three battles each pick one).

import type { DeckRecommendation, BossElement, BossProfile } from '../types/recommend'
import { DeckCard, type UnitLookups } from './DeckCard'
import { formatDamage } from './formatDamage'
import { elementLabel } from '../lib/elementName'
import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'
import { weaknessFor } from '../lib/elementAdvantage'

// 보스의 본인 속성이 아니라 약점을 이름 붙인다 — 보스 폼이 받는 것이 약점이므로,
// 결과가 본인 속성으로 말하면 두 화면이 다른 언어를 쓰게 된다.
const bossElementLabel = (element: BossElement): string =>
  element === null ? '무속성' : `약점 ${elementLabel(weaknessFor(element))}`

interface EvaluationResultsProps extends UnitLookups {
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  /** 덱 하나당 보스 하나. 유니온 레이드의 세 전투는 각자 보스를 고른다. */
  bosses: BossProfile[]
}

export function EvaluationResults({
  decks,
  combinedTotalDamage,
  bosses,
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
            label={`${index + 1}번 덱 · ${bossElementLabel(bosses[index]?.element ?? null)}`}
            deck={deck}
            boss={bosses[index]}
            {...lookups}
          />
        ))}
      </ol>
      <p className="evaluation-results__ordering-note">
        <HelpText>{HELP.results.seatOrder}</HelpText>
      </p>
    </>
  )
}
