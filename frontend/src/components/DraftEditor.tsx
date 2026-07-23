// The draft-editor's deck grid (frontend/README.md "UI scope — draft
// editor"): numDecks columns x up to 5 seats each. Seats are MEMBERSHIP
// ONLY — no burst order; the engine assigns burst roles. Placement itself
// (which deck a picked palette unit lands in) is driven externally via the
// exported placeUnit — this component renders the current value and owns
// the per-seat lock toggle / remove action.

import type { Draft, DraftSeat } from '../types/draft'
import { MAX_DRAFT_SEATS_PER_DECK } from '../types/draft'
import type { DraftDeck } from '../types/recommend'

interface DraftEditorProps {
  numDecks: number
  value: Draft
  onChange: (next: Draft) => void
}

const mapDeck = (draft: Draft, deckIndex: number, fn: (seats: DraftSeat[]) => DraftSeat[]): Draft => ({
  decks: draft.decks.map((seats, index) => (index === deckIndex ? fn(seats) : seats)),
})

/** Places `slug` into `draft.decks[deckIndex]`. No-ops (returns `draft`
 * unchanged) if the slug is already drafted anywhere, or the target deck is
 * already full — the two client-side invariants the editor enforces. */
export const placeUnit = (
  draft: Draft,
  deckIndex: number,
  slug: string,
  locked = false,
): Draft => {
  const alreadyPlaced = draft.decks.some((seats) => seats.some((seat) => seat.slug === slug))
  if (alreadyPlaced) return draft
  const targetDeck = draft.decks[deckIndex]
  if (!targetDeck || targetDeck.length >= MAX_DRAFT_SEATS_PER_DECK) return draft
  return mapDeck(draft, deckIndex, (seats) => [...seats, { slug, locked }])
}

export const toggleLock = (draft: Draft, deckIndex: number, seatIndex: number): Draft =>
  mapDeck(draft, deckIndex, (seats) =>
    seats.map((seat, i) => (i === seatIndex ? { ...seat, locked: !seat.locked } : seat)),
  )

export const removeUnit = (draft: Draft, deckIndex: number, seatIndex: number): Draft =>
  mapDeck(draft, deckIndex, (seats) => seats.filter((_, i) => i !== seatIndex))

/** Removes `slug` from whichever deck seat holds it (a slug sits in at most
 * one deck). Returns `draft` unchanged if the slug is not placed anywhere. */
export const removeUnitBySlug = (draft: Draft, slug: string): Draft => {
  const deckIndex = draft.decks.findIndex((seats) => seats.some((seat) => seat.slug === slug))
  if (deckIndex === -1) return draft
  const seatIndex = draft.decks[deckIndex].findIndex((seat) => seat.slug === slug)
  return removeUnit(draft, deckIndex, seatIndex)
}

/** Builds the POST /api/recommend-raid wire shape, omitting empty decks
 * (frontend/README.md "Draft-based raid recommendation": "0..5 units each"). */
export const toRequestDraft = (draft: Draft): DraftDeck[] =>
  draft.decks
    .filter((seats) => seats.length > 0)
    .map((seats) => ({ units: seats.map(({ slug, locked }) => ({ slug, locked })) }))

export function DraftEditor({ numDecks, value, onChange }: DraftEditorProps) {
  return (
    <div className="draft-editor">
      <p className="draft-editor__hint">
        Seats are membership only — the engine assigns burst roles, this order
        doesn&rsquo;t matter.
      </p>
      <div className="draft-editor__decks">
        {Array.from({ length: numDecks }, (_, deckIndex) => {
          const seats = value.decks[deckIndex] ?? []
          return (
            <div className="draft-editor__deck" key={deckIndex}>
              <h4 className="draft-editor__deck-title">Deck {deckIndex + 1}</h4>
              <ul className="draft-editor__seats">
                {seats.map((seat, seatIndex) => (
                  <li key={seat.slug} className="draft-editor__seat">
                    <span className="draft-editor__slug">{seat.slug}</span>
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        checked={seat.locked}
                        aria-label={`Lock ${seat.slug} in deck ${deckIndex + 1}`}
                        onChange={() => onChange(toggleLock(value, deckIndex, seatIndex))}
                      />
                      Lock
                    </label>
                    <button
                      type="button"
                      className="btn btn--icon"
                      aria-label={`Remove ${seat.slug} from deck ${deckIndex + 1}`}
                      onClick={() => onChange(removeUnit(value, deckIndex, seatIndex))}
                    >
                      ×
                    </button>
                  </li>
                ))}
                {seats.length === 0 && <li className="draft-editor__empty">No units drafted yet.</li>}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}
