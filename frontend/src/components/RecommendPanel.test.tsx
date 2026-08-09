import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { renderSettled } from '../test/renderSettled'
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
import type { SavedRun, StoredInputs, StoredResult } from '../types/profile'
import type { SupportedUnit } from '../types/supportedUnit'

vi.mock('../api/recommend', () => ({
  recommendDecks: vi.fn(),
}))
vi.mock('../api/recommendRaid', () => ({
  recommendRaidDecks: vi.fn(),
}))
vi.mock('../api/evaluateDecks', () => ({
  evaluateDecks: vi.fn(),
}))
vi.mock('../api/supportedUnits', () => ({
  getSupportedUnits: vi.fn(),
}))
vi.mock('../hooks/usePortraitManifest', () => ({
  usePortraitManifest: () => ({ portraitFor: () => null }),
}))

import { recommendDecks } from '../api/recommend'
import { recommendRaidDecks } from '../api/recommendRaid'
import { evaluateDecks } from '../api/evaluateDecks'
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

// Shared by the evaluate-mode tests below - a five-unit palette is all any of
// them needs, and a fresh array per call keeps tests from sharing references.
const makeEvaluateSupportedUnits = () =>
  ['a', 'b', 'c', 'd', 'e'].map((slug, i) => ({
    slug,
    name: slug.toUpperCase(),
    burstTier: ((i % 3) + 1) as 1 | 2 | 3,
    element: 'Iron' as const,
  }))

// Every test exercises roster + boss/mode form state, not the persistence
// wiring — inert no-op defaults for the new profile-store props keep the
// pre-existing tests focused on what they actually check.
const noPersistence = {
  activeKey: null,
  getCached: () => null,
  onResult: () => {},
  restoreInputs: null,
  restoreResult: null,
  engineVersion: null,
  savedRuns: [],
  onSaveRun: () => true,
  onRenameRun: () => {},
  onDeleteRun: () => {},
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
  vi.mocked(evaluateDecks).mockReset()
  vi.mocked(getSupportedUnits).mockReset()
})

