// 이름 붙여 남겨 둔 결과 하나를 골라 편성으로 가져오는 버튼. 누르면 그 자리에
// 고르기 목록이 펼쳐진다.
//
// SavedRunList를 재사용하지 않는 이유: 저쪽은 펼쳐서 결과를 읽고 이름을 바꾸고
// 지우는 관리 목록이고, 이쪽은 고르면 끝나는 선택 목록이다. 한 컴포넌트에 두
// 역할을 넣으면 props가 역할 스위치로 갈라진다.

import { useState } from 'react'
import { HELP } from '../lib/helpText'
import { savedAtLabel } from '../lib/savedRunLabel'
import type { Draft } from '../types/draft'
import type { SavedRun } from '../types/profile'

interface ImportRunButtonProps {
  /** 이 탭의 보관물, 최신순. */
  runs: SavedRun[]
  /** 이미 앉은 니케가 있으면 덮어쓸지 한 번 묻는다. 비어 있으면 잃을 것이 없다. */
  draft: Draft
  onImport: (run: SavedRun) => void
}

export function ImportRunButton({ runs, draft, onImport }: ImportRunButtonProps) {
  const [open, setOpen] = useState(false)
  const hasSeats = draft.decks.some((seats) => seats.length > 0)

  const pick = (run: SavedRun) => {
    if (hasSeats && !window.confirm(HELP.draftActions.confirmOverwrite)) return
    onImport(run)
    setOpen(false)
  }

  return (
    <div className="import-run">
      <button
        type="button"
        className="btn import-run__toggle"
        disabled={runs.length === 0}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        저장한 결과 가져오기
      </button>

      {open && (
        <ul className="import-run__list">
          {runs.map((run) => (
            <li key={run.id} className="import-run__item">
              <span className="import-run__name">{run.name}</span>
              <span className="import-run__when">{savedAtLabel(run.savedAt)}</span>
              <button type="button" className="btn" onClick={() => pick(run)}>
                가져오기
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
