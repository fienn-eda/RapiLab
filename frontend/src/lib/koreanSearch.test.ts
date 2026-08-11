import { describe, it, expect } from 'vitest'
import { isChosungQuery, toChosung } from './koreanSearch'

describe('toChosung', () => {
  it('음절마다 초성 하나를 낸다', () => {
    expect(toChosung('홍련')).toBe('ㅎㄹ')
    expect(toChosung('라피')).toBe('ㄹㅍ')
    expect(toChosung('네온')).toBe('ㄴㅇ')
    expect(toChosung('앨리스')).toBe('ㅇㄹㅅ')
  })

  it('된소리 초성을 그대로 낸다', () => {
    expect(toChosung('빨강')).toBe('ㅃㄱ')
  })

  // 초성은 음절 코드를 588로 나눈 몫이 정한다 - 중성·종성이 무엇이든 안 흔들린다.
  it('겹받침과 중성은 초성을 흐리지 않는다', () => {
    expect(toChosung('값')).toBe('ㄱ')
    expect(toChosung('까')).toBe('ㄲ')
    expect(toChosung('힣')).toBe('ㅎ')
    expect(toChosung('가')).toBe('ㄱ')
  })

  // 버려야 "홍련: 흑영"이 "ㅎㄹㅎㅇ"가 되어 "ㅎㄹ"로도 맞는다. 자리를 남기면
  // 구두점이 초성 사이에 끼어 아무것도 안 맞는다.
  it('한글 음절이 아닌 글자는 버린다', () => {
    expect(toChosung('홍련: 흑영')).toBe('ㅎㄹㅎㅇ')
    expect(toChosung('은화: 택티컬 업')).toBe('ㅇㅎㅌㅌㅋㅇ')
    expect(toChosung('crown')).toBe('')
    expect(toChosung('')).toBe('')
  })
})

describe('isChosungQuery', () => {
  it('초성만으로 이뤄진 질의를 가려낸다', () => {
    expect(isChosungQuery('ㅎㄹ')).toBe(true)
    expect(isChosungQuery('ㅃ')).toBe(true)
  })

  // 완성형이 섞이면 초성 대조는 틀린 답을 낸다 - toChosung('홍련')='ㅎㄹ'에
  // '홍ㄹ'은 없다. 그럴 땐 완성형 부분일치가 답해야 한다.
  it('완성형이 섞이면 초성 질의가 아니다', () => {
    expect(isChosungQuery('홍ㄹ')).toBe(false)
    expect(isChosungQuery('홍련')).toBe(false)
  })

  it('영문과 빈 문자열은 초성 질의가 아니다', () => {
    expect(isChosungQuery('crown')).toBe(false)
    expect(isChosungQuery('')).toBe(false)
    expect(isChosungQuery('   ')).toBe(false)
  })

  // 모음만으로는 초성을 못 만든다.
  it('모음은 초성이 아니다', () => {
    expect(isChosungQuery('ㅏ')).toBe(false)
  })
})
