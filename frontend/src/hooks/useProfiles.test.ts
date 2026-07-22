import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useProfiles } from './useProfiles'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useProfiles', () => {
  it('starts empty when nothing was ever saved', () => {
    const { result } = renderHook(() => useProfiles())
    expect(result.current.state).toEqual({ activeOpenId: null, profiles: {} })
  })

  it('legacy nikke-roster를 폐기하고 빈 상태로 시작한다', () => {
    localStorage.setItem('nikke-roster', JSON.stringify([{ character_slug: 'liter' }]))
    const { result } = renderHook(() => useProfiles())
    expect(result.current.state.activeOpenId).toBeNull()
    expect(localStorage.getItem('nikke-roster')).toBeNull()
  })

  it('falls back to an empty state and warns when the stored profiles are corrupt', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    localStorage.setItem('nikke-profiles', '{not json')

    const { result } = renderHook(() => useProfiles())

    expect(result.current.state).toEqual({ activeOpenId: null, profiles: {} })
    expect(warn).toHaveBeenCalledOnce()
  })

  it('upsert/switch/delete는 localStorage(nikke-profiles)에 반영되고 리렌더에 살아남는다', () => {
    const first = renderHook(() => useProfiles())
    act(() =>
      first.result.current.upsertProfile({ openId: 'A', nickname: '본계', roster: [] }),
    )
    act(() =>
      first.result.current.upsertProfile({ openId: 'B', nickname: '부계', roster: [] }),
    )
    act(() => first.result.current.switchProfile('A'))
    first.unmount()

    const second = renderHook(() => useProfiles())
    expect(Object.keys(second.result.current.state.profiles).sort()).toEqual(['A', 'B'])
    expect(second.result.current.state.activeOpenId).toBe('A')
    expect(second.result.current.activeProfile?.openId).toBe('A')

    act(() => second.result.current.deleteProfile('A'))
    expect(second.result.current.state.activeOpenId).toBe('B')
    second.unmount()

    const third = renderHook(() => useProfiles())
    expect(Object.keys(third.result.current.state.profiles)).toEqual(['B'])
  })
})
