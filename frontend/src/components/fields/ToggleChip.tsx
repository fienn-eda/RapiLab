// 켜고 끄는 것을 버튼처럼 보이게 하되 진짜 input을 남긴다. div/button으로 만들면
// 라디오 그룹의 화살표 이동과 화면 낭독기의 그룹 읽기를 둘 다 잃는다 -
// .element-picker(약점 칩)가 같은 이유로 같은 구조다.
//
// help가 <label> 밖에 서는 것이 이 구조의 요점이다: 라벨 안에서는 아무 클릭이나
// 컨트롤을 토글하므로, 설명을 열려던 클릭이 설정을 바꾼다.

import type { ReactNode } from 'react'

interface ToggleChipProps {
  type: 'checkbox' | 'radio'
  checked: boolean
  onChange: (checked: boolean) => void
  children: ReactNode
  /** 라디오 그룹을 묶는 이름. checkbox에는 필요 없다. */
  name?: string
  /** 칩 옆에 서는 설명. 라벨 밖이라 눌러도 토글되지 않는다. */
  help?: ReactNode
}

export function ToggleChip({
  type,
  checked,
  onChange,
  children,
  name,
  help,
}: ToggleChipProps) {
  return (
    <span className="chip-toggle">
      <label className="chip-toggle__label">
        <input
          type={type}
          className="visually-hidden"
          name={name}
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
        />
        {children}
      </label>
      {help}
    </span>
  )
}
