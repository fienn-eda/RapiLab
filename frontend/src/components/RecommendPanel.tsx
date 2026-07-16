// Boss-profile input + "Recommend decks" action: sends the current ready
// roster and boss profile to POST /api/recommend and renders the ranked
// results.

import { useMemo, useState, type FormEvent } from 'react'
import { useRecommend } from '../hooks/useRecommend'
import {
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from '../types/bossProfileDraft'
import { MIN_DECK_ROSTER_SIZE, type RecommendRequest } from '../types/recommend'
import type { UserNikkeState } from '../types/userNikkeState'
import { BossProfileField } from './BossProfileField'
import { DeckResults } from './DeckResults'

interface RecommendPanelProps {
  /** The validated, ready subset of the entered roster. */
  roster: UserNikkeState[]
}

export function RecommendPanel({ roster }: RecommendPanelProps) {
  const [draft, setDraft] = useState<BossProfileDraft>(makeDefaultBossProfileDraft())
  const [touched, setTouched] = useState(false)
  const { status, decks, excludedSlugs, error, submit } = useRecommend()

  const { errors, value: bossProfile } = useMemo(
    () => validateBossProfileDraft(draft),
    [draft],
  )

  // Burst-tier feasibility (tiers 1/2/3 all present) can only be checked
  // backend-side, since burst_tier is looked up from character_slug there,
  // not entered here. This roster-size check is necessary but not
  // sufficient — the backend still returns 422 for an infeasible roster.
  const rosterTooSmall = roster.length < MIN_DECK_ROSTER_SIZE
  const canSubmit = !rosterTooSmall && !!bossProfile && status !== 'loading'

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setTouched(true)
    if (!bossProfile || rosterTooSmall) return
    const request: RecommendRequest = { roster, boss: bossProfile }
    void submit(request)
  }

  return (
    <section className="card" aria-label="Deck recommendation">
      <header className="card__header">
        <h2 className="card__title">Recommend decks</h2>
      </header>

      <form onSubmit={handleSubmit} className="recommend-form">
        <BossProfileField value={draft} errors={touched ? errors : {}} onChange={setDraft} />

        {rosterTooSmall && (
          <p className="field__error" role="alert">
            Add at least {MIN_DECK_ROSTER_SIZE} ready Nikkes to recommend a deck.
          </p>
        )}

        <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
          {status === 'loading' ? 'Recommending…' : 'Recommend decks'}
        </button>
      </form>

      {status === 'error' && (
        <p className="field__error" role="alert">
          {error}
        </p>
      )}

      {status === 'success' && <DeckResults decks={decks} excludedSlugs={excludedSlugs} />}
    </section>
  )
}
