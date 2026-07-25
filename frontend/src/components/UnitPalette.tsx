// The player's unit grid, shared by all three recommend modes. Owned units
// (active profile roster) intersected with engine-supported units
// (GET /api/supported-units), grouped under B1/B2/B3.
//
// A chip is its portrait and its skill levels, nothing else. Clicking the
// portrait toggles whether that unit is in the candidate pool (default in);
// an excluded one greys out. Everything a chip used to spell out - name,
// burst tier, element, overload rolls - is on the hover card instead, so the
// grid stays dense enough to scan a whole roster at once.
//
// In draft mode (draggable) a portrait can also be dragged onto a deck to
// seat it there. Dragging is the only way to seat a unit, so draft editing is
// mouse-only; the Use toggle and everything else works from the keyboard.

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
  /** Draft mode only: slugs already seated in a deck. */
  usedSlugs?: string[]
  /** Draft mode only: lets an included, unseated unit be dragged onto a deck. */
  draggable?: boolean
}

const BURST_TIERS = [1, 2, 3] as const

export function UnitPalette({
  roster,
  supportedUnits,
  excludedSlugs,
  onToggleExclude,
  usedSlugs = [],
  draggable = false,
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
                const classes = ['palette__item']
                if (isExcluded) classes.push('palette__item--excluded')
                if (isUsed) classes.push('palette__item--seated')

                return (
                  <li
                    key={unit.slug}
                    className={classes.join(' ')}
                    // Element drives a colour, not a word: the chip has no room
                    // to spell it and the hover card already does.
                    data-element={unit.element}
                  >
                    <button
                      type="button"
                      className="palette__face"
                      // A toggle, so it reports its state rather than pretending
                      // each press is a fresh action. The name has to live here:
                      // the chip itself no longer shows any text.
                      aria-pressed={!isExcluded}
                      aria-label={`Use ${unit.name}`}
                      draggable={draggable && !isExcluded && !isUsed}
                      onDragStart={(event) => {
                        event.dataTransfer.setData(DRAG_SLUG_TYPE, unit.slug)
                        event.dataTransfer.effectAllowed = 'move'
                      }}
                      onClick={() => onToggleExclude(unit.slug)}
                    >
                      <span className="palette__figure">
                        {portrait ? (
                          <img className="palette__portrait" src={portrait} alt="" />
                        ) : (
                          <span className="palette__portrait palette__portrait--missing" />
                        )}
                        {/* Everything the chip stopped showing. Presentational:
                            the button is already named, and this would other-
                            wise read back as a second copy of the same unit. */}
                        <span className="palette__details" role="presentation">
                          <span className="palette__name">{unit.name}</span>
                          <span className="palette__meta">
                            B{unit.burstTier} · {unit.element}
                          </span>
                          <OverloadLines
                            options={owned.overload_options}
                            emptyText="No overload"
                          />
                        </span>
                      </span>
                    </button>

                    <SkillLevels levels={owned.skill_levels} layout="column" />
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