describe('RecommendPanel', () => {
  it('opens with the solo raid boss DEF prefilled', async () => {
    await renderSettled(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    expect(screen.getByLabelText(/적 방어력/)).toHaveValue(31784)
  })

  it('disables submit and shows a guard message when the roster has under 5 Nikkes', async () => {
    await renderSettled(<RecommendPanel roster={fullRoster.slice(0, 2)} {...noPersistence} />)
    expect(
      screen.getByText('덱을 추천하려면 준비된 니케가 최소 5기 필요해요.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
  })

  // The boss profile used to sit at the very END of the form, past the whole
  // 70-chip palette - 2040px below the button that acts on it, so the input
  // that changes the answer most (Element) was the one nobody scrolled to.
  it('puts the boss profile beside the mode choice, with no palette between them', async () => {
    await renderSettled(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    const boss = screen.getByRole('group', { name: /보스 설정/i })
    const mode = screen.getByRole('group', { name: /^모드$/i })
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })

    // Same row: one wrapper holds the boss fields and the mode block.
    const setup = boss.parentElement!
    expect(setup).toBe(mode.parentElement)
    expect(setup.contains(palette)).toBe(false)

    // ...and that row comes before the palette in the document.
    expect(setup.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })

  // 결과를 읽으려면 70여 개 칩의 팔레트를 스크롤해 지나야 해서는 안 된다.
  it('renders the results above the unit palette', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          skill_damage: 0, hold_burst_slugs: [],
        },
      ],
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    const results = (await screen.findByText('#1')).closest('ol')!
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })

    expect(results.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })

  it('결과 위에 그 결과가 채점된 보스를 적는다', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          skill_damage: 0, hold_burst_slugs: [],
        },
      ],
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: '작열' }))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(await screen.findByText(/약점 작열/)).toBeInTheDocument()
  })

  // 결과가 나온 뒤 폼을 만지면 숫자는 옛 보스인데 설명만 새 보스가 되어,
  // 화면이 거짓말을 한다.
  it('결과가 나온 뒤 보스 폼을 바꿔도 요약은 그 결과의 보스에 남는다', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          skill_damage: 0, hold_burst_slugs: [],
        },
      ],
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: '작열' }))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await screen.findByText(/약점 작열/)

    await user.click(screen.getByRole('radio', { name: '수냉' }))

    expect(screen.getByText(/약점 작열/)).toBeInTheDocument()
  })

  // 팔레트 아래 sticky 바에 있던 실행 버튼을, 그것이 작용하는 설정 바로
  // 아래에 세운다.
  it('stands the run button between the setup row and the palette', async () => {
    await renderSettled(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    const boss = screen.getByRole('group', { name: /보스 설정/i })
    const setup = boss.parentElement!
    const submit = screen.getByRole('button', { name: /인카운터/ })
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })

    expect(setup.compareDocumentPosition(submit) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
    expect(submit.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
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
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    const cancel = await screen.findByRole('button', { name: /^취소$/i })
    await user.click(cancel)

    expect(abortSignal?.aborted).toBe(true)
    // Back to the form, with no error: the user asked for this.
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /^취소$/i })).not.toBeInTheDocument(),
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeEnabled()
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
          skill_damage: 0, hold_burst_slugs: [],
        },
      ],
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        pierce_hits_body_behind_core: false,
        enemy_def: 31784,
        fight_duration: 180,
        part_destructible: false,
        core_diameter_px: null,
        effective_range_band: null,
        elemental_interrupt_required: false,
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
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(await screen.findByText('No feasible 5-unit deck.')).toBeInTheDocument()
  })

  it('sends the entered element and enemy DEF instead of the defaults', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [], engine_version: 'test-engine-version' })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    // The picker speaks in the boss's weakness, not its own element - 수냉
    // (Water) weak means the boss's own element is Fire.
    await user.click(screen.getByLabelText('수냉'))
    // Exact, not a substring: the help button beside it is named after the
    // same setting, so a loose match finds both.
    await user.click(screen.getByLabelText('코어 피격 가능'))
    const enemyDef = screen.getByLabelText('적 방어력')
    await user.clear(enemyDef)
    await user.type(enemyDef, '20000')

    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: 'Fire',
        core_hittable: true,
        pierce_hits_body_behind_core: false,
        enemy_def: 20000,
        fight_duration: 180,
        part_destructible: false,
        core_diameter_px: null,
        effective_range_band: null,
        elemental_interrupt_required: false,
      },
    }, expect.any(AbortSignal))
  })

  it('sends part_destructible: true when the part-destruction gimmick is toggled on', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [], engine_version: 'test-engine-version' })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText('부위파괴 기믹'))

    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        pierce_hits_body_behind_core: false,
        enemy_def: 31784,
        fight_duration: 180,
        part_destructible: true,
        core_diameter_px: null,
        effective_range_band: null,
        elemental_interrupt_required: false,
      },
    }, expect.any(AbortSignal))
  })

  it('sends the effective range band the user picked', async () => {
    // The band reached the engine before it reached any endpoint, so what this
    // pins is the wiring rather than the arithmetic: a boss fought at mid range
    // pays the AR and MG in the deck, and the recommender only knows that if
    // the request carries it.
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [], engine_version: 'test-engine-version' })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.selectOptions(screen.getByLabelText('보스 적정거리'), 'mid')

    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(recommendDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        pierce_hits_body_behind_core: false,
        enemy_def: 31784,
        fight_duration: 180,
        part_destructible: false,
        core_diameter_px: null,
        effective_range_band: 'mid',
        elemental_interrupt_required: false,
      },
    }, expect.any(AbortSignal))
  })
})

