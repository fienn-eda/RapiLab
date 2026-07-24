// Typed client for POST /api/recommend (frontend/README.md "Data contract —
// backend API"). Fetches a RELATIVE path so the Vite dev server proxies it to
// the FastAPI backend on :8000.

import type { RecommendRequest, RecommendResponse } from '../types/recommend'
import { RecommendApiError } from './recommendApiError'

export const recommendDecks = async (
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
