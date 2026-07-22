import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RecommendPanel } from './RecommendPanel'
import type { UserNikkeState } from '../types/userNikkeState'

vi.mock('../api/recommend', () => ({
  recommendDecks: vi.fn(),
}))
vi.mock('../api/recommendRaid', () => ({
  recommendRaidDecks: vi.fn(),
}))
vi.mock('../api/supportedUnits', () => ({
  getSupportedUnits: vi.fn(),
}))
vi.mock('../hooks/usePortraitManifest', () => ({
  usePortraitManifest: () => ({ portraitFor: () => null }),
}))

import { recommendDecks } from '../api/recommend'
import { recommendRaidDecks } from '../api/recommendRaid'
import { getSupportedUnits } from '../api/supportedUnits'

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 200,
  hp: 1_000_000,
  atk: 85_000,
  def_: 12_000,
  skill_levels: { skill1: 10, skill2: 7, burst: 4 },
  overload_options: [],
})

const fullRoster = ['a', 'b', 'c', 'd', 'e'].map(nikke)

beforeEach(() => {
  // Draft mode always fetches the supported-unit list (for the palette),
  // regardless of which mode a given test exercises; default to empty so
  // single/raid-mode tests don't need to know about it.
  vi.mocked(getSupportedUnits).mockResolvedValue([])
})

afterEach(() => {
  vi.mocked(recommendDecks).mockReset()
  vi.mocked(recommendRaidDecks).mockReset()
  vi.mocked(getSupportedUnits).mockReset()
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
      within_draft: null,
      baseline_total_damage: null,
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
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, pinned_slugs: [] },
        { deck: ['f', 'g', 'h', 'i', 'j'], total_damage: 80, burst_damage: 50, normal_attack_damage: 30, pinned_slugs: [] },
      ],
      combined_total_damage: 180,
      excluded_slugs: [],
      leftover_slugs: ['k'],
      within_draft: null,
      baseline_total_damage: null,
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

    resolveRequest({
      decks: [],
      combined_total_damage: 0,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
    })
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

describe('RecommendPanel draft mode', () => {
  const supportedUnits = ['a', 'b', 'c', 'd', 'e'].map((slug, i) => ({
    slug,
    name: slug.toUpperCase(),
    burstTier: ((i % 3) + 1) as 1 | 2 | 3,
    element: 'Iron' as const,
  }))

  it('sends the built draft, spanning multiple decks, to the raid endpoint', async () => {
    const user = userEvent.setup()
    const sixUnits = [
      ...supportedUnits,
      { slug: 'f', name: 'F', burstTier: 1 as const, element: 'Iron' as const },
    ]
    vi.mocked(getSupportedUnits).mockResolvedValue(sixUnits)
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [],
      combined_total_damage: 0,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
    })

    const sixRoster = [...fullRoster, nikke('f')]
    render(<RecommendPanel roster={sixRoster} />)
    await user.click(screen.getByLabelText(/draft-based/i))

    // Fill deck 1 (5 picks) then spill the 6th pick into deck 2, so the
    // submitted draft spans two decks — not just deck 1.
    for (const slug of ['a', 'b', 'c', 'd', 'e', 'f']) {
      await user.click(
        await screen.findByRole('button', { name: new RegExp(`^${slug.toUpperCase()} `, 'i') }),
      )
    }
    await user.click(screen.getByRole('button', { name: /optimize draft/i }))

    expect(recommendRaidDecks).toHaveBeenCalledWith({
      roster: sixRoster,
      boss: {
        element: null,
        core_hittable: false,
        enemy_def: 0,
        fight_duration: 180,
        part_destructible: false,
      },
      num_decks: 5,
      draft: [
        {
          units: [
            { slug: 'a', locked: false },
            { slug: 'b', locked: false },
            { slug: 'c', locked: false },
            { slug: 'd', locked: false },
            { slug: 'e', locked: false },
          ],
        },
        { units: [{ slug: 'f', locked: false }] },
      ],
    })
  })

  it('shows the backend error message on a failed draft submission (infeasible draft)', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(supportedUnits)
    const { RecommendApiError } = await import('../api/recommendApiError')
    vi.mocked(recommendRaidDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: 'draft references unusable slug: z' }),
    )

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByLabelText(/draft-based/i))
    await user.click(screen.getByRole('button', { name: /optimize draft/i }))

    expect(
      await screen.findByText('draft references unusable slug: z'),
    ).toBeInTheDocument()
  })

  it('disables shrinking "Number of decks" below the count of non-empty drafted decks', async () => {
    const user = userEvent.setup()
    const sixUnits = Array.from({ length: 6 }, (_, i) => ({
      slug: `u${i}`,
      name: `U${i}`,
      burstTier: ((i % 3) + 1) as 1 | 2 | 3,
      element: 'Iron' as const,
    }))
    vi.mocked(getSupportedUnits).mockResolvedValue(sixUnits)
    const sixRoster = Array.from({ length: 6 }, (_, i) => nikke(`u${i}`))

    render(<RecommendPanel roster={sixRoster} />)
    await user.click(screen.getByLabelText(/draft-based/i))

    // Fill deck 1 (5 seats) then spill a 6th unit into deck 2, so 2 decks
    // are non-empty.
    for (let i = 0; i < 6; i += 1) {
      await user.click(await screen.findByRole('button', { name: new RegExp(`^U${i} `, 'i') }))
    }

    const numDecksSelect = screen.getByLabelText('Number of decks')
    const optionOne = within(numDecksSelect).getByRole('option', { name: '1' })
    const optionTwo = within(numDecksSelect).getByRole('option', { name: '2' })
    expect(optionOne).toBeDisabled()
    expect(optionTwo).not.toBeDisabled()
  })
})

describe('RecommendPanel mode switch', () => {
  it('does not render the previous mode\'s result after switching modes without resubmitting', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, pinned_slugs: [] },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
    })

    render(<RecommendPanel roster={fullRoster} />)
    await user.click(screen.getByLabelText(/raid allocation/i))
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))
    // RaidResults-specific text, distinct from DraftEditor's own "Deck N" column headers.
    expect(await screen.findByText(/Field all 1 of these decks together/)).toBeInTheDocument()

    await user.click(screen.getByLabelText(/draft-based/i))
    expect(screen.queryByText(/Field all/)).not.toBeInTheDocument()
    expect(screen.queryByText('Combined total:', { exact: false })).not.toBeInTheDocument()
  })
})
