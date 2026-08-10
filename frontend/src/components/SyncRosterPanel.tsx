// blablalink 동기화 안내: 공유 URL -> 개인화 북마크릿 링크 -> (유저가 blablalink에서
// 클릭) -> postMessage 수신 -> 로스터 병합. 자격증명은 어디에도 저장하지 않는다.

import { useEffect, useState } from 'react'
import { parseShareUrl } from '../lib/shareUrl'
import { buildLocalSyncBookmarklet, type KnownAccount } from '../lib/bookmarklet'
import { useBookmarkletImport } from '../hooks/useBookmarkletImport'
import { parseRosterJson } from '../lib/rosterImport'
import { SERVERS, serverLabel } from '../types/server'
import type { NikkeDraft } from '../types/nikkeDraft'
import { SyncHelp } from './SyncHelp'
import { HelpText } from './HelpText'
import { HELP } from '../lib/helpText'

interface SyncRosterPanelProps {
  onImport: (args: {
    openId: string
    area: number
    nickname: string
    roster: NikkeDraft[]
  }) => void
  /** 이 open_id에 대해 앱이 이미 아는 것 - 어느 서버에 로스터가 있고, 어느
   * 서버의 이름을 이미 아는지. 아는 서버만 조회해 동기화를 빠르게 하고, 이미
   * 아는 이름은 다시 묻지 않는다(다시 물어도 거절될 뿐이다). */
  knownFor?: (openId: string) => KnownAccount
  /** 활성 프로필이 없는 화면에서는 도움말이 펼쳐진 채로 시작한다 - 아직 아무것도
   * 동기화하지 못한 유저가 토글을 "발견"할 필요가 없어야 한다. */
  defaultHelpOpen?: boolean
  /** 인박스에서 로스터를 집어 처리하기 시작했을 때. 이 패널이 감춰져 있을 수
   * 있는 곳(탭)에서는 이 신호로 패널을 보이게 해야 한다 - 서버 선택 질문과
   * 결과·경고 줄이 전부 여기에만 있다. */
  onActivity?: () => void
}