describe('RecommendPanel raid mode', () => {
  it('hides the number-of-decks selector in single-deck mode and shows it in raid mode', async () => {
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    expect(screen.queryByLabelText('덱 개수')).not.toBeInTheDocument()

    await user.click(screen.getByLabelText(/전부 최적화/i))
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
      swap_converged: true,
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '3')
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(recommendRaidDecks).toHaveBeenCalledWith({
      roster: fullRoster,
      boss: {
        element: null,
        core_hittable: false,
        pierce_hits_body_behind_core: false,
        enemy_def: 31784,
        fight_duration: 180,
        part_destructible: false,
        core_diameter_px: null,
        effective_range_band: null,
        elemental_interrupt_required: false,
      },
      num_decks: 3,
    }, expect.any(AbortSignal))
    expect(recommendDecks).not.toHaveBeenCalled()
  })

  it('renders the allocated decks, combined total, and leftover slugs — not as a ranked list', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [], pinned_slugs: [] },
        { deck: ['f', 'g', 'h', 'i', 'j'], total_damage: 80, burst_damage: 50, normal_attack_damage: 30, skill_damage: 0, hold_burst_slugs: [], pinned_slugs: [] },
      ],
      combined_total_damage: 180,
      excluded_slugs: [],
      leftover_slugs: ['k'],
      within_draft: null,
      baseline_total_damage: null,
      swap_converged: true,
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

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
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(await screen.findByRole('status')).toHaveTextContent(/2~5분/)
    expect(screen.getByRole('button', { name: /전부 최적화 중/i })).toBeDisabled()

    resolveRequest({
      decks: [],
      combined_total_damage: 0,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
      swap_converged: true,
      engine_version: 'test-engine-version',
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
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

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
      swap_converged: true,
      engine_version: 'test-engine-version',
    })

    const sixRoster = [...fullRoster, nikke('f')]
    render(<RecommendPanel roster={sixRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/빈자리만 최적화/i))

    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded

    // Fill deck 1 (5 seats) and put the 6th in deck 2, so the submitted draft
    // spans two decks — not just deck 1.
    for (const slug of ['a', 'b', 'c', 'd', 'e']) dropOnDeck(1, slug)
    dropOnDeck(2, 'f')
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(recommendRaidDecks).toHaveBeenCalledWith({
      roster: sixRoster,
      boss: {
        element: null,
        core_hittable: false,
        pierce_hits_body_behind_core: false,
        enemy_def: 31784,
        fight_duration: 180,
        part_destructible: false,
        core_diameter_px: null,
        effective_range_band: null,
        elemental_interrupt_required: false,
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
      swap_converged: true,
      engine_version: 'test-engine-version',
    })

    const roster = [...fullRoster, nikke('bready')]
    render(<RecommendPanel roster={roster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/빈자리만 최적화/i))
    await screen.findByRole('button', { name: /bready 배치/i }) // draft palette has her

    dropOnDeck(1, 'bready')
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

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
    await user.click(screen.getByLabelText(/빈자리만 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

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
    await user.click(screen.getByLabelText(/빈자리만 최적화/i))

    await screen.findByRole('button', { name: /u0 배치/i }) // palette loaded

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

describe('RecommendPanel evaluate mode', () => {
  const supportedUnits = makeEvaluateSupportedUnits()

  it('평가 모드는 25칸을 다 채우기 전에는 제출을 막는다', async () => {
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
  })

  it('평가 모드에서는 잠금 토글이 없다', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(supportedUnits)

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded

    // Seat a unit so the draft editor actually draws a slot — with nothing
    // placed, "no lock button" would be true regardless of showLocks. The
    // palette's own "사용" toggle also carries aria-pressed, so scope on the
    // lock button's distinct label ("고정") rather than the pressed role alone.
    dropOnDeck(1, 'a')
    expect(screen.getByRole('button', { name: '덱 1에서 A 제거' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /고정/ })).not.toBeInTheDocument()
  })

  it('선택한 덱 수만큼 5명씩 다 채워야 제출 버튼이 켜진다', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(supportedUnits)

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '1')
    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded

    for (const slug of ['a', 'b', 'c', 'd']) dropOnDeck(1, slug)
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()

    dropOnDeck(1, 'e')
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeEnabled()
  })

  it('로스터가 최소 인원 밑으로 줄어도 평가는 제출된다 - 평가는 편성된 유닛만 채점하지 로스터 크기를 보지 않는다', async () => {
    // canSubmit already exempts evaluate mode from rosterTooSmall; this test
    // is for handleSubmit's early return, which used to still bail on it -
    // reachable by drafting five units, then deleting units from the roster
    // tab (here: the roster prop shrinking on a rerender, same effect).
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(supportedUnits)
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    const { rerender } = render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '1')
    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded
    for (const slug of ['a', 'b', 'c', 'd', 'e']) dropOnDeck(1, slug)

    // The roster tab drops below MIN_DECK_ROSTER_SIZE - the already-drafted
    // deck (internal state) is unaffected.
    rerender(<RecommendPanel roster={fullRoster.slice(0, 3)} {...noPersistence} />)
    expect(screen.queryByText(/니케가 최소 5기 필요해요/)).not.toBeInTheDocument()

    const submitButton = screen.getByRole('button', { name: /인카운터/ })
    expect(submitButton).toBeEnabled()
    await user.click(submitButton)

    expect(evaluateDecks).toHaveBeenCalled()
    expect(await screen.findByText('총합:', { exact: false })).toBeInTheDocument()
  })

  it('선택한 덱만큼 evaluate-decks에 제출하고 결과를 렌더한다', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(supportedUnits)
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '1')
    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded
    for (const slug of ['a', 'b', 'c', 'd', 'e']) dropOnDeck(1, slug)

    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(evaluateDecks).toHaveBeenCalledWith(
      {
        roster: fullRoster,
        decks: [
          {
            units: ['a', 'b', 'c', 'd', 'e'],
            boss: {
              element: null,
              core_hittable: false,
              pierce_hits_body_behind_core: false,
              enemy_def: 31784,
              fight_duration: 180,
              part_destructible: false,
              core_diameter_px: null,
              effective_range_band: null,
              elemental_interrupt_required: false,
            },
          },
        ],
      },
      expect.any(AbortSignal),
    )
    expect(recommendRaidDecks).not.toHaveBeenCalled()
    expect(await screen.findByText('총합:', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('100 딜', { exact: false })).toBeInTheDocument()
  })

  it('결과가 나온 뒤 보스 속성을 바꿔도 카드 표시는 제출 당시 속성 그대로다', async () => {
    // The card's damage numbers were computed against the SUBMITTED boss, so
    // its element label must stay pinned to that submission too - reading the
    // live form field instead would relabel a finished result out from under
    // its own numbers.
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(makeEvaluateSupportedUnits())
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '1')
    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded
    for (const slug of ['a', 'b', 'c', 'd', 'e']) dropOnDeck(1, slug)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(await screen.findByText('1번 덱 · 무속성')).toBeInTheDocument()

    await user.click(screen.getByLabelText('수냉'))

    expect(screen.getByText('1번 덱 · 무속성')).toBeInTheDocument()
    expect(screen.queryByText('1번 덱 · 작열')).not.toBeInTheDocument()
  })
})

