// blablalink 동기화 안내: 공유 URL -> 개인화 북마크릿 링크 -> (유저가 blablalink에서
// 클릭) -> postMessage 수신 -> 로스터 병합. 자격증명은 어디에도 저장하지 않는다.

import { useEffect, useRef, useState } from 'react'
import { parseShareUrl } from '../lib/shareUrl'
import { buildBookmarklet } from '../lib/bookmarklet'
import { useBookmarkletImport } from '../hooks/useBookmarkletImport'
import { parseRosterJson } from '../lib/rosterImport'
import type { NikkeDraft } from '../types/nikkeDraft'

interface SyncRosterPanelProps {
  onImport: (
    drafts: NikkeDraft[],
    source: 'exia' | 'collector',
  ) => { added: number; updated: number }
}

export function SyncRosterPanel({ onImport }: SyncRosterPanelProps) {
  const [openId, setOpenId] = useState<string | null>(null)
  const [urlError, setUrlError] = useState<string | null>(null)
  const [summary, setSummary] = useState<string | null>(null)
  // React 19 blocks a `javascript:` string passed through the `href` prop
  // ("blocked a javascript: URL as a security precaution") - a bookmarklet's
  // href IS that string, so it's set via the DOM directly instead, which
  // React's sanitiser doesn't intercept.
  const bookmarkletRef = useRef<HTMLAnchorElement>(null)

  const { status, error } = useBookmarkletImport((raw) => {
    const { drafts } = parseRosterJson(raw)
    const { added, updated } = onImport(drafts, 'collector')
    setSummary(`${added} added, ${updated} updated`)
  })

  useEffect(() => {
    if (bookmarkletRef.current && openId) {
      bookmarkletRef.current.href = buildBookmarklet(openId, window.location.origin)
    }
  }, [openId])

  const handleUrl = (value: string) => {
    if (!value.trim()) {
      setOpenId(null)
      setUrlError(null)
      return
    }
    try {
      setOpenId(parseShareUrl(value))
      setUrlError(null)
    } catch (e) {
      setOpenId(null)
      setUrlError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <section className="sync">
      <h2>Sync from blablalink</h2>
      <label htmlFor="share-url">ShiftyPad share URL</label>
      <input
        id="share-url"
        type="text"
        onChange={(e) => handleUrl(e.target.value)}
        placeholder="https://www.blablalink.com/shiftyspad?uid=..."
      />
      {urlError && <p role="alert">{urlError}</p>}
      {openId && (
        <>
          <p>
            아래 링크를 북마크바로 드래그한 뒤, blablalink에 로그인한 상태에서
            눌러주세요.
          </p>
          <a ref={bookmarkletRef} href="#">
            Sync NIKKE roster
          </a>
        </>
      )}
      {status === 'importing' && <p>가져오는 중…</p>}
      {summary && <p>{summary}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
