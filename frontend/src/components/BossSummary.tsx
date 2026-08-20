// 결과가 어떤 보스를 상대로 나온 것인지 한 줄로 적는다. 보스 폼이 방어력과
// 전투 시간을 접어 두므로, 그 두 값이 결과에 남는 유일한 자리이기도 하다.

import type { BossProfile, BossRangeBand } from '../types/recommend'
import { gimmickBadges } from '../lib/bossBadges'
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
  const gimmicks = gimmickBadges(boss)

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
