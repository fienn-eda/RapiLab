import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useEvaluateDecks } from './useEvaluateDecks'
import { RecommendApiError } from '../api/recommendApiError'
import type { EvaluateDecksRequest, EvaluateDecksResponse } from '../types/evaluate'
import type { UserNikkeState } from '../types/userNikkeState'

vi.mock('../api/evaluateDecks', () => ({
  evaluateDecks: vi.fn(),
}))

import { evaluateDecks } from '../api/evaluateDecks'

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 400,
  hp: 1000,
  atk: 1000,
  def_: 1000,
  skill_levels: { skill1: 1, skill2: 1, burst: 1 },
  overload_options: [],
})

const REQUEST: EvaluateDecksRequest = {
  roster: [nikke('liter')],
  decks: [{
    units: ['liter', 'blanc', 'crown', 'modernia', 'privaty'],
    boss: { element: 'Iron', core_hittable: false, pierce_hits_body_behind_core: false, enemy_def: 0, fight_duration: 180, part_destructible: false, effective_range_band: null },
  }],
}

const RESPONSE: EvaluateDecksResponse = {
  decks: [{ deck: ['liter', 'blanc', 'crown', 'modernia', 'privaty'],
            total_damage: 100, burst_damage: 60, normal_attack_damage: 30, skill_damage: 10 }],
  combined_total_damage: 100,
  excluded_slugs: [],
  engine_version: 'abcdef012345',
}

afterEach(() => {
  vi.mocked(evaluateDecks).mockReset()
})

describe('useEvaluateDecks', () => {
  it('성공하면 덱과 합계를 노출한다', async () => {
    vi.mocked(evaluateDecks).mockResolvedValue(RESPONSE)
    const { result } = renderHook(() => useEvaluateDecks())

    await act(async () => { await result.current.submit(REQUEST) })

    await waitFor(() => expect(result.current.status).toBe('success'))
    expect(result.current.combinedTotalDamage).toBe(100)
    expect(result.current.decks).toHaveLength(1)
    expect(result.current.excludedSlugs).toEqual([])
  })

  it('422의 detail을 에러 메시지로 드러낸다', async () => {
    vi.mocked(evaluateDecks).mockRejectedValue(
      new RecommendApiError(422, { detail: '1번 덱은 4명이에요.' }))
    const { result } = renderHook(() => useEvaluateDecks())

    await act(async () => { await result.current.submit(REQUEST) })

    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toContain('1번 덱')
  })
})
