// ShiftyPad's static game tables live on a CDN under obfuscated paths: a logical
// path like `/equip/favorite_rare_map.json` is served as `/yb-61/<md5>.json`. The
// mapping is a pure function of the path, not a rotating manifest, so a table can
// be fetched directly over plain HTTP - no browser, no login, no page load.
//
// This replaced response interception for the collectible tables. Interception
// needs the SPA to actually request the file, and the collectible table is only
// fetched behind a logged-in Collection view, which is why the first attempt at
// capturing it came back empty and its values had to be derived from tooltips
// by hand (docs/engine-gaps.md #17).
//
// Transcribed from the app bundle (`index-*.js`): obfuscatedPath /
// createNormalObfuscatedPath / generateTwoLetterHash / generateTwoNumberHash /
// getDjb2Mod / str2md5. Two details matter:
//   - The djb2 accumulator is masked with `& 0xFFFFFFFF`, which in JS is a SIGNED
//     32-bit coercion. The `((h % p) + p) % p` that follows exists to undo the
//     resulting negatives, so both steps must be kept verbatim.
//   - Every path segment hashes the WHOLE path, not that segment - the directory
//     names are per-depth hashes of the same string with a different prime.
// `spine/` paths take a different branch in the bundle and are not modelled here.
const crypto = require('crypto')

const CDN_HOST = 'https://sg-tools-cdn.blablalink.com'
const LARGE_PRIMES = [224737, 1000639, 2654435761, 2654435769, 1000621, 4294967291]

const djb2Mod = (s, seed) => {
  let h = seed
  for (let i = 0; i < s.length; i++) h = (h * 33 + s.charCodeAt(i)) & 4294967295
  return h
}

const positiveMod = (s, prime) => ((djb2Mod(s, prime) % prime) + prime) % prime

const twoLetterHash = (s, prime) => {
  const r = positiveMod(s, prime)
  return String.fromCharCode(97 + (Math.floor(r / 26) % 26), 97 + (r % 26))
}

const twoNumberHash = (s, prime) => String(positiveMod(s, prime) % 99).padStart(2, '0')

// The obfuscated form of a logical path, without the CDN host.
const obfuscatedPath = (logicalPath) => {
  const path = logicalPath.replace(/^\//, '')
  if (path.startsWith('spine')) {
    throw new Error(`spine paths use a different scheme and are not supported: ${logicalPath}`)
  }
  const segments = path.split('/').filter(Boolean)
  return segments
    .map((segment, depth) => {
      if (depth < segments.length - 1) {
        return `${twoLetterHash(path, LARGE_PRIMES[depth])}-${twoNumberHash(path, LARGE_PRIMES[depth])}`
      }
      const [, ...extension] = segment.split('.')
      const digest = crypto.createHash('md5').update(path, 'utf8').digest('hex')
      return `${digest}.${extension.join('.')}`
    })
    .join('/')
}

const resourceUrl = (logicalPath) => `${CDN_HOST}/${obfuscatedPath(logicalPath)}`

const fetchResource = async (logicalPath) => {
  const url = resourceUrl(logicalPath)
  const response = await fetch(url)
  if (!response.ok) throw new Error(`GET ${logicalPath} -> ${response.status} (${url})`)
  return response.json()
}

module.exports = { CDN_HOST, obfuscatedPath, resourceUrl, fetchResource }
