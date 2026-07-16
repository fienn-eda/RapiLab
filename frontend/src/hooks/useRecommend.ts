// Owns the request/loading/error/result state for a POST /api/recommend
// submission.

import { useCallback, useState } from 'react'
import { recommendDecks } from '../api/recommend'
import { describeRecommendApiError, RecommendApiError } from '../api/recommendApiError'
import type { DeckRecommendation, RecommendRequest } from '../types/recommend'

export type RecommendStatus = 'idle' | 'loading' | 'error' | 'success'

export interface RecommendState {
  status: RecommendStatus
  decks: DeckRecommendation[]
  error?: string
  submit: (request: RecommendRequest) => Promise<void>
}

export const useRecommend = (): RecommendState => {
  const [status, setStatus] = useState<RecommendStatus>('idle')
  const [decks, setDecks] = useState<DeckRecommendation[]>([])
  const [error, setError] = useState<string>()

  const submit = useCallback(async (request: RecommendRequest) => {
    setStatus('loading')
    setError(undefined)
    try {
      const response = await recommendDecks(request)
      setDecks(response.decks)
      setStatus('success')
    } catch (err) {
      setError(
        err instanceof RecommendApiError
          ? describeRecommendApiError(err)
          : 'Failed to fetch deck recommendations.',
      )
      setStatus('error')
    }
  }, [])

  return { status, decks, error, submit }
}
