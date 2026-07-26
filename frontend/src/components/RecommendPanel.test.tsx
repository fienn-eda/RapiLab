import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RecommendPanel } from './RecommendPanel'
import { DRAG_SLUG_TYPE } from './UnitPalette'

/** Seats `slug` in deck `deckNumber` (1-based) the way the UI does: by drop.
 * jsdom implements no drag, so hand the handler the slug a real drag would
 * have carried. */
const dropOnDeck = (deckNumber: number, slug: string) => {
  const deck = screen.getByRole('heading', { name: new RegExp(`덱 ${deckNumber}`) })
  fireEvent.drop(deck.closest('div')!, {
    dataTransfer: {
      types: [DRAG_SLUG_TYPE],
      getData: (type: string) => (type === DRAG_SLUG_TYPE ? slug : ''),
    },
  })
}
import { hashRecommendInputs } from '../lib/inputHash'
import { MIN_DECK_ROSTER_SIZE } from '../types/recommend'
import type { UserNikkeState } from '../types/userNikkeState'
import type { StoredInputs, StoredResult } from '../types/profile'
import type { SupportedUnit } from '../types/supportedUnit'

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

// Every test exercises roster + boss/mode form state, not the persistence
// wiring — inert no-op defaults for the new profile-store props keep the
// pre-existing tests focused on what they actually check.
const noPersistence = {
  activeOpenId: null,
  getCached: () => null,
  onResult: () => {},
  restoreInputs: null,
  restoreResult: null,
}

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
    render(<RecommendPanel roster={fullRoster.slice(0, 2)} {...noPersistence} />)
    expect(
      screen.getByText('덱을 추천하려면 준비된 니케가 최소 5기 필요해요.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /덱 추천/i })).toBeDisabled()
  })

  // The boss profile used to sit at the very END of the form, past the whole
  // 70-chip palette - 2040px below the button that acts on it, so the input
  // that changes the answer most (Element) was the one nobody scrolled to.
  it('puts the boss profile beside the mode choice, with no palette between them', () => {
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    const boss = screen.getByRole('group', { name: /보스 설정/i })
    const mode = screen.getByRole('group', { name: /^모드$/i })
    const submit = screen.getByRole('button', { name: /덱 추천/i })
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })

    // Same row: one wrapper holds the boss fields and the mode+submit block.
    const setup = boss.parentElement!
    expect(setup).toBe(mode.parentElement)
    expect(setup.contains(submit)).toBe(true)
    expect(setup.contains(palette)).toBe(false)

    // ...and that row comes before the palette in the document.
    expect(setup.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })

  it('offers Cancel only while a run is in flight, and aborts it', async () => {
    // A run takes one to two minutes. Started by mistake, it used to be
    // unstoppable: no button, and a reload freed only the screen while the
    // server kept eight workers busy to completion.
    const user = userEvent.setup()
    let abortSignal: AbortSignal | undefined
    vi.mocked(recommendDecks).mockImplementation(
      (_req: unknown, signal?: AbortSignal) =>
        new Promise((_resolve, reject) => {
          abortSignal = signal
          signal?.addEventListener('abort', () => {
            const err = new Error('aborted')
            err.name = 'AbortError'
            reject(err)
          })
        }),
    )
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    expect(screen.queryByRole('button', { name: /^취소$/i })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /덱 추천/i }))

    const cancel = await screen.findByRole('button', { name: /^취소$/i })
    await user.click(cancel)

    expect(abortSignal?.aborted).toBe(true)
    // Back to the form, with no error: the user asked for this.
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /^취소$/i })).not.toBeInTheDocument(),
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /덱 추천/i })).toBeEnabled()
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

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('button', { name: /덱 추천/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        enemy_def: 0,
        fight_duration: 180,
        part_destructible: false,
      },
    }, expect.any(AbortSignal))
    expect(await screen.findByText('#1')).toBeInTheDocument()
    expect(screen.getByText('100 총딜')).toBeInTheDocument()
  })

  it('shows the backend error message on a failed submission', async () => {
    const user = userEvent.setup()
    const { RecommendApiError } = await import('../api/recommendApiError')
    vi.mocked(recommendDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: 'No feasible 5-unit deck.' }),
    )

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('button', { name: /덱 추천/i }))

    expect(await screen.findByText('No feasible 5-unit deck.')).toBeInTheDocument()
  })

  it('sends the entered element and enemy DEF instead of the defaults', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [] })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.selectOptions(screen.getByLabelText('속성'), 'Fire')
    await user.click(screen.getByLabelText('코어 피격 가능'))
    const enemyDef = screen.getByLabelText('적 방어력')
    await user.clear(enemyDef)
    await user.type(enemyDef, '20000')

    await user.click(screen.getByRole('button', { name: /덱 추천/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: 'Fire',
        core_hittable: true,
        enemy_def: 20000,
        fight_duration: 180,
        part_destructible: false,
      },
    }, expect.any(AbortSignal))
  })

  it('sends part_destructible: true when the part-destruction gimmick is toggled on', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [] })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/부위파괴 기믹/i))

    await user.click(screen.getByRole('button', { name: /덱 추천/i }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        enemy_def: 0,
        fight_duration: 180,
        part_destructible: true,
      },
    }, expect.any(AbortSignal))
  })
})

