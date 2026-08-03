import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnitFilterBar } from './UnitFilterBar'
import { EMPTY_FILTER, type UnitFilterState } from '../lib/unitFilter'

const bar = (value: Partial<UnitFilterState> = {}, counts: { shown?: number; total?: number } = {}) => {
  const onChange = vi.fn()
  render(
    <UnitFilterBar
      value={{ ...EMPTY_FILTER, ...value }}
      onChange={onChange}
      shown={counts.shown ?? 5}
      total={counts.total ?? 5}
    />,
  )
  return onChange
}

describe('UnitFilterBar', () => {
  it('offers every element as a Korean-labelled toggle', () => {
    bar()
    for (const label of ['작열', '수냉', '풍압', '철갑', '전격']) {
      expect(screen.getByRole('button', { name: label })).toHaveAttribute('aria-pressed', 'false')
    }
  })

  it('offers the three burst tiers as toggles', () => {
    bar()
    for (const label of ['B1', 'B2', 'B3']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
  })

  // The chips carry the game's own icons. Their names still come from the
  // markup - the alt text IS the button's accessible name - so a chip stays
  // reachable by "작열" for a screen reader and for the tests above.
  it('draws each element chip as its icon and no text', () => {
    bar()
    const chip = screen.getByRole('button', { name: '작열' })
    expect(chip).toHaveTextContent('')
    expect(chip.querySelector('img')).toHaveAttribute('src', '/elements/fire.png')
  })

  it('draws each burst chip as its icon and no text', () => {
    bar()
    const chip = screen.getByRole('button', { name: 'B2' })
    expect(chip).toHaveTextContent('')
    expect(chip.querySelector('img')).toHaveAttribute('src', '/elements/icon-burst-2.png')
  })

  // The icons say what the groups are, so a heading over each would be naming
  // them twice. The group keeps the name for anyone who cannot see them.
  it('drops the group headings but keeps the groups named', () => {
    bar()
    expect(screen.queryByText('속성')).not.toBeInTheDocument()
    expect(screen.queryByText('단계')).not.toBeInTheDocument()
    expect(screen.getByRole('group', { name: '속성' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: '단계' })).toBeInTheDocument()
  })

  it('puts the sort controls under the search box and left of the filters', () => {
    bar()
    const search = screen.getByLabelText('이름 검색')
    const sort = screen.getByLabelText('정렬')
    const elements = screen.getByRole('group', { name: '속성' })
    expect(sort.closest('.unit-filter__row')).not.toBe(search.closest('.unit-filter__row'))
    expect(elements.closest('.unit-filter__row')).toBe(sort.closest('.unit-filter__row'))
    const follows = (a: Element, b: Element) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING)
    expect(follows(search, sort)).toBe(true)
    expect(follows(sort, elements)).toBe(true)
  })

  it('adds an element to the filter when its chip is pressed', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.click(screen.getByRole('button', { name: '작열' }))
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, elements: ['Fire'] })
  })

  // Pressing a lit chip must clear that one facet value, not the whole filter.
  it('removes an element that is already in the filter', async () => {
    const user = userEvent.setup()
    const onChange = bar({ elements: ['Fire', 'Water'] })
    await user.click(screen.getByRole('button', { name: '작열' }))
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, elements: ['Water'] })
  })

  it('shows a pressed chip for each active element', () => {
    bar({ elements: ['Water'] })
    expect(screen.getByRole('button', { name: '수냉' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '작열' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('toggles a burst tier as a number, not a label', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.click(screen.getByRole('button', { name: 'B2' }))
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, burstTiers: [2] })
  })

  it('reports what was typed into the search box', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.type(screen.getByLabelText('이름 검색'), '홍')
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, query: '홍' })
  })

  it('lists the seven overload stats alongside 이름 in the sort menu', () => {
    bar()
    const sort = screen.getByLabelText('정렬')
    expect([...sort.querySelectorAll('option')].map((o) => o.textContent)).toEqual([
      '이름', '우코', '공', '장탄', '차속', '크댐', '크확', '차댐',
    ])
  })

  it('reports a chosen sort stat', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.selectOptions(screen.getByLabelText('정렬'), '우코')
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, sortKey: '우코' })
  })

  it('reports a chosen sort direction', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, sortDir: 'desc' })
  })

  // A hidden unit must never be silently missing: the count is the only thing
  // that explains where the rest of the roster went.
  it('says how many units survived the filter', () => {
    bar({ elements: ['Fire'] }, { shown: 2, total: 70 })
    expect(screen.getByText('70기 중 2기 표시 중')).toBeInTheDocument()
  })

  it('says nothing about counts when nothing is hidden', () => {
    bar({ sortKey: '우코', sortDir: 'desc' })
    expect(screen.queryByText(/표시 중/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '필터 해제' })).not.toBeInTheDocument()
  })

  // Clearing is about hiding, so it leaves the sort choice alone - otherwise
  // "필터 해제" would silently reorder the grid too.
  it('clears the three narrowing facets but keeps the sort', async () => {
    const user = userEvent.setup()
    const onChange = bar({ query: '홍', elements: ['Fire'], burstTiers: [3], sortKey: '우코', sortDir: 'desc' })
    await user.click(screen.getByRole('button', { name: '필터 해제' }))
    expect(onChange).toHaveBeenCalledWith({
      ...EMPTY_FILTER,
      sortKey: '우코',
      sortDir: 'desc',
    })
  })

  it('says so when the filter matched nothing at all', () => {
    bar({ query: '없는이름' }, { shown: 0, total: 70 })
    expect(screen.getByText('조건에 맞는 니케가 없어요.')).toBeInTheDocument()
  })

  // An empty roster is not a filter that matched nothing.
  it('stays quiet when there were no units to begin with', () => {
    bar({ query: '홍' }, { shown: 0, total: 0 })
    expect(screen.queryByText('조건에 맞는 니케가 없어요.')).not.toBeInTheDocument()
  })
})
