// The "not yet supported" note shared by DeckResults and RaidResults for
// submitted slugs the backend can't evaluate (not encoded / no local data).

import { nameFromSlug } from '../lib/unitName'

interface ExcludedSlugsNoteProps {
  excludedSlugs: string[]
}

export function ExcludedSlugsNote({ excludedSlugs }: ExcludedSlugsNoteProps) {
  if (excludedSlugs.length === 0) return null
  // These are exactly the slugs the backend has no unit for, so there is no
  // name to look up - deriving one from the slug is all there is.
  return (
    <p className="deck-results__excluded">
      아직 미지원 (탐색에서 제외됨): {excludedSlugs.map(nameFromSlug).join(', ')}
    </p>
  )
}
