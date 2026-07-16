// Request/response types for POST /api/recommend.
// SOURCE OF TRUTH: backend/app/deck_search.py (BossProfile, find_best_decks)
// and frontend/README.md "Data contract — backend API". Keep in sync; never
// edit the Python. The endpoint itself isn't implemented yet — see
// src/api/recommend.ts for the dev-mock client that stands in for it.

import type { UserNikkeState } from './userNikkeState'

export type BossElement = 'Fire' | 'Water' | 'Wind' | 'Iron' | 'Electric' | null

export const BOSS_ELEMENTS: Exclude<BossElement, null>[] = [
  'Fire',
  'Water',
  'Wind',
  'Iron',
  'Electric',
]

export interface BossProfile {
  element: BossElement // null = non-elemental
  core_hittable: boolean // default false
  enemy_def: number // default 0
  fight_duration: number // seconds, default 180
  // gauge_charge_time and mode also exist on the backend BossProfile but are
  // left to backend defaults and not surfaced here (per the README contract).
}

export interface RecommendRequest {
  roster: UserNikkeState[] // needs a feasible 5-unit deck: burst tiers 1, 2, 3 all present
  boss: BossProfile
  top_n?: number // optional, default 5
}

export interface DeckRecommendation {
  deck: string[] // 5 character slugs, ordered by burst role (B1 -> B2 -> B3)
  total_damage: number
  burst_damage: number
  normal_attack_damage: number
}

export interface RecommendResponse {
  decks: DeckRecommendation[] // ranked by total_damage desc, length <= top_n
}

// A deck needs 5 Nikkes. This is necessary but NOT sufficient for a feasible
// deck — feasibility also requires burst tiers 1, 2, and 3 all present, which
// depends on burst_tier metadata that's only looked up backend-side from
// character_slug (not part of UserNikkeState). The client can only guard on
// roster size; the backend still returns 422 for a roster that has 5+ Nikkes
// but can't cover all three burst tiers.
export const MIN_DECK_ROSTER_SIZE = 5
