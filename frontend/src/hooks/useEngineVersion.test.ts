import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useEngineVersion } from './useEngineVersion'

vi.mock('../api/engineVersion', () => ({
  fetchEngineVersion: vi.fn(),
}))

import { fetchEngineVersion } from '../api/engineVersion'

afterEach(() => {
  vi.mocked(fetchEngineVersion).mockReset()
})

describe('useEngineVersion', () => {
  it('가져오기 전에는 null이고, 도착하면 버전을 준다', async () => {
    vi.mocked(fetchEngineVersion).mockResolvedValue('abcdef012345')
    const { result } = renderHook(() => useEngineVersion())

    expect(result.current).toBeNull()
    await waitFor(() => expect(result.current).toBe('abcdef012345'))
  })

  it('가져오기가 실패해도 null로 남고 던지지 않는다', async () => {
    vi.mocked(fetchEngineVersion).mockRejectedValue(new Error('offline'))
    const { result } = renderHook(() => useEngineVersion())

    await waitFor(() => expect(result.current).toBeNull())
  })
})
