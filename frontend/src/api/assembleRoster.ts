// 북마크릿이 모은 원시 payload를 백엔드에 조립시킨다. 백엔드는 이 본문을
// 저장하지 않는다 (무상태) - 서브프로젝트 4 스펙의 프라이버시 규율.

import { getClientId } from '../lib/clientId'

export interface RawRosterPayload {
  owned: unknown[]
  character_details: unknown[]
  recycle_room_researches: unknown[]
}

export const assembleRoster = async (
  payload: RawRosterPayload,
): Promise<unknown> => {
  const response = await fetch('/api/assemble-roster', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Client-Id': getClientId(),
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error(`assemble-roster failed: ${response.status}`)
  }
  return await response.json()
}
