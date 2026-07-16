// Typed client for POST /api/recommend. Backed by a dev mock until the real
// endpoint lands (frontend/README.md "Data contract — backend API" — the
// FastAPI endpoint isn't implemented yet). Set VITE_RECOMMEND_API=live to
// swap in the live fetch client; this is the only place that decides which
// implementation runs, so callers never depend on which one is active.

import type { RecommendRequest, RecommendResponse } from '../types/recommend'
import { fetchRecommendDecks } from './recommendClient.live'
import { mockRecommendDecks } from './recommendClient.mock'

const useLiveApi = import.meta.env.VITE_RECOMMEND_API === 'live'

export const recommendDecks = (
  request: RecommendRequest,
): Promise<RecommendResponse> =>
  useLiveApi ? fetchRecommendDecks(request) : mockRecommendDecks(request)