export function SyncRosterPanel({
  onImport,
  defaultHelpOpen = false,
  onActivity,
  knownFor,
}: SyncRosterPanelProps) {
  const [helpOpen, setHelpOpen] = useState(defaultHelpOpen)
  const [openId, setOpenId] = useState<string | null>(null)
  const [urlError, setUrlError] = useState<string | null>(null)
  const [copied, setCopied] = useState<'idle' | 'ok' | 'manual'>('idle')
  // 어느 서버를 조회할지. null이면 앱이 아는 대로 - 아는 계정이면 그 서버만,
  // 처음 보는 계정이면 다섯을 다 훑는다. 직접 고르면 그 하나만 본다.
  //
  // 고르게 하는 이유는 속도다. 처음 보는 계정은 서버를 몰라 다섯을 다 훑는데,
  // 유저는 자기 서버를 안다.
  const [pickedArea, setPickedArea] = useState<number | null>(null)
  const [summary, setSummary] = useState<string | null>(null)
  // Parse warning lines (e.g. which owned units are not yet supported), shown
  // verbatim so a syncing user is told too.
  const [notes, setNotes] = useState<string[]>([])

  const { status, error, candidates, choose } = useBookmarkletImport(
    ({ openId, area, nickname, nicknameError, raw }) => {
      const { drafts, warnings } = parseRosterJson(raw)
      onImport({ openId, area, nickname, roster: drafts })
      setSummary(`${drafts.length}기 동기화됨`)
      // 이름 조회는 최선 노력이다 - ShiftyPad 화면이 뜨면서 같은 조회를 이미
      // 하기 때문에, 최초 동기화 시점에는 거의 늘 거절된다(2026-08-09 실측).
      // 그러니 「기다렸다 다시 하세요」는 거짓말이다. 유저가 실제로 할 수 있는
      // 일은 계정 드롭다운 옆에서 이름을 직접 붙이는 것 하나다.
      //
      // 설치된 북마크릿의 NAMED는 만들 때의 앱 상태 스냅샷이라, 유저가 이름을
      // 붙인 뒤에도 그 북마크릿은 계속 이름 조회를 시도해 거절당한다
      // (nicknameError≠''). 그래서 nicknameError만으로는 「안내가 필요한가」를
      // 못 가른다 - knownFor는 이번 동기화 직전 상태를 보므로 「이미 이름이
      // 있었나」를 정확히 답한다.
      const alreadyNamed = knownFor?.(openId)?.namedAreas.includes(area) ?? false
      setNotes(
        nickname || !nicknameError || alreadyNamed
          ? warnings
          : [...warnings, HELP.sync.nameUnavailable],
      )
    },
    onActivity,
  )

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
    // 주소가 바뀌면 북마크릿도 다른 계정의 것이 된다 - 앞의 "복사했어요"가
    // 남아 있으면 방금 만든 북마크가 최신인 줄 알게 된다. 서버 선택도 그
    // 계정의 것이므로 같이 비운다.
    setCopied('idle')
    setPickedArea(null)
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

  /** 고른 서버가 있으면 그 하나만, 없으면 앱이 아는 대로. */
  const buildBookmarklet = (id: string) => {
    const known = knownFor?.(id) ?? { areas: [], namedAreas: [] }
    if (pickedArea === null) return buildLocalSyncBookmarklet(id, known)
    return buildLocalSyncBookmarklet(id, {
      areas: [pickedArea],
      namedAreas: known.namedAreas.filter((area) => area === pickedArea),
    })
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
          {/* 서버를 고르면 그 하나만 조회한다. 모르면 「자동」이 앱이 아는 대로
              하고, 아는 것이 없으면 다섯을 다 훑는다 - 그때만 느리고, 그때만
              blablalink의 빈도 제한에 걸릴 수 있다. */}
          <div className="sync__servers">
            <p className="sync__hint">
              <HelpText>{HELP.sync.serverChoice}</HelpText>
            </p>
            <div className="sync__server-choices" role="group" aria-label="조회할 서버">
              <button
                type="button"
                className={pickedArea === null ? 'btn btn--primary' : 'btn'}
                aria-pressed={pickedArea === null}
                onClick={() => {
                  setPickedArea(null)
                  setCopied('idle')
                }}
              >
                자동
              </button>
              {SERVERS.map(({ area, label }) => (
                <button
                  key={area}
                  type="button"
                  className={pickedArea === area ? 'btn btn--primary' : 'btn'}
                  aria-pressed={pickedArea === area}
                  onClick={() => {
                    setPickedArea(area)
                    // 고른 서버가 바뀌면 앞서 복사한 북마크릿은 다른 서버의 것이다.
                    setCopied('idle')
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <p className="sync__hint">
            <HelpText>{HELP.sync.bookmarkletHint}</HelpText>
          </p>
          {/* 드래그가 아니라 복사인 이유: 앱은 네이티브 창이라 북마크 바가
              없고, 창 밖으로 링크를 끌어내는 것도 브라우저처럼 동작하지
              않는다. 주소만 손에 쥐면 북마크는 브라우저에서 만들 수 있다. */}
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              const url = buildBookmarklet(openId)
              navigator.clipboard?.writeText(url).then(
                () => setCopied('ok'),
                // 클립보드가 막힌 환경이면 직접 복사할 수 있게 보여준다.
                () => setCopied('manual'),
              ) ?? setCopied('manual')
            }}
          >
            북마크릿 주소 복사
          </button>
          {copied === 'ok' && (
            <p className="sync__hint" role="status">
              <HelpText>{HELP.sync.copied}</HelpText>
            </p>
          )}
          {copied === 'manual' && (
            <>
              <p className="sync__hint" role="status">
                <HelpText>{HELP.sync.copyBlocked}</HelpText>
              </p>
              <textarea
                className="field__input"
                readOnly
                rows={3}
                aria-label="북마크릿 주소"
                value={buildBookmarklet(openId)}
                onFocus={(e) => e.currentTarget.select()}
              />
            </>
          )}
        </div>
      )}
      {/* 한 계정이 여러 서버에 로스터를 가진 경우다. 어느 쪽을 원하는지는
          짐작할 수 없으므로 - 니케가 많은 쪽이 늘 정답은 아니다 - 물어본다. */}
      {status === 'choosing' && (
        <div className="sync__servers">
          <p className="sync__hint"><HelpText>{HELP.sync.chooseServer}</HelpText></p>
          <div className="sync__server-choices">
            {candidates.map(({ area, count }) => (
              <button
                key={area}
                type="button"
                className="btn"
                onClick={() => choose(area)}
              >
                {serverLabel(area)} ({count}기)
              </button>
            ))}
          </div>
        </div>
      )}
      {status === 'importing' && <p className="sync__message"><HelpText>{HELP.sync.importing}</HelpText></p>}
      {summary && <p className="sync__message">{summary}</p>}
      {notes.map((note, i) => (
        <p className="sync__message" key={i}>
          <HelpText>{note}</HelpText>
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
