// 라벨 옆에 붙는 설명. 마우스를 올리거나 키보드 포커스가 닿았을 때만 펼친다.
//
// 설명이 여럿 모이는 폼 - 보스 설정이 그렇다 - 에서는 문장들이 입력 칸보다
// 많은 세로를 먹어서, 정작 만지려는 컨트롤이 화면 밖으로 밀린다. 설명은
// 처음 한 번 읽으면 되는 것이므로 접어두고 물어볼 때만 답한다.
//
// 열고 닫는 것은 CSS(:hover / :focus-visible)가 하고 여기에는 상태가 없다.
// 클릭으로 고정하는 기능은 없다 - 포커스로 이미 열 수 있다.

import { useId, type ReactNode } from 'react'

interface HelpTipProps {
  /** 무엇에 대한 설명인지. 버튼의 접근성 이름이 된다. */
  label: string
  children: ReactNode
}

export function HelpTip({ label, children }: HelpTipProps) {
  const bubbleId = useId()

  return (
    <span className="help-tip">
      <button
        type="button"
        className="help-tip__button"
        aria-label={`${label} 설명`}
        aria-describedby={bubbleId}
      >
        ?
      </button>
      <span className="help-tip__bubble" id={bubbleId} role="tooltip">
        {children}
      </span>
    </span>
  )
}
