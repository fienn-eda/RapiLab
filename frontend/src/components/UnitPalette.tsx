// The player's unit grid, shared by all three recommend modes. Owned units
// (active profile roster) intersected with engine-supported units
// (GET /api/supported-units), grouped under B1/B2/B3. Each unit has a "Use"
// checkbox for candidate-pool membership (default on); unchecking dims it and
// drops it from the search pool. In draft mode (onPick provided) an included,
// unplaced unit is also clickable to place it into a deck; excluded or placed
// units are not placeable.

import { usePortraitManifest } from '../hooks/usePortraitManifest'
import type { SupportedUnit } from '../types/supportedUnit'

interface UnitPaletteProps {
  /** Slugs of Nikkes in the (validated) owned roster. */
  ownedSlugs: string[]
  supportedUnits: SupportedUnit[]
  /** Slugs the user has toggled OUT of the candidate pool. */
  excludedSlugs: string[]
  onToggleExclude: (slug: string) => void
  /** Draft mode only: slugs already placed in a deck (place button disabled). */
  usedSlugs?: string[]
  /** Draft mode only: click an included, unplaced unit to place it. Omit for
   * single/raid, which have no placement. */
  onPick?: (slug: string) => void
}

const BURST_TIERS = [1, 2, 3] as const

export function UnitPalette({
  ownedSlugs,
  supportedUnits,
  excludedSlugs,
  onToggleExclude,
  usedSlugs = [],
  onPick,
}: UnitPaletteProps) {
  const { portraitFor } = usePortraitManifest()
  const ownedSet = new Set(ownedSlugs)
  const usedSet = new Set(usedSlugs)
  const excludedSet = new Set(excludedSlugs)
  const shown = supportedUnits.filter((unit) => ownedSet.has(unit.slug))

  return (
    <div className="draft-palette">
      {BURST_TIERS.map((tier) => {
        const units = shown.filter((unit) => unit.burstTier === tier)
        if (units.length === 0) return null
        return (
          <section key={tier} className="draft-palette__group">
            <h4 className="draft-palette__heading">B{tier}</h4>
            <ul className="draft-palette__list">
              {units.map((unit) => {
                const isUsed = usedSet.has(unit.slug)
                const isExcluded = excludedSet.has(unit.slug)
                const portrait = portraitFor(unit.slug)
                const chip = portrait ? (
                  <img className="draft-palette__portrait" src={portrait} alt="" />
                ) : (
                  <span className="draft-palette__chip">
                    <span className="draft-palette__chip-name">{unit.name}</span>
                    <span className="draft-palette__chip-meta">
                      B{unit.burstTier} · {unit.element}
                    </span>
                  </span>
                )
                return (
                  <li
                    key={unit.slug}
                    className={
                      isExcluded
                        ? 'draft-palette__item draft-palette__item--excluded'
                        : 'draft-palette__item'
                    }
                  >
                    {onPick ? (
                      <button
                        type="button"
                        className="draft-palette__unit"
                        disabled={isUsed || isExcluded}
                        aria-label={`${unit.name} (B${unit.burstTier})`}
                        onClick={() => onPick(unit.slug)}
                      >
                        {chip}
                      </button>
                    ) : (
                      <span
                        className="draft-palette__unit"
                        aria-label={`${unit.name} (B${unit.burstTier})`}
                      >
                        {chip}
                      </span>
                    )}
                    <label className="draft-palette__use checkbox">
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
