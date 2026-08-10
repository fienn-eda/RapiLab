// 미란다 계산기: 미란다를 포함한 5인을 편성하면 파워업!과 웨이크업! 3번불릿을
// 누가 받는지 답한다.
//
// 미란다는 처음부터 앉아 있고 유저는 남은 네 자리만 채운다. 「맨 왼쪽」에
// 장치가 없는 이유는 DraftEditor가 좌석을 버스트 티어 순으로 그리기 때문이다 -
// 그녀는 B1이라 언제나 첫 칸이고, 같은 B1이 하나 더 들어와도 정렬이 안정적이라
// 먼저 앉은 그녀가 앞에 남는다.

import { useMemo, useState } from 'react'
import { postMirandaTargets } from '../api/mirandaTargets'
import { RecommendApiError, describeRecommendApiError } from '../api/recommendApiError'
import { HELP } from '../lib/helpText'
import { isDraftComplete, makeEmptyDraft, type Draft } from '../types/draft'
import type { MirandaTargetsResult } from '../types/mirandaTargets'
import type { BurstTier, SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { DraftEditor, placeUnit } from './DraftEditor'
import { HelpText } from './HelpText'
import { MirandaTargets } from './MirandaTargets'
import { UnitPalette, type UnitInvestment } from './UnitPalette'

// 애장품을 보유하면 로스터 임포트가 이미 "-signature"로 승격해 둔다. 어느
// 빌드인지가 답을 바꾸므로(애장품이면 파워업! 2명 + 웨이크업!3, 아니면 파워업!
// 1명뿐) 로스터가 가진 쪽을 그대로 앉힌다.
const MIRANDA_SLUGS = ['miranda-signature', 'miranda']

/** 이 로스터에 앉힐 미란다. 애장품 빌드가 있으면 그쪽이다 - 어느 빌드인지가
 * 답을 바꾸므로 화면 글자("미란다", 둘 다 같다)가 아니라 이 함수가 결정을
 * 쥔다. Exported so the decision can be tested without seating a whole deck. */
export const seatedMirandaSlug = (roster: UserNikkeState[]): string | null =>
  MIRANDA_SLUGS.find((slug) => roster.some((n) => n.character_slug === slug)) ?? null

interface MirandaCalculatorPanelProps {
  roster: UserNikkeState[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
  nameFor: (slug: string) => string
  burstTiersFor: (slug: string) => BurstTier[]
  investmentFor?: (slug: string) => UnitInvestment
}

export function MirandaCalculatorPanel({
  roster,
  supportedUnits,
  portraitFor,
  nameFor,
  burstTiersFor,
  investmentFor,
}: MirandaCalculatorPanelProps) {
  const mirandaSlug = useMemo(() => seatedMirandaSlug(roster), [roster])
  const [draft, setDraft] = useState<Draft>(() =>
    mirandaSlug ? placeUnit(makeEmptyDraft(1), 0, mirandaSlug) : makeEmptyDraft(1),
  )
  const [result, setResult] = useState<MirandaTargetsResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const seats = draft.decks[0] ?? []
  const usedSlugs = seats.map((seat) => seat.slug)
  const full = isDraftComplete(draft, 1)

  if (mirandaSlug === null) {
    return (
      <section className="card" aria-label="미란다 계산기">
        <p className="empty__text">
          <HelpText>{HELP.miranda.notInRoster}</HelpText>
        </p>
      </section>
    )
  }

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      setResult(await postMirandaTargets({ roster, units: usedSlugs }))
    } catch (err) {
      setResult(null)
      setError(
        err instanceof RecommendApiError
          ? describeRecommendApiError(err)
          : '계산에 실패했습니다.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card" aria-label="미란다 계산기">
      <header className="card__header">
        <h2 className="card__title">미란다 계산기</h2>
      </header>
      <p className="group__hint">
        <HelpText>{HELP.miranda.intro}</HelpText>
      </p>

      <div className="draft-layout">
        <UnitPalette
          roster={roster}
          supportedUnits={supportedUnits}
          usedSlugs={usedSlugs}
          draggable
          onSeat={(slug) => setDraft((current) => placeUnit(current, 0, slug))}
          investmentFor={investmentFor}
        />
        {/* 결과는 편성 옆, 계산 버튼 바로 아래다. 카드 맨 아래에 두면 팔레트가
            길어질수록 답이 화면 밖으로 밀려나, 눌러 놓고 스크롤을 내려야
            비로소 보인다. */}
        <div className="draft-layout__decks draft-layout__decks--with-result">
          <DraftEditor
            numDecks={1}
            value={draft}
            onChange={setDraft}
            portraitFor={portraitFor}
            nameFor={nameFor}
            burstTiersFor={burstTiersFor}
            showLocks={false}
            fixedSlugs={[mirandaSlug]}
          />
          <div className="recommend-form__actions">
            <button type="button" className="btn btn--primary" onClick={run} disabled={!full || busy}>
              {busy ? '계산 중…' : '계산'}
            </button>
          </div>
          {busy && (
            <p className="recommend-form__progress" role="status">
              <HelpText>{HELP.miranda.running}</HelpText>
            </p>
          )}
          {error && <p className="field__error" role="alert">{error}</p>}
          {result && (
            <MirandaTargets result={result} portraitFor={portraitFor} nameFor={nameFor} />
          )}
        </div>
      </div>
    </section>
  )
}
