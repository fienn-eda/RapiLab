import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RecommendPanel } from './RecommendPanel'
import type { UserNikkeState } from '../types/userNikkeState'

vi.mock('../api/recommend', () => ({
  recommendDecks: vi.fn(),
}))
vi.mock('../api/recommendRaid', () => ({
  recommendRaidDecks: vi.fn(),
}))

import { recommendDecks } from '../api/recommend'
import { recommendRaidDecks } from '../api/recommendRaid'

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 200,
  core_level: 7,
  hp: 1_000_000,
  atk: 85_000,
  def_: 12_000,
  skill_levels: { skill1: 10, skill2: 7, burst: 4 },
  overload_options: [],
})

const fullRoster = ['a', 'b', 'c', 'd', 'e'].map(nikke)

afterEach(() => {
  vi.mocked(recommendDecks).mockReset()
  vi.mocked(recommendRaidDecks).mockReset()
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
      excluded_slugs: [],
    })

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByRole('button', { name: /recommend decks/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        enemy_def: 0,
        fight_duration: 180,
        part_destructible: false,
      },
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
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [] })

    render(<RecommendPanel roster={fullRoster} />)
    await user.selectOptions(screen.getByLabelText('Element'), 'Fire')
    await user.click(screen.getByLabelText('Core is hittable'))
    const enemyDef = screen.getByLabelText('Enemy DEF')
    await user.clear(enemyDef)
    await user.type(enemyDef, '20000')

    await user.click(screen.getByRole('button', { name: /recommend decks/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: 'Fire',
        core_hittable: true,
        enemy_def: 20000,
        fight_duration: 180,
        part_destructible: false,
      },
    })
  })

  it('sends part_destructible: true when the part-destruction gimmick is toggled on', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [] })

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByLabelText(/part-destruction gimmick/i))

    await user.click(screen.getByRole('button', { name: /recommend decks/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        enemy_def: 0,
        fight_duration: 180,
        part_destructible: true,
      },
    })
  })
})

describe('RecommendPanel raid mode', () => {
  it('hides the number-of-decks selector in single-deck mode and shows it in raid mode', async () => {
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} />)

    expect(screen.queryByLabelText('Number of decks')).not.toBeInTheDocument()

    await user.click(screen.getByLabelText(/raid allocation/i))
    expect(screen.getByLabelText('Number of decks')).toHaveValue('5')
  })

  it('submits the roster, boss profile, and selected num_decks to the raid endpoint', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [],
      combined_total_damage: 0,
      excluded_slugs: [],
      leftover_slugs: [],
    })

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByLabelText(/raid allocation/i))
    await user.selectOptions(screen.getByLabelText('Number of decks'), '3')
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))

    expect(recommendRaidDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        enemy_def: 0,
        fight_duration: 180,
        part_destructible: false,
      },
      num_decks: 3,
    })
    expect(recommendDecks).not.toHaveBeenCalled()
  })

  it('renders the allocated decks, combined total, and leftover slugs — not as a ranked list', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40 },
        { deck: ['f', 'g', 'h', 'i', 'j'], total_damage: 80, burst_damage: 50, normal_attack_damage: 30 },
      ],
      combined_total_damage: 180,
      excluded_slugs: [],
      leftover_slugs: ['k'],
    })

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByLabelText(/raid allocation/i))
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))

    expect(await screen.findByText('Deck 1')).toBeInTheDocument()
    expect(screen.getByText('Deck 2')).toBeInTheDocument()
    expect(screen.queryByText('#1')).not.toBeInTheDocument()
    expect(screen.getByText('180 dmg')).toBeInTheDocument()
    expect(screen.getByText('Bench (not allocated to a deck): k')).toBeInTheDocument()
  })

  it('shows a persistent in-progress message and disables the button while a raid request is in flight', async () => {
    const user = userEvent.setup()
    let resolveRequest: (value: Awaited<ReturnType<typeof recommendRaidDecks>>) => void = () => {}
    vi.mocked(recommendRaidDecks).mockImplementation(
      () => new Promise((resolve) => { resolveRequest = resolve }),
    )

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByLabelText(/raid allocation/i))
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/1–2 minutes/)
    expect(screen.getByRole('button', { name: /allocating/i })).toBeDisabled()

    resolveRequest({ decks: [], combined_total_damage: 0, excluded_slugs: [], leftover_slugs: [] })
    await waitFor(() =>
      expect(screen.queryByRole('status')).not.toBeInTheDocument(),
    )
  })

  it('shows the backend error message on a failed raid submission', async () => {
    const user = userEvent.setup()
    const { RecommendApiError } = await import('../api/recommendApiError')
    vi.mocked(recommendRaidDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: 'No feasible deck from the usable roster.' }),
    )

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByLabelText(/raid allocation/i))
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))

    expect(await screen.findByText('No feasible deck from the usable roster.')).toBeInTheDocument()
  })
})
