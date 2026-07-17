import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useRoster } from './useRoster'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useRoster', () => {
  it('restores the roster a previous session saved', () => {
    const first = renderHook(() => useRoster())
    act(() => first.result.current.addNikke())
    act(() =>
      first.result.current.updateNikke(first.result.current.drafts[0].id, {
        ...first.result.current.drafts[0],
        character_slug: 'red-hood',
        atk: '60000',
      }),
    )
    first.unmount()

    const second = renderHook(() => useRoster())

    expect(second.result.current.drafts).toHaveLength(1)
    expect(second.result.current.drafts[0].character_slug).toBe('red-hood')
    expect(second.result.current.drafts[0].atk).toBe('60000')
  })

  it('starts empty when nothing was ever saved', () => {
    const { result } = renderHook(() => useRoster())
    expect(result.current.drafts).toEqual([])
  })

  it('falls back to an empty roster and warns when the stored roster is corrupt', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    localStorage.setItem('nikke-roster', '{not json')

    const { result } = renderHook(() => useRoster())

    expect(result.current.drafts).toEqual([])
    expect(warn).toHaveBeenCalledOnce()
    expect(warn.mock.calls[0][0]).toMatch(/stored roster/i)
  })
})
