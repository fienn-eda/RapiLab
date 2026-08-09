import { describe, expect, it } from 'vitest'
import { BLABLALINK_ORIGIN, LOCAL_SYNC_PORTS, buildLocalSyncBookmarklet } from './bookmarklet'

const code = buildLocalSyncBookmarklet('1234567890123456789')
// 본문은 encodeURIComponent로 감싸여 있어 "://" 같은 문자가 %3A%2F%2F로 바뀐다.
// 따라서 내용 단언은 반드시 디코드한 소스에 대해 한다.
const source = decodeURIComponent(code.replace(/^javascript:/, ''))

describe('buildLocalSyncBookmarklet: 수집', () => {
  it('javascript: URL로 나온다', () => {
    expect(code.startsWith('javascript:')).toBe(true)
  })

  it('건네받은 open_id 하나로만 조회한다', () => {
    // 개인정보 안내가 "남의 계정을 조회하지 않아요"라고 말하는 근거다. 북마크릿은
    // 유저 브라우저에서 유저 세션으로 도니까, 다른 id가 하나라도 섞여 들어가면
    // 그것은 곧 남의 계정을 그 세션으로 조회한다는 뜻이 된다.
    const ids = [...source.matchAll(/intl_open_id:'(\d+)'/g)].map((m) => m[1])

    expect(ids.length).toBeGreaterThan(0)
    expect(new Set(ids)).toEqual(new Set(['1234567890123456789']))
  })

  it('blablalink origin 가드를 포함한다 (우리 앱 페이지에서 실행되는 것을 막는다)', () => {
    // location.origin이 BLABLALINK_ORIGIN이 아니면 즉시 alert 후 return - 이
    // 가드가 없으면 우리 앱 페이지 등 다른 컨텍스트에서 실행됐을 때 세션
    // 없는 fetch가 나가거나 CORS 없이 조용히 실패한다.
    expect(source).toContain(`location.origin!=='${BLABLALINK_ORIGIN}'`)
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
      // 북마크릿은 수집한 것을 로컬 인박스로 POST한다. 그 호출을 가로채면
      // 앱이 받게 될 payload를 그대로 볼 수 있다 - 창도 리스너도 필요 없다.
      const wrapped = (url: string, init?: { body?: string }) => {
        if (url.includes('/api/sync-inbox')) {
          sent = JSON.parse(init?.body ?? 'null')
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ received: true }) })
        }
        return fetchImpl(url, init)
      }
      const run = new Function('location', 'fetch', 'alert', `return ${source}`)
      await run(
        { origin: BLABLALINK_ORIGIN },
        wrapped,
        (m: string) => alerts.push(m),
      )
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

    // 닉네임이 왜 비었는지는 이 payload에만 남는다 - 없으면 「이름 대신 UID가
    // 나온다」에서 더 물어볼 곳이 없다(2026-08-09 실제로 그렇게 막혔다).
    it('이름 조회가 실패하면 그 이유를 payload에 적어 보낸다', async () => {
      const { payload } = await runBookmarklet((url: string) =>
        Promise.resolve({
          json: () =>
            Promise.resolve(
              url.endsWith('GetUserProfileBasicInfo')
                ? { code: 1303005, msg: 'user has not bind role_id', data: null }
                : { code: 0, data: responseFor(url) },
            ),
        }),
      )
      const servers = payload?.servers as { nickname: string; nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe('')
      expect(servers?.[0]?.nickname_error).toContain('1303005')
    })

    // 호출은 성공했는데 이름이 없는 경우 - 응답 모양이 바뀌면 이렇게 된다.
    // 값이 아니라 최상위 키 이름만 담으므로 계정 정보가 새지 않는다.
    it('응답이 성공해도 이름이 없으면 최상위 키를 적어 보낸다', async () => {
      const { payload } = await runBookmarklet((url: string) =>
        Promise.resolve({
          json: () =>
            Promise.resolve(
              url.endsWith('GetUserProfileBasicInfo')
                ? { code: 0, data: { profile: { name: 'elsewhere' } } }
                : { code: 0, data: responseFor(url) },
            ),
        }),
      )
      const servers = payload?.servers as { nickname: string; nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe('')
      expect(servers?.[0]?.nickname_error).toBe('shape:profile')
    })

    it('이름이 있으면 이유 칸은 비어 있다', async () => {
      const { payload } = await runBookmarklet(okFetch)
      const servers = payload?.servers as { nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname_error).toBe('')
    })

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

describe('buildLocalSyncBookmarklet: 입력 검증', () => {
  it('openId에 숫자 아닌 문자가 섞이면 던진다', () => {
    expect(() =>
      buildLocalSyncBookmarklet("123'-alert(1)-'456"),
    ).toThrow()
  })



  it('openId가 6자리 미만이면 던진다 (shareUrl.ts의 OPEN_ID 규칙과 일치)', () => {
    expect(() => buildLocalSyncBookmarklet('12345')).toThrow()
  })
})

describe('buildLocalSyncBookmarklet: 전송', () => {
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
