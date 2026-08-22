import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useVersions } from './useVersions'

vi.mock('../api/versions', () => ({
  fetchVersions: vi.fn(),
}))

import { fetchVersions } from '../api/versions'

afterEach(() => {
  vi.mocked(fetchVersions).mockReset()
})

describe('useVersions', () => {
  it('가져오기 전에는 둘 다 null이고, 도착하면 채워진다', async () => {
    vi.mocked(fetchVersions).mockResolvedValue({
      engineVersion: 'abcdef012345',
      appVersion: 'v0.1.5',
    })
    const { result } = renderHook(() => useVersions())

    expect(result.current).toEqual({ engineVersion: null, appVersion: null })
    await waitFor(() =>
      expect(result.current).toEqual({
        engineVersion: 'abcdef012345',
        appVersion: 'v0.1.5',
      }),
    )
  })

  it('가져오기가 실패해도 null로 남고 던지지 않는다', async () => {
    vi.mocked(fetchVersions).mockRejectedValue(new Error('offline'))
    const { result } = renderHook(() => useVersions())

    await waitFor(() =>
      expect(result.current).toEqual({ engineVersion: null, appVersion: null }),
    )
  })

  // 개발 실행에는 릴리스 태그가 없다. 엔진 버전은 왔는데 앱 버전만 null인 이 상태가
  // 정상이고, 진단에는 「(개발 빌드)」로 적힌다 - 엔진 버전까지 버리면 안 된다.
  it('릴리스 태그가 없는 빌드여도 엔진 버전은 살린다', async () => {
    vi.mocked(fetchVersions).mockResolvedValue({
      engineVersion: 'abcdef012345',
      appVersion: null,
    })
    const { result } = renderHook(() => useVersions())

    await waitFor(() => expect(result.current.engineVersion).toBe('abcdef012345'))
    expect(result.current.appVersion).toBeNull()
  })
})
