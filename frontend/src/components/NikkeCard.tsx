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
import { FavoriteItemBadge } from './FavoriteItemBadge'
import { InvestmentBadge } from './InvestmentBadge'
import { OverloadLines, SkillLevels } from './InvestmentSummary'

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
}

export function NikkeCard({
  draft,
  index,
  name,
  element,
  portrait,
  excluded = false,
  onToggleExclude,
}: NikkeCardProps) {
  const title = name || draft.character_slug.trim() || `니케 ${index + 1}`

  return (
    <section
      className={`card roster-card${excluded ? ' roster-card--excluded' : ''}`}
      data-element={element}
      aria-label={`${title} 투자 정보`}
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
            onClick={onToggleExclude}
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
      <OverloadLines options={draft.overload_options} emptyText="오버로드 없음" />
    </section>
  )
}
