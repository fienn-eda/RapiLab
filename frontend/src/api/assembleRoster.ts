// 북마크릿이 모은 원시 payload를 백엔드에 조립시킨다. 백엔드는 이 본문을
// 저장하지 않는다 (무상태) - 서브프로젝트 4 스펙의 프라이버시 규율.

import { getClientId } from '../lib/clientId'
import { AssembleRosterApiError } from './assembleRosterApiError'

export interface RawRosterPayload {
  owned: unknown[]
  character_details: unknown[]
  recycle_room_researches: unknown[]
  // 계정의 싱크로 디바이스 레벨. 백엔드가 이 레벨로 유니온용 스탯을 조립한다.
  // 옛 북마크릿은 보내지 않으므로 옵셔널이다.
  synchro_level?: number
  // 클라이언트 전용 프로필 식별자 - 백엔드는 이 값들을 모른다 (아래 destructure로 배제).
  open_id?: string
  nickname?: string
}

export const assembleRoster = async (
  payload: RawRosterPayload,
): Promise<unknown> => {
  // open_id/nickname은 여기서 분리해 버린다 - 백엔드는 roster 필드만 받는다.
  const { open_id, nickname, ...rosterPayload } = payload
  const response = await fetch('/api/assemble-roster', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Client-Id': getClientId(),
    },
    body: JSON.stringify(rosterPayload),
  })
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new AssembleRosterApiError(response.status, detail)
  }
  return await response.json()
}
