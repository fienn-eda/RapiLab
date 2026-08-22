// 이름 붙여 남겨 둔 결과들. 항목을 열면 그 자리에서 결과를 읽기 모드로 펼치고,
// 지금 화면에 떠 있는 계산 결과는 건드리지 않는다 - 폼이 바뀌는 것은 유저가
// "이 설정으로 폼 채우기"를 눌렀을 때뿐이다.
//
// 결과를 그리는 일은 renderRun에 맡긴다: 솔로 네 모드와 유니온이 서로 다른
// 컴포넌트로 그려지는데, 그 분기는 각 탭이 이미 하고 있다.

import { useId, useState, type ReactNode } from 'react'
import { HELP } from '../lib/helpText'
import { savedAtLabel } from '../lib/savedRunLabel'
import { ErrorBoundary } from './ErrorBoundary'
import { HelpText } from './HelpText'
import type { VersionState } from '../hooks/useVersions'
import type { SavedRun } from '../types/profile'

interface SavedRunListProps {
  runs: SavedRun[]
  /** 펼친 항목의 결과를 그린다. 어떤 뷰냐에 따라 다른 컴포넌트가 나오므로
   * 그리는 일 자체는 탭이 맡는다. */
  renderRun: (run: SavedRun) => ReactNode
  onRestore: (run: SavedRun) => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
  /** 진단 정보에 적을 버전들. 없으면 「모름」으로 적힌다 - 진단을 못 만들 이유는
   * 아니다. */
  versions?: VersionState
}

const UNKNOWN_VERSIONS: VersionState = { engineVersion: null, appVersion: null }

/** 이 보관물의 덱들이 실제로 갖고 있는 키. 옛 모양이 못 열릴 때 원인을 가르는
 * 것이 정확히 이것이라, 진단에 넣는다 - 「어느 필드가 없는가」가 답이다. */
const deckFieldNames = (run: SavedRun): string[] => {
  const decks = (run.view as { decks?: unknown[] }).decks ?? []
  const names = new Set<string>()
  for (const deck of decks) {
    if (deck !== null && typeof deck === 'object') {
      for (const key of Object.keys(deck)) names.add(key)
    }
  }
  return [...names]
}

export function SavedRunList({
  runs,
  renderRun,
  onRestore,
  onRename,
  onDelete,
  versions = UNKNOWN_VERSIONS,
}: SavedRunListProps) {
  const [openId, setOpenId] = useState<string | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const renameFieldId = useId()

  if (runs.length === 0) {
    return <p className="empty__text"><HelpText>{HELP.savedRuns.empty}</HelpText></p>
  }

  const startRename = (run: SavedRun) => {
    setRenamingId(run.id)
    setRenameValue(run.name)
  }

  const commitRename = (id: string) => {
    const name = renameValue.trim()
    if (name === '') return
    onRename(id, name)
    setRenamingId(null)
  }

  return (
    <ul className="saved-runs">
      {runs.map((run) => (
        <li key={run.id} className="saved-runs__item">
          <button
            type="button"
            className="saved-runs__open"
            aria-expanded={openId === run.id}
            onClick={() => setOpenId(openId === run.id ? null : run.id)}
          >
            <span className="saved-runs__name">{run.name}</span>
            <span className="saved-runs__when">{savedAtLabel(run.savedAt)}</span>
          </button>

          {openId === run.id && (
            <div className="saved-runs__body">
              <div className="saved-runs__actions">
                <button type="button" className="btn" onClick={() => onRestore(run)}>
                  이 설정으로 폼 채우기
                </button>
                <button type="button" className="btn" onClick={() => startRename(run)}>
                  이름 바꾸기
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    if (window.confirm(HELP.savedRuns.confirmDelete(run.name))) onDelete(run.id)
                  }}
                >
                  삭제
                </button>
              </div>

              {renamingId === run.id && (
                <div className="field">
                  <label className="field__label" htmlFor={renameFieldId}>
                    이름
                  </label>
                  <input
                    id={renameFieldId}
                    className="field__input"
                    value={renameValue}
                    onChange={(event) => setRenameValue(event.target.value)}
                  />
                  <div className="saved-runs__actions">
                    <button type="button" className="btn" onClick={() => commitRename(run.id)}>
                      확인
                    </button>
                    <button type="button" className="btn" onClick={() => setRenamingId(null)}>
                      취소
                    </button>
                  </div>
                </div>
              )}

              {/* 보관물은 그때의 응답을 그대로 박제한 기록이라, 엔진이 나중에
                  더한 필드는 그 JSON에 아예 없다. 그런 옛 모양이 새 화면으로
                  들어오는 것은 구조적으로 막을 수 없고(로스터 재동기화에도 앱
                  업데이트에도 살아남는 것이 이 기능의 요점이다), 2026-08-22에는
                  그것이 트리 전체를 언마운트시켜 검은 화면이 됐다. 울타리를
                  항목마다 두는 이유가 그것이다 - 하나가 못 열려도 나머지는 열린다.

                  빠져나올 수는 울타리가 따로 주지 않는다: 위 saved-runs__actions
                  줄이 울타리 **바깥**이라 못 열리는 항목에서도 살아 있고, 거기
                  삭제는 확인 대화상자를 거친다. 울타리가 삭제를 하나 더 달면 같은
                  자리에 버튼이 둘이 되고 그중 하나만 확인을 안 묻는다. */}
              <ErrorBoundary
                title={`「${run.name}」은(는) 열 수 없습니다`}
                context={{
                  where: `저장한 결과 「${run.name}」`,
                  engineVersion: versions.engineVersion,
                  appVersion: versions.appVersion,
                  details: {
                    '저장 시각': savedAtLabel(run.savedAt),
                    탭: run.tab,
                    '덱이 가진 키': deckFieldNames(run),
                  },
                }}
              >
                {renderRun(run)}
              </ErrorBoundary>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
