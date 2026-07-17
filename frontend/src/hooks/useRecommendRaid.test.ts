import { describe, it, expect, vi, afterEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useRecommendRaid } from './useRecommendRaid'
import { RecommendApiError } from '../api/recommendApiError'
import type { RecommendRaidRequest } from '../types/recommend'

vi.mock('../api/recommendRaid', () => ({
  recommendRaidDecks: vi.fn(),
}))

import { recommendRaidDecks } from '../api/recommendRaid'

const request: RecommendRaidRequest = {
  roster: [],
  boss: {
    element: null,
    core_hittable: false,
    enemy_def: 0,
    fight_duration: 180,
    part_destructible: false,
  },
  num_decks: 3,
}

afterEach(() => {
  vi.mocked(recommendRaidDecks).mockReset()
})

describe('useRecommendRaid', () => {
  it('starts idle', () => {
    const { result } = renderHook(() => useRecommendRaid())
    expect(result.current.status).toBe('idle')
    expect(result.current.decks).toEqual([])
    expect(result.current.combinedTotalDamage).toBe(0)
  })

  it('goes loading -> success and stores the allocation', async () => {
    const decks = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40 },
      { deck: ['f', 'g', 'h', 'i', 'j'], total_damage: 80, burst_damage: 50, normal_attack_damage: 30 },
    ]
    vi.mocked(recommendRaidDecks).mockResolvedValue({
      decks,
      combined_total_damage: 180,
      excluded_slugs: ['some-slug'],
      leftover_slugs: ['k', 'l'],
    })

    const { result } = renderHook(() => useRecommendRaid())
    act(() => {
      void result.current.submit(request)
    })
    expect(result.current.status).toBe('loading')

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.decks).toEqual(decks)
    expect(result.current.combinedTotalDamage).toBe(180)
    expect(result.current.excludedSlugs).toEqual(['some-slug'])
    expect(result.current.leftoverSlugs).toEqual(['k', 'l'])
    expect(result.current.error).toBeUndefined()
  })

  it('goes loading -> error and describes a RecommendApiError', async () => {
    vi.mocked(recommendRaidDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: 'No feasible deck.' }),
    )

    const { result } = renderHook(() => useRecommendRaid())
    act(() => {
      void result.current.submit(request)
    })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toBe('No feasible deck.')
    expect(result.current.decks).toEqual([])
  })

  it('falls back to a raid-specific generic message for a non-RecommendApiError failure', async () => {
    vi.mocked(recommendRaidDecks).mockRejectedValue(new Error('network down'))

    const { result } = renderHook(() => useRecommendRaid())
    act(() => {
      void result.current.submit(request)
    })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toBe('Failed to fetch raid deck allocation.')
  })
})
