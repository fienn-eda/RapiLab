// Deterministic cache key for a recommend-raid request. The engine has no
// RNG, so two requests with the same roster investment data, boss profile,
// and draft always produce the same result - this hash lets us skip
// recomputing it. Normalizes away orderings that don't affect the result
// (roster array order, seat order within a draft deck) so equivalent
// requests collide on purpose, and canonicalizes object key order so
// structurally-equal values always serialize identically.

import type { UserNikkeState } from '../types/userNikkeState'
import type { BossProfile } from '../types/recommend'
import type { Draft } from '../types/draft'

// FNV-1a, 32-bit. No external dependency; a hash collision just costs a
// cache miss (recompute), so 32 bits of collision resistance is plenty.
const fnv1a = (input: string): string => {
  let hash = 0x811c9dc5
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i)
    hash = Math.imul(hash, 0x01000193)
  }
  return (hash >>> 0).toString(16).padStart(8, '0')
}

/** Recursively sorts object keys so property insertion order can't affect serialization. */
const canonicalize = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (value !== null && typeof value === 'object') {
    const record = value as Record<string, unknown>
    const sorted: Record<string, unknown> = {}
    for (const key of Object.keys(record).sort()) {
      sorted[key] = canonicalize(record[key])
    }
    return sorted
  }
  return value
}

const canonicalRoster = (roster: UserNikkeState[]): unknown =>
  [...roster]
    .sort((a, b) => a.character_slug.localeCompare(b.character_slug))
    .map(canonicalize)

const canonicalDraft = (draft: Draft | null): unknown => {
  if (draft === null) return null
  return {
    decks: draft.decks.map((seats) =>
      [...seats].sort((a, b) => a.slug.localeCompare(b.slug)).map(canonicalize),
    ),
  }
}

export const hashRecommendInputs = (
  roster: UserNikkeState[],
  boss: BossProfile,
  draft: Draft | null,
  numDecks: number,
): string => {
  const canonical = {
    roster: canonicalRoster(roster),
    boss: canonicalize(boss),
    draft: canonicalDraft(draft),
    numDecks,
  }
  return fnv1a(JSON.stringify(canonical))
}
