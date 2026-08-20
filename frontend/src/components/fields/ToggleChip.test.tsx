import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ToggleChip } from './ToggleChip'
import { HelpTip } from '../HelpTip'

describe('ToggleChip', () => {
  it('진짜 체크박스로 렌더된다 - 라벨로 찾을 수 있어야 한다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <ToggleChip type="checkbox" checked={false} onChange={onChange}>
        코어 타격 가능
      </ToggleChip>,
    )

    const input = screen.getByLabelText('코어 타격 가능')
    expect(input).toHaveAttribute('type', 'checkbox')
    await user.click(input)
    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('라디오는 name으로 묶인다', () => {
    render(
      <>
        <ToggleChip type="radio" name="mode" checked onChange={vi.fn()}>
          단일 덱
        </ToggleChip>
        <ToggleChip type="radio" name="mode" checked={false} onChange={vi.fn()}>
          전부 최적화
        </ToggleChip>
      </>,
    )

    expect(screen.getByLabelText('단일 덱')).toBeChecked()
    expect(screen.getByLabelText('전부 최적화')).not.toBeChecked()
  })

  // 이 구조의 존재 이유. help가 <label> 안에 있으면 설명을 열려던 클릭이
  // 설정을 바꾼다.
  it('설명 버튼을 눌러도 토글되지 않는다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <ToggleChip
        type="checkbox"
        checked={false}
        onChange={onChange}
        help={<HelpTip label="코어 타격 가능">코어를 때릴 수 있는 보스</HelpTip>}
      >
        코어 타격 가능
      </ToggleChip>,
    )

    await user.click(screen.getByRole('button', { name: '코어 타격 가능 설명' }))
    expect(onChange).not.toHaveBeenCalled()
  })
})
