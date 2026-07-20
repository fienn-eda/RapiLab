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

  it('imports drafts, preserving manual fields on a matching slug and persisting', () => {
    const first = renderHook(() => useRoster())
    act(() => first.result.current.addNikke())
    act(() =>
      first.result.current.updateNikke(first.result.current.drafts[0].id, {
        ...first.result.current.drafts[0],
        character_slug: 'rapi-red-hood',
        atk: '60000',
        skill_levels: { skill1: '1', skill2: '1', burst: '1' },
      }),
    )

    let summary = { added: -1, updated: -1 }
    act(() => {
      summary = first.result.current.importDrafts([
        {
          ...first.result.current.drafts[0],
          id: 'ignored-incoming-id',
          atk: '',
          skill_levels: { skill1: '10', skill2: '10', burst: '10' },
        },
        {
          ...first.result.current.drafts[0],
          id: 'new-one',
          character_slug: 'crown',
        },
      ])
    })

    expect(summary).toEqual({ added: 1, updated: 1 })
    const rapi = first.result.current.drafts.find(
      (d) => d.character_slug === 'rapi-red-hood',
    )!
    expect(rapi.atk).toBe('60000') // manual field preserved
    expect(rapi.skill_levels.skill1).toBe('10') // import field overwritten
    first.unmount()

    // persisted across a reload
    const second = renderHook(() => useRoster())
    expect(
      second.result.current.drafts.map((d) => d.character_slug).sort(),
    ).toEqual(['crown', 'rapi-red-hood'])
  })

  it('loads a stored roster saved before core_level was removed', () => {
    // useRoster JSON.parses whatever is in localStorage; a stale extra key must
    // be ignored, not throw or blank the roster.
    localStorage.setItem(
      'nikke-roster',
      JSON.stringify([
        {
          id: 'a',
          character_slug: 'rapi-red-hood',
          core_level: '7',
          level: '400',
          hp: '1',
          atk: '2',
          def_: '0',
          actualHp: '',
          actualAtk: '',
          actualDef: '',
          skill_levels: { skill1: '1', skill2: '1', burst: '1' },
          overload_options: [],
        },
      ]),
    )
    const { result } = renderHook(() => useRoster())
    expect(result.current.drafts).toHaveLength(1)
    expect(result.current.drafts[0].character_slug).toBe('rapi-red-hood')
    localStorage.clear()
  })
})
