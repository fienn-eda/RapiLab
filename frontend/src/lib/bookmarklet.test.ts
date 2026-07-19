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

  it('message 리스너가 window.open보다 먼저 등록된다 (cross-context race 방지)', () => {
    // 열린 탭은 별도 브라우징 컨텍스트(사이트 격리 시 별도 프로세스)라 JS의
    // 단일 스레드 순서 보장이 적용되지 않는다. window.open 전에 리스너를
    // 등록해야 앱이 먼저 뜬 뒤 ready를 보내는 경우에도 유실되지 않는다.
    const listenerIndex = source.indexOf("addEventListener('message'")
    const openIndex = source.indexOf('window.open(')
    expect(listenerIndex).toBeGreaterThan(-1)
    expect(openIndex).toBeGreaterThan(-1)
    expect(listenerIndex).toBeLessThan(openIndex)
  })

  it('message 리스너는 매칭 후 스스로를 제거한다 (재동기화 시 중복 리스너 방지)', () => {
    const handlerNameMatch = source.match(/window\.addEventListener\('message',(\w+)\)/)
    expect(handlerNameMatch).not.toBeNull()
    const handlerName = handlerNameMatch![1]
    expect(source).toContain(`removeEventListener('message',${handlerName})`)
  })

  it('메시지 가드가 발신 source까지 확인한다 (e.source===w)', () => {
    expect(source).toContain('e.source===w')
  })

  it('에러 코드 매칭이 문자열 끝에 고정된다 (:1000 같은 무관한 코드가 공유 URL 분기로 새지 않게)', () => {
    // catch 블록의 alert(...) 삼항식을 그대로 뽑아 실행해, 실제로 어떤 메시지가
    // 뜨는지 검증한다 (문자열 포함 여부만 보면 :1000이 :1 취급되는 버그를 못 잡는다).
    const match = source.match(/alert\((m\.indexOf\('300001'\)[\s\S]*?)\)\}\n\}\)\(\)$/)
    expect(match).not.toBeNull()
    const alertExprFn = new Function('m', `return (${match![1]})`)

    // GetUserCharacters:1000은 코드 1이 아니라 1000이므로 공유 URL 분기를 타면 안 된다.
    expect(alertExprFn('Error: GetUserCharacters:1000')).not.toBe('공유 URL을 다시 확인해주세요.')
    // 1303005는 여전히 공유 URL 분기를 타야 한다 (:1$ 앵커링 후에도 살아있는 별도 체크).
    expect(alertExprFn('Error: GetUserCharacterDetails:1303005')).toBe('공유 URL을 다시 확인해주세요.')
    // 코드가 정확히 1이면 공유 URL 분기를 타야 한다.
    expect(alertExprFn('Error: GetUserCharacters:1')).toBe('공유 URL을 다시 확인해주세요.')
  })
})

describe('buildBookmarklet 입력 검증', () => {
  it('openId에 숫자 아닌 문자가 섞이면 던진다', () => {
    expect(() =>
      buildBookmarklet("123'-alert(1)-'456", 'https://deck.example'),
    ).toThrow()
  })

  it('appOrigin에 따옴표가 섞이면 던진다', () => {
    expect(() =>
      buildBookmarklet('1234567890123456789', "https://deck.example'-alert(1)-'"),
    ).toThrow()
  })

  it('appOrigin이 http(s) origin 형태가 아니면 던진다', () => {
    expect(() =>
      buildBookmarklet('1234567890123456789', 'javascript:alert(1)'),
    ).toThrow()
    expect(() =>
      buildBookmarklet('1234567890123456789', 'https://deck.example/path'),
    ).toThrow()
  })

  it('openId가 6자리 미만이면 던진다 (shareUrl.ts의 OPEN_ID 규칙과 일치)', () => {
    expect(() => buildBookmarklet('12345', 'https://deck.example')).toThrow()
  })
})
