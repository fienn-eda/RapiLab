// Orchestrates a full roster scrape. Connects to the user's logged-in Chrome over CDP,
// resolves the owned SSR units (nikke directory joined with GetUserCharacters), visits
// each ShiftyPad page at level 400, parses it, and writes roster.json.
//
// Solo raid normalizes every account to character level 400, so raid400 stats are what
// the deck builder needs; actual (real-level) stats are collected too for a future
// union-raid helper. Overload/skills/cube come from the same capture.
//
// Usage (needs Chrome on --remote-debugging-port=9222 with a logged-in blablalink tab):
//   node collect.js [--dry-run] [--out roster.json] [--area 81]
//   --dry-run   collect only the first owned SSR unit (smoke test)
//   --directory dump the public nikke directory to nikke-directory.json and stop
//   --deep      with --directory, fetch corporation_sub_type for units whose
//               value was never carried over from the previous snapshot (i.e.
//               newly released units - a carried-over `null` still counts as
//               known). One page load each.
//   --headless  with any public dump mode (--directory, --nikke, --tables,
//               --collectibles), launch our own browser instead of attaching to
//               yours. Those modes read public game data, so they need no
//               account - it is what lets the scheduled check run unattended.
//   --raw       with --directory, write the CDN payload untrimmed (do NOT commit
//               it: it is huge). For discovering which fields the directory even
//               carries before deciding what the snapshot should keep.
//   --tables    dump the public stat tables (base curves per class, equipment,
//               affinity) to nikke-stat-tables.json and stop
//   --collectibles  dump every 소장품/애장품 record (R and SR per weapon group,
//               plus each SSR favorite item) to collectibles.json and stop. Reads
//               the CDN directly, so it opens no browser and needs no session;
//               --locale <ko|en> picks the language of the embedded text.
//   --details   dump this account's investment inputs + outpost research ranks
//               to details.json and stop (personal data; gitignored)
//   --nikke <rid|name>[,<rid|name>...]  dump each unit's raw ShiftyPad bundle
//               (directory entry + character detail payload) to
//               data/shiftypad/raw/<rid>.json. A list reuses one browser and one
//               directory resolve; with a list, --out names the output DIRECTORY.
//               Public data, so combine with --headless for an unattended run.
// Both dump modes read only public static game data and return before the
// account lookup, so neither needs a logged-in session.

const fs = require('fs')
const { JSDOM } = require('jsdom')
const { connect, launch, findPage, captureUnit } = require('./capture')
const { parseMainStats, parseOverload, parseSkills, parseCube } = require('./parse')
const { fetchResource } = require('./resource-url')
const { fetchLocalisedNames, mergeLocalisedNames } = require('./korean-names')

const args = process.argv.slice(2)
const DRY = args.includes('--dry-run')
const DIRECTORY_ONLY = args.includes('--directory')
const RAW = args.includes('--raw')
const DEEP = args.includes('--deep')
const HEADLESS = args.includes('--headless')
const NIKKE = args.includes('--nikke') ? args[args.indexOf('--nikke') + 1] : null
const TABLES_ONLY = args.includes('--tables')
const COLLECTIBLES_ONLY = args.includes('--collectibles')
const DETAILS_ONLY = args.includes('--details')
const DEFAULT_OUT = DIRECTORY_ONLY
  ? 'nikke-directory.json'
  : TABLES_ONLY
    ? 'nikke-stat-tables.json'
    : COLLECTIBLES_ONLY
      ? 'collectibles.json'
      : DETAILS_ONLY
        ? 'details.json'
        : 'roster.json'
const OUT = args.includes('--out') ? args[args.indexOf('--out') + 1] : DEFAULT_OUT
const AREA = args.includes('--area') ? parseInt(args[args.indexOf('--area') + 1], 10) : 81
// Only the collectible records carry localized text; the values are identical
// across locales. Korean is what this project's UI and docs quote.
const LOCALE = args.includes('--locale') ? args[args.indexOf('--locale') + 1] : 'ko'

