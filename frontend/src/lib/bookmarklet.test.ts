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
      /** 다른 「아는 계정」으로 만든 북마크릿을 돌릴 때. 기본은 아무것도 모르는 것. */
      customSource = source,
      /** 이 페이지가 이미 부른 프록시 URL들. 기본은 아무것도 안 부른 페이지다. */
      pageCalls: string[] = [],
    ): Promise<{
      payload: Record<string, unknown> | null
      alerts: string[]
      /** 북마크릿이 요청한 대기 시간들. 실제로 기다리지는 않는다. */
      waits: number[]
    }> => {
      let sent: Record<string, unknown> | null = null
      const alerts: string[] = []
      const waits: number[] = []
      // 북마크릿은 수집한 것을 로컬 인박스로 POST한다. 그 호출을 가로채면
      // 앱이 받게 될 payload를 그대로 볼 수 있다 - 창도 리스너도 필요 없다.
      const wrapped = (url: string, init?: { body?: string }) => {
        if (url.includes('/api/sync-inbox')) {
          sent = JSON.parse(init?.body ?? 'null')
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ received: true }) })
        }
        return fetchImpl(url, init)
      }
      // setTimeout도 주입한다 - 북마크릿이 대기를 하게 되면 그 길이는 blablalink가
      // 정하는 제품 판단이지 테스트가 정할 것이 아니다. 여기서는 즉시 깨운다.
      const run = new Function(
        'location', 'fetch', 'alert', 'setTimeout', 'performance',
        `return ${customSource}`,
      )
      await run(
        { origin: BLABLALINK_ORIGIN },
        wrapped,
        (m: string) => alerts.push(m),
        (fn: () => void, ms: number) => { waits.push(ms); fn() },
        { getEntriesByType: () => pageCalls.map((name) => ({ name })) },
      )
      return { payload: sent, alerts, waits }
    }

    const okFetch = (url: string) =>
      Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })

    // 서버 하나만 잡히게 한다 - responseFor의 GetUserCharacters는 area를 안 가려서
    // 기본 source(다섯 서버)로 돌리면 서버마다 한 번씩 물어 asked가 5로 쌓인다.
    // "한 번만 묻는다"를 재려면 찾히는 서버를 하나로 좁혀야 한다.
    const singleServerSource = decodeURIComponent(
      buildLocalSyncBookmarklet('1234567890123456789', { areas: [83], namedAreas: [] })
        .replace(/^javascript:/, ''),
    )

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
      expect(servers?.[0]?.nickname_error).toContain('shape:profile')
    })

    it('이름이 있으면 이유 칸은 비어 있다', async () => {
      const { payload } = await runBookmarklet(okFetch)
      const servers = payload?.servers as { nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname_error).toBe('')
    })

    // 거절된 요청도 blablalink의 제한 창을 민다(2026-08-09 실측: 15/30/60/120초
    // 정적을 두고 다시 물어도 4분 내내 거절됐다). 그래서 재시도는 완화가 아니라
    // 스스로 못 빠져나오게 만드는 악화다. 한 번 묻고 만다.
    it('이름 조회는 서버당 한 번만 부른다 - 튕겨도 다시 묻지 않는다', async () => {
      let asked = 0
      const { payload } = await runBookmarklet(
        (url: string) => {
          if (url.endsWith('GetUserProfileBasicInfo')) asked++
          return Promise.resolve({
            json: () =>
              Promise.resolve(
                url.endsWith('GetUserProfileBasicInfo')
                  ? { code: 1300015, msg: 'Requests are too frequent', data: null }
                  : { code: 0, data: responseFor(url) },
              ),
          })
        },
        singleServerSource,
      )
      expect(asked).toBe(1)
      const servers = payload?.servers as { nickname: string; nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe('')
      expect(servers?.[0]?.nickname_error).toContain('1300015')
    })

    // 페이지가 방금 부른 것을 우리가 또 부르면 반드시 거절되고, 그 거절이 창을
    // 밀어 다음 동기화까지 망친다. 「이 페이지가 이미 물었는가」는 상수 없이
    // Resource Timing으로 알 수 있다 - 기록은 문서마다 새로 시작한다.
    it('이 페이지가 이미 이름을 조회했으면 묻지 않는다', async () => {
      let asked = 0
      const { payload } = await runBookmarklet(
        (url: string) => {
          if (url.endsWith('GetUserProfileBasicInfo')) asked++
          return Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })
        },
        source,
        ['https://api.blablalink.com/api/game/proxy/Game/GetUserProfileBasicInfo'],
      )
      expect(asked).toBe(0)
      const servers = payload?.servers as { nickname: string; nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe('')
      expect(servers?.[0]?.nickname_error).toContain('page')
      // 로스터는 그대로 들어온다 - 막힌 것은 이름 하나다.
      expect((servers?.[0] as unknown as { owned: unknown[] }).owned.length).toBeGreaterThan(0)
    })

    // 페이지가 다른 것만 불렀다면 이름 조회는 통과할 수 있다. 그때는 묻는다 -
    // 계정 하나에 한 번만 성공하면 되고, 그 뒤로는 namedAreas가 건너뛴다.
    it('페이지가 이름을 조회하지 않았으면 한 번 묻는다', async () => {
      let asked = 0
      const { payload } = await runBookmarklet(
        (url: string) => {
          if (url.endsWith('GetUserProfileBasicInfo')) asked++
          return Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })
        },
        singleServerSource,
        ['https://api.blablalink.com/api/game/proxy/Game/HasFinishOnboardingMissionList'],
      )
      expect(asked).toBe(1)
      const servers = payload?.servers as { nickname: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe(NICKNAME)
    })

    // 이름을 이미 아는 서버에서는 그 호출을 아예 하지 않는다 - 빈도 제한에
    // 걸리는 바로 그 호출이라, 부르지 않는 것이 가장 확실한 대책이다.
    it('이름을 아는 서버에서는 이름 조회를 하지 않는다', async () => {
      const known = decodeURIComponent(
        buildLocalSyncBookmarklet('1234567890123456789', { areas: [83], namedAreas: [83] })
          .replace(/^javascript:/, ''),
      )
      const endpoints: string[] = []
      const { payload } = await runBookmarklet((url: string) => {
        endpoints.push(url.split('/').pop() ?? '')
        return Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })
      }, known)

      expect(endpoints).not.toContain('GetUserProfileBasicInfo')
      // 서버 하나만 훑으므로 호출은 셋이다 - 예전 여덟에서 줄어든 것이 핵심이다.
      expect(endpoints).toHaveLength(3)
      const servers = payload?.servers as { nickname: string; nickname_error: string }[] | undefined
      // 이름은 앱이 이미 갖고 있다. 빈 값을 보내면 upsertProfile이 기존 것을 지킨다.
      expect(servers?.[0]?.nickname).toBe('')
      // 물어보지 않았으니 실패도 아니다 - 안내 줄이 뜨면 안 된다.
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
      "catch(e){if(!probeErr&&e.code!==1302125)probeErr=e;owned=[]}",
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






  it('에러 분기는 코드 숫자로 갈린다 (:1000이 :1 취급되지 않게)', () => {
    // catch(err) 블록을 그대로 뽑아 실행해 실제로 어떤 문구가 뜨는지 본다.
    // 문자열 매칭이던 시절에는 `/:1$/` 앵커가 이 성질을 지켰는데, 코드 뒤에
    // 메시지가 붙으면서 앵커가 못 쓰게 됐다 - 이제 err.code로 가른다.
    const match = source.match(/catch\(err\)\{([\s\S]*)\}\s*\}\)\(\)$/)
    expect(match).not.toBeNull()
    const run = (code: number) => {
      let said = ''
      new Function('err', 'alert', match![1])(
        Object.assign(new Error('GetUserCharacters:' + code), { code }),
        (m: string) => { said = m },
      )
      return said
    }

    // 코드 1000은 1이 아니다 - 공유 URL 분기를 타면 안 된다.
    expect(run(1000)).not.toBe('공유 URL을 다시 확인해주세요.')
    expect(run(1303005)).toBe('공유 URL을 다시 확인해주세요.')
    expect(run(1)).toBe('공유 URL을 다시 확인해주세요.')
    expect(run(300001)).toBe('blablalink 로그인이 필요해요.')
    // 모르는 코드는 원문 그대로 - 이번 1300015처럼 처음 보는 것이 여기로 온다.
    expect(run(1300015)).toContain('1300015')
  })

})

