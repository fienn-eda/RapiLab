import { describe, it, expect } from 'vitest'
import { mockRecommendDecks } from './recommendClient.mock'
import { RecommendApiError } from './recommendApiError'
import type { RecommendRequest } from '../types/recommend'
import type { UserNikkeState } from '../types/userNikkeState'

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 200,
  hp: 1_000_000,
  atk: 85_000,
  def_: 12_000,
  skill_levels: { skill1: 10, skill2: 7, burst: 4 },
  overload_options: [],
})

const baseRequest = (overrides: Partial<RecommendRequest> = {}): RecommendRequest => ({
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

describe('mockRecommendDecks', () => {
  it('rejects with a 422 RecommendApiError when the roster has under 5 Nikkes', async () => {
    const request = baseRequest({ roster: ['a', 'b'].map(nikke) })
    await expect(mockRecommendDecks(request)).rejects.toBeInstanceOf(RecommendApiError)
    await mockRecommendDecks(request).catch((err: RecommendApiError) => {
      expect(err.status).toBe(422)
    })
  })

  it('returns decks of exactly 5 slugs each, ranked by descending total_damage', async () => {
    const { decks } = await mockRecommendDecks(baseRequest())
    expect(decks.length).toBeGreaterThan(0)
    for (const deck of decks) {
      expect(deck.deck).toHaveLength(5)
      expect(deck.burst_damage + deck.normal_attack_damage).toBe(deck.total_damage)
    }
    const totals = decks.map((d) => d.total_damage)
    expect(totals).toEqual([...totals].sort((a, b) => b - a))
  })

  it('draws deck slugs from the submitted roster when it has 5+ Nikkes', async () => {
    const request = baseRequest()
    const { decks } = await mockRecommendDecks(request)
    const rosterSlugs = new Set(request.roster.map((n) => n.character_slug))
    for (const deck of decks) {
      for (const slug of deck.deck) {
        expect(rosterSlugs.has(slug)).toBe(true)
      }
    }
  })

  it('caps the number of decks at top_n', async () => {
    const { decks } = await mockRecommendDecks(baseRequest({ top_n: 2 }))
    expect(decks).toHaveLength(2)
  })
})
