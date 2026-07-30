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

  // 소스에 'nickname:'이 있는지 보는 문자열 단언은 응답에서 값을 꺼내는 경로가
  // 틀려도 통과한다 - 실제로 `data.basic_info.nickname`을 `data.nickname`으로
  // 한 단계 얕게 읽던 버그가 그 단언들을 모두 통과했다. 그래서 여기서는 북마크릿을
  // 실측 응답 형태에 대고 실행해 payload에 실린 값 자체를 검증한다.
  describe('실행 결과', () => {
    const NICKNAME = 'FIENN'

    const responseFor = (endpoint: string): unknown => {
      if (endpoint.endsWith('GetUserCharacters'))
        return { characters: [{ name_code: 5101, combat: 461955 }] }
      if (endpoint.endsWith('GetUserCharacterDetails'))
        return { character_details: [{ name_code: 5101 }] }
      if (endpoint.endsWith('GetUserProfileOutpostInfo'))
        return { outpost_info: { recycle_room_researches: [{ tid: 1, lv: 2 }] } }
      // 2026-07-25 실측 형태: 닉네임은 basic_info 아래 한 단계 더 들어가 있다.
      return { basic_info: { nickname: NICKNAME, role_name: NICKNAME } }
    }

    /** 북마크릿을 가짜 blablalink 창에서 돌리고, 앱 창으로 간 payload를 돌려준다. */
    const runBookmarklet = async (
      fetchImpl: (url: string) => Promise<{ json: () => Promise<unknown> }>,
    ): Promise<Record<string, unknown> | null> => {
      let sent: Record<string, unknown> | null = null
      const appWindow = {
        postMessage: (message: { type: string; payload: Record<string, unknown> }) => {
          if (message.type === PAYLOAD_MESSAGE) sent = message.payload
        },
      }
      const listeners: ((event: unknown) => void)[] = []
      const fakeWindow = {
        open: () => appWindow,
        addEventListener: (_type: string, handler: (event: unknown) => void) =>
          listeners.push(handler),
        removeEventListener: () => {},
      }
      const run = new Function(
        'window',
        'location',
        'fetch',
        'alert',
        `return ${source}`,
      )
      const finished = run(
        fakeWindow,
        { origin: BLABLALINK_ORIGIN },
        fetchImpl,
        () => {},
      )
      // 북마크릿은 앱 창이 ready를 알린 뒤에야 payload를 보낸다.
      for (const handler of listeners) {
        handler({ source: appWindow, origin: 'https://deck.example', data: { type: 'nikke-sync-ready' } })
      }
      await finished
      return sent
    }

    const okFetch = (url: string) =>
      Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })

    it('basic_info 아래의 nickname을 payload의 서버별 항목에 싣는다', async () => {
      const payload = await runBookmarklet(okFetch)
      const servers = payload?.servers as { nickname: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe(NICKNAME)
    })

    it('프로필 조회가 실패해도 로스터 싱크는 살아남는다', async () => {
      // code 1303005("user has not bind role_id")가 실측된 적 있다. 닉네임은
      // 표시용이므로 그 실패가 로스터 전체를 날려선 안 된다.
      const payload = await runBookmarklet((url) =>
        Promise.resolve({
          json: () =>
            Promise.resolve(
              url.endsWith('GetUserProfileBasicInfo')
                ? { code: 1303005, msg: 'user has not bind role_id', data: null }
                : { code: 0, data: responseFor(url) },
            ),
        }),
      )
      expect(payload).not.toBeNull()
      const servers = payload?.servers as { nickname: string; owned: unknown[] }[] | undefined
      expect(servers?.[0]?.nickname).toBe('')
      expect(servers?.[0]?.owned).toHaveLength(1)
    })
  })

  it('다섯 서버를 모두 훑고 area를 고정하지 않는다', () => {
    expect(source).toContain('[81,82,83,84,85]')
    expect(source).not.toContain('nikke_area_id:81')
    expect(source).toContain('nikke_area_id:a')
  })

  it('서버별 조회 실패는 그 서버만 건너뛴다', () => {
    // 한 서버의 일시적 오류(1303002가 관측됨)가 동기화 전체를 죽이면 안 된다.
    expect(source).toContain('catch(e){if(!probeErr)probeErr=e;owned=[]}')
  })

  it('니케가 있는 서버가 하나도 없으면 사람이 읽을 문구를 낸다', () => {
    expect(source).toContain('니케를 찾지 못했어요')
  })

  it('payload는 서버 목록을 담는다', () => {
    expect(source).toContain('servers:servers')
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
