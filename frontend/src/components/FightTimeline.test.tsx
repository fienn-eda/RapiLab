import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FightTimeline } from './FightTimeline'
import type { GuideEvent } from '../hooks/useBossGuides'

const ev = (over: Partial<GuideEvent> = {}): GuideEvent => ({
  id: 'e1',
  at: 20,
  text: '탄막 사격 — 엄폐로 넘긴다',
  ...over,
})

const rows = () => screen.getAllByRole('listitem')

describe('FightTimeline', () => {
  it('축의 두 끝을 잔여시간으로 적는다', () => {
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[]}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByText('3:00')).toBeInTheDocument()
    expect(screen.getByText('0:00')).toBeInTheDocument()
    expect(screen.getByText('전투 시작')).toBeInTheDocument()
    expect(screen.getByText('종료')).toBeInTheDocument()
  })

  it('파괴 시각을 잔여시간으로 뒤집어 찍는다', () => {
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[1, 61, 126]}
        events={[]}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByText('2:59')).toBeInTheDocument()
    expect(screen.getByText('1:59')).toBeInTheDocument()
    expect(screen.getByText('0:54')).toBeInTheDocument()
    expect(screen.getAllByText('부위파괴')).toHaveLength(3)
  })

  // 엔진이 읽는 입력이라 여기서 고치면 진실이 둘이 된다.
  it('파괴 행은 읽기 전용이다 - 입력 칸도 삭제 버튼도 없다', () => {
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[61]}
        events={[]}
        onChange={vi.fn()}
      />,
    )

    const row = rows().find((r) => within(r).queryByText('부위파괴'))!
    expect(within(row).queryByRole('textbox')).not.toBeInTheDocument()
    expect(within(row).queryByRole('button')).not.toBeInTheDocument()
  })

  it('경과 초 오름차순으로 선다 - 잔여시간은 줄어드는 순서다', () => {
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[126]}
        events={[ev({ id: 'a', at: 20 }), ev({ id: 'b', at: 150, text: '막판' })]}
        onChange={vi.fn()}
      />,
    )

    // 시각은 읽기 전용 행에서는 텍스트이고 편집 행에서는 입력 값이다.
    const seen = rows().map((r) => {
      const box = within(r).queryByLabelText('남은 시간') as HTMLInputElement | null
      return box ? box.value : (r.textContent ?? '').slice(0, 4)
    })
    expect(seen).toEqual(['3:00', '2:40', '0:54', '0:30', '0:00'])
  })

  it('시각 없는 항목은 「상시」로 맨 아래에 선다', () => {
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[ev({ id: 'always', at: null, text: '잡몹이 계속 나온다' })]}
        onChange={vi.fn()}
      />,
    )

    const last = rows()[rows().length - 1]
    const time = within(last).getByLabelText('남은 시간') as HTMLInputElement
    expect(time.value).toBe('')
    expect(time.placeholder).toBe('상시')
    expect(within(last).getByDisplayValue('잡몹이 계속 나온다')).toBeInTheDocument()
  })

  it('설명을 고치면 그 이벤트만 바뀐 목록을 돌려준다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[ev({ id: 'a', text: '가' }), ev({ id: 'b', at: 40, text: '나' })]}
        onChange={onChange}
      />,
    )

    await user.type(screen.getByDisplayValue('가'), '!')

    expect(onChange).toHaveBeenCalledWith([
      { id: 'a', at: 20, text: '가!' },
      { id: 'b', at: 40, text: '나' },
    ])
  })

  it('시각을 온전히 치면 경과 초로 들어간다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[ev({ id: 'a', at: null, text: '가' })]}
        onChange={onChange}
      />,
    )

    await user.type(screen.getByLabelText('남은 시간'), '2:40')

    expect(onChange).toHaveBeenLastCalledWith([{ id: 'a', at: 20, text: '가' }])
  })

  // 이게 parseRemaining이 null을 주는 이유다 - 반쪽짜리 값에 at을 갱신하면
  // 목록이 정렬돼 있어 행이 튀어 오른다.
  it('치는 중인 시각으로는 at을 건드리지 않는다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[ev({ id: 'a', at: null, text: '가' })]}
        onChange={onChange}
      />,
    )

    await user.type(screen.getByLabelText('남은 시간'), '1:')

    for (const call of onChange.mock.calls) {
      expect(call[0][0].at).toBeNull()
    }
  })

  // 반대쪽: 시각 칸을 비우면 그 이벤트는 「상시」가 된다.
  it('시각을 비우면 상시가 된다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[ev({ id: 'a', at: 20, text: '가' })]}
        onChange={onChange}
      />,
    )

    await user.clear(screen.getByLabelText('남은 시간'))

    expect(onChange).toHaveBeenLastCalledWith([{ id: 'a', at: null, text: '가' }])
  })

  it('이벤트를 더하면 빈 항목이 목록 끝에 붙는다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[ev({ id: 'a' })]}
        onChange={onChange}
      />,
    )

    await user.click(screen.getByRole('button', { name: '이벤트 추가' }))

    const next = onChange.mock.calls[0][0]
    expect(next).toHaveLength(2)
    expect(next[1]).toMatchObject({ at: null, text: '' })
    expect(next[1].id).toBeTruthy()
  })

  it('이벤트를 지우면 그것만 빠진다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <FightTimeline
        fightDuration={180}
        destructionTimes={[]}
        events={[ev({ id: 'a', text: '가' }), ev({ id: 'b', at: 40, text: '나' })]}
        onChange={onChange}
      />,
    )

    const row = rows().find((r) => within(r).queryByDisplayValue('가'))!
    await user.click(within(row).getByRole('button', { name: '삭제' }))

    expect(onChange).toHaveBeenCalledWith([{ id: 'b', at: 40, text: '나' }])
  })

  it('전투 시간을 못 읽으면 아무것도 안 그린다 - 눈금의 기준이 없다', () => {
    const { container } = render(
      <FightTimeline
        fightDuration={Number.NaN}
        destructionTimes={[1]}
        events={[ev()]}
        onChange={vi.fn()}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
