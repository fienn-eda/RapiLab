// 보스 설정의 설명은 라벨 옆 버튼 뒤에 접혀 있다. 여기서 지키는 것은 그
// 버튼이 설정 자체를 건드리지 않는다는 것 - 체크박스 라벨 안에 있으면
// 설명을 열려는 클릭이 보스 프로필을 바꾼다.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { BossProfileField } from './BossProfileField'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'

const renderField = (onChange = vi.fn()) => {
  render(<BossProfileField value={makeDefaultBossProfileDraft()} onChange={onChange} />)
  return onChange
}

describe('BossProfileField', () => {
  it('설명 버튼을 눌러도 체크박스가 바뀌지 않는다', async () => {
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByRole('button', { name: '코어 피격 가능 설명' }))
    await user.click(screen.getByRole('button', { name: '부위파괴 기믹 설명' }))

    expect(onChange).not.toHaveBeenCalled()
  })

  it('체크박스는 설명을 뺀 이름으로 잡힌다', async () => {
    // 설명이 라벨 안에 있으면 접근성 이름이 문단 하나가 되어, 화면 낭독기가
    // 체크박스 하나를 읽는 데 세 문장을 읽는다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('코어 피격 가능'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: true }),
    )
  })

  it('설명은 자기가 딸린 설정을 가리킨다', () => {
    renderField()

    const button = screen.getByRole('button', { name: '보스 적정거리 설명' })
    const bubbleId = button.getAttribute('aria-describedby')

    expect(bubbleId).toBeTruthy()
    expect(document.getElementById(bubbleId!)).toHaveTextContent(
      '런처(RL)는 어느 거리에서도 받지 않아요',
    )
  })
})
