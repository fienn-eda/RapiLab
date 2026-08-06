// 화면에 떠 있는 결과에 이름을 붙여 남긴다. 저장이 거절될 수 있으므로(보관
// 상한) 확인 후에도 칸을 닫지 않고 이유를 말한다 - 눌렀는데 아무 일도 안 나는
// 화면을 만들지 않기 위해서다.

import { useId, useState } from 'react'
import { SAVED_RUNS_CAP } from '../types/profile'

interface SaveRunButtonProps {
  /** 이름 칸에 미리 채워 넣을 제안. */
  suggestedName: string
  /** 확인된 이름으로 저장한다. 상한에 걸려 거절되면 false. */
  onSave: (name: string) => boolean
}

export function SaveRunButton({ suggestedName, onSave }: SaveRunButtonProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [refused, setRefused] = useState(false)
  const fieldId = useId()

  const start = () => {
    setName(suggestedName)
    setRefused(false)
    setOpen(true)
  }

  const commit = () => {
    const trimmed = name.trim()
    if (trimmed === '') return
    if (onSave(trimmed)) {
      setOpen(false)
      return
    }
    setRefused(true)
  }

  if (!open) {
    return (
      <button type="button" className="btn" onClick={start}>
        저장
      </button>
    )
  }

  return (
    <span className="save-run">
      <label className="visually-hidden" htmlFor={fieldId}>
        이름
      </label>
      <input
        id={fieldId}
        className="field__input"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <button type="button" className="btn" onClick={commit}>
        확인
      </button>
      <button type="button" className="btn" onClick={() => setOpen(false)}>
        취소
      </button>
      {refused && (
        <span className="field__error" role="alert">
          보관은 {SAVED_RUNS_CAP}개까지예요. 목록에서 몇 개를 지우고 다시 저장해주세요.
        </span>
      )}
    </span>
  )
}
