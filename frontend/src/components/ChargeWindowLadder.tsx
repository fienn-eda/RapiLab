// The charge-speed ladder: one row per step that actually changes the cadence,
// with the row the player currently sits on marked.
//
// Both shot counts are shown with their probabilities rather than a single
// number, because the phase the Full Burst window opens at is not the player's
// to choose and it decides the last shot.

import type { ChargeWindowResult, ShotOutcome } from '../types/chargeWindow'

const percent = (ratio: number) => `${(ratio * 100).toFixed(2)}%`
const odds = (ratio: number) => `${Math.round(ratio * 100)}%`

const describeOutcome = (outcome: ShotOutcome) => {
  if (outcome.highProbability <= 0) return `${outcome.lowShots}타`
  return `${outcome.highShots}타 ${odds(outcome.highProbability)} / ${outcome.lowShots}타 ${odds(outcome.lowProbability)}`
}

export function ChargeWindowLadder({ result }: { result: ChargeWindowResult }) {
  // The highest step the current total already pays for. Steps are sorted
  // ascending, so the last one at or below the total is the live row.
  let currentIndex = 0
  result.thresholds.forEach((row, index) => {
    if (row.chargeSpeedPercent <= result.chargeSpeedPercent + 1e-9) currentIndex = index
  })
  const next = result.thresholds[currentIndex + 1]
  const gap = next ? next.chargeSpeedPercent - result.chargeSpeedPercent : null

  return (
    <div className="charge-ladder">
      <p className="charge-ladder__summary">
        탄창 {result.magazine}발 · 발당 {result.interval.toFixed(4)}초 · 현재 차지속도{' '}
        {percent(result.chargeSpeedPercent)}
      </p>
      <table className="charge-ladder__table">
        <thead>
          <tr>
            <th scope="col">차지속도</th>
            <th scope="col">간격</th>
            <th scope="col">타수</th>
          </tr>
        </thead>
        <tbody>
          {result.thresholds.map((row, index) => (
            <tr
              key={row.chargeSpeedPercent}
              data-testid={index === currentIndex ? 'ladder-row-current' : undefined}
              className={index === currentIndex ? 'charge-ladder__row--current' : undefined}
            >
              <td>{percent(row.chargeSpeedPercent)}</td>
              <td>{row.interval.toFixed(4)}초</td>
              <td>{describeOutcome(row.outcome)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="charge-ladder__next">
        {gap === null
          ? '더 올릴 구간이 없습니다 — 차지가 이미 사라졌습니다.'
          : `다음 구간까지 ${(gap * 100).toFixed(2)}%p 남았습니다.`}
      </p>
      {result.notes.length > 0 && (
        <ul className="charge-ladder__notes">
          {result.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
