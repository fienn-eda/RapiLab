import { describe, it, expect } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useAsyncRequestStatus } from './useAsyncRequestStatus'

/** Rejects the way fetch does when its signal is aborted. */
const abortError = () => {
  const err = new Error('The operation was aborted.')
  err.name = 'AbortError'
  return err
}

describe('useAsyncRequestStatus', () => {
  it('reports success and hands the result to the caller', async () => {
    const { result } = renderHook(() => useAsyncRequestStatus())
    const seen: string[] = []

    await act(async () => {
      await result.current.run(async () => 'ok', (r) => seen.push(r))
    })

    expect(result.current.status).toBe('success')
    expect(seen).toEqual(['ok'])
  })

  it('reports an error with a message', async () => {
    const { result } = renderHook(() => useAsyncRequestStatus())

    await act(async () => {
      await result.current.run(
        async () => {
          throw new Error('boom')
        },
        () => {},
        'could not fetch',
      )
    })

    expect(result.current.status).toBe('error')
    expect(result.current.error).toBe('could not fetch')
  })

  // A cancel is something the user did, not something that went wrong. Showing
  // "덱 추천을 가져오지 못했어요." for it would read as a bug in the
  // app and send them looking for a problem that does not exist.
  it('treats an aborted request as idle, not as a failure', async () => {
    const { result } = renderHook(() => useAsyncRequestStatus())

    await act(async () => {
      await result.current.run(
        async () => {
          throw abortError()
        },
        () => {},
      )
    })

    expect(result.current.status).toBe('idle')
    expect(result.current.error).toBeUndefined()
  })

  it('hands the running request a signal that cancel() aborts', async () => {
    const { result } = renderHook(() => useAsyncRequestStatus())
    let seen: AbortSignal | undefined

    await act(async () => {
      const running = result.current.run(
        (signal) => {
          seen = signal
          return new Promise((_, reject) => {
            signal.addEventListener('abort', () => reject(abortError()))
          })
        },
        () => {},
      )
      result.current.cancel()
      await running
    })

    expect(seen?.aborted).toBe(true)
    expect(result.current.status).toBe('idle')
  })

  it('does not abort a later request with an earlier request\'s cancel', async () => {
    // Each run gets its own controller; otherwise a cancel pressed during run
    // #1 would still be armed when run #2 starts.
    const { result } = renderHook(() => useAsyncRequestStatus())

    await act(async () => {
      await result.current.run(async () => 'first', () => {})
    })
    act(() => result.current.cancel())

    await act(async () => {
      await result.current.run(async (signal) => {
        expect(signal.aborted).toBe(false)
        return 'second'
      }, () => {})
    })

    expect(result.current.status).toBe('success')
  })
})
