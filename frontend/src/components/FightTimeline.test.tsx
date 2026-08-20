import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FightTimeline } from './FightTimeline'

describe('FightTimeline', () => {
  it('전투 시간과 파괴 시각을 적는다', () => {
    render(<FightTimeline durationSeconds={180} destructionTimes={[1, 61, 126]} />)

    expect(screen.getByText('180초')).toBeInTheDocument()
    expect(screen.getByText('파괴 1 · 61 · 126초')).toBeInTheDocument()
  })

  // 빈 눈금을 그리면 「관측 안 함」이 「0개」로 읽힌다.
  it('파괴 시각이 없으면 아무것도 안 그린다', () => {
    const { container } = render(
      <FightTimeline durationSeconds={180} destructionTimes={[]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('전투 시간이 숫자가 아니면 아무것도 안 그린다', () => {
    const { container } = render(
      <FightTimeline durationSeconds={Number.NaN} destructionTimes={[1]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('전투 시간이 0이면 아무것도 안 그린다 - 나눌 수 없다', () => {
    const { container } = render(
      <FightTimeline durationSeconds={0} destructionTimes={[1]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  // 전투 시간을 넘는 시각은 판독이 틀린 것이다. 끝에 몰아 찍으면 틀렸다는
  // 사실이 감춰지므로 버린다.
  it('전투 시간 밖의 시각은 버린다', () => {
    render(<FightTimeline durationSeconds={100} destructionTimes={[10, 150]} />)
    expect(screen.getByText('파괴 10초')).toBeInTheDocument()
  })

  it('전부 전투 시간 밖이면 아무것도 안 그린다', () => {
    const { container } = render(
      <FightTimeline durationSeconds={100} destructionTimes={[150, 200]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('눈금이 파괴 시각마다 하나씩 선다 - 기준선 하나를 더한 수다', () => {
    const { container } = render(
      <FightTimeline durationSeconds={180} destructionTimes={[1, 61, 126]} />,
    )
    expect(container.querySelectorAll('line')).toHaveLength(4)
  })
})
