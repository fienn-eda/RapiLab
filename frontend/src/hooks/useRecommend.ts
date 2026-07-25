// Owns the request/loading/error/result state for a POST /api/recommend
// submission.

import { useCallback, useState } from 'react'
import { recommendDecks } from '../api/recommend'
import type { DeckRecommendation, RecommendRequest } from '../types/recommend'
import { useAsyncRequestStatus, type RequestStatus } from './useAsyncRequestStatus'

export type RecommendStatus = RequestStatus

export interface RecommendState {
  status: RecommendStatus
  decks: DeckRecommendation[]
  excludedSlugs: string[]
  error?: string
  cancel: () => void
  submit: (request: RecommendRequest) => Promise<void>
}

export const useRecommend = (): RecommendState => {
  const [decks, setDecks] = useState<DeckRecommendation[]>([])
  const [excludedSlugs, setExcludedSlugs] = useState<string[]>([])
  const { status, error, run, cancel } = useAsyncRequestStatus()

  const submit = useCallback(
    (request: RecommendRequest) =>
      run(
        (signal) => recommendDecks(request, signal),
        (response) => {
          setDecks(response.decks)
          setExcludedSlugs(response.excluded_slugs)
        },
      ),
    [run],
  )

  return { status, decks, excludedSlugs, error, submit, cancel }
}
