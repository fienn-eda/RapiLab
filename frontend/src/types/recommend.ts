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

export type BossRangeBand = 'near' | 'mid' | 'far' | null

export const BOSS_RANGE_BANDS: Exclude<BossRangeBand, null>[] = ['near', 'mid', 'far']

export interface BossProfile {
  element: BossElement // null = non-elemental
  core_hittable: boolean // default false
  enemy_def: number // default 0
  fight_duration: number // seconds, default 180
  part_destructible: boolean // default false — boss has a part-destruction gimmick;
  // selects the ceiling (max-potential) model for units whose kit depends on
  // part destruction (e.g. Ark Ranger Black), false = floor (lower-bound) model.
  effective_range_band: BossRangeBand // default null — how far away the boss is
  // fought. The band decides WHICH weapons are inside their effective range and
  // collect +0.30 on their normal attacks: near pays SG/SMG, mid pays AR/MG, far
  // pays SR, and a Rocket Launcher is paid by none. null = unknown, pays nobody.
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
  // Everything that was neither a burst nor a normal attack — DoTs, per-shot
  // riders, self-cooldowned procs. The three add up to total_damage.
  skill_damage: number
}

export interface RecommendResponse {
  decks: DeckRecommendation[] // ranked by total_damage desc, length <= top_n
  excluded_slugs: string[] // submitted slugs the backend can't evaluate yet (not encoded / no data); shown as "not yet supported"
  // 이 결과를 낸 엔진의 버전 — 결과 캐시의 무효화 축(lib/inputHash.ts).
  engine_version: string
}

// A deck needs 5 Nikkes. This is necessary but NOT sufficient for a feasible
// deck — feasibility also requires burst tiers 1, 2, and 3 all present, which
// depends on burst_tier metadata that's only looked up backend-side from
// character_slug (not part of UserNikkeState). The client can only guard on
// roster size; the backend still returns 422 for a roster that has 5+ Nikkes
// but can't cover all three burst tiers.
export const MIN_DECK_ROSTER_SIZE = 5

// POST /api/recommend-raid: splits the roster into up to num_decks DISJOINT
// decks against one boss and maximizes their summed damage. Semantically
// different from /api/recommend — that endpoint ranks alternatives for ONE
// deck; this one returns a partition the player fields all at once (no Nikke
// appears in two decks).
// Draft-based raid seeding (frontend/README.md "Draft-based raid
// recommendation"): the player seeds decks with key units and the engine
// fills/optimizes the rest. Membership only — seat position is NOT burst
// order, the engine assigns it. This is the WIRE shape POST
// /api/recommend-raid expects; the editor's own state shape lives in
// types/draft.ts (DraftEditor.tsx's toRequestDraft converts between them).
export interface DraftUnit {
  slug: string
  locked: boolean // default false; true = engine must keep this unit in this deck
}

export interface DraftDeck {
  units: DraftUnit[] // 0..5 units
}

export interface RecommendRaidRequest {
  roster: UserNikkeState[]
  boss: BossProfile
  num_decks?: number // int, 1–5, default 5
  draft?: DraftDeck[] // optional; omitted or [] = zero-base behavior (no draft seeding)
}

// A raid deck additionally reports which of its slugs were pinned by the
// caller's draft (locked units the engine kept) — a draft-only concept, not
// part of the shared DeckRecommendation shape /api/recommend also uses.
export interface RaidDeck extends DeckRecommendation {
  pinned_slugs: string[]
}

// The best allocation using ONLY the drafted units (no bench) — present only
// when the submitted draft is COMPLETE (draft.length === num_decks and every
// drafted deck has exactly 5 units).
export interface DraftAllocation {
  decks: RaidDeck[]
  combined_total_damage: number
  leftover_slugs: string[]
}

export interface RecommendRaidResponse {
  decks: RaidDeck[] // one entry per allocated deck, in allocation
  // order (NOT ranked alternatives) — may be fewer than num_decks when the
  // roster can't fill more feasible decks; this is the bench-inclusive
  // RECOMMENDED tier
  combined_total_damage: number // sum over decks
  excluded_slugs: string[] // same meaning as /api/recommend
  leftover_slugs: string[] // usable units the allocation left out (sorted)
  within_draft: DraftAllocation | null // non-null only for a COMPLETE draft
  baseline_total_damage: number | null // the user's exact drafted groupings scored;
  // non-null only for a COMPLETE draft. Monotone guarantee (complete draft):
  // baseline_total_damage <= sum(within_draft.decks.total_damage) <= combined_total_damage
  // 이 결과를 낸 엔진의 버전 — 결과 캐시의 무효화 축(lib/inputHash.ts).
  engine_version: string
}

export const MIN_NUM_DECKS = 1
export const MAX_NUM_DECKS = 5
export const DEFAULT_NUM_DECKS = 5
