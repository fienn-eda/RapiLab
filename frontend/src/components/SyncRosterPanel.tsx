// blablalink 동기화 안내: 공유 URL -> 개인화 북마크릿 링크 -> (유저가 blablalink에서
// 클릭) -> postMessage 수신 -> 로스터 병합. 자격증명은 어디에도 저장하지 않는다.

import { useEffect, useState } from 'react'
import { parseShareUrl } from '../lib/shareUrl'
import { buildLocalSyncBookmarklet, type KnownAccount } from '../lib/bookmarklet'
import { useBookmarkletImport } from '../hooks/useBookmarkletImport'
import { parseRosterJson } from '../lib/rosterImport'
import { serverLabel } from '../types/server'
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
   * 서버의 이름을 이미 아는지. 북마크릿의 호출 수를 줄이는 데만 쓴다.
   * blablalink가 호출이 잦으면 거절하므로(code 1300015), 아는 계정을 다시
   * 동기화할 때 다섯 서버를 또 훑을 이유가 없다. */
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
  const [summary, setSummary] = useState<string | null>(null)
  // Parse warning lines (e.g. which owned units are not yet supported), shown
  // verbatim so a syncing user is told too.
  const [notes, setNotes] = useState<string[]>([])

  const { status, error, candidates, choose } = useBookmarkletImport(
    ({ openId, area, nickname, nicknameError, raw }) => {
      const { drafts, warnings } = parseRosterJson(raw)
      onImport({ openId, area, nickname, roster: drafts })
      setSummary(`${drafts.length}기 동기화됨`)
      // 닉네임은 로스터와 다른 호출(GetUserProfileBasicInfo)에서 오고, 그 실패는
      // 동기화를 죽이지 않으려고 삼킨다. 삼킨 것을 말하지 않으면 화면이 계정
      // 이름 자리에 UID를 띄우는데, 유저에게는 그게 「이름이 잘못 나온다」로만
      // 보이고 무엇을 해야 할지는 알 수 없다.
      //
      // 남는 원인은 빈도 제한이다(blablalink code 1300015 "Requests are too
      // frequent"). 북마크릿이 간격을 두고 재시도까지 하므로 여기까지 오는 것은
      // 제한이 세션에 누적된 경우 - 계정을 연달아 동기화할 때다. 그때 할 일은
      // 재설치가 아니라 잠시 기다렸다 다시 하는 것이다. 북마크릿이 적어 보낸
      // 응답을 그대로 붙인다 - 이것이 없으면 왜 비었는지 물어볼 곳이 없다.
      setNotes(
        nickname || !nicknameError
          ? warnings
          : [
              ...warnings,
              '계정 이름을 읽지 못해 UID로 표시했어요. 로스터는 정상이에요. ' +
                '잠시 뒤 이 계정만 다시 동기화하면 이름이 붙어요.' +
                (nicknameError ? ` (이름 조회 응답: ${nicknameError})` : ''),
            ],
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
    // 남아 있으면 방금 만든 북마크가 최신인 줄 알게 된다.
    setCopied('idle')
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
            <HelpText>{HELP.sync.bookmarkletHint}</HelpText>
          </p>
          {/* 드래그가 아니라 복사인 이유: 앱은 네이티브 창이라 북마크 바가
              없고, 창 밖으로 링크를 끌어내는 것도 브라우저처럼 동작하지
              않는다. 주소만 손에 쥐면 북마크는 브라우저에서 만들 수 있다. */}
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              const url = buildLocalSyncBookmarklet(openId, knownFor?.(openId))
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
              {HELP.sync.copied}
            </p>
          )}
          {copied === 'manual' && (
            <>
              <p className="sync__hint" role="status">
                {HELP.sync.copyBlocked}
              </p>
              <textarea
                className="field__input"
                readOnly
                rows={3}
                aria-label="북마크릿 주소"
                value={buildLocalSyncBookmarklet(openId, knownFor?.(openId))}
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
          <p className="sync__hint">{HELP.sync.chooseServer}</p>
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