const SHIFTYPAD = 'https://www.blablalink.com/shiftyspad/nikke?nikke='

const log = (...m) => console.error(...m)

// The nikke directory (resource_id <-> name_code <-> English name, rarity, class) is
// served from a hash-named CDN file that rotates, so discover it at run time: on a
// ShiftyPad load it is the JSON response that is an array whose items carry both
// resource_id and name_code.
const collectDirectory = async (page) => {
  let dir = null
  const onResp = async (r) => {
    if (dir) return
    const u = r.url()
    if (!u.includes('sg-tools-cdn.blablalink.com') || !u.endsWith('.json')) return
    try {
      const j = await r.json()
      if (Array.isArray(j) && j.length > 50 && j[0] && typeof j[0] === 'object' && 'resource_id' in j[0] && 'name_code' in j[0]) {
        dir = j
      }
    } catch {
      // not JSON / not the directory
    }
  }
  page.on('response', onResp)
  await page
    .goto(`${SHIFTYPAD}16`, { waitUntil: 'networkidle', timeout: 60000 })
    .catch(() => {})
  for (let i = 0; i < 20 && !dir; i++) await page.waitForTimeout(300)
  page.off('response', onResp)
  return dir
}

// The character detail payload is the JSON response for this resource_id that
// carries shot_detail (weapon) and skill{1,2}/ulti details. It is public data,
// so this needs no login - same as the directory dump.
const collectNikkeDetail = async (page, resourceId) => {
  let hit = null
  const onResp = async (r) => {
    if (hit) return
    const u = r.url()
    if (!u.includes('blablalink.com') || !u.split('?')[0].endsWith('.json')) return
    try {
      const j = await r.json()
      if (j && !Array.isArray(j) && String(j.resource_id) === String(resourceId) && j.shot_detail) hit = j
    } catch {}
  }
  page.on('response', onResp)
  await page
    .goto(`${SHIFTYPAD}${resourceId}`, { waitUntil: 'networkidle', timeout: 60000 })
    .catch(() => {})
  for (let i = 0; i < 30 && !hit; i++) await page.waitForTimeout(300)
  page.off('response', onResp)
  return hit
}

// The public game tables the stat calculator needs. Base ATK/HP live in a
// per-character stat file, but they are uniform per class (verified: two
// Attackers' arrays are byte-identical), so one SSR per class is enough.
// Everything here is static game data served without credentials.
const collectStatTables = async (page, dir) => {
  const wanted = ['Attacker', 'Supporter', 'Defender']
  const out = { collected_at: new Date().toISOString().slice(0, 10), classes: {}, equipment: null, affinity: null }

  const onResp = async (r) => {
    if (!r.url().includes('cdn') || !r.url().split('?')[0].endsWith('.json')) return
    let j
    try {
      j = await r.json()
    } catch {
      return
    }
    // Per-character stat file: base curves + the shared breakthrough coefficients.
    if (j && Array.isArray(j.character_level_attack_list) && j.class) {
      out.classes[j.class] ||= {
        attack: j.character_level_attack_list,
        hp: j.character_level_hp_list,
        stat_enhance: j.stat_enhance_detail,
        sampled_from: j.name_code,
      }
      return
    }
    const rows = Array.isArray(j) ? j : null
    if (!rows || !rows.length || typeof rows[0] !== 'object') return
    // Match on any row, not row 0: these tables are not sorted by the field we key on.
    if (!out.equipment && rows.some((x) => x && x.item_type === 'Equip' && Array.isArray(x.stat))) out.equipment = rows
    if (!out.affinity && rows.some((x) => x && 'attractive_level' in x)) out.affinity = rows
  }
  page.on('response', onResp)

  // These tables are fetched once and then served from the browser cache, so a
  // repeat run sees no response at all. Force them back onto the wire.
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })

  for (const cls of wanted) {
    const entry = dir.find((d) => d.class === cls && d.original_rare === 'SSR' && nameOf(d))
    if (!entry) throw new Error(`no SSR found for class ${cls} in the directory`)
    log(`  ${cls}: sampling ${nameOf(entry)} (rid=${entry.resource_id})`)
    await page
      .goto(`${SHIFTYPAD}${entry.resource_id}`, {
        waitUntil: 'networkidle',
        timeout: 60000,
      })
      .catch(() => {})
    await page.waitForTimeout(2500)
  }
  page.off('response', onResp)

  const missing = wanted.filter((c) => !out.classes[c])
  if (missing.length) throw new Error(`no stat table captured for: ${missing.join(', ')}`)
  // The equipment and affinity tables are cached by the SPA in app-level storage
  // (not the HTTP cache), so a profile that has already loaded them never
  // re-requests them and they cannot be intercepted. They are not needed to
  // derive the formula - two levels of the same unit solve for its percentage
  // and flat terms directly - only to predict for a roster we have not measured.
  // Report their absence instead of failing the class curves we did capture.
  for (const [k, v] of Object.entries({ equipment: out.equipment, affinity: out.affinity })) {
    if (!v) log(`  WARNING: ${k} table not seen (SPA app-cache); captured without it`)
  }
  return out
}

