import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NikkeCard } from './NikkeCard'
import { makeEmptyDraft, type NikkeDraft } from '../types/nikkeDraft'

const renderCard = (draft: NikkeDraft = makeEmptyDraft()) => {
  const onChange = vi.fn()
  const onRemove = vi.fn()
  render(
    <NikkeCard draft={draft} index={0} onChange={onChange} onRemove={onRemove} />,
  )
  return { onChange, onRemove, draft }
}

const filledDraft = (): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: 'red-hood',
  level: '200',
  core_level: '7',
  hp: '1000000',
  atk: '85000',
  def_: '12000',
  skill_levels: { skill1: '10', skill2: '7', burst: '4' },
})

describe('NikkeCard', () => {
  it('falls back to a positional title before a slug is entered', () => {
    renderCard()
    expect(screen.getByRole('heading', { name: 'Nikke 1' })).toBeInTheDocument()
  })

  it('uses the character slug as the title once entered', () => {
    renderCard(filledDraft())
    expect(screen.getByRole('heading', { name: 'red-hood' })).toBeInTheDocument()
  })

  it('shows a "Draft" pill and no field errors before the card is touched', () => {
    renderCard()
    expect(screen.getByText('Draft')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('surfaces validation errors after the card loses focus', async () => {
    const user = userEvent.setup()
    renderCard()
    const slug = screen.getByLabelText(/character slug/i)
    await user.click(slug)
    await user.tab()
    const alerts = await screen.findAllByRole('alert')
    expect(alerts.length).toBeGreaterThan(0)
    expect(screen.getByText(/issue/)).toBeInTheDocument()
  })

  it('shows a "Ready" pill for a complete, valid draft', () => {
    renderCard(filledDraft())
    expect(screen.getByText('Ready')).toBeInTheDocument()
  })

  it('propagates edits through onChange', async () => {
    const user = userEvent.setup()
    const { onChange } = renderCard()
    await user.type(screen.getByLabelText(/character slug/i), 'a')
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ character_slug: 'a' }),
    )
  })

  it('calls onRemove when the remove button is clicked', async () => {
    const user = userEvent.setup()
    const { onRemove } = renderCard()
    await user.click(screen.getByRole('button', { name: /remove nikke 1/i }))
    expect(onRemove).toHaveBeenCalledOnce()
  })
})