describe('RecommendPanel mode switch', () => {
  it('does not render the previous mode\'s result after switching modes without resubmitting', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [], pinned_slugs: [] },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
      swap_converged: true,
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    // RaidResults-specific text, distinct from DraftEditor's own "Deck N" column headers.
    expect(await screen.findByText(/이 1개 덱을 모두 함께 편성하세요/)).toBeInTheDocument()

    await user.click(screen.getByLabelText(/빈자리만 최적화/i))
    expect(screen.queryByText(/모두 함께 편성/)).not.toBeInTheDocument()
    expect(screen.queryByText('총합:', { exact: false })).not.toBeInTheDocument()
  })

  it('다른 모드로 바꾸면 평가 결과가 새어 보이지 않는다', async () => {
    // 평가 성공 상태를 만든 뒤 '단일 덱'으로 전환하면 결과가 사라져야 한다 -
    // 기존 raidResultMode 가드가 raid/draft 사이에서 지키는 것과 같은 계약.
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(makeEvaluateSupportedUnits())
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '1')
    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded
    for (const slug of ['a', 'b', 'c', 'd', 'e']) dropOnDeck(1, slug)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    expect(await screen.findByText('총합:', { exact: false })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /단일 덱/ }))
    expect(screen.queryByText('총합:', { exact: false })).not.toBeInTheDocument()
  })

  it('평가 결과가 나온 뒤 딴 데 갔다 편성을 바꾸고 돌아오면 옛 결과가 남아 있지 않다', async () => {
    // draftValue는 드래프트/평가 모드가 공유한다 - evaluation.cancel()은 이미
    // 끝난 요청을 다시 abort할 수 없는 no-op이라, 평가 -> 다른 모드 -> 편성
    // 수정 -> 평가로 돌아왔을 때 옛 결과가 바뀐 편성 위에 그대로 남을 수
    // 있었다. reset()이 그 성공 상태 자체를 지워야 한다.
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(makeEvaluateSupportedUnits())
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [] },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '1')
    await screen.findByRole('button', { name: /a 배치/i }) // palette loaded
    for (const slug of ['a', 'b', 'c', 'd', 'e']) dropOnDeck(1, slug)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    expect(await screen.findByText('총합:', { exact: false })).toBeInTheDocument()

    // 딴 모드로 갔다가, 공유된 draftValue의 편성을 바꾼다.
    await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/ }))
    await user.click(screen.getByRole('button', { name: '덱 1에서 E 제거' }))
    dropOnDeck(1, 'e') // rebuild a full deck so evaluate mode can submit again

    // 평가로 돌아온다 - 새로 제출하지 않았으므로 옛 성공 결과가 남아 있으면 안 된다.
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    expect(screen.queryByText('총합:', { exact: false })).not.toBeInTheDocument()
  })

  it('싱글 결과의 파훼 불가 배지는 다른 모드에서 나중에 제출해도 흔들리지 않는다', async () => {
    // Invariant: each mode's badge is judged against the boss ITS OWN result
    // was submitted with, not whatever boss was most recently submitted in
    // any mode. Single's result (single.status) and raid/draft's
    // (displayResult) both survive a mode switch, so submitting elsewhere
    // with the constraint off must not strip the badge off a single-mode
    // result still on screen, whose own decks/damage numbers never changed.
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue(
      ['a', 'b', 'c', 'd', 'e'].map((slug, i) => ({
        slug,
        name: slug.toUpperCase(),
        burstTier: ((i % 3) + 1) as 1 | 2 | 3,
        element: 'Iron' as const, // no Water unit anywhere in the roster
      })),
    )
    vi.mocked(recommendDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0, hold_burst_slugs: [] },
      ],
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks: [
        { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 200, burst_damage: 120, normal_attack_damage: 80, skill_damage: 0, hold_burst_slugs: [], pinned_slugs: [] },
      ],
      combined_total_damage: 200,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
      swap_converged: true,
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    // 탐색 모드에는 팔레트가 없다(미사용은 니케 풀 탭이 정한다) - 풀 개수 줄이
    // supported-units가 도착했다는 증거다.
    await screen.findByText(/탐색 풀에 포함됨/)

    // 단일 덱: 약점 수냉(보스는 작열), 속성저지 필수를 켜고 제출한다 - 로스터
    // 전원이 Iron이라 파훼할 수 없는 덱이 나온다.
    await user.click(screen.getByLabelText('수냉'))
    await user.click(screen.getByLabelText('속성저지 필수'))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    expect(await screen.findByText('속성저지 파훼 불가')).toBeInTheDocument()

    // 전부 최적화로 바꾸고, 이번엔 속성저지 필수를 끈 채로 거기서 제출한다.
    await user.click(screen.getByRole('radio', { name: /전부 최적화/ }))
    await user.click(screen.getByLabelText('속성저지 필수'))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    expect(await screen.findByText(/이 1개 덱을 모두 함께 편성하세요/)).toBeInTheDocument()

    // 단일 덱으로 돌아온다 - 재제출하지 않았으므로 옛 결과가 그대로 남아
    // 있고, 그 배지는 방금 다른 모드에서 제출한(속성저지 꺼진) 보스가 아니라
    // 그 결과가 실제로 제출됐던 보스 그대로여야 한다.
    await user.click(screen.getByRole('radio', { name: /단일 덱/ }))
    expect(screen.getByText('속성저지 파훼 불가')).toBeInTheDocument()
  })
})

