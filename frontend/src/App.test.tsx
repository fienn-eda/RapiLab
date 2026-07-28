import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { makeEmptyDraft, type NikkeDraft } from './types/nikkeDraft'
import type { ProfilesState } from './types/profile'

vi.mock('./api/recommendRaid', () => ({
  recommendRaidDecks: vi.fn(),
}))
vi.mock('./api/supportedUnits', () => ({
  getSupportedUnits: vi.fn(),
}))

import { recommendRaidDecks } from './api/recommendRaid'
import { getSupportedUnits } from './api/supportedUnits'

const validDraft = (overrides: Partial<NikkeDraft> = {}): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: 'red-hood',
  level: '200',
  hp: '1000000',
  atk: '85000',
  def_: '12000',
  skill_levels: { skill1: '10', skill2: '7', burst: '4' },
  ...overrides,
})

// RecommendPanel's raid mode requires MIN_DECK_ROSTER_SIZE (5) ready Nikkes
// before its submit button enables.
const fiveValidDrafts = (slugPrefix: string): NikkeDraft[] =>
  Array.from({ length: 5 }, (_, i) => validDraft({ character_slug: `${slugPrefix}-${i}` }))

const seedProfiles = (state: ProfilesState) => {
  localStorage.setItem('nikke-profiles', JSON.stringify(state))
}

beforeEach(() => {
  localStorage.clear()
  vi.mocked(getSupportedUnits).mockResolvedValue([])
})

afterEach(() => {
  vi.mocked(recommendRaidDecks).mockReset()
  vi.mocked(getSupportedUnits).mockReset()
})

describe('App', () => {
  it('앱 이름을 RapiLab으로 내건다', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'RapiLab' })).toBeInTheDocument()
  })

  it('states the harmony cube assumption', () => {
    render(<App />)
    expect(screen.getByText(/재장전 큐브 15레벨/i)).toBeInTheDocument()
  })

  it('prompts to sync and hides the roster/recommend panel when there is no active profile', () => {
    render(<App />)
    expect(screen.getByText(/동기화된 계정이 없어요/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '솔로 레이드' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'red-hood' })).not.toBeInTheDocument()
  })

  // The roster grid cards a unit only once /api/supported-units confirms the
  // engine can simulate it, so these have to wait for that list to land.
  const SUPPORTED = [
    { slug: 'red-hood', name: 'Red Hood', burstTier: 1, element: 'Fire' },
    { slug: 'privaty', name: 'Privaty', burstTier: 2, element: 'Water' },
  ] as const

  it('opens on the roster tab and reaches the recommend panel through its tab', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    seedProfiles({
      activeOpenId: 'acct-a',
      profiles: {
        'acct-a': {
          openId: 'acct-a',
          nickname: '본계',
          roster: [validDraft()],
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
      },
    })

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Red Hood' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '솔로 레이드' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))

    expect(screen.getByRole('heading', { name: '솔로 레이드' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Red Hood' })).not.toBeInTheDocument()
  })

  it('renders three tabs and reaches the union raid panel through its own tab', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    seedProfiles({
      activeOpenId: 'acct-a',
      profiles: {
        'acct-a': {
          openId: 'acct-a',
          nickname: '본계',
          roster: [validDraft()],
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
      },
    })

    render(<App />)
    expect(screen.getAllByRole('tab')).toHaveLength(3)
    expect(screen.queryByRole('heading', { name: '유니온 레이드' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: '유니온 레이드' }))

    expect(screen.getByRole('heading', { name: '유니온 레이드' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Red Hood' })).not.toBeInTheDocument()
  })

  it('switches the displayed roster when the active profile changes (isolation)', async () => {
    const user = userEvent.setup()
    vi.mocked(getSupportedUnits).mockResolvedValue([...SUPPORTED])
    seedProfiles({
      activeOpenId: 'acct-a',
      profiles: {
        'acct-a': {
          openId: 'acct-a',
          nickname: '본계',
          roster: [validDraft({ character_slug: 'red-hood' })],
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
        'acct-b': {
          openId: 'acct-b',
          nickname: '부계',
          roster: [validDraft({ character_slug: 'privaty' })],
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
      },
    })

    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Red Hood' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Privaty' })).not.toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('계정'), '부계')

    expect(screen.getByRole('heading', { name: 'Privaty' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Red Hood' })).not.toBeInTheDocument()
  })

  it('resets in-flight raid state and form mode when switching profiles (RecommendPanel is remounted per profile)', async () => {
    const user = userEvent.setup()
    // Never resolves during the test - if the profile-keyed remount didn't
    // isolate RecommendPanel's useRecommendRaid instance, this promise
    // landing later could leak profile A's loading/result into profile B.
    vi.mocked(recommendRaidDecks).mockImplementation(() => new Promise(() => {}))

    seedProfiles({
      activeOpenId: 'acct-a',
      profiles: {
        'acct-a': {
          openId: 'acct-a',
          nickname: '본계',
          roster: fiveValidDrafts('a'),
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
        'acct-b': {
          openId: 'acct-b',
          nickname: '부계',
          roster: fiveValidDrafts('b'),
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
      },
    })

    render(<App />)
    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/1~2분/)
    expect(screen.getByLabelText(/전부 최적화/i)).toBeChecked()

    await user.selectOptions(screen.getByLabelText('계정'), '부계')

    // A fresh RecommendPanel instance: no in-flight status banner (a new
    // useRecommendRaid, not the one A's never-resolving promise still
    // targets) and mode reset to its 'single' default - proof of a full
    // remount, not just the restore effect (which never touches `mode`).
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.getByLabelText(/단일 덱/i)).toBeChecked()
  })

  it('keeps an in-flight raid alive across a tab switch', async () => {
    const user = userEvent.setup()
    // A raid allocation runs 1-2 minutes. Looking at the roster mid-run is a
    // normal thing to do, and it must not abandon the request: the panel is
    // hidden on tab switch, never unmounted.
    vi.mocked(recommendRaidDecks).mockImplementation(() => new Promise(() => {}))

    seedProfiles({
      activeOpenId: 'acct-a',
      profiles: {
        'acct-a': {
          openId: 'acct-a',
          nickname: '본계',
          roster: fiveValidDrafts('a'),
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
      },
    })

    render(<App />)
    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))
    await user.click(screen.getByLabelText(/전부 최적화/i))
    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/1~2분/)

    await user.click(screen.getByRole('tab', { name: '니케 풀' }))
    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))

    // Still running, and still in raid mode - a remount would have reset both.
    expect(screen.getByRole('status')).toHaveTextContent(/1~2분/)
    expect(screen.getByLabelText(/전부 최적화/i)).toBeChecked()
    expect(vi.mocked(recommendRaidDecks)).toHaveBeenCalledTimes(1)
  })

  it('활성 프로필이 없는 화면에서는 동기화 도움말이 펼쳐져 있다', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('이미 동기화한 계정이 있으면 로스터 탭의 도움말은 접혀 있다', () => {
    seedProfiles({
      activeOpenId: 'open-1',
      profiles: {
        'open-1': {
          openId: 'open-1',
          nickname: 'Fienn',
          roster: [],
          results: {},
          lastResultHash: null,
          lastInputs: null,
        },
      },
    })
    render(<App />)
    expect(screen.getByRole('button', { name: '동기화 방법' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
  })
})
