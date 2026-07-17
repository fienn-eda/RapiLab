// Typed client for POST /api/recommend-raid. Backed by a dev mock unless
// VITE_RECOMMEND_API=live (frontend/README.md "POST /api/recommend-raid").
// Mirrors recommend.ts: this is the only module that decides which
// implementation runs, so callers never depend on which one is active.

import type { RecommendRaidRequest, RecommendRaidResponse } from '../types/recommend'
import { fetchRecommendRaidDecks } from './recommendRaidClient.live'
import { mockRecommendRaidDecks } from './recommendRaidClient.mock'

const useLiveApi = import.meta.env.VITE_RECOMMEND_API === 'live'

export const recommendRaidDecks = (
  request: RecommendRaidRequest,
): Promise<RecommendRaidResponse> =>
  useLiveApi ? fetchRecommendRaidDecks(request) : mockRecommendRaidDecks(request)
