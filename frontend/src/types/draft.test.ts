import { describe, it, expect } from 'vitest'
import { isDraftComplete, makeEmptyDraft, resizeDraft, type Draft, type DraftSeat } from './draft'

const seat = (slug: string): DraftSeat => ({ slug, locked: false })

describe('makeEmptyDraft', () => {
  it('creates the requested number of empty decks', () => {
    expect(makeEmptyDraft(3)).toEqual({ decks: [[], [], []] })
  })

  it('creates zero decks for zero decks requested', () => {
    expect(makeEmptyDraft(0)).toEqual({ decks: [] })
  })
})

describe('resizeDraft', () => {
  it('preserves already-placed decks by index while growing', () => {
    const draft: Draft = { decks: [[seat('a')], [seat('b')]] }
    expect(resizeDraft(draft, 4)).toEqual({ decks: [[seat('a')], [seat('b')], [], []] })
  })

  it('drops the trailing decks while shrinking', () => {
    const draft: Draft = { decks: [[seat('a')], [seat('b')], [seat('c')]] }
    expect(resizeDraft(draft, 1)).toEqual({ decks: [[seat('a')]] })
  })
})

describe('isDraftComplete', () => {
  it('is true only when every one of the first n decks is full', () => {
    const full = [seat('a'), seat('b'), seat('c'), seat('d'), seat('e')]
    const draft: Draft = { decks: [full, full] }
    expect(isDraftComplete(draft, 2)).toBe(true)
  })

  it('is false when a deck within n is short a seat', () => {
    const full = [seat('a'), seat('b'), seat('c'), seat('d'), seat('e')]
    const draft: Draft = { decks: [full, full.slice(0, 4)] }
    expect(isDraftComplete(draft, 2)).toBe(false)
  })

  it('ignores decks past n', () => {
    const full = [seat('a'), seat('b'), seat('c'), seat('d'), seat('e')]
    const draft: Draft = { decks: [full, []] }
    expect(isDraftComplete(draft, 1)).toBe(true)
  })
})
