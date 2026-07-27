import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RosterGrid } from './RosterGrid'
import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'
import type { SupportedUnit } from '../types/supportedUnit'

const draft = (slug: string): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: slug,
  grade: 3,
  core: 0,
  level: '400',
  hp: '1',
  atk: '1',
  def_: '1',
  skill_levels: { skill1: '10', skill2: '10', burst: '10' },
  overload_options: [],
})

const SUPPORTED: SupportedUnit[] = [
  { slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' },
  { slug: 'anne', name: 'Anne', burstTier: 1, element: 'Fire' },
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
  { slug: 'blanc', name: 'Blanc', burstTier: 3, element: 'Wind' },
]

const grid = (slugs: string[], supportedUnits = SUPPORTED) =>
  render(
    <RosterGrid
      drafts={slugs.map(draft)}
      supportedUnits={supportedUnits}
      portraitFor={() => null}
    />,
  )

describe('RosterGrid', () => {
  it('gives a card to every owned unit the engine supports', () => {
    grid(['crown', 'liter'])
    expect(screen.getByRole('heading', { name: 'Crown' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Liter' })).toBeInTheDocument()
  })

  // More than half a real roster is unsupported. Drawing those as full cards
  // buried the ones that can actually be fielded.
  it('demotes owned units the engine cannot simulate to a collapsed list', () => {
    const { container } = grid(['crown', '2b', 'alice-wonderland-bunny'])

    expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
    expect(container.querySelectorAll('.roster-card')).toHaveLength(1)

    const details = container.querySelector('details')!
    expect(details.open).toBe(false)
  })

  it('names an unsupported unit from its slug, since nothing else can', () => {
    grid(['2b', 'alice-wonderland-bunny'])
    expect(screen.getByText('2B')).toBeInTheDocument()
    expect(screen.getByText('Alice Wonderland Bunny')).toBeInTheDocument()
  })

  it('says nothing about unsupported units when every owned unit is supported', () => {
    const { container } = grid(['crown', 'liter'])
    expect(container.querySelector('details')).toBeNull()
  })

  // The list arrives over the network; until it does, nothing is known to be
  // supported and the whole roster lands in the collapsed section rather than
  // vanishing.
  it('keeps every unit reachable while the supported list is still empty', () => {
    grid(['crown', 'liter'], [])
    expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
    expect(screen.getByText('Crown')).toBeInTheDocument()
  })

  // A bordered toolbar with nothing to filter reads as a bug, not a feature -
  // this covers both an empty roster and a roster the supported list hasn't
  // loaded for yet.
  it('does not draw the filter toolbar when there is no supported unit to filter', () => {
    grid(['crown'], [])
    expect(screen.queryByLabelText('이름 검색')).not.toBeInTheDocument()
  })

  it('does not draw the filter toolbar for an empty roster', () => {
    grid([])
    expect(screen.queryByLabelText('이름 검색')).not.toBeInTheDocument()
  })

  describe('burst grouping and the filter', () => {
    const overloaded = (slug: string, value: number): NikkeDraft => ({
      ...draft(slug),
      overload_options: [{ id: `${slug}-ol`, name: '공격력 증가', value: String(value) }],
    })

    it('splits the supported units into B1/B2/B3 sections', () => {
      grid(['crown', 'liter', 'blanc'])
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()
    })

    it('draws no heading for a burst tier the player owns nobody in', () => {
      grid(['crown'])
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B2' })).not.toBeInTheDocument()
    })

    // Default sort is by name, so the grid reads 가나다순 rather than in
    // whatever order the roster arrived.
    it('orders a group by name before the user chooses anything', () => {
      const { container } = grid(['crown', 'anne'])
      const names = [...container.querySelectorAll('.roster-card__name')].map((n) => n.textContent)
      expect(names).toEqual(['Anne', 'Crown'])
    })

    it('hides the cards an element filter excludes', async () => {
      const user = userEvent.setup()
      const { container } = grid(['crown', 'anne', 'liter'])
      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(container.querySelectorAll('.roster-card')).toHaveLength(1)
      expect(screen.getByRole('heading', { name: 'Anne' })).toBeInTheDocument()
    })

    it('sorts a group by an overload stat within the group only', async () => {
      const user = userEvent.setup()
      render(
        <RosterGrid
          drafts={[overloaded('crown', 10), overloaded('anne', 90), overloaded('liter', 50)]}
          supportedUnits={SUPPORTED}
          portraitFor={() => null}
        />,
      )
      await user.selectOptions(screen.getByLabelText('정렬'), '공')
      await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')

      const b1 = screen.getByRole('heading', { name: 'B1' }).closest('section')!
      expect([...b1.querySelectorAll('.roster-card__name')].map((n) => n.textContent)).toEqual([
        'Anne',
        'Crown',
      ])
      // Liter outranks neither - she is in another group entirely.
      const b2 = screen.getByRole('heading', { name: 'B2' }).closest('section')!
      expect([...b2.querySelectorAll('.roster-card__name')].map((n) => n.textContent)).toEqual([
        'Liter',
      ])
    })

    // Unsupported units have no element and no burst tier to filter on, so the
    // toolbar deliberately does not reach them.
    it('leaves the unsupported list whole no matter what is filtered', async () => {
      const user = userEvent.setup()
      grid(['crown', '2b', 'alice-wonderland-bunny'])
      await user.click(screen.getByRole('button', { name: '수냉' }))
      expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
      expect(screen.getByText('2B')).toBeInTheDocument()
    })

    it('counts against the supported units alone', async () => {
      const user = userEvent.setup()
      grid(['crown', 'anne', '2b'])
      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(screen.getByText('2기 중 1기 표시 중')).toBeInTheDocument()
    })
  })
})
