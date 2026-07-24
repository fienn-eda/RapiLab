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
  it('states the harmony cube assumption', () => {
    render(<App />)
    expect(screen.getByText(/Resilience Cube Lv\.15/i)).toBeInTheDocument()
  })

  it('prompts to sync and hides the roster/recommend panel when there is no active profile', () => {
    render(<App />)
    expect(screen.getByText(/no synced account yet/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Recommend decks' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'red-hood' })).not.toBeInTheDocument()
  })

  it('opens on the roster tab and reaches the recommend panel through its tab', async () => {
    const user = userEvent.setup()
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

    expect(screen.getByRole('heading', { name: 'red-hood' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Recommend decks' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Recommend' }))

    expect(screen.getByRole('heading', { name: 'Recommend decks' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'red-hood' })).not.toBeInTheDocument()
  })

  it('switches the displayed roster when the active profile changes (isolation)', async () => {
    const user = userEvent.setup()
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
    expect(screen.getByRole('heading', { name: 'red-hood' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'privaty' })).not.toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Account'), '부계')

    expect(screen.getByRole('heading', { name: 'privaty' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'red-hood' })).not.toBeInTheDocument()
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
    await user.click(screen.getByRole('tab', { name: 'Recommend' }))
    await user.click(screen.getByLabelText(/raid allocation/i))
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/1–2 minutes/)
    expect(screen.getByLabelText(/raid allocation/i)).toBeChecked()

    await user.selectOptions(screen.getByLabelText('Account'), '부계')

    // A fresh RecommendPanel instance: no in-flight status banner (a new
    // useRecommendRaid, not the one A's never-resolving promise still
    // targets) and mode reset to its 'single' default - proof of a full
    // remount, not just the restore effect (which never touches `mode`).
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.getByLabelText(/single deck/i)).toBeChecked()
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
    await user.click(screen.getByRole('tab', { name: 'Recommend' }))
    await user.click(screen.getByLabelText(/raid allocation/i))
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))
    expect(await screen.findByRole('status')).toHaveTextContent(/1–2 minutes/)

    await user.click(screen.getByRole('tab', { name: 'Roster' }))
    await user.click(screen.getByRole('tab', { name: 'Recommend' }))

    // Still running, and still in raid mode - a remount would have reset both.
    expect(screen.getByRole('status')).toHaveTextContent(/1–2 minutes/)
    expect(screen.getByLabelText(/raid allocation/i)).toBeChecked()
    expect(vi.mocked(recommendRaidDecks)).toHaveBeenCalledTimes(1)
  })
})
