// The player's unit grid, shared by all three recommend modes. Owned units
// (active profile roster) intersected with engine-supported units
// (GET /api/supported-units), grouped under B1/B2/B3. Each unit has a "Use"
// checkbox for candidate-pool membership (default on); unchecking dims it and
// drops it from the search pool.
//
// In draft mode (onPick provided) an included, unplaced unit is also a way to
// seat a unit: drag its portrait onto a deck to choose where it lands, or
// click it to drop it in the next open deck. Click stays because dragging is
// mouse-only and the editor has to work from the keyboard too.
//
// Each unit carries its skill levels, because "should I field this one?" is
// exactly the question the Use checkbox asks and a portrait cannot answer it.
// Overload rolls sit behind a hover on the portrait: they matter to that same
// decision, but showing four lines per unit at once crowds out the grid.

import { usePortraitManifest } from '../hooks/usePortraitManifest'
import type { SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { OverloadLines, SkillLevels } from './InvestmentSummary'

/** dataTransfer key for a dragged unit. A custom type (rather than text/plain)
 * keeps a stray drag from elsewhere in the page reading as a unit drop. */
export const DRAG_SLUG_TYPE = 'application/x-nikke-slug'

interface UnitPaletteProps {
  /** The owned, validated roster - membership decides what the palette shows,
   * and each entry supplies that unit's investment display. */
  roster: UserNikkeState[]
  supportedUnits: SupportedUnit[]
  /** Slugs the user has toggled OUT of the candidate pool. */
  excludedSlugs: string[]
  onToggleExclude: (slug: string) => void
  /** Draft mode only: slugs already placed in a deck (not placeable again). */
  usedSlugs?: string[]
  /** Draft mode only: click an included, unplaced unit to place it. Omit for
   * single/raid, which have no placement. */
  onPick?: (slug: string) => void
}

const BURST_TIERS = [1, 2, 3] as const

export function UnitPalette({
  roster,
  supportedUnits,
  excludedSlugs,
  onToggleExclude,
  usedSlugs = [],
  onPick,
}: UnitPaletteProps) {
  const { portraitFor } = usePortraitManifest()
  const ownedBySlug = new Map(roster.map((nikke) => [nikke.character_slug, nikke]))
  const usedSet = new Set(usedSlugs)
  const excludedSet = new Set(excludedSlugs)
  const shown = supportedUnits.filter((unit) => ownedBySlug.has(unit.slug))

  return (
    <div className="palette">
      {BURST_TIERS.map((tier) => {
        const units = shown.filter((unit) => unit.burstTier === tier)
        if (units.length === 0) return null
        return (
          <section key={tier} className="palette__group">
            <h4 className="palette__heading">B{tier}</h4>
            <ul className="palette__list">
              {units.map((unit) => {
                const owned = ownedBySlug.get(unit.slug)!
                const isUsed = usedSet.has(unit.slug)
                const isExcluded = excludedSet.has(unit.slug)
                const portrait = portraitFor(unit.slug)
                const placeable = onPick !== undefined && !isUsed && !isExcluded

                const figure = (
                  <span className="palette__figure">
                    {portrait ? (
                      <img className="palette__portrait" src={portrait} alt="" />
                    ) : (
                      <span className="palette__portrait palette__portrait--missing" />
                    )}
                    <span className="palette__overload" role="presentation">
                      <OverloadLines
                        options={owned.overload_options}
                        emptyText="No overload"
                      />
                    </span>
                  </span>
                )

                return (
                  <li
                    key={unit.slug}
                    className={
                      isExcluded ? 'palette__item palette__item--excluded' : 'palette__item'
                    }
                  >
                    <div className="palette__body">
                      {onPick ? (
                        <button
                          type="button"
                          className="palette__face palette__face--pickable"
                          disabled={!placeable}
                          draggable={placeable}
                          aria-label={`${unit.name} (B${unit.burstTier})`}
                          onDragStart={(event) => {
                            event.dataTransfer.setData(DRAG_SLUG_TYPE, unit.slug)
                            event.dataTransfer.effectAllowed = 'move'
                          }}
                          onClick={() => onPick(unit.slug)}
                        >
                          {figure}
                        </button>
                      ) : (
                        // No aria-label: a generic element can't be named, and
                        // the visible name plus the "Use {name}" checkbox
                        // already name the unit.
                        <div className="palette__face">{figure}</div>
                      )}
                      <div className="palette__investment">
                        <SkillLevels levels={owned.skill_levels} layout="column" />
                      </div>
                    </div>

                    <span className="palette__name">{unit.name}</span>
                    <span className="palette__meta">
                      B{unit.burstTier} · {unit.element}
                    </span>

                    <label className="palette__use checkbox">
                      <input
                        type="checkbox"
                        checked={!isExcluded}
                        aria-label={`Use ${unit.name}`}
                        onChange={() => onToggleExclude(unit.slug)}
                      />
                      Use
                    </label>
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