describe('RecommendPanel persistence', () => {
  const defaultBoss = {
    element: null,
    core_hittable: false,
    pierce_hits_body_behind_core: false,
    enemy_def: 31784,
    fight_duration: 180,
    part_destructible: false,
    core_diameter_px: null,
    effective_range_band: null,
    elemental_interrupt_required: false,
  }

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
        skill_damage: 0, hold_burst_slugs: [],
        pinned_slugs: [],
      },
    ],
    combinedTotalDamage: 180,
    excludedSlugs: [],
    leftoverSlugs: ['k'],
    withinDraft: null,
    baselineTotalDamage: null,
  }

  it('restores a persisted raid result and its inputs on mount, with no network call', async () => {
    render(
      <RecommendPanel
        roster={fullRoster}
        {...noPersistence}
        activeKey="A"
        getCached={() => null}
        onResult={() => {}}
        restoreInputs={restoreInputs}
        restoreResult={restoreResult}
        engineVersion={null}
      />,
    )

    expect(await screen.findByText('덱 1')).toBeInTheDocument()
    expect(screen.getByText('180 딜')).toBeInTheDocument()
    expect(screen.getByText('벤치 (덱에 배정되지 않음): K')).toBeInTheDocument()
    expect(screen.getByLabelText(/전부 최적화/i)).toBeChecked()
    expect(screen.getByLabelText('덱 개수')).toHaveValue('3')
    expect(recommendRaidDecks).not.toHaveBeenCalled()
  })

  it('restores a result that only becomes restorable once the engine version arrives', async () => {
    // Whether a stored result is still valid can't be answered until the
    // backend says which engine produced the current numbers, and that answer
    // lands a beat AFTER mount (useEngineVersion fetches it). So restoreResult
    // is null on the first render and turns into a value on a later one.
    // Restoring only what was present at mount would drop it forever.
    const { rerender } = render(
      <RecommendPanel
        roster={fullRoster}
        {...noPersistence}
        activeKey="A"
        getCached={() => null}
        onResult={() => {}}
        restoreInputs={restoreInputs}
        restoreResult={null}
        engineVersion={null}
      />,
    )
    expect(screen.queryByText('덱 1')).not.toBeInTheDocument()

    rerender(
      <RecommendPanel
        roster={fullRoster}
        {...noPersistence}
        activeKey="A"
        getCached={() => null}
        onResult={() => {}}
        restoreInputs={restoreInputs}
        restoreResult={restoreResult}
        engineVersion="engine-1"
      />,
    )

    expect(await screen.findByText('덱 1')).toBeInTheDocument()
    expect(screen.getByText('180 딜')).toBeInTheDocument()
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
          skill_damage: 0, hold_burst_slugs: [],
          pinned_slugs: [],
        },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
      swap_converged: true,
      engine_version: 'test-engine-version',
    }
    vi.mocked(recommendRaidDecks).mockResolvedValue(response)

    render(
      <RecommendPanel
        roster={fullRoster}
        {...noPersistence}
        activeKey="A"
        getCached={() => null}
        onResult={onResult}
        restoreInputs={null}
        restoreResult={null}
        engineVersion={null}
      />,
    )
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await screen.findByText('덱 1')

    const expectedHash = hashRecommendInputs(fullRoster, defaultBoss, null, 5, null)
    expect(onResult).toHaveBeenCalledWith({
      hash: expectedHash,
      result: {
        decks: response.decks,
        combinedTotalDamage: response.combined_total_damage,
        excludedSlugs: response.excluded_slugs,
        leftoverSlugs: response.leftover_slugs,
        withinDraft: response.within_draft,
        baselineTotalDamage: response.baseline_total_damage,
        swapConverged: response.swap_converged,
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
    const expectedHash = hashRecommendInputs(fullRoster, defaultBoss, null, 5, null)
    const cached: StoredResult = {
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 999,
          burst_damage: 600,
          normal_attack_damage: 399,
          skill_damage: 0, hold_burst_slugs: [],
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
        {...noPersistence}
        activeKey="A"
        getCached={getCached}
        onResult={onResult}
        restoreInputs={null}
        restoreResult={null}
        engineVersion={null}
      />,
    )
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

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
          skill_damage: 0, hold_burst_slugs: [],
          pinned_slugs: [],
        },
      ],
      combined_total_damage: 100,
      excluded_slugs: [],
      leftover_slugs: [],
      within_draft: null,
      baseline_total_damage: null,
      swap_converged: true,
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    expect(await screen.findByText('100 딜')).toBeInTheDocument()

    // Change an input (num_decks) so the resubmit is a genuinely different
    // request - noPersistence's getCached always returns null anyway, so
    // this is a cache miss regardless - then make the backend call reject.
    const { RecommendApiError } = await import('../api/recommendApiError')
    vi.mocked(recommendRaidDecks).mockRejectedValueOnce(
      new RecommendApiError(422, { detail: 'No feasible deck from the usable roster.' }),
    )
    await user.selectOptions(screen.getByLabelText('덱 개수'), '3')
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

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
    swap_converged: true,
    engine_version: 'test-engine-version',
  }

  // 미사용 니케는 이제 니케 풀 탭이 정하고 이 패널은 받아 읽기만 한다.
  // 그래서 여기서는 칩을 누르는 대신 프로퍼티로 넣는다 - 컨트롤이 어디 있든
  // 「뺀 니케는 제출 로스터에도 편성에도 없다」는 이 패널의 약속이다.
  const renderExcluded = async (
    roster: UserNikkeState[],
    radio: RegExp,
    excludedSlugs: string[],
  ) => {
    vi.mocked(getSupportedUnits).mockResolvedValue(supported)
    vi.mocked(recommendRaidDecks).mockResolvedValue(raidResponse)
    const user = userEvent.setup()
    render(<RecommendPanel roster={roster} {...noPersistence} excludedSlugs={excludedSlugs} />)
    await user.click(screen.getByRole('radio', { name: radio }))
    await screen.findByText(/탐색 풀에 포함됨|덱 1/)
    return user
  }

  it('drops an unchecked unit from the raid request roster', async () => {
    const user = await renderExcluded(poolRoster, /전부 최적화/i, ['a'])
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
    const sent = vi.mocked(recommendRaidDecks).mock.calls[0][0]
    expect(sent.roster.map((n) => n.character_slug)).not.toContain('a')
    expect(sent.roster.map((n) => n.character_slug)).toContain('b')
  })

  it('disables submit when exclusions drop the roster below the minimum', async () => {
    // fullRoster is exactly MIN_DECK_ROSTER_SIZE (5); excluding one under-fills.
    expect(fullRoster.length).toBe(MIN_DECK_ROSTER_SIZE)
    await renderExcluded(fullRoster, /전부 최적화/i, ['a'])
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
  })

  it('unplaces a drafted unit when it is excluded (draft mode)', async () => {
    vi.mocked(getSupportedUnits).mockResolvedValue(supported)
    vi.mocked(recommendRaidDecks).mockResolvedValue(raidResponse)
    const user = userEvent.setup()
    const { rerender } = render(
      <RecommendPanel roster={poolRoster} {...noPersistence} excludedSlugs={[]} />,
    )
    await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/i }))
    await screen.findByRole('button', { name: /a 배치/i })

    // Seat unit "a" by dropping it on Deck 1, then bench her from the roster tab.
    dropOnDeck(1, 'a')
    // A slot renders a face, not a name — its controls are what say who is in it.
    expect(screen.getByRole('button', { name: '덱 1에서 A 제거' })).toBeInTheDocument()
    rerender(<RecommendPanel roster={poolRoster} {...noPersistence} excludedSlugs={['a']} />)
    expect(screen.queryByRole('button', { name: '덱 1에서 A 제거' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
    const sent = vi.mocked(recommendRaidDecks).mock.calls[0][0]
    const draftedSlugs = (sent.draft ?? []).flatMap((d) => d.units.map((u) => u.slug))
    expect(draftedSlugs).not.toContain('a')
    expect(sent.roster.map((n) => n.character_slug)).not.toContain('a')
  })

  it('excluding a unit changes the cache hash', async () => {
    vi.mocked(getSupportedUnits).mockResolvedValue(supported)
    vi.mocked(recommendRaidDecks).mockResolvedValue(raidResponse)
    const getCached = vi.fn().mockReturnValue(null)
    const user = userEvent.setup()
    const props = { ...noPersistence, getCached }
    const { rerender } = render(
      <RecommendPanel roster={poolRoster} {...props} excludedSlugs={[]} />,
    )
    await user.click(screen.getByRole('radio', { name: /전부 최적화/i }))
    await screen.findByText(/탐색 풀에 포함됨/)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await waitFor(() => expect(getCached).toHaveBeenCalledTimes(1))
    const hashFull = getCached.mock.calls[0][0]
    await screen.findByRole('button', { name: /인카운터/ }) // loading cleared
    rerender(<RecommendPanel roster={poolRoster} {...props} excludedSlugs={['a']} />)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await waitFor(() => expect(getCached).toHaveBeenCalledTimes(2))
    expect(getCached.mock.calls[1][0]).not.toEqual(hashFull)
  })

  // The palette filter narrows what is DRAWN. If it ever narrowed the request
  // too, a player would silently run a one-to-two-minute allocation against a
  // roster they never chose to shrink. The palette now only exists in the
  // seating modes, so that is where this is asked.
  describe('the palette filter and the search pool', () => {
    const paletteUnits: SupportedUnit[] = [
      { slug: 'a', name: 'Crown', burstTier: 1, element: 'Iron' },
      { slug: 'b', name: 'Anne', burstTier: 1, element: 'Fire' },
      { slug: 'c', name: 'Liter', burstTier: 2, element: 'Water' },
      { slug: 'd', name: 'Blanc', burstTier: 3, element: 'Wind' },
      { slug: 'e', name: 'Noir', burstTier: 3, element: 'Electric' },
      { slug: 'f', name: 'Dorothy', burstTier: 2, element: 'Iron' },
    ]
    const sixRoster = [...fullRoster, nikke('f')]

    const draftModeWith = async (excludedSlugs: string[]) => {
      const user = userEvent.setup()
      vi.mocked(getSupportedUnits).mockResolvedValue(paletteUnits)
      vi.mocked(recommendRaidDecks).mockResolvedValue(raidResponse)
      render(
        <RecommendPanel roster={sixRoster} {...noPersistence} excludedSlugs={excludedSlugs} />,
      )
      await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/i }))
      await screen.findByRole('button', { name: /Anne 배치/i })
      return user
    }

    it('sends the whole roster even while the palette shows one unit', async () => {
      const user = await draftModeWith([])
      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(screen.getByRole('button', { name: /Anne 배치/i })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /Crown 배치/i })).not.toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: /인카운터/ }))
      await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
      expect(vi.mocked(recommendRaidDecks).mock.calls[0][0].roster).toEqual(sixRoster)
    })

    // Benching is the pool control; filtering is not. A Nikke benched on the
    // roster tab stays benched no matter what the palette happens to be
    // showing.
    it('leaves an exclusion intact across a filter that hides that unit', async () => {
      const user = await draftModeWith(['b'])
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.queryByRole('button', { name: /Anne 배치/i })).not.toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: /인카운터/ }))
      await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
      expect(vi.mocked(recommendRaidDecks).mock.calls[0][0].roster).toEqual(
        sixRoster.filter((n) => n.character_slug !== 'b'),
      )
    })
  })
})

