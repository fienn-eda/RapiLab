import { describe, it, expect } from 'vitest'
import { NIKKE_ALIASES, aliasesFor } from './nikkeAliases'

// 키가 화면에 뜨는 슬러그와 일치하는지는 백엔드가 잡는다
// (backend/tests/test_nikke_aliases.py) - 거기서는 supported_units()를 직접 부를
// 수 있어, 모드 변형의 base까지 포함한 진짜 목록과 대조할 수 있다. 여기서는
// 표 자체의 형식만 본다.
describe('NIKKE_ALIASES', () => {
  it('별명이 빈 문자열이 아니고 한 니케 안에서 겹치지 않는다', () => {
    for (const [slug, aliases] of Object.entries(NIKKE_ALIASES)) {
      // 빈 배열은 정상이다 - "아직 안 채운 자리"이고, 그 자리가 있어야 채울 수 있다.
      expect(aliases.every((a) => a.trim() !== ''), slug).toBe(true)
      expect(new Set(aliases).size, slug).toBe(aliases.length)
    }
  })

  // 같은 별명이 서로 다른 니케를 가리키는지는 백엔드가 잡는다
  // (backend/tests/test_nikke_aliases.py). 애장품 변형(-signature)과 모드
  // 변형은 같은 니케의 다른 빌드라 별명이 겹치는 것이 정상인데, 그 관계는
  // MODE_VARIANTS를 아는 쪽에서만 판정할 수 있다.

  // 별명이 공식 이름의 부분문자열이면 그 줄은 아무 일도 하지 않는다 - 이름
  // 부분일치가 이미 맞히기 때문이다. 표에 죽은 줄이 쌓이는 것을 막는다.
  it('별명이 그 니케의 슬러그에 이미 들어 있지 않다', () => {
    const redundant: string[] = []
    for (const [slug, aliases] of Object.entries(NIKKE_ALIASES)) {
      for (const alias of aliases) {
        if (slug.includes(alias.toLowerCase())) redundant.push(`${slug}: ${alias}`)
      }
    }

    expect(redundant).toEqual([])
  })

  it('별명이 없는 슬러그에는 빈 배열을 준다', () => {
    expect(aliasesFor('rapi')).toEqual([])
    expect(aliasesFor('scarlet-black-shadow')).toContain('흑련')
  })
})
