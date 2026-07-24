import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DraftEditor, placeUnit, toggleLock, removeUnit, removeUnitBySlug, toRequestDraft } from './DraftEditor'
import { DRAG_SLUG_TYPE } from './UnitPalette'
import type { Draft } from '../types/draft'
import { makeEmptyDraft, MAX_DRAFT_SEATS_PER_DECK } from '../types/draft'

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
  const editor = (numDecks: number, value: Draft, onChange: (next: Draft) => void = () => {}) =>
    render(
      <DraftEditor
        numDecks={numDecks}
        value={value}
        onChange={onChange}
        portraitFor={() => null}
      />,
    )

  it('renders each deck\'s seats with their slug', () => {
    const value: Draft = {
      decks: [[{ slug: 'crown', locked: false }], []],
    }
    editor(2, value)
    expect(screen.getByRole('heading', { name: /Deck 1/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Deck 2/ })).toBeInTheDocument()
    expect(screen.getByText('crown')).toBeInTheDocument()
  })

  it('flips a seat\'s lock via the checkbox and reports the change through onChange', async () => {
    const user = userEvent.setup()
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const onChange = vi.fn()
    editor(1, value, onChange)

    await user.click(screen.getByRole('checkbox', { name: /lock crown/i }))
    expect(onChange).toHaveBeenCalledWith({ decks: [[{ slug: 'crown', locked: true }]] })
  })

  it('removes a seat via its remove button', async () => {
    const user = userEvent.setup()
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const onChange = vi.fn()
    editor(1, value, onChange)

    await user.click(screen.getByRole('button', { name: /remove crown/i }))
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
      screen.getByRole('heading', { name: new RegExp(`Deck ${index + 1}`) }).closest('div')!

    it('seats a dragged unit in the deck it was dropped on', () => {
      const onChange = vi.fn()
      editor(2, makeEmptyDraft(2), onChange)

      fireEvent.drop(deckAt(1), { dataTransfer: dataTransfer('crown') })

      expect(onChange).toHaveBeenCalledWith({ decks: [[], [{ slug: 'crown', locked: false }]] })
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
