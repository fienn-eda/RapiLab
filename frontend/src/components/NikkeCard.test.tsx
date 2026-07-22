import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NikkeCard } from './NikkeCard'
import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'

const filledDraft = (): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: 'red-hood',
  grade: 3,
  core: 7,
  level: '200',
  hp: '1000000',
  atk: '85000',
  def_: '12000',
  skill_levels: { skill1: '10', skill2: '7', burst: '4' },
  overload_options: [{ id: '1', name: 'Elemental Damage', value: '18.2' }],
})

describe('NikkeCard', () => {
  it('falls back to a positional title when no slug is set', () => {
    render(<NikkeCard draft={makeEmptyDraft()} index={0} />)
    expect(screen.getByRole('heading', { name: 'Nikke 1' })).toBeInTheDocument()
  })

  it('uses the character slug as the title once synced', () => {
    render(<NikkeCard draft={filledDraft()} index={0} />)
    expect(screen.getByRole('heading', { name: 'red-hood' })).toBeInTheDocument()
  })

  it('renders the synced level/HP/ATK/DEF as plain text', () => {
    render(<NikkeCard draft={filledDraft()} index={0} />)
    expect(screen.getByText('200')).toBeInTheDocument()
    expect(screen.getByText('1000000')).toBeInTheDocument()
    expect(screen.getByText('85000')).toBeInTheDocument()
    expect(screen.getByText('12000')).toBeInTheDocument()
  })

  it('renders the synced skill levels', () => {
    render(<NikkeCard draft={filledDraft()} index={0} />)
    expect(screen.getByText(/Skill 1/)).toBeInTheDocument()
    expect(screen.getByText(/Skill 2/)).toBeInTheDocument()
    expect(screen.getByText(/Burst/)).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('renders synced overload option lines', () => {
    render(<NikkeCard draft={filledDraft()} index={0} />)
    expect(screen.getByText('Elemental Damage')).toBeInTheDocument()
    expect(screen.getByText('18.2')).toBeInTheDocument()
  })

  it('shows the investment badge from grade/core', () => {
    render(<NikkeCard draft={filledDraft()} index={0} />)
    expect(screen.getByText('★★★')).toBeInTheDocument()
    expect(screen.getByText('+7')).toBeInTheDocument()
  })

  it('renders no editable inputs or remove button', () => {
    render(<NikkeCard draft={filledDraft()} index={0} />)
    expect(screen.queryAllByRole('textbox')).toHaveLength(0)
    expect(screen.queryAllByRole('spinbutton')).toHaveLength(0)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
