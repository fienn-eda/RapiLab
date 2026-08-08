// 계산기 탭의 서브탭. 아래 CALCULATORS 배열이 그리는 것은 탭 버튼 행뿐이다.
// 계산기를 하나 늘리려면 배열에 항목을 더하고, role="tabpanel" 블록도 손으로
// 하나 더 쓴다 - 패널마다 받는 props가 달라(예: ChargeWindowPanel과
// MirandaCalculatorPanel) 배열 하나로는 못 만든다.
//
// 두 패널을 다 마운트한 채 hidden으로 감춘다 - 메인 탭이 이미 그렇고, 그래야
// 차지 계산기에 입력한 값이 서브탭을 오갈 때 날아가지 않는다.

import { useState } from 'react'
import type { BurstTier, SupportedUnit } from '../types/supportedUnit'
import type { UserNikkeState } from '../types/userNikkeState'
import { ChargeWindowPanel } from './ChargeWindowPanel'
import { MirandaCalculatorPanel } from './MirandaCalculatorPanel'
import type { UnitInvestment } from './UnitPalette'

type CalculatorId = 'charge' | 'miranda'

const CALCULATORS: { id: CalculatorId; label: string }[] = [
  { id: 'charge', label: '차속 + 타수 계산기' },
  { id: 'miranda', label: '미란다 계산기' },
]

interface CalculatorPanelProps {
  roster: UserNikkeState[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
  nameFor: (slug: string) => string
  burstTiersFor: (slug: string) => BurstTier[]
  investmentFor?: (slug: string) => UnitInvestment
}

export function CalculatorPanel({
  roster,
  supportedUnits,
  portraitFor,
  nameFor,
  burstTiersFor,
  investmentFor,
}: CalculatorPanelProps) {
  const [active, setActive] = useState<CalculatorId>('charge')

  return (
    <div className="calculators">
      <div className="tabs tabs--sub" role="tablist" aria-label="계산기">
        {CALCULATORS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`calc-tab-${id}`}
            aria-controls={`calc-panel-${id}`}
            aria-selected={active === id}
            className={active === id ? 'tabs__tab tabs__tab--active' : 'tabs__tab'}
            onClick={() => setActive(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id="calc-panel-charge"
        aria-labelledby="calc-tab-charge"
        hidden={active !== 'charge'}
      >
        <ChargeWindowPanel roster={roster} nameFor={nameFor} />
      </div>

      <div
        role="tabpanel"
        id="calc-panel-miranda"
        aria-labelledby="calc-tab-miranda"
        hidden={active !== 'miranda'}
      >
        <MirandaCalculatorPanel
          roster={roster}
          supportedUnits={supportedUnits}
          portraitFor={portraitFor}
          nameFor={nameFor}
          burstTiersFor={burstTiersFor}
          investmentFor={investmentFor}
        />
      </div>
    </div>
  )
}
