import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  DraftEditor,
  missingBurstTiers,
  moveUnit,
  placeUnit,
  removeUnit,
  removeUnitBySlug,
  swapUnits,
  toggleLock,
  toRequestDraft,
} from './DraftEditor'
import { DRAG_SLUG_TYPE } from './UnitPalette'
import type { Draft } from '../types/draft'
import type { BurstTier } from '../types/supportedUnit'
import { makeEmptyDraft, MAX_DRAFT_SEATS_PER_DECK } from '../types/draft'
import { nameFromSlug } from '../lib/unitName'

describe('placeUnit', () => {
  it('adds a unit to the target deck', () => {
    const draft = makeEmptyDraft(2)
    const next = placeUnit(draft, 0, 'crown')
    expect(next.decks[0]).toEqual([{ slug: 'crown', locked: false }])
    expect(next.decks[1]).toEqual([])
  })

  it('rejects a 6th unit into an already-full deck', () => {
    const full: Draft = {
      decks: [
        ['a', 'b', 'c', 'd', 'e'].map((slug) => ({ slug, locked: false })),
      ],
    }
    const next = placeUnit(full, 0, 'f')
    expect(next).toEqual(full)
    expect(next.decks[0]).toHaveLength(5)
  })

  it('rejects placing the same slug twice, even into a different deck', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }
    const next = placeUnit(draft, 1, 'crown')
    expect(next).toEqual(draft)
    expect(next.decks[1]).toEqual([])
  })
})

describe('moveUnit', () => {
  it('relocates a seated unit to another deck', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }
    const next = moveUnit(draft, 1, 'crown')
    expect(next.decks[0]).toEqual([])
    expect(next.decks[1]).toEqual([{ slug: 'crown', locked: false }])
  })

  it('keeps the unit locked across the move', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: true }], []] }
    expect(moveUnit(draft, 1, 'crown').decks[1]).toEqual([{ slug: 'crown', locked: true }])
  })

  it('places an unseated slug, exactly as a palette drop always did', () => {
    const draft = makeEmptyDraft(2)
    expect(moveUnit(draft, 1, 'crown').decks[1]).toEqual([{ slug: 'crown', locked: false }])
  })

  // The capacity check has to happen BEFORE the removal, or a refused move
  // would delete the unit instead of leaving it where it was.
  it('leaves the unit in place when the target deck is full', () => {
    const draft: Draft = {
      decks: [
        [{ slug: 'crown', locked: true }],
        ['a', 'b', 'c', 'd', 'e'].map((slug) => ({ slug, locked: false })),
      ],
    }
    const next = moveUnit(draft, 1, 'crown')
    expect(next).toEqual(draft)
    expect(next.decks[0]).toEqual([{ slug: 'crown', locked: true }])
  })

  it('no-ops when dropped back on the deck it already sits in', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }
    expect(moveUnit(draft, 0, 'crown')).toBe(draft)
  })
})

describe('missingBurstTiers', () => {
  const tiersOf = (slug: string) =>
    (({ crown: [1], liter: [2], blanc: [3], 'rapi-red-hood': [3, 1] }) as Record<
      string,
      BurstTier[]
    >)[slug] ?? []

  it('reports the tiers no seat covers', () => {
    expect(missingBurstTiers([{ slug: 'crown', locked: false }], tiersOf)).toEqual([2, 3])
  })

  it('reports nothing once all three tiers are seated', () => {
    const seats = ['crown', 'liter', 'blanc'].map((slug) => ({ slug, locked: false }))
    expect(missingBurstTiers(seats, tiersOf)).toEqual([])
  })

  it('counts a seat the engine may move between tiers as covering either', () => {
    // 라피: 레드후드는 B3로도 B1로도 앉는다. 다른 B1이 없으면 엔진이 그녀를
    // B1로 앉히므로, 이 덱을 두고 "B1 없음"이라 말하면 거짓이다.
    const seats = ['rapi-red-hood', 'liter', 'blanc'].map((slug) => ({ slug, locked: false }))
    expect(missingBurstTiers(seats, tiersOf)).toEqual([])
  })
})

