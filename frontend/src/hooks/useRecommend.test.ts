import { describe, it, expect, vi, afterEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useRecommend } from './useRecommend'
import { RecommendApiError } from '../api/recommendApiError'
import type { RecommendRequest } from '../types/recommend'

vi.mock('../api/recommend', () => ({
  recommendDecks: vi.fn(),
}))

import { recommendDecks } from '../api/recommend'

const request: RecommendRequest = {
  roster: [],
  boss: {
    element: null,
    core_hittable: false,
    enemy_def: 0,
    fight_duration: 180,
    part_destructible: false,
  },
}

afterEach(() => {
  vi.mocked(recommendDecks).mockReset()
})

describe('useRecommend', () => {
  it('starts idle', () => {
    const { result } = renderHook(() => useRecommend())
    expect(result.current.status).toBe('idle')
    expect(result.current.decks).toEqual([])
  })

  it('goes loading -> success and stores the returned decks', async () => {
    const decks = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0 },
    ]
    vi.mocked(recommendDecks).mockResolvedValue({ decks, excluded_slugs: [], engine_version: 'test-engine-version' })

    const { result } = renderHook(() => useRecommend())
    act(() => {
      void result.current.submit(request)
    })
    expect(result.current.status).toBe('loading')

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.decks).toEqual(decks)
    expect(result.current.error).toBeUndefined()
  })

  it('exposes the excluded slugs the backend reports', async () => {
    const decks = [
      { deck: ['a', 'b', 'c', 'd', 'e'], total_damage: 100, burst_damage: 60, normal_attack_damage: 40, skill_damage: 0 },
    ]
    vi.mocked(recommendDecks).mockResolvedValue({ decks, excluded_slugs: ['some-slug'], engine_version: 'test-engine-version' })

    const { result } = renderHook(() => useRecommend())
    act(() => {
      void result.current.submit(request)
    })

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.excludedSlugs).toEqual(['some-slug'])
  })

  it('goes loading -> error and describes a RecommendApiError', async () => {
    vi.mocked(recommendDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: 'No feasible deck.' }),
    )

    const { result } = renderHook(() => useRecommend())
    act(() => {
      void result.current.submit(request)
    })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toBe('No feasible deck.')
    expect(result.current.decks).toEqual([])
  })

  it('falls back to a generic message for a non-RecommendApiError failure', async () => {
    vi.mocked(recommendDecks).mockRejectedValue(new Error('network down'))

    const { result } = renderHook(() => useRecommend())
    act(() => {
      void result.current.submit(request)
    })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toBe('덱 추천을 가져오지 못했어요.')
  })
})
