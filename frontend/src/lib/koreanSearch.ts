// 한글 이름 검색을 위한 초성 다루기. 니케 이름은 대부분 한글 두세 음절이라,
// 초성 두 글자가 100기 넘는 그리드를 한 자리수로 줄인다.

/** 유니코드 한글 음절이 초성을 배치한 순서 그대로. 인덱스가 곧 초성 번호다. */
const CHOSUNG = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
  'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
] as const

const SYLLABLE_FIRST = 0xac00 // '가'
const SYLLABLE_LAST = 0xd7a3 // '힣'
/** 초성 하나가 거느리는 음절 수 = 중성 21 × 종성 28. */
const PER_CHOSUNG = 21 * 28

const CHOSUNG_SET: ReadonlySet<string> = new Set(CHOSUNG)

/** 문자열에서 한글 음절의 초성만 뽑아 잇는다. 음절이 아닌 글자(공백·구두점·
 * 괄호·영숫자)는 버린다 - 자리를 남기면 "홍련: 흑영"이 "ㅎㄹ: ㅎㅇ"가 되어
 * 사이의 구두점 때문에 "ㅎㄹㅎㅇ"로 못 찾는다. */
export const toChosung = (text: string): string => {
  let out = ''
  for (const char of text) {
    const code = char.codePointAt(0)!
    if (code < SYLLABLE_FIRST || code > SYLLABLE_LAST) continue
    out += CHOSUNG[Math.floor((code - SYLLABLE_FIRST) / PER_CHOSUNG)]
  }
  return out
}

/** 질의가 초성만으로 이뤄졌는가. 완성형이 섞이면("홍ㄹ") 초성 대조는 틀린 답을
 * 내므로 - toChosung('홍련')은 'ㅎㄹ'이고 거기 '홍ㄹ'은 없다 - 그때는 쓰지
 * 않고 완성형 부분일치에 맡긴다. */
export const isChosungQuery = (text: string): boolean => {
  const chars = [...text].filter((char) => char !== ' ')
  return chars.length > 0 && chars.every((char) => CHOSUNG_SET.has(char))
}
