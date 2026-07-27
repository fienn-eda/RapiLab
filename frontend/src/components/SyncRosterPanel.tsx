// blablalink 동기화 안내: 공유 URL -> 개인화 북마크릿 링크 -> (유저가 blablalink에서
// 클릭) -> postMessage 수신 -> 로스터 병합. 자격증명은 어디에도 저장하지 않는다.

import { useEffect, useState } from 'react'
import { parseShareUrl } from '../lib/shareUrl'
import { buildBookmarklet } from '../lib/bookmarklet'
import { useBookmarkletImport } from '../hooks/useBookmarkletImport'
import { parseRosterJson } from '../lib/rosterImport'
import type { NikkeDraft } from '../types/nikkeDraft'
import { SyncHelp } from './SyncHelp'

interface SyncRosterPanelProps {
  onImport: (args: {
    openId: string
    nickname: string
    roster: NikkeDraft[]
  }) => void
  /** 활성 프로필이 없는 화면에서는 도움말이 펼쳐진 채로 시작한다 - 아직 아무것도
   * 동기화하지 못한 유저가 토글을 "발견"할 필요가 없어야 한다. */
  defaultHelpOpen?: boolean
}

export function SyncRosterPanel({ onImport, defaultHelpOpen = false }: SyncRosterPanelProps) {
  const [helpOpen, setHelpOpen] = useState(defaultHelpOpen)
  const [openId, setOpenId] = useState<string | null>(null)
  const [urlError, setUrlError] = useState<string | null>(null)
  const [summary, setSummary] = useState<string | null>(null)
  // Parse warning lines (e.g. which owned units are not yet supported), shown
  // verbatim so a syncing user is told too.
  const [notes, setNotes] = useState<string[]>([])

  const { status, error } = useBookmarkletImport(({ openId, nickname, raw }) => {
    const { drafts, warnings } = parseRosterJson(raw)
    onImport({ openId, nickname, roster: drafts })
    setSummary(`${drafts.length}기 동기화됨`)
    setNotes(warnings)
  })

  // A fresh import run supersedes whatever summary/error is on screen.
  useEffect(() => {
    if (status === 'importing') {
      setSummary(null)
      setNotes([])
    }
  }, [status])

  const handleUrl = (value: string) => {
    setSummary(null)
    setNotes([])
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
      <div className="sync__header">
        <h2 className="sync__title">blablalink에서 동기화</h2>
        <button
          type="button"
          className="sync__help-toggle"
          aria-expanded={helpOpen}
          aria-controls="sync-help"
          onClick={() => setHelpOpen((open) => !open)}
        >
          동기화 방법
        </button>
      </div>
      <SyncHelp id="sync-help" hidden={!helpOpen} />
      <div className="field">
        <label className="field__label" htmlFor="share-url">
          ShiftyPad 공유 URL
        </label>
        <input
          id="share-url"
          type="text"
          className="field__input"
          onChange={(e) => handleUrl(e.target.value)}
          placeholder="https://www.blablalink.com/shiftyspad?uid=..."
        />
      </div>
      {urlError && (
        <p className="sync__error" role="alert">
          {urlError}
        </p>
      )}
      {openId && (
        <div className="sync__bookmarklet">
          <p className="sync__hint">
            이 링크를 북마크 바로 드래그한 다음, blablalink 페이지를 열고
            로그인한 상태에서 눌러요. 로스터가 새 탭에서 열리므로, 이 탭은
            새로고침해야 갱신돼요.
          </p>
          <a
            className="btn btn--ghost"
            href="#"
            // React 19 blocks a `javascript:` string passed through the `href`
            // prop ("blocked a javascript: URL as a security precaution") - a
            // bookmarklet's href IS that string, so it's set via the DOM
            // directly instead, which React's sanitiser doesn't intercept.
            // A ref callback (rather than a passive effect) sets it during
            // commit, before paint, so the anchor is never briefly draggable
            // as a dead `href="#"` link.
            ref={(el) => {
              if (!el) return
              try {
                el.href = buildBookmarklet(openId, window.location.origin)
              } catch (e) {
                // appOrigin isn't a plain http(s) origin (e.g. opened via
                // file://) - surface it like any other URL problem instead
                // of letting the throw escape the commit phase.
                setOpenId(null)
                setUrlError(e instanceof Error ? e.message : String(e))
              }
            }}
          >
            니케 로스터 동기화
          </a>
        </div>
      )}
      {status === 'importing' && <p className="sync__message">가져오는 중…</p>}
      {summary && <p className="sync__message">{summary}</p>}
      {notes.map((note, i) => (
        <p className="sync__message" key={i}>
          {note}
        </p>
      ))}
      {error && (
        <p className="sync__error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
