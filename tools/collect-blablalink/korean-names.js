// 한국 서버 공식 표기(`name_ko`)를 nikke-directory.json에 채운다.
//
// ShiftyPad의 캐릭터 목록은 로케일마다 별도 파일로 서빙된다. 앱 번들의
// `getLFormatLangUrl('/character/{l_lang}/nikke_list_{lang}_v2.json')`이 `{l_lang}`을
// 로케일로, `{lang}`을 언어로 치환하되 **로케일이 ko면 `_ko`를 지워서**
// `/character/ko/nikke_list_v2.json`이 된다. 그래서 한글 이름은 인터셉트로 잡히는
// 영문 목록이 아니라 이 경로에 있다 — 오래도록 "blablalink에는 한글 이름이 없다"고
// 알려져 있었던 이유다.
//
// 순수 CDN 경로 계산(resource-url.js)이라 **브라우저도 세션도 필요 없다**.
//
// 사용:
//   node korean-names.js            nikke-directory.json에 name_ko를 채워 넣는다
//   node korean-names.js --check    쓰지 않고 빠진 것만 보고한다(종료코드 1이면 미반영)
//   node korean-names.js --print <resource_id|이름조각> ...   한 줄씩 조회
const fs = require('fs')
const path = require('path')
const { fetchResource } = require('./resource-url')

// 로케일이 ko면 파일명에서 _ko가 빠진다(앱 번들의 getLFormatLangUrl과 같은 규칙).
const nikkeListPath = (locale) =>
  locale === 'ko'
    ? '/character/ko/nikke_list_v2.json'
    : `/character/${locale}/nikke_list_${locale}_v2.json`

// resource_id -> 로케일 표기. 이름이 없는 엔트리(미공개 슬롯)는 버린다.
const fetchLocalisedNames = async (locale = 'ko') => {
  const list = await fetchResource(nikkeListPath(locale))
  const names = new Map()
  for (const entry of list) {
    const name = entry.name_localkey && entry.name_localkey.name
    if (name) names.set(entry.resource_id, name)
  }
  return names
}

// 스냅샷 엔트리에 name_ko를 붙인다. 목록에 없는 유닛은 필드 없이 그대로 둔다 —
// 빈 문자열을 넣으면 "이름이 없다"와 "아직 못 받았다"를 구분할 수 없게 된다.
const mergeLocalisedNames = (entries, names) =>
  entries.map((entry) =>
    names.has(entry.resource_id)
      ? { ...entry, name_ko: names.get(entry.resource_id) }
      : entry,
  )

const SNAPSHOT = path.join(__dirname, 'nikke-directory.json')

const main = async () => {
  const args = process.argv.slice(2)
  const names = await fetchLocalisedNames('ko')

  if (args[0] === '--print') {
    const wanted = args.slice(1)
    if (!wanted.length) throw new Error('--print 뒤에 resource_id나 이름 조각을 달 것')
    for (const want of wanted) {
      const hits = /^\d+$/.test(want)
        ? [[Number(want), names.get(Number(want))]].filter(([, n]) => n)
        : [...names].filter(([, n]) => n.includes(want))
      if (!hits.length) console.log(`${want}\t(없음)`)
      for (const [id, name] of hits) console.log(`${id}\t${name}`)
    }
    return
  }

  const entries = JSON.parse(fs.readFileSync(SNAPSHOT, 'utf8'))
  const merged = mergeLocalisedNames(entries, names)
  const filled = merged.filter((e) => e.name_ko).length
  const missing = merged.filter((e) => !e.name_ko).map((e) => `${e.resource_id} ${e.name_en}`)

  if (args.includes('--check')) {
    const stale = entries.filter((e, i) => e.name_ko !== merged[i].name_ko)
    console.log(`name_ko: ${filled}/${merged.length} (한국어 목록 ${names.size}개)`)
    if (missing.length) console.log(`한국어 목록에 없는 유닛: ${missing.join(', ')}`)
    if (stale.length) {
      console.log(`스냅샷과 다른 엔트리 ${stale.length}개 — 인자 없이 다시 실행할 것`)
      process.exitCode = 1
    }
    return
  }

  fs.writeFileSync(SNAPSHOT, `${JSON.stringify(merged, null, 2)}\n`)
  console.log(`wrote ${path.basename(SNAPSHOT)}: name_ko ${filled}/${merged.length}`)
  if (missing.length) console.log(`한국어 목록에 없는 유닛: ${missing.join(', ')}`)
}

module.exports = { nikkeListPath, fetchLocalisedNames, mergeLocalisedNames }

if (require.main === module) {
  main().catch((e) => {
    console.error('KOREAN_NAMES_ERROR:', e.message)
    process.exit(1)
  })
}
