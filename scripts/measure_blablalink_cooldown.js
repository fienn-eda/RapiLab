// blablalink 호출 빈도 제한(code 1300015 "Requests are too frequent")의 규칙을 재는
// 콘솔 스크립트. 앱이 아니라 사람이 붙여넣어 쓴다.
//
// **왜 필요한가.** 「이름 조회가 묶음의 마지막이라 거절된다」는 가정 위에 완화책을
// 넷 얹었고(호출 사이 350ms 간격 · 백오프 재시도 0/2/5초 · 8→4호출 축소 · 서버를
// 직접 골라 첫 계정도 4호출) 전부 부족했다. 계정의 최초 동기화는 여전히 이름 대신
// UID로 떨어진다. 가정을 재지 않은 채 다섯 번째 완화를 얹는 대신 규칙 자체를 잰다.
//
// **이미 답이 나온 것 (2026-08-09 실측).**
//   - 순서는 상관없다. 묶음의 **맨 앞**에 둔 이름 조회가 거절되고, 93초 뒤
//     **맨 뒤**에 둔 것이 통과했다. 「마지막이라 거절된다」는 죽었다.
//   - 제한은 `GetUserProfileBasicInfo` **하나에만** 걸린다. 다른 엔드포인트를
//     1.2초 안에 셋 태운 직후에도 이름 조회가 통과했다.
//   - 따라서 호출 수·간격·서버 선택은 전부 원인이 아니었다. 실제 규칙은
//     **「이 엔드포인트를 최근에 불렀는가」** 하나다.
//   - 이름은 다른 응답에 없다. `GetUserProfileOutpostInfo`=`outpost_info` 열 개,
//     `GetUserCharacters`=`characters|is_banned|trace_id`,
//     `GetUserCharacterDetails`=`character_details|state_effects|trace_id`.
//     2단계 스캔에서 이름 후보가 나온 것은 `basic_info`뿐이었다.
//
// **아직 답이 없는 것.**
//   1. 한 번만 부르는 최초 동기화가 왜 거절되는가 - 누가 먼저 불렀는가? → history
//   2. 쿨다운이 몇 초인가 (93초 안에는 풀린다는 것까지만 안다)?        → measureWindow
//
// **쓰는 법.**
//   1. blablalink.com에 로그인한 탭에서 F12 → 콘솔.
//   2. 아래 ACCOUNT에 ShiftyPad 공유 URL을 그대로 붙이고(open id만 알면 그것도
//      된다), AREA를 그 계정의 서버로 맞춘다.
//   3. 파일 전체를 붙여넣는다. history()가 자동으로 돌고 표를 찍는다(즉시).
//   4. 나머지는 따로 부른다: `__probe.measureWindow()`(최대 4분),
//      `__probe.all()`(A/B 대조, 약 7분), `__probe.contamination()`.
//   5. 표를 그대로 복사해 오면 된다.
//
// **시작 조건.** 직전 2분간 이 계정을 동기화하지 않았을 것 - 제한은 한 묶음 안이
// 아니라 세션에 누적된다(계정 둘을 연달아 동기화하면 둘째만 UID로 떨어지는 것이
// 그 증거다).
//
// 계정 값은 찍지 않는다. 남기는 것은 code · msg · 응답의 키 이름 · 「이름이
// 비었는지」뿐이다.

const ACCOUNT = '' // ShiftyPad 공유 URL 통째로, 또는 open id 숫자만
const AREA = 83 // 81=JP 82=NA 83=KR 84=GL 85=SEA

// ---------------------------------------------------------------------------

