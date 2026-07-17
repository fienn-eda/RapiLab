// The "not yet supported" note shared by DeckResults and RaidResults for
// submitted slugs the backend can't evaluate (not encoded / no local data).

interface ExcludedSlugsNoteProps {
  excludedSlugs: string[]
}

export function ExcludedSlugsNote({ excludedSlugs }: ExcludedSlugsNoteProps) {
  if (excludedSlugs.length === 0) return null
  return (
    <p className="deck-results__excluded">
      Not yet supported (excluded from search): {excludedSlugs.join(', ')}
    </p>
  )
}
