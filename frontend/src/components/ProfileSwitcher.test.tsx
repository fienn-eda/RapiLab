import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProfileSwitcher } from './ProfileSwitcher'
import type { Profile } from '../types/profile'

const makeProfile = (overrides: Partial<Profile> = {}): Profile => ({
  openId: 'abc123',
  nickname: 'Fienn',
  roster: [],
  results: {},
  lastResultHash: null,
  lastInputs: null,
  ...overrides,
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ProfileSwitcher', () => {
  it('renders nothing when there are no profiles', () => {
    const { container } = render(
      <ProfileSwitcher
        profiles={[]}
        activeOpenId={null}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('lists each profile by nickname, with the active one selected', () => {
    const profiles = [
      makeProfile({ openId: 'a', nickname: '본계' }),
      makeProfile({ openId: 'b', nickname: '부계' }),
    ]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeOpenId="b"
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: '본계' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '부계' })).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toHaveValue('b')
  })

  it('falls back to the openId when nickname is empty', () => {
    const profiles = [makeProfile({ openId: 'no-nick', nickname: '' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeOpenId="no-nick"
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: 'no-nick' })).toBeInTheDocument()
  })

  it('calls onSwitch(openId) when the selection changes', async () => {
    const user = userEvent.setup()
    const onSwitch = vi.fn()
    const profiles = [
      makeProfile({ openId: 'a', nickname: '본계' }),
      makeProfile({ openId: 'b', nickname: '부계' }),
    ]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeOpenId="a"
        onSwitch={onSwitch}
        onDelete={vi.fn()}
      />,
    )
    await user.selectOptions(screen.getByRole('combobox'), '부계')
    expect(onSwitch).toHaveBeenCalledWith('b')
  })

  it('calls onDelete(openId) for the active profile after confirming', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    const onDelete = vi.fn()
    const profiles = [makeProfile({ openId: 'a', nickname: '본계' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeOpenId="a"
        onSwitch={vi.fn()}
        onDelete={onDelete}
      />,
    )
    await user.click(screen.getByRole('button', { name: /삭제/i }))
    expect(window.confirm).toHaveBeenCalledOnce()
    expect(onDelete).toHaveBeenCalledWith('a')
  })

  it('does not delete when the confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    const onDelete = vi.fn()
    const profiles = [makeProfile({ openId: 'a', nickname: '본계' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeOpenId="a"
        onSwitch={vi.fn()}
        onDelete={onDelete}
      />,
    )
    await user.click(screen.getByRole('button', { name: /삭제/i }))
    expect(onDelete).not.toHaveBeenCalled()
  })
})