describe('toggleLock', () => {
  it('flips a seat\'s locked flag', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const next = toggleLock(draft, 0, 0)
    expect(next.decks[0][0]).toEqual({ slug: 'crown', locked: true })
  })
})

describe('removeUnit', () => {
  it('removes a seat from its deck', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: false }, { slug: 'liter', locked: true }]] }
    const next = removeUnit(draft, 0, 0)
    expect(next.decks[0]).toEqual([{ slug: 'liter', locked: true }])
  })
})

describe('removeUnitBySlug', () => {
  it('removes a placed slug from whichever deck holds it', () => {
    let draft = makeEmptyDraft(2)
    draft = placeUnit(draft, 1, 'liter')
    const next = removeUnitBySlug(draft, 'liter')
    expect(next.decks[1]).toEqual([])
  })

  it('returns the draft unchanged when the slug is not placed', () => {
    const draft = placeUnit(makeEmptyDraft(2), 0, 'crown')
    expect(removeUnitBySlug(draft, 'liter')).toBe(draft)
  })
})

describe('toRequestDraft', () => {
  it('converts populated decks to the wire shape', () => {
    const draft: Draft = {
      decks: [
        [{ slug: 'crown', locked: true }, { slug: 'liter', locked: false }],
        [],
      ],
    }
    expect(toRequestDraft(draft)).toEqual([
      { units: [{ slug: 'crown', locked: true }, { slug: 'liter', locked: false }] },
    ])
  })

  it('omits empty decks entirely', () => {
    const draft = makeEmptyDraft(3)
    expect(toRequestDraft(draft)).toEqual([])
  })
})

describe('swapUnits', () => {
  const seat = (slug: string, locked = false) => ({ slug, locked })

  it('trades two units between the decks that hold them', () => {
    const draft: Draft = { decks: [[seat('crown')], [seat('blanc')]] }
    expect(swapUnits(draft, 'crown', 'blanc')).toEqual({
      decks: [[seat('blanc')], [seat('crown')]],
    })
  })

  // A lock says "keep this one in the deck I put it in", so it belongs to the
  // unit and travels with it - the same rule moveUnit follows.
  it('sends each unit across with its own lock', () => {
    const draft: Draft = { decks: [[seat('crown', true)], [seat('blanc')]] }
    expect(swapUnits(draft, 'crown', 'blanc')).toEqual({
      decks: [[seat('blanc')], [seat('crown', true)]],
    })
  })

  it('leaves the neighbours of both seats alone', () => {
    const draft: Draft = {
      decks: [[seat('a'), seat('crown'), seat('b')], [seat('c'), seat('blanc')]],
    }
    expect(swapUnits(draft, 'crown', 'blanc')).toEqual({
      decks: [[seat('a'), seat('blanc'), seat('b')], [seat('c'), seat('crown')]],
    })
  })

  // Seat order inside a deck means nothing to the engine, so trading two of
  // one deck's own seats would be a move that changes no answer.
  it('does nothing inside a single deck', () => {
    const draft: Draft = { decks: [[seat('crown'), seat('blanc')]] }
    expect(swapUnits(draft, 'crown', 'blanc')).toEqual(draft)
  })

  it('does nothing when either unit is not drafted', () => {
    const draft: Draft = { decks: [[seat('crown')], []] }
    expect(swapUnits(draft, 'crown', 'blanc')).toEqual(draft)
    expect(swapUnits(draft, 'blanc', 'crown')).toEqual(draft)
  })
})

