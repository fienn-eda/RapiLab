// Shared warning for both raid-result views (RaidResults and DraftResults'
// complete-draft tiers): the swap hill-climb behind either can be cut off by
// SWAP_CANDIDATE_BUDGET, and the backend folds every allocate_decks call it
// made into one swap_converged flag.

interface SwapConvergenceNoteProps {
  /** false일 때만 경고한다 — 없으면(옛 저장 결과) 아무 말도 하지 않는다. */
  swapConverged?: boolean
}

export function SwapConvergenceNote({ swapConverged }: SwapConvergenceNoteProps) {
  if (swapConverged !== false) return null
  return (
    <p className="raid-results__note" role="status">
      탐색이 상한에 걸려 끝까지 가지 못했어요. 더 나은 배분이 남아 있을 수 있어요.
    </p>
  )
}
