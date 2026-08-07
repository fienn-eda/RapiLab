// Pure parsers over a ShiftyPad nikke-page Document (the Equipment-tab detail
// container). No network, no Playwright. jsdom's textContent has NO layout newlines,
// so these parse DOM structure, not text lines.

const num = (s) => parseInt(String(s).replace(/[^0-9-]/g, ''), 10)

// Stat panel: climb from the LV<n> leaf to the ancestor holding HP+ATK+DEF (< 400
// chars). Each stat row is a div with two <p>: label and "<actual> <-delta>".
// raid400 = actual + delta (delta is negative when the real level is above 400).
// The main stat rows are the only two-<p> rows whose value cell is "<actual> <signed
// delta to the slider level>" (e.g. "418862 -275319" or "5097 +89718"): a negative
// delta when the real level is above 400 (invested unit), positive when stepped up from
// a level-1 unit. Equipment/cube stat rows have a bare number and no delta, so the
// delta pattern selects the main panel without depending on the level element's
// position (the responsive layout does not always nest LV with the stat rows).
const parseMainStats = (doc) => {
  const out = { actual: {}, raid400: {} }
  const key = { HP: 'hp', ATK: 'atk', DEF: 'def' }
  for (const row of doc.querySelectorAll('div')) {
    const ps = [...row.children].filter((c) => c.tagName === 'P')
    if (ps.length !== 2) continue
    const k = key[(ps[0].textContent || '').trim().toUpperCase()]
    if (!k || k in out.actual) continue
    const m = (ps[1].textContent || '').trim().match(/^([\d,]+)\s+([+-][\d,]+)$/)
    if (!m) continue
    const actual = num(m[1])
    const delta = num(m[2])
    out.actual[k] = actual
    out.raid400[k] = actual + delta
  }
  return out
}

// ShiftyPad writes these labels two ways, and both are live data to us: the
// committed fixtures carry `Increase X` (and `Element Damage Dealt`), the page
// as served on 2026-08-07 carries `Increased X` (and `Elemental Advantage Dmg`).
// Same rows, same values - only the wording differs - so both spellings map to
// the same Korean stat name rather than one being chosen over the other.
//
// A label absent from this map drops its row silently, which is how a wording
// change costs an entire roster's overload without failing anything: the
// fixtures kept passing while every live unit came back with none. `--details`
// (option ids) is the independent read that catches it.
const OVERLOAD_LABEL_TO_NAME = {
  'Increase ATK': '공격력 증가',
  'Increased ATK': '공격력 증가',
  'Increase Element Damage Dealt': '우월코드 대미지 증가',
  'Increased Elemental Advantage Dmg': '우월코드 대미지 증가',
  'Increase Critical Damage': '크리티컬 대미지 증가',
  'Increased Critical Damage': '크리티컬 대미지 증가',
  'Increase Critical Rate': '크리티컬 확률 증가',
  'Increased Critical Rate': '크리티컬 확률 증가',
  // Charge Damage is the one row no captured or observed unit has carried; both
  // spellings follow the pattern of the rows that were observed.
  'Increase Charge Damage': '차지 대미지 증가',
  'Increased Charge Damage': '차지 대미지 증가',
  'Increase Charge Speed': '차지 속도 증가',
  'Increased Charge Speed': '차지 속도 증가',
  'Increase Max Ammunition Capacity': '최대 장탄 수 증가',
  'Increased Max Ammunition Capacity': '최대 장탄 수 증가',
  'Increase Hit Rate': '명중률 증가',
  'Increased Hit Rate': '명중률 증가',
}

// Summed overload: the div whose header child is exactly 'Equipment Effects'
// (per-piece blocks read 'Change Equipment Effects'). Rows live in its second child;
// each row text is "<English label><NN.NN>%". Unmapped labels (DEF) drop.
const parseOverload = (doc) => {
  let box = null
  for (const d of doc.querySelectorAll('div')) {
    const header = [...d.children].find((c) => (c.textContent || '').trim() === 'Equipment Effects')
    if (header) { box = d; break }
  }
  if (!box) return []
  const header = [...box.children].find((c) => (c.textContent || '').trim() === 'Equipment Effects')
  const flex = [...box.children].find((c) => c !== header)
  const rows = []
  for (const r of flex ? flex.children : []) {
    const m = (r.textContent || '').trim().match(/^(.+?)\s*(\d+(?:\.\d+)?)%$/)
    if (!m) continue
    const name = OVERLOAD_LABEL_TO_NAME[m[1].trim()]
    if (name) rows.push({ name, value: parseFloat(m[2]) })
  }
  return rows
}

// Three skill rows (div.w-40… whose text matches \d+min), in DOM order
// skill1 / skill2 / burst. Level is the integer immediately before 'min'.
const parseSkills = (doc) => {
  const rows = [...doc.querySelectorAll('div')].filter(
    (e) => (e.className || '').toString().includes('w-40') && /\d+min/.test((e.textContent || '').replace(/\s+/g, '')),
  )
  const lv = rows.map((r) => {
    const m = (r.textContent || '').replace(/\s+/g, '').match(/(\d+)min/)
    return m ? parseInt(m[1], 10) : null
  })
  return { skill1: lv[0] ?? null, skill2: lv[1] ?? null, burst: lv[2] ?? null }
}

// Cube: the compact div starting 'Battle' and containing 'Arena'. Read the Battle
// (PvE = solo raid) section only; 'No data available' -> null.
const parseCube = (doc) => {
  let panel = null
  for (const d of doc.querySelectorAll('div')) {
    const t = (d.textContent || '').trim()
    if (/^Battle/.test(t) && /Arena/.test(t) && t.length < 300) {
      if (!panel || t.length < (panel.textContent || '').length) panel = d
    }
  }
  if (!panel) return null
  const t = (panel.textContent || '').replace(/\s+/g, ' ')
  const battle = t.slice(0, t.indexOf('Arena'))
  if (/No data available/i.test(battle)) return null
  const name = battle.match(/([A-Za-z][A-Za-z .'-]*?Cube)/)
  const level = battle.match(/LV\.\s*(\d+)/)
  if (!name) return null
  return { name: name[1].trim(), level: level ? parseInt(level[1], 10) : null }
}

module.exports = { parseMainStats, parseOverload, parseSkills, parseCube }
