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
import { HelpText } from './HelpText'
import { HELP } from '../lib/helpText'

// Element order follows the game's own listing, which is also the order the
// element tokens are declared in index.css.
const ELEMENTS: readonly NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']

// The game's own code and burst icons (scripts/download_element_icons.py).
// A chip is the icon alone, so the alt text is what names the button - which
// is why it is the Korean label and not a filename or an empty string.
const ELEMENT_ICON: Record<NikkeElement, string> = {
  Fire: '/elements/fire.png',
  Water: '/elements/water.png',
  Wind: '/elements/wind.png',
  Iron: '/elements/iron.png',
  Electric: '/elements/electric.png',
}

interface UnitFilterBarProps {
  value: UnitFilterState
  onChange: (next: UnitFilterState) => void
  /** 필터를 통과한 개수와 전체 개수. 숨긴 유닛이 있을 때만 쓰인다. */
  shown: number
  total: number
  /** 이 화면에 후보 풀이라는 개념이 있는가. 없으면 「제외」 칩을 안 그린다 -
   * 아무것도 제외될 수 없는 화면에서 그 칩은 언제나 빈 격자를 만든다. */
  excludable?: boolean
}

/** 다중 선택 축에서 한 값을 켜고 끈다. */
const toggle = <T,>(list: T[], value: T): T[] =>
  list.includes(value) ? list.filter((item) => item !== value) : [...list, value]

export function UnitFilterBar({
  value,
  onChange,
  shown,
  total,
  excludable = false,
}: UnitFilterBarProps) {
  const searchId = useId()
  const sortId = useId()
  const sortDirId = useId()
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
          placeholder="이름 · 별명 · 초성 · 영문"
          value={value.query}
          onChange={(event) => onChange({ ...value, query: event.target.value })}
        />
      </div>

      {/* Sorting reorders, the chips hide - two different jobs sharing a row.
          They sit together under the search box because the search box is the
          one control wide enough to want a line of its own. */}
      <div className="unit-filter__row">
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

        {/* No heading over either group: the icons are the game's own and say
            what they are. The group keeps the name for anyone who cannot see
            them, and each chip is named by its icon's alt text. */}
        <div className="unit-filter__chips" role="group" aria-label="속성">
          {ELEMENTS.map((element) => (
            <button
              key={element}
              type="button"
              className="unit-filter__chip unit-filter__chip--icon"
              // Tints the lit chip with that element's colour, the same token
              // the portrait borders use.
              data-element={element}
              aria-pressed={value.elements.includes(element)}
              onClick={() => onChange({ ...value, elements: toggle(value.elements, element) })}
            >
              <img
                className="unit-filter__icon"
                src={ELEMENT_ICON[element]}
                alt={elementLabel(element)}
              />
            </button>
          ))}
        </div>

        <div className="unit-filter__chips" role="group" aria-label="단계">
          {BURST_TIERS.map((tier) => (
            <button
              key={tier}
              type="button"
              className="unit-filter__chip unit-filter__chip--icon"
              aria-pressed={value.burstTiers.includes(tier)}
              onClick={() => onChange({ ...value, burstTiers: toggle(value.burstTiers, tier) })}
            >
              <img
                className="unit-filter__icon"
                src={`/elements/icon-burst-${tier}.png`}
                alt={`B${tier}`}
              />
            </button>
          ))}
        </div>

        {/* 속성·단계와 같은 「선택한 것만 표시」 규약이라 같은 칩 모양을 쓴다.
            아이콘이 없는 축이라 글자로 서고, 그래서 다른 칩들과 높이를 맞추는
            것은 CSS 몫이다. 축이 하나뿐이라 role="group"은 안 붙인다 - 버튼
            자신의 글자가 이미 그 이름이다. */}
        {excludable && (
          <div className="unit-filter__chips">
            <button
              type="button"
              className="unit-filter__chip unit-filter__chip--text"
              aria-pressed={value.excludedOnly}
              onClick={() => onChange({ ...value, excludedOnly: !value.excludedOnly })}
            >
              제외한 니케
            </button>
          </div>
        )}
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
                excludedOnly: EMPTY_FILTER.excludedOnly,
              })
            }
          >
            필터 해제
          </button>
        </p>
      )}

      {filtering && shown === 0 && total > 0 && (
        <p className="unit-filter__empty"><HelpText>{HELP.roster.emptyFilter}</HelpText></p>
      )}
    </div>
  )
}
