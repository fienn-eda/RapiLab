// The Roster tab's contents: everything the active profile synced, split by
// whether the engine can actually simulate it.
//
// A player owns far more Nikkes than the engine supports (159 vs 70 on the
// roster this was built against). Drawing both alike made more than half the
// tab units that can never enter a deck, at the same size and weight as the
// ones that can. The supported units get the grid; the rest get a collapsed
// list, present so a missing Nikke is explained rather than simply absent.
//
// The supported half is grouped by burst tier, the way the recommend palette
// groups it - a roster is read to answer "what can I field", and that
// question is always asked one tier at a time.

import { useState } from 'react'
import type { NikkeDraft } from '../types/nikkeDraft'
import { BURST_TIERS, type SupportedUnit } from '../types/supportedUnit'
import { displayName } from '../lib/unitName'
import {
  EMPTY_FILTER,
  filterAndSort,
  type UnitFacets,
  type UnitFilterState,
} from '../lib/unitFilter'
import { NikkeCard } from './NikkeCard'
import { UnitFilterBar } from './UnitFilterBar'

interface RosterGridProps {
  drafts: NikkeDraft[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
  /** Benched Nikkes — the recommender may not field these. Account-wide, so
   * this tab is where they are decided; the raid tabs only read it. */
  excludedSlugs?: string[]
  onToggleExclude?: (slug: string) => void
}

export function RosterGrid({
  drafts,
  supportedUnits,
  portraitFor,
  excludedSlugs = [],
  onToggleExclude,
}: RosterGridProps) {
  const excludedSet = new Set(excludedSlugs)
  const bySlug = new Map(supportedUnits.map((unit) => [unit.slug, unit]))
  const supported = drafts.filter((draft) => bySlug.has(draft.character_slug))
  const unsupported = drafts.filter((draft) => !bySlug.has(draft.character_slug))
  const names = new Map(supportedUnits.map((unit) => [unit.slug, unit.name]))

  const [filter, setFilter] = useState<UnitFilterState>(EMPTY_FILTER)

  // Only the supported half has an element and a burst tier to filter on; the
  // unsupported list is not in `supportedUnits` at all, so a half-applied
  // toolbar would just look broken there.
  const facetsFor = (draft: NikkeDraft): UnitFacets => {
    const unit = bySlug.get(draft.character_slug)!
    return {
      name: unit.name,
      element: unit.element,
      burstTier: unit.burstTier,
      overload: draft.overload_options,
    }
  }

  // Sorted once across the whole roster, then partitioned by tier - a
  // partition preserves relative order, so each group is already in sort
  // order.
  const visible = filterAndSort(supported, facetsFor, filter)

  return (
    <div className="roster">
      {supported.length > 0 && (
        <UnitFilterBar
          value={filter}
          onChange={setFilter}
          shown={visible.length}
          total={supported.length}
        />
      )}

      {BURST_TIERS.map((tier) => {
        const units = visible.filter(
          (draft) => bySlug.get(draft.character_slug)!.burstTier === tier,
        )
        if (units.length === 0) return null
        return (
          <section key={tier} className="roster__group">
            {/* The game's own burst icon carries the tier. Its alt is what
                names the heading, so the section is still "B1" to a reader
                who never sees the image. */}
            <h2 className="roster__heading">
              <img
                className="burst-heading__icon"
                src={`/elements/icon-burst-${tier}.png`}
                alt={`B${tier}`}
              />
            </h2>
            <div className="roster__grid">
              {units.map((draft, index) => {
                const unit = bySlug.get(draft.character_slug)!
                return (
                  <NikkeCard
                    key={draft.id ?? draft.character_slug}
                    draft={draft}
                    index={index}
                    name={unit.name}
                    element={unit.element}
                    portrait={portraitFor(draft.character_slug)}
                    excluded={excludedSet.has(draft.character_slug)}
                    onToggleExclude={
                      onToggleExclude
                        ? () => onToggleExclude(draft.character_slug)
                        : undefined
                    }
                  />
                )
              })}
            </div>
          </section>
        )
      })}

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
