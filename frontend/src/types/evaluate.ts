// POST /api/evaluate-decks의 와이어 타입.
// SOURCE OF TRUTH: backend/app/api.py (EvaluateDecksRequest / EvaluateDecksResponse).
//
// /api/recommend-raid와의 차이는 방향이다. 저기는 엔진이 덱을 짜주고, 여기는
// 유저가 짠 덱을 채점만 한다 - 그래서 잠금도, 남은 유닛도, 대안 배치도 없다.
// 보스가 요청 하나에 하나가 아니라 덱마다 하나인 것도 여기뿐이다: 유니온
// 레이드는 3회 전투의 보스 속성을 유저가 전투마다 고른다.

import type { UserNikkeState } from './userNikkeState'
import type { BossProfile, DeckRecommendation } from './recommend'

export interface EvaluateDeckInput {
  units: string[] // 정확히 5개 슬러그. 소속만 — 자리 순서는 버스트 순서가 아니다.
  boss: BossProfile
}

export interface EvaluateDecksRequest {
  roster: UserNikkeState[]
  decks: EvaluateDeckInput[]
  /** 어느 스탯 벌로 잴지. 유니온은 레벨 보정이 없어 계정 싱크로 레벨로
   *  싸우고(`'actual'`), 솔로는 네 모드 모두 레벨 400 보정이다(`'raid400'`).
   *
   *  **이 엔드포인트는 두 컨텐츠가 공유한다** — 유니온 탭과 솔로 탭의 evaluate
   *  모드가 같이 쓴다. 그래서 기본값 없는 필수 필드다: 부르는 쪽이 자기 컨텐츠를
   *  말하지 않으면 타입이 거절한다. */
  stat_basis: 'raid400' | 'actual'
}

export interface EvaluateDecksResponse {
  // 각 덱의 `deck`은 엔진이 고른 최적 순서다 — 유저가 넣은 순서가 아니다.
  decks: DeckRecommendation[]
  combined_total_damage: number
  excluded_slugs: string[]
  engine_version: string
}

/** 유니온 레이드는 3회 전투다. 한 전투만 계산해보고 싶을 때를 위해 아래로 열어둔다. */
export const MIN_UNION_NUM_DECKS = 1
export const MAX_UNION_NUM_DECKS = 3
export const DEFAULT_UNION_NUM_DECKS = 3
