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
  hold_burst_slugs: [], tap_fire_slugs: [], partial_charge_slugs: [],
  partial_charge_full_rounds: {}, seating: {},
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
  it('배율까지 버린 자리는 「항상 톡톡이」로 말한다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{ ...DECK, tap_fire_slugs: ['alice'], partial_charge_slugs: ['alice'] }}
        nameFor={(slug) => (slug === 'alice' ? '앨리스' : slug)}
      />,
    )

    const note = screen.getByText(/톡톡이/)
    expect(note).toHaveTextContent('앨리스')
    expect(note).toHaveTextContent('항상')
  })

  // 밀크: 블루밍 바니처럼 매거진 안에서 풀차지와 톡톡이를 섞는 좌석은 「항상
  // 톡톡이」가 거짓이다 - 발수를 숫자로 말하는 세 번째 문구를 받는다.
  it('풀차지를 섞는 좌석은 발수를 적어 안내한다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{
          ...DECK,
          partial_charge_slugs: ['milk-blooming-bunny'],
          partial_charge_full_rounds: { 'milk-blooming-bunny': 1 },
        }}
        nameFor={(slug) => (slug === 'milk-blooming-bunny' ? '밀크: 블루밍 바니' : slug)}
      />,
    )

    const note = screen.getByText(/풀차지 1회 \+ 톡톡이로 계산했어요/)
    expect(note).toHaveTextContent('밀크: 블루밍 바니')
    expect(screen.queryByText(/항상 톡톡이로 계산했어요/)).not.toBeInTheDocument()
  })

  // 차속이 세게 걸린 구간은 차지가 0이라 눌러도 풀차지다 - 손은 톡톡이인데 잃는 것이
  // 없다. 그 구간에서만 톡톡이인 덱은 「버스트 턴은 톡톡이, 아닐 때는 X」다.
  it('배율을 안 버린 자리는 버스트 턴만 톡톡이라고 말한다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{ ...DECK, tap_fire_slugs: ['alice'], partial_charge_slugs: [] }}
        nameFor={(slug) => (slug === 'alice' ? '앨리스' : slug)}
      />,
    )

    const note = screen.getByText(/톡톡이/)
    expect(note).toHaveTextContent('앨리스')
    expect(note).toHaveTextContent('버스트 턴은 톡톡이')
  })

  // 화면은 「무엇을 하라」까지만 말한다 - 왜 이득인지는 안 적는다(Fienn).
  it('톡톡이 안내는 이유를 적지 않는다', () => {
    render(
      <DeckCard
        label="덱 1"
        deck={{ ...DECK, tap_fire_slugs: ['alice'], partial_charge_slugs: ['alice'] }}
      />,
    )

    expect(screen.getByText(/톡톡이/)).not.toHaveTextContent('재장전')
  })

  it('톡톡이 좌석이 없으면 아무것도 안 단다', () => {
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
