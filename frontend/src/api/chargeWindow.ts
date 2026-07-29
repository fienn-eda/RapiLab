// Typed client for POST /api/charge-window - the Full Burst shot-count ladder.

import type { ChargeWindowRequest, ChargeWindowResult, ChargeWindowResultWire } from '../types/chargeWindow'
import { mapChargeWindowResult } from '../types/chargeWindow'
import { RecommendApiError } from './recommendApiError'

export const postChargeWindow = async (
  request: ChargeWindowRequest,
): Promise<ChargeWindowResult> => {
  const response = await fetch('/api/charge-window', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      slug: request.slug,
      roster: request.roster,
      with_liberalio: request.withLiberalio,
      overrides: {
        charge_speed_lines: request.overrides.chargeSpeedLines,
        max_ammo_percent: request.overrides.maxAmmoPercent,
        reload_speed_percent: request.overrides.reloadSpeedPercent,
      },
    }),
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return mapChargeWindowResult((await response.json()) as ChargeWindowResultWire)
}
