import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProfileSwitcher } from './ProfileSwitcher'
import { profileKey, type Profile } from '../types/profile'

const makeProfile = (overrides: Partial<Profile> = {}): Profile => ({
  openId: 'abc123',
  area: 81,
  nickname: 'Fienn',
  roster: [],
  results: {},
  lastResultHash: null,
  lastInputs: null,
  savedRuns: [],
  excludedSlugs: [],
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
        activeKey={null}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
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
        activeKey={profileKey('b', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: '본계 (JP)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '부계 (JP)' })).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toHaveValue(profileKey('b', 81))
  })

  it('falls back to the openId when nickname is empty', () => {
    const profiles = [makeProfile({ openId: 'no-nick', nickname: '' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey={profileKey('no-nick', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: 'no-nick (JP)' })).toBeInTheDocument()
  })

  it('같은 닉네임의 두 서버 계정을 서버 표기로 구분한다', () => {
    const profiles = [
      makeProfile({ openId: '111111', area: 81, nickname: 'FIENN' }),
      makeProfile({ openId: '111111', area: 83, nickname: 'FIENN' }),
    ]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey="111111:83"
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: 'FIENN (JP)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'FIENN (KR)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'FIENN (KR) 프로필 삭제' })).toBeInTheDocument()
  })

  it('이름이 없는 프로필에도 서버가 붙는다', () => {
    const profiles = [makeProfile({ openId: '', area: 83, nickname: '' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey=":83"
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: '이름 없는 계정 (KR)' })).toBeInTheDocument()
  })

  it('calls onSwitch(key) when the selection changes', async () => {
    const user = userEvent.setup()
    const onSwitch = vi.fn()
    const profiles = [
      makeProfile({ openId: 'a', nickname: '본계' }),
      makeProfile({ openId: 'b', nickname: '부계' }),
    ]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey={profileKey('a', 81)}
        onSwitch={onSwitch}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    await user.selectOptions(screen.getByRole('combobox'), '부계 (JP)')
    expect(onSwitch).toHaveBeenCalledWith(profileKey('b', 81))
  })

  it('calls onDelete(key) for the active profile after confirming', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    const onDelete = vi.fn()
    const profiles = [makeProfile({ openId: 'a', nickname: '본계' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={onDelete}
        onRename={vi.fn()}
      />,
    )
    await user.click(screen.getByRole('button', { name: /삭제/i }))
    expect(window.confirm).toHaveBeenCalledOnce()
    expect(onDelete).toHaveBeenCalledWith(profileKey('a', 81))
  })

  // A failed sync can leave a profile keyed by the empty string. It is the one
  // profile a player most needs to remove, and an `!activeKey` guard treats it
  // as "no account selected" - the delete button silently does nothing.
  it('deletes a profile whose openId is the empty string', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    const onDelete = vi.fn()
    const profiles = [
      makeProfile({ openId: 'a', nickname: '본계' }),
      makeProfile({ openId: '', nickname: '' }),
    ]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey={profileKey('', 81)}
        onSwitch={vi.fn()}
        onDelete={onDelete}
        onRename={vi.fn()}
      />,
    )
    await user.click(screen.getByRole('button', { name: /삭제/i }))
    expect(window.confirm).toHaveBeenCalledOnce()
    expect(onDelete).toHaveBeenCalledWith(profileKey('', 81))
  })

  // With neither a nickname nor an openId to show, the option and the delete
  // button's accessible name both collapse to blank, leaving the entry
  // unidentifiable in the dropdown and unreachable by name.
  it('labels a profile that has neither nickname nor openId', () => {
    const profiles = [makeProfile({ openId: '', nickname: '' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey={profileKey('', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: '이름 없는 계정 (JP)' })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: '이름 없는 계정 (JP) 프로필 삭제' }),
    ).toBeInTheDocument()
  })

  it('does not delete when the confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    const onDelete = vi.fn()
    const profiles = [makeProfile({ openId: 'a', nickname: '본계' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={onDelete}
        onRename={vi.fn()}
      />,
    )
    await user.click(screen.getByRole('button', { name: /삭제/i }))
    expect(onDelete).not.toHaveBeenCalled()
  })

  it('이름 바꾸기를 누르면 현재 이름이 든 입력이 뜨고, 저장하면 그 이름으로 부른다', async () => {
    const onRename = vi.fn()
    const profile = makeProfile({ openId: 'a', nickname: '본계' })
    render(
      <ProfileSwitcher
        profiles={[profile]}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={onRename}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: '계정 이름 바꾸기' }))
    const input = screen.getByRole('textbox', { name: '계정 이름' })
    expect((input as HTMLInputElement).value).toBe('본계')
    await userEvent.clear(input)
    await userEvent.type(input, 'JP 본계')
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(onRename).toHaveBeenCalledWith('a:81', 'JP 본계')
  })

  // 이름을 아직 못 읽은 계정이 이 기능이 가장 필요한 계정이다. 그때 입력이
  // UID로 채워져 있으면 유저가 그것을 지우는 것부터 해야 한다.
  it('이름이 없는 계정은 빈 입력으로 시작한다', async () => {
    render(
      <ProfileSwitcher
        profiles={[makeProfile({ openId: 'a', nickname: '' })]}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: '계정 이름 바꾸기' }))
    expect((screen.getByRole('textbox', { name: '계정 이름' }) as HTMLInputElement).value).toBe('')
  })

  it('빈 이름으로는 저장하지 않는다', async () => {
    const onRename = vi.fn()
    render(
      <ProfileSwitcher
        profiles={[makeProfile({ openId: 'a', nickname: '본계' })]}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={onRename}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: '계정 이름 바꾸기' }))
    await userEvent.clear(screen.getByRole('textbox', { name: '계정 이름' }))
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(onRename).not.toHaveBeenCalled()
  })

  // 활성 계정이 없는 상태에서 이름 바꾸기 버튼이 눌리면 어느 계정을 바꿀지가
  // 없다. 삭제 버튼이 activeKey === null에서 아무것도 안 하는 것과 같은 이유다.
  it('활성 계정이 없으면 이름 바꾸기 버튼이 없다', () => {
    render(
      <ProfileSwitcher
        profiles={[makeProfile({ openId: 'a' })]}
        activeKey={null}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    expect(screen.queryByRole('button', { name: '계정 이름 바꾸기' })).toBeNull()
  })
})
