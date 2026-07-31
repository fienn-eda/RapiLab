import { describe, expect, it } from 'vitest'
import { BLABLALINK_ORIGIN, LOCAL_SYNC_PORTS, PAYLOAD_MESSAGE, buildBookmarklet, buildLocalSyncBookmarklet } from './bookmarklet'

const code = buildBookmarklet('1234567890123456789', 'https://deck.example')
// 본문은 encodeURIComponent로 감싸여 있어 "://" 같은 문자가 %3A%2F%2F로 바뀐다.
// 따라서 내용 단언은 반드시 디코드한 소스에 대해 한다.
const source = decodeURIComponent(code.replace(/^javascript:/, ''))

describe('buildBookmarklet', () => {
  it('javascript: URL로 나온다', () => {
    expect(code.startsWith('javascript:')).toBe(true)
  })

  it('blablalink origin 가드를 포함한다 (우리 앱 페이지에서 실행되는 것을 막는다)', () => {
    // location.origin이 BLABLALINK_ORIGIN이 아니면 즉시 alert 후 return - 이
    // 가드가 없으면 우리 앱 페이지 등 다른 컨텍스트에서 실행됐을 때 세션
    // 없는 fetch가 나가거나 CORS 없이 조용히 실패한다.
    expect(source).toContain(`location.origin!=='${BLABLALINK_ORIGIN}'`)
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

    type FetchImpl = (
      url: string,
      init?: { body?: string },
    ) => Promise<{ json: () => Promise<unknown> }>

    /** 북마크릿을 가짜 blablalink 창에서 돌리고, 앱 창으로 간 payload와 뜬
     * alert 문구들을 돌려준다. */
    const runBookmarklet = async (
      fetchImpl: FetchImpl,
    ): Promise<{ payload: Record<string, unknown> | null; alerts: string[] }> => {
      let sent: Record<string, unknown> | null = null
      const alerts: string[] = []
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
        (m: string) => alerts.push(m),
      )
      // 북마크릿은 앱 창이 ready를 알린 뒤에야 payload를 보낸다.
      for (const handler of listeners) {
        handler({ source: appWindow, origin: 'https://deck.example', data: { type: 'nikke-sync-ready' } })
      }
      await finished
      return { payload: sent, alerts }
    }

    const okFetch = (url: string) =>
      Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })

    /** GetUserCharacters를 area별로 갈라 응답하는 fetch를 만든다. `ownedByArea`에
     * 없는 area는 1302125("get info list err")로 실패한다 - 실측대로 "이
     * 계정은 이 서버엔 로스터가 없다"를 흉내낸다. 다른 세 엔드포인트는
     * `responseFor`로 그대로 성공한다. 모든 호출을 (endpoint, body) 로 기록해
     * 어느 area로 무엇을 불렀는지 검사할 수 있게 한다. */
    const makeAreaFetch = (
      ownedByArea: Record<number, { name_code: number }[]>,
    ): { fetchImpl: FetchImpl; calls: { endpoint: string; body: Record<string, unknown> }[] } => {
      const calls: { endpoint: string; body: Record<string, unknown> }[] = []
      const fetchImpl: FetchImpl = (url, init) => {
        const body = init?.body ? (JSON.parse(init.body) as Record<string, unknown>) : {}
        calls.push({ endpoint: url, body })
        if (url.endsWith('GetUserCharacters')) {
          const owned = ownedByArea[body.nikke_area_id as number]
          if (owned === undefined) {
            return Promise.resolve({
              json: () =>
                Promise.resolve({ code: 1302125, msg: 'get info list err', data: null }),
            })
          }
          return Promise.resolve({ json: () => Promise.resolve({ code: 0, data: { characters: owned } }) })
        }
        return Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })
      }
      return { fetchImpl, calls }
    }

    it('basic_info 아래의 nickname을 payload의 서버별 항목에 싣는다', async () => {
      const { payload } = await runBookmarklet(okFetch)
      const servers = payload?.servers as { nickname: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe(NICKNAME)
    })

    it('프로필 조회가 실패해도 로스터 싱크는 살아남는다', async () => {
      // code 1303005("user has not bind role_id")가 실측된 적 있다. 닉네임은
      // 표시용이므로 그 실패가 로스터 전체를 날려선 안 된다.
      const { payload } = await runBookmarklet((url) =>
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

    it('한 서버의 GetUserCharacters 실패는 그 서버만 빼고, 살아남은 서버는 그대로 동기화된다', async () => {
      // area 82(NA)만 니케를 갖고, 나머지 넷은 1302125("이 서버엔 없음")로
      // 응답한다. 네 개의 실패가 살아남은 서버까지 막으면 안 된다.
      const { fetchImpl } = makeAreaFetch({ 82: [{ name_code: 5101 }] })
      const { payload } = await runBookmarklet(fetchImpl)
      const servers = payload?.servers as { area: number; owned: unknown[] }[] | undefined
      expect(servers).toHaveLength(1)
      expect(servers?.[0]?.area).toBe(82)
      expect(servers?.[0]?.owned).toHaveLength(1)
    })

    it('후보별 상세/거점 조회가 그 후보의 area를 싣는다 (다른 후보의 area가 섞여 들지 않는다)', async () => {
      // 두 서버(81, 84)가 모두 후보가 되면, 각 후보의 GetUserCharacterDetails·
      // GetUserProfileOutpostInfo 호출은 그 후보 자신의 area를 실어야지 다른
      // 후보의 area를 실으면 안 된다. name_code로 어느 후보의 호출인지 구분한다.
      const { fetchImpl, calls } = makeAreaFetch({
        81: [{ name_code: 1111 }],
        84: [{ name_code: 4444 }],
      })
      await runBookmarklet(fetchImpl)
      const detailCalls = calls.filter((c) => c.endpoint.endsWith('GetUserCharacterDetails'))
      const outpostCalls = calls.filter((c) => c.endpoint.endsWith('GetUserProfileOutpostInfo'))
      expect(detailCalls).toHaveLength(2)
      expect(outpostCalls).toHaveLength(2)
      const detailFor = (nameCode: number) =>
        detailCalls.find((c) => (c.body.name_codes as number[]).includes(nameCode))
      expect(detailFor(1111)?.body.nikke_area_id).toBe(81)
      expect(detailFor(4444)?.body.nikke_area_id).toBe(84)
      expect((outpostCalls.map((c) => c.body.nikke_area_id) as number[]).sort((a, b) => a - b)).toEqual([
        81, 84,
      ])
    })

    it('payload.servers의 각 항목이 그 항목을 조회한 area를 싣는다', async () => {
      const { fetchImpl } = makeAreaFetch({
        81: [{ name_code: 1111 }],
        85: [{ name_code: 5555 }],
      })
      const { payload } = await runBookmarklet(fetchImpl)
      const servers = payload?.servers as { area: number }[] | undefined
      expect((servers?.map((s) => s.area) ?? []).sort((a, b) => a - b)).toEqual([81, 85])
    })

    it('다섯 서버 모두 1302125면 원시 코드가 아니라 사람이 읽을 문구가 뜬다 (Finding 1 회귀 고정)', async () => {
      // probeErr에 1302125가 담기면 `if(probeErr)throw probeErr`가 앞서서
      // "GetUserCharacters:1302125"라는 원시 코드가 그대로 alert에 샌다 -
      // 문자열 단언(소스에 '니케를 찾지 못했어요'가 있는지)은 이 분기가 실제로
      // 선택되는지 못 잡는다. 여기서는 북마크릿을 실행해 뜬 alert 문구
      // 자체를 검증한다.
      const { fetchImpl } = makeAreaFetch({})
      const { payload, alerts } = await runBookmarklet(fetchImpl)
      expect(payload).toBeNull()
      expect(alerts).toHaveLength(1)
      expect(alerts[0]).toContain('니케를 찾지 못했어요')
      expect(alerts[0]).not.toContain('1302125')
    })
  })

  it('다섯 서버를 모두 훑고 area를 고정하지 않는다', () => {
    expect(source).toContain('[81,82,83,84,85]')
    expect(source).not.toContain('nikke_area_id:81')
    expect(source).toContain('nikke_area_id:a')
  })

  it('서버별 조회 실패는 그 서버만 건너뛴다', () => {
    // 한 서버의 일시적 오류(1303002가 관측됨)가 동기화 전체를 죽이면 안 된다.
    // 1302125("get info list err")는 probeErr에 담기지 않는다 - 아래 실행
    // 테스트가 이 필터가 실제로 동작하는지(다섯 서버 전부 1302125일 때 사람이
    // 읽을 문구가 뜨는지) 검증한다.
    expect(source).toContain(
      "catch(e){if(!probeErr&&!/:1302125$/.test(String(e)))probeErr=e;owned=[]}",
    )
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

describe('buildLocalSyncBookmarklet', () => {
  const decoded = (openId: string) =>
    decodeURIComponent(buildLocalSyncBookmarklet(openId).replace(/^javascript:/, ''))

  it('앱을 여는 대신 로컬 인박스로 직접 POST한다', () => {
    // 네이티브 창은 유저 브라우저와 별개라 window.open + postMessage가 닿지 않는다.
    const source = decoded('123456')
    expect(source).not.toContain('window.open')
    expect(source).not.toContain('postMessage')
    expect(source).toContain('/api/sync-inbox')
    expect(source).toContain("method:'POST'")
  })

  it('앱이 잡을 수 있는 포트를 전부 훑는다', () => {
    // 앱은 비어 있는 첫 포트를 쓰므로 하나만 찔러서는 못 찾는다.
    const source = decoded('123456')
    for (const port of LOCAL_SYNC_PORTS) {
      expect(source).toContain(String(port))
    }
  })

  it('수집은 기존 북마크릿과 같은 코드를 쓴다', () => {
    // 둘이 갈라지면 한쪽만 고쳐진 채로 오래 간다.
    const local = decoded('123456')
    const web = decodeURIComponent(
      buildBookmarklet('123456', 'http://localhost:5173').replace(/^javascript:/, ''),
    )
    for (const fragment of ['GetUserCharacters', 'GetUserCharacterDetails',
                            'GetUserProfileOutpostInfo', 'GetUserProfileBasicInfo']) {
      expect(local).toContain(fragment)
      expect(web).toContain(fragment)
    }
  })

  it('blablalink 페이지에서만 동작한다', () => {
    expect(decoded('123456')).toContain(BLABLALINK_ORIGIN)
  })

  it('앱을 못 찾으면 그렇게 말한다', () => {
    expect(decoded('123456')).toContain('RapiLab을 찾지 못했어요')
  })

  it('open ID가 숫자가 아니면 만들지 않는다', () => {
    expect(() => buildLocalSyncBookmarklet("1'2")).toThrow(/숫자로만/)
  })
})
