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
//   --tables    dump the public stat tables (base curves per class, equipment,
//               affinity) to nikke-stat-tables.json and stop
//   --details   dump this account's investment inputs + outpost research ranks
//               to details.json and stop (personal data; gitignored)
// Both dump modes read only public static game data and return before the
// account lookup, so neither needs a logged-in session.

const fs = require('fs')
const { JSDOM } = require('jsdom')
const { connect, findPage, captureUnit } = require('./capture')
const { parseMainStats, parseOverload, parseSkills, parseCube } = require('./parse')

const args = process.argv.slice(2)
const DRY = args.includes('--dry-run')
const DIRECTORY_ONLY = args.includes('--directory')
const TABLES_ONLY = args.includes('--tables')
const DETAILS_ONLY = args.includes('--details')
const DEFAULT_OUT = DIRECTORY_ONLY
  ? 'nikke-directory.json'
  : TABLES_ONLY
    ? 'nikke-stat-tables.json'
    : DETAILS_ONLY
      ? 'details.json'
      : 'roster.json'
const OUT = args.includes('--out') ? args[args.indexOf('--out') + 1] : DEFAULT_OUT
const AREA = args.includes('--area') ? parseInt(args[args.indexOf('--area') + 1], 10) : 81

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
    .goto('https://www.blablalink.com/shiftyspad/nikke?nikke=16', { waitUntil: 'networkidle', timeout: 60000 })
    .catch(() => {})
  for (let i = 0; i < 20 && !dir; i++) await page.waitForTimeout(300)
  page.off('response', onResp)
  return dir
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
      .goto(`${'https://www.blablalink.com/shiftyspad/nikke?nikke='}${entry.resource_id}`, {
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

const main = async () => {
  const browser = await connect()
  const ctx = browser.contexts()[0]
  const page = findPage(ctx)

  log('resolving nikke directory…')
  const dir = await collectDirectory(page)
  if (!dir) throw new Error('nikke directory not seen in network traffic')

  // The directory is public game data, so this mode needs no account at all — it is
  // how the committed snapshot that validates the resource_id -> slug map is refreshed.
  if (DIRECTORY_ONLY) {
    const entries = trimDirectory(dir)
    fs.writeFileSync(OUT, `${JSON.stringify(entries, null, 2)}\n`)
    log(`wrote ${OUT}: ${entries.length} nikkes`)
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

  const cookies = await ctx.cookies()
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

module.exports = { trimDirectory }

if (require.main !== module) return

main().catch((e) => {
  console.error('COLLECT_ERROR:', e.message)
  process.exit(1)
})
