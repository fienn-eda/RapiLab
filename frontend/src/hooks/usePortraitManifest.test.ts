import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { usePortraitManifest } from './usePortraitManifest'

afterEach(() => {
  vi.unstubAllGlobals()
})

const manifestResponse = (portraits: Record<string, string>) =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ source: 'test', portraits }),
  } as Response)

describe('usePortraitManifest', () => {
  it('resolves a known slug to its prefixed portrait path', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => manifestResponse({ crown: 'crown.webp' })),
    )

    const { result } = renderHook(() => usePortraitManifest())
    await waitFor(() => expect(result.current.portraitFor('crown')).toBe('/portraits/crown.webp'))
  })

  it('returns null for a slug with no manifest entry', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => manifestResponse({ crown: 'crown.webp' })),
    )

    const { result } = renderHook(() => usePortraitManifest())
    await waitFor(() => expect(result.current.portraitFor('crown')).not.toBeNull())
    expect(result.current.portraitFor('unknown-slug')).toBeNull()
  })

  it('returns null for every slug when the manifest fails to load', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('network down'))),
    )

    const { result } = renderHook(() => usePortraitManifest())
    await waitFor(() => expect(result.current.portraitFor('crown')).toBeNull())
  })

  it('returns null for every slug when the manifest is malformed (no portraits key)', async () => {
    const jsonMock = vi.fn(() => Promise.resolve({}))
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve({ ok: true, json: jsonMock } as unknown as Response)),
    )

    const { result } = renderHook(() => usePortraitManifest())
    // Wait for the manifest's .json() to have been consumed, then flush the
    // remaining microtask that applies its (malformed) result to state.
    await waitFor(() => expect(jsonMock).toHaveBeenCalled())
    await Promise.resolve()

    expect(() => result.current.portraitFor('crown')).not.toThrow()
    expect(result.current.portraitFor('crown')).toBeNull()
  })
})
