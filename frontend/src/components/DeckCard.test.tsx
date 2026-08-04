// 파훼 불가 배지는 API가 아니라 화면이 판정한다 - supported-units가 슬러그별 속성을
// 주므로 응답에 필드를 더할 이유가 없다.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DeckCard } from './DeckCard'

const DECK = {
  deck: ['a', 'b', 'c', 'd', 'e'],
  total_damage: 1000,
  burst_damage: 500,
  normal_attack_damage: 400,
  skill_damage: 100,
  hold_burst_slugs: [],
}

describe('DeckCard 속성저지 배지', () => {
  it('파훼 불가 덱에 경고를 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} gimmickUnmetFor={() => true} />)

    expect(screen.getByText('속성저지 파훼 불가')).toBeInTheDocument()
  })

  it('파훼 가능한 덱에는 아무것도 안 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} gimmickUnmetFor={() => false} />)

    expect(screen.queryByText('속성저지 파훼 불가')).not.toBeInTheDocument()
  })

  it('판정자가 없으면 아무것도 안 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} />)

    expect(screen.queryByText('속성저지 파훼 불가')).not.toBeInTheDocument()
  })
})

describe('DeckCard 버스트 홀드 안내', () => {
  // 좌석은 "이 유닛은 첫 풀버스트를 건너뛴다"를 말할 수 없다. 엔진은 동점이면
  // 그대로 플레이할 수 있는 순서를 고르지만, 홀드하는 쪽이 실제로 더 높게
  // 나오면 그 순서가 남고 - 그때는 화면이 플레이어에게 말해줘야 한다.
  it('아껴야 하는 좌석이 있으면 누구를 아낄지 이름으로 말한다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{ ...DECK, hold_burst_slugs: ['d'] }}
        nameFor={(slug) => (slug === 'd' ? '디젤: 윈터 스위츠(후버)' : slug)}
      />,
    )

    // 이름은 유닛 행에도 있으므로, 안내문 자체가 누구인지 말하는지를 본다.
    expect(screen.getByText(/첫 풀버스트/)).toHaveTextContent('디젤: 윈터 스위츠(후버)')
  })

  it('홀드가 필요 없으면 아무것도 안 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} />)

    expect(screen.queryByText(/첫 풀버스트/)).not.toBeInTheDocument()
  })
})
