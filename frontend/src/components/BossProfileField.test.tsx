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

describe('BossProfileField 약점 속성 선택', () => {
  it('약점 아이콘을 고르면 보스 본인 속성이 draft로 간다', async () => {
    // 화면은 약점으로 말하고 와이어는 보스 본인 속성을 나른다. 수냉이 약점이면
    // 보스는 작열이다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('수냉'))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ element: 'Fire' }))
  })

  it('저장된 보스 속성이 대응하는 약점 아이콘을 선택 상태로 그린다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('수냉')).toBeChecked()
    expect(screen.getByLabelText('작열')).not.toBeChecked()
  })

  it('약점 없음이 null로 왕복한다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), element: 'Fire' }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('약점 없음'))

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ element: null }))
  })
})

describe('BossProfileField 속성저지', () => {
  it('기본으로 속성저지 체크박스를 그린다', async () => {
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('속성저지 필수'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ elemental_interrupt_required: true }),
    )
  })

  it('showElementalInterrupt=false면 그리지 않는다', () => {
    // 유니온레이드 탭은 탐색이 없어 제약이 걸 곳이 없다.
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        onChange={vi.fn()}
        showElementalInterrupt={false}
      />,
    )

    expect(screen.queryByLabelText('속성저지 필수')).not.toBeInTheDocument()
  })
})

describe('BossProfileField 코어 2관통', () => {
  it('2관통을 켜면 코어 피격 가능도 함께 켜진다', async () => {
    // 코어를 못 때리면 뚫고 지나갈 것이 없다. 모순 상태를 만들 수 없게 한다.
    const user = userEvent.setup()
    const onChange = renderField()

    await user.click(screen.getByLabelText('상시 코어 2관통'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: true, pierce_hits_body_behind_core: true }),
    )
  })

  it('코어 피격 가능을 끄면 2관통도 꺼진다', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <BossProfileField
        value={{
          ...makeDefaultBossProfileDraft(),
          core_hittable: true,
          pierce_hits_body_behind_core: true,
        }}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByLabelText('코어 피격 가능'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ core_hittable: false, pierce_hits_body_behind_core: false }),
    )
  })
})

describe('기타 설정', () => {
  it('방어력과 전투 시간을 접되 요약에 그 값을 남긴다', () => {
    render(
      <BossProfileField value={makeDefaultBossProfileDraft('31784')} onChange={vi.fn()} />,
    )

    const details = screen.getByText(/기타 설정/).closest('details')
    expect(details).not.toBeNull()
    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText(/방어력 31,784/)).toBeInTheDocument()
    expect(screen.getByText(/180초/)).toBeInTheDocument()
  })

  it('접힌 칸에 오류가 있으면 스스로 펼친다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), enemy_def: '' }}
        errors={{ enemy_def: '필수 입력이에요' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByText(/기타 설정/).closest('details')).toHaveAttribute('open')
  })

  it('편집 중이라 비어 있는 칸은 요약에서 —로 둔다', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), enemy_def: '' }}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByText(/방어력 —/)).toBeInTheDocument()
  })
})
