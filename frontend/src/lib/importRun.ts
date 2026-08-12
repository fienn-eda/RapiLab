// 저장해 둔 결과의 덱을 편성 칸이 쓰는 모양으로 옮긴다.
//
// 결과는 엔진 슬러그를 쓰고(`bready` -> `bready-lingering`) 그때의 로스터로
// 나온 것이라, 편성으로 옮기려면 슬러그를 되돌리고 지금 앉힐 수 없는 니케를
// 걸러내야 한다. 무엇이 걸러졌는지 함께 돌려주는 이유는, 말하지 않으면 5명이어야
// 할 덱이 4명인 채로 이유 없이 서 있기 때문이다.

import type { Draft, DraftSeat } from '../types/draft'

export interface ImportedDraft {
  draft: Draft
  /** 앉히지 못한 소유 슬러그들. 화면은 이 길이만 쓴다. */
  droppedSlugs: string[]
}

/**
 * `deckSlugs`(덱마다 슬러그 목록)를 `numDecks`개짜리 편성으로 만든다.
 *
 * 좌석은 전부 잠기지 않은 채로 나온다 - 가져온 편성은 「여기서 출발」이지
 * 「이 자리를 고정」이 아니다(Fienn, 2026-08-12).
 */
export const draftFromResultDecks = (
  deckSlugs: string[][],
  numDecks: number,
  { ownedSlugFor, canSeat }: {
    ownedSlugFor: (slug: string) => string
    canSeat: (slug: string) => boolean
  },
): ImportedDraft => {
  const droppedSlugs: string[] = []
  // 한 니케는 한 자리에만 앉는다 - 편성 편집기가 지키는 불변식이라
  // (DraftEditor의 placeUnit) 가져오기도 지킨다.
  const seated = new Set<string>()

  const decks = Array.from({ length: numDecks }, (_, deckIndex) => {
    const seats: DraftSeat[] = []
    for (const resultSlug of deckSlugs[deckIndex] ?? []) {
      const slug = ownedSlugFor(resultSlug)
      if (seated.has(slug)) continue
      if (!canSeat(slug)) {
        droppedSlugs.push(slug)
        continue
      }
      seated.add(slug)
      seats.push({ slug, locked: false })
    }
    return seats
  })

  return { draft: { decks }, droppedSlugs }
}

/**
 * `draftFromResultDecks`에 넘길 `canSeat`. 솔로 탭과 유니온 탭이 같은 판정을
 * 쓰므로 여기 한 벌만 둔다.
 *
 * 「제외」는 어디서나 같은 뜻이다: 덱에서도 빠지고 제출 로스터에서도 빠진다
 * (UnitPalette의 toggleExcludedSlug 주석). 팔레트가 막는 배치를 가져오기가
 * 대신 해 주면 그 불변식이 깨진다.
 */
export const canSeatFrom =
  (roster: { character_slug: string }[], excludedSlugs: Set<string>) =>
  (slug: string): boolean =>
    roster.some((nikke) => nikke.character_slug === slug) && !excludedSlugs.has(slug)
