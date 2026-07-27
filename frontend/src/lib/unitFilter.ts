// Search, filter and sort for a unit grid. Shared by the roster tab and the
// recommend palette, which hold the same units in different shapes.
//
// Pure, and deliberately so: this decides what is DRAWN. The recommend tab's
// candidate pool is a separate concept living in RecommendPanel's
// `excludedSlugs`, and nothing here may touch it - hiding a unit must never
// remove it from the search (see the design spec, decision 5).

import { abbreviateOverload, type OverloadKey } from './overload'
import type { BurstTier, NikkeElement } from '../types/supportedUnit'

export type SortKey = 'name' | OverloadKey

export interface UnitFilterState {
  /** 이름 부분일치. 빈 문자열(과 공백뿐인 문자열) = 조건 없음. */
  query: string
  /** 빈 배열 = 전부 표시. "전체" 항목을 따로 두지 않기 위한 규약. */
  elements: NikkeElement[]
  /** 빈 배열 = 전부 표시. */
  burstTiers: BurstTier[]
  sortKey: SortKey
  sortDir: 'asc' | 'desc'
}

/** 기본 상태. 정렬 기본값이 이름·오름차순이라, 필터를 아무것도 걸지 않아도
 * 그리드는 가나다순으로 그려진다 - 백엔드가 준 순서는 유저에게 의미가 없다. */
export const EMPTY_FILTER: UnitFilterState = {
  query: '',
  elements: [],
  burstTiers: [],
  sortKey: 'name',
  sortDir: 'asc',
}

/** 무언가 숨겨지고 있는가. 정렬은 순서만 바꾸고 아무것도 숨기지 않으므로
 * 여기 포함되지 않는다 - "N기 중 M기 표시 중"과 "필터 해제"를 가르는 값. */
export const isFiltering = (state: UnitFilterState): boolean =>
  state.query.trim() !== '' ||
  state.elements.length > 0 ||
  state.burstTiers.length > 0

/** 필터·정렬이 유닛에서 읽는 것 전부. 호출부가 자기 저장 모양을 이걸로
 * 환원해 넘기므로, 두 화면이 데이터 구조를 통일하지 않고도 규칙을 공유한다. */
export interface UnitFacets {
  name: string
  element: NikkeElement
  burstTier: BurstTier
  overload: { name: string; value: number | string }[]
}

/** 한 오버로드 옵션의 4부위 합산값. 안 굴렸으면 0 - 실제 기여가 0이므로
 * 특별 취급하지 않고 그 숫자로 줄 세운다. 값이 문자열인 쪽(NikkeDraft)과
 * 숫자인 쪽(UserNikkeState)을 같이 받으므로 Number()로 통일한다. */
const overloadValue = (facets: UnitFacets, key: OverloadKey): number => {
  const line = facets.overload.find((option) => abbreviateOverload(option.name) === key)
  if (line === undefined) return 0
  const value = Number(line.value)
  return Number.isFinite(value) ? value : 0
}

const matches = (facets: UnitFacets, state: UnitFilterState): boolean => {
  const query = state.query.trim().toLowerCase()
  if (query !== '' && !facets.name.toLowerCase().includes(query)) return false
  if (state.elements.length > 0 && !state.elements.includes(facets.element)) return false
  if (state.burstTiers.length > 0 && !state.burstTiers.includes(facets.burstTier)) return false
  return true
}

export function filterAndSort<T>(
  items: T[],
  facets: (item: T) => UnitFacets,
  state: UnitFilterState,
): T[] {
  const kept = items.filter((item) => matches(facets(item), state))
  const sign = state.sortDir === 'asc' ? 1 : -1
  // Always ascending, whichever way the primary sort runs: a tie-break exists
  // to make the order reproducible, and one that flipped with direction would
  // not be.
  const byName = (a: T, b: T) => facets(a).name.localeCompare(facets(b).name, 'ko')

  if (state.sortKey === 'name') return kept.sort((a, b) => sign * byName(a, b))

  const key = state.sortKey
  return kept.sort((a, b) => {
    const diff = overloadValue(facets(a), key) - overloadValue(facets(b), key)
    return diff !== 0 ? sign * diff : byName(a, b)
  })
}
