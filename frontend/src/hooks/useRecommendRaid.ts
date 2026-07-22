// Owns the request/loading/error/result state for a POST /api/recommend-raid
// submission. Mirrors useRecommend, sharing its loading/error bookkeeping via
// useAsyncRequestStatus — the result shape differs (a partition of decks plus
// a combined total and leftover slugs, not a ranked list).

import { useCallback, useState } from 'react'
import { recommendRaidDecks } from '../api/recommendRaid'
import type { DraftAllocation, RaidDeck, RecommendRaidRequest } from '../types/recommend'
import { useAsyncRequestStatus, type RequestStatus } from './useAsyncRequestStatus'

export type RecommendRaidStatus = RequestStatus

export interface RecommendRaidState {
  status: RecommendRaidStatus
  decks: RaidDeck[]
  combinedTotalDamage: number
  excludedSlugs: string[]
  leftoverSlugs: string[]
  /** Non-null only when the submitted draft was complete — see recommend.ts's RecommendRaidResponse. */
  withinDraft: DraftAllocation | null
  baselineTotalDamage: number | null
  error?: string
  submit: (request: RecommendRaidRequest) => Promise<void>
}

const FALLBACK_ERROR_MESSAGE = 'Failed to fetch raid deck allocation.'

export const useRecommendRaid = (): RecommendRaidState => {
  const [decks, setDecks] = useState<RaidDeck[]>([])
  const [combinedTotalDamage, setCombinedTotalDamage] = useState(0)
  const [excludedSlugs, setExcludedSlugs] = useState<string[]>([])
  const [leftoverSlugs, setLeftoverSlugs] = useState<string[]>([])
  const [withinDraft, setWithinDraft] = useState<DraftAllocation | null>(null)
  const [baselineTotalDamage, setBaselineTotalDamage] = useState<number | null>(null)
  const { status, error, run } = useAsyncRequestStatus()

  const submit = useCallback(
    (request: RecommendRaidRequest) =>
      run(
        () => recommendRaidDecks(request),
        (response) => {
          setDecks(response.decks)
          setCombinedTotalDamage(response.combined_total_damage)
          setExcludedSlugs(response.excluded_slugs)
          setLeftoverSlugs(response.leftover_slugs)
          setWithinDraft(response.within_draft)
          setBaselineTotalDamage(response.baseline_total_damage)
        },
        FALLBACK_ERROR_MESSAGE,
      ),
    [run],
  )

  return {
    status,
    decks,
    combinedTotalDamage,
    excludedSlugs,
    leftoverSlugs,
    withinDraft,
    baselineTotalDamage,
    error,
    submit,
  }
}
