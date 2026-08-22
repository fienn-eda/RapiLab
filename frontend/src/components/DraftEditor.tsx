// The draft-editor's deck grid (frontend/README.md "UI scope — draft
// editor"): numDecks columns x exactly 5 slots each, drawn like the game's
// squad slots — a square face, or a `+` for an open slot. Slots are
// MEMBERSHIP ONLY — no burst order; the engine assigns burst roles. A slot is
// both a drop target and a drag source, so a unit dropped in the wrong deck
// is moved rather than removed and re-added.
//
// Pressing a seat's face picks it up; pressing that same seat again vacates
// it, and Esc cancels the pick-up. With a unit held, pressing anywhere inside
// a deck puts it there; with nothing held, pressing a deck makes it the active
// one. Pressing a palette chip fills an open seat, or swaps into the held seat
// if one is held - the palette lives outside this component (in the parent
// panel), so onHeldSlugChange carries what is held across the boundary.
// Dragging still works in a browser but cannot be the way in: the packaged
// app's WebView2 fires `dragstart` and then delivers no drop.

import { useEffect, useState } from 'react'
import type { Draft, DraftSeat } from '../types/draft'
import { MAX_DRAFT_SEATS_PER_DECK } from '../types/draft'
import type { DraftDeck } from '../types/recommend'
import type { BurstTier } from '../types/supportedUnit'
import { HELP } from '../lib/helpText'
import type { BossHeading } from '../lib/bossLabel'
import { HelpText } from './HelpText'
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
  /** Which deck a palette press seats into. The palette sits outside this
   * component, so the choice is the caller's to hold. */
  activeDeck?: number
  /** Omit where the player has no say — with one deck there is nothing to
   * choose, so no picker is drawn and the concept never appears. */
  onActiveDeckChange?: (deckIndex: number) => void
  /** 덱마다 그 덱이 무엇인지 부르는 이름. 유니온만 넘긴다 - 솔로는 덱이 여럿
   * 이어도 보스가 하나라 덱마다 다르게 부를 것이 없다. 없으면 자리 번호로
   * 부른다. */
  deckLabels?: BossHeading[]
  /** 지금 들려 있는 유닛을 알린다. 팔레트가 이 컴포넌트 밖에 있어서, 팔레트를
   * 눌렀을 때 무엇과 바꿀지 부모가 알아야 한다. 든 유닛을 쥔 것은 이 컴포넌트
   * 하나이고 바뀔 때마다 - 편성에서 사라질 때도, 언마운트될 때도 - 빠짐없이
   * 알리므로, 부모의 사본은 언제나 이것의 그림자다. */
  onHeldSlugChange?: (slug: string | null) => void
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

/** Whether `slug` occupies a seat in any deck. A slug sits in at most one. */
const isSeated = (draft: Draft, slug: string): boolean =>
  draft.decks.some((seats) => seats.some((seat) => seat.slug === slug))

/** Places `slug` into `draft.decks[deckIndex]`. No-ops (returns `draft`
 * unchanged) if the slug is already drafted anywhere, or the target deck is
 * already full — the two client-side invariants the editor enforces. */
