// Read-only display of a unit's breakthrough (grade) and core enhancement.
// Both are inputs to the backend's ATK/HP calculation and are already folded
// into the imported stats, so this is informational only - it exists so the
// user can confirm their roster imported correctly.

const STAR_SLOTS = 3

interface InvestmentBadgeProps {
  grade?: number
  core?: number
}

export function InvestmentBadge({ grade, core }: InvestmentBadgeProps) {
  // Absent is not zero: a manually entered draft has no grade, and drawing
  // empty stars for it would claim a fact we do not have.
  if (grade === undefined) return null

  const filled = '★'.repeat(grade)
  const empty = '☆'.repeat(Math.max(0, STAR_SLOTS - grade))

  // Breakthrough and core read as one fact ("how far is this unit built?"), so
  // they share one badge. Both star glyphs are gold: an unfilled slot is an
  // outline, which is already the difference - splitting the colours would
  // mean splitting the string into elements that each duplicate the whole.
  return (
    <span className="investment" title="Breakthrough and core enhancement">
      <span className="investment__stars">{filled + empty}</span>
      {core !== undefined && core > 0 && (
        <span className="investment__core">+{core}</span>
      )}
    </span>
  )
}