// 실행 버튼은 모드를 옮겨도 같은 이름이어야 하고(무엇을 시작하는지는 모드
// 라디오가 말한다), 스크롤을 내려도 닿을 수 있어야 한다.
describe('RecommendPanel 실행 버튼', () => {
  const renderAndPick = async (radio: RegExp) => {
    vi.mocked(getSupportedUnits).mockResolvedValue(makeEvaluateSupportedUnits())
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: radio }))
    // 모드마다 supported-units 도착의 증거가 다르다: 탐색 모드는 풀 개수 줄,
    // 편성 모드는 팔레트 칩(탐색 모드에는 팔레트 자체가 없다).
    if (/단일 덱|전부 최적화/.test(radio.source)) await screen.findByText(/탐색 풀에 포함됨/)
    else await screen.findByRole('button', { name: /a 배치/i })
    return user
  }

  it('모드를 바꿔도 유휴 상태의 라벨은 늘 인카운터!다', async () => {
    const user = await renderAndPick(/전부 최적화/i)
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/i }))
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /단일 덱/ }))
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()
  })

  // 실행 버튼은 두 집 중 하나에 산다: 덱 컬럼 안이거나, 설정 행 바로 아래거나.
  // 덱 컬럼이 없는 모드는 후자다.
  it('덱 컬럼이 없는 모드에서는 실행 버튼이 설정 행 바로 아래에 선다', async () => {
    await renderAndPick(/전부 최적화/i)

    const button = screen.getByRole('button', { name: /인카운터/ })
    expect(button.closest('.draft-layout__decks')).toBeNull()

    const setup = screen.getByRole('group', { name: /보스 설정/i }).parentElement!
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })
    expect(setup.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
    expect(button.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })

  it('덱 컬럼이 있는 모드에서는 실행 버튼이 덱과 함께 붙어 다닌다', async () => {
    const user = await renderAndPick(/전부 최적화/i)
    await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/i }))

    const button = screen.getByRole('button', { name: /인카운터/ })
    expect(button.closest('.draft-layout__decks')).not.toBeNull()
  })

  it('기대 딜량 계산 모드도 실행 버튼을 덱 컬럼에 둔다', async () => {
    const user = await renderAndPick(/전부 최적화/i)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))

    expect(
      screen.getByRole('button', { name: /인카운터/ }).closest('.draft-layout__decks'),
    ).not.toBeNull()
  })
})

