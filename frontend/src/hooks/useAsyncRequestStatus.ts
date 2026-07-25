// Shared loading/error bookkeeping for a request/response hook. Extracted
// from useRecommend so useRecommendRaid doesn't duplicate the
// idle/loading/error/success dance; each hook still owns its own result
// state (decks, excluded slugs, ...) and calls run() to drive it.
//
// It also owns cancellation, because that is the same bookkeeping seen from
// the other side: run() hands its callback an AbortSignal, cancel() trips it,
// and the abort that comes back is reported as idle rather than as a failure.
// A recommendation takes one to two minutes, so a player who started one by
// mistake needs a way out - and the backend stops too, since it reads the
// dropped connection as a cancel (see app/cancellation.py).

import { useCallback, useRef, useState } from 'react'
import { describeRecommendApiError, RecommendApiError } from '../api/recommendApiError'

export type RequestStatus = 'idle' | 'loading' | 'error' | 'success'

export interface AsyncRequestStatus {
  status: RequestStatus
  error?: string
  run: <T>(
    fn: (signal: AbortSignal) => Promise<T>,
    onSuccess: (result: T) => void,
    fallbackErrorMessage?: string,
  ) => Promise<void>
  /** Aborts the request in flight, if any. No-op otherwise. */
  cancel: () => void
}

const DEFAULT_FALLBACK_ERROR_MESSAGE = 'Failed to fetch deck recommendations.'

const isAbort = (err: unknown): boolean =>
  err instanceof DOMException ? err.name === 'AbortError' : (err as Error)?.name === 'AbortError'

export const useAsyncRequestStatus = (): AsyncRequestStatus => {
  const [status, setStatus] = useState<RequestStatus>('idle')
  const [error, setError] = useState<string>()
  // Per-run, not per-hook: a cancel pressed during one request must not still
  // be armed when the next one starts.
  const controllerRef = useRef<AbortController | null>(null)

  const run = useCallback(
    async <T>(
      fn: (signal: AbortSignal) => Promise<T>,
      onSuccess: (result: T) => void,
      fallbackErrorMessage: string = DEFAULT_FALLBACK_ERROR_MESSAGE,
    ) => {
      const controller = new AbortController()
      controllerRef.current = controller
      setStatus('loading')
      setError(undefined)
      try {
        const result = await fn(controller.signal)
        onSuccess(result)
        setStatus('success')
      } catch (err) {
        if (isAbort(err)) {
          // The user asked for this. Back to the form, no error to explain.
          setStatus('idle')
          return
        }
        setError(
          err instanceof RecommendApiError
            ? describeRecommendApiError(err)
            : fallbackErrorMessage,
        )
        setStatus('error')
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null
      }
    },
    [],
  )

  const cancel = useCallback(() => controllerRef.current?.abort(), [])

  return { status, error, run, cancel }
}
