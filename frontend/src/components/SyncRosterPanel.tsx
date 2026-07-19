// blablalink 동기화 안내: 공유 URL -> 개인화 북마크릿 링크 -> (유저가 blablalink에서
// 클릭) -> postMessage 수신 -> 로스터 병합. 자격증명은 어디에도 저장하지 않는다.

import { useEffect, useState } from 'react'
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
  // Parse warning lines (e.g. which owned units are not yet supported), shown
  // verbatim like ImportRosterButton's notes so a syncing user is told too.
  const [notes, setNotes] = useState<string[]>([])

  const { status, error } = useBookmarkletImport((raw) => {
    const { drafts, warnings } = parseRosterJson(raw)
    const { added, updated } = onImport(drafts, 'collector')
    setSummary(`${added} added, ${updated} updated`)
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
      <h2 className="sync__title">Sync from blablalink</h2>
      <div className="field">
        <label className="field__label" htmlFor="share-url">
          ShiftyPad share URL
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
            Drag this link to your bookmarks bar, then click it while logged in
            to blablalink. Your roster opens in a new tab, so this tab
            won&rsquo;t update until you reload it.
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
            Sync NIKKE roster
          </a>
        </div>
      )}
      {status === 'importing' && <p className="sync__message">Importing…</p>}
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