// blablalink는 호출이 잦으면 거절한다(code 1300015 "Requests are too frequent")
// - 그리고 거절당하는 것은 묶음의 마지막인 이름 조회다. 그래서 근본 대책은
// 간격이나 재시도가 아니라 **호출 수**다. 앱이 이미 아는 계정이면 다섯 서버를
// 또 훑을 이유가 없고, 이름을 아는 서버라면 이름을 다시 물을 이유도 없다.
describe('buildLocalSyncBookmarklet: 아는 계정은 덜 부른다', () => {
  const areasIn = (src: string) => src.match(/const AREAS=\[([^\]]*)\]/)?.[1]
  const namedIn = (src: string) => src.match(/const NAMED=\[([^\]]*)\]/)?.[1]
  const decoded = (openId: string, known?: { areas: number[]; namedAreas: number[] }) =>
    decodeURIComponent(buildLocalSyncBookmarklet(openId, known).replace(/^javascript:/, ''))

  it('아는 것이 없으면 예전처럼 다섯 서버를 다 훑는다', () => {
    expect(areasIn(decoded('1234567890123456789'))).toBe('81,82,83,84,85')
  })

  it('로스터가 있는 서버를 알면 그 서버만 훑는다', () => {
    const src = decoded('1234567890123456789', { areas: [83], namedAreas: [] })
    expect(areasIn(src)).toBe('83')
  })

  it('여러 서버를 쓰는 계정은 그 서버들만 훑는다', () => {
    const src = decoded('1234567890123456789', { areas: [81, 83], namedAreas: [] })
    expect(areasIn(src)).toBe('81,83')
  })

  it('이름을 아는 서버는 이름 조회 목록에서 빠진다', () => {
    const src = decoded('1234567890123456789', { areas: [81, 83], namedAreas: [81] })
    expect(namedIn(src)).toBe('81')
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
