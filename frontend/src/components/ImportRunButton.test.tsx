import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ImportRunButton } from './ImportRunButton'
import type { Draft } from '../types/draft'
import type { SavedRun } from '../types/profile'

const run = (id: string, name: string): SavedRun => ({
  id,
  name,
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
      core_diameter_px: null,
      effective_range_band: null,
      elemental_interrupt_required: false,
    },
    numDecks: 2,
    decks: [],
    combinedTotalDamage: 1,
    excludedSlugs: [],
    leftoverSlugs: [],
  },
})

const filled: Draft = { decks: [[{ slug: 'a', locked: false }], []] }
const empty: Draft = { decks: [[], []] }

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ImportRunButton', () => {
  it('저장한 결과가 없으면 누를 수 없다', () => {
    render(<ImportRunButton runs={[]} draft={empty} onImport={() => {}} />)

    expect(screen.getByRole('button', { name: '결과 가져오기' })).toBeDisabled()
  })

  it('누르면 목록이 펼쳐지고 다시 누르면 접힌다', async () => {
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염 · 전부 최적화')]} draft={empty} onImport={() => {}} />)
    const toggle = screen.getByRole('button', { name: '결과 가져오기' })

    await user.click(toggle)
    expect(screen.getByText('화염 · 전부 최적화')).toBeInTheDocument()

    await user.click(toggle)
    expect(screen.queryByText('화염 · 전부 최적화')).not.toBeInTheDocument()
  })

  it('고르면 그 결과를 넘기고 목록을 접는다', async () => {
    const onImport = vi.fn()
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염')]} draft={empty} onImport={onImport} />)

    await user.click(screen.getByRole('button', { name: '결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(onImport).toHaveBeenCalledWith(expect.objectContaining({ id: 'r1' }))
    expect(screen.queryByRole('button', { name: '가져오기' })).not.toBeInTheDocument()
  })

  it('편성이 비어 있으면 덮어쓸지 묻지 않는다', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염')]} draft={empty} onImport={() => {}} />)

    await user.click(screen.getByRole('button', { name: '결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(confirmSpy).not.toHaveBeenCalled()
  })

  it('편성이 차 있으면 묻고, 거절하면 가져오지 않는다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const onImport = vi.fn()
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염')]} draft={filled} onImport={onImport} />)

    await user.click(screen.getByRole('button', { name: '결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(window.confirm).toHaveBeenCalledOnce()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('폼 안에서 제출을 일으키지 않는다', async () => {
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    const user = userEvent.setup()
    render(
      <form onSubmit={onSubmit}>
        <ImportRunButton runs={[run('r1', '화염')]} draft={empty} onImport={() => {}} />
      </form>,
    )

    await user.click(screen.getByRole('button', { name: '결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
