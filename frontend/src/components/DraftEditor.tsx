// The draft-editor's deck grid (frontend/README.md "UI scope — draft
// editor"): numDecks columns x exactly 5 slots each, drawn like the game's
// squad slots — a square face, or a `+` for an open slot. Slots are
// MEMBERSHIP ONLY — no burst order; the engine assigns burst roles. A slot is
// both a drop target and a drag source, so a unit dropped in the wrong deck
// is moved rather than removed and re-added.

import { useState } from 'react'
import type { Draft, DraftSeat } from '../types/draft'
import { MAX_DRAFT_SEATS_PER_DECK } from '../types/draft'
import type { DraftDeck } from '../types/recommend'
import type { BurstTier } from '../types/supportedUnit'
import { DRAG_SLUG_TYPE } from './UnitPalette'

interface DraftEditorProps {
  numDecks: number
  value: Draft
  onChange: (next: Draft) => void
  /** Resolves a slug's portrait, so a slot shows the same face that was
   * dragged into it. Null for a slug with no portrait. */
  portraitFor: (slug: string) => string | null
  /** The unit's name. Slots show no name text, so this is what labels the
   * slot's controls for anyone not looking at pixels. */
  nameFor: (slug: string) => string
  /** Every burst tier the slug can be seated at, nominal one first, empty when
   * it is not a supported unit. The only badge a slot carries: a deck needs
   * tiers 1, 2 and 3 to be feasible, and with names gone there is nothing else
   * to read that from. Plural because a character the engine fans out can hold
   * more than one (`burstTiersFor`); the slot draws the nominal one. */
  burstTiersFor: (slug: string) => BurstTier[]
  /** A lock means "the optimizer must keep this unit here" - meaningless on
   * a screen that only scores a placed squad, with no search to constrain.
   * Defaults on, matching the draft editor's existing behavior. */
  showLocks?: boolean
  /** Slugs whose seat the player may not vacate — the Miranda calculator seats
   * her itself and asks for the other four. Removing, dragging out, and being
   * swapped away all have to be closed: a swap displaces the occupant, so
   * closing the first two alone leaves a back door. */
  fixedSlugs?: string[]
}

const TIER_NUMERALS = ['I', 'II', 'III'] as const

/* Drawn rather than set as an emoji: at the 18px a slot corner allows, the
   emoji padlock renders as a coloured smudge that fights the art behind it.
   One glyph for both states - locked/unlocked is carried by aria-pressed and
   by the accent fill, not by a second shape. */
const LockGlyph = () => (
  <svg viewBox="0 0 24 24" width="11" height="11" fill="currentColor" aria-hidden="true">
    <path d="M12 2a5 5 0 0 0-5 5v2H5.5A1.5 1.5 0 0 0 4 10.5v9A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5v-9A1.5 1.5 0 0 0 18.5 9H17V7a5 5 0 0 0-5-5zm0 2a3 3 0 0 1 3 3v2H9V7a3 3 0 0 1 3-3z" />
  </svg>
)

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

/**
 * Seats `slug` in `deckIndex`, taking it out of whichever deck currently
 * holds it. This is the one path every drop goes through: a slug dragged from
 * the palette is not seated anywhere, so the "take it out" half no-ops and
 * the result is a plain placement.
 *
 * The target's capacity is checked BEFORE the removal, so a move refused for
 * a full deck leaves the unit where it was instead of deleting it.
 */
export const moveUnit = (draft: Draft, deckIndex: number, slug: string): Draft => {
  const fromIndex = draft.decks.findIndex((seats) => seats.some((seat) => seat.slug === slug))
  if (fromIndex === deckIndex) return draft
  const targetDeck = draft.decks[deckIndex]
  if (!targetDeck || targetDeck.length >= MAX_DRAFT_SEATS_PER_DECK) return draft
  if (fromIndex === -1) return placeUnit(draft, deckIndex, slug)
  // A locked unit stays locked when it changes decks: the lock says "keep
  // this one in the deck I put it in", and moving it is me saying where.
  const { locked } = draft.decks[fromIndex].find((seat) => seat.slug === slug)!
  return placeUnit(removeUnitBySlug(draft, slug), deckIndex, slug, locked)
}

/**
 * Trades two seated units between the decks that hold them.
 *
 * The plain move refuses a full deck, and correctly - it would have to drop
 * somebody. A trade does not: it is one unit out for one unit in on both
 * sides, so neither deck changes size and two full decks can still deal with
 * each other. Each unit carries its own lock across, the same rule `moveUnit`
 * follows.
 *
 * Trading within one deck is a no-op: seat order inside a deck is membership
 * only, so it would be a move that changes no answer.
 */
