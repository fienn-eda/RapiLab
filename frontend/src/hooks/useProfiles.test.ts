import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useProfiles } from './useProfiles'
import type { StoredInputs, StoredResult } from '../types/profile'

const storedResult = (n: number): StoredResult => ({
  decks: [],
  combinedTotalDamage: n,
  excludedSlugs: [],
  leftoverSlugs: [],
  withinDraft: null,
  baselineTotalDamage: null,
})

const storedInputs: StoredInputs = {
  mode: 'raid',
  numDecks: 5,
  boss: { element: null, core_hittable: false, enemy_def: 0, fight_duration: 180, part_destructible: false },
  draft: null,
}

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

  it('saveResult은 활성 프로필의 results/lastResultHash/lastInputs에 반영되고 리렌더에 살아남는다', () => {
    const first = renderHook(() => useProfiles())
    act(() =>
      first.result.current.upsertProfile({ openId: 'A', nickname: '본계', roster: [] }),
    )
    act(() =>
      first.result.current.saveResult({
        openId: 'A',
        hash: 'h1',
        result: storedResult(180),
        inputs: storedInputs,
      }),
    )

    expect(first.result.current.activeProfile?.results.h1).toEqual(storedResult(180))
    expect(first.result.current.activeProfile?.lastResultHash).toBe('h1')
    expect(first.result.current.activeProfile?.lastInputs).toEqual(storedInputs)
    first.unmount()

    const second = renderHook(() => useProfiles())
    expect(second.result.current.activeProfile?.results.h1).toEqual(storedResult(180))
    expect(second.result.current.activeProfile?.lastResultHash).toBe('h1')
  })
})
