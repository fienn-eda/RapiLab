// 이번 회차 보스 카드. 고르면 약점 속성만 보스 설정에 들어가고, 공지가 명시하지
// 않은 것(거리·저지 부위·스쿼드 추천)은 원문 그대로 카드에 남는다 — 우리 플래그로
// 번역하면 틀렸을 때 값 검증을 전부 통과하고 조용히 초록으로 남기 때문이다.

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
            <span className="rotation-picker__head">
              {boss.weakness && (
                <img
                  className="rotation-picker__icon"
                  src={WEAKNESS_ICON[boss.weakness]}
                  alt={elementLabel(boss.weakness)}
                />
              )}
              <span className="rotation-picker__name">{boss.name}</span>
            </span>
            <dl className="rotation-picker__stated">
              {Object.entries(boss.stated).map(([key, value]) => (
                <div className="rotation-picker__stated-row" key={key}>
                  <dt>{key}</dt>
                  <dd>
                    {Array.isArray(value)
                      ? value.map((line) => <span key={line}>{line}</span>)
                      : value}
                  </dd>
                </div>
              ))}
            </dl>
          </label>
        ))}
      </div>
      <p className="group__hint">
        공지 원문이에요. 약점 속성만 자동으로 채워지고, 나머지는 직접 확인해서 체크하세요.
      </p>
    </div>
  )
}
