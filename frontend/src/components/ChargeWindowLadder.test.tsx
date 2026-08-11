import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ChargeWindowLadder } from './ChargeWindowLadder'
import { HELP } from '../lib/helpText'
import type { ChargeWindowResult } from '../types/chargeWindow'

const outcome = (low: number, high: number, highProbability: number) => ({
  lowShots: low, lowProbability: 1 - highProbability,
  highShots: high, highProbability,
})

const RESULT: ChargeWindowResult = {
  interval: 0.53,
  magazine: 22,
  chargeSpeedPercent: 0,
  chargeSpeedCeiling: 0.24,
  current: outcome(18, 19, 0.868),
  thresholds: [
    { chargeSpeedPercent: 0, interval: 0.53, outcome: outcome(18, 19, 0.868) },
    { chargeSpeedPercent: 0.0556, interval: 0.5133, outcome: outcome(19, 20, 0.481) },
    { chargeSpeedPercent: 0.1111, interval: 0.4967, outcome: outcome(20, 21, 0.134) },
  ],
  // 이 픽스처는 마지막 행이 상한 한참 아래이고, 백엔드가 "오버로드가 모자라
  // 잘렸다"고 말한 경우다. 행 목록만으로는 이것과 "답이 먼저 멈췄다"를 구분할
  // 수 없어 백엔드가 이유를 실어준다.
  ladderStoppedBy: 'ceiling',
  notes: ['탄창이 창 안에서 비어 재장전이 걸립니다'],
}

describe('ChargeWindowLadder', () => {
  it('renders one row per threshold', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    expect(screen.getAllByRole('row')).toHaveLength(RESULT.thresholds.length + 1)
  })

  it('marks the row the current charge speed sits on', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    const current = screen.getByTestId('ladder-row-current')
    expect(within(current).getByText(/0\.00%/)).toBeInTheDocument()
  })

  it('marks the highest step at or below the current charge speed', () => {
    render(<ChargeWindowLadder result={{ ...RESULT, chargeSpeedPercent: 0.09 }} />)
    // 9% buys the 5.56% step but not the 11.11% one.
    const current = screen.getByTestId('ladder-row-current')
    expect(within(current).getByText(/5\.56%/)).toBeInTheDocument()
  })

  it('shows both shot counts with their probabilities', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    const current = screen.getByTestId('ladder-row-current')
    expect(within(current).getByText(/19타 87%/)).toBeInTheDocument()
    expect(within(current).getByText(/18타 13%/)).toBeInTheDocument()
  })

  it('reports how much more charge speed the next step costs', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    expect(screen.getByText(/5\.56%p/)).toBeInTheDocument()
  })

  it('counts the notes in the open and keeps their text behind hover help', () => {
    // Four judged notes of two or three lines each buried the ladder they were
    // about. Vitest runs with `test.css: false`, so what is actually collapsed
    // can only be pinned as structure: the prose lives inside the tip's bubble.
    render(<ChargeWindowLadder result={{ ...RESULT, notes: ['재장전이 걸립니다', '최대장탄이 막고 있습니다'] }} />)
    expect(screen.getByText(/알아둘 점 2개/)).toBeInTheDocument()
    const bubble = screen.getByRole('tooltip')
    expect(within(bubble).getByText('재장전이 걸립니다')).toBeInTheDocument()
    expect(within(bubble).getByText('최대장탄이 막고 있습니다')).toBeInTheDocument()
  })

  it('says nothing at all when there is nothing to note', () => {
    render(<ChargeWindowLadder result={{ ...RESULT, notes: [] }} />)
    expect(screen.queryByText(/알아둘 점/)).not.toBeInTheDocument()
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  // The bubble is absolutely positioned, and `.charge-ladder { overflow-x:
  // auto }` would clip it - a scroll container clips both axes. So the scroll
  // wrapper has to hug the table and nothing else.
  it('keeps the hover bubble outside the table scroll container', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    expect(screen.getByRole('tooltip').closest('.charge-ladder')).toBeNull()
  })

  // App.css's `.charge-ladder { overflow-x: auto; }` contains the table's
  // horizontal scroll to this wrapper instead of the page body. Vitest runs
  // with `test.css: false` (vite.config.ts), so computed style can't be
  // asserted here - this pins the DOM side of that contract: the table must
  // stay inside the exact wrapper class the stylesheet targets.
  it('wraps the table in the container the CSS scroll-containment rule targets', () => {
    render(<ChargeWindowLadder result={RESULT} />)
    expect(screen.getByRole('table').closest('.charge-ladder')).not.toBeNull()
  })

  it('names the overload ceiling as the reason the ladder ends', () => {
    // The last row is well short of the frame grid's end, so the ladder stopped
    // because overload did - not because the charge ran out.
    const topped = { ...RESULT, chargeSpeedPercent: 0.1111 }
    render(<ChargeWindowLadder result={topped} />)
    expect(screen.getByText(HELP.charge.ladderCeiling('24.00%'))).toBeInTheDocument()
  })

  it('does not blame the ceiling for a ladder that ran past it', () => {
    // A total above the ceiling extends the ladder to keep its own row, so the
    // last row is no longer what overload could buy.
    const past = {
      ...RESULT,
      chargeSpeedPercent: 0.37,
      thresholds: [...RESULT.thresholds,
                   { chargeSpeedPercent: 0.3333, interval: 0.4389, outcome: outcome(19, 20, 0.24) }],
    }
    render(<ChargeWindowLadder result={past} />)
    expect(screen.queryByText(/오버로드 상한/)).not.toBeInTheDocument()
    expect(screen.getByText(HELP.charge.ladderAtLast)).toBeInTheDocument()
  })

  it('says the charge is gone when the ladder ran out of frames instead', () => {
    const spent = {
      ...RESULT,
      chargeSpeedPercent: 1,
      chargeSpeedCeiling: 0.24,
      ladderStoppedBy: 'charge' as const,
      thresholds: [...RESULT.thresholds,
                   { chargeSpeedPercent: 1, interval: 0.43, outcome: outcome(23, 23, 0) }],
    }
    render(<ChargeWindowLadder result={spent} />)
    expect(screen.getByText(HELP.charge.ladderChargeGone)).toBeInTheDocument()
  })

  it('상한이 남았는데 답이 먼저 멈췄으면 상한을 탓하지 않는다', () => {
    // 탄창이 타수를 막으면 오버로드는 아직 살 수 있는데도 살 이유가 없다.
    // 그때 "상한까지만 보여줍니다"는 거짓이다 - 상한은 멀쩡히 남아 있다.
    const settled = {
      ...RESULT,
      chargeSpeedPercent: 0.1111,
      ladderStoppedBy: 'answer' as const,
    }
    render(<ChargeWindowLadder result={settled} />)

    expect(screen.getByText(HELP.charge.ladderAnswerSettled)).toBeInTheDocument()
    expect(screen.queryByText(/오버로드 상한/)).not.toBeInTheDocument()
  })
})
