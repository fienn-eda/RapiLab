// Capture one NIKKE's ShiftyPad detail page as sanitized HTML, over CDP against the
// user's already-logged-in Chrome. The character-detail container holds every surface
// we parse (main stats, overload, all three skills, cube, collection) while the
// Equipment tab is active, so one capture per unit is enough.
//
// Reuse: collect.js (the roster orchestrator) imports connect/findPage/captureUnit.
// CLI: node capture.js <resource_id> <slug>  ->  __fixtures__/<slug>.page.html
//
// Requires Chrome started with --remote-debugging-port=9222 and a logged-in
// blablalink session. Nothing is persisted except the sanitized HTML written here.

const { chromium } = require('playwright-core')
const fs = require('fs')

const CDP = process.env.BLABLALINK_CDP || 'http://localhost:9222'
const SHIFTYPAD = 'https://www.blablalink.com/shiftyspad/nikke?nikke='

const connect = () => chromium.connectOverCDP(CDP)

// Known install locations, tried in order; CHROME_PATH overrides. The directory
// dump is public game data and needs no account, so it can run in a browser we
// launch ourselves instead of attaching to the user's logged-in Chrome.
const CHROME_PATHS = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean)

const launch = () => {
  const exe = CHROME_PATHS.find((p) => fs.existsSync(p))
  if (!exe) {
    throw new Error(
      `no Chrome/Edge executable found; set CHROME_PATH. Tried:\n  ${CHROME_PATHS.join('\n  ')}`,
    )
  }
  return chromium.launch({ executablePath: exe, headless: true })
}

const findPage = (ctx) =>
  ctx.pages().find((p) => p.url().includes('blablalink')) || ctx.pages()[0]

const readLevel = (page) =>
  page.evaluate(() => {
    const el = [...document.querySelectorAll('*')].find(
      (e) => e.children.length === 0 && /^LV\s*\d+/i.test((e.innerText || '').trim()),
    )
    return el ? parseInt(el.innerText.replace(/[^0-9]/g, ''), 10) : null
  })

// Wait until the displayed level stops changing (the SPA renders a default before the
// user's real level lands), so we never start stepping from a transient value.
const waitStableLevel = async (page) => {
  let prev = null
  for (let i = 0; i < 20; i++) {
    const lv = await readLevel(page)
    if (lv !== null && lv === prev) return lv
    prev = lv
    await page.waitForTimeout(350)
  }
  return prev
}

// The level control is custom buttons (-10/-1/+1/+10 inside div.upgrade-btns), not a
// range input. Only the level row carries a "+10"/"-10", so scoping by it avoids the
// grade/core -1/+1 controls. Step toward 400 in either direction: down from an invested
// unit's real level, or up from an uninvested (level-1) unit — solo raid normalizes all
// to 400 regardless of the unit's actual level.
const setLevel400 = async (page) => {
  const row = page.locator('div.upgrade-btns', { hasText: '+10' }).first()
  const btn = (t) => row.getByText(t, { exact: true })
  let lv = await readLevel(page)
  for (let guard = 0; lv !== 400 && guard < 900; guard++) {
    const diff = 400 - lv
    if (diff < 0) await btn(diff <= -10 ? '-10' : '-1').click()
    else await btn(diff >= 10 ? '+10' : '+1').click()
    await page.waitForTimeout(70)
    lv = await readLevel(page)
  }
  return lv
}

const clickTab = async (page, name) => {
  const loc = page.getByText(name, { exact: true })
  const n = await loc.count()
  for (let i = 0; i < n; i++) {
    try {
      await loc.nth(i).click({ timeout: 1200 })
      return true
    } catch {
      // fall through to the next match
    }
  }
  return false
}

