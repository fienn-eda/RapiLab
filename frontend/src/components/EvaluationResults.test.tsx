import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvaluationResults } from './EvaluationResults'
import type { BossProfile } from '../types/recommend'

const DECKS = [
  { deck: ['liter', 'blanc', 'crown', 'modernia', 'privaty'],
    total_damage: 100, burst_damage: 60, normal_attack_damage: 30, skill_damage: 10, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {} },
  { deck: ['rouge', 'volume', 'mint', 'grave', 'noir'],
    total_damage: 50, burst_damage: 30, normal_attack_damage: 15, skill_damage: 5, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {} },
]

const boss = (overrides: Partial<BossProfile> = {}): BossProfile => ({
  element: null,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: 31784,
  fight_duration: 180,
  part_destructible: false,
  part_destruction_times: [],
  core_diameter_px: null,
  effective_range_band: null,
  elemental_interrupt_required: false,
  ...overrides,
})

const renderResults = (overrides = {}) =>
  render(<EvaluationResults
    decks={DECKS}
    combinedTotalDamage={150}
    bosses={[boss({ element: 'Iron' }), boss({ element: 'Water' })]}
    nameFor={(slug) => slug}
    {...overrides} />)

const DECK = {
  deck: ['a', 'b', 'c', 'd', 'e'],
  total_damage: 1000,
  burst_damage: 500,
  normal_attack_damage: 400,
  skill_damage: 100, hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [], partial_charge_full_rounds: {}, seating: {},
}

describe('EvaluationResults', () => {
  it('덱마다 카드를 그리고 합계를 보여준다', () => {
    renderResults()
    // The composed label ("N번 덱 · 속성") is this component's own output,
    // not DeckCard's internal markup — counting matches of it proves one
    // card per deck without coupling to a CSS class this component doesn't own.
    expect(screen.getAllByText(/\d번 덱 · /)).toHaveLength(2)
    expect(screen.getByText(/150/)).toBeTruthy()
  })

  it('덱마다 자기 보스 속성을 표시한다 (자리와 짝이 맞다)', () => {
    // Exact composed text, not a substring match, so this fails if the
    // element/deck pairing is transposed, reversed, or off-by-one.
    renderResults()
    expect(screen.getByText('1번 덱 · 약점 풍압')).toBeTruthy()
    expect(screen.getByText('2번 덱 · 약점 전격')).toBeTruthy()
  })

  it('엔진이 고른 순서를 안내한다', () => {
    renderResults()
    expect(screen.getByText(/순서/)).toBeTruthy()
  })

  // 미지원 슬러그는 결과 화면에서 말하지 않는다 - 니케 풀 탭이 이미 같은
  // 사실을 말하고, 여기서는 매번 뜨는 배경 소음이었다(Fienn, 2026-08-11).
  it('미지원 안내를 결과에 끼워 넣지 않는다', () => {
    renderResults()
    expect(screen.queryByText(/미지원/)).not.toBeInTheDocument()
  })

  // 전투마다 보스가 다르므로 조건은 카드 밖에 몰아 쓸 수 없다.
  it('카드마다 그 전투의 보스 설정을 다시 적는다', () => {
    renderResults()

    expect(screen.getAllByText('방어력 31,784')).toHaveLength(2)
  })

  it('카드마다 자기 보스의 기믹만 적는다', () => {
    renderResults({
      bosses: [
        boss({ element: 'Iron', part_destructible: true }),
        boss({ element: 'Water' }),
      ],
    })

    expect(screen.getAllByText('부위파괴')).toHaveLength(1)
  })
})

describe('EvaluationResults 덱 라벨', () => {
  it('보스 본인 속성이 아니라 약점 속성으로 라벨한다', () => {
    render(
      <EvaluationResults decks={[DECK]} combinedTotalDamage={1000} bosses={[boss({ element: 'Fire' })]} nameFor={(slug) => slug} />,
    )

    expect(screen.getByText('1번 덱 · 약점 수냉')).toBeInTheDocument()
  })

  it('무속성 보스는 그대로 무속성이다', () => {
    render(
      <EvaluationResults decks={[DECK]} combinedTotalDamage={1000} bosses={[boss()]} nameFor={(slug) => slug} />,
    )

    expect(screen.getByText('1번 덱 · 무속성')).toBeInTheDocument()
  })
})
