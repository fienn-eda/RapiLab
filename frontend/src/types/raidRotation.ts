// TS mirror of GET /api/raid-rotations (backend/app/api.py RaidRotationsResponse).
// types/recommend.ts와 같은 이유로 snake_case를 그대로 둔다 — 파이썬 쪽이 진실의
// 원천이고, 이름을 바꾸면 두 파일을 대조할 수 없다.
//
// `stated`는 공지 원문 기록이다. 앱은 해석하지 않는다 — 화면이 읽는 값은
// `weakness`와 `range_band`뿐이고, 둘 다 판독 시점에 엔진 어휘로 옮겨 적힌다.

import type { NikkeElement } from './supportedUnit'
import type { BossRangeBand } from './recommend'

export type RaidKind = 'solo' | 'union'

export interface RotationBoss {
  name: string
  /** 공지가 적은 약점. 비어 있을 수 없다 — 로더가 거부한다. */
  weakness: NikkeElement
  /** 공지가 적은 거리. 유니온 공지에만 있어 솔로 보스는 null이고, 그때 적정거리는
   *  「모름」으로 남는다. */
  range_band: BossRangeBand
  /** 공지 원문 기록. 항목은 솔로/유니온이 다르므로 자유 형식이다. */
  stated: Record<string, string | string[]>
}

export interface RaidRotation {
  id: string
  raid: RaidKind
  title: string
  starts_at: string | null
  ends_at: string
  source_url: string
  source_locale: 'ko' | 'en'
  read_on: string
  bosses: RotationBoss[]
}

export interface RaidRotationsWire {
  schema_version: number
  rotations: RaidRotation[]
}

/** 이 레이드의 최신 회차. 없으면 null.
 *
 * `ends_at`이 가장 늦은 회차로 정한다. 배열 순서나 `read_on`으로 고르면 과거
 * 회차를 뒤늦게 채워 넣는 날 뒤집힌다. 문자열 비교가 아니라 파싱해서 비교하는
 * 이유는 오프셋이 다른 회차가 섞일 수 있어서다. */
export const latestRotationFor = (
  rotations: RaidRotation[],
  raid: RaidKind,
): RaidRotation | null =>
  rotations
    .filter((r) => r.raid === raid)
    .reduce<RaidRotation | null>(
      (best, r) =>
        best === null || Date.parse(r.ends_at) > Date.parse(best.ends_at) ? r : best,
      null,
    )
