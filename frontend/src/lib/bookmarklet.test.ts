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

  it('GetUserProfileBasicInfo를 호출하고 payload에 open_id·nickname을 싣는다', () => {
    expect(source).toContain('GetUserProfileBasicInfo')
    // base의 intl_open_id:도 'open_id:'를 부분 문자열로 포함하므로, payload
    // 리터럴 시작(payload={open_id:) 자체를 앵커링해 그것과 구분한다.
    expect(source).toMatch(/payload=\{open_id:/)
    expect(source).toContain('nickname:')
  })

  it('area 81과 blablalink origin 가드를 포함한다', () => {
    expect(source).toContain('nikke_area_id:81')
    expect(source).toContain(BLABLALINK_ORIGIN)
    expect(source).toContain(PAYLOAD_MESSAGE)
  })

  it('자격증명을 담지 않는다', () => {
    expect(source).not.toMatch(/password|token|cookie=/i)
  })

  it('window.open은 첫 await/fetch보다 먼저 동기적으로 실행된다 (팝업 차단 방지)', () => {
    // 클릭의 transient activation은 짧게 유지된다(크롬 5초, 파이어폭스는 더
    // 엄격). 세 API 호출을 기다린 뒤에야 window.open을 부르면 그 사이
    // activation이 만료돼 브라우저가 팝업을 차단할 수 있다. open은 첫
    // await/fetch 전에, 동기 블록 안에서 실행돼야 한다.
    const openIndex = source.indexOf('window.open(')
    const firstAwaitIndex = source.indexOf('await ')
    const firstFetchIndex = source.indexOf('fetch(')
    expect(openIndex).toBeGreaterThan(-1)
    expect(firstAwaitIndex).toBeGreaterThan(-1)
    expect(firstFetchIndex).toBeGreaterThan(-1)
    expect(openIndex).toBeLessThan(firstAwaitIndex)
    expect(openIndex).toBeLessThan(firstFetchIndex)
  })

  it('message 리스너 등록이 window.open과 같은 동기 블록에 있다 (fetch보다 먼저)', () => {
    // 리스너 등록이 window.open과 분리돼 await 뒤(.then/연속)로 밀리면, 그
    // 사이 자식 창이 먼저 ready를 보내는 race가 생길 수 있다. 등록도 open과
    // 마찬가지로 첫 await/fetch 전, 같은 동기 블록에서 끝나야 한다.
    const listenerIndex = source.indexOf("addEventListener('message'")
    const firstAwaitIndex = source.indexOf('await ')
    const firstFetchIndex = source.indexOf('fetch(')
    expect(listenerIndex).toBeGreaterThan(-1)
    expect(listenerIndex).toBeLessThan(firstAwaitIndex)
    expect(listenerIndex).toBeLessThan(firstFetchIndex)
  })

  it('message 리스너는 매칭 후 스스로를 제거한다 (재동기화 시 중복 리스너 방지)', () => {
    const handlerNameMatch = source.match(/window\.addEventListener\('message',(\w+)\)/)
    expect(handlerNameMatch).not.toBeNull()
    const handlerName = handlerNameMatch![1]
    expect(source).toContain(`removeEventListener('message',${handlerName})`)
  })

  it('payload를 보낸 뒤에만 리스너가 제거된다 (ready만 왔을 때는 제거하지 않음)', () => {
    // send()가 ready && payload 둘 다 있어야만 post+remove하는 구조인지,
    // removeEventListener 호출이 실제로 그 send 경로 안에 있는지 확인한다.
    const handlerNameMatch = source.match(/window\.addEventListener\('message',(\w+)\)/)
    const handlerName = handlerNameMatch![1]
    const sendFnMatch = source.match(/const send=\(\)=>\{(.*?)\};\n/)
    expect(sendFnMatch).not.toBeNull()
    const sendBody = sendFnMatch![1]
    expect(sendBody).toContain('postMessage')
    expect(sendBody).toContain(`removeEventListener('message',${handlerName})`)
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

  it('window.open에 창 이름을 줘 재동기화 때 기존 탭을 재사용한다', () => {
    // 이름 없는 window.open은 매번 새 탭을 연다. 같은 이름을 주면 브라우저가
    // 그 탭을 재사용한다(재사용은 새로고침을 일으키지만 프로필은 매 변경마다
    // localStorage에 저장되므로 잃는 것이 없다 - useProfiles.ts 참고).
    const openCall = source.slice(
      source.indexOf('window.open('),
      source.indexOf('window.open(') + 80,
    )
    expect(openCall).toContain("'nikke-deck-builder'")
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
