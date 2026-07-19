// 북마크릿이 window.open으로 연 우리 페이지에서 원시 payload를 받는다.
// 마운트 시 opener에게 ready를 알리고, blablalink 출처의 payload 메시지만
// 받아들여 백엔드 조립을 거쳐 onRoster로 넘긴다.
//
// onRoster는 최신 값을 ref에 담아 참조한다 - 소비자가 인라인 화살표
// (`useBookmarkletImport((raw) => ...)`)를 넘기면 렌더마다 새 참조가 들어오는데,
// 그걸 그대로 useCallback/useEffect 의존성에 넣으면 렌더마다 리스너를
// 떼었다 다시 붙이고 ready 신호도 다시 보내게 된다 - 그 사이 잠깐 리스너가
// 없는 창에 payload가 도착하면 조용히 유실된다. ref로 우회하면 effect가
// 마운트당 정확히 한 번만 등록/ready를 보내면서도 항상 최신 onRoster를 호출한다.

import { useCallback, useEffect, useRef, useState } from 'react'
import { assembleRoster, type RawRosterPayload } from '../api/assembleRoster'
import {
  AssembleRosterApiError,
  describeAssembleRosterApiError,
} from '../api/assembleRosterApiError'
import {
  BLABLALINK_ORIGIN,
  PAYLOAD_MESSAGE,
  READY_MESSAGE,
} from '../lib/bookmarklet'

type Status = 'idle' | 'importing' | 'done' | 'error'

// blablalink 출처를 통과한 메시지라도 payload 형태까지 보장되지는 않는다 -
// 모양이 어긋난 값을 assembleRoster로 그대로 보내지 않도록 최소한의 형태만 확인한다.
const isRawRosterPayload = (value: unknown): value is RawRosterPayload =>
  !!value &&
  typeof value === 'object' &&
  Array.isArray((value as RawRosterPayload).owned) &&
  Array.isArray((value as RawRosterPayload).character_details) &&
  Array.isArray((value as RawRosterPayload).recycle_room_researches)

export const useBookmarkletImport = (onRoster: (raw: unknown) => void) => {
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)

  const onRosterRef = useRef(onRoster)
  useEffect(() => {
    onRosterRef.current = onRoster
  })

  const handle = useCallback(async (payload: RawRosterPayload) => {
    setStatus('importing')
    setError(null)
    try {
      onRosterRef.current(await assembleRoster(payload))
      setStatus('done')
    } catch (e) {
      setError(
        e instanceof AssembleRosterApiError
          ? describeAssembleRosterApiError(e)
          : e instanceof Error
            ? e.message
            : String(e),
      )
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      if (event.origin !== BLABLALINK_ORIGIN) return
      const data = event.data as { type?: string; payload?: unknown }
      if (data?.type !== PAYLOAD_MESSAGE || !isRawRosterPayload(data.payload)) return
      void handle(data.payload)
    }
    window.addEventListener('message', listener)
    // 북마크릿은 이 창이 뜬 뒤에야 payload를 보낼 수 있으므로 준비됐음을 알린다.
    window.opener?.postMessage({ type: READY_MESSAGE }, BLABLALINK_ORIGIN)
    return () => window.removeEventListener('message', listener)
  }, [handle])

  return { status, error }
}
