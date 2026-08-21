// A single deck's units (in burst order) and its total damage. Shared by
// DeckResults (ranked #N alternatives), RaidResults (allocation-order
// "Deck N" partitions), and DraftResults (draft tiers) — only the label,
// and DraftResults' optional pinned/diff annotations, differ.
//
// The per-source split (burst / normal / skill) rides along on the response
// and is not drawn: what a deck is worth is the total, and three more numbers
// per card cost more attention than they return (Fienn, 2026-07-26).
//
// The deck is drawn as a row of faces, the same language the palette and the
// draft slots use: a recommendation is only useful once you can tell who is
// in it, and a column of slugs made the answer the least legible screen in
// the app.

import type { BossProfile, DeckRecommendation } from '../types/recommend'
import { nameFromSlug } from '../lib/unitName'
import { BossSummary } from './BossSummary'
import { formatDamage } from './formatDamage'
import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'

/** How a result view turns a slug into something a player can recognise.
 * Threaded down from RecommendPanel, which owns both sources. */
export interface UnitLookups {
  /** Defaults leave a deck readable without a portrait manifest or the
   * supported-unit list, which is also what the unit tests render against. */
  portraitFor?: (slug: string) => string | null
  nameFor?: (slug: string) => string
  /** 이 덱이 보스의 속성저지 기믹을 파훼할 수 없는지. 판정은 화면이 한다 —
   * supported-units가 슬러그별 속성을 주므로 응답에 필드를 더할 이유가 없다.
   * 없으면(제약이 꺼졌거나 판정할 보스가 없으면) 배지도 없다. */
  gimmickUnmetFor?: (deckSlugs: string[]) => boolean
}

interface DeckCardProps extends UnitLookups {
  label: string
  deck: DeckRecommendation
  /** 이 덱이 상대한 보스. 덱마다 보스가 다른 화면(유니온 레이드)만 넘긴다 —
   * 전부 같은 보스인 화면은 결과 위에 한 번만 적는다. */
  boss?: BossProfile
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
  boss,
  pinnedSlugs = [],
  addedSlugs = [],
  removedSlugs = [],
  portraitFor = () => null,
  nameFor = nameFromSlug,
  gimmickUnmetFor,
}: DeckCardProps) {
  // 옛 SavedRun(이 브랜치 이전에 저장한 기록)에는 이 필드가 아예 없다 - engine_version
  // 캐시와 달리 SavedRun은 로스터가 바뀌어도 안 지워지므로, localStorage JSON이 TS
  // 타입의 필수 선언을 못 잡는다. 없으면 빈 객체로 대신해 아래 네 곳이 전부
  // `undefined[slug]`로 안 터지게 한다.
  const fullRounds = deck.partial_charge_full_rounds ?? {}
  return (
    <li className="deck-results__item">
      <div className="deck-results__header">
        <span className="deck-results__rank">{label}</span>
        <span className="deck-results__total">
          {formatDamage(deck.total_damage)} 총딜
        </span>
        {gimmickUnmetFor?.(deck.deck) && (
          <span className="deck-results__warning">
            <span aria-hidden="true">⚠</span> 속성저지 파훼 불가
          </span>
        )}
      </div>
      {boss && <BossSummary boss={boss} />}
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
                  <span className="deck-results__pin" title={HELP.results.pinTitle}>
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
      {/* 0이면 아무것도 안 그린다 — 대부분의 덱이 0이라 「없음」을 그리면 잡음이
          된다. 옛 SavedRun에는 필드가 아예 없고, 그때도 이 비교가 거짓이다. */}
      {(deck.gauge_bound_cycles ?? 0) > 0 && (
        <p className="deck-results__gauge-bound" title={HELP.results.gaugeBoundTitle}>
          <span aria-hidden="true">🔋</span>{' '}
          버충 밀림 {deck.gauge_bound_cycles}/{deck.total_cycles} 사이클
        </p>
      )}
      {deck.hold_burst_slugs.length > 0 && (
        <p className="deck-results__hold">
          <span aria-hidden="true">⏳</span>{' '}
          <HelpText>{HELP.results.holdBurst(deck.hold_burst_slugs.map(nameFor).join(', '))}</HelpText>
        </p>
      )}
      {/* 톡톡이 좌석을 「배율을 실제로 버렸는가」로 갈라 문구를 고른다. 어느 쪽인지는
          엔진이 정해서 실어 보내므로(`partial_charge_slugs`) 여기서 슬러그를 보고
          판단하지 않는다 — 홀드 안내·좌석 안내와 같은 계약이다. */}
      {deck.partial_charge_slugs.filter((slug) => !fullRounds[slug]).length >
        0 && (
        <p className="deck-results__hold">
          <span aria-hidden="true">👆</span>{' '}
          <HelpText>
            {HELP.results.tapFireAlways(
              deck.partial_charge_slugs
                .filter((slug) => !fullRounds[slug])
                .map(nameFor)
                .join(', '),
            )}
          </HelpText>
        </p>
      )}
      {deck.partial_charge_slugs
        .filter((slug) => fullRounds[slug] > 0)
        .map((slug) => (
          <p className="deck-results__hold" key={`tap-mixed-${slug}`}>
            <span aria-hidden="true">👆</span>{' '}
            <HelpText>
              {HELP.results.tapFireMixed(nameFor(slug), fullRounds[slug])}
            </HelpText>
          </p>
        ))}
      {deck.tap_fire_slugs.some((slug) => !deck.partial_charge_slugs.includes(slug)) && (
        <p className="deck-results__hold">
          <span aria-hidden="true">👆</span>{' '}
          <HelpText>
            {HELP.results.tapFireBurstOnly(
              deck.tap_fire_slugs
                .filter((slug) => !deck.partial_charge_slugs.includes(slug))
                .map(nameFor)
                .join(', '),
            )}
          </HelpText>
        </p>
      )}
      {Object.entries(deck.seating).map(([caster, seat]) => (
        <p className="deck-results__seating" key={caster}>
          <HelpText>
            {HELP.results.seating(
              nameFor(caster),
              seat.allies.map(nameFor).join(', '),
              // 앉을 수 있는 자리가 덱 전체면 제약이 없다는 뜻이라 자리 이야기를
              // 꺼내지 않는다. 슬러그를 보고 판단하지 않는 것이 핵심이다 - 어느
              // 유닛이 자리를 타는지는 엔진이 정하고 여기로 실려 온다.
              seat.seats.length < deck.deck.length ? seat.seats.join('·') : null,
            )}
          </HelpText>
        </p>
      ))}
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
