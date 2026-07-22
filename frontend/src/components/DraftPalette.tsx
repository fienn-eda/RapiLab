// The draft-editor's unit picker: owned units (from useRoster) intersected
// with engine-supported units (GET /api/supported-units), grouped under
// B1/B2/B3 headers (frontend/README.md "UI scope — draft editor"). A unit
// already placed in some deck ("used") renders disabled — a unit may sit in
// at most one deck.

import { usePortraitManifest } from '../hooks/usePortraitManifest'
import type { SupportedUnit } from '../types/supportedUnit'

interface DraftPaletteProps {
  /** Slugs of Nikkes in the (validated) owned roster. */
  ownedSlugs: string[]
  supportedUnits: SupportedUnit[]
  /** Slugs already placed in a deck seat — rendered disabled here. */
  usedSlugs: string[]
  onPick: (slug: string) => void
}

const BURST_TIERS = [1, 2, 3] as const

export function DraftPalette({ ownedSlugs, supportedUnits, usedSlugs, onPick }: DraftPaletteProps) {
  const { portraitFor } = usePortraitManifest()
  const ownedSet = new Set(ownedSlugs)
  const usedSet = new Set(usedSlugs)
  const draftable = supportedUnits.filter((unit) => ownedSet.has(unit.slug))

  return (
    <div className="draft-palette">
      {BURST_TIERS.map((tier) => {
        const units = draftable.filter((unit) => unit.burstTier === tier)
        if (units.length === 0) return null
        return (
          <section key={tier} className="draft-palette__group">
            <h4 className="draft-palette__heading">B{tier}</h4>
            <ul className="draft-palette__list">
              {units.map((unit) => {
                const isUsed = usedSet.has(unit.slug)
                const portrait = portraitFor(unit.slug)
                return (
                  <li key={unit.slug} className="draft-palette__item">
                    <button
                      type="button"
                      className="draft-palette__unit"
                      disabled={isUsed}
                      aria-label={`${unit.name} (B${unit.burstTier})`}
                      onClick={() => onPick(unit.slug)}
                    >
                      {portrait ? (
                        <img className="draft-palette__portrait" src={portrait} alt="" />
                      ) : (
                        <span className="draft-palette__chip">
                          <span className="draft-palette__chip-name">{unit.name}</span>
                          <span className="draft-palette__chip-meta">
                            B{unit.burstTier} · {unit.element}
                          </span>
                        </span>
                      )}
                    </button>
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
