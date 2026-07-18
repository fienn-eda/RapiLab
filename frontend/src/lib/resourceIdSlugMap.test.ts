import { describe, it, expect } from 'vitest'
import {
  RESOURCE_ID_TO_SLUG,
  SIGNATURE_OWNED,
  DUAL_SLOT_BASES,
  resolveSlugForUnit,
} from './resourceIdSlugMap'

describe('RESOURCE_ID_TO_SLUG (identity, investment-free)', () => {
  it('maps unambiguous units by resource_id', () => {
    expect(RESOURCE_ID_TO_SLUG[16]).toBe('rapi-red-hood')
    expect(RESOURCE_ID_TO_SLUG[74]).toBe('soline-frost-ticket')
    expect(RESOURCE_ID_TO_SLUG[322]).toBe('marciana-marine-study')
  })

  it('disambiguates the three "Rei" units by resource_id', () => {
    expect(RESOURCE_ID_TO_SLUG[831]).toBe('rei-ayanami') // 레이
    expect(RESOURCE_ID_TO_SLUG[834]).toBe('rei-ayanami-tentative-name')
    expect(RESOURCE_ID_TO_SLUG[392]).toBeUndefined() // 라이 — 별개 캐릭터, 미인코딩
  })

  it('keeps the two SSR Neon variants distinct and drops the unencoded one', () => {
    expect(RESOURCE_ID_TO_SLUG[18]).toBe('neon-vision-eye')
    expect(RESOURCE_ID_TO_SLUG[14]).toBeUndefined() // Neon: Blue Ocean, not encoded
  })

  it('excludes base units whose only encoded form is a variant', () => {
    expect(RESOURCE_ID_TO_SLUG[71]).toBeUndefined() // base Soline
    expect(RESOURCE_ID_TO_SLUG[321]).toBeUndefined() // base Marciana
  })

  it('stores dual-slot units as their BASE slug (no investment baked in)', () => {
    expect(RESOURCE_ID_TO_SLUG[101]).toBe('drake')
    expect(RESOURCE_ID_TO_SLUG[150]).toBe('julia')
  })
})

describe('resolveSlugForUnit (identity + investment)', () => {
  it('promotes a dual-slot base to -signature when the Favorite Item is owned', () => {
    expect(SIGNATURE_OWNED.has(101)).toBe(true) // Drake: owned
    expect(resolveSlugForUnit(101)).toBe('drake-signature')
  })

  it('leaves a dual-slot base alone when the Favorite Item is not owned', () => {
    expect(SIGNATURE_OWNED.has(150)).toBe(false) // Julia: uninvested
    expect(resolveSlugForUnit(150)).toBe('julia')
  })

  it('never promotes a non-dual-slot unit even if flagged owned', () => {
    expect(DUAL_SLOT_BASES.has('rapi-red-hood')).toBe(false)
    expect(resolveSlugForUnit(16)).toBe('rapi-red-hood')
  })

  it('returns undefined for unmapped or missing ids', () => {
    expect(resolveSlugForUnit(71)).toBeUndefined()
    expect(resolveSlugForUnit(undefined)).toBeUndefined()
  })
})
