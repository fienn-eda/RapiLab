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
  /** 그 보스와 싸우며 화면에서 잰 코어 지름을 엔진 단위로 환산한 값. 공지가
   *  아니라 실측에서 오는 유일한 필드다. 안 잰 보스는 null이고, 그때
   *  코어히트율은 모델링되지 않는다. */
  core_diameter_px: number | null
  /** 그 보스와 싸우며 관측한 파츠 파괴 시각들(초). 코어 지름과 같은 계열이라
   *  공지에서 오지 않는다. 빈 목록이면 파괴에 반응하는 스킬은 부위파괴 불리언만
   *  보던 근사로 돈다. */
  part_destruction_times: number[]
  /** 잡몹이 주기적으로 생성되는가. 공지가 「소환」을 적더라도 그것만으로 켜지지
   *  않는다 — 나오는 잡몹을 실제로 쳐야 하는지는 그 보스와 싸워 봐야 안다. */
  spawns_adds: boolean
  /** 이 보스를 상대하는 요령. 공지가 아니라 그 보스와 싸워 본 사람이 적는
   *  값이라 없을 수 있다 — 코어 지름·파괴 시각과 같은 계열이다.
   *
   *  엔진은 이 값을 읽지 않는다. 화면(시즌 가이드 카드)이 기본 내용으로 깔고,
   *  사용자가 앱에서 고치면 그쪽이 이긴다. **이 필드가 릴리즈 빌드에 가이드를
   *  싣는 유일한 길이다** — localStorage는 기기에 붙지 번들에 안 들어간다.
   *
   *  `at`은 전투 시작으로부터 경과 초로, `part_destruction_times`와 같은
   *  단위다. null이면 시각에 매이지 않는 「상시」 항목이다. */
  guide?: RotationGuideEntry[]
  /** 공지 원문 기록. 항목은 솔로/유니온이 다르므로 자유 형식이다. */
  stated: Record<string, string | string[]>
}

export interface RotationGuideEntry {
  at: number | null
  text: string
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
