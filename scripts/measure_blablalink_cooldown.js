// blablalink 호출 빈도 제한(code 1300015 "Requests are too frequent")의 규칙을 재는
// 콘솔 스크립트. 앱이 아니라 사람이 붙여넣어 쓴다.
//
// **왜 필요한가.** 「이름 조회가 묶음의 마지막이라 거절된다」는 가정 위에 완화책을
// 넷 얹었고(호출 사이 350ms 간격 · 백오프 재시도 0/2/5초 · 8→4호출 축소 · 서버를
// 직접 골라 첫 계정도 4호출) 전부 부족했다. 원인은 결국 ShiftyPad 화면 자신이
// 같은 조회를 이미 하고 있는 것으로 밝혀졌고, 고침은 착륙했다 - 계정 이름을
// 유저가 소유하는 라벨로 바꾸고, 이름 조회는 재시도 없는 최선 노력 1회로
// 낮췄다(`docs/decisions.md`「계정 이름은 유저가 소유하는 라벨이다」). 이
// 스크립트가 남아 있는 이유는 그 고침이 기대지 않은 값 - 정확한 쿨다운 길이와
// 호출 예산 - 이 여전히 미측정이라서다.
//
// **죽은 가설 (2026-08-09 실측. 다시 세우지 말 것).**
//   - 「묶음의 마지막이라 거절된다」 - 반대로 나왔다. 묶음의 **맨 앞**에 둔 이름
//     조회가 거절되고, 93초 뒤 **맨 뒤**에 둔 것이 통과했다.
//   - 「이 엔드포인트에 개별 쿨다운이 있다」 - 조용한 상태에서 0.4초 간격으로
//     연속 두 번을 불러 **둘 다 통과**했다.
//   - 「다른 응답에 이름이 있을 것이다」 - 없다. `GetUserProfileOutpostInfo`=
//     `outpost_info` 열 개, `GetUserCharacters`=`characters|is_banned|trace_id`,
//     `GetUserCharacterDetails`=`character_details|state_effects|trace_id`.
//     2단계 스캔에서 이름 후보가 나온 것은 `basic_info`뿐이었다.
//   - 「`GetSavedRoleInfo`로 갈아끼우면 된다」 - `role_info.role_name`이 있긴
//     하지만 **로그인한 세션의 것**이다. 빈 body와 이 계정이 같은 이름을 주고,
//     계정을 바꿔도 같은 이름을 주고, `role_id`가 넘긴 open_id와 다르다.
//     썼다면 계정 셋에 전부 같은 이름이 붙었을 것이다 - 없는 이름보다 나쁘다.
//   - 「프록시 전체에 시간창 예산이 걸려 있다」 - 아니다. 같은 순간
//     `GetUserCharacters`(로스터 조회)는 `code 0`으로 통과한다. 제한은
//     프록시 전체가 아니라 **엔드포인트 특이적**이다.
//
// **확정된 사실.**
//   - **blablalink 페이지가 뜰 때 프록시를 열두 번 부르고, 그중 하나가
//     `GetUserProfileBasicInfo`다**(Resource Timing, 로드 16초 뒤 판독).
//     유저 동선은 「페이지 열자마자 북마크릿 클릭」이라 우리 묶음은 늘 그 열둘
//     **위에** 얹힌다. 우리 묶음을 8→4로 줄여도 못 이긴 이유가 여기 있다.
//   - 통과한 관측은 전부 로드 후 93초·132초였고, 거절된 것은 전부 로드 직후였다.
//   - **로스터 조회(`GetUserCharacters`)는 이름 조회가 거절되는 바로 그 순간에도
//     통과한다** - 제한이 엔드포인트 특이적이라는 증거다.
//   - **거절된 요청도 제한 창을 민다** - 15/30/60/120초 정적을 두고 다시
//     물어도 4분 내내 거절됐다. 재시도가 완화가 아니라 악화인 이유다.
//
// **쓰는 법.**
//   1. blablalink.com에 로그인한 탭에서 F12 → 콘솔.
//   2. 아래 ACCOUNT에 ShiftyPad 공유 URL을 그대로 붙이고(open id만 알면 그것도
//      된다), AREA를 그 계정의 서버로 맞춘다.
//   3. **F5로 새로고침한 직후** 파일 전체를 붙여넣는다 - 유저가 북마크릿을 누르는
//      시점과 같게 만드는 것이 실험의 전부다. `freshLoad()`가 자동으로 돈다.
//   4. 거절되면 콘솔이 다음 수를 안내한다 - `__probe.staircase()`는 대기
//      시간을 좁히지만 창을 밀어 `measureWindow()`를 더 늦춘다. 그 외에는
//      따로 부른다: `__probe.burst()`(예산 세기), `__probe.measureWindow()`
//      (유일하게 남은 미측정 값), `__probe.all()`(A/B 대조, 약 7분).
//   5. 표를 그대로 복사해 오면 된다.
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
  const toOpenId = (input) => {
    const raw = String(input || '').trim()
    if (/^\d{6,}$/.test(raw)) return raw
    try {
      const uid = new URL(raw).searchParams.get('uid')
      return uid ? (atob(uid).split('-').at(-1) ?? '') : ''
    } catch {
      return ''
    }
  }

  const OPEN_ID = toOpenId(ACCOUNT)
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

  /**
   * **이름 조회 시도를 새로고침 너머까지 기억한다.** 이 조사가 반복해서 막힌
   * 지점이 「직전 시도가 언제였나」였다 - 거절된 시도도 창을 갱신하는 것으로
   * 보이는데, 그 시각을 사람의 기억에 의존하면 오염된 런과 진짜 음성을 구분할
   * 수 없다. localStorage에 남겨 모든 판독에 경과 시간이 따라붙게 한다.
   *
   * 시각과 성공 여부만 담는다 - 계정 값은 들어가지 않는다.
   */
  const ATTEMPTS_KEY = '__probe_basic_attempts'
  const readAttempts = () => {
    try {
      return JSON.parse(localStorage.getItem(ATTEMPTS_KEY) || '[]')
    } catch {
      return []
    }
  }
  const rememberAttempt = (ok) => {
    const kept = readAttempts().slice(-49)
    kept.push({ t: Date.now(), ok })
    localStorage.setItem(ATTEMPTS_KEY, JSON.stringify(kept))
  }
  const sinceLastAttempt = () => {
    const kept = readAttempts()
    return kept.length ? (Date.now() - kept[kept.length - 1].t) / 1000 : null
  }
  const forget = () => {
    localStorage.removeItem(ATTEMPTS_KEY)
    console.log('이름 조회 시도 기록을 지웠습니다.')
  }

  const attemptSummary = () => {
    const kept = readAttempts()
    if (!kept.length) return '이름 조회 시도 기록이 없습니다(이 브라우저에서 처음).'
    const last = kept[kept.length - 1]
    const recent = kept.filter((a) => Date.now() - a.t < 600000)
    return (
      `직전 이름 조회 시도: ${((Date.now() - last.t) / 1000).toFixed(0)}초 전` +
      `(${last.ok ? '통과' : '거절'}). 최근 10분간 ${recent.length}회` +
      `(거절 ${recent.filter((a) => !a.ok).length}).`
    )
  }

  // 북마크릿과 같은 간격을 쓴다 - 여기서만 더 여유를 주면 재는 대상이 달라진다.
  const GAP = 350
  let lastCall = 0

  const call = async (phase, ep, body) => {
    const wait = GAP - (Date.now() - lastCall)
    if (wait > 0) await sleep(wait)
    lastCall = Date.now()
    const isBasic = ep === 'GetUserProfileBasicInfo'
    const gap = isBasic ? sinceLastAttempt() : null
    const row = {
      phase,
      at: at(),
      ep,
      sinceLast: gap === null ? '' : gap.toFixed(0) + 's',
      code: null,
      msg: '',
      keys: '',
      nameHits: '',
      nickname: '',
    }
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
      if (isBasic) {
        const bi = (j.data && j.data.basic_info) || {}
        row.nickname = (bi.nickname || bi.role_name) ? '있음' : '빔'
        rememberAttempt(j.code === 0)
      }
      log.push(row)
      console.log(
        `[${row.at}] ${phase} ${ep} → code ${j.code} ${row.msg}` +
          (row.sinceLast ? ` (직전 시도로부터 ${row.sinceLast})` : '') +
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
   * 매번 한 호출뿐이라, 통과한 지점의 대기 시간이 곧 답이다.
   *
   * **거절도 창을 민다는 것이 이 조사의 대표 실측이다** - 그러니 이 계단도
   * 한 단계씩 거절될 때마다 스스로 창을 밀고 있다. 짧은 간격 재시도(0/2/5초)와
   * 근본적으로 다르지 않다. 그래도 단계 사이 정적이 훨씬 길어(15/30/60/120초)
   * 결국은 통과 지점을 찾아낸다 - 다만 그 지점이 "밀리지 않았을 때보다 더 늦게"
   * 찾아진다는 뜻이다.
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
   * **이름을 쿨다운 없는 다른 곳에서 얻을 수 있는가.** 페이지가 프로필 호출들보다
   * 먼저 부르는 `GetSavedRoleInfo`는 이름 그대로 「저장된 게임 롤」이고, 롤에는
   * 보통 이름이 붙는다. 여기서 나오면 `GetUserProfileBasicInfo`를 아예 안 불러도
   * 되므로 쿨다운 문제 자체가 사라진다.
   *
   * 파라미터 모양을 모르니 두 가지를 다 던진다 - 로그인한 자기 계정에 대한
   * 것이라면 빈 body로도 답하고, 프로필별이라면 base가 필요하다. 400이든
   * 에러 코드든 답이 되므로 실패도 표에 남긴다.
   */
  const sniffAlternatives = async () => {
    const p = '대체 경로'
    await call(p, 'GetSavedRoleInfo', {})
    await call(p, 'GetSavedRoleInfo', { ...base })
    await call(p, 'GetMyGuildInfo', { ...base })
    return table()
  }

  /**
   * **`GetSavedRoleInfo`의 이름이 누구 것인가.** 빈 body로도 답한다는 것은 넘긴
   * open_id를 무시하고 로그인한 계정의 롤을 준다는 뜻일 수 있다. 그렇다면 이것은
   * 고침이 아니라 더 나쁜 버그다 - 계정 셋이 전부 같은 이름으로 보이게 된다.
   * **틀린 이름은 없는 이름보다 나쁘다**: 어느 계정인지 구분하려고 붙이는 것이
   * 이름인데 구분이 안 된다.
   *
   * 다른 계정의 open_id를 넘겨 이름이 **바뀌는지**만 본다. 바뀌면 대상별이라
   * 쓸 수 있고, 그대로면 세션의 것이라 못 쓴다.
   *
   * 이름 값은 찍지 않는다 - 「서로 같은가」만 남긴다.
   *
   * 쓰는 법: `__probe.checkRoleScope('<다른 계정 공유 URL>', 81)`
   */
  const checkRoleScope = async (otherAccount, otherArea) => {
    const other = toOpenId(otherAccount)
    if (!/^\d{6,}$/.test(other)) {
      throw new Error('다른 계정의 공유 URL이나 open id를 넘겨주세요.')
    }
    if (other === OPEN_ID) {
      throw new Error('맨 위 ACCOUNT와 같은 계정입니다 - 다른 계정이어야 합니다.')
    }
    const p = '스코프'
    const nameOf = (d) => ((d && d.role_info) || {}).role_name || ''
    const idOf = (d) => String(((d && d.role_info) || {}).role_id || '')

    const blank = nameOf(await call(p, 'GetSavedRoleInfo', {}))
    const mine = await call(p, 'GetSavedRoleInfo', { ...base })
    const theirs = await call(p, 'GetSavedRoleInfo', {
      intl_open_id: other,
      nikke_area_id: otherArea === undefined ? AREA : otherArea,
    })

    const verdict = {
      '빈 body와 이 계정이 같은 이름인가': blank === nameOf(mine),
      '이 계정과 다른 계정이 같은 이름인가': nameOf(mine) === nameOf(theirs),
      '이 계정 role_id가 넘긴 open_id와 같은가': idOf(mine) === OPEN_ID,
      '다른 계정 role_id가 넘긴 open_id와 같은가': idOf(theirs) === other,
      결론:
        nameOf(mine) === nameOf(theirs)
          ? '세션의 이름이다 - 쓸 수 없다(계정마다 같은 이름이 붙는다)'
          : '대상별 이름이다 - 쓸 수 있다',
    }
    console.table(verdict)
    return verdict
  }

  /**
   * **버그를 한 호출로 재현한다.** 성공한 관측은 전부 페이지가 뜬 지 한참 뒤였고
   * (93초·132초), 실패한 것은 전부 로드 직후 몇 초 안이었다. 실제 유저 동선이
   * 정확히 후자다 - 페이지를 열자마자 북마크릿을 누른다.
   *
   * 페이지는 뜰 때 프록시를 열두 번 부른다. 그 직후 우리가 **한 번만** 물어서
   * 거절되면, 예산을 태운 것이 우리 묶음이 아니라 페이지라는 뜻이다. 거절이
   * 재현이다.
   *
   * **전제를 먼저 확인한다.** 열두 번을 부르는 것은 ShiftyPad 프로필 화면이지
   * blablalink의 아무 페이지가 아니다. 페이지가 이름 조회를 부르지 않았다면
   * 이 실험은 조건이 아예 성립하지 않으므로, 결론을 찍는 대신 멈춘다 -
   * 전제를 안 보고 낸 판정은 판정이 아니다.
   *
   * ShiftyPad 공유 URL에서 F5한 직후에 이 파일을 붙여넣으면 자동으로 돈다.
   * 거절되면 다음 수를 안내만 하고 **계단으로 자동으로 잇지 않는다** - 계단도
   * 거절될 때마다 창을 밀기 때문에(위 헤더 「확정된 사실」참고), 이어서 부를지는
   * 사람이 판단해야 한다.
   */
  const freshLoad = async (force = false) => {
    const rows = history()
    const own = rows.filter((r) => r.ep === 'GetUserProfileBasicInfo')
    console.log(
      `페이지가 프록시를 ${rows.length}번 불렀습니다.` +
        (own.length ? ` 이름 조회는 ${own.map((r) => r.secondsAgo).join('·')}초 전.` : ''),
    )
    if (!own.length && !force) {
      console.log(
        '조건 미충족 - 이 페이지는 이름 조회를 부르지 않았습니다. ShiftyPad 공유 URL' +
          '(blablalink.com/shiftyspad?uid=...)에서 F5한 직후에 다시 해주세요.' +
          ' 그래도 강행하려면 freshLoad(true).',
      )
      return null
    }
    const data = await basic('새 로드 직후')
    if (data) {
      console.log(`[${at()}] 통과 - 페이지가 먼저 불렀는데도 된다. burst()로 넘어간다.`)
      return data
    }
    console.log(`[${at()}] 거절 - 재현 성공. 태운 것은 우리 묶음이 아니라 페이지다.`)

    // 무엇이 막힌 것인가. 「프록시 전체의 예산이 고갈됐다」면 로스터 조회도 같이
    // 죽어야 하는데, 실제 동기화에서는 로스터가 멀쩡히 들어온다. 다른
    // 엔드포인트를 같은 시점에 찔러 그 모순을 데이터로 가른다.
    const other = await call('막힌 것 가리기', 'GetUserCharacters', { ...base })
    console.log(
      other
        ? `[${at()}] 다른 엔드포인트는 통과 - 막힌 것은 이름 조회 하나다.`
        : `[${at()}] 다른 엔드포인트도 거절 - 프록시 전체가 막혔다.`,
    )

    // 그럼 언제부터 다시 물을 수 있는가. 계단이 그 답을 좁혀 주지만, 계단 자체도
    // 거절될 때마다 창을 민다 - 그래서 자동으로 잇지 않고 사람에게 선택을 맡긴다.
    console.log(
      `[${at()}] 이어서 __probe.staircase()를 부르면 대기 시간을 좁힙니다(최대 4분) ` +
        '- 다만 그러면 창이 밀려 __probe.measureWindow()(유일하게 남은 미측정 값)는 ' +
        '한참 뒤에야 됩니다.',
    )
    return null
  }

  /**
   * **예산이 몇 호출인가.** 조용한 상태에서 같은 엔드포인트를 연달아 부르며
   * 몇 번째에 1300015가 나오는지 센다.
   *
   * 제한이 프록시 전체가 아니라 엔드포인트별이라는 것은 이미 갈렸다(위 헤더
   * 「확정된 사실」 참고 - 로스터 조회는 이름 조회가 거절되는 순간에도 통과한다).
   * 남은 쓸모는 `GetUserProfileBasicInfo`처럼 특정 엔드포인트 하나의 호출
   * 예산(N)을 세는 것이다 - `measureWindow`가 재는 창 길이(T)와 합쳐야
   * 「N호출/T초」 규칙이 완성된다.
   *
   * 일부러 제한을 건드리는 것이므로 끝나면 몇 분 쉴 것.
   */
  const burst = async (n = 25, ep = 'GetUserCharacters') => {
    for (let i = 1; i <= n; i++) {
      const data = await call(`버스트 ${i}`, ep, { ...base })
      if (!data) {
        console.log(`[${at()}] ${ep}: ${i}번째에서 거절됐다 - 예산은 ${i - 1}호출.`)
        return i - 1
      }
    }
    console.log(`[${at()}] ${ep}: ${n}번을 전부 통과했다 - 예산이 그보다 크다.`)
    return null
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
    sniffAlternatives,
    checkRoleScope,
    freshLoad,
    burst,
    measureWindow,
    attemptSummary,
    forget,
    table,
    log,
    all,
  }
  console.log(attemptSummary())
  console.log('__probe 준비됨. freshLoad()가 지금 돕니다. 이어서 __probe.roundB() / __probe.burst() / __probe.all()')
  return freshLoad()
})()
