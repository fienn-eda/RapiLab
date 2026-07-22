// Client-side draft-editor state (frontend/README.md "UI scope — draft
// editor"): up to num_decks decks, each an ordered list of placed seats.
// Seats are MEMBERSHIP ONLY — no burst order; the engine assigns burst
// roles server-side. This is distinct from the wire shape DraftDeck in
// types/recommend.ts (an array of {units:[]} objects vs. an array of
// arrays here) — DraftEditor.tsx's toRequestDraft converts between them.

export interface DraftSeat {
  slug: string
  locked: boolean
}

export interface Draft {
  decks: DraftSeat[][]
}

/** A deck can hold at most 5 units, matching the backend's fixed deck size. */
export const MAX_DRAFT_SEATS_PER_DECK = 5

export const makeEmptyDraft = (numDecks: number): Draft => ({
  decks: Array.from({ length: numDecks }, () => []),
})
