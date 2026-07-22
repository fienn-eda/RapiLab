import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useSupportedUnits } from './useSupportedUnits'

vi.mock('../api/supportedUnits', () => ({
  getSupportedUnits: vi.fn(),
}))

import { getSupportedUnits } from '../api/supportedUnits'

afterEach(() => {
  vi.mocked(getSupportedUnits).mockReset()
})

describe('useSupportedUnits', () => {
  it('starts loading and exposes the mapped units on success', async () => {
    const units = [
      { slug: 'crown', name: 'Crown', burstTier: 1 as const, element: 'Iron' as const },
    ]
    vi.mocked(getSupportedUnits).mockResolvedValue(units)

    const { result } = renderHook(() => useSupportedUnits())
    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.units).toEqual(units)
    expect(result.current.error).toBeUndefined()
  })

  it('exposes an error message when the request fails', async () => {
    vi.mocked(getSupportedUnits).mockRejectedValue(new Error('network down'))

    const { result } = renderHook(() => useSupportedUnits())

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.units).toEqual([])
    expect(result.current.error).toBe('Failed to load supported units.')
  })
})
