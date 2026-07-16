// Dev fixture standing in for POST /api/recommend until the backend
// implements the endpoint (see frontend/README.md "Data contract — backend
// API"). burst_tier isn't available client-side — it's looked up
// backend-side from character_slug — so this can't derive genuinely feasible
// decks; it produces plausible-looking ranked decks (using the submitted
// roster's slugs where there are enough of them) so the results UI is
// exercisable end to end. Swap-in point: recommend.ts.

import {
  MIN_DECK_ROSTER_SIZE,
  type DeckRecommendation,
  type RecommendRequest,
  type RecommendResponse,
} from '../types/recommend'
import { RecommendApiError } from './recommendApiError'

const FALLBACK_SLUGS = ['red-hood', 'liter', 'blanc', 'noir', 'anne', 'mast', 'privaty']

const BASE_TOTAL_DAMAGE = 4_200_000
const BURST_SHARE = 0.62
const RANK_DROPOFF = 0.07
const DEFAULT_TOP_N = 5

export const mockRecommendDecks = (
  request: RecommendRequest,
): Promise<RecommendResponse> => {
  if (request.roster.length < MIN_DECK_ROSTER_SIZE) {
    return Promise.reject(
      new RecommendApiError(422, {
        detail: `Roster needs at least ${MIN_DECK_ROSTER_SIZE} Nikkes with burst tiers 1, 2, and 3 present.`,
      }),
    )
  }

  const rosterSlugs = request.roster.map((nikke) => nikke.character_slug)
  const pool = rosterSlugs.length >= MIN_DECK_ROSTER_SIZE ? rosterSlugs : FALLBACK_SLUGS
  const topN = request.top_n ?? DEFAULT_TOP_N

  const decks: DeckRecommendation[] = Array.from(
    { length: Math.min(topN, pool.length) },
    (_, rank) => {
      const deck = Array.from(
        { length: MIN_DECK_ROSTER_SIZE },
        (_, slot) => pool[(rank + slot) % pool.length],
      )
      const total = Math.round(BASE_TOTAL_DAMAGE * (1 - rank * RANK_DROPOFF))
      const burst = Math.round(total * BURST_SHARE)
      return {
        deck,
        total_damage: total,
        burst_damage: burst,
        normal_attack_damage: total - burst,
      }
    },
  )

  return Promise.resolve({ decks })
}