describe('DraftEditor', () => {
  const TIERS: Record<string, BurstTier[]> = {
    crown: [1],
    liter: [2],
    blanc: [3],
    // 엔진이 티어를 골라 앉히는 캐릭터. 라피: 레드후드가 그런 유일한 경우다.
    'rapi-red-hood': [3, 1],
  }

  const editor = (
    numDecks: number,
    value: Draft,
    onChange: (next: Draft) => void = () => {},
    showLocks?: boolean,
  ) =>
    render(
      <DraftEditor
        numDecks={numDecks}
        value={value}
        onChange={onChange}
        portraitFor={() => null}
        nameFor={nameFromSlug}
        burstTiersFor={(slug: string) => TIERS[slug] ?? []}
        showLocks={showLocks}
      />,
    )

  // A slot shows a face and no name, so what identifies it in the a11y tree
  // is its controls - which is also all a keyboard user has to work with.
  it('names a seated unit through its slot controls rather than visible text', () => {
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }
    editor(2, value)
    expect(screen.getByRole('heading', { name: /덱 1/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /덱 2/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '덱 1의 Crown' })).toBeInTheDocument()
    expect(screen.queryByText('crown')).not.toBeInTheDocument()
  })

  // Five slots always, so the deck is a fixed-size drop target and the open
  // capacity is visible without counting occupied ones.
  it('draws every deck to a full five slots', () => {
    const { container } = editor(1, { decks: [[{ slug: 'crown', locked: false }]] })
    expect(container.querySelectorAll('.draft-editor__slot')).toHaveLength(
      MAX_DRAFT_SEATS_PER_DECK,
    )
    expect(container.querySelectorAll('.draft-editor__slot--open')).toHaveLength(
      MAX_DRAFT_SEATS_PER_DECK - 1,
    )
  })

  it('warns on the deck title when a burst tier is unrepresented', () => {
    editor(1, { decks: [[{ slug: 'crown', locked: false }]] })
    expect(screen.getByRole('heading', { name: /B2, B3 없음/ })).toBeInTheDocument()
  })

  it('says nothing about burst tiers for a deck with all three', () => {
    const seats = ['crown', 'liter', 'blanc'].map((slug) => ({ slug, locked: false }))
    editor(1, { decks: [seats] })
    expect(screen.queryByText(/없음$/)).not.toBeInTheDocument()
  })

  it('says nothing when the missing tier is one a seat can be moved to', () => {
    // 라피: 레드후드가 앉은 이 덱엔 다른 B1이 없다 - 그래서 엔진이 그녀를
    // B1로 앉히고, 이 편성은 실제로 성립한다. "B1 없음"은 유저가 인게임에서
    // 굴리는 편성을 못 쓰는 것으로 오해하게 만든다.
    const seats = ['rapi-red-hood', 'liter', 'blanc'].map((slug) => ({ slug, locked: false }))
    editor(1, { decks: [seats] })
    expect(screen.queryByText(/없음$/)).not.toBeInTheDocument()
  })

  it('flips a seat\'s lock via its toggle and reports the change through onChange', async () => {
    const user = userEvent.setup()
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const onChange = vi.fn()
    editor(1, value, onChange)

    const lock = screen.getByRole('button', { name: '덱 1에서 Crown 고정' })
    expect(lock).toHaveAttribute('aria-pressed', 'false')
    await user.click(lock)
    expect(onChange).toHaveBeenCalledWith({ decks: [[{ slug: 'crown', locked: true }]] })
  })

  // A screen that only scores a placed squad has no search to constrain, so
  // a lock toggle there would promise something the screen can't honor.
  it('hides the lock toggle when showLocks is false', () => {
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    editor(1, value, undefined, false)
    expect(screen.queryByRole('button', { pressed: false })).not.toBeInTheDocument()
  })

  it('shows the lock toggle by default, unchanged from before showLocks existed', () => {
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    editor(1, value)
    expect(screen.getByRole('button', { pressed: false })).toBeInTheDocument()
  })

  it('removes a seat when its control is pressed twice', async () => {
    const user = userEvent.setup()
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const onChange = vi.fn()
    editor(1, value, onChange)

    const seat = () => screen.getByRole('button', { name: '덱 1의 Crown' })
    await user.click(seat())
    await user.click(seat())
    expect(onChange).toHaveBeenCalledWith({ decks: [[]] })
  })

  it('덱 라벨을 넘기면 그 이름과 아이콘으로 부른다', () => {
    const { container } = render(
      <DraftEditor
        numDecks={2}
        value={makeEmptyDraft(2)}
        onChange={() => {}}
        portraitFor={() => null}
        nameFor={nameFromSlug}
        burstTiersFor={() => []}
        deckLabels={[
          { text: '인디비리아', iconSrc: '/elements/water.png' },
          { text: '수냉', iconSrc: '/elements/water.png' },
        ]}
      />,
    )
    expect(screen.getByRole('heading', { name: /인디비리아/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /수냉/ })).toBeInTheDocument()
    expect(container.querySelectorAll('.draft-editor__deck-icon')).toHaveLength(2)
  })

  it('덱 라벨이 없으면 지금처럼 자리 번호로 부른다', () => {
    editor(2, makeEmptyDraft(2))
    expect(screen.getByRole('heading', { name: /덱 1/ })).toBeInTheDocument()
  })

  // 좌석 컨트롤은 자리 번호를 유지한다 - 「인디비리아의 Crown」은 어느
  // 자리인지 말하지 않는다.
  it('좌석 컨트롤은 덱 라벨과 무관하게 자리 번호로 말한다', () => {
    render(
      <DraftEditor
        numDecks={1}
        value={{ decks: [[{ slug: 'crown', locked: false }]] }}
        onChange={() => {}}
        portraitFor={() => null}
        nameFor={nameFromSlug}
        burstTiersFor={(slug) => (slug === 'crown' ? [1] : [])}
        deckLabels={[{ text: '인디비리아', iconSrc: '/elements/water.png' }]}
      />,
    )
    // 그립·고정 두 컨트롤 다 확인한다 - 덱 라벨이 있어도 좌석 컨트롤은
    // 자리 번호로만 말한다.
    expect(screen.getByRole('button', { name: '덱 1의 Crown' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '덱 1에서 Crown 고정' })).toBeInTheDocument()
  })

  describe('burst-tier order', () => {
    const numerals = (container: HTMLElement) =>
      [...container.querySelectorAll('.draft-editor__slot-tier')].map((el) => el.textContent)

    // Slots carry membership, not seating: the search sorts every deck it
    // builds into tier order and permutes within a tier, so this reorders
    // nothing the engine reads. It makes "does this deck have a B2" a glance
    // instead of a hunt.
    it('draws a deck in burst-tier order however it was filled', () => {
      const { container } = editor(1, {
        decks: [[
          { slug: 'blanc', locked: false },
          { slug: 'crown', locked: false },
          { slug: 'liter', locked: false },
        ]],
      })
      expect(numerals(container)).toEqual(['I', 'II', 'III'])
    })

    it('puts a unit the engine does not know last', () => {
      const { container } = editor(1, {
        decks: [[{ slug: 'stranger', locked: false }, { slug: 'crown', locked: false }]],
      })
      const shown = [...container.querySelectorAll('.draft-editor__slot-portrait--missing')]
      expect(shown.map((el) => el.textContent)).toEqual([
        nameFromSlug('crown'), nameFromSlug('stranger'),
      ])
    })

    // The slot controls act on a position in the STORED deck, which sorting
    // no longer matches. Getting this wrong deletes the neighbour.
    it('removes the unit whose control was pressed, not its old neighbour', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      editor(1, {
        decks: [[{ slug: 'blanc', locked: false }, { slug: 'crown', locked: false }]],
      }, onChange)

      const crownSeat = () =>
        screen.getByRole('button', { name: `덱 1의 ${nameFromSlug('crown')}` })
      await user.click(crownSeat())
      await user.click(crownSeat())

      expect(onChange).toHaveBeenCalledWith({ decks: [[{ slug: 'blanc', locked: false }]] })
    })

    it('locks the unit whose control was pressed, not its old neighbour', async () => {
      const user = userEvent.setup()
      const onChange = vi.fn()
      editor(1, {
        decks: [[{ slug: 'blanc', locked: false }, { slug: 'crown', locked: false }]],
      }, onChange)

      await user.click(
        screen.getByRole('button', { name: `덱 1에서 ${nameFromSlug('crown')} 고정` }))

      expect(onChange).toHaveBeenCalledWith({
        decks: [[{ slug: 'blanc', locked: false }, { slug: 'crown', locked: true }]],
      })
    })
  })

  describe('drag and drop', () => {
    // jsdom has no drag implementation, so drive the handlers with a stub
    // dataTransfer carrying only what the component reads.
    const dataTransfer = (slug: string | null) => ({
      types: slug === null ? [] : [DRAG_SLUG_TYPE],
      getData: (type: string) => (type === DRAG_SLUG_TYPE && slug !== null ? slug : ''),
      setData: () => {},
      dropEffect: '',
      effectAllowed: '',
    })

    const deckAt = (index: number) =>
      screen.getByRole('heading', { name: new RegExp(`덱 ${index + 1}`) }).closest('div')!

    it('seats a dragged unit in the deck it was dropped on', () => {
      const onChange = vi.fn()
      editor(2, makeEmptyDraft(2), onChange)

      fireEvent.drop(deckAt(1), { dataTransfer: dataTransfer('crown') })

      expect(onChange).toHaveBeenCalledWith({ decks: [[], [{ slug: 'crown', locked: false }]] })
    })

    // The whole point of making a slot a drag source: a misplaced unit is
    // moved, not removed and re-added.
    it('moves a seated unit to the deck it was dropped on', () => {
      const onChange = vi.fn()
      editor(2, { decks: [[{ slug: 'crown', locked: true }], []] }, onChange)

      fireEvent.drop(deckAt(1), { dataTransfer: dataTransfer('crown') })

      expect(onChange).toHaveBeenCalledWith({
        decks: [[], [{ slug: 'crown', locked: true }]],
      })
    })

    it('hands the dragged slug to the drop through the shared transfer type', () => {
      const { container } = editor(2, { decks: [[{ slug: 'crown', locked: false }], []] })
      const transfer = dataTransfer(null)
      const setData = vi.fn()

      fireEvent.dragStart(container.querySelector('.draft-editor__slot-grip')!, {
        dataTransfer: { ...transfer, setData },
      })

      expect(setData).toHaveBeenCalledWith(DRAG_SLUG_TYPE, 'crown')
    })

    it('ignores a drop carrying no unit', () => {
      const onChange = vi.fn()
      editor(1, makeEmptyDraft(1), onChange)

      fireEvent.drop(deckAt(0), { dataTransfer: dataTransfer(null) })

      expect(onChange).not.toHaveBeenCalled()
    })

    const slotOf = (deckIndex: number, slug: string) =>
      screen.getByRole('button', {
        name: `덱 ${deckIndex + 1}의 ${nameFromSlug(slug)}`,
      }).closest('.draft-editor__slot')!

    // Two full decks had no way to trade at all: the deck is the drop target
    // and a full one refuses, so a swap meant removing a unit first.
    it('trades places when a seated unit is dropped on a seat in another deck', () => {
      const onChange = vi.fn()
      const deck = (prefix: string) =>
        Array.from({ length: MAX_DRAFT_SEATS_PER_DECK }, (_, i) => ({
          slug: `${prefix}${i}`,
          locked: false,
        }))
      editor(2, { decks: [deck('a'), deck('b')] }, onChange)

      fireEvent.drop(slotOf(1, 'b2'), { dataTransfer: dataTransfer('a0') })

      expect(onChange).toHaveBeenCalledTimes(1)
      const next: Draft = onChange.mock.calls[0][0]
      expect(next.decks[0].map((s) => s.slug)).toContain('b2')
      expect(next.decks[0].map((s) => s.slug)).not.toContain('a0')
      expect(next.decks[1].map((s) => s.slug)).toContain('a0')
      expect(next.decks.every((seats) => seats.length === MAX_DRAFT_SEATS_PER_DECK)).toBe(true)
    })

    // The slot sits inside the deck, so a slot drop that let the event through
    // would be handled twice - once as a swap and once as a plain move.
    it('does not let a seat drop reach the deck behind it', () => {
      const onChange = vi.fn()
      editor(2, {
        decks: [[{ slug: 'crown', locked: false }], [{ slug: 'blanc', locked: false }]],
      }, onChange)

      fireEvent.drop(slotOf(1, 'blanc'), { dataTransfer: dataTransfer('crown') })

      expect(onChange).toHaveBeenCalledTimes(1)
      expect(onChange).toHaveBeenCalledWith({
        decks: [[{ slug: 'blanc', locked: false }], [{ slug: 'crown', locked: false }]],
      })
    })

    // A palette unit is not seated anywhere, so there is nothing to trade with
    // - it is the plain move onto that deck, which its capacity still governs.
    it('seats a palette unit dropped on a seat when that deck has room', () => {
      const onChange = vi.fn()
      editor(2, { decks: [[{ slug: 'blanc', locked: false }], []] }, onChange)

      fireEvent.drop(slotOf(0, 'blanc'), { dataTransfer: dataTransfer('crown') })

      expect(onChange).toHaveBeenCalledWith({
        decks: [[{ slug: 'blanc', locked: false }, { slug: 'crown', locked: false }], []],
      })
    })

    it('accepts the dragover on a full deck when the pointer is over a seat', () => {
      const full = {
        decks: [
          Array.from({ length: MAX_DRAFT_SEATS_PER_DECK }, (_, i) => ({
            slug: `unit-${i}`,
            locked: false,
          })),
          [{ slug: 'crown', locked: false }],
        ],
      }
      editor(2, full)

      // Handled - preventDefault called - is what marks a real drop target.
      const handled = fireEvent.dragOver(slotOf(0, 'unit-1'),
                                         { dataTransfer: dataTransfer('crown') })
      expect(handled).toBe(false)
    })

    it('refuses a drop on a full deck by declining to handle the dragover', () => {
      const onChange = vi.fn()
      const full = {
        decks: [
          Array.from({ length: MAX_DRAFT_SEATS_PER_DECK }, (_, i) => ({
            slug: `unit-${i}`,
            locked: false,
          })),
        ],
      }
      editor(1, full, onChange)

      // An unhandled dragover leaves the default in place, which is what tells
      // the browser this is not a drop target.
      const handled = fireEvent.dragOver(deckAt(0), { dataTransfer: dataTransfer('crown') })
      expect(handled).toBe(true)
    })
  })

  describe('집기와 놓기', () => {
    const seated: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }

    it('좌석을 한 번 누르면 들리고, 아직 빠지지 않는다', async () => {
      const onChange = vi.fn()
      const { container } = editor(2, seated, onChange)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))

      expect(onChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
    })

    it('같은 좌석을 다시 누르면 제거한다', async () => {
      const onChange = vi.fn()
      editor(2, seated, onChange)

      const seat = () => screen.getByRole('button', { name: /덱 1의 Crown/ })
      await userEvent.click(seat())
      await userEvent.click(seat())

      expect(onChange).toHaveBeenCalledWith({ decks: [[], []] })
    })

    it('Esc는 집기를 취소하고 좌석을 그대로 둔다', async () => {
      const onChange = vi.fn()
      const { container } = editor(2, seated, onChange)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      await userEvent.keyboard('{Escape}')

      expect(onChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).toBeNull()
    })

    it('고정된 좌석은 들리지 않는다', async () => {
      const onChange = vi.fn()
      const { container } = render(
        <DraftEditor
          numDecks={2} value={seated} onChange={onChange}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          fixedSlugs={['crown']}
        />,
      )
      const grip = container.querySelector('.draft-editor__slot-grip')!
      await userEvent.click(grip)

      expect(onChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).toBeNull()
    })
  })
})

