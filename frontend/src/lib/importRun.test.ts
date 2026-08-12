import { describe, expect, it } from 'vitest'
import { canSeatFrom, draftFromResultDecks, seatableOnly } from './importRun'

/** 기본 조회: 슬러그는 그대로, 전부 앉힐 수 있음. */
const plain = {
  ownedSlugFor: (slug: string) => slug,
  canSeat: () => true,
}

describe('draftFromResultDecks', () => {
  it('결과 덱을 순서대로 좌석으로 앉힌다', () => {
    const { draft, droppedSlugs } = draftFromResultDecks(
      [['a', 'b'], ['c']],
      2,
      plain,
    )

    expect(draft.decks).toEqual([
      [
        { slug: 'a', locked: false },
        { slug: 'b', locked: false },
      ],
      [{ slug: 'c', locked: false }],
    ])
    expect(droppedSlugs).toEqual([])
  })

  it('엔진 슬러그를 소유 슬러그로 되돌린다', () => {
    const { draft } = draftFromResultDecks([['bready-lingering']], 1, {
      ...plain,
      ownedSlugFor: (slug) => (slug === 'bready-lingering' ? 'bready' : slug),
    })

    expect(draft.decks[0]).toEqual([{ slug: 'bready', locked: false }])
  })

  it('앉힐 수 없는 니케는 자리를 비우고 목록에 담는다', () => {
    const { draft, droppedSlugs } = draftFromResultDecks([['a', 'gone', 'b']], 1, {
      ...plain,
      canSeat: (slug) => slug !== 'gone',
    })

    expect(draft.decks[0]).toEqual([
      { slug: 'a', locked: false },
      { slug: 'b', locked: false },
    ])
    expect(droppedSlugs).toEqual(['gone'])
  })

  it('앉힐 수 있는지는 되돌린 소유 슬러그로 묻는다', () => {
    const asked: string[] = []
    draftFromResultDecks([['bready-lingering']], 1, {
      ownedSlugFor: () => 'bready',
      canSeat: (slug) => {
        asked.push(slug)
        return true
      },
    })

    expect(asked).toEqual(['bready'])
  })

  it('덱 개수에 맞춰 자르고 모자란 자리는 빈 덱으로 채운다', () => {
    const { draft } = draftFromResultDecks([['a'], ['b'], ['c']], 2, plain)
    expect(draft.decks).toHaveLength(2)

    const grown = draftFromResultDecks([['a']], 3, plain)
    expect(grown.draft.decks).toEqual([[{ slug: 'a', locked: false }], [], []])
  })

  it('같은 니케가 두 번 나와도 한 번만 앉는다', () => {
    const { draft } = draftFromResultDecks([['a'], ['a', 'b']], 2, plain)

    expect(draft.decks[0]).toEqual([{ slug: 'a', locked: false }])
    expect(draft.decks[1]).toEqual([{ slug: 'b', locked: false }])
  })
})

describe('canSeatFrom', () => {
  const roster = [{ character_slug: 'a' }, { character_slug: 'b' }]

  it('로스터에 있고 미사용이 아닌 니케만 앉힌다', () => {
    const canSeat = canSeatFrom(roster, new Set(['b']))

    expect(canSeat('a')).toBe(true)
    expect(canSeat('b')).toBe(false) // 미사용으로 둔 니케
    expect(canSeat('z')).toBe(false) // 로스터에 없는 니케
  })
})

describe('seatableOnly', () => {
  const draft = {
    decks: [
      [
        { slug: 'a', locked: true },
        { slug: 'gone', locked: false },
      ],
      [{ slug: 'b', locked: false }],
    ],
  }

  it('앉힐 수 없는 좌석만 빼고 목록에 담는다', () => {
    const result = seatableOnly(draft, (slug) => slug !== 'gone')

    expect(result.draft.decks[0]).toEqual([{ slug: 'a', locked: true }])
    expect(result.draft.decks[1]).toEqual([{ slug: 'b', locked: false }])
    expect(result.droppedSlugs).toEqual(['gone'])
  })

  it('잠금은 그대로 둔다 - 그때의 설정으로 되돌리는 것이 목적이다', () => {
    const result = seatableOnly(draft, () => true)

    expect(result.draft.decks[0][0].locked).toBe(true)
    expect(result.droppedSlugs).toEqual([])
  })

  it('덱 개수와 빈 덱은 건드리지 않는다', () => {
    const result = seatableOnly({ decks: [[], [{ slug: 'gone', locked: false }]] }, () => false)

    expect(result.draft.decks).toEqual([[], []])
  })
})
