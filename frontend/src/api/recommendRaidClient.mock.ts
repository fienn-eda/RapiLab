// Dev fixture standing in for POST /api/recommend-raid. The real endpoint
// simulates thousands of deck combinations and takes ~1–2 minutes (see
// frontend/README.md), so this mock adds a short artificial delay to keep
// the in-progress UI exercisable without the dev loop actually waiting
// minutes. burst_tier isn't available client-side — it's looked up
// backend-side from character_slug — so this can't derive genuinely feasible
// decks; it partitions the submitted roster's slugs into disjoint 5-slug
// decks so the results UI is exercisable end to end.
//
// Draft support is similarly approximate: a locked draft slug is marked
// pinned wherever the partition happens to place it (real allocation always
// keeps a locked slug in ITS drafted deck; this mock doesn't reproduce that,
// it only needs to exercise the pinned_slugs/within_draft/baseline_total_damage
// UI plumbing in dev). For a COMPLETE draft (frontend/README.md "Draft-based
// raid recommendation"), within_draft/baseline_total_damage are populated
// with deterministically ascending numbers so the monotone guarantee
// (baseline <= within_draft <= recommended) always holds. Swap-in point:
// recommendRaid.ts.

import {
  DEFAULT_NUM_DECKS,
  MIN_DECK_ROSTER_SIZE,
  type DraftAllocation,
  type DraftDeck,
  type RaidDeck,
  type RecommendRaidRequest,
  type RecommendRaidResponse,
} from '../types/recommend'
import { RecommendApiError } from './recommendApiError'

const BASE_TOTAL_DAMAGE = 4_200_000
const BURST_SHARE = 0.62
const DECK_DROPOFF = 0.07
const MOCK_DELAY_MS = 1_000
// Tier bumps so baseline <= within_draft <= recommended holds by construction.
const WITHIN_DRAFT_BUMP = 1.05
const BASELINE_DROP = 1 / (WITHIN_DRAFT_BUMP * 1.05)

const isCompleteDraft = (draft: DraftDeck[] | undefined, numDecks: number): draft is DraftDeck[] =>
  !!draft &&
  draft.length === numDecks &&
  draft.every((deck) => deck.units.length === MIN_DECK_ROSTER_SIZE)

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

      const lockedSlugs = new Set(
        (request.draft ?? []).flatMap((deck) =>
          deck.units.filter((unit) => unit.locked).map((unit) => unit.slug),
        ),
      )

      const decks: RaidDeck[] = Array.from({ length: allocatable }, (_, index) => {
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
          pinned_slugs: deck.filter((slug) => lockedSlugs.has(slug)),
        }
      })

      const allocatedSlugs = new Set(decks.flatMap((deck) => deck.deck))
      const leftoverSlugs = rosterSlugs.filter((slug) => !allocatedSlugs.has(slug)).sort()
      const combinedTotalDamage = decks.reduce((sum, deck) => sum + deck.total_damage, 0)

      let withinDraft: DraftAllocation | null = null
      let baselineTotalDamage: number | null = null
      if (isCompleteDraft(request.draft, numDecks)) {
        const withinTotal = Math.round(combinedTotalDamage / WITHIN_DRAFT_BUMP)
        const perDeck = Math.round(withinTotal / request.draft.length)
        const withinDecks: RaidDeck[] = request.draft.map((deck) => {
          const burst = Math.round(perDeck * BURST_SHARE)
          const slugs = deck.units.map((unit) => unit.slug)
          return {
            deck: slugs,
            total_damage: perDeck,
            burst_damage: burst,
            normal_attack_damage: perDeck - burst,
            pinned_slugs: slugs.filter((slug) => lockedSlugs.has(slug)),
          }
        })
        withinDraft = {
          decks: withinDecks,
          combined_total_damage: withinDecks.reduce((sum, deck) => sum + deck.total_damage, 0),
          leftover_slugs: [],
        }
        baselineTotalDamage = Math.round(withinDraft.combined_total_damage * BASELINE_DROP)
      }

      resolve({
        decks,
        combined_total_damage: combinedTotalDamage,
        excluded_slugs: [],
        leftover_slugs: leftoverSlugs,
        within_draft: withinDraft,
        baseline_total_damage: baselineTotalDamage,
      })
    }, MOCK_DELAY_MS)
  })