// Pluck the parseable surfaces present on the CURRENT tab as small HTML fragments. The
// nikke page is a responsive Vue view whose tabs are v-if: the stat panel is a separate
// DOM branch from the tab content, and each of overload / skills / cube renders only on
// its own tab. So there is no single container to grab — pluck each piece by its local
// anchor. The account panel (name / game_uid / token) is a different branch, never
// matched here, so the plucked fragments carry no identifiers.
const pluckSurfaces = (page) =>
  page.evaluate(() => {
    const frags = []
    // Stat rows: the two-<p> rows whose value cell is "<actual> <signed delta>" (the
    // main panel). Pluck each row directly — the level element is not reliably nested
    // with the rows in the responsive layout.
    for (const d of document.querySelectorAll('div')) {
      const ps = [...d.children].filter((c) => c.tagName === 'P')
      if (ps.length !== 2) continue
      const label = (ps[0].textContent || '').trim().toUpperCase()
      if (!['HP', 'ATK', 'DEF'].includes(label)) continue
      if (/^[\d,]+\s+[+-][\d,]+$/.test((ps[1].textContent || '').trim())) frags.push(d.outerHTML)
    }
    // Overload box (Equipment tab): the div whose header child is 'Equipment Effects'.
    for (const d of document.querySelectorAll('div')) {
      if ([...d.children].some((c) => (c.textContent || '').trim() === 'Equipment Effects')) {
        frags.push(d.outerHTML)
        break
      }
    }
    // Skill rows (Skill tab).
    for (const r of document.querySelectorAll('div')) {
      if (
        (r.className || '').toString().includes('w-40') &&
        /\d+min/.test((r.textContent || '').replace(/\s+/g, ''))
      ) {
        frags.push(r.outerHTML)
      }
    }
    // Cube panel (Cube tab): the compact 'Battle…Arena' div.
    let cube = null
    for (const d of document.querySelectorAll('div')) {
      const t = (d.textContent || '').trim()
      if (/^Battle/.test(t) && /Arena/.test(t) && t.length < 300) {
        if (!cube || t.length < (cube.textContent || '').length) cube = d
      }
    }
    if (cube) frags.push(cube.outerHTML)
    return frags
  })

// Safety net: never let a captured fragment carry an account identifier. Pluck already
// avoids the account panel; pass ids to also scrub any inlined value.
const scrub = (html, ids = {}) => {
  let out = html
  if (ids.gameUid) out = out.split(ids.gameUid).join('00000000')
  if (ids.name) out = out.split(ids.name).join('TESTER')
  if (ids.uin) out = out.split(ids.uin).join('0')
  return out
}

const captureUnit = async (page, resourceId, ids = {}) => {
  await page.goto(SHIFTYPAD + resourceId, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForFunction(
    () =>
      [...document.querySelectorAll('*')].some(
        (e) => e.children.length === 0 && /^LV\s*\d+/i.test((e.innerText || '').trim()),
      ),
    { timeout: 30000 },
  )
  await clickTab(page, 'Equipment')
  await waitStableLevel(page)
  const level = await setLevel400(page)
  if (level !== 400) throw new Error(`level not 400 after stepping (got ${level})`)
  // Tabs are v-if, so each parsed surface lives only on its own tab: visit Equipment
  // (overload), Skill, and Cube, accumulating the plucked fragments (the stat panel
  // repeats on every tab — dedupe it).
  const seen = new Set()
  const frags = []
  for (const tab of ['Equipment', 'Skill', 'Cube']) {
    await clickTab(page, tab)
    await page.waitForTimeout(500)
    for (const f of await pluckSurfaces(page)) {
      if (!seen.has(f)) {
        seen.add(f)
        frags.push(f)
      }
    }
  }
  const body = frags.join('\n')
  if (!/>ATK</.test(body)) throw new Error('stat panel not captured')
  const html = scrub(body, ids)
  return `<!DOCTYPE html>\n<html><head><meta charset="utf-8"></head><body>\n${html}\n</body></html>\n`
}

module.exports = {
  connect,
  launch,
  findPage,
  readLevel,
  setLevel400,
  clickTab,
  pluckSurfaces,
  scrub,
  captureUnit,
}

if (require.main === module) {
  const path = require('path')
  const [, , rid, slug] = process.argv
  if (!rid || !slug) {
    console.error('usage: node capture.js <resource_id> <slug>')
    process.exit(2)
  }
  ;(async () => {
    const browser = await connect()
    const page = findPage(browser.contexts()[0])
    const html = await captureUnit(page, rid)
    const dir = path.join(__dirname, '__fixtures__')
    fs.mkdirSync(dir, { recursive: true })
    fs.writeFileSync(path.join(dir, `${slug}.page.html`), html)
    console.error(`wrote __fixtures__/${slug}.page.html (${html.length}B)`)
    await browser.close()
  })().catch((e) => {
    console.error('CAPTURE_ERROR:', e.message)
    process.exit(1)
  })
}
