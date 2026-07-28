// POST /api/evaluate-decks 제출의 요청/로딩/에러/결과 상태. useRecommendRaid와
// 같은 useAsyncRequestStatus 위에 서지만, 결과가 훨씬 얇다 - 평가에는 대안
// 배치도, 남은 유닛도, 잠금도 없다.

import { useCallback, useState } from 'react'
import { evaluateDecks } from '../api/evaluateDecks'
import type { DeckRecommendation } from '../types/recommend'
import type { EvaluateDecksRequest } from '../types/evaluate'
import { useAsyncRequestStatus, type RequestStatus } from './useAsyncRequestStatus'

export interface EvaluateDecksState {
  status: RequestStatus
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  excludedSlugs: string[]
  error?: string
  cancel: () => void
  submit: (request: EvaluateDecksRequest) => Promise<void>
  /** Clears a finished result and returns to idle, with no new run - for a
   * caller leaving evaluate mode (or coming back to it) whose previous
   * result may no longer match the decks on screen (see RecommendPanel's
   * switchMode). */
  reset: () => void
}

const FALLBACK_ERROR_MESSAGE = '기대 딜량을 계산하지 못했어요.'

export const useEvaluateDecks = (): EvaluateDecksState => {
  const [decks, setDecks] = useState<DeckRecommendation[]>([])
  const [combinedTotalDamage, setCombinedTotalDamage] = useState(0)
  const [excludedSlugs, setExcludedSlugs] = useState<string[]>([])
  const { status, error, run, cancel, reset: resetStatus } = useAsyncRequestStatus()

  const submit = useCallback(
    (request: EvaluateDecksRequest) =>
      run(
        (signal) => evaluateDecks(request, signal),
        (response) => {
          setDecks(response.decks)
          setCombinedTotalDamage(response.combined_total_damage)
          setExcludedSlugs(response.excluded_slugs)
        },
        FALLBACK_ERROR_MESSAGE,
      ),
    [run],
  )

  const reset = useCallback(() => {
    resetStatus()
    setDecks([])
    setCombinedTotalDamage(0)
    setExcludedSlugs([])
  }, [resetStatus])

  return { status, decks, combinedTotalDamage, excludedSlugs, error, cancel, submit, reset }
}
