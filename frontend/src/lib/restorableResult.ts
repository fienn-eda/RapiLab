// 프로필에 저장해 둔 마지막 결과를 화면에 다시 올려도 되는지 판단한다.
//
// 캐시 조회(RecommendPanel의 getCached)와 똑같은 규칙을 쓴다: 지금 로스터와
// 지금 엔진 버전으로 다시 만든 해시가 저장 당시의 해시와 일치할 때만 그
// 결과가 지금도 유효하다. lastResultHash로 곧장 꺼내면 엔진 버전이 무효화
// 축(lib/inputHash.ts)에서 빠져나가, 옛 엔진이 낸 결과가 새 화면 코드로
// 흘러 들어간다 - RaidDeck에 필드가 하나 늘기만 해도 그리는 쪽이 없는 값을
// 읽고 터진다.

import { getResult, type Profile, type StoredResult } from '../types/profile'
import { hashRecommendInputs } from './inputHash'
import type { UserNikkeState } from '../types/userNikkeState'

export const restorableResult = (
  profile: Profile,
  roster: UserNikkeState[],
  engineVersion: string | null,
): StoredResult | null => {
  const { lastInputs, lastResultHash } = profile
  if (lastInputs === null || lastResultHash === null) return null

  const hash = hashRecommendInputs(
    roster,
    lastInputs.boss,
    lastInputs.draft,
    lastInputs.numDecks,
    engineVersion,
  )
  return hash === lastResultHash ? getResult(profile, hash) : null
}
