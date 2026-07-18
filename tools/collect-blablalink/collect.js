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
//               (no roster, no ownership data — see dumpDirectory below)

const fs = require('fs')
const { JSDOM } = require('jsdom')
const { connect, findPage, captureUnit } = require('./capture')
const { parseMainStats, parseOverload, parseSkills, parseCube } = require('./parse')

const args = process.argv.slice(2)
const DRY = args.includes('--dry-run')
const DIRECTORY_ONLY = args.includes('--directory')
const DEFAULT_OUT = DIRECTORY_ONLY ? 'nikke-directory.json' : 'roster.json'
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

  const cookies = await ctx.cookies()
  const openid = (cookies.find((c) => c.name === 'game_openid') || {}).value || null
  if (!openid) throw new Error('no game_openid cookie — is the blablalink session logged in?')
  const byCode = new Map(dir.map((d) => [d.name_code, d]))

  log('fetching owned characters…')
  const owned = await fetchOwned(page, openid, AREA)
  const synchroLevel = owned.reduce((m, c) => Math.max(m, c.lv || 0), 0)

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
