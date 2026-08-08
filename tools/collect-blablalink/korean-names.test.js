const test = require('node:test')
const assert = require('node:assert')
const { nikkeListPath, mergeLocalisedNames } = require('./korean-names')

test('the ko list drops the language suffix the other locales carry', () => {
  // 앱 번들의 getLFormatLangUrl이 로케일 ko에서만 `_ko`를 지운다. 규칙대로
  // `/character/ko/nikke_list_ko_v2.json`을 부르면 **다른 파일**이 200으로 돌아온다
  // (더 짧은 154행짜리 구판)이라, 틀린 경로는 404가 아니라 낡은 데이터로 나타난다.
  assert.strictEqual(nikkeListPath('ko'), '/character/ko/nikke_list_v2.json')
  assert.strictEqual(nikkeListPath('en'), '/character/en/nikke_list_en_v2.json')
})

test('names join onto the snapshot by resource_id', () => {
  const entries = [
    { resource_id: 202, name_en: 'Dolla' },
    { resource_id: 10, name_en: 'Rapi' },
  ]
  const merged = mergeLocalisedNames(entries, new Map([[202, '도라'], [10, '라피']]))
  assert.deepStrictEqual(merged.map((e) => e.name_ko), ['도라', '라피'])
})

test('a unit the locale list does not carry gets no name_ko field at all', () => {
  // 빈 문자열을 넣으면 "이 유닛은 이름이 없다"와 "이번 수집에서 못 받았다"가
  // 구분되지 않는다 - 필드의 부재가 후자를 말한다.
  const merged = mergeLocalisedNames([{ resource_id: 999, name_en: 'Unreleased' }], new Map())
  assert.strictEqual('name_ko' in merged[0], false)
})

test('merging never mutates the entries it was handed', () => {
  const entries = [{ resource_id: 202, name_en: 'Dolla' }]
  mergeLocalisedNames(entries, new Map([[202, '도라']]))
  assert.strictEqual('name_ko' in entries[0], false)
})