export const swapUnits = (draft: Draft, slug: string, otherSlug: string): Draft => {
  const deckOf = (wanted: string) =>
    draft.decks.findIndex((seats) => seats.some((seat) => seat.slug === wanted))
  const from = deckOf(slug)
  const to = deckOf(otherSlug)
  if (from === -1 || to === -1 || from === to) return draft
  const seatOf = (deckIndex: number, wanted: string) =>
    draft.decks[deckIndex].find((seat) => seat.slug === wanted)!
  const moving = seatOf(from, slug)
  const displaced = seatOf(to, otherSlug)
  return {
    decks: draft.decks.map((seats, index) => {
      if (index === from) return seats.map((seat) => (seat.slug === slug ? displaced : seat))
      if (index === to) return seats.map((seat) => (seat.slug === otherSlug ? moving : seat))
      return seats
    }),
  }
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

/** Which of burst tiers 1/2/3 no seat in this deck covers. A deck missing one
 * cannot be fielded, and a partly-filled deck can still be rescued — so this
 * reports the gap rather than waiting for the backend's 422.
 *
 * A seat covers EVERY tier its unit can be seated at (`burstTiersFor`), not
 * just the nominal one: the engine, not the player, settles which mode a
 * fanned-out character runs in. It stays the weak check it has always been —
 * it says nothing about deck SHAPE, which is the backend's 422 to give. */
export const missingBurstTiers = (
  seats: DraftSeat[],
  burstTiersFor: (slug: string) => BurstTier[],
): number[] => {
  const present = new Set(seats.flatMap((seat) => burstTiersFor(seat.slug)))
  return [1, 2, 3].filter((tier) => !present.has(tier as BurstTier))
}

export function DraftEditor({
  numDecks,
  value,
  onChange,
  portraitFor,
  nameFor,
  burstTiersFor,
  showLocks = true,
  fixedSlugs = [],
}: DraftEditorProps) {
  // A slot draws ONE numeral and the rows sort by ONE tier, so both read the
  // nominal tier - the first - and leave the rest to missingBurstTiers.
  const nominalTierFor = (slug: string): BurstTier | null => burstTiersFor(slug)[0] ?? null
  const fixedSet = new Set(fixedSlugs)
  // Which deck the pointer is currently over during a drag, so the target
  // reads as a target before the player commits to the drop.
  const [dropTarget, setDropTarget] = useState<number | null>(null)
  // The seat under the pointer, which is a different promise: dropping on a
  // deck seats a unit, dropping on a seat trades with its occupant.
  const [swapTarget, setSwapTarget] = useState<string | null>(null)

  const handleDrop = (event: React.DragEvent, deckIndex: number) => {
    const slug = event.dataTransfer.getData(DRAG_SLUG_TYPE)
    setDropTarget(null)
    if (!slug) return
    event.preventDefault()
    onChange(moveUnit(value, deckIndex, slug))
  }

  const handleSeatDrop = (event: React.DragEvent, deckIndex: number, occupant: string) => {
    const slug = event.dataTransfer.getData(DRAG_SLUG_TYPE)
    setSwapTarget(null)
    if (!slug) return
    event.preventDefault()
    // The seat sits inside the deck, so without this the deck would handle the
    // same drop again as a plain move.
    event.stopPropagation()
    setDropTarget(null)
    if (fixedSet.has(occupant)) return
    const seated = value.decks.some((seats) => seats.some((seat) => seat.slug === slug))
    onChange(seated ? swapUnits(value, slug, occupant) : moveUnit(value, deckIndex, slug))
  }

  // Membership, not seating: the search sorts every deck it builds into tier
  // order and permutes within a tier, so ordering the row here changes nothing
  // it reads. The stored index rides along because the slot controls act on a
  // position in the STORED deck, which this no longer matches.
  const inTierOrder = (seats: DraftSeat[]) =>
    seats
      .map((seat, seatIndex) => ({ seat, seatIndex }))
      .sort((a, b) => (nominalTierFor(a.seat.slug) ?? 4) - (nominalTierFor(b.seat.slug) ?? 4))

  return (
    <div className="draft-editor">
      <p className="draft-editor__hint">
        유닛을 덱 위로 드래그하면 배치돼요. 다른 덱의 빈자리로 드래그하면 옮겨지고,
        다른 덱의 유닛 위로 드래그하면 둘이 자리를 바꿔요. 슬롯은 소속만 나타내며,
        버스트 순서는 엔진이 정해요.
      </p>
      <div className="draft-editor__decks">
        {Array.from({ length: numDecks }, (_, deckIndex) => {
          const seats = value.decks[deckIndex] ?? []
          const full = seats.length >= MAX_DRAFT_SEATS_PER_DECK
          const missing = seats.length > 0 ? missingBurstTiers(seats, burstTiersFor) : []
          return (
            <div
              className={
                dropTarget === deckIndex
                  ? 'draft-editor__deck draft-editor__deck--drop-target'
                  : 'draft-editor__deck'
              }
              key={deckIndex}
              // Only preventDefault for a real unit drag: the default action is
              // what refuses the drop, and refusing is right for anything else.
              onDragOver={(event) => {
                if (full || !event.dataTransfer.types.includes(DRAG_SLUG_TYPE)) return
                event.preventDefault()
                event.dataTransfer.dropEffect = 'move'
                setDropTarget(deckIndex)
              }}
              onDragLeave={() => setDropTarget((current) => (current === deckIndex ? null : current))}
              onDrop={(event) => handleDrop(event, deckIndex)}
            >
              <h4 className="draft-editor__deck-title">
                덱 {deckIndex + 1}
                {missing.length > 0 && (
                  <span className="draft-editor__deck-warning">
                    {missing.map((tier) => `B${tier}`).join(', ')} 없음
                  </span>
                )}
                <span className="draft-editor__deck-count">
                  {seats.length}/{MAX_DRAFT_SEATS_PER_DECK}
                </span>
              </h4>
              <ul className="draft-editor__slots">
                {inTierOrder(seats).map(({ seat, seatIndex }) => {
                  const portrait = portraitFor(seat.slug)
                  const name = nameFor(seat.slug)
                  const tier = nominalTierFor(seat.slug)
                  const where = `덱 ${deckIndex + 1}`
                  const isFixed = fixedSet.has(seat.slug)
                  return (
                    <li
                      key={seat.slug}
                      className={[
                        'draft-editor__slot',
                        swapTarget === seat.slug ? 'draft-editor__slot--swap-target' : '',
                        isFixed ? 'draft-editor__slot--fixed' : '',
                      ].filter(Boolean).join(' ')}
                      // A seat accepts a drop even when its deck is full: a
                      // trade is one out for one in, so the deck's capacity
                      // never comes into it.
                      onDragOver={(event) => {
                        if (!event.dataTransfer.types.includes(DRAG_SLUG_TYPE)) return
                        event.preventDefault()
                        event.stopPropagation()
                        event.dataTransfer.dropEffect = 'move'
                        if (!isFixed) setSwapTarget(seat.slug)
                      }}
                      onDragLeave={() =>
                        setSwapTarget((current) => (current === seat.slug ? null : current))
                      }
                      onDrop={(event) => handleSeatDrop(event, deckIndex, seat.slug)}
                    >
                      <div
                        className="draft-editor__slot-grip"
                        draggable={!isFixed}
                        onDragStart={(event) => {
                          // draggable={false} on the grip does not stop a
                          // native-draggable descendant (the <img> portrait)
                          // from starting its own drag that bubbles up here -
                          // the handler has to refuse it too, not just the
                          // attribute.
                          if (isFixed) {
                            event.preventDefault()
                            return
                          }
                          event.dataTransfer.setData(DRAG_SLUG_TYPE, seat.slug)
                          event.dataTransfer.effectAllowed = 'move'
                        }}
                      >
                        {portrait ? (
                          <img className="draft-editor__slot-portrait" src={portrait} alt={name} />
                        ) : (
                          <span className="draft-editor__slot-portrait draft-editor__slot-portrait--missing">
                            {name}
                          </span>
                        )}
                        {tier !== null && (
                          <span className="draft-editor__slot-tier" aria-hidden="true">
                            {TIER_NUMERALS[tier - 1]}
                          </span>
                        )}
                      </div>
                      {showLocks && (
                        <button
                          type="button"
                          className="draft-editor__slot-lock"
                          aria-pressed={seat.locked}
                          aria-label={`${where}에서 ${name} 고정`}
                          onClick={() => onChange(toggleLock(value, deckIndex, seatIndex))}
                        >
                          <LockGlyph />
                        </button>
                      )}
                      {!isFixed && (
                        <button
                          type="button"
                          className="draft-editor__slot-remove"
                          aria-label={`${where}에서 ${name} 제거`}
                          onClick={() => onChange(removeUnit(value, deckIndex, seatIndex))}
                        >
                          <span aria-hidden="true">×</span>
                        </button>
                      )}
                    </li>
                  )
                })}
                {/* Open slots are drawn, not implied: they enlarge the drop
                    target and show remaining capacity without counting. The
                    count in the title already states it for a screen reader. */}
                {Array.from({ length: MAX_DRAFT_SEATS_PER_DECK - seats.length }, (_, i) => (
                  <li
                    key={`open-${i}`}
                    className="draft-editor__slot draft-editor__slot--open"
                    aria-hidden="true"
                  >
                    <span className="draft-editor__slot-plus">+</span>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}
