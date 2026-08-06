import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SaveRunButton } from './SaveRunButton'

describe('SaveRunButton', () => {
  it('제안한 이름을 미리 채운 칸을 연다', async () => {
    const user = userEvent.setup()
    render(<SaveRunButton suggestedName="작열 · 전부 최적화 · 08-06" onSave={() => true} />)

    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(screen.getByLabelText('이름')).toHaveValue('작열 · 전부 최적화 · 08-06')
  })

  it('고친 이름으로 저장하고 닫는다', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(() => true)
    render(<SaveRunButton suggestedName="제안" onSave={onSave} />)

    await user.click(screen.getByRole('button', { name: '저장' }))
    const field = screen.getByLabelText('이름')
    await user.clear(field)
    await user.type(field, '내 이름')
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(onSave).toHaveBeenCalledWith('내 이름')
    expect(screen.queryByLabelText('이름')).not.toBeInTheDocument()
  })

  it('빈 이름으로는 저장하지 않는다', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(() => true)
    render(<SaveRunButton suggestedName="제안" onSave={onSave} />)

    await user.click(screen.getByRole('button', { name: '저장' }))
    await user.clear(screen.getByLabelText('이름'))
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(onSave).not.toHaveBeenCalled()
  })

  // 눌렀는데 아무 일도 안 나는 화면을 만들지 않는다.
  it('저장소가 거절하면 닫지 않고 이유를 말한다', async () => {
    const user = userEvent.setup()
    render(<SaveRunButton suggestedName="제안" onSave={() => false} />)

    await user.click(screen.getByRole('button', { name: '저장' }))
    await user.click(screen.getByRole('button', { name: '확인' }))

    expect(screen.getByRole('alert')).toHaveTextContent(/50개/)
    expect(screen.getByLabelText('이름')).toBeInTheDocument()
  })

  it('취소하면 저장하지 않고 닫는다', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(() => true)
    render(<SaveRunButton suggestedName="제안" onSave={onSave} />)

    await user.click(screen.getByRole('button', { name: '저장' }))
    await user.click(screen.getByRole('button', { name: '취소' }))

    expect(onSave).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '저장' })).toBeInTheDocument()
  })
})
