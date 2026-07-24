// Read-only display of one synced Nikke's investment data. The roster is
// sync-only (see SyncRosterPanel) - this only ever shows what blablalink last
// reported, it never accepts edits.
//
// Level and the raw HP/ATK/DEF are deliberately not shown. They are inputs the
// engine needs, not facts the player acts on: level is pinned to the solo-raid
// baseline of 400 for everyone, and the stats are derived from breakthrough,
// core and gear - all of which are already visible here. What the player reads
// a roster for is skill levels and overload, so that is what the card shows.

import type { NikkeDraft } from '../types/nikkeDraft'
import { InvestmentBadge } from './InvestmentBadge'
import { OverloadLines, SkillLevels } from './InvestmentSummary'

interface NikkeCardProps {
  draft: NikkeDraft
  index: number
  /** Resolved portrait URL, or null to fall back to the name alone. Passed in
   * rather than resolved here so one manifest load serves the whole roster. */
  portrait: string | null
}

export function NikkeCard({ draft, index, portrait }: NikkeCardProps) {
  const title = draft.character_slug.trim() || `Nikke ${index + 1}`

  return (
    <section className="card roster-card" aria-label={`Investment data for ${title}`}>
      {/* The slot is always drawn, even with no portrait to put in it: a
          missing one would otherwise pull that whole row out of line with
          every other card. */}
      {portrait ? (
        <img className="roster-card__portrait" src={portrait} alt="" />
      ) : (
        <span className="roster-card__portrait roster-card__portrait--missing" />
      )}

      <div className="roster-card__identity">
        <h2 className="card__title">{title}</h2>
        <InvestmentBadge grade={draft.grade} core={draft.core} />
        <SkillLevels levels={draft.skill_levels} />
      </div>

      <div className="roster-card__overload">
        <h3 className="roster-card__section-title">Overload</h3>
        <OverloadLines options={draft.overload_options} />
      </div>
    </section>
  )
}
