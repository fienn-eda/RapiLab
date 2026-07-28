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

/** Resizes a draft to `numDecks`, preserving already-placed decks by index -
 * growing appends empty decks, shrinking drops the trailing ones. Shared by
 * the recommend tab's deck-count selector and the union raid tab's
 * battle-count selector, which both resize their (differently-named) draft
 * state the same way. */
export const resizeDraft = (draft: Draft, numDecks: number): Draft => ({
  decks: Array.from({ length: numDecks }, (_, i) => draft.decks[i] ?? []),
})

/** Whether every one of the first `numDecks` decks is full - the gate for
 * evaluate-shaped screens (RecommendPanel's evaluate mode, the union raid
 * tab), which score exactly what the player placed rather than searching, so
 * a partial deck has nothing to complete. */
export const isDraftComplete = (draft: Draft, numDecks: number): boolean =>
  draft.decks.slice(0, numDecks).every((seats) => seats.length === MAX_DRAFT_SEATS_PER_DECK)
