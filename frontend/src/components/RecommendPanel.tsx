// Boss-profile input + "Recommend decks" action. Three modes share the same
// boss profile: single deck (POST /api/recommend, ranked alternatives), raid
// allocation (POST /api/recommend-raid, a partition of disjoint decks fielded
// together), and draft-based raid allocation (the same endpoint, seeded with
// the player's own key units via `draft` — frontend/README.md "Draft-based
// raid recommendation"). Only one mode's request is ever in flight.

import { useEffect, useId, useMemo, useState, type FormEvent } from 'react'
import { useRecommend } from '../hooks/useRecommend'
import { useRecommendRaid } from '../hooks/useRecommendRaid'
import { useSupportedUnits } from '../hooks/useSupportedUnits'
import {
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from '../types/bossProfileDraft'
import { makeEmptyDraft, MAX_DRAFT_SEATS_PER_DECK, type Draft } from '../types/draft'
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
import { DraftEditor, placeUnit, toRequestDraft } from './DraftEditor'
import { DraftPalette } from './DraftPalette'
import { DraftResults } from './DraftResults'
import { RaidResults } from './RaidResults'

interface RecommendPanelProps {
  /** The validated, ready subset of the entered roster. */
  roster: UserNikkeState[]
}

type RecommendMode = 'single' | 'raid' | 'draft'

const NUM_DECKS_OPTIONS = Array.from(
  { length: MAX_NUM_DECKS - MIN_NUM_DECKS + 1 },
  (_, i) => MIN_NUM_DECKS + i,
)

export function RecommendPanel({ roster }: RecommendPanelProps) {
  const [mode, setMode] = useState<RecommendMode>('single')
  const [numDecks, setNumDecks] = useState(DEFAULT_NUM_DECKS)
  const [draft, setDraft] = useState<BossProfileDraft>(makeDefaultBossProfileDraft())
  const [touched, setTouched] = useState(false)
  const [draftValue, setDraftValue] = useState<Draft>(() => makeEmptyDraft(DEFAULT_NUM_DECKS))
  const [submittedDraft, setSubmittedDraft] = useState<Draft>()
  // 'raid' and 'draft' share one useRecommendRaid() instance (same endpoint);
  // without tracking which mode actually produced the current result, the
  // OTHER mode's stale success/error would render just by switching the
  // mode radio, with no resubmission. Gates raid/draft result rendering below.
  const [raidResultMode, setRaidResultMode] = useState<'raid' | 'draft' | null>(null)
  const numDecksId = useId()

  const single = useRecommend()
  const raid = useRecommendRaid()
  const active = mode === 'single' ? single : raid
  const supportedUnits = useSupportedUnits()

  // The editor always shows exactly numDecks columns; growing/shrinking that
  // selector resizes the draft, preserving already-placed decks by index.
  useEffect(() => {
    setDraftValue((current) => ({
      decks: Array.from({ length: numDecks }, (_, i) => current.decks[i] ?? []),
    }))
  }, [numDecks])

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

  // Shrinking numDecks below this would silently drop already-drafted seats
  // (the resize effect truncates draftValue.decks to numDecks) — disable
  // those options instead of losing data with no warning.
  const nonEmptyDeckCount = draftValue.decks.filter((seats) => seats.length > 0).length

  const ownedSlugs = useMemo(() => roster.map((nikke) => nikke.character_slug), [roster])
  const usedSlugs = useMemo(
    () => draftValue.decks.flatMap((seats) => seats.map((seat) => seat.slug)),
    [draftValue],
  )

  const handlePick = (slug: string) => {
    const targetDeckIndex = draftValue.decks.findIndex(
      (seats) => seats.length < MAX_DRAFT_SEATS_PER_DECK,
    )
    if (targetDeckIndex === -1) return
    setDraftValue((current) => placeUnit(current, targetDeckIndex, slug))
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setTouched(true)
    if (!bossProfile || rosterTooSmall) return
    if (mode === 'single') {
      const request: RecommendRequest = { roster, boss: bossProfile }
      void single.submit(request)
    } else if (mode === 'raid') {
      const request: RecommendRaidRequest = { roster, boss: bossProfile, num_decks: numDecks }
      setRaidResultMode('raid')
      void raid.submit(request)
    } else {
      const request: RecommendRaidRequest = {
        roster,
        boss: bossProfile,
        num_decks: numDecks,
        draft: toRequestDraft(draftValue),
      }
      setSubmittedDraft(draftValue)
      setRaidResultMode('draft')
      void raid.submit(request)
    }
  }

  const submitLabel =
    mode === 'single'
      ? active.status === 'loading'
        ? 'Recommending…'
        : 'Recommend decks'
      : mode === 'raid'
        ? active.status === 'loading'
          ? 'Allocating…'
          : 'Allocate raid decks'
        : active.status === 'loading'
          ? 'Optimizing…'
          : 'Optimize draft'

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
            <label className="radio">
              <input
                type="radio"
                name="recommend-mode"
                value="draft"
                checked={mode === 'draft'}
                onChange={() => setMode('draft')}
              />
              Draft-based optimization
              <span className="group__hint">
                {' '}
                — seed decks with your own key units, the engine fills/optimizes the rest
              </span>
            </label>
          </div>

          {mode !== 'single' && (
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
                  <option key={n} value={n} disabled={n < nonEmptyDeckCount}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
          )}
        </fieldset>

        {mode === 'draft' && (
          <fieldset className="group">
            <legend className="group__legend">Draft</legend>
            <p className="group__hint">
              Seats are membership only — the engine assigns burst roles.
              Click a unit below to place it in the next open deck; lock a
              seat to force the engine to keep it there.
            </p>
            {supportedUnits.error && <p className="field__error">{supportedUnits.error}</p>}
            <DraftPalette
              ownedSlugs={ownedSlugs}
              supportedUnits={supportedUnits.units}
              usedSlugs={usedSlugs}
              onPick={handlePick}
            />
            <DraftEditor numDecks={numDecks} value={draftValue} onChange={setDraftValue} />
          </fieldset>
        )}

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

      {mode !== 'single' && raid.status === 'loading' && (
        <p className="recommend-form__progress" role="status">
          {mode === 'raid' ? 'Allocating raid decks' : 'Optimizing your draft'} — this runs
          thousands of simulations and typically takes 1–2 minutes. It&rsquo;s still working; the
          button will re-enable when it&rsquo;s done.
        </p>
      )}

      {mode === 'single' && single.status === 'error' && (
        <p className="field__error" role="alert">
          {single.error}
        </p>
      )}
      {mode !== 'single' && raid.status === 'error' && raidResultMode === mode && (
        <p className="field__error" role="alert">
          {raid.error}
        </p>
      )}

      {mode === 'single' && single.status === 'success' && (
        <DeckResults decks={single.decks} excludedSlugs={single.excludedSlugs} />
      )}
      {mode === 'raid' && raid.status === 'success' && raidResultMode === 'raid' && (
        <RaidResults
          decks={raid.decks}
          combinedTotalDamage={raid.combinedTotalDamage}
          excludedSlugs={raid.excludedSlugs}
          leftoverSlugs={raid.leftoverSlugs}
        />
      )}
      {mode === 'draft' && raid.status === 'success' && raidResultMode === 'draft' && (
        <DraftResults
          decks={raid.decks}
          combinedTotalDamage={raid.combinedTotalDamage}
          excludedSlugs={raid.excludedSlugs}
          leftoverSlugs={raid.leftoverSlugs}
          withinDraft={raid.withinDraft}
          baselineTotalDamage={raid.baselineTotalDamage}
          submittedDraft={submittedDraft}
        />
      )}
    </section>
  )
}
