// Boss-profile input + "Recommend decks" action. Two modes share the same
// boss profile: single deck (POST /api/recommend, ranked alternatives) and
// raid allocation (POST /api/recommend-raid, a partition of disjoint decks
// fielded together). Only one mode's request is ever in flight.

import { useId, useMemo, useState, type FormEvent } from 'react'
import { useRecommend } from '../hooks/useRecommend'
import { useRecommendRaid } from '../hooks/useRecommendRaid'
import {
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from '../types/bossProfileDraft'
import {
  DEFAULT_NUM_DECKS,
  MAX_NUM_DECKS,
  MIN_DECK_ROSTER_SIZE,
  MIN_NUM_DECKS,
  type RecommendRaidRequest,
  type RecommendRequest,
} from '../types/recommend'
import type { UserNikkeState } from '../types/userNikkeState'
import { BossProfileField } from './BossProfileField'
import { DeckResults } from './DeckResults'
import { RaidResults } from './RaidResults'

interface RecommendPanelProps {
  /** The validated, ready subset of the entered roster. */
  roster: UserNikkeState[]
}

type RecommendMode = 'single' | 'raid'

const NUM_DECKS_OPTIONS = Array.from(
  { length: MAX_NUM_DECKS - MIN_NUM_DECKS + 1 },
  (_, i) => MIN_NUM_DECKS + i,
)

export function RecommendPanel({ roster }: RecommendPanelProps) {
  const [mode, setMode] = useState<RecommendMode>('single')
  const [numDecks, setNumDecks] = useState(DEFAULT_NUM_DECKS)
  const [draft, setDraft] = useState<BossProfileDraft>(makeDefaultBossProfileDraft())
  const [touched, setTouched] = useState(false)
  const numDecksId = useId()

  const single = useRecommend()
  const raid = useRecommendRaid()
  const active = mode === 'single' ? single : raid

  const { errors, value: bossProfile } = useMemo(
    () => validateBossProfileDraft(draft),
    [draft],
  )

  // Burst-tier feasibility (tiers 1/2/3 all present) can only be checked
  // backend-side, since burst_tier is looked up from character_slug there,
  // not entered here. This roster-size check is necessary but not
  // sufficient — the backend still returns 422 for an infeasible roster.
  const rosterTooSmall = roster.length < MIN_DECK_ROSTER_SIZE
  const canSubmit = !rosterTooSmall && !!bossProfile && active.status !== 'loading'

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setTouched(true)
    if (!bossProfile || rosterTooSmall) return
    if (mode === 'single') {
      const request: RecommendRequest = { roster, boss: bossProfile }
      void single.submit(request)
    } else {
      const request: RecommendRaidRequest = { roster, boss: bossProfile, num_decks: numDecks }
      void raid.submit(request)
    }
  }

  const submitLabel =
    mode === 'single'
      ? active.status === 'loading'
        ? 'Recommending…'
        : 'Recommend decks'
      : active.status === 'loading'
        ? 'Allocating…'
        : 'Allocate raid decks'

  return (
    <section className="card" aria-label="Deck recommendation">
      <header className="card__header">
        <h2 className="card__title">Recommend decks</h2>
      </header>

      <form onSubmit={handleSubmit} className="recommend-form">
        <fieldset className="group">
          <legend className="group__legend">Mode</legend>
          <div className="mode-switch">
            <label className="radio">
              <input
                type="radio"
                name="recommend-mode"
                value="single"
                checked={mode === 'single'}
                onChange={() => setMode('single')}
              />
              Single deck
              <span className="group__hint"> — ranked alternatives for one deck</span>
            </label>
            <label className="radio">
              <input
                type="radio"
                name="recommend-mode"
                value="raid"
                checked={mode === 'raid'}
                onChange={() => setMode('raid')}
              />
              Raid allocation
              <span className="group__hint"> — multiple disjoint decks fielded together</span>
            </label>
          </div>

          {mode === 'raid' && (
            <div className="field">
              <label className="field__label" htmlFor={numDecksId}>
                Number of decks
              </label>
              <select
                id={numDecksId}
                className="field__input"
                value={numDecks}
                onChange={(event) => setNumDecks(Number(event.target.value))}
              >
                {NUM_DECKS_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
          )}
        </fieldset>

        <BossProfileField value={draft} errors={touched ? errors : {}} onChange={setDraft} />

        {rosterTooSmall && (
          <p className="field__error" role="alert">
            Add at least {MIN_DECK_ROSTER_SIZE} ready Nikkes to recommend a deck.
          </p>
        )}

        <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
          {submitLabel}
        </button>
      </form>

      {mode === 'raid' && raid.status === 'loading' && (
        <p className="recommend-form__progress" role="status">
          Allocating raid decks — this runs thousands of simulations and typically takes
          1–2 minutes. It&rsquo;s still working; the button will re-enable when it&rsquo;s done.
        </p>
      )}

      {mode === 'single' && single.status === 'error' && (
        <p className="field__error" role="alert">
          {single.error}
        </p>
      )}
      {mode === 'raid' && raid.status === 'error' && (
        <p className="field__error" role="alert">
          {raid.error}
        </p>
      )}

      {mode === 'single' && single.status === 'success' && (
        <DeckResults decks={single.decks} excludedSlugs={single.excludedSlugs} />
      )}
      {mode === 'raid' && raid.status === 'success' && (
        <RaidResults
          decks={raid.decks}
          combinedTotalDamage={raid.combinedTotalDamage}
          excludedSlugs={raid.excludedSlugs}
          leftoverSlugs={raid.leftoverSlugs}
        />
      )}
    </section>
  )
}
