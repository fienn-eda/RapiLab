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
//
// 한 계정이 여러 서버에 로스터를 가질 수 있어서 북마크릿은 후보를 여러 개
// 보낼 수 있다. 조립은 선택 이후로 미룬다 - 버릴 후보를 위해 백엔드를
// 왕복하지 않는다. 후보가 하나면 물어볼 것이 없으므로 바로 조립한다.

import { useCallback, useEffect, useRef, useState } from 'react'
import { assembleRoster, type RawRosterPayload } from '../api/assembleRoster'
import { takeSyncInbox } from '../api/syncInbox'
import {
  AssembleRosterApiError,
  describeAssembleRosterApiError,
} from '../api/assembleRosterApiError'
import {
  BLABLALINK_ORIGIN,
  PAYLOAD_MESSAGE,
  READY_MESSAGE,
} from '../lib/bookmarklet'

type Status = 'idle' | 'choosing' | 'importing' | 'done' | 'error'

// 인박스를 확인하는 주기. 동기화는 유저가 버튼을 누르고 앱으로 돌아오는
// 행위라 몇 초 지연은 눈에 띄지 않고, 더 촘촘히 찔러 봐야 얻을 것이 없다.
export const SYNC_POLL_MS = 2000

// open_id/nickname are client-only profile identifiers riding alongside the
// roster payload - assembleRoster strips them before they ever reach the
// backend, so they're re-attached here from the original payload, not from
// assembleRoster's response. `raw` is assembleRoster's response as-is
// (`{ units: [...] }`), not a NikkeDraft[] - parsing into real drafts happens
// downstream (see SyncRosterPanel's parseRosterJson).
export interface BookmarkletImportArgs {
  openId: string
  area: number
  nickname: string
  raw: unknown
}

/** 북마크릿이 올린 한 서버의 원시 로스터. `area`는 blablalink API의
 * `nikke_area_id`이고, 그 서버에서 실제로 니케가 조회된 것만 온다. */
interface ServerPayload {
  area: number
  nickname: string
  owned: unknown[]
  character_details: unknown[]
  recycle_room_researches: unknown[]
}

const isServerPayload = (value: unknown): value is ServerPayload =>
  !!value &&
  typeof value === 'object' &&
  typeof (value as ServerPayload).area === 'number' &&
  Array.isArray((value as ServerPayload).owned) &&
  Array.isArray((value as ServerPayload).character_details) &&
  Array.isArray((value as ServerPayload).recycle_room_researches)

// 이미 설치된 북마크릿은 서버 하나(area 81)를 payload 최상단에 펼쳐 보낸다.
const isLegacyPayload = (value: unknown): value is RawRosterPayload =>
  !!value &&
  typeof value === 'object' &&
  Array.isArray((value as RawRosterPayload).owned) &&
  Array.isArray((value as RawRosterPayload).character_details) &&
  Array.isArray((value as RawRosterPayload).recycle_room_researches)

/** 어느 모양으로 왔든 서버 목록 하나로 만든다. 구 payload는 area 81로 조회된
 * 데이터이므로 81을 붙이는 것이 정확하다. */
const toServers = (payload: unknown): ServerPayload[] | null => {
  const p = payload as { servers?: unknown }
  if (Array.isArray(p?.servers)) {
    return p.servers.every(isServerPayload) ? (p.servers as ServerPayload[]) : null
  }
  if (isLegacyPayload(payload)) {
    return [
      {
        area: 81,
        nickname: String((payload as RawRosterPayload).nickname ?? ''),
        owned: payload.owned,
        character_details: payload.character_details,
        recycle_room_researches: payload.recycle_room_researches,
      },
    ]
  }
  return null
}

