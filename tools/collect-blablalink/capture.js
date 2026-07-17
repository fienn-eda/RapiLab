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

const CDP = process.env.BLABLALINK_CDP || 'http://localhost:9222'
const SHIFTYPAD = 'https://www.blablalink.com/shiftyspad/nikke?nikke='

const connect = () => chromium.connectOverCDP(CDP)

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

// Smallest container holding the parser anchors. Extracting it drops the page chrome
// and the account panel (name / game_uid / token live outside this subtree). Anchors
// are present on every unit including uninvested ones — an uninvested unit has no
// "Equipment Effects" panel, so anchor on the stat panel (LV + ATK) plus a skill row.
const extractDetail = (page) =>
  page.evaluate(() => {
    const has = (t) => /LV\s*\d/.test(t) && /\bATK\b/.test(t) && /min/.test(t)
    let best = null
    for (const el of document.querySelectorAll('div')) {
      if (has(el.textContent || '')) {
        if (!best || el.outerHTML.length < best.outerHTML.length) best = el
      }
    }
    return best ? best.outerHTML : null
  })

// Safety net: even though extraction drops the account panel, never let a captured
// fragment carry an account identifier. Pass ids when the DOM might inline them.
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
  const detail = await extractDetail(page)
  if (!detail) throw new Error('detail container not found')
  const html = scrub(detail, ids)
  return `<!DOCTYPE html>\n<html><head><meta charset="utf-8"></head><body>\n${html}\n</body></html>\n`
}

module.exports = {
  connect,
  findPage,
  readLevel,
  setLevel400,
  clickTab,
  extractDetail,
  scrub,
  captureUnit,
}

if (require.main === module) {
  const fs = require('fs')
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