describe('RecommendPanel raid mode', () => {
  it('hides the number-of-decks selector in single-deck mode and shows it in raid mode', async () => {
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    expect(screen.queryByLabelText('덱 개수')).not.toBeInTheDocument()

    await user.click(screen.getByLabelText(/레이드 배분/i))
    expect(screen.getByLabelText('덱 개수')).toHaveValue('5')
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

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '3')
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))

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
    }, expect.any(AbortSignal))
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

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))

    expect(await screen.findByText('덱 1')).toBeInTheDocument()
    expect(screen.getByText('덱 2')).toBeInTheDocument()
    expect(screen.queryByText('#1')).not.toBeInTheDocument()
    expect(screen.getByText('180 딜')).toBeInTheDocument()
    expect(screen.getByText('벤치 (덱에 배정되지 않음): K')).toBeInTheDocument()
  })

  it('shows a persistent in-progress message and disables the button while a raid request is in flight', async () => {
    const user = userEvent.setup()
    let resolveRequest: (value: Awaited<ReturnType<typeof recommendRaidDecks>>) => void = () => {}
    vi.mocked(recommendRaidDecks).mockImplementation(
      () => new Promise((resolve) => { resolveRequest = resolve }),
    )

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/1~2분/)
    expect(screen.getByRole('button', { name: /배분 중/i })).toBeDisabled()

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

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))

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
    render(<RecommendPanel roster={sixRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/드래프트 기반/i))

    await screen.findByRole('button', { name: /a 사용/i }) // palette loaded

    // Fill deck 1 (5 seats) and put the 6th in deck 2, so the submitted draft
    // spans two decks — not just deck 1.
    for (const slug of ['a', 'b', 'c', 'd', 'e']) dropOnDeck(1, slug)
    dropOnDeck(2, 'f')
    await user.click(screen.getByRole('button', { name: /드래프트 최적화/i }))

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
    }, expect.any(AbortSignal))
  })

  it('drafts a multi-candidate unit under the slug the player owns', async () => {
    // Bready is one owned character the engine models in two modes. Which mode
    // she runs in is the engine's call, so the palette offers the OWNED slug and
    // the request carries it - the backend resolves the mode by completing the
    // deck each way (deck_allocation's `_seed_choices`).
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([
      ...supportedUnits,
      {
        slug: 'bready',
        name: 'Bready',
        burstTier: 3 as const,
        element: 'Water' as const,
        candidates: ['bready-lingering', 'bready-recommended'],
      },
    ])
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [],
      combined_total_damage: 0,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
    })

    const roster = [...fullRoster, nikke('bready')]
    render(<RecommendPanel roster={roster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/드래프트 기반/i))
    await screen.findByRole('button', { name: /bready 사용/i }) // draft palette has her

    dropOnDeck(1, 'bready')
    await user.click(screen.getByRole('button', { name: /드래프트 최적화/i }))

    expect(recommendRaidDecks).toHaveBeenCalledWith(
      expect.objectContaining({
        draft: [{ units: [{ slug: 'bready', locked: false }] }],
      }),
      expect.any(AbortSignal),
    )
  })

  it('shows the backend error message on a failed draft submission (infeasible draft)', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(supportedUnits)
    const { RecommendApiError } = await import('../api/recommendApiError')
    vi.mocked(recommendRaidDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: 'draft references unusable slug: z' }),
    )

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/드래프트 기반/i))
    await user.click(screen.getByRole('button', { name: /드래프트 최적화/i }))

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

    render(<RecommendPanel roster={sixRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/드래프트 기반/i))

    await screen.findByRole('button', { name: /u0 사용/i }) // palette loaded

    // Fill deck 1 (5 seats) and put the 6th in deck 2, so 2 decks are
    // non-empty.
    for (let i = 0; i < 5; i += 1) dropOnDeck(1, `u${i}`)
    dropOnDeck(2, 'u5')

    const numDecksSelect = screen.getByLabelText('덱 개수')
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

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    // RaidResults-specific text, distinct from DraftEditor's own "Deck N" column headers.
    expect(await screen.findByText(/이 1개 덱을 모두 함께 편성하세요/)).toBeInTheDocument()

    await user.click(screen.getByLabelText(/드래프트 기반/i))
    expect(screen.queryByText(/모두 함께 편성/)).not.toBeInTheDocument()
    expect(screen.queryByText('총합:', { exact: false })).not.toBeInTheDocument()
  })
})

