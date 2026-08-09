import { describe, it, expect } from 'vitest'
import { abbreviateOverload, OVERLOAD_KEYS } from './overload'

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
