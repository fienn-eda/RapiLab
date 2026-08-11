import { describe, it, expect } from 'vitest'
import {
  EMPTY_FILTER,
  filterAndSort,
  isFiltering,
  type UnitFacets,
  type UnitFilterState,
} from './unitFilter'

interface Row {
  slug: string
  name: string
  element: UnitFacets['element']
  burstTier: UnitFacets['burstTier']
  overload: { name: string; value: number | string }[]
}

const facets = (row: Row): UnitFacets => row

const ROWS: Row[] = [
  { slug: 'scarlet', name: '홍련', element: 'Fire', burstTier: 3, overload: [{ name: '공격력 증가', value: 40.91 }] },
  { slug: 'rapi', name: '라피', element: 'Water', burstTier: 1, overload: [{ name: '공격력 증가', value: 12.5 }] },
  { slug: 'neon', name: '네온', element: 'Fire', burstTier: 1, overload: [{ name: '우월코드 대미지 증가', value: 99.82 }] },
  { slug: 'alice', name: '앨리스', element: 'Wind', burstTier: 3, overload: [] },
]

/** 별명 표는 슬러그로 키를 잡으므로 실재하는 슬러그가 필요하다. ROWS에 섞지
 * 않는 이유는 「홍련: 흑영」의 초성이 'ㅎㄹㅎㅇ'이라 위 초성 테스트의 'ㅎㄹ'에도
 * 맞아, 별명과 무관한 단언들을 흔들기 때문이다. */
const ALIAS_ROWS: Row[] = [
  { slug: 'scarlet-black-shadow', name: '홍련: 흑영', element: 'Fire', burstTier: 3, overload: [] },
  { slug: 'little-mermaid', name: '리틀 머메이드', element: 'Water', burstTier: 2, overload: [] },
  { slug: 'rapi', name: '라피', element: 'Water', burstTier: 1, overload: [] },
]

const names = (rows: Row[]) => rows.map((row) => row.name)
const run = (state: Partial<UnitFilterState>) =>
  names(filterAndSort(ROWS, facets, { ...EMPTY_FILTER, ...state }))
const searchAlias = (query: string) =>
  names(filterAndSort(ALIAS_ROWS, facets, { ...EMPTY_FILTER, query }))

