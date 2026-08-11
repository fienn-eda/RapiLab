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

// What to say under the ladder. A ladder that ends can end for different
// reasons and they call for different advice, so the backend names the reason
// (`ladder_stopped_by`) rather than letting this guess from the rows: a last
// row short of the ceiling means "overload ran out" and "the answer settled
// first" alike, and only the frame grid can tell those apart.
const closingLine = (result: ChargeWindowResult, gap: number | null): string => {
  if (gap !== null) return HELP.charge.ladderGap(gap * 100)
  const last = result.thresholds[result.thresholds.length - 1]
  // 차지가 남지 않은 것이 가장 강한 이유다 - 상한도 답도 그 앞에서는 할 말이 없다.
  if (last === undefined || result.ladderStoppedBy === 'charge') {
    return HELP.charge.ladderChargeGone
  }
  // 읽는 사람의 합계가 이미 상한을 넘겨 사다리를 끌고 갔다면, 상한을 탓하는
  // 말은 위 행들과 모순된다.
  if (last.chargeSpeedPercent > result.chargeSpeedCeiling + 1e-9) {
    return HELP.charge.ladderAtLast
  }
  if (result.ladderStoppedBy === 'answer') return HELP.charge.ladderAnswerSettled
  return HELP.charge.ladderCeiling(percent(result.chargeSpeedCeiling))
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
              {/* 차지 시간이 아니라 평타 하나에서 다음 평타까지다 - 차지·모션
                  딜레이·재장전이 모두 든 값이라 이름이 그것을 말해야 한다. */}
              <th scope="col">평타 간격</th>
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
