// Typed client for POST /api/miranda-targets - who receives Miranda's two
// top-ATK buffs, and what overload ATK would change that.

import type { MirandaTargetsResult, MirandaTargetsResultWire } from '../types/mirandaTargets'
import { mapMirandaTargetsResult } from '../types/mirandaTargets'
import { RecommendApiError } from './recommendApiError'

export interface MirandaTargetsRequest {
  roster: unknown[]
  units: string[]
}

export const postMirandaTargets = async (
  request: MirandaTargetsRequest,
): Promise<MirandaTargetsResult> => {
  const response = await fetch('/api/miranda-targets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ roster: request.roster, units: request.units }),
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return mapMirandaTargetsResult((await response.json()) as MirandaTargetsResultWire)
}