// The investment inputs behind the stats: per-unit gear/cube/collectible/affinity
// plus the account-wide outpost research ranks. Joined with roster.json's measured
// stats this is the stat calculator's ground truth (scripts/build_stat_ground_truth.py).
// Personal data - the output is gitignored.
const collectDetails = async (page, openid, area, owned) => {
  const call = (endpoint, body) =>
    page.evaluate(
      async ({ endpoint, body }) => {
        const r = await fetch(`https://api.blablalink.com/api/game/proxy/Game/${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          credentials: 'include',
        })
        const j = await r.json()
        if (j.code !== 0) throw new Error(`${endpoint}: ${j.code} ${j.msg}`)
        return j.data
      },
      { endpoint, body },
    )
  const base = { intl_open_id: openid, nikke_area_id: area }
  // name_codes takes the whole roster in one request, so this is two calls total.
  const detail = await call('GetUserCharacterDetails', { ...base, name_codes: owned.map((c) => c.name_code) })
  const outpost = await call('GetUserProfileOutpostInfo', base)
  return {
    owned: owned.map((c) => ({ name_code: c.name_code, lv: c.lv, core: c.core, grade: c.grade })),
    character_details: detail.character_details,
    recycle_room_researches: outpost.outpost_info.recycle_room_researches,
  }
}

const fetchOwned = (page, openid, area) =>
  page.evaluate(
    async ({ openid, area }) => {
      const r = await fetch('https://api.blablalink.com/api/game/proxy/Game/GetUserCharacters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intl_open_id: openid, nikke_area_id: area }),
        credentials: 'include',
      })
      const j = await r.json()
      return (j.data && j.data.characters) || []
    },
    { openid, area },
  )

const nameOf = (entry) => (entry.name_localkey && entry.name_localkey.name) || null

// Reduce the raw directory to the public identity fields the repo commits as a
// snapshot: enough to prove a resource_id names the unit its slug claims, and to
// look one up for a not-yet-owned unit. Nothing here is account-specific.
const trimDirectory = (dir) =>
  dir
    .filter((d) => nameOf(d))
    .map((d) => ({
      resource_id: d.resource_id,
      name_code: d.name_code,
      name_en: nameOf(d),
      original_rare: d.original_rare,
      // Base ATK/HP are a function of (level, class), so the class is what the
      // stat calculator looks up - it cannot be derived from the other fields.
      class: d.class,
      // Corporation research is ranked per account and adds flat ATK to that
      // corporation's units, so a unit's corporation is part of its stat inputs.
      corporation: d.corporation,
    }))
    .sort((a, b) => a.resource_id - b.resource_id)

// corporation_sub_type ("OVERSPEC") decides how much flat ATK each breakthrough
// core is worth, but the directory payload does not carry it - it lives in the
// per-character stat file, one page load away (collectSubTypes below). A `null`
// is itself a determined answer ("this unit has no sub type"), not a missing
// one, so both helpers key on presence of the field, never its truthiness:
// carrying over a previous `null` is what keeps a plain --directory refresh
// from silently dropping it, and only entries that were never visited at all
// (the field absent from the previous snapshot) are newly released units.
const carryOverSubTypes = (entries, previous) => {
  const known = new Map(
    (previous || [])
      .filter((e) => 'corporation_sub_type' in e)
      .map((e) => [e.resource_id, e.corporation_sub_type]),
  )
  return entries.map((e) =>
    known.has(e.resource_id)
      ? { ...e, corporation_sub_type: known.get(e.resource_id) }
      : e,
  )
}

// Ids never visited (no carried-over answer at all, determined or not): newly
// released units, the only ones --deep needs to visit.
const missingSubTypeIds = (entries) =>
  entries.filter((e) => !('corporation_sub_type' in e)).map((e) => e.resource_id)

// One page load per unit to read corporation_sub_type off its stat file (see
// carryOverSubTypes above for what the field is and why it's opt-in via --deep).
const collectSubTypes = async (page, entries) => {
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
  const out = new Map()
  for (const [i, e] of entries.entries()) {
    let seen
    const onResp = async (r) => {
      if (seen !== undefined || !r.url().includes('cdn') || !r.url().split('?')[0].endsWith('.json')) return
      try {
        const j = await r.json()
        if (j && Array.isArray(j.character_level_attack_list) && String(j.resource_id) === String(e.resource_id)) {
          seen = j.corporation_sub_type || null
        }
      } catch {
        // not the stat file
      }
    }
    page.on('response', onResp)
    await page
      .goto(`${SHIFTYPAD}${e.resource_id}`, { waitUntil: 'networkidle', timeout: 60000 })
      .catch(() => {})
    for (let k = 0; k < 20 && seen === undefined; k++) await page.waitForTimeout(300)
    page.off('response', onResp)
    if (seen === undefined) log(`  WARNING: no stat file for rid ${e.resource_id} (${e.name_en})`)
    else out.set(e.resource_id, seen)
    if ((i + 1) % 25 === 0) log(`  …${i + 1}/${entries.length}`)
  }
  return out
}

// 소장품(collectible)·애장품(favorite item) 레코드: 무기군마다 다른 스킬을 담고
// 있고, 그 스킬 효과는 엔진의 대미지 소스다(docs/engine-gaps.md #17).
//
// 브라우저를 쓰지 않는다. 이 테이블은 로그인한 Collection 화면에서만 요청되므로
// 페이지 트래픽을 가로채는 방식은 빈손으로 끝난다 - 대신 CDN 경로를 직접 계산해
// 받는다(resource-url.js). favorite_rare_map.json이 등급별 id 목록(R 6 · SR 6 ·
// SSR 21)을 주고, 각 id마다 레코드 파일이 하나씩 있다.
const collectCollectibles = async (locale) => {
  const rareMap = await fetchResource('/equip/favorite_rare_map.json')
  const out = {}
  for (const [rare, ids] of Object.entries(rareMap)) {
    for (const id of ids) {
      const record = await fetchResource(`/equip/${locale}/favorite_${id}.json`)
      out[String(record.id)] = record
      log(`  ${rare} ${record.id}: ${record.weapon_type} (${record.favorite_type})`)
    }
  }
  // 등급 x 무기군은 6개씩이어야 한다. 하나라도 비면 게임 쪽 id 목록이 바뀐 것이니
  // 조용히 반쪽짜리 테이블을 쓰지 말고 알린다.
  for (const rare of ['R', 'SR']) {
    const groups = new Set(
      Object.values(out).filter((c) => c.favorite_rare === rare).map((c) => c.weapon_type))
    for (const w of ['AR', 'SMG', 'SG', 'RL', 'SR', 'MG']) {
      if (!groups.has(w)) log(`  WARNING: no ${rare} collectible for weapon group ${w}`)
    }
  }
  return out
}

const parseUnit = (html) => {
  const doc = new JSDOM(html).window.document
  const stats = parseMainStats(doc)
  return {
    raid400: stats.raid400,
    actual: stats.actual,
    overload: parseOverload(doc),
    skill_levels: parseSkills(doc),
    pve_cube: parseCube(doc),
  }
}

// The modes that return before the account lookup: they read only public static
// game data, so they can run in a browser we launch ourselves.
const PUBLIC_MODE = DIRECTORY_ONLY || Boolean(NIKKE) || TABLES_ONLY || COLLECTIBLES_ONLY

const main = async () => {
  if (HEADLESS && !PUBLIC_MODE) {
    throw new Error('--headless applies to the public dump modes (--directory, --nikke, --tables, --collectibles); other modes need your logged-in session')
  }

  // Fetched straight off the CDN, so this mode opens no browser at all - it runs
  // anywhere `fetch` does and is the reason --collectibles needs no session.
  if (COLLECTIBLES_ONLY) {
    log(`collecting collectible records (locale=${LOCALE})…`)
    const collectibles = await collectCollectibles(LOCALE)
    fs.writeFileSync(OUT, `${JSON.stringify(collectibles, null, 2)}\n`)
    log(`wrote ${OUT}: ${Object.keys(collectibles).length} records`)
    return
  }

  const browser = HEADLESS ? await launch() : await connect()
  const page = HEADLESS
    ? await browser.newPage()
    : findPage(browser.contexts()[0])

  log('resolving nikke directory…')
  const dir = await collectDirectory(page)
  if (!dir) throw new Error('nikke directory not seen in network traffic')

  // The directory is public game data, so this mode needs no account at all — it is
  // how the committed snapshot that validates the resource_id -> slug map is refreshed.
  if (DIRECTORY_ONLY) {
    let entries = RAW ? dir : trimDirectory(dir)
    if (!RAW) {
      const previous = fs.existsSync(OUT)
        ? JSON.parse(fs.readFileSync(OUT, 'utf8'))
        : null
      entries = carryOverSubTypes(entries, previous)
      if (DEEP) {
        const missingIds = new Set(missingSubTypeIds(entries))
        log(`collecting corporation_sub_type for ${missingIds.size} unit(s) without one…`)
        const subTypes = await collectSubTypes(page, entries.filter((e) => missingIds.has(e.resource_id)))
        entries = entries.map((e) =>
          subTypes.has(e.resource_id)
            ? { ...e, corporation_sub_type: subTypes.get(e.resource_id) }
            : e,
        )
      }
      // 한국 서버 공식 표기. 인터셉트로 잡히는 목록은 영문판이라 여기서 따로
      // 받아 붙인다(korean-names.js). 실패하면 던져서 스냅샷을 손대지 않는다 —
      // 반쪽짜리로 덮어쓰면 name_ko가 통째로 사라진다.
      entries = mergeLocalisedNames(entries, await fetchLocalisedNames('ko'))
    }
    fs.writeFileSync(OUT, `${JSON.stringify(entries, null, 2)}\n`)
    log(`wrote ${OUT}: ${entries.length} nikkes`)
    await browser.close()
    return
  }

  if (NIKKE) {
    // A comma-separated list reuses one browser and one directory resolve, which is
    // what makes a whole-roster weapon audit (~76 units) practical; --out then names
    // a directory instead of a file, or is left at the default raw/ location.
    const wanted = NIKKE.split(',').map((s) => s.trim()).filter(Boolean)
    const entries = wanted.map((want) => {
      const entry = /^\d+$/.test(want)
        ? dir.find((d) => String(d.resource_id) === want)
        : dir.find((d) => nameOf(d) === want)
      if (!entry) throw new Error(`no directory entry for --nikke ${want}`)
      return entry
    })
    const dest = OUT !== DEFAULT_OUT ? OUT : '../../data/shiftypad/raw'
    fs.mkdirSync(dest, { recursive: true })
    for (const [i, entry] of entries.entries()) {
      const detail = await collectNikkeDetail(page, entry.resource_id)
      if (!detail) throw new Error(`no detail payload for resource_id ${entry.resource_id}`)
      const out = `${dest}/${entry.resource_id}.json`
      fs.writeFileSync(out, `${JSON.stringify({ directory: entry, detail }, null, 2)}\n`)
      log(`[${i + 1}/${entries.length}] wrote ${out}: ${nameOf(entry)} (rid=${entry.resource_id})`)
    }
    await browser.close()
    return
  }

  // Also account-free: the stat tables are static game data.
  if (TABLES_ONLY) {
    log('collecting stat tables…')
    const tables = await collectStatTables(page, dir)
    fs.writeFileSync(OUT, `${JSON.stringify(tables, null, 2)}\n`)
    const count = (t) => (t ? t.length : 'missing')
    log(
      `wrote ${OUT}: classes=${Object.keys(tables.classes).join(',')} ` +
        `equipment=${count(tables.equipment)} affinity=${count(tables.affinity)}`,
    )
    await browser.close()
    return
  }

  const cookies = await browser.contexts()[0].cookies()
  const openid = (cookies.find((c) => c.name === 'game_openid') || {}).value || null
  if (!openid) throw new Error('no game_openid cookie — is the blablalink session logged in?')
  const byCode = new Map(dir.map((d) => [d.name_code, d]))

  log('fetching owned characters…')
  const owned = await fetchOwned(page, openid, AREA)
  const synchroLevel = owned.reduce((m, c) => Math.max(m, c.lv || 0), 0)

  if (DETAILS_ONLY) {
    log('fetching investment details…')
    const details = await collectDetails(page, openid, AREA, owned)
    fs.writeFileSync(OUT, `${JSON.stringify(details, null, 2)}\n`)
    log(
      `wrote ${OUT}: ${details.character_details.length} units, ` +
        `${details.recycle_room_researches.length} research rows`,
    )
    await browser.close()
    return
  }

  let targets = []
  for (const c of owned) {
    const d = byCode.get(c.name_code)
    if (!d || d.original_rare !== 'SSR') continue // raid content is SSR-only
    const name = nameOf(d)
    if (!name) continue
    targets.push({ resource_id: d.resource_id, name_en: name })
  }
  targets.sort((a, b) => a.resource_id - b.resource_id)
  // No owned SSR means the roster fetch failed (bad session / API error envelope), not
  // an empty account — fail loudly instead of writing a 0-unit roster.json.
  if (targets.length === 0) {
    throw new Error('no owned SSR resolved — is the blablalink session valid?')
  }
  if (DRY) targets = targets.slice(0, 1)
  log(`owned SSR to collect: ${targets.length}${DRY ? ' (dry-run)' : ''}`)

  const units = []
  let ok = 0
  let failed = 0
  for (const t of targets) {
    try {
      const html = await captureUnit(page, t.resource_id)
      const parsed = parseUnit(html)
      units.push({ resource_id: t.resource_id, name_en: t.name_en, ...parsed })
      ok += 1
      log(`  [${ok + failed}/${targets.length}] ${t.name_en} (rid=${t.resource_id}) atk400=${parsed.raid400.atk}`)
    } catch (e) {
      failed += 1
      log(`  [${ok + failed}/${targets.length}] FAILED ${t.name_en} (rid=${t.resource_id}): ${e.message}`)
    }
  }

  const roster = { synchroLevel, units }
  fs.writeFileSync(OUT, JSON.stringify(roster, null, 2))
  log(`wrote ${OUT}: ${units.length} units (${failed} failed), synchroLevel=${synchroLevel}`)
  await browser.close()
}

module.exports = { trimDirectory, carryOverSubTypes, missingSubTypeIds }

if (require.main !== module) return

main().catch((e) => {
  console.error('COLLECT_ERROR:', e.message)
  process.exit(1)
})
