// The 차지 tab: how many shots a charge unit lands inside its Full Burst
// window, and what charge-speed total buys the next one.
//
// The numeric fields start empty, which means "use the synced roster". A typed
// value overrides it - the roster snapshot goes stale the moment gear changes,
// and for this screen that is the normal state rather than an error.

import { useState } from 'react'
import { postChargeWindow } from '../api/chargeWindow'
import { HELP } from '../lib/helpText'
import type { ChargeWindowResult } from '../types/chargeWindow'
import { ChargeWindowLadder } from './ChargeWindowLadder'
import { HelpText } from './HelpText'
import { HelpTip } from './HelpTip'
import { NumberField } from './fields/NumberField'

// Which units the tab offers is a UI scoping decision; the backend's 422 stays
// the authority on what the calculator actually covers. The display names are
// NOT restated here - they come from /api/supported-units through `nameFor`.
const UNIT_SLUGS = ['scarlet-black-shadow', 'liberalio', 'neon-vision-eye']

const LIBERALIO_SLUG = 'liberalio'

// The two cubes the project holds stat tables for. Everywhere else in the app
// the Resilience cube is an assumption nobody is asked about; here the Tactical
// Bear's rounds decide whether a reload lands inside the window at all, which
// is two different shot counts on identical gear.
const CUBES = [
  { name: 'resilience', label: '렐릭 베어 (재장전 속도)' },
  { name: 'tactical_bear', label: '택티컬 베어 (탄환 충전)' },
]

const optional = (raw: string): number | null => {
  const trimmed = raw.trim()
  if (trimmed === '') return null
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}

interface ChargeWindowPanelProps {
  roster: unknown[]
  nameFor: (slug: string) => string
}

export function ChargeWindowPanel({ roster, nameFor }: ChargeWindowPanelProps) {
  const [slug, setSlug] = useState(UNIT_SLUGS[0])
  const [cube, setCube] = useState(CUBES[0].name)
  const [withLiberalio, setWithLiberalio] = useState(true)
  const [chargeSpeed, setChargeSpeed] = useState('')
  const [maxAmmo, setMaxAmmo] = useState('')
  const [result, setResult] = useState<ChargeWindowResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      const chargeSpeedValue = optional(chargeSpeed)
      const maxAmmoValue = optional(maxAmmo)
      setResult(await postChargeWindow({
        slug,
        roster,
        withLiberalio: slug === LIBERALIO_SLUG ? false : withLiberalio,
        cube,
        overrides: {
          chargeSpeedLines: chargeSpeedValue === null ? null : [chargeSpeedValue],
          maxAmmoPercent: maxAmmoValue === null ? null : maxAmmoValue / 100,
          reloadSpeedPercent: null,
        },
      }))
    } catch {
      setResult(null)
      setError('계산에 실패했습니다. 해당 유닛이 로스터에 있는지 확인해 주세요.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="charge-panel">
      {/* 고르는 것은 네 가지뿐인데 입력이 카드 폭을 다 쓰면 줄만 길어지고 답은
          그 아래로 밀려난다. 입력은 왼쪽 한 칸에 모으고 답은 옆에 세운다 -
          미란다 계산기가 편성 옆에 답을 두는 것과 같은 이유다. */}
      <div className="charge-panel__form">
        <label className="field__label" htmlFor="charge-unit">유닛</label>
        <select
          id="charge-unit"
          className="field__input"
          value={slug}
          onChange={(event) => setSlug(event.target.value)}
        >
          {UNIT_SLUGS.map((unitSlug) => (
            <option key={unitSlug} value={unitSlug}>{nameFor(unitSlug)}</option>
          ))}
        </select>

        <span className="field__label-row">
          <label className="field__label" htmlFor="charge-cube">하모니 큐브</label>
          <HelpTip label="하모니 큐브">
            <HelpText>{HELP.charge.cube}</HelpText>
          </HelpTip>
        </span>
        <select
          id="charge-cube"
          className="field__input"
          value={cube}
          onChange={(event) => setCube(event.target.value)}
        >
          {CUBES.map((option) => (
            <option key={option.name} value={option.name}>{option.label}</option>
          ))}
        </select>

        {/* Strange Currents makes Liberalio immune to external charge-speed
            effects, so pairing her with herself is not a choice that exists. */}
        {slug !== LIBERALIO_SLUG && (
          <label className="field__checkbox">
            <input
              type="checkbox"
              checked={withLiberalio}
              onChange={(event) => setWithLiberalio(event.target.checked)}
            />
            리버렐리오 동반
          </label>
        )}

        {/* The synced roster reports overload options already summed across gear,
            so the per-slot lines the two aggregation rules differ on are not
            recoverable from it. Typing the lines in is what makes the comparison
            possible, hence a standing caveat rather than a per-result note. */}
        <NumberField
          label="차지속도 합계"
          hint={HELP.charge.rosterFallbackHint}
          help={HELP.charge.speedTotal}
          value={chargeSpeed}
          onChange={setChargeSpeed}
          step={0.01}
        />
        <NumberField
          label="최대장탄 오버로드"
          hint={HELP.charge.rosterFallbackHint}
          help={HELP.charge.maxAmmo}
          value={maxAmmo}
          onChange={setMaxAmmo}
          step={0.01}
        />

        {/* 미란다 계산기의 실행 버튼과 같은 것 - 두 계산기가 나란히 있는 탭에서
            같은 일을 하는 버튼이 다르게 생길 이유가 없다. */}
        <div className="recommend-form__actions">
          <button type="button" className="btn btn--primary" onClick={run} disabled={busy}>
            {busy ? '계산 중…' : '계산'}
          </button>
        </div>
      </div>

      <div className="charge-panel__result">
        {error && <p className="field__error" role="alert">{error}</p>}
        {result && <ChargeWindowLadder result={result} />}
      </div>
    </section>
  )
}
