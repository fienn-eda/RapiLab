// Owns the request/loading/error/result state for a POST /api/recommend-raid
// submission. Mirrors useRecommend, sharing its loading/error bookkeeping via
// useAsyncRequestStatus — the result shape differs (a partition of decks plus
// a combined total and leftover slugs, not a ranked list).

import { useCallback, useState } from 'react'
import { recommendRaidDecks } from '../api/recommendRaid'
import type { DeckRecommendation, RecommendRaidRequest } from '../types/recommend'
import { useAsyncRequestStatus, type RequestStatus } from './useAsyncRequestStatus'

export type RecommendRaidStatus = RequestStatus

export interface RecommendRaidState {
  status: RecommendRaidStatus
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  excludedSlugs: string[]
  leftoverSlugs: string[]
  error?: string
  submit: (request: RecommendRaidRequest) => Promise<void>
}

const FALLBACK_ERROR_MESSAGE = 'Failed to fetch raid deck allocation.'

export const useRecommendRaid = (): RecommendRaidState => {
  const [decks, setDecks] = useState<DeckRecommendation[]>([])
  const [combinedTotalDamage, setCombinedTotalDamage] = useState(0)
  const [excludedSlugs, setExcludedSlugs] = useState<string[]>([])
  const [leftoverSlugs, setLeftoverSlugs] = useState<string[]>([])
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
        },
        FALLBACK_ERROR_MESSAGE,
      ),
    [run],
  )

  return { status, decks, combinedTotalDamage, excludedSlugs, leftoverSlugs, error, submit }
}
