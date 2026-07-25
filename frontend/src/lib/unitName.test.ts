import { describe, it, expect } from 'vitest'
import { displayName, nameFromSlug } from './unitName'

describe('nameFromSlug', () => {
  it('title-cases each hyphenated word', () => {
    expect(nameFromSlug('ada-wong')).toBe('Ada Wong')
    expect(nameFromSlug('alice-wonderland-bunny')).toBe('Alice Wonderland Bunny')
    expect(nameFromSlug('crown')).toBe('Crown')
  })

  // Capitalising the first CHARACTER would leave these lowercase, since the
  // character is a digit.
  it('capitalises the first letter even when a digit comes first', () => {
    expect(nameFromSlug('2b')).toBe('2B')
    expect(nameFromSlug('a2')).toBe('A2')
  })
})

describe('displayName', () => {
  const names = new Map([['ada-wong', 'Ada Wong (Modernia)']])

  it('prefers the name the backend supplied', () => {
    expect(displayName('ada-wong', names)).toBe('Ada Wong (Modernia)')
  })

  // The 89 owned-but-unsupported units have no name anywhere in the frontend.
  it('falls back to the slug for a unit the backend does not know', () => {
    expect(displayName('alice-wonderland-bunny', names)).toBe('Alice Wonderland Bunny')
  })
})