describe('filterAndSort', () => {
  it('keeps every unit when nothing is filtered', () => {
    expect(run({}).sort()).toEqual(['네온', '라피', '앨리스', '홍련'].sort())
  })

  // The grid opens on the units the player invested in most, rather than on
  // whatever order the backend happened to return.
  it('starts on 우코, highest first', () => {
    expect(EMPTY_FILTER.sortKey).toBe('우코')
    expect(EMPTY_FILTER.sortDir).toBe('desc')
    // Rows whose 우코 order contradicts their name order: in ROWS only one
    // unit rolled the stat, so there the two orders coincide and the default
    // would pass either way.
    const rows: Row[] = [
      { slug: 'ga', name: '가', element: 'Fire', burstTier: 1, overload: [{ name: '우월코드 대미지 증가', value: 10 }] },
      { slug: 'na', name: '나', element: 'Fire', burstTier: 1, overload: [{ name: '우월코드 대미지 증가', value: 50 }] },
    ]
    expect(names(filterAndSort(rows, facets, EMPTY_FILTER))).toEqual(['나', '가'])
  })

  it('sorts by name in Korean collation order', () => {
    expect(run({ sortKey: 'name', sortDir: 'asc' })).toEqual(['네온', '라피', '앨리스', '홍련'])
  })

  it('reverses the name order when the direction is descending', () => {
    expect(run({ sortKey: 'name', sortDir: 'desc' })).toEqual(['홍련', '앨리스', '라피', '네온'])
  })

  it('matches a name by substring, ignoring case and surrounding space', () => {
    expect(run({ query: '  련 ' })).toEqual(['홍련'])
  })

  it('finds nothing for a query no name contains', () => {
    expect(run({ query: '없는이름' })).toEqual([])
  })

  // 니케 이름은 한글인데 유저가 기억하는 것이 영문일 때가 있다. 슬러그가 곧
  // 케밥케이스 영문명이라(backend/tests/test_resource_id_directory.py가
  // 고정한다) 백엔드가 영문명을 따로 안 내보내도 된다.
  it('영문으로 치면 슬러그로 맞는다', () => {
    expect(run({ query: 'scar' })).toEqual(['홍련'])
    expect(run({ query: 'RAPI' })).toEqual(['라피'])
  })

  it('슬러그의 하이픈과 질의의 공백을 같은 것으로 본다', () => {
    const rows: Row[] = [
      { slug: 'ada-wong', name: '에이다 웡', element: 'Fire', burstTier: 3, overload: [] },
    ]
    const search = (query: string) =>
      names(filterAndSort(rows, facets, { ...EMPTY_FILTER, query }))
    expect(search('ada wong')).toEqual(['에이다 웡'])
    expect(search('ada-wong')).toEqual(['에이다 웡'])
    expect(search('adawong')).toEqual(['에이다 웡'])
  })

  it('초성으로 치면 이름의 초성으로 맞는다', () => {
    expect(run({ query: 'ㅎㄹ' })).toEqual(['홍련'])
    expect(run({ query: 'ㄴㅇ' })).toEqual(['네온'])
  })

  // 한글 질의에서 영숫자만 남기면 빈 문자열이고, 빈 문자열은 모든 슬러그에
  // includes로 맞는다. 가드가 없으면 초성 검색이 아무것도 안 거르는
  // "전부 표시"가 되는데, 값이 전부 그럴듯해 눈으로는 안 보인다.
  it('초성 질의가 슬러그 갈래로 새어 전부 통과시키지 않는다', () => {
    expect(run({ query: 'ㅎㄹ' })).toHaveLength(1)
    expect(run({ query: 'ㅋ' })).toEqual([])
  })

  // 완성형이 섞인 질의는 초성 대조가 답할 수 없다 - 완성형 부분일치가 맡는다.
  it('완성형이 섞인 질의는 초성으로 맞추지 않는다', () => {
    expect(run({ query: '홍ㄹ' })).toEqual([])
    expect(run({ query: '홍' })).toEqual(['홍련'])
  })

  // 유저들은 공식 표기가 아니라 자기들이 부르는 이름으로 찾는다. 별명은
  // lib/nikkeAliases.ts가 관리한다.
  it('별명으로 치면 그 니케가 맞는다', () => {
    expect(searchAlias('흑련')).toEqual(['홍련: 흑영'])
    expect(searchAlias('세이렌')).toEqual(['리틀 머메이드'])
  })

  it('별명도 초성으로 찾을 수 있다', () => {
    // 이름에 초성이 되는데 별명만 안 되면 유저는 규칙을 둘로 기억해야 한다.
    // 'ㅎㄹ'은 「홍련: 흑영」의 이름 초성이기도 하므로, 별명 갈래만 재려면
    // 이름 초성과 겹치지 않는 'ㅅㅇㄹ'(세이렌)로 물어야 한다.
    expect(searchAlias('ㅅㅇㄹ')).toEqual(['리틀 머메이드'])
  })

  it('별명이 없는 니케까지 통과시키지는 않는다', () => {
    expect(searchAlias('흑련')).toHaveLength(1)
    expect(searchAlias('없는별명')).toEqual([])
  })

  it('keeps only the chosen elements, treating an empty list as no filter', () => {
    expect(run({ elements: ['Fire'] })).toEqual(['네온', '홍련'])
    expect(run({ elements: ['Fire', 'Wind'] })).toEqual(['네온', '앨리스', '홍련'])
  })

  it('keeps only the chosen burst tiers', () => {
    expect(run({ burstTiers: [1] })).toEqual(['네온', '라피'])
  })

  // The two facets narrow together, not alternately.
  it('intersects the element and burst filters', () => {
    expect(run({ elements: ['Fire'], burstTiers: [1] })).toEqual(['네온'])
  })

  it('sorts by one overload stat, highest first when descending', () => {
    expect(run({ sortKey: '공', sortDir: 'desc' })).toEqual(['홍련', '라피', '네온', '앨리스'])
  })

  // A unit that never rolled the stat contributes 0 of it, so it sorts as the
  // number it is - which is exactly what "which units did I not invest in"
  // asks for in ascending order.
  it('treats a stat the unit never rolled as zero', () => {
    expect(run({ sortKey: '공', sortDir: 'asc' })).toEqual(['네온', '앨리스', '라피', '홍련'])
  })

  // Two units on 0 must not swap places between renders.
  it('breaks a tie by name, in both directions', () => {
    expect(run({ sortKey: '장탄', sortDir: 'desc' })).toEqual(['네온', '라피', '앨리스', '홍련'])
    expect(run({ sortKey: '장탄', sortDir: 'asc' })).toEqual(['네온', '라피', '앨리스', '홍련'])
  })

  it('leaves the caller array untouched', () => {
    const original = [...ROWS]
    filterAndSort(ROWS, facets, { ...EMPTY_FILTER, sortDir: 'desc' })
    expect(ROWS).toEqual(original)
  })
})

describe('isFiltering', () => {
  it('is false for the empty filter', () => {
    expect(isFiltering(EMPTY_FILTER)).toBe(false)
  })

  it('is true once any facet narrows the list', () => {
    expect(isFiltering({ ...EMPTY_FILTER, query: '홍' })).toBe(true)
    expect(isFiltering({ ...EMPTY_FILTER, elements: ['Fire'] })).toBe(true)
    expect(isFiltering({ ...EMPTY_FILTER, burstTiers: [2] })).toBe(true)
  })

  it('ignores whitespace-only search text', () => {
    expect(isFiltering({ ...EMPTY_FILTER, query: '   ' })).toBe(false)
  })

  // Sorting reorders; it never hides. The "N기 중 M기" line and the clear
  // button are about hiding, so a sort choice must not raise them.
  it('is false for a sort choice alone', () => {
    expect(isFiltering({ ...EMPTY_FILTER, sortKey: '우코', sortDir: 'desc' })).toBe(false)
  })
})
