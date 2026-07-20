import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mockRecommendRaidDecks } from './recommendRaidClient.mock'
import { RecommendApiError } from './recommendApiError'
import type { RecommendRaidRequest } from '../types/recommend'
import type { UserNikkeState } from '../types/userNikkeState'

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 200,
  core_level: 7,
  hp: 1_000_000,
  atk: 85_000,
  def_: 12_000,
  skill_levels: { skill1: 10, skill2: 7, burst: 4 },
  overload_options: [],
})

const baseRequest = (overrides: Partial<RecommendRaidRequest> = {}): RecommendRaidRequest => ({
  roster: ['a', 'b', 'c', 'd', 'e'].map(nikke),
  boss: {
    element: null,
    core_hittable: false,
    enemy_def: 0,
    fight_duration: 180,
    part_destructible: false,
  },
  ...overrides,
})

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('mockRecommendRaidDecks', () => {
  it('rejects with a 422 RecommendApiError when the roster has under 5 Nikkes', async () => {
    const request = baseRequest({ roster: ['a', 'b'].map(nikke) })
    const promise = mockRecommendRaidDecks(request)
    const expectation = expect(promise).rejects.toBeInstanceOf(RecommendApiError)
    await vi.runAllTimersAsync()
    await expectation
  })

  it('partitions the roster into disjoint decks of exactly 5 slugs each', async () => {
    const request = baseRequest({
      roster: Array.from({ length: 15 }, (_, i) => nikke(`slug-${i}`)),
      num_decks: 5,
    })
    const promise = mockRecommendRaidDecks(request)
    await vi.runAllTimersAsync()
    const { decks, combined_total_damage } = await promise

    expect(decks).toHaveLength(3)
    const seenSlugs = new Set<string>()
    let sum = 0
    for (const deck of decks) {
      expect(deck.deck).toHaveLength(5)
      expect(deck.burst_damage + deck.normal_attack_damage).toBe(deck.total_damage)
      for (const slug of deck.deck) {
        expect(seenSlugs.has(slug)).toBe(false) // decks are disjoint
        seenSlugs.add(slug)
      }
      sum += deck.total_damage
    }
    expect(combined_total_damage).toBe(sum)
  })

  it('caps the number of decks at num_decks even when the roster could fill more', async () => {
    const request = baseRequest({
      roster: Array.from({ length: 15 }, (_, i) => nikke(`slug-${i}`)),
      num_decks: 2,
    })
    const promise = mockRecommendRaidDecks(request)
    await vi.runAllTimersAsync()
    const { decks } = await promise
    expect(decks).toHaveLength(2)
  })

  it('lists units left out of every deck as leftover_slugs, sorted', async () => {
    const request = baseRequest({
      roster: ['z', 'a', 'm', 'b', 'c', 'd', 'e'].map(nikke),
      num_decks: 1,
    })
    const promise = mockRecommendRaidDecks(request)
    await vi.runAllTimersAsync()
    const { decks, leftover_slugs } = await promise
    expect(decks).toHaveLength(1)
    expect(decks[0].deck).toEqual(['z', 'a', 'm', 'b', 'c'])
    expect(leftover_slugs).toEqual(['d', 'e'])
  })

  it('defaults num_decks to 5 when omitted', async () => {
    const request = baseRequest({
      roster: Array.from({ length: 30 }, (_, i) => nikke(`slug-${i}`)),
    })
    const promise = mockRecommendRaidDecks(request)
    await vi.runAllTimersAsync()
    const { decks } = await promise
    expect(decks).toHaveLength(5)
  })
})
