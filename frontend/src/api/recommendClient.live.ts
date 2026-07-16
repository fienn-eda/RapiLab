// Live client for POST /api/recommend. Not wired to a running backend yet —
// the endpoint isn't implemented (see frontend/README.md "Data contract —
// backend API"). Swap in via VITE_RECOMMEND_API=live once it lands; see
// recommend.ts, the only module that chooses between this and the dev mock.

import type { RecommendRequest, RecommendResponse } from '../types/recommend'
import { RecommendApiError } from './recommendApiError'

export const fetchRecommendDecks = async (
  request: RecommendRequest,
): Promise<RecommendResponse> => {
  const response = await fetch('/api/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  return (await response.json()) as RecommendResponse
}
