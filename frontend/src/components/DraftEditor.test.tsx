import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DraftEditor, placeUnit, toggleLock, removeUnit, toRequestDraft } from './DraftEditor'
import type { Draft } from '../types/draft'
import { makeEmptyDraft } from '../types/draft'

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
  it('renders each deck\'s seats with their slug', () => {
    const value: Draft = {
      decks: [[{ slug: 'crown', locked: false }], []],
    }
    render(<DraftEditor numDecks={2} value={value} onChange={() => {}} />)
    expect(screen.getByText('Deck 1')).toBeInTheDocument()
    expect(screen.getByText('Deck 2')).toBeInTheDocument()
    expect(screen.getByText('crown')).toBeInTheDocument()
  })

  it('flips a seat\'s lock via the checkbox and reports the change through onChange', async () => {
    const user = userEvent.setup()
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const onChange = vi.fn()
    render(<DraftEditor numDecks={1} value={value} onChange={onChange} />)

    await user.click(screen.getByRole('checkbox', { name: /lock crown/i }))
    expect(onChange).toHaveBeenCalledWith({ decks: [[{ slug: 'crown', locked: true }]] })
  })

  it('removes a seat via its remove button', async () => {
    const user = userEvent.setup()
    const value: Draft = { decks: [[{ slug: 'crown', locked: false }]] }
    const onChange = vi.fn()
    render(<DraftEditor numDecks={1} value={value} onChange={onChange} />)

    await user.click(screen.getByRole('button', { name: /remove crown/i }))
    expect(onChange).toHaveBeenCalledWith({ decks: [[]] })
  })
})
