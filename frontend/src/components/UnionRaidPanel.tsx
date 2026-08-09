// 유니온 레이드: 5속성 보스 중 골라 3회 전투하고, 한 번 출전한 니케는 다음
// 전투에 못 나온다. 그래서 화면은 "보스 설정 + 5인 편성"을 전투 수만큼 세운
// 것이고, 편성 규칙은 솔로 5덱과 같다(전원이 서로 달라야 한다).
//
// 추천 탭과 달리 여기엔 최적화가 없다 - 엔진은 유저가 짠 편성을 채점만 한다.
// 잠금이 없는 것도(고정할 최적화가 없다), 결과를 캐시하지 않는 것도(수 초면
// 끝난다) 같은 이유다.

import { useId, useMemo, useState, type FormEvent } from 'react'
import { useEvaluateDecks } from '../hooks/useEvaluateDecks'
import {
  bossProfileToDraft,
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from '../types/bossProfileDraft'
import { isDraftComplete, makeEmptyDraft, resizeDraft, type Draft } from '../types/draft'
import { DEFAULT_UNION_NUM_DECKS, MAX_UNION_NUM_DECKS, MIN_UNION_NUM_DECKS } from '../types/evaluate'
import { latestRotationFor, type RaidRotation } from '../types/raidRotation'
import type { BossProfile } from '../types/recommend'
import type { BurstTier, SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { BossProfileField } from './BossProfileField'
import { DraftEditor, placeUnit, removeUnitBySlug } from './DraftEditor'
import { EvaluationResults } from './EvaluationResults'
import { SaveRunButton } from './SaveRunButton'
import { SavedRunList } from './SavedRunList'
import { makeRunId, type SavedRun, type UnionRunView } from '../types/profile'
import { UnitPalette, toggleExcludedSlug, type UnitInvestment } from './UnitPalette'

interface UnionRaidPanelProps {
  roster: UserNikkeState[]
  /** 공지에서 읽어둔 회차 전체. 이 탭은 유니온 레이드 회차만 쓴다. */
  rotations?: RaidRotation[]
  supportedUnits: SupportedUnit[]
  /** Resolves a slug's portrait for a deck slot. Null when unknown. */
  portraitFor: (slug: string) => string | null
  /** The unit's display name, for a slot's controls. */
  nameFor: (slug: string) => string
  /** Every burst tier a slug can be seated at, nominal one first; empty when
   * the slug is not a supported unit. */
  burstTiersFor: (slug: string) => BurstTier[]
  /** Breakthrough/core/Favorite Item per slug, for the palette chips - same
   * lookup RecommendPanel passes its own palette. Without it every chip here
   * would show blank stars/core/heart next to a recommend tab that shows them. */
  investmentFor?: (slug: string) => UnitInvestment
  /** 이 프로필이 유니온 탭에서 이름 붙여 남겨 둔 결과들, 최신순. */
  savedRuns: SavedRun[]
  /** 보관 상한에 걸려 거절되면 false. */
  onSaveRun: (run: SavedRun) => boolean
  onRenameRun: (id: string, name: string) => void
  onDeleteRun: (id: string) => void
}

/** 유니온은 전투마다 보스가 달라 하나를 이름에 뽑을 수 없다 — 전투 수와 날짜로
 * 구분한다. */
const suggestUnionRunName = (at: Date, numBattles: number): string => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `유니온 ${numBattles}전투 · ${pad(at.getMonth() + 1)}-${pad(at.getDate())}`
}

const NUM_BATTLES_OPTIONS = Array.from(
  { length: MAX_UNION_NUM_DECKS - MIN_UNION_NUM_DECKS + 1 },
  (_, i) => MIN_UNION_NUM_DECKS + i,
)

export function UnionRaidPanel({
  roster,
  rotations = [],
  supportedUnits,
  portraitFor,
  nameFor,
  burstTiersFor,
  investmentFor,
  savedRuns,
  onSaveRun,
  onRenameRun,
  onDeleteRun,
}: UnionRaidPanelProps) {
  const [numBattles, setNumBattles] = useState(DEFAULT_UNION_NUM_DECKS)
  const [bosses, setBosses] = useState<BossProfileDraft[]>(() =>
    Array.from({ length: DEFAULT_UNION_NUM_DECKS }, () => makeDefaultBossProfileDraft()),
  )
  const [draftValue, setDraftValue] = useState<Draft>(() => makeEmptyDraft(DEFAULT_UNION_NUM_DECKS))
  const [touched, setTouched] = useState(false)
  // The boss elements each battle's card was actually scored against,
  // captured at submit time - same reasoning as RecommendPanel's
  // evaluateBoss. Reading the live bosses array from the render below
  // would relabel a finished result's cards the moment the player edits a
  // boss field afterward, while the damage numbers still reflect the old boss.
  const [evaluatedBosses, setEvaluatedBosses] = useState<BossProfile[]>([])
  const [excludedSlugs, setExcludedSlugs] = useState<Set<string>>(new Set())
  // Which battle's deck the palette's `+` fills. Clamped at the point of use
  // rather than resynced when numBattles shrinks: one expression that is
  // always right beats a second piece of state that can disagree with the
  // first for one render.
  const [activeDeck, setActiveDeck] = useState(0)
  const seatDeck = Math.min(activeDeck, numBattles - 1)
  const numBattlesId = useId()

  const evaluation = useEvaluateDecks()
  const unionRotation = useMemo(() => latestRotationFor(rotations, 'union'), [rotations])

  // Shrinking numBattles drops the trailing battles' boss settings and seats;
  // growing it appends fresh (default) ones - preserving earlier battles by
  // index either way. Resized in the same handler as numBattles itself
  // (rather than a numBattles-keyed effect) so a render never sees `bosses`/
  // `draftValue` still at the OLD length while `numBattles` already reads the
  // new one - React batches these three setState calls into one re-render.
  const changeNumBattles = (next: number) => {
    setNumBattles(next)
    setBosses((current) =>
      Array.from({ length: next }, (_, i) => current[i] ?? makeDefaultBossProfileDraft()),
    )
    setDraftValue((current) => resizeDraft(current, next))
  }

  const validated = useMemo(() => bosses.map((draft) => validateBossProfileDraft(draft)), [bosses])
  const allBossesValid = validated.every((v) => v.value !== undefined)

  const decksFull = isDraftComplete(draftValue, numBattles)

  const canSubmit = decksFull && allBossesValid && evaluation.status !== 'loading'

  const usedSlugs = useMemo(
    () => draftValue.decks.flatMap((seats) => seats.map((seat) => seat.slug)),
    [draftValue],
  )

  // The roster after exclusions - what actually gets submitted. Unlike
  // RecommendPanel's search modes, evaluate never searches or scores the
  // roster - only the placed units are - so this filter isn't keeping an
  // excluded unit from being weighed by anything; its real effects are
  // unseating it from whichever battle holds it (below) and keeping it out
  // of what gets submitted as `roster`.
  const effectiveRoster = useMemo(
    () => roster.filter((nikke) => !excludedSlugs.has(nikke.character_slug)),
    [roster, excludedSlugs],
  )

  const toggleExclude = (slug: string) => {
    if (!excludedSlugs.has(slug)) {
      // Excluding a unit also unplaces it from whichever battle holds it.
      setDraftValue((current) => removeUnitBySlug(current, slug))
    }
    setExcludedSlugs((prev) => toggleExcludedSlug(prev, slug))
  }

  // 화면에 떠 있는 유니온 결과. 보스는 제출 시점 스냅샷(evaluatedBosses)이라,
  // 결과가 나온 뒤 보스 폼을 만져도 이 값은 따라 움직이지 않는다.
  const displayedRun = useMemo<UnionRunView | null>(() => {
    if (evaluation.status !== 'success') return null
    return {
      numBattles,
      bosses: evaluatedBosses,
      draft: draftValue,
      decks: evaluation.decks,
      combinedTotalDamage: evaluation.combinedTotalDamage,
      excludedSlugs: evaluation.excludedSlugs,
    }
  }, [
    evaluation.status,
    evaluation.decks,
    evaluation.combinedTotalDamage,
    evaluation.excludedSlugs,
    evaluatedBosses,
    draftValue,
    numBattles,
  ])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setTouched(true)
    if (!canSubmit) return

    const bossProfiles = validated.slice(0, numBattles).map((v) => v.value!)
    setEvaluatedBosses(bossProfiles)
    void evaluation.submit({
      roster: effectiveRoster,
      decks: draftValue.decks.slice(0, numBattles).map((seats, i) => ({
        units: seats.map((seat) => seat.slug),
        boss: bossProfiles[i],
      })),
    })
  }

  return (
    <section className="card" aria-label="유니온 레이드">
      <header className="card__header">
        <h2 className="card__title">유니온 레이드</h2>
      </header>

      <form onSubmit={handleSubmit} className="recommend-form">
        <div className="field">
          <label className="field__label" htmlFor={numBattlesId}>
            전투 수
          </label>
          <select
            id={numBattlesId}
            className="field__input"
            value={numBattles}
            onChange={(event) => changeNumBattles(Number(event.target.value))}
          >
            {NUM_BATTLES_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>

        <div className="union-raid-form__battles">
          {Array.from({ length: numBattles }, (_, i) => (
            <fieldset className="union-raid-form__battle" key={i}>
              <legend className="union-raid-form__battle-legend">{i + 1}번 전투</legend>
              <BossProfileField
                value={bosses[i]}
                errors={touched ? validated[i].errors : {}}
                onChange={(next) =>
                  setBosses((current) => current.map((boss, idx) => (idx === i ? next : boss)))
                }
                rotation={unionRotation}
                // 이 탭은 유저가 짠 편성을 채점만 해서 탐색이 없다 - 제약이 걸 곳이 없다.
                showElementalInterrupt={false}
              />
            </fieldset>
          ))}
        </div>

        {/* 답은 보스 설정 바로 아래에 선다. 편성 칸은 그 아래로. */}
        {evaluation.status === 'loading' && (
          <p className="recommend-form__progress" role="status">
            기대 딜량 계산 중이에요 — 몇 초면 끝나요.
          </p>
        )}
        {evaluation.status === 'error' && (
          <p className="field__error" role="alert">
            {evaluation.error}
          </p>
        )}
        {displayedRun && (
          <div className="result-head">
            <span className="saved-runs__name">유니온 레이드 {numBattles}전투</span>
            <SaveRunButton
              suggestedName={suggestUnionRunName(new Date(), numBattles)}
              onSave={(name) => {
                const savedAt = Date.now()
                return onSaveRun({
                  id: makeRunId(savedAt, savedRuns),
                  name,
                  savedAt,
                  tab: 'union',
                  view: displayedRun,
                })
              }}
            />
          </div>
        )}
        {evaluation.status === 'success' && (
          <EvaluationResults
            decks={evaluation.decks}
            combinedTotalDamage={evaluation.combinedTotalDamage}
            excludedSlugs={evaluation.excludedSlugs}
            bosses={evaluatedBosses}
            portraitFor={portraitFor}
            nameFor={nameFor}
          />
        )}

        <fieldset className="group">
          <legend className="group__legend">편성</legend>
          {/* Palette left, decks right: dragging a unit into a battle's deck
              only works if both are on screen at once - same layout the
              recommend tab's draft/evaluate modes use. */}
          <div className="draft-layout">
            <UnitPalette
              roster={roster}
              supportedUnits={supportedUnits}
              usedSlugs={usedSlugs}
              draggable
              onSeat={(slug) => setDraftValue((current) => placeUnit(current, seatDeck, slug))}
              excludedSlugs={[...excludedSlugs]}
              onToggleExclude={toggleExclude}
              investmentFor={investmentFor}
            />
            <div className="draft-layout__decks">
              <DraftEditor
                numDecks={numBattles}
                value={draftValue}
                onChange={setDraftValue}
                activeDeck={seatDeck}
                onActiveDeckChange={setActiveDeck}
                portraitFor={portraitFor}
                nameFor={nameFor}
                burstTiersFor={burstTiersFor}
                // There is no optimizer here to constrain - locking a unit in
                // place has nothing to mean on a screen that only scores what
                // was placed.
                showLocks={false}
              />
              {/* 이 컬럼은 sticky라, 여기 얹은 실행 버튼은 편성과 함께
                  화면에 남는다. */}
              <div className="recommend-form__actions">
                <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
                  {evaluation.status === 'loading' ? '계산 중…' : '인카운터!'}
                </button>
              </div>
            </div>
          </div>
        </fieldset>

        <fieldset className="group saved-runs-group">
          <legend className="group__legend">저장한 결과 ({savedRuns.length})</legend>
          <details className="group__details">
            <summary className="group__hint">
              이름을 눌러 그때의 결과를 다시 볼 수 있어요
            </summary>
            <SavedRunList
              runs={savedRuns}
              renderRun={(run) => {
                const view = run.view as UnionRunView
                return (
                  <EvaluationResults
                    decks={view.decks}
                    combinedTotalDamage={view.combinedTotalDamage}
                    excludedSlugs={view.excludedSlugs}
                    bosses={view.bosses}
                    portraitFor={portraitFor}
                    nameFor={nameFor}
                  />
                )
              }}
              onRestore={(run) => {
                const view = run.view as UnionRunView
                // changeNumBattles가 bosses/draftValue도 함께 바꾸므로, 뒤따르는
                // 두 setState가 최종 값을 쥔다 - React가 셋을 한 렌더로 묶는다.
                changeNumBattles(view.numBattles)
                setBosses(view.bosses.map(bossProfileToDraft))
                setDraftValue(view.draft)
              }}
              onRename={onRenameRun}
              onDelete={onDeleteRun}
            />
          </details>
        </fieldset>
      </form>
    </section>
  )
}
