// Boss-profile input + "Recommend decks" action. Four modes share the same
// boss profile: single deck (POST /api/recommend, ranked alternatives), raid
// allocation (POST /api/recommend-raid, a partition of disjoint decks fielded
// together), draft-based raid allocation (the same endpoint, seeded with
// the player's own key units via `draft` — frontend/README.md "Draft-based
// raid recommendation"), and evaluate (POST /api/evaluate-decks, scoring
// decks the player fully built themselves — no search, so no caching either;
// see useEvaluateDecks). Only one mode's request is ever in flight.

import { useCallback, useEffect, useId, useMemo, useRef, useState, type FormEvent } from 'react'
import { useRecommend } from '../hooks/useRecommend'
import { useRecommendRaid } from '../hooks/useRecommendRaid'
import { useEvaluateDecks } from '../hooks/useEvaluateDecks'
import { usePortraitManifest } from '../hooks/usePortraitManifest'
import { useSupportedUnits } from '../hooks/useSupportedUnits'
import { nameFromSlug, withFavoriteItem } from '../lib/unitName'
import { burstTiersFor, ownedSlugFor, ownedSlugIndex } from '../types/supportedUnit'
import { hashRecommendInputs } from '../lib/inputHash'
import {
  bossProfileToDraft,
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from '../types/bossProfileDraft'
import { isDraftComplete, makeEmptyDraft, resizeDraft, type Draft } from '../types/draft'
import type { StoredInputs, StoredResult } from '../types/profile'
import {
  DEFAULT_NUM_DECKS,
  MAX_NUM_DECKS,
  MIN_DECK_ROSTER_SIZE,
  MIN_NUM_DECKS,
  type BossProfile,
  type RecommendRaidRequest,
  type RecommendRequest,
} from '../types/recommend'
import { weaknessFor } from '../lib/elementAdvantage'
import type { UserNikkeState } from '../types/userNikkeState'
import { BossProfileField } from './BossProfileField'
import { DeckResults } from './DeckResults'
import { DraftEditor, removeUnitBySlug, toRequestDraft } from './DraftEditor'
import { DraftResults } from './DraftResults'
import { EvaluationResults } from './EvaluationResults'
import { RaidResults } from './RaidResults'
import { UnitPalette, toggleExcludedSlug, type UnitInvestment } from './UnitPalette'
import { HELP } from '../lib/helpText'

interface RecommendPanelProps {
  /** The validated, ready subset of the entered roster. */
  roster: UserNikkeState[]
  /** The active profile's key — keys the restore effect so switching
   * accounts (not just re-rendering) reloads that profile's form/result. */
  activeKey: string | null
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

type RecommendMode = 'single' | 'raid' | 'draft' | 'evaluate'

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
  activeKey,
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
  // The boss each SURVIVING result was actually computed against, captured
  // at submit time (or restore time) - same idea as submittedDraft above.
  // bossProfile is live form state; reading it straight from a result render
  // would relabel that result's cards - and its gimmick-unmet badges - the
  // moment the player edits the boss field afterward, while the damage
  // numbers still reflect the old boss.
  //
  // One shared snapshot is not enough: single's result (single.status) and
  // the raid/draft result (displayResult) both survive a MODE switch - only
  // evaluate's is cleared on one (switchMode below calls evaluation.reset()).
  // So switching to another mode and submitting there must not touch the
  // boss a still-displayed single or raid/draft result is judged against -
  // each gets its own slot, updated only when ITS OWN result is (re)computed.
  const [singleBoss, setSingleBoss] = useState<BossProfile | null>(null)
  const [displayBoss, setDisplayBoss] = useState<BossProfile | null>(null)
  const [evaluateBoss, setEvaluateBoss] = useState<BossProfile | null>(null)
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
  const evaluation = useEvaluateDecks()
  const active = mode === 'single' ? single : mode === 'evaluate' ? evaluation : raid
  const supportedUnits = useSupportedUnits()
  const { portraitFor } = usePortraitManifest()

  // Restore the active profile's last raid/draft submission (form + result)
  // whenever the ACCOUNT changes, not on every render, so it never clobbers
  // in-progress edits mid-typing. engineVersion is the other trigger because
  // whether a stored result is still valid can't be answered until the backend
  // names the current engine, and that lands a beat after mount - restoreResult
  // is null until then. Without it here, a restorable result would be dropped
  // for good. It settles once per mount, so this stays two firings.
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
      // The restored result was computed against restoreInputs.boss, not
      // whatever the (now-reset) form happens to hold - same submit-time
      // snapshot rule as a fresh handleSubmit, just replayed from storage.
      // Only displayBoss: a restored raid/draft result never touches
      // single's or evaluate's own result slots.
      setDisplayBoss(restoreInputs.boss)
    } else {
      setDisplayResult(null)
      setDisplayMode(null)
      setDisplayBoss(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeKey, engineVersion])

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
    // pending.inputs.boss is the boss THIS submit was made with, captured
    // back in handleSubmit before the request went out - not whatever the
    // form (or another mode's later submit) holds by the time this resolves.
    setDisplayBoss(pending.inputs.boss)
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
    setDraftValue((current) => resizeDraft(current, numDecks))
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
  // Evaluate mode has no search, so its gate isn't roster size but "every
  // selected deck is actually fielded" — a partial squad can't be scored.
  const evaluateDecksFull = isDraftComplete(draftValue, numDecks)
  const canSubmit =
    mode === 'evaluate'
      ? evaluateDecksFull && !!bossProfile && active.status !== 'loading'
      : !rosterTooSmall && !!bossProfile && active.status !== 'loading'

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

  const elementOf = useMemo(
    () => new Map(supportedUnits.units.map((u) => [u.slug, u.element])),
    [supportedUnits.units],
  )

  // Builds the "can this deck break the gimmick" predicate for ONE boss
  // snapshot - undefined (no badge drawn) when the constraint is off, there's
  // no boss yet, or supported-units hasn't loaded. That last case matters:
  // with elementOf empty, `.get()` always misses and `.some()` is always
  // false, which would flip EVERY deck to "unmet" - asserting a fact the
  // panel has no data for, rather than just not asserting one.
  //
  // Reads through ownedSlugResolver purely for consistency with every other
  // slug lookup in this file (nameFor below), not because it fills a gap:
  // supported-units already lists a MODE_VARIANTS candidate like
  // `bready-lingering` under its own key, carrying the same element as the
  // owned `bready` (backend/app/supported_units.py merges a candidate's own
  // fields into the base entry, and
  // test_a_merged_entry_describes_candidates_that_actually_agree pins that
  // they agree) - so a raw deck slug would already resolve correctly here.
  const gimmickUnmetForBoss = useCallback(
    (boss: BossProfile | null) => {
      if (!boss?.elemental_interrupt_required || boss.element === null) return undefined
      if (elementOf.size === 0) return undefined
      const weakness = weaknessFor(boss.element)
      return (deckSlugs: string[]) =>
        !deckSlugs.some((slug) => elementOf.get(ownedSlugResolver(slug)) === weakness)
    },
    [elementOf, ownedSlugResolver],
  )

  // One predicate per result slot (see singleBoss/displayBoss/evaluateBoss
  // above) - sharing one would badge whichever OTHER result is still on
  // screen using the boss most recently submitted in a different mode.
  const singleGimmickUnmetFor = useMemo(
    () => gimmickUnmetForBoss(singleBoss),
    [singleBoss, gimmickUnmetForBoss],
  )
  const raidGimmickUnmetFor = useMemo(
    () => gimmickUnmetForBoss(displayBoss),
    [displayBoss, gimmickUnmetForBoss],
  )
  const evaluateGimmickUnmetFor = useMemo(
    () => gimmickUnmetForBoss(evaluateBoss),
    [evaluateBoss, gimmickUnmetForBoss],
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
  const burstTiersResolver = (slug: string) => burstTiersFor(slug, unitIndex)

  const toggleExclude = (slug: string) => {
    if (!excludedSlugs.has(slug)) {
      // Excluding a unit also unplaces it from the draft.
      setDraftValue((current) => removeUnitBySlug(current, slug))
    }
    setExcludedSlugs((prev) => toggleExcludedSlug(prev, slug))
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setTouched(true)
    // Evaluate scores exactly the units placed in the draft, never searching
    // the roster - roster size genuinely isn't its gate (canSubmit above
    // already agrees), so this early return must not apply to it, or the
    // button can be enabled by a full draft and still silently do nothing
    // once the roster tab shrinks below MIN_DECK_ROSTER_SIZE.
    if (!bossProfile || (mode !== 'evaluate' && rosterTooSmall)) return
    if (mode === 'single') {
      // singleBoss is single's own result-slot snapshot (see the state
      // declarations above) - set alongside the submit so single.decks and
      // the boss it was judged against always change together.
      setSingleBoss(bossProfile)
      const request: RecommendRequest = { roster: effectiveRoster, boss: bossProfile }
      void single.submit(request)
      return
    }

    if (mode === 'evaluate') {
      // No cache, no raidResultMode/displayResult - evaluation is seconds-fast
      // and renders straight from useEvaluateDecks' own state (see file header).
      setEvaluateBoss(bossProfile)
      void evaluation.submit({
        roster: effectiveRoster,
        decks: draftValue.decks.slice(0, numDecks).map((seats) => ({
          units: seats.map((seat) => seat.slug),
          boss: bossProfile,
        })),
      })
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
    setDisplayBoss(null)

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
      setDisplayBoss(bossProfile)
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

  // 유휴 라벨은 모드와 무관하게 하나다 - 무엇을 시작하는 버튼인지는 바로 위의
  // 모드 라디오가 이미 말한다. 실행 중 라벨만 모드별로 갈리는데, 버튼이 진행
  // 상태를 알려주는 유일한 자리이기 때문이다.
  const loadingLabel =
    mode === 'single'
      ? '단일 덱 탐색 중…'
      : mode === 'raid'
        ? '전부 최적화 중…'
        : mode === 'draft'
          ? '빈자리만 최적화 중…'
          : '계산 중…'
  const submitLabel = active.status === 'loading' ? loadingLabel : '인카운터!'

  // Evaluation isn't cached and its display is gated purely on `mode`, unlike
  // raid/draft's raidResultMode/displayResult - so a stray in-flight evaluate
  // request left running after the player moves to another mode is stopped
  // here rather than by a render guard. reset() also clears a FINISHED
  // result, which cancel() cannot touch (there is nothing left in flight to
  // abort) - draftValue is shared with draft mode, so without it a result
  // computed for one composition could still render after the player edits
  // the decks elsewhere and switches back to evaluate.
  const switchMode = (next: RecommendMode) => {
    evaluation.cancel()
    evaluation.reset()
    setMode(next)
  }

  // 실행 버튼은 두 자리 중 하나에 선다 - 아래 폼을 볼 것. 내용물은 같으므로
  // 여기서 한 번만 만든다.
  const actionButtons = (
    <>
      <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
        {submitLabel}
      </button>
      {/* 무언가 실제로 돌고 있을 때만 - 제출 옆에 상시 놓인 취소는 두 행동
          사이의 선택처럼 읽힌다. `type="button"`이 중요하다: 폼 안의 맨
          버튼은 제출이라, 첫 실행을 멈추는 대신 두 번째를 시작해버린다. */}
      {active.status === 'loading' && (
        <button type="button" className="btn" onClick={active.cancel}>
          취소
        </button>
      )}
      {mode !== 'evaluate' && rosterTooSmall && (
        <p className="field__error" role="alert">
          덱을 추천하려면 준비된 니케가 최소 {MIN_DECK_ROSTER_SIZE}기 필요해요.
        </p>
      )}
    </>
  )

  return (
    <section className="card" aria-label="솔로 레이드">
      <header className="card__header">
        <h2 className="card__title">솔로 레이드</h2>
      </header>

      <form onSubmit={handleSubmit} className="recommend-form">
        {/* Everything needed to CONFIGURE a run sits in one row: the boss on
            the left, the mode choice on the right. The boss fields used
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
                  onChange={() => switchMode('single')}
                />
                단일 덱
                <span className="group__hint"> — {HELP.recommendMode.single}</span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="raid"
                  checked={mode === 'raid'}
                  onChange={() => switchMode('raid')}
                />
                전부 최적화
                <span className="group__hint"> — {HELP.recommendMode.raid}</span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="draft"
                  checked={mode === 'draft'}
                  onChange={() => switchMode('draft')}
                />
                빈자리만 최적화
                <span className="group__hint"> — {HELP.recommendMode.draft}</span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="evaluate"
                  checked={mode === 'evaluate'}
                  onChange={() => switchMode('evaluate')}
                />
                기대 딜량 계산
                <span className="group__hint"> — {HELP.recommendMode.evaluate}</span>
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
          </fieldset>
        </div>

        {/* 덱 컬럼이 없는 모드의 실행 버튼. 자기가 작용하는 보스·모드 설정
            바로 아래에 선다. */}
        {(mode === 'single' || mode === 'raid') && (
          <div className="recommend-form__actions">{actionButtons}</div>
        )}

        {/* 답은 설정 바로 아래에 선다. 팔레트와 편성 칸은 그 아래로, 결과를
            읽는 데 스크롤이 필요 없도록. */}
        {(mode === 'raid' || mode === 'draft') && raid.status === 'loading' && (
          <p className="recommend-form__progress" role="status">
            {/* 실측(Fienn 로스터 78기·5덱, 2026-08-04): 전부 최적화 188초,
                편성이 꽉 찬 빈자리만 최적화 264초 — 후자는 배분을 세 번 돌린다
                (recommend_from_draft의 recommended + within_draft 둘). 스왑 단계
                상한은 backend/app/deck_allocation.py의 SWAP_TIME_BUDGET_SEC이고,
                개선이 끊기면 상한을 다 쓰지 않고 끝나므로 얇은 로스터는 훨씬 빠르다. */}
            {mode === 'raid' ? '전부 최적화 중' : '빈자리만 최적화 중'} — 수천 번의
            시뮬레이션을 실행하며 보통 2~5분이 걸려요. 아직 진행 중이니 완료되면
            버튼이 다시 활성화돼요.
          </p>
        )}
        {mode === 'evaluate' && evaluation.status === 'loading' && (
          <p className="recommend-form__progress" role="status">
            기대 딜량 계산 중이에요 — 몇 초면 끝나요.
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
        {mode === 'evaluate' && evaluation.status === 'error' && (
          <p className="field__error" role="alert">
            {evaluation.error}
          </p>
        )}

        {mode === 'single' && single.status === 'success' && (
          <DeckResults
            decks={single.decks}
            excludedSlugs={single.excludedSlugs}
            portraitFor={portraitFor}
            nameFor={nameFor}
            gimmickUnmetFor={singleGimmickUnmetFor}
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
            gimmickUnmetFor={raidGimmickUnmetFor}
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
            gimmickUnmetFor={raidGimmickUnmetFor}
          />
        )}
        {/* Reads straight off useEvaluateDecks, not displayResult/displayMode -
            see the file header. bossElements comes from evaluateBoss
            (submit-time snapshot), not the live bossProfile, so editing the
            boss field afterward can't relabel a result it wasn't scored
            against. */}
        {mode === 'evaluate' && evaluation.status === 'success' && (
          <EvaluationResults
            decks={evaluation.decks}
            combinedTotalDamage={evaluation.combinedTotalDamage}
            excludedSlugs={evaluation.excludedSlugs}
            bossElements={evaluation.decks.map(() => evaluateBoss?.element ?? null)}
            portraitFor={portraitFor}
            nameFor={nameFor}
            gimmickUnmetFor={evaluateGimmickUnmetFor}
          />
        )}

        {mode !== 'draft' && mode !== 'evaluate' && (
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

        {(mode === 'draft' || mode === 'evaluate') && (
          <fieldset className="group">
            <legend className="group__legend">{mode === 'draft' ? '내 편성' : '평가할 덱'}</legend>
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
                  burstTiersFor={burstTiersResolver}
                  // Evaluate has no optimizer to constrain - locking a unit in
                  // place has nothing to mean there.
                  showLocks={mode !== 'evaluate'}
                />
                {/* 이 컬럼은 sticky라, 여기 얹은 실행 버튼은 덱과 함께
                    화면에 남는다. */}
                <div className="recommend-form__actions">{actionButtons}</div>
              </div>
            </div>
          </fieldset>
        )}
      </form>
    </section>
  )
}
