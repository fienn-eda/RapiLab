// 결과가 어떤 보스를 상대로 나온 것인지 한 줄로 적는다. 보스 폼이 방어력과
// 전투 시간을 접어 두므로, 그 두 값이 결과에 남는 유일한 자리이기도 하다.
//
// 켜진 기믹만 나온다 — 꺼진 기믹까지 적으면 줄만 길어지고, 없는 것은 화면에
// 없는 것으로 읽힌다.

import type { BossProfile, BossRangeBand } from '../types/recommend'
import { elementLabel } from '../lib/elementName'
import { weaknessFor } from '../lib/elementAdvantage'
import { formatDamage } from './formatDamage'

const RANGE_BAND_LABEL: Record<Exclude<BossRangeBand, null>, string> = {
  near: '근거리',
  mid: '중거리',
  far: '원거리',
}

interface BossSummaryProps {
  boss: BossProfile
}

export function BossSummary({ boss }: BossSummaryProps) {
  const gimmicks = [
    boss.core_hittable && '코어 피격',
    boss.pierce_hits_body_behind_core && '2관통',
    boss.part_destructible && '부위파괴',
    boss.spawns_adds && '잡몹 생성',
    boss.elemental_interrupt_required && '속성저지 필수',
  ].filter((label): label is string => typeof label === 'string')

  return (
    <p className="boss-summary">
      <span className="boss-summary__weakness">
        {boss.element === null ? '약점 없음' : `약점 ${elementLabel(weaknessFor(boss.element))}`}
      </span>
      {boss.effective_range_band !== null && (
        <span className="boss-summary__badge">
          {RANGE_BAND_LABEL[boss.effective_range_band]}
        </span>
      )}
      {gimmicks.map((label) => (
        <span key={label} className="boss-summary__badge">
          {label}
        </span>
      ))}
      <span className="boss-summary__number">방어력 {formatDamage(boss.enemy_def)}</span>
      <span className="boss-summary__number">{boss.fight_duration}초</span>
    </p>
  )
}
