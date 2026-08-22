// 옛 릴리스에서 저장한 결과가 오늘의 화면에서 열리는가.
//
// 이 스위트가 있는 이유는 그것이 두 번 안 열렸기 때문이다(hold_burst_slugs,
// 그리고 hold_fire_slugs). 두 번 다 릴리스가 나가고 Fienn이 검은 화면을 본 뒤에야
// 알았다 - 그 전까지 모든 테스트가 **오늘 모양의 덱**만 그리고 있었다.
//
// 새 필드를 응답에 더하면 여기가 먼저 빨개진다. 고치는 법은 필드를 옵셔널로
// 선언하고 읽는 쪽에서 채우는 것이지, 이 표에서 행을 지우는 것이 아니다 -
// 유저의 localStorage에는 그 모양이 그대로 남아 있다.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DeckResults } from './DeckResults'
import { DraftResults } from './DraftResults'
import { EvaluationResults } from './EvaluationResults'
import { RaidResults } from './RaidResults'
import { LEGACY_SHAPES, legacyBoss, legacyDeck } from '../fixtures/legacySchemas'
import type { BossProfile, DeckRecommendation, RaidDeck } from '../types/recommend'

describe.each(LEGACY_SHAPES)('$label에서 저장한 결과', (shape) => {
  // 저장된 JSON은 오늘의 타입을 지킬 의무가 없다. 단언이 여기 있는 것이 정상이고,
  // 그것이 바로 이 스위트가 재는 위험이다.
  const decks = [legacyDeck(shape)] as unknown as DeckRecommendation[]
  const raidDecks = decks as unknown as RaidDeck[]
  const bosses = [legacyBoss(shape)] as unknown as BossProfile[]

  it('추천 목록(단일)으로 열린다', () => {
    render(<DeckResults decks={decks} />)

    expect(screen.getAllByText(/총딜/).length).toBeGreaterThan(0)
  })

  it('솔로 레이드 결과로 열린다', () => {
    render(<RaidResults decks={decks} combinedTotalDamage={1_000_000} />)

    expect(screen.getAllByText(/총딜/).length).toBeGreaterThan(0)
  })

  it('편성 결과로 열린다', () => {
    render(<DraftResults decks={raidDecks} combinedTotalDamage={1_000_000} />)

    expect(screen.getAllByText(/총딜/).length).toBeGreaterThan(0)
  })

  it('유니온 결과로 열린다', () => {
    render(
      <EvaluationResults decks={decks} combinedTotalDamage={1_000_000} bosses={bosses} />,
    )

    expect(screen.getAllByText(/총딜/).length).toBeGreaterThan(0)
  })
})

// 표가 늘 최신인지는 사람이 지켜야 하지만, 적어도 "가장 새로운 행이 오늘의 타입과
// 같은가"는 기계가 물을 수 있다. 새 필드를 더하고 표를 안 고치면 여기서 걸린다.
describe('LEGACY_SHAPES 표', () => {
  it('가장 새로운 행이 오늘 화면이 읽는 필드를 전부 담고 있다', () => {
    const newest = LEGACY_SHAPES[LEGACY_SHAPES.length - 1]
    // DeckCard가 실제로 읽는 것들. 여기 없는 필드가 화면에 새로 쓰이면 이 목록도
    // 같이 늘려야 하고, 그때 표에 새 행을 더하게 된다.
    const readByTheScreen = [
      'deck',
      'total_damage',
      'hold_burst_slugs',
      'tap_fire_slugs',
      'partial_charge_slugs',
      'partial_charge_full_rounds',
      'hold_fire_slugs',
      'seating',
      'gauge_delay_seconds',
      'gauge_bound_cycles',
      'total_cycles',
    ]

    expect(newest.deckFields).toEqual(expect.arrayContaining(readByTheScreen))
  })
})
