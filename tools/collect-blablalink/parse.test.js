const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('fs')
const path = require('path')
const { JSDOM } = require('jsdom')
const { parseMainStats, parseOverload, parseSkills, parseCube } = require('./parse')

const doc = (slug) =>
  new JSDOM(fs.readFileSync(path.join(__dirname, '__fixtures__', `${slug}.page.html`), 'utf8')).window.document

test('parseMainStats returns actual (real level) and level-400 stats', () => {
  const r = parseMainStats(doc('rapi-red-hood'))
  assert.deepEqual(r.actual, { hp: 9727100, atk: 418862, def: 55537 })
  assert.deepEqual(r.raid400, { hp: 3532402, atk: 143543, def: 20986 })
  const l = parseMainStats(doc('liter'))
  assert.equal(l.actual.atk, 340063)
  assert.equal(l.raid400.atk, 106533)
})

test('parseMainStats handles an uninvested unit stepped UP to 400 (positive delta)', () => {
  // Neon: Blue Ocean is owned at level 1; the slider is raised to 400, so the delta
  // to the selected level is positive: raid400 = actual + (+delta).
  const r = parseMainStats(doc('neon-blue-ocean'))
  assert.deepEqual(r.actual, { hp: 290571, atk: 5097, def: 1842 })
  assert.deepEqual(r.raid400, { hp: 2309238, atk: 94815, def: 13100 })
})

test('parseOverload maps English labels to the Korean stat names, summed', () => {
  const rows = parseOverload(doc('rapi-red-hood'))
  assert.deepEqual(rows, [
    { name: '우월코드 대미지 증가', value: 87.21 },
    { name: '공격력 증가', value: 42.32 },
    { name: '최대 장탄 수 증가', value: 173.93 },
    { name: '크리티컬 확률 증가', value: 4.69 },
  ])
  // Moran confirms Charge Speed. Hit Rate is now mapped; DEF still drops
  // (the engine consumes enemy DEF only, so an ally DEF stat would be inert).
  const moran = parseOverload(doc('moran'))
  assert.ok(moran.some((o) => o.name === '차지 속도 증가' && o.value === 4.92))
  assert.ok(moran.some((o) => o.name === '크리티컬 대미지 증가' && o.value === 16.44))
  assert.ok(moran.some((o) => o.name === '명중률 증가' && o.value === 17.99))
  assert.ok(!moran.some((o) => /DEF|방어/.test(o.name)))
  // Three more fixtures carry a Hit Rate row, at three different totals.
  const hitRate = (slug) =>
    parseOverload(doc(slug)).find((o) => o.name === '명중률 증가')?.value
  assert.equal(hitRate('blanc'), 23.62)
  assert.equal(hitRate('liter'), 11.81)
  assert.equal(hitRate('maxwell'), 7.59)
  // An uninvested unit has no equipment, so no overload section.
  assert.deepEqual(parseOverload(doc('neon-blue-ocean')), [])
})

test('parseOverload reads the relabelled page to the same rows', () => {
  // ShiftyPad writes the same rows two ways - `Increase ATK` on the pages
  // captured in July, `Increased ATK` on the page as served on 2026-08-07,
  // with Element Damage Dealt becoming Elemental Advantage Dmg. Rapi is
  // captured under both wordings with the same gear, so the two must parse
  // identically. Without this, a wording change costs every unit its whole
  // overload while the suite stays green - which is exactly what happened.
  assert.deepEqual(
    parseOverload(doc('rapi-red-hood-relabelled')),
    parseOverload(doc('rapi-red-hood')),
  )
  const relabelled = parseOverload(doc('rapi-red-hood-relabelled'))
  assert.deepEqual(relabelled, [
    { name: '우월코드 대미지 증가', value: 87.21 },
    { name: '공격력 증가', value: 42.32 },
    { name: '최대 장탄 수 증가', value: 173.93 },
    { name: '크리티컬 확률 증가', value: 4.69 },
  ])
})

test('parseSkills reads the three skill levels in order (skill1, skill2, burst)', () => {
  assert.deepEqual(parseSkills(doc('rapi-red-hood')), { skill1: 10, skill2: 10, burst: 10 })
  assert.deepEqual(parseSkills(doc('liter')), { skill1: 10, skill2: 4, burst: 10 })
  assert.deepEqual(parseSkills(doc('moran')), { skill1: 7, skill2: 10, burst: 10 })
  assert.deepEqual(parseSkills(doc('maxwell')), { skill1: 1, skill2: 1, burst: 1 })
})

test('parseCube reads the Battle-loadout cube, null when none equipped', () => {
  assert.deepEqual(parseCube(doc('rapi-red-hood')), { name: 'Resilience Cube', level: 15 })
  assert.deepEqual(parseCube(doc('moran')), { name: 'Bastion Cube', level: 15 })
  assert.equal(parseCube(doc('liter')), null)   // Battle loadout: "No data available"
  assert.equal(parseCube(doc('maxwell')), null) // no cube at all
  assert.equal(parseCube(doc('neon-blue-ocean')), null) // uninvested, no cube
})

