import { describe, it, expect } from 'vitest'
import { NIKKE_ALIASES, aliasesFor } from './nikkeAliases'
import { RESOURCE_ID_TO_SLUG } from './resourceIdSlugMap'

describe('NIKKE_ALIASES', () => {
  // 키가 오타이거나 낡으면 그 별명은 예외 없이 조용히 아무것도 안 맞힌다 -
  // 검색이 "없는 니케"라고 답할 뿐이라 화면만 봐서는 표가 죽은 줄 모른다.
  it('모든 키가 실재하는 슬러그다', () => {
    const known = new Set(Object.values(RESOURCE_ID_TO_SLUG))
    // 애장품 변형(-signature)은 이 맵에 base로만 들어 있다.
    const base = (slug: string) => slug.replace(/-signature$/, '')

    const unknown = Object.keys(NIKKE_ALIASES).filter((slug) => !known.has(base(slug)))

    expect(unknown).toEqual([])
  })

  it('별명이 빈 문자열이거나 중복이지 않다', () => {
    for (const [slug, aliases] of Object.entries(NIKKE_ALIASES)) {
      expect(aliases.length, slug).toBeGreaterThan(0)
      expect(aliases.every((a) => a.trim() !== ''), slug).toBe(true)
      expect(new Set(aliases).size, slug).toBe(aliases.length)
    }
  })

  // 같은 별명이 두 니케를 가리키면 검색 결과가 둘 다 나와 아무것도 좁히지
  // 못한다. 별명은 사람들이 그 하나를 부르려고 쓰는 말이므로 겹치면 표가 틀린 것이다.
  it('두 니케가 같은 별명을 쓰지 않는다', () => {
    const seen = new Map<string, string>()
    const clashes: string[] = []
    for (const [slug, aliases] of Object.entries(NIKKE_ALIASES)) {
      for (const alias of aliases) {
        const owner = seen.get(alias)
        if (owner !== undefined) clashes.push(`${alias}: ${owner} vs ${slug}`)
        else seen.set(alias, slug)
      }
    }

    expect(clashes).toEqual([])
  })

  it('별명이 없는 슬러그에는 빈 배열을 준다', () => {
    expect(aliasesFor('rapi')).toEqual([])
  })
})
