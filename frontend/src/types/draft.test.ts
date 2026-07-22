import { describe, it, expect } from 'vitest'
import { makeEmptyDraft } from './draft'

describe('makeEmptyDraft', () => {
  it('creates the requested number of empty decks', () => {
    expect(makeEmptyDraft(3)).toEqual({ decks: [[], [], []] })
  })

  it('creates zero decks for zero decks requested', () => {
    expect(makeEmptyDraft(0)).toEqual({ decks: [] })
  })
})
