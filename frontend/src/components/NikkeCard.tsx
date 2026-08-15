// Read-only display of one synced Nikke's investment data, as a tile in the
// roster grid. The roster is sync-only (see SyncRosterPanel) - this only ever
// shows what blablalink last reported, it never accepts edits.
//
// Level and the raw HP/ATK/DEF are deliberately not shown. They are inputs the
// engine needs, not facts the player acts on: level is pinned to the solo-raid
// baseline of 400 for everyone, and the stats are derived from breakthrough,
// core and gear - all of which are already visible here. What the player reads
// a roster for is skill levels and overload, so that is what the tile shows.

import type { NikkeDraft } from '../types/nikkeDraft'
import type { NikkeElement } from '../types/supportedUnit'
import { byGearPiece } from '../lib/overload'
import { HELP } from '../lib/helpText'
import { FavoriteItemBadge } from './FavoriteItemBadge'
import { HelpText } from './HelpText'
import { InvestmentBadge } from './InvestmentBadge'
import { OverloadGearGrid, OverloadLines, SkillLevels } from './InvestmentSummary'

interface NikkeCardProps {
  draft: NikkeDraft
  index: number
  /** The unit's name. The slug is an identifier, not something to read. */
  name: string
  /** Tints the tile's edge, so the element is legible without a label. */
  element: NikkeElement
  /** Resolved portrait URL, or null to fall back to a placeholder. Passed in
   * rather than resolved here so one manifest load serves the whole roster. */
  portrait: string | null
  /** Whether this Nikke is benched — the recommender may not field her. */
  excluded?: boolean
  /** Omit on a screen with no recommendation to narrow; the portrait is then
   * a plain image rather than a control that does nothing. */
  onToggleExclude?: () => void
  /** Redraw the overload as the game's gear screen - the four pieces and their
   * option rows - instead of the per-stat totals. Decided for the whole tab at
   * once, so two units can still be read against each other. */
  overloadDetail?: boolean
}

export function NikkeCard({
  draft,
  index,
  name,
  element,
  portrait,
  excluded = false,
  onToggleExclude,
  overloadDetail = false,
}: NikkeCardProps) {
  const title = name || draft.character_slug.trim() || `니케 ${index + 1}`
  // Null whenever the rolls behind the totals cannot be placed on gear - see
  // byGearPiece. The totals are still true, so they are what gets shown.
  const pieces = overloadDetail ? byGearPiece(draft.overload_options) : null

  return (
    <section
      className={`card roster-card${excluded ? ' roster-card--excluded' : ''}`}
      data-element={element}
      aria-label={`${title} 투자 정보`}
      // 표적은 카드 테두리 안 전체다. 핸들러가 여기 하나뿐이라 초상화를 눌러도
      // 버블링으로 같은 핸들러에 한 번 닿는다 - 버튼에도 두면 두 번 불린다.
      onClick={onToggleExclude}
    >
      {/* The slot is always drawn, even with no portrait to put in it: a
          missing one would otherwise shorten that tile against its row.
          Where benching is offered the art is the control - this is the one
          tab that decides which Nikkes the recommender may field, and it is
          the same gesture the palette used to carry. */}
      <div className="roster-card__figure">
        {onToggleExclude ? (
          <button
            type="button"
            className="roster-card__use"
            aria-pressed={!excluded}
            aria-label={`${title} 사용`}
          >
            {portrait ? (
              <img className="roster-card__portrait" src={portrait} alt="" />
            ) : (
              <span className="roster-card__portrait roster-card__portrait--missing" />
            )}
          </button>
        ) : portrait ? (
          <img className="roster-card__portrait" src={portrait} alt="" />
        ) : (
          <span className="roster-card__portrait roster-card__portrait--missing" />
        )}
        {/* Breakthrough and core sit ON the art the way the game shows them,
            which keeps the tile's text column to name and investment. The
            Favorite Item heart joins them for the same reason. */}
        <span className="roster-card__grade">
          <InvestmentBadge grade={draft.grade} core={draft.core} />
          <FavoriteItemBadge equipped={draft.favorite_item} />
        </span>
      </div>

      <h3 className="roster-card__name">{title}</h3>
      <SkillLevels levels={draft.skill_levels} />
      {pieces ? (
        <OverloadGearGrid pieces={pieces} />
      ) : (
        <>
          <OverloadLines options={draft.overload_options} emptyText="오버로드 없음" />
          {/* Only when detail was asked for and there was something to detail:
              a unit with no overload at all has nothing a re-sync would add. */}
          {overloadDetail && draft.overload_options.length > 0 && (
            <p className="overload__note">
              <HelpText>{HELP.roster.gearNeedsResync}</HelpText>
            </p>
          )}
        </>
      )}
    </section>
  )
}
