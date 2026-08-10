// 이름 붙여 남겨 둔 결과들. 항목을 열면 그 자리에서 결과를 읽기 모드로 펼치고,
// 지금 화면에 떠 있는 계산 결과는 건드리지 않는다 - 폼이 바뀌는 것은 유저가
// "이 설정으로 폼 채우기"를 눌렀을 때뿐이다.
//
// 결과를 그리는 일은 renderRun에 맡긴다: 솔로 네 모드와 유니온이 서로 다른
// 컴포넌트로 그려지는데, 그 분기는 각 탭이 이미 하고 있다.

import { useId, useState, type ReactNode } from 'react'
import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'
import type { SavedRun } from '../types/profile'

const savedAtLabel = (savedAt: number): string => {
  const at = new Date(savedAt)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(at.getMonth() + 1)}-${pad(at.getDate())} ${pad(at.getHours())}:${pad(at.getMinutes())}`
}

interface SavedRunListProps {
  runs: SavedRun[]
  /** 펼친 항목의 결과를 그린다. 어떤 뷰냐에 따라 다른 컴포넌트가 나오므로
   * 그리는 일 자체는 탭이 맡는다. */
  renderRun: (run: SavedRun) => ReactNode
  onRestore: (run: SavedRun) => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
}

export function SavedRunList({
  runs,
  renderRun,
  onRestore,
  onRename,
  onDelete,
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

              {renderRun(run)}
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
