// 인박스 폴링 경로. 네이티브 창에는 북마크릿의 postMessage가 닿지 않으므로
// 앱에서 실제로 로스터가 들어오는 길은 이쪽이다.

import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useBookmarkletImport } from './useBookmarkletImport'
import { assembleRoster } from '../api/assembleRoster'
import { takeSyncInbox } from '../api/syncInbox'

vi.mock('../api/assembleRoster', () => ({ assembleRoster: vi.fn() }))
vi.mock('../api/syncInbox', () => ({ takeSyncInbox: vi.fn() }))

const payload = (area = 81, count = 2) => ({
  open_id: '123456',
  servers: [{
    area,
    nickname: 'fienn',
    owned: Array.from({ length: count }, (_, i) => ({ name_code: i + 1 })),
    character_details: [],
    recycle_room_researches: [],
  }],
})

beforeEach(() => {
  vi.mocked(takeSyncInbox).mockResolvedValue(null)
  vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
})
afterEach(() => {
  vi.mocked(takeSyncInbox).mockReset()
  vi.mocked(assembleRoster).mockReset()
})

describe('인박스 폴링', () => {
  it('마운트하자마자 한 번 확인한다 - 주기를 기다리지 않는다', async () => {
    // 유저는 북마크릿을 누르고 앱으로 돌아온다. 그 시점에 이미 인박스에 있다.
    renderHook(() => useBookmarkletImport(vi.fn()))
    await waitFor(() => expect(takeSyncInbox).toHaveBeenCalled())
  })

  it('인박스에 있던 로스터를 조립해 넘긴다', async () => {
    vi.mocked(takeSyncInbox).mockResolvedValueOnce(payload())
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))
    await waitFor(() => expect(assembleRoster).toHaveBeenCalled())
    await waitFor(() => expect(onRoster).toHaveBeenCalled())
  })

  it('비어 있으면 아무 일도 하지 않는다', async () => {
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))
    await waitFor(() => expect(takeSyncInbox).toHaveBeenCalled())
    expect(assembleRoster).not.toHaveBeenCalled()
    expect(onRoster).not.toHaveBeenCalled()
  })

  it('서버가 없어도 조용히 넘어간다', async () => {
    // 개발 중 백엔드를 안 띄웠을 수 있다. 화면에 에러를 띄울 일이 아니다.
    vi.mocked(takeSyncInbox).mockRejectedValue(new Error('failed to fetch'))
    const { result } = renderHook(() => useBookmarkletImport(vi.fn()))
    await waitFor(() => expect(takeSyncInbox).toHaveBeenCalled())
    expect(result.current.status).toBe('idle')
    expect(result.current.error).toBeNull()
  })

  it('동기화를 마친 뒤에도 다음 계정을 집어온다', async () => {
    // 계정이 여러 개인 유저는 북마크를 연달아 누른다. 한 번 동기화한 뒤
    // 폴링이 멈추면 두 번째 계정은 인박스에 놓인 채 앱에 닿지 못한다.
    vi.mocked(takeSyncInbox)
      .mockResolvedValueOnce(payload())
      .mockResolvedValueOnce({ ...payload(), open_id: '999999' })
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))
    await waitFor(() => expect(onRoster).toHaveBeenCalledTimes(2))
    expect(onRoster.mock.calls[1][0].openId).toBe('999999')
  })

  it('후보를 고르는 중에는 더 집어오지 않는다', async () => {
    // 유저가 서버를 고르는 동안 새 payload가 끼어들면 방금 누른 것과 다른
    // 로스터가 들어온다.
    vi.mocked(takeSyncInbox).mockResolvedValueOnce({
      open_id: '123456',
      servers: [payload(81).servers[0], payload(83).servers[0]],
    })
    const { result } = renderHook(() => useBookmarkletImport(vi.fn()))
    await waitFor(() => expect(result.current.status).toBe('choosing'))
    const callsWhileChoosing = vi.mocked(takeSyncInbox).mock.calls.length
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(vi.mocked(takeSyncInbox).mock.calls.length).toBe(callsWhileChoosing)
  })
})