describe('RecommendPanel 결과 보관', () => {
  const singleSuccess = () => {
    vi.mocked(recommendDecks).mockResolvedValue({
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          skill_damage: 0, hold_burst_slugs: [],
        },
      ],
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })
  }

  it('결과가 없으면 저장 버튼도 없다', async () => {
    await renderSettled(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    expect(screen.queryByRole('button', { name: '저장' })).not.toBeInTheDocument()
  })

  it('화면에 뜬 결과를 이름 붙여 솔로 탭 몫으로 남긴다', async () => {
    const user = userEvent.setup()
    singleSuccess()
    const saved: SavedRun[] = []
    render(
      <RecommendPanel
        roster={fullRoster}
        {...noPersistence}
        onSaveRun={(run: SavedRun) => {
          saved.push(run)
          return true
        }}
      />,
    )

    await user.click(screen.getByRole('button', { name: /인카운터/ }))
    await screen.findByText('#1')
    await user.click(screen.getByRole('button', { name: '저장' }))
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(saved).toHaveLength(1)
    expect(saved[0].tab).toBe('solo')
    expect(saved[0].view).toMatchObject({ mode: 'single' })
  })

  it('보관한 결과를 열면 그때의 덱을 다시 그린다', async () => {
    const user = userEvent.setup()
    render(
      <RecommendPanel
        roster={fullRoster}
        {...noPersistence}
        savedRuns={[
          {
            id: 'r1',
            name: '지난 주 배분',
            savedAt: 1754438400000,
            tab: 'solo',
            view: {
              mode: 'single',
              boss: {
                element: 'Fire',
                core_hittable: false,
                pierce_hits_body_behind_core: false,
                enemy_def: 31784,
                fight_duration: 180,
                part_destructible: false,
                core_diameter_px: null,
                effective_range_band: null,
                elemental_interrupt_required: false,
              },
              numDecks: 5,
              decks: [
                {
                  deck: ['a', 'b', 'c', 'd', 'e'],
                  total_damage: 777,
                  burst_damage: 400,
                  normal_attack_damage: 300,
                  skill_damage: 77, hold_burst_slugs: [],
                },
              ],
              excludedSlugs: [],
            },
          },
        ]}
      />,
    )

    await user.click(screen.getByRole('button', { name: /지난 주 배분/ }))

    expect(screen.getByText('777 총딜')).toBeInTheDocument()
  })

  // 여는 것만으로 폼이 바뀌면, 결과를 훑어보려던 클릭이 지금 짜던 설정을 지운다.
  it('"폼 채우기"를 눌러야 보스 설정이 그때로 돌아간다', async () => {
    const user = userEvent.setup()
    render(
      <RecommendPanel
        roster={fullRoster}
        {...noPersistence}
        savedRuns={[
          {
            id: 'r1',
            name: '지난 주 배분',
            savedAt: 1754438400000,
            tab: 'solo',
            view: {
              mode: 'single',
              boss: {
                element: 'Fire',
                core_hittable: true,
                pierce_hits_body_behind_core: false,
                enemy_def: 12345,
                fight_duration: 180,
                part_destructible: false,
                core_diameter_px: null,
                effective_range_band: null,
                elemental_interrupt_required: false,
              },
              numDecks: 5,
              decks: [],
              excludedSlugs: [],
            },
          },
        ]}
      />,
    )

    await user.click(screen.getByRole('button', { name: /지난 주 배분/ }))
    expect(screen.getByLabelText(/적 방어력/)).toHaveValue(31784)

    await user.click(screen.getByRole('button', { name: '이 설정으로 폼 채우기' }))

    expect(screen.getByLabelText(/적 방어력/)).toHaveValue(12345)
    expect(screen.getByLabelText('코어 피격 가능')).toBeChecked()
  })
})
