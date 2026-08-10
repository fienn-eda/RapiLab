// The charge-speed ladder: one row per step that actually changes the cadence,
// with the row the player currently sits on marked.
//
// Both shot counts are shown with their probabilities rather than a single
// number, because the phase the Full Burst window opens at is not the player's
// to choose and it decides the last shot.

import { HELP } from '../lib/helpText'
import type { ChargeWindowResult, ShotOutcome } from '../types/chargeWindow'
import { HelpText } from './HelpText'
import { HelpTip } from './HelpTip'

const percent = (ratio: number) => `${(ratio * 100).toFixed(2)}%`
const odds = (ratio: number) => `${Math.round(ratio * 100)}%`

const describeOutcome = (outcome: ShotOutcome) => {
  if (outcome.highProbability <= 0) return `${outcome.lowShots}타`
  return `${outcome.highShots}타 ${odds(outcome.highProbability)} / ${outcome.lowShots}타 ${odds(outcome.lowProbability)}`
}

// What to say under the ladder. A ladder that ends can end for three different
// reasons and they call for different advice: the frame grid runs to 100%, so a
// last row short of it means overload ran out first - unless the reader's own
// total already carried the ladder past that ceiling, in which case blaming the
// ceiling would contradict the rows above it.
const closingLine = (result: ChargeWindowResult, gap: number | null): string => {
  if (gap !== null) return HELP.charge.ladderGap(gap * 100)
  const last = result.thresholds[result.thresholds.length - 1]
  if (last === undefined || last.chargeSpeedPercent >= 1) {
    return HELP.charge.ladderChargeGone
  }
  if (last.chargeSpeedPercent <= result.chargeSpeedCeiling + 1e-9) {
    return HELP.charge.ladderCeiling(percent(result.chargeSpeedCeiling))
  }
  return HELP.charge.ladderAtLast
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
    <div>
      <p className="charge-ladder__summary">
        탄창 {result.magazine}발 · 발당 {result.interval.toFixed(4)}초 · 현재 차지속도{' '}
        {percent(result.chargeSpeedPercent)}
      </p>
      {/* Only the table is inside the scroll container. A help bubble is
          absolutely positioned and a scroll container clips both axes, so
          anything with one has to sit outside this wrapper. */}
      <div className="charge-ladder">
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
      </div>
      <p className="charge-ladder__next"><HelpText>{closingLine(result, gap)}</HelpText></p>
      {/* The count stays in the open because it is the part that has to be
          noticed; the reasoning behind each is read once. */}
      {result.notes.length > 0 && (
        <p className="charge-ladder__notes">
          알아둘 점 {result.notes.length}개{' '}
          <HelpTip label="알아둘 점">
            {result.notes.map((note) => (
              <span className="charge-ladder__note" key={note}>{note}</span>
            ))}
          </HelpTip>
        </p>
      )}
    </div>
  )
}
