import { describe, expect, it } from 'vitest'
import {
  BLABLALINK_ORIGIN,
  PAYLOAD_MESSAGE,
  buildBookmarklet,
} from './bookmarklet'

const code = buildBookmarklet('1234567890123456789', 'https://deck.example')
// 본문은 encodeURIComponent로 감싸여 있어 "://" 같은 문자가 %3A%2F%2F로 바뀐다.
// 따라서 내용 단언은 반드시 디코드한 소스에 대해 한다.
const source = decodeURIComponent(code.replace(/^javascript:/, ''))

describe('buildBookmarklet', () => {
  it('javascript: URL로 나온다', () => {
    expect(code.startsWith('javascript:')).toBe(true)
  })

  it('open_id와 앱 origin이 박힌다', () => {
    expect(source).toContain('1234567890123456789')
    expect(source).toContain('https://deck.example')
  })

  it('세 엔드포인트를 모두 부른다', () => {
    for (const ep of [
      'GetUserCharacters',
      'GetUserCharacterDetails',
      'GetUserProfileOutpostInfo',
    ]) {
      expect(source).toContain(ep)
    }
  })

  it('area 81과 blablalink origin 가드를 포함한다', () => {
    expect(source).toContain('nikke_area_id:81')
    expect(source).toContain(BLABLALINK_ORIGIN)
    expect(source).toContain(PAYLOAD_MESSAGE)
  })

  it('자격증명을 담지 않는다', () => {
    expect(source).not.toMatch(/password|token|cookie=/i)
  })
})