describe('fixedSlugs', () => {
  const tiersFor = (slug: string): BurstTier[] =>
    slug === 'miranda-signature' ? [1] : [3]
  const seededDraft: Draft = {
    decks: [[
      { slug: 'miranda-signature', locked: false },
      { slug: 'ada-wong', locked: false },
    ]],
  }
  const renderWith = (
    fixedSlugs?: string[],
    value: Draft = seededDraft,
    numDecks = 1,
    portraitFor: (slug: string) => string | null = () => null,
  ) => {
    const onChange = vi.fn()
    render(
      <DraftEditor
        numDecks={numDecks}
        value={value}
        onChange={onChange}
        portraitFor={portraitFor}
        nameFor={(slug) => slug}
        burstTiersFor={tiersFor}
        showLocks={false}
        fixedSlugs={fixedSlugs}
      />,
    )
    return onChange
  }

  it('draws no seat control for a fixed seat', () => {
    renderWith(['miranda-signature'])
    expect(
      screen.queryByRole('button', { name: /덱 1의 miranda-signature/ }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /덱 1의 ada-wong/ })).toBeInTheDocument()
  })

  it('refuses a drag-out started from the portrait image, not just the grip', () => {
    // draggable={false} on the grip does not stop a native-draggable
    // descendant - jsdom fires dragStart on the <img> regardless of the
    // attribute, which is exactly why the handler itself has to refuse it.
    const onChange = renderWith(['miranda-signature'], seededDraft, 1, () => 'https://example.com/miranda.png')
    const portrait = screen.getByAltText('miranda-signature')
    const setData = vi.fn()
    fireEvent.dragStart(portrait, { dataTransfer: { setData, effectAllowed: '' } })
    expect(setData).not.toHaveBeenCalled()
    expect(onChange).not.toHaveBeenCalled()
  })

  it('refuses a swap dropped onto a fixed seat', () => {
    // 좌석 컨트롤과 드래그만 막으면 뒷문이 열려 있다 - 스왑은 점유자를 밀어낸다.
    // crown이 다른 덱에 이미 앉아 있어야 seated===true가 되어 실제로
    // swapUnits 분기를 탄다 - 안 그러면 자리 없는 유닛의 moveUnit 분기를
    // 시험하게 된다.
    const onChange = renderWith(['miranda-signature'], {
      decks: [
        [
          { slug: 'miranda-signature', locked: false },
          { slug: 'ada-wong', locked: false },
        ],
        [{ slug: 'crown', locked: false }],
      ],
    }, 2)
    const fixed = screen.getByText('miranda-signature').closest('li')!
    fireEvent.drop(fixed, {
      dataTransfer: { getData: (type: string) => (type === DRAG_SLUG_TYPE ? 'crown' : '') },
    })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('leaves every seat removable when no slug is fixed', () => {
    renderWith()
    expect(
      screen.getByRole('button', { name: /덱 1의 miranda-signature/ }),
    ).toBeInTheDocument()
  })
})

// 팔레트의 배치 버튼은 "어느 덱에"를 말하지 않는다 - 그것을 정하는 것이 활성
// 덱이다. 덱이 하나뿐인 화면에는 고를 것이 없으므로 개념 자체가 안 나타난다.
describe('활성 덱', () => {
  const renderDecks = (numDecks: number, activeDeck = 0) => {
    const onActiveDeckChange = vi.fn()
    render(
      <DraftEditor
        numDecks={numDecks}
        value={makeEmptyDraft(numDecks)}
        onChange={vi.fn()}
        portraitFor={() => null}
        nameFor={nameFromSlug}
        burstTiersFor={() => []}
        activeDeck={activeDeck}
        onActiveDeckChange={onActiveDeckChange}
      />,
    )
    return onActiveDeckChange
  }

  it('덱을 눌러 활성 덱을 바꾼다', async () => {
    const onActiveDeckChange = renderDecks(3)
    await userEvent.click(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))
    expect(onActiveDeckChange).toHaveBeenCalledWith(1)
  })

  it('활성 덱만 눌린 상태로 보고한다', () => {
    renderDecks(3, 1)
    expect(screen.getByRole('button', { name: '덱 1 활성 덱으로 선택' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('덱이 하나면 고를 것이 없어 선택 컨트롤을 안 그린다', () => {
    renderDecks(1)
    expect(screen.queryByRole('button', { name: /활성 덱으로 선택/ })).not.toBeInTheDocument()
  })

  // 이 프로퍼티들이 없는 화면(그리고 예전 호출부)은 아무것도 달라지지 않는다.
  it('활성 덱을 다루지 않는 화면에서는 선택 컨트롤이 없다', () => {
    render(
      <DraftEditor
        numDecks={3}
        value={makeEmptyDraft(3)}
        onChange={vi.fn()}
        portraitFor={() => null}
        nameFor={nameFromSlug}
        burstTiersFor={() => []}
      />,
    )
    expect(screen.queryByRole('button', { name: /활성 덱으로 선택/ })).not.toBeInTheDocument()
  })
})
