import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { makeEmptyDraft, type NikkeDraft } from './types/nikkeDraft'
import type { ProfilesState } from './types/profile'

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

const seedProfiles = (state: ProfilesState) => {
  localStorage.setItem('nikke-profiles', JSON.stringify(state))
}

beforeEach(() => {
  localStorage.clear()
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

  it('shows the synced roster and recommend panel once a profile is active', () => {
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
    expect(screen.getByRole('heading', { name: 'Recommend decks' })).toBeInTheDocument()
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
})
