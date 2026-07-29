// Wire and view shapes for POST /api/charge-window. The backend speaks
// snake_case; everything past the api client speaks camelCase.

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
  current: ShotOutcomeWire
  thresholds: ChargeWindowThresholdWire[]
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
  current: ShotOutcome
  thresholds: ChargeWindowThreshold[]
  notes: string[]
}

export interface ChargeWindowRequest {
  slug: string
  roster: unknown[]
  withLiberalio: boolean
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
  current: mapShotOutcome(wire.current),
  thresholds: wire.thresholds.map((row) => ({
    chargeSpeedPercent: row.charge_speed_percent,
    interval: row.interval,
    outcome: mapShotOutcome(row.outcome),
  })),
  notes: wire.notes,
})
