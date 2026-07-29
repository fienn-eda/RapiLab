// The 차지 tab: how many shots a charge unit lands inside its Full Burst
// window, and what charge-speed total buys the next one.
//
// The numeric fields start empty, which means "use the synced roster". A typed
// value overrides it - the roster snapshot goes stale the moment gear changes,
// and for this screen that is the normal state rather than an error.

import { useState } from 'react'
import { postChargeWindow } from '../api/chargeWindow'
import type { ChargeWindowResult } from '../types/chargeWindow'
import { ChargeWindowLadder } from './ChargeWindowLadder'
import { NumberField } from './fields/NumberField'

const UNITS = [
  { slug: 'scarlet-black-shadow', label: '홍련: 흑영' },
  { slug: 'liberalio', label: '리버렐리오' },
  { slug: 'neon-vision-eye', label: '네온: 비전 아이' },
]

const LIBERALIO_SLUG = 'liberalio'

const optional = (raw: string): number | null => {
  const trimmed = raw.trim()
  if (trimmed === '') return null
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}

export function ChargeWindowPanel({ roster }: { roster: unknown[] }) {
  const [slug, setSlug] = useState(UNITS[0].slug)
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
      <label className="field__label" htmlFor="charge-unit">유닛</label>
      <select
        id="charge-unit"
        className="field__input"
        value={slug}
        onChange={(event) => setSlug(event.target.value)}
      >
        {UNITS.map((unit) => (
          <option key={unit.slug} value={unit.slug}>{unit.label}</option>
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

      <NumberField
        label="차지속도 합계"
        hint="(%, 비우면 동기화된 로스터 값)"
        value={chargeSpeed}
        onChange={setChargeSpeed}
        step={0.01}
      />
      {/* The synced roster reports overload options already summed across gear,
          so the per-slot lines the two aggregation rules differ on are not
          recoverable from it. Typing the lines in is what makes the comparison
          possible, hence a standing caveat rather than a per-result note. */}
      <p className="charge-panel__assumption">
        동기화된 로스터는 부위별 옵션이 아닌 합계만 알고 있어, 부위별 집계 규칙이
        다를 경우 결과가 한 프레임 갈릴 수 있습니다.
      </p>
      <NumberField
        label="최대장탄 오버로드"
        hint="(%, 비우면 동기화된 로스터 값)"
        value={maxAmmo}
        onChange={setMaxAmmo}
        step={0.01}
      />

      <p className="charge-panel__assumption">
        풀버스트 진입 시 탄창은 가득으로 가정합니다. 흑련은 아수라가 즉시 재장전하므로
        사실이고, 리버렐리오와 네온은 가정입니다.
      </p>

      <button type="button" className="button" onClick={run} disabled={busy}>
        계산
      </button>

      {error && <p className="field__error" role="alert">{error}</p>}
      {result && <ChargeWindowLadder result={result} />}
    </section>
  )
}
