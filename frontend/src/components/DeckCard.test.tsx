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
  hold_burst_slugs: [], tap_fire_slugs: [], seating: {},
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
  // 덱 순서는 "이 유닛은 첫 풀버스트를 건너뛴다"를 말할 수 없다. 엔진은 동점이면
  // 그대로 플레이할 수 있는 순서를 고르지만, 홀드하는 쪽이 실제로 더 높게
  // 나오면 그 순서가 남고 - 그때는 화면이 플레이어에게 말해줘야 한다.
  // (여기서 말하는 순서는 버스트 우선순위다. 자리는 별개 축이고 아래 좌석 안내가 맡는다.)
  it('아껴야 하는 자리가 있으면 누구를 아낄지 이름으로 말한다', () => {
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

  // 톡톡이도 홀드와 같은 성격의 지시다: 수치가 그 조작을 전제로 계산됐으니
  // 그렇게 안 하면 이 딜이 안 나온다. 누가 해당되는지는 엔진이 실어 보낸다.
  it('톡톡이를 전제로 계산된 자리가 있으면 누구인지 이름으로 말한다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{ ...DECK, tap_fire_slugs: ['alice'] }}
        nameFor={(slug) => (slug === 'alice' ? '앨리스' : slug)}
      />,
    )

    expect(screen.getByText(/톡톡이/)).toHaveTextContent('앨리스')
  })

  // 「버스트 중에 톡톡이」로 읽히면 정확히 거꾸로다 - 차속 버프가 걸린 구간이야말로
  // 풀차지가 거의 공짜라 기다려야 하는 구간이다. 문구는 두 모드를 다 말해야 한다.
  it('톡톡이 안내는 풀차지 구간도 같이 말한다', () => {
    render(<DeckCard label="덱 1" deck={{ ...DECK, tap_fire_slugs: ['alice'] }} />)

    expect(screen.getByText(/톡톡이/)).toHaveTextContent('풀차지')
  })

  it('톡톡이 전제가 없으면 아무것도 안 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} />)

    expect(screen.queryByText(/톡톡이/)).not.toBeInTheDocument()
  })
})

describe('DeckCard 좌석 안내', () => {
  // 좌석은 덱 목록에 안 담긴다 - 목록 순서는 버스트 우선순위이고, 게임에서 자리와
  // 버스트 순서는 별개 축이다. 그래서 화면이 따로 말해줘야 이 수치가 재현된다.
  const named = (slug: string) =>
    ({ a: '루주', b: '드레이크', c: '모더니아' })[slug] ?? slug

  it('누구 양 옆에 누구를 앉힐지 이름으로 말한다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{ ...DECK, seating: { a: { allies: ['b', 'c'], seats: [2, 4] } } }}
        nameFor={named}
      />,
    )

    // 이름은 유닛 행에도 있으므로 안내문 자체가 셋을 다 말하는지를 본다.
    const line = screen.getByText(/양 옆/)
    expect(line).toHaveTextContent('루주')
    expect(line).toHaveTextContent('드레이크')
    expect(line).toHaveTextContent('모더니아')
  })

  it('앉을 수 있는 자리가 정해져 있으면 그 자리도 말한다', () => {
    // 「양 옆에 둘」만 지키면 3번 자리도 만족하는데, 거기는 앞열이라 루주의
    // 버프가 아예 안 켜진다. 자리를 안 적으면 안내를 그대로 따라도 통째로 놓친다.
    render(
      <DeckCard
        label="덱 1"
        deck={{ ...DECK, seating: { a: { allies: ['b', 'c'], seats: [2, 4] } } }}
        nameFor={named}
      />,
    )

    expect(screen.getByText(/양 옆/)).toHaveTextContent('2·4번')
  })

  it('아무 자리나 되면 자리 이야기를 꺼내지 않는다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{
          ...DECK,
          seating: { a: { allies: ['b', 'c'], seats: [1, 2, 3, 4, 5] } },
        }}
        nameFor={named}
      />,
    )

    expect(screen.getByText(/양 옆/)).not.toHaveTextContent('번 자리')
  })

  it('좌석형 유닛이 없으면 아무것도 안 단다', () => {
    render(<DeckCard label="덱 1" deck={DECK} />)

    expect(screen.queryByText(/양 옆/)).not.toBeInTheDocument()
  })
})

describe('DeckCard 보스 설정', () => {
  // 덱마다 보스가 다른 화면(유니온 레이드)만 넘긴다. 전부 같은 보스인 화면은
  // 결과 위에 한 번만 적는다.
  it('보스를 받으면 카드 안에 그 설정을 적는다', () => {
    render(
      <DeckCard
        label="1번 덱"
        deck={DECK}
        boss={{
          element: 'Fire',
          core_hittable: true,
          pierce_hits_body_behind_core: false,
          enemy_def: 31784,
          fight_duration: 180,
          part_destructible: false,
          core_diameter_px: null,
          effective_range_band: null,
          elemental_interrupt_required: false,
        }}
      />,
    )

    expect(screen.getByText(/약점 수냉/)).toBeInTheDocument()
    expect(screen.getByText('코어 피격')).toBeInTheDocument()
  })

  it('보스가 없으면 그 줄을 아예 그리지 않는다', () => {
    render(<DeckCard label="#1" deck={DECK} />)

    expect(screen.queryByText(/약점/)).not.toBeInTheDocument()
  })
})
