// 이번 회차 보스를 상대하기 전에 읽는 것. 왼쪽 컬럼(보스 설정 · 모드)이 「내가
// 고르는 것」이면 이 카드는 「내가 읽는 것」이다.
//
// 뱃지는 보스 설정에서 파생된다 - 손으로 다시 적지 않으므로 실제 계산 입력과
// 어긋날 수 없다. 솔로 탭은 보스 설정을 접어 두므로 그 값들을 비추는 유일한
// 자리이기도 하다.
//
// 문장만 사람이 쓴다. 지금은 localStorage에만 남는다(useBossGuides의 주석 참조).

import { gimmickBadges } from '../lib/bossBadges'
import { guideTitle } from '../lib/bossLabel'
import { weaknessFor } from '../lib/elementAdvantage'
import { elementLabel } from '../lib/elementName'
import { useBossGuides } from '../hooks/useBossGuides'
import { FightTimeline } from './FightTimeline'
import type { BossProfileDraft } from '../types/bossProfileDraft'
import type { RaidRotation } from '../types/raidRotation'
import type { BossRangeBand } from '../types/recommend'

const RANGE_BAND_LABEL: Record<Exclude<BossRangeBand, null>, string> = {
  near: '근거리',
  mid: '중거리',
  far: '원거리',
}

/** 「1, 61, 126」을 숫자로. 폼은 편집 중일 수 있으므로 빈 조각을 버린다 -
 * Number('')는 0이라, 안 버리면 「1, 」이 0초짜리 눈금을 만든다. 제출을 막는
 * 판정은 validateBossProfileDraft가 따로 한다. */
const parseTimes = (raw: string): number[] =>
  raw
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part !== '')
    .map(Number)
    .filter((value) => Number.isFinite(value))

interface SeasonGuideCardProps {
  rotation: RaidRotation | null
  boss: BossProfileDraft
}

export function SeasonGuideCard({ rotation, boss }: SeasonGuideCardProps) {
  const { guideFor, setGuide } = useBossGuides()

  // 저장할 칸의 이름. 회차 보스를 안 골랐으면 없다 - 그 상태에서 입력을 받으면
  // 쓴 글이 어디에도 안 남는다.
  const key =
    rotation !== null && boss.boss_name !== null
      ? `${rotation.id}::${boss.boss_name}`
      : null

  const badges = [
    boss.element === null ? '약점 없음' : `${elementLabel(weaknessFor(boss.element))} 약점`,
    ...(boss.effective_range_band === null
      ? []
      : [RANGE_BAND_LABEL[boss.effective_range_band]]),
    ...gimmickBadges(boss),
  ]

  // 부위파괴가 꺼져 있으면 엔진이 시각을 무시한다 - 화면에서도 빠져야 지울 수
  // 없는 값이 계산에 쓰이는 것처럼 보이지 않는다.
  const times = boss.part_destructible ? parseTimes(boss.part_destruction_times) : []

  const title = guideTitle(rotation)

  return (
    <section className="guide-card" aria-label={title}>
      <h3 className="guide-card__title">{title}</h3>

      <p className="guide-card__badges">
        {badges.map((label) => (
          <span key={label} className="guide-badge">
            {label}
          </span>
        ))}
      </p>

      <FightTimeline
        durationSeconds={Number(boss.fight_duration)}
        destructionTimes={times}
      />

      {key === null ? (
        <p className="guide-card__empty">위에서 이번 회차 보스를 고르세요.</p>
      ) : (
        <textarea
          className="guide-card__text"
          aria-label="가이드 내용"
          placeholder="무엇을 챙기고 무엇을 피하는지"
          value={guideFor(key, '')}
          onChange={(event) => setGuide(key, event.target.value)}
        />
      )}
    </section>
  )
}
