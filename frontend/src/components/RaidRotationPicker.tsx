// 이번 회차 보스 카드. 이름과 약점 아이콘만 그린다 — 고르면 어떤 값이 채워지는지는
// 「보스 설정」 옆 설명이 말하고, 공지 원문 전문은 `stated`에 기록으로 남아 있되
// 화면에는 나오지 않는다(Fienn, 2026-08-07).

import { useId } from 'react'
import { WEAKNESS_ICON } from '../lib/elementIcon'
import { elementLabel } from '../lib/elementName'
import type { RaidRotation, RotationBoss } from '../types/raidRotation'

interface RaidRotationPickerProps {
  rotation: RaidRotation
  /** 지금 골라져 있는 보스 이름. 아무것도 안 고른 상태는 null. */
  selectedName: string | null
  onPick: (boss: RotationBoss) => void
}

export function RaidRotationPicker({
  rotation,
  selectedName,
  onPick,
}: RaidRotationPickerProps) {
  const groupId = useId()

  return (
    <div className="field">
      <span className="field__label" id={`${groupId}-label`}>
        {rotation.title} 보스
      </span>
      {/* 진짜 라디오를 시각적으로만 숨긴다 — 약점 선택과 같은 이유로, div/button으로
          만들면 화살표 이동과 화면 낭독기의 그룹 읽기를 둘 다 잃는다. */}
      <div
        className="rotation-picker"
        role="radiogroup"
        aria-labelledby={`${groupId}-label`}
      >
        {rotation.bosses.map((boss) => (
          <label key={boss.name} className="rotation-picker__option">
            <input
              type="radio"
              className="visually-hidden"
              name={groupId}
              checked={selectedName === boss.name}
              onChange={() => onPick(boss)}
            />
            <img
              className="rotation-picker__icon"
              src={WEAKNESS_ICON[boss.weakness]}
              alt={elementLabel(boss.weakness)}
            />
            <span className="rotation-picker__name">{boss.name}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
