import { describe, it, expect } from 'vitest'
import {
  abbreviateOverload,
  byGearPiece,
  formatOverloadName,
  gearRows,
  GEAR_SLOTS,
  OVERLOAD_KEYS,
  rollTier,
} from './overload'

describe('abbreviateOverload', () => {
  it('모든 타입에서 꼬리의 「증가」를 뗀다', () => {
    // 어느 옵션이든 달고 있어서 아무것도 구분하지 않는다.
    expect(abbreviateOverload('공격력 증가')).toBe('공')
    expect(abbreviateOverload('우월코드 대미지 증가')).toBe('우코')
  })

  it('표에서 쓰는 짧은 이름으로 줄인다', () => {
    expect(abbreviateOverload('최대 장탄 수 증가')).toBe('장탄')
    expect(abbreviateOverload('차지 속도 증가')).toBe('차속')
    expect(abbreviateOverload('크리티컬 확률 증가')).toBe('크확')
  })

  // 정렬 메뉴(OVERLOAD_KEYS)에는 없지만 칩에는 나온다 - 표기만 줄인다
  // (Fienn, 2026-08-09).
  it('명중률을 명중으로 줄이되 정렬 키로 만들지는 않는다', () => {
    expect(abbreviateOverload('명중률 증가')).toBe('명중')
    expect(abbreviateOverload('명중률')).toBe('명중')
    expect([...OVERLOAD_KEYS]).not.toContain('명중')
  })

  // 새 효과나 다른 로케일이 들어와도 알아볼 수 있게 남긴다 - 모르는 이름을
  // 잘라내면 무엇이었는지 화면에서 사라진다.
  it('모르는 이름은 「증가」만 떼고 그대로 둔다', () => {
    expect(abbreviateOverload('재장전 속도 증가')).toBe('재장전 속도')
  })
})

// 상세 모드의 이름은 인게임처럼 대괄호에 전체 이름을 담는다. 요약(칩)의 축약과
// 다른 함수인 것이 핵심이다 - 나중에 상세도 축약으로 바꾸고 싶으면 여기 본문
// 한 줄만 abbreviateOverload로 갈아끼우면 된다.
describe('formatOverloadName', () => {
  it('꼬리의 「증가」만 떼고 대괄호에 담는다', () => {
    expect(formatOverloadName('우월코드 대미지 증가')).toBe('[우월코드 대미지]')
    expect(formatOverloadName('최대 장탄 수 증가')).toBe('[최대 장탄 수]')
  })

  it('축약하지 않는다 - 요약 줄과 구분되는 지점이다', () => {
    expect(formatOverloadName('공격력 증가')).not.toBe('[공]')
  })

  it('모르는 이름도 대괄호 안에 그대로 남는다', () => {
    expect(formatOverloadName('재장전 속도 증가')).toBe('[재장전 속도]')
  })
})

// 인게임은 롤을 수치가 아니라 단계로 강조한다 - 15단계는 검은 행, 12~14단계는
// 밝은 파랑, 그 아래는 평범하게. 스크린샷의 85.37%(장탄 15단계)와 26.36%
// (우월코드 13단계)가 각각 그 두 강조였다.
describe('rollTier', () => {
  it('15단계는 최고 강조다', () => {
    expect(rollTier(15)).toBe('max')
  })

  it('12·13·14단계는 중간 강조다', () => {
    expect([rollTier(12), rollTier(13), rollTier(14)]).toEqual(['high', 'high', 'high'])
  })

  it('11단계 이하는 강조하지 않는다', () => {
    expect(rollTier(11)).toBeNull()
    expect(rollTier(1)).toBeNull()
  })

  // 단계를 안 싣고 동기화된 옛 로스터가 최고 롤로 보이면 없는 투자를 말하는 것이다.
  it('단계를 모르면 강조하지 않는다', () => {
    expect(rollTier(undefined)).toBeNull()
  })
})

