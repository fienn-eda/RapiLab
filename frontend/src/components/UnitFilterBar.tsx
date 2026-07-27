// The search / filter / sort toolbar over a unit grid. Shared by the roster
// tab and the recommend palette.
//
// Controlled and stateless: the grid that draws the units owns the filter, so
// the two tabs keep independent filters without this component knowing there
// is more than one of it.
//
// It narrows what is DRAWN and nothing else. In the recommend tab the
// candidate pool is a separate toggle on each portrait, and a unit hidden
// here is still in the pool - which is why the count line and the clear
// button are not optional chrome: they are the only thing that explains
// where the rest of the grid went.

import { useId } from 'react'
import { elementLabel } from '../lib/elementName'
import {
  EMPTY_FILTER,
  isFiltering,
  type SortKey,
  type UnitFilterState,
} from '../lib/unitFilter'
import { OVERLOAD_KEYS } from '../lib/overload'
import { BURST_TIERS, type NikkeElement } from '../types/supportedUnit'

// Element order follows the game's own listing, which is also the order the
// element tokens are declared in index.css.
const ELEMENTS: readonly NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']

interface UnitFilterBarProps {
  value: UnitFilterState
  onChange: (next: UnitFilterState) => void
  /** 필터를 통과한 개수와 전체 개수. 숨긴 유닛이 있을 때만 쓰인다. */
  shown: number
  total: number
}

/** 다중 선택 축에서 한 값을 켜고 끈다. */
const toggle = <T,>(list: T[], value: T): T[] =>
  list.includes(value) ? list.filter((item) => item !== value) : [...list, value]

export function UnitFilterBar({ value, onChange, shown, total }: UnitFilterBarProps) {
  const searchId = useId()
  const sortId = useId()
  const sortDirId = useId()
  const elementsId = useId()
  const tiersId = useId()
  const filtering = isFiltering(value)

  return (
    <div className="unit-filter">
      <div className="unit-filter__row">
        <label className="unit-filter__label" htmlFor={searchId}>
          이름 검색
        </label>
        <input
          id={searchId}
          type="search"
          className="unit-filter__search"
          placeholder="니케 이름"
          value={value.query}
          onChange={(event) => onChange({ ...value, query: event.target.value })}
        />

        <label className="unit-filter__label" htmlFor={sortId}>
          정렬
        </label>
        <select
          id={sortId}
          className="unit-filter__select"
          value={value.sortKey}
          onChange={(event) => onChange({ ...value, sortKey: event.target.value as SortKey })}
        >
          <option value="name">이름</option>
          {OVERLOAD_KEYS.map((key) => (
            <option key={key} value={key}>
              {key}
            </option>
          ))}
        </select>

        {/* A select rather than an arrow toggle: a button whose label has to
            state both the current direction and the action it performs reads
            wrong whichever of the two it names. */}
        <label className="unit-filter__label" htmlFor={sortDirId}>
          정렬 방향
        </label>
        <select
          id={sortDirId}
          className="unit-filter__select"
          value={value.sortDir}
          onChange={(event) =>
            onChange({ ...value, sortDir: event.target.value as UnitFilterState['sortDir'] })
          }
        >
          <option value="asc">오름차순</option>
          <option value="desc">내림차순</option>
        </select>
      </div>

      <div className="unit-filter__row">
        <span className="unit-filter__label" id={elementsId}>
          속성
        </span>
        <div className="unit-filter__chips" role="group" aria-labelledby={elementsId}>
          {ELEMENTS.map((element) => (
            <button
              key={element}
              type="button"
              className="unit-filter__chip"
              // Tints the lit chip with that element's colour, the same token
              // the portrait borders use.
              data-element={element}
              aria-pressed={value.elements.includes(element)}
              onClick={() => onChange({ ...value, elements: toggle(value.elements, element) })}
            >
              {elementLabel(element)}
            </button>
          ))}
        </div>

        <span className="unit-filter__label" id={tiersId}>
          단계
        </span>
        <div className="unit-filter__chips" role="group" aria-labelledby={tiersId}>
          {BURST_TIERS.map((tier) => (
            <button
              key={tier}
              type="button"
              className="unit-filter__chip"
              aria-pressed={value.burstTiers.includes(tier)}
              onClick={() => onChange({ ...value, burstTiers: toggle(value.burstTiers, tier) })}
            >
              B{tier}
            </button>
          ))}
        </div>
      </div>

      {filtering && (
        <p className="unit-filter__status">
          <span aria-live="polite">
            {total}기 중 {shown}기 표시 중
          </span>
          {/* Clears only what hides units. Resetting the sort as well would
              reorder the grid on a button that never said it would. */}
          <button
            type="button"
            className="unit-filter__clear"
            onClick={() =>
              onChange({
                ...value,
                query: EMPTY_FILTER.query,
                elements: EMPTY_FILTER.elements,
                burstTiers: EMPTY_FILTER.burstTiers,
              })
            }
          >
            필터 해제
          </button>
        </p>
      )}

      {filtering && shown === 0 && total > 0 && (
        <p className="unit-filter__empty">조건에 맞는 니케가 없어요.</p>
      )}
    </div>
  )
}
