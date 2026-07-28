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
  toggleLock,
  toRequestDraft,
} from './DraftEditor'
import { DRAG_SLUG_TYPE } from './UnitPalette'
import type { Draft } from '../types/draft'
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
  const tierOf = (slug: string) =>
    (({ crown: 1, liter: 2, blanc: 3 }) as Record<string, 1 | 2 | 3>)[slug] ?? null

  it('reports the tiers no seat covers', () => {
    expect(missingBurstTiers([{ slug: 'crown', locked: false }], tierOf)).toEqual([2, 3])
  })

  it('reports nothing once all three tiers are seated', () => {
    const seats = ['crown', 'liter', 'blanc'].map((slug) => ({ slug, locked: false }))
    expect(missingBurstTiers(seats, tierOf)).toEqual([])
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

describe('DraftEditor', () => {
  const TIERS: Record<string, 1 | 2 | 3> = { crown: 1, liter: 2, blanc: 3 }

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
        burstTierFor={(slug) => TIERS[slug] ?? null}
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
    expect(screen.getByRole('button', { name: '덱 1에서 Crown 제거' })).toBeInTheDocument()
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

  it('removes a seat via its remove button', async () => {
    const user = userEvent.setup()
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const onChange = vi.fn()
    editor(1, value, onChange)

    await user.click(screen.getByRole('button', { name: '덱 1에서 Crown 제거' }))
    expect(onChange).toHaveBeenCalledWith({ decks: [[]] })
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
})
