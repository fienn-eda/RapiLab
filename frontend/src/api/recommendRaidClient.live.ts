// Live client for POST /api/recommend-raid. Deliberately does NOT set a
// fetch timeout/AbortController: a realistic full-roster allocation takes
// ~1–2 minutes (thousands of 180s simulations), per frontend/README.md's
// latency warning. Swap in via VITE_RECOMMEND_API=live; see recommendRaid.ts,
// the only module that chooses between this and the dev mock.

import type { RecommendRaidRequest, RecommendRaidResponse } from '../types/recommend'
import { RecommendApiError } from './recommendApiError'

export const fetchRecommendRaidDecks = async (
  request: RecommendRaidRequest,
): Promise<RecommendRaidResponse> => {
  const response = await fetch('/api/recommend-raid', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return (await response.json()) as RecommendRaidResponse
}
