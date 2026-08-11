// Wire and view shapes for POST /api/charge-window. The backend speaks
// snake_case; everything past the api client speaks camelCase.

/** 사다리가 왜 끝났는가. 행 목록만으로는 구분할 수 없어 백엔드가 알려준다:
 *  'answer' 더 살 수 있는데 살 이유가 없다 · 'ceiling' 오버로드가 모자란다 ·
 *  'charge' 차지가 이미 사라졌다. */
export type LadderStop = 'answer' | 'ceiling' | 'charge'

export interface ShotOutcomeWire {
  low_shots: number
  low_probability: number
  high_shots: number
  high_probability: number
}

export interface ChargeWindowThresholdWire {
  charge_speed_percent: number
  interval: number
  outcome: ShotOutcomeWire
}

export interface ChargeWindowResultWire {
  interval: number
  magazine: number
  charge_speed_percent: number
  charge_speed_ceiling: number
  current: ShotOutcomeWire
  thresholds: ChargeWindowThresholdWire[]
  ladder_stopped_by: LadderStop
  notes: string[]
}

export interface ShotOutcome {
  lowShots: number
  lowProbability: number
  highShots: number
  highProbability: number
}

export interface ChargeWindowThreshold {
  chargeSpeedPercent: number
  interval: number
  outcome: ShotOutcome
}

export interface ChargeWindowResult {
  interval: number
  magazine: number
  chargeSpeedPercent: number
  chargeSpeedCeiling: number
  current: ShotOutcome
  thresholds: ChargeWindowThreshold[]
  ladderStoppedBy: LadderStop
  notes: string[]
}

export interface ChargeWindowRequest {
  slug: string
  roster: unknown[]
  withLiberalio: boolean
  cube: string
  overrides: {
    chargeSpeedLines: number[] | null
    maxAmmoPercent: number | null
    reloadSpeedPercent: number | null
  }
}

export const mapShotOutcome = (wire: ShotOutcomeWire): ShotOutcome => ({
  lowShots: wire.low_shots,
  lowProbability: wire.low_probability,
  highShots: wire.high_shots,
  highProbability: wire.high_probability,
})

export const mapChargeWindowResult = (wire: ChargeWindowResultWire): ChargeWindowResult => ({
  interval: wire.interval,
  magazine: wire.magazine,
  chargeSpeedPercent: wire.charge_speed_percent,
  chargeSpeedCeiling: wire.charge_speed_ceiling,
  current: mapShotOutcome(wire.current),
  thresholds: wire.thresholds.map((row) => ({
    chargeSpeedPercent: row.charge_speed_percent,
    interval: row.interval,
    outcome: mapShotOutcome(row.outcome),
  })),
  ladderStoppedBy: wire.ladder_stopped_by,
  notes: wire.notes,
})