export const useBookmarkletImport = (
  onRoster: (args: BookmarkletImportArgs) => void,
) => {
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState('')
  const [servers, setServers] = useState<ServerPayload[]>([])

  const onRosterRef = useRef(onRoster)
  useEffect(() => {
    onRosterRef.current = onRoster
  })

  const importServer = useCallback(async (id: string, server: ServerPayload) => {
    setStatus('importing')
    setError(null)
    try {
      const assembled = await assembleRoster({
        owned: server.owned,
        character_details: server.character_details,
        recycle_room_researches: server.recycle_room_researches,
      })
      onRosterRef.current({
        openId: id,
        area: server.area,
        nickname: server.nickname,
        raw: assembled,
      })
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

  const handle = useCallback(
    (payload: unknown) => {
      // 출처를 통과한 메시지라도 payload 형태까지 보장되지는 않는다. 모양이
      // 어긋난 것은 조용히 무시한다 - 우리가 보낸 것이 아닐 수도 있고, 화면에
      // 에러를 띄울 근거가 없다. `null`/`undefined`에 속성을 읽으면 던지므로
      // 이 검사가 open_id 검사보다 반드시 앞에 온다.
      if (!payload || typeof payload !== 'object') return
      const list = toServers(payload)
      if (list === null || list.length === 0) return

      setError(null)
      // open_id는 프로필 저장소 키의 절반이다. 없으면 어느 계정인지 알 수 없어
      // 이름 없는 프로필이 생기므로, 받지 않고 그 자리에서 거절한다. 여기까지
      // 왔다면 로스터 모양은 맞으므로, 이것은 조용히 무시할 문제가 아니다.
      const id = String((payload as { open_id?: unknown }).open_id ?? '').trim()
      if (id === '') {
        setError(
          '북마크릿이 계정 정보를 보내지 않았어요. "동기화 방법"을 열어 북마크릿을 다시 설치한 뒤 시도해 주세요.',
        )
        setStatus('error')
        return
      }
      setOpenId(id)
      setServers(list)
      if (list.length === 1) {
        void importServer(id, list[0])
        return
      }
      setStatus('choosing')
    },
    [importServer],
  )

  const choose = useCallback(
    (area: number) => {
      // The picker's buttons stay mounted while a choice imports, so a second
      // click (or the same click landing twice) before it settles must not
      // start a second assembleRoster call for the same candidate.
      if (status === 'importing') return
      const server = servers.find((s) => s.area === area)
      if (!server) return
      void importServer(openId, server)
    },
    [status, servers, openId, importServer],
  )

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      if (event.origin !== BLABLALINK_ORIGIN) return
      const data = event.data as { type?: string; payload?: unknown }
      if (data?.type !== PAYLOAD_MESSAGE) return
      handle(data.payload)
    }
    window.addEventListener('message', listener)
    // 북마크릿은 이 창이 뜬 뒤에야 payload를 보낼 수 있으므로 준비됐음을 알린다.
    window.opener?.postMessage({ type: READY_MESSAGE }, BLABLALINK_ORIGIN)
    return () => window.removeEventListener('message', listener)
  }, [handle])

  // 북마크릿이 로컬 인박스에 두고 간 것을 집어온다. 네이티브 창에는 위
  // postMessage가 닿지 않으므로 앱에서는 이 경로가 실제로 쓰이는 쪽이다.
  //
  // idle일 때만 돈다: 후보를 고르는 중이거나 조립 중에 새 payload가 끼어들면
  // 유저가 방금 누른 것과 다른 로스터가 들어온다.
  useEffect(() => {
    if (status !== 'idle') return
    const controller = new AbortController()
    let stopped = false

    const check = async () => {
      try {
        const payload = await takeSyncInbox(controller.signal)
        if (!stopped && payload) handle(payload)
      } catch {
        // 서버가 아직 없거나(개발 중 백엔드 미기동) 잠깐 끊긴 것이다.
        // 화면에 띄울 일이 아니라 다음 주기를 기다리면 된다.
      }
    }

    const timer = setInterval(() => void check(), SYNC_POLL_MS)
    void check()
    return () => {
      stopped = true
      controller.abort()
      clearInterval(timer)
    }
  }, [status, handle])

  const candidates = servers.map((s) => ({ area: s.area, count: s.owned.length }))

  return { status, error, candidates, choose }
}
