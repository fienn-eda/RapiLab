// The Roster tab's contents: everything the active profile synced, split by
// whether the engine can actually simulate it.
//
// A player owns far more Nikkes than the engine supports (159 vs 70 on the
// roster this was built against). Drawing both alike made more than half the
// tab units that can never enter a deck, at the same size and weight as the
// ones that can. The supported units get the grid; the rest get a collapsed
// list, present so a missing Nikke is explained rather than simply absent.

import type { NikkeDraft } from '../types/nikkeDraft'
import type { SupportedUnit } from '../types/supportedUnit'
import { displayName } from '../lib/unitName'
import { NikkeCard } from './NikkeCard'

interface RosterGridProps {
  drafts: NikkeDraft[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
}

export function RosterGrid({ drafts, supportedUnits, portraitFor }: RosterGridProps) {
  const bySlug = new Map(supportedUnits.map((unit) => [unit.slug, unit]))
  const supported = drafts.filter((draft) => bySlug.has(draft.character_slug))
  const unsupported = drafts.filter((draft) => !bySlug.has(draft.character_slug))
  const names = new Map(supportedUnits.map((unit) => [unit.slug, unit.name]))

  return (
    <div className="roster">
      <div className="roster__grid">
        {supported.map((draft, index) => {
          const unit = bySlug.get(draft.character_slug)!
          return (
            <NikkeCard
              key={draft.id ?? draft.character_slug}
              draft={draft}
              index={index}
              name={unit.name}
              element={unit.element}
              portrait={portraitFor(draft.character_slug)}
            />
          )
        })}
      </div>

      {unsupported.length > 0 && (
        <details className="roster__unsupported">
          <summary className="roster__unsupported-summary">
            엔진 미지원 ({unsupported.length}기)
          </summary>
          <ul className="roster__unsupported-list">
            {unsupported.map((draft) => (
              <li key={draft.id ?? draft.character_slug}>
                {displayName(draft.character_slug, names)}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
