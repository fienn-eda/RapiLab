// Read-only display of one synced Nikke's investment data. The roster is
// sync-only (see SyncRosterPanel) - this only ever shows what blablalink last
// reported, it never accepts edits.

import type { NikkeDraft } from '../types/nikkeDraft'
import { InvestmentBadge } from './InvestmentBadge'

interface NikkeCardProps {
  draft: NikkeDraft
  index: number
}

export function NikkeCard({ draft, index }: NikkeCardProps) {
  const title = draft.character_slug.trim() || `Nikke ${index + 1}`

  return (
    <section className="card" aria-label={`Investment data for ${title}`}>
      <header className="card__header">
        <h2 className="card__title">{title}</h2>
        <InvestmentBadge grade={draft.grade} core={draft.core} />
      </header>

      <div className="field-row">
        <div className="stat">
          <span className="stat__label">Level</span>
          <span className="stat__value">{draft.level}</span>
        </div>
      </div>

      <div className="field-row field-row--thirds">
        <div className="stat">
          <span className="stat__label">HP</span>
          <span className="stat__value">{draft.hp}</span>
        </div>
        <div className="stat">
          <span className="stat__label">ATK</span>
          <span className="stat__value">{draft.atk}</span>
        </div>
        <div className="stat">
          <span className="stat__label">DEF</span>
          <span className="stat__value">{draft.def_}</span>
        </div>
      </div>

      <fieldset className="group">
        <legend className="group__legend">Skill levels</legend>
        <div className="field-row field-row--thirds">
          <div className="stat">
            <span className="stat__label">Skill 1</span>
            <span className="stat__value">{draft.skill_levels.skill1}</span>
          </div>
          <div className="stat">
            <span className="stat__label">Skill 2</span>
            <span className="stat__value">{draft.skill_levels.skill2}</span>
          </div>
          <div className="stat">
            <span className="stat__label">Burst</span>
            <span className="stat__value">{draft.skill_levels.burst}</span>
          </div>
        </div>
      </fieldset>

      <fieldset className="group">
        <legend className="group__legend">
          Overload options
          <span className="group__hint"> aggregated across 4 gear pieces</span>
        </legend>
        {draft.overload_options.length === 0 ? (
          <p className="group__empty">No overload lines.</p>
        ) : (
          draft.overload_options.map((row) => (
            <div key={row.id} className="field-row">
              <div className="stat">
                <span className="stat__label">{row.name}</span>
                <span className="stat__value">{row.value}</span>
              </div>
            </div>
          ))
        )}
      </fieldset>
    </section>
  )
}