describe('RecommendPanel persistence', () => {
  const defaultBoss = {
    element: null,
    core_hittable: false,
    enemy_def: 0,
    fight_duration: 180,
    part_destructible: false,
  }

  it('restores a persisted raid result and its inputs on mount, with no network call', async () => {
    const restoreInputs: StoredInputs = {
      mode: 'raid',
      numDecks: 3,
      boss: defaultBoss,
      draft: null,
    }
    const restoreResult: StoredResult = {
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          pinned_slugs: [],
        },
      ],
      combinedTotalDamage: 180,
      excludedSlugs: [],
      leftoverSlugs: ['k'],
      withinDraft: null,
      baselineTotalDamage: null,
    }

    render(
      <RecommendPanel
        roster={fullRoster}
        activeOpenId="A"
        getCached={() => null}
        onResult={() => {}}
        restoreInputs={restoreInputs}
        restoreResult={restoreResult}
      />,
    )

    expect(await screen.findByText('덱 1')).toBeInTheDocument()
    expect(screen.getByText('180 딜')).toBeInTheDocument()
    expect(screen.getByText('벤치 (덱에 배정되지 않음): K')).toBeInTheDocument()
    expect(screen.getByLabelText(/레이드 배분/i)).toBeChecked()
    expect(screen.getByLabelText('덱 개수')).toHaveValue('3')
    expect(recommendRaidDecks).not.toHaveBeenCalled()
  })

  it('calls onResult with the submitted inputs\' hash on a successful raid submit', async () => {
    const user = userEvent.setup()
    const onResult = vi.fn()
    const response = {
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          pinned_slugs: [],
        },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
    }
    vi.mocked(recommendRaidDecks).mockResolvedValue(response)

    render(
      <RecommendPanel
        roster={fullRoster}
        activeOpenId="A"
        getCached={() => null}
        onResult={onResult}
        restoreInputs={null}
        restoreResult={null}
      />,
    )
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    await screen.findByText('덱 1')

    const expectedHash = hashRecommendInputs(fullRoster, defaultBoss, null, 5)
    expect(onResult).toHaveBeenCalledWith({
      hash: expectedHash,
      result: {
        decks: response.decks,
        combinedTotalDamage: response.combined_total_damage,
        excludedSlugs: response.excluded_slugs,
        leftoverSlugs: response.leftover_slugs,
        withinDraft: response.within_draft,
        baselineTotalDamage: response.baseline_total_damage,
      },
      inputs: {
        mode: 'raid',
        numDecks: 5,
        boss: defaultBoss,
        draft: null,
      },
    })
    // Exactly-once persistence per submit - a rerender must not re-save.
    expect(onResult).toHaveBeenCalledTimes(1)
  })

  it('renders a cache hit immediately, never calls the raid client, and never calls onResult', async () => {
    const user = userEvent.setup()
    const onResult = vi.fn()
    const expectedHash = hashRecommendInputs(fullRoster, defaultBoss, null, 5)
    const cached: StoredResult = {
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 999,
          burst_damage: 600,
          normal_attack_damage: 399,
          pinned_slugs: [],
        },
      ],
      combinedTotalDamage: 999,
      excludedSlugs: [],
      leftoverSlugs: [],
      withinDraft: null,
      baselineTotalDamage: null,
    }
    const getCached = vi.fn((hash: string) => (hash === expectedHash ? cached : null))

    render(
      <RecommendPanel
        roster={fullRoster}
        activeOpenId="A"
        getCached={getCached}
        onResult={onResult}
        restoreInputs={null}
        restoreResult={null}
      />,
    )
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))

    expect(await screen.findByText('999 딜')).toBeInTheDocument()
    expect(recommendRaidDecks).not.toHaveBeenCalled()
    // A cache hit is never persisted - onResult is reserved for submits that
    // actually reached the backend (see pendingSaveRef in RecommendPanel).
    expect(onResult).not.toHaveBeenCalled()
  })

  it('clears a stale success result when a resubmit after success genuinely fails', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendRaidDecks).mockResolvedValueOnce({
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          pinned_slugs: [],
        },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/레이드 배분/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    expect(await screen.findByText('100 딜')).toBeInTheDocument()

    // Change an input (num_decks) so the resubmit is a genuinely different
    // request - noPersistence's getCached always returns null anyway, so
    // this is a cache miss regardless - then make the backend call reject.
    const { RecommendApiError } = await import('../api/recommendApiError')
    vi.mocked(recommendRaidDecks).mockRejectedValueOnce(
      new RecommendApiError(422, { detail: 'No feasible deck from the usable roster.' }),
    )
    await user.selectOptions(screen.getByLabelText('덱 개수'), '3')
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))

    expect(
      await screen.findByText('No feasible deck from the usable roster.'),
    ).toBeInTheDocument()
    // The prior success must not linger under (or be mistaken for) the new
    // failure - both the stale damage total and the deck-grouping heading
    // it rendered under must be gone.
    expect(screen.queryByText('100 딜')).not.toBeInTheDocument()
    expect(screen.queryByText('덱 1')).not.toBeInTheDocument()
  })
})

