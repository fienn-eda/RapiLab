import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useRaidRotations } from './useRaidRotations'

const wire = {
  schema_version: 1,
  rotations: [
    {
      id: 'solo-39',
      raid: 'solo',
      title: '솔로 레이드 39시즌',
      starts_at: null,
      ends_at: '2026-07-23T04:59:00+09:00',
      source_url: 'https://example.test',
      source_locale: 'ko',
      read_on: '2026-08-07',
      bosses: [{ name: '아일랜드 이터', weakness: 'Iron', stated: {} }],
    },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useRaidRotations', () => {
  it('회차 목록을 실어 온다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => wire,
    }))
    const { result } = renderHook(() => useRaidRotations())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.rotations.map((r) => r.id)).toEqual(['solo-39'])
  })

  it('실패하면 빈 목록으로 끝난다', async () => {
    // 회차 데이터가 없으면 피커가 안 그려질 뿐이고 보스 설정은 손으로 다 된다.
    // 배너를 띄울 만한 실패가 아니다.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const { result } = renderHook(() => useRaidRotations())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.rotations).toEqual([])
  })
})
