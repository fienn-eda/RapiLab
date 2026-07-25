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
}

export function NikkeCard({ draft, index, name, element, portrait }: NikkeCardProps) {
  const title = name || draft.character_slug.trim() || `Nikke ${index + 1}`

  return (
    <section className="card roster-card" data-element={element} aria-label={`Investment data for ${title}`}>
      {/* The slot is always drawn, even with no portrait to put in it: a
          missing one would otherwise shorten that tile against its row. */}
      <div className="roster-card__figure">
        {portrait ? (
          <img className="roster-card__portrait" src={portrait} alt="" />
        ) : (
          <span className="roster-card__portrait roster-card__portrait--missing" />
        )}
        {/* Breakthrough and core sit ON the art the way the game shows them,
            which keeps the tile's text column to name and investment. */}
        <span className="roster-card__grade">
          <InvestmentBadge grade={draft.grade} core={draft.core} />
        </span>
      </div>

      <h2 className="roster-card__name">{title}</h2>
      <SkillLevels levels={draft.skill_levels} />
      <OverloadLines options={draft.overload_options} emptyText="No overload" />
    </section>
  )
}
