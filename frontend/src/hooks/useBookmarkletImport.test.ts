import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useBookmarkletImport } from './useBookmarkletImport'
import { BLABLALINK_ORIGIN, PAYLOAD_MESSAGE } from '../lib/bookmarklet'
import { assembleRoster } from '../api/assembleRoster'

// 이 코드베이스의 모킹 관례는 vi.mock + vi.mocked다 (RecommendPanel.test.tsx 참고).
// ESM 명명 export는 vi.spyOn으로 가로챌 수 없다.
vi.mock('../api/assembleRoster', () => ({
  assembleRoster: vi.fn(),
}))

const EMPTY = { owned: [], character_details: [], recycle_room_researches: [] }

const post = (origin: string, data: unknown) =>
  window.dispatchEvent(new MessageEvent('message', { origin, data }))

afterEach(() => vi.mocked(assembleRoster).mockReset())

describe('useBookmarkletImport', () => {
  it('blablalink에서 온 payload를 조립해 넘긴다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))

    post(BLABLALINK_ORIGIN, { type: PAYLOAD_MESSAGE, payload: EMPTY })

    await waitFor(() => expect(onRoster).toHaveBeenCalledWith({ units: [] }))
  })

  it('다른 출처의 메시지는 무시한다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))

    post('https://evil.example', { type: PAYLOAD_MESSAGE, payload: EMPTY })

    await new Promise((r) => setTimeout(r, 10))
    expect(assembleRoster).not.toHaveBeenCalled()
    expect(onRoster).not.toHaveBeenCalled()
  })

  it('조립 실패는 error 상태로 드러난다', async () => {
    vi.mocked(assembleRoster).mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useBookmarkletImport(vi.fn()))

    post(BLABLALINK_ORIGIN, { type: PAYLOAD_MESSAGE, payload: EMPTY })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toContain('boom')
  })

  it('onRoster가 매 렌더마다 새로 생겨도 리스너/ready 신호는 마운트당 한 번만 등록한다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const opener = { postMessage: vi.fn() }
    window.opener = opener as unknown as Window
    const addSpy = vi.spyOn(window, 'addEventListener')
    const messageListenerCount = () =>
      addSpy.mock.calls.filter((call) => call[0] === 'message').length

    // SyncRosterPanel(Task 9)처럼 onRoster를 인라인 화살표로 넘기는 소비자를
    // 흉내낸다 - 렌더마다 새 함수 참조가 onRoster로 들어온다.
    let received: unknown = null
    const { rerender } = renderHook(
      ({ tag }: { tag: number }) =>
        useBookmarkletImport((raw: unknown) => {
          received = { tag, raw }
        }),
      { initialProps: { tag: 1 } },
    )

    expect(messageListenerCount()).toBe(1)
    expect(opener.postMessage).toHaveBeenCalledTimes(1)

    rerender({ tag: 2 })
    rerender({ tag: 3 })
    rerender({ tag: 4 })

    expect(messageListenerCount()).toBe(1)
    expect(opener.postMessage).toHaveBeenCalledTimes(1)

    post(BLABLALINK_ORIGIN, { type: PAYLOAD_MESSAGE, payload: EMPTY })

    await waitFor(() =>
      expect(received).toEqual({ tag: 4, raw: { units: [] } }),
    )

    addSpy.mockRestore()
    window.opener = null as unknown as Window
  })
})