describe('byGearPiece', () => {
  const roll = (slot: string, index: number, value: number, level: number) => ({
    slot,
    index,
    value,
    level,
  })

  it('네 부위를 인게임 배치 순서로 돌려준다', () => {
    const pieces = byGearPiece([
      { name: '공격력 증가', value: 4.77, lines: [roll('leg', 1, 4.77, 1)] },
    ])
    expect(pieces?.map((piece) => piece.slot)).toEqual([...GEAR_SLOTS])
    expect(GEAR_SLOTS).toEqual(['head', 'torso', 'arm', 'leg'])
  })

  // 롤이 없는 부위도 자리를 지켜야 2×2 격자가 어긋나지 않는다.
  it('롤이 없는 부위는 빈 채로 남는다', () => {
    const pieces = byGearPiece([
      { name: '공격력 증가', value: 4.77, lines: [roll('head', 1, 4.77, 1)] },
    ])
    expect(pieces?.find((piece) => piece.slot === 'torso')?.rolls).toEqual([])
  })

  it('한 부위 안에서는 인게임과 같은 옵션 행 순서로 늘어놓는다', () => {
    const pieces = byGearPiece([
      // 타입 순서로는 우월코드가 먼저다. 행 번호가 그것을 이긴다.
      { name: '우월코드 대미지 증가', value: 29.16, lines: [roll('head', 3, 29.16, 15)] },
      { name: '공격력 증가', value: 4.77, lines: [roll('head', 1, 4.77, 1)] },
    ])
    const head = pieces?.find((piece) => piece.slot === 'head')
    expect(head?.rolls.map((r) => r.name)).toEqual(['공격력 증가', '우월코드 대미지 증가'])
  })

  it('행 번호를 안 실은 로스터는 타입 순서로 늘어놓는다', () => {
    const pieces = byGearPiece([
      { name: '공격력 증가', value: 4.77, lines: [{ slot: 'arm', value: 4.77 }] },
      { name: '우월코드 대미지 증가', value: 9.54, lines: [{ slot: 'arm', value: 9.54 }] },
    ])
    const arm = pieces?.find((piece) => piece.slot === 'arm')
    expect(arm?.rolls.map((r) => r.name)).toEqual(['우월코드 대미지 증가', '공격력 증가'])
  })

  it('단계를 그대로 넘겨준다', () => {
    const pieces = byGearPiece([
      { name: '최대 장탄 수 증가', value: 85.37, lines: [roll('torso', 2, 85.37, 15)] },
    ])
    expect(pieces?.find((p) => p.slot === 'torso')?.rolls[0].level).toBe(15)
  })

  // 롤을 안 실은 로스터는 부위별로 그릴 방법이 없다. 합계는 롤로 되돌릴 수 없다.
  it('롤이 아예 없으면 null이다', () => {
    expect(byGearPiece([{ name: '공격력 증가', value: 4.77 }])).toBeNull()
  })

  // 하나라도 빠지면 그 스탯이 격자에서 통째로 사라진다 - 없는 장비처럼 보인다.
  it('옵션 하나만 롤을 잃어도 null이다', () => {
    expect(
      byGearPiece([
        { name: '공격력 증가', value: 4.77, lines: [roll('head', 1, 4.77, 1)] },
        { name: '우월코드 대미지 증가', value: 9.54 },
      ]),
    ).toBeNull()
  })

  it('모르는 부위가 섞이면 null이다', () => {
    expect(
      byGearPiece([
        { name: '공격력 증가', value: 4.77, lines: [roll('backpack', 1, 4.77, 1)] },
      ]),
    ).toBeNull()
  })

  it('오버로드가 아예 없으면 null이다', () => {
    expect(byGearPiece([])).toBeNull()
  })
})

// 장비 하나가 인게임처럼 세 행을 갖는다. 어느 행이 비는가는 자리를 당겨 붙이면
// 틀린다 - 방어력 롤은 엔진이 안 쓴다고 백엔드가 버리므로, 2행이 방어력이던
// 장비는 우리에게 1행과 3행만 온다. 그 구멍은 실제로 자주 생긴다.
describe('gearRows', () => {
  const roll = (name: string, index?: number) => ({ name, value: 1, index })

  it('세 행을 채운다 - 롤이 모자라면 빈 자리로', () => {
    expect(gearRows([roll('공격력 증가', 1)]).map((r) => r?.name)).toEqual([
      '공격력 증가',
      undefined,
      undefined,
    ])
  })

  it('빠진 행 번호의 자리를 지킨다', () => {
    const rows = gearRows([roll('우월코드 대미지 증가', 1), roll('공격력 증가', 3)])
    expect(rows.map((r) => r?.name)).toEqual(['우월코드 대미지 증가', undefined, '공격력 증가'])
  })

  // 행 번호를 안 실은 로스터는 어느 행이 비었는지 알 방법이 없다. 당겨 붙이는
  // 것이 없는 정보를 지어내지 않는 유일한 선택이다.
  it('행 번호가 없으면 앞에서부터 채운다', () => {
    const rows = gearRows([roll('우월코드 대미지 증가'), roll('공격력 증가')])
    expect(rows.map((r) => r?.name)).toEqual(['우월코드 대미지 증가', '공격력 증가', undefined])
  })

  it('롤이 없는 장비도 세 행을 낸다', () => {
    expect(gearRows([])).toHaveLength(3)
  })

  // 행이 셋보다 많아질 일은 없지만, 생긴다면 조용히 잘리는 것이 최악이다.
  it('네 번째 행이 오면 잘라내지 않고 늘린다', () => {
    expect(gearRows([roll('공격력 증가', 4)])).toHaveLength(4)
  })
})
