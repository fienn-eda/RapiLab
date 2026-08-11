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
  replaceUnit,
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

describe('replaceUnit', () => {
  it('자리를 물려주므로 꽉 찬 덱에서도 된다', () => {
    const full: Draft = {
      decks: [['a', 'b', 'c', 'd', 'e'].map((slug) => ({ slug, locked: false }))],
    }
    const next = replaceUnit(full, 'c', 'z')
    expect(next.decks[0].map((s) => s.slug)).toEqual(['a', 'b', 'z', 'd', 'e'])
  })

  it('잠금은 자리에 남는다', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: true }]] }
    expect(replaceUnit(draft, 'crown', 'liter').decks[0]).toEqual([
      { slug: 'liter', locked: true },
    ])
  })

  it('다른 덱, 다른 자리는 건드리지 않는다', () => {
    const draft: Draft = {
      decks: [[{ slug: 'crown', locked: false }, { slug: 'blanc', locked: false }], [{ slug: 'liter', locked: true }]],
    }
    expect(replaceUnit(draft, 'crown', 'z')).toEqual({
      decks: [[{ slug: 'z', locked: false }, { slug: 'blanc', locked: false }], [{ slug: 'liter', locked: true }]],
    })
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

    it('들고 다른 덱의 빈자리를 누르면 옮긴다', async () => {
      const onChange = vi.fn()
      editor(2, seated, onChange)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      await userEvent.click(screen.getByRole('button', { name: '덱 2에 놓기' }))

      expect(onChange).toHaveBeenCalledWith({
        decks: [[], [{ slug: 'crown', locked: false }]],
      })
    })

    it('들고 차 있는 자리를 누르면 둘을 교환한다', async () => {
      const both: Draft = {
        decks: [[{ slug: 'crown', locked: false }], [{ slug: 'liter', locked: false }]],
      }
      const onChange = vi.fn()
      editor(2, both, onChange)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      await userEvent.click(screen.getByRole('button', { name: /덱 2의 Liter/ }))

      expect(onChange).toHaveBeenCalledWith({
        decks: [[{ slug: 'liter', locked: false }], [{ slug: 'crown', locked: false }]],
      })
    })

    it('아무것도 안 들었으면 빈자리는 버튼이 아니다', () => {
      editor(2, seated)
      expect(screen.queryByRole('button', { name: /놓기/ })).not.toBeInTheDocument()
    })

    it('들고 고정된 좌석을 누르면 아무 일도 없고 계속 들고 있다', async () => {
      const both: Draft = {
        decks: [[{ slug: 'crown', locked: false }], [{ slug: 'liter', locked: false }]],
      }
      const onChange = vi.fn()
      const { container } = render(
        <DraftEditor
          numDecks={2} value={both} onChange={onChange}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          fixedSlugs={['liter']}
        />,
      )

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      await userEvent.click(container.querySelectorAll('.draft-editor__slot-grip')[1])

      expect(onChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
    })

    // 든 것을 좌표로 기억하면, 밖에서 value가 통째로 바뀔 때(보관물 복원,
    // 전투 수 축소, 니케 풀 탭 제외) 그 좌표에 새로 들어온 유닛이 "든 자리"가
    // 된다 - 한 번 누르면 유저가 집은 적 없는 유닛이 편성에서 빠진다.
    it('밖에서 든 유닛이 사라지면 그 자리에 온 유닛을 눌러도 안 빠진다', async () => {
      const onChange = vi.fn()
      const props = {
        numDecks: 2,
        onChange,
        portraitFor: () => null,
        nameFor: nameFromSlug,
        burstTiersFor: (slug: string) => TIERS[slug] ?? [],
      }
      // blanc은 B3라 crown(B1) 다음, 즉 저장 순서로도 화면 순서로도 두 번째다.
      const before: Draft = {
        decks: [[{ slug: 'crown', locked: false }, { slug: 'blanc', locked: false }], []],
      }
      // 같은 자리에 liter가 앉은 다른 편성. blanc은 어디에도 없다.
      const after: Draft = {
        decks: [[{ slug: 'crown', locked: false }, { slug: 'liter', locked: false }], []],
      }
      const { rerender, container } = render(<DraftEditor {...props} value={before} />)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Blanc/ }))
      rerender(<DraftEditor {...props} value={after} />)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Liter/ }))

      expect(onChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
    })

    // i===0 빈자리만 놓기 버튼이 되므로, 접근성 트리 노출도 그 하나에만
    // 한정돼야 한다 - 나머지 넷까지 노출되면 스크린리더가 덱마다 "+"를
    // 여러 번 읽는, i===0 제한이 막으려던 바로 그 소음이 aria-hidden 축에서
    // 새는 것이다.
    it('들었을 때 덱마다 첫 빈자리만 접근성 트리에 노출하고 나머지는 숨긴다', async () => {
      const { container } = editor(2, seated)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))

      const decks = container.querySelectorAll('.draft-editor__deck')
      expect(decks.length).toBeGreaterThan(0)
      decks.forEach((deck) => {
        const openSlots = [...deck.querySelectorAll('.draft-editor__slot--open')]
        expect(openSlots[0]).not.toHaveAttribute('aria-hidden')
        expect(
          openSlots.slice(1).every((slot) => slot.getAttribute('aria-hidden') === 'true'),
        ).toBe(true)
      })
    })
  })

  // 덱 이름 글자와 첫 빈자리의 `+` 글자, 이 둘만 표적이었다. 나머지 테두리
  // 안은 전부 죽어 있어서 「다른 덱으로 옮기기」가 20px 과녁 맞히기였다.
  describe('덱 몸통 표적', () => {
    const seated: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }
    const both: Draft = {
      decks: [[{ slug: 'crown', locked: false }], [{ slug: 'liter', locked: false }]],
    }
    const moved = { decks: [[], [{ slug: 'crown', locked: false }]] }

    const pickable = (
      value: Draft,
      onChange: (next: Draft) => void = () => {},
      onActiveDeckChange: (deckIndex: number) => void = () => {},
      extra: Partial<React.ComponentProps<typeof DraftEditor>> = {},
    ) =>
      render(
        <DraftEditor
          numDecks={2}
          value={value}
          onChange={onChange}
          portraitFor={() => null}
          nameFor={nameFromSlug}
          burstTiersFor={(slug: string) => TIERS[slug] ?? []}
          activeDeck={0}
          onActiveDeckChange={onActiveDeckChange}
          {...extra}
        />,
      )

    /** 덱 컨테이너 자체 - 안쪽 컨트롤이 아니라 테두리 안 빈 면적을 누르는 것과
     * 같다. jsdom에는 레이아웃이 없어서 이 요소에 직접 디스패치한다. */
    const deckBody = (container: HTMLElement, deckNumber: number) =>
      container.querySelectorAll<HTMLElement>('.draft-editor__deck')[deckNumber - 1]

    it('아무것도 안 들었으면 덱 몸통을 누를 때 그 덱이 활성 덱이 된다', async () => {
      const onActiveDeckChange = vi.fn()
      const { container } = pickable(seated, () => {}, onActiveDeckChange)

      await userEvent.click(deckBody(container, 2))

      expect(onActiveDeckChange).toHaveBeenCalledWith(1)
    })

    it('들고 덱 몸통을 누르면 옮기고, 그 덱이 활성 덱이 된다', async () => {
      const onChange = vi.fn()
      const onActiveDeckChange = vi.fn()
      const { container } = pickable(seated, onChange, onActiveDeckChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      await userEvent.click(deckBody(container, 2))

      expect(onChange).toHaveBeenCalledWith(moved)
      expect(onActiveDeckChange).toHaveBeenLastCalledWith(1)
    })

    // Fienn의 보고: 「가장 왼쪽 자리만 활성화된다」. 나머지 넷은 버튼이 아닌
    // 것을 넘어 클릭이 어디로도 안 갔다.
    it('들고 다른 덱의 세 번째 빈자리를 눌러도 옮긴다', async () => {
      const onChange = vi.fn()
      const { container } = pickable(seated, onChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      const open = deckBody(container, 2).querySelectorAll<HTMLElement>(
        '.draft-editor__slot--open',
      )
      expect(open).toHaveLength(5)
      await userEvent.click(open[2])

      expect(onChange).toHaveBeenCalledWith(moved)
    })

    // 껍데기가 moveUnit의 거절을 안 보면, 옮기지도 않고 든 것만 내려놓는다 -
    // 화면에서 유닛이 조용히 사라진 것처럼 보인다.
    it('꽉 찬 덱 몸통을 누르면 옮기지 않고 계속 들고 있다', async () => {
      const full: Draft = {
        decks: [
          [{ slug: 'crown', locked: false }],
          ['liter', 'blanc', 'x1', 'x2', 'x3'].map((slug) => ({ slug, locked: false })),
        ],
      }
      const onChange = vi.fn()
      const onHeldSlugChange = vi.fn()
      const { container } = pickable(full, onChange, () => {}, { onHeldSlugChange })

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      onHeldSlugChange.mockClear()
      await userEvent.click(deckBody(container, 2))

      expect(onChange).not.toHaveBeenCalled()
      expect(onHeldSlugChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
    })

    // 좌석 버튼이 자기 핸들러에서 setHeld(null)을 불러도, 껍데기가 읽는
    // heldSlug는 같은 배치 안이라 아직 옛 값이다 - 전파를 안 끊으면 교환하고
    // 나서 또 이동한다.
    it('좌석으로 교환할 때 껍데기가 겹쳐 처리하지 않는다', async () => {
      const onChange = vi.fn()
      pickable(both, onChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      await userEvent.click(screen.getByRole('button', { name: '덱 2의 Liter' }))

      expect(onChange).toHaveBeenCalledTimes(1)
      expect(onChange).toHaveBeenCalledWith({
        decks: [[{ slug: 'liter', locked: false }], [{ slug: 'crown', locked: false }]],
      })
    })

    it('잠금 토글은 껍데기로 새지 않는다', async () => {
      const onActiveDeckChange = vi.fn()
      pickable(both, () => {}, onActiveDeckChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 2에서 Liter 고정' }))

      expect(onActiveDeckChange).not.toHaveBeenCalled()
    })

    // 든 채로는 덱 이름도 놓는 자리다 - 표적 한가운데에 죽은 띠를 두지 않는다.
    it('들고 덱 이름을 눌러도 옮긴다', async () => {
      const onChange = vi.fn()
      pickable(seated, onChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      await userEvent.click(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))

      expect(onChange).toHaveBeenCalledWith(moved)
    })

    it('안 들었을 때 덱 이름은 활성 덱만 한 번 바꾼다', async () => {
      const onChange = vi.fn()
      const onActiveDeckChange = vi.fn()
      pickable(seated, onChange, onActiveDeckChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))

      expect(onActiveDeckChange).toHaveBeenCalledTimes(1)
      expect(onActiveDeckChange).toHaveBeenCalledWith(1)
      expect(onChange).not.toHaveBeenCalled()
    })

    // 덱이 하나면 고를 것이 없다. 껍데기가 onActiveDeckChange의 존재만 보고
    // 부르면, 미란다 화면에 없는 개념이 생긴다.
    it('덱이 하나면 몸통을 눌러도 활성 덱을 부르지 않는다', async () => {
      const onActiveDeckChange = vi.fn()
      const { container } = render(
        <DraftEditor
          numDecks={1}
          value={{ decks: [[]] }}
          onChange={() => {}}
          portraitFor={() => null}
          nameFor={nameFromSlug}
          burstTiersFor={(slug: string) => TIERS[slug] ?? []}
          activeDeck={0}
          onActiveDeckChange={onActiveDeckChange}
        />,
      )

      await userEvent.click(deckBody(container, 1))

      expect(onActiveDeckChange).not.toHaveBeenCalled()
    })
  })

  // 팔레트가 이 컴포넌트 밖에 있어서, 부모는 무엇이 들렸는지 슬러그로 알아야
  // 한다. 든 것이 바뀌는 길 전부(집기·제거·이동·교환·Esc·편성에서 사라짐·
  // 언마운트)가 이 알림을 거쳐야 하고, 하나라도 빠지면 부모의 사본이 조용히
  // 낡아 팔레트 클릭이 엉뚱한 유닛을 밀어낸다.
  describe('든 유닛 알림 (onHeldSlugChange)', () => {
    const seated: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }
    const both: Draft = {
      decks: [[{ slug: 'crown', locked: false }], [{ slug: 'liter', locked: false }]],
    }

    it('집으면 슬러그를 알린다', async () => {
      const onHeldSlugChange = vi.fn()
      render(
        <DraftEditor
          numDecks={2} value={seated} onChange={vi.fn()}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          onHeldSlugChange={onHeldSlugChange}
        />,
      )

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))

      expect(onHeldSlugChange).toHaveBeenCalledWith('crown')
    })

    it('같은 자리를 다시 눌러 제거하면 null을 알린다', async () => {
      const onHeldSlugChange = vi.fn()
      render(
        <DraftEditor
          numDecks={2} value={seated} onChange={vi.fn()}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          onHeldSlugChange={onHeldSlugChange}
        />,
      )
      const seat = () => screen.getByRole('button', { name: /덱 1의 Crown/ })

      await userEvent.click(seat())
      await userEvent.click(seat())

      expect(onHeldSlugChange).toHaveBeenLastCalledWith(null)
    })

    it('들고 다른 덱의 빈자리로 옮기면 null을 알린다', async () => {
      const onHeldSlugChange = vi.fn()
      render(
        <DraftEditor
          numDecks={2} value={seated} onChange={vi.fn()}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          onHeldSlugChange={onHeldSlugChange}
        />,
      )

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      await userEvent.click(screen.getByRole('button', { name: '덱 2에 놓기' }))

      expect(onHeldSlugChange).toHaveBeenLastCalledWith(null)
    })

    it('들고 찬 자리와 교환하면 null을 알린다', async () => {
      const onHeldSlugChange = vi.fn()
      render(
        <DraftEditor
          numDecks={2} value={both} onChange={vi.fn()}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          onHeldSlugChange={onHeldSlugChange}
        />,
      )

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      await userEvent.click(screen.getByRole('button', { name: /덱 2의 Liter/ }))

      expect(onHeldSlugChange).toHaveBeenLastCalledWith(null)
    })

    it('Esc로 취소하면 null을 알린다', async () => {
      const onHeldSlugChange = vi.fn()
      render(
        <DraftEditor
          numDecks={2} value={seated} onChange={vi.fn()}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          onHeldSlugChange={onHeldSlugChange}
        />,
      )

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      await userEvent.keyboard('{Escape}')

      expect(onHeldSlugChange).toHaveBeenLastCalledWith(null)
    })

    // 팔레트를 눌러 든 자리를 대신 채우는 처리는 부모가 한다 - 이 컴포넌트의
    // 클릭 핸들러를 거치지 않는다. 든 유닛이 편성에서 사라진 것을 여기서 알아
    // 스스로 내리지 않으면, 방금 팔레트가 채운 자리가 여전히 "든 자리"로 남고
    // 부모의 사본도 그 유닛을 가리킨 채 낡는다.
    it('팔레트가 든 자리를 대신 채우면 스스로 내리고 그것도 알린다', async () => {
      const onChange = vi.fn()
      const onHeldSlugChange = vi.fn()
      const props = {
        numDecks: 2,
        onChange,
        portraitFor: () => null,
        nameFor: nameFromSlug,
        burstTiersFor: (slug: string) => TIERS[slug] ?? [],
        onHeldSlugChange,
      }
      const { rerender, container } = render(<DraftEditor {...props} value={seated} />)

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      expect(onHeldSlugChange).toHaveBeenLastCalledWith('crown')
      expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()

      // 팔레트가 든 자리를 liter로 대신 채운다.
      const replaced: Draft = { decks: [[{ slug: 'liter', locked: false }], []] }
      rerender(<DraftEditor {...props} value={replaced} />)

      expect(onHeldSlugChange).toHaveBeenLastCalledWith(null)
      expect(container.querySelector('.draft-editor__slot--held')).toBeNull()

      // 방금 채워진 자리를 누르면 집기여야 한다 - 즉시 제거되면 낡은 자리를
      // 여전히 "든 자리"로 여기고 있다는 뜻이다.
      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Liter/ }))
      expect(onChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
    })

    // 모드를 바꾸면 편성 칸째로 언마운트된다. 부모의 사본은 이 알림으로만
    // 갱신되므로, 사라지면서 안 내리면 부모는 있지도 않은 든 유닛을 계속 믿고
    // 다음 팔레트 클릭을 맞바꾸기로 처리한다.
    it('언마운트되면 든 것이 없어졌음을 알린다', async () => {
      const onHeldSlugChange = vi.fn()
      const { unmount } = render(
        <DraftEditor
          numDecks={2} value={seated} onChange={vi.fn()}
          portraitFor={() => null} nameFor={nameFromSlug}
          burstTiersFor={(slug) => TIERS[slug] ?? []}
          onHeldSlugChange={onHeldSlugChange}
        />,
      )

      await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
      expect(onHeldSlugChange).toHaveBeenLastCalledWith('crown')

      unmount()

      expect(onHeldSlugChange).toHaveBeenLastCalledWith(null)
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
