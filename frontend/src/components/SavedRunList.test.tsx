import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SavedRunList } from './SavedRunList'
import { HELP } from '../lib/helpText'
import type { SavedRun } from '../types/profile'

const run = (overrides: Partial<SavedRun> = {}): SavedRun => ({
  id: 'r1',
  name: '작열 · 전부 최적화 · 08-06',
  savedAt: 1754438400000,
  tab: 'solo',
  view: {
    mode: 'raid',
    boss: {
      element: 'Fire',
      core_hittable: false,
      pierce_hits_body_behind_core: false,
      enemy_def: 31784,
      fight_duration: 180,
      part_destructible: false,
      part_destruction_times: [],
      spawns_adds: false,
      hold_fire_despite_adds: false,
      core_diameter_px: null,
      effective_range_band: null,
      elemental_interrupt_required: false,
    },
    numDecks: 5,
    decks: [],
    combinedTotalDamage: 1,
    excludedSlugs: [],
    leftoverSlugs: [],
  },
  ...overrides,
})

const noop = () => {}

const renderList = (overrides = {}) =>
  render(
    <SavedRunList
      runs={[run()]}
      renderRun={() => <p>결과 내용</p>}
      onRestore={noop}
      onRename={noop}
      onDelete={noop}
      {...overrides}
    />,
  )

describe('SavedRunList', () => {
  it('보관한 것이 없으면 없다고 말한다', () => {
    renderList({ runs: [] })

    expect(screen.getByText(HELP.savedRuns.empty)).toBeInTheDocument()
  })

  it('열기 전에는 결과를 그리지 않는다', async () => {
    const user = userEvent.setup()
    renderList()
    expect(screen.queryByText('결과 내용')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))

    expect(screen.getByText('결과 내용')).toBeInTheDocument()
  })

  // 여는 것만으로 폼이 바뀌면, 결과를 훑어보려던 클릭이 지금 짜던 설정을 지운다.
  it('여는 것만으로는 폼을 되돌리지 않는다', async () => {
    const user = userEvent.setup()
    const onRestore = vi.fn()
    renderList({ onRestore })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    expect(onRestore).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: '이 설정으로 폼 채우기' }))
    expect(onRestore).toHaveBeenCalledWith(run())
  })

  it('지우기 전에 묻는다', async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderList({ onDelete })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await user.click(screen.getByRole('button', { name: '삭제' }))
    expect(onDelete).not.toHaveBeenCalled()

    confirmSpy.mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: '삭제' }))
    expect(onDelete).toHaveBeenCalledWith('r1')

    confirmSpy.mockRestore()
  })

  it('그 자리에서 이름을 바꾼다', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await user.click(screen.getByRole('button', { name: '이름 바꾸기' }))
    const field = screen.getByLabelText('이름')
    await user.clear(field)
    await user.type(field, '새 이름')
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(onRename).toHaveBeenCalledWith('r1', '새 이름')
  })

  it('빈 이름으로는 바꾸지 않는다', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await user.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await user.click(screen.getByRole('button', { name: '이름 바꾸기' }))
    await user.clear(screen.getByLabelText('이름'))
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(onRename).not.toHaveBeenCalled()
  })

  // 이름에도 날짜가 들어갈 수 있으므로 시각까지 있는 형식으로 특정한다.
  it('저장한 때를 보여준다', () => {
    renderList()

    expect(screen.getByText(/^\d{2}-\d{2} \d{2}:\d{2}$/)).toBeInTheDocument()
  })
})
