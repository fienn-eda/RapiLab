import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ClearDraftButton } from './ClearDraftButton'
import type { Draft } from '../types/draft'

const filled: Draft = { decks: [[{ slug: 'a', locked: false }], []] }
const empty: Draft = { decks: [[], []] }

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ClearDraftButton', () => {
  it('확인을 수락하면 비운다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const onClear = vi.fn()
    const user = userEvent.setup()
    render(<ClearDraftButton draft={filled} onClear={onClear} />)

    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    expect(onClear).toHaveBeenCalledOnce()
  })

  it('확인을 거절하면 비우지 않는다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const onClear = vi.fn()
    const user = userEvent.setup()
    render(<ClearDraftButton draft={filled} onClear={onClear} />)

    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    expect(onClear).not.toHaveBeenCalled()
  })

  it('편성이 비어 있으면 누를 수 없다', () => {
    render(<ClearDraftButton draft={empty} onClear={() => {}} />)

    expect(screen.getByRole('button', { name: '전체 초기화' })).toBeDisabled()
  })

  it('폼 안에서 제출을 일으키지 않는다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    const user = userEvent.setup()
    render(
      <form onSubmit={onSubmit}>
        <ClearDraftButton draft={filled} onClear={() => {}} />
      </form>,
    )

    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