;(() => {
  if (location.origin !== 'https://www.blablalink.com') {
    throw new Error('blablalink.com 탭의 콘솔에서 실행해주세요.')
  }
  // `frontend/src/lib/shareUrl.ts`와 같은 규칙(uid = "<앞자리>-<open id>"의 base64).
  // 콘솔에 붙여넣는 물건이라 앱 코드를 import할 수 없어 여기서 한 번 더 푼다.
  const OPEN_ID = (() => {
    const raw = ACCOUNT.trim()
    if (/^\d{6,}$/.test(raw)) return raw
    try {
      const uid = new URL(raw).searchParams.get('uid')
      return uid ? (atob(uid).split('-').at(-1) ?? '') : ''
    } catch {
      return ''
    }
  })()
  if (!/^\d{6,}$/.test(OPEN_ID)) {
    throw new Error('맨 위 ACCOUNT에 ShiftyPad 공유 URL이나 open id를 넣어주세요.')
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
  const t0 = Date.now()
  const at = () => ((Date.now() - t0) / 1000).toFixed(1) + 's'

  /** 한 줄 = 한 호출. 표로 찍을 것이 전부 여기 쌓인다. */
  const log = []

  /**
   * 응답 어딘가에 이름이 숨어 있는지 찾는다. 이름 조회를 아예 없앨 수 있으면
   * 빈도 제한 문제 자체가 사라지므로, 부르는 김에 모든 응답을 훑는다.
   *
   * 두 단계까지 내려가는 이유는 `basic_info.nickname`이 한 단계 얕게 읽으면
   * 안 보였던 전례가 있어서다(2026-07-25). 배열은 첫 원소만 대표로 본다.
   * 값은 담지 않고 **경로만** 남긴다 - 계정 정보가 새지 않게.
   */
  const scanForName = (value, path = '', depth = 0) => {
    if (!value || typeof value !== 'object' || depth > 2) return []
    if (Array.isArray(value)) {
      return value.length ? scanForName(value[0], path + '[0]', depth + 1) : []
    }
    const hits = []
    for (const [k, v] of Object.entries(value)) {
      const here = path ? path + '.' + k : k
      if (/nick|role|name/i.test(k) && typeof v === 'string' && v.trim()) hits.push(here)
      hits.push(...scanForName(v, here, depth + 1))
    }
    return hits
  }

  // 북마크릿과 같은 간격을 쓴다 - 여기서만 더 여유를 주면 재는 대상이 달라진다.
  const GAP = 350
  let lastCall = 0

  const call = async (phase, ep, body) => {
    const wait = GAP - (Date.now() - lastCall)
    if (wait > 0) await sleep(wait)
    lastCall = Date.now()
    const row = { phase, at: at(), ep, code: null, msg: '', keys: '', nameHits: '', nickname: '' }
    try {
      const r = await fetch('https://api.blablalink.com/api/game/proxy/Game/' + ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include',
      })
      const j = await r.json()
      row.code = j.code
      row.msg = j.msg || ''
      row.keys = Object.keys(j.data || {}).join('|')
      row.nameHits = scanForName(j.data).join(' , ')
      if (ep === 'GetUserProfileBasicInfo') {
        const bi = (j.data && j.data.basic_info) || {}
        row.nickname = (bi.nickname || bi.role_name) ? '있음' : '빔'
      }
      log.push(row)
      console.log(
        `[${row.at}] ${phase} ${ep} → code ${j.code} ${row.msg}` +
          (row.nameHits ? ` | 이름 후보: ${row.nameHits}` : ''),
      )
      return j.code === 0 ? j.data : null
    } catch (e) {
      row.code = 'fetch 실패'
      row.msg = String((e && e.message) || e)
      log.push(row)
      console.log(`[${row.at}] ${phase} ${ep} → ${row.msg}`)
      return null
    }
  }

  const base = { intl_open_id: OPEN_ID, nikke_area_id: AREA }

  const basic = (phase) => call(phase, 'GetUserProfileBasicInfo', { ...base })
  const characters = (phase) => call(phase, 'GetUserCharacters', { ...base })
  const outpost = (phase) => call(phase, 'GetUserProfileOutpostInfo', { ...base })
  const details = (phase, owned) =>
    call(phase, 'GetUserCharacterDetails', {
      ...base,
      name_codes: (owned || []).map((c) => c.name_code),
    })

  /** 이름 조회를 맨 앞에 둔 4호출. 「마지막 자리라서 거절된다」가 맞다면 통과한다. */
  const roundA = async () => {
    const p = 'A(이름 먼저)'
    await basic(p)
    const chars = await characters(p)
    await details(p, chars && chars.characters)
    await outpost(p)
  }

  /** 지금 북마크릿과 같은 순서. roundA와 대조군이다. */
  const roundB = async () => {
    const p = 'B(이름 나중)'
    const chars = await characters(p)
    await details(p, chars && chars.characters)
    await outpost(p)
    await basic(p)
  }

  /**
   * 정적을 늘려가며 이름 조회만 한 번씩 찔러 필요한 쿨다운을 좁힌다.
   * 매번 한 호출뿐이라, 통과한 지점의 대기 시간이 곧 답이다. 짧은 간격으로
   * 계속 두드리는 것(0/2/5초 재시도)과 달리 슬라이딩 윈도를 자기가 갱신하지 않는다.
   */
  const staircase = async (waits = [15, 30, 60, 120]) => {
    for (const w of waits) {
      console.log(`[${at()}] 계단: ${w}초 정적 후 이름 조회 한 번`)
      await sleep(w * 1000)
      const data = await basic(`계단 ${w}초`)
      if (data) {
        console.log(`[${at()}] 계단 통과 - 필요한 정적은 ${w}초 이하`)
        return w
      }
    }
    console.log(`[${at()}] 계단 전부 거절 - 정적만으로는 안 풀린다`)
    return null
  }

  /**
   * 제한이 이름 조회만의 것인지 프록시 전체의 것인지 가른다.
   * 다른 엔드포인트를 셋 태운 직후 이름을 묻는다. 여기서 거절되면 예산은 공유고,
   * 통과하면 이름 조회에만 걸린 별도의 제한이다.
   */
  const contamination = async () => {
    const p = 'C(오염)'
    await characters(p)
    await characters(p)
    await characters(p)
    await basic(p)
  }

  /**
   * **페이지 자신이 이름 조회를 부르고 있는가.** 우리가 한 번만 불러도 거절된다면
   * 누군가 먼저 불렀다는 뜻이고, 가장 유력한 범인은 blablalink 페이지 자신이다
   * (ShiftyPad 화면이 닉네임을 띄우려면 같은 엔드포인트가 필요하다).
   *
   * 브라우저는 페이지가 보낸 요청을 Resource Timing에 남긴다. 교차 출처라
   * 상세 타이밍은 가려지지만 **URL과 시각은 보인다** - 우리가 물어야 하는 것은
   * 그 둘뿐이다. 페이지를 새로 연 직후에 부를 것(기록이 그때 초기화된다).
   */
  const history = () => {
    const now = performance.now()
    const rows = performance
      .getEntriesByType('resource')
      .filter((e) => e.name.includes('/api/game/proxy/Game/'))
      .map((e) => ({
        ep: e.name.split('/Game/')[1],
        secondsAgo: ((now - e.startTime) / 1000).toFixed(1),
        initiatorType: e.initiatorType,
      }))
    console.table(rows)
    return rows
  }

  /**
   * 쿨다운의 길이를 잰다. 한 번 통과시켜 기준을 잡고 곧바로 다시 물어 거절을
   * 확인한 뒤, 정적을 늘려가며 언제 다시 통과하는지 본다.
   *
   * 계단의 라벨은 **직전 호출로부터의 정적**이다. 최초 거절로부터의 누적 시간은
   * 표의 `at` 열로 따로 읽을 것 - 어느 쪽이 제한의 기준인지는 아직 모른다.
   */
  const measureWindow = async () => {
    const first = await basic('창1(기준)')
    if (!first) {
      console.log(`[${at()}] 아직 쿨다운 중입니다. 2분쯤 뒤에 다시 불러주세요.`)
      return null
    }
    const again = await basic('창2(직후)')
    if (again) {
      console.log(`[${at()}] 연속 두 번이 통과 - 쿨다운은 0.35초보다 짧습니다.`)
      return 0
    }
    return staircase()
  }

  const table = () => {
    console.table(log)
    return log
  }

  const all = async () => {
    console.log('시작. 약 7분 걸립니다. 탭을 닫지 말아주세요.')
    await roundA()
    console.log(`[${at()}] 90초 쉽니다(다음 라운드를 앞 라운드가 오염시키지 않도록).`)
    await sleep(90000)
    await roundB()
    const rejected = log.some(
      (r) => r.phase.startsWith('B') && r.ep === 'GetUserProfileBasicInfo' && r.code !== 0,
    )
    if (rejected) await staircase()
    else console.log(`[${at()}] B에서도 이름이 붙었습니다 - 계단은 건너뜁니다.`)
    console.log(`[${at()}] 끝. 아래 표를 그대로 복사해주세요.`)
    return table()
  }

  window.__probe = {
    roundA,
    roundB,
    staircase,
    contamination,
    history,
    measureWindow,
    table,
    log,
    all,
  }
  console.log('__probe 준비됨. history() / measureWindow() / all() / roundA() / roundB()')
  return history()
})()
