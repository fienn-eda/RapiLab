import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
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
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
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
})
