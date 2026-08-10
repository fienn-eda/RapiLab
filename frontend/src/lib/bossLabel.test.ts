import { describe, it, expect } from 'vitest'
import { bossHeading, weaknessLabelOf } from './bossLabel'

describe('weaknessLabelOf', () => {
  it('보스 속성을 그 약점의 이름으로 바꾼다', () => {
    // 작열(Fire) 보스는 수냉(Water)에 약하고, 수냉(Water) 보스는 전격(Electric)에 약하다.
    expect(weaknessLabelOf('Fire')).toBe('수냉')
    expect(weaknessLabelOf('Water')).toBe('전격')
  })

  it('속성이 없으면 자리를 지키는 낱말을 준다', () => {
    expect(weaknessLabelOf(null)).toBe('약점없음')
  })
})

describe('bossHeading', () => {
  it('보스 이름이 있으면 이름과 약점 아이콘을 준다', () => {
    const h = bossHeading({ bossName: '인디비리아', element: 'Fire', fallback: '덱 1' })
    expect(h.text).toBe('인디비리아')
    expect(h.iconSrc).toBe('/elements/water.png')
  })

  it('이름이 없고 속성만 있으면 약점 이름을 쓴다', () => {
    const h = bossHeading({ bossName: null, element: 'Fire', fallback: '덱 1' })
    expect(h.text).toBe('수냉')
    expect(h.iconSrc).toBe('/elements/water.png')
  })

  it('둘 다 없으면 부르는 쪽이 준 이름으로 돌아간다', () => {
    const h = bossHeading({ bossName: null, element: null, fallback: '덱 1' })
    expect(h.text).toBe('덱 1')
    expect(h.iconSrc).toBeNull()
  })

  // 이름은 그 속성의 보스를 가리켜 붙은 것이다. 속성이 없으면 이름도 가리킬
  // 대상이 없다.
  it('속성 없이 이름만 있으면 폴백으로 돌아간다', () => {
    const h = bossHeading({ bossName: '인디비리아', element: null, fallback: '덱 1' })
    expect(h.text).toBe('덱 1')
    expect(h.iconSrc).toBeNull()
  })
})
