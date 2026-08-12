// 유니온 레이드: 5속성 보스 중 골라 3회 전투하고, 한 번 출전한 니케는 다음
// 전투에 못 나온다. 그래서 화면은 "보스 설정 + 5인 편성"을 전투 수만큼 세운
// 것이고, 편성 규칙은 솔로 5덱과 같다(전원이 서로 달라야 한다).
//
// 추천 탭과 달리 여기엔 최적화가 없다 - 엔진은 유저가 짠 편성을 채점만 한다.
// 잠금이 없는 것도(고정할 최적화가 없다), 결과를 캐시하지 않는 것도(수 초면
// 끝난다) 같은 이유다.

import { useEffect, useId, useMemo, useState, type FormEvent } from 'react'
import { useEvaluateDecks } from '../hooks/useEvaluateDecks'
import { HELP } from '../lib/helpText'
import { bossHeading, weaknessLabelOf } from '../lib/bossLabel'
import { canSeatFrom, draftFromResultDecks } from '../lib/importRun'
import {
  bossProfileToDraft,
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from '../types/bossProfileDraft'
import {
  firstDeckWithRoom,
  isDraftComplete,
  makeEmptyDraft,
  resizeDraft,
  type Draft,
} from '../types/draft'
import { DEFAULT_UNION_NUM_DECKS, MAX_UNION_NUM_DECKS, MIN_UNION_NUM_DECKS } from '../types/evaluate'
import { latestRotationFor, type RaidRotation } from '../types/raidRotation'
import type { BossElement, BossProfile } from '../types/recommend'
import { ownedSlugFor, ownedSlugIndex } from '../types/supportedUnit'
import type { BurstTier, SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { BossProfileField } from './BossProfileField'
import { ClearDraftButton } from './ClearDraftButton'
import { DraftEditor, placeUnit, removeUnitBySlug, replaceUnit } from './DraftEditor'
import { EvaluationResults } from './EvaluationResults'
import { HelpText } from './HelpText'
import { ImportRunButton } from './ImportRunButton'
import { SaveRunButton } from './SaveRunButton'
import { SavedRunList } from './SavedRunList'
import { makeRunId, type SavedRun, type UnionRunView } from '../types/profile'
import { UnitPalette, type UnitInvestment } from './UnitPalette'

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
  /** 니케 풀 탭에서 정한 미사용 니케. 이 탭은 읽기만 한다. */
  excludedSlugs?: string[]
  onRenameRun: (id: string, name: string) => void
  onDeleteRun: (id: string) => void
}

/** 유니온은 전투마다 보스가 달라 하나를 이름에 뽑을 수 없다 — 덱 순서대로
 * 약점을 나열한다. 날짜는 넣지 않는다: 보관 목록이 이름 옆에 저장 시각을
 * 항상 따로 찍는다.
 *
 * 속성만 읽으므로 폼의 초안(BossProfileDraft)이든 제출된 보스(BossProfile)든
 * 받는다 - 부르는 쪽은 숫자를 낸 그 스냅샷을 넘겨야 한다. */
export const suggestUnionRunName = (bosses: { element: BossElement }[]): string =>
  bosses.map((boss) => weaknessLabelOf(boss.element)).join(' ')

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
  excludedSlugs: excludedSlugsProp,
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
  // Benched Nikkes, decided once for the account on the roster tab. Optional
  // so tests that render this panel directly keep their signature.
  const excludedSlugs = useMemo(() => new Set(excludedSlugsProp ?? []), [excludedSlugsProp])
  // A value the unseat effect can depend on - a fresh Set every render would
  // re-run it forever.
  const excludedKey = [...excludedSlugs].sort().join(',')
  // Which battle's deck a palette press fills. Clamped at the point of use
  // rather than resynced when numBattles shrinks: one expression that is
  // always right beats a second piece of state that can disagree with the
  // first for one render.
  const [activeDeck, setActiveDeck] = useState(0)
  const seatDeck = Math.min(activeDeck, numBattles - 1)
  // 팔레트가 DraftEditor 밖에 있어서, 그 안에서 들린 유닛을 이 사본으로
  // 따라 안다 - 팔레트 클릭을 "빈자리에 앉히기"와 "든 유닛과 맞바꾸기"로
  // 가르는 데 쓴다. 편집기가 든 것이 바뀔 때마다(사라질 때·언마운트될 때까지)
  // 알려주므로 이쪽에서 손댈 일은 없다.
  const [heldSlug, setHeldSlug] = useState<string | null>(null)
  // 방금 가져오기에서 앉히지 못한 니케 수. 솔로 탭과 같은 이유로 화면에 남긴다.
  const [droppedCount, setDroppedCount] = useState(0)
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

  // 결과가 부르는 슬러그를 유저가 가진 슬러그로 되돌린다 - 솔로 탭이 쓰는 것과
  // 같은 표다(bready-lingering -> bready).
  const ownedSlugs = useMemo(() => ownedSlugIndex(supportedUnits), [supportedUnits])

  const validated = useMemo(() => bosses.map((draft) => validateBossProfileDraft(draft)), [bosses])
  const allBossesValid = validated.every((v) => v.value !== undefined)

  const decksFull = isDraftComplete(draftValue, numBattles)

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

  // 유니온은 싱크로 레벨로 싸우므로 실제 레벨 스탯이 있어야 잴 수 있다. 400레벨
  // 값으로 대신 재면 유닛 간 상대 ATK가 최대 24% 뒤틀린다 - 레벨은 base 커브에만
  // 들어가고 장비·큐브·소장품은 레벨과 무관하게 더해지기 때문이다.
  // DEF는 보지 않는다: 스탯 모델이 DEF를 내지 않아 "없음"과 0을 구분할 수 없다.
  const missingActualStats = useMemo(
    () => effectiveRoster.some((n) => n.actual_atk == null || n.actual_hp == null),
    [effectiveRoster],
  )

  const canSubmit =
    decksFull && allBossesValid && !missingActualStats && evaluation.status !== 'loading'

  // Benching a Nikke also unseats her from whichever battle holds her, so
  // "제외" means the same thing here as in the submitted roster. The decision
  // arrives from the roster tab now, so it is watched rather than handled.
  useEffect(() => {
    setDraftValue((current) =>
      [...excludedSlugs].reduce((draft, slug) => removeUnitBySlug(draft, slug), current),
    )
    // removeUnitBySlug returns the same draft when nothing matched, so this
    // settles without a re-render.
  }, [excludedKey])

  // 화면에 떠 있는 유니온 결과. 보스는 제출 시점 스냅샷(evaluatedBosses)이라,
  // 결과가 나온 뒤 보스 폼을 만져도 이 값은 따라 움직이지 않는다.
  const displayedRun = useMemo<UnionRunView | null>(() => {
    if (evaluation.status !== 'success') return null
    return {
      // 라이브 numBattles가 아니라 이 결과가 실제로 낸 전투 수 - 결과가 뜬 뒤
      // 전투 수 셀렉트를 만지면 라이브 값은 더 이상 이 결과를 설명하지 않는다.
      numBattles: evaluatedBosses.length,
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
  ])

  /** 편성만 비운다. 전투 수도 보스 설정도 그대로다. importRun과 같은 이유로
   * 화면에 뜬 결과도 함께 내린다 - 안 내리면 빈 편성 위에 옛 결과가 거짓으로
   * 남는다. */
  const clearDraft = () => {
    setDraftValue(makeEmptyDraft(numBattles))
    setDroppedCount(0)
    evaluation.reset()
  }

  /** 저장된 numBattles가 실제 bosses/decks 배열보다 작은 보관물이 로컬스토리지에
   * 이미 있을 수 있다(저장 시점 스냅샷 버그) - 작은 쪽을 쓰면 니케가 조용히
   * 사라지거나(덱 부족) validated[i]가 undefined라 렌더가 죽는다(보스 부족). */
  const safeNumBattlesFor = (view: UnionRunView, deckSlugs: string[][]): number =>
    Math.max(view.numBattles, view.bosses.length, deckSlugs.length)

  /** `numBattles`에 정확히 맞춰 보스 초안을 채운다. changeNumBattles 자신도
   * bosses를 패딩하지만, 그 함수형 갱신은 옛 bosses를 기준으로 하고 이어지는
   * plain setBosses가 그 결과를 통째로 덮어써 무의미해진다 - 그래서 최종 길이는
   * 여기서 직접 맞춘다. */
  const padBosses = (bosses: BossProfile[], numBattles: number): BossProfileDraft[] =>
    Array.from({ length: numBattles }, (_, i) =>
      bosses[i] ? bossProfileToDraft(bosses[i]) : makeDefaultBossProfileDraft(),
    )

  const importRun = (run: SavedRun) => {
    const view = run.view as UnionRunView
    const deckSlugs = view.decks.map((deck) => deck.deck)
    const nextNumBattles = safeNumBattlesFor(view, deckSlugs)

    const { draft: imported, droppedSlugs } = draftFromResultDecks(deckSlugs, nextNumBattles, {
      ownedSlugFor: (slug) => ownedSlugFor(slug, ownedSlugs),
      canSeat: canSeatFrom(roster, excludedSlugs),
    })

    changeNumBattles(nextNumBattles)
    setBosses(padBosses(view.bosses, nextNumBattles))
    setDraftValue(imported)
    setDroppedCount(droppedSlugs.length)
    // 편성을 갈아치웠으므로 그 전 편성으로 나온 결과는 화면에서 내린다.
    evaluation.reset()
  }

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
      stat_basis: 'actual',
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
            <HelpText>{HELP.recommend.evaluateRunning}</HelpText>
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
              suggestedName={suggestUnionRunName(displayedRun.bosses)}
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
              onSeat={(slug) => {
                if (heldSlug) {
                  // 들고 있던 자리를 팔레트 유닛에게 내준다. 들고 있던 쪽은
                  // 풀로 돌아간다. 자리를 물려받는 것이라 덱 크기가 안
                  // 변하므로 활성 덱도 그대로다.
                  setDraftValue((current) => replaceUnit(current, heldSlug, slug))
                  setHeldSlug(null)
                  return
                }
                // 활성 덱이 꽉 차 있으면 다음 빈 덱을 찾는다. 클릭 하나는 한
                // 번의 배치라 클로저의 draftValue가 최신이다 - 갱신자 안에서
                // setActiveDeck을 부르면 갱신자가 더 이상 순수하지 않고
                // StrictMode가 두 번 부른다.
                const target = firstDeckWithRoom(draftValue, seatDeck, numBattles)
                if (target === null) return
                const next = placeUnit(draftValue, target, slug)
                setDraftValue(next)
                // 앉힌 직후로 다시 훑는다 - 방금 찬 덱이면 표시가 곧바로 다음
                // 덱으로 넘어가, 다음 클릭이 어디로 갈지 보인다.
                setActiveDeck(firstDeckWithRoom(next, target, numBattles) ?? target)
              }}
              excludedSlugs={[...excludedSlugs]}
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
                onHeldSlugChange={setHeldSlug}
                // There is no optimizer here to constrain - locking a unit in
                // place has nothing to mean on a screen that only scores what
                // was placed.
                showLocks={false}
                deckLabels={bosses.slice(0, numBattles).map((boss, i) =>
                  bossHeading({
                    bossName: boss.boss_name,
                    element: boss.element,
                    fallback: `덱 ${i + 1}`,
                  }),
                )}
              />
              {/* 이 컬럼은 sticky라, 여기 얹은 실행 버튼은 편성과 함께
                  화면에 남는다. */}
              <div className="recommend-form__actions">
                {missingActualStats && <HelpText>{HELP.sync.unionNeedsActualStats}</HelpText>}
                <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
                  {evaluation.status === 'loading' ? '계산 중…' : '인카운터!'}
                </button>
                <ImportRunButton runs={savedRuns} draft={draftValue} onImport={importRun} />
                <ClearDraftButton draft={draftValue} onClear={clearDraft} />
                {droppedCount > 0 && (
                  <p className="field__error" role="status">
                    <HelpText>{HELP.draftActions.droppedUnits(droppedCount)}</HelpText>
                  </p>
                )}
              </div>
            </div>
          </div>
        </fieldset>

        <fieldset className="group saved-runs-group">
          <legend className="group__legend">저장한 결과 ({savedRuns.length})</legend>
          <details className="group__details">
            <summary className="group__hint">
              <HelpText>{HELP.savedRuns.restoreHint}</HelpText>
            </summary>
            <SavedRunList
              runs={savedRuns}
              renderRun={(run) => {
                const view = run.view as UnionRunView
                return (
                  <EvaluationResults
                    decks={view.decks}
                    combinedTotalDamage={view.combinedTotalDamage}
                    bosses={view.bosses}
                    portraitFor={portraitFor}
                    nameFor={nameFor}
                  />
                )
              }}
              onRestore={(run) => {
                const view = run.view as UnionRunView
                // bosses가 numBattles보다 짧게 저장된 보관물도 안전해야 한다 -
                // importRun과 같은 이유(safeNumBattlesFor/padBosses 참고).
                const nextNumBattles = safeNumBattlesFor(view, [])
                changeNumBattles(nextNumBattles)
                setBosses(padBosses(view.bosses, nextNumBattles))
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
