// Shared loading/error bookkeeping for a request/response hook. Extracted
// from useRecommend so useRecommendRaid doesn't duplicate the
// idle/loading/error/success dance; each hook still owns its own result
// state (decks, excluded slugs, ...) and calls run() to drive it.

import { useCallback, useState } from 'react'
import { describeRecommendApiError, RecommendApiError } from '../api/recommendApiError'

export type RequestStatus = 'idle' | 'loading' | 'error' | 'success'

export interface AsyncRequestStatus {
  status: RequestStatus
  error?: string
  run: <T>(
    fn: () => Promise<T>,
    onSuccess: (result: T) => void,
    fallbackErrorMessage?: string,
  ) => Promise<void>
}

const DEFAULT_FALLBACK_ERROR_MESSAGE = 'Failed to fetch deck recommendations.'

export const useAsyncRequestStatus = (): AsyncRequestStatus => {
  const [status, setStatus] = useState<RequestStatus>('idle')
  const [error, setError] = useState<string>()

  const run = useCallback(
    async <T>(
      fn: () => Promise<T>,
      onSuccess: (result: T) => void,
      fallbackErrorMessage: string = DEFAULT_FALLBACK_ERROR_MESSAGE,
    ) => {
      setStatus('loading')
      setError(undefined)
      try {
        const result = await fn()
        onSuccess(result)
        setStatus('success')
      } catch (err) {
        setError(
          err instanceof RecommendApiError
            ? describeRecommendApiError(err)
            : fallbackErrorMessage,
        )
        setStatus('error')
      }
    },
    [],
  )

  return { status, error, run }
}
