import { describe, it, expect } from 'vitest'
import {
  firstDeckWithRoom,
  isDraftComplete,
  makeEmptyDraft,
  resizeDraft,
  type Draft,
  type DraftSeat,
} from './draft'

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

describe('firstDeckWithRoom', () => {
  const deck = (count: number) => Array.from({ length: count }, (_, i) => seat(`u${i}`))

  it('활성 덱에 자리가 있으면 그 덱이다', () => {
    expect(firstDeckWithRoom({ decks: [deck(0), deck(0)] }, 0, 2)).toBe(0)
    expect(firstDeckWithRoom({ decks: [deck(4), deck(0)] }, 0, 2)).toBe(0)
  })

  it('활성 덱이 꽉 차면 다음 덱이다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5), deck(0)] }, 0, 2)).toBe(1)
  })

  // 앞 덱을 비워 두고 뒤에서 채우다 끝에 닿았을 때, 되돌아가지 않으면 빈자리를
  // 두고도 "전부 찼다"가 된다.
  it('뒤가 다 차 있으면 처음으로 되돌아간다', () => {
    expect(firstDeckWithRoom({ decks: [deck(0), deck(5), deck(5)] }, 1, 3)).toBe(0)
    expect(firstDeckWithRoom({ decks: [deck(0), deck(5), deck(5)] }, 2, 3)).toBe(0)
  })

  it('전부 차 있으면 null이다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5), deck(5)] }, 0, 2)).toBeNull()
  })

  // 덱 개수를 줄인 직후에는 draft.decks가 numDecks보다 길다(리사이즈 이펙트가
  // 아직 안 돌았다). 화면에 없는 덱에 앉히면 유저는 유닛이 사라진 것을 본다.
  it('numDecks 밖의 덱은 보지 않는다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5), deck(0)] }, 0, 1)).toBeNull()
  })

  // 반대로 늘린 직후에는 decks가 numDecks보다 짧다. 없는 덱을 골라 주면
  // placeUnit이 조용히 거절해서, 활성 덱만 옮겨가고 아무도 안 앉는다.
  it('decks 배열에 아직 없는 자리는 건너뛴다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5)] }, 0, 3)).toBeNull()
  })
})