describe('RecommendPanel unit-pool exclusion', () => {
  // getSupportedUnits resolves the ALREADY-MAPPED camelCase shape
  // (SupportedUnit, `burstTier`) — the hook uses it verbatim, no re-mapping.
  const supported: SupportedUnit[] = [
    { slug: 'a', name: 'A', burstTier: 1, element: 'Iron' },
    { slug: 'b', name: 'B', burstTier: 2, element: 'Fire' },
    { slug: 'c', name: 'C', burstTier: 3, element: 'Water' },
    { slug: 'd', name: 'D', burstTier: 3, element: 'Wind' },
    { slug: 'e', name: 'E', burstTier: 3, element: 'Electric' },
    { slug: 'f', name: 'F', burstTier: 2, element: 'Iron' },
  ]
  // Six units so excluding one still leaves >= MIN_DECK_ROSTER_SIZE (5) and the
  // request can actually fire. `fullRoster` (top of file) is exactly 5.
  const poolRoster = ['a', 'b', 'c', 'd', 'e', 'f'].map(nikke)

  const raidResponse = {
    decks: [], combined_total_damage: 0, excluded_slugs: [],
    leftover_slugs: [], within_draft: null, baseline_total_damage: null,
  }

  const renderMode = async (roster: UserNikkeState[], radio: RegExp) => {
    vi.mocked(getSupportedUnits).mockResolvedValue(supported)
    vi.mocked(recommendRaidDecks).mockResolvedValue(raidResponse)
    const user = userEvent.setup()
    render(<RecommendPanel roster={roster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: radio }))
    await screen.findByRole('button', { name: /a 사용/i }) // palette loaded
    return user
  }

  it('drops an unchecked unit from the raid request roster', async () => {
    const user = await renderMode(poolRoster, /레이드 배분/i)
    await user.click(screen.getByRole('button', { name: /a 사용/i }))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
    const sent = vi.mocked(recommendRaidDecks).mock.calls[0][0]
    expect(sent.roster.map((n) => n.character_slug)).not.toContain('a')
    expect(sent.roster.map((n) => n.character_slug)).toContain('b')
  })

  it('disables submit when exclusions drop the roster below the minimum', async () => {
    // fullRoster is exactly MIN_DECK_ROSTER_SIZE (5); excluding one under-fills.
    expect(fullRoster.length).toBe(MIN_DECK_ROSTER_SIZE)
    const user = await renderMode(fullRoster, /레이드 배분/i)
    await user.click(screen.getByRole('button', { name: /a 사용/i }))
    expect(screen.getByRole('button', { name: /레이드 덱 배분/i })).toBeDisabled()
  })

  it('unplaces a drafted unit when it is excluded (draft mode)', async () => {
    // poolRoster/supported/raidResponse are defined in this describe's scope.
    const user = await renderMode(poolRoster, /드래프트 기반/i)

    // Seat unit "a" by dropping it on Deck 1, then exclude it.
    dropOnDeck(1, 'a')
    // A slot renders a face, not a name — its controls are what say who is in it.
    expect(screen.getByRole('button', { name: '덱 1에서 A 제거' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /a 사용/i }))

    await user.click(screen.getByRole('button', { name: /드래프트 최적화/i }))
    await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
    const sent = vi.mocked(recommendRaidDecks).mock.calls[0][0]
    const draftedSlugs = (sent.draft ?? []).flatMap((d) => d.units.map((u) => u.slug))
    expect(draftedSlugs).not.toContain('a')
    expect(sent.roster.map((n) => n.character_slug)).not.toContain('a')
  })

  it('resets exclusions when the active profile changes', async () => {
    vi.mocked(getSupportedUnits).mockResolvedValue(supported)
    const user = userEvent.setup()
    const { rerender } = render(
      <RecommendPanel roster={poolRoster} {...noPersistence} activeOpenId="p1" />,
    )
    await user.click(screen.getByRole('radio', { name: /레이드 배분/i }))
    await screen.findByRole('button', { name: /a 사용/i })
    await user.click(screen.getByRole('button', { name: /a 사용/i }))
    expect(screen.getByRole('button', { name: /a 사용/i })).toHaveAttribute('aria-pressed', 'false')
    rerender(<RecommendPanel roster={poolRoster} {...noPersistence} activeOpenId="p2" />)
    expect(screen.getByRole('button', { name: /a 사용/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('excluding a unit changes the cache hash', async () => {
    vi.mocked(getSupportedUnits).mockResolvedValue(supported)
    vi.mocked(recommendRaidDecks).mockResolvedValue(raidResponse)
    const getCached = vi.fn().mockReturnValue(null)
    const user = userEvent.setup()
    render(<RecommendPanel roster={poolRoster} {...noPersistence} getCached={getCached} />)
    await user.click(screen.getByRole('radio', { name: /레이드 배분/i }))
    await screen.findByRole('button', { name: /a 사용/i })
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    await waitFor(() => expect(getCached).toHaveBeenCalledTimes(1))
    const hashFull = getCached.mock.calls[0][0]
    await screen.findByRole('button', { name: /레이드 덱 배분/i }) // loading cleared
    await user.click(screen.getByRole('button', { name: /a 사용/i }))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    await waitFor(() => expect(getCached).toHaveBeenCalledTimes(2))
    expect(getCached.mock.calls[1][0]).not.toEqual(hashFull)
  })
})
