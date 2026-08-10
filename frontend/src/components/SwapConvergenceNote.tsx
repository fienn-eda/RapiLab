// Shared warning for both raid-result views (RaidResults and DraftResults'
// complete-draft tiers): the swap hill-climb behind either can be cut off by
// SWAP_CANDIDATE_BUDGET, and the backend folds every allocate_decks call it
// made into one swap_converged flag.

import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'

interface SwapConvergenceNoteProps {
  /** false일 때만 경고한다 — 없으면(옛 저장 결과) 아무 말도 하지 않는다. */
  swapConverged?: boolean
}

export function SwapConvergenceNote({ swapConverged }: SwapConvergenceNoteProps) {
  if (swapConverged !== false) return null
  return (
    <p className="raid-results__note" role="status">
      <HelpText>{HELP.results.swapCutoff}</HelpText>
    </p>
  )
}
