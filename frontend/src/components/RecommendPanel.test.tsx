import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RecommendPanel } from './RecommendPanel'
import type { UserNikkeState } from '../types/userNikkeState'

vi.mock('../api/recommend', () => ({
  recommendDecks: vi.fn(),
}))

import { recommendDecks } from '../api/recommend'

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 200,
  core_level: 7,
  hp: 1_000_000,
  atk: 85_000,
  def_: 12_000,
  skill_levels: { skill1: 10, skill2: 7, burst: 4 },
  overload_options: [],
  pve_cube: null,
})

const fullRoster = ['a', 'b', 'c', 'd', 'e'].map(nikke)

afterEach(() => {
  vi.mocked(recommendDecks).mockReset()
})

describe('RecommendPanel', () => {
  it('disables submit and shows a guard message when the roster has under 5 Nikkes', () => {
    render(<RecommendPanel roster={fullRoster.slice(0, 2)} />)
    expect(
      screen.getByText('Add at least 5 ready Nikkes to recommend a deck.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /recommend decks/i })).toBeDisabled()
  })

  it('submits the roster and boss profile, and renders the ranked results', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
        },
      ],
    })

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByRole('button', { name: /recommend decks/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: { element: null, core_hittable: false, enemy_def: 0, fight_duration: 180 },
    })
    expect(await screen.findByText('#1')).toBeInTheDocument()
    expect(screen.getByText('100 total dmg')).toBeInTheDocument()
  })

  it('shows the backend error message on a failed submission', async () => {
    const user = userEvent.setup()
    const { RecommendApiError } = await import('../api/recommendApiError')
    vi.mocked(recommendDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: 'No feasible 5-unit deck.' }),
    )

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByRole('button', { name: /recommend decks/i }))

    expect(await screen.findByText('No feasible 5-unit deck.')).toBeInTheDocument()
  })

  it('sends the entered element and enemy DEF instead of the defaults', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [] })

    render(<RecommendPanel roster={fullRoster} />)
    await user.selectOptions(screen.getByLabelText('Element'), 'Fire')
    await user.click(screen.getByLabelText('Core is hittable'))
    const enemyDef = screen.getByLabelText('Enemy DEF')
    await user.clear(enemyDef)
    await user.type(enemyDef, '20000')

    await user.click(screen.getByRole('button', { name: /recommend decks/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: { element: 'Fire', core_hittable: true, enemy_def: 20000, fight_duration: 180 },
    })
  })
})
