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
    expect(result.current.state).toEqual({ activeKey: null, profiles: {} })
  })

  it('legacy nikke-roster를 폐기하고 빈 상태로 시작한다', () => {
    localStorage.setItem('nikke-roster', JSON.stringify([{ character_slug: 'liter' }]))
    const { result } = renderHook(() => useProfiles())
    expect(result.current.state.activeKey).toBeNull()
    expect(localStorage.getItem('nikke-roster')).toBeNull()
  })

  it('falls back to an empty state and warns when the stored profiles are corrupt', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    localStorage.setItem('nikke-profiles', '{not json')

    const { result } = renderHook(() => useProfiles())

    expect(result.current.state).toEqual({ activeKey: null, profiles: {} })
    expect(warn).toHaveBeenCalledOnce()
  })

  it('upsert/switch/delete는 localStorage(nikke-profiles)에 반영되고 리렌더에 살아남는다', () => {
    const first = renderHook(() => useProfiles())
    act(() =>
      first.result.current.upsertProfile({ openId: 'A', area: 81, nickname: '본계', roster: [] }),
    )
    act(() =>
      first.result.current.upsertProfile({ openId: 'B', area: 81, nickname: '부계', roster: [] }),
    )
    act(() => first.result.current.switchProfile('A:81'))
    first.unmount()

    const second = renderHook(() => useProfiles())
    expect(Object.keys(second.result.current.state.profiles).sort()).toEqual(['A:81', 'B:81'])
    expect(second.result.current.state.activeKey).toBe('A:81')
    expect(second.result.current.activeProfile?.openId).toBe('A')

    act(() => second.result.current.deleteProfile('A:81'))
    expect(second.result.current.state.activeKey).toBe('B:81')
    second.unmount()

    const third = renderHook(() => useProfiles())
    expect(Object.keys(third.result.current.state.profiles)).toEqual(['B:81'])
  })

  it('saveResult은 활성 프로필의 results/lastResultHash/lastInputs에 반영되고 리렌더에 살아남는다', () => {
    const first = renderHook(() => useProfiles())
    act(() =>
      first.result.current.upsertProfile({ openId: 'A', area: 81, nickname: '본계', roster: [] }),
    )
    act(() =>
      first.result.current.saveResult({
        key: 'A:81',
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

  it('구 스키마(open_id만 키)를 area 81 프로필로 옮긴다', () => {
    localStorage.setItem(
      'nikke-profiles',
      JSON.stringify({
        activeOpenId: '111111',
        profiles: {
          '111111': {
            openId: '111111',
            nickname: 'FIENN',
            roster: [],
            results: {},
            lastResultHash: null,
            lastInputs: null,
          },
        },
      }),
    )

    const { result } = renderHook(() => useProfiles())

    expect(Object.keys(result.current.state.profiles)).toEqual(['111111:81'])
    expect(result.current.state.activeKey).toBe('111111:81')
    expect(result.current.state.profiles['111111:81'].area).toBe(81)
  })

  it('구·신 스키마가 섞인 저장소도 두 프로필 모두 area를 갖고 살아남는다', () => {
    // area 없는 bare-key 항목 하나와 이미 복합 키인 항목 하나가 한 스토어에
    // 섞인 경우 - 이 코드는 실제로 만들 수 없지만(도달 불가), 유저 브라우저의
    // localStorage 위에서 도는 함수라 안전망으로 검증해 둔다. 스토어 전체를
    // "신 스키마"로 단정해 통째로 통과시키던 예전 코드였다면 bare-key 항목은
    // area 없이, 키도 그대로 남았을 것이다.
    localStorage.setItem(
      'nikke-profiles',
      JSON.stringify({
        activeKey: '222222:83',
        profiles: {
          '111111': {
            openId: '111111',
            nickname: 'LEGACY',
            roster: [],
            results: {},
            lastResultHash: null,
            lastInputs: null,
          },
          '222222:83': {
            openId: '222222',
            area: 83,
            nickname: 'NEW',
            roster: [],
            results: {},
            lastResultHash: null,
            lastInputs: null,
          },
        },
      }),
    )

    const { result } = renderHook(() => useProfiles())

    expect(Object.keys(result.current.state.profiles).sort()).toEqual(['111111:81', '222222:83'])
    expect(result.current.state.profiles['111111:81'].area).toBe(81)
    expect(result.current.state.profiles['222222:83'].area).toBe(83)
    expect(result.current.state.activeKey).toBe('222222:83')
  })

  it('이미 새 스키마면 그대로 둔다', () => {
    localStorage.setItem(
      'nikke-profiles',
      JSON.stringify({
        activeKey: '111111:83',
        profiles: {
          '111111:83': {
            openId: '111111',
            area: 83,
            nickname: 'FIENN',
            roster: [],
            results: {},
            lastResultHash: null,
            lastInputs: null,
          },
        },
      }),
    )

    const { result } = renderHook(() => useProfiles())

    expect(Object.keys(result.current.state.profiles)).toEqual(['111111:83'])
    expect(result.current.state.activeKey).toBe('111111:83')
  })
})