export const placeUnit = (
  draft: Draft,
  deckIndex: number,
  slug: string,
  locked = false,
): Draft => {
  if (isSeated(draft, slug)) return draft
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

/** `replacedSlug`가 있던 자리에 `slug`를 앉힌다. 자리를 그대로 물려받으므로
 * 덱이 꽉 차 있어도 된다 - 하나 나가고 하나 들어온다. */
export const replaceUnit = (draft: Draft, replacedSlug: string, slug: string): Draft => ({
  decks: draft.decks.map((seats) =>
    seats.map((seat) => (seat.slug === replacedSlug ? { slug, locked: seat.locked } : seat)),
  ),
})

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
  activeDeck = 0,
  onActiveDeckChange,
  deckLabels,
  onHeldSlugChange,
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

  // 든 유닛. 「누르면 제거」와 「누르면 이동」을 한 제스처로 잇는 상태다 -
  // 드래그가 앱에서 죽어 있어 이동은 클릭 두 번으로만 만들 수 있다. 좌표가
  // 아니라 슬러그로 쥔다: 좌표는 밖에서 value가 바뀌면 그 자리에 새로 온 다른
  // 유닛을 가리키지만, 슬러그는 그 유닛이 편성에 있는 한 언제나 그 유닛이다.
  const [heldSlug, setHeldSlugState] = useState<string | null>(null)

  // 든 유닛을 바꾸는 유일한 통로. 팔레트가 이 컴포넌트 밖에 있어서 부모도
  // 무엇이 들렸는지 알아야 하고 - 팔레트 클릭을 "빈자리에 앉히기"와 "든
  // 유닛과 맞바꾸기"로 가르는 데 쓴다 - 한 번이라도 안 알리면 부모의 사본이
  // 조용히 낡는다.
  const setHeld = (next: string | null) => {
    setHeldSlugState(next)
    onHeldSlugChange?.(next)
  }

  // 든 유닛이 편성에서 사라지면 든 것도 없다: 보관물을 복원해 value가 통째로
  // 바뀌거나, 니케 풀 탭에서 제외되거나, 팔레트가 그 자리를 대신 채웠을 때다.
  // 지우지 않으면 화면에는 든 표시가 없는데 다음 클릭만 없는 유닛과
  // 맞바꾸려다 아무 일도 없이 삼켜진다.
  useEffect(() => {
    if (heldSlug !== null && !isSeated(value, heldSlug)) setHeld(null)
  }, [heldSlug, value])

  // 이 컴포넌트가 사라지면 든 것도 사라진다 - 모드를 바꾸면 편성 칸째로
  // 언마운트된다. 부모의 사본은 이 알림으로만 갱신되므로, 여기서 안 내리면
  // 돌아왔을 때 화면엔 든 것이 없는데 팔레트 클릭만 맞바꾸기로 튄다.
  useEffect(() => () => onHeldSlugChange?.(null), [])

  // 집었다가 마음이 바뀌었을 때의 출구. 같은 좌석을 다시 누르는 것은 제거라
  // 취소로 쓸 수 없다.
  useEffect(() => {
    if (heldSlug === null) return
    const cancel = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setHeld(null)
    }
    window.addEventListener('keydown', cancel)
    return () => window.removeEventListener('keydown', cancel)
  }, [heldSlug])

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
    onChange(
      isSeated(value, slug)
        ? swapUnits(value, slug, occupant)
        : moveUnit(value, deckIndex, slug),
    )
  }

  // Membership, not seating: the search sorts every deck it builds into tier
  // order and permutes within a tier, so ordering the row here changes nothing
  // it reads. The stored index rides along because the slot controls act on a
  // position in the STORED deck, which this no longer matches.
  const inTierOrder = (seats: DraftSeat[]) =>
    seats
      .map((seat, seatIndex) => ({ seat, seatIndex }))
      .sort((a, b) => (nominalTierFor(a.seat.slug) ?? 4) - (nominalTierFor(b.seat.slug) ?? 4))

  // One deck leaves nothing to choose, and a caller that does not hold the
  // choice cannot honour it either.
  const picksDeck = onActiveDeckChange !== undefined && numDecks > 1

  return (
    <div className="draft-editor">
      {/* 접힌 상태에서는 이 박스가 곧 summary라, 박스 아무 데나 눌러도 열린다.
          내용까지 토글 대상으로 삼지 않는 이유는 읽는 문단이기 때문이다 -
          거기까지 클릭을 먹으면 문장을 드래그해 읽을 수가 없다. */}
      <details className="draft-editor__usage">
        <summary>사용 방법</summary>
        <p className="draft-editor__hint">
          <HelpText>
            {(picksDeck ? HELP.draft.seatHintWithDeckPick : HELP.draft.seatHintSingleDeck) +
              HELP.draft.seatHintCommon}
          </HelpText>
        </p>
      </details>
      <div className="draft-editor__decks">
        {Array.from({ length: numDecks }, (_, deckIndex) => {
          const seats = value.decks[deckIndex] ?? []
          const full = seats.length >= MAX_DRAFT_SEATS_PER_DECK
          const missing = seats.length > 0 ? missingBurstTiers(seats, burstTiersFor) : []
          const label = deckLabels?.[deckIndex] ?? null
          const deckName = label?.text ?? `덱 ${deckIndex + 1}`
          // 누를 수 있을 때만 손 모양이 뜬다. 든 것이 있으면 꽉 찬 덱은 받지
          // 못하므로 그때는 표적이 아니다.
          const pressable = heldSlug !== null ? !full : picksDeck
          return (
            <div
              className={[
                'draft-editor__deck',
                dropTarget === deckIndex ? 'draft-editor__deck--drop-target' : '',
                picksDeck && activeDeck === deckIndex ? 'draft-editor__deck--active' : '',
                pressable ? 'draft-editor__deck--pressable' : '',
              ].filter(Boolean).join(' ')}
              // 이 덱이 맡은 보스의 약점 속성. App.css 맨 위의 배선이 이걸 보고
              // --element를 세우고, 덱 이름이 켜질 때 그 색을 읽는다. 보스를
              // 아직 안 고른 덱은 속성이 없어 --element도 안 선다.
              data-element={label?.weakness ?? undefined}
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
              // 덱 테두리 안 전체가 표적이다. 안쪽 컨트롤은 저마다 전파를 끊어
              // 자기 몫을 가져가므로, 여기 닿는 것은 「덱을 눌렀다」뿐이다.
              onClick={() => {
                if (heldSlug !== null) {
                  const next = moveUnit(value, deckIndex, heldSlug)
                  // moveUnit은 꽉 찬 덱과 「이미 그 덱」을 거절하며 같은 객체를
                  // 돌려준다. 거절당했는데 든 것을 내려놓으면, 화면에서 유닛이
                  // 조용히 사라진 것처럼 보인다.
                  if (next === value) return
                  onChange(next)
                  setHeld(null)
                  onActiveDeckChange?.(deckIndex)
                  return
                }
                if (picksDeck) onActiveDeckChange(deckIndex)
              }}
            >
              <h4 className="draft-editor__deck-title">
                {label?.iconSrc && (
                  <img className="draft-editor__deck-icon" src={label.iconSrc} alt="" />
                )}
                {picksDeck ? (
                  // A toggle, so it reports which deck the next `+` will fill
                  // rather than reading as a button that does something once.
                  <button
                    type="button"
                    className="draft-editor__deck-pick"
                    aria-pressed={activeDeck === deckIndex}
                    // 조사 없이 쓴다 - 「덱 N을/를」은 N을 읽은 소리의 받침이
                    // 정하는데(1·3·6·7·8은 을, 2·4·5·9는 를), 그걸 위해 숫자
                    // 읽기 표를 들일 만한 문장이 아니다. 자리 번호를 앞에 두어
                    // 보스 이름으로 불러도 몇 번째인지 잃지 않는다.
                    // label.iconSrc로 가른다(label 자체가 아니라) - 유니온은
                    // 보스를 아직 안 고른 덱에도 폴백 라벨을 채워 보내서,
                    // label만 보면 "덱 2 덱 2 활성 덱으로 선택"으로 겹쳐
                    // 읽힌다. iconSrc는 진짜 이름이 있을 때만 채워진다
                    // (bossLabel.ts) - 아이콘을 그리는 조건과 같다.
                    aria-label={
                      label?.iconSrc
                        ? `덱 ${deckIndex + 1} ${deckName} 활성 덱으로 선택`
                        : `덱 ${deckIndex + 1} 활성 덱으로 선택`
                    }
                    onClick={(event) => {
                      // 든 채로는 이름도 놓는 자리다 - 표적 한가운데에 죽은
                      // 띠를 두지 않는다. 껍데기가 이동으로 처리하도록
                      // 흘려보낸다.
                      if (heldSlug !== null) return
                      event.stopPropagation()
                      onActiveDeckChange(deckIndex)
                    }}
                  >
                    {deckName}
                  </button>
                ) : (
                  <>{deckName}</>
                )}
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
                  // Drawn once: the two grips below differ only in whether
                  // they can be pressed, never in what they show.
                  const slotFace = (
                    <>
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
                    </>
                  )
                  return (
                    <li
                      key={seat.slug}
                      className={[
                        'draft-editor__slot',
                        swapTarget === seat.slug ? 'draft-editor__slot--swap-target' : '',
                        isFixed ? 'draft-editor__slot--fixed' : '',
                        heldSlug === seat.slug ? 'draft-editor__slot--held' : '',
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
                      {/* The seat's own face is what vacates it. A 14px `×` in
                          the corner used to be the only way out, which is a
                          small target for the thing a player does most while
                          drafting. A fixed seat stays a plain div - it cannot
                          be vacated, so it must not look pressable. */}
                      {isFixed ? (
                        <div
                          className="draft-editor__slot-grip"
                          // draggable={false} does not stop a native-draggable
                          // descendant (the <img> portrait) from starting its
                          // own drag that bubbles up here - the handler has to
                          // refuse it too, not just the attribute.
                          onDragStart={(event) => event.preventDefault()}
                          // 고정 좌석은 드롭도 거절한다(handleSeatDrop과 같은
                          // 규칙). 안 끊으면 덱 껍데기가 이 클릭을 「이 덱에
                          // 놓기」로 받아, 못 건드린다고 말한 자리를 눌러
                          // 유닛이 그 덱에 들어간다.
                          onClick={(event) => event.stopPropagation()}
                        >
                          {slotFace}
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="draft-editor__slot-grip"
                          aria-label={`덱 ${deckIndex + 1}의 ${name}`}
                          draggable
                          onDragStart={(event) => {
                            event.dataTransfer.setData(DRAG_SLUG_TYPE, seat.slug)
                            event.dataTransfer.effectAllowed = 'move'
                          }}
                          onClick={(event) => {
                            // 좌석은 자기 몫을 여기서 끝낸다. 안 끊으면 덱
                            // 껍데기가 같은 클릭을 이동으로 한 번 더 처리한다 -
                            // 아래에서 내려놓아도 껍데기가 읽는 heldSlug는 같은
                            // 배치 안이라 아직 옛 값이다.
                            event.stopPropagation()
                            if (heldSlug === seat.slug) {
                              onChange(removeUnit(value, deckIndex, seatIndex))
                              setHeld(null)
                              return
                            }
                            if (heldSlug !== null) {
                              // 차 있는 자리에 놓는 것은 교환이다 - 드래그 드롭이
                              // 이미 그렇게 해서 두 경로가 같은 규칙이 된다.
                              onChange(swapUnits(value, heldSlug, seat.slug))
                              setHeld(null)
                              return
                            }
                            setHeld(seat.slug)
                          }}
                        >
                          {slotFace}
                        </button>
                      )}
                      {showLocks && (
                        <button
                          type="button"
                          className="draft-editor__slot-lock"
                          aria-pressed={seat.locked}
                          aria-label={`${where}에서 ${name} 고정`}
                          onClick={(event) => {
                            event.stopPropagation()
                            onChange(toggleLock(value, deckIndex, seatIndex))
                          }}
                        >
                          <LockGlyph />
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
                    // 들고 있을 때 첫 빈자리만 놓을 수 있다. 누를 수 없는
                    // 것을 버튼으로 보이게 하지 않으려고 그때만 버튼이 되고,
                    // 접근성 트리 노출도 그 하나로 한정한다 - 나머지 넷까지
                    // 노출하면 스크린리더가 덱마다 "+"를 여러 번 읽는다.
                    aria-hidden={heldSlug !== null && i === 0 ? undefined : 'true'}
                  >
                    {heldSlug !== null && i === 0 ? (
                      <button
                        type="button"
                        className="draft-editor__slot-plus"
                        aria-label={`덱 ${deckIndex + 1}에 놓기`}
                        // 핸들러가 없는 것이 맞다: 누르면 덱 껍데기가 이동으로
                        // 받는다(키보드의 Enter/Space도 click을 올려보낸다).
                        // 같은 일을 하는 핸들러를 두 벌 두면 조용히 갈라진다.
                        // 버튼으로 남기는 것은 접근성 트리에 노출되는 유일한
                        // 놓기 컨트롤이기 때문이다.
                      >
                        +
                      </button>
                    ) : (
                      <span className="draft-editor__slot-plus">+</span>
                    )}
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
