// Dev fixture standing in for POST /api/recommend-raid. The real endpoint
// simulates thousands of deck combinations and takes ~1–2 minutes (see
// frontend/README.md), so this mock adds a short artificial delay to keep
// the in-progress UI exercisable without the dev loop actually waiting
// minutes. burst_tier isn't available client-side — it's looked up
// backend-side from character_slug — so this can't derive genuinely feasible
// decks; it partitions the submitted roster's slugs into disjoint 5-slug
// decks so the results UI is exercisable end to end. Swap-in point:
// recommendRaid.ts.

import {
  DEFAULT_NUM_DECKS,
  MIN_DECK_ROSTER_SIZE,
  type DeckRecommendation,
  type RecommendRaidRequest,
  type RecommendRaidResponse,
} from '../types/recommend'
import { RecommendApiError } from './recommendApiError'

const BASE_TOTAL_DAMAGE = 4_200_000
const BURST_SHARE = 0.62
const DECK_DROPOFF = 0.07
const MOCK_DELAY_MS = 1_000

export const mockRecommendRaidDecks = (
  request: RecommendRaidRequest,
): Promise<RecommendRaidResponse> =>
  new Promise((resolve, reject) => {
    setTimeout(() => {
      if (request.roster.length < MIN_DECK_ROSTER_SIZE) {
        reject(
          new RecommendApiError(422, {
            detail: `Roster needs at least ${MIN_DECK_ROSTER_SIZE} Nikkes with burst tiers 1, 2, and 3 present.`,
          }),
        )
        return
      }

      const rosterSlugs = request.roster.map((nikke) => nikke.character_slug)
      const numDecks = request.num_decks ?? DEFAULT_NUM_DECKS
      const allocatable = Math.min(
        numDecks,
        Math.floor(rosterSlugs.length / MIN_DECK_ROSTER_SIZE),
      )

      const decks: DeckRecommendation[] = Array.from({ length: allocatable }, (_, index) => {
        const deck = rosterSlugs.slice(
          index * MIN_DECK_ROSTER_SIZE,
          (index + 1) * MIN_DECK_ROSTER_SIZE,
        )
        const total = Math.round(BASE_TOTAL_DAMAGE * (1 - index * DECK_DROPOFF))
        const burst = Math.round(total * BURST_SHARE)
        return {
          deck,
          total_damage: total,
          burst_damage: burst,
          normal_attack_damage: total - burst,
        }
      })

      const allocatedSlugs = new Set(decks.flatMap((deck) => deck.deck))
      const leftoverSlugs = rosterSlugs.filter((slug) => !allocatedSlugs.has(slug)).sort()

      resolve({
        decks,
        combined_total_damage: decks.reduce((sum, deck) => sum + deck.total_damage, 0),
        excluded_slugs: [],
        leftover_slugs: leftoverSlugs,
      })
    }, MOCK_DELAY_MS)
  })
