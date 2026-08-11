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

/** `from`부터 앞으로, 끝까지 가면 처음으로 되돌아 훑어 빈자리가 있는 첫 덱.
 * 전부 찼으면 null.
 *
 * 팔레트 클릭이 어느 덱에 앉는지와, 앉힌 뒤 활성 덱이 어디로 가는지를 이 하나가
 * 정한다 - 그래서 「덱이 차면 다음 덱으로 넘어간다」와 「꽉 찬 덱을 직접 골라
 * 두고 팔레트를 눌렀을 때」가 같은 규칙으로 풀린다.
 *
 * `numDecks` 밖은 보지 않고, decks 배열에 아직 없는 자리는 건너뛴다. 덱 개수를
 * 방금 바꿨을 때 저장된 draft와 화면의 덱 수가 한 렌더 어긋나는데, 그때 화면에
 * 없는 덱을 고르면 placeUnit이 조용히 거절해 아무도 안 앉는다. */
export const firstDeckWithRoom = (
  draft: Draft,
  from: number,
  numDecks: number,
): number | null => {
  for (let offset = 0; offset < numDecks; offset += 1) {
    const index = (from + offset) % numDecks
    const seats = draft.decks[index]
    if (seats !== undefined && seats.length < MAX_DRAFT_SEATS_PER_DECK) return index
  }
  return null
}
