import { describe, it, expect } from 'vitest'
import {
  EMPTY_FILTER,
  filterAndSort,
  isFiltering,
  type UnitFacets,
  type UnitFilterState,
} from './unitFilter'

interface Row {
  name: string
  element: UnitFacets['element']
  burstTier: UnitFacets['burstTier']
  overload: { name: string; value: number | string }[]
}

const facets = (row: Row): UnitFacets => row

const ROWS: Row[] = [
  { name: '홍련', element: 'Fire', burstTier: 3, overload: [{ name: '공격력 증가', value: 40.91 }] },
  { name: '라피', element: 'Water', burstTier: 1, overload: [{ name: '공격력 증가', value: 12.5 }] },
  { name: '네온', element: 'Fire', burstTier: 1, overload: [{ name: '우월코드 대미지 증가', value: 99.82 }] },
  { name: '앨리스', element: 'Wind', burstTier: 3, overload: [] },
]

const names = (rows: Row[]) => rows.map((row) => row.name)
const run = (state: Partial<UnitFilterState>) =>
  names(filterAndSort(ROWS, facets, { ...EMPTY_FILTER, ...state }))

describe('filterAndSort', () => {
  it('keeps every unit when nothing is filtered', () => {
    expect(run({}).sort()).toEqual(['네온', '라피', '앨리스', '홍련'].sort())
  })

  // The default sort is by name, so an unfiltered grid is 가나다순 rather than
  // whatever order the backend happened to return.
  it('sorts by name in Korean collation order by default', () => {
    expect(run({})).toEqual(['네온', '라피', '앨리스', '홍련'])
  })

  it('reverses the name order when the direction is descending', () => {
    expect(run({ sortDir: 'desc' })).toEqual(['홍련', '앨리스', '라피', '네온'])
  })

  it('matches a name by substring, ignoring case and surrounding space', () => {
    expect(run({ query: '  련 ' })).toEqual(['홍련'])
  })

  it('finds nothing for a query no name contains', () => {
    expect(run({ query: '없는이름' })).toEqual([])
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