test('parseSkills reads level-1 skills for an uninvested unit', () => {
  assert.deepEqual(parseSkills(doc('neon-blue-ocean')), { skill1: 1, skill2: 1, burst: 1 })
})

// Blanc is captured with the current per-tab pluck (stat rows, overload, skills, and
// cube each plucked from their own tab and concatenated) — the format collect.js now
// produces. Its Equipment Effects box carries both a mapped label (Hit Rate) and a
// dropped one (DEF) alongside distinct skill levels.
test('parses a per-tab-plucked capture (Blanc): stats, overload, skills, no cube', () => {
  const d = doc('blanc')
  assert.deepEqual(parseMainStats(d), {
    actual: { hp: 10006777, atk: 240903, def: 67080 },
    raid400: { hp: 3374236, atk: 80115, def: 22859 },
  })
  assert.deepEqual(parseOverload(d), [
    { name: '최대 장탄 수 증가', value: 137.86 },
    { name: '명중률 증가', value: 23.62 },
    { name: '크리티컬 확률 증가', value: 5.71 },
  ])
  assert.deepEqual(parseSkills(d), { skill1: 4, skill2: 7, burst: 9 })
  assert.equal(parseCube(d), null)
})

// --- directory snapshot -------------------------------------------------------

const { trimDirectory, carryOverSubTypes, missingSubTypeIds } = require('./collect')

test('trimDirectory keeps the public identity fields, sorted by resource_id', () => {
  const raw = [
    { resource_id: 16, name_code: 5129, original_rare: 'SSR', name_localkey: { name: 'Rapi: Red Hood' }, class: 'Attacker', corporation: 'ELYSION', combat: 999, extra: 'drop me' },
    { resource_id: 2, name_code: 1, original_rare: 'R', name_localkey: { name: 'Rapi' }, class: 'Attacker', corporation: 'ELYSION' },
  ]
  assert.deepEqual(trimDirectory(raw), [
    { resource_id: 2, name_code: 1, name_en: 'Rapi', original_rare: 'R', class: 'Attacker', corporation: 'ELYSION' },
    { resource_id: 16, name_code: 5129, name_en: 'Rapi: Red Hood', original_rare: 'SSR', class: 'Attacker', corporation: 'ELYSION' },
  ])
})

test('trimDirectory drops entries with no English name (unreleased placeholders)', () => {
  const raw = [
    { resource_id: 9, name_code: 9, original_rare: 'SSR', name_localkey: {} },
    { resource_id: 10, name_code: 10, original_rare: 'SSR', name_localkey: { name: 'Real' } },
  ]
  assert.deepEqual(trimDirectory(raw).map((e) => e.resource_id), [10])
})

const dirEntry = (id, name, extra = {}) => ({
  resource_id: id,
  name_code: 3000 + id,
  name_localkey: { name },
  original_rare: 'SSR',
  class: 'Attacker',
  corporation: 'ELYSION',
  ...extra,
})

test('carryOverSubTypes restores corporation_sub_type from the previous snapshot', () => {
  const fresh = trimDirectory([dirEntry(10, 'Alpha'), dirEntry(20, 'Bravo')])
  const previous = [{ resource_id: 10, corporation_sub_type: 'OVERSPEC' }]
  const out = carryOverSubTypes(fresh, previous)
  assert.equal(out[0].corporation_sub_type, 'OVERSPEC')
  assert.equal('corporation_sub_type' in out[1], false)
})

test('carryOverSubTypes does not mutate its input', () => {
  const fresh = trimDirectory([dirEntry(10, 'Alpha')])
  carryOverSubTypes(fresh, [{ resource_id: 10, corporation_sub_type: 'OVERSPEC' }])
  assert.equal('corporation_sub_type' in fresh[0], false)
})

test('carryOverSubTypes passes through when there is no previous snapshot', () => {
  const fresh = trimDirectory([dirEntry(10, 'Alpha')])
  assert.deepEqual(carryOverSubTypes(fresh, null), fresh)
  assert.deepEqual(carryOverSubTypes(fresh, []), fresh)
})

test('carryOverSubTypes carries a previous null through as a determined answer', () => {
  const fresh = trimDirectory([dirEntry(10, 'Alpha')])
  const out = carryOverSubTypes(fresh, [{ resource_id: 10, corporation_sub_type: null }])
  assert.equal(out[0].corporation_sub_type, null)
  assert.deepEqual(missingSubTypeIds(out), [])
})

test('missingSubTypeIds reports an id whose key is genuinely absent from the previous snapshot', () => {
  const fresh = trimDirectory([dirEntry(10, 'Alpha'), dirEntry(20, 'Bravo')])
  const out = carryOverSubTypes(fresh, [{ resource_id: 10, corporation_sub_type: null }])
  assert.deepEqual(missingSubTypeIds(out), [20])
})

test('missingSubTypeIds lists only the ids the carry-over left empty', () => {
  const fresh = trimDirectory([dirEntry(10, 'Alpha'), dirEntry(20, 'Bravo')])
  const out = carryOverSubTypes(fresh, [{ resource_id: 10, corporation_sub_type: 'OVERSPEC' }])
  assert.deepEqual(missingSubTypeIds(out), [20])
})
