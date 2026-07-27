const test = require('node:test')
const assert = require('node:assert')
const { obfuscatedPath, resourceUrl } = require('./resource-url')

// Observed on the wire: these three tables were captured by intercepting a
// ShiftyPad page load, so the pairing of logical path to served URL is a real
// reading, not a re-derivation of the code under test. They pin the whole
// scheme - the signed-32-bit djb2, the per-depth prime, and the md5 filename.
const OBSERVED = {
  '/character/AttractiveLevelTable.json': 'qe-66/cb6bd83fc9f961e0975612b760fbef8e.json',
  '/character/RecycleResearchStatTable.json': 'eu-96/258f853112b1d6f69d1508e12918ff3b.json',
  '/character/CharacterLevelTable.json': 'dv-15/e8b9e7f748f8734b2848842b47bf1cb2.json',
  '/equip/ko/favorite_100202.json': 'dl-61/cz-26/1d5f72120564cef28ac7889650c78a47.json',
}

test('obfuscated paths match what the CDN actually served', () => {
  for (const [logical, served] of Object.entries(OBSERVED)) {
    assert.strictEqual(obfuscatedPath(logical), served, logical)
  }
})

test('a leading slash is optional', () => {
  assert.strictEqual(
    obfuscatedPath('character/CharacterLevelTable.json'),
    obfuscatedPath('/character/CharacterLevelTable.json'),
  )
})

test('the directory segment hashes the whole path, not the segment', () => {
  // Same first segment, different full path -> different directory hash. If the
  // hash were per-segment these would collide.
  assert.notStrictEqual(
    obfuscatedPath('/equip/ko/favorite_100202.json').split('/')[1],
    obfuscatedPath('/equip/ko/favorite_100302.json').split('/')[1],
  )
})

test('spine paths are refused rather than silently mis-hashed', () => {
  assert.throws(() => obfuscatedPath('/spine/stand/c001/00/c001_00.skel.bytes'), /spine/)
})

test('resourceUrl prefixes the CDN host', () => {
  assert.ok(resourceUrl('/character/CharacterLevelTable.json').startsWith(
    'https://sg-tools-cdn.blablalink.com/'))
})
