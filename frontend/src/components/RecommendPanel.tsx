// Boss-profile input + "Recommend decks" action. Three modes share the same
// boss profile: single deck (POST /api/recommend, ranked alternatives), raid
// allocation (POST /api/recommend-raid, a partition of disjoint decks fielded
// together), and draft-based raid allocation (the same endpoint, seeded with
// the player's own key units via `draft` — frontend/README.md "Draft-based
// raid recommendation"). Only one mode's request is ever in flight.

import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from 'react'
import { useRecommend } from '../hooks/useRecommend'
import { useRecommendRaid } from '../hooks/useRecommendRaid'
import { usePortraitManifest } from '../hooks/usePortraitManifest'
import { useSupportedUnits } from '../hooks/useSupportedUnits'
import { nameFromSlug, withFavoriteItem } from '../lib/unitName'
import { ownedSlugFor, ownedSlugIndex } from '../types/supportedUnit'
import { hashRecommendInputs } from '../lib/inputHash'
import {
  bossProfileToDraft,
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from '../types/bossProfileDraft'
import { makeEmptyDraft, type Draft } from '../types/draft'
import type { StoredInputs, StoredResult } from '../types/profile'
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
import { DraftEditor, removeUnitBySlug, toRequestDraft } from './DraftEditor'
import { DraftResults } from './DraftResults'
import { RaidResults } from './RaidResults'
import { UnitPalette, type UnitInvestment } from './UnitPalette'

interface RecommendPanelProps {
  /** The validated, ready subset of the entered roster. */
  roster: UserNikkeState[]
  /** The active profile's open_id — keys the restore effect so switching
   * accounts (not just re-rendering) reloads that profile's form/result. */
  activeOpenId: string | null
  /** Looks up a cached raid/draft result by inputHash — a hit skips the
   * network call entirely (see lib/inputHash.ts). */
  getCached: (hash: string) => StoredResult | null
  /** Called exactly once per raid/draft submit that actually reaches the
   * backend, so the caller can persist it into the active profile. */
  onResult: (args: { hash: string; result: StoredResult; inputs: StoredInputs }) => void
  /** The active profile's last submitted raid/draft inputs, to repopulate the
   * form - null when the profile has never submitted one. */
  restoreInputs: StoredInputs | null
  /** The stored result for restoreInputs' hash - null alongside it. */
  restoreResult: StoredResult | null
  /** Breakthrough/core per slug, for the palette chips. Not part of the
   * roster: UserNikkeState mirrors the backend model, which has neither. */
  investmentFor?: (slug: string) => UnitInvestment
  /** The result cache's invalidation axis - lib/inputHash.ts. Null until the
   * backend has answered. */
  engineVersion: string | null
}

type RecommendMode = 'single' | 'raid' | 'draft'

/** Maps the useRecommendRaid hook's success fields to the cacheable shape -
 * both raid and draft submits persist through this. */
const toStoredResult = (raid: {
  decks: StoredResult['decks']
  combinedTotalDamage: number
  excludedSlugs: string[]
  leftoverSlugs: string[]
  withinDraft: StoredResult['withinDraft']
  baselineTotalDamage: number | null
}): StoredResult => ({
  decks: raid.decks,
  combinedTotalDamage: raid.combinedTotalDamage,
  excludedSlugs: raid.excludedSlugs,
  leftoverSlugs: raid.leftoverSlugs,
  withinDraft: raid.withinDraft,
  baselineTotalDamage: raid.baselineTotalDamage,
})

const NUM_DECKS_OPTIONS = Array.from(
  { length: MAX_NUM_DECKS - MIN_NUM_DECKS + 1 },
  (_, i) => MIN_NUM_DECKS + i,
)

export function RecommendPanel({
  roster,
  activeOpenId,
  getCached,
  onResult,
  restoreInputs,
  restoreResult,
  investmentFor,
  engineVersion,
}: RecommendPanelProps) {
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
  // Unified raid/draft result display - populated either by a fresh
  // raid.submit() success or by a cache hit / restore, so rendering doesn't
  // care which of those produced it (see toStoredResult/getCached below).
  const [displayResult, setDisplayResult] = useState<StoredResult | null>(null)
  const [displayMode, setDisplayMode] = useState<'raid' | 'draft' | null>(null)
  // Ephemeral per-request exclusions from the search pool — NOT persisted,
  // reset whenever the active profile changes (see the restore effect).
  const [excludedSlugs, setExcludedSlugs] = useState<Set<string>>(new Set())
  // Set right before a raid/draft raid.submit() call that actually reaches
  // the backend (a cache hit never sets it), and cleared once its success is
  // persisted via onResult - the guard that makes persistence exactly-once
  // per submit rather than re-firing on unrelated rerenders.
  const pendingSaveRef = useRef<{ hash: string; inputs: StoredInputs } | null>(null)
  const numDecksId = useId()

  const single = useRecommend()
  const raid = useRecommendRaid()
  const active = mode === 'single' ? single : raid
  const supportedUnits = useSupportedUnits()
  const { portraitFor } = usePortraitManifest()

  // Restore the active profile's last raid/draft submission (form + result)
  // whenever the ACCOUNT changes, not on every render - keyed on
  // activeOpenId alone so it never clobbers in-progress edits mid-typing.
  useEffect(() => {
    setExcludedSlugs(new Set())
    if (restoreInputs && restoreResult) {
      setMode(restoreInputs.mode)
      setNumDecks(restoreInputs.numDecks)
      setDraft(bossProfileToDraft(restoreInputs.boss))
      setDraftValue(restoreInputs.draft ?? makeEmptyDraft(restoreInputs.numDecks))
      setSubmittedDraft(restoreInputs.mode === 'draft' ? (restoreInputs.draft ?? undefined) : undefined)
      setRaidResultMode(restoreInputs.mode)
      setDisplayResult(restoreResult)
      setDisplayMode(restoreInputs.mode)
    } else {
      setDisplayResult(null)
      setDisplayMode(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOpenId])

  // Persist a raid/draft submission's success exactly once - guarded by
  // pendingSaveRef so a rerender that doesn't follow a fresh submit (e.g. a
  // parent passing a new onResult reference) can't re-save the same result.
  const { status: raidStatus, decks, combinedTotalDamage, excludedSlugs: raidExcludedSlugs, leftoverSlugs, withinDraft, baselineTotalDamage } = raid
  useEffect(() => {
    if (raidStatus !== 'success') return
    const pending = pendingSaveRef.current
    if (!pending) return

    const result = toStoredResult({
      decks,
      combinedTotalDamage,
      excludedSlugs: raidExcludedSlugs,
      leftoverSlugs,
      withinDraft,
      baselineTotalDamage,
    })
    setDisplayResult(result)
    setDisplayMode(pending.inputs.mode)
    onResult({ hash: pending.hash, result, inputs: pending.inputs })
    pendingSaveRef.current = null
  }, [
    raidStatus,
    decks,
    combinedTotalDamage,
    raidExcludedSlugs,
    leftoverSlugs,
    withinDraft,
    baselineTotalDamage,
    onResult,
  ])

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

  // The roster after per-request exclusions — what actually gets sent to the
  // engine. `ownedSlugs` below stays on the full roster so the palette can
  // still show (and re-include) excluded units.
  const effectiveRoster = useMemo(
    () => roster.filter((nikke) => !excludedSlugs.has(nikke.character_slug)),
    [roster, excludedSlugs],
  )

  // Burst-tier feasibility (tiers 1/2/3 all present) can only be checked
  // backend-side, since burst_tier is looked up from character_slug there,
  // not entered here. This roster-size check is necessary but not
  // sufficient — the backend still returns 422 for an infeasible roster.
  const rosterTooSmall = effectiveRoster.length < MIN_DECK_ROSTER_SIZE
  const canSubmit = !rosterTooSmall && !!bossProfile && active.status !== 'loading'

  // Shrinking numDecks below this would silently drop already-drafted seats
  // (the resize effect truncates draftValue.decks to numDecks) — disable
  // those options instead of losing data with no warning.
  const nonEmptyDeckCount = draftValue.decks.filter((seats) => seats.length > 0).length

  const usedSlugs = useMemo(
    () => draftValue.decks.flatMap((seats) => seats.map((seat) => seat.slug)),
    [draftValue],
  )

  // Deck slots show a face and nothing else, so what a slot IS comes from
  // here: the name labels its controls, the burst tier is the one badge it
  // draws. Both degrade to the slug / no badge when /api/supported-units is
  // unavailable, which is the same fallback the palette already makes.
  const unitIndex = useMemo(
    () => new Map(supportedUnits.units.map((unit) => [unit.slug, unit])),
    [supportedUnits.units],
  )
  // What the palette actually draws, and therefore what the search really
  // ranges over: owned AND engine-supported. Counting the whole roster claimed
  // 159 units were in the pool while showing 70 chips. The unsupported ones
  // are still sent - the backend drops them and names them in excluded_slugs -
  // so this corrects the claim without changing the request.
  const poolTotal = useMemo(
    () => roster.filter((nikke) => unitIndex.has(nikke.character_slug)).length,
    [roster, unitIndex],
  )
  const poolIncluded = useMemo(
    () =>
      roster.filter(
        (nikke) =>
          unitIndex.has(nikke.character_slug) && !excludedSlugs.has(nikke.character_slug),
      ).length,
    [roster, unitIndex, excludedSlugs],
  )
  // Before the list arrives (or if it never does) there is no intersection to
  // report, so fall back to the roster rather than claiming a pool of zero.
  const poolKnown = unitIndex.size > 0
  const unsupportedCount = roster.length - poolTotal

  // A drafted character whose mode the engine picks comes back under a
  // different slug (`bready` -> `bready-lingering`), so reconciling the
  // submitted draft with the result has to compare owned characters.
  const ownedSlugs = useMemo(
    () => ownedSlugIndex(supportedUnits.units),
    [supportedUnits.units],
  )
  const ownedSlugResolver = useMemo(
    () => (slug: string) => ownedSlugFor(slug, ownedSlugs),
    [ownedSlugs],
  )

  // A result names ENGINE slugs, so the Favorite Item flag - which rides on the
  // roster, keyed by the slug the player owns - is looked up through
  // ownedSlugResolver (bready-lingering -> bready; helm-signature is already
  // the owned slug and passes through). Everywhere this name lands is text-only
  // (deck rosters, the bench line, a draft seat), so the heart is part of the
  // string; where there is art to put it on, FavoriteItemBadge does it instead.
  const nameFor = (slug: string) =>
    withFavoriteItem(
      unitIndex.get(slug)?.name ?? nameFromSlug(slug),
      investmentFor?.(ownedSlugResolver(slug))?.favoriteItem,
    )
  const burstTierFor = (slug: string) => unitIndex.get(slug)?.burstTier ?? null

  const toggleExclude = (slug: string) => {
    if (!excludedSlugs.has(slug)) {
      // Excluding a unit also unplaces it from the draft.
      setDraftValue((current) => removeUnitBySlug(current, slug))
    }
    setExcludedSlugs((prev) => {
      const next = new Set(prev)
      if (next.has(slug)) next.delete(slug)
      else next.add(slug)
      return next
    })
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setTouched(true)
    if (!bossProfile || rosterTooSmall) return
    if (mode === 'single') {
      const request: RecommendRequest = { roster: effectiveRoster, boss: bossProfile }
      void single.submit(request)
      return
    }

    if (mode === 'draft') setSubmittedDraft(draftValue)
    setRaidResultMode(mode)
    // Clear any previously displayed result up front, before the cache
    // check - otherwise a resubmit that genuinely fails (cache miss) would
    // leave a stale success on screen while the error banner is suppressed
    // by the `displayResult && displayMode === mode` guard below. A cache
    // hit re-sets both immediately after; a fresh submit leaves them null
    // through loading and, on failure, lets the error banner show.
    setDisplayResult(null)
    setDisplayMode(null)

    // Only raid/draft cache — the engine is deterministic, so identical
    // roster/boss/draft/numDecks/engineVersion always reproduces the same
    // result, and a hit means we can skip the (slow,
    // thousands-of-simulations) request.
    const draftForHash = mode === 'draft' ? draftValue : null
    const hash = hashRecommendInputs(
      effectiveRoster,
      bossProfile,
      draftForHash,
      numDecks,
      engineVersion,
    )
    const cached = getCached(hash)
    if (cached) {
      setDisplayResult(cached)
      setDisplayMode(mode)
      return
    }

    pendingSaveRef.current = {
      hash,
      inputs: { mode, numDecks, boss: bossProfile, draft: draftForHash },
    }

    if (mode === 'raid') {
      const request: RecommendRaidRequest = { roster: effectiveRoster, boss: bossProfile, num_decks: numDecks }
      void raid.submit(request)
    } else {
      const request: RecommendRaidRequest = {
        roster: effectiveRoster,
        boss: bossProfile,
        num_decks: numDecks,
        draft: toRequestDraft(draftValue),
      }
      void raid.submit(request)
    }
  }

  const submitLabel =
    mode === 'single'
      ? active.status === 'loading'
        ? '추천 중…'
        : '덱 추천'
      : mode === 'raid'
        ? active.status === 'loading'
          ? '배분 중…'
          : '레이드 덱 배분'
        : active.status === 'loading'
          ? '최적화 중…'
          : '드래프트 최적화'

  return (
    <section className="card" aria-label="덱 추천">
      <header className="card__header">
        <h2 className="card__title">덱 추천</h2>
      </header>

      <form onSubmit={handleSubmit} className="recommend-form">
        {/* Everything needed to START a run sits in one row: the boss on the
            left, the mode choice and Submit on the right. The boss fields used
            to close the form instead, 2040px below the button that acts on
            them with the whole 70-chip palette in between - so the input that
            moves the answer most (Element) was the one a player never scrolled
            to, and a minute of simulation ran against a default nobody chose. */}
        <div className="recommend-form__setup">
          <BossProfileField value={draft} errors={touched ? errors : {}} onChange={setDraft} />

          <fieldset className="group">
            <legend className="group__legend">모드</legend>
            <div className="mode-switch">
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="single"
                  checked={mode === 'single'}
                  onChange={() => setMode('single')}
                />
                단일 덱
                <span className="group__hint"> — 덱 하나의 순위별 대안</span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="raid"
                  checked={mode === 'raid'}
                  onChange={() => setMode('raid')}
                />
                레이드 배분
                <span className="group__hint"> — 여러 개의 겹치지 않는 덱을 동시에 편성</span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="draft"
                  checked={mode === 'draft'}
                  onChange={() => setMode('draft')}
                />
                드래프트 기반 최적화
                <span className="group__hint">
                  {' '}
                  — 직접 고른 핵심 유닛으로 덱을 시드하면, 엔진이 나머지를 채우고
                  최적화해요
                </span>
              </label>
            </div>

            {mode !== 'single' && (
              <div className="field">
                <label className="field__label" htmlFor={numDecksId}>
                  덱 개수
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

            {/* Submit sits with the mode choice rather than after the boss
                fields: the palette and deck grid between them run long, and the
                player should not have to scroll past their whole roster to
                start a run they have already configured. */}
            <div className="recommend-form__actions">
              <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
                {submitLabel}
              </button>
              {/* Only while something is actually running - a permanent Cancel
                  next to Submit would read as a choice between two actions.
                  `type="button"` matters: inside a form, a bare button submits,
                  which would start a second run instead of stopping the first. */}
              {active.status === 'loading' && (
                <button type="button" className="btn" onClick={active.cancel}>
                  취소
                </button>
              )}
              {rosterTooSmall && (
                <p className="field__error" role="alert">
                  덱을 추천하려면 준비된 니케가 최소 {MIN_DECK_ROSTER_SIZE}기 필요해요.
                </p>
              )}
            </div>
          </fieldset>
        </div>

        {mode !== 'draft' && (
          <fieldset className="group">
            <legend className="group__legend">사용할 유닛</legend>
            {/* Default-expanded (discoverable) but collapsible. `open` also keeps the
                unit toggles in the a11y tree for tests without a jsdom details toggle. */}
            <details className="group__details" open>
              <summary className="group__hint">
                {poolKnown ? poolIncluded : effectiveRoster.length}/
                {poolKnown ? poolTotal : roster.length} 탐색 풀에 포함됨 — 편성하지
                않을 유닛을 클릭하면 제외돼요
                {poolKnown && unsupportedCount > 0 && (
                  <> (보유 중이나 아직 미지원 {unsupportedCount}기)</>
                )}
              </summary>
              {supportedUnits.error && <p className="field__error">{supportedUnits.error}</p>}
              <UnitPalette
                roster={roster}
                supportedUnits={supportedUnits.units}
                excludedSlugs={[...excludedSlugs]}
                onToggleExclude={toggleExclude}
                investmentFor={investmentFor}
              />
            </details>
          </fieldset>
        )}

        {mode === 'draft' && (
          <fieldset className="group">
            <legend className="group__legend">드래프트</legend>
            {/* How to seat a unit is explained beside the decks themselves
                (DraftEditor's hint), where the player is looking when they
                need it. */}
            {supportedUnits.error && <p className="field__error">{supportedUnits.error}</p>}
            {/* Palette left, decks right: dragging a unit into a deck only
                works if both are on screen at once. */}
            <div className="draft-layout">
              <UnitPalette
                roster={roster}
                supportedUnits={supportedUnits.units}
                usedSlugs={usedSlugs}
                draggable
                excludedSlugs={[...excludedSlugs]}
                onToggleExclude={toggleExclude}
                investmentFor={investmentFor}
              />
              <div className="draft-layout__decks">
                <DraftEditor
                  numDecks={numDecks}
                  value={draftValue}
                  onChange={setDraftValue}
                  portraitFor={portraitFor}
                  nameFor={nameFor}
                  burstTierFor={burstTierFor}
                />
              </div>
            </div>
          </fieldset>
        )}
      </form>

      {mode !== 'single' && raid.status === 'loading' && (
        <p className="recommend-form__progress" role="status">
          {mode === 'raid' ? '레이드 덱 배분 중' : '드래프트 최적화 중'} — 수천 번의
          시뮬레이션을 실행하며 보통 1~2분이 걸려요. 아직 진행 중이니 완료되면
          버튼이 다시 활성화돼요.
        </p>
      )}

      {mode === 'single' && single.status === 'error' && (
        <p className="field__error" role="alert">
          {single.error}
        </p>
      )}
      {/* A cache hit sets displayResult without touching raid.status, so a
          stale error from an earlier, different submit must not outrank it. */}
      {mode !== 'single' &&
        raid.status === 'error' &&
        raidResultMode === mode &&
        !(displayResult && displayMode === mode) && (
          <p className="field__error" role="alert">
            {raid.error}
          </p>
        )}

      {mode === 'single' && single.status === 'success' && (
        <DeckResults
          decks={single.decks}
          excludedSlugs={single.excludedSlugs}
          portraitFor={portraitFor}
          nameFor={nameFor}
        />
      )}
      {mode === 'raid' && displayResult && displayMode === 'raid' && (
        <RaidResults
          decks={displayResult.decks}
          combinedTotalDamage={displayResult.combinedTotalDamage}
          excludedSlugs={displayResult.excludedSlugs}
          leftoverSlugs={displayResult.leftoverSlugs}
          portraitFor={portraitFor}
          nameFor={nameFor}
        />
      )}
      {mode === 'draft' && displayResult && displayMode === 'draft' && (
        <DraftResults
          decks={displayResult.decks}
          combinedTotalDamage={displayResult.combinedTotalDamage}
          excludedSlugs={displayResult.excludedSlugs}
          leftoverSlugs={displayResult.leftoverSlugs}
          withinDraft={displayResult.withinDraft}
          baselineTotalDamage={displayResult.baselineTotalDamage}
          submittedDraft={submittedDraft}
          ownedSlugFor={ownedSlugResolver}
          portraitFor={portraitFor}
          nameFor={nameFor}
        />
      )}
    </section>
  )
}
