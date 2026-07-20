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

  return (
    <span className="investment" title="Breakthrough and core enhancement">
      <span className="investment__stars">{filled + empty}</span>
      {core !== undefined && core > 0 && (
        <span className="investment__core">+{core}</span>
      )}
    </span>
  )
}
