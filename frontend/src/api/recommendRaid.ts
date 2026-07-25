// Typed client for POST /api/recommend-raid. Sets no TIMEOUT - a realistic
// full-roster allocation takes ~1–2 minutes (thousands of 180s simulations),
// per frontend/README.md's latency warning, and a deadline would cut off a run
// that is working fine. It does take a caller's `signal`, which is a different
// thing: the user asking to stop. Dropping the connection also stops the
// SERVER, which reads it as a cancel (backend app/cancellation.py).
//
// `request` is serialized as-is, so the optional `draft` field (frontend/
// README.md "Draft-based raid recommendation") flows through automatically
// whenever a caller includes it — no special-casing needed here.

import type { RecommendRaidRequest, RecommendRaidResponse } from '../types/recommend'
import { RecommendApiError } from './recommendApiError'

export const recommendRaidDecks = async (
  request: RecommendRaidRequest,
  signal?: AbortSignal,
): Promise<RecommendRaidResponse> => {
  const response = await fetch('/api/recommend-raid', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return (await response.json()) as RecommendRaidResponse
}
